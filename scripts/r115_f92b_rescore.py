#!/usr/bin/env python3
"""r113_f92_f91_rescore.py — the R115 dir-4 acceptance rerun (VF-R114-2, rubric 2.2.1):
the F92/F91-fixed rubric (invention_rubric/2.2.0) re-scores the 30
BURNED v15 rows (committed bytes) and produces the acceptance record:

  * the four R113-adjudicated flags re-score: HO15-03/05 (baseline-
    context + participial guards), HO15-20 (predictor gate),
    HO15-10 (computed cure-relation catch on magnitude)
  * 0 false-positives on predictor rows (the F92 acceptance clause)
  * full before/after per-row direction diff vs the committed
    r105s2 spread record (any collateral shift is disclosed, never
    silently absorbed)
  * the computed check's own numbers quoted for the HO15-10 catch

Zero LLM. Deterministic. Committed bytes in, JSON record out.
"""
from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
REPO = Path(__file__).resolve().parent.parent
AUDIT_REF = "origin/audit/r11-auditor-verdict-20261114"
V15_PROBLEMS = (f"{AUDIT_REF}:audit/holdout_v15/"
                "holdout_v15_problems.json")
BEFORE = REPO / "eval" / "r105s2_rubric_spread_v15.json"
OUT = REPO / "eval" / "r115_f92b_gerund_guard_rescore.json"

from discovery_fabric.engine import invention_rubric as ir  # noqa: E402
from discovery_fabric.engine import physics_checks as pc  # noqa: E402

FLAGGED = ("HO15-03", "HO15-05", "HO15-10", "HO15-20")


