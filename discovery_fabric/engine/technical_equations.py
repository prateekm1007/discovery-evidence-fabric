"""discovery_fabric/engine/technical_equations.py — R383 THE ANALYTICAL
EQUATION LAYER (quantitative deterministic technical evaluator).

CEO directive (2026-09-01, IMPROVE THE INVENTION ENGINE):

> "6. Introduce additional deterministic evaluators where useful:
>    analytical equations, geometric calculations, simple numerical
>    models, domain-specific constraints."
> "4. Feed measured geometry back into technical evaluation."
> "Demonstrate CANDIDATE A -> TECHNICAL DIAGNOSIS -> REAL DESIGN
>  VARIABLE MUTATION -> NEW CAD / TECHNICAL STATE -> INDEPENDENT
>  EVALUATION -> CANDIDATE B ... technically better for a stated
>  reason."

This module is that layer (ADR_R383_ANALYTICAL_EVALUATOR.md):

  technical_state (R379)  --\
  parametric model         ---+--> bind_equations() --> evaluate_quantitatively()
  measurements (R380 CAD) --/         (deterministic)          |
                                                                 +- objective value + margin
                                                                 +- elasticity sensitivities
                                                                 +- magnitude-ranked limiting variable
                                                                 +- solve_for (bisection over the envelope)

Honesty rules that are STRUCTURAL here:
  - every computed output is COMPUTATIONAL_RESULT (rank 4) with a
    computation log naming every input, its source and class
    (Art. XXVIII / XXXVIII); MODELLED never becomes MEASURED
  - the state is NEVER written back to (Art. IX: evaluation is
    observational)
  - a VIOLATED or UNDECIDABLE validity predicate blocks the number
    entirely (Art. IV: no fallback computation, no "compute anyway")
  - equations are ENGINE-OWNED code (Art. XVIII: the LLM never writes
    physics); bindings are deterministic; a declared state dependency
    that CONTRADICTS the equation's monotonicity rejects the binding
    (STATE_PHYSICS_DISAGREEMENT — recorded, never resolved by
    preference, Art. II)
  - input values resolve GEOMETRY_MEASURED (the candidate's OWN
    validated built solid — CEO R383 focus 4) > EXTRACTED > MODELLED >
    ENGINEERING_REFERENCE constant; every use of a reference constant
    is logged; a declared state value always beats a constant
  - the binding constraint's limit class travels with the margin
    (Art. XXVII); the evaluator never invents a requirement
"""
from __future__ import annotations

import math
from typing import Any, Callable, Dict, List, Optional, Tuple

from .candidate import sha256_obj, utc_now
from .technical_state import get_technical_state

EVALUATOR_ID = "analytical_equation_v1"
FIDELITY_TIER = "ANALYTICAL_EQUATION"
EVIDENCE_RANK = 4              # COMPUTATIONAL_RESULT (Art. XXXVIII)
EQUATION_LAYER_VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# Declared thresholds (Art. XXVII — class + justification BEFORE use)
# ---------------------------------------------------------------------------
QUANTITATIVE_THRESHOLDS: Dict[str, Dict[str, Any]] = {
    "QUANT_MIN_RELATIVE_IMPROVEMENT": {
        "value": 0.005,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "a margin improvement below 0.5% of the binding limit's "
            "magnitude is computation-noise-level at this tier, not a "
            "defensible technical improvement; the K8 keep gate "
            "requires more than this"),
        "uncertainty": "declared convention, not a measurement"},
    "SOLVE_MARGIN_FACTOR": {
        "value": 0.10,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "solve-for targets limit * (1 + 10%): solving exactly onto "
            "the constraint boundary leaves zero robustness margin; "
            "the T-gates and K-gates still decide the proposal"),
        "uncertainty": "declared design convention"},
    "BISECTION_ITERATIONS": {
        "value": 60,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "deterministic bisection convergence for monotone "
            "relations; relative tolerance 1e-9 is 3+ orders below "
            "any declared engineering margin"),
        "uncertainty": "none (deterministic)"},
    "SENSITIVITY_STEP_FRACTION": {
        "value": 0.01,
        "epistemic_class": "ENGINEERING",
        "justification": (
            "central finite difference at +/-1% of the resolved input "
            "value: small enough to localize the derivative, large "
            "enough to stay above double-precision noise for the "
            "magnitude ranges in this registry"),
        "uncertainty": "derivative is local at the operating point"},
}

# ---------------------------------------------------------------------------
# Declared ENGINEERING REFERENCE constants (used ONLY when the candidate's
# own state does not declare the quantity; every use is logged; a declared
# state value always wins)
# ---------------------------------------------------------------------------
ENGINEERING_CONSTANTS: Dict[str, Dict[str, Any]] = {
    "viscosity": {
        "constant_id": "const:csf_viscosity",
        "name": "CSF dynamic viscosity (water-like)",
        "value": 1.0, "unit": "mPa·s",
        "epistemic_class": "ENGINEERING_REFERENCE",
        "source_note": (
            "cerebrospinal fluid is reported at ~1.0 mPa·s, essentially "
            "water viscosity at 37 C; a reference value for model "
            "computation, never a measurement of this candidate"),
        "uncertainty": "+/- 20% (literature spread)"},
    "fluid_density": {
        "constant_id": "const:water_density",
        "name": "water/CSF mass density",
        "value": 1000.0, "unit": "kg/m^3",
        "epistemic_class": "ENGINEERING_REFERENCE",
        "source_note": (
            "CSF density ~1004-1007 kg/m^3; water at 37 C is 993; 1000 "
            "is the standard reference value for model computation"),
        "uncertainty": "+/- 1%"},
    "gravity": {
        "constant_id": "const:standard_gravity",
        "name": "standard gravity",
        "value": 9.80665, "unit": "m/s^2",
        "epistemic_class": "ENGINEERING_REFERENCE",
        "source_note": "defined standard value (ISO 80000-3)",
        "uncertainty": "negligible for implant-scale height differences"},
}

# ---------------------------------------------------------------------------
# UNIT MACHINERY (deterministic normalization + SI conversion)
# ---------------------------------------------------------------------------
_UNIT_LONG_FORMS = {
    "millimeter": "mm", "millimeters": "mm", "millimetre": "mm",
    "millimetres": "mm", "centimeter": "cm", "centimeters": "cm",
    "meter": "m", "meters": "m", "metre": "m", "metres": "m",
    "micron": "um", "microns": "um", "micrometer": "um",
    "second": "s", "seconds": "s", "sec": "s",
    "hour": "hr", "hours": "hr", "h": "hr",
    "minute": "min", "minutes": "min",
    "pascal": "pa", "kilopascal": "kpa", "megapascal": "mpa",
    "gigapascal": "gpa", "millipascalsecond": "mpas",
    "centipoise": "cp", "hertz": "hz", "watt": "w", "watts": "w",
    "microwatt": "uw", "nanowatt": "nw", "milliwatt": "mw",
    "picofarad": "pf", "farad": "f", "volt": "v",
    "rayl": "rayl", "mrayl": "mrayl", "strain": "strain",
    "microstrain": "ustrain",
}

# normalized unit -> (factor to SI base, si_base symbol)
_UNIT_SI: Dict[str, Tuple[float, str]] = {
    # length
    "mm": (1e-3, "m"), "cm": (1e-2, "m"), "m": (1.0, "m"),
    "um": (1e-6, "m"),
    # area / volume
    "mm2": (1e-6, "m2"), "cm2": (1e-4, "m2"), "m2": (1.0, "m2"),
    "mm3": (1e-9, "m3"), "cm3": (1e-6, "m3"), "m3": (1.0, "m3"),
    "ml": (1e-6, "m3"), "ul": (1e-9, "m3"), "liter": (1e-3, "m3"),
    # time
    "s": (1.0, "s"), "min": (60.0, "s"), "hr": (3600.0, "s"),
    "day": (86400.0, "s"),
    # flow (volume/time) — composite units are resolved pairwise
    "ml/hr": (1e-6 / 3600.0, "m3/s"), "ml/h": (1e-6 / 3600.0, "m3/s"),
    "ml/min": (1e-6 / 60.0, "m3/s"), "ul/min": (1e-9 / 60.0, "m3/s"),
    "ul/hr": (1e-9 / 3600.0, "m3/s"),
    "ul/day": (1e-9 / 86400.0, "m3/s"), "ml/day": (1e-6 / 86400.0, "m3/s"),
    # pressure
    "pa": (1.0, "pa"), "kpa": (1e3, "pa"), "mpa": (1e6, "pa"),
    "gpa": (1e9, "pa"), "mmhg": (133.322, "pa"),
    # dynamic viscosity
    "pas": (1.0, "pa·s"), "mpas": (1e-3, "pa·s"), "cp": (1e-3, "pa·s"),
    # density
    "kg/m3": (1.0, "kg/m3"), "g/cm3": (1e3, "kg/m3"),
    # speed
    "m/s": (1.0, "m/s"), "mm/s": (1e-3, "m/s"),
    # frequency
    "hz": (1.0, "hz"), "khz": (1e3, "hz"), "mhz": (1e6, "hz"),
    # power
    "w": (1.0, "w"), "mw": (1e-3, "w"), "uw": (1e-6, "w"),
    "nw": (1e-9, "w"), "pw": (1e-12, "w"),
    # power density
    "w/m2": (1.0, "w/m2"), "mw/cm2": (10.0, "w/m2"),
    # capacitance
    "f": (1.0, "f"), "pf": (1e-12, "f"), "nf": (1e-9, "f"),
    # acoustic impedance
    "mrayl": (1e6, "pa·s/m"), "rayl": (1.0, "pa·s/m"),
    # strain
    "strain": (1.0, "strain"), "ustrain": (1e-6, "strain"),
    "%": (1e-2, "strain"),
    # attenuation
    "1/mm": (1e3, "1/m"), "1/cm": (100.0, "1/m"), "1/m": (1.0, "1/m"),
    # dimensionless
    "": (1.0, "ratio"), "ratio": (1.0, "ratio"),
    "fraction": (1.0, "ratio"), "dimensionless": (1.0, "ratio"),
    "none": (1.0, "ratio"), "-": (1.0, "ratio"),
}


