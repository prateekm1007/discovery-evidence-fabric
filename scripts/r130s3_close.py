#!/usr/bin/env python3
"""r130s3_close.py — the dir-3 close for claim c-0209 (work id
r130s3-diffmin-fold): (1) work_claims c-0209 -> DONE with the quoted
CI chain + the gate outcome; (2) eval/r130s3_status.json — the
third-lane R130 record (the byte-proven dict schemas). Zero engine
lines."""
import datetime
import json
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
NOW = datetime.datetime.now(datetime.timezone.utc).strftime(
    "%Y-%m-%dT%H:%M:%SZ")

scoring = json.load(open(REPO / "eval" / "r130s3_diffmin_scoring.json"))
gate = scoring["gate"]
assert gate["verdict"] == "FOLD"
assert gate["no_regression_defects"] and gate["no_regression_heal"]

# (1) claim c-0209 -> DONE
wc_path = REPO / "eval" / "work_claims.json"
wc = json.load(open(wc_path))
claim = None
for c in wc["claims"]:
    if c["claim_id"] == "c-0209":
        claim = c
        break
assert claim is not None and claim["status"] in ("OPEN", "DONE")
claim["status"] = "DONE"
claim["completed_at"] = NOW
claim["notes"] = (
    "Art. 29(b) held: prereg + claim pushed as the lock at 269343a57 "
    "BEFORE any run call (refs/claims/next rides the same push); CI "
    "re-read from the API: check-run 137319021739 surface completed "
    "SUCCESS (quoted, never asserted). THEN the re-test: 96 legs "
    "(v1 vs v2 PAIRED over the 48 held-out committed F31e pre-review "
    "bills, leg mechanics byte-reused from the twin's committed "
    "harness), 1115.3 s wall pool-of-3, 0 typed fails, 96/96 "
    "parse-first-try, 7 (v1) + 15 (v2) rate_limited backoff legs "
    "absorbed (max 2 attempts). GATE (dir 3, preregistered): v2 "
    "2/48 defect rows <= v1 2/48 (both duty_pricing, DIFFERENT pids "
    "— the MF-2 rate-floor finding: the residual is a ~2/48-per-draw "
    "rate property, not a fixed item property) AND heal v2 0 >= v1 0 "
    "-> FOLD (no regression on either metric; typed honestly as "
    "no-regression, NOT improvement — the improvement evidence stays "
    "the twin's stage-1 heal 0.083 on their corpus). THE FOLD "
    "(byte-verified): r125_f31e_run.py IMPROVED_DIRECTIVE = the v1 "
    "provenance bytes (eval/r122_lever_prereg.json UNTOUCHED) + the "
    "M5 clause literal (byte-identical to the twin's m5_minimal; 567 "
    "+ 195 = 762 chars == the re-tested v2, asserted in-session). "
    "Changed-file map: scripts/r125_f31e_run.py (one prompt constant "
    "+ comment), eval/MECHANISM_FINDINGS.json (created: MF-1 over-"
    "rewriting/diff-min countermeasure FOLDED, MF-2 the rate-floor, "
    "MF-3 m1/m4 DROPPED from the pool per dir 8 — recorded not "
    "deleted, MF-4 the agnes cache-telemetry-zero note), the replay "
    "records + scoring + this record set. GUARD SWEEP: no test pins "
    "the directive bytes/length (grep clean); the len() uses are "
    "recorded data fields; the record-rule + Art. 20/29 suites green "
    "locally pre-push. THE DIR-2 RECONCILIATION TYPED: the GEPA "
    "round-2 incumbent baseline stays the FROZEN v1 bytes (sha-pinned "
    "at 6f97f8311's r122_lever_prereg.json — untouched on disk), so "
    "the canonical fold does NOT collapse the twin's arm; GEPA "
    "round-2 = their typed lane item, UNCLAIMED at window start "
    "(Art. 29(c), never duplicated). THE CLOSE PUSH'S OWN CHECK-RUN "
    "IS RE-READ AFTER LANDING AND QUOTED PER D2. Dir 8: no deletions. "
    "Art. 27: zero engine lines (one prompt constant + records + "
    "instruments).")
json.dump(wc, open(wc_path, "w"), indent=1)
print(f"claim c-0209 -> DONE at {NOW}")

