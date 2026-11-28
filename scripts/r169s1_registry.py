#!/usr/bin/env python3
"""r169s1_registry.py — the R169 lane registry acts (Art. 29(a) FIRST).

Registers session builder-r169s1 + files claim c-0272 from the counter
(advanced c-0272 -> c-0273 in the same commit, the claim guard's
protocol): the ctai third-judge lane — the owner's R169 delivery
('use it for judges') supplies openai/gpt-6-luna, whose working ids
(openai/gpt-6-luna, openai/gpt-6-astra, openai/gpt-6.1-sol) were
recovered from the site's own frontend bundle and probe-verified 200
(real generation, ~7-9.5s). This lane TAKES OVER c-0271 (the aya32b
execution — DONE with the bars FAIL: acc 0.667; aya32b SPENT; the
xkiro free pool has ZERO unspent judge candidates). The competing
r170s1 window typed the ctai transport 'NOT-USABLE until the owner
supplies the allowlist model ids' — its probe list was the wrong ids
(mistral/sensenova/hy4 names, never on that provider's allowlist);
the actual ids resolve the finding.
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "eval" / "work_claims.json"
CNT = REPO / "eval" / "claim_next_id.txt"

reg = json.loads(REG.read_text())
sessions = reg.setdefault("sessions", {})
claims = reg["claims"]

assert (CNT.read_text().strip() == "c-0272"), \
    "the counter moved again — re-derive before filing"

sessions["builder-r169s1"] = {
    "role": "EXECUTOR (the R169 owner-delivery window: the ctai "
            "transport vaulted (11/11) + wired for judges; the "
            "gpt-6-luna third-judge qualification + the amended panel "
            "lane)",
    "registered": "2026-11-27 (sandbox clock, TRUE UTC ~11:20Z)",
    "base_sha": "fc4f348d8 (the r170s1 aya32b outcome)",
    "note": "DIR 1 verified (EPISTEMIC 153ac62efca36c2d + AUDITOR "
            "3775f869a1c19a96 full reads; ledger V133; vault "
            "re-restored after the recycle rollback, then 11/11 with "
            "the CTAI keys added; secret-grep 0 live). THE CTAI IDS "
            "RECOVERED: the r170s1 probe list (mistral/sensenova/hy4 "
            "names) was never on the cantrustai allowlist — the "
            "working ids (openai/gpt-6-luna, openai/gpt-6-astra, "
            "openai/gpt-6.1-sol) come from the site's own frontend "
            "bundle (assets/index-DRx2tlw8.js, baseURL "
            "api.cantrustai.xyz + /v1); probe-verified 200 with real "
            "generation; the mid-window 502s were transient congestion "
            "(recovered ~90s — the retry ladders now carry the "
            "502/408 classes). The xkiro pool was LIVE at ~10:40Z "
            "(unconsumed all morning); the r170s1 window's 24-leg "
            "aya32b qualification consumed its lane (SPENT+FAILED acc "
            "0.667). This window's cron-tool view: 550745 + 550250 "
            "each show run_count=1 with zero landed artifacts; the "
            "r170s1 window's tool view showed 0 scheduled jobs — two "
            "different tool surfaces, both typed (the r166s1 "
            "not-verifiable finding reproduced on their side).",
}

if not any(c.get("claim_id") == "c-0272" for c in claims):
    claims.append({
        "claim_id": "c-0272",
        "work_id": "r153-xkiro-qualify-panel-v18",
        "role": "EXECUTOR",
        "status": "OPEN",
        "kind": "measurement",
        "session_id": "builder-r169s1",
        "claimed_at": "2026-11-27T11:20:00Z",
        "lease_expiry": "2026-11-28T12:00:00Z",
        "takes_over": "c-0271",
        "base_sha": "fc4f348d8 (the aya32b bars-FAIL outcome)",
        "artifact_paths": [
            "scripts/r169_rcal_ctai.py",
            "scripts/r168_am51_substitution_panel.py",
            "scripts/r153_p4_panel_v18.py",
            "eval/r169_rcal_ctai/",
            "eval/r168_am51_seal/",
            "eval/r148_p4_panel_v18/",
        ],
        "note": "THE CTAI THIRD-JUDGE LANE (the owner's R169 delivery, "
                "'use it for judges'): the AM51 continuation — with "
                "aya32b SPENT+FAILED (r170s1, acc 0.667) and the xkiro "
                "free pool exhausted of judge candidates, the "
                "substitute is openai/gpt-6-luna on cantrustai (the "
                "owner's named model; ids recovered from the frontend "
                "bundle, probe-verified). ONE firing plan: the "
                "wrapper (r168_am51_substitution_panel.py, the "
                "gpt6luna path) qualifies gpt6luna on the r148 corpus "
                "via the ctai instrument (24 legs, byte-resume) -> "
                "THE ENGINE'S OWN bars (acc>=0.8, answered>=0.9, "
                "bias<=1) + the serving alpha>=0.6 from snlite+"
                "gpt6luna+hy4f leg bytes -> PASS: seal (the runner's "
                "QUALIFICATION.json mst14b->gpt6luna, forward-only) "
                "-> the UNMODIFIED panel (snlite 7 remaining + "
                "gpt6luna 30; hy4f 30 skip-VALID) -> tally + "
                "recompute diff=0. On bar FAIL: typed exit, no seal, "
                "no panel; the unspent fallbacks are gpt6astra + "
                "gpt6sol (same transport, the owner's delivery) then "
                "the msm2603 owner-funding path. The v18 candidates "
                "stay FROZEN; aya32b is never re-rolled (Art. 7).",
    })

CNT.write_text("c-0273\n")
REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
print("session builder-r169s1 registered; c-0272 filed from the "
      "counter (advanced to c-0273)")
