#!/usr/bin/env python3
"""r413_build_opportunity_score.py — emit the Phase 5 decision
artifact: the Physics Gap Opportunity Score + the ONE-solver
selection (operator directive V2 Phase 5).

"Choose the domain with the highest: candidate unlock x expected
information gain / integration cost" — extended by the operator's six
factor list (dead candidates unlocked, mechanism diversity, expected
information gain, implementation cost, validation maturity,
automation feasibility). "Then the machine itself tells us:
'Structural mechanics would unlock 31 candidates at estimated
integration cost X, while electromagnetics would unlock 4.'"

THE HONESTY DISCLOSURE THIS ARTIFACT CARRIES (Art. XV/XXXII): the
selection is FORMULA-SENSITIVE. Under the operator's simple three-
factor shape (U x G / C) elmer leads; under the full six-factor
shape (which adds the operator's own validation-maturity and
automation-feasibility factors) sfepy leads. Both rankings are
reported, the decisive factors are named, and the measured
installability fact (sfepy: pip-resolvable in THIS environment,
measured by dry-run; elmer: system binary absent, measured by the
availability probe — the Phase 6 wiring standard 'at least one real
candidate must traverse the complete path' is executable ONLY for
sfepy here) is recorded as the practical tie-breaker.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.physics_stack.opportunity import (  # noqa: E402
    compute_opportunity_score, solver_factor_table,
)

#: THE DECISION-TIME STATE (Art. XI): at the Phase 5 decision moment
#: the ONLY measured-INSTALLED solver was hydraulic_network_1d.
#: The frozen decision artifact is computed with this set so a
#: post-wiring re-run can never silently rewrite the decision (the
#: LIVE query — 'which solver is missing NEXT' — now excludes
#: sfepy, and that state-dependence is tested, not hidden).
DECISION_TIME_INSTALLED = {"hydraulic_network_1d"}

OUT_PATH = (REPO / "R413" / "PHYSICS_STACK_V1"
            / "PHYSICS_GAP_OPPORTUNITY_SCORE_V1.json")
MATRIX_PATH = (REPO / "R13" if False else REPO / "R413"
               / "PHYSICS_STACK_V1" / "PHYSICS_COVERAGE_MATRIX_V1.json")
BUILD_DATE = "2026-09-06"


def main() -> None:
    matrix = json.loads(MATRIX_PATH.read_text())
    result = compute_opportunity_score(
        matrix, installed_exclude=DECISION_TIME_INSTALLED)

    # the formula-sensitivity disclosure (computed, not asserted)
    by_simple = sorted(result["records"],
                       key=lambda r: (-r["operator_simple_score_UxG_div_C"],
                                      r["solver_id"]))
    simple_leader = by_simple[0]
    six_factor_leader = result["records"][0]

    doc = {
        "artifact_type": "R413_PHYSICS_GAP_OPPORTUNITY_SCORE_V1",
        "version": "1.0.0",
        "directive": "operator directive V2 Phase 5 + the Physics Gap "
                     "Opportunity Score (the operator's improvement "
                     "beyond the auditor): physics expansion as a "
                     "MEASURED discovery investment decision",
        "input_matrix": {
            "path": "R413/PHYSICS_STACK_V1/"
                    "PHYSICS_COVERAGE_MATRIX_V1.json",
            "sha256": hashlib.sha256(
                MATRIX_PATH.read_bytes()).hexdigest(),
        },
        "factor_tables_pre_registered": solver_factor_table(),
        "scores": result["records"],
        "selection": result["selected_solver"],
        "formula": result["formula"],
        "pre_registration_note": result["pre_registration_note"],
        "decision_time_state": {
            "installed_solvers_at_decision": sorted(
                DECISION_TIME_INSTALLED),
            "note": "the decision is computed over the decision-time "
                    "missing-solver set (sfepy was THEN the missing "
                    "top scorer); the LIVE forward query "
                    "('which solver is missing next') now excludes "
                    "the wired sfepy — the machine's question moves "
                    "on, the frozen decision does not (Art. XI)",
        },
        "FORMULA_SENSITIVITY_DISCLOSURE": {
            "six_factor_ranking_top3": [
                {"solver_id": r["solver_id"], "score": r["score"]}
                for r in result["records"][:3]],
            "operator_simple_ranking_top3": [
                {"solver_id": r["solver_id"],
                 "score": r["operator_simple_score_UxG_div_C"]}
                for r in by_simple[:3]],
            "finding": f"the two formulas disagree on the leader: "
                       f"the full six-factor formula selects "
                       f"{six_factor_leader['solver_id']} "
                       f"({six_factor_leader['score']:.1f}) while the "
                       f"operator's simple three-factor shape "
                       f"(U x G / C) leads with "
                       f"{simple_leader['solver_id']} "
                       f"({simple_leader['operator_simple_score_UxG_div_C']:.1f})",
            "decisive_factors": [
                "elmer's raw phenomenon coverage is larger (5 "
                "registered phenomena vs sfepy's 3: elmer adds "
                "heat_transfer and electromagnetic_fields_lowfreq) — "
                "it wins on U under the simple formula",
                "sfepy's integration cost is 3 vs elmer's 7 (MEASURED: "
                "sfepy is a pure-Python pip package resolvable in "
                "THIS environment by pip dry-run; elmer requires a "
                "system binary that is absent per the availability "
                "probe)",
                "sfepy's validation maturity is 3 vs elmer's 2 "
                "(sfepy ships a testsuite + analytical-solution "
                "examples replayable headless)",
                "sfepy's automation feasibility is 3 vs elmer's 2 "
                "(native Python API vs sif-case CLI)"
            ],
            "practical_decisive_fact": "the operator's Phase 6 standard "
                                       "is 'at least one real candidate "
                                       "must traverse the complete "
                                       "path' — only sfepy is "
                                       "installable in THIS environment "
                                       "(measured), so elmer cannot "
                                       "meet the Phase 6 standard here "
                                       "regardless of ranking",
            "classification": "the disagreement is disclosed, not "
                              "resolved by preference (Art. XV); the "
                              "selection rule was pre-registered as "
                              "the six-factor score (all six factors "
                              "are the operator's own list), and the "
                              "simple-formula disagreement is carried "
                              "on this artifact",
        },
        "provenance": {
            "builder": "scripts/r413_build_opportunity_score.py",
            "build_date": BUILD_DATE,
            "determinism": "byte-identical on re-run from the frozen "
                           "matrix (Art. LXII)",
            "llm_calls": 0,
        },
        "reviewer_provenance": "AI_REVIEW",
    }

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False)
                        + "\n")
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    print(f"wrote {OUT_PATH}")
    print(f"sha256: {digest}")
    print(f"SELECTED: {result['selected_solver']['solver_id']} "
          f"(score {result['selected_solver']['score']})")
    print(f"simple-formula leader: "
          f"{simple_leader['solver_id']} "
          f"({simple_leader['operator_simple_score_UxG_div_C']}) "
          "— DISCLOSED disagreement")


if __name__ == "__main__":
    main()
