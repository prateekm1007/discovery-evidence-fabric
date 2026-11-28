#!/usr/bin/env python3
"""R146s1-b: heal the R146S1 tip reds (two Art. 29 / F36 defect classes,
both from the twin's strengthened-sealed-run commits; forward-only, no
history rewrite, Art. 4).

Measured state at tip d87a64758 (CI run 138318767499 surface | completed
| failure, API-quoted; both failures reproduce in the local battery):

  1e9793a04 (builder-r146s1, 'R146S1 DEV-VERIFY') — the commit message
             carries a MALFORMED DOUBLE TRAILER BLOCK (two 'Session:'
             and two 'Work-Id:' lines separated by a blank line); git's
             trailer parser stops at the blank line and misses Session:
             entirely -> test_post_adoption_commits_carry_... RED.
             The attribution is unambiguous (both blocks name
             builder-r146s1 / r146-v17-s2-strength). Registered in
             trailer_violations[] per F36.

  170be8ab7 (builder-r145s1, 'the STRENGTHENED sealed one-shot') —
             commits the canonical bytes eval/holdout_v17_strengthened_
             generation/ (31 files) under Work-Id r145-generation-
             strength, but NO registry claim covers that work_id + path
             set (c-0250 covers r146-v17-s2-strength with the
             eval/holdout_v17_s2_* paths; the r145 lane's claims ended
             at c-0249). Registered in canonical_claim_violations[] (the
             r95s1 c-0115 precedent) + the covering claim named.

Heals (the local battery surfaced a second instance of each class):
  1. trailer_violations[] += 1e9793a04 AND c9992c04e (both carry the
     same malformed double trailer block; attribution unambiguous).
  2. canonical_claim_violations[] += 170be8ab7 (31 strengthened-run
     files, no covering claim) AND 1e9793a04 (5 dev files — coverage
     REAL under c-0250's paths, but the broken trailer pairing).
  3. c-0250 artifact_paths += eval/holdout_v17_strengthened_generation/
     + eval/holdout_v17_s2_dev/ extension, so the strengthened run
     matches a live claim directly going forward.
  4. This lane's chain-maintenance claim c-0251 (counter -> c-0252).

Session note: builder-r146s1-b is a fresh sandbox context continuing
the r143s3-b lineage (same builder lane family, second R146 window).
"""
import json

REG = "/home/z/my-project/discovery-evidence-fabric/eval/work_claims.json"
COUNTER = "/home/z/my-project/discovery-evidence-fabric/eval/claim_next_id.txt"

with open(REG) as f:
    reg = json.load(f)
by_id = {c["claim_id"]: c for c in reg["claims"]}

# --- sanity gates ---------------------------------------------------------
assert by_id["c-0250"]["status"] == "OPEN", "c-0250 unexpectedly not OPEN"
assert by_id["c-0250"]["session_id"] == "builder-r146s1"
assert "eval/holdout_v17_strengthened_generation/" not in \
    by_id["c-0250"]["artifact_paths"], "paths already extended"
tv_shas = [v.get("sha", "") for v in reg.get("trailer_violations", [])]
assert not any(s.startswith("1e9793a04") for s in tv_shas), "already registered"
assert not any(s.startswith("c9992c04e") for s in tv_shas), "already registered"
cv_shas = [v.get("sha", "") for v in reg.get("canonical_claim_violations", [])]
assert not any(s.startswith("170be8ab7") for s in cv_shas), "already registered"
assert not any(s.startswith("1e9793a04") for s in cv_shas), "already registered"

TS = "2026-11-24 (sandbox clock)"
SESSION = "builder-r146s1-b"

