"""A2 classify — epistemic state classification."""
from __future__ import annotations

# Epistemic state hierarchy (no silent promotion)
STATES = [
    "OBSERVED",
    "INFERRED",
    "ANALOGY",
    "CANDIDATE_CONNECTION",
    "MECHANISTIC_HYPOTHESIS",
    "EXPERIMENTAL_PROPOSAL",
    "INVENTION_CANDIDATE",
]

def classify(candidate: dict, evidence_verification: dict, prior_art: dict, adversarial: dict) -> dict:
    """Step 7: Assign epistemic state. No silent promotion."""
    # Start at OBSERVED (evidence was retrieved)
    state = "OBSERVED"

    # Can only promote if evidence is verified
    if not evidence_verification.get("verified"):
        return {"epistemic_state": "OBSERVED", "final_status": "REJECTED",
                "reason": "evidence verification failed", "promotion_blocked": True}

    state = "INFERRED"

    # Check prior art
    pa_status = prior_art.get("prior_art_status", "UNKNOWN")
    if pa_status == "LIKELY_PRIOR_ART_EXISTS":
        return {"epistemic_state": "INFERRED", "final_status": "REJECTED",
                "reason": "prior art likely exists", "promotion_blocked": True}
    if pa_status == "UNKNOWN":
        return {"epistemic_state": "INFERRED", "final_status": "UNKNOWN",
                "reason": "prior art unknown — cannot promote", "promotion_blocked": True}

    state = "CANDIDATE_CONNECTION"

    # Check adversarial
    if adversarial.get("overall") != "PASS":
        return {"epistemic_state": "CANDIDATE_CONNECTION", "final_status": "REJECTED",
                "reason": f"adversarial challenge failed: {adversarial.get('reason', '')}",
                "promotion_blocked": True}

    state = "MECHANISTIC_HYPOTHESIS"

    # Check falsification test exists
    if not candidate.get("falsification_test") or len(candidate["falsification_test"]) < 10:
        return {"epistemic_state": "MECHANISTIC_HYPOTHESIS", "final_status": "REJECTED",
                "reason": "no concrete falsification test", "promotion_blocked": True}

    state = "EXPERIMENTAL_PROPOSAL"

    # All checks passed → INVENTION_CANDIDATE
    state = "INVENTION_CANDIDATE"
    final_status = "INVENTION_CANDIDATE"

    result = {
        "epistemic_state": state,
        "final_status": final_status,
        "reason": "all checks passed: evidence verified, no prior art, adversarial survived, falsification concrete",
        "promotion_blocked": False,
        "state_history": ["OBSERVED", "INFERRED", "CANDIDATE_CONNECTION", "MECHANISTIC_HYPOTHESIS", "EXPERIMENTAL_PROPOSAL", "INVENTION_CANDIDATE"],
    }
    print(f"  [classify] state={state} status={final_status}")
    return result
