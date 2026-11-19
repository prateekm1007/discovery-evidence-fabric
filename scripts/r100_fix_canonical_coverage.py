#!/usr/bin/env python3
"""Remediate the canonical-claim coverage failure (CI 7c7c44dc9 RED).

The sealed v14 run commit touched canonical measurement bytes while
the covering claim c-0115's artifact_paths carried ANNOTATED strings
('eval/holdout_v14_generation/ (the run artifacts)') — the coverage
was real in substance but failed the machine prefix-match rule (a
path matches a canonical byte only when equal, or when it is a bare
directory prefix ending with '/'). Remediation, forward-only:
  1. c-0115's artifact_paths -> bare machine-matchable paths (tip);
  2. the historical commit 7c7c44dc9 registered in
     canonical_claim_violations[] with the correct work_id named
     (the F36-pattern typed allowance; no history rewrite).
"""
import datetime
import json

PATH = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"

BARE_PATHS = [
    "audit/holdout_v14/holdout_v14_problems.json",
    "audit/holdout_v14/PREREGISTRATION.json",
    "scripts/r99_disjointness_guard.py",
    "scripts/r100_v14_one_shot.py",
    "scripts/r100_stake_v14_corrected_claim.py",
    "eval/holdout_v14_generation/",
    "eval/r100s1_status.json",
    "eval/r99_disjointness_v14_record.json",
    "eval/r100_core_mechanism_prereg.json",
]

VIOLATION = {
    "sha": "7c7c44dc9",
    "session": "builder-r95s1",
    "correct_work_id": "holdout-v14-generation",
    "correct_claim_id": "c-0115",
    "detected_by": "builder-r95s1",
    "detected_at": None,  # filled at write time
    "finding": (
        "the sealed v14 run commit touched canonical measurement "
        "bytes while the covering claim c-0115's artifact_paths "
        "carried annotated strings ('eval/holdout_v14_generation/ "
        "(the run artifacts)') — the coverage was real in substance "
        "(every touched byte IS a c-0115 artifact: the run rows, "
        "events, attestations and gateway slices of the claim's own "
        "lane) but failed the machine prefix-match (paths must be "
        "bare or end with '/'); remediation: the paths fixed to bare "
        "machine-matchable form at the current tip and this "
        "historical commit registered here with the correct work_id "
        "named (the F36-pattern typed allowance; forward-only "
        "disclosure, no history rewrite)"),
}


def main():
    now = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    with open(PATH) as f:
        d = json.load(f)
    c = [x for x in d["claims"] if x["claim_id"] == "c-0115"][0]
    assert c["artifact_paths"] != BARE_PATHS
    c["artifact_paths"] = BARE_PATHS
    c["notes"] = c["notes"] + (
        " ARTIFACT-PATH FORMAT FIX (forward-only): the original "
        "paths carried human annotations that broke the Art.29 "
        "canonical prefix-match — replaced with bare machine-"
        "matchable paths; the 7c7c44dc9 run commit is registered in "
        "canonical_claim_violations[] with this work_id named.")
    v = dict(VIOLATION)
    v["detected_at"] = f"{now} (sandbox clock, TRUE UTC)"
    d["canonical_claim_violations"].append(v)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("c-0115 paths -> bare; violation registered for 7c7c44dc9")


if __name__ == "__main__":
    main()
