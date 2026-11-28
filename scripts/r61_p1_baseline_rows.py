#!/usr/bin/env python3
"""scripts/r61_p1_baseline_rows.py — direction 4 (auditor R61): P1's
">=80% computed magnitudes" measured on the 36 BASELINE ablation rows'
problem corpus with the run-metrics instrument's pre-registered
definition (r54, claim c-0072), zero-LLM, zero-network.

Same claim set and same carrying definition as r54, applied to the
burned-DEV corpus the baseline arm actually ran (the driver's
load_dev_problems — the SAME 36-problem selection as the committed
rows_baseline, cross-checked by problem_id). The instrument runs the
deterministic engine route + physics router; no LLM call is made.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from discovery_fabric.engine import engine_route as er      # noqa: E402
from discovery_fabric.engine import physics_checks as pc    # noqa: E402
from r58_p2_ablation_driver import load_dev_problems        # noqa: E402

BAR = 0.80


def main() -> None:
    problems = load_dev_problems()
    committed = {p.stem for p in
                 (REPO / "eval/r58_ablation/rows_baseline").glob("*.json")}
    pids = {p["problem_id"] for p in problems}
    if committed != pids:
        print(json.dumps({"record": "R61_P1_BASELINE_ROWS/1.0.0",
                          "verdict": "CORPUS_MISMATCH_REFUSED",
                          "committed_rows": len(committed),
                          "corpus": len(pids),
                          "missing_in_corpus": sorted(committed - pids)[:6],
                          "extra_in_corpus": sorted(pids - committed)[:6]}))
        raise SystemExit(2)
    rows_out = []
    carrying = 0
    total = 0
    for p in problems:
        out = er.run_row(p)
        results = out.get("results", [])
        numeric_claims = []
        for r in results:
            c = r.get("candidate") or {}
            pe = str(c.get("predicted_effect", ""))
            if "computed physics result" in pe or "SIGN" in pe:
                numeric_claims.append({
                    "candidate_id": c.get("candidate_id"),
                    "physics_results": r.get("physics", [])})
        if not numeric_claims:
            rows_out.append({"problem_id": p["problem_id"],
                             "numeric_claims": 0, "carrying": 0,
                             "note": "no numeric-direction claims on "
                                     "this row (all PENDING/structural)"})
            continue
        fclass = pc.classify_failure(str(p.get("failure", "")))
        applicable = pc.check_for_failure_class(fclass) if fclass else []
        runs = []
        for check_id in applicable:
            scen = pc.REFERENCE_SCENARIOS.get(check_id)
            if scen is None:
                runs.append({"check_id": check_id,
                             "verdict": "NO_REFERENCE_SCENARIO"})
                continue
            res = pc.run_check(check_id, **scen)
            runs.append({"check_id": check_id, "verdict": res["verdict"],
                         "value": res["value"], "unit": res["unit"],
                         "direction": res["direction_of_effect"]})
        ok = bool(runs) and any(r["verdict"] == "RUN" for r in runs)
        on_row = [pr for nc in numeric_claims
                  for pr in (nc["physics_results"] or [])
                  if pr.get("verdict") == "RUN"]
        carrying += len(numeric_claims) if ok else 0
        total += len(numeric_claims)
        rows_out.append({
            "problem_id": p["problem_id"], "failure_class": fclass,
            "numeric_claims": len(numeric_claims),
            "carrying": len(numeric_claims) if ok else 0,
            "applicable_checks": applicable,
            "check_runs": runs,
            "on_row_physics_runs": len(on_row),
            "carrying_note": ("a registry relation is applicable and "
                              "RUNS with a pint value on its committed "
                              "reference scenario" if ok else
                              "no applicable registry relation RUNS — "
                              "the claim degrades to PENDING_INPUTS "
                              "on-row (inputs absent, never fabricated)")})
    fraction = (carrying / total) if total else 0.0
    art = {
        "record": "R61_P1_BASELINE_ROWS/1.0.0",
        "claim": "c-0083 (auditor R61 direction 4)",
        "definition_source": "scripts/r54_p1_unit_checked_measurement.py "
                             "pre-registered definition, verbatim",
        "corpus": "the 36 burned-DEV problems behind rows_baseline "
                  "(load_dev_problems; problem_id set cross-checked "
                  "against the committed rows)",
        "bar": BAR,
        "numeric_claims_total": total,
        "carrying": carrying,
        "fraction": round(fraction, 4),
        "verdict": ("P1_BASELINE_ROWS_PASS" if fraction >= BAR else
                    "P1_BASELINE_ROWS_BELOW_BAR"),
        "rows": rows_out,
    }
    dest = REPO / "eval/r61_p1_baseline_rows.json"
    dest.write_text(json.dumps(art, indent=1) + "\n")
    print(json.dumps({k: art[k] for k in ("numeric_claims_total",
                                          "carrying", "fraction",
                                          "verdict")}, indent=1))


if __name__ == "__main__":
    main()
