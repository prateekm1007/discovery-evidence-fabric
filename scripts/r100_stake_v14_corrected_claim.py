#!/usr/bin/env python3
"""Claim continuity for the CORRECTED v14 lane (AM88/CORR-7).

c-0114 (the original v14 lane) -> TAKEN_OVER: its guard run typed the
fail-closed stop that caught the auditor's HO14-08 authoring clash;
the set is now re-authored/re-sealed (7707a0b4520c2a52) and the lane
continues under c-0115 (same work_id, lease continuity per Art. 29(d)).

Art. 29(b): c-0115 is staked BEFORE any byte of the CORRECTED v14 set
is read — the executor has read zero bytes of the re-sealed file; the
only corrected-set facts in context are the auditor's own AM88
disclosures (HO14-08-cwetland-clog replacement, new seal
7707a0b4520c2a52, rubric updated private). The OLD v14 bytes read last
round (post-c-0114, sanctioned instrument reads) are VOID — the set
was re-authored.
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

takeover_note = (
    "TAKEN_OVER by c-0115 (the CORR-7 continuation): the claim's "
    "guard run typed the fail-closed stop that caught the auditor's "
    "v14 HO14-08 authoring clash (AM88 credits the catch); the set is "
    "re-authored/re-sealed (7707a0b4520c2a52) and the lane continues "
    "under c-0115 on the same work_id. No acceptance/score claim was "
    "ever made under this claim; zero generation calls were served "
    "under it.")

claim = {
    "claim_id": "c-0115",
    "claimed_at": f"{now} (sandbox clock, TRUE UTC)",
    "registered_at": f"{now} (sandbox clock, TRUE UTC)",
    "work_id": "holdout-v14-generation",
    "title": (
        "THE CORRECTED V14 LANE (builder-r95s1, AM88/CORR-7 "
        "continuation of c-0114): (1) verify the re-sealed set's F50 "
        "canonical-tuple seal == 7707a0b4520c2a52 (post-claim); (2) "
        "re-derive the HO14-08 domain-head map entry from the "
        "CORRECTED row (constructed-wetland substrate clogging — the "
        "stale ~mbr entry no longer identifies the row and would "
        "false-clash v8-08); (3) re-run the fail-closed "
        "r99_disjointness_guard over the FULL v1-v13 corpus — 0 "
        "clashes REQUIRED before any run; (4) the sealed v14 one-shot "
        "on agnes-3.0-flash (default, 2-key rotation) with the five "
        "binds + c-0109 corrector (v1.1) + c-0110 AIDE + c-0112 "
        "adaptive conformal; 30/30 served==requested==registered "
        "attestation; durable events; MEASURED_PATH through "
        "engine_route -> mechanism_space; (5) push + remote CI + "
        "typed handoff. The problems are read ONLY from the audit "
        "branch (36f9559ef) AFTER this claim's push (push=lock). The "
        "rubric is PRIVATE and NEVER read pre-generation. Zero "
        "acceptance/score claims — the auditor scores vs the private "
        "rubric (mean >=3.5, CI lower >3.0, 0/0/0 -> re-earn score 7)."),
    "status": "OPEN",
    "session_id": "builder-r95s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": base,
    "lease_expiry": "2026-11-22T23:59:00Z",
    "takes_over": "c-0114",
    "artifact_paths": [
        "audit/holdout_v14/holdout_v14_problems.json (audit branch "
        "36f9559ef — the CORRECTED re-sealed set; read post-claim)",
        "audit/holdout_v14/PREREGISTRATION.json (seal verification "
        "input; rubric ABSENT pre-generation)",
        "scripts/r99_disjointness_guard.py (the fail-closed gate)",
        "scripts/r100_v14_one_shot.py (the v14 driver, derived from "
        "the frozen r98/r97 machines)",
        "eval/holdout_v14_generation/ (the run artifacts)",
        "eval/r100s1_status.json (the lane status record)",
    ],
    "notes": (
        "Art. 29(b): claimed before ANY corrected-v14 byte is read — "
        "no_problem_read_before_claim=True for the re-sealed set; the "
        "old-set reads under c-0114 are VOID (the set was "
        "re-authored; only HO14-08 replaced per AM88). The claim push "
        "IS the lock; the seal verification and the guard's "
        "instrument read of the corrected problem texts happen "
        "strictly post-push, fail-closed."),
    "no_problem_read_before_claim": "True",
}


def main():
    with open(PATH) as f:
        d = json.load(f)
    claims = d["claims"] if isinstance(d, dict) and "claims" in d else d
    assert all(c["claim_id"] != "c-0115" for c in claims), \
        "c-0115 already exists"
    prev = [c for c in claims if c["claim_id"] == "c-0114"]
    assert len(prev) == 1 and prev[0]["status"] == "OPEN", \
        "c-0114 must be OPEN before takeover"
    prev[0]["status"] = "TAKEN_OVER"
    prev[0]["notes"] = prev[0]["notes"] + " " + takeover_note
    claims.append(claim)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("c-0114 -> TAKEN_OVER; c-0115 staked | claims:", len(claims),
          "| base:", base)


if __name__ == "__main__":
    main()
