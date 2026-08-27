"""
r370b_engineering_data.py — Package-specific engineering cores for 12 generic dossiers.

Each package gets REAL domain engineering (governing equations, external precedents,
failure modes, build plan) — NOT a generic template. UNKNOWN stays UNKNOWN.

Constitutional compliance:
- Article I:  evidence precedes assertion (no fabricated numbers)
- Article VI: never manufacture provenance (real URLs only)
- Article XXV:  unknown stays unknown
- Article XXVII: thresholds have provenance (FDA/ISO/ASTM cites)
- Article XXVIII: EXTERNAL_PRECEDENT != INVENTION_VALIDATION

Engineering domains per package (per CEO directive):
  P-02  → CFD / fluid dynamics / valve mechanics
  P-04  → enzyme kinetics / molecular transport / clearance / catheter delivery
  P-07  → pressure-flow / valve mechanics / failure modes
  P-11  → microbiology / anti-biofouling / surface science
  P-24  → hydraulic valve physics / pressure-flow / proportional control
  P-26  → osmotic membrane transport / membrane mechanics / fouling
  P-15-R1 → vibration mechanics / energy harvesting / fatigue
  P-21-R1 → RF / localization / tissue propagation / SAR
  P-22-R1 → catheter mechanics / buckling / hydraulic actuation / tissue interaction
  P-27-R1 → tubing mechanics / kink resistance / fatigue / patency
  P-28  → acoustics / ultrasound / impedance / signal detection
  P-29  → MRI/NMR physics / flow quantification / miniaturization
"""

# ============================================================================
# Shared engineering constants (REAL physics, not invented)
# ============================================================================

# CSF physical properties (from published physiology literature)
CSF_DENSITY_KG_M3 = 1007.0   # approximate CSF density (Weber et al, J Clin Monit)
CSF_VISCOSITY_PA_S = 0.0009  # ~0.9 mPa·s at 37°C (Bloomfield et al)
G_GRAVITY_M_S2 = 9.81
MMHG_TO_PA = 133.322

# Standard governing equations for citation (string form, not numeric claims)
EQUATIONS = {
    "hagen_poiseuille": "Q = (pi * r^4 * dP) / (8 * eta * L)  [laminar flow through circular conduit]",
    "orifice":          "Q = Cd * A * sqrt(2 * dP / rho)     [turbulent/orifice flow]",
    "reynolds":         "Re = (rho * v * D) / eta             [laminar if Re < 2300]",
    "michaelis_menten": "v = (Vmax * [S]) / (Km + [S])         [enzyme kinetics]",
    "damkohler":        "Da = (k * L) / D                      [reaction vs transport]",
    "fick_1st":         "J = -D * dC/dx                        [diffusive flux]",
    "vant_hoff":        "pi = i * C * R * T                    [osmotic pressure]",
    "membrane_flux":    "Jv = Lp * (dP - sigma * dPi)          [Starling/Kedem-Katchalsky]",
    "piezo_voltage":    "V = g33 * d * sigma                   [piezoelectric voltage]",
    "piezo_power":      "P ~ (d33 * g33 * sigma^2 * Volume) / (2 * duty_cycle)",
    "rf_toa":           "d = c * dt                            [time-of-arrival ranging]",
    "sar":              "SAR = (sigma * E^2) / (2 * rho)       [specific absorption rate]",
    "euler_buckling":   "P_cr = (pi^2 * E * I) / L^2           [elastic column buckling]",
    "piezoresistance":  "dR/R = pi_L * sigma_L + pi_T * sigma_T",
    "wheatstone":       "V_out = (dR / (4*R + 2*dR)) * V_ex    [bridge output]",
    "acoustic_impedance": "Z = rho * c                         [characteristic impedance]",
    "acoustic_reflection": "R = (Z2 - Z1) / (Z2 + Z1)         [pressure reflection coefficient]",
    "larmor":           "omega = gamma * B0                    [Larmor precession]",
    "pc_mri_phase":     "dphi = gamma * M1 * v                 [phase-contrast MRI velocity encoding]",
    "gravity_head":     "dP_gravity = rho * g * dh             [hydrostatic pressure differential]",
    "damper_force":     "F = c * v                             [linear viscous damper]",
    "monod_biofilm":    "mu = mu_max * S / (Ks + S)            [biofilm specific growth rate]",
    "phage_adsorption": "dP/dt = -k_ads * [Phage] * [Bacteria] [phage-bacteria binding kinetics]",
}


