#!/usr/bin/env python3
"""r144s1 claim registration v2 (Art. 29(b) re-derive after the twin's
advance): session builder-r144s1 + claim c-0245, work_id
r144-v17-one-shot, base 7438f8dd2. The first attempt (c-0243, commit
ed2cba296) collided with the twin session's c-0243 and was STOOD DOWN
per Art. 29(e) — the duplicate engine bytes preserved in
/home/z/my-project/r144_duplicate_lane_scratch/, never landed."""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "eval" / "work_claims.json"
CNT = REPO / "eval" / "claim_next_id.txt"
BASE = "7438f8dd2"
SESSION = "builder-r144s1"

d = json.loads(REG.read_text())
assert d.get("schema") == "work-claims/v1"

sess = d.setdefault("sessions", {})
if SESSION not in sess:
    sess[SESSION] = {
        "role": "builder",
        "note": (
            "R144 session-1 (second window): fetched state, FULL-read "
            "both constitutions (EPISTEMIC @ 2c0191653a62, "
            "153ac62efca36c2d; AUDITOR @ 42e4d2e4698d, 3775f869a1c19a96) "
            "and the ACTUAL AUDIT_LEDGER.json (last V110; AM47/48/49; "
            "v16 BURNED_NOT_GRANTED) before acting. DIR-1 verified: "
            "vault digests match the committed custody records, "
            "secret-grep = 0 live, tip check-run success from the API. "
            "Art. 29(e) stand-down typed: the first-window engine build "
            "(claim c-0243 attempt, orphaned commit ed2cba296) "
            "duplicated the twin session's LANDED c-0243 levers "
            "(5bbe7e0b0) — stood down, bytes preserved in scratch, "
            "never landed. THIS window: the DISJOINT v17 lane (the "
            "twin's own typed follow-up) — the fresh candidate set + "
            "the one-shot on the LANDED engine + the additive lexicon "
            "extension the fresh vocabulary measured necessary."),
        "registered_at": "2026-11-24 (sandbox clock)",
    }
elif not sess[SESSION].get("role"):
    sess[SESSION]["role"] = "builder"

claims = d.setdefault("claims", [])
# drop any prior append of THIS script (idempotent re-run)
pre = len(claims)
claims[:] = [c for c in claims
             if not (c.get("work_id") == "r144-v17-one-shot"
                     and c.get("session_id") == SESSION)]
if len(claims) != pre:
    print(f"idempotency: removed {pre - len(claims)} prior append(s)")
ids = [c.get("claim_id") for c in claims]
nums = [int(x[2:]) for x in ids
        if isinstance(x, str) and x.startswith("c-") and x[2:].isdigit()]
# the COUNTER is the allocation authority (r128 dir 1): the next id is
# the counter's value, never max(registry)+1 (c-0244 was allocated by
# the twin and never landed — a typed skipped id, disclosed in the
# claim title)
counter_val = CNT.read_text().strip()
assert counter_val.startswith("c-"), "counter unreadable"
nxt = counter_val
existing = [c for c in claims
            if c.get("work_id") == "r144-v17-one-shot"
            and c.get("role") == "EXECUTOR"]
if existing:
    nxt = existing[0]["claim_id"]
    print(f"claim already registered: {nxt} (idempotent re-run)")
    REG.write_text(json.dumps(d, indent=2, ensure_ascii=True) + "\n")
    raise SystemExit(0)

lease = (datetime.now(timezone.utc) + timedelta(days=7)).strftime(
    "%Y-%m-%dT%H:%M:00Z")
claim = {
    "work_id": "r144-v17-one-shot",
    "claim_id": nxt,
    "role": "EXECUTOR",
    "session_id": SESSION,
    "kind": "task",
    "status": "OPEN",
    "base_sha": BASE,
    "lease_expiry": lease,
    "claimed_at": "2026-11-24 (sandbox clock)",
    "registered_at": "2026-11-24 (sandbox clock)",
    "artifact_paths": [
        "discovery_fabric/engine/failure_mechanism_map.py",
        "scripts/r144s1_lexicon_extension_record.json",
        "eval/r52_labelled_regression.json",
        "eval/holdout_v17/problems.json",
        "eval/holdout_v17_generation/",
        "scripts/r144_v17_one_shot.py",
    ],
    "one_shot": True,
    "title": (
        "R144S1 EXECUTOR (claim " + nxt + ", base " + BASE + "; the "
        "Art. 29(e) re-derive after the twin's c-0243 landed; the "
        "c-0244 id typed SKIPPED — allocated by the twin, never "
        "landed; this id comes from the counter per r128 dir 1): the "
        "v17 ONE-SHOT lane — the twin's own typed follow-up (their "
        "close a0e3c2ba7 requested 'v17 the fresh sealed set — DIR "
        "2/3's acceptance bar'). THIS lane: (1) the ADDITIVE lexicon "
        "extension of the twin's failure_mechanism_map (5 new failure "
        "families + the verb-form/rolling-contact detector additions) "
        "— measured necessity: the c-0243 lexicon routed only 9/30 "
        "fresh problems (the DIR-3 lever inert on 70% of the fresh "
        "acceptance material; 'eros' is not a substring of 'erodes'); "
        "after: 29/30; the F77 refresh per the twin's 7438f8dd2 "
        "precedent (r52 verdict UNCHANGED PASS 0/0/0); the off-target "
        "scan re-validated (2/2 precision, 0 false fires); (2) the "
        "r85-path wiring completion of the twin's lever (d) (the r60 "
        "conditioning was inert on the sealed-set path, the F61 "
        "class); (3) the 30-problem builder-authored CANDIDATE set "
        "(fresh cluster-disjoint domains; the seal + rubrics + "
        "scoring stay the AUDITOR's act) + the one-shot generation "
        "on the LANDED engine, raw bytes committed with the run. "
        "Acceptance typed: the mean>=3.3/CI>3.0/>=30%-strong gate is "
        "PENDING-AUDITOR-SCORE (the builder never scores itself, "
        "Art. 10/14); this lane's verifiable acceptance = the "
        "committed bytes + the per-row family/winner/scan surface."),
}
claims.append(claim)
d["claims"] = claims
# advance the counter in the SAME commit (the r128 guard)
CNT.write_text(f"c-{int(nxt[2:]) + 1:04d}\n")
REG.write_text(json.dumps(d, indent=2, ensure_ascii=True) + "\n")
print(f"registered session {SESSION} + claim {nxt} "
      f"(work r144-v17-one-shot, base {BASE}, lease {lease}); "
      f"counter -> c-{int(nxt[2:]) + 1:04d}")
