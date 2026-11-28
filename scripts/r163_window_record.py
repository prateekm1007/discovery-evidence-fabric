#!/usr/bin/env python3
"""r163_window_record.py — the r163 builder window's typed record.

The window's facts (all measured, none assumed):
1. xkiro: HARD-BLOCKED — api.xkiro.ai no longer RESOLVES (DNS
   'Name or service not known' at 12:31Z), beyond the 10:43Z 401
   auth-dead typed by r160s1. The panel finish (5 snlite + 30
   mst14b legs) waits on owner delivery (a new key or the funded
   path) or the Nov 27 00:00 reset probe (which disambiguates
   provider-revoked vs quota-disabled vs domain-gone).
2. cent-ai J2 (hy4-flash:free): 503 upstream_unavailable 09:32Z ->
   12:55Z+ (3.5h+); the model is still LISTED in the 50-model
   catalog -> a genuine outage, not a retirement. The P5 v2 run is
   HELD at 21/30: the 21 recorded items are checkpoint-FINAL
   (fail-closed PARTIAL under the outage) — with them, the 40% bar
   (min 12 RECOVERED of 30) is mathematically UNREACHABLE no matter
   what J2 does — the DIR-4 verdict will be NOT_MET. The remaining
   9 items are HELD so they can get REAL two-judge adjudication
   (measurement quality for the instrument calibration and the v3
   design), not to chase the bar. Byte-resume fires the moment J2
   serves.
3. DIR 6: the physics regression 26/26 GREEN (pint restored to the
   env after the recycle).
4. F45 rotation: HF rotated TODAY (the new token in the vault,
   digest 0af8db243dee); remaining history-exposed: GH_PAT /
   cent-ai / xkiro / llmtr / tokenrouter. TOKENROUTER was restored
   to the vault after the recycle (digest c148574f6215).
5. Monitor (DIR 8): MOOSE-Chem — only the known entries (2410.07076
   alphaxiv Oct-2025 + ICLR 2025); no new lever event.
6. Funding intelligence (the owner's path A): the cent-ai catalog
   is 50 models (image + chat); hy4-flash:free is the only free
   hy4-class chat model and it is the DOWN one — a cent-ai top-up
   would NOT fix the J2 seat today; the xkiro plan funding is
   moot while the domain does not resolve. The fast panel path
   needs either xkiro's domain+auth back, or an owner-sealed
   transport change (which is a re-qualification, never mid-gate).
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

rec = {
    "record": "R163_WINDOW_RECORD/1.0.0",
    "claim": "c-0267 (the P5 v2 run lane — hold state, no new burn)",
    "work_id": "r163-hold-typing",
    "session": "builder-r163",
    "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    "facts": [
        "xkiro HARD-BLOCKED: DNS failure on api.xkiro.ai (12:31Z), "
        "beyond the 10:43Z 401 auth-dead; the panel finish waits on "
        "owner delivery or the Nov 27 00:00 reset probe",
        "cent-ai J2 503 outage 09:32Z->12:55Z+; hy4-flash:free still "
        "catalog-listed (50 models) -> outage not retirement",
        "P5 v2 HELD at 21/30 (21 checkpoint-FINAL fail-closed "
        "PARTIAL); the 40% bar is unreachable regardless of J2 -> "
        "the DIR-4 verdict will be NOT_MET; the 9 remaining items "
        "are held for real two-judge measurement quality",
        "DIR 6 physics regression 26/26 GREEN (pint env-restored)",
        "F45: HF rotated today (digest 0af8db243dee); remaining "
        "exposed: GH_PAT/cent-ai/xkiro/llmtr/tokenrouter; "
        "TOKENROUTER re-custodied after the recycle (c148574f6215)",
        "MOOSE-Chem monitor: no new events (the known 2410.07076 + "
        "ICLR 2025 entries only)",
    ],
    "decision_rules": {
        "j2_recovery": "byte-resume scripts/r159_p5_v2_run.py the "
                       "moment hy4-flash:free serves (each item "
                       "retries J2 twice mid-run)",
        "j2_still_down_next_window": "the next window chooses: "
                                     "complete the run fail-closed "
                                     "with the typed outage "
                                     "disclosure, or file the v3 "
                                     "prereg with the pre-registered "
                                     "seat (the r160s1 fire-time "
                                     "safety valve)",
        "panel": "no lawful action until the owner delivers or the "
                 "reset probe disambiguates; NO mid-gate transport "
                 "swaps (the serving models exist on NO alternative "
                 "lane: sensenova absent from tokenrouter, mistral-"
                 "14b absent from both alternatives)",
    },
}
out = REPO / "eval/r163_window_record.json"
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("wrote", out)
