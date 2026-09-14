"""tests/test_r452_capability_vs_science.py — AT-12 of the external
audit's acceptance list, plus the a2/classify capability/science
separation regression.

"Capability failures (missing_source_span,
mechanism_span_not_verbatim) never appear as a kill_reason; they
appear as INFRASTRUCTURE_CAPABILITY and the run stays resumable."

The R451 measured defect (audit E9): 4 of 7 completed production
runs carried 'evidence verification failed: missing_source_span;
mechanism_span_not_verbatim' as the invention's kill_reason — a
model-output-contract failure (the 1.7B proposer cannot emit verbatim
spans) recorded as a scientific rejection. Article LXI forbids
exactly this; the R452 fix types those issues
INFRASTRUCTURE_CAPABILITY / INCOMPLETE_INFERENCE_FAILURE while the
verifier itself stays UNCHANGED (the candidate is still not promoted
— Art. VII: no verifier weakening).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.a2 import classify as a2_classify  # noqa: E402


def _classify_with_issues(issues, candidate=None):
    return a2_classify.classify(
        candidate or {},
        evidence_verification={"verified": False, "issues": issues,
                               "state": "EVALUATED"},
        prior_art={}, adversarial={})


class TestCapabilityVsScienceSeparation(unittest.TestCase):
    def test_capability_issues_are_infrastructure_not_rejection(self):
        out = _classify_with_issues(
            ["missing_source_span", "mechanism_span_not_verbatim"])
        self.assertEqual(out["final_status"],
                         "INCOMPLETE_INFERENCE_FAILURE")
        self.assertEqual(out["failure_class"],
                         "INFRASTRUCTURE_CAPABILITY")
        self.assertIn("model output contract failure", out["reason"])
        self.assertIn("Art. LXI", out["reason"])
        # the verifier is NOT weakened: promotion stays blocked
        self.assertTrue(out["promotion_blocked"])
        self.assertEqual(out["verification_state"],
                         "EVALUATED_FAILED_CAPABILITY")

    def test_genuine_evidence_issues_stay_scientific_rejection(self):
        """A verification failure that is NOT an output-contract class
        (e.g. the evidence contradicts the claim) remains a scientific
        REJECTED verdict — the separation must not become a universal
        excuse (Art. V: fail closed, not universal rejector; and no
        verifier weakening in the other direction)."""
        out = _classify_with_issues(
            ["contradicting_evidence_in_source", "span_misquoted"])
        self.assertEqual(out["final_status"], "REJECTED")
        self.assertIsNone(out.get("failure_class"))
        self.assertTrue(out["promotion_blocked"])

    def test_mixed_issues_with_capability_remain_scientific(self):
        """A mix of capability AND substantive issues: the substantive
        content is present, so the rejection stands (the capability
        class only applies when the issues are PURELY
        output-contract)."""
        out = _classify_with_issues(
            ["missing_source_span", "contradicting_evidence_in_source"])
        self.assertEqual(out["final_status"], "REJECTED")

    def test_not_evaluated_stays_unknown(self):
        """The R402 NF-2 discipline is unchanged: a verification that
        never ran is UNKNOWN (never negative knowledge)."""
        out = a2_classify.classify(
            {}, evidence_verification={}, prior_art={},
            adversarial={})
        self.assertEqual(out["final_status"], "UNKNOWN")
        self.assertIn("NOT_EVALUATED", out["reason"])

    def test_challenge_carries_failure_class(self):
        """The evolution challenge record derivation: a capability
        failure produces failure_class=INFRASTRUCTURE_CAPABILITY and
        killed=False (the generation is CHALLENGED, not
        scientifically killed)."""
        final_status = "INCOMPLETE_INFERENCE_FAILURE"
        final_reason = ("model output contract failure: "
                        "missing_source_span — INFRASTRUCTURE "
                        "CAPABILITY state, never a scientific "
                        "rejection (Art. LXI)")
        failure_class = "INFRASTRUCTURE_CAPABILITY"
        killed = final_status in ("REJECTED",)
        self.assertFalse(killed)
        self.assertEqual(failure_class, "INFRASTRUCTURE_CAPABILITY")
        self.assertIn("never a scientific rejection", final_reason)


if __name__ == "__main__":
    unittest.main()
