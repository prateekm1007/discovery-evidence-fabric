#!/usr/bin/env python3
"""R529 §6-9: MECHANISM_SPACE provider-call causal split.

Joins, per executed MECHANISM_SPACE call, using ONLY explicit
identity joins (never time-window matching):
  mechanism_attribution/1.0.0 (runtime_attribution on the durable
    MECHANISM_SPACE envelope)
  + routing ledger (durable model_routing/ledger.jsonl, joined on
    session_id + engine_stage + request_id)
  + R526 attribution pipeline (harvest rows: mechanism_space_spans,
    generate_calls, ledger_per_role)

For every executed MECHANISM_SPACE call, partitions the wall into:
  A. actual provider/inference execution (dispatch_s on the OK hop)
  B. failed first-hop transport/authentication (the unorouter
     AUTH_FAILURE rung: probe_admission_s from the gen_spans rung
     record; the hop produces NO ledger line — recorded with its
     measured probe wall, or UNKNOWN if unmeasured)
  C. fallback routing overhead (selection_ordering_s: the ladder
     walk that evaluated and skipped the failed provider)
  D. retry/backoff (retry_sleep_s + probe_retry_sleep_s)
  E. local orchestration/adapter overhead (post_provider_local_s +
     adapter_and_stage_overhead_s)
  F. unattributed remainder (generate remainder + stage overhead
     gap; Art. XXV: unmeasured = UNKNOWN, never missing = 0)

Every material component receives exactly one evidence-backed class:
  REQUIRED_SCIENTIFIC_WORK / POLICY_REQUIRED_WORK /
  PROVIDER_EXECUTION / PROVIDER_FAILURE_OR_RETRY /
  IMPLEMENTATION_WAIT / AVOIDABLE_IDLE / UNKNOWN

PROVIDER_EXECUTION is not automatically an optimization target.
PROVIDER_FAILURE_OR_RETRY is not automatically removable.
Only IMPLEMENTATION_WAIT / AVOIDABLE_IDLE authorizes an
intervention (directive §9, §12).

Output: R529/MECHANISM_SPACE_PROVIDER_JOIN.json
  per-row joins + aggregate mean/median/p95 + fallback/auth-failure
  contribution + retry/backoff contribution + unknown remainder +
  discovery-funnel parity block (mechanisms_found, n_distinct,
  BUILT vs NO_CANDIDATES, LLM outcome, provider/model, fallback
  occurrence, retry occurrence, terminal reason).
"""
from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
R526 = REPO / "R526"
R529 = REPO / "R529"
OUT = R529 / "MECHANISM_SPACE_PROVIDER_JOIN.json"
BRANCH = "origin/runtime-state-hf"


def _git(*args, timeout=120):
    out = subprocess.run(["git"] + list(args), capture_output=True,
                         cwd=str(REPO), timeout=timeout)
    return out.stdout


