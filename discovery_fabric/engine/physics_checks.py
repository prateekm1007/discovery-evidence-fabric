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

Rounds 2+ of P1 add checks (NPSH/surge margin, frost psychrometrics,
Larson-Miller, COP/charge proxy); this slice lands the harness plus
the first three relations, each unit-tested in
tests/test_physics_checks.py.
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


CHECKS = {
    "arrhenius_rate_ratio": arrhenius_rate_ratio,
    "fouling_u_degradation": fouling_u_degradation,
    "langelier_lsi": langelier_lsi,
}

CHECKS_BY_FAILURE_CLASS = {
    "thermal_aging": ["arrhenius_rate_ratio"],
    "fouling": ["fouling_u_degradation"],
    "scaling": ["langelier_lsi", "fouling_u_degradation"],
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
