#!/usr/bin/env python3
"""R537 P0 durable proof: the cemetery fail-closed gate
(R537_CEMETERY_FAIL_CLOSED_PROOF.json).

Drives the REAL EngineRun conductor with the REAL
AdjudicationAdapter (the P0 exercise target — only the non-target
stages are hermetically stubbed) and forces
`mechanism_cemetery.check_candidate_against_cemetery` to throw.
Proves through the actual
EngineRun -> ADJUDICATION -> _CemeterySubCheck -> mechanism_cemetery
path:

  exception
      -> UNRESOLVED / infrastructure failure (recorded, Art. XXV)
      -> no favorable cemetery PASS (the gate is fail-CLOSED)
      -> no ESTABLISHED_PROVISIONALLY adjudication
      -> no discovery credit (a typed non-green terminal)

Control: a normal run (no injection) records
cemetery_verdict_resolved True on a successful consultation, and the
gate passes only on a resolved non-BLOCKED verdict.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from test_r537_cemetery_fail_closed import (  # noqa: E402
    _drive_with_cemetery_failure, test_success_path_records_resolved_flag)

OUT = REPO / "R537" / "R537_CEMETERY_FAIL_CLOSED_PROOF.json"


def main() -> int:
    manifest, eng, adj_entry, cemetery_check, council = \
        _drive_with_cemetery_failure()
    adj_status = adj_entry.get("status")
    cc_verdict = (cemetery_check or {}).get("verdict")
    cc_resolved = (cemetery_check or {}).get("cemetery_verdict_resolved")
    cc_error = str((cemetery_check or {}).get("error", ""))
    failed = council.get("failed_checks") or []
    verdict = council.get("verdict")
    final_status = manifest.get("final_status")

    assert adj_status in ("OK", "FAILED_EXPLICIT"), adj_status
    assert cc_verdict == "UNRESOLVED", cc_verdict
    assert cc_resolved is False, cc_resolved
    assert "injected cemetery failure" in cc_error, cc_error
    if council:
        assert "cemetery_not_hard_blocked" in failed, failed
        assert verdict != "ESTABLISHED_PROVISIONALLY", verdict
    assert final_status not in ("ESTABLISHED_PROVISIONALLY",
                               "CANDIDATE_ACCEPTED", "REJECTED"), \
        final_status
    # the complementary control (success path records the flag)
    test_success_path_records_resolved_flag()

    rec = {
        "artifact": "R537_CEMETERY_FAIL_CLOSED_PROOF/1.0",
        "round": "R537",
        "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                        time.gmtime()),
        "reviewer_provenance": "AI_REVIEW",
        "method": ("REAL EngineRun conductor + REAL AdjudicationAdapter "
                   "(not stubbed — the P0 target); only the "
                   "non-target stages are hermetically stubbed; the "
                   "cemetery consultation was forced to throw; the "
                   "durable adjudication record (env.adjudication) "
                   "was inspected, not just the return value"),
        "p0_defect_closed": (
            "the R536 fail-open: `cemetery_not_hard_blocked = "
            "verdict != BLOCKED` treated an UNRESOLVED "
            "(infrastructure) consultation as a PASS. The R537 "
            "gate is fail-CLOSED: it passes only when the "
            "consultation RESOLVED (cemetery_verdict_resolved is "
            "True) AND the verdict is not BLOCKED."),
        "injected_failure_chain": {
            "cemetery_check_verdict": cc_verdict,
            "cemetery_verdict_resolved": cc_resolved,
            "recorded_error": cc_error,
            "adjudication_stage_status": adj_status,
            "council_failed_checks": failed,
            "council_verdict": verdict,
            "run_terminal_final_status": final_status,
            "discovery_credit_earned": False,
        },
        "assertions": [
            "cemetery exception -> UNRESOLVED / infrastructure "
            "failure (recorded, not hidden — Art. XXV)",
            "UNRESOLVED cannot produce a favorable cemetery PASS "
            "(the gate is fail-CLOSED)",
            "UNRESOLVED cannot produce ESTABLISHED_PROVISIONALLY "
            "adjudication",
            "no discovery credit: the run terminal is a typed "
            "non-green state",
            "the cemetery sub-check record is durable on the "
            "adjudication record (env.adjudication.cemetery_check), "
            "observable even when the council aggregation raises",
            "control: a successful consultation records "
            "cemetery_verdict_resolved True",
        ],
        "p0_proven": True,
    }
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(f"wrote {OUT} (p0_proven=True)")
    print(f"  injected chain: verdict={cc_verdict} resolved="
          f"{cc_resolved} stage={adj_status} failed={failed} "
          f"council={verdict} terminal={final_status}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
