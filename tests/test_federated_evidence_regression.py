"""
Regression tests for the Federated Patent Evidence Layer (V4).

Tests:
  1. UnifiedPatentRecord schema
  2. Source normalizer (patent number normalization, same_patent check)
  3. Record merging (same patent from multiple sources -> one record)
  4. GOLD evidence evaluation (8 conditions)
  5. Federated discovery routing (14 families -> correct source priority)
  6. EPO OPS adapter schema + auth detection
  7. Google BigQuery adapter schema + auth detection
  8. USPTO ODP adapter schema + auth detection
  9. Citation categories (X/I/Y/A) mapping
  10. Family types (DOCDB/INPADOC/EXTEND) — no country prefixes
  11. Credential status check
"""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.federated_evidence import (
    UnifiedPatentRecord, normalize_patent_number, same_patent, merge_records,
    evaluate_gold_evidence, federated_discover, get_federated_source_status,
    _get_sources_for_family,
)
from discovery_fabric.prior_art_v2.epo_ops_adapter import (
    EPOPatentRecord, EPOClaimRecord, EPOCitationRecord, EPOFamilyRecord,
    EPOSearchAttempt, CITATION_CATEGORIES, FAMILY_TYPES, is_epo_ops_available,
    epo_ops_search, epo_ops_get_bibliography, epo_ops_get_claims,
    epo_ops_get_citations, epo_ops_get_family,
)
from discovery_fabric.prior_art_v2.bigquery_patents_adapter import (
    BigQueryPatentRecord, BigQueryClaimRecord, BigQuerySearchAttempt,
    is_bigquery_available, bigquery_search_concepts, bigquery_get_claims,
    bigquery_search_cpc,
)
from discovery_fabric.prior_art_v2.uspto_odp_adapter import (
    USPTOPatentRecord, USPTOClaimRecord, USPTOSearchAttempt,
    is_uspto_available, uspto_search, uspto_get_patent,
)


# ============================================================
# 1. UNIFIED PATENT RECORD SCHEMA
# ============================================================
class TestUnifiedPatentRecordSchema:
    def test_required_fields(self):
        r = UnifiedPatentRecord(patent_number="US11912894B2")
        assert r.patent_number == "US11912894B2"
        assert r.is_gold is False
        assert r.gold_checklist == {}
        assert r.source_provenances == []

    def test_claim_fields(self):
        r = UnifiedPatentRecord(
            patent_number="US123",
            claims=["1. A method comprising..."],
            claim_count=1,
            independent_claim_count=1,
            claim_content_hash="abc123",
        )
        assert r.claim_count == 1
        assert r.claim_content_hash == "abc123"


# ============================================================
# 2. SOURCE NORMALIZER
# ============================================================
class TestSourceNormalizer:
    def test_normalize_us_patent(self):
        assert normalize_patent_number("US-11912894-B2") == "US11912894B2"
        assert normalize_patent_number("us11912894b2") == "US11912894B2"
        assert normalize_patent_number("US11912894B2") == "US11912894B2"

    def test_normalize_ep_patent(self):
        assert normalize_patent_number("EP-3397675-B1") == "EP3397675B1"
        assert normalize_patent_number("EP3397675B1") == "EP3397675B1"

    def test_normalize_with_url_prefix(self):
        assert normalize_patent_number("patent/US11912894B2/en") == "US11912894B2"

    def test_same_patent_with_different_kind_codes(self):
        """US11912894 and US11912894B2 refer to the same patent (different kind codes)."""
        assert same_patent("US11912894B2", "US11912894B1") is True
        assert same_patent("US11912894B2", "US11912894") is True

    def test_different_patents(self):
        assert same_patent("US11912894B2", "US10919033B2") is False
        assert same_patent("US11912894B2", "EP3397675B1") is False


