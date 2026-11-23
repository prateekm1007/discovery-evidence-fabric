#!/usr/bin/env python3
"""tests/test_pool_admission_gate.py — the R139 DIR-3 acceptance:
functional tests of the REAL engine-boundary gate and the REAL
enrichment executor (the same functions run.py's pool build calls).
NO source-text pattern checks.

Cases: grounded joins the pool; ungrounded never does (including a
legacy unlabeled envelope — fail closed); the enrichment executor
runs a REAL retrieval attempt and records its outcome per hypothesis;
an enriched-grounded hypothesis joins; retrieval failure types as
infrastructure, never as evidence absence."""
import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.run import (  # noqa: E402
    ms_pool_admission_split, enrich_ungrounded_hypotheses)


def _grounded(cid="g1"):
    return {"candidate_id": cid,
            "candidate_lifecycle": "EVIDENCE_GROUNDED_CANDIDATE",
            "discovery_admissible": True,
            "mechanism": "trailing edge vortex generators suppress "
                         "cavitation erosion on francis runner blades",
            "intervention": "install vortex generators"}


def _ungrounded(cid="u1"):
    return {"candidate_id": cid,
            "candidate_lifecycle": "UNGROUNDED_HYPOTHESIS",
            "discovery_admissible": False,
            "enrichment_required": True,
            "mechanism": "quantum plasmonic resonance damping lattice",
            "intervention": "coat blades with a plasmonic lattice"}


def test_grounded_joins_ungrounded_split_out():
    adm, ung = ms_pool_admission_split([_grounded(), _ungrounded()])
    assert [c["candidate_id"] for c in adm] == ["g1"]
    assert [c["candidate_id"] for c in ung] == ["u1"]


def test_legacy_unlabeled_fails_closed_to_ungrounded():
    """A candidate WITHOUT lifecycle labels (an R138-era envelope) is
    NOT admissible — an unlabeled candidate is never admitted."""
    adm, ung = ms_pool_admission_split(
        [{"candidate_id": "old1", "mechanism": "x",
          "intervention": "y"}])
    assert not adm and len(ung) == 1
    assert ung[0]["candidate_lifecycle"] == "UNGROUNDED_HYPOTHESIS"
    assert ung[0]["discovery_admissible"] is False
    assert ung[0]["enrichment_required"] is True


def test_false_admissible_flag_not_enough():
    """discovery_admissible=True WITHOUT the lifecycle label is not
    enough — both fields must agree (the label is the authority)."""
    adm, ung = ms_pool_admission_split(
        [{"candidate_id": "x1", "discovery_admissible": True}])
    assert not adm and len(ung) == 1


def test_enrichment_executes_and_records(tmp_path=None):
    """The REAL enrichment executor: one ungrounded hypothesis, a real
    retrieval attempt (the live Europe PMC path or its typed failure),
    the outcome recorded per hypothesis. This drives the actual
    production function end to end."""
    td = Path(tmp_path or tempfile.mkdtemp())
    problem = {"device": "Francis runner",
               "failure": "cavitation erosion",
               "problem_id": "t-enrich-1"}
    ungrounded = [_ungrounded("u-enrich-1")]
    # a mechanism with real-world terms so retrieval can hit
    ungrounded[0]["mechanism"] = (
        "ultrasonic antifouling vibration suppresses marine growth "
        "on ship hulls")
    res = enrich_ungrounded_hypotheses(problem, ungrounded, td,
                                       max_enrich=1)
    atts = res["ledger"]["attempts"]
    assert len(atts) == 1
    a = atts[0]
    assert (a["outcome"] == "ENRICHED_GROUNDED"
            or a["outcome"].startswith("STILL_UNGROUNDED")
            or a["outcome"].startswith("RETRIEVAL_FAILED")), (
        "the outcome is one of the three typed classes (the "
        "parenthetical detail may follow)")
    # zero silent outcomes: every attempt carries retrieval status
    assert a.get("retrieval_status")
    assert "candidate_id" in a
    # the hypothesis is never left unlabeled
    c = ungrounded[0]
    assert c["candidate_lifecycle"] in ("HELD_UNGROUNDED",
                                        "EVIDENCE_GROUNDED_CANDIDATE_"
                                        "ENRICHED")
    # the ledger persisted (typed record, Art. 4)
    led_file = td / "ENRICHMENT_LEDGER.json"
    if a["outcome"] != "RETRIEVAL_FAILED" or True:
        assert led_file.exists() or res["ledger"].get("persist_error")


def test_enriched_grounded_joins_pool():
    """A hypothesis the enrichment grounds (via a monkeypatched
    retrieval arm carrying a REAL matching record with correct id +
    hash) becomes admissible through the executor itself."""
    import hashlib
    from discovery_fabric.engine import evolution as ev
    text = ("Ultrasonic antifouling vibration suppresses marine "
            "growth accumulation on ship hull plates.")
    h = hashlib.sha256(text.encode()).hexdigest()
    fresh = {"status": "OK", "query": "ultrasonic antifouling hull",
             "n_items": 1, "items": [{
                 "id": "doi:10.1007/test-enrich",
                 "title": "Ultrasonic antifouling",
                 "abstract": text, "content_hash": h,
                 "source": "europe_pmc"}]}
    orig = ev.retrieve_fresh_evidence
    ev.retrieve_fresh_evidence = lambda *a, **k: fresh
    try:
        td = Path(tempfile.mkdtemp())
        problem = {"device": "ship hull", "failure": "fouling",
                   "problem_id": "t-enrich-2"}
        ung = [_ungrounded("u-enrich-2")]
        ung[0]["mechanism"] = (
            "ultrasonic antifouling vibration suppresses marine "
            "growth accumulation on ship hull plates")
        res = enrich_ungrounded_hypotheses(problem, ung, td,
                                           max_enrich=1)
        assert res["enriched"], "the enriched hypothesis must join"
        c = res["enriched"][0]
        assert c["candidate_lifecycle"] == (
            "EVIDENCE_GROUNDED_CANDIDATE_ENRICHED")
        assert c["discovery_admissible"] is True
        b = c["admission_basis"]["binding"]
        assert b["evidence_id"] == "doi:10.1007/test-enrich"
        assert b["content_hash"] == h  # the record's REAL hash
        # and the same function's output feeds the pool gate cleanly
        adm, ung2 = ms_pool_admission_split(res["enriched"])
        assert len(adm) == 1
    finally:
        ev.retrieve_fresh_evidence = orig


def test_retrieval_failure_types_infrastructure():
    """A retrieval exception types as INFRASTRUCTURE (Art. 15) — never
    silently converted into evidence absence or a novelty claim."""
    from discovery_fabric.engine import evolution as ev
    def _boom(*a, **k):
        raise ConnectionError("network unreachable")
    orig = ev.retrieve_fresh_evidence
    ev.retrieve_fresh_evidence = _boom
    try:
        td = Path(tempfile.mkdtemp())
        res = enrich_ungrounded_hypotheses(
            {"device": "x", "failure": "y", "problem_id": "t3"},
            [_ungrounded("u3")], td, max_enrich=1)
        a = res["ledger"]["attempts"][0]
        assert a["outcome"].startswith("RETRIEVAL_FAILED")
        assert a["failure_class"].startswith("INFRASTRUCTURE")
        assert res["ledger"]["n_enriched_grounded"] == 0
    finally:
        ev.retrieve_fresh_evidence = orig
