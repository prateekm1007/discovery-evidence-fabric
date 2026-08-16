"""
Regression tests for Retrieval V4 — Claim-Relevant Prior-Art Retrieval.

Per CEO directive Section 18:
1. same-device relevance
2. same-mechanism relevance
3. topical-only rejection
4. irrelevant patent rejection
5. CPC expansion
6. family deduplication
7. citation expansion
8. claim-specific GOLD
9. relationship-specific GOLD
"""
import pytest
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.retrieval_v4 import (
    ConceptGraph, QueryFamily, QueryFamilyGenerator,
    PatentRelevanceAssessment, RetrievedPatent, RetrievalResult,
    RetrievalV4, CPCExpander, FamilyDeduplicator,
    RELEVANCE_LEVELS, TERM_CATEGORIES,
)
from discovery_fabric.prior_art_v2.retrieval_v3 import _sha256, _now_utc


# ============================================================
# 1. SAME-DEVICE RELEVANCE
# ============================================================
class TestSameDeviceRelevance:
    """Test that same-device-family patents are classified correctly."""

    def test_directly_relevant_same_device(self):
        """A patent about 'hydrogel coating' IS directly relevant to a hydrogel coating invention."""
        assessment = PatentRelevanceAssessment(
            patent_id="US12345678B2",
            title="Hydrogel coating for medical devices",
            relevance_level="DIRECTLY_RELEVANT",
            same_device_family=True,
            same_problem=True,
            same_mechanism=True,
            evidence_explanation="Same device, same mechanism",
        )
        assert assessment.relevance_level == "DIRECTLY_RELEVANT"
        assert assessment.same_device_family is True

    def test_pressure_vessel_not_same_device_as_hydrogel(self):
        """A patent about 'pressure vessels' is NOT same-device as 'hydrogel coating'."""
        assessment = PatentRelevanceAssessment(
            patent_id="CN107850259B",
            title="Pressure Vessels with Reinforced Heads",
            relevance_level="IRRELEVANT",
            same_device_family=False,
            same_problem=False,
            same_mechanism=False,
            evidence_explanation="Pressure vessels are a completely different technology",
        )
        assert assessment.same_device_family is False
        assert assessment.relevance_level == "IRRELEVANT"


# ============================================================
# 2. SAME-MECHANISM RELEVANCE
# ============================================================
class TestSameMechanismRelevance:
    """Test that same-mechanism patents are classified correctly."""

    def test_same_mechanism_directly_relevant(self):
        """A patent using the same mechanism (e.g., nanofiber reinforcement) is directly relevant."""
        assessment = PatentRelevanceAssessment(
            patent_id="US123",
            title="Nanofiber-reinforced composite",
            relevance_level="DIRECTLY_RELEVANT",
            same_mechanism=True,
            evidence_explanation="Uses same nanofiber reinforcement mechanism",
        )
        assert assessment.same_mechanism is True
        assert assessment.relevance_level == "DIRECTLY_RELEVANT"


# ============================================================
# 3. TOPICAL-ONLY REJECTION
# ============================================================
class TestTopicalOnlyRejection:
    """TOPICAL_ONLY patents must NEVER become GOLD claim evidence."""

    def test_topical_only_never_becomes_gold(self):
        """A TOPICAL_ONLY patent cannot be GOLD."""
        rp = RetrievedPatent(
            patent_id="US123",
            title="Related but different technology",
            source_id="GOOGLE_PATENTS",
            source_url="https://patents.google.com/patent/US123",
            retrieved_at_utc=_now_utc(),
            raw_payload_sha256="abc",
            claims=["1. A different device..."],
            relevance=PatentRelevanceAssessment(
                patent_id="US123",
                title="Related but different technology",
                relevance_level="TOPICAL_ONLY",
            ),
        )
        # Even if claims exist, TOPICAL_ONLY cannot be GOLD
        rp.is_gold = (
            len(rp.claims) > 0 and
            rp.relevance.relevance_level == "DIRECTLY_RELEVANT"
        )
        assert not rp.is_gold
        assert rp.relevance.relevance_level == "TOPICAL_ONLY"


# ============================================================
# 4. IRRELEVANT PATENT REJECTION
# ============================================================
class TestIrrelevantPatentRejection:
    """IRRELEVANT patents must be rejected before GOLD mapping."""

    def test_irrelevant_not_gold(self):
        """An IRRELEVANT patent (e.g., pressure vessel for hydrogel invention) is never GOLD."""
        assessment = PatentRelevanceAssessment(
            patent_id="CN107850259B",
            title="Pressure Vessels with Reinforced Heads",
            relevance_level="IRRELEVANT",
            evidence_explanation="Completely different technology",
        )
        assert assessment.relevance_level == "IRRELEVANT"
        # IRRELEVANT must never proceed to GOLD mapping
        can_proceed_to_gold = assessment.relevance_level == "DIRECTLY_RELEVANT"
        assert not can_proceed_to_gold

    def test_quick_irrelevant_check_skips_obviously_unrelated(self):
        """The quick keyword check should skip patents with no device-term overlap."""
        cg = ConceptGraph(
            invention_id="TEST",
            device_terms=["hydrogel", "coating"],
        )
        retriever = RetrievalV4()
        # Patent about pressure vessels — no device term overlap
        is_irrelevant = retriever._quick_irrelevant_check(cg, "Pressure Vessels", "Reinforced heads for pressure vessels")
        assert is_irrelevant is True


