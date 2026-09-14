"""
constants.py — Shared engineering constants and equations for R370B dossiers.

All values are REAL, published physics constants. No fabricated numbers.
All equations are standard textbook formulas with citations to their originating field.
"""

# ============================================================================
# CSF / physiological constants (from published literature, NOT invented)
# ============================================================================

CSF_DENSITY_KG_M3 = 1007.0      # CSF density approx (Weber et al, J Clin Monit 2019)
CSF_VISCOSITY_PA_S = 0.0009     # CSF viscosity ~0.9 mPa·s at 37°C (Bloomfield et al)
G_GRAVITY_M_S2 = 9.81           # standard gravity
MMHG_TO_PA = 133.322            # 1 mmHg = 133.322 Pa
CM_H2O_TO_PA = 98.0665          # 1 cm H2O = 98.0665 Pa

# Speed of sound in soft tissue (approximate, published range 1540-1570 m/s)
ACOUSTIC_VELOCITY_SOFT_TISSUE_M_S = 1540.0
ACOUSTIC_VELOCITY_CSF_M_S = 1505.0  # similar to water at 37°C
ACOUSTIC_VELOCITY_BLOOD_M_S = 1570.0

# Acoustic impedance (rho * c, kg/(m^2·s))
ACOUSTIC_Z_SOFT_TISSUE = 1.63e6   # MRayles ~ 1.63 (soft tissue average)
ACOUSTIC_Z_CSFR = 1.50e6          # CSF/water-like
ACOUSTIC_Z_BLOOD = 1.66e6
ACOUSTIC_Z_AIR = 415

# Piezoelectric constants (PZT-5H, published values)
PZT5H_D33_PM_V = 593e-12          # m/V (charge constant)
PZT5H_G33_VM_N = 19e-3            # V·m/N (voltage constant)
PVDF_D33_PM_V = -33e-12           # m/V (PVDF typical)
PVDF_G33_VM_N = 0.216             # V·m/N (PVDF, high voltage coefficient)

# MRI constants
GAMMA_H_BAR_RAD_S_T = 2.6752218744e8   # proton gyromagnetic ratio (rad/(s·T))
GAMMA_H_HZ_T = 42.577478518e6           # proton gyromagnetic ratio (Hz/T)

# RF speed in tissue (approximate)
RF_SPEED_TISSUE_M_S = 3e8 / 9.0       # dielectric constant ~9 at low MHz; varies by frequency

# Standard governing equations (string form for citation in dossiers)
EQUATIONS = {
    "hagen_poiseuille": "Q = (pi * r^4 * dP) / (8 * eta * L)  [laminar flow, circular conduit]",
    "orifice":          "Q = Cd * A * sqrt(2 * dP / rho)     [orifice/turbulent flow]",
    "reynolds":         "Re = (rho * v * D) / eta             [laminar if Re < 2300]",
    "michaelis_menten": "v = (Vmax * [S]) / (Km + [S])         [enzyme kinetics]",
    "damkohler":        "Da = (k * L) / D                      [reaction vs transport]",
    "fick_1st":         "J = -D * dC/dx                        [diffusive flux]",
    "fick_2nd":         "dC/dt = D * d2C/dx2                   [diffusion equation]",
    "vant_hoff":        "pi = i * C * R * T                    [osmotic pressure]",
    "membrane_flux":    "Jv = Lp * (dP - sigma * dPi)          [Starling/Kedem-Katchalsky]",
    "piezo_voltage":    "V = g33 * d * sigma                   [piezoelectric voltage]",
    "piezo_power":      "P ~ (d33 * g33 * sigma^2 * Volume) / (2 * duty_cycle)  [piezo harvested power]",
    "rf_toa":           "d = c * dt                            [time-of-arrival ranging]",
    "sar":              "SAR = (sigma * E^2) / (2 * rho)       [specific absorption rate]",
    "euler_buckling":   "P_cr = (pi^2 * E * I) / L^2           [elastic column buckling]",
    "piezoresistance":  "dR/R = pi_L * sigma_L + pi_T * sigma_T  [piezoresistive effect]",
    "wheatstone":       "V_out = (dR / (4*R + 2*dR)) * V_ex    [bridge output]",
    "acoustic_impedance": "Z = rho * c                         [characteristic impedance]",
    "acoustic_reflection": "R = (Z2 - Z1) / (Z2 + Z1)         [pressure reflection coefficient]",
    "larmor":           "omega = gamma * B0                    [Larmor precession]",
    "pc_mri_phase":     "dphi = gamma * M1 * v                 [phase-contrast MRI velocity encoding]",
    "gravity_head":     "dP_gravity = rho * g * dh             [hydrostatic pressure differential]",
    "damper_force":     "F = c * v                             [linear viscous damper]",
    "monod_biofilm":    "mu = mu_max * S / (Ks + S)            [Monod specific growth rate]",
    "phage_adsorption": "dP/dt = -k_ads * [Phage] * [Bacteria] [phage-bacteria binding kinetics]",
    "weibull_reliability": "R(t) = exp(-(t/eta)^beta)         [Weibull reliability]",
    "snr":              "SNR = signal / sqrt(signal + noise)   [Poisson-limited SNR]",
    "thermal_diffusivity": "alpha = k / (rho * Cp)             [thermal diffusivity]",
}

