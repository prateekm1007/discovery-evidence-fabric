#!/usr/bin/env python3
"""R123: flip claim c-0183 OPEN -> DONE with the F31c typed outcome."""
import datetime
import json

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for cl in d["claims"]:
    if cl.get("claim_id") == "c-0183":
        assert cl["status"] == "OPEN", cl["status"]
        cl["status"] = "DONE"
        cl["notes"] = (
            "EXECUTED to its typed outcome (the R122 direction 2): "
            "quota probe OPEN; bare_only 24/24 + successor 24/24 (48 "
            "calls, zero typed fails, byte-skip one-shot held; the "
            "successor record's authored bill verified byte-identical "
            "to the bare arm's committed bytes). THE RESULT (the "
            "pre-registered gates, scoring.json + the independent "
            "cross-check PASS): delivered-defect-rate bare_only 14/24 "
            "(0.583) vs successor 10/24 (0.417); paired bootstrap "
            "seed 123 mean +0.167 CI95 [-0.0417, +0.375] — COVERS 0; "
            "damage gate 2/10 = 0.200 <= 0.25 HOLDS. ACCEPTANCE: "
            "TYPED_NEGATIVE ON THE FRESH SET — the successor rate "
            "(0.417) exceeds the enacted 0.25 gate and the CI covers "
            "0; the score-9 axis question returns to the auditor. "
            "THE DECOMPOSITION (typed, for the adjudication): the "
            "point estimate REPLICATES the F31b positive exactly "
            "(mean diff +0.167 both runs) on a set that is HARDER "
            "(bare-only 0.583 vs 0.417 on the seeded battery); the "
            "per-class table shows duty_pricing 6->2 (the reviewer "
            "fixes it — the F31b mechanism repeats) and "
            "physics_direction 4->3, but input_availability 9->9 — "
            "REVIEWER-IMMUNE under the standard existing-"
            "instrumentation constraint (it sits in 9 of the 10 "
            "residual-defective successor items); the residual rate "
            "is dominated by a class the reviewer cannot fix BY THE "
            "PROBLEM'S OWN constraint shape. Damage rows: r123-05-s1, "
            "r123-08-s2. Art. 27: a measurement round (no engine "
            "change); zero new guards, zero new claim kinds."
        )
        cl["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
        print("claim c-0183 -> DONE (TYPED_NEGATIVE outcome recorded)")
        break
else:
    raise SystemExit("claim c-0183 not found")
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print("registry updated")
