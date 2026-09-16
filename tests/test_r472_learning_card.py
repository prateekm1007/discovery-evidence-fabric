"""R472 — the no-survivor LEARNING CARD (audit Top-10 #4 / P0-4, the
30-day roadmap item: "Turn MECHANISM_GENERATION_FAILED into a useful
learning and next-action experience"; acceptance: "A terminal
no-mechanism card shows searched territory, strongest failed
hypothesis, key missing evidence, and 2-3 ranked next actions").

The honest-refusal terminal is PRODUCT-CORRECT (zero fabricated
packages — the standing mission); the audit's demand is that it also
TEACH: what was tested, what failed or remained unknown, and the
smallest next action that could change the result.

These contracts pin:
  1. the card fires ONLY for terminal scientific no-survivor runs —
     never for live runs, premise-incoherent runs (nothing was
     searched), infrastructure blocks (not science), or runs with a
     package/verified survivor;
  2. the four audit-named fields, derived from RECORDED data only;
  3. the honesty floor: absent facts are labeled absent, never
     fabricated (a card with no lineage says so; missing evidence
     says what is recorded);
  4. the ranked actions: 2-3 typed, contiguous ranks, kinds that map
     to real product affordances, no outcome promises;
  5. the user_state_view wiring (the card travels on the canonical
     session projection).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
from toscanini import run_state as rs  # noqa: E402
from toscanini.user_state import user_state_view  # noqa: E402


def _lineage(tmp_path: Path, generations: list, survivor=False) -> Path:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "INVENTION_LINEAGE.json").write_text(json.dumps({
        "generations": generations,
        "survivor_reached": survivor,
        "current_invention": {"gen": generations[-1]["gen"]
                              if generations else None},
    }))
    return run_dir


def _gen(gen=1, mechanism="electrochemical gradient concentration cell",
         killed=True, kill_reason="obvious_combination: KILLED",
         cause="prior art combination obvious", verified=False):
    return {"gen": gen, "mechanism": mechanism,
            "challenge": {"killed": killed, "kill_reason": kill_reason},
            "diagnosed_cause": cause, "evidence_verified": verified}


# ---------------------------------------------------------------------------
# 1. the trigger surface
# ---------------------------------------------------------------------------

def test_none_for_live_run(tmp_path):
    s = {"status": "RUNNING", "final_status": ""}
    assert rs.learning_card(s, tmp_path) is None


def test_none_for_premise_incoherent(tmp_path):
    s = {"status": "COMPLETE",
         "final_status": "MALFORMED_OR_FALSE_PREMISE",
         "reason": "premise incoherent"}
    assert rs.learning_card(s, tmp_path) is None


def test_none_for_infrastructure_block(tmp_path):
    s = {"status": "COMPLETE", "final_status": "RUN_BLOCKED_CAPABILITY",
         "reason": "route degraded"}
    assert rs.learning_card(s, tmp_path) is None


def test_none_when_survivor_reached(tmp_path):
    gens = [_gen(1, killed=True), _gen(2, killed=False, verified=True)]
    run_dir = _lineage(tmp_path, gens, survivor=True)
    s = {"status": "COMPLETE", "final_status": "INVENTION_UNDER_DEVELOPMENT"}
    assert rs.learning_card(s, run_dir) is None


def test_fires_for_killed_lineage_no_survivor(tmp_path):
    gens = [_gen(1), _gen(2)]
    run_dir = _lineage(tmp_path, gens, survivor=False)
    s = {"status": "COMPLETE", "final_status": "INVENTION_KILLED_BY_CHALLENGE",
         "failed_stages": {}, "reason": "challenge killed all"}
    card = rs.learning_card(s, run_dir)
    assert card is not None and card["kind"] == "no_survivor_learning_card"


def test_fires_for_generation_failed_without_lineage(tmp_path):
    run_dir = tmp_path / "empty_run"
    run_dir.mkdir()
    s = {"status": "COMPLETE",
         "final_status": "MECHANISM_GENERATION_FAILED",
         "failed_stages": {"SYNTHESIZE": "no mechanism survived gates"},
         "reason": "synthesis failed before any candidate existed"}
    card = rs.learning_card(s, run_dir)
    assert card is not None


# ---------------------------------------------------------------------------
# 2. the four audit-named fields, recorded-data-only
# ---------------------------------------------------------------------------

def test_card_fields_killed_lineage(tmp_path):
    gens = [_gen(1, mechanism="mechanism A"),
            _gen(2, mechanism="mechanism B",
                 kill_reason="novelty: KILLED — combination anticipated")]
    run_dir = _lineage(tmp_path, gens, survivor=False)
    s = {"status": "COMPLETE", "final_status": "INVENTION_KILLED_BY_CHALLENGE",
         "failed_stages": {}, "reason": "killed"}
    card = rs.learning_card(s, run_dir)
    # searched territory: names the generations explored
    assert "2" in card["what_was_tested"]
    # strongest failed hypothesis: the LAST genuine kill's mechanism + reason
    assert "mechanism B" in card["strongest_failed_hypothesis"]
    assert "novelty" in card["strongest_failed_hypothesis"].lower()
    # key missing evidence: derived from the recorded state
    assert isinstance(card["key_missing_evidence"], str)
    assert card["key_missing_evidence"]
    # the trust line names the derivation basis
    assert "lineage" in card["basis"].lower()


def test_card_honest_when_no_lineage(tmp_path):
    run_dir = tmp_path / "empty_run"
    run_dir.mkdir()
    s = {"status": "COMPLETE",
         "final_status": "MECHANISM_GENERATION_FAILED",
         "failed_stages": {"SYNTHESIZE": "gate: no causal mechanism"},
         "reason": "synthesis failed"}
    card = rs.learning_card(s, run_dir)
    # the card says the search reached synthesis and produced no
    # candidate — it NEVER claims a rejection that did not happen
    wt = card["what_was_tested"].lower()
    assert "synthesis" in wt or "no candidate" in wt or "no mechanism" in wt
    sfh = card["strongest_failed_hypothesis"].lower()
    assert "no causal mechanism" in sfh or "synthesis" in sfh
    assert "rejected" not in sfh.replace("not rejected", "")


# ---------------------------------------------------------------------------
# 3. the honesty floor
# ---------------------------------------------------------------------------

def test_missing_evidence_honest_when_nothing_recorded(tmp_path):
    gens = [_gen(1)]
    run_dir = _lineage(tmp_path, gens, survivor=False)
    s = {"status": "COMPLETE", "final_status": "INVENTION_KILLED_BY_CHALLENGE",
         "failed_stages": {}, "reason": ""}
    card = rs.learning_card(s, run_dir)
    # the honest line: the records do not name a specific missing input
    assert isinstance(card["key_missing_evidence"], str)
    assert card["key_missing_evidence"]  # present, not empty


def test_evidence_unverified_surfaces_in_missing_evidence(tmp_path):
    gens = [_gen(1, verified=False)]
    run_dir = _lineage(tmp_path, gens, survivor=False)
    s = {"status": "COMPLETE", "final_status": "INVENTION_KILLED_BY_CHALLENGE",
         "failed_stages": {}, "reason": "killed"}
    card = rs.learning_card(s, run_dir)
    assert "evidence" in card["key_missing_evidence"].lower()


# ---------------------------------------------------------------------------
# 4. the ranked actions
# ---------------------------------------------------------------------------

def test_actions_typed_ranked_and_bounded(tmp_path):
    gens = [_gen(1), _gen(2)]
    run_dir = _lineage(tmp_path, gens, survivor=False)
    s = {"status": "COMPLETE", "final_status": "INVENTION_KILLED_BY_CHALLENGE",
         "failed_stages": {}, "reason": "killed"}
    actions = rs.learning_card(s, run_dir)["ranked_next_actions"]
    assert 2 <= len(actions) <= 3
    assert [a["rank"] for a in actions] == list(range(1, len(actions) + 1))
    kinds = set()
    for a in actions:
        assert a["action_kind"] in ("ADD_EVIDENCE", "REFINE_PROBLEM",
                                    "NEW_TERRITORY")
        assert a["action"] and a["why"]
        kinds.add(a["action_kind"])
    # distinct affordances — the same action is never listed twice
    assert len(kinds) == len(actions)


def test_actions_never_promise_an_outcome(tmp_path):
    gens = [_gen(1)]
    run_dir = _lineage(tmp_path, gens, survivor=False)
    s = {"status": "COMPLETE", "final_status": "INVENTION_KILLED_BY_CHALLENGE",
         "failed_stages": {}, "reason": "killed"}
    card = rs.learning_card(s, run_dir)
    for a in card["ranked_next_actions"]:
        blob = (a["action"] + " " + a["why"]).lower()
        for promise in ("will survive", "will succeed", "guarantee",
                        "will produce", "will find"):
            assert promise not in blob


# ---------------------------------------------------------------------------
# 5. the user_state_view wiring
# ---------------------------------------------------------------------------

def test_user_state_view_carries_the_card(tmp_path):
    gens = [_gen(1)]
    run_dir = _lineage(tmp_path, gens, survivor=False)
    s = {"status": "COMPLETE", "final_status": "INVENTION_KILLED_BY_CHALLENGE",
         "failed_stages": {}, "reason": "killed",
         "run_dir": str(run_dir)}
    view = user_state_view(s)
    assert view.get("learning_card") is not None
    assert view["learning_card"]["kind"] == "no_survivor_learning_card"


def test_user_state_view_card_absent_for_found_runs(tmp_path):
    s = {"status": "COMPLETE",
         "final_status": "AUTOMATED_INVENTION_CANDIDATE",
         "package": {"complete": True}}
    view = user_state_view(s)
    assert view.get("learning_card") is None