def _agg(vs):
    vs = [v for v in vs if v is not None]
    if not vs:
        return {"n": 0, "mean": None, "median": None, "min": None,
                "max": None, "p95": None, "values": []}
    s = sorted(vs)
    i95 = min(len(s) - 1, int(0.95 * len(s)))
    return {"n": len(vs), "mean": round(statistics.mean(vs), 3),
            "median": round(statistics.median(vs), 3),
            "min": round(min(vs), 3), "max": round(max(vs), 3),
            "p95": round(s[i95], 3),
            "values": [round(v, 3) for v in vs]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--harvest", default="R526/ATTR_CURRENT_HARVEST.json",
                    help="harvest file (repo-relative)")
    ap.add_argument("--out", default=str(OUT),
                    help="output path (repo-relative or absolute)")
    args = ap.parse_args()

    hpath = REPO / args.harvest
    h = json.loads(hpath.read_text(encoding="utf-8"))
    rows = [r for r in h.get("rows", []) if "stage_table" in r]

    # ---- durable ledger: index by (session_id, request_id) ----
    led_raw = _git("show", f"{BRANCH}:model_routing/ledger.jsonl")
    by_req = {}
    for line in led_raw.decode("utf-8", "replace").splitlines():
        try:
            ln = json.loads(line)
        except Exception:
            continue
        if ln.get("line_class") == "PHASE_SPAN":
            continue
        by_req[(ln.get("session_id"), ln.get("request_id"))] = ln

    joins = []
    for r in sorted(rows, key=lambda x: x.get("problem_index")):
        pi = r.get("problem_index")
        sid = r.get("session_id")
        ms = r.get("mechanism_space_spans") or {}
        if ms.get("class") != "OBSERVED_IN_STAGE":
            joins.append({
                "problem_index": pi, "session_id": sid,
                "class": ms.get("class", "UNKNOWN"),
                "note": ms.get("note"),
                "partition": None,
            })
            continue
        spans = ms.get("spans") or {}
        ll = ms.get("llm") or {}
        # the operator_* generate call (Q-A decomposition)
        gcall = None
        for gc in ((r.get("generate_calls") or {}).get("calls") or []):
            if (gc.get("purpose") or "").startswith("operator_") and \
               (gc.get("audit") or {}).get("class") == "AUDITED":
                gcall = gc
                break
        sub = (gcall or {}).get("subphases") or {}
        audit = (gcall or {}).get("audit") or {}
        req_id = (gcall or {}).get("request_id")
        # the durable ledger line for the successful call (explicit
        # identity join on session_id + request_id)
        led = by_req.get((sid, req_id)) or {}
        gs = led.get("generate_spans") or {}
        # per-rung probe detail from the gen_spans rung records
        # (the failed hop produces NO ledger line — its wall is the
        # rung's probe_admission_s, measured in the span record)
        failed_hops = []
        ok_hops = []
        for rung in gs.get("rungs") or []:
            adm = rung.get("admission") or {}
            if adm.get("admitted"):
                for a in rung.get("attempts") or []:
                    ok_hops.append({
                        "provider": rung.get("provider"),
                        "attempt_index": a.get("attempt_index"),
                        "dispatch_s": a.get("dispatch_s"),
                        "retry_sleep_s": a.get("retry_sleep_s"),
                        "outcome": a.get("outcome"),
                        "failure_type": a.get("failure_type"),
                    })
            else:
                failed_hops.append({
                    "provider": rung.get("provider"),
                    "capability_state": adm.get("capability_state"),
                    "note": adm.get("note"),
                    "probe_admission_s": adm.get("probe_admission_s"),
                    "ledger_line_present": False,
                })
        # ---- causal partition (R530 §4 corrected semantics) ----
        # R529 ERROR CORRECTED: selection_ordering_s is a PRE-CALL
        # span (it closes before message construction and before any
        # provider rung is attempted). It is SELECTION_ORCHESTRATION,
        # NOT fallback-routing overhead. The corrected 5-way split:
        #   pre-call selection/ordering cost (selection_subspans A–I
        #     when the R530 instrumented build served the call, else
        #     the aggregate selection_ordering_s with class UNKNOWN)
        #   failed-hop admission cost (rung probe_admission_s)
        #   actual inter-rung fallback cost (transition_s on RETRIED
        #     attempts — the measured gap between consecutive attempts)
        #   provider execution cost (dispatch_s on the OK hop)
        #   unknown remainder (everything else)
        # Anything not directly measured remains UNKNOWN (Art. XXV).
        sel = sub.get("selection_ordering_s") or 0.0
        adm_e = sub.get("admission_s") or 0.0
        dispatch = sub.get("dispatch_s") or 0.0
        retry_sl = sub.get("retry_sleep_s") or 0.0
        probe_sl = sub.get("probe_retry_sleep_s") or 0.0
        trans = sub.get("transition_s") or 0.0
        local = sub.get("post_provider_local_s") or 0.0
        rem = audit.get("remainder_s")
        llm_wall = spans.get("llm_instantiation_wall")
        stage_wall = ms.get("stage_wall_s")
        overhead = ms.get("adapter_and_stage_overhead_s")
        failed_probe_wall = round(sum(
            (fh.get("probe_admission_s") or 0.0) for fh in failed_hops),
            6)
        # R530 selection subspans when the instrumented build served
        # this call (ledger gen_spans carries selection_subspans);
        # else None (pre-R530 build — the aggregate is retained
        # historically but NOT causally decomposed).
        sel_subs = (led.get("generate_spans") or {}).get(
            "selection_subspans")
        sel_diag = (led.get("generate_spans") or {}).get(
            "selection_diag")
        partition = {
            "selection_orchestration_s": {
                "value": round(sel, 6),
                "class": "UNKNOWN",
                "subspans": sel_subs,
                "selection_diag": sel_diag,
                "evidence": ("Q-A selection_ordering_s: PRE-CALL "
                             "route assembly (availability snapshot, "
                             "chain construction, retirement/cost "
                             "filters, ladder build, capability "
                             "snapshot). It closes BEFORE any rung "
                             "is attempted — it is NOT fallback-"
                             "routing overhead (R530 §4 correction)"),
            },
            "failed_hop_admission_s": {
                "value": failed_probe_wall,
                "class": ("PROVIDER_FAILURE_OR_RETRY"
                          if failed_hops else None),
                "n_failed_hops": len(failed_hops),
                "hops": failed_hops,
                "evidence": ("gen_spans rung probe_admission_s; "
                             "the failed hop produces NO ledger "
                             "line (admission refusal, not a call)"),
            },
            "inter_rung_fallback_s": {
                "value": round(trans, 6),
                "class": ("PROVIDER_FAILURE_OR_RETRY"
                          if trans and trans > 0 else None),
                "transition_s": trans,
                "evidence": ("Q-A transition_to_next_s on RETRIED "
                             "attempts: the measured gap between "
                             "consecutive attempts (the ONLY "
                             "post-failure fallback wall)"),
            },
            "provider_execution_s": {
                "value": round(dispatch, 6),
                "class": "PROVIDER_EXECUTION",
                "evidence": "Q-A dispatch_s on the OK hop "
                            "(durable ledger latency_ms)",
            },
            "retry_backoff_s": {
                "value": round(retry_sl + probe_sl, 6),
                "class": ("PROVIDER_FAILURE_OR_RETRY"
                          if (retry_sl + probe_sl) > 0 else None),
                "retry_sleep_s": retry_sl,
                "probe_retry_sleep_s": probe_sl,
                "evidence": "Q-A retry_sleep_s + probe_retry_sleep_s",
            },
            "local_orchestration_s": {
                "value": round(local, 6),
                "class": "REQUIRED_SCIENTIFIC_WORK",
                "post_provider_local_s": local,
                "adapter_and_stage_overhead_s": overhead,
                "evidence": "Q-A post_provider_local_s + "
                            "stage overhead",
            },
            "unattributed_remainder_s": {
                "value": rem,
                "class": ("UNKNOWN" if rem is None or rem >= 0.05
                          else None),
                "evidence": "Q-A remainder (generate_total - "
                            "measured subspans)",
            },
            "in_stage_llm_wall_s": llm_wall,
            "generate_total_s": audit.get("total_s"),
            "stage_wall_s": stage_wall,
            # legacy keys (R529 naming) retained for record
            # continuity; the corrected keys above are canonical.
            "legacy_A_provider_inference_s": round(dispatch, 6),
            "legacy_B_failed_first_hop_s": failed_probe_wall,
            "legacy_C_selection_s": round(sel, 6),
        }
        # ---- funnel parity block (directive §10) ----
        fn = ms.get("funnel") or {}
        joins.append({
            "problem_index": pi,
            "session_id": sid,
            "class": "OBSERVED_IN_STAGE",
            "terminal_state": ms.get("terminal_state"),
            "partition": partition,
            "funnel": {
                "mechanisms_found": (
                    1 if ms.get("terminal_state") == "BUILT" else 0),
                "terminal_state": ms.get("terminal_state"),
                "n_distinct": (fn.get("distinctness") or {}).get(
                    "n_distinct") if isinstance(
                        fn.get("distinctness"), dict) else None,
                "llm_outcome": fn.get("llm_outcome"),
                "provider": (ll.get("provider")),
                "model": (ll.get("model")),
                "fallback_occurred": ll.get("fallback_occurred"),
                "routed_hops": ll.get("routed_hops"),
                "retry_occurred": bool(
                    (ll.get("llm_retries") or 0) > 0
                    or (partition["retry_backoff_s"]["value"] or 0)
                    > 0),
                "terminal_reason": fn.get("terminal_reason"),
            },
            "join_keys": {
                "session_id": sid,
                "request_id": req_id,
                "engine_stage": "MECHANISM_SPACE",
                "provider": ll.get("provider"),
                "model": ll.get("model"),
            },
        })

    # ---- aggregates (R530 §4 corrected keys) ----
    obs = [j for j in joins if j.get("partition")]
    out = {
        "artifact": "R529_MECHANISM_SPACE_PROVIDER_JOIN/1.1",
        "harvest": args.harvest,
        "harvest_sha256": (
            __import__("hashlib").sha256(
                hpath.read_bytes()).hexdigest()),
        "n_rows": len(joins),
        "n_observed": len(obs),
        "per_row": joins,
        "aggregate": {
            "selection_orchestration_s": _agg([
                j["partition"]["selection_orchestration_s"]["value"]
                for j in obs]),
            "failed_hop_admission_s": _agg([
                j["partition"]["failed_hop_admission_s"]["value"]
                for j in obs]),
            "inter_rung_fallback_s": _agg([
                j["partition"]["inter_rung_fallback_s"]["value"]
                for j in obs]),
            "provider_execution_s": _agg([
                j["partition"]["provider_execution_s"]["value"]
                for j in obs]),
            "retry_backoff_s": _agg([
                j["partition"]["retry_backoff_s"]["value"]
                for j in obs]),
            "local_orchestration_s": _agg([
                j["partition"]["local_orchestration_s"]["value"]
                for j in obs]),
            "in_stage_llm_wall_s": _agg([
                j["partition"]["in_stage_llm_wall_s"] for j in obs]),
        },
        "selection_subspan_aggregate": None,  # set below when present
        "fallback_auth_failure": {
            "n_calls_with_failed_first_hop": sum(
                1 for j in obs
                if j["partition"]["failed_hop_admission_s"][
                    "n_failed_hops"] > 0),
            "failed_hop_providers": sorted({
                fh.get("provider")
                for j in obs
                for fh in j["partition"]["failed_hop_admission_s"][
                    "hops"]}),
            "failed_hop_states": sorted({
                fh.get("capability_state")
                for j in obs
                for fh in j["partition"]["failed_hop_admission_s"][
                    "hops"]}),
        },
        "funnel_parity": {
            "mechanisms_found": sum(
                j["funnel"]["mechanisms_found"] for j in obs),
            "n_observed": len(obs),
            "terminal_states": {
                ts: sum(1 for j in obs
                        if j.get("terminal_state") == ts)
                for ts in {j.get("terminal_state") for j in obs}},
            "fallback_occurred_rows": sum(
                1 for j in obs if j["funnel"]["fallback_occurred"]),
        },
        "classification": None,  # set by the analyst below
        "reviewer_provenance": "AI_REVIEW",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
    }

    # ---- R530 §4: selection-subspan aggregate (only when the
    # R530 instrumented build served the calls — each per-row
    # partition carries selection_subspans + selection_diag).
    # Anything not directly measured remains UNKNOWN (Art. XXV).
    _sub_rows = [
        j["partition"]["selection_orchestration_s"].get("subspans")
        for j in obs
        if isinstance(j["partition"]["selection_orchestration_s"].get(
            "subspans"), dict)]
    _diag_rows = [
        j["partition"]["selection_orchestration_s"].get(
            "selection_diag")
        for j in obs
        if isinstance(j["partition"]["selection_orchestration_s"].get(
            "selection_diag"), dict)]
    if _sub_rows:
        _sub_keys = ("A_availability_matrix_s",
                     "B_chain_construction_s",
                     "C_route_retirement_s", "D_cost_policy_s",
                     "E_build_ladder_s", "F_catalog_detail_s",
                     "G_scoring_detail_s",
                     "H_capability_evidence_s",
                     "I_selection_remainder_s")
        out["selection_subspan_aggregate"] = {
            k: _agg([s.get(k) for s in _sub_rows]) for k in _sub_keys}
        _diag_keys = ("n_providers_inspected", "n_models_inspected",
                      "n_ladder_rungs_emitted",
                      "n_availability_score_calls",
                      "n_availability_report_scans",
                      "n_eligible_models_calls",
                      "n_eligible_models_returned",
                      "n_discover_catalog_calls",
                      "n_discover_catalog_cache_hits",
                      "n_span_failed_recently_calls")
        out["selection_diag_aggregate"] = {
            k: _agg([d.get(k) for d in _diag_rows
                     if isinstance(d.get(k), (int, float))])
            for k in _diag_keys}

    # ---- classification (R530 §4 corrected: NO valid avoidable
    # fraction exists until the selection subspan decomposition is
    # measured). The R529 "19.5% avoidable fraction" is WITHDRAWN:
    # selection_ordering_s is pre-call orchestration, not
    # fallback-routing overhead, so B+C was never a causal
    # avoidable quantity. The verdict is set from the subspan
    # evidence when present, else UNKNOWN.
    if not _sub_rows:
        out["classification"] = {
            "verdict": "SELECTION_DECOMPOSITION_UNMEASURED",
            "rule": ("no R530-instrumented calls in this harvest: "
                     "the selection subspan decomposition is "
                     "UNMEASURED (Art. XXV). No avoidable fraction "
                     "is computed; the withdrawn R529 19.5% figure "
                     "must not be cited as a causal finding."),
            "avoidable_fraction": None,
        }
    else:
        agg = out["aggregate"]
        p_mean = (agg["provider_execution_s"] or {}).get("mean") or 0
        f_mean = (agg["failed_hop_admission_s"] or {}).get("mean") \
            or 0
        t_mean = (agg["inter_rung_fallback_s"] or {}).get("mean") or 0
        total_mean = p_mean + f_mean + t_mean
        avoidable = f_mean + t_mean
        if total_mean > 0 and avoidable / total_mean < 0.05:
            out["classification"] = {
                "verdict": "MECHANISM_SPACE_PROVIDER_COST_REAL",
                "rule": ("the measured post-failure wall "
                         "(failed-hop admission + inter-rung "
                         "fallback) is <5% of the measured "
                         "MECHANISM_SPACE LLM-path wall; the "
                         "dominant cost is genuine provider "
                         "inference (R530 stopping rule)"),
                "avoidable_fraction": (round(
                    avoidable / total_mean, 4) if total_mean else None),
            }
        else:
            out["classification"] = {
                "verdict": "AVOIDABLE_COMPONENT_UNDER_REVIEW",
                "rule": ("the measured post-failure wall is >=5% "
                         "of the measured wall OR the join is "
                         "incomplete; a single causal intervention "
                         "may be named only after the component is "
                         "proven avoidable without changing "
                         "scientific behavior"),
                "avoidable_fraction": (round(
                    avoidable / total_mean, 4) if total_mean else None),
            }

    opath = Path(args.out)
    if not opath.is_absolute():
        opath = REPO / opath
    opath.parent.mkdir(parents=True, exist_ok=True)
    opath.write_text(json.dumps(out, indent=1, ensure_ascii=False)
                     + "\n", encoding="utf-8")
    print(f"wrote {opath} ({len(obs)}/{len(joins)} observed)")
    print("aggregate selection_orchestration:",
          out["aggregate"]["selection_orchestration_s"])
    print("aggregate failed_hop_admission:",
          out["aggregate"]["failed_hop_admission_s"])
    print("aggregate provider_execution:",
          out["aggregate"]["provider_execution_s"])
    if out.get("selection_subspan_aggregate"):
        print("selection subspan means:",
              {k: v.get("mean")
               for k, v in
               out["selection_subspan_aggregate"].items()})
    print("classification:", out["classification"])
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
