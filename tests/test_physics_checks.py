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


def test_arrhenius_closed_form_magnitude():
    # F93 (R114 dir 3, the auditor's finding): the MAGNITUDE test the
    # sign-only suite lacked. The historical exponent divided the
    # already-J/mol Ea by (R * 1000) — every magnitude wrong by 1000x
    # in the exponent, every DIRECTION still right (which is exactly
    # why the sign-only tests above never caught it). This test pins
    # the closed form k2/k1 = exp(-Ea/R (1/T2 - 1/T1)) with Ea in
    # J/mol against an independent literal recomputation — a magnitude
    # regression of ANY size reds, not just a sign flip.
    import math
    R = 8.314462618  # J/(mol*K), the CODATA value the engine carries
    cases = [
        # (ea_kj_mol, t1_degC, t2_degC) — includes the REFERENCE
        # SCENARIO pair (80, 60, 80) whose pre-fix value 1.0016369748
        # was wrong (true 5.1327) and the adjudicated cure pair
        # (60, 150, 120) shared with thermoset_cure_residual_direction
        (80.0, 60.0, 90.0),   # big rise: ~10.87x
        (80.0, 90.0, 60.0),   # symmetric drop: ~0.0920x
        (60.0, 25.0, 35.0),   # the R113 demonstrated pair: ~2.19x
        (80.0, 60.0, 80.0),   # the reference scenario: ~5.13x
        (60.0, 150.0, 120.0),  # the cure axis: ~0.2722x
    ]
    for ea_kj, t1_c, t2_c in cases:
        r = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=ea_kj,
                         t1_degC=t1_c, t2_degC=t2_c)
        assert r["verdict"] == "RUN", (ea_kj, t1_c, t2_c, r)
        true_ratio = math.exp(
            -(ea_kj * 1000.0 / R)
            * (1.0 / (t2_c + 273.15) - 1.0 / (t1_c + 273.15)))
        assert abs(r["value"] - true_ratio) < 1e-9 * max(1.0, true_ratio), (
            f"magnitude regression: Ea={ea_kj} {t1_c}->{t2_c}C engine="
            f"{r['value']} closed-form={true_ratio} (the F93 x1000 "
            "exponent bug class — a magnitude error, not a sign one)")
    # the saturation path stays honest: the disclosed clamp fires only
    # beyond the double range, never on these in-range magnitudes
    big = pc.run_check("arrhenius_rate_ratio", ea_kj_mol=400.0,
                       t1_degC=20.0, t2_degC=200.0)
    assert big["verdict"] == "RUN"
    assert "saturated" not in big["detail"]


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
    "surge_margin": dict(p_surge_kpa=None, p_op_kpa=360.0),
    "fatigue_miner": dict(n_cycles=None, stress_amp_mpa=120.0,
                          sn_a_mpa_pow_b=1.0e12, sn_b=3.0),
    "breakthrough_capacity": dict(m_air_kg=None, w_in_kg_kg=0.010,
                                  w_out_kg_kg=0.001, m_desiccant_kg=10.0,
                                  q_e_kg_kg=0.125),
    "faraday_gas_rate": dict(current_after_a=None,
                             current_before_a=8000.0,
                             molar_mass_g_mol=32.0, z_electrons=4),
    "wagner_number": dict(conductivity_s_m=None,
                          polarization_slope_v_m2_a=0.02,
                          characteristic_length_m=0.3),
    "foam_index": dict(sigma_ref_mn_m=None, sigma_sludge_mn_m=45.0),
    "larson_miller_lmp": dict(t1_degC=None, t1_h=40000, t2_degC=600.0,
                              t2_h=60000),
}


def test_registry_has_nineteen_relations():
    # R54 (c-0072): 6 -> 12. R62 (claim c-0085): 12 -> 19 relations /
    # 31 failure classes. AM91 (claim c-0116): 19 -> 22 relations /
    # 34 failure classes (the v14 defect-class relations:
    # ammonia_strip_direction, vant_hoff_adsorption_direction,
    # aqueous_molarity_saturation_bound); the pin moves with the
    # registry (a stale literal reds — the R60-F1 lesson applied).
    # R113 F91 (dirs 3+4): 22 -> 23 relations / 34 -> 35 failure
    # classes (thermoset_cure_residual_direction, the new
    # cure_kinetics class — the computed cure/Arrhenius relation the
    # R113 adjudication routed HO15-10-class claims through).
    assert len(pc.CHECKS) == 23, sorted(pc.CHECKS)
    assert len(pc.CHECKS_BY_FAILURE_CLASS) == 35


def test_every_check_refuses_garbage_rather_than_fabricating():
    for cid, bad in BAD_INPUTS.items():
        r = pc.run_check(cid, **bad)
        assert r["verdict"] == "REFUSED", (cid, r)
        assert r["direction_of_effect"] == "unavailable"
        assert r["value"] is None


