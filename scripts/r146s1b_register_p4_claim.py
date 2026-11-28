#!/usr/bin/env python3
"""R146s1-b: register the DIR-4 EXECUTOR claim (claim-before-work,
Art. 29(b)) — the calibrated P4 panel on the v17 STRENGTHENED full
set (the score-8 gate; R145-F2).

State from bytes: eval/r146_p4_panel/packs.json exists (30 packs,
the v17-strengthened candidates + top-3 SPECTER2-nearest prior arts
each, sha-parity presentation rotation) but ZERO judge legs exist —
the twin's 'DIR-4 in flight' stopped at the packs. The twin's
c-0250 lease covers the strength LANE (r146-v17-s2-strength), not
the panel; no claim exists for the panel work. This lane registers
c-0252 and executes with the twin's own committed driver
(scripts/r146_p4_panel_oneshot.py — reads the audit-branch sealed
v17 problems, the V109-qualified 4-judge panel, blind+rotated,
EPO problem-solution ruling contract, byte-resume, no re-roll).
"""
import json

REG = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
COUNTER = "/home/z/my-project/discovery-evidence-fabric/eval/claim_next_id.txt"

with open(REG) as f:
    reg = json.load(f)
by_id = {c["claim_id"]: c for c in reg["claims"]}

# sanity gates
import os
assert not any(s.startswith("dsr1__") for s in os.listdir(
    "eval/r146_p4_panel")), "panel legs already exist — verifier role"
assert by_id["c-0250"]["status"] == "OPEN"
assert by_id["c-0251"]["status"] == "DONE"

TS = "2026-11-24 (sandbox clock)"
SESSION = "builder-r146s1-b"
reg["sessions"][SESSION] = {
    "claimed_at": TS,
    "role": "builder",
    "note": (
        "R146 second window (the c-0251 tip-red-heal lane): now the "
        "EXECUTOR of the DIR-4 P4 panel on the v17 strengthened full "
        "set — the twin's packs stood un-run (zero legs); the twin's "
        "c-0250 lease covers the strength lane, not the panel. "
        "Constitutions full-read verified at the DIR-1 pins."
    ),
}
reg["claims"].append({
    "work_id": "r146-p4-panel-v17-strengthened",
    "claim_id": "c-0252",
    "role": "EXECUTOR",
    "session_id": SESSION,
    "kind": "one_shot",
    "status": "OPEN",
    "base_sha": "560c55a37",
    "lease_expiry": "2026-12-01T23:59:00Z",
    "claimed_at": TS,
    "registered_at": TS,
    "artifact_paths": [
        "eval/r146_p4_panel/",
        "scripts/r146s1b_register_p4_claim.py"
    ],
    "title": (
        "R146S1-B EXECUTOR (claim c-0252, base 560c55a37): DIR-4 — the "
        "calibrated P4 panel on the v17 STRENGTHENED full set (the "
        "score-8 gate re-run, R145-F2): the V109-qualified 4-judge "
        "panel (dsr1/qw32b/qwen235b/dsv32, 2 non-agnes families) blind "
        "+ sha-parity rotated on the 30 committed packs "
        "(eval/r146_p4_panel/packs.json — the strengthened v17 "
        "candidates vs their top-3 SPECTER2-nearest EXTERNAL prior "
        "arts, 120-doc corpus), the EPO problem-solution ruling "
        "(closest art -> distinguishing features -> objective "
        "technical problem -> viable/non_obvious), AM47 "
        "viability-necessity verbatim, ONE generation per (judge, "
        "candidate) — no re-roll regardless of outcome (Art. 7); "
        "byte-resume continues the same run. Driver: the twin's "
        "committed scripts/r146_p4_panel_oneshot.py unchanged. "
        "Acceptance (the owner's DIR-4): >=50% viable+non-obvious on "
        "the FULL set; recompute diff=0; no subsets. The tally + the "
        "independent recompute commit with the raw legs."
    ),
    "notes": (
        "The packs carry the strengthened generation's candidate_text "
        "(the 170be8ab7 run, quant 30/30, 16 strong/14 marginal "
        "builder-screen); the panel ruling is the independent "
        "non-obviousness measure against EXTERNAL prior art."
    ),
})

with open(COUNTER) as f:
    cur = f.read().strip()
assert cur == "c-0252", f"counter unexpectedly {cur!r}"
with open(COUNTER, "w") as f:
    f.write("c-0253\n")

with open(REG, "w") as f:
    json.dump(reg, f, ensure_ascii=True, indent=2)
    f.write("\n")

print("c-0252 registered OPEN (r146-p4-panel-v17-strengthened); "
      "counter -> c-0253")
