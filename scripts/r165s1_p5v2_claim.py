#!/usr/bin/env python3
"""r165s1_p5v2_claim.py — file c-0269, the P5 v2 FRESH counting-run claim.

The mutex conflict (resolved here, before the hy4 recovery trigger):
- r164s1 (builder-r160s1, holds c-0267): "the 9-item tail byte-resume
  fires when the hy4 J2 upstream serves" — the TAIL-COMPLETION plan.
- r165s1 (this lane): the V127 re-authorization — "a fresh authorized
  run on the same sealed corpus (sha c9670d8dd4b55c0c) with live
  J2+generator is the path to a COUNTING DIR-4 verdict" — the FRESH
  counting run (all 30 items under live seats).

The authority is the auditor's: V127's adjudication names the FRESH
run as the counting path. The tail-completion can only produce
diagnostics — r163s1's own terminal record (the lane that typed the
21/30 infra-terminal) says exactly this: "completing the tail 9 with
live seats yields diagnostics, not a passing verdict; a fresh
authorized run on the same sealed corpus with live J2+generator is
the path to a COUNTING DIR-4 verdict". Firing BOTH = a double-burn of
the corpus (DIR 7: one run per corpus; 0 double-burns).

So: the tail-resume plan is RETIRED (it contradicts its own origin
typing + V127); the ONE P5 v2 run that fires on hy4 recovery is the
FRESH counting run, under this claim, via
scripts/r165_p5_v2_counting_run.py (two-seat live gate; the UNMODIFIED
runner; the infra-terminal 21/30 archived, not overwritten).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "eval/work_claims.json"
NEXT = REPO / "eval/claim_next_id.txt"

reg = json.loads(REG.read_text())
claims = reg["claims"] if isinstance(reg, dict) else reg
next_id = NEXT.read_text().strip()
assert next_id == "c-0269", f"unexpected next id {next_id}"

claim = {
    "claim_id": "c-0269",
    "work_id": "r159-p5-rediscovery-v2-counting",
    "role": "EXECUTOR",
    "status": "OPEN",
    "kind": "measurement",
    "session_id": "builder-r165s1",
    "claimed_at": "2026-11-26T14:20:00Z",
    "lease_expiry": "2026-11-27T12:00:00Z",
    "takes_over": "c-0267 (builder-r160s1) — the P5 v2 lane, with the "
                  "firing plan CORRECTED to the V127 fresh counting run "
                  "(the 9-item tail-resume plan is retired: it "
                  "contradicts r163s1's own terminal typing and V127, "
                  "and firing both = a corpus double-burn)",
    "base_sha": "d4dd95032 (the r164s1 yield commits)",
    "artifact_paths": [
        "scripts/r165_p5_v2_counting_run.py",
        "scripts/r159_p5_v2_run.py",
        "eval/r159_p5_v2_corpus/sampled_items.jsonl",
        "eval/r159_p5_v2_prereg.json",
        "eval/r159_p5_v2_checkpoint.json",
        "eval/r159_p5_v2_run.json",
        "eval/r159_p5_v2_infra_terminal/",
    ],
    "note": "ONE firing plan for the P5 v2 lane (the hy4-recovery "
            "trigger): the V127 FRESH counting run — all 30 items of "
            "the sealed corpus c9670d8dd4b55c0c under live seats (G0 "
            "tokenrouter deepseek + J1 z-ai glm + J2 cent-ai hy4 budget "
            "4000 + Jt2 z-ai glm), via the two-seat-live-gated wrapper. "
            "The 21/30 infra-terminal is archived (eval/"
            "r159_p5_v2_infra_terminal/), never overwritten — forward-"
            "only. NO seat swaps (V128: a live qualified J2 = hy4 when "
            "it serves; no unilateral judge changes). Accept per the "
            "prereg: >=40% RECOVERED (min 12/30), 0 canary, >=1 T1, "
            ">=1 T2, 0 interventions, byte-resume across windows.",
}
if isinstance(reg, dict):
    reg["claims"] = claims + [claim]
    REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
else:
    REG.write_text(json.dumps(claims + [claim], indent=1, ensure_ascii=False) + "\n")
NEXT.write_text("c-0270\n")
print("filed", claim["claim_id"], "lease to", claim["lease_expiry"])
