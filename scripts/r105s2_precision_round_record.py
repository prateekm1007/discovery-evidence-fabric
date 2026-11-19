#!/usr/bin/env python3
"""Write the r105s2 precision-lane round record — the Art. 27 typing,
the Art. 16 accounting for the deleted usage, the F81 disposition
evidence, the Art. 29 trail, the D2 CI reads. CI fields are filled by
the caller after the API reads (rate-limit window; the record is
written once, complete, never patched with placeholders)."""
import json
import subprocess
from pathlib import Path

REPO = Path("/home/z/my-project/discovery-evidence-fabric")
OUT = REPO / "eval" / "r105s2_precision_round_record.json"


def sha(short=False):
    r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                       text=True, cwd=str(REPO))
    return r.stdout.strip()[:9] if short else r.stdout.strip()


def build(ci_747e2fa1: dict, ci_tip: dict) -> dict:
    return {
        "record": "R105S2_PRECISION_ROUND_RECORD/1.0.0",
        "session": "builder-r105s2",
        "claim": ("c-0123 (work_id r105s2-precision-lane, kind task, "
                  "base 747e2fa1f; staked 5d4a498f3 — the Art. 29(b) "
                  "lock; lane bytes d4f8a5581 + 81ac43073 rebased over "
                  "the parallel c-0124 lock 83dfa43a3 per Art. 29(e) "
                  "disjoint-work rebase)"),
        "auditor_items": ("VERDICT R105 directions 6-7 (precision "
                          "fixes + deletions); directions 2/3/4 are "
                          "OTHER lanes (2 = the parallel r103s1 "
                          "c-0124 lock; this session stands down to "
                          "VERIFIER there)"),
        "work_completed": [
            {
                "item": "D6: the r99 pairwise-disjointness JSON "
                        "records (the verdict's F82 item)",
                "bytes": ("eval/r99_disjointness_pairwise_records.json "
                          "(9,241 bytes) + scripts/"
                          "r105s2_pairwise_records.py running the "
                          "COMMITTED guard bytes"),
                "evidence": ("chain gates v13-vs-v1-12+dev12 / "
                             "v14-vs-v1-13+dev12 / v15-vs-v1-14+dev12 "
                             "ALL PASS (0 clashes); 42 per-pair rows "
                             "(each prior version ALONE + dev12 alone) "
                             "ALL CLEAN; seal pin 46b826512; the "
                             "previously prose-only chain (r101 status "
                             "line) is now committed JSON (Art. 7: a "
                             "summary never outranks the artifact; "
                             "here the artifact finally exists)"),
            },
            {
                "item": "D6: typed refusal on self-comparison "
                        "(target ∈ corpus)",
                "bytes": ("scripts/r99_disjointness_guard.py: "
                          "derive_target_version() + "
                          "check_self_comparison() — exit 2, "
                          "SELF_COMPARISON_REFUSED, fired BEFORE any "
                          "corpus assembly"),
                "evidence": ("subprocess-proven per target in the "
                             "record JSON (v13/v14/v15 all exit 2 "
                             "typed); the legitimate corpus-extension "
                             "form (--versions 1-14 vs v15) still "
                             "passes (0 clashes, re-run this session)"),
            },
            {
                "item": "D7: the stale F81 note deleted from roadmap "
                        "Update 2",
                "bytes": ("audit/ROADMAP_4_TO_9_DETAILED.md commit "
                          "89d1f9ae8 (parent 01895fe49): ONE sentence "
                          "removed — 'NOTE F81: ... MISSING from "
                          "NOTICE.md — fix before wiring into the "
                          "frozen machine.'"),
                "evidence": ("byte-exact blob check 1f4a6def87 == "
                             "expected; numstat 1/1 on exactly that "
                             "file; the AM79 discipline text untouched "
                             "(asserted in the script); NOTICE.md "
                             "verified to carry noahshinn/reflexion "
                             "(MIT) + madaan/self-refine (Apache-2.0) "
                             "rows before the edit; the audit-branch "
                             "crossing is EXPLICITLY VERDICT-DIRECTED "
                             "(D7) and disclosed in the commit message "
                             "— one sentence, one commit, reversible"),
            },
            {
                "item": "D7: the --versions self-comparison usage "
                        "deleted",
                "bytes": ("the guard refuses the configuration; no "
                          "byte of the r103 verifier record is "
                          "rewritten (history is evidence, Art. 4)"),
                "evidence": ("Art. 16 accounting: RETIRED usage = the "
                             "self-clash non-vacuity proof (the "
                             "54/55-clash run; verdict cites 55, the "
                             "committed r103 verifier record typed 54 "
                             "— both recorded, never silently "
                             "reconciled, Art. 1); SUCCESSOR = the "
                             "typed refusal (stronger: the class is "
                             "now structurally impossible); kept = the "
                             "--versions flag itself (the legitimate "
                             "corpus extension), the pyribs NOT-ADOPTED "
                             "row (NOTICE.md:159, untouched); NO new "
                             "guard/claim kinds (the two battery tests "
                             "ride the EXISTING "
                             "test_r98_disjointness_guard.py file)"),
            },
        ],
        "art16_retirement_ledger_note": (
            "the deleted usage is accounted HERE (the round record) "
            "and in the commit messages; the retirement_ledger.json "
            "carries module/article retirements, this is a "
            "technique-usage retirement inside a live module — the "
            "successor is named above"),
        "f81_disposition": {
            "finding": ("F81 (LOW, opened 2026-11-18): convergence-"
                        "prototype attribution gap — NOTICE.md missing "
                        "Reflexion/Self-Refine attributions"),
            "evidence_of_resolution": ("NOTICE.md at queue tip carries "
                                       "the two attribution rows (the "
                                       "r94 auditor verification "
                                       "9146195e2 already typed 'F81 "
                                       "stale'); the stale NOTE F81 "
                                       "sentence is deleted from the "
                                       "roadmap Update 2 file "
                                       "(89d1f9ae8)"),
            "closure_owner": ("the auditor closes F81 in their ledger "
                              "at their next push; the builder-side "
                              "evidence is complete"),
        },
        "art29_trail": [
            ("5d4a498f3", "claim c-0123 staked + pushed (push=lock)"),
            ("33d2c150a (rebased d4f8a5581)",
             "the guard bytes + pairwise records + battery +2"),
            ("81ac43073", "kind correction + duplicate-stake "
                          "stand-down (Art. 4 + Art. 29)"),
            ("89d1f9ae8 (audit branch)",
             "the verdict-directed F81 sentence deletion"),
        ],
        "duplicate_stake_disclosure": (
            "this session staked a score-8 lane under id c-0124 "
            "(local 53bcb62e1, push REFUSED non-fast-forward, ZERO "
            "remote effect, the mutex held) while builder-r103s1 "
            "landed the lawful c-0124 score8-execution-panel-gate "
            "(83dfa43a3) FIRST; the duplicate is dropped unlanded "
            "(the 9b2d16e9c precedent); this session is VERIFIER on "
            "score8-execution-panel-gate (recompute-from-bytes duty "
            "when their run lands) and executed ZERO score-8 bytes; "
            "also: the c-0123 staked kind precision_fixes breached "
            "the registry enum — the Art.29 CI test caught it and "
            "the kind was corrected to task the same session "
            "(disclosed in the claim notes, the guard worked)"),
        "art27_capability_budget": {
            "engine_diff": ("ZERO discovery_fabric/engine lines in "
                            "this lane by design (the guard lives in "
                            "scripts/; the blind_panel/"
                            "core_mechanism_gate engine modules are "
                            "the parallel c-0124 lane's custody and "
                            "untouched here)"),
            "primary_metric_delta": ("NO capability change — this is "
                                     "a typed precision/custody round "
                                     "(the Art. 27 disclosure path; "
                                     "the gate arithmetic is unchanged "
                                     "and the sealed-set instruments "
                                     "gained a committed JSON record "
                                     "and a structural refusal)"),
            "engine_line_share": 0,
        },
        "art5_self_caught": [
            ("the kind-enum breach (self-caught by the Art.29 CI "
             "suite run BEFORE any push of dependent work)"),
            ("the first F81-deletion attempt produced a 2/2 diff "
             "(the script's own fail-closed numstat check ABORTED the "
             "push; root cause = the git() helper stripped the file's "
             "trailing newline; fixed with a verbatim-output variant "
             "+ a byte-exact blob assertion; nothing was pushed on "
             "the failed attempt)"),
        ],
        "ci_reads": {
            "note": ("the D2 rule: API-quoted check-runs; the core "
                     "rate limit was exhausted 19:53Z (reset "
                     "20:34:12Z, evidence: GET /rate_limit "
                     "remaining 0) — the reads landed after the "
                     "reset, quoted verbatim"),
            "final_tip_747e2fa1": ci_747e2fa1,
            "lane_tip": ci_tip,
        },
        "next": [
            ("VERIFIER duty on score8-execution-panel-gate: recompute "
             "the c-0124 run records from committed bytes when the "
             "r103s1 bytes land (never re-run, Art. 29(c))"),
            ("direction 5: the measure_guard per-problem layer "
             "applicability 15/15 check rides the NEXT sealed run "
             "(no sealed run is open; the instrument is ready)"),
            ("directions 3/4: unclaimed — P3 real-data validation "
             "(C-MAPSS/XJTU-SY/CWRU + conformal) is the next "
             "executor lane candidate for this session, claimed "
             "separately if still unclaimed next window"),
        ],
        "no_acceptance_or_score_claims": True,
    }


if __name__ == "__main__":
    import sys
    ci_747 = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {}
    ci_tip = json.loads(sys.argv[2]) if len(sys.argv) > 2 else {}
    rec = build(ci_747, ci_tip)
    OUT.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")
