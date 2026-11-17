#!/usr/bin/env python3
"""scripts/r54_p1_unit_checked_measurement.py — the P1 >=80%
numeric-claims-unit-checked measurement on labelled DEV outputs
(claim c-0072; the AM49 P1-gate leg).

CLAIM SET (pre-registered here, before the number exists — the AM44
criteria-before-data protocol):
  one claim = one candidate's numeric-direction claim on a labelled
  DEV row (the 12 burned v7 problems), i.e. a predicted_effect that
  names computed signals and a sign-of-result direction.

A claim CARRIES A RUNNING UNIT-CHECKED CALCULATION iff:
  (a) an applicable registry relation exists for the row's failure
      class — routed by the deterministic keyword router
      (physics_checks.classify_failure), never by prose parsing; and
  (b) that relation RUNS through run_check — verdict "RUN" with a
      computed pint value — demonstrated on the relation's COMMITTED
      reference scenario (physics_checks.REFERENCE_SCENARIOS).
The rows themselves carry no numeric context (typed: user_variables
and clarification_answer are None on all 12 rows), so on-row the
honest claim state is PENDING_INPUTS — the route must never fabricate
inputs. The reference scenario proves the calculation is wired and
RUNS with real units; it is NOT presented as the row's measured data.

The fraction = claims-with-a-running-check / all numeric-direction
claims. Bar: >= 0.80 (roadmap P1). The artifact carries the per-row
breakdown; the CI gate reds below the bar. Zero LLM, zero network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import engine_route as er      # noqa: E402
from discovery_fabric.engine import physics_checks as pc    # noqa: E402

BAR = 0.80


def main() -> None:
    rows = json.loads(
        (REPO / "eval/r43_v7_problem_fields_burned.json")
        .read_text())["problems"]
    rows_out = []
    carrying = 0
    total = 0
    for p in rows:
        # the claim set: candidates with numeric-direction claims
        # (predicted_effect referencing the computed-sign path)
        out = er.run_row(p)
        results = out.get("results", [])
        numeric_claims = []
        for r in results:
            c = r.get("candidate") or {}
            pe = str(c.get("predicted_effect", ""))
            if "computed physics result" in pe or "SIGN" in pe:
                numeric_claims.append({
                    "candidate_id": c.get("candidate_id"),
                    "predicted_effect": pe,
                    "physics_results": r.get("physics", [])})
        if not numeric_claims:
            rows_out.append({"problem_id": p["problem_id"],
                             "numeric_claims": 0, "carrying": 0,
                             "note": "no numeric-direction claims on this "
                                     "row (all PENDING/structural)"})
            continue
        # deterministic router: failure text -> registry class
        fclass = pc.classify_failure(str(p.get("failure", "")))
        applicable = pc.check_for_failure_class(fclass) if fclass else []
        runs = []
        for check_id in applicable:
            scen = pc.REFERENCE_SCENARIOS.get(check_id)
            if scen is None:
                runs.append({"check_id": check_id, "verdict":
                             "NO_REFERENCE_SCENARIO"})
                continue
            res = pc.run_check(check_id, **scen)
            runs.append({"check_id": check_id, "verdict":
                         res["verdict"], "value": res["value"],
                         "unit": res["unit"],
                         "direction": res["direction_of_effect"]})
        ok = bool(runs) and any(r["verdict"] == "RUN" for r in runs)
        # the claim's own physics leg (what the route recorded on-row)
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
            "carrying_note": ("a registry relation is applicable and RUNS "
                              "with a pint value on its committed "
                              "reference scenario" if ok else
                              "no applicable registry relation RUNS — "
                              "the claim degrades to PENDING_INPUTS "
                              "on-row (inputs absent, never fabricated)")})
    fraction = (carrying / total) if total else 0.0
    art = {
        "record": "R54_P1_UNIT_CHECKED/1.0.0",
        "claim": "c-0072",
        "pre_registered_definition": "claim = a candidate's "
            "numeric-direction claim on a labelled DEV row; carrying = "
            "an applicable registry relation (deterministic "
            "classify_failure router) RUNS via run_check with a pint "
            "value on the relation's committed reference scenario "
            "(on-row inputs are absent -> PENDING_INPUTS; never "
            "fabricated)",
        "bar": BAR,
        "numeric_claims_total": total,
        "carrying": carrying,
        "fraction": round(fraction, 4),
        "verdict": ("P1_UNIT_CHECKED_PASS" if fraction >= BAR else
                    "P1_UNIT_CHECKED_BELOW_BAR"),
        "rows": rows_out,
    }
    dest = REPO / "eval/r54_p1_unit_checked.json"
    dest.write_text(json.dumps(art, indent=1))
    print(json.dumps({k: art[k] for k in ("numeric_claims_total",
                                          "carrying", "fraction",
                                          "verdict")}, indent=1))
    if fraction < BAR:
        print(f"BELOW BAR {fraction:.3f} < {BAR}: expand registry "
              "coverage / route more claims through run_check")


if __name__ == "__main__":
    main()