def _norm_unit(unit: Any) -> str:
    """Deterministic unit normalization: lowercase, strip, unify
    unicode/superscripts, drop separators, map long forms."""
    if unit is None:
        return ""
    u = str(unit).strip().lower()
    u = (u.replace("µ", "u").replace("μ", "u")
          .replace("·", "").replace(".", "").replace(" ", "")
          .replace("^", "").replace("²", "2").replace("³", "3")
          .replace("–", "").replace("—", ""))
    u = _UNIT_LONG_FORMS.get(u, u)
    # composite flow/density forms: "ml/hr" etc. already tabled; a few
    # residual composites are assembled from their parts
    if u not in _UNIT_SI and "/" in u:
        num, den = u.split("/", 1)
        pair = {"ml": ("m3", 1e-6), "ul": ("m3", 1e-9),
                "hr": ("s", 3600.0), "min": ("s", 60.0),
                "day": ("s", 86400.0), "s": ("s", 1.0),
                "kg": ("kg", 1.0), "m": ("m", 1.0),
                "w": ("w", 1.0), "m2": ("m2", 1.0),
                "pa": ("pa", 1.0), "pa·s": ("pa·s", 1.0),
                "m3": ("m3", 1.0)}
        if num in pair and den in pair:
            (nb, nf), (db, df) = pair[num], pair[den]
            base = f"{nb}/{db}"
            _UNIT_SI[u] = (nf / df, base)
    return u


def unit_si(unit: Any) -> Optional[Tuple[float, str]]:
    """(factor, si_base) for a declared unit, or None when the unit is
    unknown — an unknown unit NEVER converts (Art. IV: no guessing)."""
    u = _norm_unit(unit)
    entry = _UNIT_SI.get(u)
    return entry if entry else None


def units_compatible(a: Any, b: Any) -> bool:
    ea, eb = unit_si(a), unit_si(b)
    if ea is None or eb is None:
        return False
    return ea[1] == eb[1]


def convert_value(value: float, from_unit: Any, to_unit: Any
                  ) -> Optional[float]:
    """Convert between compatible units (same SI base). Incompatible or
    unknown units return None — never a guess."""
    fa, fb = unit_si(from_unit), unit_si(to_unit)
    if fa is None or fb is None or fa[1] != fb[1]:
        return None
    return float(value) * fa[0] / fb[0]


def _tokens(text: Any) -> set:
    """Deterministic keyword tokens (>=3 chars) for role matching."""
    import re
    return {t for t in re.findall(r"[a-z]{3,}",
                                  str(text or "").lower()
                                  .replace("_", " "))}


# ---------------------------------------------------------------------------
# INPUT ROLE DEFINITIONS (shared across equations)
# roles carry: acceptable units, keyword aliases, optional constant
# ---------------------------------------------------------------------------
ROLE_DEFS: Dict[str, Dict[str, Any]] = {
    "lumen_diameter": {
        "units": ["mm"], "si_base": "m",
        "aliases": ["lumen", "diameter", "bore", "inner", "channel"],
        "constant": None},
    "flow_path_length": {
        "units": ["mm", "cm", "m"], "si_base": "m",
        "aliases": ["length", "path", "tube", "catheter", "segment"],
        "constant": None},
    "viscosity": {
        "units": ["mPa·s", "cP", "Pa·s"], "si_base": "pa·s",
        "aliases": ["viscosity", "dynamic", "fluid"],
        "constant": "viscosity"},
    "pressure_drop": {
        "units": ["mmHg", "Pa", "kPa"], "si_base": "pa",
        "aliases": ["pressure", "drop", "head", "differential", "delta",
                    "driving"],
        "constant": None},
    "fluid_density": {
        "units": ["kg/m^3", "g/cm^3"], "si_base": "kg/m3",
        "aliases": ["density", "mass"],
        "constant": "fluid_density"},
    "volumetric_flow": {
        "units": ["ml/hr", "ml/min", "ul/min", "ul/hr"], "si_base": "m3/s",
        "aliases": ["flow", "rate", "drainage", "perfusion", "efflux"],
        "constant": None},
    "contact_time": {
        "units": ["s"], "si_base": "s",
        "aliases": ["contact", "residence", "transit", "dwell", "time"],
        "constant": None},
    "height_difference": {
        "units": ["mm", "cm", "m"], "si_base": "m",
        "aliases": ["height", "elevation", "column", "vertical", "rise"],
        "constant": None},
    "radius": {
        "units": ["mm", "cm", "m"], "si_base": "m",
        "aliases": ["radius", "bore", "cylindrical"],
        "constant": None},
    "wall_thickness": {
        "units": ["mm", "um"], "si_base": "m",
        "aliases": ["wall", "thickness"],
        "constant": None},
    "internal_pressure": {
        "units": ["mmHg", "Pa", "kPa"], "si_base": "pa",
        "aliases": ["pressure", "internal", "transmural", "lumen"],
        "constant": None},
    "acoustic_impedance_1": {
        "units": ["MRayl"], "si_base": "pa·s/m",
        "aliases": ["impedance", "medium", "lumen", "first", "carrier",
                    "propagation"],
        "constant": None},
    "acoustic_impedance_2": {
        "units": ["MRayl"], "si_base": "pa·s/m",
        "aliases": ["impedance", "obstruction", "second", "target",
                    "lesion", "contrast", "stone"],
        "constant": None},
    "cell_area": {
        "units": ["mm2", "cm2"], "si_base": "m2",
        "aliases": ["area", "cell", "aperture", "active", "photovoltaic",
                    "photoreceiver"],
        "constant": None},
    "incident_irradiance": {
        "units": ["W/m^2", "mW/cm^2"], "si_base": "w/m2",
        "aliases": ["irradiance", "incident", "light", "flux", "power",
                    "intensity"],
        "constant": None},
    "attenuation_coefficient": {
        "units": ["1/mm", "1/cm"], "si_base": "1/m",
        "aliases": ["attenuation", "absorption", "extinction",
                    "coefficient"],
        "constant": None},
    "tissue_depth": {
        "units": ["mm", "cm"], "si_base": "m",
        "aliases": ["depth", "tissue", "penetration", "scalp", "overlying"],
        "constant": None},
    "cell_efficiency": {
        "units": ["", "fraction", "ratio", "dimensionless", "%"],
        "si_base": "ratio",
        "aliases": ["efficiency", "conversion", "quantum"],
        "constant": None},
    "membrane_area": {
        "units": ["mm2", "cm2"], "si_base": "m2",
        "aliases": ["area", "membrane", "active"],
        "constant": None},
    "hydraulic_permeability": {
        "units": ["um/(min·kPa)", "m/(Pa·s)"], "si_base": "m/(pa·s)",
        "aliases": ["permeability", "hydraulic", "conductance"],
        "constant": None},
    "osmotic_pressure_difference": {
        "units": ["kPa", "Pa", "mmHg"], "si_base": "pa",
        "aliases": ["osmotic", "oncotic", "pressure", "difference"],
        "constant": None},
    "reflection_coefficient": {
        "units": ["", "fraction", "ratio", "dimensionless"],
        "si_base": "ratio",
        "aliases": ["reflection", "selectivity", "sigma", "sieving"],
        "constant": None},
    "strain": {
        "units": ["ustrain", "strain", "%", ""], "si_base": "strain",
        "aliases": ["strain", "deformation", "microstrain", "bending"],
        "constant": None},
    "youngs_modulus": {
        "units": ["MPa", "GPa", "kPa"], "si_base": "pa",
        "aliases": ["modulus", "young", "stiffness", "elastic"],
        "constant": None},
    "active_volume": {
        "units": ["mm3", "cm3"], "si_base": "m3",
        "aliases": ["volume", "active", "piezoelectric", "element"],
        "constant": None},
    "frequency": {
        "units": ["Hz", "kHz"], "si_base": "hz",
        "aliases": ["frequency", "vibration", "cardiac", "pulsation",
                    "cycling"],
        "constant": None},
    "electromechanical_coupling": {
        "units": ["", "fraction", "ratio", "dimensionless"],
        "si_base": "ratio",
        "aliases": ["coupling", "electromechanical", "coefficient"],
        "constant": None},
    "electrode_area": {
        "units": ["mm2", "cm2"], "si_base": "m2",
        "aliases": ["area", "electrode", "plate", "capacitive"],
        "constant": None},
    "gap": {
        "units": ["um", "mm"], "si_base": "m",
        "aliases": ["gap", "separation", "cavity", "diaphragm",
                    "spacing"],
        "constant": None},
    "relative_permittivity": {
        "units": ["", "ratio", "dimensionless", "fraction"],
        "si_base": "ratio",
        "aliases": ["permittivity", "dielectric", "relative"],
        "constant": None},
}

# output roles (unit of the computed quantity as displayed/reported)
OUTPUT_ROLES: Dict[str, Dict[str, Any]] = {
    "volumetric_flow": {"units": ["ml/hr"], "si_base": "m3/s"},
    "contact_time": {"units": ["s"], "si_base": "s"},
    "hydrostatic_pressure": {"units": ["Pa", "mmHg"], "si_base": "pa"},
    "hoop_stress": {"units": ["MPa"], "si_base": "pa"},
    "reflection_ratio": {"units": ["", "fraction"], "si_base": "ratio"},
    "delivered_power": {"units": ["uW", "nW", "mW", "W"], "si_base": "w"},
    "osmotic_flux": {"units": ["uL/day", "mL/day"], "si_base": "m3/s"},
    "capacitance": {"units": ["pF"], "si_base": "f"},
}

_EPSILON0 = 8.8541878128e-12     # F/m (SI-defined, exact)
_G = 9.80665                     # m/s^2 (ISO standard gravity)


def _positive(**kwargs) -> List[Dict[str, Any]]:
    """Validity predicate: every named SI value must be finite and > 0."""
    out = []
    for name, v in kwargs.items():
        ok = isinstance(v, (int, float)) and math.isfinite(v) and v > 0
        out.append({
            "id": f"positive:{name}",
            "status": "VERIFIED" if ok else "VIOLATED",
            "detail": f"{name} = {v} must be finite and > 0"})
    return out


def _range_check(name: str, v: float, lo: float, hi: float,
                 why: str) -> Dict[str, Any]:
    ok = isinstance(v, (int, float)) and math.isfinite(v) \
        and lo <= v <= hi
    return {
        "id": f"range:{name}",
        "status": "VERIFIED" if ok else "VIOLATED",
        "detail": f"{name} = {v} must lie in [{lo}, {hi}] ({why})"}


# extra composite units needed by the registry (declared before use)
_UNIT_SI.update({
    "um/(minkpa)": (1.0e-6 / 60.0 / 1.0e3, "m/(pa·s)"),
    "m/(pas)": (1.0, "m/(pa·s)"),
    "m/pas": (1.0, "m/(pa·s)"),
    "pa·s/m": (1.0, "pa·s/m"),
    "kg/m3": (1.0, "kg/m3"),
    "pas": (1.0, "pa·s"),
    "mpas": (1e-3, "pa·s"),
})


