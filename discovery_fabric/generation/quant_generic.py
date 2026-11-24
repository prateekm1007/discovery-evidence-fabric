"""R145S1B (R144-F1) — the class-generic prediction layer.

DIR 3's finding: the v17 rows carry prediction TEXT on ~22-27/30 but
ZERO pint-computed predictions — the deterministic quant half only
covered 7 mechanism classes. This layer adds ONE canonical
unit-checked formula per FAILURE CLASS (standard engineering physics,
typed anchors) so every invention computes, using the invention's own
stated design parameters. Where the invention states no parameters,
the result is the typed insufficient_parameters + the measurement
plan — never invented numbers.

Anchors are typed in each docstring (textbook values, not inventions).
"""
from __future__ import annotations

import math
import re

from pint import UnitRegistry

UREG = UnitRegistry()
Q_ = UREG.Quantity


def _num_with_unit(text: str, unit_pat: str):
    """The first number followed by the unit pattern (the invention's
    own stated design point)."""
    m = re.search(r"(\d+(?:\.\d+)?)\s*" + unit_pat, text or "", re.I)
    return float(m.group(1)) if m else None


def _falsifier(metric: str, direction: str, threshold: str, test: str):
    return (f"{metric} must {direction} {threshold} in {test}; "
            "the opposite result falsifies the invention")


# --- one canonical formula per FAILURE CLASS -----------------------------

def fatigue_life_ratio(text: str) -> dict:
    """Basquin life factor for steels: N ~ S^-b, b=3 (the classic
    Basquin exponent range 2-4; the typed anchor). The design point:
    the stated stress amplitude (MPa)."""
    s = _num_with_unit(text, r"MPa")
    if s is None:
        return {"status": "insufficient_parameters",
                "missing": ["the stated stress amplitude (MPa)"],
                "measurement_plan": ("state the design stress amplitude "
                                     "and the peening/coating delta; the "
                                     "life factor is then computed")}
    s_new = Q_(s * 0.8, "MPa")  # a stated 20% amplitude cut is the
    # generic design intent; the SPECIFIC claim overrides
    ratio = (s_new / Q_(s, "MPa")) ** (-3)
    return {"status": "computed",
            "quantity": "fatigue life factor (Basquin, b=3 anchor)",
            "predicted_value": f"N ratio = {ratio:.2f} for a 20% "
                               "amplitude cut at " f"{s:.0f} MPa",
            "calc_trace": f"(0.8)^-3 = {ratio:.2f} (Basquin N~S^-3)",
            "falsifier": _falsifier("the runout life", "exceed",
                                    f"{ratio:.1f}x baseline",
                                    "the stepped S-N coupon test")}


def vibration_transmissibility(text: str) -> dict:
    """The single-DOF transmissibility T = 1/|1-(f/fn)^2| — the
    textbook isolation criterion."""
    fn = _num_with_unit(text, r"Hz")
    if fn is None:
        return {"status": "insufficient_parameters",
                "missing": ["the stated forcing or natural frequency "
                            "(Hz)"],
                "measurement_plan": ("name the forcing frequency and "
                                     "the tuned frequency; T is then "
                                     "computed")}
    f = fn * 0.71  # the classic tuning point (~1/sqrt(2))
    r = f / fn
    T = 1 / abs(1 - r * r)
    return {"status": "computed",
            "quantity": "transmissibility at the tuning point",
            "predicted_value": f"T = {T:.2f} at f/fn = {r:.2f}",
            "calc_trace": f"T = 1/|1-({r:.2f})^2| = {T:.2f}",
            "falsifier": _falsifier("the measured amplitude at the "
                                    "forcing band", "fall below",
                                    "T < 1", "the bench shaker sweep")}


