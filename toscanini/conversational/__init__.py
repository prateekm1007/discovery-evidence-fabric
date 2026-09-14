"""toscanini/conversational — R446-C1: the conversational orchestration
layer ABOVE the canonical discovery pipeline.

Operator directive (CODER 1 — DISCOVERY INTELLIGENCE / CLAUDE-LIKE
PROBLEM PROCESSING): make Toscanini behave like one intelligent
conversational discovery engine rather than a user-operated sequence
of internal stages.

Constitutional contract (this layer NEVER violates):
  - Art. X (one canonical state): every object here is a PROJECTION of
    the run directory's persisted artifacts or a typed POLICY DECISION
    recorded before execution — never a second truth store.
  - Art. XXV (unknown remains unknown): a policy skip is a RECORDED
    refusal with a typed reason, never an absence claim.
  - Art. XXVIII (no silent semantic promotion): inferred fields stay
    INFERRED; conversation context never promotes scientific state.
  - Art. LVI (optimize for information gain): the stage policy and the
    NBA controller score expected information gain against cost.
  - Art. LXI (infrastructure failure is never scientific rejection):
    the six non-execution states keep infrastructure and science
    distinct in every projection.

The canonical scientific loop and the engine STAGE_ORDER are
UNCHANGED (ACTIVE_PATH.md is the authority). This layer makes them
adaptive, selectively executed, and cleanly consumable by the product.
"""
from __future__ import annotations

CONVERSATIONAL_LAYER_VERSION = "toscanini/conversational/1.0.0"

__all__ = [
    "problem_understanding",
    "clarification",
    "stage_policy",
    "nba_controller",
    "product_events",
    "run_contract",
    "conversation_memory",
    "model_provenance",
]
