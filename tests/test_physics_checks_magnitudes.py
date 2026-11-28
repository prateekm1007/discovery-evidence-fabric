#!/usr/bin/env python3
"""tests/test_physics_checks_magnitudes.py — F95 (R116 dir 3): the
closed-form MAGNITUDE cross-check for EVERY relation in the CHECKS
registry.

The F93 lesson (R114, arrhenius x1000): the sign-only suite hid a
magnitude-wrong value behind a green gate for 6+ rounds — every
direction was right, every magnitude 1000x off in the exponent. The
arrhenius closed-form test that closed F93 exists for ONE relation;
this suite extends the same discipline to ALL of them: each relation
is asserted against an INDEPENDENT literal recomputation of its
closed form (constants spelled here, never imported from the engine),
at tight relative tolerance — a magnitude regression of ANY size on
ANY relation reds CI, not just a sign flip.

Registry-completeness is fail-closed (the Art. 3 F67 pattern): a new
relation without a magnitude row reds here until one is added.

Conventions pinned per relation (from the engine source, read
line-by-line): relations that return round(x, k) are compared at
1e-9 rel-tol against the independently computed round(literal, k);
relations that return float(f"{x:.4g}") are compared at 1e-9 rel-tol
against float(f"{literal:.4g}") — the formatting is a display
convention, the physics is in the literal, and a x1000-class error
cannot hide in either. Zero LLM, zero network.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import physics_checks as pc  # noqa: E402

# physical constants as INDEPENDENT literals (never imported from the
# engine module under test)
R_GAS = 8.314462618            # J/(mol*K), CODATA
G_STD = 9.80665                # m/s^2
F_FARADAY = 96485.33212        # C/mol
MAGNUS_A, MAGNUS_B = 17.625, 243.04
H2SO4_OVER_H2S = 98.08 / 34.08  # molar-mass ratio, full oxidation

REL_TOL = 1e-9


def _close(engine_val, true_val, rel=REL_TOL):
    return abs(engine_val - true_val) <= rel * max(1.0, abs(true_val))


def _fmt4g(x):
    return float(f"{x:.4g}")


# ---------------------------------------------------------------------------
# the per-relation magnitude rows. Each entry: (check_id, kwargs,
# closed_form) where closed_form() -> float is the independent literal
# recomputation of the relation's PRIMARY value (the `value` field).
# ---------------------------------------------------------------------------
def _cf_arrhenius():
    ea_kj, t1_c, t2_c = 80.0, 60.0, 90.0
    true = math.exp(-(ea_kj * 1000.0 / R_GAS)
                    * (1.0 / (t2_c + 273.15)
                       - 1.0 / (t1_c + 273.15)))
    return true  # unrounded in the engine


def _cf_thermoset_cure():
    t1_c, t2_c, ea_kj = 150.0, 120.0, 60.0
    ratio = math.exp(-(ea_kj * 1000.0 / R_GAS)
                     * (1.0 / (t2_c + 273.15)
                        - 1.0 / (t1_c + 273.15)))
    return round(ratio, 6)  # engine rounds to 6


def _cf_fouling():
    u, rf_a, rf_b = 2000.0, 4e-4, 0.0
    return ((1.0 / (1.0 / u + rf_a))
            / (1.0 / (1.0 / u + rf_b)))  # unrounded


def _cf_langelier():
    tds, t, ca, alk, ph = 800.0, 60.0, 200.0, 150.0, 8.6
    a = (math.log10(tds) - 1.0) / 10.0
    b = -13.12 * math.log10(t + 273.0) + 34.55
    c = math.log10(ca) - 0.4
    d = math.log10(alk)
    return ph - ((9.3 + a + b) - (c + d))  # unrounded


def _cf_npsh():
    patm, pvap, rho, hs, hf, npshr = (101.3, 2.3, 998.0, 2.0,
                                      0.3, 0.5)
    head = (patm - pvap) * 1000.0 / (rho * G_STD)
    return round(head + hs - hf - npshr, 4)  # engine rounds to 4


def _cf_dewpoint():
    t_air, rh, t_surf = 30.0, 60.0, 25.0
    alpha = math.log(rh / 100.0) + MAGNUS_A * t_air / (
        MAGNUS_B + t_air)
    td = MAGNUS_B * alpha / (MAGNUS_A - alpha)
    return round(t_surf - td, 3)  # engine rounds to 3


def _cf_larson_miller():
    t1_c, t1_h, t2_c, t2_h = 540.0, 40000.0, 600.0, 60000.0
    lmp1 = (t1_c + 273.15) * (20.0 + math.log10(t1_h))
    lmp2 = (t2_c + 273.15) * (20.0 + math.log10(t2_h))
    return round(lmp2 - lmp1, 1)  # engine rounds to 1


def _cf_surge():
    ps, po = 300.0, 250.0
    return round((ps - po) / ps, 4)


def _cf_fatigue():
    n, s, a, b = 1e6, 200.0, 800.0, 5.0
    return round(n / (a * s ** (-b)), 4)


def _cf_breakthrough():
    m_air, w_in, w_out, m_des, q_e = (1.0, 0.010, 0.001, 10.0,
                                      0.125)
    return round(m_air * (w_in - w_out) / (m_des * q_e), 4)


def _cf_faraday():
    ia, ib, m_g, z = 9000.0, 8000.0, 32.0, 4
    m_kg = m_g / 1000.0
    delta_kg_h = (ia - ib) * m_kg / (z * F_FARADAY) * 3600.0
    return round(delta_kg_h, 6)


def _cf_wagner():
    kappa, dvdi, length = 45.0, 0.02, 0.3
    return round(kappa * dvdi / length, 4)


def _cf_foam():
    s_ref, s_sl = 72.0, 45.0
    return round((s_ref - s_sl) / s_ref, 4)


def _cf_archard():
    f, s, h, k = 500.0, 50000.0, 1.0e8, 2.0e-3
    return _fmt4g(k * f * s / h)


def _cf_impact_erosion():
    flux, e_rm, t, eff = 250.0, 8.0e9, 3600.0, 0.05
    return _fmt4g(flux * eff * t / e_rm)


def _cf_contact_erosion():
    charge, coeff, ops = 0.8, 15.0, 6000.0
    return _fmt4g(charge * coeff * ops)


def _cf_biogenic():
    flux, y, cap = 1.0, 0.85, 75.0
    # g/(m^2*day) * yield * (98.08/34.08) / (kg/m^3): the g/kg and
    # m/mm conversions cancel to 1.0 on the mm/day scale (pint carries
    # the units; the magnitude arithmetic is exactly this)
    return _fmt4g(flux * y * H2SO4_OVER_H2S / cap)


def _cf_microbial():
    mu_ref, q10, t, tref, days = 0.25, 2.2, 32.0, 20.0, 30.0
    exponent = mu_ref * q10 ** ((t - tref) / 10.0) * days
    return _fmt4g(math.exp(exponent))


def _cf_dust_ignition():
    t_hot, t_li, thick, derate = 220.0, 350.0, 10.0, 15.0
    return round(t_hot - (t_li - derate * thick), 1)


def _cf_humidity():
    alpha, rh, rh_ref = 0.09, 85.0, 0.0
    return _fmt4g(math.exp(alpha * (rh - rh_ref)))


def _cf_ammonia():
    ph0, ph1, t0, t1, aw0, aw1 = (9.0, 10.5, 20.0, 30.0, 3.0, 3.0)

    def pot(ph, t_c, aw):
        t_k = t_c + 273.15
        pka = 0.09018 + 2729.92 / t_k  # Emerson et al. 1975
        alpha = 1.0 / (1.0 + 10.0 ** (pka - ph))
        return alpha * (1.0 - math.exp(-aw))

    return _fmt4g(pot(ph1, t1, aw1) - pot(ph0, t0, aw0))


def _cf_vant_hoff():
    dh_kj, t0_c, t1_c = -45.0, 25.0, 60.0
    dh_j = dh_kj * 1000.0
    ln_ratio = (-dh_j / R_GAS) * (1.0 / (t1_c + 273.15)
                                  - 1.0 / (t0_c + 273.15))
    return _fmt4g(math.exp(ln_ratio))


def _cf_molarity():
    return 15.0  # the bound check returns the input molarity verbatim


MAGNITUDE_CASES = {
    "arrhenius_rate_ratio": (
        dict(ea_kj_mol=80.0, t1_degC=60.0, t2_degC=90.0),
        _cf_arrhenius),
    "thermoset_cure_residual_direction": (
        dict(t1_degC=150.0, t2_degC=120.0, ea_kj_mol=60.0),
        _cf_thermoset_cure),
    "fouling_u_degradation": (
        dict(u_clean_w_m2k=2000.0, rf_after_m2k_w=4e-4,
             rf_before_m2k_w=0.0), _cf_fouling),
    "langelier_lsi": (
        dict(tds_mg_l=800.0, temp_degC=60.0,
             ca_hardness_mg_l_caco3=200.0,
             alkalinity_mg_l_caco3=150.0, ph=8.6), _cf_langelier),
    "npsh_margin": (
        dict(patm_kpa=101.3, pvap_kpa=2.3, rho_kg_m3=998.0,
             suction_head_m=2.0, friction_loss_m=0.3, npshr_m=0.5),
        _cf_npsh),
    "dewpoint_frost_margin": (
        dict(t_air_degC=30.0, rh_percent=60.0, t_surface_degC=25.0),
        _cf_dewpoint),
    "larson_miller_lmp": (
        dict(t1_degC=540.0, t1_h=40000, t2_degC=600.0, t2_h=60000),
        _cf_larson_miller),
    "surge_margin": (
        dict(p_surge_kpa=300.0, p_op_kpa=250.0), _cf_surge),
    "fatigue_miner": (
        dict(n_cycles=1e6, stress_amp_mpa=200.0, sn_a_mpa_pow_b=800.0,
             sn_b=5.0), _cf_fatigue),
    "breakthrough_capacity": (
        dict(m_air_kg=1.0, w_in_kg_kg=0.010, w_out_kg_kg=0.001,
             m_desiccant_kg=10.0, q_e_kg_kg=0.125), _cf_breakthrough),
    "faraday_gas_rate": (
        dict(current_after_a=9000.0, current_before_a=8000.0,
             molar_mass_g_mol=32.0, z_electrons=4), _cf_faraday),
    "wagner_number": (
        dict(conductivity_s_m=45.0, polarization_slope_v_m2_a=0.02,
             characteristic_length_m=0.3), _cf_wagner),
    "foam_index": (
        dict(sigma_ref_mn_m=72.0, sigma_sludge_mn_m=45.0), _cf_foam),
    "archard_wear": (
        dict(load_n=500.0, sliding_distance_m=50000.0,
             hardness_pa=1.0e8, wear_coeff=2.0e-3), _cf_archard),
    "impact_erosion_rate": (
        dict(impact_flux_w_m2=250.0, specific_removal_energy_j_m3=8.0e9,
             exposure_s=3600.0, erosion_efficiency=0.05),
        _cf_impact_erosion),
    "contact_erosion_per_operation": (
        dict(arc_charge_c=0.8, erosion_coeff_ug_per_c=15.0,
             operations_per_year=6000.0), _cf_contact_erosion),
    "biogenic_acid_thinning": (
        dict(h2s_flux_g_m2_day=1.0, acid_yield_fraction=0.85,
             neutralization_capacity_kg_m3=75.0), _cf_biogenic),
    "microbial_growth_rate": (
        dict(mu_ref_per_day=0.25, q10=2.2, t_degC=32.0,
             t_ref_degC=20.0, days=30.0), _cf_microbial),
    "dust_layer_ignition_margin": (
        dict(t_hot_surface_degC=220.0, layer_ignition_degC=350.0,
             layer_thickness_mm=10.0,
             thickness_derate_degC_per_mm=15.0), _cf_dust_ignition),
    "humidity_permeability_ratio": (
        dict(alpha_per_rh_percent=0.09, rh_percent=85.0,
             rh_ref_percent=0.0), _cf_humidity),
    "ammonia_strip_direction": (
        dict(ph_initial=9.0, ph_proposed=10.5, temp_initial_degC=20.0,
             temp_proposed_degC=30.0, aw_initial=3.0, aw_proposed=3.0),
        _cf_ammonia),
    "vant_hoff_adsorption_direction": (
        dict(delta_h_ads_kj_mol=-45.0, t_initial_degC=25.0,
             t_proposed_degC=60.0, intent="PROMOTE_DESORPTION"),
        _cf_vant_hoff),
    "aqueous_molarity_saturation_bound": (
        dict(solute="NaOH", molarity_mol_per_l=15.0), _cf_molarity),
}


def test_magnitude_rows_cover_exactly_the_registry():
    """Fail-closed completeness (the Art. 3 F67 pattern): every
    relation in the CHECKS registry carries a magnitude row — a new
    relation without one reds here until a closed-form case is added."""
    ids = set(pc.CHECKS)
    rows = set(MAGNITUDE_CASES)
    assert rows == ids, (
        f"magnitude rows missing for new relations: {ids - rows}; "
        f"stale rows for retired relations: {rows - ids}")


def test_magnitude_rows_use_their_own_kwargs():
    """Each row's kwargs must actually exercise the relation (RUN, a
    real value) — a row that never runs proves nothing."""
    for cid, (kwargs, _) in MAGNITUDE_CASES.items():
        r = pc.run_check(cid, **kwargs)
        assert r["verdict"] == "RUN", (cid, r)
        assert r["value"] is not None, cid


def test_every_relation_matches_its_closed_form_magnitude():
    """THE F95 assertion: engine value vs independent literal closed
    form, tight rel-tol, one row per relation. A x1000-class error on
    ANY relation reds here — the class of bug the sign-only suite hid
    for 6+ rounds (F93) cannot recur anywhere in the registry."""
    failures = []
    for cid, (kwargs, cf) in sorted(MAGNITUDE_CASES.items()):
        r = pc.run_check(cid, **kwargs)
        assert r["verdict"] == "RUN", (cid, r)
        true = cf()
        if not _close(r["value"], true):
            failures.append(
                f"{cid}: engine={r['value']!r} closed_form={true!r} "
                f"(rel diff "
                f"{abs(r['value'] - true) / max(1.0, abs(true)):.3e})")
    assert not failures, (
        "MAGNITUDE REGRESSION (the F93 x1000 class, now tested on "
        "every relation):\n  " + "\n  ".join(failures))


def test_magnitude_assertions_catch_a_x1000_error():
    """Self-attack (Art. 2): prove the assertion would actually fire —
    a deliberately 1000x-wrong literal must FAIL the comparison for
    every relation that returns a scale-carrying value."""
    for cid, (kwargs, cf) in sorted(MAGNITUDE_CASES.items()):
        r = pc.run_check(cid, **kwargs)
        true = cf()
        wrong = true * 1000.0
        assert not _close(r["value"], wrong), (
            f"{cid}: a x1000 error would PASS the magnitude check — "
            "the assertion is vacuous for this relation")
