"""Evidence coverage report tests (L7) — hermetic, no network.

Covers:
- The 10 directive dimensions are exactly present.
- Usable-record rule: full custody (record_id + raw_payload_sha256 +
  provenance.provider + non-empty normalized + limitations) — a record
  missing ANY component is not usable (negative controls).
- Coverage derivation: COVERED requires usable records AND custody hash
  match; provider failure is PROVIDER_FAILURE (never 'gap-by-absence').
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.base import SourceRecord, utc_now
from scripts.evidence_coverage_report import (
    DIMENSION_PROBES, _usable, measure_dimension,
)


def _full_record(record_id="r1", limitations=("caveat",)):
    return SourceRecord(
        source_id="s", role="R", record_id=record_id, title="t",
        uri="u", retrieved_at=utc_now(), query="q",
        raw_payload_sha256="sha", normalized={"k": "v"},
        provenance={"provider": "s", "raw_payload_sha256": "sha"},
        epistemic_state="OBSERVED", limitations=list(limitations),
    )


class TestDimensionSpec:
    def test_exactly_the_ten_directive_dimensions(self):
        dims = [d["dimension"] for d in DIMENSION_PROBES]
        assert dims == [
            "SCIENCE_COVERAGE", "PATENT_COVERAGE", "DEVICE_COVERAGE",
            "REGULATORY_COVERAGE", "CLINICAL_COVERAGE", "FAILURE_COVERAGE",
            "MATERIAL_COVERAGE", "MANUFACTURING_COVERAGE",
            "STANDARDS_COVERAGE", "COMMERCIAL_COVERAGE",
        ]

    def test_every_probe_has_a_real_query(self):
        for d in DIMENSION_PROBES:
            assert d["query"] and d["probe"] and d["roles"], d["dimension"]


class TestUsableRule:
    def test_full_custody_record_is_usable(self):
        assert _usable(_full_record()) is True

    def test_missing_limitations_not_usable(self):
        # Art. XV: caveats ride WITH the data
        assert _usable(_full_record(limitations=())) is False

    def test_missing_sha_not_usable(self):
        r = _full_record()
        r.raw_payload_sha256 = None
        assert _usable(r) is False

    def test_missing_provider_not_usable(self):
        r = _full_record()
        r.provenance = {"provider": ""}
        assert _usable(r) is False

    def test_empty_normalized_not_usable(self):
        r = _full_record()
        r.normalized = {}
        assert _usable(r) is False


class TestMeasureDimension:
    def test_covered_requires_usable_and_hash_match(self, monkeypatch):
        spec = {"dimension": "X_COVERAGE", "roles": ["R"],
                "probe": "p", "query": "q"}
        good = _full_record()
        result = type("R", (), {
            "source_id": "s", "status": "OK", "records": [good]})()
        monkeypatch.setattr(
            "scripts.evidence_coverage_report._connector_for",
            lambda dim: type("C", (), {"search": lambda self, q, timeout=25: result})())
        m = measure_dimension(spec, timeout=5)
        assert m["coverage"] == "COVERED"
        assert m["usable_records"] == 1
        assert m["custody_verified"] is True

    def test_hash_mismatch_is_not_coverage(self, monkeypatch):
        spec = {"dimension": "X_COVERAGE", "roles": ["R"],
                "probe": "p", "query": "q"}
        bad = _full_record()
        bad.provenance = {"provider": "s", "raw_payload_sha256": "OTHER"}
        result = type("R", (), {
            "source_id": "s", "status": "OK", "records": [bad]})()
        monkeypatch.setattr(
            "scripts.evidence_coverage_report._connector_for",
            lambda dim: type("C", (), {"search": lambda self, q, timeout=25: result})())
        m = measure_dimension(spec, timeout=5)
        assert m["coverage"] == "GAP"
        assert m["custody_verified"] is False

    def test_provider_failure_is_provider_failure(self, monkeypatch):
        spec = {"dimension": "X_COVERAGE", "roles": ["R"],
                "probe": "p", "query": "q"}
        result = type("R", (), {
            "source_id": "s", "status": "SEARCH_FAILED",
            "records": []})()
        monkeypatch.setattr(
            "scripts.evidence_coverage_report._connector_for",
            lambda dim: type("C", (), {"search": lambda self, q, timeout=25: result})())
        m = measure_dimension(spec, timeout=5)
        assert m["coverage"] == "PROVIDER_FAILURE"

    def test_definitive_empty_is_covered_no_match(self, monkeypatch):
        spec = {"dimension": "X_COVERAGE", "roles": ["R"],
                "probe": "p", "query": "q"}
        result = type("R", (), {
            "source_id": "s", "status": "EMPTY", "records": []})()
        monkeypatch.setattr(
            "scripts.evidence_coverage_report._connector_for",
            lambda dim: type("C", (), {"search": lambda self, q, timeout=25: result})())
        m = measure_dimension(spec, timeout=5)
        assert m["coverage"] == "COVERED_NO_MATCH"
