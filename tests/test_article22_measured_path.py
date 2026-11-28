#!/usr/bin/env python3
"""tests/test_article22_measured_path.py — EPISTEMIC v3.2.0 Art. 22 CI
wiring (AM52/V49 ratification): the MEASURED-PATH declaration.

Grounded in F61 (auditor-verified): the holdouts measured a 559-line
wrapper while the engine is 3716 lines — a wrapper-only measurement is
an instrument failure. The CI: the integrated measurement route imports
the engine (mechanism_space), the routing decision is committed, and the
route's legality/contract tests stay wired — so a wrapper-only
measurement cannot silently return.

Zero LLM. Deterministic. No external calls.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

ENGINE_ROUTE = REPO / "discovery_fabric" / "engine" / "engine_route.py"


def test_measurement_route_imports_the_engine() -> None:
    """The integrated route's measured path runs through mechanism_space
    (the typed-operator engine) — a wrapper-only route is the F61
    failure and REDS."""
    src = ENGINE_ROUTE.read_text(encoding="utf-8")
    assert "mechanism_space" in src, (
        "engine_route.py must import mechanism_space — the measured path "
        "runs through the ENGINE (F61)")
    r = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, '.'); "
         "from discovery_fabric.engine import engine_route as er; "
         "import discovery_fabric.engine.mechanism_space as ms; "
         "assert ms is not None; print('engine-route imports engine')"],
        capture_output=True, text=True, cwd=REPO, timeout=60)
    assert r.returncode == 0, (
        f"live import failed: {r.stderr[-200:]}")


def test_routing_decision_committed_names_the_engine() -> None:
    """The routing decision record (F61 remedy) names mechanism_space as
    the measured path and types the wrapper's role."""
    dec = REPO / "eval" / "measured_path_decision_r47.json"
    assert dec.exists(), "the measured-path decision record is committed"
    doc = json.loads(dec.read_text(encoding="utf-8"))
    assert "mechanism_space" in doc.get("decision", ""), (
        "the decision must name mechanism_space as the measured path")


def test_ablation_criteria_evaluator_declares_the_path() -> None:
    """The pre-registered P2 ablation evaluator runs on the engine route,
    not a wrapper (the v9 gate will be measured through the engine)."""
    crit = REPO / "scripts" / "r53_p2_ablation_criteria.py"
    assert crit.exists(), "the pre-registered criteria evaluator exists"
    src = crit.read_text(encoding="utf-8")
    assert ("engine_route" in src) or ("mechanism_space" in src) or (
        "measured_path" in src), (
        "the ablation evaluator must declare/name the measured engine "
        "path (F61 class)")


def test_route_legality_tests_stay_wired() -> None:
    """The engine-route contract tests remain part of the battery (the
    v3.2.0 additions extend, never narrow — no verifier weakening)."""
    t = (REPO / "tests" / "test_engine_route.py").read_text(encoding="utf-8")
    for name in ("test_route_emits_1_1_schema_from_plan",
                 "test_route_physics_runs_only_with_supplied_inputs",
                 "test_route_contract_legality_is_recorded"):
        assert f"def {name}" in t, f"{name} must stay wired"


def test_f31e_measured_path_runs_through_the_engine() -> None:
    """R133 DIR-3 (the R131-F2/F63 debt): the F31e measured path —
    the check layer + the reviewer schema — resolves through
    discovery_fabric/engine/, not a scripts/-local definition. The
    historical scripts stay importable via thin re-export shims."""
    r = subprocess.run(
        [sys.executable, "-I", "-c",
         "import sys; sys.path.insert(0, '.'); "
         "sys.path.insert(0, 'scripts'); "
         "from discovery_fabric.engine.review_layer import check_layer; "
         "assert check_layer.__module__ == "
         "'discovery_fabric.engine.review_layer', check_layer.__module__; "
         "import r121_successor_run; "
         "assert r121_successor_run.check_layer is check_layer; "
         "from discovery_fabric.engine.review_layer import REVIEWER_FIX_SCHEMA; "
         "assert REVIEWER_FIX_SCHEMA['json_schema']['name'] == 'reviewer_fix'; "
         "from discovery_fabric.engine.prompts import ("
         "improved_directive, AUTHORING_DIRECTIVE); "
         "assert len(improved_directive()) == 762; "
         "print('f31e-path engine-routed')"],
        capture_output=True, text=True, cwd=REPO, timeout=120)
    assert r.returncode == 0, (
        f"the F31e path must resolve through the engine: "
        f"{r.stderr[-300:]}")


def test_panel_measured_path_runs_through_the_engine() -> None:
    """R133 DIR-2 (R132-F1): the panel's judging contract + tally
    logic live in the engine (blind_panel pair contract +
    panel_agreement R-CAL/swap-robust tally); the driver script is a
    thin transport/pacing layer (tests/_panel_engine_check.py)."""
    r = subprocess.run(
        [sys.executable, "-I",
         str(REPO / "tests" / "_panel_engine_check.py")],
        capture_output=True, text=True, cwd=REPO, timeout=120)
    assert r.returncode == 0, (
        f"the panel path must resolve through the engine: "
        f"{r.stderr[-400:]}")
