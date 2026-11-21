#!/usr/bin/env python3
"""test_r115_gerund_guard.py — the VF-R114-2 acceptance tests (R115
dir 4, c-0164): the direct-gerund consequence chain must be EXCLUDED
as mechanism description when agent-less, agent-ful proposed
interventions must STAY violations, predictors stay exempt, and the
REAL burned HO15-03/05 rows must keep their 2.2.0 direction scores
(the rescore record's unchanged-rows clause, baked into CI)."""
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import invention_rubric as ir  # noqa


def _dir(problem, answer):
    r = ir.score_answer(problem, answer)
    scores = r[0]["scores"] if isinstance(r, tuple) else r["scores"]
    return scores["direction_correctness"]


P_INT = {"question_type": "intervention-proposal",
         "failure": "elongation increases raising breaks",
         "question": "intervene on the paste rheology"}
P_PRED = {"question_type": "predictor-design",
          "failure": "current rises above the trip band",
          "question": "design a leading indicator"}
P_BAD = {"question_type": "intervention-proposal",
         "failure": "residual oligomer",
         "question": "reduce residual oligomer"}


def test_adversarial_direct_gerund_is_excluded():
    """VF-R114-2 itself: 'increases raising breaks' with no comma, no
    agent signal — mechanism description, NOT a violation (>=2)."""
    ans = ("The failure mechanism is clear: elongation increases "
           "raising breaks in the web during speed ramp.")
    assert _dir(P_INT, ans) >= 2


def test_agentful_gerund_stays_a_violation():
    """The asymmetric principle: a proposed intervention that raises
    the failure quantity stays a violation even with a trailing
    consequence gerund."""
    ans = ("We propose adding a filler that increases the residual "
           "oligomer content, leading to faster discoloration.")
    assert _dir(P_BAD, ans) == 1


def test_agentful_plain_violation_stays():
    ans = ("The proposed intervention raises the residual oligomer "
           "content by 40 percent.")
    assert _dir(P_BAD, ans) == 1


def test_predictor_rising_indicator_exempt():
    ans = ("The indicator detects when the current increases beyond "
           "the threshold, giving early warning before the trip.")
    assert _dir(P_PRED, ans) == 2


def test_real_burned_rows_direction_unchanged():
    """The 30-row rescore must be UNCHANGED under 2.2.1: re-score the
    four formerly-flagged rows from committed bytes and compare with
    the committed r113_f92_f91_rescore.json (real rows unchanged, the
    auditor's dir-4 accept clause)."""
    rescore = json.loads(
        (REPO / "eval" / "r113_f92_f91_rescore.json").read_text())
    probs = {p["problem_id"]: p for p in json.loads(subprocess.run(
        ["git", "show",
         "origin/audit/r11-auditor-verdict-20261114:audit/holdout_v15/"
         "holdout_v15_problems.json"],
        capture_output=True, text=True, cwd=str(REPO))
        .stdout)["problems"]}
    rows_dir = REPO / "eval/holdout_v15_generation/rows"
    checked = 0
    for row_file in sorted(rows_dir.glob("*.json")):
        row = json.loads(row_file.read_text())
        pid = row["problem_id"].split("-")[0] + "-" + \
            row["problem_id"].split("-")[1]
        if pid not in ("HO15-03", "HO15-05", "HO15-10", "HO15-20"):
            continue
        recorded = rescore["flagged_four_after"].get(pid)
        if recorded is None:
            continue
        fresh = _dir(probs[row["problem_id"]], row.get("a1_answer")
                     or row.get("answer", ""))
        assert fresh == recorded["direction"], \
            f"{pid}: {recorded['direction']} -> {fresh} " \
            "(collateral shift)"
        checked += 1
    assert checked >= 3, f"only {checked} flagged rows checkable"
