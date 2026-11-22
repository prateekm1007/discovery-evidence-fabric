#!/usr/bin/env python3
"""Flip claim c-0188 OPEN -> DONE with the F31d typed outcome."""
import datetime
import json

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for cl in d["claims"]:
    if cl.get("claim_id") == "c-0188":
        assert cl["status"] == "OPEN", cl["status"]
        cl["status"] = "DONE"
        cl["notes"] = (
            "EXECUTED to its typed outcome (the R123 verdict dirs 3+5): "
            "48/48 rows (zero authoring calls — the committed bare "
            "bytes of BOTH draws; the improved-directive reviewer "
            "bytes imported byte-exact from the c-0185 prereg; zero "
            "typed fails; no-findings items delivered themselves with "
            "zero calls spent). THE RESULT (the pre-registered gates, "
            "scoring.json + the independent cross-check PASS): POOLED "
            "n=48 bare 18/48 (0.375) vs succ_v2 6/48 (0.125) <= 0.25; "
            "paired bootstrap seed 126 mean +0.25 CI95 "
            "[+0.0833,+0.4167] EXCLUDES 0 (15 better / 3 worse); "
            "damage 3/30 = 0.10 <= 0.25 (r123-06-s1, r123-11-s2, "
            "r123-12-s1). ALL THREE SCORE-9 GATES MET ON THE POOLED "
            "F31D MEASUREMENT — the enactment is the AUDITOR's; no "
            "score claim by this session. Per lane: replication "
            "0.4167 -> 0.0417 (damage 0.0), claiming 0.3333 -> 0.2083 "
            "(damage 0.1875). Per class: duty_pricing 13->4, "
            "physics_direction 5->2, input_availability 0->0 — the "
            "canonical detector's recall question (c-0187) is visible "
            "at the measurement level: the F31d rate rides on "
            "duty_pricing + physics_direction fixes; the "
            "derived-feature/input-name class is silent under the "
            "canonical instrument. Art. 27: a PROBE round (measurement "
            "only, zero engine lines by this session)."
        )
        cl["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
        print("claim c-0188 -> DONE (F31d outcome recorded)")
        break
else:
    raise SystemExit("claim c-0188 not found")
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print("registry updated")
