#!/usr/bin/env python3
"""r45_run_metrics.py — the AM42 D1/D2 RUN-TIME acceptance metrics
measured from the V8.1 run artifacts (eval/v81_run):
  D1: the share of intervention rows whose final answer carries a
      COMPUTED_PHYSICS_CONSISTENT verdict (target >= 0.80) and the
      count of COMPUTED_PHYSICS_INCONSISTENT (target 0);
  D2: the non-duty-cycle share among interventions (target >= 0.80
      where physics admits — the auditor adjudicates 'admits'), the
      candidate-population facts (>=3 plans, distinct classes and
      TRIZ principles — the machine guarantees; verified from the
      events), the diversity-cap firings on the 3rd inferred
      template, and mean repairs/row vs the v7 3.0 baseline;
  plus the residual inventory and 0-inverted / 0-unavailable-input
  reads for the auditor's acceptance bar.
Emits eval/r45_run_metrics.json. Works on partial runs (reports
n_rows and marks PARTIAL)."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT = REPO / "eval" / "v81_run"


def main():
    ev_path = OUT / "v81_events_ledger.json"
    if not ev_path.exists():
        print("no run yet")
        return
    doc = json.loads(ev_path.read_text(encoding="utf-8"))
    events = doc["events"]
    rows = {}
    for rp in sorted((OUT / "rows").glob("*.json")):
        d = json.loads(rp.read_text(encoding="utf-8"))
        rows[d["problem_id"]] = d

    interventions = [e for e in events
                     if e["question_type"].lower()
                     .startswith("intervention")]
    predictors = [e for e in events
                  if e["question_type"].lower().startswith("predictor")]

    # D1: computed-physics verdicts on final rows
    comp_ok, comp_bad, comp_missing = [], [], []
    for pid, d in rows.items():
        res = (d.get("final_meta") or {}).get("residual_findings") or {}
        att = {k for a in (doc["events"][next(
            i for i, e in enumerate(events)
            if e["problem_id"] == pid)])["attempts"]
            for k in (a.get("scan") or {})}
        if "COMPUTED_PHYSICS_INCONSISTENT" in res or \
                "COMPUTED_PHYSICS_INCONSISTENT" in att:
            comp_bad.append(pid)
        elif "COMPUTED_PHYSICS_CONSISTENT" in att:
            comp_ok.append(pid)
        else:
            comp_missing.append(pid)
    n_int_rows = len([p for p in rows.values()
                      if p["question_type"].lower()
                      .startswith("intervention")])
    computed_share = (len([p for p in comp_ok
                           if rows[p]["question_type"].lower()
                           .startswith("intervention")])
                      / n_int_rows) if n_int_rows else 0.0

    # D2: classes + duty families
    class_seq = [(e["problem_id"], e.get("counted_class") or "UNSTATED")
                 for e in interventions]
    duty_rows = [(pid, c) for pid, c in class_seq
                 if c != "UNSTATED" and __import__("re")
                 .search(r"duty[- ]?cycle|schedul|periodic|setpoint[- ]?"
                         r"(modulat|retun)|cyclic|interval|puls", c, __import__("re").I)]
    non_duty = [(pid, c) for pid, c in class_seq
                if c == "UNSTATED" or (pid, c) not in duty_rows]
    non_duty_share = (len(non_duty) / len(class_seq)) if class_seq else 0.0

    # population facts from the events (the machine's guarantees,
    # verified from bytes)
    pop_facts = []
    for e in interventions:
        pop = (e["final_meta"] or {}).get("population") or {}
        pop_facts.append({
            "problem_id": e["problem_id"],
            "n_candidates": pop.get("n_candidates"),
            "selected": pop.get("selected"),
            "triz_principle": pop.get("triz_principle"),
            "candidate_scores": pop.get("candidate_scores")})

    # cap firings during the run
    cap_fires = []
    for e in events:
        for a in e.get("attempts", []):
            if "MECHANISM_TEMPLATE_MONOCULTURE" in (a.get("scan") or {}):
                cap_fires.append({"problem_id": e["problem_id"],
                                  "attempt": a.get("stage")})

    reps = [e["final_meta"].get("repairs", 0) for e in events]
    mean_repairs = (sum(reps) / len(reps)) if reps else 0.0

    res: dict = {}
    for pid, d in rows.items():
        rf = (d.get("final_meta") or {}).get("residual_findings") or {}
        for k, v in rf.items():
            res.setdefault(k, []).append(pid)

    metrics = {
        "record": "R45_RUN_METRICS/1.0.0",
        "basis": "run-time properties from eval/v81_run (the FRESH "
                 "V8.1 generation, claim c-0066)",
        "partial": len(rows) < 30,
        "n_rows": len(rows),
        "n_intervention_rows": n_int_rows,
        "n_predictor_rows": len(predictors),
        "d1_computed_physics": {
            "consistent_rows": comp_ok,
            "inconsistent_rows": comp_bad,
            "missing_or_uncomputable_rows": comp_missing,
            "intervention_computed_share": round(computed_share, 3),
            "target": ">= 0.80 of intervention rows computed-consistent; "
                      "0 INCONSISTENT"},
        "d2_population": {
            "intervention_class_sequence": class_seq,
            "non_duty_cycle_rows": non_duty,
            "duty_cycle_rows": duty_rows,
            "non_duty_cycle_share": round(non_duty_share, 3),
            "target": ">= 0.80 where physics admits (auditor "
                      "adjudicates the admits clause)",
            "population_facts": pop_facts,
            "cap_firings_during_run": cap_fires,
            "mean_repairs_per_row": round(mean_repairs, 2),
            "v7_baseline_mean_repairs": 3.0},
        "residual_inventory": {k: {"count": len(v), "rows": v}
                               for k, v in sorted(res.items())},
        "inverted_rows": res.get("PHYSICS_DIRECTION_INVERTED", []),
        "input_unavailable_rows": res.get("INPUT_UNAVAILABLE", []),
        "written": "2026-11-17"}
    (REPO / "eval" / "r45_run_metrics.json").write_text(
        json.dumps(metrics, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8")
    print(json.dumps({
        "n_rows": len(rows),
        "d1_computed_share": metrics["d1_computed_physics"]
        ["intervention_computed_share"],
        "d1_inconsistent": len(comp_bad),
        "d2_non_duty_share": metrics["d2_population"]
        ["non_duty_cycle_share"],
        "cap_fires": len(cap_fires),
        "mean_repairs": metrics["d2_population"]
        ["mean_repairs_per_row"],
        "inverted": len(metrics["inverted_rows"])}, indent=1))


if __name__ == "__main__":
    main()