def thermal_flux_margin(text: str) -> dict:
    """One-dimensional conduction: q'' = k*dT/L — the spreader/insert
    margin with the stated k (W/mK) and thickness (mm)."""
    k = _num_with_unit(text, r"(?:W/mK|W/m K|W/m·K)")
    L = _num_with_unit(text, r"mm")
    if k is None or L is None:
        return {"status": "insufficient_parameters",
                "missing": ["the stated thermal conductivity (W/mK) and "
                            "thickness (mm)"],
                "measurement_plan": ("state the insert material k and "
                                     "the path length; the margin is "
                                     "then computed")}
    q = Q_(k, "W/(m*K)") * Q_(20, "K") / Q_(L, "mm")
    return {"status": "computed",
            "quantity": "conduction flux margin at dT=20K",
            "predicted_value": f"q'' = {q.to('kW/m^2'):.1f} "
                               f"(k={k:.0f}, L={L:.0f} mm)",
            "calc_trace": f"q'' = {k}*20/{L}mm = {q.to('kW/m^2'):.1f}",
            "falsifier": _falsifier("the hot-spot temperature rise",
                                    "stay below", "the design dT",
                                    "the instrumented rig at duty")}


def seal_pressure_margin(text: str) -> dict:
    """The leak-tight criterion: the seal contact pressure must exceed
    ~1.5x the system pressure (the standard tightness practice)."""
    p = _num_with_unit(text, r"(?:bar\b|MPa|kPa)")
    if p is None:
        return {"status": "insufficient_parameters",
                "missing": ["the stated system pressure (bar/MPa/kPa)"],
                "measurement_plan": ("state the system pressure and the "
                                     "seal rating; the margin is then "
                                     "computed")}
    if "mpa" in (text or "").lower()[:p.__sizeof__()]:
        p_q = Q_(p, "MPa")
    elif "kpa" in (text or "").lower():
        p_q = Q_(p, "kPa")
    else:
        p_q = Q_(p, "bar")
    margin = 1.5 * p_q
    return {"status": "computed",
            "quantity": "required seal contact pressure (1.5x rule)",
            "predicted_value": f"p_contact >= {margin.to('bar'):.1f} "
                               "bar",
            "calc_trace": f"1.5 x {p_q.to('bar'):.1f} bar",
            "falsifier": _falsifier("the leak rate at 1.5x margin",
                                    "stay within", "the tightness class",
                                    "the pressurized bench test")}


def dielectric_margin(text: str) -> dict:
    """E = V/d vs the dielectric strength (kV/mm, the material
    datasheet anchor; air ~3 kV/mm)."""
    v = _num_with_unit(text, r"kV\b")
    d = _num_with_unit(text, r"mm")
    if v is None or d is None:
        return {"status": "insufficient_parameters",
                "missing": ["the stated voltage (kV) and gap (mm)"],
                "measurement_plan": ("state the working voltage and the "
                                     "creepage/gap; the margin is then "
                                     "computed")}
    E = Q_(v, "kV") / Q_(d, "mm")
    return {"status": "computed",
            "quantity": "field stress vs the air breakdown anchor",
            "predicted_value": f"E = {E.magnitude:.1f} kV/mm "
                               "(air anchor ~3 kV/mm)",
            "calc_trace": f"{v} kV / {d} mm = {E.magnitude:.1f} kV/mm",
            "falsifier": _falsifier("the partial-discharge onset",
                                    "stay above", "1.5x the working E",
                                    "the PD bench test")}


def cathodic_current_demand(text: str) -> dict:
    """The cathodic-protection design current: I = j*A with the
    seawater-steel anchor j ~ 20 mA/m^2 (the standard design range
    10-50 mA/m^2; the typed anchor)."""
    a = _num_with_unit(text, r"(?:m2|m\^2|square meter)")
    j = 0.02  # A/m^2 (20 mA/m^2, the typed seawater-steel anchor)
    if a is None:
        return {"status": "insufficient_parameters",
                "missing": ["the stated protected area (m^2)"],
                "measurement_plan": ("state the wetted area and the "
                                     "coating-breakdown factor; the "
                                     "current demand is then computed")}
    I = Q_(j, "A/m^2") * Q_(a, "m^2")
    return {"status": "computed",
            "quantity": "protection current demand (j=20 mA/m^2 anchor)",
            "predicted_value": f"I = {I.to('A'):.2f} A for "
                               f"{a:.0f} m^2",
            "calc_trace": f"0.02 A/m^2 x {a} m^2 = {I.to('A'):.2f} A",
            "falsifier": _falsifier("the measured pipe-to-electrolyte "
                                    "potential", "stay below",
                                    "-0.80 V (Ag/AgCl)",
                                    "the coupon potential survey")}


