"""A2 classify — epistemic state classification with corrected prior-art state machine."""
from __future__ import annotations

# Epistemic state hierarchy (no silent promotion)
STATES = [
    "OBSERVED",
    "INFERRED",
    "ANALOGY",
    "CANDIDATE_CONNECTION",
    "MECHANISTIC_HYPOTHESIS",
    "EXPERIMENTAL_PROPOSAL",
    "AUTOMATED_INVENTION_CANDIDATE",  # Renamed from INVENTION_CANDIDATE per spec Item 2
]

# Prior-art states that AUTOMATICALLY kill (Item 4, Item 10a)
KILL_STATES = {
    "SPECIFIC_DISCLOSURE",
    "IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE",
}

# Prior-art states that do NOT kill (Item 4)
NON_KILL_STATES = {
    "NO_MATCH_FOUND",
    "TOPICAL_RELATED",
    "POSSIBLE_RELEVANCE",
    "UNRESOLVED_INSUFFICIENT_EVIDENCE",
}


def classify(candidate: dict, evidence_verification: dict, prior_art: dict, adversarial: dict) -> dict:
    """Step 7: Assign epistemic state. No silent promotion.
    
    PRIOR_ART_KILL_REQUIRES_SPECIFIC_DISCLOSURE = TRUE (Item 10a)
    Only SPECIFIC_DISCLOSURE or IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE may kill.
    TOPICAL_RELATED, POSSIBLE_RELEVANCE, NO_MATCH_FOUND do NOT kill.
    """
    state = "OBSERVED"

    # Can only promote if evidence is verified
    if not evidence_verification.get("verified"):
        return {"epistemic_state": "OBSERVED", "final_status": "REJECTED",
                "reason": "evidence verification failed", "promotion_blocked": True}

    state = "INFERRED"

    # Check prior art — Item 4 state machine
    pa_status = prior_art.get("prior_art_status", "UNKNOWN")
    
    # KILL states: only SPECIFIC_DISCLOSURE or IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE
    if pa_status in KILL_STATES:
        return {"epistemic_state": "INFERRED", "final_status": "REJECTED",
                "reason": f"prior art: {pa_status} — specific disclosure found",
                "promotion_blocked": True}
    
    # NON-KILL states: pass through
    if pa_status in NON_KILL_STATES:
        pass  # Continue to next gate
    elif pa_status == "LIKELY_PRIOR_ART_EXISTS":
        # OLD state — backwards compatibility, but should not be used in new runs
        # Per Item 4: this state is REPLACED entirely
        # For safety, treat as POSSIBLE_RELEVANCE (non-kill)
        pass
    elif pa_status == "UNKNOWN":
        return {"epistemic_state": "INFERRED", "final_status": "UNKNOWN",
                "reason": "prior art unknown — cannot promote", "promotion_blocked": True}
    elif pa_status == "PARTIAL_PRIOR_ART":
        pass  # Non-kill
    
    state = "CANDIDATE_CONNECTION"

    # Check adversarial — Item 11: adversarial firewall
    # Adversarial may NOT convert TOPICAL_RELATED or POSSIBLE_RELEVANCE into prior-art kill
    if adversarial.get("overall") != "PASS":
        # Check if the adversarial kill is based on prior art
        adv_reason = adversarial.get("reason", "").lower()
        attacks = adversarial.get("attacks", {})
        prior_art_attack = attacks.get("prior_art", "")
        
        # If prior_art state is non-kill, adversarial cannot use prior art to kill
        if pa_status in NON_KILL_STATES and "KILLED" in prior_art_attack.upper():
            # Adversarial tried to convert non-kill prior art into kill — BLOCK this
            # Check other dimensions independently
            other_kills = [k for k, v in attacks.items() if k != "prior_art" and "KILLED" in v.upper()]
            if not other_kills:
                # Only prior_art kill — but prior_art state is non-kill → don't kill
                pass  # Continue
            else:
                return {"epistemic_state": "CANDIDATE_CONNECTION", "final_status": "REJECTED",
                        "reason": f"adversarial challenge failed: {', '.join(other_kills)}",
                        "promotion_blocked": True}
        else:
            return {"epistemic_state": "CANDIDATE_CONNECTION", "final_status": "REJECTED",
                    "reason": f"adversarial challenge failed: {adv_reason}",
                    "promotion_blocked": True}

    state = "MECHANISTIC_HYPOTHESIS"

    # Check falsification test exists
    if not candidate.get("falsification_test") or len(candidate["falsification_test"]) < 10:
        return {"epistemic_state": "MECHANISTIC_HYPOTHESIS", "final_status": "REJECTED",
                "reason": "no concrete falsification test", "promotion_blocked": True}

    state = "EXPERIMENTAL_PROPOSAL"

    # All checks passed → AUTOMATED_INVENTION_CANDIDATE
    state = "AUTOMATED_INVENTION_CANDIDATE"
    final_status = "AUTOMATED_INVENTION_CANDIDATE"

    result = {
        "epistemic_state": state,
        "final_status": final_status,
        "reason": "all checks passed: evidence verified, no specific disclosure, adversarial survived, falsification concrete",
        "promotion_blocked": False,
        "state_history": ["OBSERVED", "INFERRED", "CANDIDATE_CONNECTION", "MECHANISTIC_HYPOTHESIS", "EXPERIMENTAL_PROPOSAL", "AUTOMATED_INVENTION_CANDIDATE"],
    }
    print(f"  [classify] state={state} status={final_status}")
    return result
