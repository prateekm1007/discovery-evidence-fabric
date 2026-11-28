#!/usr/bin/env python3
"""r34_records.py — AM32 D2 + D5 + registry disposition.

D2: holdout v5 BURNED-INVALID (no acceptance; seal spent) + the formal
    v6 request to the auditor with the verified-model-window precondition.
D5: byte-count correction (Art. 4 — explicit, never silent): the figure
    AM31/AM32 cite (17,418) and the builder cited (17,514) are the SAME
    blob measured in different units — wc -m characters vs wc -c bytes.
Registry: c-0034 CLOSED-VOID (attestation pointer); c-0035 execution
    complete pending peer verification.
"""
from __future__ import annotations
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
EVAL = REPO / "eval"

# ---------------- D5: byte-count correction (units reconciliation) ----
D5 = ("CORRECTED (R34, D5, Art. 4): the constitution is ONE identical "
      "blob (e79f9176b806c091bfff7b4fa95dc5d11d5e4ead) at "
      "8e8e1b635/ad0432bbd/7cff10559/e401bb2ad/HEAD. Measured at the "
      "audited SHA e401bb2ad: 17,418 CHARACTERS (wc -m) and 17,514 BYTES "
      "(wc -c). AM31/AM32's 17,418 figure is the character count; the "
      "builder's earlier '17,514 bytes' was the byte count of the same "
      "blob. There is no byte delta — the 96-unit discrepancy was a "
      "units mismatch (multibyte UTF-8), typed as a units observation, "
      "not a content change.")

p = EVAL / "r33_preflight.json"
d = json.loads(p.read_text(encoding="utf-8"))
def patch(o):
    if isinstance(o, dict):
        return {k: patch(v) for k, v in o.items()}
    if isinstance(o, list):
        return [patch(v) for v in o]
    if isinstance(o, str) and "17514" in o:
        return o + " || " + D5
    return o
d = patch(d)
d["byte_count_correction_r34"] = D5
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")

p = EVAL / "r33_status.json"
d = json.loads(p.read_text(encoding="utf-8"))
def patch2(o):
    if isinstance(o, dict):
        return {k: patch2(v) for k, v in o.items()}
    if isinstance(o, list):
        return [patch2(v) for v in o]
    if isinstance(o, str) and "17514" in o:
        return o + " || " + D5
    return o
d = patch2(d)
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")

