#!/usr/bin/env python3
"""r412_v3_run_lanes.py — directive item 3: run the three retrieval
lanes (A/B/C) through the retrieval fabric with the REPAIRED
connectors, persist every pool byte, per lane, per rung.

PLUMBING DISCIPLINE (Art. XLVII — identical instrument across arms):
the fabric invocation is BYTE-IDENTICAL to the v1/v2 runner's
_retrieve(): same problem construction from the query string, same
lane caps (defaults), same enable_reciprocal=False /
enable_unpaywall=False. The ONLY deltas vs the v2 run are (a) the
repaired connectors (a disclosed, root-caused defect fix), (b) the
lane query forms (the experimental variable), (c) FEAL pool
persistence (richer record schema — additive, disclosed).

Incremental + resumable: one checkpoint file per lane query; a
re-invocation skips completed queries (per-query checkpointing, the
R412 durability pattern). No LLM anywhere in this script.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.r412.frontier_evidence import (  # noqa: E402
    all_lane_queries, pool_record_from_item, rungs_from_ga1b,
    FEAL_VERSION,
)

POOLS = REPO / "R412" / "GRADIENT_V3" / "RUN" / "LANE_POOLS"
DONE = POOLS / "_progress.json"


def _slug(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower())
    return s.strip("-")[:60]


def _query_key(q: Dict[str, Any]) -> str:
    """CONTENT-keyed resumption: the key is derived from the query
    STRING (sha8) + lane, not the plan index — so a repaired plan
    (the lane-C UNKNOWN-domain incident) skips unchanged completed
    queries and simply never re-runs removed ones."""
    h = re.sub(r"[^a-z0-9]", "",
               __import__("hashlib").sha256(
                   q["query"].encode()).hexdigest())[:10]
    return f"{_slug(q['rung'])}__{q['lane']}__{h}"


def _retrieve(query: str):
    """BYTE-IDENTICAL plumbing to the v1/v2 runners' _retrieve."""
    from discovery_fabric.retrieval_fabric.pipeline import \
        retrieve_fabric
    problem = {"device": query[:120], "failure_mode":
               query[120:240] or query[:120]}
    items, report = retrieve_fabric(
        problem, lane_caps=None,
        enable_reciprocal=False, enable_unpaywall=False)
    return items, report


def _canonical_by_id(report: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for cr in report.get("canonical_records") or []:
        out[str(cr.get("canonical_id"))] = cr
    return out


def run_lanes(limit: int = 0) -> int:
    rungs = rungs_from_ga1b()
    plan = all_lane_queries(rungs)
    POOLS.mkdir(parents=True, exist_ok=True)
    progress = json.loads(DONE.read_text()) if DONE.exists() else {}
    done_keys = {e["key"] for e in progress.get("completed", [])}
    n_new = 0
    for i, q in enumerate(plan):
        key = _query_key(q)
        if key in done_keys:
            continue
        if limit and n_new >= limit:
            print(f"invocation limit reached ({limit}); "
                  f"remaining queries stay PENDING (resumable)")
            break
        t0 = time.time()
        print(f"[{i + 1}/{len(plan)}] lane {q['lane']} "
              f"rung='{q['rung'][:40]}' q='{q['query'][:60]}...'")
        try:
            items, report = _retrieve(q["query"])
        except Exception as e:
            rec = {"key": key, "status": "INCOMPLETE_TRANSPORT",
                   "error": str(e)[:200], "ts": _now()}
            _append_progress(rec)
            print(f"    INCOMPLETE_TRANSPORT: {str(e)[:80]}")
            continue
        canon = _canonical_by_id(report)
        pool_records = []
        for item in items or []:
            cr = canon.get(str(item.get("id") or
                               item.get("canonical_id")))
            pool_records.append(pool_record_from_item(item, cr))
        entry = {
            "key": key,
            "status": "OK",
            "lane": q["lane"],
            "lane_attribution": q["lane_attribution"],
            "rung": q["rung"],
            "query": q["query"],
            "query_provenance": q.get("query_provenance"),
            "frontier_domain": q.get("frontier_domain"),
            "n_items": len(items or []),
            "n_pool_records": len(pool_records),
            "pool_records": pool_records,
            "retrieval_stats": {
                "fabric_version":
                    report.get("fabric_version"),
                "retrieved_at": report.get("retrieved_at"),
                "lane_states": [
                    {k: v for k, v in (ls or {}).items()
                     if k in ("lane", "source_id", "status",
                              "record_count", "error",
                              "fabric_health")}
                    for ls in (report.get("retrieval_stats")
                               or {}).get("lane_states", [])],
                "sources_attempted":
                    (report.get("retrieval_stats") or {}).get(
                        "sources_attempted"),
                "sources_succeeded":
                    (report.get("retrieval_stats") or {}).get(
                        "sources_succeeded"),
                "sources_failed":
                    (report.get("retrieval_stats") or {}).get(
                        "sources_failed"),
                "sources_rate_limited":
                    (report.get("retrieval_stats") or {}).get(
                        "sources_rate_limited"),
            },
            "retrieval_duration_s": round(time.time() - t0, 2),
            "ts": _now(),
        }
        (POOLS / f"{key}.json").write_text(
            json.dumps(entry, indent=1) + "\n")
        _append_progress({"key": key, "status": "OK",
                          "n_items": len(items or []),
                          "ts": _now()})
        n_new += 1
        print(f"    items={len(items or [])} "
              f"pool_records={len(pool_records)} "
              f"({entry['retrieval_duration_s']}s)")
    total_done = len([e for e in
                      json.loads(DONE.read_text())["completed"]
                      if e.get("status") == "OK"])
    print(f"\nlane run state: {total_done}/{len(plan)} queries "
          f"completed OK; re-run to resume pending queries")
    return 0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _append_progress(rec: Dict[str, Any]) -> None:
    doc = json.loads(DONE.read_text()) if DONE.exists() else \
        {"completed": []}
    doc["completed"].append(rec)
    DONE.write_text(json.dumps(doc, indent=1) + "\n")


if __name__ == "__main__":
    lim = int(sys.argv[1]) if len(sys.argv) > 1 and \
        sys.argv[1].isdigit() else 0
    raise SystemExit(run_lanes(lim))
