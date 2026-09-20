"""R512 RETRIEVE fan-out: parallel-vs-serial parity + attribution.

Hermetic (stub connectors, no network). The parallel executor must
produce byte-identical evidence content to the serial reference:
same items, same ordering, same dedup winners, same lane states,
same failure taxonomy. Only call-time timestamps may differ (they
are provenance of the actual call, Art. VI — never fabricated to
match).

The retrieval attribution record must carry every directive field
so the next audit can see which remote jobs dominate RETRIEVE.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceQueryResult, SourceRecord, utc_now,
)
from discovery_fabric.retrieval_fabric import pipeline as fabric_pipeline

PROBLEM = {
    "device": "implantable dual matched pressure sensor",
    "failure_mode": "SENSOR_DRIFT",
    "constraint": "in vivo accuracy",
}


def _rec(source_id, record_id, title, doi="",
         abstract="", **norm):
    n = {"doi": doi or None, "title": title, "abstract": abstract or None,
         "publication_year": "2020"}
    n.update(norm)
    return SourceRecord(
        source_id=source_id, role="SCIENTIFIC", record_id=record_id,
        title=title, uri="https://example.org/%s" % record_id,
        retrieved_at=utc_now(), query="stub", raw_payload_sha256="f" * 64,
        normalized=n, provenance={"provider": source_id},
        epistemic_state="OBSERVED")


class StubConnector(ConnectorBase):
    SOURCE_ID = "stub"
    ROLES = ("SCIENTIFIC",)

    def __init__(self, status="OK", records=None, error=None):
        self.status = status
        self.records = records or []
        self.error = error

    def build_url(self, query):
        return "https://stub.example/api"

    def parse_payload(self, raw, query):
        return {}

    def normalize_payload(self, payload, query, raw_sha):
        return []

    def search(self, query, timeout=25, retrieval_role=""):
        if self.status in ("OK", "EMPTY"):
            return SourceQueryResult(
                source_id=self.SOURCE_ID, status=self.status, ok=True,
                records=self.records, query=query,
                retrieved_at=utc_now())
        return SourceQueryResult(
            source_id=self.SOURCE_ID, status=self.status, ok=False,
            error=self.error or "stubbed failure", query=query,
            retrieved_at=utc_now())


class NoKwargConnector(StubConnector):
    """Registry-style connector without the retrieval_role kwarg."""

    def search(self, query, timeout=25):  # noqa: D102
        return super().search(query, timeout=timeout)


class RaisingConnector(StubConnector):
    def search(self, query, timeout=25, retrieval_role=""):
        raise ValueError("stubbed connector defect")


def _pool():
    dup_long = ("dual biopressure drift study " * 10)
    dup_short = "dual biopressure drift study"
    return {
        "europepmc": StubConnector("OK", [
            _rec("europepmc", "epmc:1", "Drift in implantable sensors",
                 "10.1/a", "drift of implantable pressure sensors " * 10)]),
        "openalex": StubConnector("OK", [
            _rec("openalex", "W1", "Dual biopressure implantable study",
                 "10.9/dup", dup_long)]),
        "semantic_scholar": StubConnector("OK", [
            _rec("semantic_scholar", "s2:1",
                 "Dual biopressure implantable study",
                 "10.9/dup", dup_short)]),
        "crossref": StubConnector("OK", [
            _rec("crossref", "doi:10.1/d", "Thermally compensated sensor",
                 "10.1/d", "thermal compensation bridge " * 10)]),
        "doaj": StubConnector("RATE_LIMITED",
                              error="429: too many requests"),
        "datacite": StubConnector("OK", [
            _rec("datacite", "10.13140/rg.1", "An Implantable Low Pressure "
                 "Low Drift Dual BioPressure Sensor",
                 "10.13140/rg.2.2.32705.61282",
                 "dissertation dual matched dies drift " * 10,
                 resource_type_general="Dissertation")]),
        "openaire": StubConnector("TIMEOUT"),
        "core": StubConnector("OK", [
            _rec("core", "core:1", "Dissertation biopressure dual die",
                 "", "dual die dissertation study " * 10,
                 document_type="thesis")]),
        "arxiv": StubConnector("UNAVAILABLE", error="503"),
        "google_patents": StubConnector("OK", [
            _rec("google_patents", "patent:US4320664A",
                 "Thermally compensated silicon pressure sensor", "",
                 snippet="dummy element bridge",
                 patent_id="US4320664A",
                 raw_metadata={"publication_date": "1982-03-23",
                               "priority_date": "1980-06-27",
                               "inventor": "Eaton",
                               "assignee_harmonized": {"name": "Foxboro"}})]),
    }


def _stub_pool(monkeypatch, pool):
    def fake_connector_for(source_id, scoped=None):
        return pool.get(source_id)

    monkeypatch.setattr(fabric_pipeline, "_connector_for",
                        fake_connector_for)

    def fake_claims(patent_id, retries=1):
        from discovery_fabric.retrieval_fabric.adapters import \
            PatentClaimFetch
        return PatentClaimFetch(patent_id=patent_id, ok=True,
                                claim_count=8,
                                claims_excerpt="1. A sensor comprising "
                                "a dummy element bridge...")

    monkeypatch.setattr(fabric_pipeline, "fetch_patent_claims_custoied",
                        fake_claims)
    monkeypatch.setattr(
        "discovery_fabric.retrieval_fabric.reciprocal.reciprocal_expansion",
        lambda *a, **k: {"records": [], "calls": [],
                         "budget": {"max": 4, "used": 0},
                         "retrieved_at": utc_now()})


def _run(monkeypatch, mode=None, workers=None):
    _stub_pool(monkeypatch, _pool())
    if mode is not None:
        monkeypatch.setenv("ENGINE_RETRIEVE_FANOUT", mode)
    else:
        monkeypatch.delenv("ENGINE_RETRIEVE_FANOUT", raising=False)
    if workers is not None:
        monkeypatch.setenv("ENGINE_RETRIEVE_MAX_WORKERS", str(workers))
    else:
        monkeypatch.delenv("ENGINE_RETRIEVE_MAX_WORKERS", raising=False)
    return fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)


def _normalized(items, report):
    norm_items = []
    for it in items:
        it2 = dict(it)
        it2.pop("retrieval_timestamp", None)
        norm_items.append(it2)
    rep = dict(report)
    rep.pop("retrieved_at", None)
    rep.pop("completed_at", None)
    # attribution carries its own wall timings (expected to differ)
    rep.pop("retrieval_attribution", None)
    return norm_items, rep


def test_parallel_matches_serial_content(monkeypatch):
    """The core parity contract: parallel execution must not change a
    single evidence byte (ordering, dedup winners, lane states,
    failure taxonomy)."""
    items_s, rep_s = _run(monkeypatch, mode="serial")
    items_p, rep_p = _run(monkeypatch, mode="parallel")
    ni_s, nr_s = _normalized(items_s, rep_s)
    ni_p, nr_p = _normalized(items_p, rep_p)
    assert (json.dumps(ni_p, sort_keys=True, default=str)
            == json.dumps(ni_s, sort_keys=True, default=str)), \
        "parallel evidence items differ from serial reference"
    assert (json.dumps(nr_p, sort_keys=True, default=str)
            == json.dumps(nr_s, sort_keys=True, default=str)), \
        "parallel fabric report differs from serial reference"
    # dedup order check: the record yielded by BOTH openalex and
    # semantic_scholar must have identical origin + best abstract
    # under BOTH modes (first-in-job-order wins)
    def _merged(canon):
        for r in canon:
            if {"openalex", "semantic_scholar"} <= set(
                    r.get("indexing_sources") or []):
                return r
        return None
    m_s = _merged(rep_s["canonical_records"])
    m_p = _merged(rep_p["canonical_records"])
    assert m_s and m_p, "shared-record dedup case missing"
    assert (m_p["origin_source"] == m_s["origin_source"] == "openalex")
    assert (m_p["best_record"]["abstract"]
            == m_s["best_record"]["abstract"])


def test_default_mode_is_parallel_and_recorded(monkeypatch):
    _, rep = _run(monkeypatch)
    attrib = rep["retrieval_attribution"]
    assert attrib["mode"] == "parallel"
    assert attrib["max_workers_configured"] == 5
    assert attrib["max_workers_effective"] >= 1
    assert attrib["peak_concurrency_observed"] >= 1
    assert (attrib["peak_concurrency_observed"]
            <= attrib["max_workers_effective"])


def test_attribution_record_complete(monkeypatch):
    """Every directive attribution field is present and coherent."""
    _, rep = _run(monkeypatch, mode="parallel")
    a = rep["retrieval_attribution"]
    for k in ("schema", "mode", "max_workers_configured",
              "max_workers_effective", "peak_concurrency_observed",
              "n_jobs", "fanout_wall_s", "total_network_s",
              "max_job_wall_s", "assemble_s",
              "orchestration_overhead_s", "jobs", "records_returned",
              "records_admitted", "canonical_merges", "enrichment_s"):
        assert k in a, k
    assert a["schema"] == "RETRIEVAL_ATTRIBUTION/1.0"
    assert a["n_jobs"] == len(a["jobs"]) > 0
    allowed = {"successful", "empty", "timeout", "unavailable",
               "other_typed_failure"}
    total = 0
    for j in a["jobs"]:
        for k in ("index", "lane", "source_id", "variant_classes",
                  "n_variants", "network_ms", "job_wall_s", "outcome",
                  "variant_statuses", "records_returned"):
            assert k in j, k
        assert j["outcome"] in allowed, j["outcome"]
        assert j["network_ms"] >= 0
        total += j["records_returned"]
    assert total == a["records_returned"]
    assert set(a["enrichment_s"]) == {"patent_claims", "reciprocal",
                                      "unpaywall"}
    # failure taxonomy preserved: the stubbed failures ride the jobs
    by_src = {j["source_id"]: j for j in a["jobs"]}
    assert by_src["doaj"]["outcome"] == "unavailable"
    assert by_src["openaire"]["outcome"] == "timeout"
    assert by_src["arxiv"]["outcome"] == "unavailable"


def test_max_workers_bound_respected(monkeypatch):
    _, rep = _run(monkeypatch, mode="parallel", workers=2)
    a = rep["retrieval_attribution"]
    assert a["max_workers_configured"] == 2
    assert a["max_workers_effective"] == 2
    assert a["peak_concurrency_observed"] <= 2
    _, rep_bad = _run(monkeypatch, mode="parallel", workers="nope")
    assert (rep_bad["retrieval_attribution"]["max_workers_configured"]
            == 5)
    _, rep_big = _run(monkeypatch, mode="parallel", workers=999)
    assert (rep_big["retrieval_attribution"]["max_workers_configured"]
            == 16)


def test_invalid_mode_falls_back_to_parallel(monkeypatch):
    _, rep = _run(monkeypatch, mode="bogus")
    assert rep["retrieval_attribution"]["mode"] == "parallel"


def test_typeerror_fallback_preserved_in_parallel(monkeypatch):
    """Registry connectors without the retrieval_role kwarg keep
    working under the worker path."""
    pool = _pool()
    pool["crossref"] = NoKwargConnector("OK", [
        _rec("crossref", "doi:10.1/z", "Kwargless connector record",
             "10.1/z", "kwargless abstract text " * 10)])
    _stub_pool(monkeypatch, pool)
    items, rep = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    assert any(it["source"] == "crossref" for it in items)


def test_raise_contract_parity(monkeypatch):
    """A connector defect that raises must surface identically under
    both modes (first-in-job-order re-raise)."""
    for mode in ("serial", "parallel"):
        pool = _pool()
        pool["core"] = RaisingConnector()
        _stub_pool(monkeypatch, pool)
        monkeypatch.setenv("ENGINE_RETRIEVE_FANOUT", mode)
        with pytest.raises(ValueError, match="stubbed connector defect"):
            fabric_pipeline.retrieve_fabric(
                PROBLEM, enable_reciprocal=False, enable_unpaywall=False)


def test_all_failed_honest_with_attribution(monkeypatch):
    """Total failure stays honest under parallel execution, with a
    complete attribution record (zeros are data)."""
    pool = {sid: StubConnector("UNAVAILABLE", error="down")
            for sid in ("europepmc", "openalex", "semantic_scholar",
                        "crossref", "doaj", "datacite", "openaire",
                        "core", "arxiv", "google_patents")}
    _stub_pool(monkeypatch, pool)
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    assert items == []
    a = report["retrieval_attribution"]
    assert a["records_returned"] == 0
    assert a["records_admitted"] == 0
    assert all(j["outcome"] in ("unavailable", "other_typed_failure")
               for j in a["jobs"])
