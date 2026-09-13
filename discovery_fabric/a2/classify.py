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
    # R376 (CEO prior-art differentiation + resolution directive):
    # RESOLVED_ANTICIPATED is a search-derived specific-disclosure-class
    # finding — a prior-art family whose claim/abstract text covers the
    # candidate's mechanism AND >= 80% of its distinguishing terms
    # (thresholds declared in collision_resolution.THRESHOLDS, per-family
    # evidence recorded in collision_results.differentiation_resolution).
    # It kills promotion exactly like SPECIFIC_DISCLOSURE, with the
    # evidence trail recorded; it is NOT a novelty determination
    # (Art. XXVIII limitation carried inline in the resolution record).
    "RESOLVED_ANTICIPATED",
}

# Prior-art states that do NOT kill (Item 4)
NON_KILL_STATES = {
    "NO_MATCH_FOUND",
    "TOPICAL_RELATED",
    "POSSIBLE_RELEVANCE",
    "UNRESOLVED_INSUFFICIENT_EVIDENCE",
    # R376 resolution states (collision_resolution.py):
    # the position is resolved with surviving differentiators — the
    # candidate MAY promote (attack/adjudication still apply)
    "RESOLVED_DIFFERENTIATED",
    # honest unresolved states — never converted either way (Art. XXV)
    "UNRESOLVED_PARTIAL_EVIDENCE",
    "UNRESOLVED_NO_RELEVANT_ART",
    # R394 s2: a mandatory (query_class x source) search failed — the
    # searched universe is incomplete. Findings stand as evidence, but
    # NO absence/differentiation conclusion is permitted (non-kill,
    # unknown — replaces the measured false RESOLVED_DIFFERENTIATED on
    # partial-search failures, production run ts_d1ab9fd4d756).
    "UNRESOLVED_SEARCH_INCOMPLETE",
    # scientific-side search-execution states (a2/prior_art.py R394):
    # outages and partial outages are UNKNOWN, never no-match
    "SEARCH_FAILED",
    "SEARCH_PARTIAL",
}


