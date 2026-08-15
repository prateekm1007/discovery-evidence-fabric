#!/usr/bin/env python3
"""
Regression tests for V4 corrections (Items 5-11).

Tests:
  test_boundary_prefilter_conditional_no_evidence    (Correction 9)
  test_boundary_prefilter_conditional_with_evidence   (Correction 9)
  test_boundary_prefilter_no_conditional              (Correction 9)
  test_boundary_evidence_no_external                  (Correction 5)
  test_boundary_evidence_with_external                (Correction 5)
  test_boundary_evidence_external_incomplete          (Correction 5)
  test_adversarial_invalid_verdict_reason_conflict    (Correction 6)
  test_adversarial_invalid_boundary_no_evidence       (Correction 6)
  test_adversarial_invalid_prior_art_firewall         (Correction 6 + 10)
  test_adversarial_valid_no_conflict                  (Correction 6)
  test_prior_art_firewall_non_kill_state              (Correction 10)
  test_prior_art_firewall_kill_state                  (Correction 10)
  test_prior_art_firewall_unknown_state               (Correction 10)
  test_evidence_gate_blocks_adversarial               (Correction 11)
  test_evidence_gate_allows_adversarial               (Correction 11)
  test_source_hash_reconstruction_complete            (Correction 7)
  test_source_hash_reconstruction_missing             (Correction 7)
  test_winner_v4_no_winner                             (Correction 8)
  test_winner_v4_preliminary_best_m0                  (Correction 8)
  test_winner_v4_winning_architecture                 (Correction 8)
  test_m4_context_isolation_missing_file              (Correction 3)
  test_m4_context_isolation_committed_file            (Correction 3)
"""
import sys, os, json, tempfile, pytest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from discovery_fabric.v4_corrections import (
    boundary_prefilter,
    validate_boundary_evidence,
    check_adversarial_invalid,
    enforce_prior_art_firewall,
    check_evidence_gate_before_adversarial,
    reconstruct_source_hashes,
    determine_winner_v4,
    commit_m4_memory,
    load_m4_memory,
)


# ===== CORRECTION 9: BOUNDARY PRE-FILTER =====

class TestBoundaryPrefilter:
    def test_conditional_no_evidence(self):
        """Conditional language + no external citation → INSUFFICIENT_EVIDENCE."""
        reason = "The device might fail if the boundary condition is exceeded."
        result = boundary_prefilter(reason)
        assert result["action"] == "DOWNGRADE_TO_INSUFFICIENT_EVIDENCE"
        assert "might" in result["conditional_words_found"]
        assert "if" in result["conditional_words_found"]
        assert result["external_evidence_found"] is False

    def test_conditional_with_evidence(self):
        """Conditional language + external citation → PASS_THROUGH."""
        reason = "The device might fail if the boundary is exceeded, per ISO 14971 risk analysis."
        result = boundary_prefilter(reason)
        assert result["action"] == "PASS_THROUGH"
        assert result["external_evidence_found"] is True

    def test_no_conditional(self):
        """No conditional language → PASS_THROUGH."""
        reason = "The device fails catastrophically when temperature exceeds 80°C."
        result = boundary_prefilter(reason)
        assert result["action"] == "PASS_THROUGH"
        assert result["conditional_words_found"] == []

    def test_no_conditional_no_evidence(self):
        """No conditional language, no evidence → PASS_THROUGH (prefilter only screens conditional)."""
        reason = "The device fails when the boundary is crossed."
        result = boundary_prefilter(reason)
        assert result["action"] == "PASS_THROUGH"

    def test_empty_reason(self):
        result = boundary_prefilter("")
        assert result["action"] == "PASS_THROUGH"


# ===== CORRECTION 5: BOUNDARY EVIDENCE STANDARD =====