# --- 1. trailer_violations[] += 1e9793a04 + c9992c04e ----------------------
for sha, what in (("1e9793a044c1", "the dev-verify commit"),
                  ("c9992c04e1c2", "the strength-lane setup commit")):
    reg.setdefault("trailer_violations", []).append({
        "violation": "missing Session:/Work-Id: trailers (malformed double "
                     "trailer block — a blank line splits the block and "
                     "git's parser misses the first Session: line)",
        "session_attribution": "builder-r146s1",
        "work_id_attribution": f"r146-v17-s2-strength (the c-0250 lane's {what})",
        "registered_by": f"{SESSION} (the R146 tip-red heal, claim c-0251)",
        "typed": "the commit message carries TWO trailer blocks (Session:/"
                 "Work-Id: twice, separated by a blank line); the parser "
                 "reads only the block after the blank line. Both blocks "
                 "name builder-r146s1 / r146-v17-s2-strength — attribution "
                 "unambiguous. Registered per F36 rather than rewriting "
                 "landed history; the fix is the single-block convention "
                 "(typed in corrections[])",
        "at": TS,
        "sha": sha,
    })

# --- 2. canonical_claim_violations[] += 170be8ab7 + 1e9793a04 ---------------
reg.setdefault("canonical_claim_violations", []).append({
    "sha": "170be8ab77a0",
    "session": "builder-r145s1",
    "work_id": "r145-generation-strength",
    "violation": "the strengthened sealed one-shot commit carries the "
                 "31 canonical files under eval/holdout_v17_"
                 "strengthened_generation/ with Work-Id r145-generation-"
                 "strength, but no registry claim covers that work_id + "
                 "path set (the r145 lane's claims ended at c-0249; "
                 "c-0250 covers r146-v17-s2-strength with the "
                 "eval/holdout_v17_s2_* paths)",
    "remediation": "c-0250 artifact_paths extended with eval/holdout_"
                   "v17_strengthened_generation/ so the strengthened "
                   "run matches a live EXECUTOR claim going forward "
                   "(the r95s1 c-0115 precedent — coverage real in "
                   "substance per the commit message, absent in "
                   "registry form at the immutable snapshot)",
    "at": TS,
})
reg.setdefault("canonical_claim_violations", []).append({
    "sha": "1e9793a044c1",
    "session": "builder-r146s1",
    "work_id": "r146-v17-s2-strength",
    "violation": "the dev-verify commit carries the 5 canonical files "
                 "under eval/holdout_v17_s2_dev/ with a trailer block "
                 "the parser only half-reads (the malformed double "
                 "block), so the canonical-match step cannot pair the "
                 "bytes with the c-0250 claim that covers them",
    "remediation": "c-0250 artifact_paths already lists eval/holdout_"
                   "v17_s2_dev/ — the coverage is REAL, the trailer "
                   "format broke the pairing; registered here F36-"
                   "style (forward-only) alongside the trailer-"
                   "violation entry; the single-block convention typed "
                   "in corrections[]",
    "at": TS,
})

# --- 3. c-0250 artifact_paths extension ------------------------------------
by_id["c-0250"]["artifact_paths"] = sorted(
    set(by_id["c-0250"]["artifact_paths"]) | {
        "eval/holdout_v17_strengthened_generation/"})
by_id["c-0250"]["paths_note"] = (
    "extended by the c-0251 chain-maintenance heal: the strengthened "
    "sealed run (170be8ab7) wrote eval/holdout_v17_strengthened_"
    "generation/ under the r145-generation-strength Work-Id; the lane "
    "continuation c-0250 (the same builder-r145s1/146s1 lineage, the "
    "strengthened-instrument work) now claims the path directly — "
    "one canonical dir per the Art. 16/29(e) discipline"
)

