#!/usr/bin/env python3
"""R80: registry snapshot — flip c-0102 OPEN->DONE (credit to the executor
builder-r91s1, per the R75 verifier-flip precedent) and c-0104 OPEN->DONE,
both in the SAME registry write (the DONE-without-verifier CI rule)."""
import json, datetime

NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg

c0102 = next(c for c in claims if str(c.get("claim_id")) == "c-0102")
assert str(c0102.get("status")).upper() == "OPEN", "c-0102 not OPEN — race?"
c0102["status"] = "DONE"
c0102["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
c0102["completion_note"] = (
    "DONE — flipped by the peer VERIFIER lane c-0104 (builder-r80s1), credit "
    "to the EXECUTOR builder-r91s1 (staked+executed b822f50ab/771e5a2b9), per "
    "the R75/c-0094 and R91/c-0103 verifier-flip precedents. Evidence: eval/"
    "r92_v11_verifier_c0104.json — verdict VERIFIED: (1) the v11 seal "
    "1493bb84cccf027f recomputed EXACT from the committed packet via the "
    "committed instrument's own verify_seal (recomputed == doc == prereg); "
    "(2) the attestation recompute matches the committed record on ALL "
    "countable fields (30 rows, 167 completed calls, 0 error lines, "
    "requested==served==registered agnes-3.0-flash, both custody key digests "
    "5c4dffd28fe4+d0c666a3842f); (3) 30/30 unique problem_ids, all non-smoke; "
    "(4) row/event recomputes match every run-record claim: critic 24 CLEAN / "
    "6 FLAG, 0 on-row sign contradictions, winner non_schedule_first 30/30, "
    "repairs {1:3, 2:1, 3:26}, full-budget burn 26/30 = 86.7%. Method: Art. "
    "29(c) read-only recompute (the committed parser imported, zero LLM, zero "
    "quota, zero gateway calls; the committed attestation.json bytes NOT "
    "rewritten, Art. 4 — post-verify sha256_16 86046640add9dbc6 byte-exact). "
    "Typed incident disclosed in the record: the committed `attest` mode "
    "itself writes into the live artifact (one field: window_ended_at) — "
    "self-caught, restored byte-exact before any commit, instrument "
    "untouched in this verifier lane, read-only patch recommended for a "
    "builder round. The AUDITOR's scoring of the 30 rows vs the PRIVATE "
    "rubric remains the separate open lane (the path to score 6)."
)

c0104 = next(c for c in claims if str(c.get("claim_id")) == "c-0104")
assert str(c0104.get("status")).upper() == "OPEN", "c-0104 not OPEN"
c0104["status"] = "DONE"
c0104["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
c0104["completion_note"] = (
    "DONE: the verifier lane is complete and green — eval/"
    "r92_v11_verifier_c0104.json verdict VERIFIED (seal EXACT; attestation "
    "recompute matches on all countable fields; 30/30 unique non-smoke rows; "
    "every run-record claim recomputes TRUE from committed bytes). Typed "
    "incident self-caught and disclosed in the record: the committed "
    "`attest` mode rewrote window_ended_at on the live artifact when invoked "
    "as documented — restored byte-exact (git checkout, sha256_16 "
    "86046640add9dbc6) before any commit; the lane then recomputed through "
    "the pure-compute path only. The instrument was NOT edited in this lane "
    "(verifier scope + possible seal/prereg pinning); the read-only patch is "
    "a typed recommendation for a builder round. Both flips landed in THIS "
    "same registry snapshot (the DONE-without-verifier CI rule satisfied by "
    "the c-0104 VERIFIER claim + the c-0102 flip together)."
)

if isinstance(reg, dict):
    reg["claims"] = claims
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("c-0102 OPEN->DONE (credit builder-r91s1); c-0104 OPEN->DONE — same snapshot")
