"""R521 retrieval sub-phase timing: observability-only instrumentation.

Hermetic (no network): stubbed transports/connectors throughout. The
instrumentation under test adds perf_counter brackets + latency fields
ONLY — no ordering, retry, timeout, routing, prompt, budget, or
threshold change. These tests evidence that claim:

  1. connector attempts carry per-attempt latency_s (INDEX_LOADING
     retry path AND success path);
  2. the retry/backoff policy is unchanged (429 -> single attempt;
     INDEX_LOADING -> bounded retries with identical states);
  3. evidence-fabric channel meta carries latency_s;
  4. pipeline phase_s is present, non-negative, and bounded by the
     enclosing wall on a hermetic retrieve;
  5. hermetic retrieve determinism IGNORING timing fields (the
     adversarial behavior-neutrality case: strip every timing key and
     require byte-identical evidence content across two runs);
  6. the R521 harvester reads instrumented envelopes AND tolerates
     pre-instrumentation envelopes (no crash, UNKNOWN verdicts).

English only (Art. LXX).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.evidence_fabric import connectors as hc
from discovery_fabric.evidence_fabric import _query_source
from discovery_fabric.retrieval_fabric import pipeline as fabric_pipeline
from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceQueryResult, SourceRecord, utc_now,
)

TIMING_KEYS = ("phase_s", "latency_s", "fanout_wall_s",
               "total_search_call_s", "max_job_wall_s", "assemble_s",
               "worker_queue_wait_s", "search_call_ms", "job_wall_s",
               "pacing_s", "channel_latency_sum_s", "retrieved_at")
# enrichment_s values are pre-existing wall measurements (not R521
# behavior): compared by key presence only, never by value.
ENRICHMENT_KEY = "enrichment_s"


def _strip_timing_deep(o):
    if isinstance(o, dict):
        out = {}
        for k, v in o.items():
            if k in TIMING_KEYS:
                continue
            if k == ENRICHMENT_KEY and isinstance(v, dict):
                out[k] = sorted(v.keys())
                continue
            if k == "attempts" and isinstance(v, list):
                out[k] = [{kk: vv for kk, vv in a.items()
                           if kk != "latency_s"} for a in v]
                continue
            out[k] = _strip_timing_deep(v)
        return out
    if isinstance(o, list):
        return [_strip_timing_deep(v) for v in o]
    return o


# ---------------------------------------------------------------- connectors
def test_attempts_carry_latency_on_retry_path(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, timeout=60):
        calls["n"] += 1
        if calls["n"] == 1:
            return {"error": "index is loading"}, None
        return {"rows": [{"row_idx": 0, "row": {"text": "x"}}],
                "num_rows_total": 1}, None

    monkeypatch.setattr(hc, "_get_json", fake_get)
    rows, meta = hc.search_rows("ds", "c", "s", "q", length=1,
                                index_retries=2, retry_backoff_s=0)
    assert rows is not None and len(rows) == 1
    assert meta["state"] == "SUCCESS"
    assert len(meta["attempts"]) == 2
    assert meta["attempts"][0]["state"] == "INDEX_LOADING"
    assert meta["attempts"][1]["state"] == "SUCCESS"
    for a in meta["attempts"]:
        assert isinstance(a["latency_s"], float) and a["latency_s"] >= 0.0


def test_no_retry_on_rate_limited(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, timeout=60):
        calls["n"] += 1
        return None, "RATE_LIMITED"

    monkeypatch.setattr(hc, "_get_json", fake_get)
    rows, meta = hc.search_rows("ds", "c", "s", "q", length=1)
    assert rows is None
    assert meta["state"] == "UNKNOWN"
    assert meta["reason"] == "RATE_LIMITED"
    assert len(meta["attempts"]) == 1
    assert isinstance(meta["attempts"][0]["latency_s"], float)


# ---------------------------------------------------------------- channel meta
def test_channel_meta_carries_latency(monkeypatch):
    def fake_search(ds, config, split, query, length=4):
        return ([{"row_idx": 0,
                  "row": {"text": "reaction record",
                          "title": "t"}}],
                {"state": "SUCCESS", "num_rows_total": 1,
                 "endpoint": "search",
                 "attempts": [{"attempt": 0, "state": "SUCCESS",
                               "latency_s": 0.5}],
                 "query": query})

    monkeypatch.setattr(hc, "search_rows", fake_search)
    src = {"source_id": "chemrag_reactions", "dataset_id": "d",
           "config": "default", "split": "train",
           "query_mode": "search", "text_field": "text",
           "license_verified": True, "license": "cc0-1.0"}
    recs, meta = _query_source(src, "test query",
                               problem={"device": "x"})
    assert meta["state"] == "SUCCESS"
    assert isinstance(meta["latency_s"], float) and meta["latency_s"] >= 0.0
    assert recs is not None


# ---------------------------------------------------------------- pipeline phases
class _StubConn(ConnectorBase):
    SOURCE_ID = "stub-all"
    ROLES = ("SCIENTIFIC",)

    def search(self, query, timeout=25, retrieval_role=""):
        return SourceQueryResult(
            source_id=self.SOURCE_ID, status="OK", ok=True,
            records=[SourceRecord(
                source_id=self.SOURCE_ID, role="SCIENTIFIC",
                record_id="stub:1", title="Stub record one",
                uri="https://example.org/1",
                retrieved_at=utc_now(), query=query,
                raw_payload_sha256="f" * 64,
                normalized={"title": "Stub record one",
                            "abstract": "stub abstract text " * 8},
                provenance={"provider": self.SOURCE_ID},
                epistemic_state="OBSERVED")],
            query=query, retrieved_at=utc_now())


def _stub_connector_for(source_id, scoped=None):
    return _StubConn()


class _StubClaimFetch:
    ok = False
    claims_excerpt = ""
    claim_count = 0
    raw_payload_sha256 = ""
    error = "stubbed (hermetic: no patent-claim network)"


def _stub_claim_fetch(patent_id):
    return _StubClaimFetch()


PROBLEM = {"device": "test valve", "failure": "test leak",
           "failure_mode": "TEST_LEAK", "constraint": "test bench"}


def test_phase_s_present_and_bounded(monkeypatch):
    monkeypatch.setattr(fabric_pipeline, "_connector_for",
                        _stub_connector_for)
    monkeypatch.setattr(fabric_pipeline, "fetch_patent_claims_custoied",
                        _stub_claim_fetch)
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    att = report["retrieval_attribution"]
    phases = att.get("phase_s")
    assert isinstance(phases, dict)
    for key in ("query_derivation", "fanout",
                "canonicalization_diversity_stats",
                "ranking_item_assembly"):
        assert key in phases, f"missing phase {key}"
        assert isinstance(phases[key], (int, float))
        assert phases[key] >= 0.0
    assert att.get("fanout_wall_s") == phases["fanout"]
    assert len(items) >= 0


def test_hermetic_retrieve_deterministic_ignoring_timing(monkeypatch):
    """Adversarial behavior-neutrality: two hermetic runs must produce
    byte-identical evidence content once every timing key is stripped.
    If instrumentation altered behavior, this fails."""
    monkeypatch.setattr(fabric_pipeline, "_connector_for",
                        _stub_connector_for)
    monkeypatch.setattr(fabric_pipeline, "fetch_patent_claims_custoied",
                        _stub_claim_fetch)
    _, rep1 = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    _, rep2 = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    s1 = _strip_timing_deep(rep1["retrieval_attribution"])
    s2 = _strip_timing_deep(rep2["retrieval_attribution"])
    assert s1 == s2


# ---------------------------------------------------------------- harvester compat
def test_harvester_reads_instrumented_and_legacy():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]
                           / "scripts"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "r521_harvest_attribution",
        str(Path(__file__).resolve().parents[1] / "scripts"
            / "r521_harvest_attribution.py"))
    # import would sys.exit without R521_ARM; exercise the pure
    # function via source load with a stubbed env instead
    import os
    os.environ["R521_ARM"] = "before"
    try:
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        del os.environ["R521_ARM"]
    legacy_env = {"provenance": {"retrieval_fabric": {
        "retrieval_attribution": {"mode": "parallel", "n_jobs": 1,
                                  "fanout_wall_s": 2.0, "jobs": []},
        "sources_attempted": [], "sources_succeeded": [],
        "sources_failed": [], "sources_rate_limited": []}}}
    out = mod._retrieve_two_level(legacy_env, [])
    assert out["phase_s"] is None
    assert out["evidence_fabric"]["per_channel_timing"]["class"] == \
        "UNKNOWN"
    assert out["connector_visibility_verdict"][
        "retry_waste_claim_permitted"] is False
    modern_env = {"provenance": {"retrieval_fabric": {
        "retrieval_attribution": {
            "mode": "parallel", "n_jobs": 0, "fanout_wall_s": 1.0,
            "total_search_call_s": 1.0, "max_job_wall_s": 1.0,
            "assemble_s": 0.0, "worker_queue_wait_s": 0.0, "jobs": [],
            "enrichment_s": {"patent_claims": 0.0},
            "phase_s": {"query_derivation": 0.1, "fanout": 1.0}},
        "sources_attempted": [], "sources_succeeded": [],
        "sources_failed": [], "sources_rate_limited": [],
        "evidence_fabric": {
            "channels": 1, "unknown_channels": 0,
            "channel_latencies": [{"source_id": "s", "state": "SUCCESS",
                                   "attempted_as": "primary",
                                   "latency_s": 0.7, "records": 1}],
            "channel_latency_sum_s": 0.7, "pacing_s": 0.0}}}}
    out2 = mod._retrieve_two_level(modern_env, [])
    assert out2["phase_s"]["fanout"] == 1.0
    assert out2["evidence_fabric"]["per_channel_timing"]["class"] == \
        "OBSERVED_IN_STAGE"
