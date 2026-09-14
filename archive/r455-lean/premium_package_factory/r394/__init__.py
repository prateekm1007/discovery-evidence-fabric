"""R394 — Truth and semantics layer for the premium package factory.

CEO directive R392/R393 (updated): make the product truthful, semantically
clear, and genuinely end-to-end. This package implements the engine-side
semantics without touching the epistemic machinery of the discovery loop:

  canonical_corrections  V3 correction overlay (recorded, auditable,
                         exact-match only — extends the V2 mutation
                         apparatus to structural corrections)
  evidence_classes       the 5-way evidence classification and the
                         four-question mechanism evidence record
  decisive_experiment    the decisive work package derived from the
                         dominant kill condition (never the first WP)
  validation_states      the CAD/engineering validation state SPLIT
                         (never PRESENT_AND_VALIDATED as one blob)
  release_gates          four HARD release gates:
                           MECHANISM_CLAIM_WITHOUT_GEOMETRIC_IMPLEMENTATION
                           DECISIVE_EXPERIMENT_INVALID
                           NO_MISSING_REFERENCED_ARTIFACTS
                           SAFETY_EQUATION_STRUCTURALLY_BROKEN
"""
