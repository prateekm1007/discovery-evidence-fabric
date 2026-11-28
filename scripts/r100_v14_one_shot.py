#!/usr/bin/env python3
"""scripts/r100_v14_one_shot.py — the sealed holdout v14 one-shot
machine (the AM88/CORR-7 corrected-set lane; claim c-0115).

DELTA vs the sealed r98 v13 driver (everything else is IMPORTED,
never copied):
  1. custody: the AUDITOR-authored v14 problems + preregistration
     (CORRECTED per AM88/CORR-7: HO14-08-mbr-fouling replaced by
     HO14-08-cwetland-clog) live on the AUDIT BRANCH — this driver
     reads them from the PINNED audit ref 36f9559ef (committed bytes
     only, never a worktree) and verifies the F50 seal
     7707a0b4520c2a52... fail-closed BEFORE any row runs;
  2. record ids R100_V14_*; executor builder-r95s1@holdout-v14-
     generation; run label holdout-v14-generation;
  3. the disjointness gate: the r99 guard ran 0-clashes CLEAN over
     the FULL v1-v13 corpus against THIS seal (36f9559ef) before this
     driver existed — the run order is the auditor's own prereg.

The generation loop is r97.machine_generate_v79 — the frozen V7.7
expansion byte-mirrored with the AM82 controllers — imported and
called UNCHANGED. All five binds stay the frozen machine's own
battery; the c-0109 corrector (v1.1, incl. the typed-vocabulary
convergence extension, CI-tested) and the c-0110 AIDE controller ride
it as committed. Model pin agnes-3.0-flash (AM75 lineage), pre-gated
by route_adapter.require_registered_model BEFORE the gateway starts.
Zero LLM at import and in dry-run. Resume-safe heartbeat chunks
(10 -> 20 -> 30 accumulate).
"""
from __future__ import annotations

import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r97_v12_one_shot as r97  # noqa: E402  (the frozen v12 machine)
import r40_machine_v77 as m77  # noqa: E402

OUT = REPO / "eval" / "holdout_v14_generation"
EXECUTOR_ID = "builder-r95s1@holdout-v14-generation"
AUDIT_REF = "36f9559ef"  # the AM88/CORR-7 audit tip (pinned by sha)
V14_PREREG_PATH = "audit/holdout_v14/PREREGISTRATION.json"
V14_PROBLEMS_PATH = "audit/holdout_v14/holdout_v14_problems.json"
EXPECTED_SEAL = ("7707a0b4520c2a52b92fa56841d46e2d3cea757b391a6d091b2a"
                 "de18cd4bd6a7")
V14_REQUEST_MODEL = "agnes-3.0-flash"
EXPECTED_N = 30
P3_MEDIAN_MAX_S = 120.0
P3_WORST_MAX_S = 300.0

MACHINE_RECORD = (
    "r100_v14_one_shot/1.0.0 — the sealed v14 one-shot (the "
    "AM88/CORR-7 corrected set): r97's machine_generate_v79 imported "
    "UNCHANGED (the frozen V7.7 expansion + [c-0109] "
    "tool_grounded_critic post-generation correction v1.1 with the "
    "typed-vocabulary convergence extension, CI-tested; [c-0110] "
    "aide_tree_search best-first population controller, "
    "budget-matched); ALL FIVE BINDS = the frozen battery, "
    "byte-identical; P3 per-row wall-clock measured by THIS driver "
    "(measurement only — zero generation-behavior change)")


def _git_show_audit(path: str) -> str:
    """The v14 custody reader: the AUDITOR-authored corrected set is
    committed on the AUDIT branch — read from the PINNED audit ref
    (committed bytes only, never a worktree), fail-closed."""
    import subprocess
    out = subprocess.run(["git", "show", f"{AUDIT_REF}:{path}"],
                         capture_output=True, cwd=REPO)
    assert out.returncode == 0, (
        f"the v14 custody file {path} is not readable at the pinned "
        f"audit ref {AUDIT_REF} (typed abort — custody comes from "
        f"committed bytes only)")
    return out.stdout.decode("utf-8")


