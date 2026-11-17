#!/usr/bin/env python3
"""scripts/r53_p2_ablation_criteria.py — the zero-LLM adoption-criteria
evaluator for the P2 matched-budget DEV ablation (roadmap P2; claim
c-0071).

WHAT THIS IS: the deterministic evaluator of the three pre-registered
adoption criteria — schedule-share <= 17%, ALLOWED_ROW_OUTSIDE = 0,
mean score no drop vs the V7.7 baseline — over two run-row files. It
computes the typed verdict inputs and NOTHING else.

WHAT THIS IS NOT (typed): it is NOT the ablation itself. The ablation's
expansion leg is the machine's LLM job; this sandbox's LLM credential
state is degraded (the typed mid-R52 NVIDIA key absence carries over),
and the "mean no drop" leg must be scored under a valid metric
instrument — the public v8 rubric is burned evidence (F60) and may not
score anything. The ablation RUN therefore defers to the round where
the machine leg runs under a confidential instrument (v9 post-P0
custody). Committing the evaluator now keeps the adoption bar
pre-registered and CI-testable BEFORE any run (the AM44 protocol:
criteria before data).

Zero LLM, zero network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

# v3.2.0 Art. 22 measured-path declaration (c-0079, F61 class): when the
# v9 machine leg runs, its measurement goes through the ENGINE route
# (discovery_fabric.engine.engine_route -> mechanism_space, the typed-
# operator engine), never a wrapper. See eval/measured_path_decision_r47
# .json (the committed routing decision) and
# tests/test_article22_measured_path.py (the CI that enforces this).
MEASURED_PATH = "discovery_fabric.engine.engine_route -> mechanism_space"

SCHEDULE_BAR = 0.17


def evaluate(rows_path: Path, baseline_path: Path) -> dict:
    """Evaluate the three criteria. Row files are dicts keyed by
    problem_id -> {"mean_score": float|None, "measure_classes":
    [..], "allowed_row_outside": int} — the machine run's normalizer
    emits this shape; the evaluator refuses to guess."""
    rows = json.loads(rows_path.read_text())
    base = json.loads(baseline_path.read_text())
    common = sorted(set(rows) & set(base))
    if not common:
        return {"verdict": "EVALUATION_REFUSED",
                "reason": "no overlapping problem ids between the "
                          "candidate rows and the baseline rows — "
                          "nothing is invented"}
    # criterion 1: schedule-share over the candidate rows' measure
    # classes (duty_cycle = the monoculture family, F54)
    cls = [c for pid in common
           for c in rows[pid].get("measure_classes", [])]
    share = (cls.count("duty_cycle") / len(cls)) if cls else None
    crit1 = {"criterion": "schedule_share<=0.17",
             "value": share, "met": share is not None and
             share <= SCHEDULE_BAR}
    # criterion 2: ALLOWED_ROW_OUTSIDE must be 0
    outside = sum(rows[pid].get("allowed_row_outside", 0)
                  for pid in common)
    crit2 = {"criterion": "ALLOWED_ROW_OUTSIDE==0", "value": outside,
             "met": outside == 0}
    # criterion 3: mean no drop (scored under a valid instrument only;
    # absent scores -> UNMEASURABLE, never fabricated)
    if all(rows[pid].get("mean_score") is not None for pid in common) \
            and all(base[pid].get("mean_score") is not None
                    for pid in common):
        cand_m = sum(rows[pid]["mean_score"] for pid in common) / len(common)
        base_m = sum(base[pid]["mean_score"] for pid in common) / len(common)
        crit3 = {"criterion": "mean_no_drop", "candidate": round(cand_m, 4),
                 "baseline": round(base_m, 4), "met": cand_m >= base_m}
    else:
        crit3 = {"criterion": "mean_no_drop", "value": "UNMEASURABLE",
                 "reason": "scores absent — the instrument must be a "
                           "confidential valid one (v9 post-P0 custody)",
                 "met": False}
    all_met = crit1["met"] and crit2["met"] and crit3["met"]
    return {"record": "R53_P2_ABLATION_CRITERIA/1.0.0",
            "schedule_bar": SCHEDULE_BAR,
            "overlapping_rows": len(common),
            "criteria": [crit1, crit2, crit3],
            "verdict": ("ADOPT" if all_met else
                        "DELETE" if crit1["met"] and crit2["met"] else
                        "INCOMPLETE — criteria unmet; the pre-registered "
                        "bar says the addition does not survive"),
            "note": "evaluator only; the RUN defers (see module docstring)"}


def main() -> None:
    if len(sys.argv) != 3:
        print("usage: r53_p2_ablation_criteria.py <candidate_rows.json> "
              "<baseline_rows.json>")
        sys.exit(2)
    out = evaluate(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