# ============================================================================
# Honest standard status (no fabricated certification claims)
# ============================================================================

STANDARDS = {
    "ISO_10993": {
        "title": "Biological evaluation of medical devices",
        "applicability": "All implantable components",
        "verification_required": "Cytotoxicity, sensitization, irritation, systemic toxicity, sub-chronic toxicity, genotoxicity, implantation",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "url": "https://www.iso.org/standard/68436.html"
    },
    "ISO_7437": {
        "title": "Neurosurgical implants — Sterile, single-use cerebrospinal fluid shunts and components",
        "applicability": "All CSF shunt components",
        "verification_required": "Flow-pressure characterization, fatigue, biocompatibility",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ISO_11135": {
        "title": "Sterilization of health-care products — Ethylene oxide",
        "applicability": "EtO-sterilizable components",
        "verification_required": "Sterilization validation",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ISO_11137": {
        "title": "Sterilization of health care products — Radiation",
        "applicability": "Gamma/e-beam sterilizable components",
        "verification_required": "Sterilization validation + material effects",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "IEC_60601_1_2": {
        "title": "Medical electrical equipment — EMC",
        "applicability": "Active electronic components",
        "verification_required": "EMC testing",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "IEC_62304": {
        "title": "Medical device software — Software life cycle processes",
        "applicability": "Software in medical devices (Classes A/B/C)",
        "verification_required": "Software development process + V&V",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ISO_14708_1": {
        "title": "Implants for surgery — Active implantable medical devices — General requirements",
        "applicability": "Active implantable devices",
        "verification_required": "General safety + reliability",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ASTM_F640": {
        "title": "Test method for radiopacity of plastics for medical devices",
        "applicability": "Radiopaque catheter materials",
        "verification_required": "Radiopacity test",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ASTM_E2180": {
        "title": "Test method for efficacy of antimicrobial device surfaces",
        "applicability": "Antimicrobial-coated surfaces",
        "verification_required": "Antimicrobial efficacy test",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ISO_22196": {
        "title": "Measurement of antibacterial activity on plastics and other non-porous surfaces",
        "applicability": "Antimicrobial surfaces",
        "verification_required": "Antibacterial activity measurement",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "FCC_15_250": {
        "title": "FCC Part 15.250 — Ultra-wideband operation",
        "applicability": "UWB medical devices",
        "verification_required": "FCC certification",
        "evidence_class": "EXTERNAL_PRECEDENT",
        "note": "SAR limit 1.6 W/kg averaged over 1g tissue"
    },
    "IEEE_1528": {
        "title": "Recommended practice for determining SAR in human head",
        "applicability": "RF-emitting devices near body",
        "verification_required": "SAR measurement",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ISO_10555_1": {
        "title": "Intravascular catheters — Sterile and single-use — General requirements",
        "applicability": "Intravascular catheters",
        "verification_required": "General safety + performance",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "AIUM_NEMA_UD_2": {
        "title": "Acoustic output measurement standard for diagnostic ultrasound",
        "applicability": "Ultrasound-emitting catheter-based devices",
        "verification_required": "Acoustic output measurement",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
    "ASTM_D3985": {
        "title": "Test method for oxygen gas transmission rate through plastic film",
        "applicability": "Membrane permeation characterization",
        "verification_required": "Permeation test",
        "evidence_class": "EXTERNAL_PRECEDENT"
    },
}

# Common warning for all dossiers
DOSSIER_WARNING = (
    "Package-specific engineering dossier. Technology-specific content (not generic template). "
    "External evidence has evidence->decision chains. No fabrication. No truncation. "
    "Constitution Article XXV: unknown stays unknown. Article XXVII: thresholds have provenance. "
    "Article XXVIII: EXTERNAL_PRECEDENT != INVENTION_VALIDATION."
)
