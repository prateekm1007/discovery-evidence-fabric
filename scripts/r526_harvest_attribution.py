#!/usr/bin/env python3
"""
R526 CURRENT-PRODUCTION RUNTIME ATTRIBUTION HARVEST — per-arm measurement + paired
current/after comparison from durable bytes.

R526 instrument, mechanically derived from scripts/r522_harvest_attribution.py
(R521 frozen history — never modified, never imported: the R521 file exits
at import without R521_ARM, so this copy carries its own arm gate; Art. LXIV
supersession noted here). R522-specific additions to the R521 stage
attribution:

Reads (never writes) origin/runtime-state-hf:
  1. fetch the branch;
  2. map arm session ids -> run slugs via run_manifest/final_state;
  3. per run:
     - FULL stage table from run_manifest.stage_order + work-envelope
       stage_log (server monotonic walls): stage entry/exit timestamps,
       wall, status, skip_reason, capability, module, function. Every
       stage_order entry appears exactly once: EXECUTED with a wall, or
       SKIPPED_* with the engine's reason, or NOT_IN_LOG (typed, never
       zero for an unexecuted stage).
     - ledger per role for EVERY engine_stage value present in the
       model-routing ledger for this session (attempts, retries,
       fallbacks, failure classes, provider/model chains, call walls);
       roles with no lines are listed absent (typed, never zero).
     - RETRIEVE two-level: V2 fanout jobs (logical job level, fully
       observed incl. attempt/retry/fallback/outcome/error) +
       enrichment_s + evidence-fabric channel states (EVIDENCE_FABRIC
       report when persisted, else UNKNOWN) + the connector-visibility
       verdict: retry waste may be claimed ONLY when both the logical
       job level AND the connector/HTTP attempt level are visible.
     - COLLISION block: status/wall/envelope/per-source timing when
       admitted; typed skip otherwise.
     - quality: SYNTHESIZE span validity (mirrored derivation, provenance
       cited), mechanism count, funnel row via the frozen r515
       instrument, terminal state.
  4. --compare joins before/after harvests into paired per-problem
     deltas + arm aggregates (mean/median/min/max/n per stage +
     provider/retry/fallback contributions; measurement only —
     classification lives in the round record).

Vocabulary: every number carries OBSERVED_IN_STAGE / LIVE_API /
OFFLINE_DERIVED / UNKNOWN. Every scored submission harvested, zeros
included. No tuning, no rewording, no selection.

Env:
  R526_SESSIONS     arm session file, REQUIRED (LOCAL-only file)
  R526_MANIFEST     default R526/BATTERY_PROBLEMS.json
  R526_ARM          current | after, REQUIRED (explicit arm, never a default)
  R526_OUT_HARVEST  default R526/ATTR_<ARM>_HARVEST.json
  R526_YIELD_ROW_PREFIX default ATTR_<ARM>_ROW_
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
sys.path.insert(0, str(REPO))

ARM = os.environ.get("R526_ARM", "").strip().lower()
_NEEDS_ARM = ("--live" in sys.argv) or ("--compare" not in sys.argv)
if _NEEDS_ARM and ARM not in ("current", "after"):
    print("FATAL: R526_ARM must be 'current' or 'after' "
          "(explicit arm, never a default)")
    sys.exit(2)
SESSIONS = REPO / os.environ.get(
    "R526_SESSIONS", f"R526/BATTERY_SESSIONS_{ARM.upper()}.json")
MANIFEST = REPO / os.environ.get("R526_MANIFEST",
                                 "R526/BATTERY_PROBLEMS.json")
OUT_HARVEST = REPO / os.environ.get(
    "R526_OUT_HARVEST", f"R526/ATTR_{ARM.upper()}_HARVEST.json")
YIELD_ROW_PREFIX = os.environ.get("R526_YIELD_ROW_PREFIX",
                                  f"ATTR_{ARM.upper()}_ROW_")

import r516_harvest_attribution as hv  # noqa: E402  (frozen MS module)
from discovery_fabric.engine.provider_health import (  # noqa: E402
    independence_degree)

INSTRUMENT_ID = "r506_discovery_yield"
INSTRUMENT_VERSION = "1.1.0"


def _git(*args, **kwargs):
    return subprocess.run(["git", *args], capture_output=True,
                          timeout=kwargs.get("timeout", 120),
                          cwd=str(REPO))


def _show(ref_path):
    r = _git("show", ref_path, timeout=120)
    return r.stdout if r.returncode == 0 else None


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _iso_seconds(a, b):
    try:
        from datetime import datetime

        def p(s):
            s = (s or "").replace("Z", "+00:00")
            if s.endswith("+00:00+00:00"):
                s = s[:-6]
            return datetime.fromisoformat(s)
        return (p(b) - p(a)).total_seconds()
    except Exception:
        return None


# ---------------------------------------------------------------- stage table
def _stage_table(manifest, envs):
    """One entry per stage in run_manifest.stage_order.

    EXECUTED entries carry the server monotonic wall + timestamps +
    skip_reason=None. SKIPPED_* entries carry the engine's skip_reason
    and wall=None (never zero). Stages absent from the log are
    NOT_IN_LOG (typed, never zero).
    """
    order = (manifest or {}).get("stage_order") or []
    work = hv._work_envelope(envs)
    by_stage = {}
    for e in (work or {}).get("stage_log") or []:
        st = e.get("stage")
        if st and st not in by_stage:
            by_stage[st] = e
    table = []
    for st in order:
        e = by_stage.get(st)
        if e is None:
            table.append({"stage": st, "entry_class": "NOT_IN_LOG",
                          "class": "UNKNOWN",
                          "note": "stage_order entry with no stage_log "
                                  "record — unmeasured (Art. XXV)",
                          "wall_s": None, "status": None})
            continue
        status = e.get("status")
        executed = status not in ("SKIPPED_ADMISSION",
                                  "SKIPPED_UPSTREAM_FAILURE",
                                  "NOT_IN_STAGE_LOG", None) or \
            e.get("duration_monotonic_s") is not None
        if status in ("SKIPPED_ADMISSION", "SKIPPED_UPSTREAM_FAILURE"):
            table.append({
                "stage": st, "entry_class": status, "class": "OBSERVED_IN_STAGE",
                "status": status,
                "skip_reason": e.get("skip_reason"),
                "entry": e.get("entry"),
                "wall_s": None,
                "started_at": e.get("started_at"),
                "finished_at": e.get("finished_at"),
                "capability_id": e.get("capability_id"),
                "note": "unexecuted stage is None, never zero",
            })
        else:
            table.append({
                "stage": st, "entry_class": "EXECUTED",
                "class": "OBSERVED_IN_STAGE",
                "status": status,
                "wall_s": _num(e.get("duration_monotonic_s")),
                "started_at": e.get("started_at"),
                "finished_at": e.get("finished_at"),
                "capability_id": e.get("capability_id"),
                "module_path": e.get("module_path"),
                "function": e.get("function"),
                "result_meta": e.get("result_meta"),
                "executed_flag": executed,
            })
    return table


# ---------------------------------------------------------------- ledger
def _phase_spans_block(lines):
    """R526 Q-B: pair phase enter/exit lines by (phase, scope,
    candidate_key, candidate_id), in epoch order.

    Scope discriminator (B1/B2): "top" lines are top-level phase walls
    (whole GAUNTLET / KILL_IMPROVE / IMPROVEMENT_PASS /
    TECHNICAL_IMPROVEMENT_PASS) — the ONLY walls that may enter the
    run-wall reconciliation; "child" lines are per-candidate /
    per-target spans nested inside a top-level phase (attribution
    detail, never added on top of the parent wall). B3: the durable
    join key is (phase, scope, candidate_key, candidate_id) — the
    smallest explicit identity already on the line. A child span's
    `phase` is the enclosing top-scope phase name (documented
    invariant enforced by the caller), so (phase, scope,
    candidate_key, candidate_id) uniquely identifies each span and
    deterministically joins children to their parent WITHOUT
    time-window matching and WITHOUT a separate parent_phase field
    (PART 3: parent_phase is not on the durable schema). Lines
    without a scope field (older instrumented data) fall back to
    event-name derivation: candidate_*/target_* => "child",
    everything else => "top" (documented fallback, never inferred
    from timestamps). Unmatched events are listed explicitly (never
    force-paired, never zero-filled)."""
    by_key = {}
    for ln in sorted(lines,
                     key=lambda l: (l.get("recorded_at_epoch") or 0)):
        _evt = str(ln.get("event") or "")
        _scope = ln.get("scope")
        if _scope not in ("top", "child"):
            _scope = ("child"
                      if (_evt.startswith("candidate_")
                          or _evt.startswith("target_"))
                      else "top")
        key = (ln.get("phase"), _scope, ln.get("candidate_key"),
               ln.get("candidate_id"))
        by_key.setdefault(key, []).append(ln)
    phases = {}
    unmatched = []
    for (phase, scope, ckey, cid), evs in sorted(
            by_key.items(), key=lambda kv: str(kv[0])):
        if phase is None:
            unmatched.append({"reason": "phase-name-absent",
                              "scope": scope,
                              "n_lines": len(evs)})
            continue
        enters = [e for e in evs
                  if str(e.get("event") or "") == "enter"
                  or str(e.get("event") or "").endswith("_enter")]
        exits = [e for e in evs
                 if str(e.get("event") or "") == "exit"
                 or str(e.get("event") or "").endswith("_exit")]
        rec = phases.setdefault(
            phase, {"walls_s": [], "top_wall_sum_s": 0.0,
                    "children": {}, "n_unmatched": 0})
        ident = ckey or cid
        for i, ex in enumerate(exits):
            if i < len(enters):
                en = enters[i]
                w = ex.get("wall_s")
                if w is None:
                    te = en.get("recorded_at_epoch")
                    tx = ex.get("recorded_at_epoch")
                    w = (round(tx - te, 3)
                         if te and tx else None)
                if w is not None:
                    rec["walls_s"].append(w)
                if scope == "top":
                    rec["top_wall_sum_s"] = round(
                        rec["top_wall_sum_s"] + (w or 0.0), 3)
                if scope == "child" and ident is not None:
                    cr = rec["children"].setdefault(
                        str(ident), {"scope": scope,
                                     "walls_s": [],
                                     "outcomes": []})
                    if w is not None:
                        cr["walls_s"].append(w)
                    det = ex.get("detail") or {}
                    if det.get("outcome"):
                        cr["outcomes"].append(det["outcome"])
            else:
                rec["n_unmatched"] += 1
                unmatched.append({"phase": phase, "scope": scope,
                                  "candidate": ident,
                                  "reason": "exit-without-enter"})
        for _en in enters[len(exits):]:
            rec["n_unmatched"] += 1
            unmatched.append({"phase": phase, "scope": scope,
                              "candidate": ident,
                              "reason": "enter-without-exit"})
    for rec in phases.values():
        rec["wall_sum_s"] = round(sum(rec["walls_s"]), 3)
        for cr in rec["children"].values():
            cr["wall_sum_s"] = round(sum(cr["walls_s"]), 3)
    return {"class": ("OBSERVED_IN_STAGE" if phases else "UNKNOWN"),
            "n_phase_lines": len(lines),
            "phases": phases,
            "unmatched": unmatched,
            "reconciliation_rule": ("run_wall = "
                                    "executed_linear_stage_wall + "
                                    "top_level_post_rank_phase_wall "
                                    "(top_wall_sum_s, scope=top ONLY) + "
                                    "explicit_external_or_orchestration_"
                                    "wall + UNKNOWN_remainder; child "
                                    "spans (scope=child) are attribution "
                                    "detail, never added on top of the "
                                    "parent phase wall; B3: child "
                                    "spans join to their parent by "
                                    "explicit (phase, scope, "
                                    "candidate_key, candidate_id) "
                                    "identity (the smallest durable "
                                    "identity; no separate parent_"
                                    "phase field), never time-window "
                                    "matching; unmatched events are "
                                    "reported explicitly, never "
                                    "force-paired or zero-filled"),
            }


def _generate_calls_block(lines):
    """R526 Q-A: group attempt lines by per-call request_id and audit
    generate_total_s = measured_subspans + unattributed_remainder per
    call. Lines without spans (uninstrumented builds) audit UNKNOWN."""
    by_call = {}
    for ln in lines:
        by_call.setdefault(ln.get("request_id"), []).append(ln)
    calls = []
    for cid, ls in sorted(by_call.items(), key=lambda kv: str(kv[0])):
        full = max(ls, key=lambda l: (l.get("recorded_at_epoch") or 0))
        sp = full.get("generate_spans")
        if not isinstance(sp, dict) or sp.get("instrument") != \
                "gen_spans/1.0":
            calls.append({"request_id": cid,
                          "spans_present": False,
                          "n_ledger_lines": len(ls),
                          "audit": {"class": "UNKNOWN",
                                    "note": "uninstrumented build"}})
            continue
        # R526 Q-A (S4): per-call subphase sums from the COMPLETE
        # spans block (last line by epoch carries the full rung
        # history). These feed the directive §11 generate-subphase
        # ranking.
        # PART 5 (accumulate all probe segments): probe_admission_s
        # already accumulates every probe-attempt wall + the final
        # admission check (the instrument now accumulates, not
        # overwrites); probe_retry_sleep_s accumulates every probe-
        # retry sleep. admission_exclusive = probe_admission -
        # probe_retry_sleep is therefore the exclusive non-sleep
        # admission work. The two are mutually exclusive and NO
        # component is counted twice.
        # PART 6 (per-component non-negativity): every component is
        # clamped to >= 0 at the source (the instrument measures
        # perf_counter deltas, never negative); any negative value
        # in the ledger is an instrumentation violation and is
        # flagged per-component in the audit (never silently
        # clamped in the harvester, never concealed by a positive
        # remainder).
        sub = {"selection_ordering_s": (sp.get("selection_ordering_s")
                                        or 0.0),
               "admission_s": 0.0, "probe_retry_sleep_s": 0.0,
               "dispatch_s": 0.0, "retry_sleep_s": 0.0,
               "transition_s": 0.0, "post_provider_local_s": 0.0}
        _neg_components = []
        for rung in sp.get("rungs") or []:
            adm = rung.get("admission") or {}
            _probe_wall = adm.get("probe_admission_s") or 0.0
            _probe_sleep = adm.get("probe_retry_sleep_s") or 0.0
            _exclusive = _probe_wall - _probe_sleep
            if _exclusive < 0:
                _neg_components.append(
                    f"admission_exclusive({rung.get('provider')}):"
                    f"{_exclusive}")
            sub["admission_s"] += max(_exclusive, 0.0)
            sub["probe_retry_sleep_s"] += max(_probe_sleep, 0.0)
            for a in rung.get("attempts") or []:
                _disp = a.get("dispatch_s")
                if _disp is not None and _disp < 0:
                    _neg_components.append(
                        f"dispatch({rung.get('provider')},"
                        f"att{a.get('attempt_index')}):{_disp}")
                sub["dispatch_s"] += (
                    max(_disp, 0.0) if _disp is not None else 0.0)
                _rs = a.get("retry_sleep_s") or 0.0
                if _rs < 0:
                    _neg_components.append(
                        f"retry_sleep({rung.get('provider')},"
                        f"att{a.get('attempt_index')}):{_rs}")
                sub["retry_sleep_s"] += max(_rs, 0.0)
                _tr = a.get("transition_to_next_s")
                if _tr is not None and _tr < 0:
                    _neg_components.append(
                        f"transition({rung.get('provider')},"
                        f"att{a.get('attempt_index')}):{_tr}")
                sub["transition_s"] += (
                    max(_tr, 0.0) if _tr is not None else 0.0)
            _pl = rung.get("post_provider_local_s")
            if _pl is not None and _pl < 0:
                _neg_components.append(
                    f"post_provider_local({rung.get('provider')}):{_pl}")
            sub["post_provider_local_s"] += (
                max(_pl, 0.0) if _pl is not None else 0.0)
        _sel = sp.get("selection_ordering_s") or 0.0
        if _sel < 0:
            _neg_components.append(f"selection_ordering:{_sel}")
        sub["selection_ordering_s"] = max(_sel, 0.0)
        sub = {k: round(v, 3) for k, v in sub.items()}
        sub["admission_s_inclusive_note"] = (
            "admission_exclusive = probe_admission_accumulated - "
            "probe_retry_sleep; the instrument accumulates every "
            "probe-attempt wall + the final admission check (PART 5); "
            "the raw inclusive probe wall is not reported separately "
            "(exclusive form is the canonical one)")
        measured = round(
            sub["selection_ordering_s"] + sub["admission_s"]
            + sub["probe_retry_sleep_s"] + sub["dispatch_s"]
            + sub["retry_sleep_s"] + sub["transition_s"]
            + sub["post_provider_local_s"], 3)
        # A2: the canonical Q-A total is the instrument's terminal
        # generate_total_s (final=True snapshot on the last durable
        # line of the call). Ledger-timestamp reconstruction is kept
        # only as audit provenance (ordering check), never silently
        # substituted for the measured total (PART 7: the terminal
        # instrument total remains canonical).
        terms = [((l.get("generate_spans") or {}).get(
            "generate_total_s")) for l in ls
            if isinstance(l.get("generate_spans"), dict)]
        terms = [t for t in terms if t is not None]
        total = terms[-1] if terms else None
        epochs = [l.get("recorded_at_epoch") for l in ls
                  if l.get("recorded_at_epoch")]
        start = sp.get("generate_start_epoch")
        total_ledger_provenance = (round(max(epochs) - start, 3)
                                   if epochs and start else None)
        calls.append({
            "request_id": cid,
            "spans_present": True,
            "purpose": sp.get("purpose"),
            "providers": sorted(
                {r.get("provider") for r in sp.get("rungs") or []
                 if r.get("provider")}),
            "n_ledger_lines": len(ls),
            "ledger_provider_wall_s": round(sum(
                float(l.get("latency_ms") or 0) for l in ls) / 1000.0,
                3),
            "subphases": sub,
            "audit": {
                "class": ("AUDITED" if total is not None else
                          "UNKNOWN"),
                "total_s": total,
                "measured_s": measured,
                "remainder_s": (round(total - measured, 3)
                                if total is not None else None),
                "generate_total_s_terminal": total,
                "total_ledger_provenance_s": total_ledger_provenance,
                # PART 6: per-component non-negativity is mechanically
                # proven; any negative component is flagged explicitly
                # (never concealed by the remainder).
                "negative_components": _neg_components,
                "all_components_non_negative": (
                    len(_neg_components) == 0),
                "remainder_rule": ("generate_total_s (instrument "
                                   "terminal) = measured_subspans + "
                                   "unattributed_remainder_s; the "
                                   "remainder is UNATTRIBUTED_REMAINDER "
                                   "until a fresh measurement proves its "
                                   "contents — it is NOT assumed to be "
                                   "loop overhead, dict building, ledger "
                                   "I/O, or result construction "
                                   "(S5 PART 5: unknown remains "
                                   "unknown, never estimated or "
                                   "distributed); a small negative "
                                   "value beyond clock tolerance -0.05 s "
                                   "is an instrumentation violation, "
                                   "flagged never hidden; the remainder "
                                   "must NOT be used to conceal "
                                   "negative components (PART 6)"),
                "note": ("total from the instrument's terminal "
                         "generate_total_s; the ledger-epoch "
                         "reconstruction is provenance only and is "
                         "never silently substituted (PART 7)"),
            },
        })
    return {"class": ("OBSERVED_IN_STAGE" if calls else "UNKNOWN"),
            "n_calls": len(calls),
            "n_spans_present": sum(1 for c in calls
                                   if c.get("spans_present")),
            "calls": calls}


def _ledger_block(lines):
    if not lines:
        return {"class": "UNKNOWN",
                "note": "no ledger lines — unmeasured stays "
                        "unmeasured (Art. XXV)"}
    prov_chain, models = [], []
    for ln in lines:
        if ln.get("provider") not in prov_chain:
            prov_chain.append(ln.get("provider"))
        if ln.get("model") not in models:
            models.append(ln.get("model"))
    attempts = sorted({ln.get("attempt") for ln in lines
                       if ln.get("attempt") is not None})
    fbs = [{"from": ln.get("fallback_from"), "to": ln.get("fallback_to"),
            "reason": ln.get("fallback_reason")}
           for ln in lines if ln.get("fallback_from")]
    lat = sum(float(ln.get("latency_ms") or 0) for ln in lines) / 1000.0
    ok_lat = sum(float(ln.get("latency_ms") or 0) for ln in lines
                 if ln.get("ok")) / 1000.0
    return {
        "class": "OFFLINE_DERIVED",
        "n_calls": len(lines),
        "n_ok": sum(1 for ln in lines if ln.get("ok")),
        "attempts_seen": attempts,
        "retries_observed": (max(attempts) - 1) if attempts and all(
            isinstance(a, int) for a in attempts) else None,
        "retries_note": ("max(attempt)-1 per ledger; None when attempt "
                         "numbers absent (Art. XXV)"),
        "provider_chain": prov_chain,
        "models": models,
        "provider_call_wall_s": round(lat, 3),
        "ok_call_wall_s": round(ok_lat, 3),
        "fallback_hops": fbs,
        "n_fallback_hops": len(fbs),
        "failures": sorted({str(ln.get("failure_class"))
                            for ln in lines if not ln.get("ok")}),
        "first_ok_provider": next(
            (ln.get("provider") for ln in lines if ln.get("ok")), None),
    }


# ---------------------------------------------------------------- RETRIEVE two-level
def _retrieve_two_level(ret_env, run_dir_files):
    """Logical-job level (observed) vs connector/HTTP-attempt level.

    The R521 RETRIEVE rule: retry waste may be claimed ONLY when both
    levels are visible. Connector internals that retry opaquely (bounded
    retries inside adapters with no per-attempt record) force the
    connector level to UNKNOWN with a named reason.
    """
    fab = ((ret_env or {}).get("provenance") or {}).get(
        "retrieval_fabric") or {}
    att = fab.get("retrieval_attribution") or {}
    jobs = []
    for j in att.get("jobs") or []:
        vds = j.get("variant_details") or []
        conn_attempts_visible = all(
            isinstance(v, dict) and v.get("attempt_index") is not None
            for v in vds) if vds else False
        jobs.append({
            "index": j.get("index"), "lane": j.get("lane"),
            "source_id": j.get("source_id"),
            "n_variants": j.get("n_variants"),
            "search_call_ms": j.get("search_call_ms"),
            "job_wall_s": _num(j.get("job_wall_s")),
            "attempt_index": j.get("attempt_index"),
            "retry_backoff_s": j.get("retry_backoff_s"),
            "fallback": j.get("fallback"),
            "outcome": j.get("outcome"),
            "variant_statuses": j.get("variant_statuses"),
            "records_returned": j.get("records_returned"),
            "error": (str(j.get("error"))[:200]
                      if j.get("error") else None),
            "connector_attempts_visible": conn_attempts_visible,
        })
    fanout = {k: att.get(k) for k in (
        "schema", "mode", "max_workers_configured",
        "max_workers_effective", "peak_concurrency_observed", "n_jobs",
        "fanout_wall_s", "total_search_call_s", "max_job_wall_s",
        "assemble_s", "worker_queue_wait_s")}
    ef = fab.get("evidence_fabric") or {}
    # envelope-state discriminator: ABSENT (channel disabled — no key
    # or null) vs CHANNEL_ERROR (crashed) vs SUMMARY (ran). This is
    # the before/after proof for an env-knob intervention.
    if "evidence_fabric" not in fab or fab.get("evidence_fabric") is None:
        ef_envelope_state = "ABSENT"
    elif isinstance(fab.get("evidence_fabric"), dict) and \
            fab["evidence_fabric"].get("state"):
        ef_envelope_state = fab["evidence_fabric"]["state"]
    elif isinstance(fab.get("evidence_fabric"), dict) and \
            "version" in fab["evidence_fabric"]:
        ef_envelope_state = "SUMMARY_RAN"
    else:
        ef_envelope_state = "UNKNOWN_SHAPE"
    ef_report = None
    for f in run_dir_files:
        if f.endswith("EVIDENCE_FABRIC_REPORT.json"):
            ef_report = f
            break
    # R521 phase accounting (present on instrumented builds; absent on
    # pre-instrumentation runs — UNKNOWN then, never zero).
    phases = att.get("phase_s") or {}
    phase_table = {k: v for k, v in phases.items()
                   if k != "phase_accounting_note"}
    # evidence-fabric compact per-channel timing (rides the envelope
    # since R521 instrumentation; absent before).
    ef_channels = ef.get("channel_latencies") or []
    ef_timed = [c for c in ef_channels
                if isinstance(c.get("latency_s"), (int, float))]
    out = {
        "class": "OBSERVED_IN_STAGE",
        "fanout": fanout,
        "jobs": jobs,
        "n_jobs": len(jobs),
        "jobs_with_retry_backoff": sum(
            1 for j in jobs if (j.get("retry_backoff_s") or 0) > 0),
        "jobs_with_fallback": sum(1 for j in jobs if j.get("fallback")),
        "jobs_with_attempt_gt1": sum(
            1 for j in jobs if (j.get("attempt_index") or 1) > 1),
        "job_outcomes": {o: sum(1 for j in jobs if j.get("outcome") == o)
                         for o in {j.get("outcome") for j in jobs}},
        "enrichment_s": att.get("enrichment_s"),
        "canonical_merges": att.get("canonical_merges"),
        "records_admitted": att.get("records_admitted"),
        "records_returned": att.get("records_returned"),
        "sources_attempted": fab.get("sources_attempted"),
        "sources_succeeded": fab.get("sources_succeeded"),
        "sources_failed": fab.get("sources_failed"),
        "sources_rate_limited": fab.get("sources_rate_limited"),
        "evidence_fabric": {
            "envelope_state": ef_envelope_state,
            "channels": ef.get("channels"),
            "unknown_channels": ef.get("unknown_channels"),
            "pool_items": ef.get("pool_items"),
            "records_in_custody": ef.get("records_in_custody"),
            "production_sources": ef.get("production_sources"),
            "report_file": ef_report,
            "channel_latencies": ef_channels or None,
            "channel_latency_sum_s": ef.get("channel_latency_sum_s"),
            "pacing_s": ef.get("pacing_s"),
            "per_channel_timing": {
                "class": ("OBSERVED_IN_STAGE" if ef_timed
                          else "UNKNOWN"),
                "n_timed": len(ef_timed),
                "n_channels": len(ef_channels),
                "note": ("compact per-channel timing rides the "
                         "envelope (R521 instrumentation)"
                         if ef_timed else
                         "no per-channel latency in the envelope — "
                         "channel time unmeasured (Art. XXV)"),
            },
        },
        "phase_s": phase_table or None,
        "phase_accounting_note": phases.get("phase_accounting_note"),
    }
    # connector-visibility verdict (the RETRIEVE-specific rule gate)
    logical_visible = bool(jobs)
    connector_visible = all(
        j.get("connector_attempts_visible") for j in jobs) if jobs else False
    # connector-visibility verdict (the RETRIEVE-specific rule gate)
    logical_visible = bool(jobs)
    connector_visible = all(
        j.get("connector_attempts_visible") for j in jobs) if jobs else False
    out["connector_visibility_verdict"] = {
        "logical_job_level": "OBSERVED_IN_STAGE" if logical_visible
        else "UNKNOWN",
        "evidence_fabric_channel_level": (
            "OBSERVED_IN_STAGE — compact per-channel latency rides "
            "the envelope (R521 instrumentation)" if ef_timed else
            "UNKNOWN — pre-instrumentation run; channel time "
            "unmeasured (Art. XXV)"),
        "v2_connector_sub_attempt_level": (
            "OBSERVED_IN_STAGE — per-variant attempt records present "
            "on every job" if (logical_visible and connector_visible)
            else "UNKNOWN — V2 connector internals below the variant "
            "level carry no per-attempt timing (Art. XXV)"),
        "retry_waste_claim_permitted": bool(logical_visible
                                            and connector_visible
                                            and ef_timed),
        "retry_waste_claim_note": (
            "retry waste may be claimed ONLY for levels observed: "
            "fanout jobs (attempt/retry/fallback per job) + "
            "evidence-fabric channels (latency/state/attempts per "
            "channel). V2 connector sub-attempt waste stays UNKNOWN."),
    }
    return out


# ---------------------------------------------------------------- COLLISION
def _collision_block(col_env, stage_entry):
    entry = stage_entry or {}
    status = entry.get("status")
    if status != "OK":
        return {"class": "OBSERVED_IN_STAGE", "status": status,
                "skip_reason": entry.get("skip_reason"),
                "wall_s": None,
                "note": "unexecuted COLLISION is None, never zero"}
    col = (col_env or {}).get("collision_results") or {}
    return {"class": "OBSERVED_IN_STAGE", "status": status,
            "wall_s": _num(entry.get("duration_monotonic_s")),
            "started_at": entry.get("started_at"),
            "finished_at": entry.get("finished_at"),
            "envelope_present": col_env is not None,
            "novelty_risk": col.get("novelty_risk"),
            "prior_art_status": col.get("prior_art_status"),
            "per_source_timing": {
                "class": "UNKNOWN",
                "note": "collision runs sequential scientific + patent "
                        "legs with no per-leg timing in the envelope — "
                        "leg-level time unmeasured (Art. XXV)",
            }}


# ---------------------------------------------------------------- quality (mirrored derivation)
# Span-derivation logic mirrored from scripts/r520_harvest_ab.py
# (_synth_validity/_spans/_evidence_texts, OBSERVED_IN_STAGE semantics).
# Mirrored, not imported: r520_harvest_ab.py exits at import without
# R520_ARM, and R520 files are frozen history (never modified).
def _openalex_block(ret_env, two_level):
    """R522 measurements 3-8 and 12 for the openalex V2 fan-out job:
    job wall, transport state, retry/backoff, records returned, and
    unique canonical contribution where deterministically
    reconstructable — from the durable envelope bytes only.

    - Emitted-pool contribution (measure 7, pool side): openalex-
      originating items in the engine evidence list, and whether their
      canonical_ids are shared with other indexing sources. Fully
      reconstructable from the envelope: every engine item carries
      origin_source + indexing_sources in its provenance.
    - Canonical-admitted contribution (measure 7, pool formation): the
      per-source admitted count requires the Canonicalizer merge order,
      which no committed machinery attributes per job (R517 note carried
      on every job row) — UNKNOWN with the named reason, never a guess.
    - Retry/backoff (measure 5): the V2 connector records one attempt
      per variant in the fanout (no retry loop); retry waste below that
      level is the connector sub-attempt level, UNKNOWN by the frozen
      R521 two-level rule.
    """
    fab = ((ret_env or {}).get("provenance") or {}).get(
        "retrieval_fabric") or {}
    att = fab.get("retrieval_attribution") or {}
    jobs = [j for j in (att.get("jobs") or [])
            if j.get("source_id") == "openalex"]
    out = {
        "class": "OBSERVED_IN_STAGE" if jobs else "UNKNOWN",
        "n_jobs": len(jobs),
    }
    if jobs:
        j = jobs[0]
        vd = j.get("variant_details") or []
        out["job_wall_s"] = j.get("job_wall_s")
        out["search_call_ms"] = j.get("search_call_ms")
        out["transport_state"] = j.get("outcome")
        out["variant_statuses"] = j.get("variant_statuses")
        out["records_returned"] = j.get("records_returned")
        out["attempt_index"] = j.get("attempt_index")
        out["retry_backoff_s"] = j.get("retry_backoff_s")
        out["fallback"] = j.get("fallback")
        out["connector_attempts_visible"] = all(
            isinstance(v, dict) and v.get("attempt_index") is not None
            for v in vd) if vd else False
        out["error"] = (str(j.get("error"))[:200]
                        if j.get("error") else None)
    else:
        out["note"] = ("no openalex fan-out job in the attribution — "
                       "absent or excluded; see sources_excluded "
                       "(R522 lane_state EXCLUDED is NOT an outcome)")
    # emitted-pool contribution (deterministic from envelope evidence)
    items = (ret_env or {}).get("evidence") or []
    oa_items = []
    for it in items:
        prov = (it or {}).get("provenance") or {}
        if (prov.get("origin_source") or it.get("source")) == "openalex":
            oa_items.append({
                "id": it.get("id"),
                "indexing_sources": sorted(
                    prov.get("indexing_sources") or []),
            })
    shared = [i for i in oa_items
              if any(s != "openalex"
                     for s in i["indexing_sources"])]
    out["emitted_pool"] = {
        "class": "OBSERVED_IN_STAGE",
        "n_openalex_items": len(oa_items),
        "n_also_indexed_by_other_sources": len(shared),
        "openalex_unique_ids": [i["id"] for i in oa_items
                                if i not in shared],
        "evidence": "envelope_RETRIEVE.json $.evidence[].provenance "
                    "origin_source + indexing_sources",
    }
    out["canonical_admitted_contribution"] = {
        "class": "UNKNOWN",
        "note": "per-source admitted count requires join with "
                "Canonicalizer merge order (not attributed per job in "
                "current machinery — R517 contract carried on every "
                "job row); unmeasured (Art. XXV)",
    }
    # sources_excluded from the envelope stats (measure 4/12 context)
    out["sources_excluded_envelope"] = (
        fab.get("sources_excluded")
        if "sources_excluded" in fab else None)
    return out


def _source_job_walls(ret_env):
    """R526 measure 4: EVERY V2 source job wall + transport state, from
    the durable retrieval attribution (parallel mode). Sorted descending
    by wall. This is the sub-operation ranking the round requires; it
    is derived from the R517 per-operation attribution already persisted
    in the envelope — never re-timed."""
    fab = ((ret_env or {}).get("provenance") or {}).get(
        "retrieval_fabric") or {}
    att = fab.get("retrieval_attribution") or {}
    rows = []
    for j in att.get("jobs") or []:
        rows.append({
            "source_id": j.get("source_id"),
            "lane": j.get("lane"),
            "job_wall_s": _num(j.get("job_wall_s")),
            "transport_state": j.get("outcome"),
            "records_returned": j.get("records_returned"),
            "attempt_index": j.get("attempt_index"),
            "retry_backoff_s": j.get("retry_backoff_s"),
            "fallback": j.get("fallback"),
        })
    rows.sort(key=lambda r: -(r.get("job_wall_s") or 0.0))
    return {
        "class": "OBSERVED_IN_STAGE" if rows else "UNKNOWN",
        "fanout_wall_s": att.get("fanout_wall_s"),
        "n_jobs": att.get("n_jobs"),
        "max_job_wall_s": att.get("max_job_wall_s"),
        "sources_excluded": att.get("excluded_sources"),
        "jobs": rows,
        "note": "critical path = max_job_wall_s; a job whose wall ~= "
                "fanout_wall_s is the fan-out straggler",
    }


def _evidence_texts(syn_env):
    texts = []
    ev = (syn_env or {}).get("evidence") or []
    if isinstance(ev, list):
        for e in ev:
            if not isinstance(e, dict):
                continue
            for k in ("abstract", "title"):
                v = e.get(k)
                if isinstance(v, str) and v.strip():
                    texts.append(v)
    return texts


def _spans(syn_env):
    mm = (syn_env or {}).get("mechanism_map") or {}
    out = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k == "mechanism_source_span" and isinstance(v, str):
                    out.append(v)
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(mm)
    return out


def _synth_validity(syn_env):
    spans = [s for s in _spans(syn_env) if s.strip()]
    texts = _evidence_texts(syn_env)
    verbatim = [s for s in spans
                if any(s.strip() and s.strip() in t for t in texts)] \
        if texts else []
    mechs = 0
    mm = (syn_env or {}).get("mechanism_map") or {}
    raw = mm.get("raw_candidate") or mm.get("mechanisms") or []
    if isinstance(raw, list):
        mechs = len(raw)
    elif isinstance(raw, dict):
        mechs = 1
    return {
        "class": "OBSERVED_IN_STAGE" if spans or mechs else "UNKNOWN",
        "n_mechanisms_seen": mechs if mechs else None,
        "n_spans_present": len(spans),
        "n_spans_verbatim_in_own_evidence": (
            len(verbatim) if texts else None),
        "span_verbatim_rate": (round(len(verbatim) / len(spans), 3)
                               if spans and texts else None),
        "evidence_texts_available": len(texts),
        "derivation_provenance": "mirrored from "
                                 "scripts/r521_harvest_attribution.py::_synth_validity "
                                 "(frozen; Art. II byte-substring rule); R526 mirrors R522/R521, "
                                 "never imports them (round env gate)",
    }


def _synth_spans(syn_env, stage_entry, ledger_block):
    """R526 Q-A: SYNTHESIZE wall decomposition from implementation spans
    only (no invented sub-phases; anything unmeasured stays
    UNATTRIBUTED).

    Reads, all from durable bytes:
      stage wall ......... stage_log SYNTHESIZE duration_monotonic_s
      span record ........ mechanism_map.raw_candidate
                           .synthesis_span_timings (synth_spans/1.0;
                           absent on uninstrumented builds or failed
                           synthesis -> UNATTRIBUTED)
      provider-call wall . durable model_routing ledger SYNTHESIZE role
    Derives (labeled, never force-fit):
      adapter_and_stage_overhead_s = stage wall - synthesize_total_s
      routing_gap_s = llm_chat_total_s - ledger provider-call wall
        (provider selection/routing + registry retries + sleeps inside
        generate(); the per-call split is not durably recorded)
    """
    out = {"class": "UNKNOWN", "note": None}
    st_wall = None
    try:
        for e in ((syn_env or {}).get("stage_log") or []):
            if isinstance(e, dict) and e.get("stage") == "SYNTHESIZE":
                st_wall = e.get("duration_monotonic_s")
                out["stage_started_at"] = e.get("started_at")
                out["stage_finished_at"] = e.get("finished_at")
                break
    except Exception:
        st_wall = None
    if st_wall is None and isinstance(stage_entry, dict):
        st_wall = stage_entry.get("wall_s")
    out["stage_wall_s"] = st_wall
    mm = ((syn_env or {}).get("mechanism_map") or {})
    raw = mm.get("raw_candidate") or {}
    spans = (raw.get("synthesis_span_timings")
             if isinstance(raw, dict) else None)
    if not isinstance(spans, dict) or spans.get("instrument") != \
            "synth_spans/1.0":
        out["note"] = ("no synth_spans/1.0 record on the durable "
                       "candidate (uninstrumented build or failed "
                       "synthesis) - decomposition UNATTRIBUTED")
        return out
    led = ledger_block or {}
    led_wall = led.get("provider_call_wall_s") or 0.0
    total = spans.get("synthesize_total_s")
    chat = spans.get("llm_chat_total_s") or 0.0
    out.update({
        "class": "OBSERVED_IN_STAGE",
        "spans": {k: spans.get(k) for k in (
            "abstract_gate_s", "prompt_construction_total_s",
            "llm_chat_total_s", "n_llm_chat_calls",
            "rotation_backoff_sleep_s", "parse_total_s",
            "span_repair_check_s", "candidate_assembly_s",
            "post_success_sleep_s", "synthesize_total_s")},
        "ledger_provider_call_wall_s": round(led_wall, 3),
        "ledger_n_calls": led.get("n_calls"),
        "ledger_n_ok": led.get("n_ok"),
        "ledger_failures": list(led.get("failures") or []),
        "adapter_and_stage_overhead_s": (
            round(st_wall - total, 3)
            if isinstance(st_wall, (int, float))
            and isinstance(total, (int, float)) else None),
        "routing_gap_s": round(chat - led_wall, 3),
        "evidence": ("envelope_SYNTHESIZE.json $.stage_log "
                     "[SYNTHESIZE].duration_monotonic_s + "
                     "$.mechanism_map.raw_candidate."
                     "synthesis_span_timings + durable model_routing "
                     "ledger SYNTHESIZE role"),
    })
    return out


def _mechanism_space_spans(ms_env, stage_entry, ledger_block):
    """R528: MECHANISM_SPACE subphase decomposition from the existing
    mechanism_attribution/1.0.0 instrument (runtime_attribution on
    the durable MECHANISM_SPACE envelope). Behavior-neutral: the
    instrument already exists in adapters._lean_mechanism_space; this
    harvest step only EXTRACTS it into the row (no second
    attribution framework).

    Reads, all from durable bytes:
      stage wall ......... stage_log MECHANISM_SPACE duration_monotonic_s
      span record ........ envelope_MECHANISM_SPACE.json
                          $.mechanism_space.runtime_attribution
                          (mechanism_attribution/1.0.0; absent on
                          uninstrumented builds or skipped stages ->
                          UNATTRIBUTED)
      provider-call wall . durable model_routing ledger MECHANISM_SPACE
                          role
    Derives (labeled, never force-fit):
      adapter_and_stage_overhead_s = stage wall - total_s
    The 12 subphases (mechanism_attribution.SUBPHASES) are the
    decomposition; provider_call_split_offline is an explicit
    unmeasured marker (duration_s=None) — never a fabricated zero
    (Art. XXV).
    """
    out = {"class": "UNKNOWN", "note": None}
    st_wall = None
    try:
        for e in ((ms_env or {}).get("stage_log") or []):
            if isinstance(e, dict) and e.get("stage") == "MECHANISM_SPACE":
                st_wall = e.get("duration_monotonic_s")
                out["stage_started_at"] = e.get("started_at")
                out["stage_finished_at"] = e.get("finished_at")
                break
    except Exception:
        st_wall = None
    if st_wall is None and isinstance(stage_entry, dict):
        st_wall = stage_entry.get("wall_s")
    out["stage_wall_s"] = st_wall
    space = (ms_env or {}).get("mechanism_space") or {}
    attr = space.get("runtime_attribution") if isinstance(space, dict) \
        else None
    if not isinstance(attr, dict) or attr.get(
            "attribution_version") is None:
        out["note"] = ("no mechanism_attribution/1.0.0 record on the "
                       "durable MECHANISM_SPACE envelope "
                       "(uninstrumented build or skipped stage) - "
                       "decomposition UNATTRIBUTED")
        return out
    led = ledger_block or {}
    led_wall = led.get("provider_call_wall_s") or 0.0
    total = attr.get("total_s")
    subphases = attr.get("subphases") or []
    out.update({
        "class": "OBSERVED_IN_STAGE",
        "attribution_version": attr.get("attribution_version"),
        "terminal_state": attr.get("terminal_state"),
        "total_s": total,
        "spans": {s.get("subphase"): s.get("duration_s")
                  for s in subphases
                  if isinstance(s, dict)},
        "subphase_detail": [
            {k: v for k, v in s.items()
             if k in ("subphase", "duration_s", "n_verified_items_examined",
                      "n_structured_items", "n_contracts_evaluated",
                      "n_satisfied", "selected_operator", "provider",
                      "model", "transport_status", "n_fields_nonempty",
                      "semantic_verdict", "candidate_state",
                      "n_consulted", "n_blocked", "n_distinct",
                      "n_indeterminate", "n_retained",
                      "support_states", "derivation")}
            for s in subphases if isinstance(s, dict)],
        "funnel": attr.get("funnel"),
        "llm": attr.get("llm"),
        "ledger_provider_call_wall_s": round(led_wall, 3),
        "ledger_n_calls": led.get("n_calls"),
        "ledger_n_ok": led.get("n_ok"),
        "ledger_failures": list(led.get("failures") or []),
        "adapter_and_stage_overhead_s": (
            round(st_wall - total, 3)
            if isinstance(st_wall, (int, float))
            and isinstance(total, (int, float)) else None),
        "evidence": ("envelope_MECHANISM_SPACE.json $.stage_log "
                      "[MECHANISM_SPACE].duration_monotonic_s + "
                      "$.mechanism_space.runtime_attribution "
                      "(mechanism_attribution/1.0.0) + durable "
                      "model_routing ledger MECHANISM_SPACE role"),
    })
    return out


# ---------------------------------------------------------------- durable row
def harvest_row(dest: Path, run_files, ledger_lines, idx, source_id,
                family, sid, slug, manifest):
    row = {"arm": ARM, "problem_index": idx, "source_id": source_id,
           "declared_family": family, "session_id": sid,
           "run_slug": slug, "observation_source": "DURABLE_BRANCH"}
    envs = {}
    for f in sorted(dest.glob("envelope_*.json")):
        try:
            raw = f.read_bytes()
            d = json.loads(raw.decode("utf-8"))
        except Exception:
            continue
        envs[f.stem[len("envelope_"):]] = d
    row["stage_table"] = _stage_table(manifest, envs)
    by_stage = {e["stage"]: e for e in row["stage_table"]
                if e.get("stage")}
    row["run_wall_s"] = _iso_seconds(manifest.get("started_at"),
                                     manifest.get("finished_at"))
    row["run_manifest_wall"] = {
        "started_at": manifest.get("started_at"),
        "finished_at": manifest.get("finished_at"),
        "final_status": manifest.get("final_status"),
    }

    # ledger per role: EVERY engine_stage value present for this session.
    # R526: PHASE_SPAN lines (orchestration timing, line_class set) are
    # EXCLUDED from provider-call aggregation — they carry no provider
    # wall and would corrupt n_calls/provider chains. Old lines lack
    # line_class (None) and aggregate exactly as before (R525
    # semantics preserved byte-identically on uninstrumented data).
    _att_lines = [ln for ln in ledger_lines
                  if ln.get("session_id") == sid
                  and ln.get("line_class") != "PHASE_SPAN"]
    _phase_lines = [ln for ln in ledger_lines
                    if ln.get("session_id") == sid
                    and ln.get("line_class") == "PHASE_SPAN"]
    roles = sorted({ln.get("engine_stage") for ln in _att_lines
                    if ln.get("engine_stage")})
    led = {}
    for role in roles:
        led[role] = _ledger_block(
            [ln for ln in _att_lines
             if ln.get("engine_stage") == role])
    row["ledger_per_role"] = led
    row["ledger_roles_present"] = roles
    # R526 Question C: the R525 gauntlet purpose boundary, proven per
    # run from durable bytes. The ledger `stage` field carries the
    # generate() purpose tag: gauntlet lines must route ONLY under
    # post_rank:independent_attack; linear ATTACK lines ONLY under
    # "attack". Any independent_attack purpose under POST_RANK_GAUNTLET
    # is a boundary violation (recorded, never silently passed).
    _gaunt_stages = sorted({
        ln.get("stage") for ln in _att_lines
        if ln.get("engine_stage") == "POST_RANK_GAUNTLET"
        and ln.get("stage")})
    _attack_stages = sorted({
        ln.get("stage") for ln in _att_lines
        if ln.get("engine_stage") == "ATTACK" and ln.get("stage")})
    _gaunt_viol = [s for s in _gaunt_stages
                   if s != "post_rank:independent_attack"]
    row["purpose_audit"] = {
        "class": ("OBSERVED_IN_STAGE" if (_gaunt_stages or
                                          _attack_stages)
                  else "UNKNOWN"),
        "gauntlet_purposes": _gaunt_stages,
        "attack_purposes": _attack_stages,
        "gauntlet_boundary_intact": (not _gaunt_stages
                                     or not _gaunt_viol),
        "gauntlet_violations": _gaunt_viol,
        "attack_uses_independent_attack": any(
            s == "independent_attack" for s in _attack_stages),
        "note": ("gauntlet lines must carry only "
                 "post_rank:independent_attack; linear ATTACK lines "
                 "only 'attack' (a2/adversarial)"),
    }
    row["ledger_roles_absent"] = [
        e["stage"] for e in row["stage_table"]
        if e.get("entry_class") == "EXECUTED"
        and e["stage"] not in roles]
    # ledger-only phases: provider-call roles with NO stage_log entry
    # (e.g. the post-rank pipeline, which runs after RANK outside the
    # stage table). Measured via the ledger, explicitly unstaged —
    # never folded into a stage wall, never zero.
    staged = {e["stage"] for e in row["stage_table"]}
    row["ledger_only_phases"] = {
        role: led[role] for role in roles if role not in staged}
    # run residual: run wall minus the executed stage walls
    # (inter-stage overhead + unstaged pipelines). OFFLINE_DERIVED.
    stage_sum = sum(e.get("wall_s") or 0 for e in row["stage_table"]
                    if e.get("entry_class") == "EXECUTED")
    row["run_residual_s"] = {
        "class": "OFFLINE_DERIVED",
        "run_wall_s": row["run_wall_s"],
        "executed_stage_sum_s": round(stage_sum, 3),
        "residual_s": (round(row["run_wall_s"] - stage_sum, 3)
                       if row["run_wall_s"] is not None else None),
        "note": "residual covers unstaged pipelines (e.g. post-rank) "
                "plus inter-stage overhead; see ledger_only_phases",
    }
    # R526 Q-B: post-rank phase spans from the durable ledger channel
    # (PHASE_SPAN lines). run_id->session fallback for lines whose
    # session did not resolve at record time (explicit, never
    # time-window inference: the map comes from sibling attempt lines
    # of the same harvest).
    _run2sess = {}
    for ln in _att_lines:
        _rid, _sid = ln.get("run_id"), ln.get("session_id")
        if _rid and _sid:
            _run2sess.setdefault(_rid, _sid)
    row["phase_spans"] = _phase_spans_block(
        [ln for ln in ledger_lines
         if (ln.get("session_id") == sid
             or (not ln.get("session_id")
                 and _run2sess.get(ln.get("run_id")) == sid))
         and ln.get("line_class") == "PHASE_SPAN"])
    # R526 Q-A: per-generate()-call audit from gen_spans blocks
    # (grouped by the shared per-call request_id — no time windows).
    row["generate_calls"] = _generate_calls_block(
        [ln for ln in _att_lines
         if (ln.get("request_id") or "").startswith("gen_")])

    # RETRIEVE two-level + COLLISION + quality
    row["retrieve_two_level"] = _retrieve_two_level(
        envs.get("RETRIEVE"), run_files)
    # R522: the openalex V2 fan-out job (measures 3-8, 12) + the
    # emitted evidence-pool cardinality (measure 8) — from durable
    # envelope bytes only.
    row["openalex"] = _openalex_block(
        envs.get("RETRIEVE"), row["retrieve_two_level"])
    _oa_items = (envs.get("RETRIEVE") or {}).get("evidence") or []
    row["evidence_pool_cardinality"] = {
        "class": "OBSERVED_IN_STAGE",
        "n_engine_items": len(_oa_items),
        "evidence": "envelope_RETRIEVE.json $.evidence length",
    }
    # R526: per-source V2 job wall table (measure 4) — the ranking
    # input for the sub-operation cliff.
    row["source_job_walls"] = _source_job_walls(envs.get("RETRIEVE"))
    row["collision"] = _collision_block(
        envs.get("COLLISION"), by_stage.get("COLLISION"))
    row["synthesize_validity"] = _synth_validity(envs.get("SYNTHESIZE"))
    # R526 Q-A: SYNTHESIZE wall decomposition from the behavior-neutral
    # implementation spans (synth_spans/1.0 on the durable candidate).
    row["synthesize_spans"] = _synth_spans(
        envs.get("SYNTHESIZE"), by_stage.get("SYNTHESIZE"),
        led.get("SYNTHESIZE"))
    # R528: MECHANISM_SPACE subphase decomposition from the existing
    # mechanism_attribution/1.0.0 instrument (runtime_attribution on
    # the durable MECHANISM_SPACE envelope). Behavior-neutral: the
    # instrument already exists in adapters._lean_mechanism_space; this
    # harvest step only EXTRACTS it into the row (no second
    # attribution framework).
    row["mechanism_space_spans"] = _mechanism_space_spans(
        envs.get("MECHANISM_SPACE"), by_stage.get("MECHANISM_SPACE"),
        led.get("MECHANISM_SPACE"))
    atk_env = envs.get("ATTACK") or {}
    ar = atk_env.get("attack_results") or {}
    row["attack"] = {
        "class": "OBSERVED_IN_STAGE",
        "overall": ar.get("overall") if isinstance(ar, dict) else None,
        "status": (by_stage.get("ATTACK") or {}).get("status"),
        "skip_reason": (by_stage.get("ATTACK") or {}).get("skip_reason"),
        "evidence": "envelope_ATTACK.json $.attack_results + stage_log",
    }
    gen = (led.get("SYNTHESIZE") or {}).get("first_ok_provider")
    atk_lines = [ln for ln in ledger_lines
                 if ln.get("session_id") == sid
                 and ln.get("engine_stage") == "ATTACK"]
    atk_ok = next((ln.get("provider") for ln in atk_lines
                   if ln.get("ok")), None)
    row["attack"]["generator_provider"] = gen
    row["attack"]["attacker_chain"] = [
        ln.get("provider") for ln in atk_lines] or None
    if not (atk_lines and (by_stage.get("ATTACK") or {}).get(
            "status") == "OK"):
        row["attack"]["independence"] = {
            "class": "UNKNOWN",
            "note": "ATTACK did not run to OK on this run — "
                    "independence unmeasured (Art. XXV/LXI)"}
    else:
        row["attack"]["independence"] = {
            "class": "OFFLINE_DERIVED",
            "degree": independence_degree(gen, atk_ok),
            "generator": gen, "attacker": atk_ok,
            "authority": "provider_health.independence_degree (Art. X)",
        }

    # funnel row via the frozen instrument + determinism check
    out = REPO / "R526" / f"{YIELD_ROW_PREFIX}{idx}_{slug}.json"
    r = subprocess.run(
        [sys.executable, str(hv.INSTRUMENT), "--run-dir",
         str(dest), "--out", str(out)],
        capture_output=True, text=True, timeout=300)
    if r.returncode == 0:
        try:
            frow2 = json.loads(out.read_text(
                encoding="utf-8"))["rows"][0]
            row["funnel_row"] = frow2
            row["funnel_row_class"] = "OBSERVED_IN_STAGE"
        except Exception as exc:  # noqa: BLE001
            row["funnel_row"] = None
            row["funnel_row_class"] = "UNKNOWN"
            row["funnel_row_note"] = f"row parse: {exc}"[:160]
    else:
        row["funnel_row"] = None
        row["funnel_row_class"] = "UNKNOWN"
        row["funnel_row_note"] = f"instrument error: {r.stderr[-200:]}"
    row["row_file"] = str(out.relative_to(REPO))
    return row


# ---------------------------------------------------------------- merge store
def _load_existing():
    if OUT_HARVEST.exists():
        try:
            d = json.loads(OUT_HARVEST.read_text(encoding="utf-8"))
            if d.get("arm") != ARM:
                print(f"FATAL: existing harvest is arm={d.get('arm')}, "
                      f"not {ARM} — refusing cross-arm merge")
                sys.exit(2)
            rows = {r.get("session_id"): r for r in d.get("rows", [])}
            return d, rows
        except SystemExit:
            raise
        except Exception:
            pass
    return None, {}


def _is_placeholder(r):
    return "stage_table" not in r and "harvest" in r


def _write_merged(header_extra, new_rows):
    header, rows = _load_existing()
    for r in new_rows:
        sid = r.get("session_id")
        prev = rows.get(sid)
        if prev is not None and _is_placeholder(r) and not _is_placeholder(prev):
            continue
        rows[sid] = r
    # R527 Q5 (build-identity custody): the harvest records the ACTUAL
    # measured build identity taken from the session/build evidence,
    # NOT the manifest stamp. The manifest's measured_engine_sha is
    # the build that FROZE the problems (the baseline/current arm);
    # the after arm runs a DIFFERENT build (the intervention). The
    # session file's expected_commit is the build identity the arm
    # was submitted against — that is the custody of record. If the
    # after-arm artifact identifies itself as the counterpart
    # (baseline) build, the custody check fails closed: the harvest
    # records the discrepancy and the round record refuses to treat
    # it as a valid after measurement (Art. LXXI: the deployed
    # production URL is the delivery standard; the build identity must
    # match the pushed SHA, not a stale manifest stamp).
    _session_engine = ""
    _expected_commit = ""
    try:
        _s = json.loads(SESSIONS.read_text(encoding="utf-8"))
        _expected_commit = _s.get("expected_commit") or ""
        _session_engine = _s.get("expected_commit") or ""
    except Exception:
        _session_engine = ""
        _expected_commit = ""
    _man_engine = ""
    try:
        _m = json.loads(MANIFEST.read_text(encoding="utf-8"))
        _man_engine = _m.get("measured_engine_sha") or ""
    except Exception:
        _man_engine = ""
    # The custody of record for the MEASURED build is the session
    # file's expected_commit (the arm was submitted against that
    # build). The manifest stamp is retained as the baseline reference
    # only. If the two differ, that is EXPECTED for the after arm
    # (the after build differs from the baseline by exactly one
    # intervention) — the harvest records both + the identity check
    # result.
    _identity_check = "MATCH"
    if ARM == "after" and _session_engine and _man_engine \
            and _session_engine != _man_engine:
        # The after arm runs a build that differs from the manifest
        # stamp by exactly the one authorized intervention. The
        # custody of record is the session's expected_commit (the
        # after build), NOT the manifest stamp (the baseline).
        _identity_check = "AFTER_ARM"
    out = {
        "artifact_type": "R526_ATTRIBUTION_HARVEST",
        "battery": "R526-CURRENT-PRODUCTION-ATTRIBUTION",
        "arm": ARM,
        "instrument": f"{INSTRUMENT_ID}/{INSTRUMENT_VERSION}",
        "ms_module": "scripts/r516_harvest_attribution.py (frozen import)",
        "manifest_sha256": hashlib.sha256(
            MANIFEST.read_bytes()).hexdigest(),
        # R527 Q5: the measured build identity is the session's
        # expected_commit (the build the arm was submitted against),
        # NOT the manifest stamp. The manifest stamp is the baseline
        # reference (the build that froze the problems).
        "measured_engine_sha": (_session_engine or _man_engine),
        "measured_engine_sha_source": ("session_expected_commit"
                                       if _session_engine else
                                       "manifest_stamped_engine"),
        "manifest_stamped_engine_sha": _man_engine,
        "session_expected_commit": _expected_commit,
        "build_identity_check": _identity_check,
        "harvested_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                           time.gmtime()),
        "n_rows": len(rows),
        "rows": [rows[k] for k in sorted(rows)],
        "reviewer_provenance": "AI_REVIEW",
    }
    # Fail-closed custody: if the after arm's measured build identity
    # does NOT differ from the baseline manifest stamp, the artifact
    # is recording the WRONG build (a re-harvest of the baseline or
    # a session that was submitted against the baseline, not the
    # after build). That is not a valid after measurement — fail
    # closed with a named reason (Art. XXV: UNKNOWN stays distinct).
    if ARM == "after" and not _session_engine:
        print("FATAL: after-arm harvest has no session expected_commit "
              "— the build identity cannot be verified; refusing to "
              "record a custody-less after measurement")
        sys.exit(2)
    if ARM == "after" and _session_engine and _man_engine \
            and _session_engine == _man_engine:
        print(f"FATAL: after-arm harvest identifies itself as the "
              f"baseline build {_man_engine[:12]} (the manifest "
              f"stamp), not the after build — the custody check "
              f"failed closed: this is NOT a valid after measurement "
              f"(a re-harvest of the baseline or a session submitted "
              f"against the baseline, not the intervention build)")
        sys.exit(2)
    out.update(header_extra or {})
    OUT_HARVEST.write_text(json.dumps(out, indent=1, sort_keys=True,
                                      ensure_ascii=False) + "\n",
                           encoding="utf-8")
    print(f"wrote {OUT_HARVEST} ({len(rows)} rows total)")
    return out


# ---------------------------------------------------------------- live fallback
def harvest_live(result_path: str, idx: int) -> int:
    """Harvest one run from its LIVE /result payload (owner-scoped).

    Full stage table from live stages[] timestamps (all stages present
    in the payload); ledger grouped by EVERY model_route role present;
    RETRIEVE two-level and envelope-derived quality are UNKNOWN with
    named reasons (live retrieval_route is the string "UNKNOWN"; spans
    need envelopes). Never backfilled.
    """
    d = json.loads(Path(result_path).read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_idx = {p["selection_index"]: p for p in manifest["problems"]}
    p = by_idx[idx]
    sid = d.get("session_id")
    row = {"arm": ARM, "problem_index": idx,
           "source_id": p["source_id"],
           "declared_family": p["declared_family"],
           "session_id": sid,
           "observation_source": "LIVE_API",
           "observation_note": (
               "harvested from the live owner-scoped /result payload; "
               "the durable row, when it lands, supersedes only on "
               "byte-identical session_id with fuller evidence")}
    table = []
    for e in d.get("stages") or []:
        st = e.get("stage")
        status = e.get("status")
        if status in ("SKIPPED_ADMISSION", "SKIPPED_UPSTREAM_FAILURE"):
            table.append({"stage": st, "entry_class": status,
                          "class": "LIVE_API", "status": status,
                          "wall_s": None,
                          "note": "unexecuted stage is None, never zero"})
        else:
            dur = _iso_seconds(e.get("started_at"), e.get("finished_at"))
            table.append({"stage": st, "entry_class": "EXECUTED",
                          "class": "OFFLINE_DERIVED_FROM_TIMESTAMPS",
                          "status": status,
                          "wall_s": round(dur, 3) if dur is not None else None,
                          "started_at": e.get("started_at"),
                          "finished_at": e.get("finished_at"),
                          "evidence": "live /result stages[] timestamps"})
    row["stage_table"] = table
    row["run_terminal"] = {"class": "OBSERVED_LIVE",
                           "status": d.get("status"),
                           "final_status": d.get("final_status")}
    calls = ((d.get("run_state") or {}).get("model_route") or {}).get(
        "calls") or []
    roles = sorted({c.get("role") for c in calls if c.get("role")})
    led = {}
    for role in roles:
        lines = [c for c in calls if (c.get("role") or "") == role]
        provs, models = [], []
        for c in lines:
            if c.get("provider") not in provs:
                provs.append(c.get("provider"))
            if c.get("model") not in models:
                models.append(c.get("model"))
        wall = sum(float(c.get("latency_ms") or 0)
                   for c in lines) / 1000.0
        led[role] = {
            "class": "LIVE_API", "n_calls": len(lines),
            "n_ok": sum(1 for c in lines if c.get("status") == "OK"),
            "attempts_seen": None, "retries_observed": None,
            "retries_note": "live calls carry no attempt numbers",
            "provider_chain": provs, "models": models,
            "provider_call_wall_s": round(wall, 3),
            "fallback_hops": None,
            "fallback_note": "live calls carry no fallback edges",
            "failures": sorted({str(c.get("status")) for c in lines
                                if c.get("status") != "OK"}),
            "first_ok_provider": next(
                (c.get("provider") for c in lines
                 if c.get("status") == "OK"), None),
        }
    row["ledger_per_role"] = led
    row["ledger_roles_present"] = roles
    ms = ((d.get("run_state") or {}).get("mechanism_state") or {})
    row["synthesize_validity"] = {
        "class": "LIVE_API_PARTIAL",
        "mechanism_text_chars": len(str(ms.get("mechanism") or "")),
        "candidate_count": ms.get("candidate_count"),
        "evidence_pack_present": bool(d.get("evidence_pack")),
        "span_verbatim_rate": None,
        "span_note": "envelope-level spans unavailable live (Art. XXV)",
    }
    row["retrieve_two_level"] = {
        "class": "UNKNOWN",
        "note": "live retrieval_route is uninformative; two-level "
                "attribution needs the durable RETRIEVE envelope "
                "(Art. XXV)",
    }
    row["source_job_walls"] = {
        "class": "UNKNOWN",
        "note": "per-source job walls need the durable envelope",
    }
    row["collision"] = {
        "class": "LIVE_API",
        "status": next((e.get("status") for e in d.get("stages") or []
                        if e.get("stage") == "COLLISION"), None),
        "note": "leg-level timing unavailable live",
    }
    row["attack"] = {
        "class": "LIVE_API",
        "overall": (d.get("final_state") or {}).get("adversarial_overall"),
        "status": next((e.get("status") for e in d.get("stages") or []
                        if e.get("stage") == "ATTACK"), None),
    }
    row["funnel_row"] = None
    row["funnel_row_class"] = "UNKNOWN"
    row["funnel_row_note"] = "funnel instrument needs durable run bytes"
    _write_merged({"live_harvest_note": (
        "rows tagged LIVE_API predate their durable rows; re-harvest "
        "merges by session_id when the branch lands")}, [row])
    return 0


# ---------------------------------------------------------------- durable arm
def harvest_arm() -> int:
    branch = "origin/runtime-state-hf"
    print("fetching durable branch ...")
    fr = _git("fetch", "origin", "runtime-state-hf", timeout=300)
    print("fetch rc=", fr.returncode)
    sessions = json.loads(SESSIONS.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    ls = _git("ls-tree", "--name-only", f"{branch}:runs", timeout=120)
    slugs = sorted(ls.stdout.decode("utf-8", "replace").split())
    slug_of = {}
    for slug in slugs:
        for name in ("run_manifest.json", "final_state.json"):
            raw = _show(f"{branch}:runs/{slug}/{name}")
            if not raw:
                continue
            try:
                dd = json.loads(raw.decode("utf-8"))
            except Exception:
                continue
            if dd.get("session_id"):
                slug_of[dd["session_id"]] = slug
                break
    print(f"mapped {len(slug_of)} sessions to slugs")

    led_raw = _show(f"{branch}:model_routing/ledger.jsonl") or b""
    ledger_lines = []
    for line in led_raw.decode("utf-8", "replace").splitlines():
        try:
            ledger_lines.append(json.loads(line))
        except Exception:
            continue
    print(f"ledger lines: {len(ledger_lines)}")

    try:
        import tempfile
        tmp = Path(tempfile.mkdtemp(prefix="R526_harvest_"))
        rows = []
        for s in sessions["submissions"]:
            sid = s.get("session_id")
            idx = s.get("problem_index")
            slug = slug_of.get(sid)
            if not slug:
                rows.append({"arm": ARM, "problem_index": idx,
                             "session_id": sid, "harvest": "NOT_YET",
                             "note": "session not on durable branch yet"})
                print(f"#{idx} {sid}: not on durable branch yet")
                continue
            dest = tmp / "runs" / slug
            dest.mkdir(parents=True, exist_ok=True)
            fl = _git("ls-tree", "--name-only",
                      f"{branch}:runs/{slug}", timeout=120)
            files = sorted(
                fl.stdout.decode("utf-8", "replace").split())
            for f in files:
                raw = _show(f"{branch}:runs/{slug}/{f}")
                if raw is not None:
                    (dest / f).write_bytes(raw)
            man_raw = _show(f"{branch}:runs/{slug}/run_manifest.json")
            man = json.loads(man_raw.decode("utf-8")) if man_raw else {}
            by_idx = {pp["selection_index"]: pp
                      for pp in manifest["problems"]}
            pp = by_idx[idx]
            row = harvest_row(dest, files, ledger_lines, idx,
                              pp["source_id"], pp["declared_family"],
                              sid, slug, man)
            rows.append(row)
            st = {e["stage"]: e.get("status")
                  for e in row["stage_table"]
                  if e.get("stage") in ("RETRIEVE", "SYNTHESIZE",
                                        "MECHANISM_SPACE", "COLLISION",
                                        "PHYSICS", "ATTACK")}
            print(f"#{idx} {slug[-24:]}: " + " ".join(
                f"{k}={v}" for k, v in st.items()))
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    _write_merged({}, rows)
    return 0


# ---------------------------------------------------------------- compare
def _agg(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return {"n": 0, "mean": None, "median": None, "min": None,
                "max": None, "stdev": None, "values": []}
    return {"n": len(vals), "mean": round(sum(vals) / len(vals), 3),
            "median": round(statistics.median(vals), 3),
            "min": round(min(vals), 3), "max": round(max(vals), 3),
            "stdev": round(statistics.pstdev(vals), 3)
            if len(vals) > 1 else 0.0,
            "values": [round(v, 3) for v in vals]}


def compare(base_path, opt_path, out_path):
    base = json.loads(Path(base_path).read_text(encoding="utf-8"))
    opt = json.loads(Path(opt_path).read_text(encoding="utf-8"))
    ar = {r["problem_index"]: r for r in base["rows"]
          if "stage_table" in r}
    br = {r["problem_index"]: r for r in opt["rows"]
          if "stage_table" in r}
    pairs = []
    for idx in sorted(set(ar) & set(br)):
        ra, rb = ar[idx], br[idx]
        ta = {e["stage"]: e for e in ra["stage_table"]}
        tb = {e["stage"]: e for e in rb["stage_table"]}
        pair = {"problem_index": idx,
                "source_id": ra["source_id"],
                "declared_family": ra["declared_family"],
                "current_source": ra.get("observation_source"),
                "after_source": rb.get("observation_source"),
                "stages": {}}
        for st in sorted(set(ta) | set(tb)):
            ea, eb = ta.get(st) or {}, tb.get(st) or {}
            wa, wb = ea.get("wall_s"), eb.get("wall_s")
            pair["stages"][st] = {
                "current_wall_s": wa, "after_wall_s": wb,
                "delta_s": (round(wb - wa, 3)
                            if wa is not None and wb is not None
                            else None),
                "current_status": ea.get("status"),
                "after_status": eb.get("status"),
            }
        la, lb = ra.get("ledger_per_role", {}), rb.get(
            "ledger_per_role", {})
        pair["ledger"] = {}
        for role in sorted(set(la) | set(lb)):
            ba, bb = la.get(role) or {}, lb.get(role) or {}
            pair["ledger"][role] = {
                "current_call_wall_s": ba.get("provider_call_wall_s"),
                "after_call_wall_s": bb.get("provider_call_wall_s"),
                "current_providers": ba.get("provider_chain"),
                "after_providers": bb.get("provider_chain"),
                "current_retries": ba.get("retries_observed"),
                "after_retries": bb.get("retries_observed"),
                "current_fallbacks": ba.get("n_fallback_hops"),
                "after_fallbacks": bb.get("n_fallback_hops"),
            }
        pair["ledger_only_phases"] = {
            "current": sorted((ra.get("ledger_only_phases") or {}).keys()),
            "after": sorted((rb.get("ledger_only_phases") or {}).keys()),
        }
        pair["run_residual_s"] = {
            "current": (ra.get("run_residual_s") or {}).get("residual_s"),
            "after": (rb.get("run_residual_s") or {}).get("residual_s"),
        }
        # R522: the openalex job + emitted pool + quality parity ride
        # the pair directly so the decision evidence is per-problem.
        oa_b = ra.get("openalex") or {}
        oa_a = rb.get("openalex") or {}
        pair["openalex"] = {
            "current_wall_s": oa_b.get("job_wall_s"),
            "after_wall_s": oa_a.get("job_wall_s"),
            "current_transport_state": oa_b.get("transport_state"),
            "after_transport_state": oa_a.get("transport_state"),
            "current_records_returned": oa_b.get("records_returned"),
            "after_records_returned": oa_a.get("records_returned"),
            "current_retry_backoff_s": oa_b.get("retry_backoff_s"),
            "after_retry_backoff_s": oa_a.get("retry_backoff_s"),
            "current_attempts": oa_b.get("attempt_index"),
            "after_attempts": oa_a.get("attempt_index"),
            "current_emitted_items": (
                oa_b.get("emitted_pool") or {}).get("n_openalex_items"),
            "after_emitted_items": (
                oa_a.get("emitted_pool") or {}).get("n_openalex_items"),
            "current_sources_excluded": (
                oa_b.get("sources_excluded_envelope")),
            "after_sources_excluded": (
                oa_a.get("sources_excluded_envelope")),
        }
        pair["evidence_pool_cardinality"] = {
            "current": (ra.get("evidence_pool_cardinality") or {}).get(
                "n_engine_items"),
            "after": (rb.get("evidence_pool_cardinality") or {}).get(
                "n_engine_items"),
        }
        pair["quality"] = {
            "current_span_rate": (ra.get("synthesize_validity") or {}).get(
                "span_verbatim_rate"),
            "after_span_rate": (rb.get("synthesize_validity") or {}).get(
                "span_verbatim_rate"),
            "current_mechanisms": (ra.get("synthesize_validity") or {}).get(
                "n_mechanisms_seen"),
            "after_mechanisms": (rb.get("synthesize_validity") or {}).get(
                "n_mechanisms_seen"),
            "current_funnel_class": ra.get("funnel_row_class"),
            "after_funnel_class": rb.get("funnel_row_class"),
        }
        pairs.append(pair)
    agg = {}
    for tag, rows in (("current", [ar[i] for i in sorted(
            set(ar) & set(br))]),
                      ("after", [br[i] for i in sorted(
                          set(ar) & set(br))])):
        per_stage = {}
        stages = set()
        for r in rows:
            for e in r["stage_table"]:
                if e.get("entry_class") == "EXECUTED":
                    stages.add(e["stage"])
        for st in sorted(stages):
            per_stage[st] = _agg([
                next((e.get("wall_s") for e in r["stage_table"]
                      if e.get("stage") == st), None) for r in rows])
        # provider / retry / fallback contributions across all roles
        prov, retr, fb = {}, {}, {}
        for r in rows:
            for role, b in (r.get("ledger_per_role") or {}).items():
                for pv in b.get("provider_chain") or []:
                    prov[pv] = prov.get(pv, 0) + (b.get(
                        "provider_call_wall_s") or 0)
                if b.get("retries_observed"):
                    retr[role] = retr.get(role, 0) + b["retries_observed"]
                if b.get("n_fallback_hops"):
                    fb[role] = fb.get(role, 0) + b["n_fallback_hops"]
        # per-source job wall totals (R526 measure 4): sum of each
        # source's max job wall across rows = a rough critical-path
        # contribution ranking; mean too.
        src_walls = {}
        for r in rows:
            for jr in (r.get("source_job_walls") or {}).get("jobs") or []:
                sid = jr.get("source_id")
                if sid is None:
                    continue
                src_walls.setdefault(sid, []).append(
                    jr.get("job_wall_s"))
        per_source = {sid: _agg([v for v in vs if v is not None])
                      for sid, vs in src_walls.items()}
        agg[tag] = {"n_paired": len(rows), "per_stage": per_stage,
                    "per_source_job_wall": per_source,
                    "provider_wall_contribution_s": {
                        k: round(v, 3) for k, v in prov.items()},
                    "retry_counts": retr, "fallback_counts": fb}
    out = {
        "artifact_type": "R526_ATTRIBUTION_COMPARISON",
        "battery": "R526-CURRENT-PRODUCTION-ATTRIBUTION",
        "current_harvest": str(base_path),
        "after_harvest": str(opt_path),
        "n_paired_problems": len(pairs),
        "pairs": pairs,
        "aggregates": agg,
        "statistics_note": ("raw paired rows + arm aggregates "
                            "(mean/median/min/max/stdev; no significance "
                            "theater). Classification lives in the round "
                            "record."),
        "reviewer_provenance": "AI_REVIEW",
    }
    Path(out_path).write_text(json.dumps(out, indent=1, sort_keys=True,
                                         ensure_ascii=False) + "\n",
                              encoding="utf-8")
    print(f"wrote {out_path} ({len(pairs)} paired problems)")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--compare", nargs=2, metavar=("CURRENT", "AFTER"),
                    default=None)
    ap.add_argument("--out", default=None)
    ap.add_argument("--live", default=None,
                    help="live /result payload path to harvest")
    ap.add_argument("--idx", type=int, default=None,
                    help="manifest selection_index for --live")
    args = ap.parse_args()
    if args.compare:
        sys.exit(compare(args.compare[0], args.compare[1],
                         args.out or "R526/ATTR_COMPARISON.json"))
    if args.live:
        if args.idx is None:
            print("FATAL: --live requires --idx")
            sys.exit(2)
        sys.exit(harvest_live(args.live, args.idx))
    sys.exit(harvest_arm())
