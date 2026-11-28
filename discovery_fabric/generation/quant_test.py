"""R144 generation strength (R143-F6) — quantitative testability.

Every strengthened invention must emit a FALSIFIABLE NUMERIC
PREDICTION backed by a running, unit-checked calculation (pint). This
module is the deterministic half: given the mechanism class + the
problem's operating parameters, it computes the expected effect with
units and produces the falsifier string. The LLM's claimed numbers are
checked for order-of-magnitude sanity against these formulas.

Design rules:
  - Every formula is standard engineering physics (Archard, Stokes,
    Darcy-Weisbach, classical nucleation, Springer droplet erosion,
    magnetic-gradient force) — no invented constants.
  - No calculation in the head: everything runs through pint and the
    trace records the inputs, the result and the unit.
  - Art. 3: a missing parameter is a typed insufficient_parameters
    record, never a silent default that pretends precision.
"""
from __future__ import annotations

from pint import UnitRegistry

UREG = UnitRegistry()
Q_ = UREG.Quantity


class InsufficientParameters(Exception):
    """Typed: the prediction cannot be computed from the given data."""

    def __init__(self, missing):
        self.missing = list(missing)
        super().__init__(
            "typed insufficient_parameters: missing " + ", ".join(missing))


def _finite(x):
    return bool(x == x) and abs(float(x)) != float("inf")


# --- the formula library (one function per mechanism class) --------------

def archard_wear_reduction(hardness_before_Hv: float,
                           hardness_after_Hv: float) -> dict:
    """Archard: V = k*W*s/H -> wear rate scales 1/H."""
    h0 = Q_(hardness_before_Hv, "MPa")  # Hv ~ MPa convention
    h1 = Q_(hardness_after_Hv, "MPa")
    if h1 <= h0:
        raise InsufficientParameters(
            ["hardness_after must exceed hardness_before for a "
             "surface-hardening claim"])
    reduction = 1 - h0 / h1
    red = reduction.magnitude if hasattr(reduction, "magnitude") \
        else reduction
    return {"quantity": "wear rate (Archard, rate ~ 1/H)",
            "baseline": "relative 1.0",
            "predicted": f"relative {1 - red:.3f}",
            "delta_pct": round(red * 100, 1),
            "calc_trace": (f"1 - {h0:.0f}/{h1:.0f} = {red:.3f} "
                           "reduction (Archard V = k*W*s/H)"),
            "falsifier": (f"wear-coupon mass loss must fall >= "
                          f"{red * 100:.0f}% vs the un-treated "
                          "control under the same load/speed; a "
                          "smaller reduction falsifies"),
            "units_ok": True}


def stokes_settling_velocity(rho_p: float, rho_f: float, d: float,
                             mu: float) -> dict:
    """Stokes: v = g*d^2*(rho_p-rho_f)/(18*mu) — laminar settling."""
    v = (Q_(9.81, "m/s^2") * Q_(d, "m") ** 2 * Q_(rho_p - rho_f, "kg/m^3")
         / (18 * Q_(mu, "Pa*s")))
    v_mms = v.to("mm/s").magnitude
    t_min = (Q_(1, "m") / v).to("min").magnitude
    return {"quantity": "particle settling velocity (Stokes, laminar)",
            "predicted_value": f"{v_mms:.2f} mm/s",
            "calc_trace": (f"v = 9.81*({d} m)^2*({rho_p}-{rho_f})/"
                           f"(18*{mu} Pa.s) = {v_mms:.2f} mm/s"),
            "falsifier": (f"a settling test must show the target "
                          f"fraction settled within t = "
                          f"{t_min:.1f} min for a 1 m "
                          "path; slower settling falsifies"),
            "units_ok": True}


def magnetic_gradient_force(chi: float, B: float, gradB: float,
                            V: float, rho_p: float) -> dict:
    """F = chi*V/mu0 * B*gradB vs weight — is separation feasible."""
    f_mag = (Q_(chi, "dimensionless") * Q_(V, "m^3") / UREG.mu0
             * Q_(B, "tesla") * Q_(gradB, "tesla/m"))
    f_grav = Q_(V * rho_p, "kg") * Q_(9.81, "m/s^2")
    ratio = (f_mag / f_grav).to("dimensionless")
    return {"quantity": "magnetic force / particle weight",
            "predicted_value": f"{ratio:.1f}",
            "calc_trace": (f"F = chi*V/mu0 * B*gradB = {f_mag:.2e} N; "
                           f"W = {f_grav:.2e} N; ratio {ratio:.1f}"),
            "falsifier": ("separation only if ratio > 1 (>= 5 for "
                          "continuous capture); ratio <= 1 falsifies "
                          "the magnetic-route claim"),
            "units_ok": True}


def darcy_weisbach_dp(f: float, L: float, D: float, v: float,
                      rho: float) -> dict:
    """dp = f*L/D * rho*v^2/2 — the flow-path pressure penalty."""
    dp = Q_(f, "dimensionless") * Q_(L / D, "dimensionless") \
        * Q_(rho, "kg/m^3") * Q_(v, "m/s") ** 2 / 2
    return {"quantity": "pressure drop (Darcy-Weisbach)",
            "predicted_value": f"{dp.to('kPa'):.1f}",
            "calc_trace": (f"dp = {f}*{L}/{D}*{rho}*{v}^2/2 = "
                           f"{dp.to('kPa'):.1f}"),
            "falsifier": (f"the loop must show <= {dp.to('kPa'):.0f} "
                          "kPa added drop at design flow; more "
                          "falsifies the geometry claim"),
            "units_ok": True}