def classify(candidate: dict, evidence_verification: dict, prior_art: dict, adversarial: dict) -> dict:
    """Step 7: Assign epistemic state. No silent promotion.

    PRIOR_ART_KILL_REQUIRES_SPECIFIC_DISCLOSURE = TRUE (Item 10a)
    Only SPECIFIC_DISCLOSURE or IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE may kill.
    TOPICAL_RELATED, POSSIBLE_RELEVANCE, NO_MATCH_FOUND do NOT kill.

    R402 (audit NF-2, Art. XXV/LXI): an UNEVALUATED verification (the
    VERIFY stage never ran — skipped, disabled, or failed upstream) is
    NOT negative knowledge. Converting "never evaluated" into
    REJECTED/"evidence verification failed" manufactures negative
    knowledge from an infrastructure state and contaminates the
    scientific statistics (the audit reproduced it: VERIFY+SYNTHESIZE
    disabled -> final REJECTED). The honest outcome is UNKNOWN with
    the stage state named; only an evaluation that ACTUALLY RAN and
    failed may reject — and then it must say WHY (the issues).
    """
    state = "OBSERVED"

    # Can only promote if evidence is verified
    if not evidence_verification.get("verified"):
        # distinguish EVALUATED-AND-FAILED from NEVER-EVALUATED
        # (Art. XXV/LXI): a verification record that exists and carries
        # an evaluation is negative knowledge; an absent/empty record
        # means the stage never produced one — UNKNOWN, rerunnable
        evaluated = bool(evidence_verification) and (
            "verified" in evidence_verification
            or evidence_verification.get("state") not in (
                None, "NOT_RUN", "SKIPPED", "DISABLED", ""))
        if not evaluated:
            return {
                "epistemic_state": "OBSERVED", "final_status": "UNKNOWN",
                "reason": ("evidence verification NOT_EVALUATED — the "
                           "verification stage did not produce a verdict "
                           "(skipped/disabled/upstream failure); not a "
                           "scientific verdict, never negative knowledge "
                           "(Art. XXV/LXI); rerunnable"),
                "promotion_blocked": True, "adjudication_blocked": True,
                "verification_state": "NOT_EVALUATED"}
        issues = evidence_verification.get("issues") or []
        issue_text = "; ".join(str(i) for i in issues[:5]) or "no issues recorded"
        # R452 (external audit B1-engine-half, Art. LXI): the
        # output-contract issue classes (the proposer model failed to
        # emit a verbatim span / any span at all) are CAPABILITY
        # failures of the generation transport, not scientific
        # properties of the candidate. They are typed
        # INFRASTRUCTURE_CAPABILITY and recorded as
        # INCOMPLETE_INFERENCE_FAILURE — the candidate is STILL NOT
        # PROMOTED (the verifier is not weakened, Art. VII), but the
        # failure is never laundered into a scientific REJECTED verdict
        # (the R451 defect: 4 of 7 production runs carried
        # 'missing_source_span' as the invention's kill_reason).
        _CAPABILITY_ISSUES = {
            "missing_source_span", "mechanism_span_not_verbatim",
            "missing_mechanism_span", "missing_source_id",
            "missing_source_hash"}
        if issues and set(issues) <= _CAPABILITY_ISSUES:
            return {
                "epistemic_state": "OBSERVED",
                "final_status": "INCOMPLETE_INFERENCE_FAILURE",
                "failure_class": "INFRASTRUCTURE_CAPABILITY",
                "reason": (
                    f"model output contract failure: {issue_text} — "
                    "the proposer model did not emit a verbatim "
                    "evidence-bound span; an INFRASTRUCTURE CAPABILITY "
                    "state, never a scientific rejection (Art. LXI); "
                    "the candidate remains unpromoted and the run "
                    "rerunnable on a capable route"),
                "promotion_blocked": True,
                "verification_state": "EVALUATED_FAILED_CAPABILITY",
            }
        return {"epistemic_state": "OBSERVED", "final_status": "REJECTED",
                "reason": (f"evidence verification failed: {issue_text}"),
                "promotion_blocked": True,
                "verification_state": "EVALUATED_FAILED"}

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

    # ===== Art. XXV separation: non-scientific adversarial states =======
    # The adversarial challenge may end WITHOUT a scientific verdict about
    # the candidate: the evaluator transport failed (EVALUATOR_CALL_
    # FAILED), the evidence gate skipped it (NOT_RUN), or the evaluator
    # produced an internally invalid verdict (EVALUATION_FAILED). None of
    # these states is evidence AGAINST the candidate — converting them
    # into final_status REJECTED would manufacture negative knowledge from
    # an infrastructure failure (Art. XXI.3/XXV: provider failure is not
    # absence; unknown stays unknown). The honest outcome is UNKNOWN with
    # adjudication blocked: promotion is refused AND the cemetery is NOT
    # written (the conductor only records negative knowledge on REJECTED).
    # The run stays rerunnable — a later attempt with a healthy evaluator
    # can still adjudicate the candidate either way.
    NON_SCIENTIFIC_ADVERSARIAL = {
        "EVALUATOR_CALL_FAILED",   # transport: timeout / rate limit / error
        "NOT_RUN",                 # evidence gate skipped the challenge
        "EVALUATION_FAILED",       # evaluator verdict internally invalid
    }
    adv_overall = adversarial.get("overall", "")
    if adv_overall in NON_SCIENTIFIC_ADVERSARIAL:
        return {
            "epistemic_state": "CANDIDATE_CONNECTION",
            "final_status": "UNKNOWN",
            "reason": (
                f"adversarial adjudication incomplete: {adv_overall} — "
                "infrastructure/evaluator state, NOT a scientific verdict "
                "(Art. XXV); rerunnable, never negative knowledge"),
            "promotion_blocked": True,
            "adjudication_blocked": True,
            "adversarial_overall": adv_overall,
        }

    # Check adversarial — Item 11: adversarial firewall
    # Adversarial may NOT convert TOPICAL_RELATED or POSSIBLE_RELEVANCE into prior-art kill
    if adversarial.get("overall") != "PASS":
        # R402 (audit CB-6): the terminal reason must carry the kill
        # dimensions — never an empty trailing colon. The kill basis
        # lives in adversarial["attacks"] (dimension -> verdict text);
        # surface it when the top-level reason is absent or thin.
        attacks = adversarial.get("attacks", {})
        killed_dims = [k for k, v in attacks.items()
                       if "KILLED" in str(v).upper()]
        dim_detail = ", ".join(
            f"{k}: {str(attacks[k])[:80]}" for k in killed_dims)
        adv_reason = str(adversarial.get("reason", "") or "").strip()
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
                other_detail = ", ".join(
                    f"{k}: {str(attacks[k])[:80]}" for k in other_kills)
                return {"epistemic_state": "CANDIDATE_CONNECTION", "final_status": "REJECTED",
                        "reason": (f"adversarial challenge failed: "
                                   f"{other_detail}"),
                        "promotion_blocked": True}
        else:
            detail = adv_reason or dim_detail or "no kill basis recorded"
            reason = (f"adversarial challenge failed: {detail}")
            if dim_detail and dim_detail.lower() not in adv_reason.lower():
                reason = (f"{reason}; killed dimensions: {dim_detail}")
            return {"epistemic_state": "CANDIDATE_CONNECTION", "final_status": "REJECTED",
                    "reason": reason,
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
