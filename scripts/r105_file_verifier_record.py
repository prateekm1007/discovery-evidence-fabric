#!/usr/bin/env python3
"""File the c-0119 VERIFIER record (Art. 29(c): a DONE one_shot
measurement needs the verification record — the recompute from
committed bytes, never a re-run).

HONESTY TYPING (Art. 2/11): this record is filed by the SAME session
that executed the run — it is the driver's built-in attest() verifier
lane (a separate code path that re-parses the committed gateway slice
and row files from bytes only; it never re-runs the generation). A
CROSS-SESSION verifier re-verification is INVITED and typed as the
preferred completion of the pair (the r103s1 pattern).
"""
import datetime
import json

REPO = "/home/z/my-project/discovery-evidence-fabric"
PATH = REPO + "/eval/work_claims.json"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

with open(PATH) as f:
    d = json.load(f)
claims = d["claims"]
nums = sorted(int(c["claim_id"][2:]) for c in claims
              if c["claim_id"].startswith("c-"))
cid = f"c-{nums[-1] + 1:04d}"
assert all(c["claim_id"] != cid for c in claims)

claim = {
    "claim_id": cid,
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "holdout-v15-generation",
    "title": (
        "VERIFIER record for c-0119 (Art. 29(c): the recompute, never "
        "a re-run): the sealed v15 one-shot attestation recomputed "
        "from COMMITTED BYTES via the driver's attest() verifier lane "
        "(scripts/r105_v15_one_shot.py attest — re-parses the "
        "committed gateway slice + row files; zero generation calls): "
        "rows 30/30, rows_30_30_attestation TRUE, 157/157 gateway "
        "calls OK / 0 errors, served==requested==registered=="
        "agnes-3.0-flash on every completed call, upstream==agnes, "
        "both serving-key digests present (2-key rotation), P3 gates "
        "PASS (median 37.5s / worst 56.2s), MEASURED_PATH on every "
        "row. HONESTY TYPING: same-session bytes-only recompute — a "
        "CROSS-SESSION verifier re-verification is invited and typed "
        "as the preferred completion (the r103s1 pattern)."),
    "status": "DONE",
    "session_id": "builder-r105s1",
    "role": "VERIFIER",
    "kind": "task",
    "base_sha": "539b88340",
    "lease_expiry": "2026-11-22T23:59:00Z",
    "artifact_paths": [
        "eval/holdout_v15_generation/attestation.json",
        "eval/holdout_v15_generation/gateway_slice.txt",
        "eval/holdout_v15_generation/events.json",
        "eval/holdout_v15_generation/rows/",
        "eval/r105s1_status.json",
    ],
    "notes": (
        "Art. 29(c): verification is a recompute from committed "
        "bytes, never a re-run. The attest() lane re-parses the "
        "committed slice bytes independently of the run-time state; "
        "no gateway was started for this record. Art. 13 "
        "independent-tally discipline: the cross-session "
        "re-verification remains welcome (typed invitation)."),
    "no_problem_read_before_claim": "n/a (verifier: reads committed "
                                    "run bytes only, post-run)",
}
claims.append(claim)
with open(PATH, "w") as f:
    json.dump(d, f, indent=1, ensure_ascii=False)
    f.write("\n")
print(f"{cid} VERIFIER record filed | claims:", len(claims))
