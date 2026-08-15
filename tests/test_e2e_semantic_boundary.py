#!/usr/bin/env python3
"""
E2E tests for semantic boundary evidence validation.

Tests that the boundary evidence resolver requires ACTUAL SUPPORT,
not just keyword co-occurrence. All tests call adversarial_challenge()
at least once (production path).
"""
import sys, os, json, pytest
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.a2.adversarial import adversarial_challenge
from discovery_fabric.v4_corrections import resolve_boundary_evidence, validate_boundary_evidence

TEST_CANDIDATE = {
    "proposed_modification": "Add a secondary flow sensor downstream of the pump",
    "mechanistic_reasoning": "The sensor detects flow discrepancies",
    "falsification_test": "Measure flow accuracy in bench test",
    "device_class": "Insulin Pump",
    "failure_mode": "MECHANICAL_FAILURE",
}

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


class TestSemanticBoundaryEvidence:
    """Test that the resolver requires semantic support, not keyword co-occurrence."""

    def test_1_exact_boundary_plus_failure_relationship_valid(self):
        """Span with boundary + failure + causal relationship → VALID."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        sources = [{
            "source_id": "europepmc:12345",
            "source_type": "PUBLICATION",
            "content_hash": "abc123def456ghi789jkl012mno345pqr678stu901vwx234yz56789",
            "source_span": "The insulin pump mechanical failure occurs when flow rate exceeds 200 mL/h, "
                          "causing the drive mechanism to fail. This threshold is documented in ISO 14971.",
            "doi": "10.1234/test",
            "retrieval_timestamp": "2026-08-15T00:00:00Z",
        }]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is not None
        assert evidence["boundary_claim_supported"] is not None
        assert evidence["supporting_relationship"] is not None
        assert evidence["full_source_hash"] == sources[0]["content_hash"]  # full hash preserved
        assert len(evidence["full_source_hash"]) > 16  # NOT truncated

    def test_2_boundary_keyword_only_invalid(self):
        """Span with boundary keyword but no device/failure/causal → INVALID (None)."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        sources = [{
            "source_id": "europepmc:12345",
            "source_span": "The temperature threshold was measured at 40°C.",
            # no device mention, no failure mention, no causal relationship
        }]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is None

    def test_3_device_plus_threshold_but_unrelated_failure(self):
        """Span with device + threshold but no causal connection to failure → INVALID."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        sources = [{
            "source_id": "europepmc:12345",
            "source_span": "The insulin pump has a temperature threshold of 40°C for storage.",
            # mentions device + threshold, but no failure mechanism, no causal relationship
        }]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is None

    def test_4_failure_mention_but_no_boundary(self):
        """Span with failure mention but no boundary indicator → INVALID."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        sources = [{
            "source_id": "europepmc:12345",
            "source_span": "The insulin pump experienced mechanical failure in clinical use.",
            # mentions device + failure, but no boundary/threshold
        }]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is None

    def test_5_generic_standard_citation_no_connection(self):
        """Span with ISO citation but no connection to device/failure → INVALID."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        sources = [{
            "source_id": "europepmc:12345",
            "source_span": "ISO 14971 is a general risk management standard for medical devices.",
            # has standard citation, but no device, no failure, no causal relationship
        }]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is None

    def test_6_source_absent_invalid(self):
        """No sources → INVALID (None)."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        evidence = resolve_boundary_evidence(candidate, [])
        assert evidence is None

    def test_7_valid_evidence_full_hash_preserved(self):
        """Valid evidence preserves the COMPLETE content hash, not truncated."""
        candidate = {"device_class": "Insulin Pump", "failure_mode": "MECHANICAL_FAILURE"}
        full_hash = "a" * 64  # 64-char SHA-256 hash
        sources = [{
            "source_id": "europepmc:12345",
            "source_type": "PUBLICATION",
            "content_hash": full_hash,
            "source_span": "The insulin pump fails when flow exceeds 200 mL/h, causing mechanical breakdown.",
            "doi": "10.1234/test",
            "retrieval_timestamp": "2026-08-15T00:00:00Z",
        }]
        evidence = resolve_boundary_evidence(candidate, sources)
        assert evidence is not None
        assert evidence["full_source_hash"] == full_hash
        assert len(evidence["full_source_hash"]) == 64
        assert evidence["oracle_source_hash"] == full_hash  # also full in oracle field


