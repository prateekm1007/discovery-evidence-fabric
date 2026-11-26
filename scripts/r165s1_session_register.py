#!/usr/bin/env python3
"""r165s1_session_register.py — heal the red tip (DIR 5, forward-only).

The failure (run 139955580318, tip b03a5a835): "c-0268: session
builder-r165s1 is not registered (Art. 29(a): identity on first
push)" — this lane filed c-0268/c-0269 (and their predecessor
commits) WITHOUT registering the session in the registry's
sessions{} object. The heal is additive: register
builder-r165s1 with its lineage, base_sha, and the full-read
evidence — no history is rewritten (Art. 4).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "eval/work_claims.json"

reg = json.loads(REG.read_text())
sessions = reg.setdefault("sessions", {})

sessions["builder-r165s1"] = {
    "role": "EXECUTOR (panel c-0268 + P5 v2 counting run c-0269; "
            "continuation of the r159s2/r163 P5 lane lineage and the "
            "r153 panel lane after the r164s1 yield)",
    "registered": "2026-11-26 (sandbox clock, TRUE UTC ~14:30Z)",
    "base_sha": "b03a5a835985ae81f917d64e300cd6a1fd4f2a99",
    "note": "DIR 1 verified at the pinned tips (EPISTEMIC "
            "153ac62efca36c2d @ queue tip, full read; AUDITOR "
            "3775f869a1c19a96 @ audit tip, full read; ledger V129 "
            "actual-read; vault digests verified f1ebca5f9b62/"
            "0af8db243dee/a5beece70d05/f6c09bee9bde/c148574f6215, "
            "secret-grep 0 live). The session MISSED its own Art. "
            "29(a) first-push registration when filing c-0268/"
            "c-0269 — the red tip b03a5a835 (run 139955580318) is "
            "that omission, healed forward-only here (the registry "
            "is additive; no claim entries are edited). The lanes: "
            "c-0268 = the ONE post-reset xkiro panel byte-resume "
            "(00:05Z scheduled, r164s1 stands down to VERIFIER); "
            "c-0269 = the V127 fresh counting run on the sealed "
            "corpus c9670d8dd4b55c0c (the wrapper two-seat gate; "
            "c-0267 yields accepted by both lanes).",
}

REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
print("registered builder-r165s1; sessions now:", len(sessions))
