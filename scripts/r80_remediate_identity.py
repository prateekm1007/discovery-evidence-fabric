#!/usr/bin/env python3
"""R80 forward-only remediation: register session builder-r80s1 (Art. 29(a)
identity-on-first-push — the R80 verifier push was the session's first push
and I missed the registration) + register the trailer violation for 63d6b3f5c
(typed, session-attributed, DISCLOSED_PENDING_REMEDIATION per the F36/R47
precedent). The NEXT commit carries proper Session:/Work-Id: trailers."""
import json, datetime, subprocess

NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
BAD_FULL = subprocess.run(["git", "rev-parse", "63d6b3f5c"],
                          capture_output=True, text=True).stdout.strip()

with open("eval/work_claims.json") as f:
    reg = json.load(f)

assert "builder-r80s1" not in reg.get("sessions", {}), "already registered?"
reg.setdefault("sessions", {})["builder-r80s1"] = {
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "role": "builder",
    "note": "R80 session-1: continuation of the r91s1 conversation lineage "
            "(same builder lane, new context window; the r91s1 session "
            "itself remains registered). This session's work: the PEER "
            "VERIFIER lane c-0104 for the sealed holdout v11 one-shot (the "
            "c-0103/c-0100 Art. 29(c) pattern) — read-only recompute from "
            "committed bytes, eval/r92_v11_verifier_c0104.json, verdict "
            "VERIFIED, the c-0102 flip credited to the executor "
            "builder-r91s1. Registration is part of the typed remediation "
            "push: the session's FIRST push (63d6b3f5c) preceded this "
            "registration and was caught by the Art. 29 CI (session not "
            "registered + commit lacked Session:/Work-Id: trailers) — both "
            "disclosed forward-only, never rewritten.",
}

tvs = reg.setdefault("trailer_violations", [])
assert not any(str(v.get("sha")).startswith("63d6b3f5c") for v in tvs), \
    "violation already registered?"
tvs.append({
    "sha": BAD_FULL[:9],
    "session": "builder-r80s1",
    "detected_by": "builder-r80s1",
    "detected_at": NOW,
    "finding": "commit lacks Session:/Work-Id: trailers (Art. 29(a)) — "
               "caught by tests/test_article29_parallel_coordination.py on "
               "this push's own CI read; the same push also carried the "
               "session's first claim (c-0104) before the session was "
               "registered in sessions{}",
    "status": "DISCLOSED_PENDING_REMEDIATION",
    "note": "F36 typed allowance pattern (the R47 precedent): pushed "
            "history is never rewritten (Art. 4); remediation is forward — "
            "the remediation commit registers session builder-r80s1, "
            "registers THIS violation typed, and itself carries Session: "
            "builder-r80s1 + Work-Id: holdout-v11-generation trailers; all "
            "builder-r80s1 commits from this disclosure onward carry "
            "trailers. The commit's CONTENT is unaffected: the verifier "
            "record eval/r92_v11_verifier_c0104.json (verdict VERIFIED) and "
            "the c-0102/c-0104 registry flips stand as landed.",
})

with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("session builder-r80s1 registered; trailer violation for "
      f"{BAD_FULL[:9]} registered ({len(tvs)} total)")
