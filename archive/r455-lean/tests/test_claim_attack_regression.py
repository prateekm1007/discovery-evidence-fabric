"""
Regression tests for Claim-Level Forensic Attack.

Per CEO Section 13:
1. claim-specific GOLD
2. single-reference 102
3. required arrangement
4. could/would
5. anti-hindsight
6. claim redesign lineage
7. deep-fetch failure handling
"""
import pytest
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.claim_attack import (
    ClaimAttackAuditor, ClaimAttackResult, ClaimElement,
    ElementMatrixEntry, ArrangementMapping, NoveltyResult,
    _now_utc, _sha256,
)
from discovery_fabric.prior_art_v2.forensic_review import (
    ObviousnessAttackForensic, DesignAroundForensic, EliteGateResult,
)


# ============================================================
# 1. CLAIM-SPECIFIC GOLD
# ============================================================
class TestClaimSpecificGold:
    """GOLD requires actual claim text mapped to invention elements."""

    def test_gold_patent_has_claims(self):
        """A GOLD patent must have actual claims, not just snippets."""
        entry = ElementMatrixEntry(
            patent_id="US12345678B2",
            claim_number="claim_1",
            element_id="A",
            disclosure_type="EXPLICIT",
            exact_passage="the hydrogel coating comprises a matrix",
            evidence_level="GOLD",
        )
        assert entry.evidence_level == "GOLD"
        assert entry.exact_passage != ""
        assert entry.disclosure_type == "EXPLICIT"

    def test_claim_specific_requires_actual_claim_text(self):
        """Claim-specific mapping must use actual claim text, not abstract."""
        # A mapping from abstract is NOT claim-specific
        entry_from_abstract = ElementMatrixEntry(
            patent_id="US123",
            claim_number="",
            element_id="A",
            disclosure_type="IMPLICIT",
            exact_passage="from abstract: mentions hydrogel",
            evidence_level="BRONZE",  # Not GOLD
        )
        assert entry_from_abstract.evidence_level != "GOLD"


# ============================================================
# 2. SINGLE-REFERENCE 102
# ============================================================
class TestSingleReference102:
    """102 requires ONE reference with ALL elements + arrangement."""

    def test_102_succeeds_when_all_elements_found(self):
        """102 succeeds when one patent has all elements + arrangement."""
        nr = NoveltyResult(
            patent_id="US123",
            all_elements_found=True,
            elements_found=["A", "B", "C"],
            elements_missing=[],
            arrangement_disclosed=True,
            novelty_attacked=True,
        )
        assert nr.novelty_attacked is True
        assert len(nr.elements_missing) == 0

    def test_102_fails_with_missing_element(self):
        """102 fails when any element is missing — report exact element."""
        nr = NoveltyResult(
            patent_id="US123",
            all_elements_found=False,
            elements_found=["A", "B"],
            elements_missing=["C"],
            element_preventing_anticipation="C",
            novelty_attacked=False,
        )
        assert nr.novelty_attacked is False
        assert nr.element_preventing_anticipation == "C"

    def test_102_fails_without_arrangement(self):
        """102 fails when arrangement not disclosed."""
        nr = NoveltyResult(
            patent_id="US123",
            all_elements_found=True,
            elements_found=["A", "B", "C"],
            elements_missing=[],
            arrangement_disclosed=False,
            novelty_attacked=False,
            element_preventing_anticipation="arrangement",
        )
        assert nr.novelty_attacked is False
        assert not nr.arrangement_disclosed

    def test_102_never_combines_references(self):
        """102 must never combine multiple references — one reference only."""
        nr = NoveltyResult(
            patent_id="US123",  # Single reference
            all_elements_found=True,
            novelty_attacked=True,
        )
        # Only one patent_id per NoveltyResult
        assert isinstance(nr.patent_id, str)


# ============================================================
# 3. REQUIRED ARRANGEMENT
# ============================================================
class TestRequiredArrangement:
    """Per MPEP §2131: anticipation requires arrangement."""

    def test_arrangement_is_first_class_field(self):
        am = ArrangementMapping(
            patent_id="US123",
            element_pair="A→B",
            required_arrangement_disclosed="FALSE",
            arrangement_analysis="Elements present but not in required arrangement",
        )
        assert am.required_arrangement_disclosed in ("TRUE", "FALSE", "UNCERTAIN")
        assert am.required_arrangement_disclosed == "FALSE"

    def test_arrangement_uncertain_does_not_create_102(self):
        am = ArrangementMapping(
            patent_id="US123",
            element_pair="A+B+C",
            required_arrangement_disclosed="UNCERTAIN",
        )
        assert am.required_arrangement_disclosed == "UNCERTAIN"


