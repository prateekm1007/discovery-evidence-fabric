#!/usr/bin/env python3
"""One-off: merge baseline session files (prefer completed sessions)."""
import json
from pathlib import Path

base = json.loads(Path("R519/BATTERY_SESSIONS_BASELINE.json").read_text(
    encoding="utf-8"))
r2 = json.loads(Path("R519/BATTERY_SESSIONS_BASELINE_R2.json").read_text(
    encoding="utf-8"))
w1r = json.loads(Path("R519/BATTERY_SESSIONS_BASELINE_W1R.json").read_text(
    encoding="utf-8"))
by = {}
for s in base.get("submissions", []):
    by[s["problem_index"]] = s
for s in r2.get("submissions", []):
    by[s["problem_index"]] = s
for s in w1r.get("submissions", []):
    by[s["problem_index"]] = s
merged = {
    "arm": "baseline",
    "battery_name": "R519-routing-AB-baseline-merged",
    "submissions": [by[k] for k in sorted(by)],
}
Path("R519/BATTERY_SESSIONS_BASELINE_MERGED.json").write_text(
    json.dumps(merged, indent=1) + "\n", encoding="utf-8")
print("merged", len(merged["submissions"]))
for s in merged["submissions"]:
    print(s["problem_index"], s["session_id"])
