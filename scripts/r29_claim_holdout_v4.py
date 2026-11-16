#!/usr/bin/env python3
"""r29_claim_holdout_v4.py — file claim c-0029 (holdout-v4-generation,
AM28 D1) BEFORE any problem read / generation call (Art. 29(b)).
Idempotent."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
existing = {c["claim_id"] for c in d["claims"]}
if "c-0029" in existing:
    print("c-0029 already filed")
    raise SystemExit(0)
taken = sorted(c["claim_id"] for c in d["claims"])
assert "c-0029" not in taken
d["claims"].append({
    "claim_id": "c-0029", "work_id": "holdout-v4-generation",
    "session_id": "builder-r20s1", "role": "EXECUTOR",
    "kind": "one-shot-sealed-generation", "base_sha": "7a1b7e050",
    "claimed_at": "2026-11-16T12:00:00Z",
    "lease_expiry": "2026-11-16T16:00:00Z", "status": "OPEN",
    "takes_over": None,
    "artifact_paths": ["eval/holdout_v4_generation/"],
    "notes": "AM28 D1 (the ACCEPTANCE test). Sealed instrument: "
             "audit/holdout_v4/ @ audit tip af3ef4d01, "
             "selection_sha256 00dfaf7e..., authored+sealed by the "
             "AUDITOR (fully auditor-authored problems and rubric; "
             "12 problems = 6 intervention with explicit "
             "allowed-measures lists + 6 predictor with "
             "existing-sensor + failure-defining quantity; "
             "domain-disjoint from v1/v2/v3 and the dev batteries). "
             "Executor = the non-author session (builder-r20s1) per "
             "the sealed pre-registration's division of labor. "
             "Discipline: PROBLEMS ONLY (the PRIVATE rubric is never "
             "opened/listed/copied — fail-closed custody read); ONE "
             "generation pass per problem with the FROZEN V7.4 "
             "machine IMPORTED BYTE-IDENTICAL from the peer's "
             "committed module scripts/r29_tune_battery_v74.py::"
             "machine_generate_v74 (commit 7a1b7e050) — import (not "
             "copy) is the no-contract-edit proof; K_GEN=1, no "
             "selection; NO judge calls, NO baseline assembly, NO "
             "problem iteration, NO rubric feedback; transport-level "
             "transient retries only (a call that returns content is "
             "never re-drawn); pace staggered; resume anchors per "
             "Art. 18/29(d). Machine-internal repair loop is part of "
             "the machine under test (same code path as the R29 dev "
             "battery, disclosed). Outputs: "
             "eval/holdout_v4_generation/ per-problem records + "
             "holdout_v4_generation_record.json, all rows "
             "PENDING-AUDITOR (Art. 10 — the auditor scores with the "
             "PRIVATE rubric; acceptance bar mean >=3.0/4 and 0 "
             "allowed-measures violations; burn after use per the "
             "sealed pre-registration). VERIFIER: peer session "
             "invited — recompute integrity from committed bytes "
             "(Art. 13); flips to DONE only when the verifier record "
             "exists."})
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("claim c-0029 filed (holdout-v4-generation, executor "
      "builder-r20s1)")
