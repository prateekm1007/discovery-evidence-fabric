#!/usr/bin/env python3
"""Append claim c-0276 (the r174 lever + diagnosis lane, a
landed-bytes registration) to eval/work_claims.json.

Art. 29 discipline, honestly typed: this session's r174 work (the
DIR-2 divergence diagnosis + the DIR-3 v19 non-obviousness lever +
the 4-round smoke) was BUILT before this registration (the window
recycled mid-turn; the bytes sit uncommitted in the worktree). The
claim records the lane honestly as landed-bytes: the artifacts are
complete, the smoke verdict is NOT MET (recorded honestly), and
nothing was measured against a sealed set. No conflict with c-0275
(P5 counting run, builder-r159s2's OPEN lease — untouched).
"""
import datetime, json, subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"
now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]
claim = {
    "claim_id": "c-0276",
    "work_id": "r174-v19-nonobviousness-lever",
    "role": "EXECUTOR",
    "kind": "lever",
    "status": "DONE",
    "session_id": "builder-r174s1",
    "claimed_at": now,
    "registered_at": now,
    "lease_expiry": "2026-11-27T23:59:00Z",
    "base_sha": base,
    "artifact_paths": [
        "eval/r174_dir2_divergence_diagnosis.json",
        "eval/r174s2_v19_lever_delivery.json",
        "eval/r174_v19_smoke/",
        "discovery_fabric/generation/nonobvious_departure.py",
        "discovery_fabric/generation/mechanism_map.py",
        "tests/test_nonobvious_departure.py",
        "scripts/r174_dir2_divergence_diagnosis.py",
        "scripts/r174_v19_departure_smoke.py",
        "scripts/r174s2_v19_lever_record.py",
    ],
    "note": ("LANDED-BYTES registration (the window recycled mid-turn; "
             "the honest typed state): the DIR-2 divergence diagnosis "
             "(bytes-only, zero LLM) + the DIR-3 v19 lever "
             "engine-wired (7-part DEPARTURE contract + failure-sign "
             "filtering + lexicon stems) + the 4-round smoke verdict "
             "NOT MET (2-4/5 non-obvious under the single-judge "
             "strict proxy; structure 5/5; physics 5/5) — recorded "
             "honestly, never screen-gamed. No sealed-set "
             "measurement. No conflict with c-0275."),
    "takes_over": "",
}
doc = json.load(open(PATH))
doc["claims"].append(claim)
json.dump(doc, open(PATH, "w"), indent=1, ensure_ascii=False)
print("appended", claim["claim_id"], "base", base)
