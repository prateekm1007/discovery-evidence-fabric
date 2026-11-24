#!/usr/bin/env python3
"""r146s1 v17 strengthened SEALED one-shot — DIR-2 (TOP) + DIR-3 + the
DIR-6 integration vehicle.

DISCIPLINE (typed): the delegated owner SEALED v17 (the prereg
V17_SEALED_PREREG/1.0.0, rubrics PRIVATE in
prateekm1007/def-rubric-custody:v17_sealed_rubrics.json, digest
1db1539e935038db, NEVER read by the builder). The r145 sealed one-shot
(eval/holdout_v17_sealed_generation/) is the BASELINE — committed,
never deleted (Art. 4). THIS run is the STRENGTHENED-ENGINE one-shot:
the engine state changed (the R146 levers below), so this is a NEW
experiment on the sealed problems, not a re-roll of the same one (Art.
7): the baseline + this run both stand; the auditor scores both; the
owner's direction demands exactly this ("a fresh sealed one-shot").

THE R146 LEVERS (both deterministic prompt conditioning, zero LLM in
the levers themselves):
  A. NOVELTY STRENGTH (DIR 2 + DIR 6): generation.novelty_strength —
     the EPO problem-solution conditioning (closest conventional
     practice -> distinguishing features -> objective technical
     problem -> mechanism, with the routine-parameter-change rejection
     clause) + the MOOSE-Chem hypothesis ranking (the allowed
     mechanism classes ordered by cross-domain transfer distance, the
     conventional-response class demoted last — the inspiration lever
     is now a RANKING decision, not just prompt context: the DIR-6
     integration).
  B. THE QUANT GENERATION-TIME CONTRACT (DIR 3): the runner DEMANDS
     the design point at generation — after the machine call, the
     runner runs the generic-quant compute + the machine scan on the
     DELIVERED answer; when the compute does not find a runnable
     design point (status != computed) or the scan flags
     QUANT_TEST_MISSING, the runner fires ONE typed regeneration
     demand (the missing element quoted; the design point required:
     a running unit-checked calculation on the problem's own numbers
     or TYPED assumptions; invented numbers forbidden), then re-runs
     the compute. Every attempt committed raw; the final row records
     the demand loop state. No invented numbers: the compute only
     ever reads the answer's OWN text.

The rest of the strength kit (mechanism_map constraint block, engine
prediction manifest, inspiration block, the binds, the scans) rides
exactly as in the r145 baseline (one source of truth — the engine
modules).

agnes-3.0-flash pinned; problem-only; byte-resume per row; the raw
rows + the demand-loop attempts commit with the run (Art. 18/22). The
scoring is the AUDITOR's act (PENDING-AUDITOR-SCORE, Art. 10/14).
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
from discovery_fabric.generation import quant_test as qt  # noqa: E402
from discovery_fabric.generation import (  # noqa: E402
    inspiration_retrieval as ir)
from discovery_fabric.generation import novelty_gate as ng  # noqa: E402
from discovery_fabric.generation import (  # noqa: E402
    novelty_strength as ns)

OUT = REPO / "eval" / "holdout_v17_strengthened_generation"
OUT.mkdir(exist_ok=True)
EXECUTOR_ID = os.environ.get(
    "R146_EXECUTOR", "builder-r145s1-strengthened-lane")
MODEL_PIN = "agnes-3.0-flash"
MACHINE_RECORD = r97.MACHINE_RECORD if hasattr(r97, "MACHINE_RECORD") \
    else "v12 machine (r97) + the strength kit"


AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
PROBLEMS_AUDIT_PATH = "eval/holdout_v17/problems.json"


def load_sealed_problems():
    """The SEALED bytes from the audit branch (the twin's loader
    pattern byte-for-byte: git-show the audit tip, digest the probs
    list, map to the engine's problem shape)."""
    import subprocess
    import hashlib
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
            "contamination_tag": "V17_SEALED",
        })
    return mapped, digest16


def _gateway_key() -> str:
    k = os.environ.get("ZAI_API_KEY")
    if not k:
        env_keys = REPO / ".env.keys"
        if env_keys.exists():
            for line in env_keys.read_text().splitlines():
                if line.startswith("ZAI_API_KEY="):
                    k = line.split("=", 1)[1].strip()
                    break
    return k or ""


