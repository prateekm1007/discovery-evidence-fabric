"""solver_registry.py — the multi-solver registry (R413 Physics Stack V1).

The operator's layer table, machine-readable, with MEASURED
availability from R413/PHYSICS_STACK_V1/SOLVER_AVAILABILITY_PROBES.json.

THE TWO HARD RULES (operator directive, enforced here):
1. execution_evidence_class is PINNED to COMPUTATIONAL_RESULT for every
   solver. A solver registration may not declare any other evidence
   class — the stack computes; it never observes (Art. XXXVIII layer 4,
   Art. LIII: no state may skip a level).
2. phenomenon vocabulary is CLOSED and PER-SOLVER-SCOPED. No solver may
   register a phenomenon class in FORBIDDEN_PHENOMENON_CLASSES (e.g.
   "ALL_PHYSICS") — "never claim all laws of physics" is a schema
   constraint, not advice (Art. XXVIII: no silent semantic promotion).

Blender's record is deliberately physics-EMPTY: its phenomenon_classes
list is empty, so it can never be selected to compute physics evidence
and a render can never enter the evidence chain as computation (the
pipeline's RENDERING stage binds renders to simulation output hashes
instead). OpenMDAO and the SOFA->Blender bridge are likewise empty:
they orchestrate and visualize, they do not produce physics evidence.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
PROBES_PATH = (REPO / "R413" / "PHYSICS_STACK_V1"
               / "SOLVER_AVAILABILITY_PROBES.json")

#: Art. XXXVIII layer 4 — the ONLY evidence class any solver here may emit.
EXECUTION_EVIDENCE_CLASS = "COMPUTATIONAL_RESULT"

#: The operator's crucial rule, as a closed set of forbidden registry
#: values. Registering any of these as a phenomenon class is a schema
#: violation caught by validate_registry().
FORBIDDEN_PHENOMENON_CLASSES = frozenset({
    "ALL_PHYSICS", "ALL", "EVERYTHING", "GENERAL_PHYSICS",
    "PHYSICS_VERIFIED", "LAWS_OF_PHYSICS",
})

#: Stack layer taxonomy (the operator's table, one layer per row).
STACK_LAYERS = {
    "3D_RENDERING": "geometry, materials, animation, exploded views, "
                    "PDF/web renders (Blender)",
    "RIGID_BODY_DYNAMICS": "motion, collisions, joints, actuators, "
                           "contact dynamics (Blender / MuJoCo)",
    "CFD_FLUIDS": "fluid flow, turbulence, heat transfer, chemical "
                  "reactions, acoustics (OpenFOAM)",
    "STRUCTURAL_FEM": "stress, strain, deformation, thermal and "
                      "multiphysics (FEniCSx / SfePy / Elmer)",
    "SOFT_BODY": "continuum mechanics, soft bodies, collisions, "
                 "biomechanics/robotics (SOFA)",
    "MULTIBODY": "mechanisms, vehicles, multibody systems, "
                 "contact/friction (Project Chrono)",
    "ELECTROMAGNETICS": "electrical and electromagnetic behavior "
                         "(Elmer / openEMS)",
    "THERMAL": "heat transfer and thermal fields (OpenFOAM / Elmer)",
    "OPTIMIZATION": "automated design-parameter search against "
                    "physical objectives (OpenMDAO)",
    "VISUALIZATION_BRIDGE": "bring simulated motion/results into "
                            "Blender for rendering (SOFA -> Blender)",
}

#: Required fields on every solver record (Art. VI: availability must
#: carry a probe; Art. LXII: solver_version must be declared; Art. II:
#: the role must be exact).
REQUIRED_SOLVER_FIELDS = (
    "solver_id",             # unique identity in this registry
    "layer",                 # one of STACK_LAYERS
    "role_in_stack",         # what it gives us (operator's table, verbatim)
    "phenomenon_classes",    # CLOSED list; [] for non-physics layers
    "execution_evidence_class",  # must == EXECUTION_EVIDENCE_CLASS
    "solver_version",        # declared version identity (LXII)
    "availability",          # {state, probe, measured_at, detail}
    "alternates",            # same-layer substitutes (routing surface)
    "instrument_validation", # how the solver itself is validated
)


def _probe_state(solver_id: str, *probe_ids: str) -> Dict[str, Any]:
    """Load the MEASURED availability from the probe artifact. A missing
    probe file is a REGISTRY-VALIDATION failure (availability may never
    be assumed — Art. VI); this loader fails loudly rather than guessing.
    """
    if not PROBES_PATH.exists():
        raise FileNotFoundError(
            f"probe artifact missing: {PROBES_PATH} — availability "
            "cannot be assumed without measurement (Art. VI)")
    doc = json.loads(PROBES_PATH.read_text())
    by_id = {p["solver_id"]: p for p in doc["probes"]}
    hits = [by_id[pid] for pid in probe_ids if pid in by_id]
    if not hits:
        return {
            "state": "PROBE_MISSING",
            "probe": "NONE",
            "measured_at": None,
            "detail": f"no probe record for {probe_ids} — registry "
                      "validation must fail (Art. VI: never assumed)",
        }
    primary = hits[0]
    return {
        "state": "INSTALLED" if primary["result"] == "INSTALLED"
                 else "PROBED_NOT_INSTALLED",
        "probe": primary["probe"],
        "measured_at": primary.get("measured_at"),
        "probe_result": primary["result"],
        "detail": primary.get("detail", "")[:300],
        "version_detail": primary.get("version_detail"),
        "all_probe_ids": list(probe_ids),
    }


def _record(solver_id, layer, role, phenomena, version, availability,
            alternates, instrument_validation, notes=None):
    rec = {
        "solver_id": solver_id,
        "layer": layer,
        "role_in_stack": role,
        "phenomenon_classes": phenomena,
        "execution_evidence_class": EXECUTION_EVIDENCE_CLASS,
        "solver_version": version,
        "availability": availability,
        "alternates": alternates,
        "instrument_validation": instrument_validation,
    }
    if notes:
        rec["notes"] = notes
    return rec


_V0_VALIDATION = {
    "method": "closed-form reference replay (single tube Poiseuille, "
              "series resistances, parallel conductances)",
    "artifact": "R413/PHYSICS_STACK_V1/SOLVER_AVAILABILITY_PROBES.json "
                "(probe hydraulic_network_1d, replayed live 2026-09-06)",
    "all_cases_pass": True,
    "max_rel_error": 0.0,
    "declared_threshold": {
        "name": "REFERENCE_REL_TOL",
        "value": 1e-12,
        "epistemic_class": "ENGINEERING",
        "justification": "the R394 V0 threshold: a linear-network solver "
                         "must reproduce Poiseuille closed forms to "
                         "floating-point agreement",
    },
}

#: THE REGISTRY — the operator's preferred stack, availability MEASURED
#: in this environment (16 of 18 probes: NOT_INSTALLED; the V0 and its
#: numpy dependency: INSTALLED). Each record cites its probe.
SOLVER_REGISTRY: List[Dict[str, Any]] = [
    _record(
        solver_id="blender",
        layer="3D_RENDERING",
        role="geometry, materials, animation, exploded views, "
             "PDF/web renders",
        phenomena=[],  # VISUALIZATION ONLY — computes no physics evidence
        version="blender/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("blender", "blender",
                                  "blender_python_bpy"),
        alternates=[],
        instrument_validation={
            "method": "NOT_APPLICABLE_VISUALIZATION",
            "note": "renders bind to simulation output hashes at the "
                    "pipeline RENDERING stage; a Blender image is never "
                    "computation and never evidence (the operator's "
                    "'AI -> Blender picture -> looks physically "
                    "plausible' path is forbidden downstream)",
        },
        notes="operator: 'Blender should be the visualization/geometry "
              "layer, not the all-physics engine' — encoded by the empty "
              "phenomenon_classes list",
    ),
    _record(
        solver_id="mujoco",
        layer="RIGID_BODY_DYNAMICS",
        role="motion, collisions, joints, actuators, contact dynamics",
        phenomena=["rigid_body_contact_dynamics",
                   "actuated_multibody_control"],
        version="mujoco/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("mujoco", "mujoco"),
        alternates=["blender_rigidbody"],
        instrument_validation={
            "method": "NONE_IN_THIS_ENVIRONMENT",
            "note": "standard MuJoCo ships its own analytical/validation "
                    "suite; until installed and replayed here, the "
                    "coverage registry keeps validated_regime empty for "
                    "its phenomena (Art. XXV)",
        },
    ),
    _record(
        solver_id="blender_rigidbody",
        layer="RIGID_BODY_DYNAMICS",
        role="Blender's built-in rigid-body/cloth/fluid features "
             "(the operator noted these exist)",
        phenomena=[],  # lower-fidelity visualization-grade, not evidence
        version="blender/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("blender", "blender"),
        alternates=["mujoco"],
        instrument_validation={
            "method": "NOT_APPLICABLE_VISUALIZATION",
            "note": "visualization-grade dynamics; explicitly NOT an "
                    "evidence source (fidelity insufficient for "
                    "dossier-grade computational validation)",
        },
    ),
    _record(
        solver_id="openfoam",
        layer="CFD_FLUIDS",
        role="fluid flow, turbulence, heat transfer, chemical "
             "reactions, acoustics",
        phenomena=["incompressible_viscous_flow", "turbulent_flow",
                   "convective_heat_transfer", "porous_media_flow"],
        version="openfoam/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("openfoam", "openfoam",
                                  "openfoam_simplefoam"),
        alternates=["elmer"],
        instrument_validation={
            "method": "NONE_IN_THIS_ENVIRONMENT",
            "note": "OpenFOAM tutorial/validation cases are the standard "
                    "instrument checks; until installed and replayed "
                    "here, validated_regime stays empty (Art. XXV)",
        },
    ),
    _record(
        solver_id="fenicsx",
        layer="STRUCTURAL_FEM",
        role="stress, strain, deformation, thermal and multiphysics "
             "calculations (FEniCSx)",
        phenomena=["structural_stress_strain", "linear_elastic_deformation",
                   "thermal_structural_multiphysics"],
        version="fenicsx/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("fenicsx", "fenicsx_dolfinx",
                                  "fenics_legacy"),
        alternates=["sfepy", "elmer"],
        instrument_validation={
            "method": "NONE_IN_THIS_ENVIRONMENT",
            "note": "FEniCSx ships MMS (method of manufactured "
                    "solutions) test conventions; not replayed here "
                    "(Art. XXV)",
        },
    ),
    _record(
        solver_id="sfepy",
        layer="STRUCTURAL_FEM",
        role="stress, strain, deformation, multiphysics (SfePy)",
        phenomena=["structural_stress_strain", "linear_elastic_deformation",
                   "thermal_structural_multiphysics"],
        version="sfepy/2026.2",
        availability=_probe_state("sfepy", "sfepy"),
        alternates=["fenicsx", "elmer"],
        instrument_validation={
            "method": "closed-form reference replay: uniform-traction "
                      "plane-stress problems whose exact displacement "
                      "fields lie inside the bilinear element space "
                      "(3 cases, 2 geometries, 3 materials, tension + "
                      "compression) — executed live, all cases pass, "
                      "determinism replay byte-identical",
            "artifact": "R413/PHYSICS_STACK_V1/"
                        "SFEPY_INSTRUMENT_VALIDATION.json",
            "all_cases_pass": True,
            "max_rel_error": 1.9e-14,
            "declared_threshold": {
                "name": "REFERENCE_REL_TOL",
                "value": 1e-9,
                "epistemic_class": "ENGINEERING",
                "justification": "the closed-form solution is exactly "
                                 "representable in the bilinear "
                                 "element space (the R394 V0 "
                                 "discipline applied to FEM)",
            },
            "validated_regime_scope": "plane-stress, uniform traction, "
                                      "exactly-representable fields — "
                                      "stress concentrations and "
                                      "other regimes stay OUTSIDE "
                                      "(the claim contract enforces "
                                      "the scoping)",
        },
        notes="installed and validated this round: selected by the "
              "Phase 5 decision machine (score 20855 under the "
              "pre-registered six-factor formula; the formula-"
              "sensitivity disagreement with the simple UxG/C shape "
              "is disclosed on the opportunity artifact), installed "
              "by the operator-authorized decision, then validated by "
              "closed-form replay BEFORE any discovery use — the "
              "second execution-capable member after hydraulic_"
              "network_1d (Art. LXIV: a member, not a replacement)",
    ),
    _record(
        solver_id="elmer",
        layer="STRUCTURAL_FEM",
        role="stress, strain, deformation, thermal and multiphysics "
             "(Elmer FEM)",
        phenomena=["structural_stress_strain", "linear_elastic_deformation",
                   "thermal_structural_multiphysics",
                   "electromagnetic_fields_lowfreq", "heat_transfer"],
        version="elmer/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("elmer", "elmer", "elmer_grid"),
        alternates=["fenicsx", "sfepy"],
        instrument_validation={
            "method": "NONE_IN_THIS_ENVIRONMENT",
            "note": "Elmer ships verification cases; not replayed here "
                    "(Art. XXV)",
        },
    ),
    _record(
        solver_id="sofa",
        layer="SOFT_BODY",
        role="continuum mechanics, soft bodies, collisions, "
             "biomechanics/robotics",
        phenomena=["soft_body_continuum_mechanics",
                   "deformable_biomechanics"],
        version="sofa/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("sofa", "sofa", "sofa_python"),
        alternates=[],
        instrument_validation={
            "method": "NONE_IN_THIS_ENVIRONMENT",
            "note": "SOFA ships scene-level regression tests; not "
                    "replayed here (Art. XXV)",
        },
    ),
    _record(
        solver_id="project_chrono",
        layer="MULTIBODY",
        role="mechanisms, vehicles, multibody systems, contact/friction",
        phenomena=["multibody_mechanisms", "vehicle_dynamics",
                   "contact_friction_mechanics"],
        version="projectchrono/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("project_chrono", "project_chrono_pychrono"),
        alternates=["mujoco"],
        instrument_validation={
            "method": "NONE_IN_THIS_ENVIRONMENT",
            "note": "Chrono ships unit/regression tests; not replayed "
                    "here (Art. XXV)",
        },
    ),
    _record(
        solver_id="openems",
        layer="ELECTROMAGNETICS",
        role="electrical and electromagnetic behavior (openEMS, "
             "FDTD)",
        phenomena=["electromagnetic_fields_highfreq"],
        version="openems/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("openems", "openems"),
        alternates=["elmer"],
        instrument_validation={
            "method": "NONE_IN_THIS_ENVIRONMENT",
            "note": "openEMS ships validation examples; not replayed "
                    "here (Art. XXV)",
        },
    ),
    _record(
        solver_id="openmdao",
        layer="OPTIMIZATION",
        role="automated design-parameter search against physical "
             "objectives",
        phenomena=[],  # orchestrates solvers; produces no physics evidence
        version="openmdao/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("openmdao", "openmdao"),
        alternates=[],
        instrument_validation={
            "method": "NOT_APPLICABLE_ORCHESTRATION",
            "note": "an optimization layer's outputs are design points; "
                    "the physics content of each point is whatever the "
                    "underlying solver computed (COMPUTATIONAL_RESULT)",
        },
    ),
    _record(
        solver_id="sofa_blender_bridge",
        layer="VISUALIZATION_BRIDGE",
        role="bring simulated motion/results into Blender for "
             "high-quality rendering",
        phenomena=[],  # transport of results, never computation
        version="sofa-blender-bridge/DECLARED_VERSION_AT_INSTALL",
        availability=_probe_state("sofa", "sofa", "sofa_python"),
        alternates=[],
        instrument_validation={
            "method": "NOT_APPLICABLE_TRANSPORT",
            "note": "the bridge moves solver outputs into the rendering "
                    "layer; byte-identity of transported results is the "
                    "bridge's only correctness property",
        },
    ),
    _record(
        solver_id="hydraulic_network_1d",
        layer="CFD_FLUIDS",
        role="the R394 V0: 1D laminar incompressible network flow "
             "(Poiseuille conductances + mass conservation) — the ONE "
             "deterministic solver already built into the engine, "
             "reference-validated by closed-form replay",
        phenomena=["laminar_incompressible_network_flow"],
        version="hydraulic_network_1d/1.0.0",
        availability=_probe_state("hydraulic_network_1d",
                                  "hydraulic_network_1d"),
        alternates=[],
        instrument_validation=_V0_VALIDATION,
        notes="exists since R394 (discovery_fabric/engine/physics_core.py); "
              "registered into the stack as the first execution-capable "
              "member — the stack generalizes the V0 pattern, it does "
              "not replace it (Art. LXIV discipline: the V0 is not "
              "superseded, it is a member)",
    ),
]

_BY_ID = {r["solver_id"]: r for r in SOLVER_REGISTRY}


def get_solver(solver_id: str) -> Optional[Dict[str, Any]]:
    return _BY_ID.get(solver_id)


def solvers_for_phenomenon(phenomenon_class: str) -> List[Dict[str, Any]]:
    """Deterministic (registry-order) list of solvers declaring the
    phenomenon class. Visualization/orchestration records never appear
    here because their phenomenon_classes lists are empty by schema."""
    return [r for r in SOLVER_REGISTRY
            if phenomenon_class in r["phenomenon_classes"]]


def validate_registry() -> List[str]:
    """Adversarial self-check (Art. XVI/XVII/XVIII: code is a hypothesis
    about enforcement; this function is the enforcement evidence).
    Returns a list of violations — EMPTY means valid."""
    v: List[str] = []
    seen_ids = set()
    for rec in SOLVER_REGISTRY:
        sid = rec.get("solver_id")
        if not sid:
            v.append("solver record without solver_id")
            continue
        if sid in seen_ids:
            v.append(f"duplicate solver_id {sid!r}")
        seen_ids.add(sid)
        for field in REQUIRED_SOLVER_FIELDS:
            if field not in rec:
                v.append(f"{sid}: missing required field {field!r}")
        if rec.get("execution_evidence_class") != EXECUTION_EVIDENCE_CLASS:
            v.append(f"{sid}: execution_evidence_class must be pinned "
                     f"to {EXECUTION_EVIDENCE_CLASS!r} (Art. XXXVIII "
                     "layer 4 — the stack computes, it never observes)")
        if rec.get("layer") not in STACK_LAYERS:
            v.append(f"{sid}: unknown layer {rec.get('layer')!r}")
        for ph in rec.get("phenomenon_classes", []):
            if ph in FORBIDDEN_PHENOMENON_CLASSES:
                v.append(f"{sid}: forbidden phenomenon class {ph!r} — "
                         "'never claim all laws of physics' is a schema "
                         "constraint (operator crucial rule)")
        av = rec.get("availability") or {}
        if av.get("state") not in ("INSTALLED", "PROBED_NOT_INSTALLED"):
            v.append(f"{sid}: availability state {av.get('state')!r} is "
                     "not a measured state — availability may never be "
                     "assumed (Art. VI)")
        if av.get("state") == "INSTALLED" and not av.get("measured_at"):
            v.append(f"{sid}: INSTALLED without a probe timestamp "
                     "(Art. VI: measured, not assumed)")
        if not rec.get("solver_version"):
            v.append(f"{sid}: solver_version required (Art. LXII)")
        if not rec.get("instrument_validation"):
            v.append(f"{sid}: instrument_validation declaration required")
    # the operator's preferred stack must be represented (directive
    # fidelity check: every named tool has a record)
    for required in ("blender", "mujoco", "openfoam", "fenicsx", "sfepy",
                     "elmer", "sofa", "project_chrono", "openems",
                     "openmdao", "sofa_blender_bridge",
                     "hydraulic_network_1d"):
        if required not in _BY_ID:
            v.append(f"operator preferred stack member missing: "
                     f"{required!r}")
    return v
