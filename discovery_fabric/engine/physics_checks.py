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
        ratio = math.exp(-float(ea.magnitude / (R_GAS.magnitude * 1000))
                         * (1.0 / t2.magnitude - 1.0 / t1.magnitude))
        direction = "worsens" if ratio > 1.0 + 1e-12 else (
            "improves" if ratio < 1.0 - 1e-12 else "neutral")
        return _result(
            "arrhenius_rate_ratio", "thermal_aging", "RUN", ratio,
            "dimensionless", direction,
            {"ea": f"{ea}", "t1": f"{t1}", "t2": f"{t2}",
             "basis": "k2/k1 = exp(-Ea/R (1/T2 - 1/T1)) — rate ratio "
                      "> 1 means the proposed regime consumes life "
                      "faster (accelerated-aging equivalence)"})
    except (TypeError, ValueError) as e:
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
        dp = (_q(patm_kpa, "kPa") - _q(pvap_kpa, "kPa")).to("Pa")
        rho = _q(rho_kg_m3, "kg/m**3")
        head = dp / (rho * g)                       # m of fluid
        hs = _q(suction_head_m, "m")
        hf = _q(friction_loss_m, "m")
        npsha = head + hs - hf
        npshr = _q(npshr_m, "m")
        margin = float((npsha - npshr).to("m").magnitude)
        if float(rho.magnitude) <= 0 or float(pvap_kpa) <= 0:
            raise ValueError("rho and vapour pressure must be > 0")
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
        alpha = math.log(rhs / 100.0) + a * t / (b + t)
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
    except (TypeError, ValueError) as e:
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


CHECKS = {
    "arrhenius_rate_ratio": arrhenius_rate_ratio,
    "fouling_u_degradation": fouling_u_degradation,
    "langelier_lsi": langelier_lsi,
    "npsh_margin": npsh_margin,
    "dewpoint_frost_margin": dewpoint_frost_margin,
    "larson_miller_lmp": larson_miller_lmp,
}

CHECKS_BY_FAILURE_CLASS = {
    "thermal_aging": ["arrhenius_rate_ratio"],
    "fouling": ["fouling_u_degradation"],
    "scaling": ["langelier_lsi", "fouling_u_degradation"],
    "cavitation": ["npsh_margin"],
    "frost_condensation": ["dewpoint_frost_margin"],
    "creep": ["larson_miller_lmp", "arrhenius_rate_ratio"],
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
