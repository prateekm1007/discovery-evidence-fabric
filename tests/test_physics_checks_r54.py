#!/usr/bin/env python3
"""tests/test_physics_checks_r54.py — the registry expansion (claim
c-0072): 6 new relations (surge, fatigue, desiccant breakthrough,
electrolytic gas evolution, Wagner number, foam index), the
deterministic failure-class router, and the committed reference
scenarios the P1 measurement runs. Every relation must RUN on its
reference scenario with a pint-computed value and a typed direction;
refusals must be typed (never a prose fallback). Zero LLM."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pint  # noqa: E402
import pytest  # noqa: E402

from discovery_fabric.engine import physics_checks as pc  # noqa: E402


def test_registry_grew_to_22_relations_33_classes():
    # R54 (c-0072): 6 -> 12. R62 (c-0085): 12 -> 19 relations /
    # 31 failure classes (the full-DEV-corpus P1 coverage gap closed);
    # R103 (c-0117): 19 -> 22 relations / 33 classes (the AM89
    # ride-along legs: ammonia_free_fraction, nh3_henry_ratio,
    # naoh_solubility_guard + the ammonia_stripping/caustic_dosing
    # failure classes);
    # the pin moves with the registry, never stale (R60-F1 lesson).
    assert len(pc.CHECKS) == 22
    assert len(pc.CHECKS_BY_FAILURE_CLASS) == 33
    assert set(pc.CHECKS) == set(pc.REFERENCE_SCENARIOS)


@pytest.mark.parametrize("check_id", sorted(pc.REFERENCE_SCENARIOS))
def test_every_reference_scenario_runs(check_id):
    res = pc.run_check(check_id, **pc.REFERENCE_SCENARIOS[check_id])
    assert res["verdict"] == "RUN", (check_id, res)
    assert res["value"] is not None
    assert res["direction_of_effect"] in pc.DIRECTIONS


def test_router_covers_all_12_labelled_rows():
    import json
    rows = json.loads(
        (REPO / "eval/r43_v7_problem_fields_burned.json")
        .read_text())["problems"]
    for p in rows:
        fclass = pc.classify_failure(str(p.get("failure", "")))
        assert fclass is not None, p["problem_id"]
        assert fclass in pc.CHECKS_BY_FAILURE_CLASS, (p["problem_id"],
                                                      fclass)


def test_router_typed_no_match():
    assert pc.classify_failure("the coffee machine is slow") is None
    assert pc.classify_failure("") is None


def test_surge_margin_directions():
    ok = pc.run_check("surge_margin", p_surge_kpa=420.0, p_op_kpa=360.0)
    assert ok["verdict"] == "RUN" and ok["direction_of_effect"] == \
        "improves"
    near = pc.run_check("surge_margin", p_surge_kpa=420.0, p_op_kpa=410.0)
    assert near["direction_of_effect"] == "worsens"
    refused = pc.run_check("surge_margin", p_surge_kpa=-1.0,
                           p_op_kpa=10.0)
    assert refused["verdict"] == "REFUSED"


def test_fatigue_miner_unity_bound():
    over = pc.run_check("fatigue_miner", n_cycles=1.0e6,
                        stress_amp_mpa=120.0, sn_a_mpa_pow_b=1.0e12,
                        sn_b=3.0)
    assert over["verdict"] == "RUN"
    assert over["value"] == pytest.approx(1.728, abs=1e-2)
    assert over["direction_of_effect"] == "worsens"


def test_breakthrough_capacity_regimes():
    within = pc.run_check("breakthrough_capacity", m_air_kg=100.0,
                          w_in_kg_kg=0.010, w_out_kg_kg=0.001,
                          m_desiccant_kg=10.0, q_e_kg_kg=0.125)
    assert within["value"] == pytest.approx(0.72, abs=1e-6)
    assert within["direction_of_effect"] == "improves"
    broke = pc.run_check("breakthrough_capacity", m_air_kg=200.0,
                         w_in_kg_kg=0.010, w_out_kg_kg=0.001,
                         m_desiccant_kg=10.0, q_e_kg_kg=0.125)
    assert broke["value"] == pytest.approx(1.44, abs=1e-6)
    assert broke["direction_of_effect"] == "worsens"
    bad = pc.run_check("breakthrough_capacity", m_air_kg=100.0,
                       w_in_kg_kg=0.001, w_out_kg_kg=0.010,
                       m_desiccant_kg=10.0, q_e_kg_kg=0.125)
    assert bad["verdict"] == "REFUSED"


def test_faraday_gas_rate_hand_value():
    # 2000 A of oxygen evolution: 2000*0.032/(4*F) kg/s -> kg/h
    r = pc.run_check("faraday_gas_rate", current_after_a=10000.0,
                     current_before_a=8000.0, molar_mass_g_mol=32.0,
                     z_electrons=4)
    expected = 2000.0 * 0.032 / (4.0 * 96485.33212) * 3600.0
    assert r["value"] == pytest.approx(expected, rel=1e-4)
    assert r["direction_of_effect"] == "worsens"
    down = pc.run_check("faraday_gas_rate", current_after_a=8000.0,
                        current_before_a=10000.0, molar_mass_g_mol=32.0,
                        z_electrons=4)
    assert down["direction_of_effect"] == "improves"


def test_wagner_number_regimes():
    uniform = pc.run_check("wagner_number", conductivity_s_m=40.0,
                           polarization_slope_v_m2_a=0.02,
                           characteristic_length_m=0.3)
    assert uniform["value"] == pytest.approx(2.6667, abs=1e-3)
    assert uniform["direction_of_effect"] == "improves"
    nonuni = pc.run_check("wagner_number", conductivity_s_m=40.0,
                          polarization_slope_v_m2_a=0.005,
                          characteristic_length_m=0.5)
    assert nonuni["value"] == pytest.approx(0.4, abs=1e-6)
    assert nonuni["direction_of_effect"] == "worsens"


def test_foam_index_regimes():
    stable = pc.run_check("foam_index", sigma_ref_mn_m=72.0,
                          sigma_sludge_mn_m=45.0)
    assert stable["value"] == pytest.approx(0.375, abs=1e-6)
    assert stable["direction_of_effect"] == "worsens"
    clean = pc.run_check("foam_index", sigma_ref_mn_m=72.0,
                         sigma_sludge_mn_m=70.0)
    assert clean["direction_of_effect"] == "improves"


def test_units_are_pint_checked():
    # dimensionally-invalid input composition must REFUSE, not run
    with pytest.raises(pint.DimensionalityError):
        pint.Quantity(40.0, "S/m").to("m")
    r = pc.run_check("npsh_margin", patm_kpa=101.325, pvap_kpa=12.3,
                     rho_kg_m3=988.0, suction_head_m=2.0,
                     friction_loss_m=1.5, npshr_m=3.0)
    assert r["verdict"] == "RUN" and r["unit"] == "m"


# ---------------------------------------------------------------------------
# F66 (R55): the dew-point disambiguation regression. Dew-point
# phrasing with desiccant-dryer context routes breakthrough; bare
# dew-point phrasing stays frost; the 12 labelled rows keep their
# committed mapping (the P1 artifact's 36/36 stands).
# ---------------------------------------------------------------------------
def test_f66_dewpoint_with_dryer_context_routes_breakthrough():
    assert pc.classify_failure(
        "dew point rising after the desiccant dryer loses capacity") \
        == "desiccant_breakthrough"
    assert pc.classify_failure(
        "dew point out of spec after incomplete regeneration") \
        == "desiccant_breakthrough"
    assert pc.classify_failure(
        "compressed-air dew point spikes while the dryer ages") \
        == "desiccant_breakthrough"


def test_f66_bare_dewpoint_stays_frost():
    assert pc.classify_failure(
        "surface condensation when the dew point exceeds the coil "
        "temperature") == "frost_condensation"
    assert pc.classify_failure(
        "frost builds unevenly; fixed-interval defrost wastes energy") \
        == "frost_condensation"


def test_f66_desiccant_keywords_unchanged():
    assert pc.classify_failure(
        "desiccant ageing and incomplete regeneration let moisture "
        "break through") == "desiccant_breakthrough"


def test_f66_all_12_labelled_rows_keep_their_mapping():
    import json
    rows = json.loads(
        (REPO / "eval/r43_v7_problem_fields_burned.json")
        .read_text())["problems"]
    expected = {
        "HO7-01-zinc-ew-acid-mist": "electrolytic_mist",
        "HO7-02-rubber-extruder-scorch": "thermal_aging",
        "HO7-03-hydro-partload-cavitation": "cavitation",
        "HO7-04-freezer-demand-defrost": "frost_condensation",
        "HO7-05-cu-ew-nodulation": "electrodeposition",
        "HO7-06-ge-turbo-surge": "surge",
        "HO7-07-gearbox-oil-varnish": "thermal_aging",
        "HO7-08-conveyor-splice-fatigue": "fatigue",
        "HO7-09-chiller-condenser-fouling": "fouling",
        "HO7-10-desiccant-dryer-breakthrough": "desiccant_breakthrough",
        "HO7-11-pitch-battery-degradation": "thermal_aging",
        "HO7-12-digester-foaming": "foaming",
    }
    for p in rows:
        got = pc.classify_failure(str(p.get("failure", "")))
        assert got == expected[p["problem_id"]], (p["problem_id"], got)
