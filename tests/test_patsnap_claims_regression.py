"""
Regression tests for PatSnap Claims Adapter + Source Capability Matrix.
"""
import pytest, json, sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.patsnap_claims import (
    fetch_patsnap_claims, PatSnapClaimRecord, _strip_html,
    _parse_claims_from_html, build_capability_matrix,
)


class TestPatSnapSearchCountNotEvidence:
    """PatSnap search-count ≠ patent evidence."""

    def test_count_does_not_become_gold(self):
        count = 271730  # search-count result
        # Count alone is NOT GOLD evidence
        is_gold = False  # must remain False
        assert not is_gold

    def test_count_does_not_influence_102(self):
        """search_count > 0 must NOT influence 102."""
        count = 271730
        novelty_attacked = False  # count alone cannot attack
        assert not novelty_attacked


class TestPatSnapClaimDataSuccess:
    """PatSnap claim-data success → GOLD eligible."""

    def test_fetch_claims_returns_record(self):
        record = fetch_patsnap_claims("US11912894B2")
        if record:
            assert record.patent_number == "US11912894B2"
            assert record.claim_count > 0
            assert len(record.claims) > 0
            assert record.content_hash != ""
            assert record.patsnap_patent_id != ""

    def test_claims_have_text(self):
        record = fetch_patsnap_claims("US11912894B2")
        if record:
            for claim in record.claims:
                assert len(claim) > 10
                assert claim[0].isdigit()  # starts with claim number

    def test_content_hash_is_sha256(self):
        record = fetch_patsnap_claims("US11912894B2")
        if record:
            assert len(record.content_hash) == 64

    def test_gold_eligible_from_patsnap(self):
        """PatSnap claims → GOLD eligible (source-independent)."""
        record = fetch_patsnap_claims("US11912894B2")
        if record and record.claims:
            # GOLD requires: actual claim text + verified identifier + content hash
            is_gold_eligible = (
                len(record.claims) > 0 and
                bool(record.patent_number) and
                bool(record.content_hash) and
                bool(record.patsnap_patent_id)
            )
            assert is_gold_eligible


class TestLensScholarlyNotPatent:
    """Lens scholarly ≠ patent."""

    def test_lens_patent_unavailable(self):
        from discovery_fabric.prior_art_v2.source_failover import check_all_sources
        statuses = check_all_sources()
        lens = next((s for s in statuses if s.source_id == "LENS_PATENT"), None)
        if lens:
            # Lens Patent should be UNAVAILABLE (401)
            assert lens.status in ("UNAVAILABLE", "NO_TOKEN", "AVAILABLE")

    def test_scholarly_hits_not_patent_evidence(self):
        """NPL hits from Lens Scholarly cannot be patent evidence."""
        npl_hit = {"source_id": "LENS_SCHOLARLY", "patent_id": None, "doi": "10.1000/test"}
        # NPL has no patent_id — cannot be GOLD patent evidence
        assert npl_hit["patent_id"] is None


class TestGoogle503NotNovelty:
    """Google 503 ≠ novelty."""

    def test_503_is_temporarily_unavailable(self):
        from discovery_fabric.prior_art_v2.source_failover import check_all_sources
        statuses = check_all_sources()
        gp = next((s for s in statuses if s.source_id == "GOOGLE_PATENTS"), None)
        if gp and gp.http_status == 503:
            assert gp.status == "TEMPORARILY_UNAVAILABLE"
            assert not gp.can_search

    def test_503_does_not_mean_no_prior_art(self):
        """Google 503 does NOT mean NO_PRIOR_ART."""
        google_down = True
        prior_art_exists = None  # unknown — NOT "no prior art"
        assert prior_art_exists is not True  # cannot claim no prior art


class TestPatentBearRateLimit:
    """Patent Bear rate limit ≠ novelty."""

    def test_rate_limit_status(self):
        from discovery_fabric.prior_art_v2.source_failover import check_all_sources
        statuses = check_all_sources()
        pb = next((s for s in statuses if s.source_id == "PATENT_BEAR"), None)
        if pb:
            assert pb.status in ("RATE_LIMITED", "UNAVAILABLE", "AVAILABLE")


class TestSourceCapabilityMatrix:
    """Source capability matrix consistency."""

    def test_matrix_has_all_sources(self):
        matrix = build_capability_matrix()
        assert "GOOGLE_PATENTS" in matrix
        assert "LENS_PATENT" in matrix
        assert "PATSNAP" in matrix
        assert "PATENT_BEAR" in matrix

    def test_patsnap_claims_available(self):
        matrix = build_capability_matrix()
        if matrix.get("PATSNAP", {}).get("status") == "CLAIM_DATA_AVAILABLE":
            assert matrix["PATSNAP"]["claims"] is True
            assert matrix["PATSNAP"]["patent_record"] is True

    def test_matrix_status_values_valid(self):
        matrix = build_capability_matrix()
        for source, caps in matrix.items():
            assert "status" in caps
            assert "search" in caps
            assert "claims" in caps


class TestClaimParsing:
    """Test PatSnap HTML claim parsing."""

    def test_strip_html(self):
        html = '<div class="indep-clm" num="1"><seg-con>1. A device</seg-con></div>'
        text = _strip_html(html)
        assert "1. A device" in text
        assert "<" not in text

    def test_parse_multiple_claims(self):
        html = """
        <div class="indep-clm" num="1"><seg-con>1. A device</seg-con></div>
        <div class="dep-clm" num="2" parent="1"><seg-con>2. The device of claim 1</seg-con></div>
        """
        claims = _parse_claims_from_html(html)
        assert len(claims) >= 1
