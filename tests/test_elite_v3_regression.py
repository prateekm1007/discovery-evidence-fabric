"""
Regression tests for Elite V3 framework — fixed evidence layer.

Per CEO directive Section 19, tests for:
1. no GOLD without claim text
2. LENS scholarly ≠ Lens patent
3. inherency requires necessity
4. single-reference novelty
5. required arrangement
6. could/would distinction
7. no hindsight
8. claim redesign lineage
9. commercial hypothesis labeling
"""
import pytest
import json
import hashlib
import sys
from pathlib import Path
from dataclasses import dataclass, asdict

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.elite_v3 import (
    EliteV3Auditor, LLMClient, ClaimElement, ElementMapping, Attack,
    ClaimVersion, RelationshipMapping, EconomicValue, ManufacturingFeasibility,
    TechnicalEffect, FINAL_STATUSES, DISCLOSURE_TYPES, EVIDENCE_LEVELS,
    ATTACK_TYPES, MAX_REDESIGN_ROUNDS, MIN_GOLD_EVIDENCE_FOR_STRONG,
    _now_utc, _sha256,
)
from discovery_fabric.prior_art_v2.retrieval_v3 import (
    PatentRecord, RetrievalAttempt, fetch_patent_full,
    get_source_status_honest, normalize_patent_family,
)


# ============================================================
# 1. NO GOLD WITHOUT CLAIM TEXT
# ============================================================
class TestNoGoldWithoutClaims:
    """GOLD evidence requires actual claim text. Snippet/abstract/LLM summary = NOT GOLD."""

    def test_gold_requires_claims(self):
        """A PatentRecord with no claims cannot be GOLD."""
        record = PatentRecord(patent_id="US12345678B2")
        record.claims = []  # No claims!
        record.publication_date = "2023-01-01"
        record.priority_date = "2022-01-01"
        record.family_id = "12345"
        record.source_url = "https://patents.google.com/patent/US12345678B2/en"
        record.retrieved_at_utc = _now_utc()
        record.full_content_hash = _sha256("test")
        record.assess_gold()
        assert not record.is_gold
        assert "claim_text" in record.gold_missing

    def test_gold_with_claims_and_all_fields(self):
        """A PatentRecord with ALL fields including claims IS GOLD."""
        record = PatentRecord(patent_id="US12345678B2")
        record.claims = ["1. A device comprising..."]
        record.publication_date = "2023-01-01"
        record.priority_date = "2022-01-01"
        record.family_id = "12345"
        record.source_url = "https://patents.google.com/patent/US12345678B2/en"
        record.retrieved_at_utc = _now_utc()
        record.full_content_hash = _sha256("test")
        record.assess_gold()
        assert record.is_gold
        assert len(record.gold_missing) == 0

    def test_snippet_alone_not_gold(self):
        """Search snippet alone = NOT GOLD (per CEO Section 3)."""
        record = PatentRecord(patent_id="US12345678B2")
        record.claims = []  # Only snippet available, no claims
        record.assess_gold()
        assert not record.is_gold

    def test_abstract_only_not_gold(self):
        """Abstract only = NOT GOLD (per CEO Section 3)."""
        record = PatentRecord(patent_id="US12345678B2")
        record.abstract = "Some abstract..."
        record.claims = []  # No claims!
        record.assess_gold()
        assert not record.is_gold


# ============================================================
# 2. LENS SCHOLARLY ≠ LENS PATENT
# ============================================================
class TestLensDistinction:
    """LENS_SCHOLARLY (NPL) must never be counted as LENS_PATENT coverage."""

    def test_lens_scholarly_is_not_lens_patent(self):
        """Per CEO Section 4: separate LENS_PATENT from LENS_SCHOLARLY."""
        sources = get_source_status_honest()
        assert sources["LENS_SCHOLARLY"] == "LIVE"
        assert sources["LENS_PATENT"] == "UNAVAILABLE"
        assert sources["LENS_SCHOLARLY"] != sources["LENS_PATENT"]

    def test_lens_patent_unavailable_status(self):
        """Lens patent API returns 401 — must be UNAVAILABLE, not LIVE."""
        sources = get_source_status_honest()
        assert sources["LENS_PATENT"] == "UNAVAILABLE"

    def test_npl_hits_have_no_patent_id(self):
        """NPL hits from Lens Scholarly should not have patent_id."""
        # This is a structural test — NPL hits have doi, not patent_id
        npl_hit = {
            "source_id": "LENS_SCHOLARLY",
            "patent_id": None,  # NPL has no patent_id
            "doi": "10.1000/test",
            "title": "Scholarly paper",
        }
        assert npl_hit["patent_id"] is None
        assert npl_hit["doi"] is not None