def load_v14_problems() -> tuple:
    """Problems ONLY, from committed audit-ref bytes (the AM88
    corrected set), fail-closed on the F50 seal + the model pin. The
    auditor's PRIVATE rubric is never touched."""
    prereg = json.loads(_git_show_audit(V14_PREREG_PATH))
    sel = str(prereg.get("selection_sha256") or "")
    assert sel == EXPECTED_SEAL, (
        f"the prereg's selection_sha256 drifted from the "
        f"pre-registered v14 seal {EXPECTED_SEAL[:16]}... (typed abort)")
    pin = str((prereg.get("model_pin") or {}).get("registered_id") or "")
    assert pin == V14_REQUEST_MODEL, (
        f"the prereg's model_pin.registered_id is {pin!r} but the "
        f"instrument serves {V14_REQUEST_MODEL!r} (typed abort)")
    reg_model = r97.route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == V14_REQUEST_MODEL, (
        f"the route registry's registered id is {reg_model!r} but "
        f"the instrument serves {V14_REQUEST_MODEL!r} (typed abort)")
    doc = json.loads(_git_show_audit(V14_PROBLEMS_PATH))
    seal = r97.verify_seal(doc, sel)
    assert seal["verified"], (
        f"SEAL MISMATCH (typed abort, fail closed): recomputed "
        f"{seal['recomputed'][:16]} doc "
        f"{seal['doc_selection_sha256'][:16]} prereg "
        f"{seal['prereg_selection_sha256'][:16]}")
    probs = doc["problems"]
    assert len(probs) == EXPECTED_N, (
        f"expected {EXPECTED_N} problems, got {len(probs)} (typed abort)")
    qt = {}
    for p in probs:
        k = (p.get("question_type") or "").lower()
        qt[k] = qt.get(k, 0) + 1
    n_int = sum(v for k, v in qt.items() if k.startswith("intervention"))
    n_pre = sum(v for k, v in qt.items() if k.startswith("predictor"))
    assert n_int == 15 and n_pre == 15, (
        f"expected 15 intervention + 15 predictor, got {n_int}+{n_pre} "
        f"({qt}; typed abort)")
    return prereg, doc, probs, seal


def run_rows(probs: list, max_rows: int = 0, smoke: bool = False) -> int:
    """The sealed v14 one-shot pass. Resume-safe; prefix heartbeat
    chunks ACCUMULATE (10 -> 20 -> 30). P3 per-row wall-clock is
    measured around the WHOLE row body (engine route + generation +
    legs)."""
    try:
        r97.route_adapter.require_registered_model(V14_REQUEST_MODEL)
    except Exception as e:  # RouteRefused and registry drift
        print(f"MEASURED-PATH REFUSAL (typed, Art. 22 v3.2.0): "
              f"{V14_REQUEST_MODEL} is not the engine-registered "
              f"route: {e}", flush=True)
        return 3
    if r97._gateway_alive():
        print("REFUSED (typed, exit 3): a gateway is already listening "
              "on 127.0.0.1:8787 — kill it first.", flush=True)
        return 3
    if r97.route_adapter.resolve_vault_key("AGNES_API_KEY") is None:
        print("REFUSED (typed INFRA_CREDENTIAL_MISSING, exit 3): "
              "AGNES_API_KEY absent — restore custody first.",
              flush=True)
        return 3
    frozen_const = r97.bind_v12_request_model()  # identity no-op,
    # asserted + logged (the freeze guard owns the file byte)
    assert frozen_const == V14_REQUEST_MODEL, (
        "identity drifted: the frozen machine constant and the "
        "registered route must be the same id (typed abort)")
    import os
    os.environ["ZAI_GATEWAY_UPSTREAM"] = r97.GATEWAY_UPSTREAM
    os.environ["AGNES_MODEL_ID"] = V14_REQUEST_MODEL
    rows_dir = OUT / ("rows_smoke" if smoke else "rows")
    rows_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / ("events_smoke.json" if smoke else "events.json")
    gw, gw_key = m77.start_gateway()
    print(f"gateway healthy (upstream={r97.GATEWAY_UPSTREAM}, "
          f"registered route {V14_REQUEST_MODEL}; frozen v77 file "
          f"constant {frozen_const!r} runtime-bound to "
          f"{V14_REQUEST_MODEL!r})", flush=True)
    try:
        return _run_body(probs, max_rows, smoke, rows_dir, ledger_path,
                         gw, gw_key)
    finally:
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:
            gw.kill()