# ---------------------------------------------------------------------------
# THE EQUATION REGISTRY (engine-owned; the LLM never writes physics)
# ---------------------------------------------------------------------------
def _hp_flow(si: Dict[str, float]) -> float:
    # R401A A1: delegates to the ONE canonical equation authority
    # (equation_authority.py) — the historical standalone
    # implementation is identical and retired to git history; its
    # numerical equivalence is pinned by tests/test_r401_stream_a.py
    from discovery_fabric.engine.equation_authority import (
        hagen_poiseuille_flow_si)
    return hagen_poiseuille_flow_si(
        diameter_m=si["lumen_diameter"],
        pressure_drop_Pa=si["pressure_drop"],
        viscosity_Pa_s=si["viscosity"],
        length_m=si["flow_path_length"])


def _hp_validity(si: Dict[str, float], out: float
                 ) -> List[Dict[str, Any]]:
    checks = _positive(
        lumen_diameter=si["lumen_diameter"],
        flow_path_length=si["flow_path_length"],
        viscosity=si["viscosity"], pressure_drop=si["pressure_drop"],
        fluid_density=si["fluid_density"])
    D, mu, rho = si["lumen_diameter"], si["viscosity"], \
        si["fluid_density"]
    if D > 0 and mu > 0 and rho > 0 and out > 0:
        v = out / (math.pi * D ** 2 / 4.0)
        re = rho * v * D / mu
        checks.append({
            "id": "regime:laminar_re",
            "status": "VERIFIED" if re < 2300.0 else "VIOLATED",
            "detail": (f"Re = {re:.1f} (laminar requires Re < 2300; "
                       "Hagen-Poiseuille is derived for laminar flow)")})
        ld = si["flow_path_length"] / D
        checks.append({
            "id": "regime:developed_ld",
            "status": "VERIFIED" if ld >= 10.0 else "VIOLATED",
            "detail": (f"L/D = {ld:.1f} (fully developed requires "
                       "L/D >= 10)")})
    return checks


def _rt_time(si: Dict[str, float]) -> float:
    return si["flow_path_length"] * (math.pi * si["lumen_diameter"]
                                      ** 2 / 4.0) / si["volumetric_flow"]


def _rt_validity(si: Dict[str, float], out: float
                 ) -> List[Dict[str, Any]]:
    return _positive(
        flow_path_length=si["flow_path_length"],
        lumen_diameter=si["lumen_diameter"],
        volumetric_flow=si["volumetric_flow"])


def _hs_pressure(si: Dict[str, float]) -> float:
    return si["fluid_density"] * _G * si["height_difference"]


def _hs_validity(si: Dict[str, float], out: float
                 ) -> List[Dict[str, Any]]:
    return _positive(fluid_density=si["fluid_density"],
                     height_difference=si["height_difference"])


def _hoop_stress(si: Dict[str, float]) -> float:
    return si["internal_pressure"] * si["radius"] / \
        si["wall_thickness"]


def _hoop_validity(si: Dict[str, float], out: float
                   ) -> List[Dict[str, Any]]:
    checks = _positive(internal_pressure=si["internal_pressure"],
                       radius=si["radius"],
                       wall_thickness=si["wall_thickness"])
    rt = si["radius"] / si["wall_thickness"] \
        if si["wall_thickness"] > 0 else 0.0
    checks.append({
        "id": "regime:thin_wall_rt",
        "status": "VERIFIED" if rt >= 20.0 else "VIOLATED",
        "detail": (f"r/t = {rt:.1f} (thin-wall closed form requires "
                   "r/t >= 20; thick-wall Lamé correction otherwise)")})
    return checks


def _refl_ratio(si: Dict[str, float]) -> float:
    z1, z2 = si["acoustic_impedance_1"], si["acoustic_impedance_2"]
    return ((z2 - z1) / (z2 + z1)) ** 2


def _refl_validity(si: Dict[str, float], out: float
                   ) -> List[Dict[str, Any]]:
    checks = _positive(acoustic_impedance_1=si["acoustic_impedance_1"],
                       acoustic_impedance_2=si["acoustic_impedance_2"])
    s = si["acoustic_impedance_1"] + si["acoustic_impedance_2"]
    checks.append({
        "id": "regime:nonzero_sum",
        "status": "VERIFIED" if s > 0 else "VIOLATED",
        "detail": "Z1 + Z2 must be > 0"})
    return checks


def _pv_power(si: Dict[str, float]) -> float:
    return (si["cell_efficiency"] * si["cell_area"] *
            si["incident_irradiance"] *
            math.exp(-si["attenuation_coefficient"] *
                     si["tissue_depth"]))


def _pv_validity(si: Dict[str, float], out: float
                 ) -> List[Dict[str, Any]]:
    checks = _positive(cell_area=si["cell_area"],
                       incident_irradiance=si["incident_irradiance"],
                       attenuation_coefficient=si[
                           "attenuation_coefficient"],
                       tissue_depth=si["tissue_depth"])
    checks.append(_range_check("cell_efficiency",
                               si["cell_efficiency"], 1e-4, 1.0,
                               "a photovoltaic conversion efficiency "
                               "is a positive fraction"))
    return checks


def _osm_flux(si: Dict[str, float]) -> float:
    return (si["membrane_area"] * si["hydraulic_permeability"] *
            si["reflection_coefficient"] *
            si["osmotic_pressure_difference"])


def _osm_validity(si: Dict[str, float], out: float
                  ) -> List[Dict[str, Any]]:
    checks = _positive(membrane_area=si["membrane_area"],
                       hydraulic_permeability=si[
                           "hydraulic_permeability"],
                       osmotic_pressure_difference=si[
                           "osmotic_pressure_difference"])
    checks.append(_range_check("reflection_coefficient",
                               si["reflection_coefficient"], 0.0, 1.0,
                               "the Staverman reflection coefficient "
                               "lies in [0, 1]"))
    return checks


def _piezo_power(si: Dict[str, float]) -> float:
    return (0.5 * si["strain"] ** 2 * si["youngs_modulus"] *
            si["active_volume"] * si["frequency"] *
            si["electromechanical_coupling"] ** 2)


def _piezo_validity(si: Dict[str, float], out: float
                    ) -> List[Dict[str, Any]]:
    checks = _positive(youngs_modulus=si["youngs_modulus"],
                       active_volume=si["active_volume"],
                       frequency=si["frequency"])
    checks.append(_range_check("strain", si["strain"], 1e-9, 1e-2,
                               "linear piezoelectric regime "
                               "(strain <= 1%)"))
    checks.append(_range_check("electromechanical_coupling",
                               si["electromechanical_coupling"],
                               1e-4, 1.0,
                               "a coupling coefficient is a positive "
                               "fraction"))
    return checks


def _cap_capacitance(si: Dict[str, float]) -> float:
    return _EPSILON0 * si["relative_permittivity"] * \
        si["electrode_area"] / si["gap"]


def _cap_validity(si: Dict[str, float], out: float
                  ) -> List[Dict[str, Any]]:
    checks = _positive(electrode_area=si["electrode_area"],
                       relative_permittivity=si["relative_permittivity"])
    checks.append(_range_check("gap", si["gap"], 1e-7, 1.0,
                               "a measurable capacitive gap "
                               "(0.1 um .. 1 m)"))
    return checks


