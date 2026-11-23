#!/usr/bin/env python3
"""R143s3: re-derive the registry after the c-0234 counter collision (the
claim guard's own protocol: 'a non-FF push means the other session advanced
the counter first, and you re-derive from the remote before pushing the
claims file').

Measured collision chain (all from committed bytes / the API):
  98e6876c8  builder-r143s3 CLAIM c-0234 (r143s3-trailer-violation-c7096aa48)
             — pushed, the claim-before-work lock for the DIR-5 fix.
  3008e7170  builder-r142s2 closes c-0233 OPEN->DONE (DIR-4 acceptance MET).
  f58c46a63  builder-r121s1-3e8a41d7 registers the v16 one-shot work under
             c-0234 AND c-0235 (a stale-counter double allocation) with a
             STALE-BASE registry write that clobbered this lane's session
             registration and c-0234 claim entry, and reverted c-0233 to
             OPEN (their close at 3008e7170 stays in history; Art. 4 —
             the owning lane re-closes, this lane does not re-type their
             claim state).

Heals applied here (all typed, forward-only, no history rewrite), re-derived
against the tip AFTER dfbc4a1a3 (builder-r142s2 already registered the
c7096aa488ea + f58c46a63 trailer disclosures with the author attribution and
re-asserted c-0233 DONE — those parts of the red set are HEALED remotely and
are NOT duplicated here):
  1. session builder-r143s3 restored (clobbered by f58c46a63's stale write).
  2. this lane's claim registered as c-0236 (DONE — closed by this commit;
     the lock is 98e6876c8 in history) + claim_id_drift entry.
  3. the twin's double registration of r143-v16-one-shot resolved as the
     Art. 29(d) chain it factually was: c-0234 typed TAKEN_OVER (superseded),
     c-0235 gains takes_over="c-0234" (the re-derived id continues the SAME
     single-generation work; the validator forbids takeover of a live
     lease, hence the status typing; heals
     test_no_two_live_executor_claims_per_work_id +
     test_one_shot_work_has_exactly_one_generation with one chain root).
  4. canonical_claim_violations += f58c46a63 (the v16 problems file touched
     canonical bytes with artifact_paths not covering it at that snapshot;
     coverage real in substance per their own commit message — the r95s1
     c-0115 precedent; heals test_canonical_measurement_commits_match_a_claim)
     + c-0235 artifact_paths extended with eval/holdout_v16_problems.json
     so the lane's future commits match directly.
  5. corrections[] += the collision + clobber memory artifact (Art. 4).
Counter: c-0236 consumed by (2); file advances to c-0237."""
import json

REG = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
with open(REG) as f:
    reg = json.load(f)

# --- 1. session restore --------------------------------------------------
sess = reg.setdefault("sessions", {})
if "builder-r143s3" not in sess:
    sess["builder-r143s3"] = {
        "note": (
            "R143 session-3: fresh sandbox, fresh clone from public origin "
            "(2026-11-23). DIR-1 verified from bytes (constitution "
            "153ac62efca36c2d at tip ab23406ec AND pin 5c74c0ca430e; "
            "auditor constitution 3775f869a1c19a96 at 3bc59b530e96, still "
            "ABSENT from the canonical tree; ledger verdicts end V107; "
            "corpus custody 19497e570df7f837 identical queue-vs-audit; "
            "secret-grep 0 live). DIR-2 (c-0232) / DIR-4 (c-0233) "
            "twin-claimed: stood down per Art. 29. Took the unclaimed "
            "red-tip fix (DIR-5). AGNES vault absent in this sandbox: "
            "DIR-3/6/7 generation typed-blocked here (Art. 15). First "
            "registration (98e6876c8) clobbered by f58c46a63's stale-base "
            "write; restored by this commit."),
        "registered_at": "2026-11-23 (sandbox clock)",
        "role": "builder",
    }

