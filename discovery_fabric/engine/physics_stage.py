"""discovery_fabric/engine/physics_stage.py — R397 Phase 2.

THE PHYSICS STAGE IS A FIRST-CLASS CANONICAL STAGE (STAGE_ORDER),
reachable from an ordinary user run — not a report field bolted onto
the engineering gauntlet.

The consultant finding this closes:
  "THE PHYSICS SOLVER IS VALIDATED CODE BUT NOT PART OF THE LIVE RUN
   CHAIN."

Chain executed for every representable candidate (directive order):

  PRE-REQUIREMENTS  -> domain representability (deterministic
                       classifier; non-representable = honest
                       MECHANISM_NOT_SIMULATABLE, never a fabricated
                       comparison — Art. XXXVIII / R394 s9)
  PLAUSIBILITY      -> deterministic cheap bounds (six families:
                       mass/energy/flow/thermal/attenuation/scale)
                       BEFORE the solve (R394 s11 / R396 D.2)
  SOLVER            -> the ONE canonical solver (physics_core V0,
                       1D hydraulic network)
  FAILURE MODES     -> NORMAL / PARTIAL_FAILURE / SEVERE_FAILURE /
                       ALTERNATIVE_PATH — the scenarios the invention
                       exists for, on candidate AND baseline
  BASELINE COMPARISON -> BEATS_BASELINE / DOES_NOT_BEAT_BASELINE /
                       INCONCLUSIVE (the five required fields:
                       BASELINE, CANDIDATE, TARGET METRIC, CONSTRAINTS,
                       RELATIVE IMPROVEMENT)
  COMPUTATIONAL_RESULT -> Art. XXXVIII layer-4 emission with
                       computation log (input/output hashes, solver
                       version, residual). NEVER a physical claim.

LIFECYCLE (R397: "Do not make any of these merely report fields.
They must affect the actual candidate lifecycle."):

  MECHANISM_NOT_SIMULATABLE      -> the candidate proceeds but can
                                    never claim a physics-validated
                                    improvement; the release record
                                    carries the refusal verbatim.
  PLAUSIBILITY_BOUND_VIOLATED    -> the candidate is KILLED at the
                                    physics gate BEFORE expensive
                                    simulation; downstream attack/
                                    dossier stages record it (the
                                    gauntlet-level enforcement lives
                                    in run.py — a candidate whose
                                    bounds are violated gets NO
                                    engineering gauntlet run).
  DOES_NOT_BEAT_BASELINE         -> the candidate is NOT promotable
                                    to an automatic release; the
                                    deterministic design-learning
                                    loop proposes the next candidate
                                    (parameter/direction/reason);
                                    only a mutation that BEATS the
                                    baseline (or an explicit human
                                    review decision) can release.
  BEATS_BASELINE                 -> recorded as the strengthening
                                    signal with the quantified
                                    margin.
  INCONCLUSIVE                   -> recorded; the candidate is not
                                    physics-blocked but the release
                                    must disclose the inconclusive
                                    basis.

Stage-level vs gauntlet-level division of labor (recorded, not
duplicated): THIS stage evaluates the mechanism the ordinary user run
carries on the envelope (the synthesized candidate) and writes the
verdict block into the canonical envelope (env.physics) so every
downstream stage — ATTACK, ADJUDICATION, CLASSIFY, the release —
consumes it. The engineering gauntlet (run.py) evaluates EVERY
candidate of the pool through the SAME gate (physics_gate.
evaluate_candidate_physics, R396 Phase D) and ENFORCES the lifecycle
rules above on the candidate set. Same canonical implementation,
one authority (Art. X).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from discovery_fabric.engine import physics_core as pc

STAGE_VERSION = "physics_stage/1.0.0"
HYDRAULIC_DOMAIN = "fluidics_hydraulic"

# R397 Phase 2 exact directive vocabulary. physics_core's scenario
# names (PARTIAL_OBSTRUCTION / SEVERE_OBSTRUCTION) map to the
# lifecycle vocabulary (PARTIAL_FAILURE / SEVERE_FAILURE) — the mapping
# is recorded here, not implicit.
FAILURE_MODE_VOCABULARY = ("NORMAL", "PARTIAL_FAILURE", "SEVERE_FAILURE",
                           "ALTERNATIVE_PATH")
_FAILURE_MODE_MAP = {
    "NORMAL": "NORMAL",
    "PARTIAL_OBSTRUCTION": "PARTIAL_FAILURE",
    "SEVERE_OBSTRUCTION": "SEVERE_FAILURE",
    "ALTERNATIVE_PATH": "ALTERNATIVE_PATH",
}
BASELINE_VOCABULARY = ("BEATS_BASELINE", "DOES_NOT_BEAT_BASELINE",
                       "INCONCLUSIVE")

# The P-07 reference envelope (MODEL_DERIVED — the package's own
# declared basis; identical to physics_gate.REFERENCE_ENVELOPE: one
# authority, imported not copied where possible; the duplication here
# is ONLY the subset the stage needs before an engineering spec
# exists, and it is pinned by test to physics_gate's values).
from discovery_fabric.engine.physics_gate import REFERENCE_ENVELOPE  # noqa: E402


def _mechanism_texts(env) -> Dict[str, str]:
    mm = env.mechanism_map or {}
    return {
        "mechanism": str(mm.get("mechanism", "") or ""),
        "intervention": str(mm.get("intervention", "") or ""),
        "expected_effect": str(mm.get("expected_effect", "") or ""),
    }


def _wrapper_text(env) -> str:
    problem = env.problem or {}
    return " ".join(str(problem.get(k, "")) for k in
                    ("device", "failure", "constraint", "failure_mode"))


def _problem_declared_parameters(env) -> tuple:
    """Problem-declared parameter overrides (deterministic extraction
    from the problem's constraint field — a MEASURED/declared value the
    problem itself carries, never invented). Anything not declared
    falls back to the reference envelope.

    Returns (overrides, discarded):
      overrides — name -> declared value. A NEGATIVE declared dimension
        is passed through VERBATIM: the solver's positive-diameter bound
        produces the honest physics kill. Never sign-flipped, never
        laundered to the reference envelope (Art. VII/XXV — a declared
        physical impossibility must surface, not be silently corrected).
      discarded — regex matches rejected by the sanity band (probable
        misfire on a non-lumen dimension, e.g. a shaft length), WITH the
        reason. Disclosed, never silently dropped (Art. XV).
    """
    overrides: Dict[str, float] = {}
    discarded: List[Dict[str, Any]] = []
    problem = env.problem or {}
    text = " ".join(str(problem.get(k, "")) for k in
                    ("constraint", "device", "failure")).lower()
    # diameter declarations (mm) — first match wins, recorded as
    # PROBLEM_DECLARED (Art. XXVII class recorded by the caller).
    # The sign is captured: [^\d-] keeps the gap from swallowing a
    # leading minus (the old pattern silently read '-0.2' as '0.2' —
    # a declared-impossible dimension became a solvable one).
    import re
    for name, pattern in (
            ("primary_lumen_diameter_mm",
             r"(?:primary[^\d-]{0,40})?(-?\d\.\d+)\s*mm"),
            ("floor_lumen_diameter_mm",
             r"(?:floor|secondary|bypass|rescue)[^\d-]{0,40}(-?\d\.\d+)\s*mm"),
    ):
        m = re.search(pattern, text)
        if not m:
            continue
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        if v < 0:
            # declared physical impossibility — pass through so the
            # solver's positive-diameter bound kills it honestly
            overrides[name] = v
        elif 0.05 <= v <= 10.0:  # sanity band (lumen mm scale)
            overrides[name] = v
        else:
            discarded.append({
                "parameter": name, "value": v,
                "reason": ("outside the lumen sanity band [0.05, 10.0] mm — "
                           "probable extraction misfire on a non-lumen "
                           "dimension; the reference envelope is retained "
                           "(disclosed, never silent)"),
            })
    return overrides, discarded


def _problem_declared_overrides(env) -> Dict[str, float]:
    """Overrides alone (the pinned extraction contract).

    Kept as the stable seam tests pin; the stage body uses
    _problem_declared_parameters so discards are disclosed too."""
    return _problem_declared_parameters(env)[0]


def _envelope_network_spec(primary_mm: float, floor_mm: Optional[float],
                           label: str) -> Dict[str, Any]:
    """Reuse physics_gate's network-spec builder (one authority)."""
    from discovery_fabric.engine.physics_gate import _network_spec
    return _network_spec(primary_mm, floor_mm, label)