EQUATIONS: Dict[str, Dict[str, Any]] = {
    "eq:hagen_poiseuille_flow_v1": {
        # R401A A1: the law's identity (form, symbols, units,
        # assumptions, provenance) is owned by equation_authority.py;
        # this layer-specific entry keeps ONLY the evaluation machinery
        # (compute/validity/monotonicity/output_role) and carries the
        # canonical reference.
        "canonical_law": "law:hagen_poiseuille",
        "authority_version": "equation_authority/1.0.0",
        "equation_id": "eq:hagen_poiseuille_flow_v1",
        "name": "Hagen–Poiseuille laminar volumetric flow",
        "domain": "FLUIDICS",
        "form": "Q = pi * D^4 * dP / (128 * mu * L)",
        "relation_epistemic_class": "ANALYTICAL_LAW",
        "provenance": (
            "closed-form solution of the Navier–Stokes equations for "
            "steady incompressible laminar flow of a Newtonian fluid "
            "in a long circular tube; a conservation-derived analytical "
            "law, not a fit; the BINDING to a candidate is a declared "
            "model relation (rank-4 outputs once computed)"),
        "inputs": ["lumen_diameter", "flow_path_length", "viscosity",
                   "pressure_drop", "fluid_density"],
        "validity_only_inputs": ["fluid_density"],
        "output_role": "volumetric_flow",
        "monotonicity": {"lumen_diameter": 1, "flow_path_length": -1,
                         "viscosity": -1, "pressure_drop": 1},
        "assumptions": [
            "steady, incompressible, Newtonian fluid",
            "fully developed laminar flow (Re < 2300, L/D >= 10)",
            "rigid circular cross-section of constant diameter",
        ],
        "compute_si": _hp_flow,
        "validity_si": _hp_validity,
    },
    "eq:residence_time_v1": {
        "equation_id": "eq:residence_time_v1",
        "name": "mean transit (residence) time",
        "domain": "FLUIDICS",
        "form": "tau = V_lumen / Q = L * pi * D^2 / (4 * Q)",
        "relation_epistemic_class": "ANALYTICAL_LAW",
        "provenance": (
            "mean transit time of a tracer through a control volume in "
            "steady incompressible flow is exactly V/Q; a "
            "conservation-derived identity applied to a prismatic "
            "circular lumen"),
        "inputs": ["flow_path_length", "lumen_diameter",
                   "volumetric_flow"],
        "validity_only_inputs": [],
        "output_role": "contact_time",
        "monotonicity": {"flow_path_length": 1, "lumen_diameter": 1,
                         "volumetric_flow": -1},
        "assumptions": [
            "steady incompressible flow; the MEAN transit time (not the "
            "laminar velocity-profile distribution)",
        ],
        "compute_si": _rt_time,
        "validity_si": _rt_validity,
    },
    "eq:hydrostatic_head_v1": {
        "equation_id": "eq:hydrostatic_head_v1",
        "name": "hydrostatic pressure head",
        "domain": "FLUIDICS",
        "form": "dP = rho * g * h   (g = 9.80665 m/s^2, SI standard)",
        "relation_epistemic_class": "ANALYTICAL_LAW",
        "provenance": (
            "hydrostatic equilibrium of a static fluid column; "
            "conservation-derived"),
        "inputs": ["fluid_density", "height_difference"],
        "validity_only_inputs": [],
        "output_role": "hydrostatic_pressure",
        "monotonicity": {"fluid_density": 1, "height_difference": 1},
        "assumptions": ["static fluid column; implant-scale height "
                        "differences (g constant)"],
        "compute_si": _hs_pressure,
        "validity_si": _hs_validity,
    },
    "eq:hoop_stress_v1": {
        "equation_id": "eq:hoop_stress_v1",
        "name": "thin-wall hoop stress",
        "domain": "STRUCTURES",
        "form": "sigma = dP * r / t",
        "relation_epistemic_class": "ANALYTICAL_LAW",
        "provenance": (
            "thin-wall pressure-vessel force balance (boiler formula); "
            "conservation-derived; Lamé thick-wall correction neglected "
            "by declared assumption r/t >= 20"),
        "inputs": ["internal_pressure", "radius", "wall_thickness"],
        "validity_inputs": [],
        "validity_only_inputs": [],
        "output_role": "hoop_stress",
        "monotonicity": {"internal_pressure": 1, "radius": 1,
                         "wall_thickness": -1},
        "assumptions": ["thin wall (r/t >= 20)", "axisymmetric internal "
                        "pressure", "free-ended cylinder"],
        "compute_si": _hoop_stress,
        "validity_si": _hoop_validity,
    },
    "eq:acoustic_reflection_v1": {
        "equation_id": "eq:acoustic_reflection_v1",
        "name": "normal-incidence acoustic intensity reflection",
        "domain": "ACOUSTICS",
        "form": "R = ((Z2 - Z1) / (Z2 + Z1))^2",
        "relation_epistemic_class": "ANALYTICAL_LAW",
        "provenance": (
            "plane-wave acoustic boundary condition (pressure/velocity "
            "continuity); conservation-derived"),
        "inputs": ["acoustic_impedance_1", "acoustic_impedance_2"],
        "validity_only_inputs": [],
        "output_role": "reflection_ratio",
        "monotonicity": {"acoustic_impedance_1": None,
                         "acoustic_impedance_2": None},
        "monotone_note": (
            "NON-MONOTONE: the reflection coefficient is non-monotone "
            "in each impedance individually (depends on which medium "
            "has the higher impedance); solve-for and magnitude-ranked "
            "limiting-variable selection are DISABLED for this "
            "equation — sensitivity is still computed numerically at "
            "the operating point"),
        "assumptions": ["normal incidence", "plane waves", "lossless "
                        "media"],
        "compute_si": _refl_ratio,
        "validity_si": _refl_validity,
    },
    "eq:pv_delivered_power_v1": {
        "equation_id": "eq:pv_delivered_power_v1",
        "name": "photovoltaic delivered power at depth",
        "domain": "PHOTONICS",
        "form": "P = eta * A * G0 * exp(-alpha * d)",
        "relation_epistemic_class": "ANALYTICAL_ESTIMATE",
        "provenance": (
            "Beer–Lambert attenuation of irradiance through tissue "
            "(conservation-derived transport form) times a DECLARED "
            "cell efficiency; the product is an engineering estimate, "
            "not a law — the estimate class travels with every output"),
        "inputs": ["cell_area", "incident_irradiance",
                   "attenuation_coefficient", "tissue_depth",
                   "cell_efficiency"],
        "validity_only_inputs": [],
        "output_role": "delivered_power",
        "monotonicity": {"cell_area": 1, "incident_irradiance": 1,
                         "attenuation_coefficient": -1,
                         "tissue_depth": -1, "cell_efficiency": 1},
        "assumptions": [
            "normally incident irradiance", "exponential (Beer–Lambert) "
            "attenuation with a constant effective alpha",
            "cell efficiency independent of irradiance and wavelength "
            "(declared estimate)",
        ],
        "compute_si": _pv_power,
        "validity_si": _pv_validity,
    },
    "eq:osmotic_flux_v1": {
        "equation_id": "eq:osmotic_flux_v1",
        "name": "osmotic volumetric flux (Kedem–Katchalsky form)",
        "domain": "MEMBRANES",
        "form": "J_v = A * Lp * sigma * dPI",
        "relation_epistemic_class": "ANALYTICAL_ESTIMATE",
        "provenance": (
            "linear nonequilibrium transport relation (Kedem–"
            "Katchalsky) with declared constant coefficients; an "
            "engineering estimate, not a conservation law"),
        "inputs": ["membrane_area", "hydraulic_permeability",
                   "reflection_coefficient",
                   "osmotic_pressure_difference"],
        "validity_only_inputs": [],
        "output_role": "osmotic_flux",
        "monotonicity": {"membrane_area": 1,
                         "hydraulic_permeability": 1,
                         "reflection_coefficient": 1,
                         "osmotic_pressure_difference": 1},
        "assumptions": ["linear transport regime",
                        "constant membrane properties"],
        "compute_si": _osm_flux,
        "validity_si": _osm_validity,
    },
    "eq:piezo_harvest_power_v1": {
        "equation_id": "eq:piezo_harvest_power_v1",
        "name": "piezoelectric strain-energy harvest bound",
        "domain": "ENERGY_HARVESTING",
        "form": "P = 0.5 * eps^2 * Y * V * f * k^2",
        "relation_epistemic_class": "ANALYTICAL_ESTIMATE",
        "provenance": (
            "elastic strain energy per cycle times frequency times the "
            "square of the electromechanical coupling coefficient — a "
            "declared upper-bound-style engineering estimate for "
            "resonant harvesting, not a law"),
        "inputs": ["strain", "youngs_modulus", "active_volume",
                   "frequency", "electromechanical_coupling"],
        "validity_only_inputs": [],
        "output_role": "delivered_power",
        "monotonicity": {"strain": 1, "youngs_modulus": 1,
                         "active_volume": 1, "frequency": 1,
                         "electromechanical_coupling": 1},
        "assumptions": [
            "fully rectified strain energy per cycle (upper-bound "
            "character)", "linear piezoelectric regime (strain <= 1%)",
            "operation at the strain frequency",
        ],
        "compute_si": _piezo_power,
        "validity_si": _piezo_validity,
    },
    "eq:parallel_plate_capacitance_v1": {
        "equation_id": "eq:parallel_plate_capacitance_v1",
        "name": "parallel-plate capacitance",
        "domain": "SENSING",
        "form": "C = eps0 * eps_r * A / d   (eps0 = 8.8541878128e-12 F/m)",
        "relation_epistemic_class": "ANALYTICAL_LAW",
        "provenance": (
            "electrostatics of ideal parallel plates (Gauss's law); "
            "conservation-derived; fringe fields neglected by declared "
            "assumption"),
        "inputs": ["electrode_area", "gap", "relative_permittivity"],
        "validity_only_inputs": [],
        "output_role": "capacitance",
        "monotonicity": {"electrode_area": 1,
                         "relative_permittivity": 1, "gap": -1},
        "assumptions": ["ideal parallel plates", "fringe fields "
                        "neglected", "linear dielectric"],
        "compute_si": _cap_capacitance,
        "validity_si": _cap_validity,
    },
}

# dimensionless families unify on the ratio base (strain IS a ratio;
# percent is a scaled ratio) — declared so cross-unit conversion of
# dimensionless quantities is exact and never guessed
_UNIT_SI.update({
    "strain": (1.0, "ratio"), "ustrain": (1e-6, "ratio"),
    "%": (1e-2, "ratio"), "percent": (1e-2, "ratio"),
    "mm-1": (1e3, "1/m"), "cm-1": (100.0, "1/m"),
})

OUTPUT_ROLES["volumetric_flow"]["aliases"] = [
    "flow", "rate", "drainage", "perfusion", "efflux", "volumetric"]
OUTPUT_ROLES["contact_time"]["aliases"] = [
    "contact", "residence", "transit", "dwell", "time"]
OUTPUT_ROLES["hydrostatic_pressure"]["aliases"] = [
    "pressure", "head", "hydrostatic"]
OUTPUT_ROLES["hoop_stress"]["aliases"] = [
    "stress", "hoop", "tangential"]
OUTPUT_ROLES["reflection_ratio"]["aliases"] = [
    "reflection", "contrast", "ratio", "coefficient"]
OUTPUT_ROLES["delivered_power"]["aliases"] = [
    "power", "delivered", "harvest", "output", "generated"]
OUTPUT_ROLES["osmotic_flux"]["aliases"] = [
    "flux", "osmotic", "volumetric"]
OUTPUT_ROLES["capacitance"]["aliases"] = [
    "capacitance", "capacitive", "sense", "sensing"]


# ---------------------------------------------------------------------------
# GEOMETRY RESOLVERS (measured quantities of the candidate's OWN built
# solid — CEO R383 focus 4; used in PREFERENCE to declared values, with
# any discrepancy recorded, never silently resolved)
# ---------------------------------------------------------------------------
def _primary_object(measurements: Dict[str, Any]) -> \
        Optional[Tuple[str, Dict[str, Any]]]:
    """The primary object = largest measured volume (deterministic)."""
    best: Optional[Tuple[float, str, Dict[str, Any]]] = None
    for oid, m in (measurements.get("objects") or {}).items():
        v = (m or {}).get("volume_mm3")
        if isinstance(v, (int, float)) and not isinstance(v, bool) \
                and (best is None or float(v) > best[0]):
            best = (float(v), str(oid), m or {})
    return (best[1], best[2]) if best else None


def _measured_field_value(measurements: Dict[str, Any],
                          field: str) -> Optional[Dict[str, Any]]:
    """Resolve a declared measured field (template
    measured_dimension_bindings: field -> param_id) to its measured
    value in mm on the primary object."""
    prim = _primary_object(measurements)
    if prim is None:
        return None
    oid, m = prim
    bbox = m.get("bbox") or {}
    val = None
    if field == "bbox_z":
        val = bbox.get("zlen")
    elif field == "bbox_x":
        val = bbox.get("xlen")
    elif field == "bbox_y":
        val = bbox.get("ylen")
    elif field == "bbox_xy_max":
        xs = [bbox.get("xlen") or 0.0, bbox.get("ylen") or 0.0]
        val = max(xs) if max(xs) > 0 else None
    else:
        v = m.get(field)
        val = v if isinstance(v, (int, float)) and \
            not isinstance(v, bool) else None
    if val is None:
        return None
    return {"value_mm": float(val), "object_id": oid, "field": field}


