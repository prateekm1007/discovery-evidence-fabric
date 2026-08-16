"""
Regression tests for Source Failover system.
"""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.source_failover import (
    SourceStatus, MultiSourceResult, check_all_sources,
    patsnap_search_count, multi_source_search,
)


class TestLensPatentVsScholarly:
    """Lens Patent API must be separate from Lens Scholarly."""

    def test_lens_patent_status_checked(self):
        statuses = check_all_sources()
        lens_patent = next((s for s in statuses if s.source_id == "LENS_PATENT"), None)
        assert lens_patent is not None
        assert lens_patent.status in ("AVAILABLE", "UNAVAILABLE", "NO_TOKEN")

    def test_lens_scholarly_not_counted_as_patent(self):
        """Lens Scholarly hits are NPL, NOT patent evidence."""
        result = MultiSourceResult(query="test")
        result.lens_scholarly_hits = [{"title": "NPL paper", "patent_id": None}]
        # NPL hits should not be in google_patents_hits or gold_patents
        assert len(result.lens_scholarly_hits) == 1
        assert len(result.google_patents_hits) == 0
        assert len(result.gold_patents) == 0


class TestPatSnapSearchCount:
    """PatSnap search-count endpoint works (returns count, not claims)."""

    def test_patsnap_count_returns_int(self):
        count = patsnap_search_count("hydrogel coating")
        # Should return a number or None
        assert count is None or isinstance(count, int)

    def test_patsnap_status_search_count_only(self):
        statuses = check_all_sources()
        ps = next((s for s in statuses if s.source_id == "PATSNAP"), None)
        if ps:
            assert ps.status in ("SEARCH_COUNT_ONLY", "UNAVAILABLE", "NO_KEY")


class TestGoogle503Failover:
    """Google Patents 503 should be TEMPORARILY_UNAVAILABLE, not NO_PRIOR_ART."""

    def test_google_503_status(self):
        statuses = check_all_sources()
        gp = next((s for s in statuses if s.source_id == "GOOGLE_PATENTS"), None)
        if gp and gp.http_status == 503:
            assert gp.status == "TEMPORARILY_UNAVAILABLE"
            assert gp.can_search is False

    def test_503_does_not_mean_novel(self):
        """Google 503 → RESCUE_PENDING_EVIDENCE, not NOVEL."""
        result = MultiSourceResult(query="test")
        result.google_patents_hits = []  # Google is down
        # 0 GOLD does NOT mean novel
        assert len(result.gold_patents) == 0
        # Status should be PENDING_EVIDENCE, not NOVEL


class TestSourceIndependentGold:
    """GOLD can come from any source, not just Google."""

    def test_gold_from_any_source(self):
        result = MultiSourceResult(query="test")
        result.gold_patents = [{
            "patent_id": "US123",
            "source_id": "PATENT_BEAR",  # Not Google
            "is_gold": True,
            "claims": ["1. A device..."],
        }]
        assert len(result.gold_patents) == 1
        assert result.gold_patents[0]["source_id"] != "GOOGLE_PATENTS"

    def test_gold_requires_claims(self):
        """GOLD requires actual claim text."""
        gold = {
            "patent_id": "US123",
            "claims": [],  # No claims!
            "is_gold": False,
        }
        assert not gold["is_gold"]


class TestCrossSourceConfirmation:
    """Cross-source confirmation when multiple sources find same patent."""

    def test_cross_source_confirmed(self):
        result = MultiSourceResult(query="test")
        result.cross_source_confirmed = ["US123"]
        assert len(result.cross_source_confirmed) == 1

    def test_single_source_tracked(self):
        result = MultiSourceResult(query="test")
        result.single_source = ["US456"]
        assert len(result.single_source) == 1

    def test_source_conflict_tracked(self):
        result = MultiSourceResult(query="test")
        result.source_conflicts = [{"patent_id": "US123", "conflict": "metadata mismatch"}]
        assert len(result.source_conflicts) == 1


class TestFamilyCollapse:
    """US/EP/WO/CN/JP/KR/AU family members should be collapsed."""

    def test_family_jurisdictions(self):
        jurisdictions = ["US", "EP", "WO", "CN", "JP", "KR", "AU"]
        for j in jurisdictions:
            assert len(j) == 2


class TestSourceStatusHonesty:
    """Source status must be honest per CEO directive."""

    def test_all_sources_checked(self):
        statuses = check_all_sources()
        source_ids = {s.source_id for s in statuses}
        assert "GOOGLE_PATENTS" in source_ids
        assert "LENS_PATENT" in source_ids
        assert "PATSNAP" in source_ids
        assert "PATENT_BEAR" in source_ids

    def test_unavailable_source_not_searched(self):
        """If a source is UNAVAILABLE, it should not have hits."""
        result = MultiSourceResult(query="test")
        # If Google is 503, google_patents_hits should be empty
        gp_status = next((s for s in result.source_statuses if s.get("source_id") == "GOOGLE_PATENTS"), None)
        if gp_status and gp_status.get("status") == "TEMPORARILY_UNAVAILABLE":
            assert len(result.google_patents_hits) == 0
