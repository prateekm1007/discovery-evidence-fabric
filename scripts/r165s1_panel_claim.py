#!/usr/bin/env python3
"""r165s1_panel_claim.py — file c-0268, the post-reset panel byte-resume claim.

Claim-before-work (DIR 7): the panel byte-resume (5 snlite + 30
mst14b legs on the fresh xkiro free pool) fires at the Nov 27
00:00 UTC reset. The prior panel claim c-0265's lease dies at
2026-11-26T20:00Z — BEFORE the reset — so a fresh claim spanning
the reset window is filed now, with the lease covering the resume
window. The xkiro vault key is AUTH-VALID (429 quota at 13:41Z,
NOT 401 — the wrong-.ai-TLD probe error is corrected in V128).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "eval/work_claims.json"
NEXT = REPO / "eval/claim_next_id.txt"

reg = json.loads(REG.read_text())
claims = reg["claims"] if isinstance(reg, dict) else reg
next_id = NEXT.read_text().strip()
assert next_id == "c-0268", f"unexpected next id {next_id}"

claim = {
    "claim_id": "c-0268",
    "work_id": "r153-xkiro-qualify-panel-v18",
    "role": "EXECUTOR",
    "status": "OPEN",
    "kind": "measurement",
    "session_id": "builder-r165s1",
    "claimed_at": "2026-11-26T13:45:00Z",
    "lease_expiry": "2026-11-27T08:00:00Z",
    "takes_over": "c-0265 (lease dies 2026-11-26T20:00Z, before the reset)",
    "base_sha": "PENDING — the pre-reset queue tip at fire time",
    "artifact_paths": [
        "scripts/r153_p4_panel_v18.py",
        "scripts/r153s1_tally_recompute.py",
        "eval/r148_p4_panel_v18/",
        "eval/r149_v18_panel/packs_sealed_set.json",
        "eval/r153s1_panel_resume_state.json",
    ],
    "note": "FRESH claim (claim-before-work, DIR 7): the ONE post-reset "
            "xkiro run = the panel byte-resume (5 snlite + 30 mst14b; "
            "hy4f 30/30 + snlite 25/30 stand, byte-resume skips them). "
            "The fresh daily free pool belongs to THIS run first — no "
            "qualifications, no seal builds, no concurrent xkiro lanes "
            "before it completes (the c-0265 disclosure: the 2026-11-25 "
            "double-burn was three concurrent lanes sharing the pool). "
            "The xkiro vault key f6c09bee9bde AUTH-VALID on "
            "api.xkiro.com (429 quota 13:41Z, not 401 — the .ai-TLD "
            "probe error corrected per V128). Accept: the full 3-judge "
            "two-axis majority tally >=50% viable+non-obvious on the "
            "30 candidates + r153s1_tally_recompute.py diff=0 -> "
            "score-8 evidence.",
}
if isinstance(reg, dict):
    reg["claims"] = claims + [claim]
    REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
else:
    REG.write_text(json.dumps(claims + [claim], indent=1, ensure_ascii=False) + "\n")
NEXT.write_text("c-0269\n")
print("filed", claim["claim_id"], "lease to", claim["lease_expiry"])
