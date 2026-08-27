"""discovery_fabric/engine/equations.py — E7 domain equation library.

CEO E7: the invention specification triggers a domain equation library, but
every equation must identify equation_id, variables, source, applicability
and assumptions. This is what stops the system from sprinkling
impressive-looking equations into every dossier.

Constitutional guardrails (Art. II, XXVII, XXXVIII):
  - Equations are EXTERNAL_PRECEDENT knowledge (textbook/standard
    relationships), tagged with a source string a human can verify.
  - Numeric evaluation is allowed ONLY when every required input exists with
    epistemic class SOURCE_FACT or COMPUTED. Otherwise the equation is
    emitted symbolically with UNKNOWN inputs — never with invented numbers.
  - Applicability is a RECORDED JUDGMENT (MODEL_DERIVED) with its rationale;
    it never silently becomes a fact about the invention.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .invention_spec import tagged  # reuse the one tagging authority

Equation = Dict[str, Any]


def _eq(equation_id: str, name: str, expression: str, variables: List[dict],
        source: str, applicability: str, assumptions: List[str],
        domain: str, output_symbol: str) -> Equation:
    """Mark the LHS variable with role=output so evaluation requires only
    the independent inputs."""
    for var in variables:
        var["role"] = "output" if var["symbol"] == output_symbol else "input"
    return {
        "equation_id": equation_id,
        "name": name,
        "expression": expression,
        "variables": variables,          # symbol, description, unit, role
        "output_symbol": output_symbol,
        "source": {"text": source, "epistemic_class": "EXTERNAL_PRECEDENT",
                   "verify_before_release": True},
        "applicability": {"condition": applicability,
                          "epistemic_class": "MODEL_DERIVED",
                          "judged_for_domain": domain},
        "assumptions": assumptions,
    }


# --------------------------------------------------------------------------
EQUATION_LIBRARY: Dict[str, List[Equation]] = {
    "fluidics_hydraulic": [
        _eq("FLUID-001", "Hagen-Poiseuille (laminar pipe flow)",
            "Q = (pi * r^4 * dP) / (8 * mu * L)",
            [{"symbol": "Q", "description": "volumetric flow rate", "unit": "m^3/s"},
             {"symbol": "r", "description": "lumen radius", "unit": "m"},
             {"symbol": "dP", "description": "pressure drop", "unit": "Pa"},
             {"symbol": "mu", "description": "dynamic viscosity", "unit": "Pa.s"},
             {"symbol": "L", "description": "lumen length", "unit": "m"}],
            "standard Newtonian laminar pipe-flow relation (any fluid-mechanics text)",
            "Newtonian fluid, laminar regime, rigid circular lumen, fully developed flow",
            ["CSF approximated as Newtonian (valid at shunt flow rates)",
             "no wall compliance effects"],
            "fluidics_hydraulic", output_symbol="Q"),
        _eq("FLUID-002", "Reynolds number",
            "Re = (rho * v * D) / mu",
            [{"symbol": "Re", "description": "Reynolds number", "unit": "-"},
             {"symbol": "rho", "description": "density", "unit": "kg/m^3"},
             {"symbol": "v", "description": "mean velocity", "unit": "m/s"},
             {"symbol": "D", "description": "hydraulic diameter", "unit": "m"},
             {"symbol": "mu", "description": "dynamic viscosity", "unit": "Pa.s"}],
            "standard dimensionless similarity number (any fluid-mechanics text)",
            "circular section; single-phase flow",
            ["transition criterion Re~2300 is a MODEL_DERIVED engineering rule of thumb"],
            "fluidics_hydraulic", output_symbol="Re"),
        _eq("FLUID-003", "Orifice flow (sharp-edged restriction)",
            "Q = C_d * A * sqrt(2 * dP / rho)",
            [{"symbol": "Q", "description": "volumetric flow rate", "unit": "m^3/s"},
             {"symbol": "C_d", "description": "discharge coefficient", "unit": "-"},
             {"symbol": "A", "description": "orifice area", "unit": "m^2"},
             {"symbol": "dP", "description": "pressure drop", "unit": "Pa"},
             {"symbol": "rho", "description": "density", "unit": "kg/m^3"}],
            "standard orifice-equation form (any fluid-mechanics text)",
            "turbulent orifice flow; C_d treated as MODEL_DERIVED until measured",
            ["C_d ~0.6-0.65 is an engineering prior, not a measurement"],
            "fluidics_hydraulic", output_symbol="Q"),
    ],
    "optical_photonic": [
        _eq("OPT-001", "Beer-Lambert attenuation",
            "I = I0 * exp(-mu_a * d)",
            [{"symbol": "I", "description": "transmitted intensity", "unit": "W/m^2"},
             {"symbol": "I0", "description": "incident intensity", "unit": "W/m^2"},
             {"symbol": "mu_a", "description": "effective attenuation coefficient", "unit": "1/m"},
             {"symbol": "d", "description": "path depth", "unit": "m"}],
            "Beer-Lambert law (standard radiative-transfer relation)",
            "homogeneous medium; effective coefficient folds scattering into mu_a",
            ["tissue is heterogeneous; mu_a is a MODEL_DERIVED effective value"],
            "optical_photonic", output_symbol="I"),
        _eq("OPT-002", "Photovoltaic conversion",
            "P_elec = eta * I * A",
            [{"symbol": "P_elec", "description": "electrical power", "unit": "W"},
             {"symbol": "eta", "description": "conversion efficiency", "unit": "-"},
             {"symbol": "I", "description": "irradiance at cell", "unit": "W/m^2"},
             {"symbol": "A", "description": "cell area", "unit": "m^2"}],
            "standard photovoltaic power relation (photovoltaics texts)",
            "cell operated below saturation; eta at actual wavelength and temperature",
            ["eta under monochromatic NIR differs from solar-rated eta"],
            "optical_photonic", output_symbol="P_elec"),
    ],
    "rf_wireless": [
        _eq("RF-001", "Friis link budget",
            "P_r = P_t * G_t * G_r * (lambda / (4 * pi * d))^2",
            [{"symbol": "P_r", "description": "received power", "unit": "W"},
             {"symbol": "P_t", "description": "transmitted power", "unit": "W"},
             {"symbol": "G_t", "description": "tx antenna gain", "unit": "-"},
             {"symbol": "G_r", "description": "rx antenna gain", "unit": "-"},
             {"symbol": "lambda", "description": "wavelength", "unit": "m"},
             {"symbol": "d", "description": "distance", "unit": "m"}],
            "Friis transmission equation (standard antenna-theory relation)",
            "far field, line of sight; tissue path requires additional loss term",
            ["in-body path loss exceeds free-space — margin is MODEL_DERIVED"],
            "rf_wireless", output_symbol="P_r"),
        _eq("RF-002", "Signal-to-noise ratio",
            "SNR = P_signal / P_noise",
            [{"symbol": "SNR", "description": "signal-to-noise ratio", "unit": "-"},
             {"symbol": "P_signal", "description": "signal power", "unit": "W"},
             {"symbol": "P_noise", "description": "noise power", "unit": "W"}],
            "standard detection-theory quantity (communications texts)",
            "defined for the chosen detection bandwidth",
            ["noise figure and interference terms must be budgeted explicitly"],
            "rf_wireless", output_symbol="SNR"),
    ],
    "acoustic": [
        _eq("AC-001", "Acoustic impedance contrast (pulse-echo)",
            "R = ((Z2 - Z1) / (Z2 + Z1))^2",
            [{"symbol": "R", "description": "reflected intensity fraction", "unit": "-"},
             {"symbol": "Z1", "description": "impedance of medium 1", "unit": "Rayl"},
             {"symbol": "Z2", "description": "impedance of medium 2", "unit": "Rayl"}],
            "standard plane-wave reflection coefficient (ultrasonics texts)",
            "normal incidence, plane wave, lossless media",
            ["oblique incidence and attenuation modify detectability"],
            "acoustic", output_symbol="R"),
    ],
    "mri_nmr": [
        _eq("MRI-001", "Larmor frequency",
            "f0 = gamma * B0",
            [{"symbol": "f0", "description": "precession frequency", "unit": "Hz"},
             {"symbol": "gamma", "description": "gyromagnetic ratio (H-1: 42.58 MHz/T)", "unit": "Hz/T"},
             {"symbol": "B0", "description": "static field strength", "unit": "T"}],
            "standard NMR relation (MRI physics texts)",
            "single species (protons), weak-field linear regime",
            [],
            "mri_nmr", output_symbol="f0"),
    ],
    "enzyme_biocatalytic": [
        _eq("ENZ-001", "Michaelis-Menten kinetics",
            "v = (Vmax * S) / (Km + S)",
            [{"symbol": "v", "description": "reaction rate", "unit": "mol/s"},
             {"symbol": "Vmax", "description": "max rate", "unit": "mol/s"},
             {"symbol": "S", "description": "substrate concentration", "unit": "mol/m^3"},
             {"symbol": "Km", "description": "Michaelis constant", "unit": "mol/m^3"}],
            "standard enzyme-kinetics relation (biochemistry texts)",
            "steady state, single substrate, enzyme stability maintained",
            ["immobilization shifts Km/Vmax — must be re-measured on-surface"],
            "enzyme_biocatalytic", output_symbol="v"),
    ],
    "phage_microbio": [
        _eq("BIO-001", "Multiplicity of infection",
            "MOI = N_phage / N_bacteria",
            [{"symbol": "MOI", "description": "multiplicity of infection", "unit": "-"},
             {"symbol": "N_phage", "description": "phage count", "unit": "-"},
             {"symbol": "N_bacteria", "description": "bacterial count", "unit": "-"}],
            "standard microbiology dosing quantity",
            "well-mixed system; planktonic or defined-surface assay",
            ["surface-immobilized phage dosing is not a well-mixed MOI — "
             "use contact-area density instead (MODEL_DERIVED adaptation)"],
            "phage_microbio", output_symbol="MOI"),
    ],
    "mechanical_structural": [
        _eq("MEC-001", "Euler buckling load",
            "P_cr = pi^2 * E * I / (K * L)^2",
            [{"symbol": "P_cr", "description": "critical buckling load", "unit": "N"},
             {"symbol": "E", "description": "Young's modulus", "unit": "Pa"},
             {"symbol": "I", "description": "area moment of inertia", "unit": "m^4"},
             {"symbol": "K", "description": "effective-length factor", "unit": "-"},
             {"symbol": "L", "description": "column length", "unit": "m"}],
            "standard Euler column relation (mechanics of materials texts)",
            "elastic, slender column, small deflection",
            ["K for catheter constraint conditions is MODEL_DERIVED"],
            "mechanical_structural", output_symbol="P_cr"),
    ],
    "thermal": [
        _eq("TH-001", "Fourier conduction",
            "q = -k * A * dT/dx",
            [{"symbol": "q", "description": "heat flow", "unit": "W"},
             {"symbol": "k", "description": "thermal conductivity", "unit": "W/(m.K)"},
             {"symbol": "A", "description": "cross-section area", "unit": "m^2"},
             {"symbol": "dT/dx", "description": "temperature gradient", "unit": "K/m"}],
            "Fourier's law (heat-transfer texts)",
            "steady state, isotropic conduction",
            [],
            "thermal", output_symbol="q"),
    ],
    "ml_data": [
        _eq("ML-001", "Expected utility of a decision rule",
            "EU = sum_y P(y | x) * U(a(x), y)",
            [{"symbol": "EU", "description": "expected utility", "unit": "-"},
             {"symbol": "P(y|x)", "description": "posterior predictive", "unit": "-"},
             {"symbol": "U", "description": "utility of action under truth", "unit": "-"}],
            "standard Bayesian decision theory (decision-theory texts)",
            "utility table fully specified; probabilities calibrated",
            ["utility weights are BUYER_DEFINED/MODEL_DERIVED, never measured"],
            "ml_data", output_symbol="EU"),
    ],
}


def equations_for_domain(domain: str) -> List[Equation]:
    return EQUATION_LIBRARY.get(domain, [])


def evaluate_equation(eq: Equation, inputs: Dict[str, Dict[str, Any]],
                      ) -> Dict[str, Any]:
    """Attempt numeric evaluation ONLY with fully-sourced inputs.

    `inputs` maps symbol -> {"value": number, "epistemic_class": cls}.
    If ANY required symbol is missing or not SOURCE_FACT/COMPUTED, the result
    is symbolic with UNKNOWN inputs and NO number is emitted (Art. XXV/XXVII:
    no invented numbers; a model cannot masquerade as a fact).
    """
    numeric_cls = ("SOURCE_FACT", "COMPUTED")
    resolved: Dict[str, Any] = {}
    missing: List[str] = []
    unqualified: List[str] = []
    for var in eq["variables"]:
        if var.get("role") == "output":
            continue
        sym = var["symbol"]
        got = inputs.get(sym)
        if not got or got.get("value") is None:
            missing.append(sym)
        elif got.get("epistemic_class") not in numeric_cls:
            unqualified.append(sym)
        else:
            resolved[sym] = got["value"]
    if missing or unqualified:
        return {
            "equation_id": eq["equation_id"],
            "evaluation": "SYMBOLIC_ONLY",
            "missing_inputs": missing,
            "unqualified_inputs": [
                {"symbol": s, "epistemic_class": inputs.get(s, {})
                 .get("epistemic_class", "ABSENT")} for s in unqualified],
            "reason": "numeric evaluation forbidden without SOURCE_FACT or "
                      "COMPUTED inputs (Art. XXVII/XXXVIII)",
        }
    # Deterministic evaluation of the small whitelisted relations by id.
    result = _evaluate_by_id(eq["equation_id"], resolved)
    if result is None:
        return {"equation_id": eq["equation_id"],
                "evaluation": "NOT_EVALUATED",
                "reason": "no deterministic evaluator registered for this id; "
                          "symbolic emission only"}
    return {"equation_id": eq["equation_id"], "evaluation": "COMPUTED",
            "inputs_used": {k: {"value": v,
                                "epistemic_class": inputs[k]["epistemic_class"]}
                            for k, v in resolved.items()},
            "result": result}


def _evaluate_by_id(equation_id: str, v: Dict[str, float]) -> Optional[float]:
    """Whitelisted deterministic evaluators. Only arithmetic over sourced
    inputs — nothing here invents a physical parameter."""
    import math
    try:
        if equation_id == "FLUID-002":
            return round(v["rho"] * v["v"] * v["D"] / v["mu"], 2)
        if equation_id == "OPT-001":
            return round(v["I0"] * math.exp(-v["mu_a"] * v["d"]), 6)
        if equation_id == "OPT-002":
            return round(v["eta"] * v["I"] * v["A"], 6)
        if equation_id == "RF-002":
            return round(v["P_signal"] / v["P_noise"], 6)
        if equation_id == "MRI-001":
            return round(v["gamma"] * v["B0"], 2)
        if equation_id == "BIO-001":
            return round(v["N_phage"] / v["N_bacteria"], 6)
        if equation_id == "MEC-001":
            return round(math.pi ** 2 * v["E"] * v["I"]
                         / (v["K"] * v["L"]) ** 2, 4)
        if equation_id == "TH-001":
            return round(-v["k"] * v["A"] * v["dT/dx"], 6)
        # FLUID-001/003, RF-001, ENZ-001, ML-001 etc.: emitted symbolically
        # until a specific design context defines every parameter.
        return None
    except (KeyError, ZeroDivisionError, OverflowError, ValueError):
        return None


def select_equations(spec: Dict[str, Any], domain: str,
                     ) -> Dict[str, Any]:
    """Attach domain equations to the invention with per-equation selection
    rationale. Selection is MODEL_DERIVED and recorded as such."""
    eqs = equations_for_domain(domain)
    if not eqs:
        return {"value": [],
                "epistemic_class": "UNKNOWN",
                "origin_stage": "EQUATION_LIBRARY",
                "evidence_ids": [],
                "note": f"no equation library for domain {domain!r}; "
                        "no equations emitted (never sprinkled)"}
    mech_text = ""
    mech = (spec.get("mechanism") or {}).get("value") or {}
    mech_text = " ".join(str(mech.get(k, "")) for k in
                         ("mechanism", "intervention", "expected_effect"))
    selected = []
    for eq in eqs:
        selected.append({
            "equation": eq,
            "selection_rationale": {
                "epistemic_class": "MODEL_DERIVED",
                "reason": f"domain template {domain} declares this relation "
                          "as part of its governing model",
                "mechanism_mentions": [k for k in eq["variables"]
                                       if k["description"].lower()
                                       .split()[0] in mech_text.lower()],
            }})
    return {
        "value": selected,
        "epistemic_class": "EXTERNAL_PRECEDENT",
        "origin_stage": "EQUATION_LIBRARY",
        "evidence_ids": [],
        "note": ("equations are textbook/standard EXTERNAL_PRECEDENT "
                 "relations selected by domain template; numeric values are "
                 "emitted only with fully-sourced inputs"),
    }
