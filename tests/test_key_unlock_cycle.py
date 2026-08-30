"""Key-unlock cycle tests — Lens patent/scholarly split, PatentBear metering,
Elsevier Scopus. Hermetic: NO network, NO ambient credentials (Art. XVII).

Covers (positive + negative + adversarial, Art. V/VIII):
- Registry: the three new sources carry all 13 directive fields; the two
  Lens resources are SEPARATE entries (CEO Section 4 — never merged);
  PatentBear carries provider-metering wiring.
- Lens string-query pin (Art. XXXI regression): the request body MUST use
  the 'title:(...)' string form. The DSL form is silently ignored by
  api.lens.org and returns newest records REGARDLESS of relevance — an
  astrophysics paper answered a CSF-shunt query (measured 2026-08-29).
  This is the most dangerous class of defect: status OK + garbage records.
- Lens patent parsing: list-form invention_title, parties.applicants.
- PatentBear quota guard: provider-reported remaining==0 -> RATE_LIMITED
  WITHOUT spending a request (attack: does anything still hit the wire?).
- Metered health policy: no proof -> UNAVAILABLE (never silently LIVE);
  fresh proof -> LIVE with disclosed timestamp; quota 0 -> DEGRADED;
  the health check NEVER live-probes a metered source.
- Scopus: parse/normalize/total-hits; malformed entries skipped, not
  fabricated; absent key -> AUTH_FAILED without network.
- KG: bibliographic patent -> PATENT_FAMILY only; verbatim claims ->
  PATENT_CLAIM entities + PATENT_CLAIM_BELONGS_TO edges (evidence-bound).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import retrieval_log
from discovery_fabric.source_registry.base import (
    SourceQueryResult, SourceRecord, STATUS_OK, utc_now,
)
from discovery_fabric.source_registry.registry import (
    SOURCE_REGISTRY, REQUIRED_FIELDS, validate_registry,
)


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    """Never write test custody entries into the real log (Art. IX)."""
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "retrieval_log.jsonl")
    yield


# ---------------------------------------------------------------------------
# registry structure
# ---------------------------------------------------------------------------

class TestNewSourcesRegistered:
    @pytest.mark.parametrize("sid", ["lens_patent", "lens_scholarly",
                                     "patentbear", "elsevier_scopus"])
    def test_thirteen_directive_fields_present(self, sid):
        rec = SOURCE_REGISTRY[sid]
        for f in REQUIRED_FIELDS:
            assert rec.get(f) not in (None, ""), f"{sid}.{f} missing/empty"

    def test_lens_resources_are_separate_sources(self):
        # CEO Section 4: LENS_PATENT != LENS_SCHOLARLY, never merged.
        sch = SOURCE_REGISTRY["lens_scholarly"]
        pat = SOURCE_REGISTRY["lens_patent"]
        assert sch["authority_role"] == ["SCIENTIFIC"]
        assert pat["authority_role"] == ["PATENT"]
        assert "PATENT" not in sch["authority_role"]
        assert "SCIENTIFIC" not in pat["authority_role"]

    def test_patentbear_is_metered_with_policy(self):
        mq = SOURCE_REGISTRY["patentbear"]["metered_quota"]
        assert mq is not None
        assert mq["monthly_limit"] == 20
        assert mq["health_policy"].startswith("no-live-probe")
        assert any("run_lab" in t for t in mq["prohibited_tools"])

    def test_registry_still_validates_clean(self):
        assert validate_registry() == []

    def test_scopus_role_scientific(self):
        assert SOURCE_REGISTRY["elsevier_scopus"]["authority_role"] == ["SCIENTIFIC"]


# ---------------------------------------------------------------------------
# Lens adapters: the string-query pin (Art. XXXI regression)
# ---------------------------------------------------------------------------

class TestLensStringQueryPin:
    def test_query_builder_returns_string_form(self):
        from discovery_fabric.prior_art_v2.sources import _lens_string_query
        assert _lens_string_query("hydrocephalus shunt valve") == \
            "title:(hydrocephalus shunt valve)"

    def _capture_body(self, monkeypatch, response_body: bytes, status=200):
        """Run search_lens_patent with an intercepted HTTP layer."""
        import discovery_fabric.prior_art_v2.sources as src
        captured = {}

        def _fake_post(url, payload, headers=None, timeout=25):
            captured["url"] = url
            captured["payload"] = json.loads(payload.decode())
            captured["headers"] = headers or {}
            return status, response_body, 5

        monkeypatch.setattr(src, "_http_post", _fake_post)
        monkeypatch.setattr(src, "LENS_TOKEN", "test-token", raising=False)
        return captured

    def test_patent_adapter_never_sends_dsl_form(self, monkeypatch):
        # NEGATIVE CONTROL for the measured silent-relevance defect: the
        # DSL body is silently ignored by Lens (756k irrelevant results).
        import discovery_fabric.prior_art_v2.sources as src
        ok_body = json.dumps({"total": 1, "data": []}).encode()
        cap = self._capture_body(monkeypatch, ok_body)
        src.search_lens_patent("hydrocephalus shunt valve", num_results=3)
        q = cap["payload"]["query"]
        assert isinstance(q, str), "query must be the STRING form, not DSL"
        assert q.startswith("title:(")
        assert "bool" not in cap["payload"]["query"]
        assert "include" not in cap["payload"], \
            "patent endpoint rejects include (measured 400 Unrecognized fields)"

    def test_scholarly_adapter_never_sends_dsl_form(self, monkeypatch):
        import discovery_fabric.prior_art_v2.sources as src
        ok_body = json.dumps({"total": 1, "data": []}).encode()
        cap = self._capture_body(monkeypatch, ok_body)
        src.search_lens_scholarly("cerebrospinal fluid shunt", num_results=3)
        q = cap["payload"]["query"]
        assert isinstance(q, str) and q.startswith("title:(")

    def test_patent_parses_list_form_title_and_parties(self, monkeypatch):
        import discovery_fabric.prior_art_v2.sources as src
        body = json.dumps({
            "total": 1,
            "data": [{
                "lens_id": "119-287-251-825-617",
                "doc_key": "US_9033909_B2_20150519",
                "date_published": "2015-05-19",
                "jurisdiction": "US", "kind": "B2",
                "abstract": "A shunt valve for treatment of hydrocephalus.",
                "biblio": {
                    "invention_title": [{"text": "SHUNT VALVE FOR TREATMENT "
                                                 "OF HYDROCEPHALUS", "lang": "en"}],
                    "parties": {"applicants": [
                        {"extracted_name": {"value": "AIHARA YASUO"}},
                    ]},
                },
            }],
        }).encode()
        self._capture_body(monkeypatch, body)
        r = src.search_lens_patent("hydrocephalus shunt valve", num_results=3)
        assert r.success and len(r.hits) == 1
        h = r.hits[0]
        assert h.title == "SHUNT VALVE FOR TREATMENT OF HYDROCEPHALUS"
        assert h.assignee_or_authors == ["AIHARA YASUO"]
        assert h.patent_id == "US_9033909_B2_20150519"
        assert h.raw_payload_sha256

    def test_patent_auth_failure_is_not_empty(self, monkeypatch):
        import discovery_fabric.prior_art_v2.sources as src
        body = json.dumps({"message": "Unable to authorize", "code": 401}).encode()
        self._capture_body(monkeypatch, body, status=401)
        r = src.search_lens_patent("q")
        assert r.success is False
        assert "401" in (r.error or "")


# ---------------------------------------------------------------------------
# PatentBear quota guard
# ---------------------------------------------------------------------------

class TestPatentBearQuotaGuard:
    def _guard_connector(self, monkeypatch, remaining):
        from discovery_fabric.source_registry.connectors.patents import (
            PatentBearConnector,
        )
        entries = [{
            "source_id": "patentbear", "status": "OK",
            "rate_limit_remaining": str(remaining),
            "timestamp": utc_now(),
        }] if remaining is not None else []
        monkeypatch.setattr(
            "discovery_fabric.source_registry.retrieval_log.read_entries",
            lambda source_id=None: entries,
        )
        return PatentBearConnector()

    def test_exhausted_quota_blocks_without_network(self, monkeypatch):
        # ATTACK TEST (Art. XVII): with provider-reported remaining=0,
        # NOTHING may hit the wire (quota is money on this source).
        import discovery_fabric.prior_art_v2.sources as src

        def _boom(*a, **k):  # noqa: ANN001
            raise AssertionError("network call attempted with exhausted quota")

        monkeypatch.setattr(src, "search_patent_bear", _boom)
        c = self._guard_connector(monkeypatch, remaining=0)
        r = c.search("hydrocephalus shunt valve")
        assert r.status == "RATE_LIMITED"
        assert r.ok is False
        assert "quota exhausted" in r.error
        assert "not an absence" in r.error  # Art. XXI.3 wording pinned

    def test_positive_quota_proceeds(self, monkeypatch):
        import discovery_fabric.prior_art_v2.sources as src
        from discovery_fabric.prior_art_v2.sources import SourceQueryResult as PaR

        def _fake_pb(query, num_results=8):
            return PaR(source_id="PATENT_BEAR", success=True, latency_ms=10,
                       hits=[], rate_limit_remaining=4)

        monkeypatch.setattr(src, "search_patent_bear", _fake_pb)
        c = self._guard_connector(monkeypatch, remaining=4)
        r = c.search("hydrocephalus shunt valve")
        assert r.status == "EMPTY" and r.ok is True
        assert r.rate_limit_remaining == "4"

    def test_no_quota_state_yet_proceeds(self, monkeypatch):
        import discovery_fabric.prior_art_v2.sources as src
        from discovery_fabric.prior_art_v2.sources import SourceQueryResult as PaR
        monkeypatch.setattr(
            src, "search_patent_bear",
            lambda q, num_results=8: PaR(source_id="PATENT_BEAR",
                                         success=True, latency_ms=10, hits=[]),
        )
        c = self._guard_connector(monkeypatch, remaining=None)
        r = c.search("q")
        assert r.ok is True  # first-ever call: no reported quota yet


# ---------------------------------------------------------------------------
# metered health policy
# ---------------------------------------------------------------------------

class TestMeteredHealthPolicy:
    def _entries(self, *entries):
        return list(entries)

    def test_no_proof_is_unavailable_never_live(self, monkeypatch):
        from discovery_fabric.source_registry import health
        monkeypatch.setattr(
            "discovery_fabric.source_registry.retrieval_log.read_entries",
            lambda source_id=None: [],
        )
        r = health.check_source("patentbear")
        # 2026-08-30 vocabulary rename (CEO #5): UNAVAILABLE -> BLOCKED with
        # machine-derived block_class; the test's INTENT is unchanged —
        # no live proof is NEVER silently LIVE
        assert r["status"] == "BLOCKED"
        assert r["block"]["block_class"] == "METERED_WINDOW"
        assert "no live retrieval-log proof" in r["error"]
        assert r["request_status"] == "NOT_PROBED"

    def test_metered_source_is_never_live_probed(self, monkeypatch):
        # ATTACK TEST: the health check must not even LOAD the connector
        # (a live probe would burn provider quota).
        from discovery_fabric.source_registry import health

        def _boom(sid):
            raise AssertionError("metered health check attempted connector load")

        monkeypatch.setattr(health, "load_connector", _boom)
        monkeypatch.setattr(
            "discovery_fabric.source_registry.retrieval_log.read_entries",
            lambda source_id=None: [],
        )
        health.check_source("patentbear")  # must return, not raise

    def test_fresh_proof_derives_live_with_disclosure(self, monkeypatch):
        from discovery_fabric.source_registry import health
        entries = [{
            "source_id": "patentbear", "status": "OK",
            "query": "hydrocephalus shunt valve", "record_count": 5,
            "raw_payload_sha256": "ab" * 32,
            "rate_limit_remaining": "16",
            "timestamp": utc_now(),
        }]
        monkeypatch.setattr(
            "discovery_fabric.source_registry.retrieval_log.read_entries",
            lambda source_id=None: entries,
        )
        r = health.check_source("patentbear")
        assert r["status"] == "LIVE"
        assert r["chain"]["proof_kind"] == "last_live_measurement"
        assert r["last_live_proof"]["raw_payload_sha256"] == "ab" * 32
        assert r["metered"]["provider_reported_remaining"] == 16

    def test_exhausted_quota_derives_degraded(self, monkeypatch):
        from discovery_fabric.source_registry import health
        entries = [{
            "source_id": "patentbear", "status": "OK",
            "query": "q", "record_count": 1,
            "raw_payload_sha256": "ab" * 32,
            "rate_limit_remaining": "0",
            "timestamp": utc_now(),
        }]
        monkeypatch.setattr(
            "discovery_fabric.source_registry.retrieval_log.read_entries",
            lambda source_id=None: entries,
        )
        r = health.check_source("patentbear")
        assert r["status"] == "DEGRADED"
        assert "quota exhausted" in r["error"]


# ---------------------------------------------------------------------------
# Scopus connector
# ---------------------------------------------------------------------------

_SCOPUS_BODY = json.dumps({
    "search-results": {
        "opensearch:totalResults": "32517",
        "opensearch:itemsPerPage": "5",
        "entry": [
            {
                "dc:identifier": "SCOPUS_ID:105035324256",
                "dc:title": "Effectiveness of neuronavigation-assisted shunts",
                "dc:creator": "Doe J.",
                "prism:publicationName": "Journal of Neurosurgery",
                "prism:doi": "10.1234/x.5678",
                "prism:coverDate": "2024-05-01",
                "citedby-count": "12",
            },
            {"service-error": {"status": {"statusCode": "ERROR"}}},  # malformed
            {"dc:title": "no identifier record"},  # malformed: no id
        ],
    },
}).encode()


class TestScopusConnector:
    def _conn(self, monkeypatch, body=_SCOPUS_BODY, status=200):
        from discovery_fabric.source_registry.connectors.scientific import (
            ElsevierScopusConnector,
        )
        from discovery_fabric.source_registry.base import STATUS_AUTH_FAILED
        if status == 200:
            canned = (body, STATUS_OK, 200, None, None)
        else:
            canned = (body, STATUS_AUTH_FAILED, status,
                      f"HTTP {status}: auth error", None)
        c = ElsevierScopusConnector()
        c._request = lambda url, timeout=25: canned
        monkeypatch.setattr(
            "discovery_fabric.source_registry.keys.load_key",
            lambda name: "fake-key" if name == "ELSEVIER_API_KEY" else "",
        )
        return c

    def test_parse_and_normalize(self, monkeypatch):
        c = self._conn(monkeypatch)
        r = c.search("hydrocephalus shunt")
        assert r.status == "OK"
        assert len(r.records) == 1  # malformed entries skipped, not fabricated
        rec = r.records[0]
        assert rec.record_id == "scopus:105035324256"
        assert rec.normalized["doi"] == "10.1234/x.5678"
        assert rec.normalized["citedby_count"] == "12"
        assert rec.provenance["raw_payload_sha256"]

    def test_total_hits_extracted_from_provider(self, monkeypatch):
        c = self._conn(monkeypatch)
        r = c.search("hydrocephalus shunt")
        assert r.total_hits == 32517  # provider-reported population disclosed

    def test_error_body_is_parse_failed_not_results(self, monkeypatch):
        err = json.dumps({"service-error": {"status": {
            "statusCode": "AUTHENTICATION_ERROR",
            "statusText": "Invalid API Key",
        }}}).encode()
        c = self._conn(monkeypatch, body=err, status=401)
        r = c.search("q")
        assert r.status == "AUTH_FAILED"  # 401 maps to AUTH_FAILED, not EMPTY

    def test_absent_key_is_auth_failed_without_network(self, monkeypatch):
        from discovery_fabric.source_registry.connectors.scientific import (
            ElsevierScopusConnector,
        )
        monkeypatch.setattr(
            "discovery_fabric.source_registry.keys.load_key", lambda name: "",
        )
        c = ElsevierScopusConnector()
        c._request = lambda url, timeout=25: (_ for _ in ()).throw(
            AssertionError("network attempted without key"))
        r = c.search("q")
        assert r.status == "AUTH_FAILED"
        assert "not provisioned" in r.error

    def test_zero_entries_is_definitive_empty(self, monkeypatch):
        body = json.dumps({"search-results": {
            "opensearch:totalResults": "0", "entry": [],
        }}).encode()
        c = self._conn(monkeypatch, body=body)
        r = c.search("zzz-no-match-xyzzy")
        assert r.status == "EMPTY" and r.ok is True  # provider answered: zero


# ---------------------------------------------------------------------------
# knowledge graph: patent claim entities
# ---------------------------------------------------------------------------

class TestPatentClaimLifting:
    def _record(self, claims=None, source_id="lens_patent"):
        return SourceRecord(
            source_id=source_id, role="PATENT",
            record_id=f"patent:US9033909B2", title="Shunt valve",
            uri="https://x", retrieved_at=utc_now(), query="q",
            raw_payload_sha256="ab" * 32,
            normalized={"patent_id": "US9033909B2", "claims": claims},
            provenance={"provider": source_id},
        )

    def test_bibliographic_only_creates_family_only(self):
        from discovery_fabric.knowledge_graph.graph import KnowledgeGraph
        from discovery_fabric.knowledge_graph.lifters import lift_query_result
        g = KnowledgeGraph()
        qr = SourceQueryResult(source_id="lens_patent", status="OK",
                               ok=True, records=[self._record()])
        out = lift_query_result(g, qr)
        assert out["lifted"] == 1
        assert len(g.entities("PATENT_FAMILY")) == 1
        assert len(g.entities("PATENT_CLAIM")) == 0
        assert len(g.edges()) == 0

    def test_verbatim_claims_create_claim_entities_and_edges(self):
        from discovery_fabric.knowledge_graph.graph import KnowledgeGraph
        from discovery_fabric.knowledge_graph.lifters import lift_query_result
        g = KnowledgeGraph()
        rec = self._record(
            claims=[{"number": 1, "text": "A shunt valve for treatment of hydrocephalus."},
                    {"number": 2, "text": "The valve of claim 1 wherein..."},
                    {"number": 3, "text": ""}],  # empty claim text: skipped
            source_id="patentbear",
        )
        qr = SourceQueryResult(source_id="patentbear", status="OK",
                               ok=True, records=[rec])
        lift_query_result(g, qr)
        assert len(g.entities("PATENT_FAMILY")) == 1
        claims = g.entities("PATENT_CLAIM")
        assert len(claims) == 2  # the empty-text claim produced nothing
        texts = {c.attributes["claim_text"] for c in claims}
        assert any("hydrocephalus" in t for t in texts)
        assert len(g.edges("PATENT_CLAIM_BELONGS_TO")) == 2
        # every edge is evidence-bound (custody on the edge itself)
        for e in g.edges():
            assert e.provenance[0]["raw_payload_sha256"] == "ab" * 32
        assert len(g.rejected()) == 0
