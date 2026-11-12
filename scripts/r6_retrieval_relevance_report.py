#!/usr/bin/env python3
"""R6 A3/A4 per-problem report — abstract coverage + refined queries.

Deterministic, zero LLM, zero new retrieval. Two evidence planes, kept
separate (Art. XXV):

  * ABSTRACT COVERAGE is recomputed from the COMMITTED retrieve envelopes
    (the evidence pool SYNTHESIZE actually consumed). These envelopes
    predate the A3 backfill, so this is the PRE-FIX baseline — the
    starvation number the owner asked to see. Post-fix coverage needs a
    live retrieval run and is reported NOT_MEASURED, never invented.
  * QUERY REFINEMENT is computed by the SHIPPED R6 A4 code from each
    committed problem's own failure/constraint text. It is deterministic
    and needs no provider: it shows exactly which mechanism terms and
    constraint terms now reach the query plan.

The 12-problem plan is the committed run's lexicographic first 12
directories (eval-sofc-thermal-cycling is the deterministic 13th).
"""
from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.retrieval_fabric.query_expansion import (  # noqa: E402
    failure_constraint_variants,
    mechanism_query,
)

RUN_ROOT = REPO / "eval" / "runs" / "2505e43b9003"
OUT_JSON = REPO / "eval" / "score" / "R6_ABSTRACT_COVERAGE_12.json"
OUT_MD = REPO / "eval" / "score" / "R6_ABSTRACT_COVERAGE_12.md"


def _plan_problems() -> list[str]:
    return sorted(d.name for d in RUN_ROOT.iterdir() if d.is_dir())[:12]


