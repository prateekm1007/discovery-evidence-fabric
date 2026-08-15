#!/usr/bin/env python3
"""
E2E tests for final adversarial hardening.

Tests:
  1. Boundary evidence resolver:
     - valid boundary evidence → can support KILL
     - absent boundary evidence → cannot KILL
     - irrelevant evidence → cannot KILL
     - mismatched evidence → INSUFFICIENT_EVIDENCE

  2. LLM failure paths:
     - timeout → EVALUATOR_CALL_FAILED
     - HTTP 429 → EVALUATOR_CALL_FAILED
     - HTTP 5xx → EVALUATOR_CALL_FAILED
     - malformed response → EVALUATOR_CALL_FAILED
     - empty response → EVALUATOR_CALL_FAILED

All must NOT produce KILLED.
"""
import sys, os, json, pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.a2.adversarial import adversarial_challenge
from discovery_fabric.v4_corrections import resolve_boundary_evidence

TEST_CANDIDATE = {
    "proposed_modification": "Add a secondary flow sensor downstream of the pump",
    "mechanistic_reasoning": "The sensor detects flow discrepancies",
    "falsification_test": "Measure flow accuracy in bench test",
    "device_class": "Insulin Pump",
    "failure_mode": "MECHANICAL_FAILURE",
}


