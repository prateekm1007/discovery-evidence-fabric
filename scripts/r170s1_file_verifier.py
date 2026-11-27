#!/usr/bin/env python3
"""r170s1_file_verifier.py — file the Art. 29(c) VERIFIER claim c-0273 on
work r153-xkiro-qualify-panel-v18 (closes the DONE-measurement-needs-
verifier gate for c-0271)."""
from __future__ import annotations
import json, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WC = REPO / "eval" / "work_claims.json"
CID = REPO / "eval" / "claim_next_id.txt"

d = json.loads(WC.read_text(encoding="utf-8"))
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
ver = json.loads((REPO / "eval" / "r170s1_am51_bars_verification.json").read_text())
assert ver["diff_is_zero"], "the recompute diff must be 0 before filing"

d["claims"].append({
    "claim_id": "c-0273",
    "work_id": "r153-xkiro-qualify-panel-v18",
    "role": "VERIFIER",
    "status": "DONE",
    "kind": "measurement",
    "session_id": "builder-r170s1",
    "claimed_at": now,
    "lease_expiry": "2026-11-27T22:00:00Z",
    "base_sha": "fc4f348d8 (the AM51 outcome commit — the verified bytes)",
    "artifact_paths": [
        "eval/r170s1_am51_bars_verification.json",
        "scripts/r170s1_verify_bars.py",
    ],
    "note": "the Art. 29(c)/Art. 13 VERIFIER act for c-0271's DONE "
            "measurement: the AM51 aya32b bars RECOMPUTED FROM COMMITTED "
            "BYTES ONLY (the 24 leg JSONs as committed at fc4f348d8 + the "
            "committed r148 corpus at b218b1e9d + the engine's own "
            "rcal_qualification/am47_bias/krippendorff code; zero LLM "
            "calls, never a re-run). diff vs the committed "
            "eval/r168_am51_seal/BARS.json = 0 on every axis: acc 0.667 "
            "(< 0.8, FAIL), answered 1.0, AM47 imbalance 0, serving alpha "
            "0.611719, qualified=False. The typed bar-FAIL verdict stands "
            "byte-verified; no seal, no panel — the consequence chain in "
            "eval/r170s1_am51_outcome.json is confirmed. Same-session "
            "disclosure: the recompute ran in a FRESH PROCESS over "
            "committed bytes (the Art. 13 recompute class); a fully "
            "independent-session re-verification stays the next window's "
            "optional duty.",
})
CID.write_text("c-0274\n", encoding="utf-8")
WC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")
print("filed: VERIFIER claim c-0273 (DONE); counter -> c-0274")
