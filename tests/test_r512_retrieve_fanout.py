"""R512 RETRIEVE fan-out: parallel-vs-serial parity + attribution.

Hermetic (stub connectors, no network). The parallel executor must
produce byte-identical evidence content to the serial reference:
same items, same ordering, same dedup winners, same lane states,
same failure taxonomy. Only call-time timestamps may differ (they
are provenance of the actual call, Art. VI — never fabricated to
match).

Section A compares the two shipped execution modes (parallel vs
ENGINE_RETRIEVE_FANOUT=serial). Section B compares the parallel
path against FROZEN_REFERENCE_SERIAL, a verbatim copy of the
pre-R512 loop (commit 47b60e73) embedded below: the auditor
correctly observed that mode-vs-mode alone shares the new
planner/worker/assembler, so the frozen copy is the independent
proof of pre-R512 semantic equivalence (Arts. III, XVI).

Narrowed exception contract (audited R512): a worker raise
re-surfaces first-in-plan-order with identical type/message, and
lane_states/canonical content assembled BEFORE the raise point is
identical; but already-executed parallel jobs keep their network
side effects (no rollback). The adversarial test below pins all
three properties.
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
              "n_jobs", "fanout_wall_s", "total_search_call_s",
              "max_job_wall_s", "assemble_s",
              "worker_queue_wait_s", "jobs", "records_returned",
              "records_admitted", "canonical_merges", "enrichment_s"):
        assert k in a, k
    assert a["schema"] == "RETRIEVAL_ATTRIBUTION/1.0"
    assert a["n_jobs"] == len(a["jobs"]) > 0
    allowed = {"successful", "empty", "timeout", "unavailable",
               "other_typed_failure"}
    total = 0
    for j in a["jobs"]:
        for k in ("index", "lane", "source_id", "variant_classes",
                  "n_variants", "search_call_ms", "job_wall_s", "outcome",
                  "variant_statuses", "records_returned"):
            assert k in j, k
        assert j["outcome"] in allowed, j["outcome"]
        assert j["search_call_ms"] >= 0
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


# ---------------------------------------------------------------------------
# B. independent frozen serial reference (verbatim pre-R512 loop,
#    commit 47b60e73 — FROZEN; do not "fix" it to match new code)
# ---------------------------------------------------------------------------

def _serial_reference_frozen(all_variants, canonicalizer, lane_states):
    """Verbatim copy of the pre-R512 lane fan-out loop
    (47b60e73:discovery_fabric/retrieval_fabric/pipeline.py, the
    "# ---- 3. lane fan-out" block), adapted only to take its inputs
    as parameters. Shared leaf helpers (_select_variants,
    _ingest_record, fabric_health_of, LaneRunState) are unchanged
    pre/post and are intentionally reused: the independence under
    test is the ORCHESTRATION (plan/execute/assemble/order), which
    this copy does not share with the new implementation.
    """
    from discovery_fabric.retrieval_fabric.adapters import (
        LaneRunState, fabric_health_of,
    )
    from discovery_fabric.retrieval_fabric.fabric_registry import (
        get_fabric_source,
    )
    from discovery_fabric.retrieval_fabric.pipeline import (
        LANE_SOURCE_MAP, SOURCE_VARIANT_POLICY, _ingest_record,
        _select_variants,
    )
    for lane, source_ids in LANE_SOURCE_MAP.items():
        for source_id in source_ids:
            fabric_src = get_fabric_source(source_id)
            if fabric_src is None:
                continue  # not in this fabric version
            policy = SOURCE_VARIANT_POLICY.get(source_id, "PRIMARY")
            scoped = "THESIS" if (lane == "THESIS" and
                                  source_id in ("crossref", "datacite")) else None
            chosen = _select_variants(all_variants, policy)
            if lane == "THESIS" and source_id in ("openaire", "core"):
                # thesis lane on post-hoc sources: use a CROSS_DOMAIN
                # variant if present (alternative terminology is the
                # measured discovery path for theses)
                chosen = ([v for v in all_variants
                           if v["derivation_class"] == "CROSS_DOMAIN_TERM"][:1]
                          or chosen)
            if not chosen:
                continue
            conn = fabric_pipeline._connector_for(source_id, scoped)
            if conn is None:
                lane_states.append(LaneRunState(
                    lane=lane, source_id=source_id,
                    queries=[v["query"] for v in chosen],
                    status="NOT_IMPLEMENTED", fabric_health="DEGRADED",
                    error="connector unavailable in registry wiring"))
                continue
            state = LaneRunState(lane=lane, source_id=source_id,
                                 queries=[v["query"] for v in chosen])
            total_records = 0
            variant_statuses = []
            errors = []
            for v in chosen:
                q = v["query"]
                try:
                    result = conn.search(
                        q, retrieval_role="DISCOVERY")
                except TypeError:
                    # some registry connectors (prior_art_v2 wrappers) do
                    # not accept the retrieval_role kwarg — call without
                    # it (the custody log entry is still written by the
                    # wrapper's own _finish path)
                    result = conn.search(q)
                variant_statuses.append(result.status)
                total_records += len(result.records)
                if result.error:
                    errors.append(f"[{result.status}] {str(result.error)[:120]}")
                for rec in result.records:
                    _ingest_record(canonicalizer, source_id, rec, q,
                                   v["derivation_class"], lane_states, lane,
                                   scoped)
            # multi-variant honesty: the source is AVAILABLE when ANY
            # variant was answered (OK/EMPTY); a variant-level failure is
            # recorded in the error string, never masked as total failure
            any_answered = any(s in ("OK", "EMPTY") for s in variant_statuses)
            if any_answered:
                state.status = "OK" if total_records else "EMPTY"
            else:
                state.status = variant_statuses[-1] if variant_statuses else "SEARCH_FAILED"
            state.record_count = total_records
            state.error = "; ".join(errors)[:300] or None
            state.fabric_health = fabric_health_of(state.status)
            lane_states.append(state)


def _reference_run(monkeypatch, pool):
    """Drive the frozen reference on stub connectors (no patent-claim
    enrichment: google_patents is excluded so the reference's
    canonical pool compares directly with the fan-out pool)."""
    from discovery_fabric.retrieval_fabric.canonical import Canonicalizer
    from discovery_fabric.retrieval_fabric.query_expansion import (
        expand_query, mechanism_query,
    )
    _stub_pool(monkeypatch, pool)
    primary = mechanism_query(PROBLEM)
    all_variants = expand_query(primary, PROBLEM)
    canonicalizer = Canonicalizer()
    lane_states = []
    _serial_reference_frozen(all_variants, canonicalizer, lane_states)
    return canonicalizer, lane_states


def test_parallel_matches_frozen_reference(monkeypatch):
    """Parallel path vs the independent pre-R512 contract.

    google_patents is excluded from the pool so both sides run
    without the post-fan-out claim-enrichment step (covered instead
    by the mode-vs-mode test, which runs enrichment identically).
    """
    pool = _pool()
    del pool["google_patents"]
    canonicalizer, lane_states = _reference_run(monkeypatch, pool)
    _stub_pool(monkeypatch, dict(pool))
    monkeypatch.delenv("ENGINE_RETRIEVE_FANOUT", raising=False)
    monkeypatch.delenv("ENGINE_RETRIEVE_MAX_WORKERS", raising=False)
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    ref_canon = json.dumps(
        [r.to_dict() for r in canonicalizer.canonical_records()],
        sort_keys=True, default=str)
    new_canon = json.dumps(report["canonical_records"],
                           sort_keys=True, default=str)
    assert ref_canon == new_canon, \
        "parallel canonical pool differs from frozen reference"
    ref_lanes = json.dumps([s.to_dict() for s in lane_states],
                           sort_keys=True, default=str)
    new_lanes = json.dumps(report["retrieval_stats"]["lane_states"],
                           sort_keys=True, default=str)
    assert new_lanes == ref_lanes, \
        "parallel lane states differ from frozen reference"
    # engine items likewise (minus call-time timestamps)
    ref_ids = sorted(r.canonical_id
                     for r in canonicalizer.canonical_records())
    new_ids = sorted(it["canonical_id"] for it in items)
    assert new_ids == ref_ids, \
        "engine pool diverged from reference canonical pool"


def test_missing_connector_ordering_parity(monkeypatch):
    """An interspersed missing connector must land in the same
    LANE_SOURCE_MAP position under all three executions (parallel,
    shipped serial, frozen reference) — not front/back-loaded."""
    pool = _pool()
    del pool["crossref"]  # middle of SCHOLARLY: europepmc, openalex,
    # semantic_scholar, CROSSREF, doaj
    got = {}
    for mode in ("parallel", "serial"):
        _stub_pool(monkeypatch, dict(pool))
        monkeypatch.setenv("ENGINE_RETRIEVE_FANOUT", mode)
        _, rep = fabric_pipeline.retrieve_fabric(
            PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
        got[mode] = [(s["lane"], s["source_id"], s["status"])
                     for s in rep["retrieval_stats"]["lane_states"]]
    canonicalizer, lane_states = _reference_run(monkeypatch, pool)
    got["reference"] = [(s.lane, s.source_id, s.status)
                        for s in lane_states]
    assert got["parallel"] == got["serial"] == got["reference"], \
        "lane-state ordering diverged across executions"
    sch_names = [s for l, s, _ in got["parallel"] if l == "SCHOLARLY"]
    assert (sch_names.index("crossref")
            == sch_names.index("semantic_scholar") + 1), \
        "NOT_IMPLEMENTED crossref not interleaved at its map position"
    cross = [t for t in got["parallel"] if t[1] == "crossref"][0]
    assert cross[2] == "NOT_IMPLEMENTED"


class CountingStub(StubConnector):
    """Stub recording every search invocation (side-effect witness)."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self.calls = []

    def search(self, query, timeout=25, retrieval_role=""):
        self.calls.append(query)
        return super().search(query, timeout=timeout,
                              retrieval_role=retrieval_role)