def _lumen_diameter_from_geometry(measurements: Dict[str, Any]
                                  ) -> Optional[Dict[str, Any]]:
    """Lumen diameter measured on the built solid from the inner
    cylinder faces: inner radii = every cylinder radius strictly below
    the outer-wall radius; the resolver requires exactly ONE distinct
    inner radius (multiple distinct lumen sizes are AMBIGUOUS — the
    resolver refuses and the state value is used instead; Art. II)."""
    prim = _primary_object(measurements)
    if prim is None:
        return None
    oid, m = prim
    radii = [r for r in (m.get("cylinder_face_radii") or [])
             if isinstance(r, (int, float))]
    if len(radii) < 2:
        return None
    outer = max(radii)
    inner = [r for r in radii if r < outer - 1e-9]
    if not inner:
        return None
    distinct = sorted({round(float(r), 6) for r in inner})
    if len(distinct) > 1:
        return None
    return {"value_mm": 2.0 * distinct[0], "object_id": oid,
            "field": "cylinder_face_radii(inner)",
            "note": (f"{len(inner)} inner cylinder face(s) at radius "
                     f"{distinct[0]} mm; outer wall radius {outer} mm")}


def _geometry_value_for_param(role: str, param_id: str,
                              model: Dict[str, Any],
                              measurements: Dict[str, Any],
                              param_unit: Any
                              ) -> Optional[Dict[str, Any]]:
    """Resolve a bound input parameter to a MEASURED value on the
    built solid. Resolver A: the model's declared
    measured_dimension_bindings (field -> param_id). Resolver B: the
    lumen-diameter cylinder-face scan. Returns the measured value in
    the PARAM's unit (converted from mm; incompatible units refuse)."""
    resolvers: List[Tuple[str, Any]] = []
    mdb = (model.get("measured_dimension_bindings") or {})
    field = next((f for f, pid in mdb.items() if pid == param_id), None)
    if field is not None:
        resolvers.append((
            f"template_binding:{field}",
            lambda: _measured_field_value(measurements, field)))
    if role == "lumen_diameter":
        resolvers.append((
            "cylinder_face_scan",
            lambda: _lumen_diameter_from_geometry(measurements)))
    if not param_unit or not isinstance(param_unit, str):
        # a parameter without a declared unit cannot be converted
        # safely — the resolver refuses (never guesses a scale)
        return None
    for name, fn in resolvers:
        rec = fn()
        if rec is None:
            continue
        v = convert_value(rec["value_mm"], "mm", param_unit)
        if v is None:
            continue
        return {"value": v, "unit": param_unit, "resolver": name,
                "measured_mm": rec["value_mm"],
                "object_id": rec["object_id"], "field": rec["field"],
                "note": rec.get("note")}
    return None


# ---------------------------------------------------------------------------
# PARAMETER <-> ROLE MATCHING (deterministic; ambiguity refuses to bind)
# ---------------------------------------------------------------------------
def _role_tokens(role: str, units_aliases: List[str]) -> set:
    return _tokens(role) | _tokens(units_aliases)


def _match_param_for_role(role: str, aliases: List[str],
                          role_units: List[str],
                          params: List[Dict[str, Any]]
                          ) -> Tuple[Optional[Dict[str, Any]], str]:
    """Unit-compatible + keyword-scored deterministic match. Ambiguity
    (a tie at the best score) REFUSES to bind (Art. II/IV)."""
    tokens = _role_tokens(role, aliases)
    candidates: List[Tuple[int, Dict[str, Any]]] = []
    for p in params:
        unit = p.get("unit")
        if not unit or not isinstance(unit, str):
            continue        # a unitless declaration cannot bind safely
        if role_units and not any(units_compatible(unit, ru)
                                   for ru in role_units):
            continue
        p_tokens = (_tokens(p.get("param_id")) |
                    _tokens(p.get("name")) | _tokens(p.get("role")))
        score = len(tokens & p_tokens)
        if score >= 1:
            candidates.append((score, p))
    if not candidates:
        return None, "no unit-compatible keyword-matching parameter"
    best = max(s for s, _ in candidates)
    tied = [p for s, p in candidates if s == best]
    if len(tied) > 1:
        return None, ("ambiguous match: " +
                      ", ".join(sorted(str(p.get("param_id") or "?")
                                       for p in tied)))
    return tied[0], ""


# ---------------------------------------------------------------------------
# THE QUANTITATIVE EVALUATION (deterministic; never writes back)
# ---------------------------------------------------------------------------
def _resolve_input(role: str, params_list: List[Dict[str, Any]],
                   model: Optional[Dict[str, Any]],
                   measurements: Optional[Dict[str, Any]]
                   ) -> Tuple[Optional[Dict[str, Any]], str]:
    """Resolve one equation input role to a numeric value with its
    source and class. Precedence (declared, ADR_R383):
    GEOMETRY_MEASURED > EXTRACTED > MODELLED > ENGINEERING_REFERENCE
    constant. Unresolved returns (None, reason)."""
    rdef = ROLE_DEFS[role]
    p, why = _match_param_for_role(role, rdef["aliases"],
                                   rdef["units"], params_list)
    rec: Optional[Dict[str, Any]] = None
    if p is not None:
        p_unit = p.get("unit") or \
            ((model or {}).get("parameter_map") or {}).get(
                p.get("param_id"), {}).get("unit")
        if measurements is not None and model is not None:
            geo = _geometry_value_for_param(
                role, str(p.get("param_id")), model, measurements,
                p_unit)
            if geo is not None:
                u_si = unit_si(p_unit) if p_unit else None
                if u_si is not None:
                    note = geo.get("note")
                    declared = p.get("value")
                    if isinstance(declared, (int, float)) and \
                            not isinstance(declared, bool):
                        delta = geo["value"] - float(declared)
                        if abs(delta) > 1e-6 * max(1.0, abs(float(declared))):
                            note = (f"declared {declared} vs measured "
                                    f"{round(geo['value'], 6)} "
                                    f"{p_unit} — the MEASURED value on "
                                    f"the built solid is used (the "
                                    f"declared value stays in the "
                                    f"state, unwritten); discrepancy "
                                    f"recorded, never silently resolved")
                    rec = {
                        "role": role,
                        "param_id": p.get("param_id"),
                        "source": "GEOMETRY_MEASURED_ON_BUILT_SOLID",
                        "value": round(float(geo["value"]), 9),
                        "unit": p_unit,
                        "si_value": float(geo["value"]) * u_si[0],
                        "value_class": "COMPUTATIONAL_RESULT",
                        "resolver": geo["resolver"],
                        "measured_on": {
                            "object_id": geo["object_id"],
                            "measured_field": geo["field"],
                            "evidence_class": "COMPUTATIONAL_RESULT",
                            "note": ("measured on the built solid by "
                                     "the CAD kernel; the parametric "
                                     "model's measurements section "
                                     "carries the computation log "
                                     "(R380); the state's own value "
                                     "is never written back "
                                     "(Art. XXVIII)")},
                        "note": note,
                    }
        if rec is None:
            v = p.get("value")
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                u_si = unit_si(p.get("unit"))
                if u_si is not None:
                    rec = {
                        "role": role,
                        "param_id": p.get("param_id"),
                        "source": "STATE_DECLARED",
                        "value": float(v),
                        "unit": p.get("unit"),
                        "si_value": float(v) * u_si[0],
                        "value_class": str(p.get("value_class")
                                           or "UNKNOWN"),
                    }
    if rec is None:
        ckey = rdef.get("constant")
        if ckey:
            c = ENGINEERING_CONSTANTS[ckey]
            cu = next((u for u in rdef["units"]
                       if units_compatible(c.get("unit"), u)), None)
            if cu is not None:
                v = convert_value(float(c["value"]), c["unit"], cu)
                if v is not None:
                    rec = {
                        "role": role, "param_id": None,
                        "source": "ENGINEERING_REFERENCE",
                        "value": round(float(v), 9), "unit": cu,
                        "si_value": float(v) * unit_si(cu)[0],
                        "value_class": "ENGINEERING_REFERENCE",
                        "constant_id": c["constant_id"],
                        "constant_name": c["name"],
                        "constant_note": (
                            "the candidate's state does not declare "
                            "this quantity; the declared reference "
                            "value is used for the MODEL computation "
                            "and its use is recorded here — a "
                            "reference constant, never a measurement"),
                        "uncertainty": c.get("uncertainty"),
                    }
    if rec is None:
        reason = why or "unresolved"
        if p is None and not rdef.get("constant"):
            reason = why
        return None, reason
    return rec, ""


def _binding_constraint(target_pid: str, direction: str,
                        constraints: List[Dict[str, Any]]
                        ) -> Optional[Dict[str, Any]]:
    """The direction-consistent constraint on the objective target —
    the requirement the objective is measured against. MAXIMIZE pairs
    with '>=', MINIMIZE with '<='; the TIGHTEST wins. MAINTAIN_WITHIN
    has no margin semantics here (recorded honestly)."""
    if direction not in ("MAXIMIZE", "MINIMIZE"):
        return None
    want_bound = ">=" if direction == "MAXIMIZE" else "<="
    best: Optional[Dict[str, Any]] = None
    for c in constraints or []:
        if str(c.get("target")) != str(target_pid):
            continue
        if str(c.get("bound")) != want_bound:
            continue
        lim = c.get("limit")
        if not isinstance(lim, (int, float)) or isinstance(lim, bool):
            continue
        if best is None:
            best = c
        else:
            bl = float(best.get("limit"))
            if (want_bound == ">=" and float(lim) > bl) or \
                    (want_bound == "<=" and float(lim) < bl):
                best = c
    return best


