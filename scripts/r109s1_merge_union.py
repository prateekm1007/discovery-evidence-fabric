#!/usr/bin/env python3
"""r109s1_merge_union.py — resolve eval/work_claims.json as a PER-FIELD
UNION for the forward-only merge with the peer's registry commit (the
R95/r108s2 precedent: SHAs preserved, no rebase renumber, both sides'
fields kept)."""
import json
import subprocess
from pathlib import Path

REG = Path("eval/work_claims.json")
OURS = json.loads(subprocess.run(
    ["git", "show", "HEAD:eval/work_claims.json"],
    capture_output=True, text=True).stdout)
THEIRS = json.loads(subprocess.run(
    ["git", "show", "d17fca7f1:eval/work_claims.json"],
    capture_output=True, text=True).stdout)

# sessions: union (identical registrations are idempotent)
sessions = dict(THEIRS.get("sessions", {}))
sessions.update(OURS.get("sessions", {}))

# claims: union by claim_id; shared rows merge field-wise with OURS
# (the executor's stage_progress/status) winning ONLY on the fields it
# actually carries, THEIRS kept verbatim where we have no update
ours_by = {c["claim_id"]: c for c in OURS.get("claims", [])}
theirs_by = {c["claim_id"]: c for c in THEIRS.get("claims", [])}
claims = []
for cid in sorted(set(ours_by) | set(theirs_by),
                  key=lambda x: (theirs_by.get(x, ours_by.get(x, {}))
                                 .get("claimed_at") or "", x)):
    o, t = ours_by.get(cid), theirs_by.get(cid)
    if o and t:
        merged = dict(t)
        merged.update(o)  # our executor fields win on overlap
        # keep peer fields we do not carry (defensive: explicit union)
        for k, v in t.items():
            if k not in merged or merged[k] in (None, "", []):
                merged[k] = v
        claims.append(merged)
    else:
        claims.append(dict(o or t))

out = dict(OURS)  # our violations/findings counters are the fresher
out["sessions"] = sessions
out["claims"] = claims
REG.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print("union: %d sessions, %d claims "
      "(new from peer: %s)" % (
          len(sessions), len(claims),
          sorted(set(theirs_by) - set(ours_by))))
