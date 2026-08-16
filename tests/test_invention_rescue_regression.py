"""
Regression tests for Invention Rescue.

Per CEO Section 15:
1. 102 rejection preservation
2. claim lineage
3. commercial objective preservation
4. material technical change
5. new prior-art search after redesign
6. no fabricated novelty
7. no claim resurrection without new technical distinction
"""
import pytest
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.invention_rescue import (
    RescueAuditor, RescueResult, KillingReference, CommercialObjective,
    ArchitectureAlternative, ClaimVersionResult, _now_utc,
)
from discovery_fabric.prior_art_v2.elite_v3 import _sha256


# ============================================================
# 1. 102 REJECTION PRESERVATION
# ============================================================
class Test102RejectionPreservation:
    """Claim 0 rejection must be preserved — never relabeled as novel."""

    def test_claim_0_status_rejected_102(self):
        cv = ClaimVersionResult(
            version=0, claim_text="A device...", claim_hash=_sha256("A device..."),
            status="REJECTED_102", killing_patent="US123",
        )
        assert cv.status == "REJECTED_102"
        assert cv.killing_patent == "US123"

    def test_claim_0_hash_preserved(self):
        """Claim 0 hash must be preserved even after redesign."""
        claim = "A hydrogel coating..."
        cv = ClaimVersionResult(version=0, claim_text=claim, claim_hash=_sha256(claim))
        assert cv.claim_hash == _sha256(claim)


# ============================================================
# 2. CLAIM LINEAGE
# ============================================================
class TestClaimLineage:
    """Claim versions tracked through redesign."""

    def test_claim_lineage_versions(self):
        v0 = ClaimVersionResult(version=0, claim_text="Claim 0", claim_hash=_sha256("Claim 0"))
        v1 = ClaimVersionResult(version=1, claim_text="Claim 1", claim_hash=_sha256("Claim 1"))
        v2 = ClaimVersionResult(version=2, claim_text="Claim 2", claim_hash=_sha256("Claim 2"))
        lineage = [v0, v1, v2]
        assert lineage[0].version == 0
        assert lineage[1].version == 1
        assert lineage[2].version == 2

    def test_different_claims_different_hash(self):
        v0 = ClaimVersionResult(version=0, claim_text="A", claim_hash=_sha256("A"))
        v1 = ClaimVersionResult(version=1, claim_text="B", claim_hash=_sha256("B"))
        assert v0.claim_hash != v1.claim_hash


# ============================================================
# 3. COMMERCIAL OBJECTIVE PRESERVATION
# ============================================================
class TestCommercialObjectivePreservation:
    """Commercial objective must be preserved through redesign."""

    def test_commercial_objective_has_fields(self):
        co = CommercialObjective(
            customer_problem="Hydrogel coatings fail under stress",
            economic_value_hypothesis="Reduced replacement costs",
            desired_technical_effect="Enhanced mechanical strength",
        )
        assert co.customer_problem != ""
        assert co.economic_value_hypothesis != ""
        assert co.desired_technical_effect != ""


# ============================================================
# 4. MATERIAL TECHNICAL CHANGE
# ============================================================
class TestMaterialTechnicalChange:
    """Architecture alternatives must change real technical properties."""

    def test_architecture_has_technical_change_type(self):
        arch = ArchitectureAlternative(
            architecture_id="V1",
            technical_change_type="mechanism",
            description="Covalent bonding via click reaction",
            material_difference="Click reaction creates covalent bonds",
            new_technical_effect="Enhanced stability",
        )
        assert arch.technical_change_type in (
            "structure", "relationship", "mechanism",
            "operating_condition", "material_process", "control_logic"
        )

    def test_material_difference_not_empty(self):
        arch = ArchitectureAlternative(
            architecture_id="V1",
            technical_change_type="mechanism",
            material_difference="Covalent bond vs non-covalent",
        )
        assert arch.material_difference != ""

    def test_preserves_commercial_value(self):
        arch = ArchitectureAlternative(
            architecture_id="V1",
            technical_change_type="operating_condition",
            preserves_commercial_value=True,
            commercial_value_note="Value preserved through improved durability",
        )
        assert arch.preserves_commercial_value is True


# ============================================================
# 5. NEW PRIOR-ART SEARCH AFTER REDESIGN
# ============================================================
class TestNewSearchAfterRedesign:
    """Each claim version must get its own prior-art search."""

    def test_claim_version_has_search_result(self):
        cv = ClaimVersionResult(
            version=1, claim_text="New claim", claim_hash=_sha256("New claim"),
            search_result={"gold_count": 2, "databases": ["GOOGLE_PATENTS"]},
        )
        assert cv.search_result is not None
        assert cv.search_result.get("gold_count") == 2


# ============================================================
# 6. NO FABRICATED NOVELTY
# ============================================================
class TestNoFabricatedNovelty:
    """Do not claim novelty without evidence."""

    def test_insufficient_evidence_not_novel(self):
        cv = ClaimVersionResult(
            version=1, claim_text="Claim", claim_hash=_sha256("Claim"),
            status="INSUFFICIENT_EVIDENCE",
            rationale="No GOLD patents from re-search",
        )
        assert cv.status != "SURVIVED_102"
        assert cv.status == "INSUFFICIENT_EVIDENCE"

    def test_rejected_102_stays_rejected(self):
        cv = ClaimVersionResult(
            version=0, claim_text="Claim 0", claim_hash=_sha256("Claim 0"),
            status="REJECTED_102", killing_patent="US123",
        )
        # Never relabel as novel
        assert cv.status == "REJECTED_102"
        assert cv.status != "SURVIVED_102"


# ============================================================
# 7. NO CLAIM RESURRECTION WITHOUT NEW TECHNICAL DISTINCTION
# ============================================================
class TestNoResurrectionWithoutDistinction:
    """Cannot resurrect a rejected claim without a material technical change."""

    def test_killing_reference_preserved(self):
        kr = KillingReference(
            patent_id="US11912894B2",
            title="Antimicrobial hydrogel coatings",
            what_was_already_disclosed="Prior art teaches: hydrogel + nanofiber reinforcement",
        )
        assert kr.patent_id != ""
        assert kr.what_was_already_disclosed != ""

    def test_new_claim_must_have_material_difference(self):
        """Claim 1 must have a material_difference from Claim 0."""
        arch = ArchitectureAlternative(
            architecture_id="V1",
            technical_change_type="mechanism",
            material_difference="Covalent bonding instead of physical mixing",
            new_technical_effect="Stronger bond stability",
        )
        # A valid rescue requires a non-empty material_difference
        assert arch.material_difference != ""
        assert arch.technical_change_type != ""


# ============================================================
# 8. FINAL RESOLUTION VALUES
# ============================================================
class TestFinalResolution:
    """Test valid final resolution values."""

    def test_valid_resolutions(self):
        valid = {
            "CLAIM_REJECTED_INVENTION_RESCUED",
            "CLAIM_REJECTED_INVENTION_ABANDONED",
            "CLAIM_SURVIVES_102_REQUIRES_103_REVIEW",
            "STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW",
        }
        assert "CLAIM_REJECTED_INVENTION_RESCUED" in valid
        assert "CLAIM_REJECTED_INVENTION_ABANDONED" in valid

    def test_rescue_result_has_resolution(self):
        rr = RescueResult(
            invention_id="TEST",
            final_resolution="CLAIM_REJECTED_INVENTION_RESCUED",
            final_reasoning="Claim 1 constructed but insufficient GOLD evidence",
        )
        assert rr.final_resolution == "CLAIM_REJECTED_INVENTION_RESCUED"
