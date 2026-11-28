#!/usr/bin/env python3
"""Append claim c-0280 (the DIR-3 diverse-generation lane) —
claim-before-work."""
import datetime, json, subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"
now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]
doc = json.load(open(PATH))
doc["claims"].append({
    "claim_id": "c-0280",
    "work_id": "r175-dir3-diverse-selection",
    "role": "EXECUTOR",
    "kind": "measurement",
    "status": "OPEN",
    "session_id": "builder-r175s1",
    "claimed_at": now,
    "registered_at": now,
    "lease_expiry": "2026-11-28T18:00:00Z",
    "base_sha": base,
    "artifact_paths": [
        "scripts/r175s3_dir3_diverse_selection.py",
        "eval/r175s3_dir3/",
    ],
    "note": ("the V-latest DIR-3 lane: diverse generation (4 "
             "strategies: plain / v19 departure contract / "
             "contradiction mapping / constraint relaxation) + "
             "obviousness subtraction (Jaccard>0.6 near-duplicate "
             "collapse) + stronger selection (cheap-judge pairwise "
             "tournament, order-randomized, baseline answer IN the "
             "pool). BASELINE ARM: fresh draws of the SAME best-of-4"
             "+critique+revise recipe in the SAME instrument (the "
             "c-0278 texts are hash-only by design — never a reburn "
             "of the sealed DIR-2 measurement). Accept >=50% "
             "wins+ties on 12 DEV items, blind two-pass judge "
             "gpt-6-luna (ctai), CI computed."),
    "takes_over": "",
})
json.dump(doc, open(PATH, "w"), indent=1, ensure_ascii=False)
open(REPO + "/eval/claim_next_id.txt", "w").write("c-0281")
print("appended c-0280 | counter -> c-0281 | base", base)