def evaluate_envelope_physics(env, run_ctx: Optional[Dict[str, Any]] = None
                              ) -> Dict[str, Any]:
    """The PHYSICS stage body: evaluate the envelope's mechanism through
    the full directive chain and assign the LIFECYCLE verdict.

    Never raises (failures are disclosed in the block); never converts
    computation into a physical claim (Art. XXXVIII); never fabricates
    a comparison for a non-representable mechanism (R394 s9)."""
    out: Dict[str, Any] = {
        "stage_version": STAGE_VERSION,
        "solver_version": pc.SOLVER_VERSION,
        "run_id": (run_ctx or {}).get("run_id"),
        "directive_chain": ["PRE_REQUIREMENTS", "PLAUSIBILITY", "SOLVER",
                            "FAILURE_MODES", "BASELINE_COMPARISON",
                            "COMPUTATIONAL_RESULT"],
        "chain_executed": [],
    }
    texts = _mechanism_texts(env)
    mech_text = " ".join(texts.values())

    # ---- PRE-REQUIREMENTS: mechanism present + domain representability
    out["chain_executed"].append("PRE_REQUIREMENTS")
    if not (texts["mechanism"] or texts["intervention"]):
        out["pre_requirements"] = {
            "mechanism_present": False,
            "reason": ("no synthesized mechanism on the envelope — "
                       "PHYSICS cannot evaluate a candidate that does "
                       "not exist (upstream SYNTHESIZE state governs)"),
        }
        out["lifecycle_verdict"] = "MECHANISM_NOT_SIMULATABLE"
        out["lifecycle_effect"] = _lifecycle_effect(
            "MECHANISM_NOT_SIMULATABLE",
            reason="no mechanism on the envelope")
        return out
    from discovery_fabric.engine.domain_reasoning import \
        detect_domain_reasoned
    detection = detect_domain_reasoned(mech_text, _wrapper_text(env))
    domain = detection.get("domain")
    out["pre_requirements"] = {
        "mechanism_present": True,
        "domain": domain,
        "domain_detection": {
            k: detection.get(k) for k in
            ("domain", "why_this_domain", "layer", "signals")
            if k in detection},
        "solver_domain": HYDRAULIC_DOMAIN,
        "representable": domain == HYDRAULIC_DOMAIN,
    }
    if domain != HYDRAULIC_DOMAIN:
        out["chain_executed"] = ["PRE_REQUIREMENTS"]
        out["lifecycle_verdict"] = "MECHANISM_NOT_SIMULATABLE"
        out["applicability"] = {
            "domain": domain,
            "solver_domain": HYDRAULIC_DOMAIN,
            "reason": ("the V0 solver's declared domain is 1D hydraulic "
                       "networks; this candidate's mechanism is outside "
                       "it — no physics comparison is FABRICATED (R397 "
                       "Phase 2 / R394 s9 honest refusal)"),
        }
        out["lifecycle_effect"] = _lifecycle_effect(
            "MECHANISM_NOT_SIMULATABLE",
            reason=f"domain {domain} not representable by the V0 solver")
        out["evidence_class_note"] = (
            "no computational evidence emitted; the refusal is the "
            "honest result (Art. XXVIII: no silent semantic promotion)")
        return out

    # ---- parameters: reference envelope + problem-declared overrides
    overrides, discarded_declarations = _problem_declared_parameters(env)
    primary_mm = overrides.get(
        "primary_lumen_diameter_mm",
        REFERENCE_ENVELOPE["primary_lumen_diameter_mm"])
    floor_mm = overrides.get(
        "floor_lumen_diameter_mm",
        REFERENCE_ENVELOPE["floor_lumen_diameter_mm"])
    out["envelope"] = {
        "primary_lumen_diameter_mm": primary_mm,
        "floor_lumen_diameter_mm": floor_mm,
        "basis": ("REFERENCE_ENVELOPE (P-07 MODEL_DERIVED) with "
                  "PROBLEM_DECLARED overrides "
                  f"{sorted(overrides)}" if overrides else
                  "REFERENCE_ENVELOPE (P-07 MODEL_DERIVED, no "
                  "problem-declared overrides)"),
        "parameter_classes": {
            k: ("PROBLEM_DECLARED" if k in overrides else
                "MODEL_DERIVED (P-07 reference envelope)")
            for k in ("primary_lumen_diameter_mm",
                      "floor_lumen_diameter_mm")},
        "discarded_problem_declarations": discarded_declarations or None,
    }

    # BASELINE: the un-invented device (primary lumen only)
    baseline_spec = _envelope_network_spec(primary_mm, None,
                                           "stage-baseline")
    candidate_spec = _envelope_network_spec(primary_mm, floor_mm,
                                            "stage-candidate")

    # ---- PLAUSIBILITY: deterministic bounds BEFORE the solve
    out["chain_executed"].append("PLAUSIBILITY")
    normal = pc.solve_network(candidate_spec)
    out["plausibility"] = {
        # the PLAUSIBILITY step's own verdict — NOT the solver's status
        # (a passed bound check is PLAUSIBILITY_OK even when the solver
        # record's own status is COMPUTATIONAL_RESULT; the two steps are
        # distinct in the directive chain and must not be conflated)
        "status": ("PLAUSIBILITY_BOUND_VIOLATED"
                   if normal.get("status") == "PLAUSIBILITY_BOUND_VIOLATED"
                   else "PLAUSIBILITY_OK"),
        "solver_status": normal.get("status"),
        "violations": normal.get("violations") or [],
        "families": ["mass", "energy", "flow", "thermal", "attenuation",
                     "scale"],
        "note": ("deterministic cheap bounds before expensive "
                 "simulation (R397 Phase 2 / R396 D.2)"),
    }
    if normal.get("status") == "PLAUSIBILITY_BOUND_VIOLATED":
        out["lifecycle_verdict"] = "PLAUSIBILITY_BOUND_VIOLATED"
        out["lifecycle_effect"] = _lifecycle_effect(
            "PLAUSIBILITY_BOUND_VIOLATED",
            reason="deterministic physical bound violated — killed "
                   "before the solver runs")
        out["evidence_class_note"] = (
            "no computational evidence emitted (the bound violation "
            "IS the result — Art. IV fail closed)")
        return out

    # ---- SOLVER (the NORMAL solve is already computed above)
    out["chain_executed"].append("SOLVER")
    out["solver"] = {
        "status": normal.get("status"),
        "solver_version": pc.SOLVER_VERSION,
        "predicted_quantities": (normal.get("predicted_quantities")
                                 or {}),
        "convergence_residual": normal.get("convergence_residual"),
        "assumptions": normal.get("assumptions"),
    }

    # ---- FAILURE MODES: candidate AND baseline, directive vocabulary
    out["chain_executed"].append("FAILURE_MODES")
    cand_fm = pc.simulate_failure_modes(candidate_spec, "primary")
    base_fm = pc.simulate_failure_modes(baseline_spec, "primary")
    fm_flows: Dict[str, Optional[float]] = {}
    for s in (cand_fm.get("scenarios") or []):
        core_name = s.get("scenario")
        flow = ((s.get("result") or {}).get("predicted_quantities", {})
                .get("total_flow_ml_min"))
        fm_flows[_FAILURE_MODE_MAP.get(core_name, core_name)] = flow
    base_flows: Dict[str, Optional[float]] = {}
    for s in (base_fm.get("scenarios") or []):
        core_name = s.get("scenario")
        flow = ((s.get("result") or {}).get("predicted_quantities", {})
                .get("total_flow_ml_min"))
        base_flows[_FAILURE_MODE_MAP.get(core_name, core_name)] = flow
    out["failure_mode_contract"] = {
        "vocabulary": FAILURE_MODE_VOCABULARY,
        "core_scenario_names": pc.FAILURE_MODE_SCENARIOS,
        "vocabulary_map": _FAILURE_MODE_MAP,
        "candidate": fm_flows,
        "baseline": base_flows,
        "status": cand_fm.get("status"),
        "note": ("the failure modes the invention exists for, simulated "
                 "on the candidate AND the un-invented baseline (R396 "
                 "D.3 / R397 Phase 2)"),
    }

    # ---- BASELINE COMPARISON (five required fields + verdict)
    out["chain_executed"].append("BASELINE_COMPARISON")
    comp = pc.compare_to_baseline(
        candidate_spec, baseline_spec, "primary",
        scenario="SEVERE_OBSTRUCTION",
        required_min=REFERENCE_ENVELOPE["required_min_flow_ml_min"])
    out["baseline_comparison"] = comp
    outcome = comp.get("outcome")
    out["lifecycle_verdict"] = outcome if outcome in \
        BASELINE_VOCABULARY else "INCONCLUSIVE"

    # ---- design learning on a miss (deterministic mutation proposal)
    if outcome in ("BEATS_BASELINE", "DOES_NOT_BEAT_BASELINE"):
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
                required_min=REFERENCE_ENVELOPE[
                    "required_min_flow_ml_min"],
                scenario="SEVERE_OBSTRUCTION")
            out["design_learning"] = {
                k: loop.get(k) for k in (
                    "status", "loop_version", "n_iterations",
                    "verdict", "verdict_basis", "final_value")
                if k in loop}
        except Exception as exc:  # noqa: BLE001 — disclosed, non-fatal
            out["design_learning"] = {
                "error": f"{type(exc).__name__}: {exc}"[:300]}

    # ---- COMPUTATIONAL_RESULT emission (Art. XXXVIII layer 4)
    out["chain_executed"].append("COMPUTATIONAL_RESULT")
    try:
        out["computational_result"] = pc.to_computational_result(normal)
    except Exception as exc:  # noqa: BLE001 — disclosed, non-fatal
        out["computational_result"] = {
            "error": f"{type(exc).__name__}: {exc}"[:300],
            "note": "the solve above remains the record; emission "
                    "failed and is disclosed (Art. XV)"}

    out["lifecycle_effect"] = _lifecycle_effect(
        out["lifecycle_verdict"],
        reason=f"baseline comparison outcome: {outcome}")
    out["evidence_class_note"] = (
        "all results are COMPUTATIONAL_RESULT class (Art. XXXVIII "
        "layer 4) or honest negative states; none may be cited as a "
        "physical observation — physical validation is the Phase E "
        "experiment's job, not the solver's")
    return out


