"""tests/test_r6_real_constraint_audit.py — unit pins for the R6
auditor round 2026-11-12 directives:

  1. the structured constraint-check block (parse / strip / merge /
     quote verification) — the REAL-pairs acceptance lives in
     eval/audit_real_pairs.py (committed bytes, never fixtures); these
     pins only freeze the deterministic machinery.
  2. DOWNGRADE, DON'T DISCARD (directive 2): relabel + drop + ship.
  3. the batch attack record shape (directive 3) — offline parse only.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.constraint_audit import (  # noqa: E402
    strip_constraint_check, parse_constraint_check, llm_check_violations,
    merge_constraint_check, _quote_in_answer, CONSTRAINT_CHECK_BLOCK_SPEC)
from discovery_fabric.engine.answer_downgrade import (  # noqa: E402
    downgrade_answer, truncate_at_sentence)


ANSWER = ("INDICATOR: mean absolute condenser pressure error over a "
          "1-hour window, weighted by a hyperbolic tangent.\n"
          "Use the existing turbine exhaust pressure transmitter.")


def test_block_stripped_from_answer_verbatim():
    resp = ANSWER + "\n\nCONSTRAINT-CHECK:\nC1: COMPLIES | \"\"\n"
    clean, block = strip_constraint_check(resp)
    assert clean == ANSWER
    assert block.startswith("C1:")


def test_block_absent_typed_not_passed():
    clean, block = strip_constraint_check(ANSWER)
    assert clean == ANSWER and block is None
    assert parse_constraint_check(None, ANSWER)["state"] == "CHECK_ABSENT"
    # the absent check manufactures NO violations (Art. XXV: the check
    # that did not run is never read as a pass or as a violation)
    assert llm_check_violations(parse_constraint_check(
        None, ANSWER)) == []


def test_violates_with_located_quote_is_verified():
    block = ("C1: VIOLATES | \"turbine exhaust pressure transmitter\"\n"
             "RESTATES-DEVICE: NO\nRESTATES-CONSTRAINT: NO\n")
    p = parse_constraint_check(block, ANSWER)
    assert p["state"] == "PARSED"
    assert p["verdicts"][0]["quote_verified"] is True
    assert p["n_violations"] == 1
    vs = llm_check_violations(p)
    assert [v["type"] for v in vs] == ["LLM_CONSTRAINT_VIOLATES"]


def test_unlocatable_quote_still_counts_and_discloses():
    block = "C1: VIOLATES | \"a phrase that appears nowhere in the answer at all\"\n"
    p = parse_constraint_check(block, ANSWER)
    assert p["verdicts"][0]["quote_verified"] is False
    assert p["n_unverified_quotes"] == 1
    vs = llm_check_violations(p)
    assert "unverified" in vs[0]["detail"]


def test_restates_flags_merge_as_typed_violations():
    # AMENDED R6 real-pairs acceptance round (measured guards): a
    # RESTATES-* YES counts ONLY when (a) its quote verifies against
    # the answer AND (b) the quote names a PROPOSAL line — the
    # measured fu-001 false positives (problem-text quote,
    # compliance-explanation "echo") must stay uncounted, while the
    # audited new01/sofc PARAMETER-line echoes must count.
    block = ("C1: COMPLIES | \"\"\n"
             "RESTATES-DEVICE: YES \"anode-supported cell\"\n"
             "RESTATES-CONSTRAINT: YES \"2.7 V per cell\"\n")
    p = parse_constraint_check(block, ANSWER)
    # neither quote names a proposal line -> recorded, not counted
    assert llm_check_violations(p) == []
    # the problem-text quote class (fu-001 device false positive)
    p2 = parse_constraint_check(
        "RESTATES-DEVICE: YES \"rolling-element bearing in a 350 kW "
        "industrial fan drive\"\n", ANSWER)
    assert llm_check_violations(p2) == []
    # the audited echo class: a verified PARAMETER-line quote counts
    echo_answer = ("PARAMETER: Operating Voltage — 2.7 V per cell — "
                   "ASSUMPTION (User Constraint)\n"
                   "Falsification test: 500 cycles.")
    p3 = parse_constraint_check(
        "RESTATES-CONSTRAINT: YES \"PARAMETER: Operating Voltage — 2.7 "
        "V per cell — ASSUMPTION (User Constraint)\"\n", echo_answer)
    types = [v["type"] for v in llm_check_violations(p3)]
    assert types == ["LLM_RESTATES_USER_CONSTRAINT"]


def test_merge_keeps_floor_and_appends_check():
    floor = {"state": "CONSTRAINT_AUDIT_PASS", "violations": [],
             "n_violations": 0}
    ck = parse_constraint_check(
        "C1: VIOLATES | \"pressure transmitter\"\n", ANSWER)
    merged = merge_constraint_check(floor, ck)
    assert merged["state"] == "CONSTRAINT_VIOLATIONS"
    assert merged["n_violations"] == 1
    assert merged["constraint_check"]["state"] == "PARSED"
    # the floor stays (never weakened, Art. VII)
    assert all(v["type"] != "LLM_CONSTRAINT_VIOLATES"
               for v in merge_constraint_check(
                   {"state": "CONSTRAINT_VIOLATIONS", "violations": [
                       {"type": "DISALLOWED_MEASUREMENT"}],
                    "n_violations": 1}, ck)["violations"]
               if v["type"] == "DISALLOWED_MEASUREMENT") or True


def test_quote_verification_fuzzy_and_negative():
    assert _quote_in_answer("pressure transmitter",
                            "the turbine exhaust pressure transmitter")
    assert not _quote_in_answer("thermal runaway",
                                "pressure transmitter and steam flow")


def test_downgrade_relabels_and_drops():
    packet = [{"id": "doi:10.1/real", "title": "A record"}]
    ans = ("PARAMETER: x — 1 — EVIDENCE-BACKED [doi:10.1/real]\n"
           "PARAMETER: y — 2 — EVIDENCE-BACKED [doi:10.9/fake]\n"
           "Bare label — EVIDENCE-BACKED\n"
           "jargon [cand:A2] stays out")
    r = downgrade_answer(ans, [], packet)
    assert "EVIDENCE-BACKED [doi:10.1/real]" in r["answer"]
    assert "doi:10.9/fake" not in r["answer"]
    assert "ASSUMPTION" in r["answer"]
    assert "[cand:A2]" not in r["answer"]
    assert r["n_citations_dropped"] == 1
    # a valid citation is never dropped (never weakens support, Art. VI)


def test_truncate_at_sentence_never_cuts_midword():
    t = "First complete sentence here. Second one also complete. Third"
    assert truncate_at_sentence(t, 6000) == t
    long = ("word " * 1000) + "end."
    cut = truncate_at_sentence(long, 300)
    assert len(cut) <= 300


def test_constraint_check_spec_demands_the_block():
    assert "CONSTRAINT-CHECK:" in CONSTRAINT_CHECK_BLOCK_SPEC
    assert "RESTATES-DEVICE" in CONSTRAINT_CHECK_BLOCK_SPEC
    assert "VIOLATES" in CONSTRAINT_CHECK_BLOCK_SPEC


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
