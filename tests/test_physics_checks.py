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