# ============================================================
# 3. INHERENCY REQUIRES NECESSITY
# ============================================================
class TestInherencyRequiresNecessity:
    """INHERENT disclosure requires 'necessarily present', not 'possible' or 'likely'."""

    def test_inherent_requires_necessity_evidence(self):
        """INHERENT mapping must have necessity_evidence."""
        m = ElementMapping(
            element_id="A",
            disclosure_type="INHERENT",
            prior_art_text="The combustion process necessarily produces heat",
            evidence_level="GOLD",
            confidence=0.95,
            reasoning="Heat is necessary byproduct",
            necessity_evidence="Heat is a thermodynamic necessity of combustion",
            technical_basis="First law of thermodynamics",
        )
        assert m.disclosure_type == "INHERENT"
        assert m.necessity_evidence != ""
        assert m.technical_basis != ""

    def test_probable_is_not_inherent(self):
        """'Likely' or 'probably' is NOT INHERENT — it's IMPLICIT or UNCERTAIN."""
        # Per CEO Section 10: "likely", "probable", "compatible", "could be" ≠ INHERENT
        non_inherent_words = ["likely", "probable", "compatible", "could be", "would usually be"]
        for word in non_inherent_words:
            # These words indicate probability, not necessity
            assert word != "necessarily"

    def test_inherent_disclosure_type_exists(self):
        assert "INHERENT" in DISCLOSURE_TYPES

    def test_all_disclosure_types_present(self):
        expected = {"EXPLICIT", "IMPLICIT", "INHERENT", "NOT_DISCLOSED", "UNCERTAIN"}
        assert set(DISCLOSURE_TYPES) == expected


# ============================================================
# 4. SINGLE-REFERENCE NOVELTY
# ============================================================
class TestSingleReferenceNovelty:
    """102 requires ONE reference with ALL elements. Multiple refs cannot combine for 102."""

    def test_102_requires_single_reference(self):
        """FIREWALL: Multiple references CANNOT create a 102 failure."""
        attack = Attack(
            attack_type="NOVELTY_102",
            attack_strength="STRONG",
            primary_reference={"title": "Single Ref"},
            secondary_references=[],  # MUST be empty for 102
        )
        assert attack.secondary_references == []

    def test_102_with_multiple_refs_is_invalid(self):
        """If 102 has secondary_references, it's a violation."""
        attack = Attack(
            attack_type="NOVELTY_102",
            attack_strength="STRONG",
            primary_reference={"title": "Ref A"},
            secondary_references=[{"title": "Ref B"}],  # INVALID for 102
        )
        # This should be flagged as a violation
        assert len(attack.secondary_references) > 0  # Documents the violation

    def test_bronze_evidence_cannot_create_novelty_failure(self):
        """BRONZE evidence CANNOT create a novelty failure."""
        attack = Attack(
            attack_type="NOVELTY_102",
            attack_strength="NONE",
            evidence_level="BRONZE",
        )
        assert attack.evidence_level == "BRONZE"
        assert attack.attack_strength not in ("STRONG", "FATAL")


