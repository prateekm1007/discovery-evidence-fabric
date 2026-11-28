"""tests/test_domain_requery.py — the R145 DIR-4 lever tests: the
domain-anchored re-query on zero support (the wind root cause)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.domain_requery import (
    anchored_query, exclude_math, zero_support_requery)

PROB = {
    "device": "onshore wind turbine (4 MW, 150 m rotor, IEC class I)",
    "failure_mode": "blade leading-edge erosion",
    "problem": "Wind blade leading-edge erosion from rain and "
               "particulate impact degrades rotor aerodynamics.",
}


def test_anchored_query_forces_family_anchors():
    v = anchored_query(PROB, "abrasion_erosion")
    assert v is not None
    assert "erosion" in v["failure_mode"]       # the family anchor
    assert "onshore wind turbine" in v["device"]  # the device head
    # the parenthetical spec clutter is cut from the device head
    assert "4 MW" not in v["device"]


def test_no_family_no_requery_view():
    assert anchored_query(PROB, None) is None
    assert anchored_query(PROB, "unknown_family") is None


def test_math_exclusion_for_engineering_problems():
    recs = [
        {"id": "m1", "title": "Sasakian Geometry and Einstein "
                              "Metrics on Spheres"},
        {"id": "m2", "title": "Noether's Theorem in Multisymplectic "
                              "Geometry"},
        {"id": "ok", "title": "Rain erosion of wind turbine blade "
                              "leading-edge coatings"},
    ]
    kept, excluded = exclude_math(recs, PROB)
    assert [r["id"] for r in kept] == ["ok"]
    assert {e["id"] for e in excluded} == {"m1", "m2"}
    assert all(e["reason"] == "REQUERY_EXCLUDED_MATH"
               for e in excluded)


def test_math_exclusion_silent_for_non_engineering():
    recs = [{"id": "m1", "title": "Sasakian Geometry"}]
    kept, excluded = exclude_math(
        recs, {"device": "calabi-yau space", "failure_mode": ""})
    assert len(kept) == 1 and not excluded


class _Env:
    """The minimal env shape: classification with zero support."""
    def __init__(self, items):
        self.evidence_classification = {
            "items": items, "counts": {
                "DIRECT_SUPPORT": 0, "PARTIAL_SUPPORT": 0,
                "BACKGROUND": 0, "ANALOGY": 5, "CONTRADICTORY": 0,
                "IRRELEVANT": 7}}
        self.evidence = []
        self.mechanism_map = {}


def test_no_requery_when_support_exists(monkeypatch):
    env = _Env([{"source_id": "x",
                 "classification": "DIRECT_SUPPORT"}])
    called = []
    monkeypatch.setattr(
        "discovery_fabric.retrieval_fabric.pipeline.retrieve_fabric",
        lambda v: called.append(v) or ([], {}))
    out = zero_support_requery(env, PROB, "abrasion_erosion")
    assert out is None and not called


def test_requery_classifies_fresh_records(monkeypatch):
    env = _Env([])
    fresh = [{"id": "w1", "title": "Rain erosion of wind turbine "
                                   "blade leading-edge coatings",
              "abstract": "Leading edge protection coatings "
                          "against rain erosion on wind turbine "
                          "blades; erosion wear of the blade "
                          "surface measured.",
              "source": "arxiv", "content_hash": "h1"}]
    monkeypatch.setattr(
        "discovery_fabric.retrieval_fabric.pipeline.retrieve_fabric",
        lambda v: (fresh, {"lane_states": [], "record": "test"}))
    out = zero_support_requery(env, PROB, "abrasion_erosion")
    assert out["state"] == "RUN"
    assert out["n_fresh_records"] == 1
    assert out["n_promoted"] >= 1
    assert "w1" in out["promoted_ids"]


def test_retrieve_boundary_math_filter_is_typed():
    """R145 DIR-4: the RETRIEVE adapter's V2 branch applies the math
    exclusion at the boundary — the source text pins the wiring (the
    filter + the typed provenance field)."""
    from pathlib import Path
    src = Path(REPO / "discovery_fabric/engine/adapters.py").read_text()
    assert "RETRIEVE_MATH_EXCLUDED" in src
    assert "exclude_math(items, env.problem" in src
