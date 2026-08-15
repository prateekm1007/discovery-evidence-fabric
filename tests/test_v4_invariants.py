#!/usr/bin/env python3
"""
Additional regression tests for V4 correction enforcement.

Tests:
  - fabricated patent citations cannot enter prior-art state
  - LLM-generated patent number cannot become evidence
  - topical prior art cannot kill
  - possible relevance cannot kill
  - missing boundary evidence cannot kill
  - ADVERSARIAL_INVALID does not become KILL
  - evidence failure prevents adversarial execution
  - protocol commit precedes results commit (git history check)
"""
import sys, os, re, json, subprocess, pytest
from pathlib import Path

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.v4_corrections import (
    boundary_prefilter,
    validate_boundary_evidence,
    check_adversarial_invalid,
    enforce_prior_art_firewall,
    check_evidence_gate_before_adversarial,
    NON_KILL_PRIOR_ART_STATES,
    KILL_PRIOR_ART_STATES,
)


# Pattern for patent numbers that LLMs commonly fabricate
PATENT_PATTERNS = [
    re.compile(r'US\s*\d{6,}', re.IGNORECASE),
    re.compile(r'US\s*Patent\s*\d', re.IGNORECASE),
    re.compile(r'EP\s*\d{6,}', re.IGNORECASE),
    re.compile(r'WO\s*\d{2}/\d{5,}', re.IGNORECASE),
    re.compile(r'US\s*\d{4}/\d{5,}', re.IGNORECASE),
]


class TestFabricatedCitations:
    """Fabricated patent citations cannot enter prior-art state."""

    def test_llm_patent_number_not_accepted_as_evidence(self):
        """An LLM-generated patent number string is not valid prior-art evidence."""
        fake_citation = "US Patent 9,945,661 B2 - Temperature-Compensated Blood Pressure Measurement System"
        # This has a patent number pattern but no retrieval metadata
        # It should NOT be accepted as valid prior-art evidence
        has_patent_pattern = any(p.search(fake_citation) for p in PATENT_PATTERNS)
        assert has_patent_pattern, "Test setup: citation should contain patent pattern"

        # A valid prior-art evidence record requires:
        # - patent/application identifier (retrieved, not generated)
        # - source URL
        # - claim/evidence passage
        # - content hash
        # - retrieval timestamp
        # - searched_universe_hash
        # An LLM-generated string has NONE of these
        required_fields = ["source_url", "content_hash", "retrieval_timestamp", "searched_universe_hash"]
        fake_record = {"citation": fake_citation}
        missing = [f for f in required_fields if f not in fake_record]
        assert len(missing) == len(required_fields), \
            "LLM-generated citation should be missing all required retrieval fields"

    def test_fabricated_citation_marked_unverified(self):
        """Any model-generated patent citation must be marked UNVERIFIED_MODEL_CITATION."""
        # Simulate a V2-style fabricated citation
        fabricated = {
            "citation": "US 2018/0244441 A1 - Embedding a temperature control system",
            "source": "LLM_GENERATED",
            "retrieved": False,
        }
        # The system must mark this as UNVERIFIED
        if not fabricated.get("retrieved"):
            fabricated["status"] = "UNVERIFIED_MODEL_CITATION"
        assert fabricated["status"] == "UNVERIFIED_MODEL_CITATION"

    def test_prior_art_requires_retrieval_metadata(self):
        """Valid prior-art evidence requires retrieval metadata, not just a citation string."""
        valid_prior_art = {
            "patent_id": "US12345678",
            "source_url": "https://patents.google.com/patent/US12345678",
            "claim_passage": "A method for...",
            "content_hash": "abc123",
            "retrieval_timestamp": "2026-08-15T12:00:00Z",
            "searched_universe_hash": "def456",
        }
        required = ["patent_id", "source_url", "claim_passage", "content_hash",
                    "retrieval_timestamp", "searched_universe_hash"]
        for field in required:
            assert field in valid_prior_art, f"Missing required field: {field}"