def quant_contract_state(failure_class: str, answer: str) -> dict:
    """The DIR-3 contract check on the DELIVERED answer: the
    generic-quant compute (which reads ONLY the answer's own text) +
    the machine scan's QUANT_TEST_MISSING. Returns the state the
    demand loop acts on (never inventing a number)."""
    from discovery_fabric.generation.quant_generic import (
        emit_prediction_generic)
    try:
        gq = emit_prediction_generic(failure_class, answer)
    except Exception as e:  # noqa: BLE001 — typed
        gq = {"status": "compute_error",
              "error": f"{type(e).__name__}: {e}"}
    prob = {"question_type": "invention"}
    try:
        from r144_quantitative_testability_scan import (
            scan_quantitative_testability)
        scan = scan_quantitative_testability(prob, answer)
    except Exception as e:  # noqa: BLE001 — typed
        scan = {"scan_error": f"{type(e).__name__}: {e}"}
    computed = gq.get("status") == "computed"
    missing = bool(scan.get("QUANT_TEST_MISSING"))
    return {"generic_quant": gq, "machine_scan": scan,
            "computed": computed, "quant_test_missing": missing,
            "satisfied": computed and not missing}


def build_demand_block(state: dict) -> str:
    """The ONE typed regeneration demand (DIR 3): quotes the missing
    element and requires the design point. The demand rides the
    typed_plan of the retry call; the machine is unchanged."""
    gq = state.get("generic_quant") or {}
    lines = [
        "DESIGN-POINT DEMAND (the quantitative contract, second and "
        "FINAL attempt): your previous answer did not carry a RUNNABLE "
        "design point.",
    ]
    if not state.get("computed"):
        lines.append(
            "The unit-checked compute could not run on your text: "
            f"status={gq.get('status')!r}"
            + (f" ({json.dumps(gq.get('missing') or gq.get('required_inputs') or gq.get('note') or '')[:200]})"
               if not state.get("computed") else "")
            + ".")
    if state.get("quant_test_missing"):
        lines.append(
            "The machine scan flagged QUANT_TEST_MISSING: the "
            "falsification-test section lacks a numeric threshold.")
    lines.append(
        "REDELIVER the SAME invention with the design point made "
        "RUNNABLE: (a) name the governing relation; (b) list every "
        "input WITH its unit and value — use the problem's own "
        "numbers where given; for any input the problem does not "
        "state, give a physically reasonable value marked "
        "'assumed: <value> because <one-line reason>'; (c) show the "
        "one substitution and the numeric result WITH unit; (d) the "
        "falsification test states a numeric threshold with units "
        "(the kill condition). INVENTED UNMARKED NUMBERS ARE "
        "FORBIDDEN — every number must be problem-stated, "
        "assumption-marked, or computed by the shown substitution.")
    return "\n".join(lines)


