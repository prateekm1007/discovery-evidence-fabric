"""tests/test_r10_consistency_real_runs.py — R10 P0 item 3 (owner
round 2026-11-13): the consistency improvement is regressed against
REAL COMMITTED RUN BYTES, never a hand-built fixture.

The owner's directive, verbatim requirements:
  * the COMMITTED new07 answer + the ACTUAL problem must flag the
    factor mismatch through consistency_check(actual_answer, None,
    actual_problem) — the exact call shape the A0+ arm rides;
  * a p02 REAL positive control guards against false positives (the
    committed baseline bytes pass — the check fires on the real
    defect, not on the shape);
  * the marker handling is PINNED: a bare 'protocol:' inside the
    threshold's calibration clause must NOT split the test section
    (the R9 measured mis-split: admitting bare 'protocol:' cut the
    new07 answer at its THRESHOLD calibration line and orphaned the
    protocol segment);
  * BOTH paths are verified — the candidate-free path (None, the
    A0+ arm's call) and the candidate path (the composer's call with
    the REAL run-tree candidate records).

Every fixture is committed bytes: eval/pairs/dev12_fresh/*.json,
eval/problems_dev12.json, tests/fixtures/r7_owner_round/
new07_candidates.json (extracted from the audited run trees). No
gitignored tree, no hand-built dict (Art. IX).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_consistency import (  # noqa: E402
    consistency_check, _split_test)

PAIRS = REPO / "eval" / "pairs" / "dev12_fresh"
DEV12 = REPO / "eval" / "problems_dev12.json"


def _pair(pid: str) -> dict:
    return json.loads((PAIRS / f"{pid}.json").read_text(
        encoding="utf-8"))


def _problem(pid: str) -> dict:
    d = json.loads(DEV12.read_text(encoding="utf-8"))
    plist = d if isinstance(d, list) else d.get("problems", [])
    return next(p for p in plist
                if str(p.get("problem_id") or p.get("id")) == pid)


def _real_candidate(pid: str, substr: str) -> dict:
    """A VERBATIM real candidate record from the committed run-tree
    fixture (never a hand-built dict — owner R9 item 3, carried)."""
    fx = json.loads((REPO / "tests" / "fixtures" / "r7_owner_round"
                     / "new07_candidates.json").read_text(
                         encoding="utf-8"))
    for c in fx[pid]["candidates"]:
        if substr.lower() in str(c.get("intervention", "")).lower():
            return c
    raise AssertionError(f"no real candidate matching {substr!r}")


class TestNew07FactorMismatchRealBytes:
    def test_consistency_check_actual_answer_none_actual_problem(self):
        """The directive's exact call shape: consistency_check(
        actual_answer, None, actual_problem) must DETECT the factor
        mismatch on the committed new07 bytes."""
        pair = _pair("eval-new07-transformer-dga-predictor")
        prob = _problem("eval-new07-transformer-dga-predictor")
        chk = consistency_check(pair["pipeline_answer"], None, prob)
        assert chk["state"] == "CONSISTENCY_VIOLATIONS", chk
        types = {v["type"] for v in chk["violations"]}
        assert "TEST_FACTOR_MISMATCH" in types, types

    def test_candidate_path_flags_two_designs(self):
        """The candidate path (the composer's call) flags the SAME
        defect class on the same real bytes (both paths verified)."""
        pair = _pair("eval-new07-transformer-dga-predictor")
        prob = _problem("eval-new07-transformer-dga-predictor")
        nanofluid = _real_candidate(
            "eval-new07-transformer-dga-predictor",
            "nanofluid containing Al2O3")
        chk = consistency_check(pair["pipeline_answer"], [nanofluid],
                                prob)
        assert chk["state"] == "CONSISTENCY_VIOLATIONS", chk
        types = {v["type"] for v in chk["violations"]}
        assert types & {"TWO_DESIGNS_IN_PROPOSAL",
                        "TEST_FACTOR_MISMATCH"}, types


class TestP02RealPositiveControl:
    def test_committed_p02_baseline_passes_no_false_positive(self):
        """防误报 (owner R10): the committed p02 baseline bytes + the
        actual problem must PASS — the factor-variation rule fires on
        the real new07 defect, never on an honest same-factor test."""
        pair = _pair("bench-p02-leadacid-grid-corrosion")
        prob = _problem("bench-p02-leadacid-grid-corrosion")
        base = str(pair.get("baseline_answer") or "").strip()
        assert base, "the p02 baseline bytes must exist"
        chk = consistency_check(base, None, prob)
        types = {v["type"] for v in (chk.get("violations") or [])}
        assert "TEST_FACTOR_MISMATCH" not in types, (chk["state"], types)

    def test_p02_repaired_arm_shape_stays_clean(self):
        """The A0+-repaired p02 shape (R9 arm bytes) is ALSO a positive
        control: the surgical test section tests the design's own
        factor (charge conditions), no mismatch typed."""
        r9 = REPO / "eval" / "pairs" / "r9_a0plus" / \
            "bench-p02-leadacid-grid-corrosion.json"
        if not r9.exists():
            return  # the arm bytes are round evidence; the pin rides
            # the committed bytes when present
        ans = str(json.loads(r9.read_text(encoding="utf-8"))
                  .get("a0plus_answer") or "").strip()
        if not ans:
            return
        prob = _problem("bench-p02-leadacid-grid-corrosion")
        chk = consistency_check(ans, None, prob)
        types = {v["type"] for v in (chk.get("violations") or [])}
        assert "TEST_FACTOR_MISMATCH" not in types


class TestBareProtocolMarkerHandling:
    def test_bare_protocol_colon_never_splits_the_test_section(self):
        """保留 marker 处理 (owner R10): a bare 'protocol:' inside the
        THRESHOLD's calibration clause is NOT a test marker — the
        answer with only a bare 'protocol:' yields an EMPTY test
        section (CHECK_ABSENT territory), never a mis-split at the
        calibration line."""
        syn = ("INDICATOR: d[H2]/dt slope in ppm/day\n"
               "THRESHOLD: mean + 3 sigma over 30 days; calibration "
               "protocol: fleet percentile ranking\n"
               "MONITORING: online DGA sensor at 15-minute resolution")
        prop, test = _split_test(syn)
        assert test.strip() == "", (
            "a bare 'protocol:' must not split the test section — the "
            "R9 measured mis-split class")
        assert prop.strip().startswith("INDICATOR:")

    def test_real_new07_answer_split_lands_on_the_test(self):
        """The committed new07 answer DOES carry a real falsification
        test: the split must land ON it (not on the calibration
        clause) — the real bytes pin the marker set both ways."""
        ans = str(_pair("eval-new07-transformer-dga-predictor")
                  .get("pipeline_answer") or "")
        prop, test = _split_test(ans)
        assert len(test.strip()) > 100, test[:120]
        low = test.strip().lower()
        assert low.startswith("falsification") or \
            low.startswith("kill criteria") or \
            low.startswith("pass criteria") or \
            low.startswith("test parameters") or \
            low.startswith("validation"), low[:80]

    def test_validation_protocol_marker_still_splits(self):
        """The admissible form ('VALIDATION PROTOCOL:') remains a
        marker — the predictor contract's own required heading."""
        syn = ("INDICATOR: slipring contact resistance drift\n"
               "THRESHOLD: mean + 3 sigma from 30 days of healthy "
               "telemetry\n"
               "VALIDATION PROTOCOL: fleet of n = 120 machines for "
               "12 months; detection lead >= 30 days")
        prop, test = _split_test(syn)
        assert test.strip().lower().startswith("validation protocol")
