#!/usr/bin/env python3
"""End-to-end dress rehearsal of the R506 harvest pipeline:
driver-shaped measurement (scratch fixture) -> r506_harvest_rules.py attach
-> assert merge contract (sections added; rows/aggregate byte-identical;
pre_merge_sha256 recorded; self-attestation passes). Uses the REAL R484
terminal run bytes for the contamination row. Nothing touches R506/."""
import hashlib
import json
import os
import shutil
import subprocess
import sys

import os as _os
REPO = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
WORKTREE = "/home/z/my-project/r506_durable"  # the durability worktree (local, Art. LXXIV)
import tempfile
SCRATCH = tempfile.mkdtemp(prefix="r506_rehearsal_")

shutil.rmtree(SCRATCH, ignore_errors=True)
os.makedirs(SCRATCH)

fails = []


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f" | {detail}" if detail else ""))
    if not cond:
        fails.append(name)


# driver-shaped measurement: one harvested row (R484 run, real bytes) + one
# not-yet-on-branch row (typed), exactly like r506_battery_driver.harvest emits
slug = "toscanini_ui_ui_calcite_and_silica_gel_deposition_on_separ_602181"
row_file = os.path.join(SCRATCH, f"YIELD_ROW_0_{slug}.json")
r = subprocess.run(
    ["python3", os.path.join(REPO, "scripts", "r506_discovery_yield.py"),
     "--run-dir", os.path.join(WORKTREE, "runs", slug), "--out", row_file],
    capture_output=True, text=True)
check("frozen instrument runs on real durable bytes", r.returncode == 0,
      r.stderr[-120:] if r.returncode else "")
inner = json.load(open(row_file, encoding="utf-8"))["rows"][0]

meas = {
    "artifact_type": "R506_YIELD_MEASUREMENT",
    "battery": "R506-discovery-yield",
    "instrument": "r506_discovery_yield/1.0.0",
    "instrument_sha256": hashlib.sha256(open(
        os.path.join(REPO, "scripts", "r506_discovery_yield.py"), "rb").read()).hexdigest(),
    "harvested_at_utc": "SCRATCH-REHEARSAL-NOT-A-MEASUREMENT",
    "rows": [
        {"problem_index": 0, "source_id": "scratch", "session_id": "ts_rehearsal",
         "declared_family": "mechanical", "run_slug": slug,
         "row_file": "scratch", "row": inner},
        {"problem_index": 2, "source_id": "odi:11746712",
         "session_id": "ts_ca977637f50b",
         "harvest": "NOT_YET_ON_DURABLE_BRANCH_OR_UNKNOWN"},
    ],
    "aggregate": {"n_rows": 2, "note": "scratch rehearsal"},
    "reviewer_provenance": "AI_REVIEW",
}
meas_path = os.path.join(SCRATCH, "YIELD_MEASUREMENT.json")
with open(meas_path, "w", encoding="utf-8") as f:
    json.dump(meas, f, indent=1, ensure_ascii=False)
pre_sha = hashlib.sha256(open(meas_path, "rb").read()).hexdigest()

# check-only observer pass
r0 = subprocess.run(
    ["python3", os.path.join(REPO, "scripts", "r506_harvest_rules.py"),
     "--measurement", meas_path, "--worktree", WORKTREE,
     "--rules", os.path.join(REPO, "R506", "HARVEST_RULES.json"),
     "--check-only"], capture_output=True, text=True, cwd=REPO)
check("check-only pass exit 0", r0.returncode == 0, r0.stdout[-200:])
check("check-only wrote nothing",
      hashlib.sha256(open(meas_path, "rb").read()).hexdigest() == pre_sha)

# real attach (in-place)
r1 = subprocess.run(
    ["python3", os.path.join(REPO, "scripts", "r506_harvest_rules.py"),
     "--measurement", meas_path, "--worktree", WORKTREE,
     "--rules", os.path.join(REPO, "R506", "HARVEST_RULES.json")],
    capture_output=True, text=True, cwd=REPO)
check("attach pass exit 0", r1.returncode == 0, r1.stdout[-300:])

merged = json.load(open(meas_path, encoding="utf-8"))
check("contamination_audit attached", "contamination_audit" in merged)
check("clarification_audit attached", "clarification_audit" in merged)
check("harvest_rules attached", "harvest_rules" in merged)
check("pre_merge_sha256 recorded correctly",
      merged["harvest_rules"]["pre_merge_sha256"] == pre_sha)
check("rows byte-identical post-merge",
      json.dumps(merged["rows"], sort_keys=True)
      == json.dumps(meas["rows"], sort_keys=True))
check("aggregate byte-identical post-merge",
      json.dumps(merged["aggregate"], sort_keys=True)
      == json.dumps(meas["aggregate"], sort_keys=True))

runs = merged["contamination_audit"]["runs"]
r484 = [v for v in runs.values() if v.get("run_slug") == slug]
check("real R484 row verdict CLEAN", r484 and r484[0]["verdict"] == "CLEAN",
      r484[0]["verdict"] if r484 else "row missing")
mid = [v for v in runs.values() if v.get("run_slug") is None]
check("unharvested row typed RUN_BYTES_ABSENT",
      mid and mid[0].get("typed") == "RUN_BYTES_ABSENT_ON_DURABLE_WORKTREE")
cl = merged["clarification_audit"]["runs"]
rehearsal = [v for v in cl.values() if v.get("session_id") == "ts_rehearsal"]
check("clarification absent typed honestly",
      rehearsal and rehearsal[0]["verdict"]
      == "CLARIFICATION_BYTES_ABSENT_IN_DURABLE_RECORD")

# tamper probe: a mutated rules script must fail closed
rules_script = os.path.join(REPO, "scripts", "r506_harvest_rules.py")
tampered = os.path.join(SCRATCH, "tampered_rules.py")
src = open(rules_script, encoding="utf-8").read()
open(tampered, "w", encoding="utf-8").write(
    src.replace('RULES_VERSION = "1.0.0"', 'RULES_VERSION = "9.9.9"'))
r2 = subprocess.run(
    ["python3", tampered, "--measurement", meas_path, "--worktree", WORKTREE,
     "--rules", os.path.join(REPO, "R506", "HARVEST_RULES.json"),
     "--check-only"], capture_output=True, text=True, cwd=REPO)
check("tampered script fails closed (exit 2)", r2.returncode == 2,
      r2.stdout.strip()[:100])

shutil.rmtree(SCRATCH, ignore_errors=True)
print()
print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAILURES: {fails}")
sys.exit(1 if fails else 0)
