"""discovery_fabric/engine/physics_checks.py — the computed physics
layer (ROADMAP P1.1, AM44 D4, claim lineage c-0066).

A registry of computable governing relations keyed by failure class.
Every quantitative claim a candidate makes must emit a small typed
calculation that RUNS here; the direction-of-effect is the SIGN of the
computed result, never prose (the F57/F58 lesson: scanners reading
prose cannot tell a correct direction from an inverted one).

Unit discipline: every dimensional input is a pint Quantity — bare
floats for dimensional inputs are a typed refusal (UNVERIFIABLE),
never silently accepted. The heavier libraries (CoolProp, ht, fluids,
thermo, tespy) are per-check optional imports: a check that needs one
returns a typed UNAVAILABLE verdict when the library is absent — a
missing library never degrades into a fabricated number.

Rounds 2+ of P1 (R52, claim c-0069) bring the registry to the six
roadmap-named relations: Arrhenius rate ratio, fouling U-degradation,
Langelier LSI, NPSH cavitation margin, Magnus dewpoint/frost margin,
and the Larson-Miller creep comparator — each unit-checked in
tests/test_physics_checks.py; the direction-of-effect is the SIGN of
the computed result on every one.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Optional

import pint

_UREG = pint.UnitRegistry()
R_GAS = pint.Quantity(8.314462618, "J/(mol*K)")

DIRECTIONS = ("improves", "worsens", "neutral", "unavailable")
VERDICTS = ("RUN", "UNAVAILABLE", "REFUSED")


def _q(value: Any, unit: str) -> pint.Quantity:
    """Coerce an input to a pint Quantity with the declared unit. Bare
    numeric inputs are ACCEPTED here only because the registry schema
    declares the unit per input; strings without dimensions are
    refused by the caller's schema check."""
    if isinstance(value, pint.Quantity):
        return value.to(unit)
    return pint.Quantity(float(value), unit)


def _result(check_id: str, failure_class: str, verdict: str,
            value: Optional[float], unit: str,
            direction: str, detail: Dict[str, Any]) -> Dict[str, Any]:
    assert verdict in VERDICTS
    if direction not in DIRECTIONS:
        raise ValueError(f"direction {direction!r} not typed")
    return {"check_id": check_id, "failure_class": failure_class,
            "verdict": verdict, "value": value, "unit": unit,
            "direction_of_effect": direction, "detail": detail}


