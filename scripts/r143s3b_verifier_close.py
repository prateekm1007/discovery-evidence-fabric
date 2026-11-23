#!/usr/bin/env python3
"""R143s3-b VERIFIER LANE: (1) file the VERIFIER records for the twin's
DONE one-shot measurements (the current CI red is exactly 'c-0237 DONE
without a VERIFIER record'); (2) heal the c-0232/c-0236 verdict
misplacement (the twin's close commit typed the R-CAL panel verdict onto
c-0236 — the trailer-violation TASK — while c-0232, the actual panel
work, stayed OPEN with no verdict); (3) register the independent
recompute results (already computed and stored by
scripts/r143s3b_verify_rcal_panel.py — diff=0 vs the driver record).

Measured state at 32877e0cf (all from bytes; CI run 138077556130
surface | completed | failure, API-quoted):
  - one red test: test_each_done_measurement_has_a_verifier_record —
    c-0237 (r143-v16-one-shot, DONE) has no VERIFIER claim.
  - c-0232 (r143-rcal-oneshot-am47, the panel work) still OPEN under
    builder-r121s1-3e8a41d7; the twin's panel verdict bytes landed on
    c-0236's entry (the wrong claim — a task claim for the trailer
    violation work).
  - this lane already recomputed the panel from raw legs: 4 qualified
    (dsr1/dsv32/qw32b/qwen235b), acc 0.833/0.917/0.917/1.0, answered
    1.0 each, imbalance<=1, kappa 0.668, 2 non-agnes families — the
    driver record matches on every bias counter (diff=0).
  - the v16 generation: 30/30 rows present at a34d69eb4+ (verified
    31 files incl. GENERATION_EVENTS.json).
  - the yield confirm: recomputed 2/5 grounded, 0 bad — matches the
    twin's SUMMARY.json exactly.

Heals (forward-only, no history rewrite, Art. 4):
  1. VERIFIER claims filed: c-0240 (r143-v16-one-shot), c-0241
     (r143-rcal-oneshot-am47), c-0242 (r143-yield-confirm-clean) —
     all DONE, this lane's session, recompute-based (Art. 29(c):
     recomputed from committed bytes, never re-run).
  2. c-0232 -> DONE with the verdict pointer (the panel acceptance
     MET; the verdict bytes live on the qualification record + the
     c-0236 annotation; the misplacement typed in corrections[]).
  3. CORR-13: the c-0236 verdict misplacement + the c-0232 gap.
"""
import json

REG = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
COUNTER = "/home/z/my-project/discovery-evidence-fabric/eval/claim_next_id.txt"

with open(REG) as f:
    reg = json.load(f)
by_id = {c["claim_id"]: c for c in reg["claims"]}

# --- sanity gates --------------------------------------------------------
assert by_id["c-0232"]["status"] == "OPEN", "c-0232 unexpectedly not OPEN"
assert by_id["c-0237"]["status"] == "DONE", "c-0237 unexpectedly not DONE"
assert by_id["c-0238"]["status"] == "DONE", "c-0238 unexpectedly not DONE"
assert "verdict" in by_id["c-0236"], "c-0236 verdict missing (precondition)"
# the twin's placeholder verifier claims (pushed at ad87aeb75: the push is
# the mutex — they registered first; this lane COMPLETES them, not duplicates)
for cid in ("c-0240", "c-0241", "c-0242"):
    assert by_id[cid]["status"] == "OPEN", cid + " unexpectedly not OPEN"
    assert by_id[cid]["session_id"] == "builder-r142s2", cid + " owner changed"
    assert by_id[cid]["role"] == "VERIFIER", cid + " role changed"

SESSION = "builder-r143s3-b"
TS = "2026-11-23 (sandbox clock)"

def vclaim(cid, work, paths, title, notes=None):
    return {
        "work_id": work, "claim_id": cid, "role": "VERIFIER",
        "session_id": SESSION, "kind": "task", "status": "DONE",
        "base_sha": "32877e0cf", "lease_expiry": "2026-11-30T23:59:00Z",
        "claimed_at": TS, "registered_at": TS,
        "artifact_paths": paths, "title": title,
        **({"notes": notes} if notes else {}),
    }

# --- 1. COMPLETE the twin's OPEN verifier claims (c-0240/c-0241/c-0242;
# their registration is the mutex — this lane executes the recompute work
# they deferred to "the next window", on their claim ids, with attribution)
by_id["c-0240"]["status"] = "DONE"
by_id["c-0240"]["completed_by"] = (
    "builder-r143s3-b (the recompute execution: "
    "scripts/r143s3b_verify_rcal_panel.py + "
    "eval/r143_panel_recompute_independent.json — the deterministic "
    "tally recompute from the 120 committed leg bytes)")