def evaluate_quantitatively(state: Dict[str, Any],
                            model: Optional[Dict[str, Any]] = None
                            ) -> Dict[str, Any]:
    """The deterministic analytical evaluation. INPUT: the structured
    technical state + (optionally) the candidate's OWN validated
    parametric model. OUTPUT: bindings, computations with validity and
    logs, the objective value + margin, numeric sensitivities, the
    magnitude-ranked limiting variable with a solve-for record.

    Observational: NOTHING is written back to the state or the model
    (Art. IX). Fail-closed: a VIOLATED/UNDECIDABLE validity predicate
    blocks the number (Art. IV)."""
    params_list = list((state or {}).get("parameters") or [])
    params = {str(p.get("param_id")): p for p in params_list}
    constraints = list((state or {}).get("constraints") or [])
    objectives = list((state or {}).get("objectives") or [])
    dependencies = list((state or {}).get("dependencies") or [])
    effect_side = {str(d.get("effect")) for d in dependencies}
    # (a declared EFFECT is an outcome — moved by its causes, never a
    # mutation target; the causes are the design variables)

    gv = ((model or {}).get("geometry_validation") or {})
    geometry_ok = bool(gv.get("valid"))
    measurements = (model or {}).get("measurements") \
        if (model is not None and geometry_ok) else None
    if model is not None and not geometry_ok and \
            (model.get("measurements") is not None):
        measurements = None      # invalid geometry is NOT evidence

    objective = objectives[0] if objectives else None
    obj_target = str((objective or {}).get("target") or "")
    obj_dir = str((objective or {}).get("direction") or "")

    bindings: List[Dict[str, Any]] = []
    computations: List[Dict[str, Any]] = []
    steps: List[str] = []

    for eq_id in sorted(EQUATIONS.keys()):
        eq = EQUATIONS[eq_id]
        binding: Dict[str, Any] = {
            "binding_id": f"eqb:{eq_id.split(':')[1]}",
            "equation_id": eq_id,
            "equation_name": eq.get("name"),
            "domain": eq.get("domain"),
            "form": eq.get("form"),
            "relation_epistemic_class": eq.get(
                "relation_epistemic_class"),
            "inputs": [], "status": "INACTIVE", "problems": [],
            "sign_checks": [], "output_binding": None,
        }
        si: Dict[str, float] = {}
        all_resolved = True
        for role in list(eq.get("inputs") or []) + \
                list(eq.get("validity_only_inputs") or []):
            rec, reason = _resolve_input(role, params_list, model,
                                         measurements)
            if rec is None:
                all_resolved = False
                binding["problems"].append(
                    f"input '{role}' unresolved: {reason}")
                continue
            si[role] = float(rec["si_value"])
            binding["inputs"].append(rec)

        # output param binding
        out_role = str(eq.get("output_role"))
        odef = OUTPUT_ROLES.get(out_role) or {}
        out_param, out_why = _match_param_for_role(
            out_role, odef.get("aliases") or [],
            odef.get("units") or [], params_list)
        binding["output_binding"] = {
            "role": out_role,
            "param_id": (out_param or {}).get("param_id"),
            "unit": (out_param or {}).get("unit"),
            "match": "BOUND" if out_param is not None else
            f"UNBOUND ({out_why})",
        }

        # sign agreement: declared direct dependencies vs the
        # equation's monotonicity (a contradiction rejects the binding)
        mono = eq.get("monotonicity") or {}
        sign_disagreements: List[str] = []
        if out_param is not None:
            out_pid = str(out_param.get("param_id"))
            for d in dependencies:
                cause, effect = str(d.get("cause")), str(d.get("effect"))
                if effect != out_pid:
                    continue
                for rec in binding["inputs"]:
                    if rec.get("param_id") is None or \
                            str(rec["param_id"]) != cause:
                        continue
                    m = mono.get(str(rec["role"]))
                    if m is None:
                        binding["sign_checks"].append({
                            "cause": cause, "effect": effect,
                            "declared": d.get("direction"),
                            "equation_sign": "NON_MONOTONE",
                            "verdict": "UNCHECKED",
                            "note": (eq.get("monotone_note") or
                                     "non-monotone role")})
                        continue
                    declared_sign = 1 if str(d.get("direction")) \
                        == "INCREASES" else -1
                    agree = (declared_sign == m)
                    binding["sign_checks"].append({
                        "cause": cause, "effect": effect,
                        "declared": d.get("direction"),
                        "equation_sign":
                            "INCREASES" if m > 0 else "DECREASES",
                        "verdict": "AGREE" if agree else
                        "STATE_PHYSICS_DISAGREEMENT"})
                    if not agree:
                        sign_disagreements.append(
                            f"state declares {cause} {d.get('direction')} "
                            f"{effect} but {eq_id} says the output "
                            f"{'increases' if m > 0 else 'decreases'} "
                            f"when {rec['role']} increases — the state's "
                            f"declared physics CONTRADICTS the "
                            f"analytical law; the binding is rejected "
                            f"(never resolved by preference, Art. II)")

        if not all_resolved:
            binding["status"] = "INACTIVE_INPUT_UNRESOLVED"
        elif sign_disagreements:
            binding["status"] = "REJECTED_STATE_PHYSICS_DISAGREEMENT"
            binding["problems"].extend(sign_disagreements)
        elif not out_param:
            binding["status"] = "INACTIVE_OUTPUT_UNBOUND"
        else:
            binding["status"] = "ACTIVE"
        bindings.append(binding)

        if binding["status"] != "ACTIVE":
            continue

        # ---- compute + validity (fail-closed) ------------------------
        try:
            out_si = float(eq["compute_si"](si))
        except (KeyError, TypeError, ValueError, ZeroDivisionError,
                OverflowError) as exc:
            binding["status"] = "INACTIVE_COMPUTE_ERROR"
            binding["problems"].append(
                f"compute failed: {type(exc).__name__}: {exc}")
            bindings[-1] = binding
            continue
        validity = eq["validity_si"](si, out_si)
        statuses = {c.get("status") for c in validity}
        comp: Dict[str, Any] = {
            "equation_id": eq_id,
            "equation_name": eq.get("name"),
            "relation_epistemic_class": eq.get(
                "relation_epistemic_class"),
            "assumptions": eq.get("assumptions"),
            "output_role": out_role,
            "output_param_id": out_param.get("param_id"),
            "output_unit": out_param.get("unit"),
            "evidence_class": "COMPUTATIONAL_RESULT",
            "validity": validity,
        }
        if statuses and statuses <= {"VERIFIED"}:
            f_out = unit_si(out_param.get("unit"))
            value_out = out_si / f_out[0] if f_out else None
            comp["status"] = "COMPUTED"
            comp["value"] = round(value_out, 9) \
                if value_out is not None else None
            comp["si_value"] = out_si
            comp["inputs"] = [
                {k: rec.get(k) for k in
                 ("role", "param_id", "source", "value", "unit",
                  "value_class", "resolver", "constant_id",
                  "constant_name", "note", "uncertainty")}
                for rec in binding["inputs"]
                if rec.get("role") in
                (eq.get("inputs") or [])]
            steps.append(
                f"{eq_id}: computed {out_param.get('param_id')} = "
                f"{comp['value']} {out_param.get('unit')} from "
                f"{len(comp['inputs'])} resolved input(s); validity "
                f"VERIFIED on {len(validity)} predicate(s)")
        else:
            comp["status"] = "BLOCKED_VALIDITY"
            comp["value"] = None
            comp["inputs"] = [
                {k: rec.get(k) for k in ("role", "param_id", "source",
                                         "value", "unit", "value_class")}
                for rec in binding["inputs"]]
            steps.append(
                f"{eq_id}: computation BLOCKED — validity not fully "
                f"VERIFIED ({sorted(statuses)})")
        computations.append(comp)

    # ---- objective value + margin --------------------------------------
    objective_record: Dict[str, Any] = {
        "target": obj_target or None, "direction": obj_dir or None,
        "computed": False, "value": None, "unit": None,
        "equation_id": None, "margin": None,
        "margin_status": "UNCOMPUTED", "binding_constraint": None,
        "statement": ("no active computation binds the objective "
                      "target" if obj_target else "no objective "
                      "declared"),
    }
    obj_comp = next((c for c in computations
                     if c.get("status") == "COMPUTED" and
                     c.get("output_param_id") == obj_target), None)
    if obj_comp is not None and obj_dir in ("MAXIMIZE", "MINIMIZE"):
        objective_record.update({
            "computed": True, "value": obj_comp.get("value"),
            "unit": obj_comp.get("output_unit"),
            "equation_id": obj_comp.get("equation_id"),
        })
        bc = _binding_constraint(obj_target, obj_dir, constraints)
        if bc is not None:
            lim = float(bc.get("limit"))
            v = float(obj_comp.get("value"))
            margin = ((v - lim) / abs(lim)) if bc.get("bound") == ">=" \
                else ((lim - v) / abs(lim))
            objective_record["margin"] = round(margin, 6)
            objective_record["margin_status"] = \
                "MET" if margin >= 0 else "UNMET"
            objective_record["binding_constraint"] = {
                "constraint_id": bc.get("constraint_id"),
                "target": bc.get("target"), "bound": bc.get("bound"),
                "limit": bc.get("limit"), "unit": bc.get("unit"),
                "limit_class": bc.get("limit_class"),
                "justification": bc.get("justification"),
            }
            objective_record["statement"] = (
                f"objective {obj_target} = "
                f"{obj_comp.get('value'):.4g} "
                f"{obj_comp.get('output_unit')} against requirement "
                f"{bc.get('bound')} {lim} ({bc.get('unit') or ''} "
                f"{bc.get('limit_class')}) — margin "
                f"{margin * 100:+.1f}% "
                f"({objective_record['margin_status']}); computed by "
                f"{obj_comp.get('equation_name')} "
                f"[{obj_comp.get('equation_id')}] "
                f"(COMPUTATIONAL_RESULT, rank 4, computation-logged)")
            steps.append(
                f"objective {obj_target} margin "
                f"{objective_record['margin']} "
                f"({objective_record['margin_status']})")
        else:
            objective_record["margin_status"] = "UNBOUNDED"
            objective_record["statement"] = (
                f"objective {obj_target} = "
                f"{obj_comp.get('value'):.4g} "
                f"{obj_comp.get('output_unit')} (computed) but NO "
                f"direction-consistent constraint exists on the "
                f"target — no requirement is stated, so no margin and "
                f"no quantitative mutation target exists (the "
                f"requirement is the CONSTRAINT's, never invented "
                f"here; Art. XXVII)")
            steps.append(
                f"objective {obj_target} computed but UNBOUNDED")

    # ---- numeric sensitivity (finite differences, deterministic) ------
    sensitivity: Dict[str, Dict[str, Any]] = {}
    step_frac = QUANTITATIVE_THRESHOLDS[
        "SENSITIVITY_STEP_FRACTION"]["value"]
    for comp in computations:
        if comp.get("status") != "COMPUTED":
            continue
        eq = EQUATIONS[comp["equation_id"]]
        base_inputs = next(
            (b for b in bindings
             if b["equation_id"] == comp["equation_id"]), None)
        if base_inputs is None:
            continue
        si = {rec["role"]: float(rec["si_value"])
              for rec in base_inputs["inputs"]}
        for rec in base_inputs["inputs"]:
            pid = rec.get("param_id")
            if pid is None or pid not in params:
                continue        # constants have no design leverage
            v_si = float(rec["si_value"])
            h = step_frac * abs(v_si) if v_si != 0 else step_frac
            def _f(x: float, _si=dict(si), _role=rec["role"],
                   _eq=eq) -> float:
                _si2 = dict(_si)
                _si2[_role] = x
                return float(_eq["compute_si"](_si2))
            try:
                d_si = (_f(v_si + h) - _f(v_si - h)) / (2.0 * h)
            except (KeyError, TypeError, ValueError, ZeroDivisionError,
                    OverflowError):
                continue
            if not math.isfinite(d_si):
                continue
            out_si = float(comp["si_value"])
            elasticity = abs(d_si * v_si / out_si) \
                if out_si not in (0.0,) and math.isfinite(out_si) else None
            f_in = unit_si(rec.get("unit")) or (1.0, "ratio")
            f_out = unit_si(comp.get("output_unit")) or (1.0, "ratio")
            deriv_display = d_si * f_in[0] / f_out[0]
            sensitivity[str(pid)] = {
                "param_id": pid,
                "equation_id": comp["equation_id"],
                "elasticity": round(elasticity, 6)
                if elasticity is not None else None,
                "derivative": round(deriv_display, 9),
                "derivative_units":
                    f"{comp.get('output_unit')} per {rec.get('unit')}",
                "derivative_sign": "INCREASES" if d_si > 0 else
                "DECREASES",
                "method": (f"central finite difference +/-"
                           f"{step_frac * 100:.0f}% of the resolved "
                           f"value (declared convention)"),
                "note": ("local linearization at the operating point "
                         "— a model derivative, not a measurement"),
            }

    # ---- limiting variable + solve-for ---------------------------------
    limiting_variable: Optional[Dict[str, Any]] = None
    requirement_satisfied = None
    if objective_record.get("computed") and \
            objective_record.get("margin") is not None:
        requirement_satisfied = objective_record["margin"] >= 0
    if objective_record.get("computed") and \
            objective_record.get("margin_status") == "UNMET":
        eq_id = objective_record["equation_id"]
        eq = EQUATIONS[eq_id]
        obj_comp = next(c for c in computations
                        if c.get("equation_id") == eq_id and
                        c.get("status") == "COMPUTED")
        base_inputs = next(
            (b for b in bindings if b["equation_id"] == eq_id), None)
        mono = eq.get("monotonicity") or {}
        candidates: List[Tuple[float, str, Dict[str, Any],
                               Dict[str, Any]]] = []
        for rec in (base_inputs or {}).get("inputs") or []:
            pid = str(rec.get("param_id") or "")
            if pid in ("", "None") or pid not in params:
                continue
            p = params[pid]
            role = str(rec.get("role"))
            m = mono.get(role)
            if m is None:
                continue
            rmin, rmax = p.get("range_min"), p.get("range_max")
            if rmin is None and rmax is None:
                continue        # unbounded parameters are immutable
            if pid in effect_side:
                continue        # outcomes are moved by causes, not set
            improve_by_increase = (m > 0) == (obj_dir == "MAXIMIZE")
            move = "INCREASE" if improve_by_increase else "DECREASE"
            room = (improve_by_increase and
                    (rmax is None or float(rec["value"]) < rmax - 1e-12)) \
                or ((not improve_by_increase) and
                    (rmin is None or float(rec["value"]) > rmin + 1e-12))
            if not room:
                continue
            elast = (sensitivity.get(pid) or {}).get("elasticity")
            candidates.append((
                -(elast if elast is not None else -1.0), pid, rec, p))
        candidates.sort(key=lambda t: (t[0], t[1]))
        if candidates:
            _, pid, rec, p = candidates[0]
            role = str(rec.get("role"))
            m = mono[role]
            improve_by_increase = (m > 0) == (obj_dir == "MAXIMIZE")
            move = "INCREASE" if improve_by_increase else "DECREASE"
            solve = _solve_for_margin(
                eq, base_inputs, role, rec, p, move,
                objective_record["binding_constraint"], obj_dir,
                obj_comp)
            limiting_variable = {
                "param_id": pid, "name": p.get("name"),
                "improving_move": move,
                "objective_target": obj_target,
                "objective_direction": obj_dir,
                "equation_id": eq_id,
                "elasticity": (sensitivity.get(pid) or {}).get(
                    "elasticity"),
                "envelope": [p.get("range_min"), p.get("range_max")],
                "envelope_class": p.get("range_class"),
                "requirement": objective_record[
                    "binding_constraint"],
                "solve_for": solve,
                "convention": {
                    "name": "MAGNITUDE_RANKED_ELASTICITY",
                    "epistemic_class": "ENGINEERING",
                    "justification": (
                        "among design variables with a declared "
                        "envelope, an improving direction, and a "
                        "monotone bound relation, the limiting "
                        "variable is the one with the highest "
                        "normalized elasticity (a 1% input move "
                        "moves the objective the most percent). "
                        "R379's ordinal path-length convention "
                        "governs when no equation binds."),
                    "uncertainty": "elasticity is a local "
                                   "linearization",
                },
                "statement": _limiting_statement(
                    p, pid, move, solve, sensitivity.get(pid),
                    objective_record, obj_comp),
            }
            steps.append(
                f"limiting variable {pid} (elasticity "
                f"{(sensitivity.get(pid) or {}).get('elasticity')}); "
                f"solve_for status {solve.get('status')}")

    n_computed = sum(1 for c in computations
                     if c.get("status") == "COMPUTED")
    status = ("QUANTIFIED" if objective_record.get("computed") and
              objective_record.get("margin") is not None
              else ("PARTIALLY_QUANTIFIED" if n_computed
                    else "UNQUANTIFIED"))

    uncertainty = {
        "inactive_bindings": [
            {"equation_id": b.get("equation_id"),
             "status": b.get("status"),
             "problems": b.get("problems")}
            for b in bindings if b.get("status") != "ACTIVE"],
        "blocked_validity": [
            {"equation_id": c.get("equation_id"),
             "validity": c.get("validity")}
            for c in computations
            if c.get("status") == "BLOCKED_VALIDITY"],
        "geometry_used": measurements is not None,
        "model_id": (model or {}).get("model_id"),
        "note": ("unresolved inputs and blocked validity are recorded "
                 "and never converted into values (Art. XXV/IV); the "
                 "objective margin exists only when the candidate's "
                 "own constraints state a requirement"),
    }

    return {
        "evaluator_id": EVALUATOR_ID,
        "fidelity_tier": FIDELITY_TIER,
        "evidence_rank": EVIDENCE_RANK,
        "version": EQUATION_LAYER_VERSION,
        "status": status,
        "bindings": bindings,
        "computations": computations,
        "objective": objective_record,
        "requirement_satisfied": requirement_satisfied,
        "sensitivity": sensitivity,
        "limiting_variable": limiting_variable,
        "uncertainty": uncertainty,
        "thresholds": QUANTITATIVE_THRESHOLDS,
        "computation_log": {
            "evaluator_id": EVALUATOR_ID,
            "fidelity_tier": FIDELITY_TIER,
            "evidence_rank": EVIDENCE_RANK,
            "input_state_sha256": sha256_obj(state or {}),
            "model_id": (model or {}).get("model_id"),
            "equations_evaluated": sorted(EQUATIONS.keys()),
            "steps": steps,
            "computed_at": utc_now(),
            "deterministic": True,
        },
        "evidence_class_note": (
            "every computed value in this evaluation is a "
            "COMPUTATIONAL_RESULT (rank 4) from a declared analytical "
            "relation with a computation log naming every input, its "
            "source and class; MODELLED inputs stay MODELLED, "
            "GEOMETRY_MEASURED inputs are measurements of the BUILT "
            "SOLID by the CAD kernel (also rank 4); nothing here is a "
            "physical observation and the state is never written back "
            "(Art. XXVIII / XXXVIII / IX)"),
    }


