#!/usr/bin/env python3
"""r176i_claim.py — Art. 29(a)/(b) registration + claim c-0283 for the
AM53 DIR-2 invention-shaped lane (work_id
r176-invention-shaped-dev24; builder-r176s1).

The lane: author the 24-item INVENTION-SHAPED DEV corpus (novel-
discovery problems where standard practice is INSUFFICIENT — R176-F2),
run the diverse-selection harness compute-matched on it, and measure
GENUINE novel-candidate wins (the champion's origin is a novel
strategy — departure/contradiction/cross-domain — AND the blind judge
says WIN; dominance ties and plain best-of-N wins are EXCLUDED from
the genuine count per AM53).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WC = REPO / "eval" / "work_claims.json"
COUNTER = REPO / "eval" / "claim_next_id.txt"

SESSION = "builder-r176s1"
CLAIM_ID = "c-0283"
WORK_ID = "r176-invention-shaped-dev24"
BASE_SHA = "c1dbd0cf2"
LEASE = "2026-11-28T20:00:00Z"


def main() -> int:
    d = json.loads(WC.read_text(encoding="utf-8"))
    if SESSION not in d["sessions"]:
        d["sessions"][SESSION] = {
            "role": ("EXECUTOR (the AM53 DIR-2 invention-shaped lane: "
                     "the 24-item novel-discovery DEV corpus + genuine "
                     "novel-candidate wins — dominance ties and plain "
                     "best-of-N wins excluded per AM53)"),
            "registered": "2026-11-27 (sandbox clock; TRUE UTC ~17:4xZ)",
            "base_sha": BASE_SHA + " (the directed read tip; "
                        "DIR 1 verified this session)",
            "note": ("DIR 1 complete this session: constitutions "
                     "full-read at c1dbd0cf2 + audit 8413e1ad0 "
                     "(digests 153ac62efca36c2d / 3775f869a1c19a96 "
                     "match, byte-identical to the prior full-reads); "
                     "ledger V137 read from bytes (R176: DIR-2 "
                     "non-loss 0.75 CI[0.428,0.945]; DIR-3 VACUOUS — "
                     "champions baseline7/plain4/contradiction1, "
                     "departure 0; AM53 genuine-invention gate; score "
                     "3); vault 11/11 restored (all digests match; "
                     "session HF live 200); secret-scan green; "
                     "queue-tip check-run green.")
        }
    else:
        print(f"session {SESSION} already registered")

    if any(c.get("claim_id") == CLAIM_ID for c in d["claims"]):
        print(f"claim {CLAIM_ID} already present — typed no-op")
        return 0

    d["claims"].append({
        "claim_id": CLAIM_ID,
        "work_id": WORK_ID,
        "role": "EXECUTOR",
        "kind": "measurement",
        "status": "OPEN",
        "session_id": SESSION,
        "claimed_at": "2026-11-27T17:45:00Z",
        "lease_expiry": LEASE,
        "base_sha": BASE_SHA,
        "artifact_paths": [
            "eval/r176_invention_corpus/items.jsonl",
            "eval/r176_invention_prereg.json",
            "eval/r176_invention_run/",
            "scripts/r176_invention_run.py",
            "scripts/r176_invention_tally.py"
        ],
        "note": ("the AM53 DIR-2 lane (R176-F1 direction): a 24-item "
                 "invention-shaped DEV corpus (novel-discovery "
                 "problems where standard practice is insufficient — "
                 "the f31e mitigation corpus is the wrong test per "
                 "R176-F2); the diverse-selection harness "
                 "compute-matched (same generator both arms via the "
                 "m77 transport; blind two-pass judge gpt-6-luna via "
                 "ctai with the NOVELTY axis explicit); the gate = "
                 "GENUINE novel-candidate wins (champion origin "
                 "departure/contradiction/relaxation AND blind WIN) — "
                 "dominance ties (champion==baseline) and plain "
                 "best-of-N wins EXCLUDED from the genuine count; "
                 "n=24, Wilson CI; one run per item, byte-resume; the "
                 "kill criterion (DIR 3) pre-declared")
    })

    WC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    COUNTER.write_text("c-0284", encoding="utf-8")
    print(f"registered {SESSION} + claim {CLAIM_ID} for {WORK_ID}; "
          f"counter -> c-0284")
    return 0


if __name__ == "__main__":
    sys.exit(main())