# ============================================================================
# P-02: Adaptive Valve Profile
# Domain: CFD / fluid dynamics / valve mechanics
# ============================================================================

def get_data():
    return p02_adaptive_valve()


def p02_adaptive_valve():
    return {
        "technology_domain": "Fluid Mechanics + Adaptive Valve Design",
        "engineering_disciplines": [
            "Computational fluid dynamics (CFD)",
            "Valve mechanics",
            "Control systems",
            "Polymer actuator engineering"
        ],
        "system_architecture": {
            "description": "CSF shunt valve whose opening pressure profile adapts to ICP trend rather than fixed cracking pressure; reduces postural pressure excursions",
            "subsystems": [
                {"id": "SS-01", "name": "Adaptive valve seat", "function": "Variable-area flow orifice whose area A(P, dP/dt) depends on pressure and pressure trend", "status": "MODELLED", "evidence_source": "R332 mechanism"},
                {"id": "SS-02", "name": "Pressure-trend sensor", "function": "Measures ICP(t) and computes dP/dt for controller input", "status": "PROPOSED", "evidence_source": "R332 mechanism"},
                {"id": "SS-03", "name": "Actuator (candidate: MEMS electrothermal or shape-memory polymer)", "function": "Adjusts valve seat area based on controller signal", "status": "PROPOSED", "evidence_source": "External precedent for MEMS valves"},
                {"id": "SS-04", "name": "Controller (P or PI)", "function": "Maps (P, dP/dt) -> actuator command to track target opening profile", "status": "MODELLED", "evidence_source": "R332 model"}
            ],
            "fluid_mechanics": {
                "flow_regime": "Laminar (CSF Re << 2300 at shunt flow rates ~0.3 mL/min in 1-1.5 mm ID catheter)",
                "pressure_range": "ICP 5-20 mmHg normal, postural transients to 40 mmHg reported",
                "key_equations": [
                    EQUATIONS["hagen_poiseuille"],
                    EQUATIONS["orifice"],
                    EQUATIONS["reynolds"]
                ],
                "critical_parameter": "Valve conductance G(P, dP/dt) = Q / dP, intentionally variable vs fixed",
                "dual_invariants": {
                    "INV-1": "P_ICP <= 20 mmHg (intracranial pressure safety; same threshold class as P-01 — MODEL_DERIVED per R332)",
                    "INV-2": "Q_drainage >= 0.05 mL/min (minimum drainage floor; prevents overdrainage-induced collapse AND underdrainage)",
                    "FALSIFICATION": "Unknown — not tested in hardware",
                    "evidence_class": "MODELLED"
                }
            }
        },
        "mechanism_architecture": {
            "physical_changes": "Valve orifice area A adapts: when dP/dt indicates postural transient (positive trend with postural change), the valve reduces conductance briefly to attenuate over-drainage; when ICP rises monotonically, conductance increases to maintain drainage.",
            "key_physics": "Variable-area orifice: Q = Cd * A(dP, dP/dt) * sqrt(2 dP / rho). The 'adaptive' component is the A(dP, dP/dt) dependence — a non-linear feedback on the orifice equation.",
            "trend_estimator": {
                "input": "ICP(t) sampled at 1-10 Hz",
                "model": "Discrete derivative dP/dt with low-pass filter (cutoff < 0.1 Hz to reject pulsatile cardiac component)",
                "prediction_horizon": "Not applicable — adaptive response is reactive, not predictive",
                "status": "MODELLED — controller architecture specified; hardware transfer function UNKNOWN"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "Variable-area hydraulic orifice with trend-feedback control. The valve is modeled as a non-linear orifice whose area A is a function of measured pressure and its time-derivative.",
                "equations": [
                    EQUATIONS["orifice"],
                    EQUATIONS["hagen_poiseuille"],
                    EQUATIONS["reynolds"],
                    "A_actuator(P, dP/dt) = A0 + k_p * (P - P0) + k_d * dP/dt   [proposed controller law, MODELLED]"
                ],
                "assumptions": [
                    "CSF is Newtonian (valid at low shear rates in shunt flow)",
                    "Flow is quasi-steady (valve response time > flow timescale)",
                    "Catheter geometry is rigid (compliance UNKNOWN)",
                    "No cavitation (validated by Re and pressure range)"
                ],
                "boundary_conditions": [
                    "Inlet: ICP in [5, 40] mmHg",
                    "Outlet: intra-abdominal pressure ~5-15 mmHg supine, lower upright",
                    "Postural head differential: 0-50 cm H2O (~0-37 mmHg)"
                ],
                "input_variables": ["ICP(t)", "postural state", "ambient pressure"],
                "output_variables": ["drainage rate Q(t)", "valve area A(t)"],
                "parameter_sensitivities": [
                    "Cd (discharge coefficient) ± 0.1 -> ±15% flow error",
                    "A_actuator gain k_p -> directly controls response amplitude",
                    "Filter cutoff frequency -> determines pulsatile rejection vs response lag"
                ],
                "failure_regimes": [
                    "Actuator saturation (max area reached) -> reverts to fixed-valve behavior",
                    "Filter lag > postural transient duration -> adaptation ineffective",
                    "Sensor noise > dP/dt signal -> controller unstable"
                ]
            },
            "critical_parameters": [
                {"name": "Cracking pressure P_crack", "value": "UNKNOWN", "unit": "mmHg", "basis": "Design choice", "evidence_class": "UNKNOWN", "verification_requirement": "Bench measurement per ISO 7437"},
                {"name": "Maximum valve area A_max", "value": "UNKNOWN", "unit": "mm^2", "basis": "Design choice", "evidence_class": "UNKNOWN", "verification_requirement": "Geometric inspection + flow bench"},
                {"name": "Response time tau_valve", "value": "UNKNOWN", "unit": "s", "basis": "Actuator-dependent", "evidence_class": "UNKNOWN", "verification_requirement": "Step response test"},
                {"name": "Controller gains k_p, k_d", "value": "UNKNOWN", "unit": "dimensionless, mm^2·s/mmHg", "basis": "Tuned via simulation", "evidence_class": "MODELLED", "verification_requirement": "Closed-loop stability test"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — see external_engineering_precedent field for FDA-cleared comparable valves (Miethke proGAV, Medtronic Strata). These establish that programmable shunt valves are manufacturable. They do NOT establish that the adaptive profile proposed here achieves clinical benefit.",
            "proposed_design": {
                "input": "ICP sensor + postural sensor (accelerometer or external tilt indicator)",
                "mechanism": "Trend-feedback controller modulates valve seat area",
                "transformation": "(P, dP/dt) -> A_actuator -> Q(P, A) -> drainage rate",
                "output": "Drainage rate that attenuates postural excursions while maintaining minimum floor",
                "component_architecture": "Pressure sensor -> controller (MCU) -> actuator -> variable valve seat -> outlet catheter"
            },
            "failure_modes": [
                {"mode": "Actuator jam", "mechanism": "Mechanical obstruction or electrical failure of actuator", "design_feature": "Valve seat becomes fixed", "evidence": "Known failure mode of programmable valves (FDA MAUDE reports exist)", "mitigation": "Fail-safe fixed-pressure mode (fallback)", "verification_test": "Induce jam, verify fallback behavior", "residual_uncertainty": "UNKNOWN whether fallback meets clinical need"},
                {"mode": "Sensor drift", "mechanism": "Long-term pressure sensor drift", "design_feature": "Controller receives biased input", "evidence": "Known for implantable pressure sensors (PMC4279503)", "mitigation": "Periodic recalibration protocol (UNKNOWN specifics)", "verification_test": "Aging study", "residual_uncertainty": "Drift magnitude in CSF environment UNKNOWN"},
                {"mode": "Postural misclassification", "mechanism": "Controller misclassifies postural transient", "design_feature": "Adaptive response inappropriate", "evidence": "MODELLED — sensitivity to filter cutoff", "mitigation": "Multi-sensor fusion (postural + pressure)", "verification_test": "Bench postural simulation", "residual_uncertainty": "Classifier accuracy UNKNOWN"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "Valve opening pressure tracks target profile within tolerance", "method": "Bench flow loop with programmable pressure source", "acceptance": "Steady-state error < 2 mmHg", "evidence_class": "PROPOSED"},
                {"id": "VER-002", "requirement": "Response time to postural step < 5 s", "method": "Step input test", "acceptance": "10-90% rise time < 5 s", "evidence_class": "PROPOSED"},
                {"id": "VER-003", "requirement": "Minimum drainage maintained during adaptation", "method": "Worst-case flow measurement", "acceptance": "Q >= 0.05 mL/min at all valid inputs", "evidence_class": "PROPOSED"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "Reduced ICP excursion vs fixed valve in patient cohort", "method": "Clinical trial (IDE required)", "acceptance": "Statistically significant reduction in ICP excursion amplitude", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Actuator technology choice (MEMS electrothermal vs shape-memory polymer vs electromagnetic) — UNKNOWN",
                "Long-term drift of pressure sensor in CSF environment — UNKNOWN",
                "Controller gains in vivo — UNKNOWN until clinical data",
                "Biocompatibility of actuator materials in CSF — UNKNOWN (ISO 10993 testing required)",
                "Battery life if active (or energy harvesting if passive) — UNKNOWN",
                "Regulatory pathway (Class II with special controls vs Class III PMA) — UNKNOWN until pre-submission to FDA"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "ICP excursions during postural changes cause patient symptoms and possible complications (R332 problem statement)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "Valve opening profile adapts to ICP trends to reduce postural pressure excursions", "evidence_class": "MODELLED", "source": "R332"},
            {"id": "DI-003", "input": "Flow regime", "value": "Laminar, Re << 2300 at typical CSF flow rates", "evidence_class": "COMPUTATIONALLY_SUPPORTED", "source": "Hagen-Poiseuille + CSF rheology literature"},
            {"id": "DI-004", "input": "Pressure range", "value": "ICP 5-20 mmHg normal, postural transients up to 40 mmHg", "evidence_class": "VERIFIED", "source": "R332 + external literature"},
            {"id": "DI-005", "input": "ICP safety threshold", "value": "P_ICP <= 20 mmHg (INV-1, MODEL_DERIVED)", "evidence_class": "MODELLED", "source": "R332 mechanism"},
            {"id": "DI-006", "input": "Minimum drainage floor", "value": "Q >= 0.05 mL/min (INV-2, MODEL_DERIVED)", "evidence_class": "MODELLED", "source": "R332 mechanism"},
            {"id": "DI-007", "input": "Biocompatibility (ISO 10993)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 series testing for valve materials (likely silicone/silicone-steel composite based on external precedent)", "applicability": "APPLICABLE"},
            {"id": "DI-008", "input": "Sterilization compatibility", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "EtO or gamma sterilization validation per ISO 11135/11137", "applicability": "APPLICABLE"},
            {"id": "DI-009", "input": "EMC", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "IEC 60601-1-2 if active components", "applicability": "APPLICABLE if active"},
            {"id": "DI-010", "input": "Response time", "value": "Target < 5 s (postural transient timescale)", "evidence_class": "MODELLED", "source": "R332 model"},
            {"id": "DI-011", "input": "Controller type", "value": "PI controller with trend feedback (proposed)", "evidence_class": "PROPOSED", "source": "R332 mechanism"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Valve seat geometry (variable-area orifice)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["A_max", "A_min", "valve seat profile", "actuator mechanism"]},
            {"id": "DO-002", "description": "Pressure sensor specification", "status": "CONCEPTUAL", "design_status": "COTS_IDENTIFIED", "note": "COTS implantable-grade pressure sensors exist (e.g., similar to Codman ICP Express)"},
            {"id": "DO-003", "description": "Controller firmware", "status": "MODELLED", "design_status": "COMPUTATIONALLY_DEFINED", "note": "Algorithm specified in R332; not production-implemented"},
            {"id": "DO-004", "description": "Actuator specification", "status": "ABSENT", "design_status": "CONCEPT_ONLY", "missing_inputs": ["Actuator technology choice", "force/displacement requirement", "power budget"]}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "Valve tracks target opening profile", "method": "Bench flow loop", "acceptance": "Steady-state error < 2 mmHg", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-002", "requirement": "Response time < 5 s to postural step", "method": "Step input test", "acceptance": "10-90% rise < 5 s", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-003", "requirement": "Minimum drainage floor maintained", "method": "Worst-case flow measurement", "acceptance": "Q >= 0.05 mL/min", "result": "NOT_TESTED", "evidence_class": "PROPOSED"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "Reduced ICP excursion vs fixed valve in patient cohort", "method": "Clinical trial (IDE required)", "acceptance": "Statistically significant reduction", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "Valve body housing", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED", "material": "UNKNOWN — likely silicone/Titanium composite (external precedent)", "supplier": "UNKNOWN", "criticality": "CRITICAL", "verification": "Bench flow + biocompatibility"},
            {"item": "02", "description": "Pressure sensor", "qty": "1", "component_type": "COTS_CANDIDATE", "source_basis": "External precedent (Codman ICP Express)", "material": "N/A (COTS)", "supplier": "UNKNOWN — to be evaluated", "criticality": "HIGH", "verification": "Calibration + drift test"},
            {"item": "03", "description": "Actuator (MEMS or shape-memory)", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED", "material": "UNKNOWN — depends on technology choice", "supplier": "UNKNOWN", "criticality": "CRITICAL", "verification": "Lifetime + force calibration"},
            {"item": "04", "description": "Microcontroller", "qty": "1", "component_type": "COTS_CANDIDATE", "source_basis": "Standard medical-grade MCU", "material": "N/A (COTS)", "supplier": "Multiple (TI, STM, NXP)", "criticality": "MEDIUM", "verification": "Software validation + EMC"}
        ],
        "materials": [
            {"component": "Valve body", "candidate_material": "Silicone elastomer", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard CSF shunt material (K062009 Miethke proGAV)", "verification_required": "ISO 10993 + mechanical fatigue", "status": "CANDIDATE"},
            {"component": "Valve seat (variable-area mechanism)", "candidate_material": "Shape-memory polymer (SMP)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Published SMP valve literature", "verification_required": "ISO 10993 + fatigue + activation temperature range", "status": "CANDIDATE — not selected"},
            {"component": "Pressure sensor diaphragm", "candidate_material": "Silicon (MEMS)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard MEMS pressure sensor material", "verification_required": "ISO 10993 + drift characterization", "status": "CANDIDATE"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Silicone injection molding", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard CSF valve manufacturing", "tolerance_implication": "±0.02 mm typical for medical-grade", "note": "Variable-area mechanism may require modified process"},
                {"process": "MEMS fabrication (if actuator is MEMS)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard MEMS foundry process", "tolerance_implication": "Sub-micron feature tolerance", "note": "Requires foundry partnership"},
                {"process": "Laser welding (housing assembly)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard implantable device assembly", "tolerance_implication": "±0.05 mm weld positioning", "note": "Hermetic seal required"}
            ],
            "status": "ENGINEERING_CANDIDATE — no process validated"
        },
        "failure_analysis": [
            {"failure_mode": "Actuator jam", "mechanism": "Mechanical obstruction or electrical failure", "design_feature_affected": "Variable-area mechanism", "evidence": "Known for programmable valves (FDA MAUDE)", "mitigation": "Fail-safe fixed-pressure fallback", "verification_test": "Jam simulation bench test", "residual_uncertainty": "UNKNOWN fallback efficacy"},
            {"failure_mode": "Pressure sensor drift", "mechanism": "Long-term offset drift", "design_feature_affected": "Controller input", "evidence": "PMC4279503 chronically implanted sensors", "mitigation": "Recalibration protocol (UNKNOWN specifics)", "verification_test": "Aging study", "residual_uncertainty": "Drift magnitude in CSF UNKNOWN"},
            {"failure_mode": "Battery depletion (if active)", "mechanism": "Energy source exhausted", "design_feature_affected": "Controller + actuator", "evidence": "Standard for active implants", "mitigation": "Low-power design + indicator", "verification_test": "Battery life test", "residual_uncertainty": "UNKNOWN battery life given duty cycle"},
            {"failure_mode": "Postural misclassification", "mechanism": "dP/dt filter misclassifies transient", "design_feature_affected": "Adaptive response", "evidence": "MODELLED sensitivity to filter cutoff", "mitigation": "Multi-sensor fusion (postural + pressure)", "verification_test": "Bench postural simulation", "residual_uncertainty": "Classifier accuracy UNKNOWN"},
            {"failure_mode": "Mechanical fatigue of valve seat", "mechanism": "Cyclic actuation causes material fatigue", "design_feature_affected": "Valve seat", "evidence": "Standard fatigue theory", "mitigation": "Material selection + lifetime derating", "verification_test": "ASTM F466 fatigue characterization", "residual_uncertainty": "Cycle count to failure UNKNOWN"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "Variable-area valve prototype (passive, no actuator)", "equipment": "Bench flow loop, Transonic flow sensor, pressure transducer", "design_work": "CAD + 3D printed valve seat", "measurement": "Q vs dP characterization", "acceptance_criterion": "Demonstrate variable conductance over pressure range", "dependency": "None", "deliverable": "Passive flow characterization report", "estimated_effort": "4 weeks"},
            {"work_package": "WP-02", "test_article": "Actuator-integrated valve", "equipment": "Bench flow loop + actuator driver", "design_work": "Actuator selection + integration", "measurement": "Step response of A(t)", "acceptance_criterion": "10-90% rise < 5 s", "dependency": "WP-01 + actuator procurement", "deliverable": "Active valve step-response report", "estimated_effort": "8 weeks"},
            {"work_package": "WP-03", "test_article": "Closed-loop controller", "equipment": "Real-time controller (e.g., dSPACE or STM32)", "design_work": "Controller firmware", "measurement": "Closed-loop tracking error", "acceptance_criterion": "Steady-state error < 2 mmHg", "dependency": "WP-02", "deliverable": "Closed-loop performance report", "estimated_effort": "6 weeks"},
            {"work_package": "WP-04", "test_article": "Postural simulator", "equipment": "Programmable pressure source mimicking postural transients", "design_work": "Test fixture", "measurement": "ICP excursion attenuation vs fixed valve", "acceptance_criterion": "Excursion amplitude reduced by >=30% vs fixed valve (MODEL_DERIVED target)", "dependency": "WP-03", "deliverable": "Adaptive performance report", "estimated_effort": "6 weeks"},
            {"work_package": "WP-05", "test_article": "Biocompatibility specimens", "equipment": "ISO 10993 test lab", "design_work": "Material selection frozen", "measurement": "Cytotoxicity, sensitization, irritation", "acceptance_criterion": "ISO 10993 pass", "dependency": "Material selection frozen", "deliverable": "ISO 10993 report", "estimated_effort": "12 weeks (external lab)"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "Adaptive valve concept + mechanism description",
                "Controller algorithm specification (MODELLED, not production-firmware)",
                "Variable-area orifice governing equation + sensitivity analysis",
                "V0 bench prototype BOM (COTS sensor + custom valve body + candidate actuators)",
                "This engineering dossier with external precedent + failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Production valve design (dimensioned drawings, tolerances, material selection frozen)",
                "Actuator technology selection and validation",
                "Production controller firmware + software V&V per IEC 62304",
                "Manufacturing process for variable-area valve",
                "Regulatory submission (likely 510(k) with substantial equivalence, or De Novo if no predicate)",
                "Clinical validation evidence (IDE trial)",
                "Long-term reliability testing (ISO 14708-1 for active implants)"
            ]
        }
    }