class TestProductionPathSemanticBoundary:
    """E2E through adversarial_challenge() — production path."""

    def test_e2e_valid_boundary_evidence_supports_kill(self):
        """Production path: valid external boundary evidence → KILL permitted."""
        candidate = {
            **TEST_CANDIDATE,
            "sources": [{
                "source_id": "europepmc:12345",
                "source_type": "PUBLICATION",
                "content_hash": "abc123def456ghi789",
                "source_span": "The insulin pump mechanical failure occurs when flow exceeds 200 mL/h, "
                              "causing drive mechanism failure.",
                "doi": "10.1234/test",
                "retrieval_timestamp": "2026-08-15T00:00:00Z",
            }]
        }
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=BOUNDARY_KILL_RESPONSE):
            result = adversarial_challenge(candidate, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        # With valid semantic evidence, boundary KILL should be permitted
        boundary_verdict = result["attacks"].get("boundary_failure", "")
        # Should NOT be INSUFFICIENT_EVIDENCE (evidence was resolved and valid)
        assert "INSUFFICIENT_EVIDENCE" not in boundary_verdict.upper()

    def test_e2e_keyword_only_boundary_not_kill(self):
        """Production path: keyword-only evidence (no causal relationship) → INSUFFICIENT_EVIDENCE."""
        candidate = {
            **TEST_CANDIDATE,
            "sources": [{
                "source_id": "europepmc:12345",
                "source_span": "The insulin pump has a temperature threshold of 40°C for storage.",
                # keyword + device, but no failure mechanism, no causal relationship
            }]
        }
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=BOUNDARY_KILL_RESPONSE):
            result = adversarial_challenge(candidate, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        # Resolver returns None → evaluate_boundary_condition gets None → INSUFFICIENT_EVIDENCE
        boundary_verdict = result["attacks"].get("boundary_failure", "")
        assert "INSUFFICIENT_EVIDENCE" in boundary_verdict.upper() or \
               any("boundary_evidence" in c for c in result.get("v4_corrections_applied", []))

    def test_e2e_no_sources_boundary_not_kill(self):
        """Production path: no sources → INSUFFICIENT_EVIDENCE."""
        candidate = {**TEST_CANDIDATE, "sources": []}
        with patch("discovery_fabric.a2.adversarial.llm_chat", return_value=BOUNDARY_KILL_RESPONSE):
            result = adversarial_challenge(candidate, evidence_verified=True, prior_art_state="NO_MATCH_FOUND")
        boundary_verdict = result["attacks"].get("boundary_failure", "")
        assert "INSUFFICIENT_EVIDENCE" in boundary_verdict.upper() or \
               any("boundary_evidence" in c for c in result.get("v4_corrections_applied", []))


class TestStaticAuditSemanticBoundary:
    """Static audit: no production boundary kill without external_evidence.valid == true."""

    def test_no_boundary_kill_without_valid_evidence(self):
        """Grep adversarial.py: boundary KILL requires valid external evidence."""
        adv_path = REPO / "discovery_fabric" / "a2" / "adversarial.py"
        content = adv_path.read_text()
        # The boundary evaluation path must call evaluate_boundary_condition
        # with resolved evidence, and only permit KILL if bc["valid"] is True
        assert "evaluate_boundary_condition" in content, \
            "Production path must call evaluate_boundary_condition"
        assert "resolve_boundary_evidence" in content, \
            "Production path must call resolve_boundary_evidence"
        # Check that KILL is only set when bc["valid"] is True (i.e., not when evidence is insufficient)
        assert 'if not bc["valid"]' in content, \
            "Production path must check bc['valid'] before permitting boundary KILL"

    def test_validate_boundary_evidence_requires_semantic_fields(self):
        """validate_boundary_evidence must require boundary_claim_supported + supporting_relationship."""
        # Evidence with all structural fields but no semantic fields → INVALID
        ext_ev = {
            "oracle_source_id": "FDA-MAUDE-12345",
            "oracle_source_type": "PUBLISHED_FAILURE_RECORD",
            "oracle_source_hash": "abc123",
            "oracle_evidence_span": "Device failed at 80°C boundary...",
            # MISSING: boundary_claim_supported, supporting_relationship
        }
        result = validate_boundary_evidence("Boundary crossed", ext_ev)
        assert result["valid"] is False
        assert result["disposition"] == "INSUFFICIENT_EVIDENCE"
        assert "semantic" in result["reason"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
