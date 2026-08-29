"""Source registry tests — hermetic (no network), Art. XVII hardened.

Covers:
- Registry structure: 13 directive fields per source; role validity;
  no-connector-never-LIVE rule (negative control).
- Base connector semantics (Art. XXI.3): provider failure is NOT absence —
  SEARCH_FAILED / TIMEOUT / RATE_LIMITED / PARSE_FAILED are distinct from
  EMPTY; EMPTY only after a definitive provider answer.
- MAUDE limitation metadata (Art. XXI.5).
- Retrieval-log custody: hash chain valid; tamper detection (attack test).
- Health status derivation rules.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import retrieval_log
from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, STATUS_RATE_LIMITED, STATUS_SEARCH_FAILED,
    STATUS_TIMEOUT, STATUS_PARSE_FAILED, STATUS_UNAVAILABLE,
)
from discovery_fabric.source_registry.connectors.openfda import (
    MaudeConnector, MAUDE_LIMITATIONS, _OpenFdaBase,
)
from discovery_fabric.source_registry.connectors.scientific import EuropePmcConnector
from discovery_fabric.source_registry.registry import (
    SOURCE_REGISTRY, REQUIRED_FIELDS, apply_measured_statuses, validate_registry,
    NOT_MEASURED,
)
from discovery_fabric.source_registry.roles import VALID_ROLES, COVERAGE_MATRIX_ROLES


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    """Never write test custody entries into the real log (Art. IX)."""
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "retrieval_log.jsonl")
    yield


def _mk_connector(payload: bytes | None, http_status=200, status=STATUS_OK):
    """Build a minimal concrete connector with a canned _request."""
    class _C(_OpenFdaBase):
        SOURCE_ID = "test_source"
        ROLES = ("SCIENTIFIC",)
        ENDPOINT = "test/endpoint.json"
        HEALTH_QUERY = "probe"

        def to_record(self, r, query, raw_sha):
            from discovery_fabric.source_registry.base import SourceRecord, utc_now
            return SourceRecord(
                source_id=self.SOURCE_ID, role="SCIENTIFIC",
                record_id=f"test:{r.get('id')}", title=r.get("title", ""),
                uri="https://example.org", retrieved_at=utc_now(), query=query,
                raw_payload_sha256=raw_sha,
                normalized={"id": r.get("id")}, provenance={"provider": self.SOURCE_ID},
            )

    c = _C()
    if payload is not None:
        c._request = lambda url, timeout=25: (payload, status, http_status, None, None)
    else:
        c._request = lambda url, timeout=25: (None, status, http_status, "injected", None)
    return c


# ---------------------------------------------------------------------------
# registry structure
# ---------------------------------------------------------------------------

class TestRegistryStructure:
    def test_every_source_has_all_13_directive_fields(self):
        for sid, rec in SOURCE_REGISTRY.items():
            for f in REQUIRED_FIELDS:
                assert f in rec, f"{sid} missing {f}"
                assert rec[f] not in (None, ""), f"{sid}.{f} empty"

    def test_all_roles_valid(self):
        for sid, rec in SOURCE_REGISTRY.items():
            for role in rec["authority_role"]:
                assert role in VALID_ROLES, f"{sid} bad role {role}"

    def test_registry_validates_clean(self):
        assert validate_registry() == []

    def test_live_never_assertable_without_connector(self):
        # Negative control (Art. XXI): a README-mentioned source with no
        # connector cannot be marked LIVE by overlay.
        no_conn = [s for s in SOURCE_REGISTRY.values() if not s["connector"]]
        assert no_conn, "expected at least one no-connector source"
        bad = {no_conn[0]["source_id"]: "LIVE"}
        with pytest.raises(ValueError, match="no connector"):
            apply_measured_statuses(bad)

    def test_unmeasured_default_is_not_measured(self):
        overlay = apply_measured_statuses({})
        for rec in overlay.values():
            assert rec["health_status"] == NOT_MEASURED

    def test_unknown_measured_status_rejected(self):
        with pytest.raises(ValueError):
            apply_measured_statuses({"pubmed": "PROBABLY_FINE"})

    def test_unknown_source_id_rejected(self):
        with pytest.raises(KeyError):
            apply_measured_statuses({"nonexistent_source": "LIVE"})

    def test_directive_roles_all_represented_in_matrix(self):
        for role in COVERAGE_MATRIX_ROLES:
            assert role in VALID_ROLES


# ---------------------------------------------------------------------------
# Art. XXI.3 — provider failure is not absence
# ---------------------------------------------------------------------------

class TestFailureSemantics:
    def test_network_failure_is_search_failed_not_empty(self):
        c = _mk_connector(None, status=STATUS_SEARCH_FAILED)
        r = c.search("q")
        assert r.status == STATUS_SEARCH_FAILED
        assert r.ok is False
        assert r.records == []

    def test_timeout_is_timeout_not_empty(self):
        c = _mk_connector(None, status=STATUS_TIMEOUT)
        r = c.search("q")
        assert r.status == STATUS_TIMEOUT
        assert r.ok is False

    def test_rate_limited_is_degraded_signal_not_empty(self):
        c = _mk_connector(None, status=STATUS_RATE_LIMITED, http_status=429)
        r = c.search("q")
        assert r.status == STATUS_RATE_LIMITED
        assert r.ok is False

    def test_5xx_is_unavailable(self):
        c = _mk_connector(None, status=STATUS_UNAVAILABLE, http_status=503)
        r = c.search("q")
        assert r.status == STATUS_UNAVAILABLE
        assert r.ok is False

    def test_success_with_records_is_ok(self):
        payload = json.dumps({"results": [{"id": "1", "title": "t"}]}).encode()
        c = _mk_connector(payload)
        r = c.search("q")
        assert r.status == STATUS_OK
        assert r.ok is True
        assert len(r.records) == 1

    def test_success_with_zero_records_is_empty_and_ok(self):
        payload = json.dumps({"results": []}).encode()
        c = _mk_connector(payload)
        r = c.search("q")
        assert r.status == STATUS_EMPTY
        assert r.ok is True  # provider answered definitively

    def test_unparseable_body_is_parse_failed(self):
        c = _mk_connector(b"<html>not json</html>")
        r = c.search("q")
        assert r.status == STATUS_PARSE_FAILED
        assert r.ok is False

    def test_error_body_does_not_mask_provider_status(self):
        # Regression pin (defect found + fixed this session): a 429 JSON
        # error body must stay RATE_LIMITED, never become PARSE_FAILED.
        body = json.dumps({"error": "Rate limit exceeded"}).encode()
        c = _mk_connector(body, http_status=429, status=STATUS_RATE_LIMITED)
        r = c.search("q")
        assert r.status == STATUS_RATE_LIMITED
        assert r.status != STATUS_PARSE_FAILED

    def test_openfda_404_not_found_is_definitive_empty(self):
        body = json.dumps({"error": {"code": "NOT_FOUND",
                                     "message": "No matches found!"}}).encode()
        c = MaudeConnector()
        c._request = lambda url, timeout=25: (body, STATUS_SEARCH_FAILED, 404,
                                              "HTTP 404", None)
        r = c.search("nonexistent")
        assert r.status == STATUS_EMPTY
        assert r.ok is True

    def test_openfda_404_without_error_object_stays_search_failed(self):
        # fail-safe: a 404 whose body we do NOT recognize must NOT be
        # treated as absence (Art. XXI.3).
        c = MaudeConnector()
        c._request = lambda url, timeout=25: (b"<html>404</html>",
                                              STATUS_SEARCH_FAILED, 404,
                                              "HTTP 404", None)
        r = c.search("q")
        assert r.status == STATUS_SEARCH_FAILED
        assert r.ok is False


# ---------------------------------------------------------------------------
# Art. XXI.5 — MAUDE limitation metadata
# ---------------------------------------------------------------------------

class TestMaudeLimitations:
    def test_every_maude_record_carries_fda_limitations(self):
        payload = json.dumps({
            "results": [{
                "mdr_report_key": "123",
                "report_number": "R123",
                "event_type": "Malfunction",
                "device": [{"brand_name": "TEST PACER"}],
            }]
        }).encode()
        c = MaudeConnector()
        c._request = lambda url, timeout=25: (payload, STATUS_OK, 200, None, None)
        r = c.search("q")
        assert r.status == STATUS_OK
        for rec in r.records:
            for lim in MAUDE_LIMITATIONS:
                assert lim in rec.limitations
        # specifically: the incidence/causality caveats FDA requires
        joined = " ".join(r.records[0].limitations)
        assert "NOT incidence" in joined
        assert "CAUSALITY_UNVERIFIED" in joined

    def test_maude_record_normalization_fields(self):
        payload = json.dumps({
            "results": [{
                "mdr_report_key": "123",
                "event_type": "Malfunction",
                "pma_pmn_number": "K123456",
                "product_problems": ["Battery Problem"],
                "device": [{"brand_name": "TEST PACER", "udi_di": "DI123"}],
                "mdr_text": [{"text": "narrative text"}],
            }]
        }).encode()
        c = MaudeConnector()
        c._request = lambda url, timeout=25: (payload, STATUS_OK, 200, None, None)
        r = c.search("q")
        n = r.records[0].normalized
        assert n["mdr_report_key"] == "123"
        assert n["pma_pmn_number"] == "K123456"
        assert n["product_problems"] == ["Battery Problem"]
        assert n["udi_di"] == "DI123"
        assert "narrative text" in (n["narrative_text"] or "")


# ---------------------------------------------------------------------------
# Art. XXI.9 — provenance custody + retrieval log integrity
# ---------------------------------------------------------------------------

class TestProvenanceCustody:
    def test_records_carry_full_custody_chain(self):
        payload = json.dumps({"results": [{"id": "1", "title": "t"}]}).encode()
        c = _mk_connector(payload)
        r = c.search("q")
        rec = r.records[0]
        assert rec.provenance["provider"] == "test_source"
        assert rec.raw_payload_sha256  # sha of raw payload
        assert rec.retrieved_at
        assert rec.query == "q"

    def test_retrieval_log_written_and_chained(self):
        payload = json.dumps({"results": [{"id": "1", "title": "t"}]}).encode()
        c = _mk_connector(payload)
        c.search("q")
        entries = retrieval_log.read_entries()
        assert len(entries) == 1
        assert entries[0]["source_id"] == "test_source"
        assert entries[0]["raw_payload_sha256"]
        assert retrieval_log.verify_chain()["chain_valid"] is True

    def test_tampered_log_detected(self):
        # ATTACK TEST (Art. XVII): an adversary edits a past entry.
        payload = json.dumps({"results": [{"id": "1", "title": "t"}]}).encode()
        c = _mk_connector(payload)
        c.search("q")
        c.search("q2")
        path = retrieval_log.LOG_PATH
        lines = path.read_text().splitlines()
        entry = json.loads(lines[0])
        entry["status"] = "OK_FORGED"
        lines[0] = json.dumps(entry, sort_keys=True)
        path.write_text("\n".join(lines) + "\n")
        audit = retrieval_log.verify_chain()
        assert audit["chain_valid"] is False

    def test_provider_failure_also_logged(self):
        c = _mk_connector(None, status=STATUS_SEARCH_FAILED)
        c.search("q")
        entries = retrieval_log.read_entries()
        assert len(entries) == 1
        assert entries[0]["status"] == STATUS_SEARCH_FAILED


# ---------------------------------------------------------------------------
# health derivation rules
# ---------------------------------------------------------------------------

class TestHealthDerivation:
    def test_rate_limited_maps_to_degraded(self):
        from discovery_fabric.source_registry import health
        class _Fake:
            SOURCE_ID = "x"; ROLES = ("SCIENTIFIC",)
            def search(self, query, timeout=25):
                from discovery_fabric.source_registry.base import SourceQueryResult
                return SourceQueryResult(source_id="x", status=STATUS_RATE_LIMITED,
                                         ok=False, http_status=429, error="budget")
        # inject fake connector via monkeypatched loader
        orig = health.load_connector
        health.load_connector = lambda sid: (lambda: _Fake())
        try:
            r = health.check_source("pubmed")
            assert r["status"] == "DEGRADED"
            assert r["chain"]["live_request_works"] is True
        finally:
            health.load_connector = orig

    def test_no_connector_maps_to_not_integrated(self):
        from discovery_fabric.source_registry.health import check_source
        r = check_source("who_ictrp")  # registry source without connector
        assert r["status"] == "NOT_INTEGRATED"
        assert not any(r["chain"].values())

    def test_latency_above_triage_bound_is_degraded(self):
        from discovery_fabric.source_registry import health
        from discovery_fabric.source_registry.base import SourceQueryResult
        class _Slow:
            SOURCE_ID = "x"; ROLES = ("SCIENTIFIC",)
            def search(self, query, timeout=25):
                return SourceQueryResult(source_id="x", status=STATUS_OK, ok=True,
                                         http_status=200, latency_ms=99999,
                                         records=[])
        orig = health.load_connector
        health.load_connector = lambda sid: (lambda: _Slow())
        try:
            r = health.check_source("pubmed")
            assert r["status"] == "DEGRADED"
        finally:
            health.load_connector = orig
