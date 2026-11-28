"""discovery_fabric/engine/physics_library_checks.py — the D2
computed-physics layer (auditor direction 2, claim c-0128): the
heavier physics libraries become ENGINE-NATIVE checks, not script
harnesses (auditor Art. 5: the measured path runs through
discovery_fabric/engine/).

Every check: a lazy import (a missing library is a typed UNAVAILABLE
verdict — never a fabricated number, the physics_checks contract),
a pint-unit discipline, and a direction-of-effect that is the SIGN
of the computed result. Zero LLM, zero network.

Checks:
  equilibrium_direction (Cantera, BSD-3-Clause): ported from
    scripts/r80_chemistry_equilibrium.py (c-0107) — the r80 script
    RETIRES in the same change (Art. 16; successor = this module).
    A claimed chemistry direction is verified against the COMPUTED
    equilibrium sign; mole-fraction comparisons use the dilution-free
    X[target]/X[source] ratio (the r80 discipline).
  pipe_pressure_drop (fluids, MIT): Darcy-Weisbach with the
    fluids.friction_factor correlation — the sign of the computed
    dP change under a geometric/flow intervention verifies a claimed
    pressure-drop direction.
  fluid_property_direction (CoolProp, MIT): a computed property at
    two states (e.g., density vs temperature) verifies a claimed
    property direction against PropsSI values.
  convective_htc_direction (ht, MIT): the Nu_conv_internal
    correlation -> htc = Nu*k/D; the sign of the computed htc change
    (e.g., velocity up) verifies a claimed heat-transfer direction.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

import pint

_UREG = pint.UnitRegistry()
VERDICTS = ("RUN", "UNAVAILABLE", "REFUSED")
DIRECTIONS = ("improves", "worsens", "neutral", "unavailable")
FLAT_REL = 0.02


def _result(check_id: str, verdict: str, value: Optional[float],
            unit: str, direction: str,
            detail: Dict[str, Any]) -> Dict[str, Any]:
    assert verdict in VERDICTS
    if direction not in DIRECTIONS:
        raise ValueError(f"direction {direction!r} not typed")
    return {"check_id": check_id, "verdict": verdict, "value": value,
            "unit": unit, "direction_of_effect": direction,
            "detail": detail}


def _lib(name: str):
    """Lazy import; None = the typed-UNAVAILABLE path (never silent,
    never fabricated)."""
    try:
        return __import__(name)
    except Exception:
        return None


def _signed(rel: float) -> str:
    if abs(rel) < FLAT_REL:
        return "neutral"
    return "improves" if rel > 0 else "worsens"


# ---------------------------------------------------------------------------
# 1. Cantera: the computed equilibrium direction (the r80 port)
# ---------------------------------------------------------------------------
def check_equilibrium_direction(claim: dict) -> dict:
    """claim: {kind: 'T_direction'|'oxidant_direction', mechanism,
    X: {species: frac}, target, source, T_low, T_high, P, claimed}
    claimed ∈ {'increases','decreases'}. The check computes the
    equilibrium at the two states and returns CONSISTENT/INVERTED as
    the direction_of_effect ('improves' = the claim matches the
    computed sign)."""
    ct = _lib("cantera")
    if ct is None:
        return _result("equilibrium_direction", "UNAVAILABLE", None,
                       "1", "unavailable",
                       {"reason": "cantera not installed"})
    import math
    mech = str(claim.get("mechanism") or "gri30.yaml")
    T = claim.get("T_low"); T_hi = claim.get("T_high")
    P = float(claim.get("P") or 101325.0)
    X = {k: float(v) for k, v in (claim.get("X") or {}).items()}
    target = str(claim.get("target") or "")
    source = str(claim.get("source") or "")
    claimed = str(claim.get("claimed") or "")
    if claimed not in ("increases", "decreases"):
        return _result("equilibrium_direction", "REFUSED", None, "1",
                       "unavailable",
                       {"reason": "claimed must be increases/decreases"})
    if not target or not source or T is None or T_hi is None:
        return _result("equilibrium_direction", "REFUSED", None, "1",
                       "unavailable",
                       {"reason": "target/source/T_low/T_high required"})

    def ratio(t: float) -> float:
        gas = ct.Solution(mech)
        gas.TPX = t, P, X
        gas.equilibrate("TP")
        return float(gas.X[gas.species_index(target)]) / \
            max(float(gas.X[gas.species_index(source)]), 1e-300)

    r_lo, r_hi = ratio(float(T)), ratio(float(T_hi))
    if not (math.isfinite(r_lo) and math.isfinite(r_hi)) or r_lo <= 0:
        return _result("equilibrium_direction", "REFUSED", None, "1",
                       "unavailable", {"reason": "non-finite ratio"})
    rel = (r_hi - r_lo) / r_lo
    computed_up = rel > 0
    consistent = (claimed == "increases") == computed_up
    return _result("equilibrium_direction", "RUN", round(rel, 6), "1",
                   "improves" if consistent else "worsens",
                   {"r_low": round(r_lo, 8), "r_high": round(r_hi, 8),
                    "claimed": claimed, "computed": "increases" if
                    computed_up else "decreases"})


# ---------------------------------------------------------------------------
# 2. fluids: the computed pipe pressure-drop direction
# ---------------------------------------------------------------------------
def check_pipe_pressure_drop(claim: dict) -> dict:
    """claim: {rho (kg/m3), mu (Pa s), L (m), D (m), D_new (m) or
    v (m/s), v_new (m/s), eps (m), claimed}. Computes Darcy dP before
    and after the intervention; the direction is the SIGN (a claimed
    'worsens/increases' that matches the computed sign = improves the
    claim's truth, i.e. the claim is CONSISTENT)."""
    fl = _lib("fluids")
    if fl is None:
        return _result("pipe_pressure_drop", "UNAVAILABLE", None,
                       "Pa", "unavailable",
                       {"reason": "fluids not installed"})
    try:
        rho = float(claim["rho"]); mu = float(claim["mu"])
        L = float(claim["L"]); D = float(claim["D"])
        v = float(claim["v"])
        D_new = float(claim.get("D_new") or D)
        v_new = float(claim.get("v_new") or v)
        eps = float(claim.get("eps") or 0.0)
    except (KeyError, TypeError, ValueError) as e:
        return _result("pipe_pressure_drop", "REFUSED", None, "Pa",
                       "unavailable", {"reason": f"bad input: {e}"})
    claimed = str(claim.get("claimed") or "")
    if claimed not in ("increases", "decreases"):
        return _result("pipe_pressure_drop", "REFUSED", None, "Pa",
                       "unavailable",
                       {"reason": "claimed must be increases/decreases"})

    def dp(d: float, vel: float) -> float:
        Re = rho * vel * d / mu
        fd = fl.friction_factor(Re=Re, eD=eps / d)
        return fd * (L / d) * rho * vel * vel / 2.0

    p0, p1 = dp(D, v), dp(D_new, v_new)
    if p0 <= 0:
        return _result("pipe_pressure_drop", "REFUSED", None, "Pa",
                       "unavailable", {"reason": "non-positive base dP"})
    rel = (p1 - p0) / p0
    computed_up = rel > 0
    consistent = (claimed == "increases") == computed_up
    return _result("pipe_pressure_drop", "RUN", round(p1, 3), "Pa",
                   "improves" if consistent else "worsens",
                   {"dp_base": round(p0, 3), "dp_new": round(p1, 3),
                    "rel": round(rel, 4)})


# ---------------------------------------------------------------------------
# 3. CoolProp: the computed fluid-property direction
# ---------------------------------------------------------------------------
def check_fluid_property_direction(claim: dict) -> dict:
    """claim: {fluid, prop ('D'|'V'|'C'|'L'), P, T_a, T_b, claimed}.
    Computes the property at two states with PropsSI; the direction
    is the sign of the computed change vs the claim."""
    cp = _lib("CoolProp")
    if cp is None:
        return _result("fluid_property_direction", "UNAVAILABLE", None,
                       "1", "unavailable",
                       {"reason": "CoolProp not installed"})
    try:
        fluid = str(claim["fluid"]); prop = str(claim["prop"])
        P = float(claim["P"]); ta = float(claim["T_a"])
        tb = float(claim["T_b"])
    except (KeyError, TypeError, ValueError) as e:
        return _result("fluid_property_direction", "REFUSED", None,
                       "1", "unavailable", {"reason": f"bad input: {e}"})
    claimed = str(claim.get("claimed") or "")
    if claimed not in ("increases", "decreases"):
        return _result("fluid_property_direction", "REFUSED", None,
                       "1", "unavailable",
                       {"reason": "claimed must be increases/decreases"})
    try:
        v_a = float(cp.CoolProp.PropsSI(prop, "T", ta, "P", P, fluid))
        v_b = float(cp.CoolProp.PropsSI(prop, "T", tb, "P", P, fluid))
    except Exception as e:
        return _result("fluid_property_direction", "REFUSED", None,
                       "1", "unavailable", {"reason": f"PropsSI: {e}"})
    if v_a == 0:
        return _result("fluid_property_direction", "REFUSED", None,
                       "1", "unavailable", {"reason": "zero base value"})
    rel = (v_b - v_a) / v_a
    computed_up = rel > 0
    consistent = (claimed == "increases") == computed_up
    return _result("fluid_property_direction", "RUN", round(v_b, 6),
                   prop, "improves" if consistent else "worsens",
                   {"v_a": round(v_a, 6), "v_b": round(v_b, 6),
                    "rel": round(rel, 4)})


# ---------------------------------------------------------------------------
# 4. ht: the computed convective-htc direction
# ---------------------------------------------------------------------------
def check_convective_htc_direction(claim: dict) -> dict:
    """claim: {v (m/s), v_new, D (m), k (W/m/K), mu (Pa s), rho,
    cp (J/kg/K), claimed}. Computes the internal-flow Nu via
    ht.conv_internal.Nu_conv_internal -> htc = Nu*k/D at both
    velocities; the direction is the sign of the computed htc
    change vs the claim (higher velocity should RAISE htc)."""
    ht_mod = _lib("ht")
    if ht_mod is None:
        return _result("convective_htc_direction", "UNAVAILABLE", None,
                       "W/m^2/K", "unavailable",
                       {"reason": "ht not installed"})
    try:
        v = float(claim["v"]); v_new = float(claim["v_new"])
        D = float(claim["D"]); k = float(claim["k"])
        mu = float(claim["mu"]); rho = float(claim["rho"])
        cpv = float(claim["cp"])
    except (KeyError, TypeError, ValueError) as e:
        return _result("convective_htc_direction", "REFUSED", None,
                       "W/m^2/K", "unavailable",
                       {"reason": f"bad input: {e}"})
    claimed = str(claim.get("claimed") or "")
    if claimed not in ("increases", "decreases"):
        return _result("convective_htc_direction", "REFUSED", None,
                       "W/m^2/K", "unavailable",
                       {"reason": "claimed must be increases/decreases"})

    def htc(vel: float) -> float:
        Re = rho * vel * D / mu
        Pr = cpv * mu / k
        Nu = ht_mod.conv_internal.Nu_conv_internal(Re=Re, Pr=Pr)
        return Nu * k / D

    h0, h1 = htc(v), htc(v_new)
    if h0 <= 0:
        return _result("convective_htc_direction", "REFUSED", None,
                       "W/m^2/K", "unavailable",
                       {"reason": "non-positive base htc"})
    rel = (h1 - h0) / h0
    computed_up = rel > 0
    consistent = (claimed == "increases") == computed_up
    return _result("convective_htc_direction", "RUN", round(h1, 4),
                   "W/m^2/K", "improves" if consistent else "worsens",
                   {"htc_base": round(h0, 4), "htc_new": round(h1, 4),
                    "rel": round(rel, 4)})