def main() -> int:
    probs, sealed_digest16 = load_sealed_problems()
    print(f"v17 STRENGTHENED SEALED: {len(probs)} problems | digest "
          f"{sealed_digest16} | model pin {MODEL_PIN} | the R146 "
          f"levers (EPO + ranking + the quant contract)", flush=True)
    events = []
    ledger_path = OUT / "GENERATION_EVENTS.json"
    if ledger_path.exists():
        events = json.loads(
            ledger_path.read_text()).get("events", [])
    done = skipped = demand_fired = demand_satisfied = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(probs,
                                      key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = OUT / f"{pid}.json"
        if outp.exists():  # byte-resume, same generation
            skipped += 1
            continue
        row_wall_start = time.time()
        print(f"=== v17-strengthened {pid} ({idx}/30) ...", flush=True)
        problem_text = prob.get("failure") or prob.get("problem", "")
        sel = mm.classify_failure(problem_text)
        mprompt = mm.mechanism_prompt_block(problem_text)
        import inspect
        eng_pred = {"status": "no_formula_for_class",
                    "note": ("typed: no deterministic formula for the "
                             "mapped classes — the invention carries "
                             "the first-principles estimate")}
        for mech in sel.allowed_mech_classes:
            if mech in qt.FORMULAS:
                fn = qt.FORMULAS[mech]
                required = [pname for pname, prm in
                            inspect.signature(fn).parameters.items()
                            if prm.default is inspect.Parameter.empty]
                eng_pred = {
                    "status": "parameters_required",
                    "mech_class": mech,
                    "formula": getattr(fn, "__name__", str(fn)),
                    "required_inputs": required,
                    "pint_unit_checked": True,
                    "note": ("typed: the deterministic pint-checked "
                             "formula needs these inputs — the "
                             "invention MUST name the measurement "
                             "plan and the estimated values (typed "
                             "assumptions allowed, Art. 9)")}
                break
        insp = ir.retrieve_inspiration(sel.failure_class)
        # THE R146 LEVER A: the EPO conditioning + the hypothesis
        # ranking (the DIR-6 integration: the inspiration lever as a
        # RANKING decision)
        ns_out = ns.novelty_strength_block(
            problem_text, prob.get("domain", ""))
        row_out = r97.engine_route.run_row(prob)
        winner, wresult, rule = r97.v10m.select_winner(row_out)
        machine_prob = r97.v10m.challenger_prob(prob, winner, rule)
        machine_prob["typed_plan"]["failure_class"] = sel.failure_class
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
        machine_prob["typed_plan"]["novelty_strength_bind"] = (
            "the departure from standard practice must be a NON-OBVIOUS "
            "arrangement with a stated physical reason the obvious "
            "knob fails here; the generic moves (increase/reduce flow, "
            "modulate pressure, add monitoring, insulate more, add a "
            "filter or a schedule) are NOT a mechanism when they are "
            "the whole departure — put the novelty in the arrangement")
        trace = r97.v10m.engine_trace(prob, row_out, winner, wresult,
                                      rule)
        trace["strength_kit"] = {
            "failure_class": sel.failure_class,
            "confidence": sel.confidence,
            "evidence_span": sel.evidence_span,
            "allowed_mech_classes": list(sel.allowed_mech_classes),
            "engine_prediction_status": eng_pred.get("status"),
            "engine_prediction_mech_class": eng_pred.get("mech_class"),
            "inspiration_analogies_n": len(insp.get("analogies") or []),
            "inspiration_spans_n": len(insp.get("evidence_spans") or []),
            "winner_measure_class": winner.get("measure_class"),
            "winner_rule": rule,
        }
        trace["r146_levers"] = {
            "epo_conditioning": True,
            "hypothesis_ranking": {
                "n_classes_ranked": len(ns_out["ranking"]["ranked"]),
                "top_class": (ns_out["ranking"]["ranked"] or [{}])[0]
                .get("mech_class"),
                "top_transfer_distance": (ns_out["ranking"]["ranked"]
                                          or [{}])[0]
                .get("transfer_distance"),
                "conventional_first_response":
                    ns_out["ranking"].get(
                        "conventional_first_response"),
            },
            "quant_contract": "generation-time (the demand loop)",
        }
        t_row = r97._now()
        final, attempts, final_meta = r97.machine_generate_v79(
            machine_prob, _gateway_key(), used_templates={})

        # THE R146 LEVER B: the quant generation-time contract — the
        # runner DEMANDS the design point (DIR 3). ONE typed retry.
        contract = quant_contract_state(sel.failure_class, final)
        demand = None
        if not contract["satisfied"]:
            demand_fired += 1
            demand = {"fired": True,
                      "first_state": {
                          "computed": contract["computed"],
                          "quant_test_missing":
                              contract["quant_test_missing"],
                          "generic_status":
                              (contract["generic_quant"] or {})
                          .get("status")}}
            machine_prob["typed_plan"]["design_point_demand"] = (
                build_demand_block(contract))
            final2, attempts2, final_meta2 = r97.machine_generate_v79(
                machine_prob, _gateway_key(), used_templates={})
            attempts = attempts + attempts2
            contract2 = quant_contract_state(sel.failure_class, final2)
            if contract2["satisfied"] or contract2["computed"]:
                demand_satisfied += 1
                demand.update({
                    "retry_computed": contract2["computed"],
                    "retry_quant_test_missing":
                        contract2["quant_test_missing"],
                    "retry_accepted": contract2["satisfied"]})
                final, final_meta = final2, final_meta2
                contract = contract2
            else:
                demand.update({
                    "retry_computed": False,
                    "retry_accepted": False,
                    "typed_residual": (
                        "the retry still lacks a runnable design "
                        "point — the row stands with the honest "
                        "finding (never an invented number, Art. 9)")})
            demand["demand_block_sha16"] = m77.__dict__.get(
                "_unused", "") or _sha16_local(
                machine_prob["typed_plan"]["design_point_demand"])
        mapped_mech = eng_pred.get("mech_class") or (
            sel.allowed_mech_classes[0] if sel.allowed_mech_classes
            else "")
        gate = ng.gate(final, mm.MechanismSelection(
            failure_class=sel.failure_class, confidence=sel.confidence,
            evidence_span=sel.evidence_span,
            allowed_mech_classes=sel.allowed_mech_classes,
            selected_mech_class=mapped_mech,
            root_cause_chain=sel.root_cause_chain,
            cross_domain=(insp.get("analogies") or [{}])[0].get(
                "from_domain", "") if insp.get("analogies") else "",
            notes=sel.notes))
        row_wall_s = round(time.time() - row_wall_start, 1)
        decl = m77.declared_template(final)
        row = {
            "problem_id": pid,
            "domain": prob.get("domain"),
            "question_type": prob.get("question_type"),
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "machine": MACHINE_RECORD,
            "run": "holdout-v17-strengthened-generation (the SEALED "
                   "strengthened one-shot: the R146 levers — the EPO "
                   "conditioning, the hypothesis ranking, the "
                   "quant generation-time contract)",
            "sealed_problems_digest16": sealed_digest16,
            "engine_trace": trace,
            "generated_at": t_row,
            "attempts_n": len(attempts),
            "row_wall_s": row_wall_s,
            "a1_answer": final,
            "final_meta": {
                "critic_verdict": final_meta.get("critic_verdict"),
                "type_gate": final_meta.get("type_gate"),
                "repairs": final_meta.get("repairs"),
                "stop_reason": final_meta.get("stop_reason"),
                "residual_findings": final_meta.get(
                    "residual_findings"),
                "findings_disclosed": final_meta.get(
                    "findings_disclosed"),
                "novelty_gate": gate,
                "quant_contract": {
                    "final_computed": contract["computed"],
                    "final_quant_test_missing":
                        contract["quant_test_missing"],
                    "generic_quant": contract["generic_quant"],
                    "machine_scan": contract["machine_scan"],
                    "demand": demand,
                },
            },
            "declared_template_prose": decl,
            "sha256_16": r97._sha16(final),
        }
        outp.write_text(json.dumps(row, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
        events.append({
            "problem_id": pid, "generated_at": t_row,
            "row_wall_s": row_wall_s, "attempts": len(attempts),
            "final_sha256_16": row["sha256_16"],
            "final_chars": len(final),
            "failure_class": sel.failure_class,
            "engine_prediction_status": eng_pred.get("status"),
            "quant_final_computed": contract["computed"],
            "quant_quant_test_missing": contract["quant_test_missing"],
            "demand_fired": bool(demand),
            "demand_accepted": (demand or {}).get("retry_accepted"),
            "novelty_gate": gate.get("novelty"),
        })
        ledger_path.write_text(json.dumps({
            "record": "HOLDOUT_V17_STRENGTHENED_EVENTS/1.0.0",
            "run": "holdout-v17-strengthened-generation",
            "executor_id": EXECUTOR_ID,
            "registered_model": MODEL_PIN,
            "sealed_problems_digest16": sealed_digest16,
            "events": events}, indent=1) + "\n")
        done += 1
        print(f"{pid}: wall {row_wall_s}s chars {len(final)} "
              f"class={sel.failure_class} "
              f"computed={contract['computed']} "
              f"miss={contract['quant_test_missing']} "
              f"demand={'Y' if demand else 'n'} "
              f"novelty={gate.get('novelty')} "
              f"({done} done, {skipped} resumed)", flush=True)
    print(f"v17 STRENGTHENED generation: {done} generated, {skipped} "
          f"resumed, {round(time.time() - t0, 1)}s wall | the quant "
          f"contract: {demand_fired} demands fired, "
          f"{demand_satisfied} satisfied", flush=True)
    return 0


def _sha16_local(text: str) -> str:
    import hashlib
    return hashlib.sha256((text or "").encode()).hexdigest()[:16]


if __name__ == "__main__":
    raise SystemExit(main())
