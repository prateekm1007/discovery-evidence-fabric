"""discovery_fabric/engine/engine_route.py — the INTEGRATED candidate
path (ROADMAP P1.3, claim c-0069, the F63 remedy).

This is the wiring the roadmap names:

    knowledge_first_item (anchor) -> typed plan (population_search)
      -> mechanism_space.assemble_candidate (1.0.0 core)
      -> candidate_schema.extend_to_1_1 (the four enums FROM THE PLAN)
      -> candidate_schema.validate_candidate_schema (schema findings)
      -> physics_checks.run_check (computed physics, sign-of-result
         direction) for every check whose inputs are supplied
      -> the assembled record carries the trace

The measured DEV path runs THROUGH the engine — not a script harness
(F63: R47-cont 0%, R50 6.6%, R51 24.8% engine lines; this module plus
the migrated population/novelty/TRIZ modules are the correction).

Honesty boundaries (typed, not prose):
- fields come from the problem-statement anchor plus a DETERMINISTIC
  plan-conditioned template marked call_provenance =
  route_template/deterministic — the LLM expansion of the chosen plan
  remains the machine's job (the matched-budget ablation swaps the
  template for the machine call; the wiring is identical).
- physics checks run ONLY on caller-supplied inputs; checks whose
  inputs are absent are recorded PENDING_INPUTS — a missing number
  never becomes a fabricated result (Art. XXV).
- mechanism_class is schema-sourced from the plan (the plan's measure
  class family), replacing the prose "MECHANISM CLASS:" parse on this
  path (the F57/F58 retirement bridge).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import mechanism_space as ms
from . import population_search as ps
from . import candidate_schema as cs
from . import physics_checks as pc

ROUTE_SCHEMA = "engine_route/1.0.0"


def _route_fields(problem: Dict[str, Any],
                  plan: Dict[str, Any]) -> Dict[str, str]:
    """Deterministic plan-conditioned fields from the problem's own
    statement (no generated claims — the template names the plan's
    measured intervention shape and the problem's stated failure)."""
    sig = ", ".join(plan.get("signals_used") or ["none"])
    return {
        "system": str(problem.get("device") or ""),
        "mechanism": str(problem.get("failure") or ""),
        "intervention": (
            f"apply a {plan['measure_class']}-class intervention "
            f"(operator {plan['operator_id']}, TRIZ "
            f"{plan['principle_id']}) on "
            f"{problem.get('device') or 'the system'}"),
        "observed_effect": str(problem.get("failure_mode") or ""),
        "boundary_conditions": str(problem.get("constraint") or ""),
        "failure_mode": str(problem.get("failure_mode") or ""),
        "predicted_effect": (
            f"the {plan['measure_class']} intervention changes the "
            f"failure rate; direction is the SIGN of the computed "
            f"physics result over signals [{sig}]"),
        "testable_prediction": (
            f"measure [{sig}] before and after the "
            f"{plan['measure_class']} intervention; the computed "
            "physics check for the failure class must move in the "
            "sign the check reports"),
        "known_failure_modes": str(problem.get("failure_mode") or ""),
        "novel_design_variable": (
            f"{plan['measure_class']} schedule/geometry variable per "
            f"TRIZ {plan['principle_id']}"),
        "mechanism_source_span": "problem statement (route anchor)",
    }


def run_integrated_candidate(problem: Dict[str, Any],
                             plan: Dict[str, Any],
                             physics_inputs: Optional[Dict[str,
                                                           Dict[str,
                                                                Any]]] = None,
                             ) -> Dict[str, Any]:
    """One plan through the full integrated path. Returns the 1.1.0
    candidate plus its schema findings, computed physics results and
    the route trace. Validation failures are recorded states, never
    silent drops (the machine convention)."""
    item = ps.anchor_item(problem)
    ops = {op["operator_id"]: op for op in ms.TRANSFORMATION_OPERATORS}
    operator = ops[plan["operator_id"]]
    fields = _route_fields(problem, plan)
    cand = ms.assemble_candidate(operator, item, fields, problem,
                                 llm_meta={
                                     "provider": "route_template",
                                     "model": "deterministic",
                                     "prompt_hash": None,
                                     "output_hash": None,
                                     "call_provenance": {
                                         "kind": "route_template",
                                         "note": "the LLM expansion of "
                                                 "the chosen plan is the "
                                                 "machine's job; this "
                                                 "call proves the WIRING "
                                                 "on deterministic "
                                                 "inputs"},
                                 })
    cand11 = cs.extend_to_1_1(
        cand, problem,
        measure_class=plan["measure_class"],
        signals_used=plan["signals_used"],
        principle_id=plan["principle_id"],
        mechanism_class=plan["measure_class"])
    findings = cs.validate_candidate_schema(cand11, problem)
    # physics: run every applicable check the caller supplied inputs
    # for; record the rest PENDING_INPUTS (never fabricated)
    applicable = pc.check_for_failure_class(
        str(problem.get("failure_class") or problem.get("failure") or ""))
    physics_results = []
    for check_id in applicable:
        kwargs = (physics_inputs or {}).get(check_id)
        if kwargs:
            physics_results.append(pc.run_check(check_id, **kwargs))
        else:
            physics_results.append({
                "check_id": check_id, "failure_class":
                    str(problem.get("failure_class") or ""),
                "verdict": "PENDING_INPUTS", "value": None,
                "unit": "dimensionless",
                "direction_of_effect": "unavailable",
                "detail": {"reason": "no caller-supplied numeric "
                                     "inputs — the route records the "
                                     "gap instead of fabricating a "
                                     "result"}})
    return {
        "route_schema": ROUTE_SCHEMA,
        "candidate": cand11,
        "schema_findings": findings,
        "physics": physics_results,
        "trace": {
            "operator_id": plan["operator_id"],
            "measure_class": plan["measure_class"],
            "principle_id": plan["principle_id"],
            "candidate_schema": "mechanism_candidate/1.1.0",
            "candidate_hash_1_0_0": cand.get("candidate_hash"),
            "candidate_state": cand.get("candidate_state"),
        },
    }


def run_row(problem: Dict[str, Any],
            physics_inputs: Optional[Dict[str, Dict[str, Any]]] = None,
            ) -> Dict[str, Any]:
    """All legal plans for one problem through the integrated path,
    then the novelty gate over the row (the F54 near-duplicate kill).
    Returns per-plan results plus the gate verdicts."""
    plans = ps.enumerate_plans(problem)
    results = [run_integrated_candidate(problem, p, physics_inputs)
               for p in plans]
    gate_in = [{"candidate_id": r["candidate"]["candidate_id"],
                "text": " ".join([
                    r["candidate"].get("mechanism", ""),
                    r["candidate"].get("intervention", ""),
                    r["candidate"].get("testable_prediction", "")])}
               for r in results]
    from . import novelty_gate as ng
    return {"problem_id": problem.get("problem_id"),
            "plans": plans, "results": results,
            "novelty_gate": ng.gate_row(gate_in)}
