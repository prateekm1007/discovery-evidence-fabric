#!/usr/bin/env python3
"""Register session builder-r130s3 + claim c-0209 (OPEN) — the Art.
29(b) claim-before-work for the dir-3 diff-minimization fold (the R130
verdict; the held-out no-regression re-test gates the fold). The claim
push is the lock."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r130s3-diffmin-fold":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
if "builder-r130s3" not in d.get("sessions", {}):
    d["sessions"]["builder-r130s3"] = {
        "note": "R130 session-3: the dir-3 window (the R130 auditor "
                "verdict) — the diff-minimization fold gated by the "
                "held-out no-regression re-test + the mechanism "
                "knowledge base + dir 8 (m1/m4 dropped from the "
                "candidate pool, recorded not deleted). Dir 1 held: "
                "the constitution byte-identity re-verified at "
                "f85ffe556 (0-line diff 6f97f8311..f85ffe556; the "
                "auditor's adjudication 2aed5305d8bf touched only its "
                "own JSON). Dir 2 (GEPA round-2) cross-referenced to "
                "the twin's lane — UNCLAIMED at window start, never "
                "duplicated (Art. 29(c)). BoN round-2 DONE this lane "
                "at c-0208 (ADOPT). Dirs 4/5 owner-gated; dir 6 "
                "auditor-authored.",
        "registered_at": NOW,
        "role": "builder"}
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
cnt = (open(f"{REPO}/eval/claim_next_id.txt").read().strip())
for c in d["claims"]:
    if c.get("claim_id") == cnt:
        raise SystemExit(f"REFUSED: claim id {cnt} already used")
claim = {
    "work_id": "r130s3-diffmin-fold",
    "claim_id": cnt,
    "role": "EXECUTOR",
    "session_id": "builder-r130s3",
    "kind": "task",
    "status": "OPEN",
    "base_sha": base,
    "lease_expiry": "2026-11-29T23:59:00Z",
    "claimed_at": NOW,
    "artifact_paths": [
        "eval/r130s3_diffmin_prereg.json",
        "eval/r130s3_diffmin_replay/",
        "eval/r130s3_diffmin_scoring.json",
        "eval/MECHANISM_FINDINGS.json",
        "scripts/r130s3_diffmin_replay.py",
        "scripts/r130s3_diffmin_score.py",
    ],
    "title": "Dir 3 (the R130 verdict): fold the diff-minimization "
             "clause into the canonical reviewer directive — v2 = v1 "
             "+ M5 (byte-identical to the twin's m5_minimal "
             "composition), gated by the held-out no-regression "
             "re-test: v1 vs v2 PAIRED live replays over the 48 "
             "committed F31e pre-review bills (disjoint from the "
             "GEPA compile corpus), leg mechanics byte-reused from "
             "the twin's committed harness. FOLD iff v2 defect rows "
             "<= v1 AND v2 heal >= v1 (paired) AND typed-fails <= 2; "
             "the GEPA round-2 incumbent baseline stays the FROZEN "
             "v1 bytes (sha-pinned) — typed reconciliation with dir "
             "2. The finding lands in eval/MECHANISM_FINDINGS.json "
             "(created; incl. dir 8: m1/m4 dropped from the pool, "
             "recorded not deleted). Order: prereg + this claim in "
             "ONE push (the lock; refs/claims/next rides it), then "
             "the re-test, then the gated fold + KB + close.",
}
d["claims"].append(claim)
json.dump(d, open(path, "w"), indent=1)
nxt = f"c-{int(cnt[2:]) + 1:04d}"
open(f"{REPO}/eval/claim_next_id.txt", "w").write(nxt + "\n")
print(f"registered {cnt} (base {base}); counter -> {nxt}")