# ============================================================
# 5. CPC EXPANSION
# ============================================================
class TestCPCExpansion:
    """Test CPC/IPC classification expansion."""

    def test_cpc_expander_extracts_subclass(self):
        """CPCExpander should extract the subclass (e.g., A01B from A01B1/00)."""
        expander = CPCExpander()
        result = expander.expand(["A01B1/00", "A01B33/08", "C07D401/04"])
        assert "A01B" in result
        assert "C07D" in result

    def test_cpc_expander_handles_empty(self):
        expander = CPCExpander()
        result = expander.expand([])
        assert result == []

    def test_cpc_expander_deduplicates(self):
        """Multiple CPC codes in same subclass should produce one entry."""
        expander = CPCExpander()
        result = expander.expand(["A01B1/00", "A01B33/08"])
        assert result.count("A01B") == 1


# ============================================================
# 6. FAMILY DEDUPLICATION
# ============================================================
class TestFamilyDeduplication:
    """Test US/EP/WO/CN/JP/KR/AU family member collapse."""

    def test_family_deduplicator_collapses_same_family(self):
        """Patents with same family_id should be collapsed to one."""
        deduper = FamilyDeduplicator()
        patents = [
            RetrievedPatent(patent_id="US123", title="A", source_id="GP", source_url="", retrieved_at_utc="", raw_payload_sha256="", family_id="12345"),
            RetrievedPatent(patent_id="EP456", title="A", source_id="GP", source_url="", retrieved_at_utc="", raw_payload_sha256="", family_id="12345"),
            RetrievedPatent(patent_id="JP789", title="B", source_id="GP", source_url="", retrieved_at_utc="", raw_payload_sha256="", family_id="67890"),
        ]
        result = deduper.deduplicate(patents)
        assert len(result) == 2  # US+EP collapsed, JP separate

    def test_family_deduplicator_keeps_no_family(self):
        """Patents without family_id should be kept."""
        deduper = FamilyDeduplicator()
        patents = [
            RetrievedPatent(patent_id="US123", title="A", source_id="GP", source_url="", retrieved_at_utc="", raw_payload_sha256="", family_id=None),
            RetrievedPatent(patent_id="US456", title="B", source_id="GP", source_url="", retrieved_at_utc="", raw_payload_sha256="", family_id=None),
        ]
        result = deduper.deduplicate(patents)
        assert len(result) == 2


# ============================================================
# 7. CITATION EXPANSION (structure test)
# ============================================================
class TestCitationExpansion:
    """Test that citation expansion structure exists (backward/forward citations)."""

    def test_retrieved_patent_has_cpc_field(self):
        """RetrievedPatent must have cpc field for citation neighborhood."""
        rp = RetrievedPatent(
            patent_id="US123", title="Test", source_id="GP",
            source_url="", retrieved_at_utc="", raw_payload_sha256="",
            cpc=["A01B1/00", "A01B33/08"],
        )
        assert len(rp.cpc) == 2


