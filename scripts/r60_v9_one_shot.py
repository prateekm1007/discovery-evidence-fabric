#!/usr/bin/env python3
"""scripts/r60_v9_one_shot.py — the FROZEN ENGINE-ROUTE MACHINE for
the sealed holdout v9 one-shot generation (roadmap P2 -> 6; the
preregistration audit/holdout_v9/PREREGISTRATION.json @ the audit
branch, seal 502e93d8..., n=30, power pre-registered).

AUTHORED AND COMMITTED BEFORE the holdout-v9-generation claim and
BEFORE ANY v9 problem read (claim-before-work, Art. 29(b); the F62
lesson: the machine freezes before the run). The claim notes name
this file's commit as the frozen machine.

MEASURED PATH (Art. 22 v3.2.0, F61 class — the prereg's mandatory
artifact): per problem, the CAPABILITY path runs through
    discovery_fabric.engine.engine_route.run_row
      -> population_search (typed plans, K>=3, distinct TRIZ
         principles, domain clamp) -> mechanism_space.assemble_
         candidate (the six typed operator contracts) -> candidate_
         schema.extend_to_1_1 (enum fields FROM the plan) ->
         validate_candidate_schema -> physics_checks routing
         (sign-of-result; PENDING_INPUTS typed when the problem
         carries no numeric inputs) -> novelty_gate
(the deterministic wiring proof engine_route was designed for), and
the LLM EXPANSION of the chosen winner plan reuses the FROZEN V7.7
loop BYTE-UNCHANGED (machine_generate_v77 — the same expansion
discipline the matched-budget ablation measures; the engine_route
docstring: "the LLM expansion of the chosen plan is the machine's
job ... the wiring is identical"). The transport is the R36
REGISTERED route only (zai-gateway glm-4-plus), gated by
route_adapter.require_registered_model BEFORE the gateway starts
(a wrapper-only or swapped-route measurement is refused typed).

PRE-REGISTERED WINNER RULE (identical semantics to the ablation
driver's, evaluated over the ENGINE's live plan space): among the
plans whose integrated candidate carries NO MEASURE_CLASS_NOT_ALLOWED
and NO SIGNAL_NOT_PERMITTED schema finding, the FIRST non-duty_cycle
plan in population order; fallback first satisfied; last resort first
plan (the rule is typed in every row).

ONE-SHOT DISCIPLINE (the prereg's one_shot_protocol + Art. 29(c)):
  - problems ONLY from the audit branch (git show), seal verified by
    the PUBLISHED canonical-tuple recipe (eval/seal_anchor_
    verification_recipe.json @9ea2614a8; F50) — fail-closed typed;
  - the PRIVATE rubric is NEVER read, listed, or copied by this
    script (it does not exist on any builder-visible branch; custody
    = the auditor's access-controlled private repo, CORR-3);
  - ONE generation per problem (a call that returns content is never
    re-drawn; the machine's own transport retries + REPAIR_BUDGET=3
    are the frozen machine's discipline, byte-unchanged);
  - per-row durable files (resume-safe: committed rows are skipped,
    Art. 29(d) partial-row heartbeats); a durable events ledger;
  - the gateway-log slice + the 30/30 served==registered attestation
    land with the run (pre-scoring gate; `attest` recomputes it from
    committed bytes for the verifier lane, Art. 29(c)).

RESUME SAFETY: eval/holdout_v9_generation/rows/ carries one file per
problem; existing files are skipped (the r11/r58 convention). The
events ledger is rewritten after every row.

Zero LLM calls at import and in dry-run (Art. 22: fixtures prove
mechanics only).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

# CORR-3 session-local transport resolution: the z-ai CLI lives in the
# sandbox project's node_modules bin (NOT on the default PATH). The
# gateway spawns `z-ai` by name, so the bin dir MUST be on PATH
# before start_gateway().
ZAI_BIN = Path("/home/z/my-project/node_modules/.bin")
if ZAI_BIN.is_dir() and str(ZAI_BIN) not in sys.path:
    import os
    os.environ["PATH"] = f"{ZAI_BIN}:{os.environ.get('PATH', '')}"

from r40_machine_v77 import (  # noqa: E402
    machine_generate_v77, start_gateway, declared_template,
    V77_REQUEST_MODEL)
# Art. 22 v3.2.0 measured-path declaration (F61): the v9 measurement
# runs THROUGH THE ENGINE — engine_route -> mechanism_space — and the
# transport identity is gated by the engine's own route registry
# (a machine model that does not match the registered route is a
# typed refusal BEFORE any call).
from discovery_fabric.engine import engine_route  # noqa: E402
from discovery_fabric.engine import population_search  # noqa: E402
from discovery_fabric.engine import route_adapter  # noqa: E402

OUT = REPO / "eval" / "holdout_v9_generation"
GW_LOG = REPO / "ENGINE_RUNS" / "zai_gateway_calls.jsonl"
EXECUTOR_ID = "builder-r60s1@holdout-v9-generation"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V9_PREREG_PATH = "audit/holdout_v9/PREREGISTRATION.json"
V9_PROBLEMS_PATH = "audit/holdout_v9/holdout_v9_problems.json"
EXPECTED_SEAL = ("502e93d84b19dcda5b0a7d656a3195e509ddec8247aad2e6b"
                 "ddec082e10f34ce")
EXPECTED_N = 30
MEASURED_PATH = ("discovery_fabric.engine.engine_route -> "
                 "mechanism_space")
# burned NON-v9 rows for the mechanics-only smoke (the v7 packet —
# burned by the committed v7 run + judgments; NOT among the 30 v9
# rows). Problem statements load from the audit ref (the r42/r58
# convention).
SMOKE_PACKET = "audit/holdout_v7/holdout_v7_problems.json"
SMOKE_ROWS = ["HO7-01-zinc-ew-acid-mist",
              "HO7-09-chiller-condenser-fouling"]


def _now() -> str:
    return (datetime.datetime.now(datetime.UTC).isoformat()
            .replace("+00:00", "Z"))


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _git_show(path: str) -> str:
    raw = subprocess.run(["git", "show", f"{AUDIT_REF}:{path}"],
                         capture_output=True, text=True, timeout=30,
                         cwd=str(REPO))
    assert raw.returncode == 0, (
        f"cannot read {path} from {AUDIT_REF} (typed abort): "
        f"{raw.stderr[-200:]}")
    return raw.stdout


def verify_seal(doc: dict, prereg_sel: str) -> dict:
    """The PUBLISHED canonical-tuple seal recipe (F50,
    eval/seal_anchor_verification_recipe.json @9ea2614a8): project
    each uncontaminated problem to [problem_id, device, failure,
    question, question_type, list(user_variables)], sort by
    problem_id, canonical JSON blob, sha256. Fail-closed typed on any
    mismatch — a broken seal NEVER starts the one-shot."""

    def proj(p):
        return [p["problem_id"], p["device"], p["failure"],
                p["question"], p["question_type"],
                list(p["user_variables"])]

    fresh = [p for p in doc["problems"]
             if p.get("contamination_tag") is None]
    blob = json.dumps(
        [proj(p) for p in sorted(fresh, key=lambda x: x["problem_id"])],
        sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    recomputed = hashlib.sha256(blob.encode()).hexdigest()
    doc_sel = str(doc.get("selection_sha256") or "")
    # the packet's OWN seal: recomputed == the doc's == the prereg's
    # (the v9-specific expected-seal constant is asserted separately
    # in load_v9_problems — the recipe itself is packet-generic)
    ok = (recomputed == doc_sel == prereg_sel)
    return {"recomputed": recomputed, "doc_selection_sha256": doc_sel,
            "prereg_selection_sha256": prereg_sel,
            "verified": ok}


def load_v9_problems() -> tuple:
    """Problems ONLY, from the auditor's custody (fail-closed). The
    PRIVATE rubric is never touched by this script. The seal is
    verified by the published recipe BEFORE any row runs."""
    prereg = json.loads(_git_show(V9_PREREG_PATH))
    sel = str(prereg.get("selection_sha256") or "")
    assert sel == EXPECTED_SEAL, (
        f"the prereg's selection_sha256 drifted from the pre-registered "
        f"v9 seal {EXPECTED_SEAL[:16]}... (typed abort)")
    doc = json.loads(_git_show(V9_PROBLEMS_PATH))
    seal = verify_seal(doc, sel)
    assert seal["verified"], (
        f"SEAL MISMATCH (typed abort, fail closed): recomputed "
        f"{seal['recomputed'][:16]} doc {seal['doc_selection_sha256'][:16]}"
        f" prereg {seal['prereg_selection_sha256'][:16]} — the one-shot "
        f"never starts on a broken seal (Art. 7)")
    probs = doc["problems"]
    assert len(probs) == EXPECTED_N, (
        f"expected {EXPECTED_N} problems, got {len(probs)} (typed abort)")
    qt = Counter((p.get("question_type") or "").lower()
                 for p in probs)
    assert qt.get("intervention-proposal", 0) == 15, (
        f"expected 15 intervention-proposal, got {qt} (typed abort)")
    assert qt.get("predictor-design", 0) == 15, (
        f"expected 15 predictor-design, got {qt} (typed abort)")
    return prereg, doc, probs, seal


def contract_satisfied(result: dict) -> bool:
    """Pre-registered legality bind over the ENGINE's schema findings:
    no MEASURE_CLASS_NOT_ALLOWED and no SIGNAL_NOT_PERMITTED (the
    P1.4 clamp semantics; the r52 0/0/0 gate's two hard keys)."""
    f = result.get("schema_findings") or {}
    return ("MEASURE_CLASS_NOT_ALLOWED" not in f
            and "SIGNAL_NOT_PERMITTED" not in f)


def select_winner(row_out: dict) -> tuple:
    """PRE-REGISTERED deterministic winner rule over the ENGINE's live
    plan space (identical semantics to the ablation driver's rule):
    first contract-satisfied non-duty_cycle plan in population order;
    fallback first satisfied; last resort first plan."""
    plans, results = row_out["plans"], row_out["results"]
    sat = [i for i in range(len(plans))
           if contract_satisfied(results[i])]
    non_sched = [i for i in sat
                 if plans[i].get("measure_class") != "duty_cycle"]
    if non_sched:
        i = non_sched[0]
        return plans[i], results[i], "non_schedule_first"
    if sat:
        i = sat[0]
        return plans[i], results[i], "schedule_fallback"
    return plans[0], results[0], "none_satisfied_fallback"


def challenger_prob(prob: dict, winner: dict, rule: str) -> dict:
    """The typed_plan payload field (the ablation challenger-arm
    convention, byte-identical construction): the machine's own
    json.dumps(prob) carries the ENGINE's chosen plan into the
    generation prompt (machine logic byte-unchanged)."""
    p = dict(prob)
    p["typed_plan"] = {
        "note": ("PLAN CONDITIONING (the engine route's typed plan "
                 "layer — the intervention MUST implement this plan, "
                 "selected by the engine's population_search through "
                 "engine_route.run_row)"),
        "operator": winner["operator_id"],
        "triz_principle": winner["principle_id"],
        "measure_class": winner["measure_class"],
        "signals_used": list(winner.get("signals_used") or []),
        "selection_rule": rule,
    }
    return p


def engine_trace(problem: dict, row_out: dict, winner: dict,
                 wresult: dict, rule: str) -> dict:
    """The measured-path evidence: the engine's plan space, the
    winner's schema findings, the physics routing, the novelty gate —
    every capability decision on the row comes from the engine."""
    return {
        "measured_path": MEASURED_PATH,
        "route_schema": row_out["results"][0].get("route_schema"),
        "plans_n": len(row_out["plans"]),
        "plan_principles": [p.get("principle_id")
                            for p in row_out["plans"]],
        "plan_measure_classes": [p.get("measure_class")
                                 for p in row_out["plans"]],
        "declared_domain_classes": population_search
        .declared_domain_classes(problem),
        "winner_rule": rule,
        "winner": {"operator_id": winner["operator_id"],
                   "principle_id": winner["principle_id"],
                   "measure_class": winner["measure_class"],
                   "signals_used": list(winner.get("signals_used")
                                        or [])},
        "winner_schema_findings": wresult.get("schema_findings") or {},
        "winner_candidate_state": (wresult.get("trace") or {})
        .get("candidate_state"),
        "winner_physics": [
            {"check_id": r.get("check_id"),
             "verdict": r.get("verdict")}
            for r in (wresult.get("physics") or [])],
        "novelty_gate_verdicts": (row_out.get("novelty_gate")
                                  or {}).get("verdicts"),
        "physics_inputs_supplied": None,
        "physics_inputs_note": (
            "the v9 problems carry constraint TEXT (user_variables "
            "are text lines, not structured numerics) — the route "
            "records PENDING_INPUTS typed gaps, never fabricated "
            "results (Art. 8: unknown stays unknown)"),
    }


def run_rows(probs: list, smoke: bool = False,
             synthetic_plan: dict | None = None,
             smoke_pop: dict | None = None) -> int:
    """The one-shot pass. Resume-safe: committed row files are
    skipped. Rows + events ledger + gateway slice + attestation."""
    # Art. 22 v3.2.0 (F61): the measured path is declared through the
    # engine route registry — the one-shot serves ONLY the registered
    # generator id; a mismatch REFUSES typed BEFORE the gateway starts
    # (RouteRefused semantics, Art. 3).
    try:
        route_adapter.require_registered_model(V77_REQUEST_MODEL)
    except Exception as e:  # RouteRefused and any registry drift
        print(f"MEASURED-PATH REFUSAL (typed, Art. 22 v3.2.0): "
              f"machine model {V77_REQUEST_MODEL} is not the engine-"
              f"registered route: {e}", flush=True)
        return 3

    rows_dir = OUT / ("rows_smoke" if smoke else "rows")
    rows_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = OUT / ("events_smoke.json" if smoke
                         else "events.json")

    gw, gw_key = start_gateway()
    print(f"gateway healthy (registered route {V77_REQUEST_MODEL})",
          flush=True)
    try:
        return _run_body(probs, smoke, synthetic_plan, smoke_pop,
                         rows_dir, ledger_path, gw, gw_key)
    finally:
        # one gateway per run, terminated at end (the r58 lesson:
        # leaked gateways poison the next session's probe)
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:
            gw.kill()


def _run_body(probs: list, smoke: bool, synthetic_plan, smoke_pop,
              rows_dir: Path, ledger_path: Path, gw, gw_key: str) -> int:
    offset = GW_LOG.stat().st_size if GW_LOG.exists() else 0
    run_start = _now()

    # restore the diversity-cap histogram from committed rows
    used_templates: Counter = Counter()
    for f in sorted(rows_dir.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        decl = r.get("declared_template_prose")
        if decl:
            used_templates[decl] += 1

    events = []
    if ledger_path.exists():
        prev = json.loads(ledger_path.read_text(encoding="utf-8"))
        events = prev.get("events", [])

    done = skipped = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(
            probs, key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = rows_dir / f"{pid}.json"
        if outp.exists():
            skipped += 1
            continue
        # (1) THE MEASURED PATH: the engine's integrated route
        row_out = engine_route.run_row(prob)
        # (2) the pre-registered winner rule over the engine plans
        if smoke and synthetic_plan is not None:
            # mechanics-only smoke: a SYNTHETIC plan (Art. 22 —
            # fixtures prove mechanics only); the engine trace is
            # still recorded from the real run_row output
            winner, rule = synthetic_plan, "smoke_synthetic"
            wresult = {"schema_findings": {}, "physics": [],
                       "trace": {}}
            machine_prob = challenger_prob(prob, winner, rule)
        else:
            winner, wresult, rule = select_winner(row_out)
            machine_prob = challenger_prob(prob, winner, rule)
        trace = engine_trace(prob, row_out, winner, wresult, rule)
        # (3) the FROZEN V7.7 expansion loop (byte-unchanged) renders
        # the engine's chosen plan on the registered route
        hist = dict(used_templates)
        t_row = _now()
        final, attempts, final_meta = machine_generate_v77(
            machine_prob, gw_key, used_templates=used_templates)
        decl = declared_template(final)
        if decl and not str(prob.get("question_type", "")) \
                .lower().startswith("predictor"):
            used_templates[decl] += 1
        residual = final_meta.get("residual_findings") or {}
        row = {
            "problem_id": pid,
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "machine": ("r60_v9_one_shot/1.0.0 — frozen engine-route "
                        "machine: engine_route.run_row -> "
                        "mechanism_space + the V7.7 expansion loop "
                        f"(byte-reused; V77_REQUEST_MODEL="
                        f"{V77_REQUEST_MODEL})"),
            "run": "holdout-v9-generation (sealed one-shot)"
                   + (" [SMOKE mechanics-only]" if smoke else ""),
            "engine_trace": trace,
            "typed_plan": machine_prob.get("typed_plan"),
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "a1_answer": final,
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "residual_findings": residual,
            },
            "declared_template_prose": decl,
            "allowed_row_outside": len(
                residual.get("ALLOWED_ROW_OUTSIDE", [])),
            "sha256_16": _sha16(final),
            "smoke": bool(smoke),
        }
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": t_row,
            "histogram_before": hist,
            "histogram_after": dict(used_templates),
            "attempts": attempts,
            "engine_plans_n": trace["plans_n"],
            "winner_rule": rule,
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V9_GENERATION_EVENTS/1.0.0",
            "run": "holdout-v9-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": V77_REQUEST_MODEL,
            "measured_path": MEASURED_PATH,
            "window_started_at": run_start,
            "events": events},
            indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        done += 1
        print(f"[{idx}/{len(probs)}] {pid} rule={rule} plans="
              f"{trace['plans_n']} repairs="
              f"{final_meta.get('repairs')} critic="
              f"{final_meta.get('critic_verdict')} chars={len(final)} "
              f"({time.time()-t0:.0f}s)", flush=True)
        t0 = time.time()

    # gateway-log slice: exactly this run's window
    slice_lines = []
    if GW_LOG.exists():
        with GW_LOG.open("rb") as f:
            f.seek(offset)
            slice_lines = [ln for ln in f.read()
                           .decode("utf-8", "replace").splitlines()
                           if ln.strip()]
    slice_path = OUT / ("gateway_slice_smoke.txt" if smoke
                        else "gateway_slice.txt")
    slice_path.write_text("\n".join(slice_lines) + "\n",
                          encoding="utf-8")
    _write_attestation(slice_path, run_start, smoke)
    print(f"rows done={done} skipped(resumed)={skipped}", flush=True)
    return 0


def _parse_slice(slice_path: Path) -> tuple:
    calls, errors = [], []
    for ln in slice_path.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln.startswith("{"):
            continue
        try:
            c = json.loads(ln)
        except Exception:  # noqa: BLE001 — telemetry line
            continue
        if c.get("status") == "OK" and (
                c.get("requested_model") is not None
                or c.get("model") is not None):
            calls.append(c)
        elif c.get("status") == "ERROR":
            errors.append(c)
    return calls, errors


def _write_attestation(slice_path: Path, run_start: str,
                        smoke: bool) -> dict:
    """The 30/30 served==registered PRE-SCORING attestation (the
    prereg's mandatory artifact). Recomputable from committed bytes by
    `attest` (the verifier lane, Art. 29(c) — recompute, never
    re-run)."""
    calls, errors = _parse_slice(slice_path)
    rows_dir = OUT / ("rows_smoke" if smoke else "rows")
    n_rows = len(list(rows_dir.glob("*.json")))
    att = {
        "record": "HOLDOUT_V9_GENERATION_ATTESTATION/1.0.0",
        "executor_id": EXECUTOR_ID,
        "registered_model": V77_REQUEST_MODEL,
        "measured_path": MEASURED_PATH,
        "window_started_at": run_start,
        "window_ended_at": _now(),
        "rows_committed": n_rows,
        "gateway_completed_calls": len(calls),
        "gateway_error_lines": len(errors),
        "all_calls_requested_registered": all(
            c.get("requested_model") == V77_REQUEST_MODEL
            for c in calls),
        "all_calls_served_registered": all(
            c.get("model") == V77_REQUEST_MODEL for c in calls),
        "served_model_matches_registered": all(
            c.get("model") in (None, V77_REQUEST_MODEL)
            for c in calls),
        "note": ("served==requested==registered per completed call "
                 "from the gateway log slice; error lines (429/5xx "
                 "backoff telemetry) carry no model field and are "
                 "typed, never scored"),
    }
    if not smoke:
        att["rows_30_30_attestation"] = (n_rows == EXPECTED_N
                                         and len(calls) >= EXPECTED_N
                                         and att[
                                             "all_calls_served_registered"])
    dest = OUT / ("attestation_smoke.json" if smoke
                  else "attestation.json")
    dest.write_text(json.dumps(att, indent=1) + "\n",
                    encoding="utf-8")
    return att


def attest() -> int:
    """VERIFIER LANE: recompute the attestation from committed bytes
    (the slice + the row files) — never a re-run (Art. 29(c))."""
    slice_path = OUT / "gateway_slice.txt"
    assert slice_path.exists(), "no committed gateway slice (typed)"
    att = _write_attestation(slice_path, "(recomputed from bytes)",
                             smoke=False)
    print(json.dumps(att, indent=1))
    return 0


def smoke() -> int:
    """Mechanics-only live fire on BURNED NON-v9 rows (the HO7 packet
    — burned by the committed v7 run; NOT among the 30 v9 rows). The
    smoke rows carry a SYNTHETIC plan (mechanics only, Art. 22) and
    live in rows_smoke/, excluded from every measurement file."""
    doc = json.loads(_git_show(SMOKE_PACKET))
    probs = [p for p in doc["problems"]
             if p["problem_id"] in SMOKE_ROWS]
    assert len(probs) == len(SMOKE_ROWS), (
        "smoke rows not found in the HO7 packet (typed abort)")
    synth = {"operator_id": "DOMAIN_KNOWLEDGE_FIRST",
             "principle_id": "P35",
             "measure_class": "boundary",
             "signals_used": ["pressure", "temperature"]}
    return run_rows(probs, smoke=True, synthetic_plan=synth)


def dry_run() -> int:
    """Zero-LLM mechanics check (Art. 22: fixtures prove mechanics
    only): the audit-ref loader plumbing (seal recipe EXERCISED on a
    burned packet, never on v9), the engine route, the winner rule,
    the payload construction, the attestation shape — on burned DEV
    problems."""
    # (1) the seal recipe, exercised on the burned v7 packet (public;
    # the recipe recomputes its seal exactly)
    v7 = json.loads(_git_show(SMOKE_PACKET))
    v7_prereg = json.loads(
        _git_show("audit/holdout_v7/PREREGISTRATION.json"))
    seal7 = verify_seal(v7, str(v7_prereg.get("selection_sha256")
                                or ""))
    assert seal7["verified"], (
        f"seal recipe failed on the burned v7 packet: {seal7}")
    print(f"[dry-run] seal recipe verified on burned v7: "
          f"{seal7['recomputed'][:16]}")
    # (2) the engine route + winner rule + payload on 3 burned DEV
    # problems (zero LLM: run_row is the deterministic wiring proof)
    dev = json.loads((REPO / "eval/problems_dev12.json")
                     .read_text(encoding="utf-8"))
    dev_probs = dev["problems"] if isinstance(dev, dict) else dev
    rules = Counter()
    for p in dev_probs[:3]:
        row_out = engine_route.run_row(p)
        assert len(row_out["plans"]) >= 3, (
            p["problem_id"], "K>=3 violated (typed)")
        assert len({pl["principle_id"]
                    for pl in row_out["plans"]}) == len(
            row_out["plans"]), "principles not distinct (typed)"
        winner, wresult, rule = select_winner(row_out)
        rules[rule] += 1
        cp = challenger_prob(p, winner, rule)
        assert cp["typed_plan"]["operator"] == winner["operator_id"]
        assert "typed_plan" not in p, "payload mutation leaked"
        trace = engine_trace(p, row_out, winner, wresult, rule)
        assert trace["measured_path"] == MEASURED_PATH
        assert trace["plans_n"] == len(row_out["plans"])
    print(f"[dry-run] engine route OK on 3 burned DEV problems; "
          f"winner rules: {dict(rules)}; payload construction OK")
    # (3) the machine import surface is byte-reused (the frozen loop)
    import r40_machine_v77 as m  # noqa: F401 — import-time check only
    assert m.V77_REQUEST_MODEL == "agnes-3.0-flash"
    print(f"[dry-run] frozen V7.7 expansion loop importable, "
          f"V77_REQUEST_MODEL={m.V77_REQUEST_MODEL}")
    print("[dry-run] PASS (zero LLM, zero network)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["dry-run", "smoke", "run",
                                    "attest"])
    ap.add_argument("--max-rows", type=int, default=0,
                    help="cap rows for this invocation (heartbeat)")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.cmd == "dry-run":
        return dry_run()
    if args.cmd == "smoke":
        return smoke()
    if args.cmd == "run":
        _, _, probs, seal = load_v9_problems()
        print(f"[run] seal verified {seal['recomputed'][:16]}... "
              f"({len(probs)} problems, 15+15)", flush=True)
        if args.max_rows:
            probs = probs[:args.max_rows]
        return run_rows(probs)
    if args.cmd == "attest":
        return attest()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