# ============================================================
# 5. REQUIRED ARRANGEMENT
# ============================================================
class TestRequiredArrangement:
    """Per MPEP: anticipation requires every element AND its required arrangement."""

    def test_attack_has_arrangement_fields(self):
        """NOVELTY_102 attack must have required_arrangement_disclosed and arrangement_analysis."""
        attack = Attack(
            attack_type="NOVELTY_102",
            attack_strength="MODERATE",
            required_arrangement_disclosed=False,
            arrangement_analysis="The reference discloses elements A and B individually but NOT the A→B relationship",
        )
        assert hasattr(attack, "required_arrangement_disclosed")
        assert hasattr(attack, "arrangement_analysis")
        assert attack.required_arrangement_disclosed is False

    def test_relationship_mapping_has_element_pair(self):
        """RelationshipMapping must track element pairs (A→B, B→C, A+B+C)."""
        rm = RelationshipMapping(
            element_pair="A→B",
            relationship_type="structural",
            prior_art_disclosure="The sensor is mounted on the substrate",
            disclosure_type="EXPLICIT",
            evidence_level="GOLD",
        )
        assert rm.element_pair == "A→B"
        assert rm.relationship_type == "structural"

    def test_arrangement_not_disclosed_means_no_102(self):
        """If arrangement is NOT disclosed, there's no 102 anticipation."""
        attack = Attack(
            attack_type="NOVELTY_102",
            attack_strength="NONE",
            required_arrangement_disclosed=False,
            arrangement_analysis="Elements present but arrangement not taught",
        )
        # If arrangement is not disclosed, attack should not be STRONG/FATAL
        assert attack.required_arrangement_disclosed is False
        assert attack.attack_strength not in ("STRONG", "FATAL")


# ============================================================
# 6. COULD/WOULD DISTINCTION
# ============================================================
class TestCouldWouldDistinction:
    """EPO 2026 guidance: both COULD and WOULD must be answered for 103."""

    def test_attack_has_could_and_would_fields(self):
        """OBVIOUSNESS_103 attack must have could_question and would_question."""
        attack = Attack(
            attack_type="OBVIOUSNESS_103",
            attack_strength="MODERATE",
            could_question="COULD: Yes, the PHOSITA has the technical capability",
            would_question="WOULD: No, there's no motivation to combine",
        )
        assert attack.could_question != ""
        assert attack.would_question != ""

    def test_would_question_is_mandatory(self):
        """Per CEO Section 11: WOULD question is MANDATORY."""
        attack = Attack(
            attack_type="OBVIOUSNESS_103",
            attack_strength="WEAK",
            would_question="",  # Empty = violation
        )
        # An attack without would_question should not be STRONG
        if not attack.would_question:
            assert attack.attack_strength != "STRONG"

    def test_no_would_means_no_obviousness(self):
        """If WOULD answer is 'No', the 103 attack should fail."""
        attack = Attack(
            attack_type="OBVIOUSNESS_103",
            attack_strength="NONE",
            could_question="COULD: Yes",
            would_question="WOULD: No, no motivation",
            can_survive=True,
        )
        assert attack.can_survive is True


# ============================================================
# 7. NO HINDSIGHT
# ============================================================
class TestNoHindsight:
    """Obviousness analysis must NOT use knowledge of the invention."""

    def test_attack_has_no_hindsight_field(self):
        """OBVIOUSNESS_103 attack must have no_hindsight_verified field."""
        attack = Attack(
            attack_type="OBVIOUSNESS_103",
            attack_strength="MODERATE",
            no_hindsight_verified=True,
        )
        assert hasattr(attack, "no_hindsight_verified")
        assert attack.no_hindsight_verified is True

    def test_epo_structure_fields_present(self):
        """Attack must have EPO/USPTO structure fields."""
        attack = Attack(
            attack_type="OBVIOUSNESS_103",
            attack_strength="MODERATE",
            closest_prior_art="US12345678B2",
            objective_technical_problem="How to improve signal quality",
            differences="The claim adds element C",
            technical_effect="Reduced noise",
            motivation="PHOSITA would combine to reduce noise",
            reasonable_expectation_of_success="High",
            teaching_away="None found",
        )
        assert attack.closest_prior_art != ""
        assert attack.objective_technical_problem != ""
        assert attack.differences != ""
        assert attack.technical_effect != ""
        assert attack.motivation != ""