class TestBoundaryEvidence:
    def test_no_external_evidence_no_citation(self):
        """No external evidence provided, no inline citation → INSUFFICIENT_EVIDENCE."""
        result = validate_boundary_evidence("The boundary is crossed.", None)
        assert result["valid"] is False
        assert result["disposition"] == "INSUFFICIENT_EVIDENCE"

    def test_inline_citation(self):
        """Kill reason contains inline DOI/citation → KILL_PERMITTED."""
        reason = "Boundary crossed per DOI: 10.1002/jbm.b.12345"
        result = validate_boundary_evidence(reason, None)
        assert result["valid"] is True
        assert result["disposition"] == "KILL_PERMITTED"
        assert result["evidence_source"] == "INLINE_CITATION"

    def test_external_evidence_complete(self):
        """External evidence with all required fields → KILL_PERMITTED."""
        ext_ev = {
            "oracle_source_id": "FDA-MAUDE-12345",
            "oracle_source_type": "PUBLISHED_FAILURE_RECORD",
            "oracle_source_hash": "abc123",
            "oracle_evidence_span": "Device failed at 80°C boundary...",
        }
        result = validate_boundary_evidence("Boundary crossed", ext_ev)
        assert result["valid"] is True
        assert result["disposition"] == "KILL_PERMITTED"

    def test_external_evidence_incomplete(self):
        """External evidence missing required fields → INSUFFICIENT_EVIDENCE."""
        ext_ev = {"oracle_source_id": "X"}  # missing type, hash, span
        result = validate_boundary_evidence("Boundary crossed", ext_ev)
        assert result["valid"] is False
        assert result["disposition"] == "INSUFFICIENT_EVIDENCE"

    def test_external_evidence_invalid_type(self):
        """External evidence with invalid oracle_source_type → INSUFFICIENT_EVIDENCE."""
        ext_ev = {
            "oracle_source_id": "X",
            "oracle_source_type": "LLM_GENERATED",  # NOT a valid external type
            "oracle_source_hash": "abc",
            "oracle_evidence_span": "span",
        }
        result = validate_boundary_evidence("Boundary crossed", ext_ev)
        assert result["valid"] is False
        assert result["disposition"] == "INSUFFICIENT_EVIDENCE"

    def test_prefilter_downgrades_before_external_check(self):
        """Prefilter runs first; conditional + no citation → INSUFFICIENT_EVIDENCE even if external provided."""
        reason = "might fail if boundary crossed"
        ext_ev = {"oracle_source_id": "X", "oracle_source_type": "PUBLISHED_FAILURE_RECORD",
                  "oracle_source_hash": "abc", "oracle_evidence_span": "span"}
        result = validate_boundary_evidence(reason, ext_ev)
        assert result["valid"] is False
        assert "Pre-filter" in result["reason"]


# ===== CORRECTION 6: ADVERSARIAL_INVALID =====

class TestAdversarialInvalid:
    def test_verdict_reason_conflict_kill_survive(self):
        """verdict=SURVIVE but reason says 'is killed' → ADVERSARIAL_INVALID."""
        result = check_adversarial_invalid("SURVIVE", "The mechanism is killed under load.", True, "NO_MATCH_FOUND")
        assert result["disposition"] == "ADVERSARIAL_INVALID"
        assert result["evaluation_status"] == "EVALUATION_FAILED"
        assert result["re_evaluation_required"] is True
        assert result["is_aic"] is False
        assert result["is_survivor"] is False

    def test_verdict_reason_conflict_survive_kill(self):
        """verdict=SURVIVE but reason says fails → ADVERSARIAL_INVALID."""
        result = check_adversarial_invalid("SURVIVE", "The mechanism fails under load.", True, "NO_MATCH_FOUND")
        assert result["disposition"] == "ADVERSARIAL_INVALID"

    def test_boundary_kill_no_evidence(self):
        """BOUNDARY_CONDITION KILL without valid evidence → ADVERSARIAL_INVALID."""
        result = check_adversarial_invalid("KILL", "boundary condition crossed", False, "NO_MATCH_FOUND")
        assert result["disposition"] == "ADVERSARIAL_INVALID"
        assert "BOUNDARY_CONDITION" in result["invalid_reason"]

    def test_prior_art_kill_on_non_kill_state(self):
        """PRIOR_ART KILL on POSSIBLE_RELEVANCE → ADVERSARIAL_INVALID (firewall)."""
        result = check_adversarial_invalid("KILL", "prior art exists", True, "POSSIBLE_RELEVANCE")
        assert result["disposition"] == "ADVERSARIAL_INVALID"
        assert "PRIOR_ART" in result["invalid_reason"]

    def test_valid_no_conflict(self):
        """No conflicts → VALID."""
        result = check_adversarial_invalid("KILL", "The mechanism is unsupported by evidence.", True, "NO_MATCH_FOUND")
        assert result["disposition"] == "VALID"
        assert result["evaluation_status"] == "COMPLETED"


