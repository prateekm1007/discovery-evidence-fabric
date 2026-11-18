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


# ---- 5. stated-reaction element conservation (R77, the HO9-05 class) ----
from r70_stated_formula_scan import (  # noqa: E402
    CONSERV_KEY, scan_reaction_conservation)


def test_ho9_05_phantom_carbon_fires():
    """The auditor-cited v9 defect: CO2 formed from a carbon-free
    H/N/O/Fe ammonia-synthesis system. The committed row must fire
    exactly once, naming C."""
    rows = list((REPO / "eval/holdout_v9_generation/rows")
                .glob("HO9-05-*.json"))
    if not rows:
        pytest.skip("v9 rows not in this tree")
    ans = json.loads(rows[0].read_text(encoding="utf-8"))["a1_answer"]
    f = scan_reaction_conservation(ans)
    assert len(f.get(CONSERV_KEY, [])) == 1
    msg = f[CONSERV_KEY][0]
    assert "element(s) C" in msg and "CO2" in msg


def test_v9_rows_exactly_one_conservation_fire():
    """The sweep: HO9-05 fires, the other 29 committed rows stay
    silent — the leg adds no noise to the scored corpus."""
    rows = sorted((REPO / "eval/holdout_v9_generation/rows")
                  .glob("HO9-*.json"))
    if not rows:
        pytest.skip("v9 rows not in this tree")
    fired = []
    for p in rows:
        ans = json.loads(p.read_text(encoding="utf-8"))["a1_answer"]
        if scan_reaction_conservation(ans).get(CONSERV_KEY):
            fired.append(p.name.split("-")[0] + "-" + p.name.split("-")[1])
    assert fired == ["HO9-05"], fired


def test_balanced_and_sourced_reactions_stay_silent():
    silent = [
        # reactants name every product element
        "The loop runs N2 + 3H2 -> 2NH3 over the promoted Fe catalyst.",
        "Calcination drives CaCO3 -> CaO + CO2 in the preheater vessel.",
        "Complete combustion: CH4 + 2O2 -> CO2 + 2H2O, flue to stack.",
        "Steam reforming CH4 + H2O -> CO + 3H2 runs at 850 C over Ni.",
        # the removed species is the process's own (sourced) species
        "The amine absorbs CO2 from the flue slipstream; regeneration "
        "releases the CO2 for compression.",
        # word-form / unparseable products (typed limitation)
        "The oxygen species are thermally reduced, forming water on "
        "the catalyst sites.",
        # ion lists after a process noun are not products
        "Scale formation is slowed by lowering the ionic activity "
        "product of the cations (Na+, Ca2+) at the wall.",
        # letter-subscripted variables are not species
        "Removal follows $r_{rem} = A \\exp(-Ea/RT) C_{O}$ kinetics.",
        # a named carbon source rescues the claim
        "Burning the carbon deposits, the oxygen species are oxidized "
        "into CO2 that leaves with the purge.",
    ]
    for s in silent:
        assert not scan_reaction_conservation(s), s[:60]


def test_unsourced_formation_fires():
    fire = ("This utilizes the exothermic heat to thermally oxidize "
            "the absorbed oxygen species into volatile "
            "$\\text{CO}_2$ before it poisons the iron sites.")
    f = scan_reaction_conservation(fire)
    assert CONSERV_KEY in f and "element(s) C" in f[CONSERV_KEY][0]
    fire_s = ("A side reaction forms SO2 in the absorber off-gas, "
              "raising the stack opacity index.")
    f2 = scan_reaction_conservation(fire_s)
    assert CONSERV_KEY in f2 and "element(s) O,S" in f2[CONSERV_KEY][0]


def test_conservation_joins_the_merged_formula_scan():
    """The machine's frozen call site imports only
    scan_stated_formula_direction — the conservation leg must ride
    inside its output (both question types share that call)."""
    ans = ("The exothermic heat thermally oxidizes the absorbed "
           "oxygen species into volatile $\\text{CO}_2$ on the iron "
           "sites before poisoning.")
    f = scan_stated_formula_direction(ans)
    assert CONSERV_KEY in f
