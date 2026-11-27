#!/usr/bin/env python3
"""R516 distinctness benchmark runner — owner audit round 2026-11-13.

Runs the CURRENT mechanism-distinctness instrument
(mechanism_space.compare_candidates, mechanism_distinctness/2.0.0)
over an independently authored pair set labeled DISTINCT / EQUIVALENT /
INDETERMINATE, and reports:

  * false-merge rate (expected DISTINCT -> predicted EQUIVALENT),
  * false-split rate (expected EQUIVALENT -> predicted DISTINCT),
  * strict non-equivalence rate (expected EQUIVALENT -> any non-
    EQUIVALENT prediction, INCLUDING the honest INDETERMINATE deferral),
  * INDETERMINATE recall and forced-decision rate,
  * exact agreement,
  * Wilson 95% confidence intervals for every rate.

The instrument is NEVER promoted by this script. The owner audit is
explicit: mechanism_distinctness/2.0.0 is a LEXICAL SCREENING HEURISTIC
until a benchmark (ideally independent of the maintaining agent) earns
it structural authority. The report carries that class and
`discovery_credit: NOT_ESTABLISHED_AS_CAUSAL_DISTINCTNESS`, plus the
benchmark's own independence state (this authored set is NOT
INDEPENDENT — it is recorded as such, never laundered).

Deterministic, zero LLM, zero network.

Usage:
  python3 scripts/r516_distinctness_benchmark.py [--benchmark FILE]
                                                 [--out FILE]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.engine.mechanism_space import (  # noqa: E402
    DISTINCTNESS_INSTRUMENT_VERSION, compare_candidates,
)

BENCHMARK_DEFAULT = REPO / "R516" / "DISTINCTNESS_BENCHMARK.json"
ADJUDICATOR_VERSION = "r516_distinctness_benchmark_adjudicator/1.0.0"
Z_95 = 1.959963984540054


def wilson(k: int, n: int) -> Dict[str, Any]:
    """Wilson score interval for a binomial proportion (95%)."""
    if n <= 0:
        return {"numerator": k, "denominator": n, "rate": None,
                "ci95_low": None, "ci95_high": None}
    p = k / n
    denom = 1.0 + Z_95 * Z_95 / n
    centre = (p + Z_95 * Z_95 / (2 * n)) / denom
    half = (Z_95 * math.sqrt(p * (1 - p) / n
                             + Z_95 * Z_95 / (4 * n * n)) / denom)
    return {
        "numerator": k,
        "denominator": n,
        "rate": round(p, 4),
        "ci95_low": round(max(0.0, centre - half), 4),
        "ci95_high": round(min(1.0, centre + half), 4),
    }


def run(benchmark: Dict[str, Any]) -> Dict[str, Any]:
    pairs = benchmark.get("pairs") or []
    rows: List[Dict[str, Any]] = []
    counts = {k: {"DISTINCT": 0, "EQUIVALENT": 0,
                  "INDETERMINATE": 0, "UNRECOGNIZED": 0}
              for k in ("DISTINCT", "EQUIVALENT", "INDETERMINATE")}
    exact = 0
    for p in pairs:
        exp = str(p.get("expected") or "").upper()
        cmp = compare_candidates(p.get("a") or {}, p.get("b") or {})
        pred = cmp.get("verdict") or "UNRECOGNIZED"
        if pred not in ("DISTINCT", "EQUIVALENT", "INDETERMINATE"):
            pred = "UNRECOGNIZED"
        if exp in counts:
            counts[exp][pred] += 1
        if pred == exp:
            exact += 1
        rows.append({
            "pair_id": p.get("pair_id"),
            "domain": p.get("domain"),
            "expected": exp,
            "predicted": pred,
            "causal_core_jaccard": cmp.get("causal_core_jaccard"),
            "differing_dimensions": cmp.get("differing_dimensions"),
            "basis": cmp.get("basis"),
        })
    n = len(rows)
    n_dist = sum(counts["DISTINCT"].values())
    n_eq = sum(counts["EQUIVALENT"].values())
    n_ind = sum(counts["INDETERMINATE"].values())
    false_merges = counts["DISTINCT"]["EQUIVALENT"]
    strict_false_splits = counts["EQUIVALENT"]["DISTINCT"]
    non_equiv_splits = (counts["EQUIVALENT"]["DISTINCT"]
                        + counts["EQUIVALENT"]["INDETERMINATE"])
    ind_recalled = counts["INDETERMINATE"]["INDETERMINATE"]
    ind_forced = sum(v for k, v in counts["INDETERMINATE"].items()
                     if k != "INDETERMINATE")
    return {
        "report_id": "r516_distinctness_benchmark_report",
        "report_version": "1.0.0",
        "instrument": DISTINCTNESS_INSTRUMENT_VERSION,
        "adjudicator_version": ADJUDICATOR_VERSION,
        "benchmark": {
            "benchmark_id": benchmark.get("benchmark_id"),
            "benchmark_version": benchmark.get("benchmark_version"),
            "authored_at": benchmark.get("authored_at"),
            "authoring_provenance": benchmark.get("authoring_provenance"),
            "independence_state": benchmark.get("independence_state"),
            "independence_note": benchmark.get("independence_note"),
            "n_pairs": n,
        },
        "classification": "LEXICAL_SCREENING_HEURISTIC",
        "discovery_credit": "NOT_ESTABLISHED_AS_CAUSAL_DISTINCTNESS",
        "classification_basis": (
            "owner audit 2026-11-13: a lexical term instrument may screen "
            "candidates but cannot establish causal distinctness; the "
            "measured rates below are reported, NOT converted into a "
            "pass/fail threshold or structural authority"),
        "n_pairs": n,
        "class_counts": {
            "expected_to_predicted": counts,
            "n_expected_DISTINCT": n_dist,
            "n_expected_EQUIVALENT": n_eq,
            "n_expected_INDETERMINATE": n_ind,
        },
        "metrics": {
            "exact_agreement": wilson(exact, n),
            "false_merge_rate": wilson(false_merges, n_dist),
            "false_split_rate_strict": wilson(strict_false_splits, n_eq),
            "false_split_rate_non_equivalent": wilson(
                non_equiv_splits, n_eq),
            "indeterminate_recall": wilson(ind_recalled, n_ind),
            "forced_decision_rate_on_indeterminate": wilson(ind_forced,
                                                            n_ind),
        },
        "metric_definitions": {
            "false_merge_rate": (
                "of expected-DISTINCT pairs, the fraction predicted "
                "EQUIVALENT (a real mechanism difference merged away)"),
            "false_split_rate_strict": (
                "of expected-EQUIVALENT pairs, the fraction predicted "
                "DISTINCT (the same mechanism split into two)"),
            "false_split_rate_non_equivalent": (
                "of expected-EQUIVALENT pairs, the fraction predicted "
                "anything other than EQUIVALENT (DISTINCT or "
                "INDETERMINATE; the deferral is honest, but it still "
                "fails to merge a pair known to be the same family)"),
            "indeterminate_recall": (
                "of expected-INDETERMINATE pairs, the fraction the "
                "instrument correctly deferred"),
        },
        "pairs": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--benchmark", default=str(BENCHMARK_DEFAULT))
    ap.add_argument("--out", help="write the report JSON here")
    args = ap.parse_args()
    benchmark = json.loads(Path(args.benchmark).read_text(encoding="utf-8"))
    report = run(benchmark)
    payload = json.dumps(report, indent=1, sort_keys=True,
                         ensure_ascii=False)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