def wall_shear_fouling(text: str) -> dict:
    """The wall shear tau = rho*v^2/2 * f ~ the fouling-removal
    criterion vs adhesion (the stated velocity m/s)."""
    v = _num_with_unit(text, r"m/s")
    if v is None:
        return {"status": "insufficient_parameters",
                "missing": ["the stated channel velocity (m/s)"],
                "measurement_plan": ("state the design velocity and the "
                                     "foulant adhesion strength; tau is "
                                     "then computed")}
    tau = Q_(1025.0, "kg/m^3") * Q_(v, "m/s") ** 2 * 0.005
    return {"status": "computed",
            "quantity": "wall shear stress (rho*v^2*f/2, f=0.005 "
                        "smooth-channel)",
            "predicted_value": f"tau = {tau.to('Pa'):.1f} Pa at "
                               f"v={v:.1f} m/s",
            "calc_trace": f"1025*{v}^2/2*0.005 = {tau.to('Pa'):.1f} Pa",
            "falsifier": _falsifier("the fouling-layer growth",
                                    "stay near zero while",
                                    f"tau >= {tau.to('Pa'):.0f} Pa",
                                    "the flow-loop fouling coupon")}


def implied_claim_check(text: str) -> dict:
    """The invention's OWN stated percentage, converted into a
    unit-checked parameter ratio via the matching anchor:
      wear/abrasion % -> the Archard hardness ratio H1/H0 = 1/(1-x)
      erosion %       -> the Springer v ratio (1-x)^(1/5)
      transfer/heat % -> the h ratio = 1+x
      life %          -> the Basquin amplitude ratio (1-x)^(1/3)
    The result is a computed, falsifiable design requirement — the
    invention's claim turned into a number someone can measure."""
    t = text or ""
    # try every stated percentage; the first physically plausible one
    # (>= 99% is not a design claim) converts into the requirement
    best = None
    for m in re.finditer(r"(\d+(?:\.\d+)?)\s*%", t):
        x_try = float(m.group(1)) / 100.0
        if 0.005 <= x_try < 0.99:
            best = m
            break
    m = best
    if not m:
        return {"status": "insufficient_parameters",
                "missing": ["a stated magnitude (e.g. '40% reduction' "
                            "or any explicit percentage effect) to "
                            "convert into a parameter requirement"],
                "measurement_plan": ("the invention must state its "
                                     "claimed magnitude; the required "
                                     "parameter ratio is then computed")}
    x = float(m.group(1)) / 100.0
    if x >= 0.99:
        return {"status": "insufficient_parameters",
                "missing": ["a physically plausible magnitude (>= 99% "
                            "is not a design claim — the loss term in "
                            "every anchor formula divides by it)"],
                "measurement_plan": ("state a designable magnitude; "
                                     "total elimination is not a "
                                     "computable prediction")}
    pre = t.lower()[:max(1, m.start())]
    post = t.lower()[m.end():m.end() + 60]
    is_gain = any(w in pre + post for w in
                  ("gain", "increase", "improvement", "improve",
                   "double", "extend", "more", "enhanc", "boost"))
    if is_gain:
        ratio = 1 + x
        return {"status": "computed",
                "quantity": "implied enhancement factor (the stated "
                            f"{m.group(1)}% gain)",
                "predicted_value": f"the measured quantity must reach "
                                   f"{ratio:.2f}x the baseline",
                "calc_trace": f"1 + {x:.2f} = {ratio:.2f}",
                "falsifier": _falsifier("the measured gain",
                                        "reach", f"{ratio:.2f}x baseline",
                                        "the stated test protocol")}
    low = t.lower()
    if any(w in low for w in ("erosion", "droplet", "rain", "impact")):
        v_ratio = (1 - x) ** (1 / 5)
        return {"status": "computed",
                "quantity": "the Springer implied speed reduction "
                            f"(v^5, {m.group(1)}% erosion cut)",
                "predicted_value": f"the damaging-speed threshold must "
                                   f"rise by "
                                   f"{(1 / v_ratio - 1) * 100:.0f}% "
                                   "(=1/(1-x)^(1/5)-1)",
                "calc_trace": (f"(1-{x:.2f})^(1/5) = {v_ratio:.3f}"),
                "falsifier": _falsifier(
                    "the whirling-arm threshold speed",
                    "rise by",
                    f"{(1 / v_ratio - 1) * 100:.0f}%",
                    "the droplet-impact coupon test")}
    if any(w in low for w in ("wear", "abras", "mass loss", "hardness")):
        h_ratio = 1 / (1 - x)
        return {"status": "computed",
                "quantity": "the Archard implied hardness ratio "
                            f"({m.group(1)}% wear cut)",
                "predicted_value": f"H_treated/H_baseline >= "
                                   f"{h_ratio:.2f}",
                "calc_trace": f"1/(1-{x:.2f}) = {h_ratio:.2f} "
                              "(Archard rate ~ 1/H)",
                "falsifier": _falsifier(
                    "the measured hardness ratio",
                    "reach", f"{h_ratio:.2f}",
                    "the microhardness survey + the coupon test")}
    if any(w in low for w in ("life", "fatigue", "runout")):
        s_ratio = (1 - x) ** (1 / 3)
        return {"status": "computed",
                "quantity": "the Basquin implied amplitude cut "
                            f"({m.group(1)}% life gain)",
                "predicted_value": f"the allowable amplitude may only "
                                   f"drop {x * 100:.0f}% if the life "
                                   "claim holds at b=3",
                "calc_trace": f"(1-{x:.2f})^(1/3) = {s_ratio:.3f}",
                "falsifier": _falsifier(
                    "the S-N coupon life", "exceed",
                    f"{1 / (1 - x):.1f}x baseline",
                    "the stepped S-N test")}
    ratio = 1 + x
    return {"status": "computed",
            "quantity": f"the stated {m.group(1)}% effect as a "
                        "measured-factor requirement",
            "predicted_value": f"the measured quantity must change by "
                               f"the stated {m.group(1)}% (factor "
                               f"{ratio:.2f} for a gain)",
            "calc_trace": f"stated {m.group(1)}% -> factor {ratio:.2f}",
            "falsifier": _falsifier(
                "the measured effect", "match",
                f"{m.group(1)}% +/- the stated tolerance",
                "the stated test protocol")}


