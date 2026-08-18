"""
epistemic_integrity/evidence_classes.py — 9-class evidence taxonomy

Per CEO directive:
  "The final dossier needs a more restrictive evidence taxonomy.
   PRIMARY_OBSERVED / SECONDARY_REPORTED / MODEL_DERIVED / SIMULATION_DERIVED /
   INTERNAL_INFERENCE / HYPOTHESIS / ESTIMATE / ASSUMPTION / UNKNOWN / SUPERSEDED
   Then enforce wording."

This module defines the taxonomy and ENFORCES the wording that each class
is allowed to use in the final dossier.
"""

from enum import Enum
from typing import Dict, List, Set


class EvidenceClass(str, Enum):
    """9-class evidence taxonomy. SUPERSEDED is a state, not a class, but
    included here for wording enforcement on historical claims."""
    PRIMARY_OBSERVED = "PRIMARY_OBSERVED"           # Direct experiment by us
    SECONDARY_REPORTED = "SECONDARY_REPORTED"       # Literature reports observation
    MODEL_DERIVED = "MODEL_DERIVED"                  # Mathematical/analytical model
    SIMULATION_DERIVED = "SIMULATION_DERIVED"        # Monte Carlo / numerical simulation
    INTERNAL_INFERENCE = "INTERNAL_INFERENCE"        # Logical inference from other evidence
    HYPOTHESIS = "HYPOTHESIS"                        # Unproven proposal
    ESTIMATE = "ESTIMATE"                            # Rough calculation
    ASSUMPTION = "ASSUMPTION"                        # Stated assumption
    UNKNOWN = "UNKNOWN"                              # Not established
    SUPERSEDED = "SUPERSEDED"                        # Historical only, replaced


# MANDATORY wording per class. The dossier compiler must use these phrases.
MANDATORY_WORDING: Dict[EvidenceClass, List[str]] = {
    EvidenceClass.PRIMARY_OBSERVED: [
        "the experiment observed",
        "we observed",
        "the benchtop measurement showed",
    ],
    EvidenceClass.SECONDARY_REPORTED: [
        "the literature reports",
        "PMID",
        "patent",
        "the published study reported",
    ],
    EvidenceClass.MODEL_DERIVED: [
        "the model estimated",
        "the analytical model predicts",
    ],
    EvidenceClass.SIMULATION_DERIVED: [
        "the simulation estimated",
        "the Monte Carlo simulation produced",
    ],
    EvidenceClass.INTERNAL_INFERENCE: [
        "we infer",
        "internal analysis suggests",
    ],
    EvidenceClass.HYPOTHESIS: [
        "we hypothesize",
        "the proposed mechanism would",
    ],
    EvidenceClass.ESTIMATE: [
        "we estimate",
        "approximately",
    ],
    EvidenceClass.ASSUMPTION: [
        "the model assumes",
        "we assume",
    ],
    EvidenceClass.UNKNOWN: [
        "not established",
        "unknown",
    ],
    EvidenceClass.SUPERSEDED: [
        "[SUPERSEDED]",
        "[HISTORICAL ONLY]",
    ],
}

# FORBIDDEN wording per class. Dossier compiler REJECTS these combinations.
FORBIDDEN_COMBINATIONS: Dict[EvidenceClass, List[str]] = {
    EvidenceClass.MODEL_DERIVED: [
        "demonstrates",      # models don't demonstrate
        "proves",
        "shows",
        "observed",
        "confirmed",
    ],
    EvidenceClass.SIMULATION_DERIVED: [
        "demonstrates",
        "proves",
        "shows",
        "observed",
        "confirmed",
        "clinical",
    ],
    EvidenceClass.HYPOTHESIS: [
        "demonstrates",
        "proves",
        "shows",
        "confirmed",
        "established",
    ],
    EvidenceClass.ESTIMATE: [
        "demonstrates",
        "proves",
        "exact",
        "precisely",
    ],
    EvidenceClass.ASSUMPTION: [
        "demonstrates",
        "proves",
        "observed",
        "confirmed",
        "established",
    ],
    EvidenceClass.UNKNOWN: [
        "demonstrates",
        "proves",
        "shows",
        "confirmed",
        "established",
    ],
    EvidenceClass.SUPERSEDED: [
        # SUPERSEDED claims CANNOT use present-tense assertions
        "is",  # when used as current-state assertion
        "currently",
        "now",
    ],
}

# Evidence class hierarchy for "strength" comparison
CLASS_STRENGTH: Dict[EvidenceClass, int] = {
    EvidenceClass.PRIMARY_OBSERVED: 9,
    EvidenceClass.SECONDARY_REPORTED: 8,
    EvidenceClass.MODEL_DERIVED: 6,
    EvidenceClass.SIMULATION_DERIVED: 5,
    EvidenceClass.INTERNAL_INFERENCE: 4,
    EvidenceClass.ESTIMATE: 3,
    EvidenceClass.HYPOTHESIS: 2,
    EvidenceClass.ASSUMPTION: 2,
    EvidenceClass.UNKNOWN: 0,
    EvidenceClass.SUPERSEDED: -1,  # cannot be used as current evidence
}


def validate_wording(claim_text: str, evidence_class: EvidenceClass) -> dict:
    """Validate that claim_text uses allowed wording for its evidence class.

    Returns dict with:
      - valid: bool
      - mandatory_wording_found: bool (at least one allowed phrase present)
      - forbidden_wording_found: list of forbidden phrases found
      - violations: list of specific violations
    """
    text_lower = claim_text.lower()

    mandatory = MANDATORY_WORDING.get(evidence_class, [])
    forbidden = FORBIDDEN_COMBINATIONS.get(evidence_class, [])

    mandatory_found = any(phrase.lower() in text_lower for phrase in mandatory)
    forbidden_found = [phrase for phrase in forbidden if phrase.lower() in text_lower]

    violations = []
    if not mandatory_found:
        violations.append(f"MISSING_MANDATORY_WORDING: must use one of {mandatory}")
    if forbidden_found:
        violations.append(f"FORBIDDEN_WORDING_FOUND: {forbidden_found}")

    return {
        "valid": len(violations) == 0,
        "mandatory_wording_found": mandatory_found,
        "forbidden_wording_found": forbidden_found,
        "violations": violations,
    }


def can_support_claims(evidence_class: EvidenceClass) -> bool:
    """SUPERSEDED evidence CANNOT support any current claim."""
    return evidence_class != EvidenceClass.SUPERSEDED


def min_evidence_class_for_dossier() -> Set[EvidenceClass]:
    """Which evidence classes are allowed in the final dossier?
    PRIMARY_OBSERVED, SECONDARY_REPORTED, MODEL_DERIVED, SIMULATION_DERIVED are
    allowed. HYPOTHESIS, ESTIMATE, ASSUMPTION, UNKNOWN are allowed ONLY if
    explicitly labeled as such (not presented as established fact).
    SUPERSEDED is NEVER allowed."""
    return {
        EvidenceClass.PRIMARY_OBSERVED,
        EvidenceClass.SECONDARY_REPORTED,
        EvidenceClass.MODEL_DERIVED,
        EvidenceClass.SIMULATION_DERIVED,
        EvidenceClass.INTERNAL_INFERENCE,
        EvidenceClass.HYPOTHESIS,
        EvidenceClass.ESTIMATE,
        EvidenceClass.ASSUMPTION,
        EvidenceClass.UNKNOWN,
    }