def _run_body(probs: list, max_rows: int, smoke: bool, rows_dir: Path,
              ledger_path: Path, gw, gw_key: str) -> int:
    offset = r97.GW_LOG.stat().st_size if r97.GW_LOG.exists() else 0
    run_start = r97._now()
    if max_rows:
        probs = probs[:max_rows]
    used_templates = {}
    for f in sorted(rows_dir.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        decl = r.get("declared_template_prose")
        if decl:
            used_templates[decl] = used_templates.get(decl, 0) + 1
    used_templates = __import__("collections").Counter(used_templates)
    events = []
    if ledger_path.exists():
        prev = json.loads(ledger_path.read_text(encoding="utf-8"))
        events = prev.get("events", [])
    done = skipped = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(probs,
                                      key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = rows_dir / f"{pid}.json"
        if outp.exists():
            skipped += 1
            continue
        row_wall_start = time.time()  # ---- P3 measurement starts
        row_out = r97.engine_route.run_row(prob)
        winner, wresult, rule = r97.v10m.select_winner(row_out)
        machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        trace = r97.v10m.engine_trace(prob, row_out, winner, wresult,
                                      rule)
        hist = dict(used_templates)
        t_row = r97._now()
        final, attempts, final_meta = r97.machine_generate_v79(
            machine_prob, gw_key, used_templates=used_templates)
        decl = m77.declared_template(final)
        if decl and not str(prob.get("question_type", "")).lower() \
                .startswith("predictor"):
            used_templates[decl] += 1
        residual = final_meta.get("residual_findings") or {}
        leg = r97.v10m.onrow_leg(prob, row_out, final)
        row_wall_s = round(time.time() - row_wall_start, 1)  # P3 end
        row = {
            "problem_id": pid,
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": V14_REQUEST_MODEL,
            "machine": MACHINE_RECORD,
            "run": "holdout-v14-generation (sealed one-shot)"
                   + (" [SMOKE mechanics-only]" if smoke else ""),
            "engine_trace": trace,
            "onrow_physics": leg,
            "typed_plan": machine_prob.get("typed_plan"),
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "row_wall_s": row_wall_s,
            "a1_answer": final,
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "residual_findings": residual,
                "stop_reason": final_meta.get("stop_reason"),
                "trajectory": final_meta.get("trajectory"),
                "delivered_node_id":
                    final_meta.get("delivered_node_id"),
                "delivery_rule": final_meta.get("delivery_rule"),
            },
            "declared_template_prose": decl,
            "allowed_row_outside": len(
                residual.get("ALLOWED_ROW_OUTSIDE", [])),
            "sha256_16": r97._sha16(final),
            "smoke": bool(smoke),
        }
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": t_row,
            "row_wall_s": row_wall_s,
            "histogram_before": hist,
            "histogram_after": dict(used_templates),
            "attempts": attempts,
            "engine_plans_n": trace["plans_n"],
            "winner_rule": rule,
            "repairs": final_meta.get("repairs"),
            "critic_verdict": final_meta.get("critic_verdict"),
            "residual_finding_keys": sorted(residual.keys()),
            "repair_budget_burned_full": (
                final_meta.get("repairs") == m77.REPAIR_BUDGET),
            "stop_reason": final_meta.get("stop_reason"),
            "corrections_total": sum(
                a.get("corrections", {}).get("corrected", 0)
                for a in attempts),
            "chemistry_rewrites_total": sum(
                a.get("corrections", {}).get("chemistry_rewrites", 0)
                for a in attempts),
            "distinct_candidates":
                (final_meta.get("trajectory") or {})
                .get("distinct_candidate_count"),
            "delivered_node_id": final_meta.get("delivered_node_id"),
            "onrow_sign_contradictions":
                leg["sign_contradiction_count"],
            "onrow_answer_claims": len(
                leg["delivered_answer"]["claims"]),
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V14_GENERATION_EVENTS/1.0.0",
            "run": "holdout-v14-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": V14_REQUEST_MODEL,
            "registered_upstream": r97.GATEWAY_UPSTREAM,
            "measured_path": r97.MEASURED_PATH,
            "binds": ["F75_deliverable_class",
                      "chemistry_elicitation",
                      "formula_direction",
                      "element_conservation",
                      "equilibrium_direction"],
            "controllers": ["tool_grounded_critic (c-0109 v1.1; TOOLS "
                            "FIRST — post-generation mechanical "
                            "correction; typed-vocabulary "
                            "convergence extension)",
                            "aide_tree_search (c-0110; TREE SECOND "
                            "— best-first population, "
                            "budget-matched)"],
            "window_started_at": run_start,
            "events": events},
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
        print(f"[{idx}/{len(probs)}] {pid} rule={rule} plans="
              f"{trace['plans_n']} repairs="
              f"{final_meta.get('repairs')} critic="
              f"{final_meta.get('critic_verdict')} corr="
              f"{events[-1]['corrections_total']} chars={len(final)} "
              f"wall={row_wall_s}s stop="
              f"{final_meta.get('stop_reason')} "
              f"({time.time()-t0:.0f}s)", flush=True)
        t0 = time.time()
    # gateway-log slice merged across heartbeat windows (resume
    # honesty, Art. 29(d))
    slice_path = OUT / ("gateway_slice_smoke.txt" if smoke
                        else "gateway_slice.txt")
    prev_lines = []
    if slice_path.exists():
        prev_lines = [ln for ln in slice_path.read_text(
            encoding="utf-8").splitlines() if ln.strip()]
    slice_lines = []
    if r97.GW_LOG.exists():
        with r97.GW_LOG.open("rb") as f:
            f.seek(offset)
            slice_lines = [ln for ln in f.read()
                           .decode("utf-8", "replace").splitlines()
                           if ln.strip()]
    merged = prev_lines + slice_lines
    slice_path.write_text("\n".join(merged) + "\n", encoding="utf-8")
    _write_attestation(slice_path, run_start, smoke)
    print(f"rows done={done} skipped(resumed)={skipped}", flush=True)
    return 0