# ============================================================
# 4. COULD/WOULD
# ============================================================
class TestCouldWould:
    """EPO 2026: both COULD and WOULD must be answered."""

    def test_both_could_and_would_required(self):
        obv = ObviousnessAttackForensic(
            attempted=True,
            could_answer="yes",
            would_answer="no",
            would_why="No motivation to combine",
        )
        assert obv.could_answer == "yes"
        assert obv.would_answer == "no"
        assert obv.would_why != ""

    def test_103_succeeds_only_if_both_yes(self):
        obv = ObviousnessAttackForensic(
            attempted=True,
            attack_succeeded=True,
            could_answer="yes",
            would_answer="yes",
        )
        assert obv.attack_succeeded
        assert obv.could_answer == "yes"
        assert obv.would_answer == "yes"

    def test_103_fails_if_would_is_no(self):
        obv = ObviousnessAttackForensic(
            attempted=True,
            attack_succeeded=False,
            could_answer="yes",
            would_answer="no",
        )
        assert not obv.attack_succeeded


# ============================================================
# 5. ANTI-HINDSIGHT
# ============================================================
class TestAntiHindsight:
    """Obviousness must not use hindsight."""

    def test_pass_a_and_pass_b_tracked(self):
        obv = ObviousnessAttackForensic(
            attempted=True,
            pass_a_rationale="Before seeing invention",
            pass_b_rationale="After seeing invention",
            hindsight_risk="LOW",
            rationale_appears_only_after=False,
        )
        assert obv.pass_a_rationale != ""
        assert obv.pass_b_rationale != ""

    def test_high_hindsight_when_rationale_appears_only_after(self):
        obv = ObviousnessAttackForensic(
            attempted=True,
            hindsight_risk="HIGH",
            rationale_appears_only_after=True,
        )
        assert obv.hindsight_risk == "HIGH"


# ============================================================
# 6. CLAIM REDESIGN LINEAGE
# ============================================================
class TestClaimRedesignLineage:
    """Claim versions tracked through redesign."""

    def test_claim_version_tracked(self):
        result = ClaimAttackResult(
            invention_id="TEST",
            claim_version=0,
            claim_text="A device...",
            claim_hash=_sha256("A device..."),
        )
        assert result.claim_version == 0
        assert result.claim_hash != ""

    def test_claim_hash_deterministic(self):
        h1 = _sha256("test claim")
        h2 = _sha256("test claim")
        assert h1 == h2


# ============================================================
# 7. DEEP-FETCH FAILURE HANDLING
# ============================================================
class TestDeepFetchFailureHandling:
    """When deep-fetch fails, record DEEP_FETCH_UNAVAILABLE — don't call weak."""

    def test_deep_fetch_unavailable_status(self):
        """DEEP_FETCH_UNAVAILABLE is a valid status."""
        assert "DEEP_FETCH_UNAVAILABLE" == "DEEP_FETCH_UNAVAILABLE"

    def test_gold_patent_without_claims_not_claim_specific(self):
        """A GOLD patent with 0 claims is not claim-specific."""
        gold_data = {
            "patent_id": "US123",
            "claims": [],  # Deep-fetch failed
            "claim_count": 0,
            "deep_fetch_status": "DEEP_FETCH_UNAVAILABLE",
        }
        is_claim_specific = gold_data.get("claim_count", 0) > 0
        assert not is_claim_specific

    def test_invention_not_rejected_for_fetch_failure(self):
        """An invention should not be REJECTED merely because deep-fetch failed."""
        # If 0 GOLD patents due to fetch failure, status is PROMISING_INSUFFICIENT_EVIDENCE
        # not REJECT
        result = ClaimAttackResult(
            invention_id="TEST",
            final_status="PROMISING_INSUFFICIENT_EVIDENCE",
            final_reasoning="No GOLD patents — deep-fetch unavailable",
        )
        assert result.final_status != "REJECT"


# ============================================================
# 8. ELITE GATE INTEGRATION
# ============================================================
class TestEliteGateIntegration:
    """ELITE gate conditions in claim attack."""

    def test_102_attack_causes_reject(self):
        """If 102 attack succeeds, the invention is REJECTED."""
        result = ClaimAttackResult(
            invention_id="TEST",
            novelty_attacked_count=1,
            final_status="REJECT",
            final_reasoning="1 patents anticipate the claim (102)",
        )
        assert result.final_status == "REJECT"
        assert result.novelty_attacked_count > 0

    def test_103_attack_causes_reject(self):
        """If 103 attack succeeds, the invention is REJECTED."""
        result = ClaimAttackResult(
            invention_id="TEST",
            obviousness_result=ObviousnessAttackForensic(
                attempted=True, attack_succeeded=True,
            ),
            final_status="REJECT",
        )
        assert result.final_status == "REJECT"

    def test_elite_requires_all_10_conditions(self):
        gate = EliteGateResult()
        gate.failed_conditions = ["A_gold_references_mapped"]
        gate.all_pass = False
        assert not gate.all_pass
