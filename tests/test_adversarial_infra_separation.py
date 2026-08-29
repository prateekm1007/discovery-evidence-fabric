"""Regression tests for the Art. XXV adversarial-infrastructure separation.

DEFECT (found live in the M1 campaign, 2026-08-29): when the adversarial
evaluator's LLM transport failed (EVALUATOR_CALL_FAILED), classify()
converted the infrastructure failure into final_status REJECTED —
manufacturing negative knowledge from a timeout (Art. XXI.3/XXV). The
conductor would then have written a FALSE cemetery entry.

FIX: non-scientific adversarial states (EVALUATOR_CALL_FAILED, NOT_RUN,
EVALUATION_FAILED) yield final_status UNKNOWN with adjudication_blocked —
promotion refused, cemetery NOT written, run rerunnable.

These tests pin the fix from both directions:
  - infrastructure failure MUST NOT kill (the defect)
  - a genuine scientific KILL verdict MUST still reject (Art. V: the
    verifier must not become a universal pass-through — fixing the defect
    may not weaken the real kill path)
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.a2.classify import classify  # noqa: E402

BASE_CANDIDATE = {
    "candidate_id": "cand:test:1",
    "mechanism": "osmotic gradient drives fluid transport",
    "intervention": "an osmotic layer on the device surface",
    "expected_effect": "reduced deposition",
    "falsification_test": "bench flow loop with dextran challenge 24 h",
    "mechanism_source_span": "osmotic gradient drives fluid transport",
}

VERIFIED = {"verified": True}
PRIOR_ART_OK = {"prior_art_status": "NO_MATCH_FOUND"}


def _adversarial(overall, **kw):
    out = {"overall": overall, "attacks": {}, "reason": kw.pop("reason", "")}
    out.update(kw)
    return out


# ------------------------------------------------ the defect, pinned

def test_evaluator_call_failed_is_not_a_reject():
    """THE DEFECT: transport timeout became REJECTED + cemetery material."""
    result = classify(BASE_CANDIDATE, VERIFIED, PRIOR_ART_OK,
                      _adversarial("EVALUATOR_CALL_FAILED",
                                   reason="LLM call failed"))
    assert result["final_status"] == "UNKNOWN"
    assert result["adjudication_blocked"] is True
    assert result["promotion_blocked"] is True
    assert "Art. XXV" in result["reason"]


def test_not_run_is_not_a_reject():
    result = classify(BASE_CANDIDATE, VERIFIED, PRIOR_ART_OK,
                      _adversarial("NOT_RUN"))
    assert result["final_status"] == "UNKNOWN"
    assert result["adjudication_blocked"] is True


def test_evaluation_failed_is_not_a_reject():
    """EVALUATION_FAILED = the evaluator produced an internally invalid
    verdict — an evaluator defect, not a candidate verdict (Art. XXIX)."""
    result = classify(BASE_CANDIDATE, VERIFIED, PRIOR_ART_OK,
                      _adversarial("EVALUATION_FAILED"))
    assert result["final_status"] == "UNKNOWN"
    assert result["adjudication_blocked"] is True


def test_conductor_cemetery_will_not_fire_on_unknown():
    """The conductor writes the cemetery only on final_status REJECTED.
    UNKNOWN from adjudication-block must therefore produce no negative
    knowledge (pins the run.py contract the fix depends on)."""
    result = classify(BASE_CANDIDATE, VERIFIED, PRIOR_ART_OK,
                      _adversarial("EVALUATOR_CALL_FAILED"))
    assert result["final_status"] != "REJECTED"


# ------------------------------------------------ the kill path, intact

def test_genuine_scientific_kill_still_rejects():
    """Art. V: fixing the defect must not weaken the real kill path. A
    scientific KILLED verdict from a working evaluator still rejects."""
    adv = _adversarial(
        "KILLED",
        attacks={"unsupported_mechanism": "KILLED",
                 "engineering_infeasibility": "KILLED"},
        reason="mechanism unsupported by any evidence")
    result = classify(BASE_CANDIDATE, VERIFIED, PRIOR_ART_OK, adv)
    assert result["final_status"] == "REJECTED"
    assert "adjudication_blocked" not in result


def test_pass_still_promotes():
    result = classify(BASE_CANDIDATE, VERIFIED, PRIOR_ART_OK,
                      _adversarial("PASS"))
    assert result["final_status"] == "AUTOMATED_INVENTION_CANDIDATE"


# ------------------------------------------------ metamorphic

def test_state_vocabulary_is_closed():
    """Only the three named non-scientific states map to adjudication
    blocked — an arbitrary string is NOT silently excused."""
    result = classify(BASE_CANDIDATE, VERIFIED, PRIOR_ART_OK,
                      _adversarial("SOMETHING_WEIRD"))
    # unknown vocabulary falls into the generic non-PASS branch:
    # rejected with the recorded reason (fail closed on the unknown)
    assert result["final_status"] == "REJECTED"


def test_evidence_gate_rejection_unchanged():
    """The evidence-verified gate still rejects before adversarial runs."""
    result = classify(BASE_CANDIDATE, {"verified": False}, PRIOR_ART_OK,
                      _adversarial("PASS"))
    assert result["final_status"] == "REJECTED"
    assert "evidence verification failed" in result["reason"]
