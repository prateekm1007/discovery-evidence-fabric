#!/usr/bin/env python3
"""r136s2_share_reconcile.py — the Art.27 engine-share reconciliation
(work id r136s2-share-reconcile, responds to R136 directions dir 5).

Recomputes the engine-line share for R133/R134/R135 from the actual
diffs (git diff --numstat base..close) under BOTH formulas:
  old (the committed test's):       share = (ea+eb) / (ea+eb+ca+cb)
      — CODE_PATHS contains engine/, so ca,cb ALREADY include the
      engine lines and tot double-counts them (the audit's claim b);
  corrected (the twin's, adopted):  share = (ea+eb) / (ca+cb)
      — the engine counted exactly once.

Then hunts the R135 record's hand-typed 23.4% across candidate
formulas/ranges and types which (if any) reproduces it.

Output: eval/r136s2_share_reconciliation.json. Digests/numbers only;
no claim about any score.
"""
from __future__ import annotations
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ENGINE_PATHS = ["discovery_fabric/engine/"]
CODE_PATHS = ["discovery_fabric/engine/", "scripts/", "tests/",
              "requirements.txt"]

ROUNDS = [
    # closes = the LANDED round-close commits on queue/dev12_r7 (the
    # r133s1/r135s1 status records' pushed_sha values are the CLAIM /
    # pre-rebase pushes: 39c29c0d5 is the R133 claim commit on-queue;
    # 7a592f621 is unreachable server-side — rewritten by the R135
    # rebase disclosed in 908c5d446 — so the governing recompute runs
    # base..landed-close, per the audit basis "CI green on 2d1170f06,
    # 1613e109a and the three before them")
    {"round": "R133", "base": "697ac00ba", "close": "c76a26a59",
     "close_note": "R133 window-final push (the D2 amendment; base..final-push "
                   "reproduces the recorded 36.5 and the twin's 57.6 exactly)",
     "recorded_old": 36.5, "corrected_twin": 57.6},
    {"round": "R134", "base": "c76a26a59", "close": "3e3a0a00b",
     "close_note": "landed R134 ROUND-CLOSE",
     "recorded_old": 18.9, "corrected_twin": 23.3},
    {"round": "R135", "base": "3e3a0a00b", "close": "1613e109a",
     "close_note": "landed R135 ROUND-CLOSE (recorded pushed_sha "
                   "7a592f621 unreachable: pre-rebase, rewritten)",
     "recorded_old": 14.9, "corrected_twin": 17.5},
]


def rev(sha: str) -> str:
    out = subprocess.run(["git", "rev-parse", sha], cwd=REPO,
                         capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"unresolvable sha {sha}")
    return out.stdout.strip()


def numstat(base: str, head: str, paths) -> tuple[int, int]:
    out = subprocess.run(
        ["git", "diff", "--numstat", base, head, "--"] + paths,
        capture_output=True, text=True, cwd=REPO).stdout
    a = b = 0
    for line in out.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) == 3:
            try:
                a += int(parts[0])
                b += int(parts[1])
            except ValueError:
                pass
    return a, b


def pct(x: float) -> float:
    return round(100.0 * x, 1)


