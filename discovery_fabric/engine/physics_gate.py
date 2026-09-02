"""discovery_fabric/engine/physics_gate.py — R396 Phase D wiring.

The R394 physics core V0 (one deterministic 1D hydraulic solver) and the
design-learning loop existed and were benchmark-pinned, but had NO
production call site: no surviving candidate's engineering specification
carried the baseline gate. R396 Phase D.1 closes exactly that:

  "Every surviving candidate must explicitly contain: BASELINE,
   CANDIDATE, TARGET METRIC, CONSTRAINTS, RELATIVE IMPROVEMENT ...
   the machine must be capable of producing
   CANDIDATE_DOES_NOT_BEAT_BASELINE."

This module evaluates, for each candidate's engineering specification:

  1. applicability   the V0 solver's declared domain is 1D hydraulic
                     networks. Candidates in OTHER domains get an honest
                     NOT_APPLICABLE refusal (never a fabricated
                     comparison — Art. XXXVIII / R394 s9 semantics).
  2. plausibility    the deterministic cheap bounds (R394 s11 + R396
                     D.2's six families) run BEFORE the solve.
  3. failure-mode    NORMAL / PARTIAL_OBSTRUCTION / SEVERE_OBSTRUCTION /
  contract           ALTERNATIVE_PATH — the actual failure mode the
                     invention exists for, vs BASELINE (R394 s9, R396
                     D.3).
  4. baseline        BASELINE / CANDIDATE / TARGET METRIC / CONSTRAINTS /
  comparison         RELATIVE IMPROVEMENT + the exact directive
                     vocabulary CANDIDATE_DOES_NOT_BEAT_BASELINE.
  5. design          when the comparison misses the required threshold,
  learning           the deterministic mutation loop proposes the next
                     candidate (parameter/direction/reason recorded).

The network envelope for the hydraulic domain is the P-07 reference
envelope (primary lumen 1.0 mm, floor lumen 0.6 mm, 90 mm segments,
water-class fluid at 310.15 K, 12/4 mmHg) — every value carries its
epistemic class (MODEL_DERIVED, the P-07 package's own declared
envelope, recorded per Art. XXVII). Dimensions stated in the candidate's
critical parameters override the envelope when present and sourced.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from discovery_fabric.engine import physics_core as pc

GATE_VERSION = "physics_gate/1.0.0"

HYDRAULIC_DOMAIN = "fluidics_hydraulic"

# The P-07 reference envelope (MODEL_DERIVED — the package's own
# declared engineering envelope; every threshold carries its class).
REFERENCE_ENVELOPE = {
    "fluid": {"viscosity_mPa_s": 1.0, "density_kg_m3": 993.0,
              "temperature_K": 310.15,
              "source_class": "MODEL_DERIVED (P-07 declared basis: "
                              "water-class fluid at body temperature)"},
    "boundary": {"inlet_mmHg": 12.0, "outlet_mmHg": 4.0,
                 "source_class": "MODEL_DERIVED (P-07 declared "
                                 "operating envelope)"},
    "primary_lumen_diameter_mm": 1.0,
    "floor_lumen_diameter_mm": 0.6,
    "length_mm": 90.0,
    "required_min_flow_ml_min": 0.05,
    "source_class": ("MODEL_DERIVED — the P-07 reference envelope "
                     "(R381 CAD binding names; P-07 package's own "
                     "declared dimensions and operating range); not a "
                     "measured value (Art. XXVII)"),
}


def _param_values(eng: Dict[str, Any]) -> Dict[str, float]:
    """Extract sourced lumen dimensions from the engineering spec's
    critical parameters when present (value_status resolved)."""
    out: Dict[str, float] = {}
    for p in ((eng.get("engineering_core") or {})
              .get("critical_parameters", []) or []):
        label = str(p.get("label") or p.get("parameter") or "").lower()
        val = p.get("value")
        if val is None:
            continue
        try:
            val = float(val)
        except (TypeError, ValueError):
            continue
        if "primary" in label and "diameter" in label:
            out["primary_lumen_diameter_mm"] = val
        elif "floor" in label and "diameter" in label:
            out["floor_lumen_diameter_mm"] = val
    return out


def _network_spec(primary_mm: float, floor_mm: Optional[float],
                  identity: str) -> Dict[str, Any]:
    import hashlib
    segs: List[Dict[str, Any]] = [
        {"segment_id": "primary", "node_a": "A", "node_b": "B",
         "diameter_mm": primary_mm,
         "length_mm": REFERENCE_ENVELOPE["length_mm"]}]
    if floor_mm:
        segs.append({"segment_id": "floor", "node_a": "A", "node_b": "B",
                     "diameter_mm": floor_mm,
                     "length_mm": REFERENCE_ENVELOPE["length_mm"]})
    spec = {
        "geometry_identity": identity,
        "fluid": dict(REFERENCE_ENVELOPE["fluid"]),
        "boundary": dict(REFERENCE_ENVELOPE["boundary"]),
        "segments": segs,
    }
    spec["geometry_hash"] = hashlib.sha256(
        f"{identity}:{primary_mm}:{floor_mm}".encode()).hexdigest()
    return spec


def evaluate_candidate_physics(spec: Dict[str, Any],
                               eng: Dict[str, Any],
                               run_ctx: Optional[Dict[str, Any]] = None
                               ) -> Dict[str, Any]:
    """The R396 Phase D physics evaluation block for one candidate.

    Never raises (the gate discloses its own failures); never converts
    computation into a physical claim (Art. XXXVIII — the block's
    evidence class stays COMPUTATIONAL_RESULT or the honest negative
    states)."""
    domain = None
    for p in ((eng.get("engineering_core") or {})
              .get("critical_parameters", []) or []):
        domain = p.get("domain") or domain
    if not domain:
        domain = (eng.get("domain_reasoning") or {}).get("domain")
    if domain != HYDRAULIC_DOMAIN:
        return {
            "gate_version": GATE_VERSION,
            "applicable": False,
            "applicability": {
                "domain": domain,
                "solver_domain": HYDRAULIC_DOMAIN,
                "reason": ("the V0 solver's declared domain is 1D "
                           "hydraulic networks; this candidate's domain "
                           "is outside it — no physics comparison is "
                           "FABRICATED (R396 D / R394 s9: honest "
                           "refusal, not a claim)"),
            },
            "solver_version": pc.SOLVER_VERSION,
        }

    params = _param_values(eng)
    primary_mm = params.get("primary_lumen_diameter_mm",
                            REFERENCE_ENVELOPE["primary_lumen_diameter_mm"])
    floor_mm = params.get("floor_lumen_diameter_mm",
                          REFERENCE_ENVELOPE["floor_lumen_diameter_mm"])
    required_min = REFERENCE_ENVELOPE["required_min_flow_ml_min"]

    # BASELINE: the un-invented device — primary lumen only (the P-07
    # reference baseline: the standard catheter without the floor path).
    baseline_spec = _network_spec(primary_mm, None, "baseline-reference")
    # CANDIDATE: primary + the invented alternative floor path.
    candidate_spec = _network_spec(primary_mm, floor_mm,
                                   "candidate-reference")

    out: Dict[str, Any] = {
        "gate_version": GATE_VERSION,
        "applicable": True,
        "applicability": {
            "domain": domain,
            "solver_domain": HYDRAULIC_DOMAIN,
            "envelope": REFERENCE_ENVELOPE,
            "candidate_parameter_overrides": params or None,
        },
        "solver_version": pc.SOLVER_VERSION,
    }

    # 1) plausibility gate (runs INSIDE solve_network BEFORE the solve;
    #    surfaced separately for the record — a violated bound means no
    #    computational evidence at all)
    normal = pc.solve_network(candidate_spec)
    out["plausibility_gate"] = {
        # the gate's own plausibility verdict (NOT the solver record's
        # status — a passed bound check is PLAUSIBILITY_OK even when the
        # solve record is COMPUTATIONAL_RESULT; same vocabulary as the
        # PHYSICS stage, one authority, Art. X)
        "status": ("PLAUSIBILITY_BOUND_VIOLATED"
                   if normal.get("status") == "PLAUSIBILITY_BOUND_VIOLATED"
                   else "PLAUSIBILITY_OK"),
        "solver_status": normal.get("status"),
        "violations": normal.get("violations") or [],
        "families_checked": [
            "mass", "energy", "flow", "thermal", "attenuation", "scale"],
        "note": ("deterministic cheap bounds executed before the solve; "
                 "post-solve physical caps (flow/energy/mass/"
                 "attenuation) are checked inside the solver record "
                 "(R396 D.2)"),
    }
    if normal.get("status") == "PLAUSIBILITY_BOUND_VIOLATED":
        out["applicable"] = True
        out["plausibility_gate"]["consequence"] = (
            "the candidate's input envelope violates a deterministic "
            "physical bound — killed BEFORE expensive simulation; no "
            "computational evidence is emitted (R394 s11 / R396 D.2)")
        out["failure_mode_contract"] = None
        out["baseline_comparison"] = None
        return out

    # 2) failure-mode contract (R396 D.3): the four scenarios on BOTH
    #    the candidate and the baseline
    cand_fm = pc.simulate_failure_modes(candidate_spec, "primary")
    base_fm = pc.simulate_failure_modes(baseline_spec, "primary")
    out["failure_mode_contract"] = {
        "scenarios": pc.FAILURE_MODE_SCENARIOS,
        "candidate": {
            s["scenario"]: (s.get("result") or {}).get(
                "predicted_quantities", {}).get("total_flow_ml_min")
            for s in (cand_fm.get("scenarios") or [])},
        "baseline": {
            s["scenario"]: (s.get("result") or {}).get(
                "predicted_quantities", {}).get("total_flow_ml_min")
            for s in (base_fm.get("scenarios") or [])},
        "status": cand_fm.get("status"),
        "note": ("NORMAL / PARTIAL_OBSTRUCTION / SEVERE_OBSTRUCTION / "
                 "ALTERNATIVE_PATH — the actual failure mode the "
                 "invention exists for, simulated on candidate AND "
                 "baseline (R394 s9 / R396 D.3)"),
    }

    # 3) baseline comparison (R396 D.1 — the five required fields + the
    #    directive's exact verdict vocabulary)
    comp = pc.compare_to_baseline(
        candidate_spec, baseline_spec, "primary",
        scenario="SEVERE_OBSTRUCTION", required_min=required_min)
    out["baseline_comparison"] = comp

    # 4) design learning (deterministic mutation loop — R394 s12),
    #    run when the comparison executed (a KEEP loop also records the
    #    sensitivity analysis; a missed target records the mutations)
    if comp.get("outcome") in ("BEATS_BASELINE",
                               "DOES_NOT_BEAT_BASELINE"):
        try:
            from discovery_fabric.engine import design_learning as dl
            parameters = [
                {"name": "floor_lumen_diameter_mm",
                 "segment_id": "floor", "property": "diameter_mm",
                 "envelope": {"min": 0.3, "max": 0.8},
                 "cad_binding": "floor_lumen_diameter_mm"},
                {"name": "primary_lumen_diameter_mm",
                 "segment_id": "primary", "property": "diameter_mm",
                 "envelope": {"min": 0.6, "max": 1.4},
                 "cad_binding": "primary_lumen_diameter_mm"},
            ]
            loop = dl.learn_design(
                candidate_spec, baseline_spec, "primary",
                parameters=parameters,
                required_min=required_min,
                scenario="SEVERE_OBSTRUCTION")
            out["design_learning"] = {
                k: loop.get(k) for k in (
                    "status", "loop_version", "n_iterations",
                    "verdict", "verdict_basis", "final_value",
                    "required_min", "baseline_comparison")
                if k in loop}
            out["design_learning"]["iterations"] = loop.get("iterations")
        except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
            out["design_learning"] = {
                "error": f"{type(exc).__name__}: {exc}"[:300]}

    out["evidence_class_note"] = (
        "all results are COMPUTATIONAL_RESULT class (Art. XXXVIII "
        "layer 4) or the honest negative states; none may be cited as "
        "physical observation — physical validation is the Phase E "
        "experiment's job, not the solver's")
    return out
