#!/usr/bin/env python3
"""R130s2: register the b7eda71d8 amendment commit in
trailer_violations[] (F36 typed allowance, fail-closed the OTHER way
— the violation is typed with session attribution + remediation,
never silent; the register itself is CI-gated)."""
import datetime
import json

NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

reg_path = ("/home/z/my-project/discovery-evidence-fabric"
            "/eval/work_claims.json")
with open(reg_path) as f:
    reg = json.load(f)
tv = reg.setdefault("trailer_violations", [])
shas = [str(v.get("sha") or "") for v in tv]
assert not any(s.startswith("b7eda71d8") for s in shas), \
    "already registered"
tv.append({
    "sha": "b7eda71d8",
    "session": "builder-r130s2",
    "detected_by": "builder-r130s2 (self-caught from the API read of "
                   "the amendment's own check-run 137312978577 — "
                   "FAILURE — root-caused via the job log to "
                   "test_article29_parallel_coordination.py::"
                   "test_post_adoption_commits_carry_session_and_"
                   "work_id_trailers BEFORE any report claimed green; "
                   "the honest red stays quoted)",
    "detected_at": NOW,
    "finding": "the D2 AMENDMENT commit (one record file changed: "
               "the r41_remote_ci_read.py --apply of the close push "
               "8f4f4a3ec's own SUCCESS read into "
               "eval/r130s2_status.json) was made with a single-line "
               "`git commit -m` message — the Session:/Work-Id: "
               "attribution was typed INLINE at the end of the "
               "message line, which git's trailer parser does not "
               "recognize as terminal trailers (the window's lock "
               "90d546078 and close 8f4f4a3ec carry them as proper "
               "trailer lines and pass). The discipline did not "
               "break — the FORMAT did: zero new claim content, one "
               "record file, the quote content itself",
    "remediation": "typed registration (this record) + the fix "
                   "commit pushed immediately after (made from a "
                   "message file with proper TERMINAL trailer lines, "
                   "the r130s2 lock/close pattern) + the discipline "
                   "adopted forward: EVERY commit on this lane is "
                   "made from a message file whose last two lines "
                   "are the trailers (never inline in a -m string); "
                   "the validator's red on b7eda71d8 was the "
                   "detection surface and the very next push carries "
                   "this registration; no rewrite (F42)",
    "work_id": "r130s2-bon2-parity",
})
with open(reg_path, "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("b7eda71d8 registered in trailer_violations[] (F36)")