def _lifecycle_effect(verdict: str, reason: str) -> Dict[str, Any]:
    """The MECHANICAL effect of each verdict on the candidate lifecycle
    (R397: 'not merely report fields'). These rules are enforced at the
    gauntlet (run.py): this block is the contract the gauntlet
    implements — pinned by tests so the two cannot drift apart."""
    effects = {
        "MECHANISM_NOT_SIMULATABLE": {
            "candidate_pool": "PROCEEDS",
            "automatic_release": "BLOCKED_NO_PHYSICS_CLAIM",
            "release_must_disclose": "the mechanism is outside the "
                                     "solver's domain — no physics "
                                     "improvement is claimed or implied",
        },
        "PLAUSIBILITY_BOUND_VIOLATED": {
            "candidate_pool": "KILLED_BEFORE_EXPENSIVE_SIMULATION",
            "automatic_release": "BLOCKED",
            "kill_reason_class": "PHYSICS_BOUND",
        },
        "DOES_NOT_BEAT_BASELINE": {
            "candidate_pool": "PROCEEDS_WITH_MUTATION_PROPOSAL",
            "automatic_release": "BLOCKED",
            "release_must_disclose": "the candidate does not beat the "
                                     "baseline on the target metric; "
                                     "the deterministic design-learning "
                                     "loop proposes the next candidate",
        },
        "BEATS_BASELINE": {
            "candidate_pool": "PROCEEDS",
            "automatic_release": "ELIGIBLE (all other gates still apply)",
            "quantified_margin": "recorded in baseline_comparison",
        },
        "INCONCLUSIVE": {
            "candidate_pool": "PROCEEDS",
            "automatic_release": "CONDITIONAL",
            "release_must_disclose": "the baseline comparison is "
                                     "inconclusive for the recorded "
                                     "reason",
        },
    }
    eff = dict(effects.get(verdict, {
        "candidate_pool": "PROCEEDS",
        "automatic_release": "CONDITIONAL",
        "note": "unmapped verdict — conservative default"}))
    eff["reason"] = reason
    return eff
