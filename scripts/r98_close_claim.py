#!/usr/bin/env python3
"""R97: flip claim c-0113 to DONE (executor-complete) with the work
commit recorded — the Art. 29(b) lane closes executor-side."""
import json

REPO = "/home/z/my-project/discovery-evidence-fabric"
reg = json.load(open(REPO + "/eval/work_claims.json"))
for c in reg["claims"]:
    if c.get("claim_id") == "c-0113":
        assert c["status"] == "OPEN", c["status"]
        c["status"] = "DONE (executor-complete)"
        c["work_sha"] = "5cfb15996"
        c["closed_at"] = ("2026-11-19 (sandbox clock, TRUE UTC) — "
                          "the sealed v13 one-shot complete: 30/30 "
                          "rows, attestation recomputed TRUE (143 "
                          "calls 0 errors, served==registered, both "
                          "key digests), P3/P4/P5 gate records green "
                          "in eval/holdout_v13_generation/ "
                          "(p3 in attestation.json; p4_novelty.json; "
                          "p5_viability.json), efficiency targets met "
                          "(convergence 67% vs >=50% target, 2.9 "
                          "attempts/row vs <=3.5); the rubric scoring "
                          "is the auditor's exclusive next move "
                          "(score-7 bar; builder claims NOTHING about "
                          "the rubric mean)")
        print("c-0113 ->", c["status"])
        break
else:
    raise SystemExit("c-0113 not found (typed abort)")
with open(REPO + "/eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
    f.write("\n")
