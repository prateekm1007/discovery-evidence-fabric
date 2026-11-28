#!/usr/bin/env python3
"""R123 claim registration (Art. 29(b) claim-before-work): the score-9
FRESH held-out confirmation run (the R122 direction 2). Registers
c-0183 OPEN; the set + prereg + claim commit in ONE push BEFORE any
run byte."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r123-fresh-confirmation-run":
        raise SystemExit(f"REFUSED (typed): claim exists: "
                         f"{c.get('claim_id')} status={c.get('status')}")
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
remote = subprocess.run(
    ["git", "rev-parse", "--short", "origin/queue/dev12_r7"], cwd=REPO,
    capture_output=True, text=True).stdout.strip()
assert base == remote == "cfc5042c5", f"base {base} remote {remote}"

claim = {
    "work_id": "r123-fresh-confirmation-run",
    "claim_id": "c-0183",
    "role": "EXECUTOR",
    "session_id": "builder-r117s1",
    "kind": "one_shot",
    "status": "OPEN",
    "base_sha": base,
    "lease_expiry": "2026-11-26T23:59:00Z",
    "artifact_paths": [
        "eval/r123_fresh_set/",
        "eval/r123_fresh_confirmation_prereg.json",
        "eval/r123_fresh_run/",
        "scripts/r123_build_fresh_set.py",
        "scripts/r123_fresh_run.py",
        "scripts/r123_fresh_score.py",
    ],
    "title": "Dir 2 (the R122 verdict): the score-9 FRESH held-out "
             "confirmation — the F31c run of the successor shape (bare "
             "author + bind check + bare reviewer fixes) vs bare-only "
             "on the FRESH 24-item engineering set "
             "(eval/r123_fresh_set, 12 new disjoint domains x 2 draws, "
             "no defect ground truth seeded — the amendment-1 "
             "detectors are the only defect definition). Accept per "
             "the enacted axis: successor rate <= 0.25 AND the paired "
             "bootstrap CI excludes 0 below bare AND damage <= 0.25 -> "
             "score-9 axis accepted; else typed negative + the axis "
             "question returns to the auditor. The reviewer directive "
             "is the F31b FIX_DIRECTIVE bytes imported unchanged (the "
             "dir-3 residual-class lever must not confound this "
             "confirmation). Ordering: set + prereg + claim in ONE "
             "push BEFORE any run byte; 48 calls worst case, byte-skip "
             "resume, INFRA_QUOTA_WALL typed if closed.",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "notes": "No competing claim (checked: the registry's last claim "
             "c-0182 is DONE; no OPEN claim on this work_id). "
             "Diff-against-remote before each push (Art. 29(e)).",
}
d["claims"].append(claim)
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print(f"claim c-0183 registered OPEN, base {base}, "
      f"claims now {len(d['claims'])}")
