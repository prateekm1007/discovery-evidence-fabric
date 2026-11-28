#!/usr/bin/env python3
"""r43_verifier_registry.py — register session builder-r43s2, file the
VERIFIER claim c-0061 for c-0060's work, and append the verifier
attribution to the c-0060 claim notes (the c-0056/c-0058 pattern: the
verifier attribution rides the claim it verifies)."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = "2026-11-17T02:50:00Z (sandbox clock)"

p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
d.setdefault("sessions", {})["builder-r43s2"] = {
    "registered_at": NOW,
    "role": "builder",
    "note": "R43 session-2: STOOD DOWN TO VERIFIER per Art. 29(b)/(e) "
            "— this session independently built the same D1/D2/D5 "
            "lane from base 90ad970d7 without having pushed a claim "
            "first (process miss, disclosed in "
            "eval/r43_verifier_c0060.json); the peer's pushed claim "
            "c-0060 (b1632cd2c, 01:33:10Z) predates this session's "
            "first implementation write, so pusher-wins and the "
            "duplicate scratch was archived outside the repo, never "
            "pushed. This session verifies c-0060 instead."}

claims = d["claims"]
if not any(c.get("claim_id") == "c-0061" for c in claims):
    claims.append({
        "claim_id": "c-0061",
        "work_id": "v8-generation-binds",
        "title": "VERIFIER for c-0060 (the c-0058/c-0059 precedent): "
                 "zero-LLM recompute of the R43 V8 generation binds "
                 "from committed bytes — the executor's 23-test suite, "
                 "the rendered queue-CI pytest surface, the check-run "
                 "API at three SHAs, the diff secret-grep, trailers, "
                 "registry, Art. 27/16 ledger legs, the F45-class "
                 "security finding typed check, and the race "
                 "disclosure",
        "status": "DONE",
        "registered_at": NOW,
        "session_id": "builder-r43s2",
        "role": "VERIFIER",
        "kind": "task",
        "base_sha": "a792a6a97",
        "claimed_at": NOW,
        "lease_expiry": "2026-11-17T14:50:00Z",
        "takes_over": None,
        "artifact_paths": [
            "eval/r43_verifier_c0060.json",
            "eval/r43_verifier_c0060_legs.json",
            "scripts/r43_verifier_legs.py",
            "scripts/r43_verifier_record.py",
            "scripts/r43_verifier_registry.py"],
        "notes": "VERDICT: RUN-INTEGRITY-VERIFIED (11 legs green: "
                 "executor_suite RECOMPUTES_GREEN 23/23 at a792a6a97; "
                 "rendered_ci_local RECOMPUTES_GREEN — the committed "
                 "workflow's 4 rendered pytest invocations, 191 tests "
                 "total, exit 0 as bash; remote_ci_api_read "
                 "RECOMPUTES_TRUE — 29dc8af66=failure preserved as "
                 "fact, f70b95160=success, a792a6a97=success, all "
                 "matching the round record's history; "
                 "secret_grep_diff 0; trailers lawful; Art. 27 keys "
                 "present; Art. 16 retirement ledger present; "
                 "F45-class finding VERIFIED_TYPED (the R451 "
                 "credential-scan records at origin-reachable 3db194e8f "
                 "carry 5+7 credential-shaped strings, values never "
                 "printed — owner-side rotation, no history rewrite); "
                 "rubric NEVER_READ (the sole mention is the "
                 "disclosure sentence); registry lawful — exactly one "
                 "c-0060 claim, push-as-mutex held; labelled-corpus "
                 "conventions present). Zero LLM calls. No "
                 "re-generation, no re-run of the executor's work."})

for c in claims:
    if c.get("claim_id") == "c-0060":
        if "VERIFIED by builder-r43s2" not in c.get("notes", ""):
            c["notes"] = c.get("notes", "").rstrip() + (
                " | VERIFIED by builder-r43s2 via "
                "eval/r43_verifier_c0060.json (11 legs, "
                "RUN-INTEGRITY-VERIFIED, zero-LLM recompute from "
                "committed bytes at a792a6a97; the race disclosed: "
                "the verifier session's own duplicate D1/D2/D5 lane "
                "was stood down pre-push per Art. 29(b)/(e)) — "
                "the c-0056/c-0058 attribution pattern.")
d["at"] = NOW
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("registry: builder-r43s2 registered; c-0061 VERIFIER DONE; "
      "c-0060 carries the verifier attribution")
