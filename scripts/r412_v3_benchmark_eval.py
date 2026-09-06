#!/usr/bin/env python3
"""r412_v3_benchmark_eval.py — directive item 7: the deterministic
retrieval benchmark evaluation over COMMITTED lane pool bytes.

PASS/FAIL THRESHOLDS ARE PRE-REGISTERED (frozen in the v3
preregistration BEFORE the lane run; Art. XXVII/LIX — never tuned to
results). Every metric regenerates from committed bytes (Art. LXII).

Metrics (directive item 7's list, verbatim):
  * recall of numeric-bearing records       (reference-set recall)
  * recall of measurement-bearing records   (reference-set recall)
  * domain diversity                        (closed-keyword classes)
  * baseline recovery                       (extraction rate)
  * year recovery                           (multi-field persistence)
  * source identity recovery                (persistence schema)

Plus the pool property rates and the directive-14 cost metric
(numeric-bearing records exposed per fabric source-call).
NO LLM ANYWHERE.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.frontier_evidence import (  # noqa: E402
    extraction_for_pool, summarize_pool, domain_class, FEAL_VERSION,
)

POOLS = REPO / "R412" / "GRADIENT_V3" / "RUN" / "LANE_POOLS"
CORPUS = REPO / "R412" / "GRADIENT_V3" / "RETRIEVAL_BENCHMARK" / \
    "RETRIEVAL_BENCHMARK_CORPUS.json"
PREREG = REPO / "R412" / "GRADIENT_V3" / \
    "R412_GRADIENT_V3_PREREGISTRATION.json"
OUT = REPO / "R412" / "GRADIENT_V3" / "RUN" / \
    "RETRIEVAL_BENCHMARK_EVALUATION.json"

V2_BASELINE = {  # measured by RETRIEVAL_DIAGNOSTIC_V2_POOLS.json
    "numeric_bearing_rate": 0.0263,
    "measurement_bearing_rate": 0.1513,
    "abstract_bearing_rate": 0.2237,
    "year_recovery_rate": 0.0,
    "source_identity_recovery_rate": 0.0,
}


def _norm_doi(d: Optional[str]) -> str:
    if not d:
        return ""
    s = str(d).strip().lower()
    s = re.sub(r"^https?://(dx\.)?doi\.org/", "", s)
    return s


def _title_fp(title: str, year: Optional[int] = None) -> str:
    words = re.findall(r"[a-z0-9]+", (title or "").lower())[:12]
    return " ".join(words) + "|" + str(year or "")


def load_lane_pools() -> List[Dict[str, Any]]:
    entries = []
    for p in sorted(POOLS.glob("*.json")):
        if p.name.startswith("_"):
            continue
        d = json.loads(p.read_text())
        if d.get("status") == "OK":
            entries.append(d)
    return entries


def build_pools(entries: List[Dict[str, Any]]
                ) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """by-lane and union pools, deduplicated by canonical identity
    (DOI first, title-fingerprint fallback) — deterministic."""
    pools: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for lane in ("A", "B", "C"):
        seen: Dict[str, Dict[str, Any]] = {}
        for e in entries:
            if e.get("lane") != lane:
                continue
            for r in e.get("pool_records") or []:
                key = (_norm_doi(r.get("doi")) or
                       _title_fp(r.get("title"),
                                 r.get("publication_year")) or
                       str(r.get("record_id")))
                if key not in seen:
                    r2 = dict(r)
                    r2["lane_key"] = key
                    r2["matched_lane_queries"] = [e.get("query")]
                    r2["matched_rung"] = e.get("rung")
                    seen[key] = r2
                else:
                    seen[key].setdefault(
                        "matched_lane_queries", []).append(
                        e.get("query"))
        pools[lane] = {"records": list(seen.values())}
    # union across lanes
    seen_u: Dict[str, Dict[str, Any]] = {}
    for lane in ("A", "B", "C"):
        for r in pools[lane]["records"]:
            k = r["lane_key"]
            if k not in seen_u:
                seen_u[k] = dict(r)
                seen_u[k]["lanes_matched"] = [lane]
            else:
                if lane not in seen_u[k]["lanes_matched"]:
                    seen_u[k]["lanes_matched"].append(lane)
                seen_u[k].setdefault(
                    "matched_lane_queries", []).extend(
                    r.get("matched_lane_queries") or [])
    pools["UNION"] = {"records": list(seen_u.values())}
    return pools


def reference_recall(corpus: Dict[str, Any],
                     pool_records: List[Dict[str, Any]]
                     ) -> Dict[str, Any]:
    """Reference-set recall: fraction of the frozen corpus's
    RELEVANT+label-true records present in the pool (identity:
    normalized DOI, else title-fingerprint)."""
    pool_by_doi = {_norm_doi(r.get("doi"))
                   for r in pool_records if r.get("doi")}
    pool_by_fp = {_title_fp(r.get("title"),
                            r.get("publication_year"))
                  for r in pool_records}
    pool_titles = {(r.get("title") or "")[:80].lower()
                   for r in pool_records}

    def _present(ref: Dict[str, Any]) -> bool:
        doi = _norm_doi(ref.get("doi"))
        if doi and doi in pool_by_doi:
            return True
        if _title_fp(ref.get("title"),
                     (ref.get("labels") or {}).get("year")
                     ) in pool_by_fp:
            return True
        return (ref.get("title") or "")[:80].lower() in pool_titles

    out: Dict[str, Any] = {}
    for prop in ("numeric_bearing", "measurement_bearing"):
        refs = [r for r in corpus["records"]
                if (r.get("labels") or {}).get("relevant")
                and (r.get("labels") or {}).get(prop)]
        hits = [r for r in refs if _present(r)]
        out[f"recall_{prop}"] = {
            "denominator": len(refs),
            "matched": len(hits),
            "recall": round(len(hits) / len(refs), 4)
            if refs else None,
            "matched_benchmark_ids": [r["benchmark_id"]
                                      for r in hits],
            "missing_benchmark_ids": [r["benchmark_id"]
                                      for r in refs
                                      if not _present(r)],
        }
    return out


def pool_metrics(records: List[Dict[str, Any]],
                 extractions: Dict[str, Any]) -> Dict[str, Any]:
    summary = summarize_pool(records, extractions)
    n = len(records) or 1
    baseline_ids = {rid for rid, ext in extractions.items()
                    if any(e.get("baseline_comparator")
                           for e in ext.get("evidences") or [])}
    summary["baseline_recovery_count"] = len(baseline_ids)
    summary["baseline_recovery_rate"] = round(
        len(baseline_ids) / n, 4)
    src_ids = [r for r in records if r.get("source")]
    summary["source_identity_recovery_count"] = len(src_ids)
    summary["source_identity_recovery_rate"] = round(
        len(src_ids) / n, 4)
    summary["feal_version"] = FEAL_VERSION
    return summary


def main() -> int:
    corpus = json.loads(CORPUS.read_text())
    entries = load_lane_pools()
    if not entries:
        print("REFUSED: no completed lane pool bytes committed")
        return 1
    pools = build_pools(entries)

    prereg = json.loads(PREREG.read_text()) if PREREG.exists() \
        else None
    if prereg is None:
        print("REFUSED: v3 preregistration absent — seal first "
              "(thresholds must be pre-registered, Art. LIX)")
        return 1
    thresholds = prereg["retrieval_benchmark_gate"]["thresholds"]
    corpus_pin = prereg["retrieval_benchmark"]["corpus_sha256"]
    live_corpus_sha = hashlib.sha256(
        json.dumps(corpus, sort_keys=True).encode()).hexdigest()
    if live_corpus_sha != corpus_pin:
        print("REFUSED: benchmark corpus hash drift vs seal "
              f"({live_corpus_sha[:12]} != {corpus_pin[:12]})")
        return 1

    # ---- per-lane + union metrics -----------------------------------
    report: Dict[str, Any] = {
        "artifact_type": "R412_GRADIENT_V3_RETRIEVAL_BENCHMARK_"
                         "EVALUATION",
        "directive_item": 7,
        "created_at": None,
        "n_lane_query_completions": len(entries),
        "v2_measured_baseline": V2_BASELINE,
        "lanes": {},
    }
    total_source_calls = 0
    for e in entries:
        st = e.get("retrieval_stats") or {}
        # COST-DENOMINATOR DEFECT REPAIR (2026-09-06, quarantined
        # incident R412-GRADIENT-V3-EVAL-SOURCE-CALL-COUNT): the lane
        # pools persist the fabric report's sources_attempted as a
        # LIST of source ids; the first evaluator draft coerced it
        # with int() and crashed before any threshold was evaluated.
        # Count list length, int otherwise. This is the reported cost
        # denominator ONLY — no gate threshold consumes it, so the
        # defect cannot have influenced any verdict; original error
        # preserved in the incident record (Art. XI/LXI).
        att = st.get("sources_attempted") or 0
        total_source_calls += (len(att) if isinstance(att, list)
                               else int(att))
    for lane in ("A", "B", "C", "UNION"):
        records = pools[lane]["records"]
        extractions = extraction_for_pool(records)
        recall = reference_recall(corpus, records)
        metrics = pool_metrics(records, extractions)
        report["lanes"][lane] = {
            "n_records": len(records),
            "reference_recall": recall,
            "pool_metrics": metrics,
        }

    union = report["lanes"]["UNION"]
    n_union = union["n_records"]
    numeric_exposed = union["pool_metrics"][
        "numeric_bearing_count"]
    report["retrieval_cost_metric"] = {
        "total_fabric_source_calls_attempted":
            total_source_calls,
        "numeric_bearing_records_exposed": numeric_exposed,
        "numeric_bearing_records_per_100_source_calls":
            round(100.0 * numeric_exposed /
                  max(1, total_source_calls), 2),
        "metric_definition":
            "directive item 14: evidence-backed frontier capabilities "
            "exposed to the reasoning engine per unit retrieval cost",
    }

    # ---- threshold evaluation (pre-registered; no tuning) -----------
    u = union["pool_metrics"]
    ur = union["reference_recall"]
    checks = {
        "recall_numeric_bearing":
            (ur["recall_numeric_bearing"]["recall"]
             if ur["recall_numeric_bearing"]["recall"] is not None
             else 0.0),
        "recall_measurement_bearing":
            (ur["recall_measurement_bearing"]["recall"]
             if ur["recall_measurement_bearing"]["recall"]
             is not None else 0.0),
        "numeric_bearing_rate": u["numeric_bearing_rate"],
        "measurement_bearing_rate":
            u["measurement_bearing_rate"],
        "abstract_bearing_rate": u["abstract_bearing_rate"],
        "year_recovery_rate": u["year_recovery_rate"],
        "source_identity_recovery_rate":
            u["source_identity_recovery_rate"],
        "baseline_recovery_rate": u["baseline_recovery_rate"],
        "domain_diversity": u["domain_diversity"],
    }
    results = {}
    for name, value in checks.items():
        thr = thresholds[name]
        results[name] = {
            "measured": value,
            "threshold": thr,
            "pass": value >= thr,
        }
    gate_pass = all(r["pass"] for r in results.values())
    report["gate"] = {
        "rule": "ALL pre-registered thresholds must pass before any "
                "proposer call (directive item 7); a fail is an "
                "honest stop with decomposition, never a retry-with-"
                "tuning (Art. LIX)",
        "checks": results,
        "verdict": "PASS" if gate_pass else "FAIL",
    }
    report["reviewer_provenance"] = "AI_REVIEW"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, indent=1) + "\n")
    print(f"benchmark evaluation written: {OUT}")
    print(f"  union pool: {n_union} records; "
          f"numeric-bearing {numeric_exposed}")
    for name, r in results.items():
        print(f"  {'PASS' if r['pass'] else 'FAIL'} "
              f"{name}: {r['measured']} >= {r['threshold']}")
    print(f"GATE VERDICT: {report['gate']['verdict']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
