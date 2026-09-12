"""DIRECTIONAL — the Directional Improvement Engine (R450).

The canonical loop:
    EVIDENCE -> MECHANISM -> CANDIDATE -> ATTACK -> FAILURE
    -> CAUSAL DIAGNOSIS -> DIRECTIONAL HYPOTHESIS (ground-gated)
    -> CONTROLLED MUTATION -> EVALUATION -> OBSERVATION
    -> CAUSAL UPDATE -> NEXT DIRECTION

Public API:
    directional_step(...)          diagnosis -> gated hypothesis
    record_directional_outcome(...) evaluation -> observation -> update
    record_unguided_outcome(...)   the benchmark's control arm
    directional_enabled()          the channel flag
    evolution_mode()               DIRECTIONAL | LEGACY | UNGUIDED

Design constraints honored (the directive's forbidden list):
  no giant model, no second engine, no second canonical database —
  the directional layer REFERENCES the engine's own generation
  records and persists only its own typed records.
"""
from discovery_fabric.directional.hypothesis import (
    DIRECTIONS, INTERVENTION_CLASSES, HYPOTHESIS_STATUSES,
    DirectionalHypothesis, apply_gate, ground_gate,
    make_hypothesis_id, propose_directional_hypothesis,
)
from discovery_fabric.directional.loop import (
    directional_enabled, directional_step, evolution_mode,
    record_directional_outcome, record_unguided_outcome,
    serve_evidence_gaps,
)
from discovery_fabric.directional.observation import (
    EPISTEMIC_STATES, causal_update, extract_observation,
    improvement_signal, sensitivity_from_evaluations,
)
from discovery_fabric.directional.trajectory import (
    append_step, load_trajectory, trajectory_summary,
)

DIRECTIONAL_ENGINE_VERSION = "directional_engine/1.0.0"

__all__ = [
    "DIRECTIONAL_ENGINE_VERSION", "DIRECTIONS", "INTERVENTION_CLASSES",
    "HYPOTHESIS_STATUSES", "DirectionalHypothesis", "apply_gate",
    "ground_gate", "make_hypothesis_id",
    "propose_directional_hypothesis", "directional_enabled",
    "directional_step", "evolution_mode", "record_directional_outcome",
    "record_unguided_outcome", "serve_evidence_gaps",
    "EPISTEMIC_STATES", "causal_update", "extract_observation",
    "improvement_signal", "sensitivity_from_evaluations", "append_step",
    "load_trajectory", "trajectory_summary",
]