by_id["c-0240"]["verdict"] = {
    "acceptance": "VERIFIED (diff=0) — 4 qualified judges (dsr1 0.833, "
                  "dsv32 0.917, qw32b 0.917, qwen235b 1.0; answered 1.0 "
                  "each; AM47 imbalance 0/1/1/0), kappa 0.668>=0.6, 2 "
                  "non-agnes families; hy4f transport-dead (0/24); every "
                  "bias counter matches the driver record; the DIR-3 "
                  "score-8 gate acceptance is MET",
    "method": "independent recompute from eval/r143_panel/*.json raw "
              "legs + the sealed audit-branch labels; never re-run "
              "(Art. 13 / 29(c))",
}

by_id["c-0241"]["status"] = "DONE"
by_id["c-0241"]["completed_by"] = (
    "builder-r143s3-b (the row-bytes check: 31 files incl. "
    "GENERATION_EVENTS.json; 30 rows, one generation each, "
    "executor_id + registered_model + events present per row)")
by_id["c-0241"]["verdict"] = {
    "acceptance": "GENERATION VERIFIED — 30/30 problem rows committed; "
                  "the auditor's scoring vs the sealed private rubrics "
                  "is THEIR act (never read; the mean>=3.3 verdict is "
                  "theirs); problem-only mapping per the events",
    "method": "count + shape recompute from committed bytes; no re-run",
}

by_id["c-0242"]["status"] = "DONE"
by_id["c-0242"]["completed_by"] = (
    "builder-r143s3-b (the acceptance recompute from the 5 problem "
    "dirs' candidate_envelope.json admission_basis bindings)")
by_id["c-0242"]["verdict"] = {
    "acceptance": "VERIFIED (diff=0) — 2/5 problems grounded (desal 2 "
                  "admissions, cathodic 1), 0 bad admissions; MATCHES "
                  "the executor's SUMMARY.json; wind>=1 typed NOT MET "
                  "(the synthesis-stage fix is the open follow-up)",
    "method": "recompute from committed envelopes; no re-run",
}

# --- 2. c-0232 -> DONE (the actual panel work) ----------------------------
c232 = by_id["c-0232"]
c232["status"] = "DONE"
c232["completed_by"] = ("builder-r142s2 (the declared takeover at "
                       "e80d601be — the intent record; the execution "
                       "bytes are theirs, the verdict typed by the "
                       "close at 32877e0cf)")
c232["verdict"] = {
    "acceptance": "MET (the DIR-3 score-8 gate) — 4 qualified judges, "
                  "2 non-agnes families, kappa 0.668, all AM47 bars",
    "verifier": "c-0241 (builder-r143s3-b, independent recompute "
                "diff=0 from the 120 raw legs)",
    "bytes": "eval/r143_panel/ + eval/r143_panel_qualification.json "
             "committed at 924754dd1/32877e0cf",
    "one_shot": "burned per Art. 7 — no re-roll; the corpus is spent",
}

# --- 3. CORR-13: the misplacement memory artifact --------------------------
reg.setdefault("corrections", []).append({
    "id": "CORR-13",
    "art": "Art. 4 (history & corrections) + Art. 5 (disclosure)",
    "at": TS,
    "by": f"{SESSION} (verifier close c-0240/c-0241/c-0242)",
    "finding": (
        "the twin's close commit 32877e0cf typed the R-CAL panel "
        "verdict onto c-0236's registry entry (r143s3-trailer-"
        "violation-c7096aa48 — a TASK claim for the trailer-violation "
        "work) while c-0232 (r143-rcal-oneshot-am47, the actual panel "
        "one_shot work) stayed OPEN with no verdict; the close's own "
        "Work-Id trailer names r143-rcal-oneshot-am47, and the driver "
        "record (eval/r143_panel_qualification.json) carries claim "
        "c-0232 — the bytes are right, the registry placement was off"
    ),
    "correction": (
        "c-0232 typed DONE here with the verdict pointer + the "
        "c-0241 verifier record (recompute diff=0); the c-0236 "
        "annotation remains as history (the verdict text stays on "
        "that entry — nothing dropped, Art. 4); future closes: type "
        "the verdict on the claim whose work_id the trailer names"
    ),
    "unaffected": (
        "the panel bytes, the qualification record and the "
        "independent recompute are unaffected; the gates were met on "
        "both records"
    ),
})

# --- counter (unchanged — the twin's ids completed, none consumed here) ----
with open(COUNTER) as f:
    cur = f.read().strip()
assert cur == "c-0243", f"counter unexpectedly {cur!r}"

with open(REG, "w") as f:
    json.dump(reg, f, ensure_ascii=True, indent=2)
    f.write("\n")

print("verifier lane: twin's c-0240/c-0241/c-0242 completed DONE "
      "(recompute executed by this lane); c-0232 -> DONE; CORR-13 appended")
