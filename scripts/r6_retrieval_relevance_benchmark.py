#!/usr/bin/env python3
"""R6 retrieval-relevance benchmark runner — owner audit round 2026-11-13.

Measures the mechanism-space reranker at depth on the frozen labeled pool
R6/RETRIEVAL_RELEVANCE_BENCHMARK.json against five relevance dimensions:
failure, causal, boundary, evidence, transfer.

Two arms:
  * BASELINE — the frozen mechanism_signal_rerank/1.0.0 decision rule
    (density + 0.5 per shared problem-fact term), reimplemented here
    byte-for-byte from the committed 1.0.0 formula so the comparator does
    not move when the engine changes.
  * IMPROVED — the live engine instrument
    (mechanism_signal_rerank/1.1.0 + retrieval_relevance/1.0.0).

Reported per depth (the corpus declares depths):
  * precision@k and recall@k for CORE relevance
    (failure == 1 AND (causal == 1 OR evidence == 1)),
  * recall@k per relevance dimension,
  * mean dimension recall@k,
  * micro aggregates with Wilson 95% confidence intervals.

The benchmark is authored by the maintaining agent: independence_state
is NOT_INDEPENDENT and the report says so. A measured gain on this pool
is a dev regression signal, NOT independent validation and NOT a license
to promote the lexical screen to a relevance verdict (Art. XXI).

Deterministic, zero LLM, zero network.

Usage:
  python3 scripts/r6_retrieval_relevance_benchmark.py [--out FILE]
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

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402
from discovery_fabric.retrieval_fabric.query_expansion import (  # noqa: E402
    _content_terms,
)

BENCHMARK_DEFAULT = REPO / "R6" / "RETRIEVAL_RELEVANCE_BENCHMARK.json"
ADJUDICATOR_VERSION = "r6_retrieval_relevance_adjudicator/1.0.0"
BASELINE_INSTRUMENT = "mechanism_signal_rerank/1.0.0"
Z_95 = 1.959963984540054


def wilson(k: int, n: int) -> Dict[str, Any]:
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


def _legacy_problem_terms(problem: Dict[str, Any]) -> List[str]:
    """The frozen 1.0.0 relevance component's term extraction."""
    text = " ".join(str(problem.get(k) or "") for k in
                    ("device", "failure", "failure_mode", "constraint"))
    return sorted(set(_content_terms(text)))[:14]


def _legacy_rank(records: List[Dict[str, Any]],
                 problem: Dict[str, Any], top_k: int) -> List[str]:
    rel_terms = _legacy_problem_terms(problem)
    scored = []
    for r in records:
        s = ms.mechanism_signal_score(r)
        text = " ".join(str(r.get(k) or "") for k in
                        ("title", "abstract", "snippet")).lower()
        hits = sorted(t for t in rel_terms if t in text)
        score = s["score"] + 0.5 * len(hits)
        scored.append((round(score, 2), str(r.get("id") or "")))
    scored.sort(key=lambda t: (-t[0], t[1]))
    return [rid for _, rid in scored[:max(0, top_k)]]


def _core(rel: Dict[str, int]) -> int:
    return int(bool(rel.get("failure"))
               and (bool(rel.get("causal")) or bool(rel.get("evidence"))))


