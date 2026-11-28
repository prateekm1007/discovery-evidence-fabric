#!/usr/bin/env python3
"""r30_claim_v76.py — file claim c-0031 (the AM29 D1+D2 verification
round: the dev battery's 18 intervention rows re-drawn under the V7.6
machine) BEFORE any LLM call (Art. 29(b)). Idempotent."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
if "c-0031" in {c["claim_id"] for c in d["claims"]}:
    print("c-0031 already filed")
    raise SystemExit(0)
d["claims"].append({
    "claim_id": "c-0031", "work_id": "r30-v76-class-direction",
    "session_id": "builder-r20s1", "role": "EXECUTOR",
    "kind": "measurement", "base_sha": "8a8dfe20d",
    "claimed_at": "2026-11-16T13:05:00Z",
    "lease_expiry": "2026-11-16T18:00:00Z", "status": "OPEN",
    "takes_over": None,
    "artifact_paths": ["eval/pairs/r30_v76_tuned/",
                       "eval/r30_v76_tuning_generation.json"],
    "notes": "AM29 D1+D2 VERIFICATION (a DEV measurement, not an "
             "acceptance test — Art. 6: acceptance happens only on a "
             "fresh auditor-authored sealed set, v5). The dev "
             "battery's 18 intervention rows re-drawn ONCE each under "
             "the V7.6 machine: the frozen V7.4 path (one generation "
             "pass under contract_for_v72 + critic + type gate + "
             "typed scans + NEUTRAL repair directive, budget 3, "
             "K_GEN=1, judge-blind) with TWO pre-registered deltas: "
             "(1) the repair directive gains the V76 clauses "
             "(PERMITTED-SET: read the constraint at answer time; "
             "param-exhaustive sets admit no physical measure; "
             "DIRECTION-OF-EFFECT: the structured statement; a "
             "mechanism that moves a driving variable toward the "
             "failure is out of class; a LIMIT permits decrease "
             "only) — r30_v76_directive.py, pushed in 8a8dfe20d "
             "BEFORE this claim; (2) the machine's scan set gains "
             "scan_allowed_measures_class (ALLOWED_MEASURE_TYPE_"
             "OUTSIDE / LIMIT_DIRECTION_VIOLATION) and "
             "scan_physics_direction (PHYSICS_DIRECTION_UNSTATED / "
             "DRIVER_AS_REMEDY) — both pinned green against the "
             "auditor's AM29 verdict bytes before this round. The 12 "
             "predictor rows stay BYTE-FROZEN (they generalize per "
             "AM29: predictor 3.0/4). Rows land PENDING-AUDITOR "
             "(Art. 10); the machine-side claim is: 0 rows fire "
             "ALLOWED_MEASURE_TYPE_OUTSIDE / LIMIT_DIRECTION_"
             "VIOLATION, and 100% of rows carry the structured "
             "DIRECTION-OF-EFFECT statement, with the dev gate "
             "re-read by the auditor on the re-drawn rows. VERIFIER: "
             "peer session invited (Art. 13)."})
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("claim c-0031 filed (r30-v76-class-direction)")
