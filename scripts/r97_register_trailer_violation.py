#!/usr/bin/env python3
"""R95: register the f870ac640 merge commit in trailer_violations[]
(F36 typed allowance, fail-closed the OTHER way — the violation is
typed with session attribution + remediation, never silent)."""
import json, datetime

NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

reg_path = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
with open(reg_path) as f:
    reg = json.load(f)
tv = reg.setdefault("trailer_violations", [])
shas = [str(v.get("sha") or "") for v in tv]
assert not any(s.startswith("f870ac640") for s in shas), \
    "already registered"
tv.append({
    "sha": "f870ac640",
    "session": "builder-r95s1",
    "detected_by": "builder-r95s1 (self-caught from the remote CI read "
                   "of the sealed-completion push 23ab8ad36 — the "
                   "validator reds, never silent)",
    "detected_at": NOW,
    "finding": "the FORWARD-ONLY MERGE commit (integrating the parallel "
               "builder-r96s1 lanes with the c-0111 sealed-run "
               "completion after the mid-run remote advance) was made "
               "with `git merge -m` and lacks the Session:/Work-Id: "
               "trailers — the merge carries ZERO new claim content "
               "(disjoint file sets; no measurement bytes; the "
               "sealed-run content lives in 5a00dec56 which carries "
               "full trailers), but the F36 discipline requires 100% "
               "trailer compliance post-adoption, so the violation is "
               "typed here",
    "remediation": "typed registration (this record) + the discipline "
                   "adopted forward: every future merge on this lane "
                   "is made with `git merge --no-ff -m` FOLLOWED BY "
                   "`git commit --amend` ONLY when unpushed, or "
                   "created via a trailer-bearing message from the "
                   "start (merges are commits — they carry the same "
                   "trailers); the validator's red on 23ab8ad36 was "
                   "the detection surface and the very next push "
                   "carries this registration",
    "work_id": "holdout-v12-generation",
})
with open(reg_path, "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("f870ac640 registered in trailer_violations[] (F36)")