# ---------------------------------------------------------------------------
# check 1: Arrhenius time-at-temperature equivalence
#   k2/k1 = exp(-Ea/R * (1/T2 - 1/T1))
#   direction-of-effect: a proposed temperature REGIME change consumes
#   life faster when the computed rate ratio exceeds 1 (worsens).
# ---------------------------------------------------------------------------
def arrhenius_rate_ratio(ea_kj_mol: float, t1_degC: float,
                         t2_degC: float) -> Dict[str, Any]:
    try:
        ea = _q(ea_kj_mol, "kJ/mol").to("J/mol")
        t1 = _q(t1_degC, "degC").to("K")
        t2 = _q(t2_degC, "degC").to("K")
        # F-V5 domain guard: absolute temperatures must be > 0 K (the
        # 1/T terms divide by them; -273.15 degC = 0 K would raise
        # ZeroDivisionError — typed out_of_domain instead, the V8.1.2
        # 1995f7e75 lesson applied to the engine copy)
        if float(t1.magnitude) <= 0.0 or float(t2.magnitude) <= 0.0:
            return _result(
                "arrhenius_rate_ratio", "thermal_aging", "REFUSED",
                None, "dimensionless", "unavailable",
                {"error": "out_of_domain: absolute temperatures must "
                          "be > 0 K (got "
                          f"T1={float(t1.magnitude)} K, "
                          f"T2={float(t2.magnitude)} K) — typed "
                          "refusal, never a raise (F-V5)"})
        exponent = (-float(ea.magnitude / (R_GAS.magnitude * 1000))
                    * (1.0 / t2.magnitude - 1.0 / t1.magnitude))
        # F-V5 saturation bounds (the 1995f7e75 pattern): the exponent
        # saturates beyond the double range instead of raising
        # OverflowError — in-range values are unaffected, the clamp is
        # disclosed in-band
        saturated = None
        if exponent > 709.78:
            exponent, saturated = 709.78, "upper"
        elif exponent < -745.0:
            exponent, saturated = -745.0, "lower"
        ratio = math.exp(exponent)
        if saturated == "upper":
            ratio = 1e308
        elif saturated == "lower":
            ratio = 0.0
        direction = "worsens" if ratio > 1.0 + 1e-12 else (
            "improves" if ratio < 1.0 - 1e-12 else "neutral")
        detail = {
            "ea": f"{ea}", "t1": f"{t1}", "t2": f"{t2}",
            "basis": "k2/k1 = exp(-Ea/R (1/T2 - 1/T1)) — rate ratio "
                     "> 1 means the proposed regime consumes life "
                     "faster (accelerated-aging equivalence)"}
        if saturated:
            detail["saturated"] = (
                f"exponent clamped at the "
                f"{'upper' if saturated == 'upper' else 'lower'} "
                "double-precision bound — the reported ratio is the "
                "clamped value, disclosed in-band (F-V5, the V8.1.2 "
                "1995f7e75 pattern)")
        return _result(
            "arrhenius_rate_ratio", "thermal_aging", "RUN", ratio,
            "dimensionless", direction, detail)
    except (TypeError, ValueError, ZeroDivisionError) as e:
        return _result("arrhenius_rate_ratio", "thermal_aging",
                       "REFUSED", None, "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 2: fouling U-degradation
#   U_dirty = 1 / (1/U_clean + Rf)  → duty loss vs clean
#   direction-of-effect: the intervention's claimed fouling-resistance
#   change dRf (after vs before) — dRf < 0 improves duty, dRf > 0
#   worsens; the computed duty-loss ratio carries the sign.
# ---------------------------------------------------------------------------
def fouling_u_degradation(u_clean_w_m2k: float, rf_after_m2k_w: float,
                          rf_before_m2k_w: float = 0.0
                          ) -> Dict[str, Any]:
    try:
        u_clean = _q(u_clean_w_m2k, "W/(m**2*K)")
        rf_a = _q(rf_after_m2k_w, "m**2*K/W")
        rf_b = _q(rf_before_m2k_w, "m**2*K/W")
        if float(u_clean.magnitude) <= 0 or float(rf_a.magnitude) < 0 \
                or float(rf_b.magnitude) < 0:
            raise ValueError("U_clean must be > 0; Rf values >= 0")
        u_after = 1.0 / (1.0 / float(u_clean.magnitude)
                         + float(rf_a.magnitude))
        u_before = 1.0 / (1.0 / float(u_clean.magnitude)
                          + float(rf_b.magnitude))
        duty_ratio = u_after / u_before
        direction = "worsens" if duty_ratio < 1.0 - 1e-12 else (
            "improves" if duty_ratio > 1.0 + 1e-12 else "neutral")
        return _result(
            "fouling_u_degradation", "fouling", "RUN", duty_ratio,
            "dimensionless", direction,
            {"u_clean": f"{u_clean}", "rf_after": f"{rf_a}",
             "rf_before": f"{rf_b}",
             "u_after_w_m2k": round(u_after, 2),
             "basis": "U_dirty = 1/(1/U_clean + Rf); duty ratio "
                      "< 1 means the intervention as claimed LOSES "
                      "duty — an inverted prose direction cannot "
                      "survive this check"})
    except (TypeError, ValueError) as e:
        return _result("fouling_u_degradation", "fouling", "REFUSED",
                       None, "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 3: Langelier Saturation Index (scaling)
#   LSI = pH - pHs;  pHs = (9.3 + A + B) - (C + D)
#   A = (log10(TDS mg/L) - 1)/10
#   B = -13.12*log10(T_degC + 273) + 34.55
#   C = log10(Ca hardness as CaCO3 mg/L) - 0.4
#   D = log10(alkalinity as CaCO3 mg/L)
#   direction-of-effect: sign of the DELTA LSI between the proposed
#   regime and the baseline — positive delta = more scale-forming
#   (worsens for a scaling failure class).
# ---------------------------------------------------------------------------
def langelier_lsi(tds_mg_l: float, temp_degC: float,
                  ca_hardness_mg_l_caco3: float,
                  alkalinity_mg_l_caco3: float, ph: float
                  ) -> Dict[str, Any]:
    try:
        if min(tds_mg_l, ca_hardness_mg_l_caco3, alkalinity_mg_l_caco3) \
                <= 0 or not (0 < ph < 14):
            raise ValueError("TDS/hardness/alkalinity > 0; 0 < pH < 14")
        a = (math.log10(tds_mg_l) - 1.0) / 10.0
        b = -13.12 * math.log10(temp_degC + 273.0) + 34.55
        c = math.log10(ca_hardness_mg_l_caco3) - 0.4
        d = math.log10(alkalinity_mg_l_caco3)
        phs = (9.3 + a + b) - (c + d)
        lsi = ph - phs
        direction = ("worsens" if lsi > 0 else
                     "improves" if lsi < 0 else "neutral")
        return _result(
            "langelier_lsi", "scaling", "RUN", lsi, "dimensionless",
            direction,
            {"phs": round(phs, 3), "ph": ph,
             "basis": "LSI = pH - pHs; LSI > 0 is scale-forming, "
                      "< 0 corrosive — the intervention's claimed "
                      "regime change must move LSI toward < 0 to "
                      "count as improving a scaling failure"})
    except (TypeError, ValueError) as e:
        return _result("langelier_lsi", "scaling", "REFUSED", None,
                       "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 4: NPSH margin (cavitation)
#   NPSHa = (P_atm - P_vap)/(rho*g) + h_suction - h_friction
#   margin = NPSHa - NPSHr; sign of the margin is the direction:
#   <= 0 the suction side sits in the cavitation regime (worsens),
#   > 0 it clears onset (improves relative to cavitation onset).
# ---------------------------------------------------------------------------
def npsh_margin(patm_kpa: float, pvap_kpa: float, rho_kg_m3: float,
                suction_head_m: float, friction_loss_m: float,
                npshr_m: float) -> Dict[str, Any]:
    try:
        g = pint.Quantity(9.80665, "m/s**2")
        # F-V5: the rho/pvap domain guard runs BEFORE the head division
        # (rho = 0 would raise ZeroDivisionError inside pint)
        if float(rho_kg_m3) <= 0 or float(pvap_kpa) <= 0:
            return _result(
                "npsh_margin", "cavitation", "REFUSED", None, "m",
                "unavailable",
                {"error": "out_of_domain: rho and vapour pressure must "
                          "be > 0 (got "
                          f"rho={rho_kg_m3}, pvap={pvap_kpa}) — typed "
                          "refusal, never a raise (F-V5)"})
        dp = (_q(patm_kpa, "kPa") - _q(pvap_kpa, "kPa")).to("Pa")
        rho = _q(rho_kg_m3, "kg/m**3")
        head = dp / (rho * g)                       # m of fluid
        hs = _q(suction_head_m, "m")
        hf = _q(friction_loss_m, "m")
        npsha = head + hs - hf
        npshr = _q(npshr_m, "m")
        margin = float((npsha - npshr).to("m").magnitude)
        direction = ("worsens" if margin <= 0.0 else "improves")
        return _result(
            "npsh_margin", "cavitation", "RUN", round(margin, 4), "m",
            direction,
            {"npsha_m": round(float(npsha.to("m").magnitude), 4),
             "npshr_m": float(npshr.magnitude),
             "basis": "NPSHa = (P_atm - P_vap)/(rho g) + h_suction - "
                      "h_friction; margin <= 0 means cavitation "
                      "regime — an 'improves' prose claim on a "
                      "non-positive margin cannot survive this check"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("npsh_margin", "cavitation", "REFUSED", None,
                       "m", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 5: frost/condensation psychrometric margin
#   Magnus dewpoint from (T, RH); margin = T_surface - T_dewpoint.
#   margin <= 0 = condensation/frost regime (worsens), > 0 clears it.
# ---------------------------------------------------------------------------
def dewpoint_frost_margin(t_air_degC: float, rh_percent: float,
                          t_surface_degC: float) -> Dict[str, Any]:
    try:
        t = _q(t_air_degC, "degC").to("degC").magnitude
        rhs = _q(rh_percent, "percent").to("percent").magnitude
        ts = _q(t_surface_degC, "degC").to("degC").magnitude
        if not (0.0 < rhs <= 100.0):
            raise ValueError("RH must be in (0, 100]")
        a, b = 17.625, 243.04          # Magnus-Tetens (over water)
        # F-V5 domain guards (the V8.1.2 'absurd dry-bulb' guard,
        # applied to the engine copy): b + t = 0 would divide by zero
        # in the alpha term; a - alpha = 0 would divide by zero in the
        # dewpoint term — typed refusal instead of a raise
        if (b + t) <= 0.0:
            return _result(
                "dewpoint_frost_margin", "frost_condensation",
                "REFUSED", None, "delta_degC", "unavailable",
                {"error": f"out_of_domain: dry-bulb {t} degC is below "
                          "the Magnus-Tetens validity floor "
                          "(-243.04 degC) — typed refusal, never a "
                          "raise (F-V5)"})
        alpha = math.log(rhs / 100.0) + a * t / (b + t)
        if abs(a - alpha) < 1e-12:
            return _result(
                "dewpoint_frost_margin", "frost_condensation",
                "REFUSED", None, "delta_degC", "unavailable",
                {"error": "out_of_domain: degenerate Magnus solution "
                          "(a == alpha) — typed refusal, never a "
                          "raise (F-V5)"})
        td = b * alpha / (a - alpha)
        margin = ts - td
        direction = ("worsens" if margin <= 0.0 else "improves")
        return _result(
            "dewpoint_frost_margin", "frost_condensation", "RUN",
            round(margin, 3), "delta_degC", direction,
            {"dewpoint_degC": round(td, 3), "t_surface_degC": ts,
             "basis": "Magnus dewpoint; T_surface - T_dewpoint <= 0 "
                      "means condensation/frost regime — the "
                      "intervention's claimed surface-temperature "
                      "regime must keep the margin positive"})
    except (TypeError, ValueError, ZeroDivisionError) as e:
        return _result("dewpoint_frost_margin", "frost_condensation",
                       "REFUSED", None, "delta_degC", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 6: Larson-Miller creep-life comparator
#   LMP = T_K * (C + log10(t_h)), C = 20 (classical steels).
#   delta = LMP(proposed) - LMP(baseline): the monotone parameter means
#   delta > 0 consumes creep life faster (worsens), delta < 0 improves.
# ---------------------------------------------------------------------------
def larson_miller_lmp(t1_degC: float, t1_h: float, t2_degC: float,
                      t2_h: float, c_const: float = 20.0
                      ) -> Dict[str, Any]:
    try:
        tk1 = _q(t1_degC, "degC").to("K").magnitude
        tk2 = _q(t2_degC, "degC").to("K").magnitude
        if min(t1_h, t2_h) <= 0 or min(tk1, tk2) <= 0:
            raise ValueError("times and temperatures must be > 0")
        lmp1 = tk1 * (c_const + math.log10(t1_h))
        lmp2 = tk2 * (c_const + math.log10(t2_h))
        delta = lmp2 - lmp1
        direction = ("worsens" if delta > 1e-9 else
                     "improves" if delta < -1e-9 else "neutral")
        return _result(
            "larson_miller_lmp", "creep", "RUN", round(delta, 1),
            "K", direction,
            {"lmp_baseline": round(lmp1, 1), "lmp_proposed":
             round(lmp2, 1), "c_const": c_const,
             "basis": "LMP = T_K (C + log10 t) — monotone in both T "
                      "and time at temperature; delta > 0 means the "
                      "proposed regime is harsher on creep life"})
    except (TypeError, ValueError) as e:
        return _result("larson_miller_lmp", "creep", "REFUSED", None,
                       "K", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 7: compressor surge margin (HO7-06 class: turbo surge)
#   margin = (P_surge - P_op) / P_surge at the operating point.
#   The anti-surge control convention keeps >=10% margin; at or below
#   it the operating point is in/near the surge regime (worsens).
# ---------------------------------------------------------------------------
def surge_margin(p_surge_kpa: float, p_op_kpa: float) -> Dict[str, Any]:
    try:
        ps_ = _q(p_surge_kpa, "kPa").to("kPa").magnitude
        po = _q(p_op_kpa, "kPa").to("kPa").magnitude
        if min(ps_, po) <= 0:
            raise ValueError("pressures must be > 0")
        margin = (ps_ - po) / ps_
        direction = ("worsens" if margin <= 0.10 else "improves")
        return _result(
            "surge_margin", "surge", "RUN", round(margin, 4),
            "dimensionless", direction,
            {"p_surge_kpa": ps_, "p_op_kpa": po,
             "basis": "surge margin = (P_surge - P_op)/P_surge; the "
                      "anti-surge convention keeps >=10% — at or below "
                      "it the load-rejection excursion reaches the "
                      "surge line (worsens)"})
    except (TypeError, ValueError) as e:
        return _result("surge_margin", "surge", "REFUSED", None,
                       "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 8: Miner fatigue damage on a Basquin S-N basis (HO7-08 class)
#   N(S) = A * S^-b;  D = n / N.  D > 1 = the unity bound is exceeded
#   (the failure materializes); within it the duty consumes life
#   (value carries the fraction; direction neutral by convention —
#   no improvement is claimed from damage arithmetic alone).
# ---------------------------------------------------------------------------
def fatigue_miner(n_cycles: float, stress_amp_mpa: float,
                  sn_a_mpa_pow_b: float, sn_b: float) -> Dict[str, Any]:
    try:
        n = float(n_cycles)
        s = _q(stress_amp_mpa, "MPa").magnitude
        a = float(sn_a_mpa_pow_b)
        b = float(sn_b)
        if n <= 0 or s <= 0 or a <= 0 or b <= 0:
            raise ValueError("cycles, stress, and S-N constants must "
                             "be > 0")
        big_n = a * float(s) ** (-b)
        damage = n / big_n
        direction = "worsens" if damage > 1.0 else "neutral"
        return _result(
            "fatigue_miner", "fatigue", "RUN", round(damage, 4),
            "dimensionless", direction,
            {"N_cycles": round(big_n, 1), "n_cycles": n,
             "basis": "Miner damage D = n/N(S), Basquin N = A S^-b; "
                      "D > 1 = the unity bound is exceeded (splice "
                      "fatigue/pull-out regime)"})
    except (TypeError, ValueError) as e:
        return _result("fatigue_miner", "fatigue", "REFUSED", None,
                       "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 9: desiccant breakthrough utilization (HO7-10 class)
#   U = m_air * (w_in - w_out) / (m_desiccant * q_e) — the moisture
#   load against the committed dynamic capacity. U >= 1 = the load
#   exceeds capacity: moisture breaks through (worsens).
# ---------------------------------------------------------------------------
def breakthrough_capacity(m_air_kg: float, w_in_kg_kg: float,
                          w_out_kg_kg: float, m_desiccant_kg: float,
                          q_e_kg_kg: float) -> Dict[str, Any]:
    try:
        m_air = _q(m_air_kg, "kg")
        m_des = _q(m_desiccant_kg, "kg")
        w_in = _q(w_in_kg_kg, "kg/kg")
        w_out = _q(w_out_kg_kg, "kg/kg")
        q_e = _q(q_e_kg_kg, "kg/kg")
        if float(m_air.magnitude) <= 0 or float(m_des.magnitude) <= 0:
            raise ValueError("air and desiccant masses must be > 0")
        if float((w_in - w_out).magnitude) < 0:
            raise ValueError("w_in must be >= w_out")
        if float(q_e.magnitude) <= 0:
            raise ValueError("equilibrium capacity must be > 0")
        u = float((m_air * (w_in - w_out) / (m_des * q_e)).magnitude)
        direction = "worsens" if u >= 1.0 else "improves"
        return _result(
            "breakthrough_capacity", "desiccant_breakthrough", "RUN",
            round(u, 4), "dimensionless", direction,
            {"basis": "U = m_air (w_in - w_out) / (m_desiccant q_e); "
                      "U >= 1 = the moisture load exceeds the "
                      "committed dynamic capacity — breakthrough "
                      "regime (ageing/incomplete regeneration)"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("breakthrough_capacity", "desiccant_breakthrough",
                       "REFUSED", None, "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 10: electrolytic gas evolution (Faraday) (HO7-01 class)
#   m_dot = I * M / (z * F) at each electrode — the evolved-gas rate
#   that drives bubble-burst aerosol (acid mist) entrainment. Delta
#   form: the proposed operating change's sign on the mist driver is
#   the sign of the computed rate change.
# ---------------------------------------------------------------------------
F_FARADAY = 96485.33212          # C/mol (CODATA exact)


def faraday_gas_rate(current_after_a: float, current_before_a: float,
                     molar_mass_g_mol: float, z_electrons: float
                     ) -> Dict[str, Any]:
    try:
        ia = _q(current_after_a, "A")
        ib = _q(current_before_a, "A")
        m = _q(molar_mass_g_mol, "g/mol").to("kg/mol")
        z = float(z_electrons)
        if z <= 0:
            raise ValueError("electron count z must be > 0")
        f = pint.Quantity(F_FARADAY, "C/mol")
        rate_a = (ia * m / (z * f)).to("kg/h")
        rate_b = (ib * m / (z * f)).to("kg/h")
        delta = float((rate_a - rate_b).magnitude)
        direction = ("worsens" if delta > 1e-12 else
                     "improves" if delta < -1e-12 else "neutral")
        return _result(
            "faraday_gas_rate", "electrolytic_mist", "RUN",
            round(delta, 6), "kg/h", direction,
            {"rate_after_kg_h": round(float(rate_a.magnitude), 6),
             "rate_before_kg_h": round(float(rate_b.magnitude), 6),
             "basis": "Faraday m_dot = I M / (z F); the evolved-gas "
                      "rate is the bubble-burst aerosol (acid mist) "
                      "driver at the anode — a rate increase worsens "
                      "the tankhouse exposure"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("faraday_gas_rate", "electrolytic_mist",
                       "REFUSED", None, "kg/h", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 11: Wagner number — secondary current distribution (HO7-05)
#   Wa = kappa * |dV/di| / L. Wa >= 1 = polarization smooths the
#   current distribution (uniform deposition); Wa < 1 = solution-
#   resistance-dominated nonuniformity: the nodulation/dendrite regime.
# ---------------------------------------------------------------------------
def wagner_number(conductivity_s_m: float,
                  polarization_slope_v_m2_a: float,
                  characteristic_length_m: float) -> Dict[str, Any]:
    try:
        kappa = _q(conductivity_s_m, "S/m")
        dvdi = _q(polarization_slope_v_m2_a, "V*m**2/A")
        length = _q(characteristic_length_m, "m")
        if float(length.magnitude) <= 0:
            raise ValueError("characteristic length must be > 0")
        wa = float((kappa * dvdi / length).to("dimensionless").magnitude)
        direction = ("improves" if wa >= 1.0 else "worsens")
        return _result(
            "wagner_number", "electrodeposition", "RUN", round(wa, 4),
            "dimensionless", direction,
            {"kappa_S_m": float(kappa.magnitude),
             "dV_di_V_m2_A": float(dvdi.magnitude),
             "L_m": float(length.magnitude),
             "basis": "Wa = kappa |dV/di| / L — the secondary/current "
                      "distribution uniformity criterion; Wa < 1 is "
                      "the nonuniform (nodulation/dendrite) regime"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("wagner_number", "electrodeposition", "REFUSED",
                       None, "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# check 12: surface-tension foam index (HO7-12 class)
#   phi = (sigma_ref - sigma_sludge) / sigma_ref — the fractional
#   surface-tension depression. Convention: phi >= 0.2 is the
#   foam-stable regime (filamentous/organic-load slurries depress
#   sigma from ~72 mN/m toward 45-55 mN/m), foaming carries sludge.
# ---------------------------------------------------------------------------
def foam_index(sigma_ref_mn_m: float, sigma_sludge_mn_m: float
               ) -> Dict[str, Any]:
    try:
        s_ref = _q(sigma_ref_mn_m, "mN/m")
        s_sl = _q(sigma_sludge_mn_m, "mN/m")
        if float(s_ref.magnitude) <= 0 or float(s_sl.magnitude) <= 0:
            raise ValueError("surface tensions must be > 0")
        phi = float(((s_ref - s_sl) / s_ref).to("dimensionless")
                    .magnitude)
        direction = "worsens" if phi >= 0.2 else (
            "improves" if phi > 0.0 else "neutral")
        return _result(
            "foam_index", "foaming", "RUN", round(phi, 4),
            "dimensionless", direction,
            {"sigma_ref_mN_m": float(s_ref.magnitude),
             "sigma_sludge_mN_m": float(s_sl.magnitude),
             "basis": "phi = (sigma_ref - sigma_sludge)/sigma_ref — "
                      "the surface-tension depression; phi >= 0.2 is "
                      "the foam-stable regime that carries sludge "
                      "into the gas dome"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("foam_index", "foaming", "REFUSED", None,
                       "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


# ---------------------------------------------------------------------------
# R62 (claim c-0085): registry expansion closing the P1 coverage gap on
# the full DEV corpus (direction 1). The 21 unrouted rows' failure
# texts mapped to 19 deterministic classes; 7 new pint-typed relations
# below (each domain-guarded -> typed REFUSED, never a raise), 12 rows
# reuse an existing relation that is the physically-right instrument
# (LSI for water-line corrosivity and emitter precipitate potential,
# fouling U for GT blade deposits, Miner fatigue for bearing spalling,
# Faraday gassing for opportunity-charge electrolyte loss, Arrhenius
# for the thermal-acceleration leg of hydrolysis/oxidation/aging
# families — the non-thermal legs stay PENDING_INPUTS on-row, never
# fabricated).
# ---------------------------------------------------------------------------
def archard_wear(load_n: float, sliding_distance_m: float,
                 hardness_pa: float,
                 wear_coeff: float) -> Dict[str, Any]:
    try:
        k = _q(wear_coeff, "dimensionless")
        f = _q(load_n, "N")
        s = _q(sliding_distance_m, "m")
        h = _q(hardness_pa, "Pa")
        if float(f.magnitude) <= 0:
            raise ValueError("load must be > 0")
        if float(s.magnitude) < 0:
            raise ValueError("sliding distance must be >= 0")
        if float(h.magnitude) <= 0:
            raise ValueError("hardness must be > 0 (the wear volume "
                             "divides by it)")
        if not 0.0 < float(k.magnitude) <= 1.0:
            raise ValueError("wear coefficient must be in (0, 1]")
        volume = (k * f * s / h).to("m^3")
        direction = ("worsens" if float(volume.magnitude) > 1e-15
                     else "neutral")
        return _result(
            "archard_wear", "mechanical_wear", "RUN",
            float(f"{volume.magnitude:.4g}"), "m^3", direction,
            {"load_N": float(f.magnitude),
             "sliding_distance_m": float(s.magnitude),
             "hardness_Pa": float(h.magnitude),
             "wear_coeff": float(k.magnitude),
             "basis": "Archard: V = K*F*s/H — wear volume grows with "
                      "load and sliding distance and shrinks with "
                      "hardness (rollers, screeds, brush/slip-ring "
                      "contact wear)"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("archard_wear", "mechanical_wear", "REFUSED",
                       None, "m^3", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def impact_erosion_rate(impact_flux_w_m2: float,
                        specific_removal_energy_j_m3: float,
                        exposure_s: float,
                        erosion_efficiency: float) -> Dict[str, Any]:
    try:
        flux = _q(impact_flux_w_m2, "W/m^2")
        e_rm = _q(specific_removal_energy_j_m3, "J/m^3")
        t = _q(exposure_s, "s")
        eff = _q(erosion_efficiency, "dimensionless")
        if float(flux.magnitude) <= 0:
            raise ValueError("impact flux must be > 0")
        if float(e_rm.magnitude) <= 0:
            raise ValueError("specific removal energy must be > 0 "
                             "(the depth divides by it)")
        if float(t.magnitude) < 0:
            raise ValueError("exposure time must be >= 0")
        if not 0.0 < float(eff.magnitude) <= 1.0:
            raise ValueError("erosion efficiency must be in (0, 1]")
        depth = (flux * eff * t / e_rm).to("m")
        direction = ("worsens" if float(depth.magnitude) > 1e-15
                     else "neutral")
        return _result(
            "impact_erosion_rate", "leading_edge_erosion", "RUN",
            float(f"{depth.magnitude:.4g}"), "m", direction,
            {"impact_flux_W_m2": float(flux.magnitude),
             "removal_energy_J_m3": float(e_rm.magnitude),
             "exposure_s": float(t.magnitude),
             "erosion_efficiency": float(eff.magnitude),
             "basis": "depth = (KE flux * efficiency * exposure) / "
                      "specific removal energy — rain/particle impact "
                      "material loss per unit area (leading-edge "
                      "coatings)"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("impact_erosion_rate", "leading_edge_erosion",
                       "REFUSED", None, "m", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def contact_erosion_per_operation(arc_charge_c: float,
                                  erosion_coeff_ug_per_c: float,
                                  operations_per_year: float
                                  ) -> Dict[str, Any]:
    try:
        m_op = (_q(arc_charge_c, "C")
                * _q(erosion_coeff_ug_per_c, "ug/C")).to("ug")
        ops = _q(operations_per_year, "dimensionless")
        if float(_q(arc_charge_c, "C").magnitude) <= 0:
            raise ValueError("arc charge per operation must be > 0")
        if float(_q(erosion_coeff_ug_per_c, "ug/C").magnitude) <= 0:
            raise ValueError("erosion coefficient must be > 0")
        if float(ops.magnitude) < 0:
            raise ValueError("operations per year must be >= 0")
        total_ug = float(m_op.magnitude) * float(ops.magnitude)
        direction = ("worsens" if total_ug > 1e-9 else "neutral")
        return _result(
            "contact_erosion_per_operation", "electrical_contact_erosion",
            "RUN", float(f"{total_ug:.4g}"), "ug/year", direction,
            {"arc_charge_C": float(arc_charge_c),
             "erosion_coeff_ug_per_C": float(erosion_coeff_ug_per_c),
             "operations_per_year": float(operations_per_year),
             "basis": "mass loss = arc charge * erosion coefficient "
                      "* operations (charge-transfer erosion of arcing "
                      "contacts — OLTC diverters, slip-ring/brush "
                      "pairs); resistance rise follows the mass loss"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("contact_erosion_per_operation",
                       "electrical_contact_erosion", "REFUSED", None,
                       "ug/year", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def biogenic_acid_thinning(h2s_flux_g_m2_day: float,
                           acid_yield_fraction: float,
                           neutralization_capacity_kg_m3: float
                           ) -> Dict[str, Any]:
    try:
        flux = _q(h2s_flux_g_m2_day, "g/(m^2*day)")
        if float(flux.magnitude) <= 0:
            raise ValueError("H2S flux must be > 0")
        if not 0.0 < float(acid_yield_fraction) <= 1.0:
            raise ValueError("acid yield fraction must be in (0, 1]")
        cap = _q(neutralization_capacity_kg_m3, "kg/m^3")
        if float(cap.magnitude) <= 0:
            raise ValueError("neutralization capacity must be > 0 "
                             "(the thinning rate divides by it)")
        # H2S -> H2SO4 molar conversion (2 H2S + 2 O2 -> H2SO4, i.e.
        # 98.08 g H2SO4 per 34.08 g H2S consumed at full oxidation)
        acid = (flux * float(acid_yield_fraction)
                * (98.08 / 34.08))          # Quantity g H2SO4/(m^2 day)
        thinning = (acid / cap).to("mm/day")
        direction = ("worsens" if float(thinning.magnitude) > 1e-9
                     else "neutral")
        return _result(
            "biogenic_acid_thinning", "biogenic_acid_corrosion", "RUN",
            float(f"{thinning.magnitude:.4g}"), "mm/day", direction,
            {"h2s_flux_g_m2_day": float(flux.magnitude),
             "acid_yield_fraction": float(acid_yield_fraction),
             "neutralization_capacity_kg_H2SO4_m3": float(cap.magnitude),
             "basis": "crown thinning = (H2S flux * yield * 98.08/34.08 "
                      "acid mass) / acid-neutralization capacity of the "
                      "cement matrix (Pomeroy-style biogenic sulfuric-"
                      "acid corrosion of concrete)"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("biogenic_acid_thinning", "biogenic_acid_corrosion",
                       "REFUSED", None, "mm/day", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def microbial_growth_rate(mu_ref_per_day: float, q10: float,
                          t_degC: float, t_ref_degC: float,
                          days: float) -> Dict[str, Any]:
    try:
        mu_ref = _q(mu_ref_per_day, "1/day")
        if float(mu_ref.magnitude) <= 0:
            raise ValueError("reference growth rate must be > 0")
        if not 0.0 < float(q10) <= 5.0:
            raise ValueError("Q10 must be in (0, 5]")
        if float(days) < 0:
            raise ValueError("exposure days must be >= 0")
        mu = float(mu_ref.magnitude) * float(q10) ** (
            (float(t_degC) - float(t_ref_degC)) / 10.0)
        exponent = mu * float(days)
        saturated = None
        if exponent > 709.78:
            exponent, saturated = 709.78, "upper"
        multiplier = math.exp(exponent)
        if saturated == "upper":
            multiplier = 1e308
        direction = ("worsens" if multiplier > 1.0 + 1e-12
                     else "neutral")
        detail = {
            "mu_ref_per_day": float(mu_ref.magnitude),
            "q10": float(q10), "t_degC": float(t_degC),
            "t_ref_degC": float(t_ref_degC), "days": float(days),
            "basis": "growth multiplier = exp(mu * days) with "
                     "mu = mu_ref * Q10^((T-Tref)/10) — the "
                     "temperature-accelerated exponential bloom "
                     "(Legionella-type colonization of warm basins)"}
        if saturated:
            detail["saturated"] = ("exponent clamped at the upper "
                                   "double-precision bound — the "
                                   "reported multiplier is the clamped "
                                   "value, disclosed in-band (F-V5 "
                                   "pattern)")
        return _result("microbial_growth_rate", "microbial_growth",
                       "RUN", float(f"{multiplier:.4g}"),
                       "dimensionless", direction, detail)
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("microbial_growth_rate", "microbial_growth",
                       "REFUSED", None, "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def dust_layer_ignition_margin(t_hot_surface_degC: float,
                               layer_ignition_degC: float,
                               layer_thickness_mm: float,
                               thickness_derate_degC_per_mm: float
                               ) -> Dict[str, Any]:
    try:
        t_surf = _q(t_hot_surface_degC, "degC")
        t_li = _q(layer_ignition_degC, "degC")
        thick = _q(layer_thickness_mm, "mm")
        derate = float(thickness_derate_degC_per_mm)
        if float(thick.magnitude) < 0:
            raise ValueError("layer thickness must be >= 0")
        if float(derate) < 0:
            raise ValueError("thickness derate must be >= 0")
        eff_li = float(t_li.magnitude) - float(derate) * float(
            thick.magnitude)
        margin = float(t_surf.magnitude) - eff_li
        direction = ("worsens" if margin >= 0 else "improves")
        return _result(
            "dust_layer_ignition_margin", "combustible_dust_ignition",
            "RUN", round(margin, 1), "degC", direction,
            {"t_hot_surface_degC": float(t_surf.magnitude),
             "layer_ignition_degC": float(t_li.magnitude),
             "layer_thickness_mm": float(thick.magnitude),
             "thickness_derate_degC_per_mm": float(derate),
             "effective_layer_ignition_degC": round(eff_li, 1),
             "basis": "margin = hot-surface temperature minus the "
                      "thickness-derated layer ignition temperature "
                      "(a thicker insulating dust layer lowers the "
                      "effective MIT); margin >= 0 is the ignition-"
                      "reachable regime (NFPA-654-style layer control)"})
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("dust_layer_ignition_margin",
                       "combustible_dust_ignition", "REFUSED", None,
                       "degC", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def humidity_permeability_ratio(alpha_per_rh_percent: float,
                                rh_percent: float,
                                rh_ref_percent: float
                                ) -> Dict[str, Any]:
    try:
        alpha = float(alpha_per_rh_percent)
        rh = float(rh_percent)
        rh_ref = float(rh_ref_percent)
        if alpha <= 0:
            raise ValueError("humidity sensitivity alpha must be > 0")
        if not 0.0 <= rh <= 100.0 or not 0.0 <= rh_ref <= 100.0:
            raise ValueError("relative humidity values must be in "
                             "[0, 100] %RH")
        exponent = alpha * (rh - rh_ref)
        saturated = None
        if exponent > 709.78:
            exponent, saturated = 709.78, "upper"
        ratio = math.exp(exponent)
        if saturated == "upper":
            ratio = 1e308
        direction = ("worsens" if ratio > 1.1 else
                     ("improves" if ratio < 0.9 else "neutral"))
        detail = {
            "alpha_per_rh_percent": alpha, "rh_percent": rh,
            "rh_ref_percent": rh_ref,
            "basis": "permeability ratio = exp(alpha * (RH - RHref)) — "
                     "the humidity-activated barrier loss of moisture-"
                     "sensitive polymer films (EVOH-class oxygen/"
                     "moisture barriers)"}
        if saturated:
            detail["saturated"] = ("exponent clamped at the upper "
                                   "double-precision bound (F-V5 "
                                   "pattern)")
        return _result("humidity_permeability_ratio",
                       "polymer_barrier_loss", "RUN",
                       float(f"{ratio:.4g}"), "dimensionless",
                       direction, detail)
    except (TypeError, ValueError, pint.DimensionalityError) as e:
        return _result("humidity_permeability_ratio",
                       "polymer_barrier_loss", "REFUSED", None,
                       "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})



# ---------------------------------------------------------------------------
# R103 (claim c-0117; AM89 directives 2+4, the ride-along computed legs
# of the ammonia-stripping direction bind + the caustic magnitude guard)
# ---------------------------------------------------------------------------

# typed Art. 9 assumption: the NH4+ <=> NH3(aq) + H+ dissociation
# enthalpy ~ +52.2 kJ/mol (the CRC basis) -> pKa(T) via van 't Hoff on
# the equilibrium constant: pKa(T) = 9.25 - (dH/R) * ln(T/298.15) ...
# the standard integrated form on 1/T: pKa(T2) = pKa(T1) +
# dH/(2.303*R) * (1/T2 - 1/T1); at 25 C, pKa = 9.25 (the classical
# ammonia-stripper design basis).
NH4_PKA_25C = 9.25
NH4_DH_DISS_KJ_MOL = 52.2
# typed Art. 9 assumption: NH3(g) -> NH3(aq) enthalpy of solution
# ~ -34.18 kJ/mol (exothermic; the NIST/CRC basis) -> Henry constant
# kH(T2)/kH(T1) = exp(-dH_sol/R * (1/T2 - 1/T1)) (van 't Hoff);
# solubility FALLS with T -> the stripping driving force rises.
NH3_DH_SOL_KJ_MOL = -34.18
# typed Art. 9 calibration: NaOH solubility anchors (CRC Handbook,
# g NaOH / 100 g water -> mass fraction w = g/(100+g)): 0 C: 42
# (w=0.2958), 20 C: 111 (w=0.5261), 100 C: 339 (w=0.7722);
# piecewise-linear in T between anchors. Solution density anchors
# (kg/L at 20-25 C, CRC): w=0: 1.000, 0.10: 1.109, 0.20: 1.219,
# 0.30: 1.328, 0.40: 1.430, 0.50: 1.525, 0.60: 1.615 (linear interp).
NAOH_SOL_ANCHORS = ((0.0, 0.2958), (20.0, 0.5261), (100.0, 0.7722))
NAOH_RHO_ANCHORS = ((0.0, 1.000), (0.10, 1.109), (0.20, 1.219),
                     (0.30, 1.328), (0.40, 1.430), (0.50, 1.525),
                     (0.60, 1.615))
NAOH_MOLAR_MASS_G_MOL = 39.997


def _interp(x: float, anchors: tuple) -> float:
    if x <= anchors[0][0]:
        return anchors[0][1]
    if x >= anchors[-1][0]:
        return anchors[-1][1]
    for (x0, y0), (x1, y1) in zip(anchors, anchors[1:]):
        if x0 <= x <= x1:
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return anchors[-1][1]


def ammonia_free_fraction(ph: float,
                          temp_degC: float = 25.0,
                          ph_ref: Optional[float] = None
                          ) -> Dict[str, Any]:
    """The NH4+ <=> NH3 equilibrium partition — the free (strippable)
    NH3 fraction 1/(1 + 10^(pKa - pH)), pKa 9.25 at 25 C with the
    typed van-'t-Hoff temperature correction. Direction: with ph_ref,
    RAISING pH toward/above the pKa is 'improves' (more free NH3, the
    stripper design basis); without, a neutral state read."""
    try:
        ph_f = float(ph)
        t_c = float(temp_degC)
        if not 0.0 <= ph_f <= 14.0:
            raise ValueError("pH must be in [0, 14]")
        if not 0.0 <= t_c <= 100.0:
            raise ValueError("temperature must be in [0, 100] degC")
        t_k = t_c + 273.15
        pka = NH4_PKA_25C + (NH4_DH_DISS_KJ_MOL * 1e3 /
                             (2.302585 * 8.314462618)) *             (1.0 / t_k - 1.0 / 298.15)
        frac = 1.0 / (1.0 + 10.0 ** (pka - ph_f))
        direction = "neutral"
        detail = {"ph": ph_f, "temp_degC": t_c, "pka_used": round(pka, 3),
                  "basis": "free NH3 fraction = 1/(1+10^(pKa-pH)); "
                           "pKa 9.25 @25C, dH_diss +52.2 kJ/mol "
                           "(van 't Hoff corrected)"}
        if ph_ref is not None:
            phr = float(ph_ref)
            if not 0.0 <= phr <= 14.0:
                raise ValueError("ph_ref must be in [0, 14]")
            frac_ref = 1.0 / (1.0 + 10.0 ** (pka - phr))
            direction = ("improves" if frac > frac_ref * 1.05 else
                         ("worsens" if frac < frac_ref * 0.95
                          else "neutral"))
            detail["ph_ref"] = phr
            detail["fraction_at_ph_ref"] = round(frac_ref, 4)
            detail["basis"] += "; direction vs the ph_ref partition"
        return _result("ammonia_free_fraction", "ammonia_stripping",
                       "RUN", float(f"{frac:.4g}"), "fraction",
                       direction, detail)
    except (TypeError, ValueError, OverflowError) as e:
        return _result("ammonia_free_fraction", "ammonia_stripping",
                       "REFUSED", None, "fraction", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def nh3_henry_ratio(t1_degC: float, t2_degC: float) -> Dict[str, Any]:
    """The van 't Hoff temperature dependence of the NH3 Henry
    constant: kH(T2)/kH(T1) = exp(-dH_sol/R * (1/T2 - 1/T1)), dH_sol
    -34.18 kJ/mol (exothermic dissolution). Direction: raising T
    LOWERS solubility (ratio < 0.9) -> 'improves' the stripping
    driving force; cooling 'worsens' it."""
    try:
        t1 = float(t1_degC) + 273.15
        t2 = float(t2_degC) + 273.15
        if t1 <= 0.0 or t2 <= 0.0:
            raise ValueError("temperatures must be above absolute zero")
        if not 0.0 <= t1 - 273.15 <= 200.0 or \
                not 0.0 <= t2 - 273.15 <= 200.0:
            raise ValueError("temperatures must be in [0, 200] degC")
        dh = NH3_DH_SOL_KJ_MOL * 1e3
        ratio = math.exp(-dh / 8.314462618 * (1.0 / t2 - 1.0 / t1))
        direction = ("improves" if ratio < 0.9 else
                     ("worsens" if ratio > 1.1 else "neutral"))
        return _result(
            "nh3_henry_ratio", "ammonia_stripping", "RUN",
            float(f"{ratio:.4g}"), "dimensionless", direction,
            {"t1_degC": t1 - 273.15, "t2_degC": t2 - 273.15,
             "dH_sol_kJ_mol": NH3_DH_SOL_KJ_MOL,
             "basis": "kH(T2)/kH(T1) = exp(-dH_sol/R*(1/T2-1/T1)); "
                      "exothermic dissolution -> solubility FALLS with "
                      "T -> the gas-stripping driving force rises "
                      "(van 't Hoff, the AM89 ride-along leg)"})
    except (TypeError, ValueError, OverflowError) as e:
        return _result("nh3_henry_ratio", "ammonia_stripping",
                       "REFUSED", None, "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


def naoh_solubility_guard(concentration_mol_l: Optional[float] = None,
                          mass_fraction: Optional[float] = None,
                          temp_degC: float = 25.0
                          ) -> Dict[str, Any]:
    """The caustic magnitude guard: a claimed aqueous NaOH
    concentration vs the saturation curve. A claim above saturation
    (margin > 1.0) is physically unrealizable — the HO14-04 committed
    byte claims '50 M NaOH' (>2.4x the ~20.6 M saturation at 25 C;
    the 50%-w/w/50-M confusion class). Direction: margin > 1.0
    'worsens' (unrealizable as stated); <= 1.0 'neutral' (feasible)."""
    try:
        t_c = float(temp_degC)
        if not 0.0 <= t_c <= 100.0:
            raise ValueError("temperature must be in [0, 100] degC")
        if (concentration_mol_l is None) == (mass_fraction is None):
            raise ValueError("exactly one of concentration_mol_l / "
                             "mass_fraction is required")
        if mass_fraction is not None:
            w = float(mass_fraction)
            if not 0.0 < w <= 1.0:
                raise ValueError("mass_fraction must be in (0, 1]")
            c_mol_l = w * _interp(w, NAOH_RHO_ANCHORS) * 1000.0 / \
                NAOH_MOLAR_MASS_G_MOL
        else:
            c_mol_l = float(concentration_mol_l)
            if not 0.0 < c_mol_l <= 60.0:
                raise ValueError("concentration_mol_L must be in "
                                 "(0, 60] mol/L")
            # invert c = w*rho(w)*1000/M for w (monotone in range)
            lo, hi = 1e-6, 0.80
            w = lo
            for _ in range(60):
                mid = 0.5 * (lo + hi)
                c_mid = mid * _interp(mid, NAOH_RHO_ANCHORS) * \
                    1000.0 / NAOH_MOLAR_MASS_G_MOL
                if c_mid < c_mol_l:
                    lo = mid
                else:
                    hi = mid
            w = 0.5 * (lo + hi)
        w_sat = _interp(t_c, NAOH_SOL_ANCHORS)
        margin = w / w_sat
        direction = "worsens" if margin > 1.0 else "neutral"
        detail = {"claimed_mass_fraction": round(w, 4),
                  "claimed_mol_l": round(c_mol_l, 3),
                  "saturation_mass_fraction_at_T": round(w_sat, 4),
                  "saturation_mol_l_approx": round(
                      w_sat * _interp(w_sat, NAOH_RHO_ANCHORS) * 1000.0
                      / NAOH_MOLAR_MASS_G_MOL, 2),
                  "temp_degC": t_c,
                  "basis": "NaOH solubility anchors (CRC): 42/111/339 "
                           "g per 100 g water at 0/20/100 C, linear in "
                           "T; density anchors linear in w; a claim "
                           "above the curve cannot exist as a single "
                           "aqueous phase at that T"}
        if margin > 1.0:
            detail["SATURATION_EXCEEDED"] = (
                f"the claimed concentration exceeds the NaOH "
                f"saturation at {t_c:g} C by {margin:.2f}x — "
                "physically unrealizable as stated (the 50%-w/w vs "
                "50-M confusion class)")
        return _result("naoh_solubility_guard", "caustic_dosing",
                       "RUN", float(f"{margin:.4g}"), "dimensionless",
                       direction, detail)
    except (TypeError, ValueError, OverflowError) as e:
        return _result("naoh_solubility_guard", "caustic_dosing",
                       "REFUSED", None, "dimensionless", "unavailable",
                       {"error": f"{type(e).__name__}: {e}"})


CHECKS = {
    "arrhenius_rate_ratio": arrhenius_rate_ratio,
    "fouling_u_degradation": fouling_u_degradation,
    "langelier_lsi": langelier_lsi,
    "npsh_margin": npsh_margin,
    "dewpoint_frost_margin": dewpoint_frost_margin,
    "larson_miller_lmp": larson_miller_lmp,
    "surge_margin": surge_margin,
    "fatigue_miner": fatigue_miner,
    "breakthrough_capacity": breakthrough_capacity,
    "faraday_gas_rate": faraday_gas_rate,
    "wagner_number": wagner_number,
    "foam_index": foam_index,
    "archard_wear": archard_wear,
    "impact_erosion_rate": impact_erosion_rate,
    "contact_erosion_per_operation": contact_erosion_per_operation,
    "biogenic_acid_thinning": biogenic_acid_thinning,
    "microbial_growth_rate": microbial_growth_rate,
    "dust_layer_ignition_margin": dust_layer_ignition_margin,
    "humidity_permeability_ratio": humidity_permeability_ratio,
    "ammonia_free_fraction": ammonia_free_fraction,
    "nh3_henry_ratio": nh3_henry_ratio,
    "naoh_solubility_guard": naoh_solubility_guard,
}

CHECKS_BY_FAILURE_CLASS = {
    "thermal_aging": ["arrhenius_rate_ratio"],
    "fouling": ["fouling_u_degradation"],
    "scaling": ["langelier_lsi", "fouling_u_degradation"],
    "cavitation": ["npsh_margin"],
    "frost_condensation": ["dewpoint_frost_margin"],
    "creep": ["larson_miller_lmp", "arrhenius_rate_ratio"],
    "surge": ["surge_margin"],
    "fatigue": ["fatigue_miner"],
    "desiccant_breakthrough": ["breakthrough_capacity"],
    "electrolytic_mist": ["faraday_gas_rate"],
    "electrodeposition": ["wagner_number"],
    "foaming": ["foam_index"],
    # R62 (c-0085) expansion classes: 19 deterministic classes covering
    # the 21 previously-unrouted DEV rows (failure_class=None ->
    # NO_APPLICABLE). Where an existing relation is the physically-
    # right instrument it is reused; 7 new relations carry the rest.
    "water_line_corrosion": ["langelier_lsi"],
    "gt_blade_fouling": ["fouling_u_degradation"],
    "biogenic_acid_corrosion": ["biogenic_acid_thinning"],
    "electrical_contact_erosion": ["contact_erosion_per_operation"],
    "leading_edge_erosion": ["impact_erosion_rate"],
    "microbial_growth": ["microbial_growth_rate"],
    "combustible_dust_ignition": ["dust_layer_ignition_margin"],
    "mineral_clogging": ["langelier_lsi"],
    "mechanical_wear": ["archard_wear"],
    "polymer_seal_aging": ["arrhenius_rate_ratio"],
    "lead_acid_watering": ["faraday_gas_rate"],
    "lead_acid_grid_corrosion": ["arrhenius_rate_ratio"],
    "polymer_barrier_loss": ["humidity_permeability_ratio"],
    "electrolyte_dryout": ["arrhenius_rate_ratio"],
    "cell_imbalance_drift": ["arrhenius_rate_ratio"],
    "bearing_spalling_fatigue": ["fatigue_miner"],
    "insulation_pd_aging": ["arrhenius_rate_ratio"],
    "perovskite_degradation": ["arrhenius_rate_ratio"],
    "insulating_fluid_oxidation": ["arrhenius_rate_ratio"],
    # R103 (c-0117): the AM89 ride-along legs
    "ammonia_stripping": ["ammonia_free_fraction",
                          "nh3_henry_ratio"],
    "caustic_dosing": ["naoh_solubility_guard"],
}



# ---------------------------------------------------------------------------
# R54 (claim c-0072): the deterministic failure-class router + the
# committed reference scenarios. The router maps failure TEXT to a
# registry class by keyword rules (first match wins, specific before
# generic, None when nothing matches — typed, never a prose fallback);
# the reference scenarios are the per-check committed input sets the
# P1 measurement runs to prove each relation RUNS with real units
# (the labelled DEV rows carry no numeric context — on-row claims
# stay PENDING_INPUTS; the scenarios are wiring proofs, not data).
# ---------------------------------------------------------------------------
_CLASS_RULES = (
    # R103 (c-0117): specific water-chemistry classes first
    ("ammonia_stripping",
     ("ammonia strip", "ammonia removal", "nh3 removal",
      "stripping efficiency", "air stripping")),
    ("caustic_dosing", ("caustic", "naoh", "sodium hydroxide")),
    # R62 (c-0085) expansion: specific classes FIRST (first match
    # wins). Keywords are collision-checked against every existing
    # rule — e.g. "leading-edge coating" (rain erosion) never fires on
    # a paver's bare "leading edge", and "electrolyte loss" (watering)
    # never fires on "Electrolyte dry-out".
    ("water_line_corrosion",
     ("lead line", "dissolved lead", "action level")),
    ("gt_blade_fouling",
     ("deposit on blades", "heat rate")),
    ("biogenic_acid_corrosion",
     ("sulfuric acid", "cement matrix", "h2s", "crown")),
    ("electrical_contact_erosion",
     ("arcing erodes", "diverter", "contact resistance", "slip-ring",
      "brush and slip")),
    ("leading_edge_erosion",
     ("leading-edge coating", "rain and particle", "rain erosion")),
    ("microbial_growth",
     ("legionella", "cfu", "colonize")),
    ("combustible_dust_ignition",
     ("lint", "ignited", "hot-bearing spark")),
    ("mineral_clogging",
     ("emitters", "calcium-phosphate", "precipitate")),
    ("mechanical_wear",
     ("roller", "belt slip", "door stall", "screed plate", "wear thin",
      "wear progresses")),
    ("polymer_seal_aging",
     ("gasket", "hardens and shrinks", "steam leak")),
    ("lead_acid_watering",
     ("opportunity charging", "electrolyte loss", "sulfate on plate")),
    ("lead_acid_grid_corrosion",
     ("grid corrosion", "grid cross-section", "float charge")),
    ("polymer_barrier_loss",
     ("ethylene-vinyl alcohol", "barrier properties", "evoh")),
    ("electrolyte_dryout",
     ("dry-out", "solvent evaporation", "seal permeation")),
    ("cell_imbalance_drift",
     ("self-discharge", "cell-to-cell", "imbalance")),
    ("bearing_spalling_fatigue",
     ("spalling", "inner-race", "race spall")),
    ("insulation_pd_aging",
     ("partial discharge", "stator winding", "ground fault")),
    ("perovskite_degradation",
     ("perovskite", "encapsulant", "moisture ingress")),
    ("insulating_fluid_oxidation",
     ("acid number", "mgkoh", "dissolved copper")),
    ("electrolytic_mist",
     ("acid aerosol", "oxygen evolution", "bubble", "tankhouse air",
      "electrowinning mist")),
    ("cavitation",
     ("cavitation", "vortex rope", "draft-tube", "npsh")),
    ("frost_condensation",
     ("frost", "defrost", "condensation", "dew point", "dewpoint")),
    ("electrodeposition",
     ("nodulation", "dendrite", "electrodeposition", "cathode",
      "plating")),
    ("surge", ("surge", "compressor stall", "anti-surge")),
    ("desiccant_breakthrough",
     ("desiccant", "breakthrough", "regeneration")),
    ("foaming", ("foam",)),
    ("fatigue", ("fatigue", "splice", "pull-out")),
    ("creep", ("creep", "larson", "long-term stress")),
    ("scaling", ("scale ", "scaling", "lsi", "mineral deposit")),
    ("fouling", ("fouling", "fouls", "tube deposit", "slime")),
    ("thermal_aging",
     ("scorch", "crosslink", "oxidation", "varnish", "capacity fade",
      "degradation", "aging", "ageing", "thermal")),
)

# F66 (R55): dew-point phrasing is ambiguous between frost_condensation
# and desiccant_breakthrough. The typed disambiguation: when dew-point
# language co-occurs with the desiccant-dryer context, the
# moisture-load/breakthrough class governs (the dew point is the
# dryer's OUTPUT metric, not a coil-surface regime); bare dew-point
# phrasing stays frost_condensation. Checked BEFORE _CLASS_RULES.
_DESICCANT_CONTEXT = ("desiccant", "dryer", "regeneration", "dry air")


def _classify_disambiguation(low: str):
    if ("dew point" in low or "dewpoint" in low) and any(
            ctx in low for ctx in _DESICCANT_CONTEXT):
        return "desiccant_breakthrough"
    return None


def classify_failure(text: str):
    """Deterministic failure-text -> registry class. The F66
    disambiguation pre-rule runs first (dew-point + desiccant-dryer
    context -> desiccant_breakthrough); then first keyword match wins
    (specific classes ordered before generic ones); None when no rule
    matches — the caller records PENDING_INPUTS rather than guessing a
    class. Zero LLM."""
    low = str(text).lower()
    pre = _classify_disambiguation(low)
    if pre is not None:
        return pre
    for fclass, kws in _CLASS_RULES:
        if any(kw in low for kw in kws):
            return fclass
    return None


REFERENCE_SCENARIOS = {
    "arrhenius_rate_ratio": {"ea_kj_mol": 80.0, "t1_degC": 60.0,
                             "t2_degC": 80.0},
    # R103 (c-0117) ride-along legs
    "ammonia_free_fraction": {"ph": 11.0, "temp_degC": 25.0,
                              "ph_ref": 8.5},
    "nh3_henry_ratio": {"t1_degC": 25.0, "t2_degC": 60.0},
    "naoh_solubility_guard": {"concentration_mol_l": 19.0,
                              "temp_degC": 25.0},
    "fouling_u_degradation": {"u_clean_w_m2k": 2000.0,
                              "rf_after_m2k_w": 0.0004,
                              "rf_before_m2k_w": 0.0002},
    "langelier_lsi": {"tds_mg_l": 500.0, "temp_degC": 25.0,
                      "ph": 7.8, "ca_hardness_mg_l_caco3": 80.0,
                      "alkalinity_mg_l_caco3": 100.0},
    "npsh_margin": {"patm_kpa": 101.325, "pvap_kpa": 12.3,
                    "rho_kg_m3": 988.0, "suction_head_m": 2.0,
                    "friction_loss_m": 1.5, "npshr_m": 3.0},
    "dewpoint_frost_margin": {"t_air_degC": 25.0, "rh_percent": 60.0,
                              "t_surface_degC": 10.0},
    "larson_miller_lmp": {"t1_degC": 550.0, "t1_h": 100000.0,
                          "t2_degC": 570.0, "t2_h": 100000.0},
    "surge_margin": {"p_surge_kpa": 420.0, "p_op_kpa": 360.0},
    "fatigue_miner": {"n_cycles": 100000.0, "stress_amp_mpa": 120.0,
                      "sn_a_mpa_pow_b": 1.0e12, "sn_b": 3.0},
    "breakthrough_capacity": {"m_air_kg": 100.0, "w_in_kg_kg": 0.010,
                              "w_out_kg_kg": 0.001,
                              "m_desiccant_kg": 10.0,
                              "q_e_kg_kg": 0.125},
    "faraday_gas_rate": {"current_after_a": 10000.0,
                         "current_before_a": 8000.0,
                         "molar_mass_g_mol": 32.0, "z_electrons": 4},
    "wagner_number": {"conductivity_s_m": 40.0,
                      "polarization_slope_v_m2_a": 0.02,
                      "characteristic_length_m": 0.3},
    "foam_index": {"sigma_ref_mn_m": 72.0, "sigma_sludge_mn_m": 45.0},
    # R62 (c-0085) expansion scenarios — real magnitudes from the
    # relation domains (elevator/PA roller, rain-eroded coating, OLTC
    # diverter, sewer crown, Legionella basin, dryer-duct lint, EVOH
    # distribution humidity)
    "archard_wear": {"load_n": 500.0, "sliding_distance_m": 50000.0,
                     "hardness_pa": 1.0e8, "wear_coeff": 2.0e-3},
    "impact_erosion_rate": {"impact_flux_w_m2": 5.0,
                            "specific_removal_energy_j_m3": 5.0e6,
                            "exposure_s": 3.15e7,
                            "erosion_efficiency": 5.0e-5},
    "contact_erosion_per_operation": {"arc_charge_c": 30.0,
                                      "erosion_coeff_ug_per_c": 15.0,
                                      "operations_per_year": 6000.0},
    "biogenic_acid_thinning": {"h2s_flux_g_m2_day": 1.0,
                               "acid_yield_fraction": 0.85,
                               "neutralization_capacity_kg_m3": 75.0},
    "microbial_growth_rate": {"mu_ref_per_day": 0.25, "q10": 2.2,
                              "t_degC": 32.0, "t_ref_degC": 20.0,
                              "days": 30.0},
    "dust_layer_ignition_margin": {"t_hot_surface_degC": 220.0,
                                   "layer_ignition_degC": 350.0,
                                   "layer_thickness_mm": 10.0,
                                   "thickness_derate_degC_per_mm": 15.0},
    "humidity_permeability_ratio": {"alpha_per_rh_percent": 0.09,
                                    "rh_percent": 85.0,
                                    "rh_ref_percent": 0.0},
}


def run_check(check_id: str, **kwargs) -> Dict[str, Any]:
    """Registry entry point: run one computed check by id. Unknown ids
    are a typed refusal (never a prose fallback)."""
    fn = CHECKS.get(check_id)
    if fn is None:
        return _result(check_id, "unknown", "REFUSED", None,
                       "dimensionless", "unavailable",
                       {"error": f"unknown check id {check_id!r} — "
                                 "the registry is the only path"})
    return fn(**kwargs)


def check_for_failure_class(failure_class: str) -> list:
    return CHECKS_BY_FAILURE_CLASS.get(failure_class, [])
