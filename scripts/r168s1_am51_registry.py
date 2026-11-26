#!/usr/bin/env python3
"""r168s1_am51_registry.py — the AM51 lane registry acts (Art. 29(a)
FIRST, before any push — the lesson learned twice at ebd966f6a and
74ff2f6fc).

Registers session builder-r168s1 + files claim c-0270 (the AM51
serving-set substitution lane: qualify aya32b on the r148 corpus,
seal the amended set, run the amended panel) + transitions c-0268 to
TAKEN_OVER (its direct-panel firing plan is superseded by AM51 —
mst14b is delisted; the "no qualifications" clause is obsolete under
the amendment, which REQUIRES the qualification first).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REG = REPO / "eval" / "work_claims.json"

reg = json.loads(REG.read_text())
sessions = reg.setdefault("sessions", {})
claims = reg["claims"]

# 1. session registration (Art. 29(a): identity on first push)
sessions["builder-r168s1"] = {
    "role": "EXECUTOR (the AM51 serving-set substitution lane: qualify "
            "aya32b on the r148 corpus, seal the amended set, run the "
            "amended panel; the r165s1 conversation-lane continuation "
            "answering V132/AM51)",
    "registered": "2026-11-26 (sandbox clock, TRUE UTC ~18:10Z)",
    "base_sha": "74ff2f6fc (the R167 window's close)",
    "note": "DIR 1 verified at the pinned tips (EPISTEMIC "
            "153ac62efca36c2d @ queue tip 74ff2f6fc full read; AUDITOR "
            "3775f869a1c19a96 @ audit tip 945662720 full read; ledger "
            "V132 + AM51 actual-read; vault 9/9 restored from scratch; "
            "secret-grep 0 live; tip surface success). AM51 FACTS "
            "TYPED: tiny-aya (tayae) CANNOT be the substitute — its "
            "qualification is SPENT (24 legs 2026-11-25, acc 0.75 < 0.8, "
            "AM47 bias 3 > 1, swap 0.5; re-rolling a failed candidate "
            "violates Art. 7 one-shot and AM51's own integrity clause "
            "'not tuning for a desired verdict'); msm2603 needs owner "
            "funding (403 paid). The FIRST UNSPENT in-roster candidate "
            "is aya32b (cohere/aya-expanse-32b — legs=0 in "
            "eval/r153_rcal_xkiro, named 'the strongest free lanes left' "
            "by the R154 second wave; catalog-verified present Nov 26 "
            "18:05Z). The AM51 path: qualify aya32b post-reset -> "
            "bars (acc>=0.8, answered>=0.9, bias<=1) + serving "
            "alpha>=0.6 (snlite+aya32b+hy4f) -> seal the amended set "
            "(mst14b->aya32b, forward-only) -> the amended panel on the "
            "SAME frozen v18 candidates.",
}

# 2. claim c-0270 (the AM51 substitution lane)
if not any(c.get("claim_id") == "c-0270" for c in claims):
    claims.append({
        "claim_id": "c-0270",
        "work_id": "r153-xkiro-qualify-panel-v18",
        "role": "EXECUTOR",
        "status": "OPEN",
        "kind": "measurement",
        "session_id": "builder-r168s1",
        "claimed_at": "2026-11-26T18:10:00Z",
        "lease_expiry": "2026-11-27T12:00:00Z",
        "takes_over": "c-0268",
        "base_sha": "74ff2f6fc (the queue tip at filing)",
        "artifact_paths": [
            "scripts/r168_am51_substitution_panel.py",
            "scripts/r153_rcal_xkiro.py",
            "scripts/r153_p4_panel_v18.py",
            "eval/r168_am51_seal/",
            "eval/r153_rcal_xkiro/",
            "eval/r148_p4_panel_v18/",
        ],
        "note": "ONE firing plan for the panel lane under AM51: the "
                "00:05Z Nov 27 platform cron fires "
                "scripts/r168_am51_substitution_panel.py, which (1) "
                "waits for the free pool (post-00:00 reset), (2) "
                "qualifies aya32b on the r148 balanced corpus via the "
                "UNMODIFIED instrument (R153_JUDGE=aya32b, 24 legs, "
                "byte-resume), (3) checks the bars (acc>=0.8, "
                "answered>=0.9 of EXPECTED 24, AM47 bias<=1) AND the "
                "serving alpha>=0.6 recomputed from snlite+aya32b+hy4f "
                "leg bytes, (4) on PASS seals the amended set "
                "(QUALIFICATION.json qualified_tags mst14b->aya32b "
                "forward-only; the aya32b roster entry is pre-committed "
                "inert) and runs the UNMODIFIED panel runner on the "
                "SAME frozen v18 candidates (snlite 7 remaining + "
                "aya32b 30; hy4f 30 skipped VALID), (5) tallies + "
                "recomputes (diff=0). On any bar FAIL: typed exit, NO "
                "panel firing (the xkiro free pool has no unspent "
                "candidates left — bpickl 0.375 answered, mst8b bias 2, "
                "mst3b 0.625 answered, cmdr7b/tayae acc 0.75, aya32b "
                "then spent) and the msm2603 owner-funding fallback is "
                "the only path. tiny-aya is NOT eligible (spent + "
                "failed; no re-roll per Art. 7). The v18 candidate set "
                "stays FROZEN (AM51 integrity).",
    })

# 3. c-0268 -> TAKEN_OVER (superseded by the AM51 firing plan)
for c in claims:
    if c.get("claim_id") == "c-0268" and c.get("status") == "OPEN":
        c["status"] = "TAKEN_OVER"
        c["note"] = (c.get("note") or "") + (
            " STATUS TRANSITION (forward-only, AM51): the direct-panel "
            "firing plan ('no qualifications; 5 snlite + 30 mst14b') is "
            "superseded — mst14b is DELISTED provider-side (xkiro "
            "catalog has no mistral family, byte-verified Nov 26) and "
            "AM51 (V132) authorizes the sealed substitution FIRST. "
            "Taken over by c-0270 (the AM51 sequence: qualify aya32b "
            "-> seal -> amended panel). The panel byte-resume legs "
            "(snlite 23 VALID + 2 RATE_LIMITED; hy4f 30 VALID) carry "
            "forward unchanged into the amended run.").strip()

REG.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
print("session builder-r168s1 registered; c-0270 filed; c-0268 -> TAKEN_OVER")