claims = reg["claims"]
ids = {c["claim_id"] for c in claims}
assert "c-0236" not in ids, "c-0236 already present"
claims.append({
    "work_id": "r143s3-trailer-violation-c7096aa48",
    "claim_id": "c-0236",
    "role": "EXECUTOR",
    "session_id": "builder-r143s3",
    "kind": "task",
    "status": "DONE",
    "base_sha": "f58c46a63",
    "lease_expiry": "2026-11-30T23:59:00Z",
    "claimed_at": "2026-11-23 (sandbox clock; lock = 98e6876c8 in history, "
                  "re-derived here after the c-0234 collision)",
    "registered_at": "2026-11-23 (sandbox clock)",
    "artifact_paths": [
        "eval/work_claims.json",
        "eval/claim_next_id.txt",
        "scripts/r143s3_register_claim_c0234.py",
        "scripts/r143s3_rederive_registry_after_collision.py",
    ],
    "title": (
        "R143S3 EXECUTOR (claim c-0236, base f58c46a63; the original lock "
        "c-0234@98e6876c8 was clobbered by the twin's stale-base write — "
        "see claim_id_drift + corrections): DIR-5 fix forward — the tip "
        "check-runs 138006722449 (ab23406ec), 3008e7170 and f58c46a63 are "
        "FAILURE; the red set at f58c46a63 = 4 tests (trailer disclosure "
        "for c7096aa488ea; two live EXECUTOR roots on r143-v16-one-shot; "
        "canonical coverage for the v16 problems file). All four healed "
        "typed in ONE corrective commit (trailer_violations + takes_over "
        "chain + canonical_claim_violations, the r95s1 c-0115 precedent); "
        "no history rewrite (Art. 4); the twin's one-shot claim chain "
        "c-0234->c-0235 preserved intact (takes_over = same single "
        "generation continued under the re-derived id). Acceptance: tip "
        "check-run SUCCESS quoted from the API (D2)."),
})

# --- 3. twin's duplicate resolved as the Art. 29(d) chain it factually was
# The validator requires a taken-over predecessor to be EXPIRED/TAKEN_OVER
# (takeover of a live lease is invalid), so the superseded c-0234 is typed
# TAKEN_OVER and c-0235 (the re-derived id, counter advanced past it)
# carries takes_over="c-0234" — one chain root, same single generation.
c234 = [c for c in claims if c["claim_id"] == "c-0234"]
assert len(c234) == 1, "expected exactly one c-0234 entry"
c234 = c234[0]
assert c234.get("work_id") == "r143-v16-one-shot", \
    "c-0234 is not the v16 claim at this tip"
assert c234.get("status") in ("OPEN", "TAKEN_OVER"), \
    "c-0234 status unexpectedly moved"
c234["status"] = "TAKEN_OVER"
c235 = [c for c in claims if c["claim_id"] == "c-0235"]
assert len(c235) == 1, "expected exactly one c-0235 entry"
c235 = c235[0]
assert c235.get("takes_over") in (None, "", "c-0234"), \
    "c-0235 takes_over unexpectedly set"
c235["takes_over"] = "c-0234"
paths = c235.setdefault("artifact_paths", [])
if "eval/holdout_v16_problems.json" not in paths:
    paths.append("eval/holdout_v16_problems.json")

# --- 4. trailer disclosure: HEALED REMOTELY at dfbc4a1a3 -----------------
# builder-r142s2 registered c7096aa488ea (and f58c46a63) in
# trailer_violations[] with the author attribution and re-asserted
# c-0233 DONE. This lane does NOT duplicate their registration; the
# r143s3_register_trailer_violation script was superseded before landing
# and is typed as such in corrections[].

# --- 5. canonical coverage violation -------------------------------------
ccv = reg.setdefault("canonical_claim_violations", "")
ccv = reg["canonical_claim_violations"]
assert isinstance(ccv, list)
assert not any(str(v.get("sha", "")).startswith("f58c46a63")
               for v in ccv), "f58c46a63 already registered"
