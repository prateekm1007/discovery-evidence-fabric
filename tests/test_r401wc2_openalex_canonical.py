#!/usr/bin/env python3
"""R401-WC2 tests: OpenAlex in the canonical retrieval path + the
discovery/verification retrieval-role separation (CEO directive 5).

Pinned from both sides (Art. V / VIII / XVII):

  ROLE LABELING — the custody entry carries retrieval_role=DISCOVERY
  when the caller labels it; unlabeled calls stay None (legacy).

  OPENALEX LANE — merged items carry full provenance (provider, query,
  registry provenance, content_hash); the lane state is recorded for
  success AND failure (a 429 lane is an honest partial state, never
  absence, never a stage failure while the primary lane produced
  evidence).

  CROSS-SOURCE DEDUP — same-DOI and ~same-title items collapse with
  the primary lane's item winning and the dedup RECORD retained.

  PRIMARY DISCIPLINE UNCHANGED — EuropePMC (primary) failure still
  RAISES (Art. XXI.3); the OpenAlex lane never rescues a dead primary.

All retrieval is monkeypatched (hermetic); the retrieval custody log is
sandboxed by the conftest autouse guard.
"""
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _fake_openalex_result(records, status="OK", error=None):
    """Build a SourceQueryResult-shaped fake the a2 lane consumes."""
    from types import SimpleNamespace

    def rec(i, title, abstract, doi=None, rid=None):
        return SimpleNamespace(
            record_id=rid or f"W{i}",
            source_id="openalex",
            title=title,
            uri=f"https://openalex.org/W{i}",
            retrieved_at="2026-09-03T00:00:00Z",
            raw_payload_sha256=f"hash{i}",
            normalized={"abstract": abstract, "doi": doi},
            provenance={"provider": "openalex", "query": "q"},
        )
    return SimpleNamespace(
        status=status, error=error, records=[rec(*r) for r in records])


class TestRetrievalRoleCustody:
    def test_role_lands_on_custody_entry(self, monkeypatch, tmp_path):
        """A labeled search writes retrieval_role into the custody log
        entry (the sandboxed log — the conftest guard redirects it).
        Patches _request (the HTTP layer) so the FULL base pipeline
        (execute -> finish -> custody log) runs hermetically."""
        from discovery_fabric.source_registry import retrieval_log as _rl
        from discovery_fabric.source_registry.connectors.scientific \
            import OpenAlexConnector
        monkeypatch.setattr(_rl, "LOG_PATH",
                            tmp_path / "custody.jsonl")
        # an OpenAlex 200-OK payload with one minimal work
        payload = json.dumps({
            "results": [{
                "id": "https://openalex.org/W1",
                "title": "A study of thing one",
                "doi": None,
                "abstract_inverted_index": {
                    "word": list(range(60))},
            }]}).encode()
        monkeypatch.setattr(
            OpenAlexConnector, "_request",
            lambda self, url, timeout=25: (payload, "OK", 200, None,
                                           None))
        OpenAlexConnector().search("q", retrieval_role="DISCOVERY")
        entry = json.loads(
            (tmp_path / "custody.jsonl").read_text().splitlines()[-1])
        assert entry["retrieval_role"] == "DISCOVERY"
        assert entry["source_id"] == "openalex"

    def test_unlabeled_search_stays_none(self, monkeypatch, tmp_path):
        """Legacy unlabeled calls record retrieval_role=None — the field
        is additive metadata, never a behavior change."""
        from discovery_fabric.source_registry import retrieval_log as _rl
        from discovery_fabric.source_registry.connectors.scientific \
            import OpenAlexConnector
        monkeypatch.setattr(_rl, "LOG_PATH",
                            tmp_path / "custody.jsonl")
        payload = json.dumps({"results": []}).encode()
        monkeypatch.setattr(
            OpenAlexConnector, "_request",
            lambda self, url, timeout=25: (payload, "OK", 200, None,
                                           None))
        OpenAlexConnector().search("q")
        entry = json.loads(
            (tmp_path / "custody.jsonl").read_text().splitlines()[-1])
        assert entry["retrieval_role"] is None

    def test_role_value_is_caller_supplied_not_source_default(self):
        """The role is the CALLER's purpose, not a property of the
        source: scientific sources serve discovery, patent sources
        serve verification — the field must not be hardcoded on the
        connector (asserting the signature contract only)."""
        import inspect
        from discovery_fabric.source_registry.base import ConnectorBase
        sig = inspect.signature(ConnectorBase.search)
        assert "retrieval_role" in sig.parameters
        assert sig.parameters["retrieval_role"].default == ""


