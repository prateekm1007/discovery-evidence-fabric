#!/usr/bin/env python3
"""R80: stake claim c-0108 (Art. 29(b) claim-before-work) — the P3
conformal FA-control prototype lane (AM80 direction 4): MAPIE
(BSD-3-Clause, NOTICE row exists) conformal prediction intervals wrapped
around a lag-feature one-step predictor — the mechanics proof for
fault-alert (FA) control with coverage guarantees on synthetic data
(zero network, deterministic). The Time-MoE / MOMENT foundation-model eval
and the real C-MAPSS/XJTU-SY/CWRU runs are the typed next steps (heavy
downloads; the vault HF_TOKEN custody is in place)."""
import json, datetime

HEAD = "4198a764b"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

claim = {
    "claim_id": "c-0108",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "conformal-fa-control-dev",
    "title": "AM80 direction 4 DEV prototype (builder-r80s1): the "
             "conformal FA-control wrapper — MAPIE TimeSeriesRegressor "
             "(BSD-3-Clause; the NOTICE pip row already exists, planned "
             "D5) around a deterministic lag-feature one-step predictor; "
             "typed FA signal = the latest observation outside the "
             "conformal interval at the configured confidence level; "
             "CI-wired deterministic tests on synthetic AR series (fixed "
             "seed): empirical coverage >= the declared level on in-"
             "distribution holdout, an injected level-shift produces a "
             "typed FA within a bounded number of steps, determinism, "
             "zero-network, freeze parity. The Time-MoE (Apache-2.0) / "
             "MOMENT (MIT) foundation-model evals + the real dataset runs "
             "are typed next steps (heavy downloads; HF_TOKEN custody is "
             "in place via the vault bootstrap this session).",
    "status": "OPEN",
    "session_id": "builder-r80s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": HEAD,
    "lease_expiry": "2026-11-20T23:59:00Z",
    "takes_over": None,
    "artifact_paths": [
        "scripts/r80_conformal_fa.py",
        "tests/test_r80_conformal_fa.py",
    ],
    "notes": "Art. 29(b): claimed BEFORE any work byte. Lane division: "
             "c-0106 (peer) untouched; c-0107 (chemistry) DONE. No frozen "
             "bytes; adoption-gated; the predictor-answer BINDS (the "
             "predictor-violation scan surface) are read-only referenced, "
             "not edited.",
    "no_problem_read_before_claim": True,
}

with open("eval/work_claims.json") as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg else reg
ids = [str(c.get("claim_id")) for c in claims]
assert "c-0108" not in ids, "c-0108 already staked — race!"
claims.append(claim)
if isinstance(reg, dict):
    reg["claims"] = claims
with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print(f"c-0108 staked OPEN at base {HEAD} — claims now {len(claims)}")
