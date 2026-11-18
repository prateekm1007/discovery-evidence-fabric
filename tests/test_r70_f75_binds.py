#!/usr/bin/env python3
"""tests/test_r70_f75_binds.py — the AM63 directive acceptance tests:
F75 deliverable-class binds (refusal/identity/thrash never CLEAN),
the stated-formula direction contradiction (HO9-30 class), and the
monoculture-break chemistry elicitation. All deterministic, zero LLM."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

import pytest

from r70_deliverable_class_scan import (  # noqa: E402
    scan_deliverable_class, scan_refusal_shape, scan_identity_preamble,
    scan_thrash_leakage, REFUSAL_KEY, IDENTITY_KEY, THRASH_KEY)
from r70_stated_formula_scan import (  # noqa: E402
    scan_stated_formula_direction)
from r40_machine_v77 import effective_critic_verdict, F75_KEYS  # noqa: E402
from r29_a1w_v72_contract import contract_for_v72  # noqa: E402
from discovery_fabric.engine import population_search as ps  # noqa: E402

CONTROLS = json.loads((REPO / "eval" / "labelled_controls"
                       / "f75_deliverable_class_controls.json")
                      .read_text(encoding="utf-8"))


def _controls():
    return {c["id"]: c for c in CONTROLS["controls"]}


# ---- 1. the labelled control set -------------------------------------------
@pytest.mark.parametrize("cid", list(_controls().keys()))
def test_labelled_controls(cid):
    c = _controls()[cid]
    label = list(c["label"])
    findings = dict(scan_deliverable_class(c["text"]))
    findings.update(scan_stated_formula_direction(c["text"]))
    fired = set(findings)
    if label:
        for k in label:
            assert k in fired, (cid, k, fired)
    else:
        assert not fired, (cid, fired)


def test_no_false_clean_on_positives():
    """The acceptance clause: 0 false-CLEAN rows on the labelled set —
    every labelled positive forces the recorded verdict off CLEAN."""
    for cid, c in _controls().items():
        if not c["label"]:
            continue
        vio = dict(scan_deliverable_class(c["text"]))
        vio.update(scan_stated_formula_direction(c["text"]))
        verdict, note = effective_critic_verdict("CLEAN", vio)
        assert verdict != "CLEAN", (cid, verdict)
        assert note and note["f75_type_gate"]["forced_by"]


def test_machine_bind_edges():
    v, note = effective_critic_verdict("CLEAN", {})
    assert v == "CLEAN" and note is None
    v, note = effective_critic_verdict("FLAG", {})
    assert v == "FLAG" and note is None
    v, note = effective_critic_verdict(
        "CLEAN", {REFUSAL_KEY: ["opener evidence"]})
    assert v == "FLAG" and REFUSAL_KEY in note["f75_type_gate"][
        "forced_by"]
    # the hard-key tuple carries all four F75 classes
    assert set(F75_KEYS) >= {REFUSAL_KEY, IDENTITY_KEY, THRASH_KEY,
                             "STATED_FORMULA_DIRECTION_CONTRADICTION"}


# ---- 2. the real committed evidence bytes (read-only) ----------------------
def test_real_ho9_14_row_fires():
    p = REPO / "eval/holdout_v9_generation/rows"
    rows = list(p.glob("HO9-14-*.json"))
    if not rows:  # the canonical dir carries lane B; lane A is archived
        pytest.skip("v9 rows not in this tree")
    row = json.loads(rows[0].read_text(encoding="utf-8"))
    f = scan_deliverable_class(row["a1_answer"])
    assert REFUSAL_KEY in f and IDENTITY_KEY in f


def test_real_ho9_30_row_fires():
    p = REPO / "eval/holdout_v9_generation/rows"
    rows = list(p.glob("HO9-30-*.json"))
    if not rows:
        pytest.skip("v9 rows not in this tree")
    row = json.loads(rows[0].read_text(encoding="utf-8"))
    f = scan_stated_formula_direction(row["a1_answer"])
    assert "STATED_FORMULA_DIRECTION_CONTRADICTION" in f


# ---- 3. the generation directive bind --------------------------------------
def test_both_contracts_carry_the_deliverable_bind():
    for qt in ("intervention-proposal", "predictor-design"):
        contract = contract_for_v72(qt)
        assert "DELIVERABLE-CLASS BIND" in contract, qt


# ---- 4. monoculture-break chemistry elicitation ----------------------------
CHEM_PROBLEM = {
    "problem_id": "probe-chem-admits",
    "device": "digestor heater tubes",
    "failure": "aluminosilicate scale deposition on heater surfaces",
    "failure_mode": "heat-transfer loss from growing scale layer",
    "constraint": "no new sensors; use existing temperature and "
                  "pressure signals only",
    "question_type": "intervention-proposal",
    "user_variables": ["temperature", "pressure"],
}

MECHANICAL_PROBLEM = {
    "problem_id": "probe-mech-only",
    "device": "conveyor drive belt",
    "failure": "belt misalignment causing edge wear",
    "failure_mode": "premature belt edge wear",
    "constraint": "no new sensors; visual inspection only",
    "question_type": "intervention-proposal",
    "user_variables": ["visual_inspection"],
}

CLAMPED_PROBLEM = {
    "problem_id": "probe-clamped",
    "device": "digestor heater tubes",
    "failure": "aluminosilicate scale deposition on heater surfaces",
    "failure_mode": "heat-transfer loss from growing scale layer",
    "constraint": "allowed measures: geometry redesign of the heater "
                  "surface. No new sensors.",
    "question_type": "intervention-proposal",
    "user_variables": ["temperature"],
}


def test_chemistry_elicited_when_admitted():
    plans = ps.enumerate_plans(CHEM_PROBLEM)
    assert len(plans) >= 3
    assert plans[0]["measure_class"] == "chemistry", (
        "the population must LEAD with chemistry when the failure "
        "class admits it (AM63 d2)")
    assert any(p.get("chemistry_elicited") or p["measure_class"]
               == "chemistry" for p in plans)


def test_no_elicitation_when_not_admitted():
    plans = ps.enumerate_plans(MECHANICAL_PROBLEM)
    assert not any(p["measure_class"] == "chemistry" for p in plans)
    assert not any(p.get("chemistry_elicited") for p in plans)


def test_declared_domain_clamp_still_wins():
    plans = ps.enumerate_plans(CLAMPED_PROBLEM)
    domain = ps.declared_domain_classes(CLAMPED_PROBLEM)
    assert domain and "chemistry" not in domain
    assert all(p["measure_class"] in domain for p in plans), (
        "the P1.4 clamp narrows; elicitation must not fight it")
    assert not any(p.get("chemistry_elicited") for p in plans)


def test_winner_rule_still_picks_chemistry_first_when_admitted():
    """The pre-registered rule (first contract-satisfied non-duty_cycle
    in population order) is UNCHANGED — the elicitation works through
    population order only. Mirror the driver's rule here."""
    plans = ps.enumerate_plans(CHEM_PROBLEM)
    first_non_sched = next(p for p in plans
                           if p["measure_class"] != "duty_cycle")
    assert first_non_sched["measure_class"] == "chemistry"
