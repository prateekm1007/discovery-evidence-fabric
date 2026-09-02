"""tests/test_r399_routing_states.py — R399 W3: routing states.

The registry routing layer (ARCHIVED_ROUTING / SUSPENDED_RELEVANCE):
  - a first-class, REVERSIBLE epistemic state distinct from health
    status (reachable != routed-to);
  - enforced at the run dispatch (problem_builder: the synthesis-
    feeding retrieval path) with the state + basis + reinstatement
    criterion recorded — never a silent code path, never absence;
  - the health checker reports the state WITHOUT probing (no quota
    burn for a parked source);
  - OSTI carries the SUSPENDED_RELEVANCE state with the Phase P1
    reinstatement criterion (R399 directive wording);
  - the quota breaker (W2.4): quota-class 429 trips and parks the
    source; NOT_QUERIED_QUOTA_EXHAUSTED is recorded per query; a
    plain 429 never trips it (transient backoff path preserved).
"""
from __future__ import annotations

import json

import pytest

import toscanini.problem_builder as pb
from discovery_fabric.source_registry import registry as reg
from discovery_fabric.source_registry import health


# ----------------------------------------------------------------------
# 1. The registry layer
# ----------------------------------------------------------------------

def test_routing_states_exist_with_basis_and_reinstatement():
    for sid in ("nhtsa_recalls", "nhtsa_complaints", "cod_optimade"):
        assert reg.routing_state(sid) == "ARCHIVED_ROUTING", sid
        info = reg.routing_info(sid)
        assert info["routing_basis"]
        assert info["reinstatement_criterion"]
    assert reg.routing_state("doe_osti") == "SUSPENDED_RELEVANCE"
    info = reg.routing_info("doe_osti")
    # the directive's exact reinstatement criterion: semantic reranker
    assert "semantic" in info["reinstatement_criterion"].lower()
    assert info["routing_basis"]


def test_every_source_carries_an_explicit_routing_state():
    for sid, rec in reg.SOURCE_REGISTRY.items():
        assert rec.get("routing_state") in reg.ROUTING_STATES, sid
    # the untouched majority stays ACTIVE (the archive is surgical)
    active = [sid for sid, r in reg.SOURCE_REGISTRY.items()
              if r["routing_state"] == "ACTIVE"]
    assert "europepmc" in active
    assert "fda_maude" in active
    assert len(active) > len(reg.SOURCE_REGISTRY) - 10


def test_registry_validation_still_passes():
    assert reg.validate_registry() == []


# ----------------------------------------------------------------------
# 2. Health: a parked source is reported, not probed
# ----------------------------------------------------------------------

def test_health_reports_routing_state_without_probing(monkeypatch):
    monkeypatch.setattr(
        health, "load_connector",
        lambda sid: (_ for _ in ()).throw(AssertionError(
            "a non-ACTIVE source must never be probed (R399 W3)")))
    out = health.check_source("doe_osti")
    assert out["status"] == "SUSPENDED_RELEVANCE"
    assert out["probed"] is False
    assert out["routing"]["reinstatement_criterion"]
    out = health.check_source("nhtsa_complaints")
    assert out["status"] == "ARCHIVED_ROUTING"
    assert out["probed"] is False


# ----------------------------------------------------------------------
# 3. Run dispatch: OSTI suspended from synthesis-feeding retrieval
# ----------------------------------------------------------------------

def _build(monkeypatch, extraction):
    monkeypatch.setattr(pb, "extract_problem_fields",
                        lambda text: dict(extraction))
    return pb.build_problem("Why do EV battery packs fail in the field?")


def test_osti_suspended_from_synthesis_feeding_retrieval(monkeypatch):
    out = _build(monkeypatch, {
        "domain": "energy", "device": "EV battery pack",
        "failure_mode": "thermal runaway", "constraint": "x",
        "failure_query": "lithium battery thermal runaway",
        "science_query": "lithium battery thermal runaway",
        "_llm": {"status": "OK", "provider": "test", "latency_ms": 1},
    })
    statuses = {r["source"]: r["status"]
                for r in out["evidence_pack"]["retrieval"]}
    assert statuses["doe_osti"] == "NOT_QUERIED_SUSPENDED_RELEVANCE"
    row = next(r for r in out["evidence_pack"]["retrieval"]
               if r["source"] == "doe_osti")
    assert row["routing"]["routing_state"] == "SUSPENDED_RELEVANCE"
    # the record is auditable: basis + reinstatement travel with the row
    assert row["routing"]["routing_basis"]
    assert "semantic" in row["routing"]["reinstatement_criterion"].lower()
    # and visible in the problem's routing notes (never silent)
    notes = out["evidence_pack"]["extraction"]["routing_notes"]
    assert any("doe_osti" in n and "SUSPENDED_RELEVANCE" in n
               for n in notes)


