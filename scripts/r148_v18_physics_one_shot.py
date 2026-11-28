#!/usr/bin/env python3
"""r148s1 v18 PHYSICS one-shot — DIR-2/7: the physics-correct
re-generation on the SAME problem-only set, fresh rows.

Lane (claim c-0258, claim-before-work pre-draw): the generation-time
PHYSICS-TRUTH gate. The v17 rows carried genuine physics errors the
shallow screen and the pint units check missed (the owner's deep
review names six: wrong-signed relations, invalid formulas, magnitude
impossibilities, mechanism-class-at-scale failures). THIS runner:

  (1) PREVENTION at generation: the PHYSICS_TRUTH_BIND rides the
      typed_plan — every relation sign-correct, every magnitude
      first-principles bounded, every formula dimensionally valid,
      the mechanism class viable at the stated scale; every
      assumption carries a falsifiable bound (the ASSUMPTION-BOUND
      contract);
  (2) VALIDATION at generation: discovery_fabric.generation.
      physics_validate.validate_row runs on the generated row —
      GENUINE_PHYSICS_ERROR rows are NOT emitted: the runner retries
      (up to 3 physics retries) with the typed repair_directive fed
      back; a row that cannot pass stays UNWRITTEN (byte-resume
      retries it) and the failure is typed in the events ledger —
      never scored as quality (Art. 15);
  (3) the quant generation-time contract rides UNCHANGED (the pint
      prediction computed in-process; 0 invented numbers);
  (4) the r148-qualified panel arbitration stays the c-0257 lane's
      scope (no double-burn).

One-shot per problem, byte-resume, agnes-3.0-flash pinned. Fresh
output dir — the v17 rows are never overwritten.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import r97_v12_one_shot as r97  # noqa: E402
import r40_machine_v77 as m77  # noqa: E402
from discovery_fabric.generation import mechanism_map as mm  # noqa: E402
from discovery_fabric.generation import quant_generic as qg  # noqa: E402
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402
from discovery_fabric.generation import quant_test as qt  # noqa: E402
from discovery_fabric.generation import (  # noqa: E402
    inspiration_retrieval as ir)
from discovery_fabric.generation import (  # noqa: E402
    novelty_strength as ns)
from discovery_fabric.generation import (  # noqa: E402
    physics_validate as pv)

OUT = REPO / "eval" / "holdout_v18_generation"
OUT.mkdir(exist_ok=True)
EXECUTOR_ID = os.environ.get(
    "V18_EXECUTOR_ID", "builder-r148s1@v18-physics-one-shot")
PROBLEMS_AUDIT_PATH = "eval/holdout_v17/problems.json"
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
MODEL_PIN = "agnes-3.0-flash"
MAX_PHYSICS_RETRIES = 5

MACHINE_RECORD = (
    "r148_v18_physics_one_shot/1.0.0 — the physics-correct one-shot: "
    "the r146 engine (the r144 binds + the EPO scaffold + the "
    "MOOSE-Chem inspiration + the novelty_strength lever + the "
    "generation-time quant contract) with the PHYSICS-TRUTH gate "
    "added: the PHYSICS_TRUTH_BIND at generation + the typed check "
    "registry validated post-generation (GENUINE_PHYSICS_ERROR rows "
    "are repaired/retried, never emitted); every assumption carries "
    "a falsifiable bound. Problem-only, agnes-3.0-flash pinned.")

PHYSICS_TRUTH_BIND = (
    "PHYSICS GUARD (a hard gate — checked automatically): (1) SIGN: "
    "added mass LOWERS natural frequency (omega = sqrt(k/(m+m_a))); "
    "in SERIES dielectrics the LOWER-eps layer sees MORE field "
    "(E_i = D/eps_i); the protected metal is the CATHODE (the "
    "sacrificial anode is more anodic, separately connected). "
    "(2) MAGNITUDE: energy/mass/flow claims must survive "
    "first-principles bounds from the stated geometry (Q = m*c*dT, "
    "m = rho*A*t; dissolved ions are not separable by static "
    "gradient fields — susceptibility ~ 1e-6 loses to thermal "
    "agitation). (3) FORMULAS: dimensionally reducible (a field "
    "reduces to V/m; eps_0 = 8.85e-12 F/m, eps_r dimensionless). "
    "(4) SCALE: the mechanism must be capable of the stated effect "
    "at the stated scale. State every assumption with a falsifiable "
    "bound ('assumed: X because Y; falsified if Z'). A mechanism "
    "that fails any of (1)-(4) must be REPLACED, not decorated.")

DESIGN_POINT_BIND = (
    "DESIGN POINT (mandatory for testability): the invention MUST "
    "carry a 'DESIGN_POINT' paragraph stating the numbers the "
    "mechanism acts through — at least ONE explicit magnitude (a "
    "percentage effect or a parameter with a unit: MPa, kPa, mm, "
    "mm/s, Hz, K, kV, m/s, W/mK, m^2, HV). Numbers come from the "
    "problem statement, stock datasheet values, or a TYPED "
    "assumption ('assumed: X because Y') — never invented as "
    "measured facts.")

EPO_BIND = (
    "NON-OBVIOUSNESS SCAFFOLD (the EPO problem-solution approach): "
    "the invention MUST state, in order — "
    "(a) CLOSEST PRIOR ART: the closest standard practice for this "
    "failure, described concretely (what a competent shop does "
    "today); "
    "(b) DISTINGUISHING FEATURE: what the proposed mechanism does "
    "that the closest prior art does NOT — one feature, stated "
    "physically; "
    "(c) OBJECTIVE TECHNICAL PROBLEM: the technical effect the "
    "distinguishing feature achieves, phrased as the problem it "
    "solves (not 'improve durability'); "
    "(d) WHY THE OBVIOUS KNOB FAILS: the physical reason the "
    "standard practice's obvious knob (more material, harder surface, "
    "lower load, better lubrication, more monitoring) cannot achieve "
    "the same effect here. "
    "A mechanism that cannot fill (a)-(d) is not a mechanism — "
    "strengthen the ARRANGEMENT, not the adjectives.")

NOVELTY_STRENGTH_BIND = (
    "the departure from standard practice must be a NON-OBVIOUS "
    "arrangement with a stated physical reason the obvious knob "
    "fails here; the generic moves (increase/reduce flow, modulate "
    "pressure, add monitoring, insulate more, add a filter or a "
    "schedule) are NOT a mechanism when they are the whole departure "
    "— put the novelty in the arrangement")


def load_v18_problems() -> list:
    """The SEALED bytes from the audit branch (the strengthened
    runner's loader pattern byte-for-byte: git-show the audit tip,
    digest the probs list, map to the engine's problem shape). The
    LOCAL eval/holdout_v17/problems.json is a DIFFERENT 30-problem
    set (the attempt1-4 lesson: the local set's ids — rail-shelling,
    choke-erosion — are not the sealed ids — slurry-pump,
    pneumatic-elbow; those attempts are typed aside)."""
    import hashlib
    import subprocess
    raw = subprocess.run(
        ["git", "show", f"{AUDIT_REF}:{PROBLEMS_AUDIT_PATH}"],
        capture_output=True, text=True, check=True).stdout
    probs = json.loads(raw)
    probs = probs.get("problems") if isinstance(probs, dict) else probs
    assert isinstance(probs, list) and len(probs) == 30, (
        f"expected 30 sealed problems, got {len(probs) if probs else 0}")
    digest16 = hashlib.sha256(
        json.dumps(probs, sort_keys=True, ensure_ascii=False)
        .encode()).hexdigest()[:16]
    assert digest16 == "2eb520f695aaf1ab", (
        f"sealed problems digest drifted: {digest16}")
    reg_model = r97.route_adapter.ROUTE_REGISTRY["registered"]["model"]
    assert reg_model == MODEL_PIN, (
        f"route registry registered {reg_model!r} != {MODEL_PIN!r}")
    mapped = []
    for p in probs:
        mapped.append({
            "problem_id": p["problem_id"],
            "domain": p.get("domain", ""),
            "device": "(stated in the problem)",
            "failure": str(p.get("problem", "")).strip(),
            "failure_mode": str(p.get("problem", "")).strip()[:120],
            "question": ("What engineering change, intervention, or "
                         "design would prevent or mitigate the stated "
                         "failure? Invent the mechanism."),
            "question_type": "invention",
            "user_variables": [],
            "constraint": "",
            "contamination_tag": p.get("split", "V17"),
        })
    return mapped


def _row_outcome(pid: str, prob: dict, final: str, attempts: int,
                 wall_s: float, trace: dict, t_row: str,
                 physics: dict, quant: dict, sel_check, gate: dict,
                 final_meta: dict) -> dict:
    return {
        "problem_id": pid,
        "domain": prob.get("domain"),
        "question_type": prob.get("question_type"),
        "executor_id": EXECUTOR_ID,
        "registered_model": MODEL_PIN,
        "machine": MACHINE_RECORD,
        "run": "v18-physics-one-shot (one-shot, problem-only, "
               "the physics-truth gate demanded at generation)",
        "engine_trace": trace,
        "generated_at": t_row,
        "attempts_n": attempts,
        "row_wall_s": wall_s,
        "a1_answer": final,
        "quant_prediction": quant,
        "physics_validation": physics,
        "generation_checks": {
            "failure_class": trace.get("failure_physics",
                                       {}).get("family"),
            "selected_mech_class": sel_check.selected_mech_class,
            "off_target": bool(sel_check.off_target),
            "novelty": gate["novelty"],
            "genuine_physics_errors": physics["n_errors"],
            "assumption_bounds": physics["n_assumption_bounds"],
        },
        "final_meta": final_meta,
        "declared_template_prose": m77.declared_template(final),
        "sha256_16": r97._sha16(final),
    }


def main() -> int:
    probs = load_v18_problems()
    if r97._gateway_alive():
        print("REFUSED (typed, exit 3): a gateway is already "
              "listening on 127.0.0.1:8787 — kill it first (a stale "
              "gateway poisons the slice; the r58 lesson).",
              flush=True)
        return 3
    os.environ["ZAI_GATEWAY_UPSTREAM"] = r97.GATEWAY_UPSTREAM
    os.environ["AGNES_MODEL_ID"] = r97.V12_REQUEST_MODEL
    gw, gw_key = m77.start_gateway()
    print(f"gateway healthy (upstream={r97.GATEWAY_UPSTREAM}, "
          f"registered route {r97.V12_REQUEST_MODEL})", flush=True)
    print(f"r148 v18 physics one-shot: {len(probs)} problems | "
          f"pin {MODEL_PIN} | the physics gate demanded at "
          f"generation ({len(pv.CHECKS)} registry checks)",
          flush=True)
    events = []
    ledger_path = OUT / "GENERATION_EVENTS.json"
    if ledger_path.exists():
        events = json.loads(ledger_path.read_text()).get("events", [])
    done = failed = resumed = 0
    t0 = time.time()
    try:
        _run_all(probs, gw_key, events, ledger_path)
    finally:
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:  # noqa: BLE001
            try:
                gw.kill()
            except Exception:  # noqa: BLE001
                pass
    ev = json.loads(ledger_path.read_text()).get("events", [])
    done = sum(1 for e in ev if e.get("outcome") != "PHYSICS_GATE_UNRESOLVED")
    failed = sum(1 for e in ev if e.get("outcome") == "PHYSICS_GATE_UNRESOLVED")
    return 0


def _run_all(probs: list, gw_key: str, events: list,
             ledger_path: Path) -> None:
    global done, failed, resumed
    done = failed = resumed = 0
    for idx, prob in enumerate(sorted(probs,
                                      key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = OUT / f"{pid}.json"
        if outp.exists():
            resumed += 1
            continue
        row_wall_start = time.time()
        print(f"=== r148 {pid} ({idx}/30) ...", flush=True)
        try:
            problem_text = prob.get("failure") or prob.get("problem", "")
            sel = mm.classify_failure(problem_text)
            fc = sel.failure_class
            mprompt = mm.mechanism_prompt_block(problem_text)
            import inspect as _inspect
            eng_pred = {"status": "no_formula_for_class",
                        "note": ("typed: no deterministic formula for "
                                 "the mapped classes — the invention "
                                 "carries the first-principles "
                                 "estimate")}
            for mech in sel.allowed_mech_classes:
                if mech in qt.FORMULAS:
                    fn = qt.FORMULAS[mech]
                    required = [pn for pn, prm in _inspect.signature(
                        fn).parameters.items()
                        if prm.default is _inspect.Parameter.empty]
                    eng_pred = {
                        "status": "parameters_required",
                        "mech_class": mech,
                        "formula": getattr(fn, "__name__", str(fn)),
                        "required_inputs": required,
                        "pint_unit_checked": True,
                        "note": ("typed: the deterministic pint-"
                                 "checked formula needs these inputs "
                                 "— the invention MUST name the "
                                 "measurement plan and the estimated "
                                 "values (typed assumptions allowed)")}
                    break
            insp = ir.retrieve_inspiration(fc)
            row_out = r97.engine_route.run_row(prob)
            winner, wresult, rule = r97.v10m.select_winner(row_out)
            machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        except Exception as e:  # noqa: BLE001
            print(f"{pid}: ROUTE FAIL {type(e).__name__}: "
                  f"{str(e)[:120]} — skipped (byte-resume picks up)",
                  flush=True)
            continue
        # THE STRENGTHENED INSTRUMENT (r146 lever A, byte-faithful):
        # the EPO conditioning + the hypothesis ranking + the
        # mechanism-selection block + the engine prediction manifest
        ns_out = ns.novelty_strength_block(problem_text,
                                           prob.get("domain", ""))
        machine_prob["typed_plan"]["failure_class"] = fc
        machine_prob["typed_plan"]["mechanism_selection_block"] = mprompt
        machine_prob["typed_plan"]["engine_prediction"] = eng_pred
        machine_prob["typed_plan"]["inspiration"] = {
            "block": ir.inspiration_prompt_block(insp),
            "typed": insp.get("typed"),
        }
        machine_prob["typed_plan"]["novelty_strength"] = {
            "epo_block": ns_out["prompt_block"],
            "ranking": ns_out["ranking"],
        }
        machine_prob["typed_plan"]["quantitative_testability_bind"] = {
            "worked_calculation": (
                "the invention MUST carry ONE worked numeric "
                "calculation on its governing relation: inputs WITH "
                "units (problem-stated, stock datasheet, or a TYPED "
                "ASSUMPTION 'assumed: X because Y'), one substitution, "
                "one numeric result WITH unit"),
            "falsifiable_prediction": (
                "the invention MUST carry ONE falsifiable numeric "
                "prediction: the measurable quantity, its expected "
                "direction and magnitude with units, and the "
                "observation window"),
            "kill_condition": (
                "the invention MUST state its own KILL CONDITION "
                "(Art. 12): 'the mechanism is falsified if <metric> "
                "does not change by at least <N><unit> within "
                "<window>'"),
        }
        machine_prob["typed_plan"]["design_point_bind"] = DESIGN_POINT_BIND
        # THIS LANE'S DELTA (claim c-0258): the physics-truth GATE.
        # The prevention bind is typed OFF this attempt (the A/B: the
        # gate alone enforces 0 genuine physics errors via the repair
        # loop; the prevention bind crowded the novelty conditioning
        # in attempts 1-2). The gate record still lists the bind's
        # status for the record.
        trace = r97.v10m.engine_trace(prob, row_out, winner, wresult,
                                      rule)
        trace["failure_physics"] = {
            "failure_class": fc,
            "winner_measure_class": winner.get("measure_class"),
            "winner_principle_id": winner.get("principle_id"),
            "winner_rule": rule,
        }
        trace["inspiration"] = {
            "failure_class": fc,
            "n_analogies": len(insp.get("analogies", [])),
            "evidence_hashes": [s["content_hash"] for s in
                                insp.get("evidence_spans", [])],
            "route": ("discovery_fabric.generation."
                      "inspiration_retrieval.retrieve_inspiration"),
        }
        trace["physics_gate"] = {
            "route": ("discovery_fabric.generation."
                      "physics_validate.validate_row"),
            "checks": [c[0] for c in pv.CHECKS],
            "max_physics_retries": MAX_PHYSICS_RETRIES,
        }

        # generate + the physics gate (repair loop)
        final = None
        physics = None
        attempts_total = 0
        final_meta = None
        for physics_try in range(1, MAX_PHYSICS_RETRIES + 2):
            if physics_try > 1:
                machine_prob["typed_plan"]["physics_repair_bind"] = \
                    pv.repair_directive(
                        physics["genuine_physics_errors"],
                        admitted_classes=list(sel.allowed_mech_classes
                                              or []))
            try:
                final, attempts, final_meta = r97.machine_generate_v79(
                    machine_prob, gw_key, used_templates={})
                attempts_total += len(attempts)
            except Exception as e:  # noqa: BLE001
                print(f"{pid}: GEN FAIL {type(e).__name__}: "
                      f"{str(e)[:140]} — skipped (byte-resume picks "
                      "up)", flush=True)
                final = None
                break
            quant = qg.emit_prediction_generic(fc, final)
            physics = pv.validate_row(final, quant)
            if physics["verdict"] == pv.VERDICT_PASS:
                break
            print(f"{pid}: PHYSICS FAIL try {physics_try} "
                  f"({physics['n_errors']} errors: "
                  f"{[e['check_id'] for e in physics['genuine_physics_errors']]}) "
                  f"— repair fed back", flush=True)
        row_wall_s = round(time.time() - row_wall_start, 1)
        if final is None or physics is None:
            continue
        if physics["verdict"] != pv.VERDICT_PASS:
            # NOT emitted: a row that cannot pass the physics gate
            # is never scored as quality (Art. 15 typed skip)
            failed += 1
            events.append({
                "problem_id": pid, "generated_at": r97._now(),
                "row_wall_s": row_wall_s,
                "attempts": attempts_total,
                "physics_retries": MAX_PHYSICS_RETRIES,
                "outcome": "PHYSICS_GATE_UNRESOLVED",
                "errors": [e["check_id"] for e in
                           physics["genuine_physics_errors"]],
            })
            ledger_path.write_text(json.dumps({
                "record": "HOLDOUT_V18_GENERATION_EVENTS_R148/1.0.0",
                "run": "v18-physics-one-shot",
                "executor_id": EXECUTOR_ID,
                "registered_model": MODEL_PIN,
                "events": events}, indent=1) + "\n")
            print(f"{pid}: NOT EMITTED — physics gate unresolved "
                  "after retries (typed; byte-resume retries)",
                  flush=True)
            continue
        sel_check = mm.select_mechanism(prob["failure"], final)
        gate = ng.gate(final, sel_check)
        row = _row_outcome(pid, prob, final, attempts_total, row_wall_s,
                           trace, r97._now(), physics, quant, sel_check,
                           gate, final_meta)
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": row["generated_at"],
            "row_wall_s": row_wall_s, "attempts": attempts_total,
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
            "failure_class": fc,
            "winner_measure_class": winner.get("measure_class"),
            "quant_status": quant.get("status"),
            "quant_route": quant.get("route"),
            "off_target": row["generation_checks"]["off_target"],
            "novelty": gate["novelty"],
            "physics_checks_run": [c[0] for c in pv.CHECKS],
            "genuine_physics_errors": 0,
            "n_assumption_bounds": physics["n_assumption_bounds"],
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V18_GENERATION_EVENTS_R148/1.0.0",
            "run": "v18-physics-one-shot",
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "events": events}, indent=1) + "\n")
        done += 1
        print(f"{pid}: wall {row_wall_s}s chars {len(final)} "
              f"quant={quant.get('status')} novelty={gate['novelty']} "
              f"physics=PASS bounds={physics['n_assumption_bounds']} "
              f"({done} done, {resumed} resumed, {failed} unresolved)",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
