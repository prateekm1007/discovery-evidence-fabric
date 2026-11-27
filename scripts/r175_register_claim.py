#!/usr/bin/env python3
"""Append claim c-0278 (the DIR-2 compute-matched baseline lane,
V-latest) to eval/work_claims.json — claim-before-work: registered and
pushed BEFORE any generation/judge call fires."""
import datetime, json, subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"
now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]
claim = {
    "claim_id": "c-0278",
    "work_id": "r175-compute-matched-baseline",
    "role": "EXECUTOR",
    "kind": "measurement",
    "status": "OPEN",
    "session_id": "builder-r175s1",
    "claimed_at": now,
    "registered_at": now,
    "lease_expiry": "2026-11-28T12:00:00Z",
    "base_sha": base,
    "artifact_paths": [
        "scripts/r175_compute_matched_baseline.py",
        "eval/r175_compute_matched/",
    ],
    "note": ("the V-latest DIR-2 lane (the only test that moves the "
             "AM52 score): 12 DEV pairs from the f31e pool, both arms "
             "6 calls/item compute-matched, baseline = best-of-4 of "
             "the r125 AUTHORING_DIRECTIVE incumbent + critique + "
             "revise; pipeline = staged path + the baseline answer IN "
             "ITS POOL (dominance-by-construction); blind judge "
             "gpt-6-luna (ctai, judge-family != generator, F2-CLEAN), "
             "X/Y randomized, two passes order-swapped; accept 12/12 "
             "judged + win-rate with CI. Prereg rides the script's "
             "PREREG constant. NOT the sealed holdout."),
    "takes_over": "",
}
doc = json.load(open(PATH))
# register the session too (Art. 29(a))
doc["sessions"]["builder-r175s1"] = {
    "note": ("R175 session-1: the DIR-2 compute-matched baseline lane "
             "(V-latest AM52 scoreboard); same builder lineage"),
    "registered_at": now + " (sandbox clock, TRUE UTC)",
    "role": "builder",
}
doc["claims"].append(claim)
json.dump(doc, open(PATH, "w"), indent=1, ensure_ascii=False)
# advance the counter in the SAME commit
open(REPO + "/eval/claim_next_id.txt", "w").write("c-0279")
print("appended", claim["claim_id"], "| counter -> c-0279 | base", base)
