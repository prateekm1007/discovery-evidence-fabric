#!/usr/bin/env python3
"""RETRIEVAL_FABRIC benchmark runner — V1 (Europe PMC + OpenAlex) vs
V2 (multi-source fabric) on the frozen BENCHMARK_CORPUS.

Replayable from a clean checkout (Art. LXII): the corpus, the fabric
registry and both pipelines are committed; this script is the
reproduction command. Live provider states vary run-to-run — every
source failure is recorded honestly in the run report (Art. XXI.3),
never silently dropped, and recall metrics are computed against the
FROZEN target set, never against live-result equality.

Usage:
    python -m discovery_fabric.retrieval_fabric.benchmark.run_benchmark \
        [--out R409/RETRIEVAL_BENCH/fabric_benchmark_report.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from discovery_fabric.retrieval_fabric.benchmark.corpus import (
    load_corpus, target_match,
)
from discovery_fabric.source_registry.query_relevance import (
    adjudicate_record, terms,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm_title(t: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (t or "").lower()))


def _match_target_in_items(target: Dict[str, Any],
                           items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Does the target appear in an evidence pool? Match by patent
    number prefix (normalized) / DOI / title containment — never by
    pre-known position."""
    for it in items:
        # patent prefix match
        pref = target.get("match_patent_number_prefix", "")
        if pref:
            pn = it.get("patent_number") or it.get("id") or ""
            pn_norm = re.sub(r"[^A-Za-z0-9]", "", str(pn)).upper()
            if pn_norm.startswith(re.sub(r"[^A-Za-z0-9]", "", pref).upper()):
                return {"matched_item": it.get("id"),
                        "match_basis": "patent_number",
                        "title": it.get("title", "")[:120]}
        doi = (it.get("doi") or "").lower()
        tdoi = (target.get("match_doi") or "").lower()
        if tdoi and doi and doi == tdoi:
            return {"matched_item": it.get("id"), "match_basis": "doi",
                    "title": it.get("title", "")[:120]}
        # title containment (both directions on normalized titles)
        t_parts = target.get("match_title_contains") or []
        it_t = _norm_title(it.get("title", ""))
        for part in t_parts:
            if _norm_title(part) and _norm_title(part) in it_t:
                return {"matched_item": it.get("id"),
                        "match_basis": "title",
                        "title": it.get("title", "")[:120]}
    return None


