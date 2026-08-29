"""Commercial-role tests (L3) — hermetic, no network, Art. XVII hardened.

Covers:
- GUDID commercial connector: commercial normalization (company, product
  category, distribution status, end date), record ids from GUDID keys.
- Commercial dimension coverage map: pricing/procurement is an HONEST
  NOT_COVERED gap (never filled with scraped noise); competitive
  mechanism is GRAPH_DERIVED, never asserted from a commercial source.
- openFDA definitive-empty semantics inherited (404 NOT_FOUND = EMPTY).
- Registry wiring + clean validation after the commercial edit.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import retrieval_log
from discovery_fabric.source_registry.base import STATUS_EMPTY, STATUS_OK
from discovery_fabric.source_registry.connectors.commercial import (
    COMMERCIAL_DIMENSION_COVERAGE, GudidCommercialConnector,
    GUDID_COMMERCIAL_LIMITATIONS,
)
from discovery_fabric.source_registry.registry import (
    SOURCE_REGISTRY, validate_registry,
)


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "retrieval_log.jsonl")
    yield


GUDID_PAYLOAD = {
    "results": [
        {
            "public_device_record_key": "key-001",
            "brand_name": "Consensus Hip System",
            "company_name": "Shalby Advanced Technologies, Inc.",
            "labeler_duns_number": "123456789",
            "version_or_model_number": "CHS-1",
            "product_codes": [{"code": "MEH",
                                "name": "Prosthesis, hip, semi-constrained, uncemented"}],
            "gmdn_terms": [{"gmdn_pt_name": "Hip joint prosthesis, ceramic"}],
            "commercial_distribution_status": "In Commercial Distribution",
            "commercial_distribution_end_date": None,
            "device_count_in_base_package": 1,
            "publish_date": "2023-01-05",
        },
        {
            "public_device_record_key": "key-002",
            "brand_name": "Legacy Hip",
            "company_name": "Old Corp",
            "product_codes": [{"code": "LPH", "name": "Prosthesis, hip"}],
            "commercial_distribution_status": "Not in Commercial Distribution",
            "commercial_distribution_end_date": "2019-06-30",
        },
    ],
    "meta": {"results": {"total": 2}},
}


def _wire(payload: bytes | None, http_status=200, status=STATUS_OK):
    c = GudidCommercialConnector()
    if payload is not None:
        c._request = lambda url, timeout=25: (payload, status, http_status, None, None)
    else:
        c._request = lambda url, timeout=25: (None, status, http_status, "injected", None)
    return c


class TestGudidCommercial:
    def test_commercial_normalization_fields(self):
        res = _wire(json.dumps(GUDID_PAYLOAD).encode()).search("hip")
        assert res.status == STATUS_OK
        r = res.records[0]
        n = r.normalized
        assert n["company_name"] == "Shalby Advanced Technologies, Inc."
        assert n["product_codes"] == ["MEH"]
        assert n["gmdn_pt_names"] == ["Hip joint prosthesis, ceramic"]
        assert n["is_on_market"] is True
        assert r.record_id == "gudid-commercial:key-001"
        assert r.role == "COMMERCIAL"

    def test_off_market_product_carries_end_date(self):
        res = _wire(json.dumps(GUDID_PAYLOAD).encode()).search("hip")
        off = res.records[1]
        assert off.normalized["is_on_market"] is False
        assert off.normalized["commercial_distribution_end_date"] == "2019-06-30"

    def test_pricing_gap_disclosed_on_every_record(self):
        # Art. XV: the honest gap rides WITH the data, not in a README
        res = _wire(json.dumps(GUDID_PAYLOAD).encode()).search("hip")
        assert any("PRICING_PROCUREMENT_SIGNAL" in l
                   for l in res.records[0].limitations)

    def test_openfda_404_not_found_is_definitive_empty(self):
        body = json.dumps({"error": {"code": "NOT_FOUND",
                                     "message": "No matches found!"}}).encode()
        res = _wire(body, http_status=404).search("nonexistent brand")
        assert res.status == STATUS_EMPTY
        assert res.ok is True

    def test_total_hits_from_openfda_meta(self):
        res = _wire(json.dumps(GUDID_PAYLOAD).encode()).search("hip")
        assert res.total_hits == 2


class TestCommercialDimensionCoverage:
    def test_all_seven_directive_dimensions_present(self):
        expected = {
            "COMMERCIALIZED_DEVICE", "MARKETED_PRODUCT", "COMPANY",
            "PRODUCT_CATEGORY", "COMPETITIVE_MECHANISM",
            "PRICING_PROCUREMENT_SIGNAL", "COMMERCIAL_FAILURE_RECALL",
        }
        assert expected == set(COMMERCIAL_DIMENSION_COVERAGE.keys())

    def test_pricing_is_honest_not_covered(self):
        dim = COMMERCIAL_DIMENSION_COVERAGE["PRICING_PROCUREMENT_SIGNAL"]
        assert dim["state"] == "NOT_COVERED"
        assert dim["source"] is None
        assert "defensible provenance" in dim["evidence"]

    def test_competitive_mechanism_is_graph_derived_not_sourced(self):
        dim = COMMERCIAL_DIMENSION_COVERAGE["COMPETITIVE_MECHANISM"]
        assert dim["state"] == "GRAPH_DERIVED"

    def test_covered_dimensions_name_live_sources(self):
        for dim in ("COMMERCIALIZED_DEVICE", "MARKETED_PRODUCT",
                    "COMPANY", "PRODUCT_CATEGORY"):
            assert COMMERCIAL_DIMENSION_COVERAGE[dim]["source"] == "gudid_commercial"

    def test_commercial_failure_uses_recall_overlay(self):
        dim = COMMERCIAL_DIMENSION_COVERAGE["COMMERCIAL_FAILURE_RECALL"]
        assert dim["state"] == "OVERLAY"
        assert dim["source"] == "fda_recall"


class TestRegistryWiring:
    def test_connector_resolves(self):
        from discovery_fabric.source_registry.health import load_connector
        cls = load_connector("gudid_commercial")
        assert cls is not None and cls.SOURCE_ID == "gudid_commercial"

    def test_placeholder_removed(self):
        assert "commercial_product_sources" not in SOURCE_REGISTRY

    def test_registry_validates_clean_after_commercial_edit(self):
        assert validate_registry() == []

    def test_commercial_role_has_real_source(self):
        from discovery_fabric.source_registry.registry import sources_for_role
        srcs = sources_for_role("COMMERCIAL")
        assert any(s["connector"] for s in srcs)
