#!/usr/bin/env python3
"""r105s2 — the rubric SPREAD CHECK (auditor direction 6, claim
c-0129; work_id p3-score9-lane-d4d5d6, stage 3): the hardened
invention rubric v2.1.0 (the two TRUTH-BEARING axes:
direction_correctness, magnitude_plausibility) re-scores the 30
BURNED v15 rows (committed bytes, the acceptance set the auditor
found saturated at 4). The auditor's acceptance test: the new rubric
spreads scores across >=3 LEVELS on the v15 rows. The scorer is the
engine's own deterministic module (discovery_fabric/engine/
invention_rubric.py) — no LLM, committed bytes in, JSON record out.
Zero quota (the machine's own scoring surface).
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
OUT = REPO / "eval" / "r105s2_rubric_spread_v15.json"

from discovery_fabric.engine import invention_rubric as ir  # noqa: E402


def main():
    probs = {p["problem_id"]: p for p in json.loads(subprocess.run(
        ["git", "show", V15_PROBLEMS], capture_output=True, text=True,
        cwd=str(REPO)).stdout)["problems"]}
    rows = sorted((REPO / "eval/holdout_v15_generation/rows")
                  .glob("*.json"))
    assert len(rows) == 30, f"expected 30 burned rows, got {len(rows)}"
    per_row = []
    axis_vals = {ax: [] for ax in ir.AXES}
    for f in rows:
        r = json.loads(f.read_text())
        prob = probs.get(r["problem_id"])
        assert prob, f"problem {r['problem_id']} missing from the "
        "audit-branch registry"
        sc = ir.score_answer(prob, r.get("a1_answer") or "")
        per_row.append({"problem_id": r["problem_id"],
                        "scores": sc["scores"], "total": sc["total"],
                        "truth_direction":
                            sc["scores"]["direction_correctness"],
                        "truth_magnitude":
                            sc["scores"]["magnitude_plausibility"]})
        for ax in ir.AXES:
            axis_vals[ax].append(sc["scores"][ax])
    spread = {ax: dict(sorted(Counter(v).items()))
              for ax, v in axis_vals.items()}
    distinct = {ax: len(spread[ax]) for ax in spread}
    truth_distinct = (len(set(axis_vals["direction_correctness"])) +
                      len(set(axis_vals["magnitude_plausibility"])))
    record = {
        "record": "R105S2_RUBRIC_SPREAD_V15/1.0.0",
        "executor": "builder-r105s2",
        "claim": "c-0129 (p3-score9-lane-d4d5d6; stage 3 = D6)",
        "rubric_version": ir.INVENTION_RUBRIC_VERSION,
        "rows_scored": len(per_row),
        "axis_histograms": spread,
        "distinct_levels_per_axis": distinct,
        "auditor_test": {
            "clause": ("the new rubric spreads scores across >=3 "
                       "levels on v15 rows"),
            "measured_total_levels": len(set(
                axis_vals["novelty"] + axis_vals["feasibility"] +
                axis_vals["testability"] +
                axis_vals["constraint_compliance"])),
            "truth_axes_combined_levels": truth_distinct,
            "note": ("the ORIGINAL v15 saturation: 27/30 rows scored "
                     "4 on the old scale; the new truth-bearing axes "
                     "are measured on the SAME rows"),
        },
        "per_row": per_row,
        "no_acceptance_claims": True,
    }
    OUT.write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {OUT.name} ({OUT.stat().st_size} bytes)")
    print("distinct levels per axis:", distinct)
    print("truth axes histograms:",
          spread["direction_correctness"],
          spread["magnitude_plausibility"])


if __name__ == "__main__":
    main()
