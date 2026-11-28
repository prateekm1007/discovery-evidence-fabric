#!/usr/bin/env python3
"""Register claim c-0191 (r125-f31e-clean-confirmation) OPEN."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r125-f31e-clean-confirmation":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
next_id = f"c-{max(int(c['claim_id'][2:]) for c in d['claims']) + 1:04d}"
claim = {
    "work_id": "r125-f31e-clean-confirmation",
    "claim_id": next_id,
    "role": "EXECUTOR",
    "session_id": "builder-r117s1",
    "kind": "one_shot",
    "status": "OPEN",
    "base_sha": base,
    "lease_expiry": "2026-11-29T23:59:00Z",
    "artifact_paths": [
        "eval/r125_f31e_set/",
        "eval/r125_f31e_prereg.json",
        "eval/r125_f31e_run/",
        "scripts/r125_build_f31e_set.py",
        "scripts/r125_f31e_run.py",
        "scripts/r125_f31e_score.py",
    ],
    "title": "Dir 2 (the R125 verdict, TOP): the CLEAN score-9 "
             "acceptance run — the F31e set (12 NEW scenarios x 2 "
             "items, programmatic disjointness from the F31c domains, "
             "the F30 families, the battery packets and the 69-firing "
             "F97 calibration corpus — the verdict's 'fresh F31d set' "
             "= THIS F31e record; the F31d label is taken by the "
             "c-0188 run, pushed pre-adjudication). TWO independent "
             "bare-author draws over the frozen set (48 author calls "
             "fixed, the frozen r118 authoring-directive bytes) + the "
             "improved-directive reviewer arm under the CANONICAL "
             "F97-fixed detector (<= 48 reviewer calls, no-findings "
             "items deliver themselves at zero cost). The gates (seed "
             "127): pooled successor <= 0.25 AND the pooled paired CI "
             "excludes 0 below bare AND pooled damage <= 0.25 -> "
             "score-9 axis ACCEPTED; else typed honest negative. "
             "Ordering: the set + the prereg + this claim in ONE push "
             "BEFORE any run byte.",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "notes": "No competing claim (checked: no OPEN claim on this "
             "work_id). Zero LLM, zero network in THIS push (set "
             "builder + prereg + claim only).",
}
d["claims"].append(claim)
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print(f"claim {claim['claim_id']} registered OPEN "
      f"({claim['work_id']}), base {base}")
