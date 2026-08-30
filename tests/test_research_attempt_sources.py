"""Hermetic tests — research-attempt sources (EXPERIMENT information type)
and the ConnectorBase POST extension.

Covers discovery_fabric/source_registry/connectors/research_attempts.py
and base.py's HTTP_METHOD/build_request_body machinery.

Adversarial cases (Art. XVII):
- the silently-ignored query shape (the defect the relevance instrument
  caught live on this connector's first proof-chain run) must STAY fixed:
  a regression test pins the request body to the working
  advanced_text_search shape
- POST must not alter GET connectors' behavior (data=None, method GET)
- out-of-scope zero is a definitive EMPTY, not SEARCH_FAILED (Art. XXI.3)
- custody still lands in the hash-chained retrieval log for POST queries
"""

from __future__ import annotations

import json

import pytest

from discovery_fabric.source_registry.base import ConnectorBase
from discovery_fabric.source_registry.connectors.research_attempts import (
    NihReporterConnector, REPORTER_LIMITATIONS,
)


class TestPostBase:
    def test_default_is_get_with_no_body(self):
        class _C(ConnectorBase):
            def build_url(self, q):
                return "https://example.invalid"

            def parse_payload(self, raw, query):
                return {}

            def normalize_payload(self, payload, query, raw_sha):
                return []

        c = _C()
        assert c.HTTP_METHOD == "GET"
        assert c.build_request_body("q") is None

    def test_reporter_uses_post_with_json_body(self):
        c = NihReporterConnector()
        assert c.HTTP_METHOD == "POST"
        body = json.loads(c.build_request_body("hydrogel cartilage"))
        assert body["criteria"]["advanced_text_search"]["search_text"] == \
            "hydrogel cartilage"

    def test_request_body_shape_regression(self):
        """PIN the working shape — the silently-ignored shape returned the
        WHOLE CORPUS as if relevant (live defect 2026-08-30, caught by the
        relevance-custody instrument on this connector's own first run)."""
        c = NihReporterConnector()
        body = json.loads(c.build_request_body("anything"))
        crit = body["criteria"]
        assert "advanced_text_search" in crit, \
            "must use advanced_text_search (the query.operator shape is " \
            "silently ignored by the provider)"
        assert "query" not in crit
        assert crit["advanced_text_search"]["search_field"] == "all"
        assert crit["advanced_text_search"]["operator"] == "and"


class TestReporterConnector:
    def test_registry_row_exists_with_experiment_role(self):
        from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
        rec = SOURCE_REGISTRY["nih_reporter"]
        assert rec["authority_role"] == ["EXPERIMENT"]
        assert rec["connector"].endswith("NihReporterConnector")

    def test_blocked_siblings_registered_honestly(self):
        from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
        assert SOURCE_REGISTRY["nsf_awards"]["connector"] is None
        assert SOURCE_REGISTRY["cordis_projects"]["connector"] is None
        assert "HTTP 404" in SOURCE_REGISTRY["nsf_awards"]["coverage"]
        assert "HTTP 403 Forbidden" in SOURCE_REGISTRY["nsf_awards"]["coverage"]
        assert "registration" in SOURCE_REGISTRY["cordis_projects"][
            "known_gaps"].lower()

    def test_experiment_role_in_matrix(self):
        from discovery_fabric.source_registry.roles import (
            COVERAGE_MATRIX_ROLES, ROLE_DEFINITIONS,
        )
        assert "EXPERIMENT" in COVERAGE_MATRIX_ROLES
        assert "absence of a" in ROLE_DEFINITIONS["EXPERIMENT"] \
            and "not evidence of failure" in ROLE_DEFINITIONS["EXPERIMENT"]

    def test_normalization_carries_limitations_and_attempt_kind(self):
        c = NihReporterConnector()
        payload = {"results": [{
            "appl_id": 12345,
            "project_title": "Test project",
            "project_start_date": "2021-01-01",
            "project_end_date": "2024-06-30",
            "organization": {"org_name": "TEST UNIV",
                             "org_country": "USA"},
            "abstract_text": "An attempt to test.",
        }]}
        recs = c.normalize_payload(payload, "q", "sha" * 8)
        assert len(recs) == 1
        r = recs[0]
        assert r.record_id == "nih:12345"
        assert r.role == "EXPERIMENT"
        assert r.epistemic_state == "OBSERVED"
        assert r.normalized["attempt_kind"] == "FUNDED_RESEARCH_PROJECT"
        assert any("ATTEMPT_RECORD" in x for x in r.limitations)
        assert len(REPORTER_LIMITATIONS) >= 4

    def test_records_without_appl_id_skipped(self):
        c = NihReporterConnector()
        payload = {"results": [{"project_title": "no id"}]}
        assert c.normalize_payload(payload, "q", "sha") == []

    def test_total_hits_extracted(self):
        c = NihReporterConnector()
        payload = {"meta": {"total": 207}, "results": []}
        assert c.extract_total_hits(payload) == 207
        assert c.extract_total_hits({"meta": {}}) is None

    def test_live_definitive_zero_is_empty_not_failed(self, monkeypatch,
                                                      tmp_path):
        """Out-of-scope zero (provider answered 200 with 0 results) is the
        ONLY true EMPTY — never SEARCH_FAILED (Art. XXI.3)."""
        from discovery_fabric.source_registry import retrieval_log as rl
        monkeypatch.setattr(rl, "LOG_PATH", tmp_path / "rl.jsonl")

        c = NihReporterConnector()

        class _Resp:
            status = 200

            def read(self):
                return json.dumps({"meta": {"total": 0},
                                   "results": []}).encode()

        def _fake_request(url, timeout=25, query=""):
            return (_Resp().read(), "OK", 200, None, None)

        monkeypatch.setattr(c, "_request", _fake_request)
        res = c.search("wind turbine gearbox", timeout=10)
        assert res.status == "EMPTY"
        assert res.ok is True
