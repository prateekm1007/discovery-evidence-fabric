#!/usr/bin/env python3
"""Register session builder-r134s2 + claim c-0214 (OPEN) — the Art.
29(b) claim-before-work for the typed DIR 2 resume (the twin's frozen
round-3 contract; no scope change). ALSO: the counter-authority
reconciliation (the R131-F5 divergence — refs/claims/counter stale at
203 while the claims ledger advanced to c-0213): this script writes
claim_counter=214 at the repo root; the lock push carries it to BOTH
refs/heads/queue/dev12_r7 and refs/claims/counter in ONE push."""
import datetime
import json
import subprocess
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = REPO / "eval" / "work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r134s2-panel-resume":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
ids = {c.get("claim_id") for c in d["claims"]}
if "c-0214" in ids:
    raise SystemExit("REFUSED: c-0214 already allocated")
if "builder-r134s2" not in d.get("sessions", {}):
    d["sessions"]["builder-r134s2"] = {
        "note": "R134 session-2: the typed DIR 2 resume (the twin's "
                "frozen round-3 contract, byte-resume + the typed "
                "transport-retry pass; no scope change) + the "
                "counter-authority reconciliation (R131-F5) + the "
                "D2 close-push quote for the twin's 3e3a0a00b "
                "(137549621477 SUCCESS — their typed 'next "
                "window's first act'). DIR 1 held: both "
                "constitutions digest-verified at the named SHAs "
                "(153ac62efca36c2d / 3775f869a1c19a96).",
        "registered_at": NOW,
        "role": "builder"}
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"],
                      cwd=REPO, capture_output=True,
                      text=True).stdout.strip()
claim = {
    "work_id": "r134s2-panel-resume",
    "claim_id": "c-0214",
    "role": "EXECUTOR",
    "session_id": "builder-r134s2",
    "kind": "task",
    "status": "OPEN",
    "base_sha": base,
    "lease_expiry": "2026-11-29T23:59:00Z",
    "claimed_at": NOW,
    "artifact_paths": [
        "eval/r134s2_resume_prereg.json",
        "eval/r134_panel/ (byte-resumed legs + __retry1 records)",
        "eval/r134_panel_calibration.json",
        "eval/r134s2_status.json",
        "scripts/r134s2_dsr1_retry.py",
        "claim_counter (214; also pushed to refs/claims/counter)",
    ],
    "title": "R134 session-2: the typed DIR 2 resume under the twin's "
             "FROZEN round-3 contract (c-0213, be4eb8794): byte-resume "
             "the 16 missing llama4mav legs (disk truth; the close's "
             "'6/20' honestly corrected to 4/20) + the ONE-attempt "
             "transport-retry pass for the 3 dsr1 504 legs and any "
             "llama4mav transport fails (__retry1 files, VALID-only "
             "supersede, canonical bytes never mutated) + the "
             "counter-authority reconciliation (203 -> 214). HONEST "
             "DETERMINATION TYPED BEFORE THE RUN: the >=3-qualified "
             "gate is mathematically unreachable (three complete "
             "judges below 0.8) — expected verdict NOT_MET; the run "
             "completes the instrument (llama4mav n=4 unproven), the "
             "delta table, and the agreement/AUC data for the "
             "auditor's ~20-30 corpus enlargement. No bar lowering, "
             "no label tuning. Order: prereg + this claim in ONE "
             "push (the lock; refs/claims/counter rides it), then "
             "the run, then the recompute + gate read + close.",
}
d["claims"].append(claim)
json.dump(d, open(path, "w"), indent=1)
(REPO / "claim_counter").write_text("214\n")
print(f"registered c-0214 (base {base}); claim_counter -> 214 "
      f"(the R131-F5 reconciliation; refs/claims/counter rides the "
      f"lock push)")