def _evaluate_arm(problems: List[Dict[str, Any]],
                  rank_fn) -> Dict[str, Any]:
    dims = list(ms.RETRIEVAL_RELEVANCE_DIMENSIONS)
    depths = sorted({int(d) for p in problems
                     for d in (p.get("_depths") or [])})
    per_depth: Dict[str, Any] = {}
    for depth in depths:
        core_hit = core_total = 0
        dim_hit = {d: 0 for d in dims}
        dim_total = {d: 0 for d in dims}
        prec_hit = prec_total = 0
        per_problem = []
        for pr in problems:
            problem = pr["problem"]
            records = pr["records"]
            ranked = rank_fn(records, problem, depth)
            by_id = {str(r.get("id")): r for r in records}
            selected = [by_id[i] for i in ranked if i in by_id]
            n_core_sel = sum(_core(r.get("relevance") or {})
                             for r in selected)
            n_core_all = sum(_core(r.get("relevance") or {})
                             for r in records)
            prec_hit += n_core_sel
            prec_total += len(selected)
            core_hit += n_core_sel
            core_total += n_core_all
            for d in dims:
                n_sel = sum(int((r.get("relevance") or {}).get(d) or 0)
                            for r in selected)
                n_all = sum(int((r.get("relevance") or {}).get(d) or 0)
                            for r in records)
                dim_hit[d] += n_sel
                dim_total[d] += n_all
            per_problem.append({
                "problem_id": pr.get("problem_id"),
                "selected_ids": ranked,
                "n_core_selected": n_core_sel,
                "n_core_available": n_core_all,
            })
        dim_recall = {d: wilson(dim_hit[d], dim_total[d]) for d in dims}
        defined = [v["rate"] for v in dim_recall.values()
                   if v["rate"] is not None]
        per_depth[str(depth)] = {
            "precision_at_depth": wilson(prec_hit, prec_total),
            "core_recall_at_depth": wilson(core_hit, core_total),
            "dimension_recall_at_depth": dim_recall,
            "mean_dimension_recall_at_depth": (
                round(sum(defined) / len(defined), 4)
                if defined else None),
            "per_problem": per_problem,
        }
    return per_depth


def run(benchmark: Dict[str, Any]) -> Dict[str, Any]:
    problems = []
    for pr in benchmark.get("problems") or []:
        pr = dict(pr)
        pr["_depths"] = benchmark.get("depths") or [3, 5]
        problems.append(pr)
    baseline = _evaluate_arm(problems, _legacy_rank)
    improved = _evaluate_arm(
        problems,
        lambda records, problem, depth: ms.mechanism_signal_rerank(
            records, top_k=depth, problem=problem)["selected_ids"])
    deltas = {}
    for depth in baseline:
        b, i = baseline[depth], improved[depth]
        deltas[depth] = {
            "precision_at_depth_delta": round(
                (i["precision_at_depth"]["rate"] or 0.0)
                - (b["precision_at_depth"]["rate"] or 0.0), 4),
            "core_recall_at_depth_delta": round(
                (i["core_recall_at_depth"]["rate"] or 0.0)
                - (b["core_recall_at_depth"]["rate"] or 0.0), 4),
            "mean_dimension_recall_at_depth_delta": round(
                (i["mean_dimension_recall_at_depth"] or 0.0)
                - (b["mean_dimension_recall_at_depth"] or 0.0), 4),
        }
    return {
        "report_id": "r6_retrieval_relevance_benchmark_report",
        "report_version": "1.0.0",
        "adjudicator_version": ADJUDICATOR_VERSION,
        "baseline_instrument": BASELINE_INSTRUMENT,
        "improved_instrument": "mechanism_signal_rerank/1.1.0",
        "retrieval_relevance_version": ms.RETRIEVAL_RELEVANCE_VERSION,
        "benchmark": {
            "benchmark_id": benchmark.get("benchmark_id"),
            "benchmark_version": benchmark.get("benchmark_version"),
            "authored_at": benchmark.get("authored_at"),
            "authoring_provenance": benchmark.get("authoring_provenance"),
            "independence_state": benchmark.get("independence_state"),
            "independence_note": benchmark.get("independence_note"),
            "n_problems": len(problems),
            "n_records": sum(len(p["records"]) for p in problems),
            "depths": benchmark.get("depths"),
            "label_dimensions": benchmark.get("label_dimensions"),
            "core_relevance_rule": benchmark.get("core_relevance_rule"),
        },
        "classification": "LEXICAL_SCREENING_HEURISTIC",
        "discovery_credit": "NOT_ESTABLISHED_AS_RELEVANCE_VALIDATION",
        "classification_basis": (
            "owner audit 2026-11-13: a lexical reranker may order records "
            "for extraction but cannot establish relevance; the measured "
            "gain below is a dev regression signal on an authored pool, "
            "never independent validation"),
        "baseline": baseline,
        "improved": improved,
        "deltas": deltas,
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
