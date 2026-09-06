"""discovery_fabric.physics_stack — R413 Physics Stack V1 (the
computational engineering layer behind the 3D/visualization surface).

OPERATOR DIRECTIVE (2026-09-06, recorded verbatim in
R413/PHYSICS_STACK_V1/OPERATOR_DIRECTIVE.json):

  "Blender should be the visualization/geometry layer, not the 'all
   physics' engine." The system is a MULTI-SOLVER physics stack:
   Blender (3D/rendering) + MuJoCo (rigid body) + OpenFOAM (CFD/
   thermal) + FEniCSx/SfePy/Elmer (structural FEM) + SOFA (soft body)
   + Project Chrono (multibody) + Elmer/openEMS (electromagnetics)
   + OpenMDAO (optimization), with the AI deciding which solver(s) a
   proposed invention actually requires.

  The crucial rule: NEVER claim "all laws of physics." No software
  stack can guarantee that. Instead build a Physics Coverage Registry:
      phenomenon -> governing equations -> solver -> assumptions ->
      validated regime -> uncertainty -> simulation result
  so the machine can say "Validated: incompressible turbulent flow,
  Re=18,400, specified geometry and boundary conditions" rather than
  "Physics verified."

CONSTITUTIONAL MAPPING (v2.1.0):
- Art. LV stage COMPUTATIONAL VALIDATION — this package is that
  stage's machinery (the pipeline contracts here implement the
  operator's sequence: AI invention -> physical hypothesis -> 3D
  geometry -> solver selection -> simulation -> measurement
  extraction -> falsification -> redesign -> simulation -> dossier).
- Art. XXXVIII / Art. LIII — every solver output is a
  COMPUTATIONAL_RESULT (evidence layer 4) and may NEVER be cited as
  physical observation; enforced in solver_registry (registration
  schema) and pipeline (emission guard).
- Art. XXVIII — a passing simulation is not a physical finding; the
  coverage registry's validated_regime is regime-scoped by
  construction, and claim evaluation rejects global overclaims.
- Art. XXVII — assumptions and thresholds carried with epistemic
  class + justification, never silently drifted.
- Art. IV — no fallback epistemology: a phenomenon with no
  registered, measured-available solver is MECHANISM_NOT_SIMULATABLE,
  never a forced analogy onto an available solver.
- Art. VI / Art. XXV — solver availability is MEASURED (probes in
  R413/PHYSICS_STACK_V1/SOLVER_AVAILABILITY_PROBES.json); unknown
  stays unknown; not-installed is an honest state.
- Art. LXII — solver_version is part of every result's
  reproducibility record.

V1 DELIVERS: the solver registry, the Physics Coverage Registry, the
deterministic selection layer, the 11-stage pipeline contracts, and
the claim-language contract. V1 EXECUTES: nothing except the V0
hydraulic solver's deterministic closed-form replay (the only
installed solver — measured). Blender renders and CFD/FEM/EM runs
are CONTRACTS in this version, not capabilities (Art. VI).
"""
from discovery_fabric.physics_stack.solver_registry import (
    EXECUTION_EVIDENCE_CLASS,
    FORBIDDEN_PHENOMENON_CLASSES,
    REQUIRED_SOLVER_FIELDS,
    SOLVER_REGISTRY,
    get_solver,
    solvers_for_phenomenon,
    validate_registry,
)
from discovery_fabric.physics_stack.coverage import (
    SCHEMA_FIELDS_V1,
    ENTRY_EPISTEMIC_CLASS,
    evaluate_physics_claim,
    load_coverage_registry,
    validate_coverage_registry,
    simulatable_phenomena,
)
from discovery_fabric.physics_stack.selection import (
    PHENOMENON_VOCABULARY,
    select_solvers,
)
from discovery_fabric.physics_stack.pipeline import (
    PIPELINE_STAGES,
    validate_stage_output,
)
from discovery_fabric.physics_stack.mechanism_physics import (
    classify_mechanism,
    verify_proposed_classification,
    PHYSICS_DOMAINS,
    CLASSIFICATION_LABELS,
)
from discovery_fabric.physics_stack.routing import route_mechanism
from discovery_fabric.physics_stack.geometry_authority import (
    validate_geometry_spec,
    validate_render_record,
    cadquery_measured_state,
)
from discovery_fabric.physics_stack.opportunity import (
    compute_opportunity_score,
)

__all__ = [
    "EXECUTION_EVIDENCE_CLASS", "FORBIDDEN_PHENOMENON_CLASSES",
    "REQUIRED_SOLVER_FIELDS", "SOLVER_REGISTRY", "get_solver",
    "solvers_for_phenomenon", "validate_registry",
    "SCHEMA_FIELDS_V1", "ENTRY_EPISTEMIC_CLASS",
    "evaluate_physics_claim", "load_coverage_registry",
    "validate_coverage_registry", "simulatable_phenomena",
    "PHENOMENON_VOCABULARY", "select_solvers",
    "PIPELINE_STAGES", "validate_stage_output",
    "classify_mechanism", "verify_proposed_classification",
    "PHYSICS_DOMAINS", "CLASSIFICATION_LABELS",
    "route_mechanism", "validate_geometry_spec",
    "validate_render_record", "cadquery_measured_state",
    "compute_opportunity_score",
]
