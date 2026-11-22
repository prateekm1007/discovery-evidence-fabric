#!/usr/bin/env python3
"""R123 claim registrations: c-0186 (the F97 detector-precision work)
and c-0187 (the successor-v2 fresh run). Usage: --f97 | --v2"""
import datetime
import json
import subprocess
import sys

REPO = "/home/z/my-project/discovery-evidence-fabric"
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")
which = sys.argv[1] if len(sys.argv) > 1 else "--f97"

path = f"{REPO}/eval/work_claims.json"
d = json.load(open(path))
for c in d["claims"]:
    if c.get("work_id") in ("r123-f97-detector-precision",
                            "r123-successor-v2-fresh-run"):
        raise SystemExit(f"REFUSED (typed): claim exists: "
                         f"{c.get('claim_id')} {c.get('work_id')}")
base = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=REPO,
                      capture_output=True, text=True).stdout.strip()
next_id = f"c-{max(int(c['claim_id'][2:]) for c in d['claims']) + 1:04d}"

if which == "--f97":
    claim = {
        "work_id": "r123-f97-detector-precision",
        "claim_id": next_id,
        "role": "EXECUTOR",
        "session_id": "builder-r117s1",
        "kind": "one_shot",
        "status": "OPEN",
        "base_sha": base,
        "lease_expiry": "2026-11-26T23:59:00Z",
        "artifact_paths": [
            "scripts/r40_machine_v77.py",
            "tests/test_f97_input_availability_precision.py",
            "tests/fixtures/f97_input_availability_cases.json",
            "eval/r123_f97_rescoring/",
            "scripts/r123_build_f97_fixture.py",
            "scripts/r123_f97_rescore.py",
        ],
        "title": "Dir 2 (the R123 verdict, the F97 adjudicated fix): "
                 "the input_availability detector parses PROSE WORDS as "
                 "required online signals ('Continuously', 'critical', "
                 "'loop for', 'O2 concentration)') — inflating both "
                 "arms and creating the reviewer-immune class. THE "
                 "FIX (regression-pinned on REAL committed run bytes, "
                 "25 typed cases in tests/): F97-M1 balanced "
                 "paren-strip of the mechanism span before any "
                 "matching/windowing; F97-M2 a signal-name validity "
                 "gate on BOTH quantity-extraction paths (no leading/"
                 "trailing function token; not a pure "
                 "adverb/control/generic span) with the compound path "
                 "falling through to the object path; F97-M3 a "
                 "clause-verb garbage gate on the leg-2 feature-name "
                 "capture. The four named shapes go SILENT; the "
                 "genuine signal/feature findings KEEP FIRING (the "
                 "recall guard: Wet-Bulb Deviation Logic, DP-Opacity "
                 "Correlation, Amperometric Drift Correction, rate of "
                 "DP, post-pulse state, current...). THE RE-SCORING "
                 "(zero LLM, both committed fresh draws re-scored "
                 "under the fixed detector): replication lane bare "
                 "0.583->0.458 vs succ 0.417->0.292; claiming lane "
                 "bare 0.708->0.583 vs succ 0.375->0.167; POOLED n=48 "
                 "bare 0.5208 vs succ 0.2292 <= 0.25 (the ABSOLUTE "
                 "gate now passes pooled on existing bytes), mean "
                 "diff +0.2917 CI95 [+0.167,+0.438] EXCLUDES 0 (the "
                 "RELATIVE gate holds), pooled damage 1/23 = 0.043 "
                 "<= 0.25. Art. 27: an adjudicated instrument-"
                 "precision change (typed PRECISION round); the "
                 "pre-F97 committed records stand as measured under "
                 "their own instrument.",
        "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "notes": "No competing claim (checked: the registry tail c-"
                 "0185 DONE; no OPEN claim on this work_id). The "
                 "stale-bytecode hazard typed in the record: the "
                 "sandbox snapshot scrambled mtimes so a pre-R70 pyc "
                 "validated against the current source — purged; all "
                 "scoring runs execute with clean bytecode.",
    }
elif which == "--v2":
    claim = {
        "work_id": "r123-successor-v2-fresh-run",
        "claim_id": "c-0188",
        "role": "EXECUTOR",
        "session_id": "builder-r117s1",
        "kind": "one_shot",
        "status": "OPEN",
        "base_sha": base,
        "lease_expiry": "2026-11-26T23:59:00Z",
        "artifact_paths": [
            "eval/r123_successor_v2_prereg.json",
            "eval/r123_v2_run/",
            "scripts/r123_v2_run.py",
        ],
        "title": "Dirs 3+5 (the R123 verdict): the successor-v2 fresh "
                 "confirmation — the F31d run of (bare author "
                 "[committed bytes, both draws] + the F97-fixed check "
                 "layer + the improved-directive reviewer FIRST PASS) "
                 "over the frozen set's two independent authoring "
                 "draws. The reviewer directive is the TWIN'S FROZEN "
                 "improved-directive bytes (eval/r122_lever_prereg.json, "
                 "imported byte-exact, never re-typed — the dir-3 "
                 "lever as preregistered at c-0185). 48 reviewer "
                 "calls worst case, zero authoring calls, byte-skip "
                 "resume. Accept (the score-9 gates on the pooled "
                 "n=48 measurement, seed 125): pooled successor rate "
                 "<= 0.25 AND the pooled paired CI excludes 0 below "
                 "bare AND pooled damage <= 0.25 -> the score-9 axis "
                 "FULLY met; else typed honest negative. Ordering: "
                 "the prereg + this claim in ONE push BEFORE any run "
                 "byte.",
        "registered_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "claimed_at": f"{NOW} (sandbox clock, TRUE UTC)",
        "notes": "No competing claim (checked: no OPEN claim on this "
                 "work_id). The c-0185 second-pass lever result (heal-2/"
                 "break-3 under the then-buggy detector) stands; this "
                 "run tests the improved directive as a FIRST pass "
                 "under the FIXED detector — the config the absolute "
                 "target was re-based against.",
    }
else:
    raise SystemExit("usage: --f97 | --v2")

d["claims"].append(claim)
with open(path, "w") as f:
    json.dump(d, f, indent=1, sort_keys=True)
print(f"claim {claim['claim_id']} registered OPEN "
      f"({claim['work_id']}), base {base}")
