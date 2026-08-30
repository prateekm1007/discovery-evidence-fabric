"""Adversarial tests — mechanical source-status honesty (CEO directive #5).

Covers discovery_fabric/source_registry/status_model.py + the health.py
emission path + registry overlay vocabulary.

Attack classes (Art. XVII — how would an adversary defeat this?):
- signature misclassification: retired-endpoint errors masquerading as AUTH
  (they often also carry 401/403) — PROVIDER_RETIRED must win
- vocabulary smuggling: any status outside the 4-word vocabulary must be
  rejected by the registry overlay
- hand-assignment drift: classify_block is a PURE function — same measured
  signature always yields the same block class
- legacy rewriting: old artifacts saying UNAVAILABLE must be INTERPRETED,
  never silently mutated (Art. XI)
- evidence traceability: every BLOCKED verdict carries the fired rule +
  measured inputs
"""

from __future__ import annotations

import pytest

from discovery_fabric.source_registry import status_model as sm
from discovery_fabric.source_registry.status_model import classify_block


class TestClassifyBlock:
    def test_auth_missing_key(self):
        out = classify_block(
            request_status="AUTH_FAILED",
            error="AUTH_FAILED: PATSNAP_EUREKA_API_KEY not configured")
        assert out["block_class"] == "AUTH"
        assert out["status"] == "BLOCKED"

    def test_egress_ip_block(self):
        out = classify_block(
            request_status="AUTH_FAILED",
            error=('HTTP 403: {"error": "Your IP address or ASN has been '
                   '(temporarily) blocked from accessing all MP endpoints"}'))
        # PROVIDER_RETIRED checked first, EGRESS second: an IP/ASN block is
        # not a retirement and not a credential problem -> EGRESS
        assert out["block_class"] == "EGRESS"

    def test_provider_retired_wins_over_auth(self):
        # the real uspto_odp case: retirement text alongside AUTH_FAILURE
        out = classify_block(
            request_status="AUTH_FAILED",
            error=("SOURCE_UNAVAILABLE/AUTH_FAILURE: PatentsView legacy "
                   "endpoint retired 2026-08-30 (HTML page measured)"))
        assert out["block_class"] == "PROVIDER_RETIRED"

    def test_registration_wall(self):
        out = classify_block(
            request_status="SEARCH_FAILED",
            error="bot-protection: registration required to query the API")
        assert out["block_class"] == "REGISTRATION"

    def test_http_5xx(self):
        out = classify_block(request_status="UNAVAILABLE",
                             error="HTTP 503 service unavailable",
                             http_status=503)
        assert out["block_class"] == "HTTP_5XX"

    def test_bot_503_is_egress_not_5xx(self):
        # google_patents: 503 with bot-block signature -> EGRESS (provider
        # blocking us), not generic HTTP_5XX
        out = classify_block(request_status="UNAVAILABLE",
                             error="HTTP 503 bot check (captcha)",
                             http_status=503)
        assert out["block_class"] == "EGRESS"

    def test_network_timeout(self):
        out = classify_block(request_status="TIMEOUT", error="timeout after 30s")
        assert out["block_class"] == "NETWORK"

    def test_metered_window(self):
        out = classify_block(metered_window=True)
        assert out["block_class"] == "METERED_WINDOW"

    def test_connector_import(self):
        out = classify_block(request_status="CONNECTOR_IMPORT",
                             error="connector import failed: ImportError: x")
        assert out["block_class"] == "CONNECTOR_IMPORT"

    def test_bare_403_defaults_egress(self):
        out = classify_block(request_status="UNAVAILABLE", error="",
                             http_status=403)
        assert out["block_class"] == "EGRESS"

    def test_pure_function_determinism(self):
        args = dict(request_status="AUTH_FAILED",
                    error="HTTP 401 unauthorized: API key invalid",
                    http_status=401)
        a = classify_block(**args)
        b = classify_block(**args)
        assert a == b  # no state, no registry lookups, no drift

    def test_every_block_class_in_vocabulary(self):
        for bc in sm.BLOCK_CLASSES:
            assert bc in sm.BLOCK_CLASS_DERIVATION  # derivation documented


