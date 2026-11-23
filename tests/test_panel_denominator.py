#!/usr/bin/env python3
"""tests/test_panel_denominator.py — the R136 denominator + guard
fixes (the verifier's findings, now pinned as CI):

1. The answered-rate denominator is the EXPECTED leg count
   (2 x distinct pids across the whole judge_rows), never the
   legs-present count: a judge whose legs are missing on disk
   FAILS the 0.9 answered bar.
2. swap_robust_panel refuses to report panel agreement below 2
   distinct qualified judges (a single judge's label agreement is
   its own accuracy, not a panel property).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.panel_agreement import (  # noqa: E402
    rcal_qualification, swap_robust_panel)


def _leg(pid, order, pass_, a_is, outcome="VALID", prefer="A"):
    return {"pid": pid, "order": order, "pass": pass_, "a_is": a_is,
            "outcome": outcome,
            "parsed": {"prefer": prefer,
                       "axes": {"N_A": 3, "F_A": 3, "T_A": 3, "C_A": 3,
                                "N_B": 2, "F_B": 3, "T_B": 3, "C_B": 3}}
            if outcome == "VALID" else None}


PIDS = [f"p{i}" for i in range(10)]
LABELS = {p: "a1" for p in PIDS}


def test_missing_legs_fail_the_answered_bar():
    """THE partial-run fixture: full-judge has 20 VALID legs;
    missing-judge has only 4 on disk — under the OLD legs-present
    denominator its answered_rate was 4/4 = 1.0 (unfailable by
    omission); under the R136 EXPECTED denominator it is 4/20 =
    0.2 and it MUST fail the 0.9 bar."""
    judge_rows = {
        "full": [_leg(p, "a1_first", "det", "a1")
                 for p in PIDS]
                + [_leg(p, "a1_first", "mir", "baseline")
                   for p in PIDS],
        "missing": [_leg(p, "a1_first", "det", "a1")
                   for p in PIDS[:2]],
    }
    q = rcal_qualification(judge_rows, LABELS)
    # the expected denominator: 2 x 10 distinct pids = 20
    assert q["full"]["expected_legs"] == 20
    assert q["missing"]["expected_legs"] == 20, (
        "the expectation must come from the WHOLE judge_rows pid "
        "set — a partial judge inherits the full expectation")
    assert q["full"]["answered_rate"] == 1.0
    assert q["missing"]["answered_rate"] <= 0.25, (
        f"the missing-legs judge answered_rate "
        f"{q['missing']['answered_rate']} — the R136 fix requires "
        "the EXPECTED denominator (the verifier's finding)")
    assert q["missing"]["qualified"] is False, (
        "a judge with 4/20 legs on disk MUST fail the answered bar")
    assert q["full"]["qualified"] is True


def test_explicit_expected_legs_pin():
    """An explicit expected_legs pins the denominator (the corpus
    owner's form: 10 pairs => 20 legs, even if a whole judge is
    absent from judge_rows)."""
    judge_rows = {
        "half": [_leg(p, "a1_first", "det", "a1") for p in PIDS],
    }
    q = rcal_qualification(judge_rows, LABELS, expected_legs=20)
    assert q["half"]["expected_legs"] == 20
    assert q["half"]["answered_rate"] == 0.5
    assert q["half"]["qualified"] is False


def test_panel_agreement_guard_below_two_judges():
    """The R136 guard: 1 qualified judge => a TYPED REFUSAL, no
    panel-agreement number (never a silent single-judge
    'agreement')."""
    judge_rows = {
        "solo": [_leg(p, "a1_first", "det", "a1") for p in PIDS]
                + [_leg(p, "a1_first", "mir", "baseline")
                   for p in PIDS],
    }
    r = swap_robust_panel(judge_rows, ["solo"], LABELS)
    assert r["panel_agreement"] is None, (
        "panel agreement must NOT be computed below 2 qualified "
        "judges")
    assert "TYPED REFUSAL" in r["guard"]
    assert r["agreement_ge_bar"] is False


def test_panel_agreement_computes_at_two_judges():
    """The guard passes at exactly 2 distinct qualified judges (the
    agreement number is computed and honest)."""
    judge_rows = {
        "a": [_leg(p, "a1_first", "det", "a1") for p in PIDS]
             + [_leg(p, "a1_first", "mir", "baseline")
                for p in PIDS],
        "b": [_leg(p, "a1_first", "det", "a1") for p in PIDS]
             + [_leg(p, "a1_first", "mir", "baseline")
                for p in PIDS],
    }
    r = swap_robust_panel(judge_rows, ["a", "b"], LABELS)
    assert r["panel_agreement"] == 1.0, (
        "two identical perfect judges: agreement 1.0 (the guard "
        "does not block honest computation)")
    assert "guard" not in r or "TYPED REFUSAL" not in str(
        r.get("guard", ""))
