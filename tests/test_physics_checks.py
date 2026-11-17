#!/usr/bin/env python3
"""tests/test_physics_checks.py — P1.1 computed-physics slice tests.

The registry is the only path (unknown id = typed refusal); unit
discipline binds; the direction-of-effect is the SIGN of the computed
result on known-answer cases. Zero LLM, zero network.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from discovery_fabric.engine import physics_checks as pc  # noqa: E402


def test_registry_refuses_unknown_check_id():
    r = pc.run_check("no_such_check", x=1)
    assert r["verdict"] == "REFUSED"
    assert r["direction_of_effect"] == "unavailable"


def test_arrhenius_known_answer_directions():
    # a temperature RISE must compute rate_ratio > 1 -> worsens
    hot = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                       t1_degC=60.0, t2_degC=90.0)
    assert hot["verdict"] == "RUN"
    assert hot["value"] > 1.0
    assert hot["direction_of_effect"] == "worsens"
    # the same drop in temperature reverses the direction — the SIGN
    # of the computed result, never prose
    cool = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                        t1_degC=90.0, t2_degC=60.0)
    assert cool["verdict"] == "RUN"
    assert cool["value"] < 1.0
    assert cool["direction_of_effect"] == "improves"
    # isothermal -> neutral
    same = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                        t1_degC=60.0, t2_degC=60.0)
    assert same["value"] == 1.0
    assert same["direction_of_effect"] == "neutral"


def test_fouling_u_degradation_sign_and_refusal():
    # added fouling resistance (rf_after > rf_before=0) loses duty
    degraded = pc.run_check("fouling_u_degradation",
                            u_clean_w_m2k=2000.0,
                            rf_after_m2k_w=4e-4)
    assert degraded["verdict"] == "RUN"
    assert degraded["value"] < 1.0
    assert degraded["direction_of_effect"] == "worsens"
    u_after = degraded["detail"]["u_after_w_m2k"]
    # known answer: 1/(1/2000 + 4e-4) = 1/(5e-4+4e-4) = 1111.11...
    assert abs(u_after - 1.0 / (1.0 / 2000.0 + 4e-4)) < 0.01
    # negative fouling resistance is a physical refusal, not a number
    neg = pc.run_check("fouling_u_degradation", u_clean_w_m2k=2000.0,
                       rf_after_m2k_w=-1e-4)
    assert neg["verdict"] == "REFUSED"
    # non-positive U is refused too
    assert pc.run_check("fouling_u_degradation", u_clean_w_m2k=0.0,
                        rf_after_m2k_w=0.0)["verdict"] == "REFUSED"


def test_langelier_lsi_scale_forming_direction():
    # scale-forming water (LSI > 0) at high pH
    scale = pc.run_check("langelier_lsi", tds_mg_l=800.0,
                         temp_degC=60.0, ca_hardness_mg_l_caco3=200.0,
                         alkalinity_mg_l_caco3=150.0, ph=8.6)
    assert scale["verdict"] == "RUN"
    assert scale["value"] > 0
    assert scale["direction_of_effect"] == "worsens"
    # the same water at lower pH flips the sign — direction is
    # computed, never asserted
    soft = pc.run_check("langelier_lsi", tds_mg_l=800.0,
                        temp_degC=60.0, ca_hardness_mg_l_caco3=200.0,
                        alkalinity_mg_l_caco3=150.0, ph=6.6)
    assert soft["value"] < scale["value"]
    # out-of-domain pH is a typed refusal
    bad = pc.run_check("langelier_lsi", tds_mg_l=800.0,
                       temp_degC=60.0, ca_hardness_mg_l_caco3=200.0,
                       alkalinity_mg_l_caco3=150.0, ph=15.0)
    assert bad["verdict"] == "REFUSED"


def test_failure_class_routing():
    assert "langelier_lsi" in pc.check_for_failure_class("scaling")
    assert "arrhenius_rate_ratio" in pc.check_for_failure_class(
        "thermal_aging")
    assert pc.check_for_failure_class("unknown_class") == []


def test_npsh_margin_sign_and_refusal():
    # healthy suction: big atmospheric head, flooded suction -> RUN, > 0
    ok = pc.run_check("npsh_margin", patm_kpa=101.3, pvap_kpa=2.3,
                      rho_kg_m3=998.0, suction_head_m=2.0,
                      friction_loss_m=0.3, npshr_m=0.5)
    assert ok["verdict"] == "RUN" and ok["value"] > 0
    assert ok["direction_of_effect"] == "improves"
    # starving suction: hot fluid, deep lift, heavy friction — the
    # atmospheric head (~5.8 m for 80 C water) is consumed -> <= 0
    bad = pc.run_check("npsh_margin", patm_kpa=101.3, pvap_kpa=47.0,
                       rho_kg_m3=958.0, suction_head_m=-5.0,
                       friction_loss_m=1.5, npshr_m=1.0)
    assert bad["verdict"] == "RUN" and bad["value"] <= 0
    assert bad["direction_of_effect"] == "worsens"


def test_dewpoint_frost_margin_known_answer():
    # air 30 C at 60 % RH -> dewpoint ~ 21.4 C; a 25 C surface clears
    ok = pc.run_check("dewpoint_frost_margin", t_air_degC=30.0,
                      rh_percent=60.0, t_surface_degC=25.0)
    assert ok["verdict"] == "RUN"
    assert 3.0 < ok["value"] < 4.5
    assert ok["direction_of_effect"] == "improves"
    # the same surface under saturated air condenses -> worsens
    bad = pc.run_check("dewpoint_frost_margin", t_air_degC=30.0,
                       rh_percent=95.0, t_surface_degC=25.0)
    assert bad["value"] < 0
    assert bad["direction_of_effect"] == "worsens"


def test_larson_miller_comparator_sign():
    # hotter + longer at temperature = harsher creep regime
    harsh = pc.run_check("larson_miller_lmp", t1_degC=540.0, t1_h=40000,
                         t2_degC=600.0, t2_h=60000)
    assert harsh["verdict"] == "RUN" and harsh["value"] > 0
    assert harsh["direction_of_effect"] == "worsens"
    cool = pc.run_check("larson_miller_lmp", t1_degC=600.0, t1_h=60000,
                        t2_degC=540.0, t2_h=40000)
    assert cool["value"] < 0
    assert cool["direction_of_effect"] == "improves"


BAD_INPUTS = {
    "arrhenius_rate_ratio": dict(ea_kj_mol=None, t1_degC=60.0,
                                 t2_degC=90.0),
    "fouling_u_degradation": dict(u_clean_w_m2k=None,
                                  rf_after_m2k_w=0.0,
                                  rf_before_m2k_w=0.0),
    "langelier_lsi": dict(tds_mg_l=None, temp_degC=25.0,
                          ca_hardness_mg_l_caco3=100.0,
                          alkalinity_mg_l_caco3=80.0, ph=7.5),
    "npsh_margin": dict(patm_kpa=None, pvap_kpa=2.3, rho_kg_m3=998.0,
                        suction_head_m=2.0, friction_loss_m=0.3,
                        npshr_m=0.5),
    "dewpoint_frost_margin": dict(t_air_degC=None, rh_percent=60.0,
                                  t_surface_degC=25.0),
    "larson_miller_lmp": dict(t1_degC=None, t1_h=40000, t2_degC=600.0,
                              t2_h=60000),
}


def test_registry_has_six_relations():
    assert len(pc.CHECKS) == 6, sorted(pc.CHECKS)


def test_every_check_refuses_garbage_rather_than_fabricating():
    for cid, bad in BAD_INPUTS.items():
        r = pc.run_check(cid, **bad)
        assert r["verdict"] == "REFUSED", (cid, r)
        assert r["direction_of_effect"] == "unavailable"
        assert r["value"] is None


# --- R53 (claim c-0073): the F-V5 regression pins — out-of-domain
# inputs return TYPED refusals, never uncaught raises (the V8.1.2
# 1995f7e75 lesson re-incident, caught live during the R53 P1-gate
# measurement)
def test_arrhenius_zero_kelvin_typed_refusal_not_raise():
    # T2 = -273.15 degC = 0 K raised ZeroDivisionError through
    # run_check before the F-V5 fix
    r = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                     t1_degC=60.0, t2_degC=-273.15)
    assert r["verdict"] == "REFUSED"
    assert r["value"] is None
    assert "out_of_domain" in r["detail"]["error"]
    # the same for the baseline side
    r2 = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                      t1_degC=-273.15, t2_degC=60.0)
    assert r2["verdict"] == "REFUSED"


def test_arrhenius_exponent_saturation_disclosed_in_band():
    # synthetic stress inputs (disclosed as such): an absurd Ea with a
    # large temperature step saturates the exponent at the
    # double-precision bound instead of raising OverflowError; the
    # clamp is disclosed in-band and the direction follows the clamped
    # value (the 1995f7e75 pattern)
    r = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=2.5e9,
                     t1_degC=20.0, t2_degC=1000.0)
    assert r["verdict"] == "RUN"
    assert r["value"] == 1e308
    assert r["direction_of_effect"] == "worsens"
    assert "saturated" in r["detail"]
    # the lower bound saturates to 0.0 = improves
    r2 = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=2.5e9,
                      t1_degC=1000.0, t2_degC=20.0)
    assert r2["verdict"] == "RUN"
    assert r2["value"] == 0.0
    assert r2["direction_of_effect"] == "improves"
    # in-range values are UNAFFECTED by the clamp (no saturation key)
    ok = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=80.0,
                      t1_degC=60.0, t2_degC=90.0)
    assert "saturated" not in ok["detail"]
    assert 1.0 < ok["value"] < 1.01


def test_dewpoint_absurd_drybulb_typed_refusal_not_raise():
    # a dry-bulb at/below the Magnus-Tetens floor (-243.04 degC) would
    # divide by zero in the alpha term before the F-V5 guard
    r = pc.run_check("dewpoint_frost_margin", t_air_degC=-243.04,
                     rh_percent=60.0, t_surface_degC=-250.0)
    assert r["verdict"] == "REFUSED"
    assert "out_of_domain" in r["detail"]["error"]


def test_npsh_zero_rho_typed_refusal_not_raise():
    # rho = 0 raised ZeroDivisionError inside pint BEFORE the F-V5
    # guard-order fix (the guard existed but ran after the division)
    r = pc.run_check("npsh_margin", patm_kpa=101.3, pvap_kpa=2.3,
                     rho_kg_m3=0.0, suction_head_m=2.0,
                     friction_loss_m=0.3, npshr_m=0.5)
    assert r["verdict"] == "REFUSED"
    assert "out_of_domain" in r["detail"]["error"]