def main() -> int:
    results = []
    for r in ROUNDS:
        base, close = rev(r["base"]), rev(r["close"])
        ea, eb = numstat(base, close, ENGINE_PATHS)
        ca, cb = numstat(base, close, CODE_PATHS)
        old_tot = ea + eb + ca + cb
        corr_tot = ca + cb
        row = {
            "round": r["round"], "base": base[:9], "close": close[:9],
            "close_note": r["close_note"],
            "engine_added": ea, "engine_removed": eb,
            "code_added": ca, "code_removed": cb,
            "old_formula_share": pct((ea + eb) / old_tot) if old_tot else None,
            "corrected_share": pct((ea + eb) / corr_tot) if corr_tot else None,
            "recorded_old_formula": r["recorded_old"],
            "twin_corrected": r["corrected_twin"],
            "matches_twin_corrected": (
                abs(pct((ea + eb) / corr_tot) - r["corrected_twin"]) <= 0.15
                if corr_tot else False),
            "matches_recorded_old": (
                abs(pct((ea + eb) / old_tot) - r["recorded_old"]) <= 0.15
                if old_tot else False),
        }
        results.append(row)

    # --- the 23.4% hunt (R135 window) ---
    r135 = ROUNDS[2]
    base, close = rev(r135["base"]), rev(r135["close"])
    ea, eb = numstat(base, close, ENGINE_PATHS)
    ca, cb = numstat(base, close, CODE_PATHS)
    head_tip = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                              capture_output=True, text=True).stdout.strip()
    ea_t, eb_t = numstat(base, head_tip, ENGINE_PATHS)
    ca_t, cb_t = numstat(base, head_tip, CODE_PATHS)
    hunts = [
        {"candidate": "old formula at close (ea+eb)/(ea+eb+ca+cb)",
         "value": pct((ea + eb) / (ea + eb + ca + cb))},
        {"candidate": "corrected at close (ea+eb)/(ca+cb)",
         "value": pct((ea + eb) / (ca + cb))},
        {"candidate": "added-only, engine once (ea)/(ea+ca)",
         "value": pct(ea / (ea + ca)) if (ea + ca) else None},
        {"candidate": "added-only, engine double (ea)/(ea+ea+ca)",
         "value": pct(ea / (2 * ea + ca)) if (2 * ea + ca) else None},
        {"candidate": "added+removed engine over added-only code (ea+eb)/(ea+ca)",
         "value": pct((ea + eb) / (ea + ca)) if (ea + ca) else None},
        {"candidate": "old formula at tip 2d1170f06+ (twin's recompute point)",
         "value": pct((ea_t + eb_t) / (ea_t + eb_t + ca_t + cb_t))
         if (ea_t + eb_t + ca_t + cb_t) else None},
        {"candidate": "corrected at tip 2d1170f06+",
         "value": pct((ea_t + eb_t) / (ca_t + cb_t)) if (ca_t + cb_t) else None},
    ]
    recorded = 23.4
    reproduces = [h["candidate"] for h in hunts
                  if h["value"] is not None and abs(h["value"] - recorded) <= 0.15]

    record = {
        "record": "R136S2_SHARE_RECONCILIATION/1.0.0",
        "session": "builder-r134s2",
        "work_id": "r136s2-share-reconcile",
        "at": "2026-11-23 (sandbox clock)",
        "responds_to": "R136 directions dir 5 (reconcile the R135 record's 23.4% against the 14.9% old-formula and 17.5% corrected recomputes) + the verifier record's claim-b pointer",
        "method": "git diff --numstat base..LANDED-close per round; engine = discovery_fabric/engine/; code = engine+scripts+tests+requirements (the committed test's CODE_PATHS); every number in this record recomputes from the diff with the script committed alongside it (scripts/r136s2_share_reconcile.py)",
        "close_sha_note": "the r135s1_status.json remote_ci.pushed_sha (7a592f621) and its check-run are UNREACHABLE server-side (rewritten by the R135 rebase disclosed in 908c5d446 'CLAIM RECONCILIATION ... rebase conflict resolved CLEAN'); the governing recompute therefore uses the LANDED close 1613e109a (the audit basis: CI green on 2d1170f06, 1613e109a and the three before them); the 23.4% hunt on the pre-rebase bytes is impossible — the object is gone",
        "rounds": results,
        "r135_234_hunt": {
            "recorded_value": recorded,
            "source": "eval/r135s1_status.json art27_capability_budget.share_exception_reason",
            "candidates": hunts,
            "reproduced_by": reproduces,
        },
        "reconciliation_verdict": None,  # filled below
        "no_score_claims": True,
    }

    if reproduces:
        record["reconciliation_verdict"] = (
            f"the recorded 23.4% REPRODUCES from the diff as: {reproduces[0]} "
            f"— it is a real measurement under a different (added-line/"
            f"double-counting) convention, not a transcription error; the "
            f"governing corrected share for R135 remains {results[2]['corrected_share']}% "
            f"(engine counted once), which the twin independently reported")
    else:
        record["reconciliation_verdict"] = (
            f"the recorded 23.4% reproduces under NO candidate formula or "
            f"range tried (candidates typed in r135_234_hunt; corrected "
            f"R135 = {results[2]['corrected_share']}%, old-formula R135 = "
            f"{results[2]['old_formula_share']}%) — it is a hand-typed "
            f"drift, disclosed here with the diff-recomputed figures as the "
            f"governing numbers; the 25-point CI tolerance did not catch it "
            f"because the test ran at a HEAD where the diff differed")

    out = REPO / "eval" / "r136s2_share_reconciliation.json"
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(json.dumps({"rounds": [
        {k: v for k, v in row.items() if k in
         ("round", "old_formula_share", "corrected_share",
          "matches_twin_corrected", "matches_recorded_old")}
        for row in results],
        "r135_234_hunt_reproduced_by": reproduces,
        "verdict": record["reconciliation_verdict"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
