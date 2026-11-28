#!/usr/bin/env python3
"""R95/R97: stake claim c-0111 (Art. 29(b) claim-before-work) — the
sealed holdout v12 one-shot generation. Staked BEFORE any v12 problem
byte is read; the push is the lock. The frozen machine (the driver's
own commit a067d31aa) was authored and committed BEFORE this claim."""
import json, datetime

HEAD = "0eb7d31aa-placeholder"  # replaced below from git
import subprocess
DRIVER_SHA = subprocess.run(
    ["git", "rev-parse", "HEAD"], capture_output=True,
    cwd="/home/z/my-project/discovery-evidence-fabric"
).stdout.decode().strip()[:9]
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

claim = {
    "claim_id": "c-0111",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "work_id": "holdout-v12-generation",
    "title": "THE SEALED HOLDOUT V12 ONE-SHOT (builder-r95s1): claim "
             "BEFORE any problem read (Art. 29(b); the push = the "
             "lock). The frozen machine scripts/r97_v12_one_shot.py "
             f"@ {DRIVER_SHA} (authored and committed BEFORE this "
             "claim; the F62 lesson — the machine freezes before the "
             "run): the r91 sealed-one-shot conventions (audit-branch "
             "problem custody, the F50 canonical-tuple seal recipe "
             "fail-closed vs 13e95f020b85b56f, the model-pin "
             "co-verification prereg==instrument==route-registry == "
             "agnes-3.0-flash, the AM75 identity binding asserted and "
             "logged, gateway pre-gates, served==requested=="
             "registered per-call attestation from the merged slice, "
             "durable events ledger, --max-rows PREFIX heartbeat "
             "chunks accumulating 10->20->30, resume-safe) + the r93 "
             "byte-mirror discipline (the frozen machine_generate_v77 "
             "body mirrored with insertions marked; every scan, "
             "critic, contract, directive, transport byte is the "
             "frozen module's own, imported — never re-declared) + "
             "the TWO AM82 controller insertions: [c-0109] TOOLS "
             "FIRST — the tool-grounded corrector mechanically "
             "corrects every candidate BEFORE the frozen battery "
             "scores it (the machine's own base_scan as contract "
             "oracle; the c-0107 Cantera computed verdict drives the "
             "typed chemistry rewrite); [c-0110] TREE SECOND — the "
             "AIDE tree-search controller directs every repair slot "
             "best-first over a metric-pruned frontier with distinct "
             "structural angles, BUDGET-MATCHED (zero added LLM "
             "calls); delivery = the controller's own best-live-node "
             "selection, typed in the record. Dry-run PROVEN (Art. "
             "22, zero LLM): budget matched (repairs=3 == frozen "
             "REPAIR_BUDGET=3), draft PLAIN -> repairs ANGLE, the "
             "corrector ran before scoring (the committed incumbent "
             "answer's BILL_UNTAGGED 35 -> 16 on the corrected "
             "bytes), distinct_candidates=4, delivered n3 = best "
             "live node; real frozen scans on a committed incumbent "
             "answer. STATUS: OPEN — the next actions in this lane: "
             "read the problems from the audit branch (AFTER this "
             "claim is pushed), smoke on burned HO7 rows, then the "
             "sealed 30-row one-shot with heartbeat chunks; 30/30 "
             "served==requested==registered agnes-3.0-flash "
             "attestation PRE-SCORING; commit rows + slice + ledger; "
             "green pushed CI; typed handoff to the auditor for the "
             "private-repo rubric scoring (mean>=3.0/4, 0 "
             "allowed-measures violations, 0 inverted-direction, 0 "
             "unavailable-input rows, run_verdict VALID, Art. 14 CI "
             "lower bound > 3.0). The PRIVATE rubric "
             "(prateekm1007/def-rubric-custody) is NEVER read, "
             "listed, or copied by this lane. burn_after_use: true.",
    "status": "OPEN",
    "session_id": "builder-r95s1",
    "role": "EXECUTOR",
    "kind": "task",
    "base_sha": "0eb7c23d9",
    "lease_expiry": "2026-11-21T23:59:00Z",
    "takes_over": None,
    "artifact_paths": [
        "scripts/r97_v12_one_shot.py",
        "eval/holdout_v12_generation/",
        "NOTICE.md",
    ],
    "notes": "Art. 29(b): claimed BEFORE any v12 problem byte was "
             "read (the problems file checked by SIZE only via git "
             "cat-file -s). Lane division: c-0109/c-0110 (DONE+"
             "verified) are the composed controllers; the auditor's "
             "v12 packet (d33c57357) is the custody source. The run "
             "reads the problems ONLY from the audit branch.",
    "no_problem_read_before_claim": True,
}

reg_path = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
with open(reg_path) as f:
    reg = json.load(f)
claims = reg["claims"] if isinstance(reg, dict) and "claims" in reg \
    else reg
ids = [str(c.get("claim_id")) for c in claims]
assert "c-0111" not in ids, "c-0111 already staked — race!"
claims.append(claim)
if isinstance(reg, dict):
    reg["claims"] = claims
with open(reg_path, "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print(f"c-0111 staked OPEN at base 0eb7c23d9, machine "
      f"{DRIVER_SHA} — claims now {len(claims)}")
