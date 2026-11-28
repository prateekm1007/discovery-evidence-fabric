#!/usr/bin/env python3
"""Register session builder-r130s2 + claim c-0208 (OPEN) — the Art.
29(b) claim-before-work for the BoN round-2 PARITY (the typed
next-window slice of the c-0205 close: 'BoN round-2 parity — the
CLASS decision'; cross-referenced by the twin's R130 close, Art.
29(c), never duplicated). The claim push is the lock."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r130s2-bon2-parity":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
if "builder-r130s2" not in d.get("sessions", {}):
    d["sessions"]["builder-r130s2"] = {
        "note": "R130 session-2 (the second lane of the R130 window): "
                "the BoN round-2 48-row PARITY replication — the typed "
                "next-window slice of the c-0205 close, cross-"
                "referenced by the twin's R130 close (Art. 29(c); the "
                "GEPA round 2 stays the twin's lane). Dir 1 (the FULL "
                "constitution read) and dir 6 (the bounded HF credit "
                "probe, FUNDED_HEADROOM_EXISTS) completed pre-claim in "
                "this window chain. Dirs 2/3 (AWS host, score-8 panel) "
                "owner-gated — typed, unattempted beyond the vault "
                "AWS-key check; dir 4 (v16 sealed set) auditor-"
                "authored — untouched.",
        "registered_at": NOW,
        "role": "builder"}  # the registry schema requires a session
    # role (test_registry_schema_valid; the CI red 137267892171 class)
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
# the committed counter file is the allocation authority (r128 dir-1)
cnt = (open(f"{REPO}/eval/claim_next_id.txt").read().strip())
for c in d["claims"]:
    if c.get("claim_id") == cnt:
        raise SystemExit(f"REFUSED: claim id {cnt} already used")
claim = {
    "work_id": "r130s2-bon2-parity",
    "claim_id": cnt,
    "role": "EXECUTOR",
    "session_id": "builder-r130s2",
    "kind": "task",
    "status": "OPEN",
    "base_sha": base,
    "lease_expiry": "2026-11-29T23:59:00Z",
    # the registry validator (test_registry_schema_valid) requires
    # claimed_at on every claim (the CI red 137267892171 class)
    "claimed_at": NOW,
    "artifact_paths": [
        "eval/r130s2_bon2_parity_prereg.json",
        "eval/r130s2_bon_parity_run/",
        "eval/r130s2_bon_parity_scoring.json",
        "scripts/r130s2_bon_parity_run.py",
        "scripts/r130s2_byte_precheck.py",
        "scripts/r130s2_bon_parity_score.py",
    ],
    "title": "Dir 5 continuation (the R129 verdict): the BoN round-2 "
             "48-row PARITY — the Art. 20 CLASS decision for the "
             "bon2-bindselect arm (round 1 WON 0/24 vs 2/48 at "
             "builder-r129s1). The arm runs BYTE-IDENTICAL to round 1 "
             "(delegation to the committed r129_bon_run legs; the only "
             "variable is the independent replication) -> POOLED 48 "
             "arm rows (24 round-1 selected rows re-tallied from "
             "committed bytes + 24 new) vs the incumbent's 48 "
             "committed F31e rows. ADOPT iff pooled strictly < 2, "
             "else DELETE (Art. 20). Pins reproduced pre-prereg by "
             "the committed zero-LLM precheck (incumbent 2/48 + "
             "round-1 arm 0/24 from bytes). Order: prereg + this "
             "claim in ONE push (the lock; refs/claims/next rides "
             "it), then the run, then the committed scorer + "
             "registry update + close.",
}
d["claims"].append(claim)
json.dump(d, open(path, "w"), indent=1)
nxt = f"c-{int(cnt[2:]) + 1:04d}"
open(f"{REPO}/eval/claim_next_id.txt", "w").write(nxt + "\n")
print(f"registered {cnt} (base {base}); counter -> {nxt}")
