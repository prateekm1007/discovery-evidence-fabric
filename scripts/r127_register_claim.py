#!/usr/bin/env python3
"""Register claim c-0200 (r127-phaseA-speed) EXECUTOR OPEN (verifier
to be added at close per the one-claim-one-verifier pattern)."""
import datetime
import json

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r127-phaseA-speed":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
used = {c["claim_id"] for c in d["claims"]}
nxt = max(int(x[2:]) for x in used) + 1
cid = f"c-{nxt:04d}"
d["claims"].append({
    "work_id": "r127-phaseA-speed",
    "claim_id": cid,
    "role": "EXECUTOR",
    "session_id": "builder-r117s1",
    "kind": "task",
    "status": "OPEN",
    "base_sha": "cf434ea8a",
    "lease_expiry": "2026-11-29T23:59:00Z",
    "artifact_paths": [
        "eval/r127_phaseA_prereg.json",
        "eval/r127_phaseA/probe.json",
        "eval/r127_phaseA/gate/",
        "eval/r127_phaseA/gate_scoring.json",
        "scripts/r127_phaseA_probe.py",
        "scripts/r127_phaseA_gate.py",
        "scripts/r127_phaseA_score.py",
    ],
    "title": "Dir 2 (the R127 research round), Phase A — the "
             "sandbox-executable speed slice, preregistered in "
             "eval/r127_phaseA_prereg.json: (a) the capability probe "
             "typed in the prereg (the agnes route ACCEPTS "
             "response_format json_schema — HTTP 200 + strict JSON; "
             "usage carries the cached_tokens channel but reports 0; "
             "the identical-prefix repeat 5.35s->1.61s typed as "
             "warm-path variance, not billed caching); (b) the "
             "IMPLEMENTATION: an additive response_format "
             "pass-through on the route adapter's _post_chat/"
             "agnes_chat (transport-only, ~10 lines, detector bytes "
             "UNCHANGED 92485), the frozen-prefix-first reviewer "
             "composition (already the order), the 4-worker parallel "
             "offline eval harness (the sandbox equivalent of the "
             "owner-gated Bedrock Batch API for wall-clock); (c) the "
             "GATE RUN (12 r125_f31e_set problems, one fresh draw, "
             "timed end-to-end) with the gates: median <= 120 s / "
             "worst <= 300 s, parse retries 0 BY CONSTRUCTION (no "
             "retry loop — the retired repair loop stays retired), "
             "cached-token hit-rate reported, delivered-defect rate "
             "not worse than the F31e d1 baseline on the SAME items "
             "by more than 1 item; VARIABLE ISOLATION: the reviewer "
             "directive stays the frozen v1 bytes (the twin's "
             "duty-pricing clause, claim c-0197 OPEN, is THEIR lever "
             "and is not mixed in). Art. 20: a g4 failure deletes "
             "the schema variant. Bedrock-native Phase-A items "
             "(cachePoint, Batch API, small-model router) are "
             "OWNER-GATED (no AWS_* keys, re-checked this window).",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "notes": "The prereg + the claim + the implementation in ONE "
             "push BEFORE the gate-run bytes (the ordering rule); "
             "the probe is recon-class and disclosed in the prereg. "
             "Zero LLM in THIS push.",
})
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print(f"claim {cid} registered OPEN (r127-phaseA-speed)")
