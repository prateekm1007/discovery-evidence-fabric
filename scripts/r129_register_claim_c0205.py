#!/usr/bin/env python3
"""Register session builder-r129s1 + claim c-0205 (OPEN) — the Art.
29(b) claim-before-work for the r129 window's quota-consuming work
(the r129 verdict dir 5, Phase-B lever 1: best-of-n + bind-select
round 1; dir 6 rides the same window as its own committed record).
The claim push is the lock (Art. 29(b))."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r129-bon-bindselect-round1":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
if "builder-r129s1" not in d.get("sessions", {}):
    d["sessions"]["builder-r129s1"] = {
        "note": "R129 session-1: the r129-verdict window. Executor of "
                "dir 5 (Phase-B lever 1: verifier-guided best-of-n=2 "
                "+ bind-select, Art. 20-gated round 1 over the F31e "
                "set) and dir 6 (the bounded HF credit probe). Dir 1 "
                "(the FULL constitution read) completed pre-claim; "
                "dirs 2/3 (AWS host, score-8 panel) owner-gated — "
                "typed, unattempted beyond the vault AWS-key check; "
                "dir 4 (v16 sealed set) auditor-authored — untouched.",
        "registered_at": NOW}
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
# the committed counter file is the allocation authority (r128 dir-1)
cnt = (open(f"{REPO}/eval/claim_next_id.txt").read().strip())
for c in d["claims"]:
    if c.get("claim_id") == cnt:
        raise SystemExit(f"REFUSED: claim id {cnt} already used")
claim = {
    "work_id": "r129-bon-bindselect-round1",
    "claim_id": cnt,
    "role": "EXECUTOR",
    "session_id": "builder-r129s1",
    "kind": "task",
    "status": "OPEN",
    "base_sha": base,
    "lease_expiry": "2026-11-29T23:59:00Z",
    "artifact_paths": [
        "eval/r129_bon_prereg.json",
        "eval/r129_bon_run/",
        "eval/r129s1_hf_credit_probe.json",
        "scripts/r129s1_hf_credit_probe.py",
        "scripts/r129_bon_run.py",
        "scripts/r129_bon_score.py",
    ],
    "title": "Dir 5 (the R129 verdict): Phase-B lever 1 — the "
             "verifier-guided best-of-n=2 + bind-select ablation arm "
             "vs the incumbent single-shot bare+binds on the SAME 24 "
             "r125_f31e_set items, round 1 (Art. 20: beat within 2 "
             "rounds or delete). Selection by the deterministic "
             "bill_defect_classes byte rule on delivered bytes (the "
             "trustworthy metric), never LLM-judged. Incumbent "
             "recomputed from the committed F31e succ records "
             "(expected 2/48 pooled) before the gate is read. Dir 6 "
             "rides the same window: the bounded HF credit probe "
             "(whoami + ONE max_tokens=2 router call, typed verdict; "
             "FUNDED_HEADROOM_EXISTS expected per the c-0203/r128 "
             "live bytes; 402 = typed refusal class). Order: prereg "
             "+ probe record + this claim in ONE push (the lock), "
             "then the run, then the scoring + independent recompute "
             "in the round-close.",
}
d["claims"].append(claim)
json.dump(d, open(path, "w"), indent=1)
nxt = f"c-{int(cnt[2:]) + 1:04d}"
open(f"{REPO}/eval/claim_next_id.txt", "w").write(nxt + "\n")
print(f"registered {cnt} (base {base}); counter -> {nxt}")
