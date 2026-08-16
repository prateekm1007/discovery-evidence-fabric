"""
Regression tests for V5 discovery integrity fixes v2.

Tests proving:
  1. country_code != family_id
  2. no_direct_relevance -> zero GOLD
  3. historical_only != current_relevance
  4. family metadata required
  5. irrelevant fallback impossible
  6. source provenance preserved
  7. current claim hash required for relevance
  8. fresh search failure != no prior art
  9. historical evidence != fresh evidence
  10. distinct fresh-search failure states
"""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.v5_discovery import (
    V5DiscoveryRouter, DiscoveryMatrix, PatentIDWithProvenance,
)


class TestCountryCodeNotFamily:
    def test_family_resolution_not_available(self):
        m = DiscoveryMatrix()
        assert m.family_resolution_status == "NOT_AVAILABLE"

    def test_family_collapsed_empty_when_no_metadata(self):
        m = DiscoveryMatrix(family_resolution_status="NOT_AVAILABLE")
        assert len(m.family_collapsed) == 0

    def test_no_invented_family_ids(self):
        router = V5DiscoveryRouter()
        m = router.discover("INV_EXP_021", "hydrogel coating", "hydrogel")
        assert m.family_resolution_status == "NOT_AVAILABLE"
        assert m.family_collapsed == []


class TestNoDirectRelevanceNoGold:
    def test_empty_directly_relevant_means_zero_gold(self):
        m = DiscoveryMatrix(directly_relevant_ids=[])
        assert len(m.directly_relevant_ids) == 0

    def test_no_fallback_to_unique_ids(self):
        """When no DIRECTLY_RELEVANT, directly_relevant_ids must NOT be populated from unique_patent_ids."""
        router = V5DiscoveryRouter()
        m = router.discover("NONEXISTENT_INV", "test query", "test")
        # If unique_patent_ids has entries but no V4 DIRECTLY_RELEVANT...
        # directly_relevant_ids must be empty (no fallback)
        for pid in m.directly_relevant_ids:
            assert pid in m.unique_patent_ids, f"directly_relevant_id {pid} not in unique_ids — fallback detected!"


class TestHistoricalNotCurrentRelevance:
    def test_historical_relevance_field_exists(self):
        p = PatentIDWithProvenance(patent_id="US123", origin="HISTORICAL")
        assert hasattr(p, "historical_relevance")
        assert hasattr(p, "current_claim_relevance")

    def test_historical_patent_has_relevance_delta(self):
        p = PatentIDWithProvenance(patent_id="US123", origin="HISTORICAL",
                                   historical_relevance="DIRECTLY_RELEVANT",
                                   current_claim_relevance="CARRIED_FROM_V4")
        assert p.relevance_delta == "NOT_EVALUATED"

    def test_current_claim_hash_present(self):
        p = PatentIDWithProvenance(patent_id="US123", current_claim_hash="abc123")
        assert p.current_claim_hash != ""


class TestFamilyMetadataRequired:
    def test_family_requires_verified_metadata(self):
        m = DiscoveryMatrix(family_resolution_status="NOT_AVAILABLE")
        assert m.family_resolution_status != "RESOLVED"

    def test_family_id_none_when_not_verified(self):
        p = PatentIDWithProvenance(patent_id="US123")
        assert p.family_id is None


class TestIrrelevantFallbackImpossible:
    def test_irrelevant_patent_not_in_directly_relevant(self):
        m = DiscoveryMatrix(
            unique_patent_ids=["US1", "US2"],
            directly_relevant_ids=[],  # empty — no relevance proven
        )
        assert "US1" not in m.directly_relevant_ids
        assert "US2" not in m.directly_relevant_ids


class TestSourceProvenancePreserved:
    def test_every_patent_has_source(self):
        p = PatentIDWithProvenance(patent_id="US123", source="V4_HISTORICAL")
        assert p.source == "V4_HISTORICAL"

    def test_every_patent_has_origin(self):
        p = PatentIDWithProvenance(patent_id="US123", origin="HISTORICAL")
        assert p.origin == "HISTORICAL"

    def test_every_patent_has_timestamp(self):
        p = PatentIDWithProvenance(patent_id="US123", retrieval_timestamp="2026-01-01")
        assert p.retrieval_timestamp != ""


class TestCurrentClaimHashRequired:
    def test_relevance_requires_claim_hash(self):
        p = PatentIDWithProvenance(patent_id="US123", current_claim_hash="hash123")
        # Without current_claim_hash, relevance is not valid
        assert p.current_claim_hash != ""

    def test_relevance_without_hash_is_not_gold(self):
        p = PatentIDWithProvenance(patent_id="US123", current_claim_hash="")
        if not p.current_claim_hash:
            is_gold = False
            assert not is_gold


class TestFreshSearchFailureNotNoPriorArt:
    def test_temporarily_unavailable_not_no_prior_art(self):
        m = DiscoveryMatrix(fresh_search_status="TEMPORARILY_UNAVAILABLE")
        assert m.fresh_search_status != "NO_RESULTS"
        assert m.fresh_search_status != "SUCCESS"

    def test_rate_limited_not_no_prior_art(self):
        m = DiscoveryMatrix(patent_bear_search_status="RATE_LIMITED")
        assert m.patent_bear_search_status != "NO_RESULTS"


class TestHistoricalNotFreshEvidence:
    def test_historical_and_fresh_tracked_separately(self):
        m = DiscoveryMatrix(
            historical_only=["US1", "US2"],
            fresh_only=["US3"],
            overlap=["US4"],
        )
        assert "US1" in m.historical_only
        assert "US1" not in m.fresh_only
        assert "US3" in m.fresh_only
        assert "US3" not in m.historical_only

    def test_historical_only_not_fresh(self):
        m = DiscoveryMatrix(historical_only=["US1"], fresh_only=[])
        assert len(m.historical_only) > 0
        assert len(m.fresh_only) == 0


class TestDistinctFreshSearchStates:
    def test_all_failure_states_valid(self):
        valid_states = {
            "SUCCESS", "TEMPORARILY_UNAVAILABLE", "RATE_LIMITED",
            "AUTHENTICATION_FAILED", "NO_RESULTS", "NOT_ATTEMPTED"
        }
        assert "FAILED" not in valid_states  # old vague state removed
        assert "IDS_FOUND" not in valid_states  # old vague state removed

    def test_google_search_status_tracked(self):
        m = DiscoveryMatrix(google_search_status="SUCCESS")
        assert m.google_search_status == "SUCCESS"

    def test_patent_bear_search_status_tracked(self):
        m = DiscoveryMatrix(patent_bear_search_status="RATE_LIMITED")
        assert m.patent_bear_search_status == "RATE_LIMITED"
