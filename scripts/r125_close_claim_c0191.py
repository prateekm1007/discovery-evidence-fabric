#!/usr/bin/env python3
"""Flip claim c-0191 OPEN -> DONE (the F31e outcome) + register the
verifier record c-0194."""
import datetime
import json

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
have = {c["claim_id"] for c in d["claims"]}
for cl in d["claims"]:
    if cl.get("claim_id") == "c-0191":
        assert cl["status"] == "OPEN", cl["status"]
        cl["status"] = "DONE"
        cl["notes"] = (
            "EXECUTED to its typed outcome (the R125 verdict dir 2, "
            "TOP): 48/48 rows (2 independent bare-author draws x 24 "
            "items — the frozen r118 authoring-directive bytes; the "
            "improved-directive reviewer arm under the CANONICAL "
            "F97-fixed detector; zero typed fails; no-findings items "
            "delivered themselves with zero calls spent). THE RESULT "
            "(scoring.json + the independent cross-check PASS): "
            "POOLED n=48 bare 13/48 (0.2708) vs succ 2/48 (0.0417) "
            "<= 0.25; paired bootstrap seed 127 mean +0.2292 CI95 "
            "[+0.0833,+0.375] EXCLUDES 0 (13 better / 2 worse); "
            "damage 2/35 = 0.0571 <= 0.25 (r125-05-s2, r125-07-s2). "
            "PER DRAW: d1 0.1667 -> 0.0833 (damage 0.1), d2 0.375 -> "
            "0.0 (damage 0.0) — concordant, both draws under the "
            "absolute gate. Per class: duty_pricing 13->2, "
            "input_availability 0->0 (the canonical detector's "
            "recall envelope, consistent with c-0187), "
            "physics/constraint 0->0. ALL THREE SCORE-9 GATES MET ON "
            "FRESH BILLS NEVER IN THE F97 CALIBRATION CORPUS — the "
            "score-9 acceptance is typed for the auditor; no score "
            "claim by this session. Art. 27: a PROBE round "
            "(measurement only, zero engine lines)."
        )
        cl["completed_at"] = f"{NOW} (sandbox clock, TRUE UTC)"
        print("claim c-0191 -> DONE (the F31e outcome recorded)")
if "c-0194" not in have:
    d["claims"].append({
        "work_id": "r125-f31e-clean-confirmation",
        "claim_id": "c-0194",
        "role": "VERIFIER",
        "session_id": "builder-r117s1",
        "kind": "task",
        "status": "DONE",
        "base_sha": "83234e4ee",
        "lease_expiry": "2026-11-29T23:59:00Z",
        "artifact_paths": ["eval/r125_f31e_run/",
                           "scripts/r125_f31e_crosscheck.py"],
        "title": "VERIFIER record for work_id "
                 "r125-f31e-clean-confirmation",
        "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "completed_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "notes": "Recomputed from committed bytes (Art. 13, never "
                 "re-ran the LLM legs): the independent arithmetic "
                 "cross-check (scripts/r125_f31e_crosscheck.py — a "
                 "separate construction: explicit-index bootstrap, "
                 "independent aggregates, the same-draw construction "
                 "verified byte-identical per item) reproduces every "
                 "scoring.json number: pooled n=48 bare 13/48 "
                 "(0.2708) vs succ 2/48 (0.0417) <= 0.25; seed-127 "
                 "bootstrap mean +0.2292 CI95 [+0.0833,+0.375] "
                 "EXCLUDES 0; damage 2/35 = 0.0571 <= 0.25 — all "
                 "three score-9 gates recompute TRUE."})
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print("registry updated (c-0191 DONE + verifier c-0194)")