# --- R54 (claim c-0073): the F-V5 regression pins — out-of-domain
# inputs must return typed REFUSED through run_check, never raise.
# The identical defect class was verifier-filed (F-V5) and
# live-reproduced during the R53 P1-gate measurement on the r53s1
# lineage; the relay to the remote lineage did not carry the
# hardening, and all three crash classes reproduced LIVE at the
# remote tip before this fix. Content-preserving: every in-range
# value below is bit-identical to the pre-fix committed values.

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
    # F93 (R114 dir 3): this pin previously asserted 1.0 < value < 1.01
    # — it was pinning the BUGGY magnitude (the x1000 exponent bug:
    # pre-fix 1.0008-ish for this pair). The correct closed-form value
    # is ~10.87 (Ea/R = 9623 K, 1/363.15 - 1/333.15 = 2.48e-4); the
    # pin now brackets the TRUE magnitude, unsaturated.
    assert 10.0 < ok["value"] < 11.0


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


# ------------------------------------------------ R62 registry expansion
# (claim c-0085): the 7 new relations RUN on their reference scenarios,
# typed-REFUSE on their true degenerate axes, and the collision-sensitive
# router classes pin to the physically-right instrument.
def test_r62_expansion_reference_scenarios_all_run():
    for cid in ("archard_wear", "impact_erosion_rate",
                "contact_erosion_per_operation", "biogenic_acid_thinning",
                "microbial_growth_rate", "dust_layer_ignition_margin",
                "humidity_permeability_ratio"):
        r = pc.run_check(cid, **pc.REFERENCE_SCENARIOS[cid])
        assert r["verdict"] == "RUN", (cid, r)
        assert r["direction_of_effect"] == "worsens", (cid, r)


def test_r62_archard_wear_value_and_refusal():
    r = pc.run_check("archard_wear", load_n=500.0,
                     sliding_distance_m=50000.0, hardness_pa=1.0e8,
                     wear_coeff=2.0e-3)
    assert r["verdict"] == "RUN" and abs(r["value"] - 5e-4) < 1e-8
    bad = pc.run_check("archard_wear", load_n=500.0,
                       sliding_distance_m=50000.0, hardness_pa=0.0,
                       wear_coeff=2.0e-3)
    assert bad["verdict"] == "REFUSED" and "hardness" in (
        bad["detail"]["error"])


def test_r62_biogenic_acid_thinning_units():
    # 1.0 g H2S/m2/day * 0.85 * (98.08/34.08) = 7.104 g H2SO4/m2/day;
    # capacity 75 kg/m3 -> 7.104 g / 75000 g/m3 = 9.472e-5 m/day
    # = 0.03262 mm/day (the pint g/kg cancellation carries the units)
    r = pc.run_check("biogenic_acid_thinning", h2s_flux_g_m2_day=1.0,
                     acid_yield_fraction=0.85,
                     neutralization_capacity_kg_m3=75.0)
    assert r["verdict"] == "RUN"
    assert abs(r["value"] - 0.03262) < 5e-4
    assert r["unit"] == "mm/day"


def test_r62_microbial_q10_domain_refusal():
    bad = pc.run_check("microbial_growth_rate", mu_ref_per_day=0.25,
                       q10=0.0, t_degC=32.0, t_ref_degC=20.0, days=30.0)
    assert bad["verdict"] == "REFUSED"
    assert "Q10" in bad["detail"]["error"]


def test_r62_humidity_rh_domain_refusal():
    bad = pc.run_check("humidity_permeability_ratio",
                       alpha_per_rh_percent=0.09, rh_percent=150.0,
                       rh_ref_percent=0.0)
    assert bad["verdict"] == "REFUSED"
    assert "[0, 100]" in bad["detail"]["error"]


def test_r62_router_collision_pins():
    # the collision-sensitive texts route to the RIGHT instrument
    cls = pc.classify_failure
    assert cls("screed plate bottoms wear thin at the leading edge") \
        == "mechanical_wear"          # bare "leading edge" != rain erosion
    assert cls("rain and particle impact erode the leading-edge "
               "coating") == "leading_edge_erosion"
    assert cls("brush and slip-ring contact wear progresses to arcing") \
        == "electrical_contact_erosion"
    assert cls("opportunity charging drives electrolyte loss") \
        == "lead_acid_watering"
    assert cls("Electrolyte dry-out: sustained operation at high "
               "temperature drives solvent evaporation") \
        == "electrolyte_dryout"       # "dry-out" != desiccant context


def test_r62_router_covers_all_dev_rows():
    # the F64-deterministic recompute: every corpus row now routes to a
    # class whose checks RUN (the P1 coverage gap's root cause, closed)
    # this test pins the ROUTER (every corpus failure text resolves to
    # a class whose checks are mapped); the P1 recomputation itself is
    # the driver re-run committed beside the expansion
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from r58_p2_ablation_driver import load_dev_problems
    for p in load_dev_problems():
        c = pc.classify_failure(str(p.get("failure", "")))
        assert c is not None, f"{p['problem_id']}: still unrouted"
        assert pc.check_for_failure_class(c), (
            f"{p['problem_id']}: class {c} maps to no check")
