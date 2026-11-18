"""discovery_fabric/engine/onrow_physics.py — the F80 on-row
computation + sign-check (R83, claim c-0099; AM72/V73 direction 3).

The F80 gap: physics_checks runs on REFERENCE_SCENARIOS — the row's
own numbers never entered a computation (on_row_physics_runs 0/36 on
the labelled set; the P1 gate measured registry coverage). This
module runs the SAME frozen registry checks ON THE ROW:

  1. BIND (dimensional only): the row's extracted numeric claims
     (numeric_claims.extract_candidate_claims) bind to the relation's
     input kwargs by pint dimensional compatibility — a claim binds
     kwarg K iff claim.quantity.to(K's declared unit) is a valid
     conversion. A kA/m2 claim CANNOT bind an A input (typed
     unbindable, never forced). Binding is dimension-only by design:
     it can only refuse (a wrong-dimension claim never enters), it
     cannot semantically verify intent — the typed limitation is
     BINDING_IS_DIMENSIONAL_ONLY and every record carries it.

  2. ROW CLAIMS WIN: a bound claim's value is the input's value
     (provenance ROW_CLAIM + the claim id). Inputs no claim binds are
     filled from the relation's COMMITTED reference values as TYPED
     ASSUMPTIONS (provenance ASSUMPTION — the Art. 9 labelled-
     assumption path: visible, sourced, never a silent default).
     Inputs with a function default and no reference value ride the
     default (provenance FUNCTION_DEFAULT). A required input with
     neither claim nor assumption nor default -> the run refuses
     typed PENDING_INPUTS (inputs are never fabricated).

  3. RUN via physics_checks.run_check — the frozen registry is the
     only computation path (no reimplementation here).

  4. SIGN-CHECK: the computed direction_of_effect vs the claim's
     stated direction (improves/worsens words in the candidate's own
     direction text). A stated direction the computation contradicts
     is a typed SIGN_CONTRADICTION; a deferring text ("direction is
     the SIGN of the computed physics result") is DEFERRED — the
     claim does not assert a direction, so nothing contradicts.

Zero LLM, zero network. The frozen machine path is untouched: this
module is called by the measurement layer, never by the frozen
one-shot chain.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from . import physics_checks as pc
from .numeric_claims import claims_for_binding, parse_quantity

# The committed input-unit table: every kwarg of every registry check
# with the unit its _q() coercion declares (extracted from
# physics_checks verbatim; dimensionless inputs marked "dimensionless"
# — they never bind unit-carrying claims). A check missing from this
# table is typed ONROW_UNITS_UNMAPPED — never guessed.
INPUT_UNITS: Dict[str, Dict[str, str]] = {
    "archard_wear": {"load_n": "N", "sliding_distance_m": "m",
                     "hardness_pa": "Pa", "wear_coeff": "dimensionless"},
    "arrhenius_rate_ratio": {"ea_kj_mol": "kJ/mol", "t1_degC": "degC",
                             "t2_degC": "degC"},
    "biogenic_acid_thinning": {
        "h2s_flux_g_m2_day": "g/(m^2*day)",
        "acid_yield_fraction": "dimensionless",
        "neutralization_capacity_kg_m3": "kg/m^3"},
    "breakthrough_capacity": {
        "m_air_kg": "kg", "w_in_kg_kg": "kg/kg",
        "w_out_kg_kg": "kg/kg", "m_desiccant_kg": "kg",
        "q_e_kg_kg": "kg/kg"},
    "contact_erosion_per_operation": {
        "arc_charge_c": "C", "erosion_coeff_ug_per_c": "ug/C",
        "operations_per_year": "dimensionless"},
    "dewpoint_frost_margin": {"t_air_degC": "degC",
                              "rh_percent": "percent",
                              "t_surface_degC": "degC"},
    "dust_layer_ignition_margin": {
        "t_hot_surface_degC": "degC", "layer_ignition_degC": "degC",
        "layer_thickness_mm": "mm",
        "thickness_derate_degC_per_mm": "degC/mm"},
    "faraday_gas_rate": {"current_after_a": "A",
                         "current_before_a": "A",
                         "molar_mass_g_mol": "g/mol",
                         "z_electrons": "dimensionless"},
    "fatigue_miner": {"n_cycles": "dimensionless",
                      "stress_amp_mpa": "MPa",
                      "sn_a_mpa_pow_b": "dimensionless",
                      "sn_b": "dimensionless"},
    "foam_index": {"sigma_ref_mn_m": "mN/m",
                   "sigma_sludge_mn_m": "mN/m"},
    "fouling_u_degradation": {
        "u_clean_w_m2k": "W/(m**2*K)", "rf_after_m2k_w": "m**2*K/W",
        "rf_before_m2k_w": "m**2*K/W"},
    "humidity_permeability_ratio": {
        "alpha_per_rh_percent": "1/percent",
        "rh_percent": "percent", "rh_ref_percent": "percent"},
    "impact_erosion_rate": {
        "impact_flux_w_m2": "W/m^2",
        "specific_removal_energy_j_m3": "J/m^3", "exposure_s": "s",
        "erosion_efficiency": "dimensionless"},
    "langelier_lsi": {"tds_mg_l": "mg/L", "temp_degC": "degC",
                      "ca_hardness_mg_l_caco3": "mg/L",
                      "alkalinity_mg_l_caco3": "mg/L",
                      "ph": "dimensionless"},
    "larson_miller_lmp": {"t1_degC": "degC", "t1_h": "hour",
                          "t2_degC": "degC", "t2_h": "hour",
                          "c_const": "dimensionless"},
    "microbial_growth_rate": {"mu_ref_per_day": "1/day",
                              "q10": "dimensionless",
                              "t_degC": "degC", "t_ref_degC": "degC",
                              "days": "day"},
    "npsh_margin": {"patm_kpa": "kPa", "pvap_kpa": "kPa",
                    "rho_kg_m3": "kg/m**3", "suction_head_m": "m",
                    "friction_loss_m": "m", "npshr_m": "m"},
    "surge_margin": {"p_surge_kpa": "kPa", "p_op_kpa": "kPa"},
    "wagner_number": {"conductivity_s_m": "S/m",
                      "polarization_slope_v_m2_a": "V*m**2/A",
                      "characteristic_length_m": "m"},
}

# ONLY the unambiguous direction verbs map. Frame-dependent verbs
# ("reduces", "increases", "accelerates" — reduces the RATE is
# improves, reduces the MARGIN is worsens) are deliberately NOT
# mapped: a frame-dependent text sign-checks as DEFERRED (no direction
# asserted the computation can contradict), never guessed. The typed
# limitation is DIRECTION_WORDS_ARE_UNAMBIGUOUS_ONLY.
DIRECTION_WORDS = {
    "improves": "improves", "improvement": "improves",
    "worsens": "worsens", "worsening": "worsens",
}


def _all_kwargs(check_id: str) -> List[str]:
    import inspect
    return list(inspect.signature(pc.CHECKS[check_id]).parameters)


def _required_kwargs(check_id: str) -> List[str]:
    import inspect
    sig = inspect.signature(pc.CHECKS[check_id])
    return [p.name for p in sig.parameters.values()
            if p.default is inspect.Parameter.empty]


def bind_claims(check_id: str,
                extraction: Dict[str, Any]
                ) -> Dict[str, Any]:
    """Dimension-only binding over an extraction record (the same
    shape run_on_row takes): for each kwarg (signature order) take
    the FIRST not-yet-bound claim whose quantity converts to the
    kwarg's declared unit. Returns {bindings: {kwarg: {claim_id,
    value, unit}}, unbound_claims: [claim_id...]} — the unbound list
    is the typed per-claim consumption report (a claim that binds no
    kwarg of THIS check is UNBINDABLE_HERE, not an error)."""
    units = INPUT_UNITS[check_id]
    bindable = claims_for_binding(extraction)
    bindings: Dict[str, Any] = {}
    used = set()
    for kwarg in _required_kwargs(check_id):
        unit = units[kwarg]
        for claim_id, q in bindable:
            if claim_id in used:
                continue
            if unit == "dimensionless":
                # only a dimensionless claim could bind; extracted
                # claims always carry units, so no bind (typed)
                continue
            try:
                converted = q.to(unit)
            except Exception:  # noqa: BLE001 — pint refusal = no bind
                continue
            used.add(claim_id)
            bindings[kwarg] = {
                "claim_id": claim_id,
                "value": float(converted.magnitude),
                "unit": unit}
            break
    return {"bindings": bindings,
            "unbound_claims": [cid for cid, _ in bindable
                               if cid not in used]}


def stated_direction(text: str) -> Optional[str]:
    """The candidate's own direction words -> a typed direction, or
    None when the text asserts no unambiguous direction (deferring
    texts like 'direction is the SIGN of the computed physics result'
    and frame-dependent verbs both defer — the computation cannot
    contradict a direction that was never unambiguously asserted)."""
    t = (text or "").lower()
    for word, direction in DIRECTION_WORDS.items():
        if re_word_in(word, t):
            return direction
    return None


def re_word_in(word: str, text: str) -> bool:
    import re
    return re.search(rf"\b{word}\b", text) is not None


def sign_check(claimed: Optional[str],
               computed: str) -> Dict[str, Any]:
    """claimed vs computed direction. DEFERRED when the claim asserts
    no direction; CONTRADICTS only on an asserted opposite
    (improves-vs-worsens); 'neutral' computed never contradicts (the
    computation found no effect — the claim's direction is unproven,
    not contradicted: typed NEUTRAL_COMPUTED)."""
    if claimed is None:
        return {"claimed": None, "computed": computed,
                "verdict": "DEFERRED"}
    if computed == "neutral" or claimed == computed:
        verdict = "NEUTRAL_COMPUTED" if computed == "neutral" \
            else "AGREES"
    else:
        verdict = "SIGN_CONTRADICTION"
    return {"claimed": claimed, "computed": computed,
            "verdict": verdict}


def run_on_row(check_id: str,
               extraction: Dict[str, Any],
               direction_text: str = ""
               ) -> Dict[str, Any]:
    """The on-row run: bind the row's claims, fill gaps with TYPED
    ASSUMPTIONS (committed reference values) / FUNCTION_DEFAULT, run
    via the frozen registry, sign-check. Typed refusals (never
    silent): UNKNOWN_CHECK, ONROW_UNITS_UNMAPPED, PENDING_INPUTS."""
    base = {"check_id": check_id,
            "binding_rule": "BINDING_IS_DIMENSIONAL_ONLY"}
    if check_id not in pc.CHECKS:
        base["verdict"] = "REFUSED"
        base["typed"] = "UNKNOWN_CHECK"
        base["detail"] = (f"{check_id!r} is not in the frozen "
                          "registry — the registry is the only path")
        return base
    if check_id not in INPUT_UNITS or any(
            k not in INPUT_UNITS[check_id]
            for k in _required_kwargs(check_id)):
        base["verdict"] = "REFUSED"
        base["typed"] = "ONROW_UNITS_UNMAPPED"
        base["detail"] = ("the committed INPUT_UNITS table does not "
                          "cover every kwarg of this check — extend "
                          "the table, never guess units")
        return base
    bound = bind_claims(check_id, extraction)
    bindings = bound["bindings"]

    scenario = pc.REFERENCE_SCENARIOS.get(check_id, {})
    inputs: Dict[str, Any] = {}
    provenance: Dict[str, Any] = {}
    missing: List[str] = []
    for kwarg in _all_kwargs(check_id):
        if kwarg in bindings:
            inputs[kwarg] = bindings[kwarg]["value"]
            provenance[kwarg] = {
                "source": "ROW_CLAIM",
                "claim_id": bindings[kwarg]["claim_id"],
                "unit": bindings[kwarg]["unit"]}
        elif kwarg in scenario:
            inputs[kwarg] = scenario[kwarg]
            provenance[kwarg] = {
                "source": "ASSUMPTION",
                "value": scenario[kwarg],
                "unit": INPUT_UNITS[check_id][kwarg],
                "assumption": (f"committed reference value for "
                               f"{check_id}.{kwarg} — labelled "
                               "assumption, Art. 9")}
        elif kwarg in _required_kwargs(check_id):
            missing.append(kwarg)
        else:
            # a default kwarg with no scenario value: the check
            # function's own default applies — not passed, not
            # fabricated, provenance typed
            provenance[kwarg] = {
                "source": "FUNCTION_DEFAULT",
                "note": ("the check function's own default applies — "
                         "not passed, not fabricated")}
    if missing:
        base["verdict"] = "REFUSED"
        base["typed"] = "PENDING_INPUTS"
        base["detail"] = {
            "missing_kwargs": missing,
            "note": ("no row claim binds and no committed assumption "
                     "exists — inputs are never fabricated")}
        base["input_provenance"] = provenance
        return base

    result = pc.run_check(check_id, **inputs)
    claimed = stated_direction(direction_text)
    sc = sign_check(claimed, result.get("direction_of_effect",
                                        "unavailable"))
    out = dict(base)
    out.update({
        "verdict": result["verdict"],
        "value": result["value"],
        "unit": result["unit"],
        "direction_of_effect": result["direction_of_effect"],
        "input_provenance": provenance,
        "row_claim_inputs": sorted(bindings),
        "assumption_inputs": sorted(k for k, v in provenance.items()
                                    if v["source"] == "ASSUMPTION"),
        "unbound_row_claims": bound["unbound_claims"],
        "sign_check": sc,
        "computed_from": ("the row's own numbers where they bind "
                          "(ROW_CLAIM); committed reference values as "
                          "typed ASSUMPTIONS elsewhere"),
    })
    if result["verdict"] != "RUN":
        out["typed"] = f"CHECK_{result['verdict']}"
    return out