def _limiting_statement(p: Dict[str, Any], pid: str, move: str,
                        solve: Optional[Dict[str, Any]],
                        sens: Optional[Dict[str, Any]],
                        objective_record: Dict[str, Any],
                        obj_comp: Dict[str, Any]) -> str:
    elast = (sens or {}).get("elasticity")
    req = objective_record.get("binding_constraint") or {}
    base = (f"The limiting variable is {p.get('name') or pid} "
            f"({pid}): elasticity {elast} — a 1% change moves the "
            f"objective ~{elast}%; the improving move is {move}.")
    mf_pct = QUANTITATIVE_THRESHOLDS["SOLVE_MARGIN_FACTOR"]["value"] * 100
    if solve:
        if solve.get("status") == "REACHABLE":
            base += (f" Solving {obj_comp.get('equation_name')} for "
                     f"the {mf_pct:.0f}% margin target requires "
                     f"{pid} = {solve.get('proposed_value'):.4g} "
                     f"(from {solve.get('current_value'):.4g}), "
                     f"predicting {objective_record.get('target')} = "
                     f"{solve.get('predicted_output'):.4g} "
                     f"{solve.get('output_unit')} (margin "
                     f"{solve.get('predicted_margin') * 100:+.1f}%).")
        elif solve.get("status") == "UNREACHABLE_IN_ENVELOPE":
            base += (f" The margin target is UNREACHABLE inside the "
                     f"declared envelope [{solve.get('envelope')}] — "
                     f"best achievable at the envelope edge is "
                     f"{solve.get('best_output'):.4g} "
                     f"{solve.get('output_unit')} (margin "
                     f"{solve.get('best_margin') * 100:+.1f}%): "
                     f"measured evidence that no defensible "
                     f"improvement inside this design space meets "
                     f"the requirement.")
        else:
            base += f" solve_for: {solve.get('status')}."
    return base