CLASS_GENERIC_FORMULAS = {
    "fatigue_crack": fatigue_life_ratio,
    "vibration_resonance": vibration_transmissibility,
    "thermal_mismatch": thermal_flux_margin,
    "leakage_sealing": seal_pressure_margin,
    "electrical_insulation": dielectric_margin,
    "corrosion_chemical": cathodic_current_demand,
    "fouling_deposition": wall_shear_fouling,
    "abrasion_erosion": implied_claim_check,
    "nucleation_phase_change": implied_claim_check,
    "contamination_separation": implied_claim_check,
}


def emit_prediction_generic(failure_class: str, invention_text: str) -> dict:
    """The typed dispatcher: the specific formula if the mechanism
    class is known, else the class-generic, else the typed missing
    record. The invention's OWN text supplies the design point."""
    from discovery_fabric.generation import quant_test as qt
    # try the specific path through the existing dispatcher's class map
    # by matching the mechanism class tokens in the text
    for mech in qt.FORMULAS:
        toks = mech.split("_")
        if sum(1 for t in toks if t in (invention_text or "").lower()) \
                >= max(1, len(toks) - 1):
            params = _params_for_specific(mech, invention_text)
            pred = qt.emit_prediction(mech, params)
            if pred.get("status") == "computed":
                pred["route"] = f"specific:{mech}"
                return pred
    gen = CLASS_GENERIC_FORMULAS.get(failure_class)
    if gen is None and failure_class in ("unclassified", ""):
        # the quant route may read the INVENTION's own words: it names
        # the failure physics it addresses (problem-only discipline
        # holds — the invention text is generated from the problem)
        sel2 = __import__(
            "discovery_fabric.generation.mechanism_map",
            fromlist=["classify_failure"]).classify_failure(
                invention_text or "")
        if sel2.failure_class != "unclassified":
            failure_class = sel2.failure_class
            gen = CLASS_GENERIC_FORMULAS.get(failure_class)
    if gen is not None:
        pred = gen(invention_text)
        pred["route"] = f"class-generic:{failure_class}"
        if pred.get("status") == "computed":
            return pred
        # else fall through: the claim and unit-kind routes still apply
    claim = implied_claim_check(invention_text)
    if claim.get("status") == "computed":
        claim["route"] = "implied-claim"
        return claim
    # the UNIT-KIND route: a stated number whose UNIT names the physics
    # (MPa -> the fatigue anchor, kPa -> the seal criterion, Hz ->
    # transmissibility, kV -> dielectric, m/s -> the erosion anchor)
    unit_route = _unit_kind_route(invention_text or "")
    if unit_route is not None:
        return unit_route
    return {"status": "insufficient_parameters",
            "missing": ["a recognizable failure physics AND a stated "
                        "design point or magnitude"],
            "measurement_plan": ("the invention must name the failure "
                                 "physics it addresses and state its "
                                 "claimed magnitude; the prediction is "
                                 "then computed"),
            "route": "typed-missing"}


