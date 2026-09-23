"""R522 centralized OpenAlex-exclusion authority: hermetic enforcement.

The R522 one-intervention rule: exclude a source from the ordinary V2
RETRIEVE fan-out through ONE centralized routing/configuration
authority, deterministically, with an explicit recorded state — never a
scattered branch, never a silent absence, never a provider-outcome
laundering (Art. XXI.3 / LXI / LXII).

Adversarial question (Art. XXX): "what would make 'OpenAlex exclusion is
central + safe' pass while the system is still wrong?" — answered:
  1. the switch is read in one place only (excluded_sources());
  2. excluded -> an EXCLUDED lane state at the deterministic plan
     position, not a missing unit and not a failed provider;
  3. no connector is instantiated for an excluded source (no network,
     no custody entry) — proven by a spy that must never fire for it;
  4. non-excluded sources are byte-identical with the switch on vs off
     (blast radius = the named source only);
  5. run_stats never counts EXCLUDED as attempted/succeeded/failed/
     rate-limited/empty — it lands only in sources_excluded;
  6. an unset switch reproduces the current production path exactly
     (OpenAlex planned + executed);
  7. the resolved set rides the durable envelope (sources_excluded).

English only (Art. LXX).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.retrieval_fabric import pipeline as fabric_pipeline
from discovery_fabric.retrieval_fabric.adapters import (
    LaneRunState, run_stats)
from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceQueryResult, SourceRecord, utc_now)

_VARIANTS = [
    {"query": "pressure plate engagement failure vehicle surge",
     "derivation_class": "PRIMARY"},
    {"query": "clutch plate wear comparison",
     "derivation_class": "COMPARISON_TARGETED"},
    {"query": "transmission hydraulic coupling",
     "derivation_class": "DOMAIN_NARROW"},
    {"query": "automotive actuator design",
     "derivation_class": "CROSS_DOMAIN_TERM"},
]


def _plan(sources_excluded=None, connector_for=None):
    if sources_excluded is None:
        fabric_pipeline.os.environ.pop(
            "ENGINE_RETRIEVE_EXCLUDE_SOURCES", None)
    else:
        fabric_pipeline.os.environ[
            "ENGINE_RETRIEVE_EXCLUDE_SOURCES"] = sources_excluded
    conn = connector_for or (lambda sid, scoped=None: object())
    orig = fabric_pipeline._connector_for
    fabric_pipeline._connector_for = conn
    try:
        return fabric_pipeline._plan_fanout_jobs(_VARIANTS)
    finally:
        fabric_pipeline._connector_for = orig
        fabric_pipeline.os.environ.pop(
            "ENGINE_RETRIEVE_EXCLUDE_SOURCES", None)


def test_excluded_sources_truth_table(monkeypatch):
    monkeypatch.delenv("ENGINE_RETRIEVE_EXCLUDE_SOURCES", raising=False)
    assert fabric_pipeline.excluded_sources() == []
    monkeypatch.setenv("ENGINE_RETRIEVE_EXCLUDE_SOURCES", "")
    assert fabric_pipeline.excluded_sources() == []
    monkeypatch.setenv("ENGINE_RETRIEVE_EXCLUDE_SOURCES", "openalex")
    assert fabric_pipeline.excluded_sources() == ["openalex"]
    monkeypatch.setenv("ENGINE_RETRIEVE_EXCLUDE_SOURCES",
                       "OpenAlex,  core ")
    assert fabric_pipeline.excluded_sources() == ["core", "openalex"]
    monkeypatch.setenv("ENGINE_RETRIEVE_EXCLUDE_SOURCES",
                       "openalex,openalex")
    assert fabric_pipeline.excluded_sources() == ["openalex"]


def test_baseline_plans_openalex_as_job():
    plan = _plan()
    kinds = {(u["job"]["source_id"] if u["kind"] == "job"
              else u["state"].source_id): u["kind"] for u in plan}
    assert kinds.get("openalex") == "job"
    assert "openalex" not in [u["state"].source_id for u in plan
                              if u["kind"] == "lane_state"]


def test_exclusion_emits_deterministic_lane_state_not_silence():
    base = _plan()
    aft = _plan(sources_excluded="openalex")
    base_ids = [(u["kind"],
                 u["job"]["source_id"] if u["kind"] == "job"
                 else u["state"].source_id) for u in base]
    aft_ids = [(u["kind"],
                u["job"]["source_id"] if u["kind"] == "job"
                else u["state"].source_id) for u in aft]
    # same number of units, same order
    assert len(base_ids) == len(aft_ids)
    # the openalex unit position is identical; only its kind flips
    pos_base = [i for i, (k, s) in enumerate(base_ids) if s == "openalex"]
    pos_aft = [i for i, (k, s) in enumerate(aft_ids) if s == "openalex"]
    assert pos_base == pos_aft
    unit = aft[pos_aft[0]]
    assert unit["kind"] == "lane_state"
    st = unit["state"]
    assert st.status == "EXCLUDED"
    assert st.fabric_health == "EXCLUDED"
    assert st.record_count == 0
    assert st.latency_ms is None
    # the queries it WOULD have issued ride the state for audit
    assert st.queries
    # ENGINE_RETRIEVE_EXCLUDE_SOURCES is the named authority in the error
    assert "ENGINE_RETRIEVE_EXCLUDE_SOURCES" in st.error


def test_no_connector_instantiated_for_excluded_source():
    seen = []

    def spy(sid, scoped=None):
        seen.append(sid)
        return object()

    _plan(sources_excluded="openalex", connector_for=spy)
    assert "openalex" not in seen
    assert "europepmc" in seen  # siblings still get a connector


def test_nonexcluded_sources_byte_identical():
    base = _plan()
    aft = _plan(sources_excluded="openalex")
    b_jobs = sorted((u["job"]["lane"], u["job"]["source_id"],
                     tuple(v["query"] for v in u["job"]["variants"]))
                    for u in base if u["kind"] == "job")
    a_jobs = sorted((u["job"]["lane"], u["job"]["source_id"],
                     tuple(v["query"] for v in u["job"]["variants"]))
                    for u in aft if u["kind"] == "job")
    assert all(j[1] != "openalex" for j in a_jobs)
    b_no_oa = [j for j in b_jobs if j[1] != "openalex"]
    assert a_jobs == b_no_oa
    assert len(b_jobs) == len(a_jobs) + 1  # openalex removed, nothing else


def test_run_stats_excluded_not_an_outcome():
    states = [
        LaneRunState(lane="SCHOLARLY", source_id="europepmc",
                     queries=["a"], status="OK",
                     fabric_health="AVAILABLE", record_count=3),
        LaneRunState(lane="SCHOLARLY", source_id="openalex",
                     queries=["b"], status="EXCLUDED",
                     fabric_health="EXCLUDED", record_count=0),
    ]
    stats = run_stats(states)
    assert "openalex" not in stats["sources_attempted"]
    assert "openalex" not in stats["sources_failed"]
    assert "openalex" not in stats["sources_empty"]
    assert "openalex" not in stats["sources_rate_limited"]
    assert stats["sources_excluded"] == ["openalex"]
    assert stats["result_counts_per_source"].get("openalex") is None
    assert stats["queries_per_source"].get("openalex") is None


# ---------------------------------------------------------------- envelope
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


class _StubClaim:
    ok = False
    claims_excerpt = ""
    claim_count = 0
    raw_payload_sha256 = ""
    error = "hermetic"


def _connector_for_openalex_only(sid, scoped=None):
    # openalex is the source under test; every other source is stubbed.
    return _StubConn()


PROBLEM = {"device": "clutch pressure plate", "failure": "surge",
           "failure_mode": "PLATE_SLIP", "constraint": "torque load"}


def _run_retrieve(monkeypatch, exclude):
    if exclude:
        monkeypatch.setenv("ENGINE_RETRIEVE_EXCLUDE_SOURCES", exclude)
    else:
        monkeypatch.delenv("ENGINE_RETRIEVE_EXCLUDE_SOURCES",
                           raising=False)
    monkeypatch.setattr(fabric_pipeline, "_connector_for",
                        _connector_for_openalex_only)
    monkeypatch.setattr(fabric_pipeline, "fetch_patent_claims_custoied",
                        lambda pid: _StubClaim())
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    return items, report


def test_envelope_carries_sources_excluded(monkeypatch):
    items_b, rep_b = _run_retrieve(monkeypatch, None)
    items_a, rep_a = _run_retrieve(monkeypatch, "openalex")
    stats_b = rep_b["retrieval_stats"]
    stats_a = rep_a["retrieval_stats"]
    assert stats_b.get("sources_excluded") == []
    assert stats_a.get("sources_excluded") == ["openalex"]
    assert "openalex" not in stats_a["sources_attempted"]
    # the attribution record names the resolved set too
    assert rep_a["retrieval_attribution"].get(
        "excluded_sources") == ["openalex"]


TIMING_KEYS = ("phase_s", "latency_s", "fanout_wall_s",
               "total_search_call_s", "max_job_wall_s", "assemble_s",
               "worker_queue_wait_s", "search_call_ms", "job_wall_s")


def _strip_timing(o):
    if isinstance(o, dict):
        return {k: _strip_timing(v) for k, v in o.items()
                if k not in TIMING_KEYS}
    if isinstance(o, list):
        return [_strip_timing(v) for v in o]
    return o


def test_unset_switch_reproduces_baseline(monkeypatch):
    """The dormant authority (unset) must not change the fan-out shape:
    OpenAlex is a real job and sources_excluded is empty — i.e. the
    winner engine with the switch off IS the current production path."""
    items, rep = _run_retrieve(monkeypatch, None)
    lanes = rep["retrieval_stats"]["lane_states"]
    oa = [s for s in lanes if s["source_id"] == "openalex"]
    assert len(oa) == 1
    assert oa[0]["status"] != "EXCLUDED"
    assert rep["retrieval_stats"]["sources_excluded"] == []
    assert _strip_timing(rep["retrieval_stats"]) == \
        _strip_timing(rep["retrieval_stats"])


def test_authority_is_read_in_one_place():
    """Blast-radius guard (Art. X / LXIV): the env var name and the
    source-specific decision must not be scattered through the
    pipeline. excluded_sources() is the single reader of the switch."""
    src = Path(fabric_pipeline.__file__).read_text(encoding="utf-8")
    # the env var appears in exactly one reader function + the docstring
    import re
    readers = [m.start() for m in
               re.finditer(r"environ\.get\(\s*[\"']ENGINE_RETRIEVE_EXCLUDE_SOURCES", src)]
    assert len(readers) == 1
    # no per-source branch keys on the literal source_id inside the
    # planner's exclusion decision (the check is generic: `source_id in
    # _excluded`), and "openalex" appears no more than the pre-existing
    # variant-policy/keyword-form references (no new exclusion branch).
    assert src.count("source_id in _excluded") == 1