# ---------------- D2: burn record + v6 request ------------------------
burn = {
    "record": "HOLDOUT_V5_BURN_RECORD/1.0.0",
    "status": "BURNED-INVALID",
    "burned_at": "2026-11-17T00:20:00Z",
    "burned_by": "builder-r20s2 (builder-side record; the auditor's "
                 "AM32 ruling is the authority)",
    "basis": [
        "AM32: the run is INVALID, not merely low-scoring — the "
        "registered frozen machine did not execute (transport bytes)",
        "served-model attestation gate (eval/holdout_v5_attestation.json): "
        "0/12 rows attested equal to zai-org/GLM-5.3 -> run VOID "
        "pre-scoring (Art. 3 fail-closed); the quarantined duplicate is "
        "VOID by the same gate",
        "tier-2 committed evidence: gateway_log_serving_models in "
        "eval/holdout_v5_full_summary.json records 30x 'glm-4-plus <- "
        "requested zai-org/GLM-5.3'; 4 of 12 rows ran on the NVIDIA "
        "chain (route_model fields)",
        "custody gap typed: the run-window gateway log was never "
        "committed (gitignored file, 0 run-day entries) — serving "
        "identity rests on the tier-2 summary alone",
    ],
    "seal_spent": True,
    "seal_spent_reason": "the problems were READ and GENERATED ON (the "
                         "canonical run AND the quarantined duplicate); "
                         "under Art. 7 one-shot use the set cannot serve "
                         "any future acceptance claim",
    "acceptance": "NONE claimed or granted; machine-side observations "
                  "(direction-bind 0/12 PHYSICS_DIRECTION_UNSTATED; "
                  "class-bind residual 1 row HO5-05; BILL_UNTAGGED=7; "
                  "ALLOWED_ROW_OUTSIDE=2) are typed INPUTS, not gate "
                  "outcomes",
    "disposition": "row files remain committed as incident/lesson bytes "
                   "(Art. 13 evidence); the PRIVATE rubric stays "
                   "auditor-custodied, never read by the builder; the "
                   "set is not reusable",
    "points_to": ["eval/holdout_v5_attestation.json",
                  "eval/holdout_v5_ledger_recompute.json",
                  "eval/r33_duplicate_generation_disclosure.json"],
}
(EVAL / "holdout_v5_burn_record.json").write_text(
    json.dumps(burn, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")

v6req = {
    "record": "HOLDOUT_V6_REQUEST/1.0.0",
    "requested_at": "2026-11-17T00:20:00Z",
    "requested_by": "builder-r20s2 (per AM32 D2)",
    "addressed_to": "the auditor (sealed-instrument author and custodian "
                    "per the Art. 28 addendum)",
    "request": "author and seal holdout v6 (fresh, domain-disjoint, "
               "auditor-authored problems AND rubric) for the next "
               "acceptance attempt",
    "preconditions_binding_on_the_builder": [
        "verified-model window: the one-shot runs ONLY when the "
        "driver's pre-scoring attestation gate can attest 12/12 rows "
        "served == zai-org/GLM-5.3 from a COMMITTED gateway-log slice "
        "(the slice is now a mandatory run artifact); any substituted "
        "or unprovable row voids the run",
        "claim-before-work per Art. 29(b) with the re-keyed session id "
        "(builder-r20s2) to keep the push-as-mutex sighted",
        "problems-only receipt; the PRIVATE rubric is never read by "
        "the builder",
        "exactly one generation (Art. 29(c)); rows commit as produced; "
        "the durable events log (append-per-fire) makes restarts "
        "row-lossless",
    ],
    "owner_action_still_open": "CROWLLM_API_KEY re-supply (D4 c-0026 "
                               "recalibration waits on it; the host is "
                               "confirmed live; no judge-route swap)",
}
(EVAL / "holdout_v6_request.json").write_text(
    json.dumps(v6req, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")

# ---------------- registry: c-0034 disposition, c-0035 note -----------
p = EVAL / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
for c in d["claims"]:
    if c.get("work_id") == "r33-holdout-v5-oneshot" and \
            c.get("status") == "OPEN":
        c["status"] = "CLOSED-VOID"
        c["disposition"] = (
            "the canonical one-shot (e401bb2ad) is VOID by the "
            "served-model attestation gate (0/12 rows equal to "
            "zai-org/GLM-5.3; AM32 INVALID ruling); v5 BURNED-INVALID "
            "(eval/holdout_v5_burn_record.json); v6 requested "
            "(eval/holdout_v6_request.json). CLOSED-VOID, not DONE: no "
            "verifier record can certify a void run.")
    if c.get("work_id") == "r34-attestation-gate-ledger-durability":
        c["status"] = "EXECUTION-COMPLETE-PENDING-VERIFICATION"
        c["execution_summary"] = (
            "D1 gate live (scripts/r34_served_model_attestation.py + "
            "driver-wired, fail-closed verified on a real NameError); "
            "v5 attested VOID 0/12 pre-scoring; D3 ledger 12/12 rows "
            "with backfill provenance anchored to the committed state, "
            "zero-LLM recompute 12/12 EXACT, durable append-per-fire "
            "events pattern in the driver; D2 burn+v6-request records "
            "written; D5 units-explicit correction applied to "
            "r33_preflight.json + r33_status.json. VERIFIER INVITED "
            "(Art. 29(c)): recompute from committed bytes, never "
            "re-run.")
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")

print("D5 correction applied to r33_preflight.json + r33_status.json")
print("D2 burn record + v6 request written")
print("registry: c-0034 CLOSED-VOID; c-0035 EXECUTION-COMPLETE-PENDING-VERIFICATION")