def _load(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def _coverage(records: list) -> dict:
    """Same measure as the shipped abstract_coverage/1.0 evidence_pool:
    records with abstract >= 50 chars over all records."""
    n = len(records)
    with_abs = sum(
        1 for r in records
        if isinstance(r, dict)
        and len(str(r.get("abstract") or "")) >= 50)
    return {"records": n, "with_abstract_ge50": with_abs,
            "coverage": (round(with_abs / n, 3) if n else None)}


def _problem_record(problem_id: str) -> dict:
    pipeline = RUN_ROOT / problem_id / "pipeline"
    problem = _load(pipeline / "problem.json") or {}
    envelope = _load(pipeline / "envelope_RETRIEVE.json") or {}
    evidence = envelope.get("evidence") or []
    prov = ((envelope.get("provenance") or {}).get("retrieval_fabric")
            or {})
    primary = mechanism_query(problem)
    variants = failure_constraint_variants(problem, primary)
    classes = [v.get("derivation_class") for v in variants]
    return {
        "problem": problem_id,
        "problem_facts_present": bool(problem),
        "baseline_evidence_abstract_coverage": _coverage(evidence),
        "post_fix_evidence_abstract_coverage": "NOT_MEASURED",
        "post_fix_reason": ("committed envelopes predate the A3 backfill; "
                            "a live retrieval run is required"),
        "committed_query_variant_count": prov.get("query_variant_count"),
        "shipped_primary_query": primary,
        "shipped_refined_variants": variants,
        "shipped_refined_variant_classes": classes,
        "failure_terms_reach_query": "FAILURE_TEXT_TERMS" in classes,
        "constraint_terms_reach_query": "CONSTRAINT_TARGETED" in classes,
        "abstract_backfill_report": "NOT_MEASURED (pre-fix envelope)",
    }


def _markdown(report: dict) -> str:
    lines = [
        "# R6 A3/A4 — per-problem abstract coverage + refined queries",
        "",
        "Deterministic over committed envelopes and committed problem facts; "
        "zero LLM, zero new retrieval.",
        f"Source run: `{report['source_run']}`.",
        "",
        "| problem | records | abstract >=50 | coverage (pre-fix) | "
        "failure terms reach query | constraint terms reach query |",
        "|---|---:|---:|---:|---|---|",
    ]
    for p in report["problems"]:
        cov = p["baseline_evidence_abstract_coverage"]
        cov_s = "NOT_MEASURED" if cov["coverage"] is None else f"{cov['coverage']:.3f}"
        lines.append(
            f"| `{p['problem']}` | {cov['records']} | "
            f"{cov['with_abstract_ge50']} | {cov_s} | "
            f"{'yes' if p['failure_terms_reach_query'] else 'no'} | "
            f"{'yes' if p['constraint_terms_reach_query'] else 'no'} |")
    agg = report["aggregate"]
    lines += [
        "",
        f"Problems with a failure-text variant: "
        f"{agg['problems_with_failure_terms']}/{agg['problems']}.",
        f"Problems with a constraint-targeted variant: "
        f"{agg['problems_with_constraint_terms']}/{agg['problems']}.",
        f"Pre-fix evidence-pool coverage median: "
        f"{agg['baseline_coverage_median']} (min "
        f"{agg['baseline_coverage_min']}, max "
        f"{agg['baseline_coverage_max']}).",
        "",
        "## Disclosures",
        "",
    ]
    lines += [f"- {d}" for d in report["disclosures"]]
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    problems = [_problem_record(p) for p in _plan_problems()]
    covs = [p["baseline_evidence_abstract_coverage"]["coverage"]
            for p in problems
            if p["baseline_evidence_abstract_coverage"]["coverage"] is not None]
    report = {
        "instrument": ("r6_retrieval_relevance_report/1.0 — deterministic "
                       "coverage arithmetic over committed envelopes + "
                       "shipped query variants from committed problem facts; "
                       "zero LLM spend, zero new retrieval"),
        "generated_for": ("owner round 2026-11-12 items A3/A4: abstract "
                          "coverage per problem + failure/constraint query "
                          "refinement"),
        "source_run": str(RUN_ROOT.relative_to(REPO)),
        "plan": [p["problem"] for p in problems],
        "coverage_measure": ("evidence_pool: records with abstract >= 50 "
                             "chars / all evidence records (the same measure "
                             "as shipped abstract_coverage/1.0)"),
        "problems": problems,
        "aggregate": {
            "problems": len(problems),
            "problems_with_failure_terms": sum(
                1 for p in problems if p["failure_terms_reach_query"]),
            "problems_with_constraint_terms": sum(
                1 for p in problems if p["constraint_terms_reach_query"]),
            "baseline_coverage_median": (
                round(statistics.median(covs), 3) if covs else None),
            "baseline_coverage_min": min(covs) if covs else None,
            "baseline_coverage_max": max(covs) if covs else None,
            "post_fix_coverage": "NOT_MEASURED",
        },
        "disclosures": [
            ("The committed retrieve envelopes predate the A3 abstract "
             "backfill. The coverage column is the PRE-FIX baseline — the "
             "starvation number, not a claim that the fix already paid off."),
            ("Post-fix abstract coverage and backfill counts require a live "
             "retrieval run; they are NOT_MEASURED here (no credentials in "
             "this environment)."),
            ("The refined query variants are computed by the shipped A4 "
             "code from the committed problem's own failure/constraint "
             "text: zero LLM, problem facts only (Art. XLIII). They are a "
             "query-plan measurement, not a retrieval result."),
            ("A problem with no failure-text variant has no extractable "
             "content term beyond the primary query; that is a measured "
             "property of its text, not a silent skip."),
            ("The 12-problem plan is the committed run's lexicographic "
             "first 12 directories; eval-sofc-thermal-cycling is the "
             "deterministic 13th."),
        ],
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(report, indent=1, ensure_ascii=False)
                        + "\n", encoding="utf-8")
    OUT_MD.write_text(_markdown(report), encoding="utf-8")
    print(f"problems={len(problems)} "
          f"failure_terms={report['aggregate']['problems_with_failure_terms']} "
          f"constraint_terms="
          f"{report['aggregate']['problems_with_constraint_terms']} "
          f"coverage_median="
          f"{report['aggregate']['baseline_coverage_median']}")
    print(f"written {OUT_JSON}")
    print(f"written {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