# (2) the R130S3 status record (the byte-proven dict schemas)
status = {
    "record": "R130S3_STATUS/1.0.0",
    "session": "builder-r130s3",
    "at": NOW,
    "responds_to": (
        "the R130 auditor verdict dirs 3+8 (the diff-minimization "
        "fold gated by the held-out no-regression re-test + the "
        "mechanism knowledge base; m1/m4 dropped from the pool). Dir "
        "1 held: the constitution byte-identity re-verified at "
        "f85ffe556 (0-line diff 6f97f8311..f85ffe556; the auditor's "
        "adjudication 2aed5305d8bf touched only its own JSON — the "
        "standing FULL-read holds, not a skip). Dir 2 (GEPA round-2) "
        "= the twin's typed lane item, UNCLAIMED at window start — "
        "cross-referenced, never duplicated (Art. 29(c)). The "
        "verdict's BoN round-2 row is DONE on this lane's prior "
        "window (c-0208 ADOPT, tip f85ffe556 GREEN 137314980753 — "
        "the verdict's snapshot predates that landing). Dirs 4/5 "
        "owner-gated; dir 6 auditor-authored."),
    "executed": {
        "dir3_diffmin_fold": (
            "RUN AND GATED (claim c-0209, work id r130s3-diffmin-"
            "fold): v2 = IMPROVED_DIRECTIVE + M5 (the twin's exact "
            "clause bytes; byte-identical to their m5_minimal) "
            "re-tested against v1 PAIRED over the 48 committed F31e "
            "pre-review bills (disjoint from the GEPA compile "
            "corpus), leg mechanics byte-reused from the twin's "
            "committed harness. 96 legs, 1115.3 s, 0 typed fails, "
            "96/96 parse-first-try. GATE: FOLD (v2 2/48 <= v1 2/48 "
            "defect rows, heal 0 >= 0 — no regression typed honestly "
            "as no-regression, NOT improvement). FOLD APPLIED "
            "byte-verified: the v1 provenance record stays untouched "
            "(also the GEPA round-2 baseline, the dir-2 "
            "reconciliation) + the M5 clause literal appended in "
            "r125_f31e_run.py."),
        "mechanism_kb": (
            "eval/MECHANISM_FINDINGS.json CREATED: MF-1 the over-"
            "rewriting finding + the diff-min countermeasure "
            "(FOLDED, evidence-cited), MF-2 the duty_pricing "
            "~2/48-per-draw rate-floor (three disjoint draws, same "
            "tally, ~zero pid overlap — class-rate comparisons are "
            "the stable instrument), MF-3 m1/m4 harmful mutations "
            "DROPPED from the candidate pool (dir 8; recorded, code "
            "untouched), MF-4 the agnes cache-telemetry-zero note "
            "(the Bedrock cachePoint stays owner-gated)."),
        "lanes_not_taken": (
            "GEPA round-2 (dir 2, TOP) = the twin's lane per their "
            "typed R130 close + the adjudication's BoN_TWIN_LANE "
            "framing — their design, their clock; this window typed "
            "the reconciliation (the frozen v1 baseline pin) that "
            "keeps their arm valid after the canonical fold. Dirs "
            "4/5 (AWS host, score-8 panel) owner-gated — no AWS keys "
            "in the vault, unattempted beyond the check. Dir 6 (v16 "
            "sealed set) auditor-authored — untouched."),
    },
    "art27_capability_budget": {
        "engine_line_share_measured": 0,
        "engine_diff": (
            "ZERO engine lines: the fold is ONE prompt constant "
            "(scripts/r125_f31e_run.py — the reviewer directive) + "
            "records + instruments; the engine chain (detector "
            "bytes, transport, routing, model pin) untouched — the "
            "changed lines are the 96 replay records + run.log, the "
            "scoring JSON, the KB, the folded constant, and the "
            "runner/scorer/close instruments"),
        "share_exception_reason": (
            "DISCLOSED EXCEPTION (infrastructure/measurement round — "
            "the dir-3 fold IS the auditor-directed canonical "
            "adoption of the verified m5 mechanism, with its own "
            "committed gate evidence; zero engine lines is the "
            "isolation property, not a capability gap)"),
        "primary_metric_delta": (
            "the canonical reviewer directive now carries the "
            "diff-minimization countermeasure; the held-out paired "
            "re-test shows NO regression (2/48 = 2/48 defect rows, "
            "both duty_pricing; heal 0 = 0); the delivered-defect "
            "instrument unchanged; the GEPA round-2 comparison "
            "baseline = the frozen v1 bytes (typed reconciliation)"),
        "deletions": (
            "NONE (dir 8): nothing deleted; m1/m4 dropped from the "
            "candidate pool and RECORDED in the KB (their code "
            "stays committed in the twin's harness untouched); the "
            "retired ceremony stays retired; no new guards/claim "
            "kinds (the KB is a record file, neither)"),
    },
    "prereg_deviation_disclosed": (
        "NONE: the prereg was typed before any run call and the "
        "re-test followed it byte-for-byte (the prereg's held-out "
        "corpus verification, the paired arms, the gate rule — all "
        "as typed; 0 typed-fail legs, so the fail-closed policy "
        "never triggered)."),
    "remote_ci": {
        "pushed_sha": "269343a57",
        "remote_ci_conclusion": "success",
        "check_runs": [
            {"name": "surface", "conclusion": "success",
             "id": 137319021739}
        ],
        "note": (
            "the LOCK push's API read at close-commit time (the D2 "
            "honest entry); the chain this window: base f85ffe556 -> "
            "137314980753 SUCCESS; lock 269343a57 -> 137319021739 "
            "SUCCESS; THIS close push's own check-run is read via "
            "r41_remote_ci_read.py --apply after landing and quoted "
            "per D2 (a tip cannot quote itself green at commit "
            "time)"),
    },
    "dir_7_compliance": (
        "one push per push-event, each singular: the lock push "
        "(branch + refs/claims/next in ONE git push, terminal "
        "trailer lines from a message file) and this close push; "
        "each re-read to its conclusion. No multi-work_id batches."),
    "no_score_claims": True,
}
(REPO / "eval" / "r130s3_status.json").write_text(
    json.dumps(status, indent=1, ensure_ascii=False) + "\n",
    encoding="utf-8")
print("status record written: eval/r130s3_status.json")
