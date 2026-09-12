"""Toscanini Visual Feedback Layer — canonical trajectory projection (R450-C2).

Coder 2 boundary (operator directive R450-C2): the visual layer PRESENTS and
INTERROGATES the engineering truth Coder 1 establishes. It never owns it.

    visual presentation is not engineering validation.

The projection consumes ONLY canonical state (the engine's
INVENTION_LINEAGE.json evolution records — Coder 1's improvement loop) and
produces a deterministic presentation record for the trajectory viewer:

    V1 -> FAILURE -> CAUSE -> DIRECTION -> MUTATION -> V2 -> MEASURED CHANGE

Every element carries an epistemic badge derived fail-closed from the
element's OWN provenance fields (Art. III — the verifier never trusts the
claimant); unknown stays unknown (Art. XXV); no physics is interpreted
here (Art. XXVIII — no silent semantic promotion); the lineage's own
INVENTION_* status vocabulary is carried VERBATIM and never re-labeled
(Art. X; the R433 projection discipline).

Determinism contract: the same canonical lineage bytes project to the
byte-identical trajectory record (no timestamps, no generated ids, sorted
keys) — the visual regression battery holds this mechanically.
"""

from .schema import (
    BADGE_INFERRED,
    BADGE_MEASURED,
    BADGE_PROPOSED,
    BADGE_SIMULATED,
    BADGE_UNVERIFIED,
    EPISTEMIC_BADGES,
    PREDICTION_OUTCOMES,
    TRAJECTORY_SCHEMA_ID,
    TRAJECTORY_SCHEMA_VERSION,
    TrajectoryProjectionError,
    canonical_json,
    derive_badge,
    project_sensitivity,
    project_trajectory,
)

__all__ = [
    "BADGE_INFERRED",
    "BADGE_MEASURED",
    "BADGE_PROPOSED",
    "BADGE_SIMULATED",
    "BADGE_UNVERIFIED",
    "EPISTEMIC_BADGES",
    "PREDICTION_OUTCOMES",
    "TRAJECTORY_SCHEMA_ID",
    "TRAJECTORY_SCHEMA_VERSION",
    "TrajectoryProjectionError",
    "canonical_json",
    "derive_badge",
    "project_sensitivity",
    "project_trajectory",
]
