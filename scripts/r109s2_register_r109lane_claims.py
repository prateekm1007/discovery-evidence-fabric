#!/usr/bin/env python3
"""r109s2_register_r109lane_claims.py — builder-r109s2 Art. 29(a)/(b):
the VERIFIER claims for the peer builder-r109s1's five DONE R109 lanes
(c-0133..c-0137), one commit, push = the lock. Art. 29(b): the second
session is VERIFIER on the first session's items; the lanes are DONE
with no verifier records — this registers them before any verification
work byte. Fail-closed idempotence guards.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

REG = Path(__file__).resolve().parents[1] / "eval" / "work_claims.json"
SESSION = "builder-r109s2"
LEASE = "2026-11-22T23:59:00Z"
NOW = datetime.now(timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)")
BASE = "420898e84"

d = json.loads(REG.read_text(encoding="utf-8"))
assert d["schema"] == "work-claims/v1"
ids = {c.get("claim_id") for c in d["claims"]}
by_work_role = {(c.get("work_id"), c.get("role")) for c in d["claims"]}

LANES = [
    ("c-0140", "r109-lane-d6-pymupdf",
     "VERIFIER duty for c-0133 (builder-r109s1, Art. 29(c) — the "
     "recompute, never a re-run): the PyMuPDF retirement verified "
     "from COMMITTED BYTES — zero fitz imports tree-wide (the "
     "verifier's own grep + AST sweep, excluding quoted probe "
     "strings), the NOTICE row retirements/additions "
     "(fitz OUT; pdfplumber IN; poppler-utils subprocess-only), the "
     "retirement-ledger entry, test_notice_import_coverage + "
     "test_r440_package_quality_gate re-run on the ported geometry, "
     "and the parity record's quoted numbers re-derived from the "
     "committed fixture verdicts.",
     "eval/r109s2_r109lanes_verifier_record.json"),
    ("c-0141", "r109-lane-d5d8-score9",
     "VERIFIER duty for c-0134 (builder-r109s1, Art. 29(c)): the "
     "score-9 root-cause analysis + the D8 bias probe verified from "
     "COMMITTED BYTES — the label matrix (2 BOTH-RECOVERED / 9 "
     "single-judge / 15 BOTH-PARTIAL / 5 J1-NR-J2-PARTIAL / 2 BOTH-NR "
     "over 29 OK items) independently re-tallied from the committed "
     "status record's per-item labels; the 'ANY-single-judge yields "
     "7/29=0.2414 < 0.40' claim recomputed; the J2-leniency shape "
     "recounted; the MOOSE-Chem2 unavailability typing checked "
     "against its committed evidence; the D8 bias probe's raw bytes "
     "(eval/r109_d8_bias_probe_raw/) re-read and the ZERO-flips "
     "claim re-derived from the committed judgment bytes.",
     "eval/r109s2_r109lanes_verifier_record.json"),
    ("c-0142", "r109-lane-d2d3-score8",
     "VERIFIER duty for c-0135 (builder-r109s1, Art. 29(c)): the "
     "transport-probe record + the agreement pre-registration "
     "verified from COMMITTED BYTES — the seven 403 probe rows' "
     "status/error-class consistency, the {agnes, zai} served-family "
     "conclusion vs the committed probe evidence, the UNFUNDED "
     "typing of the direct transports (vault keys absent — "
     "digest-only check), and the D3 pre-registration's three levers "
     "(the 7-point rubric table present, the frozen-12-row "
     "calibration-set qualification design, BOTH disagreement "
     "statistics with mean-pairwise as the gate-binding clause) "
     "verified as committed BEFORE any v16 scoring exists.",
     "eval/r109s2_r109lanes_verifier_record.json"),
    ("c-0143", "r109-lane-d4-gate-staging",
     "VERIFIER duty for c-0136 (builder-r109s1, Art. 29(c)): the "
     "gate-staging record verified from COMMITTED BYTES — the anchor "
     "anatomy numbers (prior dist 0.10399 vs heterogeneous p95 "
     "0.158496 vs margin leg 0.119696; the 30 rows 0.037-0.096 "
     "median 0.059; n_novel=0) recomputed from the committed "
     "r106_core_mechanism_gate_run.json bytes; the three staged "
     "candidates' arithmetic re-derived.",
     "eval/r109s2_r109lanes_verifier_record.json"),
    ("c-0144", "r109-lane-d7-xjtu-full",
     "VERIFIER duty for c-0137 (builder-r109s1, Art. 29(c)): the "
     "typed disk blocker verified from COMMITTED BYTES — the probe "
     "record's df figures vs this sandbox's independent df read "
     "(the same rootfs), the >=12GB resume condition's arithmetic "
     "vs the ~11GB full-set estimate, and the 173-file sample's "
     "standing as the current real-bytes coverage cross-checked "
     "against the c-0138 verification.",
     "eval/r109s2_r109lanes_verifier_record.json"),
]

for cid, wid, title, artifact in LANES:
    assert cid not in ids, f"{cid} already registered"
    assert (wid, "VERIFIER") not in by_work_role, \
        f"a VERIFIER claim already exists on {wid}"
    assert any(c.get("work_id") == wid and c.get("role") == "EXECUTOR"
               for c in d["claims"]), f"no EXECUTOR claim on {wid}"
    d["claims"].append({
        "claim_id": cid,
        "claimed_at": NOW,
        "registered_at": NOW + " (push = the lock, Art. 29(b))",
        "work_id": wid,
        "session_id": SESSION,
        "role": "VERIFIER",
        "status": "OPEN",
        "kind": "task",
        "base_sha": BASE,
        "lease_expiry": LEASE,
        "title": title,
        "artifact_paths": [artifact],
        "notes": ("the peer's DONE R109 lanes carry no verifier "
                  "records; the second session's Art. 29(b) duty — "
                  "recompute from committed bytes, zero quota, zero "
                  "LLM, zero sealed bytes."),
    })

REG.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
               encoding="utf-8")
print(f"registered c-0140..c-0144 ({len(d['claims'])} claims)")