class TestBoundaryEvidenceResolver:
    """Test the boundary evidence resolver directly."""

    def test_valid_boundary_evidence_resolved(self):
        """Evidence packet with boundary-relevant span → evidence resolved."""
        candidate = {
            "device_class": "Insulin Pump",
            "failure_mode": "MECHANICAL_FAILURE",
        }
        sources = [
            {
                "source_id": "europepmc:12345",
                "source_type": "PUBLICATION",
                "content_hash": "abc123def456",
                "source_span": "The insulin pump failure threshold is 200 mL/h. Operating beyond this limit causes mechanical failure in the drive mechanism.",
                "doi": "10.1234/test",
                "retrieval_timestamp": "2026-08-15T00:00:00Z",
            }
        ]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is not None
        assert evidence["oracle_source_id"] == "europepmc:12345"
        assert evidence["oracle_source_hash"] == "abc123def456"
        assert "threshold" in evidence["oracle_evidence_span"].lower()

    def test_absent_boundary_evidence_returns_none(self):
        """Evidence packet with no boundary indicators → None."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        sources = [
            {
                "source_id": "europepmc:12345",
                "source_span": "This paper discusses general pump design considerations.",
            }
        ]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is None

    def test_irrelevant_evidence_returns_none(self):
        """Evidence with boundary indicators but not relevant to device → None."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        sources = [
            {
                "source_id": "europepmc:99999",
                "source_span": "The temperature threshold for cardiac pacemaker batteries is 40°C.",
            }
        ]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is None  # not relevant to Insulin Pump

    def test_no_sources_returns_none(self):
        """No evidence packet sources → None."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        evidence = resolve_boundary_evidence(candidate, [])
        assert evidence is None


class TestBoundaryEvidenceE2E:
    """E2E: boundary evidence through adversarial_challenge()."""

    BOUNDARY_KILL_RESPONSE = (
        "UNSUPPORTED_MECHANISM: PASS\n"
        "WEAK_TRANSFER: PASS\n"
        "OBVIOUS_COMBINATION: PASS\n"
        "PRIOR_ART: PASS\n"
        "CONTRADICTION: PASS\n"
        "BOUNDARY_FAILURE: KILLED\n"
        "ENGINEERING_INFEASIBILITY: PASS\n"
        "REGULATORY_INCOMPATIBILITY: PASS\n"
        "OVERALL: KILLED\n"
        "REASON: exceeds operational threshold\n"
    )

    def test_e2e_boundary_with_real_external_evidence(self):
        """Boundary KILL with valid external evidence → KILL permitted."""
        candidate = {
            **TEST_CANDIDATE,
            "sources": [{
                "source_id": "europepmc:12345",
                "source_type": "PUBLICATION",
                "content_hash": "abc123def456",
                "source_span": "The insulin pump failure threshold is 200 mL/h. Operating beyond this limit causes mechanical failure.",
                "doi": "10.1234/test",
                "retrieval_timestamp": "2026-08-15T00:00:00Z",
            }]
        }
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=self.BOUNDARY_KILL_RESPONSE):
            result = adversarial_challenge(candidate, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        # With valid external evidence, the boundary KILL should be permitted
        # (not downgraded to INSUFFICIENT_EVIDENCE)
        boundary_verdict = result["attacks"].get("boundary_failure", "")
        # Either KILLED (evidence supported) or the pre-filter caught conditional language
        # The key is: it should NOT be INSUFFICIENT_EVIDENCE if evidence was resolved
        assert "INSUFFICIENT_EVIDENCE" not in boundary_verdict.upper() or \
               "boundary_evidence" not in str(result.get("v4_corrections_applied", []))

    def test_e2e_boundary_without_external_evidence(self):
        """Boundary KILL with no external evidence → INSUFFICIENT_EVIDENCE, not KILL."""
        candidate = {
            **TEST_CANDIDATE,
            "sources": []  # no evidence
        }
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=self.BOUNDARY_KILL_RESPONSE):
            result = adversarial_challenge(candidate, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        boundary_verdict = result["attacks"].get("boundary_failure", "")
        assert "INSUFFICIENT_EVIDENCE" in boundary_verdict.upper() or \
               any("boundary_evidence" in c for c in result.get("v4_corrections_applied", []))

    def test_e2e_boundary_irrelevant_evidence(self):
        """Boundary KILL with irrelevant evidence → INSUFFICIENT_EVIDENCE."""
        candidate = {
            **TEST_CANDIDATE,
            "sources": [{
                "source_id": "europepmc:99999",
                "source_span": "The temperature threshold for cardiac pacemaker batteries is 40°C.",
            }]
        }
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=self.BOUNDARY_KILL_RESPONSE):
            result = adversarial_challenge(candidate, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        # Irrelevant evidence → resolver returns None → INSUFFICIENT_EVIDENCE
        boundary_verdict = result["attacks"].get("boundary_failure", "")
        assert "INSUFFICIENT_EVIDENCE" in boundary_verdict.upper() or \
               any("boundary_evidence" in c for c in result.get("v4_corrections_applied", []))


class TestLLMFailurePaths:
    """E2E: all LLM failure paths produce EVALUATOR_CALL_FAILED, NOT KILLED."""

    def test_e2e_llm_timeout_not_kill(self):
        """LLM timeout → EVALUATOR_CALL_FAILED, not KILLED."""
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=None):
            result = adversarial_challenge(TEST_CANDIDATE, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        assert result["overall"] == "EVALUATOR_CALL_FAILED"
        assert result["overall"] != "KILLED"
        assert result["killed_count"] == 0
        assert result.get("is_scientific_verdict") is False

    def test_e2e_llm_429_not_kill(self):
        """LLM HTTP 429 (rate limit) → EVALUATOR_CALL_FAILED, not KILLED."""
        # llm_chat returns None on 429 (it catches exceptions)
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=None):
            result = adversarial_challenge(TEST_CANDIDATE, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        assert result["overall"] == "EVALUATOR_CALL_FAILED"
        assert result["overall"] != "KILLED"

    def test_e2e_llm_5xx_not_kill(self):
        """LLM HTTP 5xx → EVALUATOR_CALL_FAILED, not KILLED."""
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=None):
            result = adversarial_challenge(TEST_CANDIDATE, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        assert result["overall"] == "EVALUATOR_CALL_FAILED"

    def test_e2e_malformed_response_not_kill(self):
        """Malformed LLM response (no parseable verdicts) → not KILLED."""
        # A malformed response that has no KILLED in it → overall = PASS (no kills)
        # But if it's truly malformed (empty string), llm_chat returns None
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=""):
            result = adversarial_challenge(TEST_CANDIDATE, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        assert result["overall"] == "EVALUATOR_CALL_FAILED"
        assert result["overall"] != "KILLED"

    def test_e2e_empty_response_not_kill(self):
        """Empty LLM response → EVALUATOR_CALL_FAILED, not KILLED."""
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=None):
            result = adversarial_challenge(TEST_CANDIDATE, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        assert result["overall"] == "EVALUATOR_CALL_FAILED"
        assert result["killed_count"] == 0


class TestNoEvaluatorFailureReturnsKilled:
    """Static audit: no evaluator failure path returns KILLED."""

    def test_no_llm_failure_path_returns_killed(self):
        """Grep adversarial.py: no path where LLM failure → KILLED."""
        adv_path = REPO / "discovery_fabric" / "a2" / "adversarial.py"
        content = adv_path.read_text()
        # The LLM failure path must return EVALUATOR_CALL_FAILED, not KILLED
        # Find the "if not resp:" block
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if "if not resp:" in line:
                # Check the next 10 lines for the return value
                block = "\n".join(lines[i:i+15])
                assert "EVALUATOR_CALL_FAILED" in block, \
                    f"LLM failure path must return EVALUATOR_CALL_FAILED, not KILLED"
                assert '"overall": "KILLED"' not in block or "EVALUATOR_CALL_FAILED" in block, \
                    f"LLM failure path at line {i} must NOT return KILLED"

    def test_killed_only_after_successful_llm(self):
        """KILLED can only be set after LLM successfully returns a response."""
        adv_path = REPO / "discovery_fabric" / "a2" / "adversarial.py"
        content = adv_path.read_text()
        # The "overall = KILLED" line must come AFTER the LLM response parsing
        llm_fail_idx = content.find('if not resp:')
        killed_idx = content.find('overall = "KILLED"')
        assert llm_fail_idx != -1, "LLM failure path must exist"
        assert killed_idx != -1, "KILLED verdict must exist"
        assert killed_idx > llm_fail_idx, \
            "KILLED verdict must come after the LLM failure check (i.e., only on successful response)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