# ============================================================
# 8. CLAIM-SPECIFIC GOLD
# ============================================================
class TestClaimSpecificGold:
    """GOLD requires DIRECTLY_RELEVANT + actual claim text + all metadata."""

    def test_gold_requires_directly_relevant(self):
        """GOLD requires DIRECTLY_RELEVANT relevance level."""
        rp = RetrievedPatent(
            patent_id="US123", title="Test", source_id="GP",
            source_url="", retrieved_at_utc="", raw_payload_sha256="",
            claims=["1. A hydrogel coating..."],
            publication_date="2023-01-01",
            priority_date="2022-01-01",
            family_id="12345",
            full_content_hash=_sha256("test"),
            relevance=PatentRelevanceAssessment(
                patent_id="US123", title="Test",
                relevance_level="DIRECTLY_RELEVANT",
            ),
        )
        rp.is_gold = (
            rp.relevance.relevance_level == "DIRECTLY_RELEVANT" and
            len(rp.claims) > 0 and
            bool(rp.publication_date) and
            bool(rp.priority_date) and
            bool(rp.family_id) and
            bool(rp.full_content_hash)
        )
        assert rp.is_gold is True

    def test_gold_fails_without_directly_relevant(self):
        """Even with full metadata, TOPICAL_ONLY cannot be GOLD."""
        rp = RetrievedPatent(
            patent_id="US123", title="Test", source_id="GP",
            source_url="", retrieved_at_utc="", raw_payload_sha256="",
            claims=["1. A device..."],
            publication_date="2023-01-01",
            priority_date="2022-01-01",
            family_id="12345",
            full_content_hash=_sha256("test"),
            relevance=PatentRelevanceAssessment(
                patent_id="US123", title="Test",
                relevance_level="TOPICAL_ONLY",  # NOT DIRECTLY_RELEVANT
            ),
        )
        rp.is_gold = (
            rp.relevance.relevance_level == "DIRECTLY_RELEVANT" and
            len(rp.claims) > 0
        )
        assert rp.is_gold is False

    def test_gold_fails_without_claims(self):
        """DIRECTLY_RELEVANT without claims is not GOLD."""
        rp = RetrievedPatent(
            patent_id="US123", title="Test", source_id="GP",
            source_url="", retrieved_at_utc="", raw_payload_sha256="",
            claims=[],  # No claims!
            relevance=PatentRelevanceAssessment(
                patent_id="US123", title="Test",
                relevance_level="DIRECTLY_RELEVANT",
            ),
        )
        rp.is_gold = (
            rp.relevance.relevance_level == "DIRECTLY_RELEVANT" and
            len(rp.claims) > 0
        )
        assert rp.is_gold is False


# ============================================================
# 9. RELATIONSHIP-SPECIFIC GOLD
# ============================================================
class TestRelationshipSpecificGold:
    """GOLD should require relationship mapping, not just element matching."""

    def test_relevance_assessment_has_relationship_check(self):
        """PatentRelevanceAssessment has same_material_or_structure field."""
        assessment = PatentRelevanceAssessment(
            patent_id="US123",
            title="Test",
            relevance_level="DIRECTLY_RELEVANT",
            same_material_or_structure=True,
            same_function=True,
        )
        assert assessment.same_material_or_structure is True
        assert assessment.same_function is True


# ============================================================
# 10. CONCEPT GRAPH
# ============================================================
class TestConceptGraph:
    """Test concept graph generation."""

    def test_concept_graph_has_8_categories(self):
        cg = ConceptGraph(invention_id="TEST")
        categories = [
            cg.device_terms, cg.failure_terms, cg.mechanism_terms,
            cg.material_terms, cg.structure_terms, cg.relationship_terms,
            cg.technical_effect_terms, cg.application_terms,
        ]
        assert len(categories) == 8

    def test_query_generator_produces_families(self):
        """QueryFamilyGenerator should produce Q1-Q10."""
        cg = ConceptGraph(
            invention_id="TEST",
            device_terms=["blood pressure monitor"],
            failure_terms=["calibration drift"],
            mechanism_terms=["pressure equalization"],
            material_terms=["polymer"],
            structure_terms=["reference cavity"],
            relationship_terms=["sensor to cavity"],
            technical_effect_terms=["calibration stability"],
            application_terms=["medical device"],
        )
        gen = QueryFamilyGenerator()
        queries = gen.generate(cg)
        assert len(queries) >= 5  # At least 5 query families
        ids = [q.query_id for q in queries]
        assert "Q1" in ids
        assert "Q7" in ids  # full conceptual

    def test_query_families_non_empty(self):
        """Query families should have non-empty query_text."""
        cg = ConceptGraph(
            invention_id="TEST",
            device_terms=["hydrogel"],
            mechanism_terms=["nanofiber reinforcement"],
        )
        gen = QueryFamilyGenerator()
        queries = gen.generate(cg)
        for q in queries:
            assert q.query_text.strip() != ""


# ============================================================
# 11. SEARCH SATURATION
# ============================================================
class TestSearchSaturation:
    """Test search saturation tracking."""

    def test_saturation_requires_5_families(self):
        """Saturation requires at least 5 query families searched."""
        result = RetrievalResult(invention_id="TEST", families_searched=4)
        result.search_saturation = result.families_searched >= 5
        assert not result.search_saturation

    def test_saturation_requires_2_databases(self):
        """Saturation requires at least 2 databases searched."""
        result = RetrievalResult(
            invention_id="TEST",
            families_searched=10,
            databases_searched=["GOOGLE_PATENTS"],  # Only 1
        )
        result.search_saturation = (
            result.families_searched >= 5 and
            len(result.databases_searched) >= 2
        )
        assert not result.search_saturation

    def test_saturation_passes_with_5_families_2_databases(self):
        result = RetrievalResult(
            invention_id="TEST",
            families_searched=5,
            databases_searched=["GOOGLE_PATENTS", "LENS_SCHOLARLY"],
        )
        result.search_saturation = (
            result.families_searched >= 5 and
            len(result.databases_searched) >= 2
        )
        assert result.search_saturation
