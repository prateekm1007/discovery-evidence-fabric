"""
p21r1.py — P-21-R1 UWB Position Mapping engineering core (revised after R1 fix).
Domain: RF / localization / tissue propagation / SAR.

Governing model: TOA ranging + tissue attenuation + SAR limit.
External precedent: UWB medical radar literature + FCC Part 15.250.
"""
from .constants import EQUATIONS, STANDARDS


def get_data():
    return {
        "technology_domain": "Radio Frequency (UWB) Localization + Tissue Propagation",
        "engineering_disciplines": [
            "RF engineering (UWB transceiver design)",
            "Antenna engineering (implantable antennas)",
            "Tissue electromagnetics (dielectric properties, propagation)",
            "Regulatory engineering (FCC SAR, IEC 60601-1-2)",
            "Signal processing (TOA estimation, multipath mitigation)"
        ],
        "system_architecture": {
            "description": "Implantable UWB transmitter in shunt catheter; external receiver array localizes catheter position via time-of-arrival (TOA) ranging. R1 fix: original P-21 assumed sub-mm accuracy without SAR analysis; R1 redesign bounds accuracy by SAR limit and tissue propagation physics.",
            "subsystems": [
                {"id": "SS-01", "name": "Implantable UWB transmitter", "function": "Emits UWB pulse train at FCC Part 15.250 compliant frequency (3.1-10.6 GHz band, BPSK or pulse UWB)", "status": "PROPOSED", "evidence_class": "PROPOSED", "evidence_source": "R332 + external UWB localization literature (PMC5375869)"},
                {"id": "SS-02", "name": "Implantable antenna (small-form-factor)", "function": "Radiates UWB signal through tissue; antenna geometry constrained by catheter diameter (~2 mm)", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-03", "name": "External receiver array (4+ antennas)", "function": "Receives UWB signal at multiple known positions; computes TOA for localization", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-04", "name": "Localization algorithm (TOA + TDOA)", "function": "Estimates 3D position of implant from TOA measurements at multiple receivers", "status": "MODELLED", "evidence_class": "MODELLED"}
            ],
            "rf_model": {
                "key_equations": [
                    EQUATIONS["rf_toa"],
                    EQUATIONS["sar"],
                    "Path loss: PL(d) = PL(d0) + 10*n*log10(d/d0) + X_sigma   [tissue propagation]"
                ],
                "frequency_band": "UWB 3.1-10.6 GHz (FCC Part 15.250)",
                "ranging_principle": "Time-of-arrival (TOA): d = c * dt; accuracy bounded by bandwidth (B) and SNR: sigma_TOA ~ c / (B * sqrt(2*SNR))",
                "sar_limit": "1.6 W/kg averaged over 1g tissue (FCC limit; IEEE 1528 measurement)",
                "R1_correction": "Original P-21 assumed sub-mm accuracy; R1 redesign bounds accuracy by SAR limit (constrains transmit power) and tissue attenuation (constrains SNR)",
                "critical_parameter": "Bandwidth B, SNR, array geometry — together determine localization accuracy",
                "evidence_class": "MODELLED"
            }
        },
        "mechanism_architecture": {
            "physical_changes": "Implant emits UWB pulse; signal propagates through tissue with frequency-dependent attenuation; external array receives signal; TOA at each receiver yields position estimate",
            "key_physics": "UWB pulse propagation through tissue: signal attenuates with frequency (higher freq more attenuated) and distance. Tissue dielectric properties (permittivity, conductivity) vary by tissue type. TOA-based ranging accuracy bounded by Cramer-Rao lower bound: sigma_TOA >= c / (2*π*β*sqrt(2*SNR)) where β is RMS bandwidth.",
            "localization_model": {
                "input": "UWB signal at multiple external receivers",
                "model": "TDOA or TOA localization; 3D position from >= 4 receivers via multilateration",
                "accuracy_estimate": "MODELLED: sigma_pos ~ c / (B * sqrt(SNR)) * GDOP, where GDOP depends on array geometry",
                "status": "MODELLED — accuracy not validated in tissue phantom"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "UWB time-of-arrival ranging through tissue. Localization accuracy bounded by signal bandwidth, SNR (limited by SAR-constrained transmit power and tissue attenuation), and array geometry (GDOP).",
                "equations": [
                    EQUATIONS["rf_toa"],
                    EQUATIONS["sar"],
                    "sigma_TOA >= c / (2*pi*beta*sqrt(2*SNR))   [Cramer-Rao lower bound]",
                    "sigma_pos = GDOP * sigma_TOA   [geometric dilution of precision]",
                    "PL_tissue(d,f) = alpha(f) * d   [frequency-dependent path loss]"
                ],
                "assumptions": [
                    "Tissue approximated as layered dielectric (skin, fat, muscle, CSF) with published properties",
                    "Multipath separable given UWB bandwidth (>= 500 MHz)",
                    "External receiver array geometry known precisely",
                    "Implant clock synchronized to external reference (or differential TDOA used to relax requirement)",
                    "FCC Part 15.250 applies (UWB medical imaging)"
                ],
                "boundary_conditions": [
                    "Implant depth: 1-10 cm typical (cranial to peritoneal)",
                    "Tissue types: skin, fat, muscle, CSF, bone",
                    "Frequency: 3.1-10.6 GHz UWB",
                    "SAR limit: 1.6 W/kg averaged over 1g tissue"
                ],
                "input_variables": ["Transmit power P_tx (SAR-limited)", "Bandwidth B", "Center frequency f_c", "Array geometry", "Tissue properties"],
                "output_variables": ["Localization accuracy sigma_pos", "Update rate"],
                "parameter_sensitivities": [
                    "P_tx (transmit power) — SNR scales linearly; but SAR limit caps P_tx",
                    "B (bandwidth) — sigma_TOA scales as 1/B; wider bandwidth = better accuracy",
                    "f_c (center frequency) — higher freq = better resolution but more tissue attenuation",
                    "Array geometry — GDOP amplifies TOA error; poor geometry = poor accuracy",
                    "Tissue dielectric heterogeneity — causes systematic bias + multipath"
                ],
                "failure_regimes": [
                    "SAR limit reached before sufficient SNR -> accuracy insufficient",
                    "Tissue attenuation > link budget -> no signal at receiver",
                    "Multipath dominates -> TOA biased",
                    "Array geometry poor (GDOP > 5) -> localization inaccurate",
                    "Implant antenna inefficient at UWB in small form factor -> transmit power wasted"
                ]
            },
            "critical_parameters": [
                {"name": "Center frequency f_c", "value": "UNKNOWN — design choice balancing resolution and tissue attenuation", "unit": "GHz", "basis": "Design tradeoff", "evidence_class": "UNKNOWN", "verification_requirement": "Tissue phantom measurement"},
                {"name": "Bandwidth B", "value": "EXTERNAL_PRECEDENT (UWB requires >= 500 MHz per FCC)", "unit": "MHz", "basis": "FCC Part 15.250", "evidence_class": "EXTERNAL_PRECEDENT"},
                {"name": "Transmit power P_tx", "value": "UNKNOWN — bounded by SAR limit", "unit": "W", "basis": "FCC SAR constraint", "evidence_class": "UNKNOWN", "verification_requirement": "SAR simulation + measurement per IEEE 1528"},
                {"name": "SAR limit", "value": "EXTERNAL_PRECEDENT (1.6 W/kg averaged over 1g tissue, FCC)", "unit": "W/kg", "basis": "FCC standard", "evidence_class": "EXTERNAL_PRECEDENT", "standard": "FCC_15_250"},
                {"name": "Implant antenna size", "value": "UNKNOWN — constrained by catheter diameter ~2 mm", "unit": "mm", "basis": "Catheter geometry", "evidence_class": "UNKNOWN"},
                {"name": "Receiver array size", "value": "UNKNOWN", "unit": "count", "basis": "Localization accuracy target", "evidence_class": "UNKNOWN"},
                {"name": "Tissue dielectric properties", "value": "EXTERNAL_PRECEDENT (published Gabriel et al. tissue properties)", "unit": "F/m, S/m", "basis": "Published tissue measurements", "evidence_class": "EXTERNAL_PRECEDENT"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — published UWB medical radar literature (PMC5375869) and FCC Part 15.250 establish that UWB localization is technically feasible and regulatory-compliant at SAR limits. They do NOT establish that the proposed catheter-integrated UWB transmitter achieves clinically useful localization accuracy in CSF shunt context.",
            "proposed_design": {
                "input": "UWB pulse train from implant at FCC-compliant power",
                "mechanism": "TOA-based multilateration from external receiver array",
                "transformation": "UWB signal -> tissue propagation -> received signal at multiple antennas -> TOA estimates -> 3D position",
                "output": "3D position estimate of implant",
                "component_architecture": "Implant (UWB TX + antenna + clock) -> tissue -> external array (4+ RX antennas + TOA estimator) -> localization algorithm"
            },
            "failure_modes": [
                {"mode": "SAR limit too restrictive", "mechanism": "SAR limit caps transmit power below useful SNR", "design_feature": "Transmit power", "evidence": "FCC SAR constraint", "mitigation": "Duty-cycle reduction (lower avg power); wider bandwidth (better SNR per pulse); external power coupling", "verification_test": "SAR simulation + IEEE 1528 measurement", "residual_uncertainty": "UNKNOWN achievable SNR at SAR limit"},
                {"mode": "Tissue attenuation excessive", "mechanism": "High-frequency UWB attenuated by tissue", "design_feature": "Center frequency", "evidence": "Published tissue dielectric properties", "mitigation": "Lower center frequency (less attenuation but lower resolution)", "verification_test": "Tissue phantom measurement", "residual_uncertainty": "UNKNOWN optimal frequency"},
                {"mode": "Multipath bias", "mechanism": "Reflected signals bias TOA estimate", "design_feature": "TOA algorithm", "evidence": "Standard RF challenge in tissue", "mitigation": "First-path detection algorithms + UWB bandwidth (separates multipath)", "verification_test": "Phantom with reflecting structures", "residual_uncertainty": "UNKNOWN multipath magnitude in vivo"},
                {"mode": "Poor array geometry (high GDOP)", "mechanism": "Receiver geometry amplifies TOA error", "design_feature": "Array geometry", "evidence": "Standard localization theory", "mitigation": "Optimal array placement + redundant receivers", "verification_test": "GDOP simulation + phantom test", "residual_uncertainty": "UNKNOWN achievable GDOP in clinical setting"},
                {"mode": "Implant antenna inefficient", "mechanism": "Small antenna at UWB has low efficiency", "design_feature": "Implant antenna", "evidence": "Standard small-antenna challenge", "mitigation": "Antenna optimization + matching network", "verification_test": "Antenna measurement in tissue phantom", "residual_uncertainty": "UNKNOWN achievable efficiency in 2 mm form factor"},
                {"mode": "Clock drift between implant and external", "mechanism": "Implant clock not synchronized to external", "design_feature": "Timing reference", "evidence": "Standard TOA challenge", "mitigation": "TDOA (differential) instead of TOA; or two-way ranging", "verification_test": "TDOA localization test", "residual_uncertainty": "UNKNOWN clock stability requirement"},
                {"mode": "EMC interference with other devices", "mechanism": "UWB emissions interfere with other medical devices", "design_feature": "UWB transmitter", "evidence": "Standard EMC concern", "mitigation": "FCC Part 15 compliance + IEC 60601-1-2 testing", "verification_test": "EMC test per IEC 60601-1-2", "residual_uncertainty": "UNKNOWN specific interferences"},
                {"mode": "Battery depletion (implant)", "mechanism": "Active UWB transmitter consumes power", "design_feature": "Implant power supply", "evidence": "Standard active implant concern", "mitigation": "Duty cycling + low-power design + energy harvesting (P-15)", "verification_test": "Battery life test", "residual_uncertainty": "UNKNOWN achievable battery life"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "Localization accuracy in tissue phantom", "method": "Phantom with known implant positions + UWB localization", "acceptance": "sigma_pos <= target accuracy (UNKNOWN specific target — likely 5-10 mm clinical utility)", "evidence_class": "PROPOSED"},
                {"id": "VER-002", "requirement": "SAR compliance", "method": "IEEE 1528 SAR measurement in phantom", "acceptance": "SAR <= 1.6 W/kg averaged over 1g", "evidence_class": "PROPOSED", "standard": "IEEE_1528"},
                {"id": "VER-003", "requirement": "FCC Part 15.250 compliance", "method": "FCC certification testing", "acceptance": "Pass FCC certification", "evidence_class": "PROPOSED", "standard": "FCC_15_250"},
                {"id": "VER-004", "requirement": "EMC per IEC 60601-1-2", "method": "EMC test", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "IEC_60601_1_2"},
                {"id": "VER-005", "requirement": "Biocompatibility of implant components", "method": "ISO 10993 series", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "ISO_10993"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "Clinical localization accuracy", "method": "Clinical study comparing UWB localization to imaging (CT/MRI)", "acceptance": "Clinically useful accuracy for shunt position verification", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Achievable localization accuracy given SAR constraint and tissue attenuation — UNKNOWN (critical)",
                "Optimal center frequency balancing resolution and attenuation — UNKNOWN",
                "Achievable antenna efficiency in 2 mm catheter form factor — UNKNOWN",
                "Multipath magnitude in vivo — UNKNOWN",
                "Clinical accuracy requirement for shunt position verification — UNKNOWN",
                "Battery life for active UWB transmitter — UNKNOWN",
                "Regulatory pathway (FCC + FDA combination) — UNKNOWN specifics"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "Catheter position verification post-implantation and during follow-up; current standard is CT/MRI (expensive, ionizing for CT)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "UWB-based localization of catheter position; R1 fix: accuracy bounded by SAR and tissue physics", "evidence_class": "MODELLED", "source": "R332 + R1 correction"},
            {"id": "DI-003", "input": "Frequency band", "value": "EXTERNAL_PRECEDENT (UWB 3.1-10.6 GHz per FCC Part 15.250)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-004", "input": "SAR limit", "value": "EXTERNAL_PRECEDENT (1.6 W/kg averaged over 1g tissue, FCC)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-005", "input": "Tissue dielectric properties", "value": "EXTERNAL_PRECEDENT (Gabriel et al. published measurements)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-006", "input": "Bandwidth", "value": "EXTERNAL_PRECEDENT (>= 500 MHz per FCC UWB definition)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-007", "input": "Localization accuracy target", "value": "UNKNOWN — clinical utility threshold TBD", "evidence_class": "UNKNOWN", "resolution_plan": "Clinical input on accuracy requirement"},
            {"id": "DI-008", "input": "Implant antenna size constraint", "value": "Constrained by catheter diameter ~2 mm", "evidence_class": "VERIFIED"},
            {"id": "DI-009", "input": "Biocompatibility (ISO 10993)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 series"},
            {"id": "DI-010", "input": "Sterilization", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "Sterilization validation"},
            {"id": "DI-011", "input": "EMC", "value": "UNKNOWN — required IEC 60601-1-2", "evidence_class": "UNKNOWN", "resolution_plan": "IEC 60601-1-2 test"},
            {"id": "DI-012", "input": "Battery life (if active TX)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "Battery life test + duty cycling optimization"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Implantable UWB transmitter design", "status": "ABSENT", "design_status": "CIRCUIT_DEVELOPMENT_BLOCKED", "missing_inputs": ["Center frequency", "Modulation scheme", "Power budget", "Antenna design"]},
            {"id": "DO-002", "description": "Implantable antenna (small form factor UWB)", "status": "ABSENT", "design_status": "DESIGN_BLOCKED", "missing_inputs": ["Geometry constraints", "Center frequency", "Tissue loading analysis"]},
            {"id": "DO-003", "description": "External receiver array", "status": "CONCEPTUAL", "design_status": "ARCHITECTURE_DEFINED", "note": "Architecture proposed; component selection not finalized"},
            {"id": "DO-004", "description": "Localization algorithm", "status": "MODELLED", "design_status": "ALGORITHM_DEFINED", "note": "TOA/TDOA algorithm specified; not validated in tissue"}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "Localization accuracy in tissue phantom", "method": "Phantom + UWB localization", "acceptance": "sigma_pos <= target", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-002", "requirement": "SAR compliance", "method": "IEEE 1528", "acceptance": "SAR <= 1.6 W/kg", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "IEEE_1528"},
            {"id": "V-003", "requirement": "FCC Part 15.250 compliance", "method": "FCC certification", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "FCC_15_250"},
            {"id": "V-004", "requirement": "EMC IEC 60601-1-2", "method": "EMC test", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "IEC_60601_1_2"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "Clinical localization accuracy", "method": "Clinical study vs imaging", "acceptance": "Clinically useful accuracy", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "UWB transmitter IC", "qty": "1", "component_type": "COTS_CANDIDATE", "source_basis": "Standard UWB ICs (Decawave DW1000, etc.)", "material": "N/A (COTS)", "supplier": "Multiple (Qorvo, NXP)", "criticality": "CRITICAL", "verification": "Bench characterization + EMC"},
            {"item": "02", "description": "Implantable antenna (custom UWB)", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED", "material": "UNKNOWN — biocompatible metal (Pt-Ir, gold)", "supplier": "UNKNOWN — custom fabrication", "criticality": "CRITICAL", "verification": "Antenna measurement in phantom"},
            {"item": "03", "description": "Implant housing + battery", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard implantable device housing", "material": "Titanium or polymer", "supplier": "Multiple", "criticality": "HIGH", "verification": "Hermeticity + biocompatibility"},
            {"item": "04", "description": "External receiver array (4+ antennas + UWB RX)", "qty": "1 set", "component_type": "COTS_CANDIDATE", "source_basis": "Standard UWB receiver modules", "material": "N/A (COTS)", "supplier": "Multiple", "criticality": "HIGH", "verification": "Calibration + system test"}
        ],
        "materials": [
            {"component": "Implant antenna", "candidate_material": "Platinum-iridium", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard implantable electrode material", "verification_required": "ISO 10993 + antenna characterization", "status": "CANDIDATE"},
            {"component": "Implant antenna", "candidate_material": "Gold", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Biocompatible conductor", "verification_required": "ISO 10993 + antenna characterization", "status": "CANDIDATE"},
            {"component": "Implant housing", "candidate_material": "Titanium", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard implantable housing", "verification_required": "ISO 10993 + hermeticity", "status": "CANDIDATE"},
            {"component": "Implant housing", "candidate_material": "Parylene-C (polymer encapsulation)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard implantable polymer encapsulation", "verification_required": "ISO 10993 + hermeticity + RF transparency", "status": "CANDIDATE — preferred for RF transparency"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Antenna microfabrication (lithography or laser-cut)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard microfabrication", "tolerance_implication": "±5 μm feature tolerance", "note": "Custom process for catheter-integrated UWB antenna"},
                {"process": "Hybrid circuit assembly (UWB IC + antenna + battery)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard hybrid assembly", "tolerance_implication": "SMT tolerance", "note": "Miniaturization required"},
                {"process": "Hermetic encapsulation (titanium canister or parylene)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard implantable encapsulation", "tolerance_implication": "Encapsulation thickness affects RF", "note": "Parylene preferred for RF transparency"}
            ],
            "status": "ENGINEERING_CANDIDATE — no catheter-integrated UWB process validated"
        },
        "failure_analysis": [
            {"failure_mode": "SAR limit too restrictive", "mechanism": "SAR cap limits P_tx below useful SNR", "design_feature_affected": "Transmit power", "evidence": "FCC SAR constraint", "mitigation": "Duty cycling + wider bandwidth + external power coupling", "verification_test": "SAR simulation + IEEE 1528 measurement", "residual_uncertainty": "UNKNOWN achievable SNR"},
            {"failure_mode": "Tissue attenuation excessive", "mechanism": "High-frequency UWB attenuated", "design_feature_affected": "Center frequency", "evidence": "Published tissue properties", "mitigation": "Lower frequency (tradeoff with resolution)", "verification_test": "Phantom measurement", "residual_uncertainty": "UNKNOWN optimal frequency"},
            {"failure_mode": "Multipath bias", "mechanism": "Reflected signals bias TOA", "design_feature_affected": "TOA algorithm", "evidence": "Standard RF challenge", "mitigation": "First-path detection + UWB bandwidth", "verification_test": "Phantom with reflectors", "residual_uncertainty": "UNKNOWN in vivo multipath"},
            {"failure_mode": "Poor array geometry (high GDOP)", "mechanism": "Geometry amplifies TOA error", "design_feature_affected": "Array geometry", "evidence": "Localization theory", "mitigation": "Optimal placement + redundant receivers", "verification_test": "GDOP simulation", "residual_uncertainty": "UNKNOWN achievable GDOP clinically"},
            {"failure_mode": "Implant antenna inefficient", "mechanism": "Small antenna low efficiency at UWB", "design_feature_affected": "Implant antenna", "evidence": "Small-antenna challenge", "mitigation": "Antenna optimization + matching network", "verification_test": "Antenna measurement in phantom", "residual_uncertainty": "UNKNOWN achievable efficiency in 2 mm"},
            {"failure_mode": "Clock drift", "mechanism": "Implant clock not synchronized", "design_feature_affected": "Timing reference", "evidence": "TOA challenge", "mitigation": "TDOA or two-way ranging", "verification_test": "TDOA test", "residual_uncertainty": "UNKNOWN clock stability requirement"},
            {"failure_mode": "EMC interference", "mechanism": "UWB emissions affect other devices", "design_feature_affected": "UWB transmitter", "evidence": "Standard EMC concern", "mitigation": "FCC + IEC 60601-1-2 compliance", "verification_test": "EMC test", "residual_uncertainty": "UNKNOWN specific interferences"},
            {"failure_mode": "Battery depletion", "mechanism": "Active UWB TX consumes power", "design_feature_affected": "Implant power", "evidence": "Standard active implant concern", "mitigation": "Duty cycling + low-power design + energy harvesting", "verification_test": "Battery life test", "residual_uncertainty": "UNKNOWN battery life"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "UWB TX + RX link bench test", "equipment": "UWB development kits (Decawave), VNA, oscilloscope", "design_work": "Frequency + modulation selection", "measurement": "Path loss vs distance in air + simple tissue phantom", "acceptance_criterion": "Link budget closes at target distance", "dependency": "UWB evaluation kit", "deliverable": "Link budget report", "estimated_effort": "6 weeks"},
            {"work_package": "WP-02", "test_article": "Implantable UWB antenna prototypes", "equipment": "VNA, anechoic chamber, tissue phantom", "design_work": "Antenna geometry optimization for 2 mm catheter", "measurement": "Return loss, efficiency, radiation pattern in phantom", "acceptance_criterion": "Efficiency > 10% in tissue phantom", "dependency": "WP-01 (frequency)", "deliverable": "Antenna design report", "estimated_effort": "12 weeks"},
            {"work_package": "WP-03", "test_article": "SAR simulation model", "equipment": "EM simulation software (CST, SEMCAD)", "design_work": "FDTD simulation with anatomical model", "measurement": "SAR distribution at 1g averaging", "acceptance_criterion": "SAR <= 1.6 W/kg at target P_tx", "dependency": "WP-02 (antenna design)", "deliverable": "SAR simulation report", "estimated_effort": "8 weeks"},
            {"work_package": "WP-04", "test_article": "Tissue phantom with known positions", "equipment": "Phantom, positioning rig, UWB RX array", "design_work": "Phantom + protocol", "measurement": "Localization accuracy at multiple positions", "acceptance_criterion": "sigma_pos <= target (UNKNOWN specific target — likely 5-10 mm)", "dependency": "WP-01 + WP-02 + array", "deliverable": "Localization accuracy report", "estimated_effort": "10 weeks"},
            {"work_package": "WP-05", "test_article": "SAR measurement in phantom", "equipment": "IEEE 1528 SAR measurement system", "design_work": "Protocol per IEEE 1528", "measurement": "SAR at 1g averaging", "acceptance_criterion": "SAR <= 1.6 W/kg measured", "dependency": "WP-02 + WP-03", "deliverable": "SAR measurement report", "estimated_effort": "6 weeks"},
            {"work_package": "WP-06", "test_article": "EMC test articles", "equipment": "EMC test lab", "design_work": "Protocol per IEC 60601-1-2", "measurement": "EMC emissions + immunity", "acceptance_criterion": "Pass IEC 60601-1-2", "dependency": "Production-equivalent prototype", "deliverable": "EMC report", "estimated_effort": "8 weeks (external lab)"},
            {"work_package": "WP-07", "test_article": "FCC certification test articles", "equipment": "FCC-approved test lab", "design_work": "FCC Part 15.250 protocol", "measurement": "FCC compliance measurements", "acceptance_criterion": "FCC certification", "dependency": "Production-equivalent prototype", "deliverable": "FCC certification", "estimated_effort": "12 weeks (external)"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "UWB localization concept + R1 correction (SAR-bounded accuracy)",
                "TOA + SAR + tissue propagation governing equations",
                "Bench test protocols (link budget, SAR, accuracy, EMC, FCC)",
                "External precedent catalog (UWB medical radar, FCC Part 15.250, IEEE 1528)",
                "Critical UNKNOWN disclosure (achievable accuracy, antenna efficiency, multipath)",
                "This engineering dossier with failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Production UWB transmitter design (IC selection, modulation, power management)",
                "Implantable UWB antenna design (small form factor)",
                "External receiver array (production hardware + localization software)",
                "Manufacturing process for catheter-integrated UWB implant",
                "Regulatory submission (FDA + FCC combination; complex)",
                "Clinical validation (localization accuracy vs imaging)",
                "FCC certification + IEC 60601-1-2 compliance"
            ]
        }
    }
