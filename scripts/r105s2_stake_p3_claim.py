#!/usr/bin/env python3
"""Stake c-0125 — the P3 real-data validation lane (auditor R105
verdict direction 4). Art. 29(b): the push is the lock; execution
starts in this window if budget allows, else the next window resumes
from committed bytes (lease 2026-11-22).

Lane: Chronos-2/Bolt (Apache-2.0) + Time-MoE/MOMENT evals on
C-MAPSS/XJTU-SY/CWRU with OWN loaders + MAPIE conformal FA-control.
Acceptance gates (the verdict's own numbers): coverage >= 1-alpha,
FA <= 1/machine/yr, median inference <= 2 min, matched-budget DEV
ablation BEFORE adoption. NOTICE attribution at adoption time only
(the LICENSE RULE: verify the license text before any byte lands).
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
    "claim_id": "c-0125",
    "claimed_at": f"{now} (sandbox clock, TRUE UTC)",
    "registered_at": f"{now} (sandbox clock, TRUE UTC)",
    "work_id": "p3-realdata-conformal-validation",
    "title": (
        "THE P3 REAL-DATA LANE (builder-r105s2, auditor R105 verdict "
        "direction 4): the predictor stack validated on REAL "
        "benchmarks — Chronos-2/Bolt (Apache-2.0, the <=250x-faster "
        "claim re-measured here) + Time-MoE/MOMENT evals on "
        "C-MAPSS/XJTU-SY/CWRU with OWN loaders (no vendored dataset "
        "bytes from unlicensed mirrors; CWRU copyright: the data is "
        "freely useable per the Case School site, the loader reads "
        "the canonical formats) + MAPIE (BSD-3) conformal FA-control "
        "on top. ACCEPTANCE GATES (typed, from the verdict): coverage "
        ">= 1-alpha, FA <= 1/machine/yr, median inference <= 2 min, "
        "matched-budget DEV ablation BEFORE any adoption. NOTICE "
        "attribution rows land ONLY at adoption with the license "
        "texts byte-verified. Zero sealed-set bytes; zero LLM "
        "generation."),
    "status": "OPEN",
    "session_id": "builder-r105s2",
    "role": "EXECUTOR",
    "kind": "measurement",
    "base_sha": base,
    "lease_expiry": "2026-11-22T23:59:00Z",
    "artifact_paths": [
        "eval/p3_realdata/",
        "scripts/r105s2_p3_loaders.py",
        "eval/r105s2_p3_realdata_record.json",
    ],
    "notes": (
        "Art. 29(b): claimed before any lane byte. The datasets are "
        "public benchmarks (not held-out material) — the DEV/accept "
        "boundary is unaffected; the acceptance gates run on "
        "committed loaders + committed metric bytes. Execution "
        "resumes from committed stage pushes if this window ends "
        "(the lease covers it); stage 1 = the loaders + the metric "
        "harness (no model weights needed), stage 2 = the FM evals, "
        "stage 3 = conformal + gates."),
    "no_problem_read_before_claim": "True",
}


def main():
    with open(PATH) as f:
        d = json.load(f)
    claims = d["claims"]
    assert all(c["claim_id"] != "c-0125" for c in claims), \
        "c-0125 already exists"
    assert not any(
        c.get("work_id") == "p3-realdata-conformal-validation"
        for c in claims), "work_id already claimed (no dual stake)"
    claims.append(claim)
    with open(PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print("c-0125 staked (p3-realdata-conformal-validation, "
          "measurement) | claims:", len(claims), "| base:", base)


if __name__ == "__main__":
    main()
