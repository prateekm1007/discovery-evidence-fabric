#!/usr/bin/env python3
"""r149s1 v18 physics-truth SEALED one-shot — the OWNER'S DIR-2 TOP
order (claim c-0260, the c-0258 supersession typed).

DISCIPLINE: same sealed problems (digest verified per row, Art. 18),
same engine kit as the r146 strengthened one-shot (one source of truth
— the engine modules), agnes-3.0-flash pinned, problem-only,
byte-resume per row. THIS IS A NEW EXPERIMENT on the sealed problems
(the engine state changed: the physics-truth gate is new), not a
re-roll of v17 (Art. 7): the v17 rows stand as the evidence base; the
6 verified error rows are the regression cases the gate must clear.

THE R149 LEVER (the DIR-2 physics-truth gate,
discovery_fabric/generation/physics_truth.py):
  BEFORE emission: the CONDITIONING_BLOCK rides the typed plan (the
  six physics rules the generator must obey).
  AFTER the machine call: physics_truth_gate runs on the DELIVERED
  answer (8 deterministic checks: sign x3, mechanism-at-scale,
  unit-labels, formula dimensions, own-input magnitude recompute,
  assumption bounds). On FAIL: ONE typed regeneration demand quoting
  the failing checks and the physics reason; the retry is accepted on
  strict improvement (fewer failing physics checks; the physics gate
  is the binding contract per the owner). Every attempt committed raw
  (Art. 18/22); the full gate verdicts ride the row.

The quant generation-time contract (r146) rides unchanged; on a retry
the demand block carries BOTH the design-point demand and the
physics-truth demand (one retry total — the r146 single-demand
precedent).

Accept (the owner's DIR 2): 0 genuine physics errors on the 6
regression cases; v18 generation bytes landed; recompute diff=0.
The scoring is the AUDITOR's act (Art. 10/14); the panel arbitration
stays the c-0259 lane's scope (DIR 7).
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
from discovery_fabric.generation import novelty_strength as ns  # noqa: E402
from discovery_fabric.generation import physics_truth as pt  # noqa: E402

OUT = REPO / "eval" / "holdout_v18_physics_generation"
OUT.mkdir(exist_ok=True)
EXECUTOR_ID = os.environ.get("R149_EXECUTOR", "builder-r147s1-physics-lane")
MODEL_PIN = "agnes-3.0-flash"
MACHINE_RECORD = "v12 machine (r97) + the strength kit + the r149 physics-truth gate"

AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
PROBLEMS_AUDIT_PATH = "eval/holdout_v17/problems.json"

# the 6 regression problem ids (the verified error rows)
REGRESSION_PREFIXES = ("v17-11", "v17-14", "v17-15", "v17-17", "v17-28", "v17-29")


def load_sealed_problems():
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
            "contamination_tag": "V18_SEALED",
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


def _sha16_local(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode()).hexdigest()[:16]


def quant_contract_state(failure_class: str, answer: str) -> dict:
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
    gq = state.get("generic_quant") or {}
    lines = [
        "DESIGN-POINT DEMAND (the quantitative contract, second and "
        "FINAL attempt): your previous answer did not carry a RUNNABLE "
        "design point.",
    ]
    if not state.get("computed"):
        lines.append(
            "The unit-checked compute could not run on your text: "
            f"status={gq.get('status')!r}.")
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
    # the r97 gateway pre-gates + lifecycle (the measured-path
    # discipline, Art. 22 v3.2.0): the registered route serves, a stale
    # gateway refuses, the AGNES key must be in custody, the gateway
    # runs for the whole pass
    try:
        r97.route_adapter.require_registered_model(r97.V12_REQUEST_MODEL)
    except Exception as e:  # noqa: BLE001 — RouteRefused and drift
        print(f"MEASURED-PATH REFUSAL (typed, Art. 22 v3.2.0): {e}",
              flush=True)
        return 3
    if r97._gateway_alive():
        print("REFUSED (typed, exit 3): a gateway is already "
              "listening on 127.0.0.1:8787 — kill it first.", flush=True)
        return 3
    if r97.route_adapter.resolve_vault_key("AGNES_API_KEY") is None:
        print("REFUSED (typed INFRA_CREDENTIAL_MISSING, exit 3): "
              "AGNES_API_KEY absent from the vault (.env.keys).",
              flush=True)
        return 3
    os.environ["ZAI_GATEWAY_UPSTREAM"] = r97.GATEWAY_UPSTREAM
    os.environ["AGNES_MODEL_ID"] = r97.V12_REQUEST_MODEL
    gw, gw_key = m77.start_gateway()
    print(f"gateway healthy (upstream={r97.GATEWAY_UPSTREAM}, "
          f"registered route {r97.V12_REQUEST_MODEL})", flush=True)
    try:
        return _run_body(gw_key)
    finally:
        try:
            gw.terminate()
            gw.wait(timeout=10)
        except Exception:  # noqa: BLE001 — typed teardown
            gw.kill()


def _run_body(gw_key: str) -> int:
    probs, sealed_digest16 = load_sealed_problems()
    print(f"v18 PHYSICS-TRUTH SEALED: {len(probs)} problems | digest "
          f"{sealed_digest16} | model pin {MODEL_PIN} | the r149 "
          f"lever (the physics gate demanded at generation time)",
          flush=True)
    events = []
    ledger_path = OUT / "GENERATION_EVENTS.json"
    if ledger_path.exists():
        events = json.loads(ledger_path.read_text()).get("events", [])
    done = skipped = gate_fired = gate_fixed = 0
    t0 = time.time()
    for idx, prob in enumerate(sorted(probs,
                                      key=lambda p: p["problem_id"]), 1):
        pid = prob["problem_id"]
        outp = OUT / f"{pid}.json"
        if outp.exists():  # byte-resume, same generation
            skipped += 1
            continue
        row_wall_start = time.time()
        is_regression = pid.startswith(REGRESSION_PREFIXES)
        print(f"=== v18 {pid} ({idx}/30)"
              f"{' [REGRESSION]' if is_regression else ''} ...", flush=True)
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
        # THE R149 LEVER: the physics-truth conditioning BEFORE emission
        machine_prob["typed_plan"]["physics_truth_bind"] = (
            pt.CONDITIONING_BLOCK)
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
        trace["r149_lever"] = {
            "physics_truth_conditioning": True,
            "physics_checks_n": len(pt.CHECKS),
            "regression_case": is_regression,
        }
        t_row = r97._now()
        final, attempts, final_meta = r97.machine_generate_v79(
            machine_prob, gw_key, used_templates={})

        # THE R149 LEVER: the physics gate on the delivered answer
        gate = pt.physics_truth_gate(final, problem_text)
        contract = quant_contract_state(sel.failure_class, final)
        demand = None
        if gate["verdict"] == "FAIL" or not contract["satisfied"]:
            gate_fired += 1
            demand = {
                "fired": True,
                "gate_first": gate["verdict"],
                "failing_first": gate["failing"],
                "quant_first_computed": contract["computed"],
            }
            parts = []
            if gate["verdict"] == "FAIL":
                parts.append(pt.build_regen_demand(gate))
            if not contract["satisfied"]:
                parts.append(build_demand_block(contract))
            machine_prob["typed_plan"]["regen_demand"] = "\n\n".join(parts)
            final2, attempts2, final_meta2 = r97.machine_generate_v79(
                machine_prob, gw_key, used_templates={})
            attempts = attempts + attempts2
            gate2 = pt.physics_truth_gate(final2, problem_text)
            contract2 = quant_contract_state(sel.failure_class, final2)
            improved = (len(gate2.get("failing") or [])
                        < len(gate.get("failing") or [])
                        or (gate["verdict"] == "FAIL"
                            and gate2["verdict"] == "PASS"))
            if gate2["verdict"] == "PASS" or improved:
                gate_fixed += 1
                demand.update({
                    "gate_retry": gate2["verdict"],
                    "failing_retry": gate2["failing"],
                    "retry_accepted": True,
                    "acceptance_rule": (
                        "strict improvement (fewer failing physics "
                        "checks); the physics gate is the binding "
                        "contract")})
                final, final_meta = final2, final_meta2
                gate, contract = gate2, contract2
            else:
                demand.update({
                    "gate_retry": gate2["verdict"],
                    "failing_retry": gate2["failing"],
                    "retry_accepted": False,
                    "typed_residual": (
                        "the retry did not improve the physics gate — "
                        "the row stands with the honest finding (never "
                        "an invented number, Art. 9)")})
        mapped_mech = eng_pred.get("mech_class") or (
            sel.allowed_mech_classes[0] if sel.allowed_mech_classes
            else "")
        ngate = ng.gate(final, mm.MechanismSelection(
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
            "run": "holdout-v18-physics-generation (the SEALED "
                   "physics-truth one-shot: the r149 lever — the gate "
                   "demanded at generation time, ONE typed regeneration "
                   "on fail)",
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
                "novelty_gate": ngate,
                "physics_gate": gate,
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
            "physics_gate": gate["verdict"],
            "physics_failing": gate.get("failing") or [],
            "regression_case": is_regression,
            "regen_fired": bool(demand and demand.get("fired")),
            "regen_fixed": bool(demand and demand.get("retry_accepted")),
            "quant_final_computed": contract["computed"],
        })
        (OUT / "GENERATION_EVENTS.json").write_text(
            json.dumps({"record": "V18_GENERATION_EVENTS/1.0.0",
                        "events": events}, indent=1) + "\n",
            encoding="utf-8")
        done += 1
        print(f"    gate={gate['verdict']} failing={gate.get('failing')}"
              f" wall={row_wall_s}s chars={len(final)}", flush=True)
    print(f"DONE: {done} generated, {skipped} byte-resumed | "
          f"gate-demand fired {gate_fired}, fixed {gate_fixed} | "
          f"wall {round(time.time() - t0)}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