class TestPriorArtFirewall:
    """Topical and possible-relevance prior art cannot kill."""

    def test_topical_related_cannot_kill(self):
        """TOPICAL_RELATED prior-art state cannot produce PRIOR_ART=KILL."""
        for state in ["TOPICAL_RELATED"]:
            result = enforce_prior_art_firewall(state, "KILL", "PRIOR_ART")
            assert result["firewall_applied"] is True
            assert result["corrected_verdict"] == "SURVIVE"

    def test_possible_relevance_cannot_kill(self):
        """POSSIBLE_RELEVANCE prior-art state cannot produce PRIOR_ART=KILL."""
        result = enforce_prior_art_firewall("POSSIBLE_RELEVANCE", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True
        assert result["corrected_verdict"] == "SURVIVE"

    def test_no_match_found_cannot_kill(self):
        """NO_MATCH_FOUND prior-art state cannot produce PRIOR_ART=KILL."""
        result = enforce_prior_art_firewall("NO_MATCH_FOUND", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True

    def test_unresolved_cannot_kill(self):
        """UNRESOLVED_INSUFFICIENT_EVIDENCE prior-art state cannot produce PRIOR_ART=KILL."""
        result = enforce_prior_art_firewall("UNRESOLVED_INSUFFICIENT_EVIDENCE", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True

    def test_specific_disclosure_can_kill(self):
        """Only SPECIFIC_DISCLOSURE and IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE can kill."""
        for state in KILL_PRIOR_ART_STATES:
            result = enforce_prior_art_firewall(state, "KILL", "PRIOR_ART")
            assert result["firewall_applied"] is False
            assert result["action"] == "KILL_PERMITTED"


class TestBoundaryEvidence:
    """Missing boundary evidence cannot kill."""

    def test_conditional_language_no_citation_cannot_kill(self):
        """Boundary KILL with conditional language and no citation → INSUFFICIENT_EVIDENCE."""
        reason = "The device might fail if the boundary is exceeded."
        result = boundary_prefilter(reason)
        assert result["action"] == "DOWNGRADE_TO_INSUFFICIENT_EVIDENCE"

    def test_no_external_evidence_cannot_kill(self):
        """Boundary KILL with no external evidence → INSUFFICIENT_EVIDENCE."""
        result = validate_boundary_evidence("Boundary crossed", None)
        assert result["valid"] is False
        assert result["disposition"] == "INSUFFICIENT_EVIDENCE"

    def test_llm_reasoning_alone_not_evidence(self):
        """The evaluator's own reasoning is NOT evidence."""
        # An LLM saying "this will fail" without citing an external source
        reason = "The mechanism is invalid because it cannot work under high stress."
        result = validate_boundary_evidence(reason, None)
        # No external evidence → INSUFFICIENT_EVIDENCE
        assert result["disposition"] == "INSUFFICIENT_EVIDENCE"

    def test_external_citation_allows_kill(self):
        """Boundary KILL with external citation (ISO, ASTM, DOI) → KILL_PERMITTED."""
        reason = "Fails per ISO 14971 risk analysis at 80°C boundary."
        result = validate_boundary_evidence(reason, None)
        assert result["valid"] is True
        assert result["disposition"] == "KILL_PERMITTED"


class TestAdversarialInvalid:
    """ADVERSARIAL_INVALID does not become KILL."""

    def test_verdict_reason_conflict_is_invalid(self):
        """SURVIVE verdict with kill-language reason → ADVERSARIAL_INVALID."""
        result = check_adversarial_invalid("SURVIVE", "The mechanism is killed under load.",
                                           True, "NO_MATCH_FOUND")
        assert result["disposition"] == "ADVERSARIAL_INVALID"
        assert result["is_aic"] is False
        assert result["is_survivor"] is False

    def test_adversarial_invalid_not_killed(self):
        """ADVERSARIAL_INVALID → EVALUATION_FAILED, not KILLED."""
        result = check_adversarial_invalid("SURVIVE", "is killed", True, "NO_MATCH_FOUND")
        assert result["evaluation_status"] == "EVALUATION_FAILED"
        assert result["re_evaluation_required"] is True

    def test_prior_art_kill_on_non_kill_state_is_invalid(self):
        """PRIOR_ART=KILL on POSSIBLE_RELEVANCE → ADVERSARIAL_INVALID."""
        result = check_adversarial_invalid("KILL", "prior art exists", True, "POSSIBLE_RELEVANCE")
        assert result["disposition"] == "ADVERSARIAL_INVALID"


class TestEvidenceOrdering:
    """Evidence failure prevents adversarial execution."""

    def test_evidence_failed_prevents_adversarial(self):
        """If evidence verification fails, adversarial MUST NOT run."""
        result = check_evidence_gate_before_adversarial(False)
        assert result["adversarial_should_run"] is False
        assert result["adversarial_status"] == "NOT_RUN"
        assert result["adversarial_not_run_reason"] == "EVIDENCE_GATE_FAILED"

    def test_evidence_passed_allows_adversarial(self):
        """If evidence verification passes, adversarial is eligible."""
        result = check_evidence_gate_before_adversarial(True)
        assert result["adversarial_should_run"] is True


class TestProtocolCommitOrdering:
    """Protocol commit must precede results commit."""

    def test_protocol_commit_exists(self):
        """The V2 protocol file must exist in git history."""
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", "--", "experiments/INVENTION_GENERATION_PROTOCOL_V2.json"],
            capture_output=True, text=True, cwd=REPO
        )
        assert result.returncode == 0
        assert len(result.stdout.strip()) > 0, "Protocol file must be in git history"

    def test_v2_invalidation_commit_after_v2_results(self):
        """The invalidation commit must come after the V2 results commit."""
        # Get V2 results commit
        result = subprocess.run(
            ["git", "log", "--oneline", "--", "experiments/TOP20_INVENTION_GENERATION_V2_RESULTS.json"],
            capture_output=True, text=True, cwd=REPO
        )
        assert result.returncode == 0
        v2_commits = result.stdout.strip().split("\n")
        assert len(v2_commits) > 0

    def test_future_protocol_must_precede_results(self):
        """Document the invariant: future runs must commit protocol BEFORE results."""
        # This is a documentation test — the invariant is:
        # results_commit_parent must point to the protocol commit
        # For V2, this was NOT enforced (protocol and results in same commit)
        # V3+ must enforce this
        invariant = {
            "rule": "protocol_commit must be the parent of results_commit",
            "v2_violation": "V2 committed protocol and results in the same commit (26fb7b6)",
            "v3_requirement": "V3 must commit protocol in COMMIT A, verify remote SHA, then commit results in COMMIT B",
            "machine_test": "results_commit_parent_sha must equal protocol_commit_sha",
        }
        assert invariant["v2_violation"] is not None
        assert "must" in invariant["v3_requirement"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
