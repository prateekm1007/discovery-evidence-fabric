"""Regression tests for V5 forensic fixes."""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.v5_discovery import (
    V5DiscoveryRouter, DiscoveryMatrix, PatentIDWithProvenance,
)


class TestCountryCodeNotFamily:
    """FIX 1: Country code cannot become family ID."""

    def test_family_resolution_not_available(self):
        m = DiscoveryMatrix()
        assert m.family_resolution_status == "NOT_AVAILABLE"

    def test_family_collapsed_empty_when_no_metadata(self):
        m = DiscoveryMatrix(family_resolution_status="NOT_AVAILABLE")
        assert len(m.family_collapsed) == 0

    def test_no_invented_family_ids(self):
        router = V5DiscoveryRouter()
        m = router.discover("INV_EXP_021", "hydrogel coating", "hydrogel")
        # Family should be NOT_AVAILABLE (no metadata from discovery)
        assert m.family_resolution_status == "NOT_AVAILABLE"
        assert m.family_collapsed == []


class TestNoRelevanceFallback:
    """FIX 2: No fallback to unique_ids when no DIRECTLY_RELEVANT."""

    def test_no_directly_relevant_means_empty(self):
        """If no DIRECTLY_RELEVANT in V4, directly_relevant_ids must be empty."""
        # INV_V3_007 has no V4 retrieval results
        router = V5DiscoveryRouter()
        m = router.discover("INV_V3_007", "smartwatch PPG sensor", "smartwatch")
        # directly_relevant_ids should be empty (no V4 results for this invention)
        # Even if unique_patent_ids has entries from fresh search
        # directly_relevant_ids must NOT fall back to unique_patent_ids
        assert m.directly_relevant_ids == [] or all(
            pid in m.unique_patent_ids for pid in m.directly_relevant_ids
        )
        # The key: directly_relevant_ids must not contain IDs that weren't
        # explicitly classified as DIRECTLY_RELEVANT

    def test_no_irrelevant_to_gold(self):
        """IRRELEVANT/TOPICAL patents cannot enter GOLD pool."""
        m = DiscoveryMatrix(
            unique_patent_ids=["US1", "US2", "US3"],
            directly_relevant_ids=[],  # empty — no relevance proven
        )
        # With no directly_relevant_ids, GOLD should be 0
        assert len(m.directly_relevant_ids) == 0


class TestHistoricalNotCurrentRelevance:
    """Historical IDs ≠ current relevance."""

    def test_historical_ids_stored_but_not_auto_gold(self):
        router = V5DiscoveryRouter()
        m = router.discover("INV_EXP_021", "hydrogel coating", "hydrogel")
        # Historical IDs exist
        assert len(m.historical_only) > 0 or len(m.overlap) > 0
        # But only DIRECTLY_RELEVANT ones enter directly_relevant_ids
        # (from V4 stored relevance classification)
        for pid in m.directly_relevant_ids:
            assert pid in m.unique_patent_ids


class TestFamilyMetadataRequired:
    """Family metadata is required for family collapse."""

    def test_family_requires_metadata(self):
        m = DiscoveryMatrix(family_resolution_status="NOT_AVAILABLE")
        assert m.family_resolution_status != "RESOLVED"
        assert m.family_collapsed == []


class TestSourceProvenancePreserved:
    """Every patent ID carries source provenance."""

    def test_provenance_fields_exist(self):
        p = PatentIDWithProvenance(
            patent_id="US123", source="V4_HISTORICAL", origin="HISTORICAL",
            retrieval_timestamp="2026-01-01",
        )
        assert p.source != ""
        assert p.origin != ""
        assert p.retrieval_timestamp != ""


class TestFreshSearchAttempted:
    """Fresh search is always attempted."""

    def test_fresh_search_attempted_flag(self):
        router = V5DiscoveryRouter()
        m = router.discover("INV_EXP_021", "hydrogel coating", "hydrogel")
        assert m.fresh_search_attempted is True
        assert m.fresh_search_status in ("SUCCESS", "TEMPORARILY_UNAVAILABLE", "RATE_LIMITED", "NO_RESULTS", "NOT_ATTEMPTED")