def p3_speed_from_rows() -> dict:
    """P3 gates recomputed from the COMMITTED row files' row_wall_s
    (never from memory — Art. 29(c))."""
    rows = sorted((OUT / "rows").glob("*.json"))
    walls = []
    for f in rows:
        r = json.loads(f.read_text(encoding="utf-8"))
        if not r.get("smoke") and r.get("row_wall_s") is not None:
            walls.append((r["problem_id"], float(r["row_wall_s"])))
    if not walls:
        return {"rows_measured": 0, "gates_evaluated": False}
    vals = [w for _, w in walls]
    median = statistics.median(vals)
    worst_pid, worst = max(walls, key=lambda t: t[1])
    return {
        "rows_measured": len(vals),
        "median_row_wall_s": round(median, 1),
        "worst_row_wall_s": worst,
        "worst_row_id": worst_pid,
        "median_gate_pass": median <= P3_MEDIAN_MAX_S,
        "worst_gate_pass": worst <= P3_WORST_MAX_S,
        "gates": f"median <= {P3_MEDIAN_MAX_S:.0f} s, worst <= "
                 f"{P3_WORST_MAX_S:.0f} s (the AM84 P3 lane gates)",
        "gates_evaluated": True,
    }


def _write_attestation(slice_path: Path, run_start: str,
                       smoke: bool) -> dict:
    n_rows = len(list((OUT / ("rows_smoke" if smoke else "rows"))
                      .glob("*.json")))
    calls, errors = [], []
    for ln in slice_path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            c = json.loads(ln)
        except Exception:  # noqa: BLE001 — telemetry line
            continue
        if c.get("status") == "OK":
            calls.append(c)
        elif c.get("status") == "ERROR":
            errors.append(c)
    att = {
        "record": ("R100_V14_SMOKE_ATTESTATION/1.0.0" if smoke
                   else "R100_V14_ATTESTATION/1.0.0"),
        "run": "holdout-v14-generation",
        "executor_id": EXECUTOR_ID,
        "registered_model": V14_REQUEST_MODEL,
        "window_started_at": run_start,
        "rows_committed": n_rows,
        "expected_rows": EXPECTED_N,
        "gateway_calls_ok": len(calls),
        "gateway_errors": len(errors),
        "all_calls_requested_registered": all(
            c.get("requested_model") == V14_REQUEST_MODEL
            for c in calls),
        "all_calls_served_registered": all(
            c.get("model") == V14_REQUEST_MODEL for c in calls),
        "all_calls_upstream_registered": all(
            c.get("upstream") == r97.GATEWAY_UPSTREAM for c in calls),
        "serving_key_digests": sorted({str(c.get("key_id"))
                                       for c in calls
                                       if c.get("key_id")}),
        "p3_speed": p3_speed_from_rows(),
        "resumed_slice_merge": True,
        "note": ("served==requested==registered per completed call "
                 "from the gateway log slice; the P3 speed gates "
                 "recompute from the committed row files; error lines "
                 "(429/5xx backoff telemetry) carry no model field "
                 "and are typed, never scored"),
    }
    if not smoke:
        att["rows_30_30_attestation"] = (
            n_rows == EXPECTED_N and len(calls) >= EXPECTED_N
            and att["all_calls_served_registered"]
            and att["all_calls_requested_registered"])
    dest = OUT / ("attestation_smoke.json" if smoke
                  else "attestation.json")
    dest.write_text(json.dumps(att, indent=1) + "\n", encoding="utf-8")
    return att


