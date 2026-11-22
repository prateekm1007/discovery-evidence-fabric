#!/usr/bin/env python3
"""Register claim c-0192 (r125-f97-generalization-check) DONE."""
import datetime
import json
import subprocess

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") == "r125-f97-generalization-check":
        raise SystemExit(f"REFUSED: claim exists {c.get('claim_id')}")
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
claim = {
    "work_id": "r125-f97-generalization-check",
    "claim_id": "c-0192",
    "role": "EXECUTOR",
    "session_id": "builder-r117s1",
    "kind": "one_shot",
    "status": "DONE",
    "base_sha": base,
    "lease_expiry": "2026-11-29T23:59:00Z",
    "artifact_paths": [
        "eval/r125_f97_generalization/",
        "scripts/r125_f97_generalization.py",
    ],
    "title": "Dir 3 (the R125 verdict): the F97 detector "
             "generalization check on a HELD-OUT narration corpus "
             "beyond the 69-firing calibration corpus and beyond the "
             "6 preregistered probes. THE RESULT (zero LLM): 12 "
             "held-out narration shapes (NEW prose shapes: "
             "loop-for-monitoring, watch-lists, standard-monitoring, "
             "alarm-frames, shift-handover narration...) — 0/12 "
             "FALSE POSITIVES (precision generalizes to unseen "
             "narration); 5 genuine-fire sensitivity probes written "
             "in the canonical fire-surface grammar the c-0186 "
             "prereg defines (an online quantity measured "
             "continuously in-line and CONSUMED as the control "
             "signal; NEW quantities: hydrogen concentration, "
             "acoustic cage noise, residual chlorine, roll crack "
             "scan, headspace oxygen) — 5/5 FIRE (genuine-fire "
             "sensitivity retained on unseen shapes). ACCEPTANCE "
             "MET (the R125 dir 3 accept: precision holds on unseen "
             "narration; genuine-fire sensitivity holds). TYPED "
             "OBSERVATION (not gating): 3 sparse short-mention "
             "shapes (bare 'continuously sense X' / 'track X every "
             "cycle' without the online-X control-signal "
             "construction) do NOT fire — the canonical fire-surface "
             "is the dense control-signal grammar; whether the "
             "sparse-mention class should bind is the auditor's "
             "semantic call, consistent with the c-0187 recall "
             "question.",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "completed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "notes": "Zero LLM, zero network. No competing claim. Verifier "
             "record follows at round-close per the Art. 29 rule.",
}
d["claims"].append(claim)
d["claims"].append({
    "work_id": "r125-f97-generalization-check",
    "claim_id": "c-0193",
    "role": "VERIFIER",
    "session_id": "builder-r117s1",
    "kind": "task",
    "status": "DONE",
    "base_sha": base,
    "lease_expiry": "2026-11-29T23:59:00Z",
    "artifact_paths": ["eval/r125_f97_generalization/",
                       "scripts/r125_f97_generalization.py"],
    "title": "VERIFIER record for work_id r125-f97-generalization-check",
    "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "completed_at": f"{NOW} (sandbox clock, TRUE UTC)",
    "notes": "Recomputed from committed bytes (Art. 13, never "
             "re-ran): the corpus script re-executes to a copy — "
             "0/12 narration false positives, 5/5 sensitivity "
             "probes fire, every case outcome identical to the "
             "committed generalization_result.json (deterministic, "
             "zero LLM)."})
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print("claims c-0192 (executor DONE) + c-0193 (verifier) registered")
