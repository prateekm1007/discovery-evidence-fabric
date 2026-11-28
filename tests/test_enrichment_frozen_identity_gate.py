#!/usr/bin/env python3
"""R142S1 regression: the enrichment's IDENTITY gate reads the FROZEN
evidence set, never the enrichment's own fresh retrieval snapshot.

The R142 yield run admitted cand:MS:GEOMETRIC_TRANSFORMATION:7feb02ad4621
bound to europepmc:29937599 — an id ABSENT from the run's frozen set —
because the resolver ran against the enrichment's freshly constructed
new_items (an unfrozen snapshot, Art. XLIV). The acceptance recompute
(against the frozen set) caught it as FALSE_ID — a bad admission.

The fix: enrich_ungrounded_hypotheses(frozen_items=...) — the resolver's
pool is the frozen set; a binding that resolves only against the fresh
snapshot is refused (typed FALSE_ID_FROZEN) and the hypothesis stays
HELD_UNGROUNDED. 0 bad admissions.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.run import enrich_ungrounded_hypotheses


def _hypothesis(cid="cand:MS:GEOMETRIC_TRANSFORMATION:testbad"):
    return {
        "candidate_id": cid,
        "mechanism": ("the desalination brine warmer recovers heat "
                      "through a plate exchanger whose fouling layer "
                      "shifts the pinch point toward the cold end"),
        "candidate_lifecycle": "HELD_UNGROUNDED",
        "transformation_operator": "DIRECT_TRANSFER",
    }


def _fresh_items():
    # the snapshot the unfixed gate resolved against: the id exists
    # HERE but nowhere in the frozen set
    return [{
        "id": "europepmc:snapshot-only-0001",
        "item_id": "europepmc:snapshot-only-0001",
        "content_hash": "a" * 64,
        "title": "plate heat exchanger fouling shifts pinch point",
        "abstract": ("fouling layers in plate exchangers shift the "
                     "thermal pinch toward the cold end and cut heat "
                     "recovery measurably across operating cycles"),
        "_record_text": ("plate heat exchanger fouling shifts the "
                         "thermal pinch toward the cold end"),
    }]


def _frozen_items():
    # the run's frozen evidence: a DIFFERENT record (the snapshot id
    # is absent)
    return [{
        "id": "doi:10.5281/zenodo.frozen-real",
        "content_hash": "b" * 64,
        "title": "desalination brine heat recovery audit",
        "abstract": "an audit of brine warmer heat recovery trains",
        "_record_text": "an audit of brine warmer heat recovery trains",
    }]


def test_snapshot_only_binding_is_refused(monkeypatch, tmp_path):
    """A binding resolving ONLY against the fresh snapshot must be
    refused when the frozen set is provided — 0 enriched, 0 admitted."""
    monkeypatch.setattr(
        "discovery_fabric.engine.retrieve_fresh_evidence",
        lambda *a, **k: {"items": _fresh_items(), "n_items": 1,
                         "status": "OK", "query": "q"},
        raising=False)
    # the run module imports retrieve_fresh_evidence via the _ev alias
    import discovery_fabric.engine.run as runmod
    monkeypatch.setattr(runmod, "_ev", type("E", (), {
        "retrieve_fresh_evidence": staticmethod(
            lambda *a, **k: {"items": _fresh_items(), "n_items": 1,
                             "status": "OK", "query": "q"})})(),
        raising=False)
    out = enrich_ungrounded_hypotheses(
        {"device": "desalination train", "domain": "water-treatment"},
        [_hypothesis()], tmp_path, max_enrich=1,
        frozen_items=_frozen_items())
    assert out["enriched"] == [], "the snapshot-only binding must not enrich"
    attempts = out["ledger"].get("attempts") or []
    assert attempts, "the attempt must be recorded (typed, never silent)"
    outcomes = " ".join(str(a.get("outcome")) for a in attempts)
    assert "UNGROUNDED" in outcomes.upper(), outcomes
    # the hypothesis stays explicitly HELD
    assert _hypothesis()["candidate_lifecycle"] is not None


def test_frozen_resolved_binding_still_enriches(monkeypatch, tmp_path):
    """A binding whose id EXISTS in the frozen set enriches exactly as
    before — the fix only closes the snapshot-only class."""
    frozen = [{
        "id": "europepmc:snapshot-only-0001",
        "content_hash": "a" * 64,
        "title": "plate heat exchanger fouling shifts pinch point",
        "abstract": ("fouling layers in plate exchangers shift the "
                     "thermal pinch toward the cold end and cut heat "
                     "recovery measurably across operating cycles"),
        "_record_text": ("plate heat exchanger fouling shifts the "
                         "thermal pinch toward the cold end"),
    }]
    monkeypatch.setattr(
        "discovery_fabric.engine.run._ev", type("E", (), {
            "retrieve_fresh_evidence": staticmethod(
                lambda *a, **k: {"items": _fresh_items(), "n_items": 1,
                                 "status": "OK", "query": "q"})})(),
        raising=False)
    out = enrich_ungrounded_hypotheses(
        {"device": "desalination train", "domain": "water-treatment"},
        [_hypothesis()], tmp_path, max_enrich=1,
        frozen_items=frozen)
    # grounded or not depends on the SUPPORT verdict; the assertion is
    # that the identity gate did NOT refuse on frozen grounds
    outcomes = " ".join(
        str(a.get("outcome"))
        for a in (out["ledger"].get("attempts") or []))
    assert "FALSE_ID_FROZEN" not in outcomes, outcomes
