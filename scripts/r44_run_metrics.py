#!/usr/bin/env python3
"""r44_run_metrics.py — the D3 RUN-TIME acceptance metrics computed
from the run artifacts (NOT from committed bytes alone — these are
run-time properties the coordinator's direction 3 requires reporting
from the run):
  1. non-duty-cycle share among the 15 interventions (target >=80%
     where physics admits — the auditor judges the 'admits' clause;
     this script reports the measured share + per-row classes);
  2. unpriced duty cycles (target 0 — UNPRICED_DUTY_CYCLE residuals);
  3. the diversity cap FIRING on a 3rd-of-class (F58 — visible in the
     events as MECHANISM_TEMPLATE_MONOCULTURE at some attempt);
  4. mean repairs/row vs the v7 baseline (3.0 — every v7 row hit
     repair_3);
plus the other run residuals (INPUT_UNAVAILABLE, PDU on predictors,
DETECTION_INTERVENTION_CONFLATION) and the candidate-classes share.
Emits eval/r44_run_metrics.json."""
from __future__ import annotations

import json
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "v8_run"

DUTY_RX = re.compile(
    r"\b(duty[ -]?cycle|schedul\w*|periodic\w*|cyclic\w*|cycle\b|"
    r"setpoint[ -]?modulat\w*|interval\w*|puls\w*|rest[ -]?interval)\b",
    re.I)


def main():
    events = json.loads((OUT / "v8_events_ledger.json")
                        .read_text(encoding="utf-8"))["events"]
    rows = {}
    for rp in sorted((OUT / "rows").glob("*.json")):
        d = json.loads(rp.read_text(encoding="utf-8"))
        rows[d["problem_id"]] = d

    interventions = [e for e in events
                     if e["question_type"].lower()
                     .startswith("intervention")]
    predictors = [e for e in events
                  if e["question_type"].lower().startswith("predictor")]

    # 1. class families (the histogram's counted classes, in order)
    class_seq = [(e["problem_id"], e.get("counted_class") or "UNSTATED")
                 for e in events if e["question_type"].lower()
                 .startswith("intervention")]
    duty_rows = [(pid, c) for pid, c in class_seq
                 if c != "UNSTATED" and DUTY_RX.search(c)]
    non_duty = [(pid, c) for pid, c in class_seq
                if c == "UNSTATED" or not DUTY_RX.search(c)]
    n_int = len(class_seq)
    share = len(non_duty) / n_int if n_int else 0.0

    # 2. residuals across final rows
    res: dict = {}
    for pid, d in rows.items():
        rf = (d.get("final_meta") or {}).get("residual_findings") or {}
        for k, v in rf.items():
            res.setdefault(k, []).append(pid)

    # 3. cap firings during the run
    cap_fires = []
    for e in events:
        for i, a in enumerate(e.get("attempts", [])):
            if "MECHANISM_TEMPLATE_MONOCULTURE" in (a.get("scan") or {}):
                cap_fires.append({
                    "problem_id": e["problem_id"],
                    "attempt": a.get("stage"),
                    "histogram_before": e.get("histogram_before")})

    # 4. repairs
    reps = [e["final_meta"].get("repairs", 0) for e in events]
    mean_repairs = (sum(reps) / len(reps)) if reps else 0.0

    # candidate-classes presence on final interventions
    cand = 0
    for pid, d in rows.items():
        if d["question_type"].lower().startswith("intervention") and \
                re.search(r"CANDIDATE CLASSES?\s*[:\-]",
                          d["a1_answer"], re.I):
            cand += 1

    metrics = {
        "record": "R44_RUN_METRICS/1.0.0",
        "basis": "run-time properties from eval/v8_run (the ONE "
                 "generation, frozen V8.0, claim c-0062)",
        "n_rows": len(rows),
        "n_interventions": n_int,
        "n_predictors": len(predictors),
        "intervention_class_sequence": class_seq,
        "non_duty_cycle_rows": non_duty,
        "duty_cycle_rows": duty_rows,
        "non_duty_cycle_share": round(share, 3),
        "d3_non_duty_target": ">= 0.80 where physics admits (the "
                              "auditor judges the admits clause)",
        "unpriced_duty_cycle_residuals": {
            "count": len(res.get("UNPRICED_DUTY_CYCLE", [])),
            "rows": res.get("UNPRICED_DUTY_CYCLE", [])},
        "cap_firings_during_run": cap_fires,
        "mean_repairs_per_row": round(mean_repairs, 2),
        "v7_baseline_mean_repairs": 3.0,
        "residual_inventory": {k: {"count": len(v), "rows": v}
                               for k, v in sorted(res.items())},
        "candidate_classes_present_interventions": cand,
        "input_unavailable_residual_rows":
            res.get("INPUT_UNAVAILABLE", []),
        "written": "2026-11-17"}
    out = REPO / "eval" / "r44_run_metrics.json"
    out.write_text(json.dumps(metrics, indent=1, ensure_ascii=False)
                   + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in metrics.items()
                      if k in ("n_rows", "non_duty_cycle_share",
                               "unpriced_duty_cycle_residuals",
                               "mean_repairs_per_row",
                               "candidate_classes_present_"
                               "interventions",
                               "cap_firings_during_run")},
                     indent=1)[:600])
    print("residuals:", {k: v["count"] for k, v in
                         metrics["residual_inventory"].items()})


if __name__ == "__main__":
    main()
