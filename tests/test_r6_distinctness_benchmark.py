"""tests/test_r6_distinctness_benchmark.py — owner audit 2026-11-13.

Pins the benchmark's epistemic honesty, not a pass threshold:
  1. The report classifies mechanism_distinctness/2.0.0 as
     LEXICAL_SCREENING_HEURISTIC with discovery credit explicitly NOT
     established — a good score never promotes the instrument.
  2. Every rate carries its numerator, denominator and Wilson 95% CI.
  3. The benchmark's own independence state is recorded (NOT_INDEPENDENT
     for this authored set) — never laundered into independent validation.
  4. All three label classes are represented and every pair yields a
     recognized verdict.
  5. The report is deterministic (same input -> same output).
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

_SPEC = importlib.util.spec_from_file_location(
    "r516_distinctness_benchmark",
    REPO / "scripts" / "r516_distinctness_benchmark.py")
B = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(B)


def _benchmark():
    return json.loads(
        (REPO / "R516" / "DISTINCTNESS_BENCHMARK.json").read_text(
            encoding="utf-8"))


def test_report_never_promotes_the_lexical_instrument():
    r = B.run(_benchmark())
    assert r["classification"] == "LEXICAL_SCREENING_HEURISTIC"
    assert r["discovery_credit"] == (
        "NOT_ESTABLISHED_AS_CAUSAL_DISTINCTNESS")
    assert r["benchmark"]["independence_state"] == "NOT_INDEPENDENT"
    assert r["benchmark"]["independence_note"]


def test_every_rate_carries_counts_and_ci():
    m = B.run(_benchmark())["metrics"]
    for name, mtr in m.items():
        assert set(mtr) == {"numerator", "denominator", "rate",
                            "ci95_low", "ci95_high"}, name
        if mtr["rate"] is not None:
            assert 0.0 <= mtr["rate"] <= 1.0
            assert 0.0 <= mtr["ci95_low"] <= mtr["rate"]
            assert mtr["rate"] <= mtr["ci95_high"] <= 1.0


def test_all_three_classes_are_represented():
    r = B.run(_benchmark())
    counts = r["class_counts"]
    assert counts["n_expected_DISTINCT"] > 0
    assert counts["n_expected_EQUIVALENT"] > 0
    assert counts["n_expected_INDETERMINATE"] > 0
    for p in r["pairs"]:
        assert p["predicted"] in ("DISTINCT", "EQUIVALENT",
                                  "INDETERMINATE"), p["pair_id"]


def test_report_is_deterministic():
    b = _benchmark()
    a = json.dumps(B.run(b), sort_keys=True)
    c = json.dumps(B.run(b), sort_keys=True)
    assert a == c


def test_versions_are_carried():
    r = B.run(_benchmark())
    assert r["instrument"] == "mechanism_distinctness/2.0.0"
    assert r["adjudicator_version"] == B.ADJUDICATOR_VERSION
    assert r["benchmark"]["benchmark_version"]