def _noise_rate(primary: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """FP/noise measurement with the pipeline's own adjudicator."""
    if not items:
        return {"noise_count": 0, "pool_size": 0, "fp_rate": 0.0,
                "instrument": "adjudicate_record (frozen)"}
    noise = 0
    relevant_items: List[str] = []
    for it in items:
        adj = adjudicate_record(
            {"title": it.get("title", ""),
             "normalized": {"abstract": it.get("abstract", "")},
             "query": primary},
            primary)
        if adj.get("relevance") != "RELEVANT":
            noise += 1
        else:
            relevant_items.append(it.get("title", "")[:80])
    return {"noise_count": noise, "pool_size": len(items),
            "fp_rate": round(noise / len(items), 4),
            "relevant_titles": relevant_items,
            "instrument": ("adjudicate_record: >=2 content-term overlap "
                           "with the primary query (the discovery "
                           "pipeline's own per-record adjudicator)")}


def run_v1(problem: Dict[str, Any]) -> Dict[str, Any]:
    """V1 = the EXACT legacy code path (a2/retrieve.py), unmodified."""
    from discovery_fabric.a2 import retrieve as v1
    result: Dict[str, Any] = {"fabric_version": "V1",
                              "sources": ["europepmc", "openalex"]}
    try:
        items = v1.retrieve(problem) or []
        result["items"] = items
        result["status"] = "OK"
    except Exception as exc:  # noqa: BLE001 — Art. XXI.3: failure != absence
        result["items"] = []
        result["status"] = "FAILED"
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
    result["lanes"] = dict(getattr(v1, "RETRIEVAL_LANES", {}) or {})
    return result


def run_v2(problem: Dict[str, Any]) -> Dict[str, Any]:
    """V2 = the multi-source fabric."""
    from discovery_fabric.retrieval_fabric import retrieve as v2
    items, report = v2(problem)
    return {"fabric_version": "V2", "items": items, "status": "OK",
            "report": report}


def run_benchmark(out_path: Optional[str] = None) -> Dict[str, Any]:
    corpus = load_corpus()
    started = utc_now()
    problems_out: List[Dict[str, Any]] = []
    for entry in corpus["problems"]:
        problem = entry["problem"]
        primary = " ".join(
            f"{problem.get('device', '')} "
            f"{str(problem.get('failure_mode', '')).lower().replace('_', ' ')}"
            .split())
        print(f"\n=== {entry['problem_id']} ===")
        print(f"    primary query: {primary}")
        v1 = run_v1(problem)
        time.sleep(2.0)
        v2 = run_v2(problem)
        # target matching on the EVIDENCE POOLS (what the engine would see)
        v1_hits = []
        for t in entry.get("targets", []):
            m = _match_target_in_items(t, v1["items"])
            v1_hits.append({"target_id": t["target_id"],
                            "kind": t["kind"], "found": bool(m),
                            "match": m})
        v2_hits = []
        v2_canonical = ((v2.get("report") or {}).get("canonical_records")
                        or [])
        for t in entry.get("targets", []):
            m = _match_target_in_items(t, v2["items"])
            m_full = m or _match_target_in_items(t, [
                {"id": r.get("canonical_id"),
                 "title": r.get("title", ""),
                 "doi": r.get("doi"),
                 "patent_number": r.get("patent_number")}
                for r in v2_canonical])
            v2_hits.append({"target_id": t["target_id"],
                            "kind": t["kind"],
                            "found_in_evidence_pool": bool(m),
                            "found_in_canonical_pool": bool(m_full),
                            "match": m_full})
        v1_noise = _noise_rate(primary, v1["items"])
        v2_noise = _noise_rate(primary, v2["items"])
        # V2-unique RELEVANT items: relevant V2 pool records whose
        # normalized title is not in V1's pool (the quantitative form of
        # 'V2 retrieves relevant records absent from V1')
        v1_title_keys = {_norm_title(t) for t in
                         (i.get("title", "") for i in v1["items"]) if t}
        v2_unique_relevant = [t for t in v2_noise.get("relevant_titles", [])
                              if _norm_title(t) not in v1_title_keys]
        div = (v2.get("report") or {}).get("retrieval_diversity", {})
        stats = (v2.get("report") or {}).get("retrieval_stats", {})
        problem_out = {
            "problem_id": entry["problem_id"],
            "primary_query": primary,
            "v1": {"status": v1["status"], "error": v1.get("error"),
                   "pool_size": len(v1["items"]),
                   "pool_titles": [it.get("title", "")[:80]
                                   for it in v1["items"][:10]],
                   "lanes": {k: v for k, v in (v1.get("lanes") or {}).items()
                             if isinstance(v, dict)}},
            "v2": {"status": v2["status"],
                   "pool_size": len(v2["items"]),
                   "pool_titles": [it.get("title", "")[:80]
                                   for it in v2["items"][:20]],
                   "canonical_pool_size": len(v2_canonical),
                   "sources_attempted": stats.get("sources_attempted"),
                   "sources_succeeded": stats.get("sources_succeeded"),
                   "sources_failed": stats.get("sources_failed"),
                   "sources_rate_limited": stats.get("sources_rate_limited"),
                   "unique_source_families": div.get(
                       "unique_source_families"),
                   "independent_source_families": div.get(
                       "independent_source_families"),
                   "source_independence_score": div.get(
                       "source_independence_score"),
                   "coverage_by_lane": div.get("coverage_by_evidence_lane"),
                   "coverage_by_publication_status": div.get(
                       "coverage_by_publication_status"),
                   "retrieval_blind_spots": (v2.get("report") or {}).get(
                       "retrieval_blind_spots")},
            "targets": {"v1_hits": v1_hits, "v2_hits": v2_hits},
            "noise": {"v1": {k: v for k, v in v1_noise.items()
                            if k != "relevant_titles"},
                      "v2": {k: v for k, v in v2_noise.items()
                            if k != "relevant_titles"}},
            "v2_unique_relevant_items": v2_unique_relevant,
        }
        problems_out.append(problem_out)
        n_v1 = sum(1 for h in v1_hits if h["found"])
        n_v2 = sum(1 for h in v2_hits if h.get("found_in_evidence_pool"))
        n_v2c = sum(1 for h in v2_hits
                    if h.get("found_in_evidence_pool")
                    or h.get("found_in_canonical_pool"))
        print(f"    V1: {len(v1['items'])} items, targets found {n_v1}/"
              f"{len(v1_hits)}, fp_rate={v1_noise['fp_rate']}")
        print(f"    V2: {len(v2['items'])} items (canonical "
              f"{len(v2_canonical)}), targets found {n_v2} in pool / "
              f"{n_v2c} incl. canonical, fp_rate={v2_noise['fp_rate']}")
        print(f"    V2 families: {len(div.get('unique_source_families', []))}"
              f" unique / {div.get('independent_source_families')} "
              f"independent (score {div.get('source_independence_score')})")
        time.sleep(2.0)

    # ---- aggregate headline numbers ----
    all_targets_v1 = [h for p in problems_out
                      for h in p["targets"]["v1_hits"]]
    all_targets_v2 = [h for p in problems_out
                      for h in p["targets"]["v2_hits"]]
    recall_v1 = (sum(1 for h in all_targets_v1 if h["found"])
                 / len(all_targets_v1)) if all_targets_v1 else 0.0
    recall_v2_pool = (sum(1 for h in all_targets_v2
                          if h.get("found_in_evidence_pool"))
                      / len(all_targets_v2)) if all_targets_v2 else 0.0
    recall_v2_any = (sum(1 for h in all_targets_v2
                         if h.get("found_in_evidence_pool")
                         or h.get("found_in_canonical_pool"))
                     / len(all_targets_v2)) if all_targets_v2 else 0.0
    v2_unique_discoveries = [h for p in problems_out
                             for h in p["targets"]["v2_hits"]
                             if (h.get("found_in_evidence_pool")
                                 or h.get("found_in_canonical_pool"))
                             and not any(
                                 g["target_id"] == h["target_id"]
                                 for g in p["targets"]["v1_hits"] if g["found"])]
    fp_v1 = [p["noise"]["v1"]["fp_rate"] for p in problems_out]
    fp_v2 = [p["noise"]["v2"]["fp_rate"] for p in problems_out]
    v2_unique_relevant_total = sum(
        len(p.get("v2_unique_relevant_items", []))
        for p in problems_out)
    failures = sorted({s for p in problems_out
                       for s in (p["v2"].get("sources_failed") or [])})
    rate_limited = sorted({s for p in problems_out
                           for s in (p["v2"].get("sources_rate_limited")
                                     or [])})

    report = {
        "benchmark_id": corpus["benchmark_id"],
        "frozen_at": corpus["frozen_at"],
        "run_started_at": started,
        "run_finished_at": utc_now(),
        "engine_commit": _git_head(),
        "summary": {
            "targets_total": len(all_targets_v2),
            "v1_target_recall": round(recall_v1, 4),
            "v2_target_recall_evidence_pool": round(recall_v2_pool, 4),
            "v2_target_recall_incl_canonical_pool": round(recall_v2_any, 4),
            "v2_unique_target_discoveries": len(v2_unique_discoveries),
            "v2_unique_discovery_target_ids": [
                h["target_id"] for h in v2_unique_discoveries],
            "v2_unique_relevant_item_count": v2_unique_relevant_total,
            "v2_unique_relevant_item_examples": [
                t for p in problems_out
                for t in p.get("v2_unique_relevant_items", [])[:5]][:12],
            "false_positive_rate_v1": fp_v1,
            "false_positive_rate_v2": fp_v2,
            "retrieval_failures": failures,
            "retrieval_rate_limited": rate_limited,
        },
        "problems": problems_out,
        "constitution_compliance": {
            "art_xxi": "search activity is not evidence; recall measured "
                       "against frozen recorded ground truth, noise with "
                       "the frozen adjudicator",
            "art_xxv": "provider failures recorded explicitly (never "
                       "absence)",
            "art_lxii": "replayable from clean checkout: committed corpus + "
                        "registry + pipelines + this script",
        },
    }
    if out_path:
        p = Path(out_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2, default=str))
        print(f"\nbenchmark report -> {p}")
    return report


def _git_head() -> str:
    import subprocess
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:  # noqa: BLE001
        return "unknown"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(
        REPO_ROOT / "R409" / "RETRIEVAL_BENCH"
        / "fabric_benchmark_report.json"))
    args = ap.parse_args()
    run_benchmark(args.out)


if __name__ == "__main__":
    main()
