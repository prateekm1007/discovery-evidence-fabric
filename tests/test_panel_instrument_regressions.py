#!/usr/bin/env python3
"""tests/test_panel_instrument_regressions.py — the R137
regression battery for the panel instrument (the coder
directions' items 2.4 and 2.6, audited base 7caddfaa3).

Part 1 — the denominator edge cases:
  a problem missing across every judge; an entirely absent judge;
  a partially completed judge; the <2-qualified agreement refusal.

Part 2 — the prompt regression tests:
  the v1 prompt stays byte-identical to the audited commit's own
  output (the golden file, generated FROM 7caddfaa3's bytes); v2
  adds ONLY the user's constraint line; the exact constraint text
  reaches the judge; a missing constraint cannot silently become
  a successful v2 input.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.panel_agreement import (  # noqa: E402
    rcal_qualification, swap_robust_panel)
from discovery_fabric.engine.blind_panel import (  # noqa: E402
    build_pair_prompt)

GOLDEN = REPO / "tests" / "golden" / "panel_prompt_v1_golden.json"


def _leg(pid, order, pass_, a_is, outcome="VALID", prefer="A"):
    return {"pid": pid, "order": order, "pass": pass_,
            "a_is": a_is, "outcome": outcome,
            "parsed": {"prefer": prefer} if outcome == "VALID"
            else None}


# ---------------------------------------------------------------------------
# Part 1 — the denominator edge cases
# ---------------------------------------------------------------------------

PIDS = [f"p{i}" for i in range(10)]
LABELS = {p: "a1" for p in PIDS}


def test_problem_missing_across_every_judge():
    """A problem with no legs ANYWHERE still counts toward the
    expectation: expected stays 2 x 10 = 20 and every judge's
    answered rate is penalized for the un-run pair."""
    judge_rows = {
        "a": ([_leg(p, "det", "det", "a1") for p in PIDS[:9]]
              + [_leg(p, "mir", "mir", "baseline")
                 for p in PIDS[:9]]),
    }
    q = rcal_qualification(judge_rows, LABELS, expected_legs=20)
    # 18 valid legs of 20 expected -> 0.9 exactly, qualified only
    # if acc also holds (it does: all vote a1 = the label)
    assert q["a"]["expected_legs"] == 20
    assert q["a"]["valid"] == 18
    assert abs(q["a"]["answered_rate"] - 0.9) < 1e-9
    assert q["a"]["n_cmp"] == 9  # the missing pid is not compared


def test_entirely_absent_judge():
    """An absent judge scores 0/20 (or 0 over the inferred
    expectation), is NOT qualified, and never disappears."""
    judge_rows = {
        "present": ([_leg(p, "det", "det", "a1") for p in PIDS]
                    + [_leg(p, "mir", "mir", "baseline")
                       for p in PIDS]),
        "absent": [],
    }
    q = rcal_qualification(judge_rows, LABELS, expected_legs=20)
    assert "absent" in q, "the absent judge must be represented"
    assert q["absent"]["expected_legs"] == 20
    assert q["absent"]["valid"] == 0
    assert q["absent"]["answered_rate"] == 0.0
    assert q["absent"]["qualified"] is False
    assert q["present"]["answered_rate"] == 1.0
    assert q["present"]["qualified"] is True


def test_partial_judge():
    """A half-completed judge: 10 valid of 20 expected -> 0.5,
    below the 0.9 bar, NOT qualified even at perfect accuracy."""
    judge_rows = {
        "half": [_leg(p, "det", "det", "a1") for p in PIDS],
    }
    q = rcal_qualification(judge_rows, LABELS, expected_legs=20)
    assert q["half"]["expected_legs"] == 20
    assert q["half"]["answered_rate"] == 0.5
    assert q["half"]["acc_vs_labels"] == 1.0
    assert q["half"]["qualified"] is False, (
        "perfect accuracy must not rescue an unanswered half")


def test_agreement_refusal_below_two():
    """swap_robust_panel refuses (typed) below 2 qualified judges;
    it computes honestly at exactly 2."""
    solo = {"solo": [_leg(p, "det", "det", "a1") for p in PIDS]
            + [_leg(p, "mir", "mir", "baseline") for p in PIDS]}
    r = swap_robust_panel(solo, ["solo"], LABELS)
    assert r["panel_agreement"] is None
    assert "TYPED REFUSAL" in r["guard"]
    duo = dict(solo)
    duo["duo"] = list(solo["solo"])
    r2 = swap_robust_panel(duo, ["solo", "duo"], LABELS)
    assert r2["panel_agreement"] == 1.0


# ---------------------------------------------------------------------------
# Part 2 — the prompt regression tests
# ---------------------------------------------------------------------------

def _golden_cases():
    return json.loads(GOLDEN.read_text())["cases"]


def test_v1_prompt_byte_identical_to_audited_commit():
    """The v1 arm (default) must produce EXACTLY the audited
    commit 7caddfaa3's bytes for every golden case."""
    for c in _golden_cases():
        got = build_pair_prompt(c["problem"], "ANSWER-A BYTES",
                                "ANSWER-B BYTES", cot=c["cot"])
        assert got == c["v1_prompt"], (
            f"v1 prompt bytes drifted for {c['case']} — the "
            "baseline arm is frozen")


def test_v2_adds_only_the_constraint_line():
    """v2 = v1 + exactly ONE new line (the USER'S CONSTRAINT
    line) — nothing else may change."""
    for c in _golden_cases():
        prob = dict(c["problem"])
        if not prob.get("constraint"):
            continue
        v1 = build_pair_prompt(prob, "ANSWER-A BYTES",
                               "ANSWER-B BYTES", cot=c["cot"])
        v2 = build_pair_prompt(prob, "ANSWER-A BYTES",
                               "ANSWER-B BYTES", cot=c["cot"],
                               show_constraint=True)
        line = (f"USER'S CONSTRAINT (a stated requirement every "
                f"answer must respect): {prob['constraint']}")
        assert line in v2, f"{c['case']}: the constraint line missing"
        assert v2.replace(line + "\n", "", 1) == v1, (
            f"{c['case']}: v2 changed MORE than the constraint "
            "line")


def test_exact_constraint_reaches_the_judge():
    """The constraint VALUE (verbatim, full text) reaches the
    judge — not a paraphrase, not a truncation."""
    constraint = ("achieve 15-year float service life at 2.27 V "
                  "per cell continuously at 35 C ambient")
    prob = {"device": "battery", "failure": "corrosion",
            "question": "how?", "constraint": constraint}
    v2 = build_pair_prompt(prob, "A", "B", show_constraint=True)
    assert constraint in v2
    # and v1 (default) still hides it
    v1 = build_pair_prompt(prob, "A", "B")
    assert constraint not in v1


def test_missing_constraint_cannot_silently_succeed():
    """A problem with NO constraint field: v2 must not fabricate
    a constraint line (no empty/marker line appears), and the v2
    prompt equals the v1 prompt byte-for-byte in that case."""
    prob = {"device": "MEMS accelerometer", "failure": "stiction",
            "question": "How to prevent in-field stiction?"}
    assert not prob.get("constraint")
    v1 = build_pair_prompt(prob, "A", "B", cot=True)
    v2 = build_pair_prompt(prob, "A", "B", cot=True,
                           show_constraint=True)
    assert v2 == v1, (
        "show_constraint=True on a constraint-less problem must "
        "be a no-op — a silent placeholder line would leak the "
        "arm to the judge")
    assert "USER'S CONSTRAINT" not in v2
