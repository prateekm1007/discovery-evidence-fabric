#!/usr/bin/env python3
"""r175_cmb_claim.py — the Art. 29(a)/(b) registration + claim c-0276 for
the DIR-2 compute-matched baseline measurement (work_id
r175-compute-matched-baseline-dev12; prereg eval/r175_cmb_prereg.json,
authored BEFORE any run — AM44: criteria before data).

Registers session builder-r175s1 in sessions{} and appends the EXECUTOR
claim, advancing eval/claim_next_id.txt c-0276 -> c-0277. Idempotent:
re-running with the claim already present is a typed no-op (the
registry snapshot is re-read inside the same write; no clobber — the
f58c46a63 lesson).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
WC = REPO / "eval" / "work_claims.json"
COUNTER = REPO / "eval" / "claim_next_id.txt"

SESSION = "builder-r175s1"
CLAIM_ID = "c-0276"
WORK_ID = "r175-compute-matched-baseline-dev12"
BASE_SHA = "a8cc8e802"
LEASE = "2026-11-28T14:00:00Z"


def main() -> int:
    d = json.loads(WC.read_text(encoding="utf-8"))

    if SESSION not in d["sessions"]:
        d["sessions"][SESSION] = {
            "role": ("EXECUTOR (the AM52 DIR-2 lane: the auditor-judged "
                     "compute-matched baseline — 12 DEV pairs, the "
                     "pipeline arm vs best-of-N + one critique at the "
                     "same call budget on the same frozen evidence "
                     "packet; dominance by construction; blind two-pass "
                     "order-swapped judging)"),
            "registered": "2026-11-27 (sandbox clock; TRUE UTC ~16:0xZ)",
            "base_sha": BASE_SHA + " (the queue tip; the directed tip "
                        "fdc00d1cd is 1 checkpoint commit back — "
                        "disclosed in DIR 1)",
            "note": ("DIR 1 complete this session (constitutions "
                     "full-read at both pinned tips, digests "
                     "153ac62efca36c2d / 3775f869a1c19a96; ledger V136 "
                     "AM52 score 3; vault 11/11 with the r174-rotated "
                     "master 0af8db243dee probed live; the stale "
                     "session-local .env.keys HF_TOKEN line repaired to "
                     "the rotated bytes; secret-scan green; check-runs "
                     "green). The P5 v2 claim c-0275 (r159s2) stays "
                     "OPEN with a live lease — NOT taken over (Art. "
                     "29(d)); its in-flight checkpoint 8/30 resumes in "
                     "its own lane after expiry.")
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
        "claimed_at": "2026-11-27T16:05:00Z",
        "lease_expiry": LEASE,
        "base_sha": BASE_SHA,
        "artifact_paths": [
            "eval/r175_cmb_prereg.json",
            "eval/r175_cmb_run/",
            "scripts/r175_cmb_run.py",
            "scripts/r175_cmb_tally.py"
        ],
        "note": ("the DIR-2 (TOP) measurement under AM52: 12 DEV pairs "
                 "on one commit, cache off; baseline = best-of-K + one "
                 "critique on the same frozen packet (K = the "
                 "pipeline's own recorded call count); pipeline arm = "
                 "EngineRun + the dominance-injected final compose "
                 "(baseline_best in the composer's candidate pool); "
                 "blind randomized A/B, two passes order-swapped; "
                 "machine panel (snlite+gpt6luna+hy4f-if-live, "
                 "non-agnes) as INPUT, the reviewer's blind judgment "
                 "as the gate; one run per item per arm, byte-resume, "
                 "typed failures never re-rolled; kill criterion "
                 "pre-declared (DIR 3)")
    })

    WC.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
                  encoding="utf-8")
    COUNTER.write_text("c-0277", encoding="utf-8")
    print(f"registered {SESSION} + claim {CLAIM_ID} for {WORK_ID}; "
          f"counter -> c-0277")
    return 0


if __name__ == "__main__":
    sys.exit(main())
