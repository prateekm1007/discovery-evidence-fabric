"""R6 two-turn integrity tests (owner directive 2026-11-11, item 5).

The measured R5 defect: the round-1 pipeline/baseline arms consumed the
problem dict WITH followup_finding attached, so round 1 already
ingested the user's follow-up — the "learning" measured in round 2 was
pre-seeded (the leak). The fix: every round-1 arm consumes the problem
through eval.run._round1_problem; ONLY the round-2 child (env
EVAL_ROUND2_INTAKE=1) keeps the finding.

Token test: a distinctive token placed in followup_finding must NEVER
appear in any round-1 intake surface (constraint, user_variables,
followup_text), and MUST appear in the round-2 intake.

Hard timeout: _spawn_child must kill an oversleeping child and report
timed_out=True (the round-2 engine's wall-clock bound).
"""
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

TOKEN = "XTOKEN9Q-FINDING-MARKER"
FINDING = (f"Bolt-loosening audit found the bearing housing bolts at 60 "
           f"percent of specified torque ({TOKEN}).")


def _problem():
    return {
        "problem_id": "two_turn_test_case",
        "device": "test device",
        "failure": "test failure",
        "failure_mode": "degradation",
        "constraint": "maintain 1.0 kW output",
        "domain": "test-domain",
        "question_type": "intervention-proposal",
        "question": "What engineering change would prevent the failure?",
        "user_variables": ["maintain 1.0 kW output"],
        "followup_finding": FINDING,
    }


def _fresh_eval():
    import eval.run as er
    importlib.reload(er)
    return er


def test_round1_intake_has_no_finding_token():
    er = _fresh_eval()
    os.environ.pop("EVAL_ROUND2_INTAKE", None)
    q = er._intake_problem(er._round1_problem(_problem()))
    blob = " ".join([str(q.get("constraint") or ""),
                     " ".join(q.get("user_variables") or []),
                     str(q.get("followup_text") or "")])
    assert TOKEN not in blob, "round-1 intake leaked the finding token"
    assert "followup_text" not in q or not q.get("followup_text")
    # the problem constraint itself survives the strip
    assert "maintain 1.0 kW output" in str(q.get("constraint"))


def test_round2_intake_keeps_finding_token():
    er = _fresh_eval()
    os.environ["EVAL_ROUND2_INTAKE"] = "1"
    try:
        q = er._intake_problem(er._round1_problem(_problem()))
        blob = " ".join([str(q.get("constraint") or ""),
                         " ".join(q.get("user_variables") or []),
                         str(q.get("followup_text") or "")])
        assert TOKEN in blob, "round-2 intake lost the finding token"
        assert "user finding:" in " ".join(q.get("user_variables") or [])
    finally:
        os.environ.pop("EVAL_ROUND2_INTAKE", None)


def test_baseline_round1_view_is_stripped():
    er = _fresh_eval()
    os.environ.pop("EVAL_ROUND2_INTAKE", None)
    q = er._intake_problem(er._round1_problem(_problem()))
    assert all(TOKEN not in str(v) for v in q.get("user_variables") or [])


def test_spawn_child_enforces_hard_timeout():
    er = _fresh_eval()
    res = er._spawn_child([sys.executable, "-c", "import time; time.sleep(30)"],
                          timeout_s=2)
    assert res["timed_out"] is True, res
    assert res["wall_s"] < 25, res  # killed well before the 30 s sleep ends


def test_spawn_child_reports_clean_exit():
    er = _fresh_eval()
    res = er._spawn_child([sys.executable, "-c", "pass"], timeout_s=30)
    assert res["timed_out"] is False and res["returncode"] == 0, res