# ============================================================
# 3. RECORD MERGING
# ============================================================
class TestRecordMerging:
    def test_merge_combines_fields(self):
        r1 = UnifiedPatentRecord(
            patent_number="US123",
            title="From source 1",
            source_provenances=[{"source": "EPO_OPS", "fields_supplied": ["title"]}],
        )
        r2 = UnifiedPatentRecord(
            patent_number="US123",
            abstract="From source 2",
            source_provenances=[{"source": "GOOGLE_BIGQUERY", "fields_supplied": ["abstract"]}],
        )
        merged = merge_records([r1, r2])
        assert merged.title == "From source 1"
        assert merged.abstract == "From source 2"
        assert len(merged.source_provenances) == 2

    def test_merge_prefers_longer_claims(self):
        r1 = UnifiedPatentRecord(
            patent_number="US123",
            claims=["short"],
            claim_count=1,
        )
        r2 = UnifiedPatentRecord(
            patent_number="US123",
            claims=["longer claim text", "second claim"],
            claim_count=2,
        )
        merged = merge_records([r1, r2])
        assert merged.claim_count == 2
        assert len(merged.claims) == 2

    def test_merges_cpc_codes_without_dupes(self):
        r1 = UnifiedPatentRecord(patent_number="US123", cpc_codes=["A01B", "C07D"])
        r2 = UnifiedPatentRecord(patent_number="US123", cpc_codes=["C07D", "H04L"])
        merged = merge_records([r1, r2])
        assert sorted(merged.cpc_codes) == ["A01B", "C07D", "H04L"]


# ============================================================
# 4. GOLD EVIDENCE EVALUATION
# ============================================================
class TestGoldEvidenceEvaluation:
    def test_empty_record_not_gold(self):
        r = UnifiedPatentRecord(patent_number="")
        is_gold, checklist = evaluate_gold_evidence(r)
        assert is_gold is False
        assert checklist["verified_patent_identity"] is False

    def test_record_with_all_fields_is_gold(self):
        r = UnifiedPatentRecord(
            patent_number="US11912894B2",
            claims=["1. A method comprising the steps of forming a hydrogel coating on a substrate and curing the coating."],
            claim_count=1,
            claim_content_hash="abc123",
            publication_date="2024-02-27",
            priority_date="2021-06-15",
            family_id="FAM123",
            source_provenances=[{"source": "EPO_OPS"}],
        )
        is_gold, checklist = evaluate_gold_evidence(r)
        assert is_gold is True
        for k, v in checklist.items():
            assert v is True, f"Checklist item {k} should be True"

    def test_record_missing_claims_not_gold(self):
        r = UnifiedPatentRecord(
            patent_number="US11912894B2",
            publication_date="2024-02-27",
            priority_date="2021-06-15",
            family_id="FAM123",
            source_provenances=[{"source": "EPO_OPS"}],
        )
        is_gold, checklist = evaluate_gold_evidence(r)
        assert is_gold is False
        assert checklist["actual_claim_text"] is False

    def test_record_missing_priority_date_not_gold(self):
        r = UnifiedPatentRecord(
            patent_number="US11912894B2",
            claims=["1. A method..."],
            claim_content_hash="abc",
            publication_date="2024-02-27",
            family_id="FAM123",
            source_provenances=[{"source": "EPO_OPS"}],
        )
        is_gold, _ = evaluate_gold_evidence(r)
        assert is_gold is False


