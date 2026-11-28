#!/usr/bin/env python3
"""r143s2_register_claims — the claim-before-work registration for this
window (legal F42 statuses ONLY: OPEN/DONE/EXPIRED/TAKEN_OVER — the
Art. 29 enum that the r142 red tip tripped on via 'STOOD_DOWN')."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CLAIMS = REPO / "eval" / "work_claims.json"
NEXT = REPO / "eval" / "claim_next_id.txt"
BASE = "ac057085e"

doc = json.loads(CLAIMS.read_text())
have = {c.get("claim_id") for c in doc["claims"]}


def mk(cid, work_id, kind, title, artifacts):
    return {
        "work_id": work_id, "claim_id": cid, "role": "EXECUTOR",
        "session_id": "builder-r142s2", "kind": kind,
        "status": "OPEN", "base_sha": BASE,
        "lease_expiry": "2026-11-30T23:59:00Z",
        "claimed_at": "2026-11-23 (sandbox clock)",
        "registered_at": "2026-11-23 (sandbox clock)",
        "artifact_paths": artifacts, "title": title}


if "c-0233" not in have:
    doc["claims"].append(mk(
        "c-0233", "r143-grounded-yield-broaden", "task",
        "R143S2 EXECUTOR (claim c-0233, base d1d136660): DIR-4 — broaden "
        "the quote-anchored re-generation firing to the synthesis/generation "
        "stage (wind starves at 0 candidates: nothing exists for the "
        "enrichment lane to anchor) and verify the frozen-set identity-gate "
        "fix holds (0 bad admissions); acceptance >=2/5 fresh problems "
        "grounded identity-true; raw bytes committed with the acceptance",
        ["eval/r143_yield_run/", "scripts/r143_yield_run.py"]))
NEXT.write_text("c-0234\n")
CLAIMS.write_text(json.dumps(doc, indent=2) + "\n")
print("registered c-0233 (r143-grounded-yield-broaden) ONLY — c-0232 "
      "belongs to builder-r121s1-3e8a41d7 (r143-rcal-oneshot-am47, "
      "first-registered at ac057085e): NO duplicate claim ids; this "
      "lane stays OFF the r143 panel one-shot (the r142 duplicate-"
      "generation lesson)")
print("statuses:", [(c["claim_id"], c["status"]) for c in doc["claims"]
                    if c["claim_id"] == "c-0233"])
