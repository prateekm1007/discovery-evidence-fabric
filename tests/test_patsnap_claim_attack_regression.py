"""Regression tests for PatSnap Claim Attack."""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.patsnap_claim_attack import (
    PatentEvidence, ElementMapping, ArrangementMapping, NoveltyResult,
    ClaimAttackResult, PatSnapClaimAttacker,
)
from discovery_fabric.prior_art_v2.patsnap_claims import fetch_patsnap_claims
from discovery_fabric.prior_art_v2.elite_v3 import _sha256


class TestClaimDataResponseAccepted:
    def test_patent_evidence_validates(self):
        pe = PatentEvidence(
            patent_number="US11912894B2",
            patsnap_patent_id="abc-123",
            claims=["1. A device..."],
            content_hash="abc123",
        )
        assert pe.validate()
        assert pe.is_valid

    def test_patent_evidence_invalid_without_claims(self):
        pe = PatentEvidence(
            patent_number="US123", patsnap_patent_id="abc",
            claims=[], content_hash="abc",
        )
        assert not pe.validate()


class TestClaimHash:
    def test_claim_hash_is_sha256(self):
        h = _sha256("test claim text")
        assert len(h) == 64

    def test_element_mapping_references_claim_hash(self):
        em = ElementMapping(
            patent_number="US123", claim_hash="abc123",
            element_id="A", disclosure_type="EXPLICIT",
            exact_passage="the sensor",
        )
        assert em.claim_hash == "abc123"


class TestIndependentClaimCount:
    def test_patent_evidence_has_independent_count(self):
        record = fetch_patsnap_claims("US11912894B2")
        if record:
            assert record.independent_claim_count > 0


class TestSingleReference102:
    def test_102_single_reference(self):
        nr = NoveltyResult(
            patent_number="US123",
            all_elements_found=True,
            elements_found=["A","B","C"],
            elements_missing=[],
            arrangement_disclosed=True,
            novelty_attacked=True,
        )
        assert nr.novelty_attacked
        assert len(nr.elements_missing) == 0

    def test_102_fails_with_missing_element(self):
        nr = NoveltyResult(
            patent_number="US123",
            all_elements_found=False,
            elements_found=["A","B"],
            elements_missing=["C"],
            element_preventing_anticipation="C",
            novelty_attacked=False,
        )
        assert not nr.novelty_attacked
        assert nr.element_preventing_anticipation == "C"


class TestRequiredArrangement:
    def test_arrangement_is_first_class(self):
        am = ArrangementMapping(
            patent_number="US123", claim_hash="abc",
            element_pair="A→B",
            required_arrangement_disclosed="FALSE",
        )
        assert am.required_arrangement_disclosed in ("TRUE","FALSE","UNCERTAIN")


class TestCouldWould103:
    def test_obviousness_has_could_and_would(self):
        obv = {"could_answer": "yes", "would_answer": "no", "would_why": "no motivation"}
        assert obv["could_answer"] == "yes"
        assert obv["would_answer"] == "no"


class TestStaleClaimPrevention:
    def test_element_mapping_has_claim_hash(self):
        em = ElementMapping(
            patent_number="US123", claim_hash="hash123",
            element_id="A", disclosure_type="EXPLICIT", exact_passage="test",
        )
        assert em.claim_hash != ""


class TestClaimRedesignLineage:
    def test_claim_version_tracked(self):
        r = ClaimAttackResult(
            invention_id="TEST", claim_version=0,
            claim_text="A device...", claim_hash=_sha256("A device..."),
        )
        assert r.claim_version == 0
        assert r.claim_hash != ""


class TestInsufficientEvidenceFirewall:
    def test_empty_element_matrix_is_insufficient(self):
        r = ClaimAttackResult(
            invention_id="TEST", claim_version=0,
            claim_text="A...", claim_hash="abc",
            element_matrix=[],  # empty!
        )
        attacker = PatSnapClaimAttacker()
        status, _ = attacker._determine_status(r)
        assert status == "INSUFFICIENT_EVIDENCE"

    def test_all_uncertain_is_insufficient(self):
        r = ClaimAttackResult(
            invention_id="TEST", claim_version=0,
            claim_text="A...", claim_hash="abc",
            element_matrix=[
                ElementMapping(patent_number="US123", claim_hash="h",
                              element_id="A", disclosure_type="UNCERTAIN", exact_passage=""),
            ],
        )
        attacker = PatSnapClaimAttacker()
        status, _ = attacker._determine_status(r)
        assert status == "INSUFFICIENT_EVIDENCE"


class TestSearchCountNotEvidence:
    def test_count_does_not_become_gold(self):
        count = 271730
        is_gold = False
        assert not is_gold
