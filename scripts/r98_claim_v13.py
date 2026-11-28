#!/usr/bin/env python3
"""R97: stake claim c-0113 (Art. 29(b) claim-before-work) — the v13
lane: authoring + the P3/P4/P5 harnesses + the sealed one-shot. Staked
BEFORE any v13 problem byte exists; the push is the lock."""
import json, datetime, subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
BASE = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                      cwd=REPO).stdout.decode().strip()[:9]

claim = {
    "claim_id": "c-0113",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "holdout-v13-lane",
    "title": "THE V13 LANE (builder-r95s1): author the fresh sealed set "
             "(n>=30, domain-disjoint from v1-v12), implement the "
             "AM84-P3/P4/P5 gates (P3 speed median<=2min/worst<=5min "
             "measured on the sealed v13 run; P4 novelty >=0.2 cosine "
             "from the nearest prior-art row for >=5/30 rows, measured "
             "by a deterministic committed-method embedding — "
             "sklearn TF-IDF/char-ngram cosine over the committed "
             "prior-art corpus, the disclosed SPECTER2-or-equivalent "
             "since SPECTER2 weights are unreachable offline, method "
             "typed in the preregistration; P5 external confirmation "
             ">=1/30 via real web semantic search on committed rows, "
             "URLs recorded), land the convergence lever (the c-0109 "
             "corrector's tag vocabulary extended with the machine's "
             "OWN measure classes — typed procurement rules, never a "
             "guessed tag, zero-LLM, CI-tested; targets >=50% "
             "zero-findings and <=3.5 attempts/row), then the sealed "
             "v13 one-shot (all five binds + c-0109 + c-0110 active, "
             "agnes-3.0-flash, 30/30 attestation) and the typed "
             "handoff for the auditor's rubric scoring (target score "
             "7: mean>=3.5, CI95 lower>3.0, 0/0/0 hard clauses + the "
             "P3/P4/P5 gates). CUSTODY DISCLOSURE: the vault currently "
             "resolves AGNES_API_KEY only (AGNES_API_KEY_2 lapsed with "
             "the sandbox recycle; its value was never committed, so "
             "unrecoverable) — the run proceeds on the primary key "
             "with the ordered-rotation degradation TYPED in the run "
             "record and handoff (identity per call unaffected; both "
             "digests re-attested honestly). STATUS: OPEN — the "
             "authoring, harnesses and run follow this claim (the "
             "claim is staked before any v13 problem byte exists).",
    "status": "OPEN",
    "session_id": "builder-r95s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": BASE,
    "lease_expiry": "2026-11-21T23:59:00Z",
    "takes_over": None,
    "artifact_paths": [
        "scripts/r98_v13_one_shot.py",
        "scripts/r98_p4_novelty.py",
        "scripts/r98_p5_viability.py",
        "audit/holdout_v13/holdout_v13_problems.json",
        "audit/holdout_v13/PREREGISTRATION.json",
        "eval/holdout_v13_generation/",
        "discovery_fabric/engine/tool_grounded_critic.py",
        "tests/test_r97_tool_grounded_critic_v13.py",
    ],
    "notes": "Art. 29(b): claimed before any v13 problem byte exists "
             "(the set is builder-authored this round per the "
             "auditor's AM84 direction; the seal computes from the "
             "committed problem bytes at authoring time; the private "
             "rubric stays auditor+owner custody — builder NEVER "
             "reads a rubric). The v12 packet is BURNED per AM84; its "
             "rows stay read-only @ 23ab8ad36. Score 6 achieved; "
             "AM78-P6 progression forcing: P3/P4/P5 next, not another "
             "acceptance re-run.",
    "no_problem_read_before_claim": True,
}

reg_path = f"{REPO}/eval/work_claims.json"
with open(reg_path) as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg \
    else reg
ids = [str(c.get("claim_id")) for c in claims]
assert "c-0113" not in ids, "c-0113 already staked — race!"
claims.append(claim)
if isinstance(reg, dict):
    reg["claims"] = claims
with open(reg_path, "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print(f"c-0113 staked OPEN at base {BASE} — claims now {len(claims)}")
