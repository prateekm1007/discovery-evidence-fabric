#!/usr/bin/env python3
"""Append claim c-0114 (holdout-v14-generation) to eval/work_claims.json.

Art. 29(b) discipline: the claim lands and is PUSHED before the
executor reads ANY v14 problem byte. The v14 set lives on the audit
branch (ca9b2d52b, seal 73222ce2feb8ab32, rubric PRIVATE); the
executor's generation lane reads problems ONLY from the audit worktree
AFTER the claim push, and NEVER reads the rubric pre-generation.
"""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"

now = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
base = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      text=True, cwd=REPO).stdout.strip()[:9]

claim = {
    "claim_id": "c-0114",
    "claimed_at": f"{now} (sandbox clock, TRUE UTC)",
    "registered_at": f"{now} (sandbox clock, TRUE UTC)",
    "work_id": "holdout-v14-generation",
    "title": (
        "THE V14 LANE (builder-r95s1, AM87 direction): run the "
        "SEALED AUDITOR-AUTHORED v14 blind set — the fail-closed "
        "r99 disjointness guard over the FULL v1-v13 corpus vs v14 "
        "MUST pass 0 domain-head clashes before any run; then the "
        "sealed v14 one-shot on agnes-3.0-flash (default, 2-key "
        "rotation) with the five binds + the c-0109 corrector (v1.1 "
        "vocabulary) + c-0110 AIDE tree search + c-0112 adaptive "
        "conformal; 30/30 served==requested==registered attestation; "
        "durable events; MEASURED_PATH through engine_route -> "
        "mechanism_space. The problems are read ONLY from the audit "
        "branch worktree (ca9b2d52b, seal 73222ce2feb8ab32) AFTER "
        "this claim's push (push=lock). The rubric is PRIVATE and "
        "NEVER read pre-generation. Zero acceptance/score claims — "
        "the auditor scores vs the private rubric (mean >=3.5, CI "
        "lower >3.0, 0/0/0 -> re-earn score 7). The score-8 "
        "core-mechanism anchor pre-registration (AM87 redefined "
        "gate) is a SEPARATE record landed with the same push."),
    "status": "ACTIVE",
    "session_id": "builder-r95s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": base,
    "lease_expiry": "2026-11-21T23:59:00Z",
    "takes_over": "None",
    "artifact_paths": [
        "audit/holdout_v14/holdout_v14_problems.json (audit branch "
        "ca9b2d52b — read post-claim, never pre-claim)",
        "audit/holdout_v14/PREREGISTRATION.json (audit branch; the "
        "seal verification input; rubric ABSENT pre-generation)",
        "scripts/r99_disjointness_guard.py (the fail-closed gate)",
        "scripts/r98_v13_one_shot.py (the frozen one-shot machine; "
        "the v14 driver derives from it unchanged)",
        "eval/r100s1_status.json (the lane status record)",
    ],
    "notes": (
        "Art. 29(b): claimed before ANY v14 problem byte is read — "
        "the set is auditor-authored (ca9b2d52b) and the executor "
        "has read zero bytes of it; the ONLY v14 facts in the "
        "executor's context are the auditor's own AM87 disclosures "
        "(cluster water/wastewater, seal 73222ce2feb8ab32, rubric "
        "PRIVATE). The claim push IS the lock; the disjointness "
        "guard's instrument read of the v14 problem texts happens "
        "strictly post-push, post-claim, fail-closed."),
    "no_problem_read_before_claim": "True",
}


def main():
    with open(PATH) as f:
        d = json.load(f)
    claims = d["claims"] if isinstance(d, dict) and "claims" in d else d
    assert all(c["claim_id"] != "c-0114" for c in claims), \
        "c-0114 already exists"
    claims.append(claim)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("c-0114 appended | claims:", len(claims), "| base:", base)


if __name__ == "__main__":
    main()