def attest() -> int:
    """VERIFIER LANE: recompute the attestation + P3 gates from
    committed bytes — never a re-run (Art. 29(c))."""
    slice_path = OUT / "gateway_slice.txt"
    assert slice_path.exists(), "no committed gateway slice (typed)"
    att = _write_attestation(slice_path, "(recomputed from bytes)",
                             smoke=False)
    print(json.dumps(att, indent=1))
    return 0


def dry_run() -> int:
    """Zero-LLM proof: the r97 wiring battery (byte-identical loop)
    PLUS the v14 custody load (seal + pin + 15/15 split) on the
    committed audit-ref bytes."""
    print("[dry-run] v14 custody load (zero LLM):", flush=True)
    _, doc, probs, seal = load_v14_problems()
    print(f"  seal {seal['recomputed'][:16]}... verified; "
          f"{len(probs)} problems (15 intervention + 15 predictor); "
          f"model pin agnes-3.0-flash co-verified "
          f"(prereg == instrument == route registry)", flush=True)
    print("[dry-run] the r97 wiring battery (the SAME generation loop "
          "object, stubbed transport, real frozen scans):", flush=True)
    return r97.dry_run()


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dry-run", "run", "attest"])
    ap.add_argument("--max-rows", type=int, default=0,
                    help="cap rows for this invocation (heartbeat; "
                    "PREFIX slice — chunks must ACCUMULATE)")
    ap.add_argument("--smoke", action="store_true",
                    help="live fire on BURNED NON-v14 rows (the HO7 "
                    "packet; rows_smoke/, excluded from every "
                    "measurement file)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "dry-run":
        return dry_run()
    if args.cmd == "run":
        if args.smoke:
            doc = json.loads(r97._git_show(r97.SMOKE_PACKET))
            probs = [p for p in doc["problems"]
                     if p["problem_id"] in r97.SMOKE_ROWS]
            print(f"[smoke] burned NON-v14 rows only: "
                  f"{[p['problem_id'] for p in probs]} (live LLM, "
                  f"mechanics validation; rows_smoke/, never scored)",
                  flush=True)
            return run_rows(probs, max_rows=args.max_rows, smoke=True)
        _, _, probs, seal = load_v14_problems()
        print(f"[run] corpus = the SEALED v14 packet (the AM88 "
              f"corrected set); seal {seal['recomputed'][:16]}... "
              f"verified ({len(probs)} problems); model_pin "
              f"co-verified: prereg == instrument == route registry "
              f"== {V14_REQUEST_MODEL}", flush=True)
        return run_rows(probs, max_rows=args.max_rows)
    if args.cmd == "attest":
        return attest()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
