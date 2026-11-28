#!/usr/bin/env python3
"""r145s1 claim-before-work: claim c-0247, work_id
r145-v17-sealed-one-shot, base 1020f079f. (A prior register script was
accidentally re-executed in this sandbox and appended a wrong c-0247
for the OLD work id — the working-tree append was restored from HEAD
before any commit; the registry's committed state was never harmed.
This script is the ONLY registration for this lane.)"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REG = REPO / "eval" / "work_claims.json"
CNT = REPO / "eval" / "claim_next_id.txt"
BASE = "1020f079f"
SESSION = "builder-r145s1"

d = json.loads(REG.read_text())
assert d.get("schema") == "work-claims/v1"
sess = d.setdefault("sessions", {})
if SESSION not in sess:
    sess[SESSION] = {
        "role": "builder",
        "note": (
            "R145 session-1 (the v17 sealed one-shot lane): fetched "
            "state, FULL-read both constitutions (EPISTEMIC @ "
            "7438f8dd2, 153ac62efca36c2d; AUDITOR @ babbaedd0cb5, "
            "3775f869a1c19a96) and the ACTUAL AUDIT_LEDGER.json (last "
            "V111: the strength kit dev-verified, v17 SEALED authored, "
            "R144-F1 quant 2/8, R144-F2 the cherry-picked P4 rung "
            "rejected) before acting. DIR-1 verified: vault digests "
            "match the committed custody records, secret-grep = 0 "
            "live, check-runs from the API. The typed discovery this "
            "window opens with: the owner's SEALED v17 problems are a "
            "DIFFERENT set (30 problems across the 10 failure classes, "
            "audit-branch bytes) — the three existing generation arms "
            "ran on the pre-seal candidate set and stand as DEV "
            "evidence; the sealed one-shot has NOT been run. Lane: "
            "claim-before-work, the full strength kit in the "
            "instrument, one generation, burn after."),
        "registered_at": "2026-11-24 (sandbox clock)",
    }
elif not sess[SESSION].get("role"):
    sess[SESSION]["role"] = "builder"

claims = d.setdefault("claims", [])
counter_val = CNT.read_text().strip()
assert counter_val.startswith("c-"), "counter unreadable"
nxt = counter_val
existing = [c for c in claims
            if c.get("work_id") == "r145-v17-sealed-one-shot"
            and c.get("role") == "EXECUTOR"]
if existing:
    print(f"claim already registered: {existing[0]['claim_id']} "
          f"(idempotent re-run)")
    REG.write_text(json.dumps(d, indent=2, ensure_ascii=True) + "\n")
    raise SystemExit(0)
ids = [c.get("claim_id") for c in claims]
assert nxt not in ids, f"collision on {nxt}"

lease = (datetime.now(timezone.utc) + timedelta(days=7)).strftime(
    "%Y-%m-%dT%H:%M:00Z")
claim = {
    "work_id": "r145-v17-sealed-one-shot",
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
        "discovery_fabric/generation/mechanism_map.py",
        "tests/test_generation_mechanism_map.py",
        "scripts/r145_v17_sealed_one_shot.py",
        "eval/holdout_v17_sealed_generation/",
        "eval/holdout_v17_sealed_screen.json",
    ],
    "one_shot": True,
    "title": (
        "R145S1 EXECUTOR (claim " + nxt + ", base " + BASE + "): "
        "DIR-2 (TOP) + DIR-3 — the v17 SEALED one-shot with the FULL "
        "strength kit (mechanism_map + quant_test + novelty_gate + "
        "inspiration; the V111 prereg: one-shot, burn after, "
        "problem-only, agnes-3.0-flash). The instrument reads the "
        "owner's SEALED problem bytes from the audit branch (digest "
        "typed in every row), wires the kit into the authoring prompt "
        "(the mechanism-map constraint block + the engine prediction "
        "leg as the typed required-inputs manifest for the pint "
        "formula + the inspiration precedents + the quantitative-"
        "testability and novelty-strength binds — the R144-F1 fix "
        "for the 2/30 kill-condition gap), and records the machine's "
        "landed scans + the novelty gate per row as the builder "
        "screen INPUTS. BEFORE the run: the additive classifier "
        "extension measured necessary — the sealed routing was 18/30 "
        "(the verb forms 'corrodes'/'fouls'/'erodes'/'resonates' and "
        "the separation/CTE/insulation vocabulary); after: 30/30 in "
        "the owner's 10-class grouping (the weighted-keyword "
        "semantics resolve the cross-class rows: resonance-caused "
        "cracking stays vibration, CTE-mismatch cracking stays "
        "thermal; pinned by tests/test_generation_mechanism_map.py). "
        "Acceptance typed for this lane: 30/30 raw rows committed "
        "with the run; 0 QUANT_TEST_MISSING on the scan surface; the "
        "mean>=3.3 / CI lower>3.0 / >=30% strong / 0 off-target gate "
        "is PENDING-AUDITOR-SCORE (the private rubrics, digest "
        "1db1539e935038db, never read by the builder; the builder "
        "never scores itself — Art. 10/14)."),
}
claims.append(claim)
d["claims"] = claims
CNT.write_text(f"c-{int(nxt[2:]) + 1:04d}\n")
REG.write_text(json.dumps(d, indent=2, ensure_ascii=True) + "\n")
print(f"registered session {SESSION} + claim {nxt} "
      f"(work r145-v17-sealed-one-shot, base {BASE}, lease {lease}); "
      f"counter -> c-{int(nxt[2:]) + 1:04d}")