def test_osti_active_dispatches_again_when_reinstated(monkeypatch):
    """Reversible: flip the state to ACTIVE and the query dispatches
    (the suspension is an engine decision, not a deleted connector)."""
    monkeypatch.setitem(reg.SOURCE_REGISTRY["doe_osti"],
                        "routing_state", "ACTIVE")
    captured = {}

    def spy(name, role, cls, query, timeout=40, run_id="toscanini:ui"):
        captured[name] = query
        return {"source": name, "role": role, "status": "CALL_FAILED",
                "count": 0, "records": [], "relevant": 0, "error": "stub"}
    monkeypatch.setattr(pb, "_search_one", spy)
    _build(monkeypatch, {
        "domain": "energy", "device": "EV battery pack",
        "failure_mode": "thermal runaway", "constraint": "x",
        "failure_query": "lithium battery thermal runaway",
        "science_query": "lithium battery thermal runaway",
        "_llm": {"status": "OK", "provider": "test", "latency_ms": 1},
    })
    assert captured.get("doe_osti") == "lithium battery thermal runaway"


def test_cod_archived_from_materials_family(monkeypatch):
    monkeypatch.setattr(pb, "extract_problem_fields", lambda text: {
        "domain": "materials", "device": "titanium implant alloy",
        "failure_mode": "fatigue fracture", "constraint": "x",
        "failure_query": "titanium implant fatigue",
        "science_query": "titanium implant fatigue",
        "_llm": {"status": "OK", "provider": "test", "latency_ms": 1},
    })
    out = pb.build_problem("Why do titanium implants fracture?")
    statuses = {r["source"]: r["status"]
                for r in out["evidence_pack"]["retrieval"]}
    assert statuses["cod_optimade"] == "NOT_QUERIED_ARCHIVED_ROUTING"


# ----------------------------------------------------------------------
# 4. The quota circuit breaker (W2.4)
# ----------------------------------------------------------------------

def test_quota_class_429_trips_plain_429_does_not(tmp_path, monkeypatch):
    from discovery_fabric.prior_art_v2 import quota_breaker as qb
    monkeypatch.setattr(qb, "BREAKER_PATH", tmp_path / "breaker.json")
    # a quota-class 429 (Lens monthly budget message shape)
    quota_err = ("HTTP 429: Insufficient budget. Resets "
                 "2026-10-01T00:00:00Z")
    assert qb.is_quota_exhaustion(quota_err) is True
    entry = qb.trip("lens_patent", quota_err)
    assert entry is not None and entry["source_state"] == "QUOTA_EXHAUSTED"
    # parked until the stated reset (+1 h safety), not the 24 h default
    assert entry["until_utc"].startswith("2026-10-01")
    # check() reports the parked state
    parked = qb.check("lens_patent")
    assert parked is not None
    rec = qb.refusal_record("lens_patent", parked)
    assert rec["epistemic_state"] == "NOT_QUERIED_QUOTA_EXHAUSTED"
    assert "NOT absence" in rec["error"]
    # a plain transient 429 does NOT trip (backoff path preserved)
    assert qb.is_quota_exhaustion("HTTP 429: Too Many Requests") is False
    assert qb.trip("lens_patent", "HTTP 429: Too Many Requests") is None
    # an active source is unaffected
    assert qb.check("google_patents") is None


def test_breaker_window_expiry_clears_and_retries_once(
        tmp_path, monkeypatch):
    import time as _time
    from discovery_fabric.prior_art_v2 import quota_breaker as qb
    monkeypatch.setattr(qb, "BREAKER_PATH", tmp_path / "breaker.json")
    # trip with a window already in the past -> expired on check
    entry = qb.trip("lens_patent", "HTTP 429: quota exceeded")
    doc = json.loads((tmp_path / "breaker.json").read_text())
    doc["sources"]["lens_patent"]["until_epoch"] = _time.time() - 1
    (tmp_path / "breaker.json").write_text(json.dumps(doc))
    assert qb.check("lens_patent") is None  # cleared: one re-attempt


def test_search_patents_respects_a_parked_source(tmp_path, monkeypatch):
    """The parked source is refused locally for EVERY ladder step with
    the honest error record; the other sources still run."""
    from discovery_fabric.prior_art_v2 import quota_breaker as qb
    from discovery_fabric.prior_art_v2 import collision_resolution as cr
    monkeypatch.setattr(qb, "BREAKER_PATH", tmp_path / "breaker.json")
    qb.trip("lens_patent",
            "HTTP 429: Insufficient budget. Resets 2099-01-01")

    called = []

    def fake_google(query, num_results=8):
        called.append(query)
        from discovery_fabric.prior_art_v2.sources import SourceQueryResult
        return SourceQueryResult(source_id="GOOGLE_PATENTS", success=True,
                                 latency_ms=1, hits=[],
                                 query=query)

    monkeypatch.setattr(
        "discovery_fabric.prior_art_v2.sources.search_google_patents",
        fake_google)
    ladder = [{"query": "q1", "query_compact": "q1",
               "query_class": "entity"}]
    hits, errors = cr.search_patents(ladder, sources=["google_patents",
                                                      "lens_patent"])
    assert len(called) == 1  # google ran; lens never did
    lens_errors = [e for e in errors if e.get("source") == "lens_patent"]
    assert len(lens_errors) == 1
    assert lens_errors[0]["epistemic_state"] == "NOT_QUERIED_QUOTA_EXHAUSTED"
    assert lens_errors[0]["query"] == "q1"