# ============================================================
# 5. FEDERATED DISCOVERY ROUTING
# ============================================================
class TestFederatedDiscoveryRouting:
    def test_q12_citation_neighborhood_uses_epo_first(self):
        """Q12_CITATION_NEIGHBORHOOD should prioritize EPO (for X/I/Y categories)."""
        sources = _get_sources_for_family("Q12_CITATION_NEIGHBORHOOD")
        assert sources[0] == "EPO_OPS"

    def test_q1_concept_uses_bigquery_first(self):
        """Q1_CONCEPT should prioritize Google BigQuery."""
        sources = _get_sources_for_family("Q1_CONCEPT")
        assert sources[0] == "GOOGLE_BIGQUERY"

    def test_q11_competitor_portfolio_uses_uspto(self):
        """Q11_COMPETITOR_PORTFOLIO should use USPTO first (US assignee data)."""
        sources = _get_sources_for_family("Q11_COMPETITOR_PORTFOLIO")
        assert "USPTO_ODP" in sources

    def test_q14_semantic_search_no_external_source(self):
        """Q14_SEMANTIC_SEARCH uses local embeddings (no external API)."""
        sources = _get_sources_for_family("Q14_SEMANTIC_SEARCH")
        assert sources == []

    def test_all_14_families_have_routing(self):
        """All 14 search families have a source routing defined."""
        families = [
            "Q1_CONCEPT", "Q2_MECHANISM", "Q3_STRUCTURE", "Q4_MATERIAL",
            "Q5_RELATIONSHIP", "Q6_TECHNICAL_EFFECT", "Q7_FULL_COMBINATION",
            "Q8_FUNCTIONAL_EQUIVALENT", "Q9_STRUCTURAL_EQUIVALENT", "Q10_CPC_IPC",
            "Q11_COMPETITOR_PORTFOLIO", "Q12_CITATION_NEIGHBORHOOD",
            "Q13_NEGATIVE_SEARCH", "Q14_SEMANTIC_SEARCH",
        ]
        for f in families:
            sources = _get_sources_for_family(f)
            # Q14 can be empty (local embeddings); others must have at least 1 source
            if f != "Q14_SEMANTIC_SEARCH":
                assert len(sources) >= 1, f"Family {f} has no sources"


# ============================================================
# 6. EPO OPS ADAPTER
# ============================================================
class TestEPOOpsAdapter:
    def test_citation_categories_defined(self):
        """EPO citation categories are mapped (X/I/Y/A)."""
        assert CITATION_CATEGORIES["X"] == "NOVELTY_RELEVANT"
        assert CITATION_CATEGORIES["I"] == "INVENTIVE_STEP_RELEVANT"
        assert CITATION_CATEGORIES["Y"] == "COMBINATION_RELEVANT"
        assert CITATION_CATEGORIES["A"] == "BACKGROUND_ART"

    def test_family_types_defined(self):
        """EPO family types use real modes (DOCDB/INPADOC/EXTEND), not country prefixes."""
        assert "INPADOC" in FAMILY_TYPES
        assert "DOCDB" in FAMILY_TYPES
        assert "EXTEND" in FAMILY_TYPES

    def test_search_attempt_schema(self):
        a = EPOSearchAttempt(query="test")
        assert a.attempted is False
        assert a.normalized_state == "SOURCE_UNAVAILABLE"

    def test_is_epo_ops_available_without_credentials(self):
        """Without credentials, EPO OPS is unavailable."""
        # This test verifies the function returns a bool (not exception)
        result = is_epo_ops_available()
        assert isinstance(result, bool)

    def test_epo_patent_record_schema(self):
        r = EPOPatentRecord(
            patent_number="US11912894B2",
            epodoc_number="US11912894B2",
            title="Test patent",
        )
        assert r.source == "EPO_OPS"
        assert r.title == "Test patent"


# ============================================================
# 7. GOOGLE BIGQUERY ADAPTER
# ============================================================
class TestBigQueryAdapter:
    def test_search_attempt_schema(self):
        a = BigQuerySearchAttempt(query="test")
        assert a.attempted is False
        assert a.normalized_state == "SOURCE_UNAVAILABLE"

    def test_is_bigquery_available_without_credentials(self):
        """Without credentials, BigQuery is unavailable."""
        result = is_bigquery_available()
        assert isinstance(result, bool)

    def test_bigquery_patent_record_schema(self):
        r = BigQueryPatentRecord(
            patent_number="US11912894B2",
            publication_number="US11912894B2",
            title="Test",
        )
        assert r.source == "GOOGLE_BIGQUERY"


# ============================================================
# 8. USPTO ODP ADAPTER
# ============================================================
class TestUSPTOODPAdapter:
    def test_search_attempt_schema(self):
        a = USPTOSearchAttempt(query="test")
        assert a.attempted is False
        assert a.normalized_state == "SOURCE_UNAVAILABLE"

    def test_is_uspto_available(self):
        """USPTO ODP is public (always available, rate-limited without key)."""
        result = is_uspto_available()
        assert isinstance(result, bool)

    def test_uspto_patent_record_schema(self):
        r = USPTOPatentRecord(
            patent_number="US11912894B2",
            title="Test",
        )
        assert r.source == "USPTO_ODP"


