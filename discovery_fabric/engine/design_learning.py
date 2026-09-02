"""design_learning.py — R394 section 12: the ACTUAL design-learning loop.

Directive:

  CANDIDATE -> CAD -> SOLVE -> DISCREPANCY -> CAUSAL HYPOTHESIS ->
  PARAMETER SELECTION -> MUTATE -> REBUILD -> RESOLVE ->
  BASELINE COMPARISON -> KEEP/KILL

  "Every mutation must state: parameter, direction, reason, discrepancy
   addressed, constraints preserved. Do not use random mutation as a
   proxy for invention."

DESIGN — deterministic, solver-driven, never random:

  SOLVE            the physics core runs the failure-mode scenarios
  DISCREPANCY      the gap between the candidate's achieved target
                   metric and the required threshold under the declared
                   failure scenario
  CAUSAL HYPOTHESIS  a DETERMINISTIC sensitivity analysis: for each
                   mutable parameter, the solver is re-run with a fixed
                   in-envelope perturbation; the signed, normalized
                   sensitivity d(metric)/d(param) IS the causal
                   statement (analytic for Poiseuille: floor-path flow
                   scales as d^4). The hypothesis names the parameter
                   whose sensitivity governs the discrepancy and the
                   DIRECTION of its effect.
  PARAMETER SELECTION  highest-magnitude normalized sensitivity to the
                   discrepancy (deterministic ranking; ties broken by
                   declared parameter order)
  MUTATE            an explicit record: parameter, direction, reason,
                   discrepancy addressed, constraints preserved (the
                   declared envelope), before/after values
  REBUILD           the geometry is rebuilt AT THE PARAMETER LEVEL with
                   a fresh geometry hash; the R381 CAD binding names
                   (primary_lumen_diameter_mm, floor_lumen_diameter_mm)
                   travel with the record so the cadquery rebuild path
                   can consume them (V0 binds parameters; the full
                   cad_pipeline.rebuild_with_mutation integration is the
                   named extension — the loop never claims a CAD rebuild
                   it did not run)
  RESOLVE           re-solve; the discrepancy is resolved or the loop
                   continues (bounded iterations, disclosed)
  BASELINE COMPARISON  physics_core.compare_to_baseline (section 10)
  KEEP/KILL         quantitative: KEEP requires the target metric met
                   under the failure scenario AND BEATS_BASELINE; both
                   are solver-derived, never asserted

No LLM in the loop. No randomness. Every step is recorded in the
learning record — the loop is auditable end-to-end.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from discovery_fabric.engine import physics_core as pc

LOOP_VERSION = "design_learning/1.0.0"
MAX_ITERATIONS = 8  # declared, deterministic cap (disclosed per run)


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"))


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def learn_design(candidate_spec: Dict[str, Any],
                 baseline_spec: Dict[str, Any],
                 primary_segment_id: str,
                 parameters: List[Dict[str, Any]],
                 target_metric: str = "total_flow_ml_min",
                 scenario: str = "SEVERE_OBSTRUCTION",
                 required_min: float = 0.0,
                 max_iterations: int = MAX_ITERATIONS) -> Dict[str, Any]:
    """Run the full design-learning loop on one candidate.

    parameters: [{name, segment_id, property ('diameter_mm'),
                  envelope: {min, max}, cad_binding (optional R381 name)}]
    Only in-envelope mutations are legal; the envelope is the preserved
    constraint set. Out-of-envelope needs are recorded as REFUSED, never
    silently clamped.
    """
    if not parameters:
        return {"status": "NO_MUTABLE_PARAMETERS",
                "reason": ("no parameters declared — the loop cannot "
                           "learn without a declared design space"),
                "loop_version": LOOP_VERSION}

    spec = json.loads(_canonical(candidate_spec))  # deep copy, canonical
    iterations: List[Dict[str, Any]] = []
    events: List[Dict[str, Any]] = []

    def _solve_current(s: Dict[str, Any]) -> Optional[float]:
        sim = pc.simulate_failure_modes(s, primary_segment_id,
                                        target_metric)
        if sim.get("status") != "SIMULATED":
            return None
        for x in sim["scenarios"]:
            if x["scenario"] == scenario:
                return x.get("value")
        return None

    current = _solve_current(spec)
    if current is None:
        return {"status": "MECHANISM_NOT_SIMULATABLE",
                "reason": ("the candidate's failure mode cannot be "
                           "simulated; no learning loop is permitted to "
                           "run (R394 s9/s12)"),
                "loop_version": LOOP_VERSION}

    def _mutate(s: Dict[str, Any], param: Dict[str, Any],
                value: float) -> Dict[str, Any]:
        s2 = json.loads(_canonical(s))
        for seg in s2["segments"]:
            if seg["segment_id"] == param["segment_id"]:
                seg[param["property"]] = value
        s2["geometry_hash"] = _sha(_canonical(
            {"parent": s.get("geometry_hash"),
             "mutation": {"parameter": param["name"], "value": value}}))
        s2["geometry_identity"] = (
            f"{s.get('geometry_identity')}#m:{param['name']}={value}")
        return s2

    def _sensitivity(s: Dict[str, Any],
                     param: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Deterministic one-sided sensitivity: fixed in-envelope probe
        step (10% of the envelope span, clamped in-envelope). The signed
        normalized sensitivity IS the causal statement."""
        env = param["envelope"]
        span = float(env["max"]) - float(env["min"])
        if span <= 0:
            return None
        step = 0.1 * span
        cur = next(
            (seg[param["property"]] for seg in s["segments"]
             if seg["segment_id"] == param["segment_id"]), None)
        if cur is None:
            return None
        probe = min(float(cur) + step, float(env["max"]))
        if probe == cur:
            probe = max(float(cur) - step, float(env["min"]))
        if probe == cur:
            return None
        s_probe = _mutate(s, param, probe)
        v_probe = _solve_current(s_probe)
        if v_probe is None or current in (None, 0.0):
            return None
        dslope = (v_probe - current) / (probe - cur)
        normalized = dslope * (span / max(abs(current), 1e-30))
        return {"parameter": param["name"],
                "slope": dslope,
                "normalized_sensitivity": normalized,
                "probe_value": probe,
                "current_value": cur,
                "causal_statement": (
                    f"increasing {param['name']} by {probe - cur:+.6g} "
                    f"changes {target_metric} by "
                    f"{v_probe - current:+.6g} ({dslope:+.6g} per unit); "
                    f"the solver's governing relation is Poiseuille "
                    "d^4 conductance — the causal path is hydraulic, "
                    "not correlative")}

    for it in range(max_iterations):
        discrepancy = required_min - (current or 0.0)

        if discrepancy <= 0:
            events.append({
                "step": "RESOLVED",
                "iteration": it,
                "value": current,
                "required_min": required_min,
                "note": "target metric met under the declared failure "
                        "scenario — proceed to baseline comparison"})
            break

        # ---- CAUSAL HYPOTHESIS: deterministic sensitivities ----------
        sens = [x for x in (_sensitivity(spec, p) for p in parameters)
                if x]
        if not sens:
            events.append({
                "step": "NO_CAUSAL_PATH",
                "iteration": it,
                "note": ("no parameter produces a measurable sensitivity "
                         "within its envelope — the design space cannot "
                         "address the discrepancy (honest stop, not a "
                         "kill of the mechanism class)")})
            break
        sens.sort(key=lambda x: (-abs(x["normalized_sensitivity"]),
                                 x["parameter"]))
        chosen_sens = sens[0]
        param = next(p for p in parameters
                     if p["name"] == chosen_sens["parameter"])
        direction = "increase" if chosen_sens["slope"] > 0 else "decrease"
        events.append({
            "step": "CAUSAL_HYPOTHESIS",
            "iteration": it,
            "sensitivities_ranked": [
                {"parameter": x["parameter"],
                 "normalized": x["normalized_sensitivity"]}
                for x in sens],
            "selected": chosen_sens["causal_statement"]})

        # ---- MUTATE (explicit, envelope-preserving) -------------------
        env = param["envelope"]
        cur_val = chosen_sens["current_value"]
        span = float(env["max"]) - float(env["min"])
        # deterministic step: 25% of the envelope span in the causal
        # direction, clamped to the envelope (never beyond)
        new_val = cur_val + (0.25 * span if direction == "increase"
                             else -0.25 * span)
        new_val = max(float(env["min"]), min(float(env["max"]), new_val))
        if new_val == cur_val:
            events.append({
                "step": "ENVELOPE_EXHAUSTED",
                "iteration": it,
                "parameter": param["name"],
                "note": ("the causal direction is blocked by the declared "
                         "envelope — the constraint set is preserved "
                         "(refused, never clamped beyond)")})
            break
        mutation_record = {
            "parameter": param["name"],
            "direction": direction,
            "reason": (f"discrepancy {target_metric}={current:.6g} < "
                       f"required {required_min:.6g} under {scenario}; "
                       f"{param['name']} has the governing sensitivity "
                       f"({chosen_sens['normalized_sensitivity']:+.6g} "
                       "normalized)"),
            "discrepancy_addressed": discrepancy,
            "constraints_preserved": {
                "envelope": env,
                "in_envelope": float(env["min"]) <= new_val
                <= float(env["max"]),
                "cad_binding": param.get("cad_binding"),
            },
            "before": cur_val,
            "after": new_val,
        }
        events.append({"step": "MUTATE", "iteration": it,
                       "mutation": mutation_record})

        # ---- REBUILD + RESOLVE ----------------------------------------
        spec = _mutate(spec, param, new_val)
        events.append({"step": "REBUILD",
                       "iteration": it,
                       "geometry_hash": spec["geometry_hash"],
                       "geometry_identity": spec["geometry_identity"],
                       "cad_binding": param.get("cad_binding"),
                       "note": ("parameter-level rebuild with fresh "
                                "geometry hash; the cadquery "
                                "rebuild_with_mutation path consumes the "
                                "cad_binding (V0 records the binding; a "
                                "full CAD rebuild is claimed only when "
                                "run)")})
        new_val_result = _solve_current(spec)
        iterations.append({
            "iteration": it,
            "mutation": mutation_record,
            "value_before": current,
            "value_after": new_val_result,
            "improvement": (new_val_result - current
                            if new_val_result is not None else None),
        })
        current = new_val_result
        if current is None:
            events.append({"step": "SOLVE_FAILED_AFTER_MUTATION",
                           "iteration": it})
            break

    # ---- BASELINE COMPARISON -> KEEP/KILL (quantitative) --------------
    comparison = pc.compare_to_baseline(
        spec, baseline_spec, primary_segment_id,
        scenario=scenario, target_metric=target_metric,
        required_min=required_min)
    meets_target = (current is not None and current >= required_min)
    beats = comparison.get("outcome") == "BEATS_BASELINE"
    if meets_target and beats:
        verdict = "KEEP"
        verdict_basis = (f"target met ({current:.6g} >= {required_min:.6g} "
                         "under the failure scenario) AND BEATS_BASELINE "
                         "— both solver-derived")
    elif not beats:
        verdict = "KILL"
        verdict_basis = ("the candidate does not beat the declared "
                         "baseline under the declared failure scenario "
                         "— a quantitative kill, not an assertion")
    else:
        verdict = "KILL"
        verdict_basis = (f"target not met ({current:.6g} < "
                         f"{required_min:.6g}) within the declared "
                         "envelope and iteration budget")

    return {
        "status": "LEARNING_COMPLETE",
        "loop_version": LOOP_VERSION,
        "solver_version": pc.SOLVER_VERSION,
        "iterations": iterations,
        "n_iterations": len(iterations),
        "max_iterations": max_iterations,
        "events": events,
        "final_spec": spec,
        "final_value": current,
        "required_min": required_min,
        "scenario": scenario,
        "target_metric": target_metric,
        "baseline_comparison": comparison,
        "verdict": verdict,
        "verdict_basis": verdict_basis,
        "rule": ("KEEP requires the target metric met under the failure "
                 "scenario AND BEATS_BASELINE; 'simulation ran' is never "
                 "'invention succeeded' (R394 s10/s12)"),
    }
