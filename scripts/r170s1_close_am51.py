#!/usr/bin/env python3
"""r170s1_close_am51.py — the typed close of the AM51 execution lane
(c-271): aya32b FAILED the AM51 bars (one-shot spend recorded); no seal,
no panel; the fallback state typed for owner/auditor."""
from __future__ import annotations
import json, time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WC = REPO / "eval" / "work_claims.json"
BARS = json.loads((REPO / "eval" / "r168_am51_seal" / "BARS.json").read_text())
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

outcome = {
    "record": "R170S1_AM51_OUTCOME/1.0.0",
    "session": "builder-r170s1",
    "claim": "c-0271",
    "at": now,
    "wrapper": "scripts/r168_am51_substitution_panel.py (the UNMODIFIED AM51 one-firing-plan wrapper, claim c-0270's bytes)",
    "run_log": "scratch (gitignored) /home/z/my-project/scratch/r170s1_am51_run.log — the fired window's console record",
    "executed_stages": [
        "pool-wait: PASS (xkiro free pool alive, probe 200 at 10:55:50Z)",
        "qualify aya32b: 24/24 legs VALID (R153_JUDGE=aya32b, the UNMODIFIED r148 instrument, corpus digest MATCH c598682b56c9c33f; leg bytes committed under eval/r153_rcal_xkiro/aya32b__*.json)",
        "bars: FAIL (typed exit)",
    ],
    "bars_result": {
        "acc_vs_labels": BARS.get("acc_vs_labels"),
        "answered_rate": BARS.get("answered_rate"),
        "am47_bias_imbalance": (BARS.get("am47_bias") or {}).get("imbalance"),
        "serving_alpha": (BARS.get("serving_alpha_recomputed") or {}).get("alpha"),
        "bar_acc_0.8": "FAIL (0.667 < 0.8)",
        "bar_answered_0.9": "PASS (1.0)",
        "bar_bias_1": "PASS (0)",
        "bar_alpha_0.6": "PASS (0.6117)",
        "pass": BARS.get("pass"),
    },
    "typed_consequences": [
        "NO seal: eval/r153_rcal_xkiro/QUALIFICATION.json untouched (qualified_tags stay [snlite, mst14b]); no SUBSTITUTION_SEALED.json",
        "NO panel firing (the AM51 typed exit — the free pool has NO unspent judge candidates left)",
        "aya32b is SPENT + FAILED (24 legs 2026-11-27; Art. 7 one-shot — never re-rolled); tiny-aya was already spent/failed; mst8b/mst3b/cmdr7b/bpickl/tayae previously spent/failed",
        "the v18 candidate set stays FROZEN; the snlite 7 remaining panel legs carry forward (c-0268's resume legs) for the eventual 3rd judge",
    ],
    "score8_paths_owner_auditor": [
        "PATH A (fastest): a funded transport serving mistralai/mistral-small-2603 (msm2603, the kept-aside 4th-judge candidate, recorded acc 0.917) — tokenrouter is 403 paid; any owner-funded endpoint works; then panel legs msm2603 30 + snlite 7",
        "PATH B: the owner supplies the cantrustai (api.cantrustai.xyz/v1) allowlist model ids — auth VALID, models endpoint 404, ALL probed judge ids rejected ('queries[0].model not in allowlist'); if the allowlist carries msm2603, PATH A rides it; any NEW model needs its own 24-leg r148 qualification first",
        "PATH C: the provider re-lists mistralai/ministral-14b on xkiro (absent from the 82-model catalog today)",
    ],
}
(REPO / "eval" / "r170s1_am51_outcome.json").write_text(
    json.dumps(outcome, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")

d = json.loads(WC.read_text(encoding="utf-8"))
for c in d["claims"]:
    if c.get("claim_id") == "c-0271":
        c["status"] = "DONE"
        c["done_at"] = now
        c["done_note"] = (
            "the ONE AM51 firing plan EXECUTED live (11:01Z): pool-wait "
            "PASS, aya32b 24/24 legs VALID, BARS FAIL (acc 0.667 < 0.8; "
            "answered 1.0; bias 0; alpha 0.6117) — typed exit, NO seal, "
            "NO panel. aya32b SPENT+FAILED (one-shot); the xkiro free "
            "pool has zero unspent judge candidates; the score-8 3rd-"
            "judge gate is owner/auditor-blocked (msm2603 funded "
            "transport / cantrustai allowlist ids / provider re-list). "
            "Evidence: eval/r168_am51_seal/BARS.json + the 24 committed "
            "leg bytes + eval/r170s1_am51_outcome.json.")
WC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
              encoding="utf-8")
print("outcome record written; c-0271 -> DONE")
