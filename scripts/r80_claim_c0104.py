#!/usr/bin/env python3
"""R80: stake claim c-0104 (Art. 29(b) claim-before-work) — VERIFIER lane for c-0102
(the sealed holdout v11 one-shot landed by builder-r91s1 at b822f50ab/771e5a2b9).
Read-only recompute lane per the c-0103 precedent (Art. 29(c)); zero generation."""
import json, subprocess, datetime

HEAD = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

claim = {
    "claim_id": "c-0104",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "holdout-v11-generation",
    "title": "PEER VERIFIER lane for c-0102 (the sealed holdout v11 one-shot, executor builder-r91s1, "
             "landed b822f50ab/771e5a2b9): Art. 29(c) verifier RECOMPUTE from committed bytes via the "
             "committed instrument's own attest mode (scripts/r91_v11_one_shot.py attest), invoked "
             "READ-ONLY. The committed attestation.json bytes are NOT rewritten (Art. 4); never a "
             "re-run: zero LLM, zero quota, zero problem bytes newly consumed, zero gateway calls. "
             "On a MATCH verdict: file eval/r92_v11_verifier_c0104.json and flip c-0102 OPEN->DONE "
             "credited to the executor (builder-r91s1) in the same registry snapshot, per the R75 "
             "verifier-flip precedent and the c-0103/c-0100 pattern. Collision check: c-0104 free; "
             "role VERIFIER on an existing EXECUTOR work_id (the Art. 29(c) pattern, c-0064/c-0103 "
             "precedents); c-0102 stays OPEN until this record lands.",
    "status": "OPEN",
    "session_id": "builder-r80s1",
    "role": "VERIFIER",
    "kind": "task",
    "base_sha": HEAD,
    "lease_expiry": "2026-11-20T23:59:00Z",
    "takes_over": None,
    "artifact_paths": ["eval/r92_v11_verifier_c0104.json"],
    "notes": "Art. 29(b)/(c): this session is NOT the c-0102 executor and never re-runs. No problem "
             "bytes read before this claim (only registry-level state: attestation header keys, "
             "claim registry, run-record commit messages). The verify work reads the COMMITTED "
             "gateway slice + row files only, through the committed instrument's attest mode. "
             "Auditor scoring of v11 is a separate lane (PRIVATE rubric custody) and is untouched.",
    "no_problem_read_before_claim": True,
}

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg
ids = [str(c.get("claim_id")) for c in claims]
assert "c-0104" not in ids, "c-0104 already staked — race!"
claims.append(claim)
if isinstance(reg, dict):
    reg["claims"] = claims
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print(f"c-0104 staked OPEN at base {HEAD[:9]} — claims now {len(claims)}")