def main() -> None:
    probs = {p["problem_id"]: p for p in json.loads(subprocess.run(
        ["git", "show", V15_PROBLEMS], capture_output=True, text=True,
        cwd=str(REPO)).stdout)["problems"]}
    before = {r["problem_id"]: r for r in
              json.loads(BEFORE.read_text())["per_row"]}
    rows = sorted((REPO / "eval/holdout_v15_generation/rows")
                  .glob("*.json"))
    assert len(rows) == 30, f"expected 30 burned rows, got {len(rows)}"

    per_row, axis_vals = [], {ax: [] for ax in ir.AXES}
    direction_shifts = []
    for f in rows:
        r = json.loads(f.read_text())
        prob = probs[r["problem_id"]]
        sc = ir.score_answer(prob, r.get("a1_answer") or "")
        s = sc["scores"]
        per_row.append({
            "problem_id": r["problem_id"],
            "question_type": prob.get("question_type"),
            "scores": s, "total": sc["total"],
            "direction_reason":
                sc["rationale"]["direction_correctness"][0],
            "direction_before": before[r["problem_id"]]["scores"][
                "direction_correctness"],
            "magnitude_before": before[r["problem_id"]]["scores"][
                "magnitude_plausibility"],
        })
        for ax in ir.AXES:
            axis_vals[ax].append(s[ax])
        db = before[r["problem_id"]]["scores"]["direction_correctness"]
        if s["direction_correctness"] != db:
            direction_shifts.append({
                "problem_id": r["problem_id"],
                "before": db, "after": s["direction_correctness"],
                "after_reason":
                    sc["rationale"]["direction_correctness"][0]})

    spread = {ax: dict(sorted(Counter(v).items()))
              for ax, v in axis_vals.items()}
    predictors = [r for r in per_row
                  if r["question_type"] == "predictor-design"]
    pred_fp = [r["problem_id"] for r in predictors
               if r["scores"]["direction_correctness"] == 1]

    # the four adjudicated flags, after
    flags_after = {r["problem_id"][:7]: {
        "direction": r["scores"]["direction_correctness"],
        "magnitude": r["scores"]["magnitude_plausibility"],
        "direction_reason": r["direction_reason"],
    } for r in per_row if r["problem_id"].startswith(FLAGGED)}

    # the F91 computed catch, quoted from the engine's own check
    ho1510 = next(r for r in per_row
                  if r["problem_id"].startswith("HO15-10"))
    comp = pc.thermoset_cure_residual_direction(150.0, 120.0)

    record = {
        "record": "R115_F92B_GERUND_GUARD_RESCORE/1.0.0",
        "at": __import__("datetime").datetime.now(
            __import__("datetime").timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ (sandbox clock, TRUE UTC)"),
        "rubric_version": ir.INVENTION_RUBRIC_VERSION,
        "adjudication_ref": ("origin/audit/r11-auditor-verdict-"
                             "20261114 @ 74aed994e626 — the R113 v15 "
                             "direction adjudication"),
        "f92_fix": ("direction_correctness is GATED on "
                    "question_type=intervention-proposal (predictor "
                    "rows typed neutral, never flagged) + three "
                    "false-positive guards: baseline-context "
                    "(HO15-03), participial-consequence DEGRADE "
                    "gerunds (HO15-05/10), threshold-object polarity "
                    "inversion (HO15-10). The regex stays an INPUT "
                    "(Art. 3/6/8) — never a retroactive gate"),
        "f91_fix": ("cure-kinetics claims route through the engine's "
                    "COMPUTED relation (physics_checks."
                    "thermoset_cure_residual_direction, the new "
                    "cure_kinetics registry class); the regexes only "
                    "extract the claim's own numbers"),
        "rows_scored": len(per_row),
        "flagged_four_after": flags_after,
        "acceptance": {
            "three_pass": {
                "HO15-03": flags_after["HO15-03"]["direction"],
                "HO15-05": flags_after["HO15-05"]["direction"],
                "HO15-20": flags_after["HO15-20"]["direction"],
                "reading": ("no direction VIOLATION (score 1) on any "
                            "of the three adjudicated false-positives; "
                            "HO15-03/05 land at the typed neutral "
                            "anchor (their mitigations are phrased "
                            "without attributable verb+object claims "
                            "on the failure quantity under the "
                            "guarded extractor — the adjudication's "
                            "own reading that the mitigation moves "
                            "the failure driver the correct way is "
                            "the AUDITOR's judgment; the axis does "
                            "not re-derive it)"),
            },
            "ho1510_flagged_on_magnitude": {
                "magnitude": ho1510["scores"]["magnitude_plausibility"],
                "computed_check_quoted": comp,
            },
            "predictor_false_positives": pred_fp,
            "predictor_rows_n": len(predictors),
        },
        "direction_histogram_after": spread["direction_correctness"],
        "magnitude_histogram_after":
            spread["magnitude_plausibility"],
        "direction_shifts_vs_committed_spread": direction_shifts,
        "shift_disclosure": (
            "every per-row direction change vs the committed r105s2 "
            "spread record is listed in direction_shifts — guards "
            "that skip previously-counted claims can only REMOVE "
            "flags or lower credited coverage (never add a "
            "violation); the axis stays an INPUT"),
        "typed_observations": [
            ("arrhenius_rate_ratio carries a latent 1000x magnitude "
             "error in its Ea/R coefficient (R_GAS.magnitude * 1000 "
             "with Ea in J/mol) — SIGN-SAFE (the direction-of-effect "
             "is scale-invariant), CI-green historically, NOT "
             "silently fixed here (Art. 4); the new "
             "thermoset_cure_residual_direction uses the correct "
             "coefficient; the arrhenius magnitude correction is "
             "typed for the auditor's call"),
        ],
        "no_acceptance_claims": True,
    }
    # attach the F91 reason text from the actual scoring rationale
    ho1510_full = ir.score_answer(
        probs[next(r["problem_id"] for r in per_row
                   if r["problem_id"].startswith("HO15-10"))],
        json.loads(next(
            (REPO / "eval/holdout_v15_generation/rows").glob(
                "HO15-10*.json")).read_text())["a1_answer"])
    record["acceptance"]["ho1510_flagged_on_magnitude"][
        "f91_reason"] = next(
            m for m in ho1510_full["rationale"][
                "magnitude_plausibility"] if "F91" in m)

    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print("wrote", OUT.name, OUT.stat().st_size, "bytes")
    print("direction after:", spread["direction_correctness"])
    print("magnitude after:", spread["magnitude_plausibility"])
    print("predictor false-positives:", pred_fp)
    print("direction shifts:", len(direction_shifts))


if __name__ == "__main__":
    main()