# --- 4. this lane's chain-maintenance claim (c-0251) ------------------------
reg.setdefault("sessions", {})[SESSION] = {
    "claimed_at": TS,
    "role": "builder",
    "note": (
        "R146 second window: fresh sandbox continuation of the "
        "builder-r143s3-b lineage (constitutions full-read verified at "
        "the DIR-1 pins — EPISTEMIC v3.3.0 153ac62efca36c2d @"
        "e1f861a8fdf3, AUDITOR v1.3.0 3775f869a1c19a96 @6ab8ee17aa98, "
        "ledger V112). Executor of the R146S1 tip-red heal (the F36 "
        "classes: the malformed double trailer block + the canonical "
        "bytes outside the covering claim's paths)."
    ),
}
reg["claims"].append({
    "work_id": "r146s1-tip-red-heal",
    "claim_id": "c-0251",
    "role": "EXECUTOR",
    "session_id": SESSION,
    "kind": "task",
    "status": "DONE",
    "base_sha": "d87a64758",
    "lease_expiry": "2026-12-01T23:59:00Z",
    "claimed_at": TS,
    "registered_at": TS,
    "artifact_paths": [
        "eval/work_claims.json",
        "eval/claim_next_id.txt",
        "scripts/r146s1b_tip_red_heal.py"
    ],
    "title": (
        "R146S1-B EXECUTOR (claim c-0251, base d87a64758): the R146 tip-"
        "red heal — CI run 138318767499 (surface | completed | failure, "
        "API-quoted) fails the Art. 29 tests, all F36 classes from the "
        "twin's strengthened-run commits: (1) the malformed DOUBLE "
        "trailer block on 1e9793a04 AND c9992c04e (blank line splits "
        "it; the parser misses Session:) — both registered in "
        "trailer_violations[] with the unambiguous attribution; (2) "
        "170be8ab7's 31 canonical files "
        "under eval/holdout_v17_strengthened_generation/ with no "
        "covering claim (Work-Id r145-generation-strength, no claim "
        "matches) and 1e9793a04's 5 dev files (coverage real under "
        "c-0250, pairing broken by the trailer defect) — registered in "
        "canonical_claim_violations[] + c-0250 artifact_paths extended "
        "so the strengthened run matches a live claim. No history "
        "rewrite (Art. 4); the single-trailer-block "
        "convention typed in corrections[]. Local pre-push: "
        "test_article29 9/9 + the full CI selection green on this "
        "exact tree. Acceptance: tip check-run SUCCESS quoted from the "
        "API (D2)."
    ),
    "notes": "Registry bytes only; no measurement re-run; the "
             "strengthened run's scoring remains the auditor's act.",
})
reg.setdefault("corrections", []).append({
    "id": "CORR-14",
    "art": "Art. 4 (history & corrections) + Art. 5 (disclosure)",
    "at": TS,
    "by": f"{SESSION} (chain maintenance c-0251)",
    "finding": (
        "the R146S1 window's two tip-reds are both commit-formatting "
        "defects on real, substantive work: 1e9793a04 (the dev-verify) "
        "carries a malformed double trailer block; 170be8ab7 (the "
        "strengthened sealed one-shot) wrote a canonical dir outside "
        "any claim's artifact_paths"
    ),
    "correction": (
        "both registered F36-style (forward-only); c-0250 extended to "
        "cover the strengthened dir; the convention going forward: ONE "
        "trailer block per commit (never a blank line inside it), and "
        "a canonical dir is added to the covering claim's "
        "artifact_paths IN THE SAME WINDOW that first writes it"
    ),
    "unaffected": (
        "the strengthened run bytes, the dev-verify results (3/4 gate-"
        "strong), and the quant contract evidence are unaffected — "
        "this heal is registry/format only"
    ),
})

# --- counter ----------------------------------------------------------------
with open(COUNTER) as f:
    cur = f.read().strip()
assert cur == "c-0251", f"counter unexpectedly {cur!r}"
with open(COUNTER, "w") as f:
    f.write("c-0252\n")

with open(REG, "w") as f:
    json.dump(reg, f, ensure_ascii=True, indent=2)
    f.write("\n")

print("healed: trailer_violations += 1e9793a04+c9992c04e; "
      "canonical_claim_violations += 170be8ab7+1e9793a04; "
      "c-0250 paths += holdout_v17_strengthened_generation/; "
      "c-0251 registered; counter -> c-0252")