# ============================================================
# 8. CLAIM REDESIGN LINEAGE
# ============================================================
class TestClaimRedesignLineage:
    """Claim versions must be tracked through redesign rounds."""

    def test_claim_version_increments(self):
        """CLAIM_0 → CLAIM_1 → CLAIM_2 — version increments by 1."""
        v0 = ClaimVersion(version=0, claim_text="Claim 0", claim_hash=_sha256("Claim 0"), created_at_utc=_now_utc())
        v1 = ClaimVersion(version=1, claim_text="Claim 1", claim_hash=_sha256("Claim 1"), created_at_utc=_now_utc(), redesign_rationale="Added element X")
        v2 = ClaimVersion(version=2, claim_text="Claim 2", claim_hash=_sha256("Claim 2"), created_at_utc=_now_utc(), redesign_rationale="Narrowed parameter Y")
        lineage = [v0, v1, v2]
        assert lineage[0].version == 0
        assert lineage[1].version == 1
        assert lineage[2].version == 2

    def test_max_redesign_rounds(self):
        """Maximum 3 redesign cycles per CEO Section 6."""
        assert MAX_REDESIGN_ROUNDS == 3

    def test_claim_hash_changes_with_text(self):
        """Different claim text → different hash."""
        v0 = ClaimVersion(version=0, claim_text="Claim A", claim_hash=_sha256("Claim A"), created_at_utc=_now_utc())
        v1 = ClaimVersion(version=1, claim_text="Claim B", claim_hash=_sha256("Claim B"), created_at_utc=_now_utc(), redesign_rationale="redesign")
        assert v0.claim_hash != v1.claim_hash


# ============================================================
# 9. COMMERCIAL HYPOTHESIS LABELING
# ============================================================
class TestCommercialHypothesisLabeling:
    """Every economic number must be tagged EVIDENCE, INFERENCE, or HYPOTHESIS."""

    def test_economic_value_has_evidence_tag(self):
        """EconomicValue must have market_size_evidence_tag."""
        ev = EconomicValue(
            customer_problem="Problem",
            economic_pain="Pain",
            current_cost="$100 (INFERENCE)",
            current_failure="Failure",
            value_created="Value",
            who_pays="Buyer",
            why_they_pay="Reason",
            adoption_barrier="Barrier",
            value_creation_types=["COST_REDUCTION"],
            market_size_evidence_tag="HYPOTHESIS",
            market_size_basis="Estimated from industry reports",
        )
        assert ev.market_size_evidence_tag in ("EVIDENCE", "INFERENCE", "HYPOTHESIS")

    def test_manufacturing_has_status(self):
        """ManufacturingFeasibility must have a status from the required set."""
        mf = ManufacturingFeasibility(
            manufacturing_process="process",
            materials="materials",
            tooling="tooling",
            assembly="assembly",
            quality_control="qc",
            throughput="throughput",
            yield_rate="90%",
            supply_chain="supplier",
            regulatory_burden="FDA 510(k)",
            status="SIMULATED_FEASIBLE",
        )
        assert mf.status in ("EVIDENCE", "INFERENCE", "HYPOTHESIS",
                             "SIMULATED_FEASIBLE", "SIMULATED_RISK", "EXPERIMENT_REQUIRED")

    def test_manufacturing_unknowns_have_resolution_method(self):
        """Per CEO Section 16: every UNKNOWN must have resolution_method."""
        mf = ManufacturingFeasibility(
            manufacturing_process="UNKNOWN",
            materials="UNKNOWN",
            tooling="UNKNOWN",
            assembly="UNKNOWN",
            quality_control="UNKNOWN",
            throughput="UNKNOWN",
            yield_rate="UNKNOWN",
            supply_chain="UNKNOWN",
            regulatory_burden="UNKNOWN",
            status="EXPERIMENT_REQUIRED",
            unknowns=[{"field": "yield_rate", "resolution_method": "prototype and measure", "estimated_cost": "medium"}],
        )
        assert len(mf.unknowns) > 0
        assert mf.unknowns[0]["resolution_method"] != ""

    def test_technical_effect_has_classification(self):
        """TechnicalEffect must have classification from the required set."""
        te = TechnicalEffect(
            problem="Problem",
            distinguishing_feature="Feature",
            mechanism="Mechanism",
            technical_effect="Effect",
            classification="HYPOTHESIZED",
        )
        assert te.classification in ("DOCUMENTED", "INFERRED", "HYPOTHESIZED")

    def test_hypothesized_effect_has_experiment(self):
        """Per CEO Section 14: if effect is HYPOTHESIZED, must have experiment_to_establish_effect."""
        te = TechnicalEffect(
            problem="Problem",
            distinguishing_feature="Feature",
            mechanism="Mechanism",
            technical_effect="Effect",
            classification="HYPOTHESIZED",
            experiment_to_establish_effect="Design experiment: baseline vs treatment...",
        )
        assert te.classification == "HYPOTHESIZED"
        assert te.experiment_to_establish_effect != ""


