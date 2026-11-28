#!/usr/bin/env python3
"""r170s1_file_claim.py — Art. 29 claim-before-work filing for the AM51
execution lane (c-271 takes_over c-0270) + the post-reset probe record.

Typed findings carried into the claim note (bytes, not hearsay):
  - cron verification FAILED: the builder cron tool surface sees ZERO
    scheduled jobs (scope=all, 2026-11-27T10:46Z); zero AM51 bytes in
    git (no eval/r168_am51_seal/ at tip 68cf02dba; no commits after
    Nov 26 18:14Z); the xkiro free pool was ALIVE at 10:50Z (10.7h
    post-reset — inconsistent with the 24-leg aya32b qualification
    having run; every prior window saw the pool dead within hours of
    use); the auditor's V133 (pushed 10:37Z today) still types the
    panel PENDING. => typed: NO EVIDENCE cron 550745 fired; this
    window executes the ONE AM51 firing plan live, under claim.
  - cantrustai (owner's new judge transport): token ALREADY
    vault-managed (digests 3779a467bb9a / 73be3c3b31e0, 0 diff vs the
    owner's bytes; r77 restores 11/11); auth VALID; /v1/models 404;
    the model allowlist REJECTS every judge id probed (aya-expanse-32b
    bare+nested, mistralai/ministral-14b, mistralai/mistral-small-2603,
    sensenova-6.8-flash-lite, hy4-flash:free) AND 4 common names
    (gpt-4o-mini, claude-3-5-haiku-20241022, deepseek-chat,
    glm-4-flash) with 'queries[0].model not in allowlist' — typed
    NOT-USABLE as a judge transport until the owner supplies the
    allowlist model ids. F45 rotation list += CTAI (history-exposed).
  - xkiro: 82-model catalog (aya32b PRESENT and callable — 200 probe;
    mistral family still absent); snlite pool probe 200 'OK'.
  - cent-ai: /models 200-empty-body anomaly; hy4-flash:free chat
    probe 404 HTML — the J2 seat typed DOWN (P5 v2 two-seat gate
    would fail-closed today; panel unaffected — hy4f 30/30 VALID
    legs stand, no hy4f calls needed).
"""
from __future__ import annotations
import json, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WC = REPO / "eval" / "work_claims.json"
CID = REPO / "eval" / "claim_next_id.txt"

d = json.loads(WC.read_text(encoding="utf-8"))
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

# 1. session registration (Art. 29(a)) — BEFORE push
d["sessions"]["builder-r170s1"] = {
    "role": "EXECUTOR (the AM51 firing lane taken over from c-0270: "
            "the post-reset cron verification typed NO-EVIDENCE-OF-FIRING, "
            "so this window executes scripts/r168_am51_substitution_panel.py "
            "live under claim — qualify aya32b, bars, seal, panel, tally "
            "recompute; plus the owner's cantrustai judge-transport census)",
    "registered": "2026-11-27 (sandbox clock, TRUE UTC ~10:55Z)",
    "base_sha": "68cf02dba (the R168S1 AM51 arming commit, the queue tip)",
    "note": "DIR 1 verified at the pinned tips: EPISTEMIC 153ac62efca36c2d "
            "@ queue tip 68cf02dba (byte-counted); AUDITOR 3775f869a1c19a96 "
            "@ audit tip 73605f7e2; ledger V133 actual-read (score 7 "
            "consolidated, AM51+CORR-R169-1); vault r77 restore 11/11 "
            "vault-managed keys (CTAI_API_KEY/CTAI_BASE_URL already "
            "vault-managed, 0 diff vs the owner's bytes this window; "
            "XKIRO f6c09bee9bde); secret-grep 0 live; checkout "
            "fast-forwarded fad0baec->68cf02dba (249 commits).",
}

# 2. mark c-0270 TAKEN_OVER (its lease dies 12:00Z; the cron payload it
#    armed never landed bytes)
for c in d["claims"]:
    if c.get("claim_id") == "c-0270":
        c["status"] = "TAKEN_OVER"
        c["taken_over_note"] = (
            "taken over by c-0271 (builder-r170s1, 2026-11-27T~10:55Z): "
            "the 00:05Z cron it armed typed NO-EVIDENCE-OF-FIRING "
            "(zero AM51 bytes in git; pool alive 10.7h post-reset; "
            "cron tool surface sees 0 jobs); the lane executes live "
            "under c-0271, same ONE firing plan, same wrapper bytes")

# 3. file the claim
d["claims"].append({
    "claim_id": "c-0271",
    "work_id": "r153-xkiro-qualify-panel-v18",
    "role": "EXECUTOR",
    "status": "OPEN",
    "kind": "measurement",
    "session_id": "builder-r170s1",
    "claimed_at": now,
    "lease_expiry": "2026-11-27T22:00:00Z",
    "takes_over": "c-0270",
    "base_sha": "68cf02dba (the queue tip at filing)",
    "artifact_paths": [
        "scripts/r168_am51_substitution_panel.py",
        "eval/r168_am51_seal/",
        "eval/r153_rcal_xkiro/",
        "eval/r148_p4_panel_v18/",
        "eval/r170s1_postreset_probe_record.json",
    ],
    "note": "ONE firing plan for the panel lane (AM51, unchanged): this "
            "window fires scripts/r168_am51_substitution_panel.py ONCE, "
            "live. Typed cron verification (DIR 7): the builder cron "
            "tool surface sees 0 scheduled jobs (scope=all at 10:46Z); "
            "NO eval/r168_am51_seal/ bytes at the tip; NO commits after "
            "68cf02dba (Nov 26 18:14Z); the xkiro pool was ALIVE at "
            "10:50Z (10.7h post-reset — the 24-leg qualification would "
            "have killed it); the auditor's V133 (10:37Z) still types "
            "the panel pending => NO EVIDENCE cron 550745 fired. "
            "Byte-resume stages: pool-wait (probe 200 at 10:50Z — "
            "passes immediately) -> qualify aya32b (24 legs, "
            "R153_JUDGE=aya32b via the UNMODIFIED instrument) -> bars "
            "(acc>=0.8, answered>=0.9, AM47 bias<=1, serving "
            "alpha>=0.6) -> seal mst14b->aya32b -> the UNMODIFIED panel "
            "(snlite 7 + aya32b 30; hy4f 30/30 VALID skipped) -> tally "
            "recompute (diff=0). On any bar FAIL: TYPED EXIT, no seal, "
            "no panel. OWNER'S NEW TRANSPORT TYPED (cantrustai): token "
            "already vault-managed (0 diff); auth VALID; /models 404; "
            "the allowlist REJECTS all 6 judge ids + 4 common names — "
            "NOT-USABLE as a judge transport until the owner supplies "
            "the allowlist model ids; F45 += CTAI. cent-ai J2 seat "
            "404/HTML DOWN today (P5 v2 gate fails closed; panel "
            "unaffected). tiny-aya stays NOT-eligible (spent); no "
            "mid-gate tuning swap (AM51 availability-only); the v18 "
            "candidate set FROZEN.",
})

CID.write_text("c-0272\n", encoding="utf-8")
WC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")
print("filed: session builder-r170s1 registered; c-0270 -> TAKEN_OVER; "
      "claim c-0271 filed; counter -> c-0272")