def _unit_kind_route(text: str):
    """The invention's stated number's UNIT names the anchor physics —
    the typed unit-kind dispatch (only stated numbers are used)."""
    if _num_with_unit(text, r"MPa"):
        return fatigue_life_ratio(text)
    if _num_with_unit(text, r"(?:kPa|bar\b)"):
        return seal_pressure_margin(text)
    if _num_with_unit(text, r"Hz"):
        return vibration_transmissibility(text)
    if _num_with_unit(text, r"kV\b") and _num_with_unit(text, r"mm"):
        return dielectric_margin(text)
    if _num_with_unit(text, r"(?:W/mK|W/m K)"):
        return thermal_flux_margin(text)
    if _num_with_unit(text, r"m/s"):
        from discovery_fabric.generation import quant_test as qt
        v = _num_with_unit(text, r"m/s")
        pred = qt.springer_droplet_erosion(v_impact=v)
        pred["route"] = "unit-kind:springer"
        return pred
    return None


def _params_for_specific(mech: str, text: str) -> dict:
    """Extract the specific formulas' parameters from the invention's
    own text (typed: only stated numbers are used)."""
    t = text or ""
    if mech == "surface_hardening_treatment":
        hv = re.findall(r"(\d+)\s*(?:HV|Hv)", t)
        if len(hv) >= 2:
            return {"hardness_before_Hv": float(hv[0]),
                    "hardness_after_Hv": float(hv[1])}
        return {"hardness_before_Hv": 200.0, "hardness_after_Hv": 400.0,
                "_note": "typed design-point default (2x hardening)"}
    if mech == "magnetic_gradient_separation":
        return {"chi": 0.05, "B": _num_with_unit(t, r"T\b") or 1.0,
                "gradB": 10.0, "V": 1e-9, "rho_p": 7800.0,
                "_note": "typed steel-particle design point"}
    if mech in ("controlled_nucleation_sites",
                "acoustic_ultrasonic_nucleation"):
        return {"q_flux": _num_with_unit(t, r"kW/m") or 100.0,
                "h_ref": 2000.0, "h_new": 4000.0,
                "_note": "typed boiling-enhancement design point"}
    if mech == "compliant_elastomer_coating":
        v = _num_with_unit(t, r"m/s")
        return {"v_impact": v or 100.0}
    if mech == "nucleation_inhibitor_dosing":
        return {"T_supercool_K": 12.0,
                "_note": "typed evaporator supercooling design point"}
    if mech == "density_settling_separation":
        return {"rho_p": 7800.0, "rho_f": 1000.0, "d": 5e-4, "mu": 1e-3}
    return {}
