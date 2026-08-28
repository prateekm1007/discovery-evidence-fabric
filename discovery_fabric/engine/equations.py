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
        _eq("OPT-003", "Numerical aperture",
            "NA = n * sin(theta)",
            [{"symbol": "NA", "description": "numerical aperture", "unit": "-"},
             {"symbol": "n", "description": "refractive index of medium", "unit": "-"},
             {"symbol": "theta", "description": "half-angle of accepted cone", "unit": "rad"}],
            "standard geometrical-optics relation (optics texts)",
            "paraxial regime; homogeneous medium at the interface",
            ["coupling/acceptance angles follow from NA and must be "
             "verified on the actual geometry"],
            "optical_photonic", output_symbol="NA"),
        _eq("OPT-004", "Thermal load deposited at target",
            "Q = I * A * (1 - eta_conversion)",
            [{"symbol": "Q", "description": "heat deposited at target", "unit": "W"},
             {"symbol": "I", "description": "irradiance at target", "unit": "W/m^2"},
             {"symbol": "A", "description": "illuminated area", "unit": "m^2"},
             {"symbol": "eta_conversion", "description": "converted fraction", "unit": "-"}],
            "energy-balance relation (radiative transfer + conversion)",
            "steady state; unconverted power deposits as heat",
            ["steady temperature requires a conduction/perfusion model "
             "before any quantitative claim"],
            "optical_photonic", output_symbol="Q"),

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
        _eq("RF-003", "Thermal noise floor",
            "N = k * T * B",
            [{"symbol": "N", "description": "noise power", "unit": "W"},
             {"symbol": "k", "description": "Boltzmann constant", "unit": "J/K"},
             {"symbol": "T", "description": "system noise temperature", "unit": "K"},
             {"symbol": "B", "description": "detection bandwidth", "unit": "Hz"}],
            "standard thermal-noise relation (communications texts)",
            "matched, linear receiver at physical temperature T",
            ["noise figure and interference add on top of the thermal "
             "floor and must be budgeted explicitly"],
            "rf_wireless", output_symbol="N"),
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
        _eq("AC-002", "Wave speed relation",
            "c = f * lambda",
            [{"symbol": "c", "description": "sound speed in medium", "unit": "m/s"},
             {"symbol": "f", "description": "frequency", "unit": "Hz"},
             {"symbol": "lambda", "description": "wavelength", "unit": "m"}],
            "standard wave relation (acoustics texts)",
            "non-dispersive propagation in the medium of interest",
            ["sound speed is medium- and temperature-dependent — source "
             "the value for the actual medium"],
            "acoustic", output_symbol="lambda"),
        _eq("AC-003", "Exponential attenuation",
            "A = A0 * exp(-alpha * d)",
            [{"symbol": "A", "description": "amplitude at depth d", "unit": "-"},
             {"symbol": "A0", "description": "initial amplitude", "unit": "-"},
             {"symbol": "alpha", "description": "attenuation coefficient", "unit": "1/m"},
             {"symbol": "d", "description": "propagation depth", "unit": "m"}],
            "standard one-dimensional attenuation model (ultrasonics "
            "texts)",
            "homogeneous lossy medium; single frequency",
            ["alpha is frequency- and medium-dependent; two-way path "
             "doubles the exponent"],
            "acoustic", output_symbol="A"),
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
        _eq("MRI-003", "Signal averaging (SNR vs averages)",
            "SNR = SNR_1 * sqrt(N_avg)",
            [{"symbol": "SNR", "description": "signal-to-noise after averaging", "unit": "-"},
             {"symbol": "SNR_1", "description": "signal-to-noise of one acquisition", "unit": "-"},
             {"symbol": "N_avg", "description": "number of averaged acquisitions", "unit": "-"}],
            "standard averaging relation (MRI physics texts)",
            "independent noise across repetitions; stationary sample",
            ["acquisition time grows linearly with N_avg — the trade must "
             "be budgeted, not ignored"],
            "mri_nmr", output_symbol="SNR"),
        _eq("MRI-002", "Faraday induction",
            "emf = -dPhi/dt",
            [{"symbol": "emf", "description": "induced electromotive force", "unit": "V"},
             {"symbol": "Phi", "description": "magnetic flux through coil", "unit": "Wb"}],
            "Faraday's law of induction (standard EM relation)",
            "quasi-static regime; coil coupling to the sample's "
            "transverse magnetization",
            ["signal magnitude requires the coil sensitivity profile — "
             "characterize, do not assume"],
            "mri_nmr", output_symbol="emf"),
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
        _eq("ENZ-002", "First-order activity decay",
            "A = A0 * exp(-k_d * t)",
            [{"symbol": "A", "description": "residual activity", "unit": "-"},
             {"symbol": "A0", "description": "initial activity", "unit": "-"},
             {"symbol": "k_d", "description": "decay rate constant", "unit": "1/s"},
             {"symbol": "t", "description": "elapsed time", "unit": "s"}],
            "standard first-order decay model (stability kinetics)",
            "constant environment; single degradation pathway",
            ["k_d must be measured in the target fluid; storage and "
             "operating profiles differ"],
            "enzyme_biocatalytic", output_symbol="A"),
        _eq("ENZ-003", "Arrhenius temperature dependence",
            "k = A_factor * exp(-Ea / (R * T))",
            [{"symbol": "k", "description": "rate constant", "unit": "1/s"},
             {"symbol": "A_factor", "description": "pre-exponential factor", "unit": "1/s"},
             {"symbol": "Ea", "description": "activation energy", "unit": "J/mol"},
             {"symbol": "R", "description": "gas constant", "unit": "J/(mol.K)"},
             {"symbol": "T", "description": "absolute temperature", "unit": "K"}],
            "standard Arrhenius relation (physical chemistry texts)",
            "single activated process within the temperature window",
            ["Ea and A_factor are material-specific and must be fitted "
             "from measurements, never quoted from a different system"],
            "enzyme_biocatalytic", output_symbol="k"),
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
        _eq("BIO-002", "Exponential population dynamics",
            "N = N0 * exp(r * t)",
            [{"symbol": "N", "description": "population size", "unit": "-"},
             {"symbol": "N0", "description": "initial population", "unit": "-"},
             {"symbol": "r", "description": "net growth rate", "unit": "1/s"},
             {"symbol": "t", "description": "elapsed time", "unit": "s"}],
            "standard exponential growth/decay model (population "
            "dynamics texts)",
            "unlimited substrate; constant net rate over the window",
            ["kill kinetics on an immobilized surface are not "
             "well-mixed growth — re-measure before quantitative use"],
            "phage_microbio", output_symbol="N"),
        _eq("BIO-003", "Surface-limited adsorption kinetics",
            "dN_infected/dt = k_ads * N_phage * N_bacteria",
            [{"symbol": "dN_infected/dt", "description": "infection rate", "unit": "1/s"},
             {"symbol": "k_ads", "description": "adsorption rate constant", "unit": "m^3/s"},
             {"symbol": "N_phage", "description": "free phage count", "unit": "-"},
             {"symbol": "N_bacteria", "description": "exposed bacterial count", "unit": "-"}],
            "standard mass-action adsorption form (phage biology texts)",
            "well-mixed suspension; constant k_ads",
            ["surface-immobilized phage dosing is not well-mixed — use "
             "contact-area density instead (MODEL_DERIVED adaptation)",
             "k_ads is strain- and environment-specific"],
            "phage_microbio", output_symbol="dN_infected/dt"),
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
        _eq("MEC-002", "Section bending stress",
            "sigma = M * c / I",
            [{"symbol": "sigma", "description": "bending stress at outer fiber", "unit": "Pa"},
             {"symbol": "M", "description": "bending moment", "unit": "N.m"},
             {"symbol": "c", "description": "distance to outer fiber", "unit": "m"},
             {"symbol": "I", "description": "area moment of inertia", "unit": "m^4"}],
            "standard elastic-beam relation (mechanics of materials "
            "texts)",
            "linear-elastic material; small deflection; prismatic section",
            ["stress concentrators multiply local stress above the nominal "
             "value — geometry factors must be applied from the actual "
             "design"],
            "mechanical_structural", output_symbol="sigma"),
        _eq("MEC-003", "Hooke's law (linear elasticity)",
            "sigma = E * epsilon",
            [{"symbol": "sigma", "description": "uniaxial stress", "unit": "Pa"},
             {"symbol": "E", "description": "Young's modulus", "unit": "Pa"},
             {"symbol": "epsilon", "description": "uniaxial strain", "unit": "-"}],
            "standard linear-elastic constitutive relation (mechanics "
            "texts)",
            "below proportional limit; isothermal",
            ["superelastic members (e.g. nitinol) do not follow linear "
             "elasticity through transformation — use their measured "
             "plateau relations instead"],
            "mechanical_structural", output_symbol="sigma"),
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
        _eq("TH-002", "Convective heat transfer (Newton's law of cooling)",
            "q = h * A * dT",
            [{"symbol": "q", "description": "heat flow", "unit": "W"},
             {"symbol": "h", "description": "convection coefficient", "unit": "W/(m^2.K)"},
             {"symbol": "A", "description": "wetted area", "unit": "m^2"},
             {"symbol": "dT", "description": "surface-to-fluid temperature difference", "unit": "K"}],
            "standard convective transfer relation (heat-transfer texts)",
            "steady state; h characterized for the actual flow geometry",
            ["h correlations are geometry- and regime-specific; using a "
             "correlation outside its validated range is forbidden"],
            "thermal", output_symbol="q"),
        _eq("TH-003", "Series thermal resistance",
            "R_total = sum(L_i / (k_i * A_i))",
            [{"symbol": "R_total", "description": "total thermal resistance", "unit": "K/W"},
             {"symbol": "L_i", "description": "layer thickness", "unit": "m"},
             {"symbol": "k_i", "description": "layer conductivity", "unit": "W/(m.K)"},
             {"symbol": "A_i", "description": "layer cross-section area", "unit": "m^2"}],
            "standard series-resistance network (heat-transfer texts)",
            "one-dimensional steady conduction through layers",
            ["interface contact resistances dominate at small scale and "
             "must be measured, not assumed zero"],
            "thermal", output_symbol="R_total"),
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
        _eq("ML-002", "Bayes' theorem (posterior inference)",
            "P(y|x) = P(x|y) * P(y) / P(x)",
            [{"symbol": "P(y|x)", "description": "posterior probability",
              "unit": "-", "concepts": ["posterior_probability"]},
             {"symbol": "P(x|y)", "description": "likelihood", "unit": "-",
              "concepts": ["posterior_probability", "training_data"]},
             {"symbol": "P(y)", "description": "prior probability", "unit": "-",
              "concepts": ["posterior_probability"]},
             {"symbol": "P(x)", "description": "evidence (marginal)", "unit": "-",
              "concepts": ["posterior_probability"]}],
            "Bayes' theorem (standard probability theory)",
            "probability model correctly specified; priors explicit",
            ["priors and likelihoods are MODEL_DERIVED until validated on "
             "deployment data"],
            "ml_data", output_symbol="P(y|x)"),
        _eq("ML-003", "Empirical risk",
            "R_emp = sum(loss(f(x_i), y_i)) / n",
            [{"symbol": "R_emp", "description": "empirical risk", "unit": "-",
              "concepts": ["risk_error"]},
             {"symbol": "n", "description": "sample count", "unit": "-",
              "concepts": ["training_data"]},
             {"symbol": "loss", "description": "loss function value", "unit": "-",
              "concepts": ["risk_error"]},
             {"symbol": "f(x_i)", "description": "prediction on sample i",
              "unit": "-", "concepts": ["learned_model", "training_data"]},
             {"symbol": "y_i", "description": "true label of sample i",
              "unit": "-", "concepts": ["label_outcome"]}],
            "standard empirical-risk quantity (statistical learning "
            "theory texts)",
            "samples independent and representative of the deployment "
            "distribution",
            ["empirical risk on a non-representative sample says nothing "
             "about deployment risk (distribution shift)"],
            "ml_data", output_symbol="R_emp"),
        _eq("ML-001", "Expected utility of a decision rule",
            "EU = sum_y P(y | x) * U(a(x), y)",
            [{"symbol": "EU", "description": "expected utility", "unit": "-",
              "concepts": ["utility_preference"]},
             {"symbol": "P(y|x)", "description": "posterior predictive",
              "unit": "-", "concepts": ["posterior_probability"]},
             {"symbol": "U", "description": "utility of action under truth",
              "unit": "-", "concepts": ["utility_preference"]}],
            "standard Bayesian decision theory (decision-theory texts)",
            "utility table fully specified; probabilities calibrated",
            ["utility weights are BUYER_DEFINED/MODEL_DERIVED, never measured"],
            "ml_data", output_symbol="EU"),
    ],
    "energy_harvesting": [
        _eq("ENH-001", "Seebeck effect (thermoelectric voltage)",
            "V = S_diff * dT",
            [{"symbol": "V", "description": "open-circuit thermoelectric voltage", "unit": "V"},
             {"symbol": "S_diff", "description": "differential Seebeck coefficient of the couple", "unit": "V/K"},
             {"symbol": "dT", "description": "temperature difference across the couple", "unit": "K"}],
            "standard thermoelectric relation (thermoelectricity texts)",
            "couple materials characterized; maintained temperature "
            "difference across the junctions",
            ["S_diff is material- and temperature-dependent — source the "
             "value for the actual couple",
             "output scales with the MAINTAINED difference, not with "
             "ambient temperature alone"],
            "energy_harvesting", output_symbol="V"),
        _eq("ENH-002", "Piezoelectric constitutive relation (charge form)",
            "D = d_T * T_stress + eps_T * E",
            [{"symbol": "D", "description": "electric displacement", "unit": "C/m^2"},
             {"symbol": "d_T", "description": "piezoelectric charge coefficient", "unit": "C/N"},
             {"symbol": "T_stress", "description": "mechanical stress", "unit": "Pa"},
             {"symbol": "eps_T", "description": "permittivity at constant stress", "unit": "F/m"},
             {"symbol": "E", "description": "electric field", "unit": "V/m"}],
            "standard linear piezoelectric constitutive relation (IEEE "
            "standard on piezoelectricity)",
            "small-signal linear regime below depoling limits",
            ["coupling coefficients are frequency-, load- and "
             "temperature-dependent; quoted values are not design values "
             "until measured in situ"],
            "energy_harvesting", output_symbol="D"),
        _eq("ENH-003", "Maximum power transfer to a load",
            "P_max = V_oc^2 / (4 * R_int)",
            [{"symbol": "P_max", "description": "maximum extractable power", "unit": "W"},
             {"symbol": "V_oc", "description": "open-circuit source voltage", "unit": "V"},
             {"symbol": "R_int", "description": "internal (source) resistance", "unit": "ohm"}],
            "standard maximum-power-transfer result (circuit theory "
            "texts)",
            "linear Thevenin-equivalent source; matched load",
            ["real conditioning chains never achieve the theoretical "
             "maximum — measure the achieved fraction"],
            "energy_harvesting", output_symbol="P_max"),
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


def _token_overlap(text_lower: str, phrases: List[str]) -> List[str]:
    """Exact substring matching of phrases in text — returns the phrases
    that appear. No fuzzy matching (Art. II)."""
    return [p for p in phrases if p and p.lower() in text_lower]


# --------------------------------------------------------------------------
# E21-B: concept grounding for variable engagement
# --------------------------------------------------------------------------
# The measured R-05 defect (BENCH_09): the invention "on-device temporal
# model learns the patient baseline and flags deviation earlier than
# fixed thresholds" engages the ml_data equations' variables in every
# engineering sense — it IS a learning/decision system — yet the surface
# matcher found zero engagements because variable DESCRIPTIONS share no
# 5+ letter words with the mechanism text. The equations were retained
# as CONDITIONAL with empty engaged_variables: structurally present,
# semantically unjustified.
#
# CONCEPT_GROUNDING closes that gap the honest way: each concept names
# an engineering ROLE a mechanism can assert ("a learned model performs
# inference", "data is consumed to adapt the model", ...). Variables
# DECLARE their concepts (the "concepts" field — auditable knowledge,
# like units); mechanism text ASSERTS concepts via the term lists below
# (the engine's own mechanism-language vocabulary, derived from the
# domain registry and the equation library's own descriptions). A
# variable is engaged only when the mechanism asserts one of ITS
# concepts — never by word coincidence across unrelated texts.
CONCEPT_GROUNDING: Dict[str, Dict[str, Any]] = {
    "learned_model": {
        "terms": ["model", "learner", "classifier", "detector",
                  "predictor", "network", "algorithm", "learns",
                  "learned", "learning", "inference", "adaptive",
                  "anomaly detector", "temporal model"],
        "grounds": "a learned or algorithmic model performs inference"},
    "training_data": {
        "terms": ["sample", "data", "training", "dataset",
                  "observation", "time-series", "waveform", "baseline",
                  "cohort", "examples", "patient baseline"],
        "grounds": "data is consumed to estimate or adapt the model"},
    "label_outcome": {
        "terms": ["label", "labels", "ground truth", "true label",
                  "annotated", "outcome class", "gold standard"],
        "grounds": "supervised labels or ground-truth outcomes exist"},
    "decision_rule": {
        "terms": ["threshold", "thresholds", "decision", "rule",
                  "policy", "flags", "flagging", "alarm", "trigger",
                  "cutoff", "criterion"],
        "grounds": "a decision rule acts on the model's output"},
    "posterior_probability": {
        "terms": ["posterior", "prior", "likelihood", "probability",
                  "probabilistic", "bayesian", "confidence"],
        "grounds": "uncertainty is represented as a probability"},
    "utility_preference": {
        "terms": ["utility", "cost", "benefit", "preference",
                  "trade-off", "penalty", "reward"],
        "grounds": "actions are scored by a utility/cost preference"},
    "risk_error": {
        "terms": ["risk", "error rate", "loss", "false positive",
                  "false negative", "generalization", "accuracy",
                  "false-alarm"],
        "grounds": "generalization error or decision risk is the "
                   "quantity of interest"},
}


def assert_concepts(text: str) -> Dict[str, List[str]]:
    """Concepts ASSERTED by a mechanism/invention text: {concept:
    [matched terms]}. Deterministic; every assertion carries evidence."""
    blob = str(text or "").lower()
    out: Dict[str, List[str]] = {}
    for concept, spec in CONCEPT_GROUNDING.items():
        hits = [t for t in spec["terms"] if t in blob]
        if hits:
            out[concept] = hits
    return out


def _variable_concepts(var: Dict[str, Any]) -> List[str]:
    """A variable's declared engineering concepts. Variables with an
    explicit 'concepts' field use it (auditable knowledge); otherwise
    concepts resolve from the variable's own description terms."""
    declared = var.get("concepts")
    if declared:
        return list(declared)
    desc = str(var.get("description", "")).lower()
    return [c for c, spec in CONCEPT_GROUNDING.items()
            if any(t in desc for t in spec["terms"])]


def evaluate_equation_applicability(eq: Equation, invention_text: str,
                                    constraint_text: str) -> Dict[str, Any]:
    """CEO A4: prove WHY each equation is applicable to THE ACTUAL INVENTION,
    and REJECT the equation when its domain assumptions do not hold.

    Mechanical, auditable judgment (never a narrative claim):
      APPLICABLE  — the invention text concretely engages the equation's
                    variables AND no stated constraint contradicts an
                    assumption.
      CONDITIONAL — the domain justifies the model but the invention text
                    does not yet engage its variables; retained with an
                    explicit list of what must be verified before use.
      REJECTED    — a stated constraint/mechanism contradicts an assumption;
                    the equation is EXCLUDED from the governing model and
                    recorded with its rejection reason (never silently
                    dropped, never silently kept — Art. XVII).
    """
    mech_part = invention_text.lower()
    # E21-B: concept-grounded engagement. Variables DECLARE engineering
    # concepts; the mechanism ASSERTS concepts; a variable is engaged
    # only when the mechanism asserts one of ITS concepts, with the
    # matching terms recorded as evidence. The legacy description-word
    # path is retained as a secondary signal (domains without declared
    # concepts still engage via their own vocabulary).
    mech_concepts = assert_concepts(invention_text)
    var_engagements = []
    engagement_evidence = []
    for var in eq["variables"]:
        v_concepts = _variable_concepts(var)
        shared = [c for c in v_concepts if c in mech_concepts]
        if shared:
            var_engagements.append(var["symbol"])
            engagement_evidence.append({
                "symbol": var["symbol"],
                "shared_concepts": shared,
                "mechanism_terms": sorted(
                    {t for c in shared for t in mech_concepts[c]}),
                "variable_concepts": v_concepts,
                "grounding": "E21-B concept grounding (declared variable "
                             "concepts matched against mechanism-asserted "
                             "concepts)"})
            continue
        words = [w for w in var["description"].lower().split()
                 if len(w) >= 5]
        if any(w in mech_part for w in words):
            var_engagements.append(var["symbol"])
            engagement_evidence.append({
                "symbol": var["symbol"],
                "shared_concepts": [],
                "matched_description_words":
                    [w for w in words if w in mech_part],
                "grounding": "legacy description-word match (no declared "
                             "concepts on this variable)"})
    name_engagement = _token_overlap(
        mech_part,
        [w for w in eq["name"].lower().split() if len(w) >= 6])
    assumptions = list(eq.get("assumptions", []))
    # contradiction scan: a stated constraint that negates an assumption term
    constraint_lower = constraint_text.lower()
    assumption_violations = []
    for a in assumptions:
        for term in _negation_conflict(a, constraint_lower):
            assumption_violations.append(
                {"assumption": a, "conflicting_constraint_term": term})
    if assumption_violations:
        verdict = "REJECTED"
        reason = ("stated constraint/mechanism conflicts with a model "
                  "assumption: " + "; ".join(
                      v["assumption"] for v in assumption_violations))
    elif var_engagements:
        verdict = "APPLICABLE"
        reason = ("invention mechanism engages the model variables: "
                  + ", ".join(var_engagements))
    else:
        verdict = "CONDITIONAL"
        reason = ("domain template justifies this relation for the domain, "
                  "but the invention text does not yet engage its "
                  "variables; applicability must be confirmed by the first "
                  "characterization")
    return {
        "equation_id": eq["equation_id"],
        "name": eq["name"],
        "verdict": verdict,
        "reason": reason,
        "engaged_variables": var_engagements,
        "engagement_evidence": engagement_evidence,
        "mechanism_asserted_concepts": mech_concepts,
        "name_signal_overlap": name_engagement,
        "assumption_check": {
            "assumptions": assumptions,
            "violations": assumption_violations,
            "epistemic_class": "MODEL_DERIVED (mechanically evaluated, "
                               "recorded for audit)"},
        "model_assumptions": assumptions,
        "model_applicability": eq["applicability"]["condition"],
    }


def _negation_conflict(assumption: str, constraint_lower: str
                       ) -> List[str]:
    """Detect a stated constraint that explicitly negates a key term of an
    assumption (e.g. assumption 'laminar regime' vs constraint 'flow is
    turbulent'). Exact term matching only — no fuzzy inference (Art. II)."""
    conflicts = []
    for term in ("laminar", "newtonian", "steady state", "single substrate",
                 "homogeneous", "rigid", "circular", "far field",
                 "single-phase", "fully developed"):
        if term in assumption.lower():
            negations = (f"non-{term}", f"not {term}", f"no {term}",
                         f"turbulent" if term == "laminar" else None,
                         f"nonnewtonian" if term == "newtonian" else None)
            for neg in negations:
                if neg and neg in constraint_lower:
                    conflicts.append(neg)
    return conflicts


def select_equations(spec: Dict[str, Any], domain: str,
                     ) -> Dict[str, Any]:
    """Attach domain equations to the invention WITH per-equation
    applicability proof (CEO A4). Selected equations are APPLICABLE or
    CONDITIONAL; REJECTED equations are excluded from the governing model
    and recorded in `rejected_equations` with reasons. Selection is
    MODEL_DERIVED and recorded as such."""
    eqs = equations_for_domain(domain)
    mech = (spec.get("mechanism") or {}).get("value") or {}
    problem = (spec.get("problem") or {}).get("value") or {}
    invention_text = " ".join(str(mech.get(k, "")) for k in
                              ("mechanism", "intervention",
                               "expected_effect"))
    constraint_text = " ".join(str(problem.get(k, "")) for k in
                               ("constraint", "failure", "device"))
    if not eqs:
        return {"value": [],
                "rejected_equations": [],
                "epistemic_class": "UNKNOWN",
                "origin_stage": "EQUATION_LIBRARY",
                "evidence_ids": [],
                "note": f"no equation library for domain {domain!r}; "
                        "no equations emitted (never sprinkled)"}
    selected, rejected = [], []
    for eq in eqs:
        judgment = evaluate_equation_applicability(
            eq, invention_text, constraint_text)
        entry = {
            "equation": eq,
            "selection_rationale": {
                "epistemic_class": "MODEL_DERIVED",
                "verdict": judgment["verdict"],
                "reason": judgment["reason"],
                "engaged_variables": judgment["engaged_variables"],
                "engagement_evidence": judgment["engagement_evidence"],
                "mechanism_asserted_concepts":
                    judgment["mechanism_asserted_concepts"],
                "assumption_check": judgment["assumption_check"],
                "mechanism_mentions": [
                    k for k in eq["variables"]
                    if k["description"].lower().split()[0]
                    in invention_text.lower()],
            },
        }
        if judgment["verdict"] == "REJECTED":
            rejected.append({
                "equation_id": eq["equation_id"],
                "name": eq["name"],
                "expression": eq["expression"],
                "rejection_reason": judgment["reason"],
                "assumption_violations":
                    judgment["assumption_check"]["violations"],
                "epistemic_class": "MODEL_DERIVED (excluded from governing "
                                   "model; recorded for transparency)"})
        else:
            selected.append(entry)
    return {
        "value": selected,
        "rejected_equations": rejected,
        "epistemic_class": "EXTERNAL_PRECEDENT",
        "origin_stage": "EQUATION_LIBRARY",
        "evidence_ids": [],
        "note": ("equations are textbook/standard EXTERNAL_PRECEDENT "
                 "relations selected by domain template; each carries an "
                 "invention-specific applicability judgment (A4); numeric "
                 "values are emitted only with fully-sourced inputs"),
    }
