#!/usr/bin/env python3
"""r128_backoff_recompute.py — the dir-5 recompute as a committed
verifier artifact (claim c-0204): derive the absorbed
transport-backoff count from the COMMITTED Phase-A gate-run bytes.

DERIVATION RULE (typed): a committed leg latency in [119, 135] s
evidences exactly one absorbed 120 s transport-backoff sleep (the
typed 429 refusal is instant at 0.07-0.1 s; the retry calls observed
at 2-10 s; two absorbed sleeps would need >= 239 s — none exist).
The 8 s reviewer spacing sits OUTSIDE the measured leg latency.

CLOSURE CHECK: every per-item wall clock must equal the sum of its
leg latencies + the reviewer spacing within 1 s.

Cross-checks the executor's own dir-5 read (their gate close: 8
legs, 5 reviewer + 3 author; their earlier verifier count of 5 was
reviewer-legs-only and was corrected).

Output: eval/r128_backoff_recompute.json
"""
from __future__ import annotations

import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "r128_backoff_recompute.json"
SPACING_S = 8.0

rows = []
for f in sorted(glob.glob(str(REPO / "eval" / "r127_phaseA"
                           / "gate" / "gate_*.json"))):
    rec = json.loads(Path(f).read_text(encoding="utf-8"))
    legs = rec["calls"]
    llm = sum((c.get("latency_s") or 0.0) for c in legs)
    spacing = SPACING_S if any(c["leg"] == "reviewer"
                               for c in legs) else 0.0
    wall = rec["wall_clock_s"]
    closure = abs(wall - (llm + spacing))
    boffs = [c["leg"] for c in legs
             if 119.0 <= (c.get("latency_s") or 0.0) <= 135.0]
    rows.append({"pid": rec["problem_id"], "wall": wall,
                 "llm_sum": round(llm, 2), "spacing": spacing,
                 "closure_s": round(closure, 2),
                 "evidenced_backoffs": len(boffs),
                 "evidenced_legs": boffs})

total = sum(r["evidenced_backoffs"] for r in rows)
max_closure = max(r["closure_s"] for r in rows)
out = {
    "record": "R128_BACKOFF_RECOMPUTE/1.0.0",
    "claim": "c-0204 (role VERIFIER on "
             "r128-cluster-rescore-and-transports)",
    "derivation_rule": "a committed leg latency in [119,135] s = "
                       "exactly one absorbed 120 s transport "
                       "backoff (instant typed 429 refusal + 120 s "
                       "sleep + a 2-10 s retry; two sleeps would "
                       "need >= 239 s — none exist)",
    "evidenced_backoffs_from_bytes": total,
    "executor_log_prose_figure": 8,
    "figures_agree": total == 8,
    "closure_check": {"max_closure_s": round(max_closure, 2),
                      "rule": "<= 1 s per item",
                      "pass": max_closure <= 1.0},
    "per_item": rows,
    "future_records": "the runner's per-leg transport_attempts "
                      "field (the executor's dir-5 patch) is the "
                      "primary evidence going forward; this "
                      "derivation rule remains the fallback for "
                      "the historical records that lack it",
}
OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
print(f"evidenced backoffs from bytes: {total} "
      f"(the executor's figure: 8) -> agree={total == 8}")
print(f"closure: max {max_closure:.2f}s "
      f"({'PASS' if max_closure <= 1.0 else 'FAIL'} at <=1s)")
for r in rows:
    if r["evidenced_backoffs"]:
        print(f"  {r['pid']}: {r['evidenced_legs']}")
print(f"written: {OUT}")
