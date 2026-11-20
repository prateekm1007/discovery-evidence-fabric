#!/usr/bin/env python3
"""r109s2_register_claim.py — builder-r109s2 Art. 29(a)/(b) registration:
the session identity + ONE VERIFIER claim (c-0138, the unclaimed
verification duty for c-0130's committed D7/D8 stage measurements),
one commit, push = the lock. The R109 verdict's execution lanes are
ALL held by the live peer builder-r109s1 (c-0133..c-0137, lease
2026-11-22T23:59Z) — this session stands down to VERIFIER on those
lanes per Art. 29(b) and executes this different unclaimed item.
Registry formatting preserved (json.dumps indent=1, ensure_ascii=False,
trailing newline). Idempotence guard: refuses to re-append existing
claim_ids (fail-closed, Art. 3).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "eval" / "work_claims.json"
SESSION = "builder-r109s2"
BASE = "f3d87cb0f"
LEASE = "2026-11-22T23:59:00Z"
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
assert d["schema"] == "work-claims/v1"
ids = {c.get("claim_id") for c in d["claims"]}
assert SESSION not in d["sessions"], \
    "session already registered — refuse to duplicate"
assert "c-0138" not in ids, "c-0138 already registered — refuse to duplicate"
# no competing VERIFIER claim on this work_id at the tip (Art. 29(b))
for c in d["claims"]:
    if c.get("work_id") == "p3-datasets-model-d7d8" and c.get("role") == "VERIFIER":
        raise SystemExit(f"refuse: {c['claim_id']} already verifies this work_id")

d["sessions"][SESSION] = {
    "registered_at": NOW,
    "role": "builder",
    "note": ("R109 session-2: continuation of the builder-r108s2 conversation "
             "lineage (the r96s1/r99s1/r103/r108s2 chain), NEW SANDBOX "
             "(reprovisioned; the worktree /home/z/queue-wt re-established at "
             "queue/dev12_r7, re-synced 5940e9749 -> f3d87cb0f ff-only). "
             "D1 preflight COMPLETE before any work byte: "
             "EPISTEMIC_CONSTITUTION.md v3.3.0 FULL-read at 5940e9749 (the "
             "R109 verdict's audited tip: 29 articles + 4 amendment records "
             "v3.0.0/v3.1.0/v3.2.0/v3.3.0 + the Art. 28 addendum) and "
             "AUDITOR_CONSTITUTION.md v1.3.0 FULL-read at "
             "origin/audit/r11-auditor-verdict-20261114 (14 articles + 3 "
             "amendments). STAND-DOWN TYPED (Art. 29(b)): the R109 verdict's "
             "execution lanes are ALL held by the LIVE peer builder-r109s1 "
             "(claims c-0133..c-0137 registered 2026-11-20T07:27:32Z, lease "
             "2026-11-22T23:59Z — active at this session's preflight; the "
             "push is the lock) — this session takes the VERIFIER role on "
             "those lanes as they land and executes the DIFFERENT UNCLAIMED "
             "item: the c-0130 D7/D8 stage measurements' verifier duty "
             "(committed at 6c02c0919, merged b024b24ad; no verifier record "
             "exists — c-0128's verifier c-0131 DONE, c-0129's verifier "
             "c-0132 is builder-r108s1's OPEN lease). Vault state "
             "(digest-only, Art. 17): GITHUB_PAT f1ebca5f9b62 (push auth "
             "verified), HF_TOKEN b5aaf542b2fd (the R108 public-read value; "
             "NO LLM work in this lane — verifier recompute, zero quota, "
             "zero sealed bytes). Default generator registration agnes-3.0-"
             "flash unchanged (peer-verified this round; not re-asked)."),
}

CLAIM = {
    "claim_id": "c-0138",
    "claimed_at": NOW,
    "registered_at": NOW + " (push = the lock, Art. 29(b))",
    "work_id": "p3-datasets-model-d7d8",
    "session_id": SESSION,
    "role": "VERIFIER",
    "status": "OPEN",
    "kind": "task",
    "base_sha": BASE,
    "lease_expiry": LEASE,
    "title": ("VERIFIER duty for c-0130 (builder-r105s2, Art. 29(c) — the "
              "recompute, never a re-run): the D7 XJTU-SY stage-5 + D8 "
              "Sundial stage-4 measurements committed at 6c02c0919 (merged "
              "b024b24ad, at tip) verified from COMMITTED BYTES. Recompute "
              "plan (zero re-serves, zero quota, zero LLM, zero sealed "
              "bytes): D8 — the Sundial record's internal consistency "
              "(coverage/alarm exact fractions where derivable), the "
              "matched-budget unit-set identity vs the stage-3 Bolt legs "
              "(same n>=212 floor + same seed-17 FD002 subsample code "
              "path), the cross-record Bolt numbers (0.887 / 0.8982 / "
              "4996.2ms byte-match vs the stage-3 record), the typed "
              "winner/tie rule application (FD001 gap 0.1714 -> Bolt wins; "
              "FD002 gap 0.0081 < 0.02 same gate state -> TIE); D7 — the "
              "flat-dir attribution verified against the committed RAR "
              "listing via an INDEPENDENT parser (recount the archive "
              "lives, all 173 (bearing, minute) pairs, per-bearing counts "
              "73/100, first/last indices, uniqueness), the measured "
              "cadence recompute (step medians/ranges), the RMS "
              "last/first ratio recompute from the committed endpoint "
              "arrays (6.5473 / 2.0115), the coverage exact-fraction "
              "checks (30/37, 33/50, 28/50), the CTX-floor adaptation "
              "math (26/40 vs n>=2*CTX+20), the n_walk derivations "
              "(73->37, 100->50). Typed findings on any mismatch; the "
              "raw XJTU/CMAPSS/CWRU bytes are sandbox-local (typed "
              "unverifiable-from-commit where so — the RMS SERIES itself "
              "is not committed; the endpoint arrays are)."),
    "artifact_paths": ["eval/r109s2_c0130_verifier_record.json"],
    "notes": ("one VERIFIER per verified execution; the executor claim "
              "c-0130 stays OPEN (the full-resolution XJTU re-extract "
              "typed when disk allows) — this verifies the COMMITTED "
              "stage measurements only, per the c-0131 precedent "
              "(partial-stage verification of an OPEN executor claim)."),
}

d["claims"].append(CLAIM)
REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print(f"registered {SESSION} + c-0138 "
      f"({len(d['claims'])} claims, {len(d['sessions'])} sessions)")
