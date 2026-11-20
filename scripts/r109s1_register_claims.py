#!/usr/bin/env python3
"""r109s1_register_claims.py — builder-r109s1 Art. 29(a)/(b) registration:
the session identity + the round's EXECUTOR claims (c-0133..c-0137),
one commit, push = the lock (R108 verdict directions 2..8 lanes).
Registry formatting preserved (json.dumps indent=1, ensure_ascii=False,
trailing newline). Idempotence guard: refuses to re-append existing
claim_ids (fail-closed, Art. 3).
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "eval" / "work_claims.json"
SESSION = "builder-r109s1"
BASE = "5940e9749"
LEASE = "2026-11-22T23:59:00Z"
NOW = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")

d = json.loads(REG.read_text(encoding="utf-8"))
assert d["schema"] == "work-claims/v1"
ids = {c.get("claim_id") for c in d["claims"]}
assert SESSION not in d["sessions"], "session already registered — refuse to duplicate"

d["sessions"][SESSION] = {
    "registered_at": NOW,
    "role": "builder",
    "note": ("R109 session-1: the R108 verdict directions 2..8 lane family. "
             "Queue re-synced bfaab8511 -> 5940e9749 ff-only (the stale R64s4-era "
             "untracked eval/holdout_v9_generation/ backed OUT of tree to "
             "/home/z/my-project/scratch_backup/, the bfaab8511 snapshot-commit "
             "precedent); the audited state 972272bbd verified as an ancestor. "
             "D1 preflight COMPLETE before any work byte: EPISTEMIC_CONSTITUTION.md "
             "v3.3.0 FULL-read at 972272bbd (29 articles + 4 amendment records + "
             "the Art. 28 addendum) and AUDITOR_CONSTITUTION.md v1.3.0 FULL-read "
             "at origin/audit/r11-auditor-verdict-20261114 (14 articles + 3 "
             "amendments); vault restored via scripts/r77_vault_restore.py exit 0 "
             "with the owner re-delivered master HF token (digest-only custody, "
             "COMMITTED_RECORD_MATCH vs the Art. 17 v3.3.0 pinned digest "
             "33bc7af22c62; 6 vault-managed keys, .env.keys back at 0600 "
             "gitignored after the 755 mode violation was caught on arrival); "
             "generator registration verified agnes-3.0-flash on the live "
             "purposes with the judge route held separate "
             "(xkiro/ministral-14b) and the 2-key rotation wired "
             "(AGNES_API_KEY + AGNES_API_KEY_2 in the gateway keyEnvs and the "
             "vault)."),
}

CLAIMS = [
    {
        "claim_id": "c-0133",
        "work_id": "r109-lane-d6-pymupdf",
        "title": ("D6 PyMuPDF retirement (the R108 direction 6): the "
                  "package_quality_gate PDF block-geometry leg ports off "
                  "fitz (AGPL) to pypdf (BSD-3, already in-tree). Test per "
                  "the direction: the NOTICE fitz row retires; "
                  "test_notice_import_coverage.py still passes (zero fitz "
                  "imports tree-wide); gate parity on the committed PDF "
                  "fixtures (mechanics-only fixtures labelled per Art. 22 — "
                  "no acceptance on fixtures alone)."),
        "artifacts": ["eval/r109_d6_parity_record.json"],
    },
    {
        "claim_id": "c-0134",
        "work_id": "r109-lane-d5d8-score9",
        "title": ("D5 score-9 root cause + D8 author/J1 bias check (the R108 "
                  "directions 5+8): the per-item failure taxonomy on the 25 "
                  "PARTIAL + the 2 RECOVERED deltas from the committed rerun "
                  "bytes (recompute, never a re-run — Art. 29(c) discipline "
                  "for the analysis stage); the MOOSE-Chem2 2025 availability "
                  "probe typed; the D8 swap-family re-judge of the 2 "
                  "RECOVERED items + the disclosed z-ai author/J1 family "
                  "overlap re-verified. Zero sealed bytes; recovery-rate "
                  "claims stay the auditor's."),
        "artifacts": ["eval/r109_d5_rootcause.json", "eval/r109_d8_bias_check.json"],
    },
    {
        "claim_id": "c-0135",
        "work_id": "r109-lane-d2d3-score8",
        "title": ("D2 third-family transport probes + D3 agreement levers "
                  "(the R108 directions 2+3): typed per-endpoint probe "
                  "records (direct OpenAI / Azure-shaped / Anthropic direct; "
                  "status + latency + protocol fit only — no key values, "
                  "vault-only custody); the D3 lever design committed "
                  "BEFORE any v16 scoring (7-point anchored rubric, blind "
                  "calibration-set agent qualification, dual pre-registered "
                  "disagreement rules) — the pre-registration is the "
                  "anti-tuning control (Art. 6)."),
        "artifacts": ["eval/r109_d2_transport_probe.json", "eval/r109_d3_agreement_design.json"],
    },
    {
        "claim_id": "c-0136",
        "work_id": "r109-lane-d4-gate-staging",
        "title": ("D4 gate staging for the auditor's v16 authoring (the R108 "
                  "direction 4): the candidate distribution data committed "
                  "(the known-novel anchor scores vs the heterogeneous prior "
                  "corpus under the p95 / robust MAD-z / margin-without-p95 "
                  "legs, recomputed from committed judgment bytes); the "
                  "builder stages data only — the v16 gate definition stays "
                  "the auditor's (claim-before-work execution when it "
                  "lands)."),
        "artifacts": ["eval/r109_d4_gate_staging.json"],
    },
    {
        "claim_id": "c-0137",
        "work_id": "r109-lane-d7-xjtu-full",
        "title": ("D7 XJTU-SY full extraction (the R108 direction 7), "
                  "disk-gated: df -h first; the full set needs ~11GB — a "
                  "typed blocker stands if the headroom is absent (Art. 15, "
                  "never a silent skip). If unlocked: all 15 bearings' full "
                  "life courses via the validated static 7zz binary, "
                  "coverage >=0.90 on >=3 bearings with the matched-budget "
                  "table."),
        "artifacts": ["eval/r109_d7_disk_probe.json"],
    },
]

now = NOW
for spec in CLAIMS:
    assert spec["claim_id"] not in ids, f"{spec['claim_id']} already exists — fail closed"
    ids.add(spec["claim_id"])
    d["claims"].append({
        "claim_id": spec["claim_id"],
        "claimed_at": now,
        "registered_at": now + " (push = the lock, Art. 29(b))",
        "work_id": spec["work_id"],
        "session_id": SESSION,
        "role": "EXECUTOR",
        "status": "OPEN",
        "kind": "task",
        "base_sha": BASE,
        "lease_expiry": LEASE,
        "title": spec["title"],
        "notes": ("one EXECUTOR per work_id; no competing claim on the same "
                  "work_id at the registry tip 5940e9749 (checked); stage "
                  "pushes are the heartbeats (Art. 29(d))"),
        "artifact_paths": spec["artifacts"],
    })

REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"registered session {SESSION} + claims c-0133..c-0137 "
      f"({len(d['claims'])} total claims, {len(d['sessions'])} sessions)")
