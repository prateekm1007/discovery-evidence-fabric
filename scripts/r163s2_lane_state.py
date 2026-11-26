#!/usr/bin/env python3
"""r163s2_lane_state.py — the lane-state addendum (the V127 input).

MY OWN probes at 12:49-12:57Z DISCONFIRM the r163s1 lane's
"F45 executing server-side" hypothesis:
- tokenrouter G0: HTTP 200 (2.9s) — NOT the 401 they typed at
  ~12:45Z. Likely cause of their reading: a stale pre-recycle
  .env.keys in their sandbox (my TOKENROUTER key was re-custodied
  post-recycle from the directions and the digest matches).
- cent-ai: the KEY IS ACCEPTED — HTTP 200 on /v1/models (50
  models). Their "401 invalid_api_key by 12:35Z" does not
  reproduce; the hy4-flash:free MODEL is 503 upstream-unavailable
  (since ~09:32Z) — an upstream serving outage with our auth
  intact, not a key death.
- xkiro: DNS-unresolvable (reproducible 12:31Z + 12:49Z), consistent
  with their 10:43Z 401 auth-dead after the auth-valid 08:15-09:30Z
  window — the provider side is the problem (domain and/or auth),
  not our key hygiene.

CONSEQUENCES (the corrected owner-action list):
1. NO new tokenrouter or cent-ai keys are needed — both keys work.
2. The v2 tail (9 items) waits ONLY on the hy4 upstream serving.
   The byte-resume fires the moment it serves (the G0 is alive).
3. The panel waits on xkiro's provider side (domain + auth) — the
   Nov 27 00:00 reset probe disambiguates; no vault-side action
   can fix a DNS-dead domain.
4. The F45 rotation urgency DOWNGRADES for cent-ai/tokenrouter
   (the keys are live; rotate on the normal schedule, not
   emergency). xkiro's key is moot until the domain returns.
5. The r163s1 terminal-record typing stands for the COUNTING
   verdict: a fresh auditor-authorized run on the sealed corpus
   (sha c9670d8dd4b55c0c) with live J2+G0 is the path to a
   counting DIR-4 verdict; the held tail 9 (if completed with
   live seats) yields diagnostics only.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

rec = {
    "record": "R163S2_LANE_STATE/1.0.0",
    "claim": "c-0267 (the P5 v2 run lane — state addendum, no burn)",
    "work_id": "r163s2-lane-state",
    "session": "builder-r163s2",
    "at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime()),
    "measured_states": {
        "tokenrouter_G0": "HTTP 200 ALIVE (12:57Z, 2.9s) — the "
                          "r163s1 401 claim does NOT reproduce",
        "cent-ai_key": "HTTP 200 on /v1/models (12:49Z) — the key "
                       "is ACCEPTED; the r163s1 401-invalid claim "
                       "does NOT reproduce",
        "cent-ai_hy4_model": "503 upstream_unavailable since "
                             "~09:32Z (all lanes agree) — the "
                             "model's serving backend is down, "
                             "auth intact",
        "xkiro": "DNS-unresolvable (reproducible 12:31Z + 12:49Z); "
                 "consistent with the r163s1 10:43Z 401 after the "
                 "auth-valid 08:15-09:30Z window — provider-side",
    },
    "sweep_hypothesis": "DISCONFIRMED for cent-ai and tokenrouter; "
                        "the likely cause of the r163s1 401s is a "
                        "stale pre-recycle .env.keys in their "
                        "sandbox (the post-recycle vault digests "
                        "match the directions' current keys and "
                        "they WORK)",
    "consequences": [
        "no new tokenrouter/cent-ai keys needed — both live",
        "the v2 tail (9 items) waits only on the hy4 upstream; the "
        "byte-resume fires when it serves",
        "the panel waits on xkiro's provider side; the Nov 27 "
        "00:00 probe disambiguates",
        "the F45 urgency downgrades to the normal schedule for "
        "cent-ai/tokenrouter",
        "the counting-verdict path stays the auditor's "
        "re-authorization on the sealed corpus",
    ],
}
out = REPO / "eval/r163s2_lane_state.json"
out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
print("wrote", out)
