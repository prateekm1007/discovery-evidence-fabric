#!/usr/bin/env python3
"""tests/test_article3_degenerate_inputs.py — EPISTEMIC v3.2.0 Art. 3 CI
wiring (ratification of audit/PROPOSED_EPISTEMIC_AMENDMENTS_v3.2.0_R57.md,
AM52/V49): a DEGENERATE-INPUT probe battery for EVERY physics relation in
the engine registry, asserting a TYPED REFUSED verdict — never an uncaught
exception through run_check.

Grounded in F67/F-V5 (auditor AM51 live-verified): arrhenius (T2=0 K) and
npsh (rho=0) crashed ZeroDivisionError pre-fix; the guards were fixed
c-0073. This battery closes the CLASS: every relation in the CHECKS
registry is probed on its true division/domain-zero axis (read from the
formula bodies at wiring time), and the typed-refusal contract is
enforced CI-side so a new relation without guards reds the push.

Zero LLM. Deterministic. No external calls.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import physics_checks as pc  # noqa: E402

# The true degenerate axis per relation, chosen from the division/
# domain sites in the formula bodies (wiring audit 2026-11-17):
#   arrhenius: 1.0/t (absolute zero);  fouling: 1/u_clean;
#   lsi: log10(tds);  npsh: dp/(rho*g);  dewpoint: log(rhs/100);
#   lmp: log(t_h);  surge: /(p_surge);  miner: big_n from sn_a=0;
#   breakthrough: /q_e;  faraday: /(z*F);  wagner: /length;
#   foam: /sigma_ref.
DEGENERATE_KWARGS: dict[str, dict] = {
    "arrhenius_rate_ratio": dict(ea_kj_mol=80.0, t1_degC=25.0,
                                 t2_degC=-273.15),          # T2 = 0 K
    "fouling_u_degradation": dict(u_clean_w_m2k=0.0,
                                  rf_after_m2k_w=0.0004,
                                  rf_before_m2k_w=0.0002),
    "langelier_lsi": dict(tds_mg_l=0.0, temp_degC=25.0,
                          ca_hardness_mg_l_caco3=100.0,
                          alkalinity_mg_l_caco3=80.0, ph=7.5),
    "npsh_margin": dict(patm_kpa=101.325, pvap_kpa=3.17, rho_kg_m3=0.0,
                        suction_head_m=2.0, friction_loss_m=0.5,
                        npshr_m=0.5),                      # rho = 0
    "dewpoint_frost_margin": dict(t_air_degC=25.0, rh_percent=0.0,
                                  t_surface_degC=15.0),
    "larson_miller_lmp": dict(t1_degC=600.0, t1_h=0.0, t2_degC=650.0,
                              t2_h=1000.0),
    "surge_margin": dict(p_surge_kpa=0.0, p_op_kpa=250.0),
    "fatigue_miner": dict(n_cycles=1e6, stress_amp_mpa=200.0,
                          sn_a_mpa_pow_b=0.0, sn_b=5.0),
    "breakthrough_capacity": dict(m_air_kg=1.0, w_in_kg_kg=0.01,
                                  w_out_kg_kg=0.002,
                                  m_desiccant_kg=0.5, q_e_kg_kg=0.0),
    "faraday_gas_rate": dict(current_after_a=1.0, current_before_a=0.9,
                             molar_mass_g_mol=2.016, z_electrons=0.0),
    "wagner_number": dict(conductivity_s_m=0.05,
                          polarization_slope_v_m2_a=1e-8,
                          characteristic_length_m=0.0),
    "foam_index": dict(sigma_ref_mn_m=0.0, sigma_sludge_mn_m=30.0),
    # R62 (c-0085) expansion: the true degenerate axis per new relation
    # (archard/impact/biogenic divide by hardness/removal-energy/
    # capacity; contact refuses a zero coefficient; microbial refuses
    # Q10 outside (0,5]; dust refuses negative thickness; humidity
    # refuses RH outside [0,100])
    "archard_wear": dict(load_n=500.0, sliding_distance_m=50000.0,
                         hardness_pa=0.0, wear_coeff=2.0e-3),
    "impact_erosion_rate": dict(impact_flux_w_m2=5.0,
                                specific_removal_energy_j_m3=0.0,
                                exposure_s=3.15e7,
                                erosion_efficiency=5.0e-5),
    "contact_erosion_per_operation": dict(arc_charge_c=30.0,
                                          erosion_coeff_ug_per_c=0.0,
                                          operations_per_year=6000.0),
    "biogenic_acid_thinning": dict(h2s_flux_g_m2_day=1.0,
                                   acid_yield_fraction=0.85,
                                   neutralization_capacity_kg_m3=0.0),
    "microbial_growth_rate": dict(mu_ref_per_day=0.25, q10=0.0,
                                  t_degC=32.0, t_ref_degC=20.0,
                                  days=30.0),
    "dust_layer_ignition_margin": dict(t_hot_surface_degC=220.0,
                                       layer_ignition_degC=350.0,
                                       layer_thickness_mm=-1.0,
                                       thickness_derate_degC_per_mm=15.0),
    "humidity_permeability_ratio": dict(alpha_per_rh_percent=0.09,
                                        rh_percent=150.0,
                                        rh_ref_percent=0.0),
    # AM91 (c-0116): the true degenerate axis per new relation —
    # ammonia refuses an all-equal proposal (no directional claim);
    # van 't Hoff refuses a zero adsorption enthalpy (no temperature
    # dependence); the saturation bound refuses a non-positive
    # molarity
    "ammonia_strip_direction": dict(ph_initial=10.8, ph_proposed=10.8,
                                    temp_initial_degC=30.0,
                                    temp_proposed_degC=30.0,
                                    aw_initial=3.0, aw_proposed=3.0),
    "vant_hoff_adsorption_direction": dict(delta_h_ads_kj_mol=0.0,
                                           t_initial_degC=25.0,
                                           t_proposed_degC=65.0,
                                           intent="PROMOTE_DESORPTION"),
    "aqueous_molarity_saturation_bound": dict(solute="naoh",
                                              molarity_mol_per_l=0.0),
    # F91 (R113 dir 4): the cure-kinetics relation refuses absolute
    # zero on its true division axis (1/T), same as arrhenius
    "thermoset_cure_residual_direction": dict(t1_degC=150.0,
                                               t2_degC=-273.15,
                                               ea_kj_mol=60.0),
}

EXPECTED_REGISTRY = {
    "arrhenius_rate_ratio", "fouling_u_degradation", "langelier_lsi",
    "npsh_margin", "dewpoint_frost_margin", "larson_miller_lmp",
    "surge_margin", "fatigue_miner", "breakthrough_capacity",
    "faraday_gas_rate", "wagner_number", "foam_index",
    "archard_wear", "impact_erosion_rate",
    "contact_erosion_per_operation", "biogenic_acid_thinning",
    "microbial_growth_rate", "dust_layer_ignition_margin",
    "humidity_permeability_ratio",
}

TYPED_VERDICTS = {"REFUSED", "FAIL", "PASS", "RUN", "NOT_COMPUTABLE"}


def test_registry_completeness() -> None:
    """Every relation in the CHECKS registry is covered by the battery —
    a new relation without a degenerate row reds here (fail-closed)."""
    ids = set(pc.CHECKS)
    assert EXPECTED_REGISTRY <= ids, (
        f"battery rows missing for new relations: {EXPECTED_REGISTRY - ids}")
    assert set(DEGENERATE_KWARGS) == ids, (
        "every registered relation needs a degenerate row (add it above); "
        f"registry={sorted(ids)} rows={sorted(DEGENERATE_KWARGS)}")


@pytest.mark.parametrize("check_id", sorted(DEGENERATE_KWARGS))
def test_degenerate_input_is_typed_refusal(check_id: str) -> None:
    """v3.2.0 Art. 3 CI: degenerate input -> TYPED REFUSED through
    run_check. An uncaught exception (ZeroDivisionError, ValueError from
    math.log10/log, ...) or a computed number on a division-by-zero axis
    is the F67 failure class and REDS."""
    kwargs = DEGENERATE_KWARGS[check_id]
    out = pc.run_check(check_id, **kwargs)  # must not raise
    assert isinstance(out, dict), "run_check returns the typed result dict"
    verdict = out.get("verdict")
    assert verdict in TYPED_VERDICTS, (
        f"{check_id}: verdict {verdict!r} is not a typed verdict")
    assert verdict == "REFUSED", (
        f"{check_id}: degenerate input produced verdict {verdict!r} — "
        "the relation must REFUSE out_of_domain before dividing (F67 "
        "class; add the guard BEFORE the division in the engine)")
    assert out.get("reason") or out.get("notes") or out.get("detail"), (
        f"{check_id}: a typed refusal carries a reason")


@pytest.mark.parametrize("check_id", sorted(DEGENERATE_KWARGS))
def test_healthy_input_still_computes(check_id: str) -> None:
    """Content-preservation guard (the F67 fix was bit-identical on the
    reference scenarios): each battery row ships a HEALTHY companion; the
    relation must still compute (not over-refuse) on it."""
    healthy = HEALTHY_KWARGS[check_id]
    out = pc.run_check(check_id, **healthy)
    assert isinstance(out, dict)
    assert out.get("verdict") in TYPED_VERDICTS - {"REFUSED"}, (
        f"{check_id}: healthy input refused — the guard over-refuses "
        f"({out.get('verdict')!r})")


HEALTHY_KWARGS: dict[str, dict] = {
    "arrhenius_rate_ratio": dict(ea_kj_mol=80.0, t1_degC=25.0, t2_degC=80.0),
    "fouling_u_degradation": dict(u_clean_w_m2k=2500.0,
                                  rf_after_m2k_w=0.0004,
                                  rf_before_m2k_w=0.0002),
    "langelier_lsi": dict(tds_mg_l=500.0, temp_degC=25.0,
                          ca_hardness_mg_l_caco3=100.0,
                          alkalinity_mg_l_caco3=80.0, ph=7.5),
    "npsh_margin": dict(patm_kpa=101.325, pvap_kpa=3.17, rho_kg_m3=998.0,
                        suction_head_m=2.0, friction_loss_m=0.5,
                        npshr_m=0.5),
    "dewpoint_frost_margin": dict(t_air_degC=25.0, rh_percent=60.0,
                                  t_surface_degC=15.0),
    "larson_miller_lmp": dict(t1_degC=600.0, t1_h=1000.0, t2_degC=650.0,
                              t2_h=1000.0),
    "surge_margin": dict(p_surge_kpa=300.0, p_op_kpa=250.0),
    "fatigue_miner": dict(n_cycles=1e6, stress_amp_mpa=200.0,
                          sn_a_mpa_pow_b=800.0, sn_b=5.0),
    "breakthrough_capacity": dict(m_air_kg=1.0, w_in_kg_kg=0.01,
                                  w_out_kg_kg=0.002,
                                  m_desiccant_kg=0.5, q_e_kg_kg=0.15),
    "faraday_gas_rate": dict(current_after_a=1.0, current_before_a=0.9,
                             molar_mass_g_mol=2.016, z_electrons=2.0),
    "wagner_number": dict(conductivity_s_m=0.05,
                          polarization_slope_v_m2_a=1e-8,
                          characteristic_length_m=0.01),
    "foam_index": dict(sigma_ref_mn_m=72.0, sigma_sludge_mn_m=30.0),
    # R62 (c-0085) expansion healthy companions (== the reference
    # scenarios; the relations must still compute, never over-refuse)
    "archard_wear": dict(load_n=500.0, sliding_distance_m=50000.0,
                         hardness_pa=1.0e8, wear_coeff=2.0e-3),
    "impact_erosion_rate": dict(impact_flux_w_m2=5.0,
                                specific_removal_energy_j_m3=5.0e6,
                                exposure_s=3.15e7,
                                erosion_efficiency=5.0e-5),
    "contact_erosion_per_operation": dict(arc_charge_c=30.0,
                                          erosion_coeff_ug_per_c=15.0,
                                          operations_per_year=6000.0),
    "biogenic_acid_thinning": dict(h2s_flux_g_m2_day=1.0,
                                   acid_yield_fraction=0.85,
                                   neutralization_capacity_kg_m3=75.0),
    "microbial_growth_rate": dict(mu_ref_per_day=0.25, q10=2.2,
                                  t_degC=32.0, t_ref_degC=20.0,
                                  days=30.0),
    "dust_layer_ignition_margin": dict(t_hot_surface_degC=220.0,
                                       layer_ignition_degC=350.0,
                                       layer_thickness_mm=10.0,
                                       thickness_derate_degC_per_mm=15.0),
    "humidity_permeability_ratio": dict(alpha_per_rh_percent=0.09,
                                        rh_percent=85.0,
                                        rh_ref_percent=0.0),
    # AM91 (c-0116): healthy companions — raise-all ammonia (improves),
    # exothermic heating for desorption (warm-caustic), practical NaOH
    "ammonia_strip_direction": dict(ph_initial=8.0, ph_proposed=10.8,
                                    temp_initial_degC=25.0,
                                    temp_proposed_degC=35.0,
                                    aw_initial=2.0, aw_proposed=3.5),
    "vant_hoff_adsorption_direction": dict(delta_h_ads_kj_mol=-40.0,
                                           t_initial_degC=25.0,
                                           t_proposed_degC=60.0,
                                           intent="PROMOTE_DESORPTION"),
    "aqueous_molarity_saturation_bound": dict(solute="naoh",
                                              molarity_mol_per_l=15.3),
    # F91 (R113 dir 4): a higher cure temperature computes RUN with
    # residual falling (improves) — never over-refused
    "thermoset_cure_residual_direction": dict(t1_degC=150.0,
                                               t2_degC=165.0,
                                               ea_kj_mol=60.0),
}


def test_battery_covers_every_registered_failure_class_mapping() -> None:
    """The registry's failure-class mapping stays total (no relation
    silently unmapped when new ones land)."""
    for cid in pc.CHECKS:
        assert cid in pc.CHECKS_BY_FAILURE_CLASS.values() or any(
            cid in v for v in pc.CHECKS_BY_FAILURE_CLASS.values()), (
            f"{cid} unmapped in CHECKS_BY_FAILURE_CLASS")