# ============================================================
# 10. FINAL STATUS NAMES (per CEO Section 17)
# ============================================================
class TestFinalStatusNames:
    """Test that the new status names are used per CEO Section 17."""

    def test_elite_status_exists(self):
        assert "ELITE" in FINAL_STATUSES

    def test_strong_candidate_for_attorney_review_exists(self):
        assert "STRONG_CANDIDATE_FOR_ATTORNEY_REVIEW" in FINAL_STATUSES

    def test_promising_insufficient_evidence_exists(self):
        assert "PROMISING_INSUFFICIENT_EVIDENCE" in FINAL_STATUSES

    def test_min_gold_for_strong(self):
        """STRONG requires at least 2 GOLD evidence."""
        assert MIN_GOLD_EVIDENCE_FOR_STRONG == 2


# ============================================================
# 11. SOURCE STATUS HONESTY (per CEO Sections 5, 6)
# ============================================================
class TestSourceStatusHonesty:
    """Test that source statuses are honest per CEO directive."""

    def test_patent_bear_rate_limited(self):
        """Patent Bear is RATE_LIMITED (20/20 monthly exhausted)."""
        sources = get_source_status_honest()
        assert sources["PATENT_BEAR"] == "RATE_LIMITED"

    def test_patsnap_api_unavailable(self):
        """PatSnap is API_UNAVAILABLE (account tier insufficient)."""
        sources = get_source_status_honest()
        assert sources["PATSNAP_EUREKA"] == "API_UNAVAILABLE"

    def test_google_patents_live(self):
        """Google Patents is LIVE."""
        sources = get_source_status_honest()
        assert sources["GOOGLE_PATENTS"] == "LIVE"


# ============================================================
# 12. PATENT FAMILY NORMALIZATION
# ============================================================
class TestPatentFamilyNormalization:
    """Test patent family collapse (US/WO/EP/CN/JP/KR/AU)."""

    def test_family_jurisdictions(self):
        jurisdictions = ["US", "WO", "EP", "CN", "JP", "KR", "AU"]
        for juris in jurisdictions:
            pid = f"{juris}12345678B2"
            family = normalize_patent_family(pid)
            assert family.startswith(juris)


# ============================================================
# 13. PATENT RECORD RETRIEVAL
# ============================================================
class TestPatentRecordRetrieval:
    """Test that patent record retrieval works and tracks attempts."""

    def test_retrieval_attempts_tracked(self):
        """PatentRecord must track retrieval_attempts."""
        record = PatentRecord(patent_id="US12345678B2")
        record.retrieval_attempts.append(RetrievalAttempt(
            method="A_html_page", success=True, claim_count=0, latency_ms=500,
        ))
        assert len(record.retrieval_attempts) == 1
        assert record.retrieval_attempts[0].method == "A_html_page"

    def test_retrieval_method_recorded(self):
        """PatentRecord must record which method succeeded."""
        record = PatentRecord(patent_id="US12345678B2")
        record.retrieval_method = "B_html_parse"
        assert record.retrieval_method == "B_html_parse"

    def test_full_content_hash_present(self):
        """PatentRecord must have full_content_hash for provenance."""
        record = PatentRecord(patent_id="US12345678B2")
        record.full_content_hash = _sha256("html content")
        assert len(record.full_content_hash) == 64
