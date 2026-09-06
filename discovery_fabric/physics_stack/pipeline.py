"""pipeline.py — the physics-validation pipeline contracts (R413
Physics Stack V1).

THE OPERATOR'S ARCHITECTURE (verbatim sequence):
    AI invention -> physical hypothesis -> 3D geometry -> solver
    selection -> simulation -> measurement extraction -> falsification
    -> redesign -> simulation -> dossier
    (with Blender rendering the ACTUAL simulated geometry/results,
     and the buyer dossier carrying the 3D model, assumptions,
     boundary conditions, simulation outputs, uncertainty and failure
     modes)

    NOT: AI -> Blender picture -> "looks physically plausible."

This module makes that sequence a typed stage machine. V1 delivers
the CONTRACTS (required fields, failure states, provenance chaining,
guards). Stage EXECUTION beyond the V0 replay is blocked by measured
solver availability — honestly, as infrastructure incompleteness
(Art. LXI), never as a scientific result.

GUARDS (all deterministic):
- SIMULATION_EXECUTION refuses a solver that is not measured-INSTALLED
  or whose instrument validation is NONE_IN_THIS_ENVIRONMENT.
- RENDERING refuses any render not bound to a simulation output hash
  (VISUALIZATION_WITHOUT_COMPUTATION — the anti-pattern kill switch).
- BUYER_DOSSIER refuses any physics claim that
  coverage.evaluate_physics_claim does not ADMIT, and requires the
  operator's dossier field list verbatim.
- Every stage output carries input_hash <- output_hash provenance
  (the computation-log discipline the R394 V0 established).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from discovery_fabric.physics_stack import coverage as _coverage
from discovery_fabric.physics_stack import solver_registry as _sr
from discovery_fabric.physics_stack import geometry_authority as _ga

#: The operator's 11 stages, in order. Names are stable identifiers —
#: renames are contract breaks and must never happen silently.
PIPELINE_STAGES: Tuple[str, ...] = (
    "MECHANISM_INPUT",
    "PHYSICAL_HYPOTHESIS",
    "GEOMETRY_SPEC",
    "SOLVER_SELECTION",
    "SIMULATION_EXECUTION",
    "MEASUREMENT_EXTRACTION",
    "FALSIFICATION_ATTACK",
    "REDESIGN",
    "SIMULATION_REPLAY",
    "RENDERING",
    "BUYER_DOSSIER",
)

_STAGE_NOTES = {
    "MECHANISM_INPUT": "the invention's mechanism arrives from the "
                       "discovery loop (upstream gate state recorded — "
                       "the physics stage never rewrites it)",
    "PHYSICAL_HYPOTHESIS": "typed phenomenon classes (closed "
                           "vocabulary) + the operating-regime "
                           "hypothesis, proposed by the PROPOSER role",
    "GEOMETRY_SPEC": "parametric 3D geometry: identity + hash + "
                     "parameters (the V0's CAD-binding pattern; "
                     "geometry is data, not pictures)",
    "SOLVER_SELECTION": "the deterministic selection record "
                        "(selection.select_solvers — code, not LLM)",
    "SIMULATION_EXECUTION": "solver run with computation log: input "
                            "hash, output hash, solver version, "
                            "assumptions, limitations",
    "MEASUREMENT_EXTRACTION": "machine-readable quantities + units "
                              "extracted from solver outputs (the "
                              "operator's step 6: 'solver outputs "
                              "become machine-readable evidence')",
    "FALSIFICATION_ATTACK": "the ATTACKER role attacks the invention "
                            "USING the simulation results; the attack "
                            "record binds to the simulation output "
                            "hash (role independence, Art. XLV)",
    "REDESIGN": "parameter/design changes responding to the attack "
                "(OpenMDAO-orchestrated search against physical "
                "objectives when installed)",
    "SIMULATION_REPLAY": "the surviving design re-enters the physics "
                         "stack under the SAME contracts (identical "
                         "instrument, Art. XLVII baseline supremacy "
                         "analog: the comparison arm never changes "
                         "instrument mid-stream)",
    "RENDERING": "Blender renders the ACTUAL simulated geometry/"
                 "results; every render binds to a simulation output "
                 "hash",
    "BUYER_DOSSIER": "3D model + assumptions + boundary conditions + "
                     "simulation outputs + uncertainty + failure "
                     "modes; every physics claim passes the claim "
                     "contract",
}

#: Required fields per stage (the contract). A stage output missing a
#: field is INVALID — there is no partial credit (Art. IV).
STAGE_REQUIRED_FIELDS: Dict[str, Tuple[str, ...]] = {
    "MECHANISM_INPUT": (
        "mechanism_id", "problem", "causal_mechanism", "upstream_gate_state",
        "provenance"),
    "PHYSICAL_HYPOTHESIS": (
        "mechanism_id", "phenomenon_classes", "regime_hypothesis",
        "proposer_role", "provenance"),
    "GEOMETRY_SPEC": (
        "geometry_identity", "geometry_hash", "geometry_authority",
        "parameters", "boundary_conditions", "provenance"),
    "SOLVER_SELECTION": (
        "selection_sha256", "selections", "execution_allowed",
        "provenance"),
    "SIMULATION_EXECUTION": (
        "solver_id", "solver_version", "phenomenon", "geometry_hash",
        "input_hash", "output_hash", "assumptions", "limitations",
        "convergence", "provenance"),
    "MEASUREMENT_EXTRACTION": (
        "simulation_output_hash", "quantities", "provenance"),
    "FALSIFICATION_ATTACK": (
        "simulation_output_hash", "attack_findings", "attacker_role",
        "independence_state", "provenance"),
    "REDESIGN": (
        "design_change", "responds_to_attack_finding", "new_geometry_hash",
        "provenance"),
    "SIMULATION_REPLAY": (
        "solver_id", "solver_version", "phenomenon", "geometry_hash",
        "input_hash", "output_hash", "convergence", "provenance"),
    "RENDERING": (
        "simulation_output_hash", "simulation_artifact_id",
        "geometry_hash", "render_asset_id",
        "renderer", "provenance"),
    "BUYER_DOSSIER": (
        "model_reference", "assumptions", "boundary_conditions",
        "simulation_outputs", "uncertainty", "failure_modes",
        "physics_claims", "provenance"),
}

#: Failure states a stage may legitimately carry (typed, never prose).
STAGE_FAILURE_STATES = {
    "SIMULATION_EXECUTION": (
        "MECHANISM_NOT_SIMULATABLE",       # no solver for a phenomenon
        "INCOMPLETE_SOLVER_NOT_INSTALLED",  # Art. LXI infrastructure
        "INCOMPLETE_NO_INSTRUMENT_VALIDATION",
        "COMPUTATIONAL_RESULT_MODEL_INVALIDITY",  # the V0's own state
    ),
    "RENDERING": (
        "REJECTED_VISUALIZATION_WITHOUT_COMPUTATION",
        "INCOMPLETE_RENDERER_NOT_INSTALLED",  # Art. LXI — measured
        # blender/bpy probe state; a Phase 7 unblock, never a verdict
    ),
    "FALSIFICATION_ATTACK": (
        "ATTACK_INDEPENDENCE_UNAVAILABLE",  # Art. XLV honest state
    ),
}


def stage_note(stage: str) -> str:
    return _STAGE_NOTES[stage]


def validate_stage_output(stage: str, doc: Dict[str, Any]
                          ) -> List[str]:
    """Contract check for one stage output. EMPTY = valid. Includes the
    stage-specific adversarial guards (the anti-overclaim /
    anti-'picture as physics' switches live here)."""
    if stage not in PIPELINE_STAGES:
        return [f"unknown stage {stage!r} — the pipeline stage set is "
                "closed; adding a stage is a contract change that "
                "requires a new version, never a silent append"]
    v: List[str] = []
    for field in STAGE_REQUIRED_FIELDS[stage]:
        if field not in doc:
            v.append(f"{stage}: missing required field {field!r}")
    if not doc.get("provenance"):
        v.append(f"{stage}: provenance required on every stage output "
                  "(the computation-log discipline)")
    if doc.get("failure_state"):
        if doc["failure_state"] not in STAGE_FAILURE_STATES.get(stage, ()):
            v.append(f"{stage}: failure_state {doc['failure_state']!r} "
                     "is not a typed failure state for this stage")
        return v  # a typed failure state is a VALID, honest output

    if stage == "GEOMETRY_SPEC":
        # THE OPERATOR'S GEOMETRY BOUNDARY (directive V2 Phase 4):
        # CadQuery is the engineering geometry authority; Blender is
        # downstream visualization and cannot originate or
        # independently validate engineering geometry.
        v.extend(_ga.validate_geometry_spec(doc))
    if stage == "PHYSICAL_HYPOTHESIS":
        for ph in doc.get("phenomenon_classes", []):
            if ph not in _PHENOMENA():
                v.append(f"{stage}: phenomenon {ph!r} outside the "
                         "closed vocabulary (Art. XLIII)")
    if stage == "SIMULATION_EXECUTION" or stage == "SIMULATION_REPLAY":
        solver = _sr.get_solver(doc.get("solver_id", ""))
        if solver is None:
            v.append(f"{stage}: solver {doc.get('solver_id')!r} is not "
                      "registered")
        else:
            if solver["availability"]["state"] != "INSTALLED":
                v.append(
                    f"{stage}: solver {doc['solver_id']} is "
                    f"{solver['availability']['state']} (MEASURED) — a "
                    "run record for a not-installed solver would "
                    "manufacture provenance (Art. VI); the honest "
                    "output is failure_state="
                    "INCOMPLETE_SOLVER_NOT_INSTALLED")
            iv = (solver.get("instrument_validation") or {})
            if str(iv.get("method", "")).startswith("NONE"):
                v.append(
                    f"{stage}: solver {doc['solver_id']} has no "
                    "instrument validation in this environment — "
                    "failure_state=INCOMPLETE_NO_INSTRUMENT_VALIDATION "
                    "is the honest output (Art. III/XVI)")
            if doc.get("solver_version") in (
                    None, "DECLARED_VERSION_AT_INSTALL"):
                v.append(
                    f"{stage}: solver_version must be the RUNTIME "
                    "version, never the registration placeholder "
                    "(Art. LXII)")
    if stage == "RENDERING":
        # the operator's Phase 7 contract, encoded now: renders bind
        # to simulation artifacts AND consume authority geometry
        v.extend(_ga.validate_render_record(doc))
        if doc.get("renderer") not in ("blender",
                                       "sofa_blender_bridge"):
            v.append(f"{stage}: renderer must be a visualization-layer "
                      "record (blender / sofa_blender_bridge)")
    if stage == "BUYER_DOSSIER":
        for claim in doc.get("physics_claims", []):
            verdict = _coverage.evaluate_physics_claim(claim)
            if verdict["verdict"] != _coverage.VERDICT_ADMITTED:
                v.append(f"{stage}: physics claim rejected by the "
                         f"claim contract: {verdict['verdict']} — "
                         f"{'; '.join(verdict['reasons'])[:200]}")
    return v


def _PHENOMENA() -> List[str]:
    from discovery_fabric.physics_stack.selection import (
        PHENOMENON_VOCABULARY,
    )
    return PHENOMENON_VOCABULARY


def pipeline_progression(stage_a: str, stage_b: str) -> bool:
    """True iff stage_b follows stage_a in the operator's sequence
    (REDESIGN -> SIMULATION_REPLAY is the loop-back edge; the sequence
    is otherwise linear)."""
    if (stage_a, stage_b) == ("REDESIGN", "SIMULATION_REPLAY"):
        return True
    ia = PIPELINE_STAGES.index(stage_a)
    ib = PIPELINE_STAGES.index(stage_b)
    return ib == ia + 1


def initial_pipeline_state(mechanism_input: Dict[str, Any]
                           ) -> Dict[str, Any]:
    """A fresh pipeline state document: the ordered stage list with
    V1's honest default — the first stage pending, everything after
    blocked (V1 executes nothing beyond the V0 replay; the state says
    so rather than pretending readiness)."""
    problems = validate_stage_output("MECHANISM_INPUT", mechanism_input)
    return {
        "stages": list(PIPELINE_STAGES),
        "current_stage": None if problems else "MECHANISM_INPUT",
        "mechanism_input_valid": not problems,
        "mechanism_input_problems": problems,
        "v1_execution_capability": {
            "measured_installed_solvers": [
                r["solver_id"] for r in _sr.SOLVER_REGISTRY
                if r["availability"]["state"] == "INSTALLED"],
            "note": "V1 ships contracts; the only execution-capable "
                    "solver in this environment is hydraulic_network_1d "
                    "(measured) — every other stage transition that "
                    "needs a solver will carry an honest typed failure "
                    "state, never a fabricated run (Art. VI/LXI)",
        },
    }
