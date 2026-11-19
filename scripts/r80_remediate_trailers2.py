#!/usr/bin/env python3
"""R80: register the trailer violation for aababd100 (the commit put
Session:/Work-Id: on ONE line — git parses that as a single malformed
trailer, so the Work-Id trailer is absent) and remediate forward-only, the
F36/R47 precedent. THIS remediation commit itself carries proper trailers."""
import json, datetime, subprocess

NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
BAD_FULL = subprocess.run(["git", "rev-parse", "aababd100"],
                          capture_output=True, text=True).stdout.strip()

with open("eval/work_claims.json") as f:
    reg = json.load(f)

tvs = reg.setdefault("trailer_violations", [])
assert not any(str(v.get("sha")).startswith("aababd100") for v in tvs), \
    "violation already registered?"
tvs.append({
    "sha": BAD_FULL[:9],
    "session": "builder-r80s1",
    "detected_by": "builder-r80s1",
    "detected_at": NOW,
    "finding": "commit carries Session:/Work-Id: on ONE line (a formatting "
               "defect of the c-0107 commit command): git parses that as a "
               "single malformed Session trailer with the Work-Id inline in "
               "its value, so the Work-Id TRAILER is absent — caught by "
               "tests/test_article29_parallel_coordination.py on the push's "
               "own CI read (the same F36-class validator, second instance "
               "in this session: 63d6b3f5c lacked trailers outright, "
               "aababd100 carried them malformed)",
    "status": "DISCLOSED_PENDING_REMEDIATION",
    "note": "F36 typed allowance pattern (the R47 precedent): pushed "
            "history is never rewritten (Art. 4); remediation is forward — "
            "the remediation commit registers THIS violation typed, itself "
            "carries Session: builder-r80s1 + Work-Id: "
            "chemistry-computed-equilibrium-dev as SEPARATE trailer lines, "
            "and every builder-r80s1 commit from here onward carries "
            "properly-formatted trailers (session self-check: git log -1 "
            "--format='%(trailers)' must show BOTH lines separately "
            "BEFORE pushing). Content unaffected: the c-0107 chemistry "
            "prototype (scripts/r80_chemistry_equilibrium.py + 12 "
            "CI-wired tests + workflow wiring + NOTICE attribution) is "
            "green and stands as landed.",
})

with open("eval/work_claims.json", "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print(f"trailer violation for {BAD_FULL[:9]} registered ({len(tvs)} total)")
