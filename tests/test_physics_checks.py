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