# ===== CORRECTION 10: PRIOR-ART FIREWALL =====

class TestPriorArtFirewall:
    def test_non_kill_state_kill_overridden(self):
        """POSSIBLE_RELEVANCE + adversarial PRIOR_ART=KILL → override to SURVIVE."""
        result = enforce_prior_art_firewall("POSSIBLE_RELEVANCE", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True
        assert result["action"] == "OVERRIDE_KILL_TO_SURVIVE"
        assert result["corrected_verdict"] == "SURVIVE"

    def test_no_match_found_kill_overridden(self):
        result = enforce_prior_art_firewall("NO_MATCH_FOUND", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True
        assert result["corrected_verdict"] == "SURVIVE"

    def test_topical_related_kill_overridden(self):
        result = enforce_prior_art_firewall("TOPICAL_RELATED", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True

    def test_unresolved_kill_overridden(self):
        result = enforce_prior_art_firewall("UNRESOLVED_INSUFFICIENT_EVIDENCE", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True

    def test_specific_disclosure_kill_permitted(self):
        """SPECIFIC_DISCLOSURE + PRIOR_ART=KILL → KILL_PERMITTED."""
        result = enforce_prior_art_firewall("SPECIFIC_DISCLOSURE", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is False
        assert result["action"] == "KILL_PERMITTED"

    def test_identical_disclosure_kill_permitted(self):
        result = enforce_prior_art_firewall("IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is False

    def test_unknown_state_kill_overridden(self):
        """Unknown prior-art state + PRIOR_ART=KILL → INSUFFICIENT_EVIDENCE."""
        result = enforce_prior_art_firewall("UNKNOWN_STATE", "KILL", "PRIOR_ART")
        assert result["firewall_applied"] is True
        assert result["corrected_verdict"] == "INSUFFICIENT_EVIDENCE"

    def test_non_prior_art_dimension_no_firewall(self):
        """Non-PRIOR_ART dimension → firewall not applied."""
        result = enforce_prior_art_firewall("POSSIBLE_RELEVANCE", "KILL", "MECHANISM_VALIDITY")
        assert result["firewall_applied"] is False

    def test_survive_verdict_no_firewall(self):
        """SURVIVE verdict → firewall not triggered."""
        result = enforce_prior_art_firewall("POSSIBLE_RELEVANCE", "SURVIVE", "PRIOR_ART")
        assert result["firewall_applied"] is False


# ===== CORRECTION 11: EVIDENCE → ADVERSARIAL ORDERING =====

class TestEvidenceGateOrdering:
    def test_evidence_fails_adversarial_not_run(self):
        """Evidence verification fails → adversarial MUST NOT run."""
        result = check_evidence_gate_before_adversarial(False)
        assert result["adversarial_should_run"] is False
        assert result["adversarial_status"] == "NOT_RUN"
        assert result["adversarial_not_run_reason"] == "EVIDENCE_GATE_FAILED"

    def test_evidence_passes_adversarial_eligible(self):
        """Evidence verification passes → adversarial eligible."""
        result = check_evidence_gate_before_adversarial(True)
        assert result["adversarial_should_run"] is True
        assert result["adversarial_status"] == "ELIGIBLE"


# ===== CORRECTION 7: SOURCE HASH RECONSTRUCTION =====

class TestSourceHashReconstruction:
    def test_complete_reconstruction(self):
        """All source_ids found in Phase-D packet → COMPLETE."""
        source_ids = ["europepmc:12345", "openalex:W67890"]
        packet_sources = [
            {"source_id": "europepmc:12345", "content_hash": "abc123def456"},
            {"source_id": "openalex:W67890", "content_hash": "xyz789ghi012"},
        ]
        result = reconstruct_source_hashes(source_ids, packet_sources)
        assert result["provenance_complete"] is True
        assert result["provenance_status"] == "COMPLETE"
        assert result["reconstructed_count"] == 2
        assert result["missing_count"] == 0
        assert result["source_hash_reconstruction_method"] == "PHASE_D_PACKET_JOIN"

    def test_missing_source(self):
        """source_id not in Phase-D packet → PROVENANCE_INCOMPLETE."""
        source_ids = ["europepmc:12345", "unknown:99999"]
        packet_sources = [{"source_id": "europepmc:12345", "content_hash": "abc123"}]
        result = reconstruct_source_hashes(source_ids, packet_sources)
        assert result["provenance_complete"] is False
        assert result["provenance_status"] == "PROVENANCE_INCOMPLETE"
        assert result["reconstructed_count"] == 1
        assert result["missing_count"] == 1
        assert "unknown:99999" in result["missing"]

    def test_empty_source_ids(self):
        result = reconstruct_source_hashes([], [])
        assert result["provenance_complete"] is True
        assert result["reconstructed_count"] == 0


# ===== CORRECTION 8: PRELIMINARY M0 PROMOTION RULE =====

class TestWinnerDetermination:
    def test_no_winner_all_zero(self):
        """All arms 0 AICs → NO_WINNER."""
        result = determine_winner_v4(
            {"M0": 0.0, "M1": 0.0, "M4": 0.0},
            {"M0": 0, "M1": 0, "M4": 0},
            {"M0": 100, "M1": 100, "M4": 100},
        )
        assert result["outcome"] == "NO_WINNER"

    def test_preliminary_best_m0(self):
        """M0 highest yield but not significant → PRELIMINARY_BEST_M0."""
        # M0: 5/100 = 0.05, M4B: 1/100 = 0.01, lift = 4pp (< 5pp)
        result = determine_winner_v4(
            {"M0": 0.05, "M1": 0.0, "M2": 0.0, "M3": 0.0, "M4": 0.0, "M4B": 0.01, "M4C": 0.03},
            {"M0": 5, "M1": 0, "M2": 0, "M3": 0, "M4": 0, "M4B": 1, "M4C": 3},
            {"M0": 100, "M1": 100, "M2": 100, "M3": 100, "M4": 100, "M4B": 100, "M4C": 100},
        )
        assert result["outcome"] in ("PRELIMINARY_BEST_M0", "NO_WINNER")
        assert result["best_arm"] == "M0"

    def test_winning_architecture_significant(self):
        """Large effect size + significant → WINNING_ARCHITECTURE."""
        # M0: 50/100 = 0.50, M1: 0/100 = 0.00, lift = 50pp
        result = determine_winner_v4(
            {"M0": 0.50, "M1": 0.0, "M4": 0.0, "M4B": 0.0, "M4C": 0.0},
            {"M0": 50, "M1": 0, "M4": 0, "M4B": 0, "M4C": 0},
            {"M0": 100, "M1": 100, "M4": 100, "M4B": 100, "M4C": 100},
        )
        assert result["outcome"] == "WINNING_ARCHITECTURE"
        assert result["winner"] == "M0"
        assert result["lift_pp"] >= 5.0

    def test_no_winner_insufficient_lift(self):
        """Best arm has <5pp lift → NO_WINNER."""
        result = determine_winner_v4(
            {"M0": 0.04, "M1": 0.03},
            {"M0": 4, "M1": 3},
            {"M0": 100, "M1": 100},
        )
        assert result["outcome"] in ("NO_WINNER", "PRELIMINARY_BEST_M0")


# ===== CORRECTION 3: M4 CONTEXT ISOLATION =====

class TestM4ContextIsolation:
    def test_missing_file_raises(self):
        """Missing committed memory file → M4_INVALID_CONTEXT_SOURCE."""
        with tempfile.TemporaryDirectory() as td:
            with pytest.raises(FileNotFoundError, match="M4_INVALID_CONTEXT_SOURCE"):
                load_m4_memory(0, "macro", Path(td))

    def test_committed_file_loads(self):
        """Committed file loads with context_source_mode=COMMITTED_FILE."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            memory = {"mechanism": "test", "intervention": "test_intervention"}
            commit_info = commit_m4_memory(0, "macro", memory, d)
            assert commit_info["context_source_mode"] == "COMMITTED_FILE"
            assert commit_info["content_hash"] is not None
            
            loaded = load_m4_memory(0, "macro", d)
            assert loaded["context_source_mode"] == "COMMITTED_FILE"
            assert loaded["memory"]["mechanism"] == "test"
            assert loaded["content_hash"] == commit_info["content_hash"]

    def test_committed_file_is_immutable_hash(self):
        """Committed file has a content_hash that changes if content changes."""
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            mem1 = {"key": "value1"}
            mem2 = {"key": "value2"}
            c1 = commit_m4_memory(0, "macro", mem1, d)
            c2 = commit_m4_memory(0, "micro", mem2, d)
            assert c1["content_hash"] != c2["content_hash"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