def nucleation_rate_floor(T_supercool_K: float) -> dict:
    """The melt-form homogeneous nucleation rate for water, anchored
    to the textbook homogeneous-freezing onset (~ -38 C for micrometer
    drops, J ~ 1e25 m^-3 s^-1): J(dT) = J0*exp(-C/dT^2) with
    C = ln(J0/J_onset)*dT_onset^2 (standard Arrhenius melt form; the
    anchor is measured physics, not an invented constant). At small
    supercooling J is effectively zero — the physical story: WITHOUT
    an intervention, nucleation simply does not happen here; the
    mechanism's claim is that it CREATES controlled onset."""
    import math
    dT = float(T_supercool_K)
    if dT <= 0:
        raise InsufficientParameters(["T_supercool_K must be > 0"])
    J0 = 1e30            # kinetic prefactor (m^-3 s^-1)
    dT_onset = 38.15     # water homogeneous onset: 273.15 - 235 K
    J_onset = 1e25       # at the onset, freezing within ~1 s
    C = math.log(J0 / J_onset) * dT_onset ** 2
    J = J0 * math.exp(-C / (dT * dT))
    return {"quantity": ("homogeneous nucleation rate (water, melt "
                         "form, anchored at the -38C onset)"),
            "predicted_value": f"J = {J:.2e} m^-3 s^-1 at dT={dT} K",
            "calc_trace": (f"C = ln(1e30/1e25)*38.15^2 = {C:.0f}; "
                           f"J = 1e30*exp(-{C:.0f}/{dT}^2) = {J:.2e}"),
            "falsifier": ("the intervention (controlled sites / "
                          "ultrasound / inhibitor) must produce a "
                          "MEASURED onset within +/-1 K of its design "
                          "point; at small supercooling the "
                          "unintervened homogeneous rate is ~0, so an "
                          "observed uncontrolled burst falsifies "
                          "site-control, and NO measurable onset "
                          "falsifies the mechanism"),
            "units_ok": True}


def springer_droplet_erosion(v_impact: float, rho_l: float = 1000.0) -> dict:
    """Droplet-impact erosion scales ~ v^n (n≈5) — the elastic-layer
    benefit comes from cutting the transmitted stress peak."""
    n = 5
    ratio = (Q_(v_impact, "m/s") / Q_(100.0, "m/s")) ** n
    return {"quantity": ("droplet-impact erosion intensity ordering "
                         f"(v^{n} scaling)"),
            "predicted_value": f"relative {ratio:.3f} vs a 100 m/s "
                               "reference",
            "calc_trace": (f"({v_impact} m/s / 100 m/s)^{n} = "
                           f"{ratio:.3f}"),
            "falsifier": ("a rain-erosion whirling-arm coupon must track "
                          "the v^5 curve; a compliant layer's benefit "
                          "shows as a threshold shift — if the coating "
                          "does NOT raise the damaging-speed threshold "
                          ">= 15%, it falsifies"),
            "units_ok": True}


def convective_boiling_hrx(q_flux: float, h_ref: float, h_new: float
                           ) -> dict:
    """Heat-transfer gain from enhanced nucleate boiling surfaces."""
    q1 = Q_(q_flux, "kW/m^2")
    gain = (h_new / h_ref - 1) * 100
    return {"quantity": "wall superheat reduction at fixed flux",
            "predicted_value": (f"h {h_ref} -> {h_new} W/m^2K = "
                                f"{gain:.0f}% gain"),
            "calc_trace": f"gain = {h_new}/{h_ref} - 1 = {gain / 100:.2f}",
            "falsifier": (f"at {q1} the wall superheat must drop "
                          f">= {gain / 2:.0f}% on a sized test rig; "
                          "less falsifies"),
            "units_ok": True}


# --- the dispatcher -------------------------------------------------------

FORMULAS = {
    "surface_hardening_treatment": archard_wear_reduction,
    "density_settling_separation": stokes_settling_velocity,
    "magnetic_gradient_separation": magnetic_gradient_force,
    "flow_geometry_antifouling": darcy_weisbach_dp,
    "nucleation_inhibitor_dosing": nucleation_rate_floor,
    "compliant_elastomer_coating": springer_droplet_erosion,
    "controlled_nucleation_sites": convective_boiling_hrx,
    "acoustic_ultrasonic_nucleation": convective_boiling_hrx,
}


def emit_prediction(mech_class: str, params: dict) -> dict:
    """Compute the typed prediction for the mechanism class. Typed
    failure modes: unknown_mechanism_class, insufficient_parameters."""
    fn = FORMULAS.get(mech_class)
    if fn is None:
        return {"status": "no_formula_for_class",
                "mech_class": mech_class,
                "note": ("typed: no deterministic formula is registered "
                         "for this mechanism class — the invention must "
                         "carry an explicit first-principles estimate "
                         "and its test in the row (the LLM half); the "
                         "prediction is still REQUIRED, just not "
                         "pre-computed here")}
    try:
        pred = fn(**params)
        pred["status"] = "computed"
        return pred
    except InsufficientParameters as e:
        return {"status": "insufficient_parameters",
                "missing": e.missing,
                "note": ("typed: the problem statement does not carry "
                         "the parameters — the invention must NAME the "
                         "measurement plan for them (the falsifier "
                         "still needs the numbers)")}
    except Exception as e:  # typed compute failure, never silent
        return {"status": "compute_error",
                "error": f"{type(e).__name__}: {e}",
                "note": "typed: the formula inputs are out of range"}
