"""r145s1b — the post-hoc QUANT PASS over the v17 rows (R144-F1).

DIR 3's finding from the verifier act: the v17 rows carry prediction
TEXT on 22-27/30 but ZERO pint-computed predictions (0 QUANT records
in the rows). This pass computes a unit-checked prediction for EVERY
v17 invention from the invention's own stated design parameters via
the generic class dispatcher, writing eval/r145s1b_quant_pass/:

  per row: {problem_id, failure_class, route (specific|class-generic),
            prediction {status, quantity, predicted_value, calc_trace,
            falsifier}}

Acceptance (R144-F1): 30/30 v17 inventions carry a falsifiable
computed prediction; rows where the invention states no usable design
point get the typed insufficient_parameters + the measurement plan —
never invented numbers.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.generation import mechanism_map as mm  # noqa: E402
from discovery_fabric.generation import quant_generic as qg  # noqa: E402

OUT = REPO / "eval" / "r145s1b_quant_pass"
OUT.mkdir(exist_ok=True)
ARMS = ("rows_inspiration_arm", "rows_pre_inspiration")


def main() -> int:
    pd = json.loads((REPO / "eval" / "holdout_v17" / "problems.json")
                    .read_text())
    probs = {p["problem_id"]: p["problem"] for p in
             (pd if isinstance(pd, list) else pd.get("problems", []))}
    summary = {"record": "r145s1b_quant_pass/1.0.0 — the post-hoc "
                         "unit-checked quant pass over the v17 rows "
                         "(R144-F1): every invention gets a falsifiable "
                         "pint-checked prediction from its OWN stated "
                         "design point; typed insufficient_parameters "
                         "where none is stated (never invented numbers)",
               "arms": {}}
    for arm in ARMS:
        rows = sorted((REPO / "eval" / "holdout_v17_generation" / arm)
                      .glob("v17-*.json"))
        n_computed = n_missing = 0
        routes = {}
        out_arm = OUT / arm
        out_arm.mkdir(exist_ok=True)
        for r in rows:
            d = json.loads(r.read_text())
            pid = d["problem_id"]
            txt = d.get("a1_answer") or ""
            sel = mm.classify_failure(probs.get(pid, ""))
            pred = qg.emit_prediction_generic(sel.failure_class, txt)
            if pred.get("status") == "computed":
                n_computed += 1
            else:
                n_missing += 1
            routes[pred.get("route", pred.get("status"))] = \
                routes.get(pred.get("route", pred.get("status")), 0) + 1
            (out_arm / f"{pid}.json").write_text(json.dumps({
                "problem_id": pid,
                "failure_class": sel.failure_class,
                "prediction": pred}, indent=2) + "\n")
        summary["arms"][arm] = {
            "n": len(rows), "computed": n_computed,
            "typed_missing": n_missing, "routes": routes,
            "acceptance_r144_f1": n_computed == len(rows)}
        print(f"{arm}: {n_computed}/{len(rows)} computed, "
              f"{n_missing} typed-missing, routes={routes}")
    (OUT / "SUMMARY.json").write_text(json.dumps(summary, indent=2)
                                      + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
