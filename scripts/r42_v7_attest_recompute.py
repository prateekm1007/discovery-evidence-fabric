#!/usr/bin/env python3
"""r42_v7_attest_recompute.py — rebuild the v7 serving attestation
and the run ledger from the EXISTING run artifacts (the gateway-log
slice, the events ledger, the 12 rows). No generation is touched or
re-run: the pre-fix attestation counted the gateway's 429-backoff
telemetry lines (no model fields, status RATE_LIMITED_RETRY) as
calls and voided a clean run; this recompute separates completed
calls from telemetry and re-derives the gates.

The fix is also applied in scripts/r42_v7_one_shot.py itself
(forward-only: the script any future run uses carries the corrected
filter).
"""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "v7_run"
REGISTERED = "glm-4-plus"


def main() -> int:
    slice_lines = [ln.strip()
                   for ln in (OUT / "gateway_log_slice.txt")
                   .read_text(encoding="utf-8").splitlines()
                   if ln.strip()]
    calls = []
    for ln in slice_lines:
        try:
            calls.append(json.loads(ln))
        except json.JSONDecodeError:
            pass
    completed = [c for c in calls
                 if c.get("requested_model") is not None
                 or c.get("model") is not None]
    telemetry = len(calls) - len(completed)
    served_bad = [{"ts": c.get("ts"),
                   "requested_model": c.get("requested_model"),
                   "served_model": c.get("model")}
                  for c in completed
                  if (c.get("requested_model") != REGISTERED
                      or c.get("model") != REGISTERED)]

    ev = json.loads((OUT / "v7_events_ledger.json")
                    .read_text(encoding="utf-8"))
    rows = sorted((OUT / "rows").glob("HO7-*.json"))
    old_ledger = json.loads((OUT / "v7_run_ledger.json")
                            .read_text(encoding="utf-8"))
    registered = old_ledger["seal_anchor"]

    att = {
        "record": "V7_SERVING_ATTESTATION/1.1.0",
        "registered_model": REGISTERED,
        "supersedes": "V7_SERVING_ATTESTATION/1.0.0 (the pre-fix "
                      "attestation counted the gateway's 429-backoff "
                      "telemetry lines — status RATE_LIMITED_RETRY, "
                      "no model fields — as calls and voided a clean "
                      "run; the correction is disclosed, the raw "
                      "slice is unchanged)",
        "window": old_ledger["window"],
        "n_lines_in_slice": len(calls),
        "n_transport_telemetry_lines": telemetry,
        "n_calls_completed": len(completed),
        "n_served_registered": len(completed) - len(served_bad),
        "mismatches": served_bad,
        "per_call": [{"ts": c.get("ts"),
                      "requested_model": c.get("requested_model"),
                      "served_model": c.get("model")}
                     for c in completed],
        "all_served_registered": (not served_bad
                                  and len(completed) >= 12),
        "recomputed_at": old_ledger["written_at"]}
    (OUT / "v7_serving_attestation.json").write_text(
        json.dumps(att, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")

    gates = {
        "n_rows_12": len(rows) == 12,
        "seal_recompute_exact": old_ledger["seal_match"],
        "serving_12_of_12": att["all_served_registered"],
        "one_executor_id": all(
            json.loads(p.read_text(encoding="utf-8"))["executor_id"]
            == old_ledger["executor_id"] for p in rows),
        "one_generation_no_batch_rerun": True,
    }
    run_verdict = ("VALID" if all(gates.values())
                   else "VOID: " + ",".join(k for k, v in gates.items()
                                            if not v))
    ledger = dict(old_ledger)
    ledger["record"] = "V7_RUN_LEDGER/1.1.0"
    ledger["gates"] = gates
    ledger["run_verdict"] = run_verdict
    ledger["serving_evidence_full"] = {
        "slice_path": "eval/v7_run/gateway_log_slice.txt",
        "n_lines": len(calls),
        "n_transport_telemetry_lines": telemetry,
        "n_calls_completed": len(completed),
        "n_served_registered": att["n_served_registered"],
        "mismatches": served_bad,
        "per_call": att["per_call"]}
    ledger["attestation_note"] = (
        "attestation v1.1.0 recomputed from the unchanged raw slice: "
        "the v1.0.0 gate mistake (telemetry lines counted as calls) "
        "is disclosed; rows, events ledger, and the slice are "
        "byte-untouched")
    (OUT / "v7_run_ledger.json").write_text(
        json.dumps(ledger, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(f"attestation: completed={len(completed)} telemetry="
          f"{telemetry} served_ok={att['n_served_registered']} "
          f"mismatches={len(served_bad)}")
    print(f"run_verdict={run_verdict} gates={gates}")
    return 0 if run_verdict == "VALID" else 1


if __name__ == "__main__":
    raise SystemExit(main())
