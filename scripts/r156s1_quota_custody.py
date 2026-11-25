#!/usr/bin/env python3
"""r156s1_quota_custody.py — the honest-custody record for the window
that was told 'the quota reset has PASSED' and measured the opposite.

The board fact chain (every count from bytes/probes, none assumed):
- the sandbox/API clock: 2026-11-25 ~10:36 UTC
- the probe (this window, vault xkiro key, auth-valid): HTTP 429
  'today's free-model token quota' — the lanes are dead NOW
- the 00:00 UTC Nov-25 reset DID pass — and its tokens were consumed
  by ~185 qualification legs from the morning's concurrent lanes
  (r153s1 canonical 72 + the s1-aside lane 65 + the r153s2 lane 48,
  per the double-burn census in b484afa4f / 739d97f0d9a7)
- the next reset: 00:00 UTC 2026-11-26 (~13.4h from the probe)

The typed refusal (Art. 3, upholding the r153s2 disposition):
the panel does NOT fire into a dead quota — 49 legs would grind
429-backoff ladders for hours and type RATE_LIMITED (no tokens
gained, no votes cast, the window wasted).

The CORRECTION to the r153s2 typing (honest record-keeping):
'r153s2_panel_quota_block.json' says RATE_LIMITED legs would be
'FINAL under the no-re-roll rule (byte-resume skips any existing
legfile)' — the panel runner's resume code says otherwise:
scripts/r153_p4_panel_v18.py line 358 skips ONLY legs whose
outcome == 'VALID' (the R146 fix). RATE_LIMITED legs retry on the
next run. The refusal was still right (a dead-quota fire wastes
the window), but the 'permanently wounding the serving panel'
rationale was overstated. This record corrects it so the post-
reset executor knows the legs are recoverable, not final.

The DIR-6 verification (this window, no API burn): 93 tests pass
(73 physics battery + 20 v18 row regression), the 8-check contract
intact, the import graph unchanged (the one-shot import at
scripts/r149_v18_physics_one_shot.py:56), the r149 lever record
stands (6 genuine errors -> 0 across 30 rows, 4 FP classes typed).
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def main() -> int:
    now = datetime.now(timezone.utc)
    rec = {
        "record": "R156S1_QUOTA_CUSTODY/1.0.0",
        "claim": "c-0264",
        "work_id": "r153-xkiro-qualify-panel-v18",
        "session": "builder-r156s1",
        "at": now.strftime("%Y-%m-%d %H:%M UTC"),
        "the_measured_fact": {
            "probe": "HTTP 429 'You've reached today's free-model "
                     "token quota' on the VAULT xkiro key "
                     "(auth-valid: the dead directions' key 401s; "
                     "the vault key is the live one)",
            "sandbox_clock": now.strftime("%Y-%m-%d %H:%M UTC"),
            "what_actually_happened": "the 00:00 UTC Nov-25 reset "
                "passed and was CONSUMED by ~185 qualification legs "
                "from the morning's concurrent lanes (the triple "
                "burn); the next reset is 00:00 UTC 2026-11-26",
            "the_directions_premise": "'the quota reset has PASSED' "
                "was TRUE of the reset and FALSE of the pool — the "
                "board reads the probe, not the premise (Art. 1)",
        },
        "the_typed_refusal": {
            "what": "the panel was NOT fired this window",
            "why": "49 legs (snlite 19 + mst14b 30) into a dead "
                   "quota = hours of 429-backoff ladders, all typed "
                   "RATE_LIMITED, no votes cast, no tokens gained",
            "upholds": "the r153s2 typed refusal "
                       "(eval/r153s2_panel_quota_block.json)",
        },
        "the_correction": {
            "to": "eval/r153s2_panel_quota_block.json",
            "the_claim": "RATE_LIMITED panel legs are 'FINAL under "
                         "the no-re-roll rule (byte-resume skips any "
                         "existing legfile)'",
            "the_code": "scripts/r153_p4_panel_v18.py line 358: "
                        "only outcome == 'VALID' legs skip (the R146 "
                        "fix); RATE_LIMITED legs RETRY on re-run",
            "the_consequence": "the 'permanent wound' rationale was "
                               "overstated; the refusal stands on the "
                               "wasted-window rationale; the post-"
                               "reset executor knows the legs are "
                               "recoverable, not final",
        },
        "dir6_verification": {
            "physics_battery": "73 passed (checks + magnitudes + r54 "
                               "+ guards)",
            "v18_row_regression": "20 passed",
            "check_contract": "8 check functions "
                              "(dimensions, magnitudes, assumption "
                              "bounds, magnetic target, 3 sign "
                              "checks, permittivity label)",
            "import_graph": "scripts/r149_v18_physics_one_shot.py:56 "
                            "-> discovery_fabric.generation."
                            "physics_truth (unchanged)",
            "the_r149_lever_record": "stands: 6 genuine errors -> 0 "
                                     "across 30 v18 rows, 4 FP "
                                     "classes typed, engine-wired",
        },
        "the_resume": {
            "when": "the first window after 00:00 UTC 2026-11-26",
            "how": "probe the quota; run the UNFILTERED "
                   "scripts/r153_p4_panel_v18.py (byte-resume skips "
                   "hy4f 30 + snlite 8 VALID legs; snlite 19 + "
                   "mst14b 30 generate)",
            "then": "the 3-judge two-axis majority tally on the FULL "
                    "30-candidate set; scripts/"
                    "r153s1_tally_recompute.py diff=0; the >=50% "
                    "viable+non-obvious bar -> score-8 evidence",
            "budget_note": "49 legs ~245K tokens vs the ~200K daily "
                           "pool (the burn census estimate); if the "
                           "pool dies late the tally computes over "
                           "votes cast and the shortfall is "
                           "disclosed, not papered; ONE run, no "
                           "re-qualification (the serving set is "
                           "frozen)",
        },
        "raw_bytes": "eval/r156s1_quota_custody.json (this file)",
    }
    out = REPO / "eval" / "r156s1_quota_custody.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print("wrote", out)
    leg_dir = REPO / "eval" / "r148_p4_panel_v18"
    census = {}
    for j in ("snlite", "mst14b", "hy4f"):
        fs = sorted(leg_dir.glob(f"{j}__*.json"))
        v = sum(1 for f in fs
                if json.loads(f.read_text()).get("outcome") == "VALID")
        census[j] = {"legs": len(fs), "valid": v}
    print("census:", json.dumps(census))
    assert census["hy4f"]["valid"] == 30, "hy4f canonical broke"
    assert census["snlite"]["legs"] == 11, "snlite bank changed"
    assert census["mst14b"]["legs"] == 0, "mst14b should be 0"
    r = subprocess.run(["git", "rev-parse", "--short=9", "HEAD"],
                       capture_output=True, text=True, check=True)
    print("recorded on", r.stdout.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