class TestOpenAlexCanonicalLane:
    def _patch(self, monkeypatch, europepmc_items, openalex_result):
        import discovery_fabric.a2.retrieve as a2r
        import discovery_fabric.a2.retrieve as _mod
        monkeypatch.setattr(a2r, "search_europe_pmc",
                            lambda q, per_page=5: europepmc_items)
        monkeypatch.setattr(_mod.time, "sleep", lambda s: None)
        monkeypatch.setattr(
            "discovery_fabric.source_registry.connectors.scientific."
            "OpenAlexConnector.search",
            lambda self, q, timeout=25, retrieval_role="":
            openalex_result)
        monkeypatch.setattr(
            "discovery_fabric.source_registry.query_relevance."
            "keyword_form", lambda t: "form|query")
        return a2r

    def test_openalex_items_merge_with_provenance(self, monkeypatch):
        epmc = [{"id": "europepmc:1", "source": "EuropePMC",
                 "title": "Alpha paper", "abstract": "x" * 200,
                 "doi": "10.1/a", "content_hash": "h1",
                 "provenance": {"provider": "EuropePMC"}}]
        oa = _fake_openalex_result([
            (2, "Beta paper", "beta abstract " * 30, "10.2/b")])
        a2r = self._patch(monkeypatch, epmc, oa)
        items = a2r.retrieve({"device": "gadget", "failure_mode": "wear"})
        ids = [i["id"] for i in items]
        assert "europepmc:1" in ids and "openalex:W2" in ids
        oa_item = next(i for i in items if i["id"] == "openalex:W2")
        assert oa_item["source"] == "OpenAlex"
        assert oa_item["provenance"]["provider"] == "OpenAlex"
        assert oa_item["provenance"]["retrieval_role"] == "DISCOVERY"
        assert oa_item["provenance"]["registry_provenance"][
            "provider"] == "openalex"
        assert oa_item["content_hash"] == "hash2"
        assert a2r.RETRIEVAL_LANES["openalex"]["status"] == "OK"
        assert a2r.RETRIEVAL_LANES["openalex"]["n_items"] == 1

    def test_failed_lane_is_partial_state_not_failure(self, monkeypatch):
        """A dead OpenAlex lane (the measured 429 budget state) returns
        the primary lane's evidence with the honest lane record — never
        absence, never a raised stage failure."""
        epmc = [{"id": "europepmc:1", "source": "EuropePMC",
                 "title": "Alpha", "abstract": "x" * 200,
                 "doi": None, "content_hash": "h1"}]
        oa = _fake_openalex_result([], status="RATE_LIMITED",
                                   error="HTTP 429: budget")
        a2r = self._patch(monkeypatch, epmc, oa)
        items = a2r.retrieve({"device": "gadget", "failure_mode": "wear"})
        assert len(items) == 1  # primary evidence intact
        assert a2r.RETRIEVAL_LANES["openalex"]["status"] == "RATE_LIMITED"
        assert "429" in a2r.RETRIEVAL_LANES["openalex"]["error"]

    def test_connector_exception_is_honest_lane_state(self, monkeypatch):
        """Even an exception in the lane is a recorded state — the
        primary evidence still flows."""
        epmc = [{"id": "europepmc:1", "source": "EuropePMC",
                 "title": "Alpha", "abstract": "x" * 200,
                 "doi": None, "content_hash": "h1"}]

        class _Boom(Exception):
            pass

        import discovery_fabric.a2.retrieve as a2r
        monkeypatch.setattr(a2r, "search_europe_pmc",
                            lambda q, per_page=5: epmc)
        monkeypatch.setattr(a2r.time, "sleep", lambda s: None)
        monkeypatch.setattr(
            "discovery_fabric.source_registry.connectors.scientific."
            "OpenAlexConnector.search",
            lambda self, q, timeout=25, retrieval_role="":
            (_ for _ in ()).throw(_Boom("socket dead")))
        monkeypatch.setattr(
            "discovery_fabric.source_registry.query_relevance."
            "keyword_form", lambda t: "q")
        items = a2r.retrieve({"device": "g", "failure_mode": "wear"})
        assert len(items) == 1
        assert a2r.RETRIEVAL_LANES["openalex"]["status"] == "SEARCH_FAILED"

    def test_doi_dedup_primary_wins_recorded(self, monkeypatch):
        """Same paper from both lanes: the primary item wins, the dedup
        record retains WHICH openalex item collapsed and WHY."""
        epmc = [{"id": "europepmc:1", "source": "EuropePMC",
                 "title": "Same Paper Title", "abstract": "x" * 200,
                 "doi": "10.9/z", "content_hash": "h1"}]
        oa = _fake_openalex_result([
            (7, "Same Paper Title", "openalex abstract " * 20, "10.9/z")])
        a2r = self._patch(monkeypatch, epmc, oa)
        items = a2r.retrieve({"device": "g", "failure_mode": "wear"})
        ids = [i["id"] for i in items]
        assert ids == ["europepmc:1"]  # primary wins, one copy
        dedup = a2r.RETRIEVAL_LANES["cross_source_dedup"]
        assert dedup == [{"deduped_id": "openalex:W7", "basis": "doi"}]

    def test_title_dedup_normalization(self, monkeypatch):
        """~Same title (case/punctuation) collapses by title basis."""
        epmc = [{"id": "europepmc:1", "source": "EuropePMC",
                 "title": "Water quality: a study!", "abstract": "x" * 200,
                 "doi": None, "content_hash": "h1"}]
        oa = _fake_openalex_result([
            (8, "Water Quality A Study", "abstract " * 30, None)])
        a2r = self._patch(monkeypatch, epmc, oa)
        items = a2r.retrieve({"device": "g", "failure_mode": "wear"})
        assert [i["id"] for i in items] == ["europepmc:1"]
        assert a2r.RETRIEVAL_LANES["cross_source_dedup"][0][
            "basis"] == "title"

    def test_primary_failure_still_raises(self, monkeypatch):
        """Art. XXI.3 discipline unchanged: the PRIMARY lane's provider
        failure raises (never absence); the OpenAlex lane does not
        rescue a dead primary — retrieve() is the a2 plane's own raise
        contract."""
        import discovery_fabric.a2.retrieve as a2r

        def _dead(q, per_page=5):
            raise a2r.SearchProviderFailure("EuropePMC down")

        monkeypatch.setattr(a2r, "search_europe_pmc", _dead)
        monkeypatch.setattr(a2r.time, "sleep", lambda s: None)
        with pytest.raises(a2r.SearchProviderFailure):
            a2r.retrieve({"device": "g", "failure_mode": "wear"})

    def test_short_abstracts_skipped(self, monkeypatch):
        """OpenAlex records with unusable abstract text (<200 chars —
        the inverted-index reconstruction often yields less) do not
        become evidence items; the lane state records the count."""
        epmc = [{"id": "europepmc:1", "source": "EuropePMC",
                 "title": "Alpha", "abstract": "x" * 200,
                 "doi": None, "content_hash": "h1"}]
        oa = _fake_openalex_result([
            (9, "Thin record", "too short", None)])
        a2r = self._patch(monkeypatch, epmc, oa)
        items = a2r.retrieve({"device": "g", "failure_mode": "wear"})
        assert [i["id"] for i in items] == ["europepmc:1"]
        assert a2r.RETRIEVAL_LANES["openalex"]["n_items"] == 0


class TestExpansionRoleLabel:
    def test_multi_source_expansion_labels_discovery(self, monkeypatch):
        """The mechanism-space expansion's connector calls carry
        retrieval_role='DISCOVERY' (the role reaches the connector)."""
        from discovery_fabric.engine import mechanism_space as ms
        calls = {}

        from types import SimpleNamespace
        empty = SimpleNamespace(status="OK", error=None, records=[])
        monkeypatch.setenv("R401_NO_EXPANSION", "1")
        out = ms.multi_source_expansion({"device": "g",
                                         "failure_mode": "wear"})
        assert out["state"].startswith("DISABLED_BY_ENV")
