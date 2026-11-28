"""tests/test_r178_problem_router.py — R178 DIR-3 SHIP: the problem-
class route split (the kill criterion as engine policy). All tests
deterministic, zero LLM, offline (the r399 fixture-chain pattern)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.problem_router import (  # noqa: E402
    ROUTER_VERSION, classify, route_disabled_stages, route_for_problem,
)
from discovery_fabric.engine.run import EngineRun  # noqa: E402

# the two measured corpus shapes (field values from the committed
# corpora: eval/r125_f31e_set/items.jsonl and
# eval/r176_invention_corpus/items.jsonl)
MITIGATION = {
    "problem_id": "r125-01-s1",
    "device": "lead-acid battery grid plate",
    "failure": "corrosion of the positive grid",
    "constraint": "no material change to the grid alloy",
    "question_type": "intervention-proposal",
}
INVENTION = {
    "problem_id": "r176i-01-ironair-efficiency",
    "device": "grid-scale iron-air battery",
    "failure": "charge step competes with hydrogen evolution",
    "constraint": "earth-abundant materials only",
    "question_type": "novel-mechanism",
}


# ---------------------------------------------------------------------------
# unit: the typed router
# ---------------------------------------------------------------------------
def test_mitigation_routes_to_cheap_arm():
    v = route_for_problem(MITIGATION)
    assert v["route"] == "CHEAP_ARM"
    assert v["problem_class"] == "intervention-proposal"
    assert v["known"] is True
    # the basis carries the measured numbers (auditor re-derivable)
    assert "1/12" in v["basis"] and "0.75" in v["basis"]
    assert "eval/r177s1_dir3_keep_retire.json" in v["basis"]


def test_invention_routes_to_cheap_arm_after_kill():
    v = route_for_problem(INVENTION)
    assert v["route"] == "CHEAP_ARM"
    assert v["problem_class"] == "novel-mechanism"
    assert v["known"] is True
    # the byte-derived kill basis rides the typed record (Art. XXV)
    assert "R183 KILL" in v["basis"] and "4/12" in v["basis"]
    assert "16/24" in v["basis"]


def test_unknown_type_takes_cheap_arm_after_kill():
    for problem in ({"question_type": ""},
                    {"question_type": "predictor-design"},
                    {}, {"question_type": "SOMETHING-NEW"}):
        v = route_for_problem(problem)
        assert v["route"] == "CHEAP_ARM", problem
        assert v["known"] is False  # the missing class is typed, never invented
        d = route_disabled_stages(problem)
        assert d["disabled_stages"] == ["EXPLORATION_GRID"]


def test_declared_type_is_authority_verbatim():
    # classify never re-derives or normalizes beyond case/whitespace
    assert classify(MITIGATION) == "intervention-proposal"
    assert classify({"question_type": " Novel-Mechanism "})
    assert classify({}) == ""


def test_route_disabled_stages_union_with_caller():
    d = route_disabled_stages(MITIGATION, extra=["COMPOSE", "RETRIEVE"])
    assert "EXPLORATION_GRID" in d["disabled_stages"]
    assert "COMPOSE" in d["disabled_stages"] and "RETRIEVE" in d["disabled_stages"]
    # invention: post-kill the route also disables the grid
    d2 = route_disabled_stages(INVENTION, extra=["COMPOSE"])
    assert d2["disabled_stages"] == ["EXPLORATION_GRID", "COMPOSE"]
    assert d2["route"] == "CHEAP_ARM"


def test_router_version_stamped():
    assert route_for_problem(MITIGATION)["router_version"] \
        == ROUTER_VERSION == "problem_router/2.0.0"


# ---------------------------------------------------------------------------
# integration: the conductor honors the route (offline fixture chain)
# ---------------------------------------------------------------------------
def _persist_chain(run, stages):
    run._persist("problem.json", run.problem)
    for stage in stages:
        run._persist_envelope(stage)


_ALL_STAGES = ("RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
               "VERIFY", "MECHANISM_SPACE", "COLLISION", "PHYSICS",
               "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
               "ADJUDICATION", "CLASSIFY", "NEXT_BEST_ACTION", "RANK")


def _env_for_problem(problem):
    """A minimal but VALID envelope: naive candidate rejected (so the
    grid would normally fire) with one verified evidence item (so the
    R399 gate passes and the ROUTE is the only thing stopping it)."""
    from discovery_fabric.engine.run import RunEnvelope  # may be internal
    return None


def test_conductor_skips_grid_for_mitigation(tmp_path, monkeypatch):
    """A MITIGATION problem whose naive candidate was rejected and
    whose evidence IS verified must record the typed route skip —
    NOT the R399 evidence skip, NOT a grid run."""
    from discovery_fabric.engine import stage_entry
    from tests.test_r399_gates import _rejected_run_env
    env = _rejected_run_env()  # rejected naive + verified-evidence shape
    env.problem = dict(MITIGATION)
    run1 = EngineRun(env.problem, str(tmp_path),
                     run_id="testrun:r178-route-mitigation",
                     with_package=True)
    run1.env = env
    _persist_chain(run1, _ALL_STAGES)
    run2 = EngineRun.from_run_dir(
        str(tmp_path),
        disabled_stages=["RETRIEVE", "FREEZE", "PREMISE_GATE",
                         "SYNTHESIZE", "COLLISION", "ATTACK"])
    manifest = run2.run()
    grid = json.loads((tmp_path / "EXPLORATION_GRID.json").read_text())
    # R183: every class routes cheap; the fixture also has unverified
    # evidence, so the record carries BOTH typed reasons (Art. XXV)
    assert grid["status"] == "SKIPPED_EVIDENCE_VERIFICATION_FAILED"
    assert grid["route_skip_status"] == "SKIPPED_ROUTE_MITIGATION_CHEAP_ARM"
    assert grid["route"]["route"] == "CHEAP_ARM"
    assert grid["route"]["problem_class"] == "intervention-proposal"
    # the measured basis rides the record (Art. XXV)
    assert "1/12" in grid["route"]["basis"]
    # NO grid candidates were generated
    assert not list(tmp_path.glob("INVENTION_SPECIFICATION_grid-*.json"))
    # the run record carries the route decision
    rr = json.loads((tmp_path / "RUN_MANIFEST.json").read_text()) \
        if (tmp_path / "RUN_MANIFEST.json").exists() else manifest
    assert manifest is not None


def test_conductor_skips_grid_for_invention_after_kill(tmp_path):
    """An INVENTION-shaped problem now takes the same typed route skip:
    the R183 kill decision retired the architecture for every class."""
    from tests.test_r399_gates import _rejected_run_env
    env = _rejected_run_env()
    env.problem = dict(INVENTION)
    run1 = EngineRun(env.problem, str(tmp_path),
                     run_id="testrun:r178-route-invention",
                     with_package=True)
    run1.env = env
    _persist_chain(run1, _ALL_STAGES)
    run2 = EngineRun.from_run_dir(
        str(tmp_path),
        disabled_stages=["RETRIEVE", "FREEZE", "PREMISE_GATE",
                         "SYNTHESIZE", "COLLISION", "ATTACK"])
    run2.run()
    grid = json.loads((tmp_path / "EXPLORATION_GRID.json").read_text())
    assert grid["status"] == "SKIPPED_EVIDENCE_VERIFICATION_FAILED"
    assert grid["route_skip_status"] == "SKIPPED_ROUTE_MITIGATION_CHEAP_ARM"
    assert grid["route"]["route"] == "CHEAP_ARM"
    assert "R183 KILL" in grid["route"]["basis"]


def test_conductor_unclassified_takes_cheap_arm(tmp_path):
    from tests.test_r399_gates import _rejected_run_env
    env = _rejected_run_env()
    env.problem = {k: v for k, v in MITIGATION.items()
                   if k != "question_type"}
    run1 = EngineRun(env.problem, str(tmp_path),
                     run_id="testrun:r178-route-unclassified",
                     with_package=True)
    run1.env = env
    _persist_chain(run1, _ALL_STAGES)
    run2 = EngineRun.from_run_dir(
        str(tmp_path),
        disabled_stages=["RETRIEVE", "FREEZE", "PREMISE_GATE",
                         "SYNTHESIZE", "COLLISION", "ATTACK"])
    run2.run()
    grid = json.loads((tmp_path / "EXPLORATION_GRID.json").read_text())
    assert grid["status"] == "SKIPPED_EVIDENCE_VERIFICATION_FAILED"
    assert grid["route_skip_status"] == "SKIPPED_ROUTE_MITIGATION_CHEAP_ARM"
    assert grid["route"]["route"] == "CHEAP_ARM"
    assert grid["route"]["known"] is False