class TestVocabulary:
    def test_four_word_vocabulary(self):
        assert sm.STATUS_VOCABULARY == ("LIVE", "DEGRADED", "BLOCKED",
                                        "NOT_INTEGRATED")

    def test_registry_overlay_accepts_new_and_legacy_rejects_garbage(self):
        from discovery_fabric.source_registry.registry import (
            MEASURED_STATUSES, apply_measured_statuses,
        )
        assert "BLOCKED" in MEASURED_STATUSES
        assert "UNAVAILABLE" in MEASURED_STATUSES  # legacy loadable (Art. XI)
        with pytest.raises(ValueError, match="not in"):
            apply_measured_statuses({"fda_maude": "PROBABLY_FINE"})

    def test_legacy_map_interprets_not_rewrites(self):
        assert sm.map_legacy_status("UNAVAILABLE") == "BLOCKED"
        assert sm.map_legacy_status("LIVE") == "LIVE"
        assert "UNAVAILABLE -> BLOCKED" in sm.LEGACY_VOCABULARY_MAP["legacy_note"]

    def test_health_derivation_has_blocked_entry(self):
        from discovery_fabric.source_registry.health import DERIVATION
        assert "BLOCKED" in DERIVATION
        assert "UNAVAILABLE" not in DERIVATION  # never emitted again


class TestHealthEmission:
    def test_blocked_source_carries_block_class(self, monkeypatch, tmp_path):
        """Wire a fake connector whose search fails with an IP-block 403 and
        verify check_source emits BLOCKED + EGRESS mechanically."""
        from discovery_fabric.source_registry import health
        from discovery_fabric.source_registry import retrieval_log as rl
        monkeypatch.setattr(rl, "LOG_PATH", tmp_path / "rl.jsonl")

        class _Res:
            status, http_status, latency_ms = "AUTH_FAILED", 403, 120
            error = ('HTTP 403: "Your IP address or ASN has been blocked '
                     'from accessing endpoints"')
            records = []

        class _Conn:
            HEALTH_QUERY = "probe"

            def search(self, q, timeout=30):
                return _Res()

        monkeypatch.setattr(health, "load_connector", lambda sid: _Conn)
        monkeypatch.setattr(
            health, "SOURCE_REGISTRY",
            {"fake_source": {"source_id": "fake_source",
                             "connector": "x.y.Z",
                             "authority_role": ["SCIENTIFIC"]}})
        out = health.check_source("fake_source")
        assert out["status"] == "BLOCKED"
        assert out["block"]["block_class"] == "EGRESS"
        assert out["block"]["block_evidence"]["fired_rule"]

    def test_live_source_has_no_block_field(self, monkeypatch, tmp_path):
        from discovery_fabric.source_registry import health
        from discovery_fabric.source_registry import retrieval_log as rl
        monkeypatch.setattr(rl, "LOG_PATH", tmp_path / "rl.jsonl")

        class _Rec:
            record_id, title, uri = "r1", "t", ""
            raw_payload_sha256, retrieved_at = "x" * 64, "2026-01-01T00:00:00Z"
            provenance = {"provider": "fake"}

        class _Res:
            status, http_status, latency_ms = "OK", 200, 100
            error, records = None, [_Rec()]

        class _Conn:
            HEALTH_QUERY = "probe"

            def search(self, q, timeout=30):
                return _Res()

        monkeypatch.setattr(health, "load_connector", lambda sid: _Conn)
        monkeypatch.setattr(
            health, "SOURCE_REGISTRY",
            {"fake_source": {"source_id": "fake_source",
                             "connector": "x.y.Z",
                             "authority_role": ["SCIENTIFIC"]}})
        out = health.check_source("fake_source")
        assert out["status"] == "LIVE"
        assert "block" not in out
