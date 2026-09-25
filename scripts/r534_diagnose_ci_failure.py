#!/usr/bin/env python3
"""R534 audit §F: CI failure diagnosis updated for R534 commits.

Confirmed observations (from gh api + gh run list, no workflow
modification, no pytest substitution):

  - Every R533/R534 commit fails at the "Classify changed paths
    (R399 W4 tier)" job — the dorny/paths-filter@v3 step.
  - The downstream "Run 14-Gate Detached Certification" job is
    SKIPPED because the classify job fails first.
  - `gh run view --log-failed` returns "log not found" — the
    log blob is not retrievable via the REST API.
  - Root cause NOT independently observed. The failure class
    remains INCOMPLETE_INFRASTRUCTURE_FAILURE (Art. LXI).

This record updates the R533 CI_DIAGNOSIS artifact; it does NOT
fix or suppress the workflow.

Next required step (separate infrastructure task, not R534):
  Fetch the GitHub Actions log via the browser UI for run
  36113870503 (job 108003259805) to read the actual error
  message from the dorny/paths-filter step.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "R534" / "CI_DIAGNOSIS_R534_FAILURE.json"


def main() -> int:
    rec = {
        "artifact": "R534_CI_DIAGNOSIS/1.0",
        "round": "R534",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "supersedes": "R533/CI_DIAGNOSIS_R532_FAILURE.json "
                      "(extends the diagnosis to R534 commits)",
        "known_failure_class": {
            "type": "PATH_CLASSIFICATION_FAILURE",
            "classification": "INCOMPLETE_INFRASTRUCTURE_FAILURE",
            "failing_job": "Classify changed paths (R399 W4 tier)",
            "failing_step": "dorny/paths-filter@v3",
            "skipped_jobs": [
                "Fast check (non-engine code path, R399 W4)",
                "Run 14-Gate Detached Certification"],
            "root_cause": "UNKNOWN — the log blob for the failing "
                          "job is not retrievable via the REST API "
                          "(gh api returns 404 for the log URL); "
                          "the error message has NOT been "
                          "independently observed",
            "affected_commits": [
                "b1c9a8315 (R533 audit repair)",
                "5349be98e (R533 §5/§6/§7/§8 repair)",
                "eaeba79d8 (R534 B/C/D/E repair + deploy)",
                "73306acce (R534 closeout proof)"],
            "affected_runs": [
                "36108354435 (b1c9a8315)",
                "36113870503 (73306acce)"],
        },
        "not_claimed": [
            "NOT claimed: CI GREEN",
            "NOT claimed: local pytest substitutes for external "
                        "certification (Art. XXVI)",
            "NOT claimed: the workflow is suppressed or modified",
            "NOT claimed: the root cause of the classify-job "
                        "failure is known",
            "NOT claimed: the R534 instrumentation/fix caused "
                        "the CI failure (the classify job has "
                        "been failing since at least R531/"
                        "36092328764)",
        ],
        "constitution_ref": (
            "Art. LXI: infrastructure failure is never a "
            "scientific verdict. Art. XXVI: local pytest does "
            "not substitute for external CI. Art. XXXIV: stop "
            "coding when reality (the CI system log) is the "
            "bottleneck — fetch the log via the browser UI to "
            "diagnose; do not guess."),
        "next_infrastructure_task": (
            "Open https://github.com/prateekm1007/discovery-"
            "evidence-fabric/actions/runs/36113870503/job/"
            "108003259805 in a browser, read the dorny/paths-"
            "filter step log, classify the specific failure "
            "reason (YAML syntax error, missing filter output, "
            "action version issue, permissions, runner "
            "environment), and fix ONLY the classify job as a "
            "separate infrastructure task — do not fold into "
            "any measurement or optimization round."),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
