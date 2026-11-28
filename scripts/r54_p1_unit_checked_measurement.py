#!/usr/bin/env python3
"""scripts/r54_p1_unit_checked_measurement.py — the P1 >=80%
numeric-claims-unit-checked measurement on labelled DEV outputs
(claim c-0072; the AM49 P1-gate leg; F80 on-row upgrade R83 c-0099).

CLAIM SET (pre-registered before the number exists — the AM44
criteria-before-data protocol; UNCHANGED by the F80 upgrade):
  one claim = one candidate's numeric-direction claim on a labelled
  DEV row (the 12 burned v7 problems), i.e. a predicted_effect that
  names computed signals and a sign-of-result direction.

DEFINITION v2 (F80, AM72 direction 3 — the on-row leg): a claim
CARRIES A RUNNING UNIT-CHECKED ON-ROW CALCULATION iff:
  (a) an applicable registry relation exists for the row's failure
      class — routed by the deterministic keyword router
      (physics_checks.classify_failure), never by prose parsing; and
  (b) that relation RUNS ON THE ROW through onrow_physics.run_on_row:
      the row's OWN extracted numeric claims bind to the relation's
      inputs by pint dimensional compatibility (ROW CLAIMS WIN), the
      gaps fill from the relation's committed reference values as
      TYPED ASSUMPTIONS with per-input provenance (Art. 9 labelled
      assumptions — visible, sourced, never silent defaults), and
      the computation runs through the frozen run_check registry with
      a pint value; and
  (c) the sign-check records no SIGN_CONTRADICTION (an unambiguous
      improves/worsens assertion the computation contradicts; a
      deferring or frame-dependent text is DEFERRED, not guessed).

The v1 reference-scenario leg is superseded (git history preserves
it): v1 proved the calculation was wired; v2 proves it runs on the
row's own numbers wherever the row states them.

The fraction = on-row-carrying claims / all numeric-direction claims.
Bar: >= 0.80 (roadmap P1) AND zero sign contradictions. The artifact
carries the per-row breakdown incl. the own-numbers inventory
(extracted / unparseable / bound) and every on-row run's input
provenance. Zero LLM, zero network.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import engine_route as er      # noqa: E402
from discovery_fabric.engine import physics_checks as pc    # noqa: E402
from discovery_fabric.engine import numeric_claims as nc    # noqa: E402
from discovery_fabric.engine import onrow_physics as onrow  # noqa: E402

BAR = 0.80


def main() -> None:
    rows = json.loads(
        (REPO / "eval/r43_v7_problem_fields_burned.json")
        .read_text())["problems"]
    rows_out = []
    carrying = 0
    total = 0
    sign_contradictions = 0
    onrow_runs_run = 0
    own_totals = {"extracted": 0, "unparseable": 0, "bound_inputs": 0,
                  "assumption_inputs": 0}
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
        # F80 on-row leg: per candidate, extract the row's OWN numbers
        # and run every applicable check ON THE ROW
        onrow_runs = []
        own = {"extracted": 0, "unparseable": 0, "bound_inputs": 0,
               "assumption_inputs": 0}
        for r in results:
            c = r.get("candidate") or {}
            extraction = nc.extract_candidate_claims(c)
            own["extracted"] += len(extraction["claims"])
            own["unparseable"] += len(extraction["unparseable"])
            for check_id in applicable:
                run = onrow.run_on_row(
                    check_id, extraction,
                    direction_text=str(c.get("expected_effect") or ""))
                run = dict(run)
                run["candidate_id"] = c.get("candidate_id")
                onrow_runs.append(run)
                if run.get("verdict") == "RUN":
                    own["bound_inputs"] += len(run.get(
                        "row_claim_inputs") or [])
                    own["assumption_inputs"] += len(run.get(
                        "assumption_inputs") or [])
                    sc = run.get("sign_check") or {}
                    if sc.get("verdict") == "SIGN_CONTRADICTION":
                        sign_contradictions += 1
        ok = bool(onrow_runs) and any(r["verdict"] == "RUN"
                                      for r in onrow_runs)
        onrow_runs_run += sum(1 for r in onrow_runs
                              if r["verdict"] == "RUN")
        for k in own_totals:
            own_totals[k] += own[k]
        carrying += len(numeric_claims) if ok else 0
        total += len(numeric_claims)
        rows_out.append({
            "problem_id": p["problem_id"], "failure_class": fclass,
            "numeric_claims": len(numeric_claims),
            "carrying": len(numeric_claims) if ok else 0,
            "applicable_checks": applicable,
            "on_row_runs": onrow_runs,
            "own_numbers": own,
            "carrying_note": ("the applicable relation RUNS ON THE ROW "
                              "(row-claims-first binding; committed "
                              "reference values enter only as TYPED "
                              "ASSUMPTIONS with per-input provenance)"
                              if ok else
                              "no applicable relation runs on-row — "
                              "the claim degrades to PENDING_INPUTS "
                              "(inputs absent, never fabricated)")})
    fraction = (carrying / total) if total else 0.0
    art = {
        "record": "R54_P1_UNIT_CHECKED/2.0.0",
        "claim": "c-0072 (v1) / c-0099 (F80 on-row upgrade)",
        "definition_version": "2.0.0 (F80: on-row, row-claims-first, "
            "typed assumptions with provenance, sign-check)",
        "pre_registered_definition": "claim = a candidate's "
            "numeric-direction claim on a labelled DEV row (UNCHANGED "
            "from v1); carrying = the applicable registry relation "
            "(deterministic classify_failure router) RUNS ON THE ROW "
            "via onrow_physics.run_on_row — the row's own extracted "
            "claims bind by pint dimensional compatibility (row "
            "claims win), gaps fill from the committed reference "
            "values as TYPED ASSUMPTIONS (per-input provenance, Art. "
            "9), computation through the frozen run_check registry "
            "with a pint value, and the sign-check records no "
            "SIGN_CONTRADICTION",
        "bar": BAR,
        "numeric_claims_total": total,
        "carrying": carrying,
        "fraction": round(fraction, 4),
        "sign_contradictions": sign_contradictions,
        "on_row_runs_run": onrow_runs_run,
        "own_numbers_totals": own_totals,
        "verdict": ("P1_UNIT_CHECKED_PASS"
                    if (fraction >= BAR and sign_contradictions == 0)
                    else "P1_UNIT_CHECKED_BELOW_BAR"),
        "rows": rows_out,
    }
    dest = REPO / "eval/r54_p1_unit_checked.json"
    dest.write_text(json.dumps(art, indent=1))
    print(json.dumps({k: art[k] for k in (
        "numeric_claims_total", "carrying", "fraction",
        "sign_contradictions", "on_row_runs_run", "verdict")},
        indent=1))
    if fraction < BAR:
        print(f"BELOW BAR {fraction:.3f} < {BAR}: expand registry "
              "coverage / route more claims through run_check")
    if sign_contradictions:
        print(f"SIGN CONTRADICTIONS {sign_contradictions} > 0: an "
              "asserted direction the computation contradicts")


if __name__ == "__main__":
    main()
