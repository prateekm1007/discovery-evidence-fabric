#!/usr/bin/env python3
"""tests/test_engine_route.py — the integrated-path tests (P1.3).

The route must: bind legal plans only, emit the 1.1.0 schema fields
FROM THE PLAN (schema-sourced, never prose-parsed), keep the 1.0.0
candidate hash untouched by the extension, record physics checks as
RUN only with supplied inputs (PENDING_INPUTS otherwise — Art. XXV),
and gate the row's novelty deterministically. Zero LLM, zero network.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import engine_route as er  # noqa: E402
from discovery_fabric.engine import population_search as ps  # noqa: E402

PROBLEM = {
    "problem_id": "route-test-sofc-1",
    "device": "a marine diesel engine cooling circuit",
    "failure": "fouling deposits build up on the cooler tube walls "
               "and reduce heat rejection",
    "failure_mode": "fouling-driven heat-rejection loss",
    "constraint": "must use existing temperature and flow measurements "
                  "only; online sensors already installed (temperature, "
                  "flow_rate)",
    "failure_class": "fouling",
}


def _first_plan():
    return ps.enumerate_plans(PROBLEM)[0]


def test_route_emits_1_1_schema_from_plan():
    r = er.run_integrated_candidate(PROBLEM, _first_plan())
    c = r["candidate"]
    assert c["candidate_schema"] == "mechanism_candidate/1.1.0"
    assert c["measure_class"] == _first_plan()["measure_class"]
    assert c["principle_id"] == _first_plan()["principle_id"]
    assert c["mechanism_class"] == _first_plan()["measure_class"]
    assert c["signals_used"] == _first_plan()["signals_used"]
    assert r["trace"]["candidate_schema"] == "mechanism_candidate/1.1.0"


def test_route_keeps_1_0_hash_and_candidate_state():
    r = er.run_integrated_candidate(PROBLEM, _first_plan())
    assert r["trace"]["candidate_hash_1_0_0"] == \
        r["candidate"]["candidate_hash"]
    assert r["candidate"]["candidate_state"] in (
        "CANDIDATE", "NOT_A_CANDIDATE_NO_TESTABLE_PREDICTION")


def test_route_physics_runs_only_with_supplied_inputs():
    r = er.run_integrated_candidate(PROBLEM, _first_plan())
    ids = [p["check_id"] for p in r["physics"]]
    assert ids, "the fouling class must have applicable checks"
    assert all(p["verdict"] == "PENDING_INPUTS" for p in r["physics"])
    r2 = er.run_integrated_candidate(
        PROBLEM, _first_plan(),
        physics_inputs={"fouling_u_degradation": {
            "u_clean_w_m2k": 2500.0, "rf_after_m2k_w": 0.0004,
            "rf_before_m2k_w": 0.0002}})
    ran = [p for p in r2["physics"]
           if p["check_id"] == "fouling_u_degradation"]
    assert ran and ran[0]["verdict"] == "RUN"
    # direction = SIGN of the computed duty ratio (< 1 = worsens)
    assert ran[0]["direction_of_effect"] == "worsens"


def test_route_row_gates_novelty_and_runs_all_plans():
    row = er.run_row(PROBLEM)
    assert len(row["results"]) >= ps.K
    assert row["novelty_gate"]["verdicts"]
    # the deterministic route template varies the plan fields, so the
    # row must not collapse into duplicates
    assert row["novelty_gate"]["rejected"] == 0


def test_route_contract_legality_is_recorded():
    plans = ps.enumerate_plans(PROBLEM)
    for p in plans:
        r = er.run_integrated_candidate(PROBLEM, p)
        assert r["trace"]["operator_id"] == p["operator_id"]
        assert p["contract_satisfied"] is True
