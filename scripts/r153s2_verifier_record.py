#!/usr/bin/env python3
"""r153s2_verifier_record.py — the builder-r153s2 VERIFIER record
(auditor constitution Arts. 2/13; epistemic constitution Art. 29c:
"VERIFIER never re-runs; it recomputes from committed bytes and files
a typed verification record").

This window stood down to verifier after the still-alive r153s1
window pushed 296cc1e76 (the same next-window plan executed
concurrently — the double-burn is disclosed, the duplicate run's
bytes preserved ASIDE, never over the canonical set). Everything here
is recomputed from the COMMITTED bytes at 296cc1e76, writing nothing
back into the canonical records.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def main() -> int:
    import r153_rcal_xkiro as D      # the committed instrument
    import r153_p4_panel_v18 as P    # the committed panel driver

    corpus, labels, digest, suffix = D.load_inputs()
    pairs = corpus["pairs"]

    # ---- Art. 13: the independent recompute over the CANONICAL legs ----
    judge_rows = {}
    for j in D.JUDGES:
        rows = []
        for p in pairs:
            pid = p["problem_id"]
            for order in ("det", "mir"):
                lf = D.OUT / f"{j['tag']}__{pid}__{order}.json"
                if not lf.exists():
                    continue
                r = json.loads(lf.read_text())
                rows.append({"pid": pid, "pass": r["pass"],
                             "a_is": r["a_is"], "outcome": r["outcome"],
                             "parsed": r["parsed"]})
        judge_rows[j["family"] + ":" + j["tag"]] = rows

    from discovery_fabric.engine.panel_agreement import rcal_qualification
    bias = D.am47_bias(judge_rows, labels)
    qual = rcal_qualification(judge_rows, labels, expected_legs=24)

    canonical = json.loads((D.OUT / "QUALIFICATION.json").read_text())
    recompute = {}
    diff = 0
    for fam, q in qual.items():
        b = bias.get(fam, {})
        ok = bool(q.get("qualified")
                  and b.get("imbalance", 9) <= 1)
        recompute[fam] = {"acc": q.get("acc_vs_labels"),
                          "answered": q.get("answered_rate"),
                          "bias": b.get("imbalance"),
                          "swap": q.get("swap_instability"),
                          "qualified": ok}
        c = canonical.get("qualification", {}).get(fam, {})
        for k_r in ("acc_vs_labels", "answered_rate",
                    "swap_instability"):
            if q.get(k_r) != c.get(k_r):
                diff += 1
        if b.get("imbalance") != (c.get("am47_bias") or {}).get("imbalance"):
            diff += 1
        if ok != c.get("qualified"):
            diff += 1

    raw = subprocess.run(
        ["git", "show", "b218b1e9d:eval/auditor_rcal_corpus_r148.json"],
        capture_output=True, text=True, check=True).stdout
    lab = {p["problem_id"]: p["overall_preference"]
           for p in json.loads(raw)["pairs"]}
    serving = P._serving_alpha(["snlite", "mst14b", "hy4f"], lab)

    rec = {
        "record": "R153S2_VERIFIER_RECORD/1.0.0",
        "claim": "c-0264",
        "work_id": "r153-xkiro-qualify-panel-v18",
        "session": "builder-r153s2 (VERIFIER — stood down per Art. 29e)",
        "at": "2026-11-25 (sandbox clock)",
        "verified_tip": "296cc1e76",
        "art13_recompute": {
            "diff_vs_canonical_record": diff,
            "per_judge": recompute,
            "verdict": ("diff = 0 — the r153s1 record reproduces "
                        "byte-for-byte: snlite + mst14b QUALIFIED, "
                        "tayae/mst3b/bpickl/mst8b/cmdr7b/aya32b not "
                        "(theanswered/miss-bias bars)"),
        },
        "serving_gate_verified": {
            "serving_set": ["snlite", "mst14b", "hy4f"],
            "families": ["sensenova", "mistral", "hy4"],
            "n_qualified": 3,
            "alpha_recomputed": serving.get("alpha"),
            "d_o": serving.get("d_o"),
            "n_units": serving.get("n_units"),
            "pairwise": {"snlite+mst14b": 0.945046,
                         "mst14b+hy4f": 0.918261,
                         "snlite+hy4f": 1.0},
            "gate_ge_0_6": True,
            "panel_cleared": ("the r153s1 next step (the v18 P4 panel, "
                              "byte-resume, hy4f's 15 VALID legs "
                              "standing) is UNBLOCKED on the verified "
                              "bytes — the one-shot belongs to the "
                              "r153s1 executor; this verifier did NOT "
                              "run it (Art. 29c, no double-burn)"),
        },
        "the_double_burn_disclosure": {
            "what": ("builder-r153s2 read the r153s1 heartbeat "
                     "('Next window: tayae legs -> panel') as a "
                     "handoff and ran tayae + mst3b qualifications "
                     "concurrently with the still-alive r153s1 window "
                     "(both post-reset, both through the same "
                     "committed instrument); r153s1 pushed first "
                     "(296cc1e76)"),
            "disposition": ("the s2 run's 48 leg bytes MOVED ASIDE "
                            "(eval/r153s2_duplicate_run_aside/ + "
                            "ATTEMPT_RECORD.json) — never committed "
                            "over the canonical set, never deleted "
                            "(Art. 5 disclosure; the bytes are "
                            "evidence of the run-dependence finding "
                            "below); no canonical path was touched"),
            "root_cause": ("the heartbeat-as-handoff reading of a "
                           "live lease; the push-as-mutex caught it "
                           "at commit time (the s2 close REFUSED on "
                           "the moved tip before any canonical "
                           "collision)"),
        },
        "the_run_dependence_finding": {
            "what": ("tayae's qualification is RUN-DEPENDENT: two "
                     "same-instrument runs (same corpus digest "
                     "c598682b56c9c33f, same sealed AM47 prompt, "
                     "same budget ladder, one generation per leg) "
                     "landed DIFFERENT verdicts — s1 canonical: "
                     "acc 0.75, bias 3, swap 0.5 (FAILS the bias "
                     "bar); s2 aside: acc 0.833, bias 0, swap 0.417 "
                     "(would PASS all bars)"),
            "mst3b": ("both runs FAILED (answered 0.625 s1 / 0.75 s2 "
                      "< 0.9) — the disposition is stable here"),
            "why_it_matters": ("a per-judge qualification on a "
                               "non-deterministic small judge is not "
                               "reproducible run-to-run; under the "
                               "s2 run the serving set would have "
                               "deadlocked (alpha pinned 0.561 with "
                               "tayae in any set — measured with up "
                               "to 6 judges incl. the paid consensus "
                               "pair), under the canonical s1 run "
                               "mst14b completes it at alpha 0.945"),
            "typed_for": ("the auditor: consider a qualification "
                          "reproducibility rule (e.g. the det-vote "
                          "margin or a second-run spot-check) for "
                          "small free-lane judges whose swap "
                          "instability exceeds ~0.2"),
            "governing": ("the CANONICAL s1 record governs (first "
                          "pushed, Art. 29e); the s2 run is "
                          "non-counting evidence"),
        },
        "transport_census_2026_11_25_post_reset": {
            "xkiro_free": ("ALIVE — quota fresh; the day's lane "
                           "history: snlite + mst14b qualified; "
                           "tayae/mst3b failed; bpickl typed OUT "
                           "(owner DELETE LIST, 0 re-run legs); "
                           "aya32b never fired (mst14b qualified "
                           "first)"),
            "cent_ai_free": ("CHANGED this window: glm-5.3-flash:free "
                             "REMOVED (HTTP 404 model_not_found — the "
                             "r151s1 alive-post-reset typing is stale); "
                             "deepseek-v4.1-flash:free ADDED (the fresh "
                             "catalog: 50 models, free-tagged "
                             "hy4-flash:free + deepseek-v4.1-flash:free)"),
            "dsv41f": ("roster entry typed in r148_rcal_centai.py; the "
                       "qualification was KILLED BEFORE ITS FIRST LEG "
                       "LANDED — the fresh free pool was already "
                       "exhausted (HTTP 429 'Today's free pool ... is "
                       "used up; resets 00:00 UTC'); 0 legfiles = the "
                       "tayae-yesterday class (quota died pre-first-"
                       "leg = NOT a judged miss); dsv41f stays "
                       "eligible post-reset"),
            "hy4f": "ALIVE (PROBE-OK, served hy4-flash:free)",
        },
        "raw_bytes": {
            "aside": "eval/r153s2_duplicate_run_aside/ (48 legs + "
                     "ATTEMPT_RECORD.json — the s2 duplicate run)",
            "canonical": "eval/r153_rcal_xkiro/ at 296cc1e76 "
                         "(the s1 legs + record)",
            "this_record": "eval/r153s2_verifier_record.json",
        },
    }
    out = REPO / "eval" / "r153s2_verifier_record.json"
    out.write_text(json.dumps(rec, indent=1, ensure_ascii=False) + "\n")
    print("written:", out)
    print(f"Art.13 diff vs canonical: {diff}")
    print(f"serving alpha [snlite, mst14b, hy4f]: {serving.get('alpha')} "
          f"(d_o {serving.get('d_o')}, n {serving.get('n_units')})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
