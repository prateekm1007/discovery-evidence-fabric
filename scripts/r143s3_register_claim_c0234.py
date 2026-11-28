#!/usr/bin/env python3
"""R143s3: register session builder-r143s3 + claim c-0234 (claim-before-work,
Art. 29(b)).

Work item r143s3-trailer-violation-c7096aa48 (DIR-5): the tip check-run
138006722449 (surface) is FAILURE at
tests/test_article29_parallel_coordination.py::
test_post_adoption_commits_carry_session_and_work_id_trailers — commit
c7096aa488ea (the twin builder-r121s1-3e8a41d7 synthesis-stage complement on
c-0233) lacks Session:/Work-Id: trailers and is unregistered in
trailer_violations[]. THIS commit is the claim lock (the push is the mutex);
the typed violation registration is the immediately-following result commit.
Enforcement/coordination only — zero engine lines, no measurement (Art. 27
typed disclosure class)."""
import json

REG_PATH = ("/home/z/my-project/discovery-evidence-fabric"
            "/eval/work_claims.json")
with open(REG_PATH) as f:
    reg = json.load(f)

sess = reg.setdefault("sessions", {})
assert "builder-r143s3" not in sess, "session already registered"
sess["builder-r143s3"] = {
    "note": (
        "R143 session-3: fresh sandbox, fresh clone from public origin "
        "(2026-11-23). DIR-1 verified from bytes: constitution digest "
        "153ac62efca36c2d at tip ab23406ec AND handoff pin 5c74c0ca430e; "
        "auditor constitution 3775f869a1c19a96 at audit tip 3bc59b530e96 "
        "(still ABSENT from the canonical tree — the R129 finding stands); "
        "ledger verdicts end V107; claims counter c-0234; sealed r143 "
        "corpus FILE sha256[:16]=19497e570df7f837 recomputed IDENTICAL on "
        "queue worktree vs audit-branch bytes; secret-grep 0 live in the "
        "tracked tree. DIR-2 (c-0232) and DIR-4 (c-0233) are twin-claimed: "
        "stood down per Art. 29, took the unclaimed red-tip fix (DIR-5). "
        "The AGNES vault (.env.keys) is ABSENT in this fresh sandbox: "
        "DIR-3/6/7 generation stays typed-blocked here (infrastructure, "
        "not mechanism — Art. 15)."),
    "registered_at": "2026-11-23 (sandbox clock)",
    "role": "builder",
}

claims = reg["claims"]
ids = [c["claim_id"] for c in claims]
assert "c-0234" not in ids, "claim id already exists"
claims.append({
    "work_id": "r143s3-trailer-violation-c7096aa48",
    "claim_id": "c-0234",
    "role": "EXECUTOR",
    "session_id": "builder-r143s3",
    "kind": "task",
    "status": "OPEN",
    "base_sha": "ab23406ec",
    "lease_expiry": "2026-11-30T23:59:00Z",
    "claimed_at": "2026-11-23 (sandbox clock)",
    "registered_at": "2026-11-23 (sandbox clock)",
    "artifact_paths": [
        "eval/work_claims.json",
        "eval/claim_next_id.txt",
        "scripts/r143s3_register_claim_c0234.py",
        "scripts/r143s3_register_trailer_violation_c7096aa48.py",
    ],
    "title": (
        "R143S3 EXECUTOR (claim c-0234, base ab23406ec): DIR-5 fix forward — "
        "the tip check-run (138006722449, surface) is FAILURE at "
        "test_article29_parallel_coordination.py::"
        "test_post_adoption_commits_carry_session_and_work_id_trailers: "
        "commit c7096aa488ea (twin r121s1-3e8a41d7, c-0233 continuation) "
        "lacks Session:/Work-Id: trailers and is unregistered. Fix = typed "
        "trailer_violations[] registration with session attribution (F36 "
        "fail-closed the OTHER way), NO history rewrite (Art. 4). "
        "Acceptance: tip check-run SUCCESS quoted from the API."),
})
with open(REG_PATH, "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("session builder-r143s3 registered; claim c-0234 appended "
      "(claim-before-work lock)")
