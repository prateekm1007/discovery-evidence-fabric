#!/usr/bin/env python3
"""r170s2_file_claims.py — the r170s2 window's registry acts:
  1. session builder-r170s2 registered (Art. 29(a));
  2. VERIFIER claim c-0274 (DONE) for the r169s1 panel-complete
     measurement (the Art. 29(c) duty: DONE measurement needs a
     verifier record; the recompute diff=0);
  3. the P5 J2-seat status record carried in the claim note (DIR 4):
     cent-ai hy4 403 (degraded from 404/HTML yesterday), G0 live,
     the ctai re-seat proposal stays owner/auditor-authorized (the
     prereg pins J2=hy4; V128 forbids unilateral swaps).
"""
from __future__ import annotations
import json, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WC = REPO / "eval" / "work_claims.json"
CID = REPO / "eval" / "claim_next_id.txt"

d = json.loads(WC.read_text(encoding="utf-8"))
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

ver = json.loads((REPO / "eval" / "r170s2_panel_verification.json").read_text())
assert ver["row_diff_count"] == 0 and ver["serving_alpha_abs_diff"] == 0.0

d["sessions"]["builder-r170s2"] = {
    "role": "VERIFIER (the Art. 13 byte-recompute lane for the AM51 amended "
            "panel + the P5 v2 seat-status watch)",
    "registered": "2026-11-27 (sandbox clock, TRUE UTC ~12:05Z)",
    "base_sha": "8f40640b7 (the r169s1 panel-complete commit, the queue tip)",
    "note": "DIR 1 verified at the pinned tips (EPISTEMIC 153ac62efca36c2d @ "
            "d794adb54a5e/8f40640b7; AUDITOR 3775f869a1c19a96 @ 94a6a74b5841; "
            "ledger V134 actual-read; vault r77 restore 11/11; CI on the tip "
            "surface completed/success via the API).",
}

d["claims"].append({
    "claim_id": "c-0274",
    "work_id": "r153-xkiro-qualify-panel-v18",
    "role": "VERIFIER",
    "status": "DONE",
    "kind": "measurement",
    "session_id": "builder-r170s2",
    "claimed_at": now,
    "lease_expiry": "2026-11-27T22:00:00Z",
    "base_sha": "8f40640b7 (the panel-complete commit — the verified bytes)",
    "artifact_paths": [
        "eval/r170s2_panel_verification.json",
        "scripts/r170s2_verify_panel.py",
    ],
    "note": "the Art. 29(c)/Art. 13 VERIFIER act for the AM51 amended panel "
            "(the r169s1 panel-complete measurement, claim c-0272, commit "
            "8f40640b7): the two-axis majority tally + the serving alpha "
            "RECOMPUTED FROM COMMITTED BYTES ONLY (the 90 VALID panel leg "
            "JSONs — snlite 30 + gpt6luna 30 + hy4f 30 — + the committed "
            "candidate set + the engine's own krippendorff code + the r148 "
            "corpus at b218b1e9d; zero LLM calls, never a re-run). RESULT: "
            "diff=0 on every axis — tally 3/30 = 10.0% (v17-01-slurry-pump "
            "3/3-viable 2/3-nonobvious; v17-08-freeze-concentration 3/3+2/3; "
            "v17-25-hydrogen-valve 2/3+2/3), row_diff_count 0, serving alpha "
            "0.888277 recomputed == committed (abs diff 0.0), 0 missing "
            "VALID legs. The >=50% score-8 bar is NOT MET by the frozen v18 "
            "candidates under the amended serving set (snlite+gpt6luna+hy4f, "
            "3 judges / 3 families, self-cert NONE) — the measurement stands "
            "honest and byte-verified; the rubric-vs-serving-bar divergence "
            "(generation-strength mean 3.73 / 73-80% strong vs the panel's "
            "10% two-axis majority) is an AUDITOR/OWNER adjudication point, "
            "never a builder bar change. P5 v2 J2-SEAT STATUS (DIR 4, typed "
            "from probes 11:55-12:00Z): G0 tokenrouter LIVE (probe 200); "
            "J2 cent-ai hy4-flash:free now 403 Forbidden (degraded from "
            "404/HTML yesterday — the outage is day 2 and deepening); the "
            "two-seat gate refuses to fire (correct fail-closed). The ctai "
            "backups openai/gpt-6-astra + openai/gpt-6.1-sol both probe 200 "
            "and are UNQUALIFIED-for-P5 but qualified-class ctai transports; "
            "however the prereg PINS J2=hy4 (V128: no unilateral seat "
            "swaps) — the re-seat (J2 -> a live ctai judge with its own "
            "P5 judge qualification) is an owner/auditor authorization, "
            "carried forward as the standing proposal.",
})
CID.write_text("c-0275\n", encoding="utf-8")
WC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")
print("session registered; VERIFIER claim c-0274 (DONE) filed; counter -> c-0275")
