#!/usr/bin/env python3
"""r109s2_ci_disclosure.py — Art. 5 forward-only append: the honest
remote-CI read of the c-0138 verification push (c09410f7b), typed into
the verifier record. The push's CI is RED on
tests/test_remote_ci_rule.py — an INHERITED red (present at 79fb06c01
and 29027a07d, the peer builder-r109s1's own pushes), caused by
eval/r109s1_status.json (the peer's round-close record, committed
a99be3768) carrying no remote_ci block — the exact gap the peer
DISCLOSED in 29027a07d and assigned to their R110 lane (scripts/
r110_ci_read.py, the round-close step). This session's diff touches
no eval/r*_status.json file (the failing test reads only those); the
local green claim in the c-0138 commit message was made at tree
d17fca7f1, BEFORE the rebase brought the peer's round-close chain in.
Fail-closed guards; registry formatting untouched.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REC = (Path(__file__).resolve().parents[1] / "eval"
       / "r109s2_c0130_verifier_record.json")
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REC.read_text(encoding="utf-8"))
assert d["claim"] == "c-0138", "wrong record"
assert "remote_ci" not in d, "remote_ci already present — refuse to dup"

d["remote_ci"] = {
    "pushed_sha": "c09410f7b7",
    "remote_ci_conclusion": "failure",
    "check_runs": [{
        "name": "surface",
        "check_run_id": 136166997244,
        "conclusion": "failure",
        "failing_step": "tests/test_remote_ci_rule.py::"
                        "test_round_records_carry_the_remote_conclusion",
        "failure_detail": "r109s1_status.json: no remote_ci block — "
                          "a local-only green is a typed defect (D2 "
                          "hard rule, c-0055)",
    }],
    "read_at": NOW,
    "attribution": "INHERITED — the same failure stands at 79fb06c01 "
                   "and 29027a07d (the peer builder-r109s1's own "
                   "pushes, verified by the authenticated check-runs "
                   "API read); the failing artifact eval/"
                   "r109s1_status.json is the peer's round-close "
                   "record (created a99be3768, no remote_ci block); "
                   "the peer DISCLOSED the gap in 29027a07d and "
                   "assigned the fix to their R110 lane (scripts/"
                   "r110_ci_read.py, the round-close step). This "
                   "session's diff (eval/work_claims.json, "
                   "eval/r109s2_*, scripts/r109s2_*) touches NO "
                   "eval/r*_status.json — the failing test reads only "
                   "those files. Art. 29(e): the artifact is the "
                   "peer's claimed path; the fix is theirs; this "
                   "disclosure is the typed notice (Art. 5).",
    "local_green_basis": "the c-0138 commit message's 'complete "
                         "workflow reproduced green' claim was TRUE at "
                         "the verification tree d17fca7f1 (every CI "
                         "step re-run locally, incl. "
                         "test_remote_ci_rule.py PASSING — "
                         "r109s1_status.json was ABSENT at that tree); "
                         "the rebase onto the peer's 29027a07d brought "
                         "the round-close chain in AFTER the local "
                         "verification; the pushed tip c09410f7b "
                         "differs from the verification tree by "
                         "exactly the peer's commits (a99be3768.."
                         "29027a07d, no overlap with this session's "
                         "files).",
}
d["amendments"] = d.get("amendments", []) + [{
    "at": NOW,
    "kind": "Art. 5 disclosure append (forward-only)",
    "what": "the remote_ci block above — the honest API read of this "
            "session's push, replacing silence; the historical fields "
            "are untouched (Art. 4)",
}]
REC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("remote_ci disclosure appended to the c-0138 verifier record")
