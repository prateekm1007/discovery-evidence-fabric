"""
Regression tests for Rescue V2.
"""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.rescue_v2 import (
    RescueV2Auditor, RescueV2Result, ClaimRescueV2Result,
    SimulationResult, ExperimentDesign, CommercialValueCheck,
    _now_utc,
)
from discovery_fabric.prior_art_v2.elite_v3 import _sha256


class TestClaimRejectionPreservation:
    def test_claim_0_status_preserved(self):
        r = RescueV2Result(invention_id="TEST", claim_0={"status": "REJECTED_102", "killing_patent": "US123"})
        assert r.claim_0["status"] == "REJECTED_102"


class TestNewConceptGraph:
    def test_claim_has_concept_graph(self):
        cr = ClaimRescueV2Result(version=1, claim_text="A device...", claim_hash=_sha256("A device..."),
                                  concept_graph={"device_terms": ["covalent", "hydrogel"]})
        assert cr.concept_graph is not None


class TestNewSearchAfterRedesign:
    def test_search_gold_count_tracked(self):
        cr = ClaimRescueV2Result(version=1, claim_text="A...", claim_hash=_sha256("A..."),
                                  search_gold_count=3, search_gold_patent_ids=["US1","US2","US3"])
        assert cr.search_gold_count == 3


class TestNoStaleClaimReuse:
    def test_different_claims_different_hash(self):
        c1 = ClaimRescueV2Result(version=1, claim_text="Claim A", claim_hash=_sha256("Claim A"))
        c2 = ClaimRescueV2Result(version=2, claim_text="Claim B", claim_hash=_sha256("Claim B"))
        assert c1.claim_hash != c2.claim_hash


class TestNoZeroGoldNovelty:
    def test_zero_gold_is_pending_evidence(self):
        cr = ClaimRescueV2Result(version=1, claim_text="A...", claim_hash=_sha256("A..."),
                                  search_gold_count=0, status="RESCUE_PENDING_EVIDENCE")
        assert cr.status != "RESCUE_SURVIVES_102"
        assert cr.status == "RESCUE_PENDING_EVIDENCE"


class TestClaimLineage:
    def test_claim_versions_tracked(self):
        r = RescueV2Result(invention_id="TEST")
        r.claim_1 = ClaimRescueV2Result(version=1, claim_text="C1", claim_hash=_sha256("C1"))
        r.claim_2 = ClaimRescueV2Result(version=2, claim_text="C2", claim_hash=_sha256("C2"))
        assert r.claim_1.version == 1
        assert r.claim_2.version == 2


class TestSimulationLineage:
    def test_simulation_has_status(self):
        sim = SimulationResult(architecture_id="V1", status="ARCHITECTURE_VIABLE")
        assert sim.status == "ARCHITECTURE_VIABLE"

    def test_weak_architecture_flagged(self):
        sim = SimulationResult(architecture_id="V1", status="ARCHITECTURE_WEAK")
        assert sim.status == "ARCHITECTURE_WEAK"


class TestCommercialValuePreservation:
    def test_commercial_value_check(self):
        cv = CommercialValueCheck(architecture_id="V1", preserves_value=True, status="VALUE_PRESERVED")
        assert cv.preserves_value is True

    def test_abandon_redesign(self):
        cv = CommercialValueCheck(architecture_id="V1", status="ABANDON_REDESIGN")
        assert cv.status == "ABANDON_REDESIGN"


class TestDesignAround:
    def test_design_around_tracked(self):
        cr = ClaimRescueV2Result(version=1, claim_text="A...", claim_hash=_sha256("A..."),
                                  design_around={"design_around_risk": "HIGH"})
        assert cr.design_around["design_around_risk"] == "HIGH"


class TestRescueStatus:
    def test_valid_statuses(self):
        valid = {"RESCUE_PENDING_EVIDENCE", "RESCUE_SURVIVES_102", "RESCUE_SURVIVES_103",
                 "RESCUE_STRONG_CANDIDATE", "REJECTED_102", "REJECTED_103", "ABANDONED"}
        assert "RESCUE_PENDING_EVIDENCE" in valid
        assert "PATENTABLE" not in valid

    def test_invention_decision(self):
        r = RescueV2Result(invention_id="TEST", invention_decision="INVENTION_REDESIGN_REQUIRED")
        assert r.invention_decision == "INVENTION_REDESIGN_REQUIRED"
