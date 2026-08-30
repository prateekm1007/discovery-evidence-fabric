#!/usr/bin/env python3
"""Run the QUERY_RELEVANCE / TEMPORAL_SPAN battery live (CEO directive
2026-08-30: "finish source maturity, not source count").

Reproduction:  python3 scripts/toscanini_query_relevance_probe.py [--timeout 30]

Runs the fixed battery in discovery_fabric/source_registry/query_relevance.py
against every non-metered connector, aggregates per-record adjudications,
and writes TOSCANINI/QUERY_RELEVANCE_PROBES.json (committed instrument
output — builder-measured per Art. XXVI; the script IS the reproduction
command).

Every live query goes through ConnectorBase.search() -> _execute(), so the
full Art. XXI.9 custody chain (query -> provider -> raw hash -> records)
lands in artifacts/source_health/retrieval_log.jsonl automatically.

Metered sources are NEVER probed (quota discipline). Sources whose
connectors are absent are skipped (disclosed in BATTERY_EXCLUSIONS).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from discovery_fabric.source_registry import query_relevance as qr  # noqa: E402
from discovery_fabric.source_registry.health import load_connector  # noqa: E402
from discovery_fabric.source_registry.registry import SOURCE_REGISTRY  # noqa: E402

OUT_PATH = REPO / "TOSCANINI" / "QUERY_RELEVANCE_PROBES.json"

# Courtesy interval between live calls (seconds) — arXiv asks 1 per 3s;
# one uniform conservative interval keeps the battery polite everywhere.
COURTESY_S = 3.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeout", type=int, default=30)
    ap.add_argument("--only", type=str, default=None,
                    help="comma-separated source ids (debug)")
    args = ap.parse_args()

    results: dict = {}
    run_log: list = []
    order = list(qr.BATTERY.keys())
    if args.only:
        order = [s for s in order if s in args.only.split(",")]

    for sid in order:
        rec = SOURCE_REGISTRY.get(sid)
        if rec is None:
            run_log.append({"source_id": sid, "skipped": "not in registry"})
            continue
        if rec.get("metered_quota"):
            run_log.append({"source_id": sid, "skipped": "metered — policy"})
            continue
        conn = load_connector(sid)
        if conn is None:
            run_log.append({"source_id": sid,
                            "skipped": "no connector (absent/blocked — "
                                       "see BATTERY_EXCLUSIONS)"})
            continue
        conn = conn()  # load_connector returns the CLASS; health.py instantiates at call sites
        qresults = []
        for q in qr.BATTERY[sid]:
            t0 = time.time()
            try:
                r = conn.search(q, timeout=args.timeout)
                d = r.to_dict()
                qresults.append({
                    "query": q,
                    "status": d["status"],
                    "http_status": d["http_status"],
                    "latency_ms": d["latency_ms"],
                    "error": d["error"],
                    "total_hits": d.get("total_hits"),
                    "records": d["records"],
                })
                run_log.append({
                    "source_id": sid, "query": q, "status": d["status"],
                    "record_count": d["record_count"],
                    "latency_ms": d["latency_ms"], "error": d["error"],
                })
            except Exception as e:  # noqa: BLE001 — surface, never swallow
                qresults.append({"query": q, "status": "SEARCH_FAILED",
                                 "error": f"probe exception: {e!r}",
                                 "records": []})
                run_log.append({"source_id": sid, "query": q,
                                "status": "EXCEPTION", "error": repr(e)})
            time.sleep(COURTESY_S)
        results[sid] = qresults
        n_ok = sum(1 for x in qresults if x["status"] == "OK")
        print(f"[battery] {sid:28s} queries={len(qresults)} ok={n_ok}",
              flush=True)

    agg = qr.aggregate(results)
    grades = {sid: qr.grade_query_relevance(a) for sid, a in agg.items()}

    # Persist this battery run's per-source adjudications through the SAME
    # custody path as pipeline adjudications (maturity §6.1 closure: one
    # recording path, one aggregation). run_id marks the origin so usage
    # aggregation can always separate battery traffic from pipeline traffic.
    from discovery_fabric.source_registry import relevance_aggregation
    for sid, a in agg.items():
        for pq in a["queries"]:
            try:
                relevance_aggregation.record_adjudications(
                    source_id=sid,
                    query=pq["query"],
                    adjudicated_records=pq["adjudications"],
                    run_id="battery:QUERY_RELEVANCE_PROBES",
                    provider_status=pq.get("status"),
                )
            except Exception as e:  # noqa: BLE001 — surface, never swallow
                print(f"[battery] custody append failed {sid}: {e!r}")

    # merge with any previous chunk run (the battery runs in chunks; each
    # chunk's sources accumulate into one artifact)
    if OUT_PATH.exists():
        try:
            prev = json.loads(OUT_PATH.read_text())
            if prev.get("artifact") == "QUERY_RELEVANCE_PROBES":
                prev_agg = prev.get("aggregates", {})
                prev_grades = prev.get("grades", {})
                prev_log = prev.get("run_log", [])
                for sid, a in prev_agg.items():
                    if sid not in agg:
                        agg[sid] = a
                for sid, g in prev_grades.items():
                    if sid not in grades:
                        grades[sid] = g
                run_log = prev_log + run_log
        except Exception as e:  # noqa: BLE001 — merge failure = surface
            print(f"[battery] merge with previous artifact failed: {e!r}")

    out = {
        "artifact": "QUERY_RELEVANCE_PROBES",
        "directive": "CEO 2026-08-30 — finish source maturity: measure "
                     "query_relevance (and harvest temporal_coverage) "
                     "per source",
        "method": "fixed committed battery (query_relevance.BATTERY); "
                  "per-record adjudication by term-overlap >= 2 (same rule "
                  "as the discovery pipeline) or STRUCTURAL for "
                  "parameterized endpoints; grades are ENGINEERING bands "
                  "declared in the module docstring (Art. XXVII)",
        "reproduction": "python3 scripts/toscanini_query_relevance_probe.py",
        "metered_policy": "metered sources are never live-probed "
                          "(quota discipline); they stay UNMEASURED here",
        "aggregates": agg,
        "grades": grades,
        "battery_exclusions": qr.BATTERY_EXCLUSIONS,
        "run_log": run_log,
    }
    OUT_PATH.write_text(json.dumps(out, indent=1, ensure_ascii=False))
    print(f"[battery] wrote {OUT_PATH}")
    n_measured = sum(1 for g in grades.values() if g["basis"] == "MEASURED")
    print(f"[battery] measured {n_measured}/{len(grades)} sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