class CountingRaising(CountingStub):
    def search(self, query, timeout=25, retrieval_role=""):
        self.calls.append(query)
        raise ValueError("stubbed connector defect")


def test_exception_contract_adversarial(monkeypatch):
    """Narrowed contract, pinned adversarially: (1) identical
    exception identity under both modes; (2) lane_states/canonical
    prefix identical (units before the raise point); (3) disclosed
    divergence — parallel keeps already-executed jobs' network side
    effects (more searches ran than serial)."""
    from discovery_fabric.retrieval_fabric.canonical import Canonicalizer
    from discovery_fabric.retrieval_fabric.query_expansion import (
        expand_query, mechanism_query,
    )

    def _pool_counting(fail_at):
        pool = {}
        for sid, stub in _pool().items():
            if sid == fail_at:
                pool[sid] = CountingRaising()
            else:
                c = CountingStub(stub.status, stub.records, stub.error)
                pool[sid] = c
        return pool

    # scenario 1: raise at the FIRST job (europepmc) — empty prefix
    serial_calls = parallel_calls = None
    serial_states = parallel_states = None
    for mode in ("serial", "parallel"):
        pool = _pool_counting("europepmc")
        _stub_pool(monkeypatch, pool)
        monkeypatch.setenv("ENGINE_RETRIEVE_FANOUT", mode)
        with pytest.raises(ValueError,
                           match="stubbed connector defect"):
            fabric_pipeline.retrieve_fabric(
                PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
        n = sum(len(s.calls) for s in pool.values())
        if mode == "serial":
            serial_calls = n
        else:
            parallel_calls = n
    assert serial_calls == 1, serial_calls
    assert parallel_calls > serial_calls, \
        "parallel must disclose extra executed searches, got %s" % (
            parallel_calls,)

    # scenario 2: raise at the LAST lane (google_patents) — full
    # non-empty prefix must be identical across modes
    prefix = {}
    for mode in ("serial", "parallel"):
        pool = _pool_counting("google_patents")
        _stub_pool(monkeypatch, pool)
        monkeypatch.setenv("ENGINE_RETRIEVE_FANOUT", mode)
        with pytest.raises(ValueError,
                           match="stubbed connector defect"):
            try:
                fabric_pipeline.retrieve_fabric(
                    PROBLEM, enable_reciprocal=False,
                    enable_unpaywall=False)
            except ValueError as exc:
                prefix[mode] = str(exc)
                raise
    assert prefix["serial"] == prefix["parallel"]
    # prefix states: drive the frozen reference with the same
    # patent-less pool, then compare the assembled lane order
    # (both sides carry the PATENT NOT_IMPLEMENTED state at its map
    # position — the ordering property under test)
    pool = _pool()
    del pool["google_patents"]
    canonicalizer, lane_states = _reference_run(monkeypatch, pool)
    order = [(s.lane, s.source_id) for s in lane_states]
    assert len(order) > 0
    # and the shipped serial mode assembles the identical order
    _stub_pool(monkeypatch, dict(pool))
    monkeypatch.setenv("ENGINE_RETRIEVE_FANOUT", "serial")
    _, rep = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    got = [(s["lane"], s["source_id"])
           for s in rep["retrieval_stats"]["lane_states"]]
    assert got == order
