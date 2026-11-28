#!/usr/bin/env python3
"""r44_claim_oneshot.py — D2 claim-before-read (Art. 29(b), the v8
preregistration step 1): register session builder-r44s1 and file claim
c-0062 {work_id: holdout-v8-generation, role: EXECUTOR, kind: one_shot,
status: OPEN, base 88e693581} BEFORE any problem byte is read. The push
is the lock."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
NOW = "2026-11-17T03:05:00Z (sandbox clock)"

p = REPO / "eval" / "work_claims.json"
d = json.loads(p.read_text(encoding="utf-8"))
d.setdefault("sessions", {})["builder-r44s1"] = {
    "registered_at": NOW,
    "role": "builder",
    "note": "R44 session (the v8 one-shot executor lane + the F59 "
            "security-scan precision deliverable). Registered before "
            "the claim push per Art. 29(a)."}

claims = d.setdefault("claims", [])
assert not any(c.get("work_id") == "holdout-v8-generation"
               for c in claims), (
    "a claim for holdout-v8-generation already exists (typed abort — "
    "never two claims for the one-shot work)")
claims.append({
    "claim_id": "c-0062",
    "work_id": "holdout-v8-generation",
    "title": "the holdout-v8 ONE-SHOT generation (the auditor's "
             "preregistration audit/holdout_v8/PREREGISTRATION.json "
             "step 1): ONE generation of the frozen V8.0 machine "
             "(scripts/r43_machine_v8.py, glm-4-plus) over the 30 "
             "sealed problems (15 intervention + 15 predictor, seal "
             "f65b9d8b…), claim committed and pushed BEFORE any "
             "problem byte is read; the PRIVATE rubric is never "
             "opened by any code path",
    "status": "OPEN",
    "registered_at": NOW,
    "session_id": "builder-r44s1",
    "role": "EXECUTOR",
    "kind": "one_shot",
    "base_sha": "88e693581",
    "claimed_at": NOW,
    "lease_expiry": "2026-11-17T15:05:00Z",
    "takes_over": None,
    "artifact_paths": [
        "eval/v8_run/rows/",
        "eval/v8_run/v8_events_ledger.json",
        "eval/v8_run/v8_serving_attestation.json",
        "eval/v8_run/v8_run_ledger.json",
        "eval/v8_run/gateway_log_slice.txt",
        "scripts/r44_v8_one_shot.py",
        "eval/r44_status.json"],
    "notes": "Preregistration gates: seal recomputed EXACT before any "
             "generation; 30/30 served==registered glm-4-plus "
             "attestation PRE-SCORING; one executor; zero "
             "re-generation (the machine's internal repair budget is "
             "its own frozen loop); green pushed CI read from the "
             "check-run API. Scoring is the auditor's step 4; BURN "
             "follows (step 5)."})
d["at"] = NOW
p.write_text(json.dumps(d, indent=1, ensure_ascii=False) + "\n",
             encoding="utf-8")
print("registry: builder-r44s1 registered; claim c-0062 OPEN "
      "(holdout-v8-generation, one_shot, base 88e693581)")