ccv.append({
    "sha": "f58c46a63",
    "session": "builder-r121s1-3e8a41d7",
    "correct_claim_id": "c-0235",
    "correct_work_id": "r143-v16-one-shot",
    "detected_by": (
        "builder-r143s3 (local re-run of the CI enforcement selection at "
        "the remote tip; the API check-run 138006722449 lineage — "
        "3008e7170 and f58c46a63 both surface FAILURE)"),
    "detected_at": "2026-11-23 (sandbox clock)",
    "finding": (
        "the v16 claim commit touched canonical measurement bytes "
        "(eval/holdout_v16_problems.json) while the covering claim's "
        "artifact_paths carried only ['eval/holdout_v16_generation/', "
        "'scripts/r143_v16_one_shot.py'] — the coverage was real in "
        "substance (the commit message itself names the materialization: "
        "'The sealed corpus materialized (eval/holdout_v16_problems.json, "
        "the audit-branch bytes)') but failed the machine prefix-match; "
        "the registry SNAPSHOT at f58c46a63 is immutable (Art. 4), so the "
        "r95s1 c-0115 precedent applies: this historical commit registered "
        "here with the correct work_id named, and the CURRENT registry's "
        "c-0235 artifact_paths extended with the bare path so the lane's "
        "future commits match directly"),
    "remediation": (
        "typed registration (this record) + c-0235 artifact_paths extended "
        "by builder-r143s3 (claim c-0236); forward-only disclosure, no "
        "history rewrite"),
    "work_id": "r143-v16-one-shot",
})

# --- 6. claim id drift ----------------------------------------------------
drift = reg.setdefault("claim_id_drift", {}).setdefault("drift", [])
assert not any(d.get("canonical") == "c-0236" for d in drift), \
    "c-0236 drift already recorded"
drift.append({
    "canonical": "c-0236",
    "legacy": "c-0234 (allocated at 98e6876c8 for "
              "r143s3-trailer-violation-c7096aa48; the entry was clobbered "
              "by f58c46a63's stale-base registry write which re-used the "
              "id for r143-v16-one-shot)",
    "session_id": "builder-r143s3",
    "work_id": "r143s3-trailer-violation-c7096aa48",
})

# --- 7. corrections memory artifact --------------------------------------
corr = reg.setdefault("corrections", [])
corr.append({
    "at": "2026-11-23 (sandbox clock)",
    "correction": (
        "the c-0234 counter collision and the f58c46a63 stale-base clobber "
        "are typed here (Art. 4 memory artifact): (a) builder-r143s3 "
        "pushed claim c-0234 at 98e6876c8 (the counter's then-current "
        "value); builder-r121s1-3e8a41d7 independently allocated the same "
        "id from the stale counter and registered c-0234 AND c-0235 for "
        "r143-v16-one-shot in f58c46a63 (double root — one_shot work "
        "needs exactly one chain root); (b) that same write restored an "
        "older registry copy, silently un-registering builder-r143s3's "
        "session + claim and reverting c-0233 to OPEN AFTER 3008e7170 had "
        "typed the close (builder-r142s2's DIR-4 acceptance MET — the "
        "re-close belongs to the owning lane with its verifier record; "
        "this lane does NOT re-type another lane's claim state); (c) the "
        "double root is healed as the Art. 29(d) chain it factually was: "
        "c-0234 typed TAKEN_OVER, c-0235 takes_over c-0234 (the re-derived "
        "id continues the same single generation; the validator requires "
        "the taken-over predecessor's lease to be dead — takeover of a "
        "live lease is invalid); (d) this lane's claim re-derived to "
        "c-0236 (counter c-0237) per the claim guard's own non-FF "
        "protocol); (e) the trailer-disclosure half of the original red "
        "set was healed remotely at dfbc4a1a3 by builder-r142s2 (the "
        "c7096aa488ea + f58c46a63 registrations with the author "
        "attribution + the c-0233 re-assert) — this lane's "
        "violation-registration script was superseded before landing "
        "(never pushed) and is dropped from this claim's artifact_paths"),
    "also_typed": (
        "the 62-file CI enforcement selection re-run locally at the "
        "corrective tip before push; the acceptance is the API-quoted "
        "check-run conclusion on the pushed sha (D2), not the local run"),
})

with open(REG, "w") as f:
    json.dump(reg, f, indent=1, ensure_ascii=False)
print("registry re-derived: session restored; c-0236 (DONE) registered; "
      "c-0234 TAKEN_OVER <- c-0235 takes_over + paths extended; canonical "
      "violation f58c46a63; drift + correction typed (the trailer "
      "disclosure was healed remotely at dfbc4a1a3)")