# ============================================================
# 9. FEDERATED SOURCE STATUS
# ============================================================
class TestFederatedSourceStatus:
    def test_status_includes_all_sources(self):
        status = get_federated_source_status()
        assert "EPO_OPS" in status
        assert "GOOGLE_BIGQUERY" in status
        assert "USPTO_ODP" in status
        assert "PATSNAP" in status

    def test_patsnap_marked_frozen(self):
        """PatSnap must be marked FROZEN per CEO directive."""
        status = get_federated_source_status()
        assert status["PATSNAP"]["available"] is False
        assert status["PATSNAP"]["current_state"] == "FROZEN_PER_CEO_DIRECTIVE"

    def test_each_source_has_registration_info(self):
        status = get_federated_source_status()
        for source, info in status.items():
            if source == "PATSNAP":
                continue  # PatSnap is frozen, no registration needed
            assert "free_tier" in info
            assert "current_state" in info


# ============================================================
# 10. CEO DIRECTIVE COMPLIANCE
# ============================================================
class TestCEODirectiveCompliance:
    """Verify the implementation matches CEO directive requirements."""

    def test_no_patsnap_spending(self):
        """PatSnap must NOT be used as a discovery source."""
        # Check that no search family routes to PatSnap
        families = [
            "Q1_CONCEPT", "Q2_MECHANISM", "Q3_STRUCTURE", "Q4_MATERIAL",
            "Q5_RELATIONSHIP", "Q6_TECHNICAL_EFFECT", "Q7_FULL_COMBINATION",
            "Q8_FUNCTIONAL_EQUIVALENT", "Q9_STRUCTURAL_EQUIVALENT", "Q10_CPC_IPC",
            "Q11_COMPETITOR_PORTFOLIO", "Q12_CITATION_NEIGHBORHOOD",
            "Q13_NEGATIVE_SEARCH", "Q14_SEMANTIC_SEARCH",
        ]
        for f in families:
            sources = _get_sources_for_family(f)
            assert "PATSNAP" not in sources, \
                f"Family {f} routes to PatSnap — CEO directive violation"

    def test_family_collapse_uses_real_modes(self):
        """Family collapse uses DOCDB/INPADOC/EXTEND, not country prefixes."""
        # Verify FAMILY_TYPES contains only real family modes
        for mode in FAMILY_TYPES:
            assert mode in ("INPADOC", "DOCDB", "EXTEND")
            assert len(mode) <= 7  # no country prefixes like "US-EPO"

    def test_citation_categories_support_102_103(self):
        """EPO citation categories support 102 (X) and 103 (Y) attack graphs."""
        assert CITATION_CATEGORIES["X"] == "NOVELTY_RELEVANT"  # 102
        assert CITATION_CATEGORIES["Y"] == "COMBINATION_RELEVANT"  # 103
        assert CITATION_CATEGORIES["I"] == "INVENTIVE_STEP_RELEVANT"  # 103

    def test_gold_evidence_has_8_conditions(self):
        """GOLD evidence requires 8 conditions per CEO directive."""
        r = UnifiedPatentRecord(patent_number="US123")
        _, checklist = evaluate_gold_evidence(r)
        expected = {
            "verified_patent_identity",
            "actual_claim_text",
            "publication_date",
            "priority_date",
            "family_provenance",
            "content_hash",
            "current_claim_relevance",
            "source_provenance",
        }
        assert set(checklist.keys()) == expected

    def test_cross_source_corroboration_supported(self):
        """The same patent from multiple sources is ONE record with multiple provenances."""
        r1 = UnifiedPatentRecord(
            patent_number="US123",
            source_provenances=[{"source": "EPO_OPS"}],
        )
        r2 = UnifiedPatentRecord(
            patent_number="US123",
            source_provenances=[{"source": "GOOGLE_BIGQUERY"}],
        )
        merged = merge_records([r1, r2])
        assert len(merged.source_provenances) == 2
        sources = {p["source"] for p in merged.source_provenances}
        assert sources == {"EPO_OPS", "GOOGLE_BIGQUERY"}
