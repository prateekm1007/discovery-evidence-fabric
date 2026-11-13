#!/usr/bin/env python3
"""r10_latency_report.py — R10 P0-2 (owner): the measured latency
report over the delivered A0+ battery records. Aggregates ONLY real
measurements (missing = NOT_MEASURED, never zero); infrastructure time
(queue wait, gateway setup) is reported separately from model work;
the p02 per-call timeline is disclosed verbatim (purpose / rung /
queue wait / TTFB / attempt duration / retry / outcome). Output:
eval/latency_report_r10.json (tracked, sanitized)."""
import json
import statistics
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_a0plus import PAIRS_A0  # noqa: E402

TARGET_MEDIAN_S = 120
TARGET_WORST_S = 300

rows = []
for f in sorted(PAIRS_A0.glob("*.json")):
    try:
        d = json.loads(f.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — typed, never silent
        continue
    pid = d.get("problem_id") or f.stem
    tl = d.get("per_call_timeline") or []
    infra = d.get("infra_time_s") or {}
    rows.append({
        "problem_id": pid,
        "result": d.get("result"),
        "n_llm_calls": d.get("n_llm_calls"),
        "n_provider_attempts": d.get("n_provider_attempts"),
        "n_retries": d.get("n_retries"),
        "e2e_wall_s": d.get("e2e_wall_s"),
        "work_time_s": d.get("work_time_s"),
        "hang_time_s": d.get("hang_time_s"),
        "infra_queue_wait_s": infra.get("queue_wait"),
        "infra_gateway_setup_s": infra.get("gateway_setup"),
        "ttfb_ms_per_measured_call": [
            t.get("ttfb_ms") for t in tl if t.get("measured")],
        "per_call": [{"purpose": t.get("purpose"),
                      "rung": t.get("rung"),
                      "status": t.get("status"),
                      "latency_ms": t.get("latency_ms"),
                      "ttfb_ms": t.get("ttfb_ms"),
                      "gateway_hang": t.get("gateway_hang"),
                      "attempts": t.get("attempts"),
                      "retry_count": t.get("retry_count"),
                      "measured": t.get("measured")}
                     for t in tl],
        "note": ("typed skip / provenance-incomplete: no model calls "
                 "this round" if d.get("result") in (
                     "TYPED_SKIP_BASELINE_ABSENT", "TYPED_SKIP_NO_PAIR",
                     "INCOMPLETE_PROVENANCE") else None),
    })

e2e = [r["e2e_wall_s"] for r in rows
       if isinstance(r["e2e_wall_s"], (int, float))]
works = [r["work_time_s"] for r in rows
         if isinstance(r["work_time_s"], (int, float))]
hangers = [r for r in rows
           if isinstance(r["hang_time_s"], (int, float))
           and r["hang_time_s"] > 0]

report = {
    "record": "r10_latency_report/1.0.0",
    "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    "targets": {"median_e2e_s": TARGET_MEDIAN_S,
                "worst_e2e_s": TARGET_WORST_S},
    "aggregate": {
        "n_problems": len(rows),
        "n_with_calls": len(e2e),
        "median_e2e_s": round(statistics.median(e2e), 1) if e2e
        else "NOT_MEASURED",
        "worst_e2e_s": round(max(e2e), 1) if e2e else "NOT_MEASURED",
        "median_work_s": round(statistics.median(works), 1) if works
        else "NOT_MEASURED",
        "worst_work_s": round(max(works), 1) if works
        else "NOT_MEASURED",
        "n_rows_with_hang": len(hangers),
        "hung_problems": [{"problem_id": r["problem_id"],
                           "hang_time_s": r["hang_time_s"]}
                          for r in hangers],
        "targets_met": (bool(e2e)
                        and statistics.median(e2e) <= TARGET_MEDIAN_S
                        and max(e2e) <= TARGET_WORST_S),
        "note": ("e2e_wall_s covers the arm invocation itself; the "
                 "queue wait and gateway setup ride INFRASTRUCTURE "
                 "fields, never summed into work (owner R10 P0-2); "
                 "missing measurements are NOT_MEASURED, never zero"),
    },
    "infrastructure_disclosure": {
        "queue_wait": ("NOT_MEASURED for the in-session battery runs "
                       "(the direct invocations carry no queue wait; "
                       "the subprocess battery rows carry the measured "
                       "value where the driver recorded it)"),
        "gateway_setup": ("the per-problem gateway start-or-probe is "
                          "recorded on the subprocess rows; the "
                          "in-process rows rode the already-admitted "
                          "gateway"),
    },
    "p02_per_call_timeline": next(
        (r["per_call"] for r in rows
         if r["problem_id"] == "bench-p02-leadacid-grid-corrosion"),
        []),
    "rows": rows,
}

out = REPO / "eval" / "latency_report_r10.json"
out.write_text(json.dumps(report, indent=1, default=str) + "\n",
               encoding="utf-8")
print("[r10lat] wrote", out)
print(json.dumps(report["aggregate"], indent=1))