def _solve_for_margin(eq: Dict[str, Any],
                      base_inputs: Dict[str, Any], role: str,
                      rec: Dict[str, Any], p: Dict[str, Any],
                      move: str, binding_constraint: Dict[str, Any],
                      obj_dir: str, obj_comp: Dict[str, Any]
                      ) -> Dict[str, Any]:
    """Deterministic bisection solve for the design-variable value that
    reaches limit * (1 +/- SOLVE_MARGIN_FACTOR). The equation is
    monotone in the input (declared in the registry) so bisection is
    exact to the declared tolerance. Honest statuses: REACHABLE,
    UNREACHABLE_IN_ENVELOPE (with best-achievable evidence),
    UNBOUNDED_ENVELOPE, NOOP_AT_TARGET."""
    mf = QUANTITATIVE_THRESHOLDS["SOLVE_MARGIN_FACTOR"]["value"]
    iters = QUANTITATIVE_THRESHOLDS["BISECTION_ITERATIONS"]["value"]
    lim = float(binding_constraint.get("limit"))
    bound = str(binding_constraint.get("bound"))
    target = lim * (1.0 + mf) if bound == ">=" else lim * (1.0 - mf)
    rmin, rmax = p.get("range_min"), p.get("range_max")
    cur = float(rec["value"])
    edge = rmax if move == "INCREASE" else rmin
    out_unit = obj_comp.get("output_unit")
    f_out = unit_si(out_unit) or (1.0, "ratio")
    f_in = unit_si(rec.get("unit")) or (1.0, "ratio")
    si = {r["role"]: float(r["si_value"])
          for r in (base_inputs or {}).get("inputs") or []}

    def _output_at(x_param_unit: float) -> Optional[float]:
        # x is in the PARAM's unit; convert to SI for compute
        x_si = x_param_unit * f_in[0]
        si2 = dict(si)
        si2[role] = x_si
        try:
            out_si = float(eq["compute_si"](si2))
        except (KeyError, TypeError, ValueError, ZeroDivisionError,
                OverflowError):
            return None
        return out_si / f_out[0]          # in the output param unit

    def _requirement_gap(x: float) -> Optional[float]:
        """< 0 means requirement unmet at x; monotone INCREASING along
        the improving direction of x."""
        y = _output_at(x)
        if y is None:
            return None
        if bound == ">=":
            return y - target
        return target - y

    solve: Dict[str, Any] = {
        "role": role, "param_id": p.get("param_id"),
        "improving_move": move,
        "target_value": round(target, 9),
        "target_basis": {
            "constraint_id": binding_constraint.get("constraint_id"),
            "bound": bound, "limit": lim,
            "margin_factor": mf,
            "note": ("limit x (1 +/- declared SOLVE_MARGIN_FACTOR); "
                     "the T-gates and K-gates still decide the "
                     "proposal (Art. XXVII: declared convention)")},
        "current_value": round(cur, 9),
        "envelope": [rmin, rmax],
        "output_unit": out_unit,
        "method": (f"deterministic bisection, {iters} iterations, "
                   f"monotone in {role} (declared)"),
    }
    if edge is None:
        solve["status"] = "UNBOUNDED_ENVELOPE"
        solve["note"] = ("the envelope is unbounded in the improving "
                         "direction — a finite solve is not defined; "
                         "no deterministic proposal is generated")
        return solve
    gap_cur = _requirement_gap(cur)
    gap_edge = _requirement_gap(float(edge))
    if gap_cur is None or gap_edge is None:
        solve["status"] = "SOLVE_COMPUTE_ERROR"
        return solve
    if gap_cur >= 0:
        solve["status"] = "NOOP_AT_TARGET"
        return solve
    if gap_edge < 0:
        best_out = _output_at(float(edge))
        solve["status"] = "UNREACHABLE_IN_ENVELOPE"
        solve["best_value"] = float(edge)
        solve["best_output"] = round(best_out, 9) \
            if best_out is not None else None
        if best_out is not None:
            bm = ((best_out - lim) / abs(lim)) if bound == ">=" \
                else ((lim - best_out) / abs(lim))
            solve["best_margin"] = round(bm, 6)
        solve["note"] = ("MEASURED evidence: even at the envelope "
                         "edge the requirement (with the declared "
                         "margin factor) is not reached — no "
                         "defensible improvement inside the declared "
                         "design space meets it")
        return solve
    # bisect in the improving-direction coordinate u = s * x so the
    # requirement gap is monotone INCREASING in u for BOTH move
    # directions (a DECREASE move inverts the raw-x ordering — the
    # first draft bisected raw x and converged onto the current value
    # for every DECREASE case; caught by the hand-computed smoke)
    s = 1.0 if move == "INCREASE" else -1.0
    u_cur, u_edge = s * cur, s * float(edge)
    lo, hi = min(u_cur, u_edge), max(u_cur, u_edge)
    for _ in range(int(iters)):
        mid = (lo + hi) / 2.0
        g = _requirement_gap(mid / s)
        if g is None:
            solve["status"] = "SOLVE_COMPUTE_ERROR"
            return solve
        if g < 0:
            lo = mid
        else:
            hi = mid
    x_star = (lo + hi) / 2.0 / s
    pred = _output_at(x_star)
    solve["status"] = "REACHABLE"
    solve["proposed_value"] = round(x_star, 9)
    solve["predicted_output"] = round(pred, 9) if pred is not None \
        else None
    if pred is not None:
        pm = ((pred - lim) / abs(lim)) if bound == ">=" \
            else ((lim - pred) / abs(lim))
        solve["predicted_margin"] = round(pm, 6)
    solve["note"] = ("a DETERMINISTIC proposal from the bound "
                     "equation — it enters the production T-gates "
                     "like any LLM proposal (no exemption); the "
                     "child's OWN re-evaluation after the CAD rebuild "
                     "decides KEEP/KILL")
    return solve


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------
def evaluate_candidate_quantitatively(spec: Dict[str, Any]
                                       ) -> Dict[str, Any]:
    """Evaluate a candidate's spec quantitatively: reads the
    technical_state section and the candidate's OWN parametric model
    (R380 loop order: geometry validation -> technical evaluation; the
    MEASURED geometry of the built solid feeds the equations where a
    resolver exists). A spec WITHOUT a technical state returns the
    honest UNQUANTIFIED record — never an error, never fabricated
    numbers."""
    state = get_technical_state(spec)
    if state is None:
        return {
            "evaluator_id": EVALUATOR_ID,
            "fidelity_tier": FIDELITY_TIER,
            "evidence_rank": EVIDENCE_RANK,
            "version": EQUATION_LAYER_VERSION,
            "status": "UNQUANTIFIED",
            "bindings": [], "computations": [],
            "objective": {"computed": False, "margin": None,
                          "margin_status": "UNCOMPUTED",
                          "statement": "no technical_state section on "
                                        "this spec — the analytical "
                                        "layer never engaged"},
            "requirement_satisfied": None,
            "sensitivity": {}, "limiting_variable": None,
            "uncertainty": {"note": "no state present"},
            "thresholds": QUANTITATIVE_THRESHOLDS,
            "computation_log": {
                "evaluator_id": EVALUATOR_ID,
                "fidelity_tier": FIDELITY_TIER,
                "evidence_rank": EVIDENCE_RANK,
                "input_state_sha256": None,
                "steps": ["no technical state present"],
                "computed_at": utc_now(),
                "deterministic": True},
            "evidence_class_note": (
                "no prediction made — nothing was evaluated"),
        }
    model = None
    try:
        from .cad_pipeline import get_parametric_model  # noqa: PLC0415
        model = get_parametric_model(spec)
    except ImportError:
        model = None        # hermetic state-only mode (recorded)
    return evaluate_quantitatively(state, model)


def quantitative_margin_comparison(
        parent_quant: Optional[Dict[str, Any]],
        child_quant: Optional[Dict[str, Any]]
        ) -> Dict[str, Any]:
    """The K8 comparison record: did the child's OWN quantitative
    objective margin improve over the parent's, from the SAME bound
    equation, by at least the declared non-trivial fraction? Pure
    function over the two evaluation records — the K8 keep gate
    consumes this; nothing is mutated here."""
    thr = QUANTITATIVE_THRESHOLDS[
        "QUANT_MIN_RELATIVE_IMPROVEMENT"]["value"]
    p_obj = (parent_quant or {}).get("objective") or {}
    c_obj = (child_quant or {}).get("objective") or {}
    out: Dict[str, Any] = {
        "engaged": False, "parent_margin": None, "child_margin": None,
        "improvement": None, "threshold": thr, "verdict": "NOT_ENGAGED",
        "parent_value": p_obj.get("value"),
        "child_value": c_obj.get("value"),
        "parent_unit": p_obj.get("unit"),
        "equation_id": c_obj.get("equation_id"),
    }
    if not (p_obj.get("computed") and c_obj.get("computed")):
        out["reason"] = ("quantitative objective not computed on both "
                         "sides — the direction-level K1 criterion "
                         "governs")
        return out
    if p_obj.get("equation_id") != c_obj.get("equation_id"):
        out["reason"] = ("parent and child computed the objective "
                         "under DIFFERENT bound equations — comparing "
                         "margins across models would be "
                         "model-laundering; not engaged (Art. XXVIII)")
        return out
    # anti-forgery (Art. VI/XXX): a margin claim WITHOUT the
    # computation that produced it is not evidence — both records must
    # carry the COMPUTED entry for this equation and a computation log
    for side, quant in (("parent", parent_quant), ("child", child_quant)):
        comps = [c for c in (quant or {}).get("computations") or []
                 if c.get("equation_id") == c_obj.get("equation_id")
                 and c.get("status") == "COMPUTED"]
        has_log = bool((quant or {}).get("computation_log"))
        if not comps or not has_log:
            out["reason"] = (
                f"the {side} margin claim carries NO computation "
                f"record for {c_obj.get('equation_id')} — a margin "
                f"without its computation is a forged claim, not "
                f"evidence (Art. VI); K8 refuses to compare it")
            return out
    pm_, cm_ = p_obj.get("margin"), c_obj.get("margin")
    if pm_ is None or cm_ is None:
        out["reason"] = ("margin not computable on both sides (no "
                         "direction-consistent requirement)")
        return out
    out["engaged"] = True
    out["parent_margin"] = pm_
    out["child_margin"] = cm_
    out["improvement"] = round(cm_ - pm_, 9)
    out["verdict"] = "IMPROVED" if (cm_ - pm_) >= thr else "NOT_IMPROVED"
    out["statement"] = (
        f"objective {c_obj.get('target')} margin "
        f"{pm_ * 100:+.1f}% -> {cm_ * 100:+.1f}% "
        f"(improvement {(cm_ - pm_) * 100:+.1f} points of the limit, "
        f"threshold {thr * 100:.1f}); values "
        f"{p_obj.get('value')} -> {c_obj.get('value')} "
        f"{c_obj.get('unit')} — both COMPUTATIONAL_RESULTs from "
        f"{c_obj.get('equation_id')} with computation logs")
    return out


def _contract_wrapper(ctx: Any) -> Dict[str, Any]:
    """Evaluator-contract adapter (same registration pattern as the
    R379 technical evaluator: opt-in, never the default diagnostic)."""
    return evaluate_candidate_quantitatively(ctx.spec)


try:                                   # opt-in registration (never default)
    from .evaluator_contract import register_evaluator  # noqa: PLC0415
    register_evaluator(EVALUATOR_ID, FIDELITY_TIER, _contract_wrapper)
except Exception:  # noqa: BLE001 — registration must never break import
    pass
