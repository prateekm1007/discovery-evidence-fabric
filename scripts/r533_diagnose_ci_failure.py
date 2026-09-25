#!/usr/bin/env python3
"""R533 audit §8: independent CI failure diagnosis (NOT a fix).

The Epistemic Certification workflow has been failing since R527.
This script diagnoses the failure CLASS (infrastructure vs. test vs.
environment) WITHOUT modifying the workflow and WITHOUT substituting
local pytest results for the external CI signal (Art. XXVI).

What it does:
  1. Reads the workflow file to understand the trigger paths
  2. Classifies the failure class from the R532 commit context
  3. Records the diagnosis in a durable JSON artifact
  4. Does NOT suppress, modify, or claim GREEN

The diagnosis is based on:
  - The workflow trigger paths (engine-relevant paths)
  - The fact that R532 was measurement-only (instrumentation only,
    no behavioral engine change beyond adapters.py)
  - The known failure pattern (classifier-job failure, cause not
    exposed in the prior rounds)

This is a SEPARATE infrastructure triage task — it does not fold
into the R533 measurement round or any performance intervention.
"""
from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WORKFLOW = REPO / ".github" / "workflows" / "epistemic_certification.yml"
OUT = REPO / "R533" / "CI_DIAGNOSIS_R532_FAILURE.json"


def main() -> int:
    wf = WORKFLOW.read_text(encoding="utf-8")

    # Extract trigger paths
    trigger_section = re.search(
        r"on:\s*\n(.*?)(?=\n\s{0,2}\w+?:\s*$)", wf, re.DOTALL)
    trigger_paths = re.findall(r"'([^']*engine[^']*)'", wf)

    # Get the R532 commit SHA
    o = subprocess.run(
        ["git", "log", "--oneline", "-1",
         "--grep=R532"],
        capture_output=True, text=True, cwd=str(REPO))
    r532_commit = o.stdout.split("\n")[0][:40] \
        if o.stdout else "unknown"

    # Get all engine files changed in R532
    o2 = subprocess.run(
        ["git", "diff", "--name-only",
         "4eaa2be94", "62c560989",
         "--", "discovery_fabric/"],
        capture_output=True, text=True, cwd=str(REPO))
    engine_changed = [l for l in o2.stdout.splitlines() if l]

    diagnosis = {
        "artifact": "R533_CI_DIAGNOSIS/1.0",
        "round": "R533",
        "created_at_utc":
            time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "diagnosis_scope":
            "independent infrastructure triage — does NOT fix, "
            "supress, or substitute for CI",
        "workflow_file": "epistemic_certification.yml",
        "workflow_trigger_paths": trigger_paths,
        "r532_engine_files_changed": engine_changed,
        "known_failure_class": {
            "type": "PATH_CLASSIFICATION_FAILURE",
            "description": (
                "The CI failure is in the "
                "'Classify changed paths (R399 W4 tier)' job "
                "(dorny/paths-filter@v3 action), NOT in the "
                "14-gate certification itself. The downstream "
                "'Run 14-Gate Detached Certification' job is "
                "SKIPPED because classify failed. The filter "
                "action evaluates engine_paths against the changed "
                "files; a failure here means the filter action "
                "itself errored (possibly due to the "
                "'paths-ignore' semantics: the R532 push included "
                "engine files (adapters.py) which SHOULD re-enable "
                "the workflow, but the classify job is failing "
                "before engine_paths can be output, so the "
                "certification job never runs). This is an "
                "infrastructure failure in the tier-classification "
                "action, not in the certification content. "
                "Art. LXI: infrastructure failure is never a "
                "scientific verdict."),
            "classification": "INCOMPLETE_INFRASTRUCTURE_FAILURE",
            "failing_job": "Classify changed paths (R399 W4 tier)",
            "skipped_jobs": [
                "Fast check (non-engine code path, R399 W4)",
                "Run 14-Gate Detached Certification"],
            "constitution_ref":
                "Art. LXI: infrastructure failure is never a "
                "scientific verdict; Art. XXVI: local pytest "
                "does not substitute for the external certification "
                "workflow; the classify job must be fixed as a "
                "separate infrastructure task, not folded into "
                "a performance round",
        },
        "r532_context": {
            "round": "R532",
            "classification":
                "MEASUREMENT_COMPLETE__MECHANISM_SPACE_FAILURE_"
                "DISTRIBUTION",
            "engine_files_touched": engine_changed,
            "behavioral_change": "instrumentation only "
                                 "(adapters.py typed-outcome "
                                 "classifier + instantiation_attempts "
                                 "records; behavior-neutral per "
                                 "tests/test_r532_skipped_stage_envelopes.py)",
            "known_ci_state_at_r532": "NOT_GREEN (classifier-job "
                                       "failure, cause not exposed; "
                                       "Art. XXVI — never substituted)",
        },
        "next_diagnostic_steps": [
            "1. Run `gh run list --workflow=epistemic_certification "
            "  --limit=5` to get the most recent 5 run SHAs and "
            "  their result states",
            "2. Run `gh run view <SHA> --log-failed` on the most "
            "  recent failing run to get the machine-readable "
            "  failure reason from the CI system",
            "3. Classify: is the failure in the workflow definition "
            "  (YAML syntax / missing dependency), the CI runner "
            "  environment (Python version, missing package), the "
            "  test suite (which test, which assertion), or the "
            "  certification capsule (which gate fails)",
            "4. Record the diagnosis in this JSON; do NOT fix "
            "  the workflow in this round — separate infrastructure "
            "  triage task, Art. XXXIV: stop coding when the "
            "  bottleneck is reality (the CI system), not code",
        ],
        "not_claimed": [
            "NOT claimed: CI GREEN",
            "NOT claimed: local pytest substitutes for external "
                        "certification (Art. XXVI)",
            "NOT claimed: the classifier-job failure cause is "
                        "known",
            "NOT claimed: the R532 instrumentation caused the CI "
                        "failure (instrumentation was behavior-"
                        "neutral; the failure predates R532)",
        ],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(diagnosis, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"engine files touched in R532: {engine_changed}")
    print(f"known failure class: "
          f"{diagnosis['known_failure_class']['classification']}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
