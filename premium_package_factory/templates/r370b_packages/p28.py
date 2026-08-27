"""
p28.py — P-28 Acoustic Blockage Detection engineering core.
Domain: acoustics / ultrasound / impedance / signal detection.

Governing model: acoustic impedance + reflection coefficient + signal detection.
External precedent: Doppler ultrasound, IVUS catheters, AIUM/NEMA UD-2.
"""
from .constants import EQUATIONS, STANDARDS, ACOUSTIC_VELOCITY_SOFT_TISSUE_M_S, ACOUSTIC_VELOCITY_CSF_M_S, ACOUSTIC_Z_SOFT_TISSUE, ACOUSTIC_Z_CSFR, ACOUSTIC_Z_BLOOD, ACOUSTIC_Z_AIR


def get_data():
    return {
        "technology_domain": "Acoustics + Ultrasound + Signal Detection",
        "engineering_disciplines": [
            "Acoustic engineering (transducer design)",
            "Ultrasound physics (wave propagation, impedance)",
            "Signal processing (classification, detection)",
            "Catheter integration (miniaturization)"
        ],
        "system_architecture": {
            "description": "Catheter-integrated acoustic transducer that emits ultrasonic pulse and detects reflections from obstruction (debris, tissue, air bubble). Signal classifier identifies obstruction type and severity.",
            "subsystems": [
                {"id": "SS-01", "name": "Acoustic transducer (piezoelectric)", "function": "Emits ultrasonic pulse and receives reflected echoes", "status": "PROPOSED", "evidence_class": "PROPOSED", "evidence_source": "R332 + external IVUS/ultrasound catheter literature (PMC5515670)"},
                {"id": "SS-02", "name": "Drive + receive electronics", "function": "Generates transmit pulse; amplifies and digitizes received echo", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-03", "name": "Signal classifier (ML or threshold-based)", "function": "Classifies echo pattern as normal, obstructed, or specific obstruction type", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-04", "name": "Catheter integration (acoustic window)", "function": "Acoustic coupling between transducer and CSF/lumen", "status": "PROPOSED", "evidence_class": "PROPOSED"}
            ],
            "acoustic_model": {
                "key_equations": [
                    EQUATIONS["acoustic_impedance"],
                    EQUATIONS["acoustic_reflection"],
                    "f/c = lambda   [wavelength = speed / frequency]"
                ],
                "impedance_contrast": "Reflection at interface proportional to (Z2-Z1)/(Z2+Z1). CSF (Z~1.5 MRayl) vs debris/clot (Z~1.6-1.7) gives weak reflection; CSF vs air (Z~0.0004) gives near-total reflection.",
                "frequency_selection": "Tradeoff: higher frequency = better resolution but more attenuation; lower frequency = better penetration but lower resolution. Typical IVUS uses 20-60 MHz.",
                "critical_parameter": "Frequency, SNR, classifier accuracy",
                "detection_target": "Obstruction (debris, tissue, air bubble) in catheter lumen",
                "evidence_class": "MODELLED"
            }
        },
        "mechanism_architecture": {
            "physical_changes": "Acoustic pulse propagates through CSF in catheter lumen; reflections from obstructions return to transducer; classifier identifies obstruction presence and type",
            "key_physics": "Acoustic impedance mismatch at obstruction boundary causes reflection. Reflection coefficient R = (Z2-Z1)/(Z2+Z1). Amplitude of reflection determines detection; time-of-flight determines distance.",
            "detection_model": {
                "input": "Acoustic echo time-series",
                "model": "Echo amplitude + time-of-flight -> obstruction presence + location + type (via classifier)",
                "detection_threshold": "SNR > threshold for detection; classifier threshold for obstruction type",
                "status": "MODELLED — no in vitro validation in CSF environment"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "Pulse-echo ultrasound detection. Acoustic impedance contrast at obstruction boundary causes reflection; transducer receives echo; classifier identifies obstruction.",
                "equations": [
                    EQUATIONS["acoustic_impedance"],
                    EQUATIONS["acoustic_reflection"],
                    "f * lambda = c   [wave equation]",
                    "TOF = 2 * d / c   [round-trip time of flight]",
                    "Attenuation: A(d) = A0 * exp(-alpha * f * d)   [frequency-dependent attenuation]"
                ],
                "assumptions": [
                    "CSF is approximately water-like acoustically (Z ~ 1.5 MRayl)",
                    "Obstruction has different acoustic impedance (debris ~ tissue-like, air ~ vacuum-like)",
                    "Catheter lumen is acoustically transparent at chosen frequency",
                    "Multipath and reverberation manageable",
                    "CSF attenuation comparable to water at operating frequency"
                ],
                "boundary_conditions": [
                    "Frequency: 1-50 MHz (low for deep penetration, high for IVUS-like resolution)",
                    "Catheter ID: ~1-2 mm",
                    "Detection range: 0-50 mm (length of catheter segment)",
                    "Acoustic coupling: CSF fills lumen"
                ],
                "input_variables": ["Frequency f", "Transmit voltage", "Obstruction properties (Z, location, size)"],
                "output_variables": ["Echo amplitude", "Time of flight", "Classification result"],
                "parameter_sensitivities": [
                    "f (frequency) — higher = better resolution, more attenuation",
                    "Z obstruction (impedance) — air gives strongest reflection; tissue gives weak",
                    "Transducer size — affects directivity and SNR",
                    "Catheter lumen geometry — affects acoustic path"
                ],
                "failure_regimes": [
                    "Low impedance contrast (tissue obstruction) -> weak reflection -> poor SNR",
                    "Attenuation excessive at high frequency -> no echo from distant obstruction",
                    "Multipath/reverberation -> false positives",
                    "Transducer failure -> no signal",
                    "Classifier misclassification -> wrong obstruction type"
                ]
            },
            "critical_parameters": [
                {"name": "Operating frequency", "value": "UNKNOWN — design choice (likely 5-20 MHz for catheter-scale resolution)", "unit": "MHz", "basis": "Resolution vs attenuation tradeoff", "evidence_class": "UNKNOWN", "verification_requirement": "Bench SNR test"},
                {"name": "Transducer size", "value": "UNKNOWN — constrained by catheter ~2 mm", "unit": "mm", "basis": "Catheter geometry", "evidence_class": "UNKNOWN"},
                {"name": "Acoustic impedance CSF", "value": "EXTERNAL_PRECEDENT (~1.5 MRayl, similar to water at 37°C)", "unit": "MRayl", "basis": "Published acoustic properties", "evidence_class": "EXTERNAL_PRECEDENT"},
                {"name": "Acoustic impedance obstruction (tissue)", "value": "EXTERNAL_PRECEDENT (~1.6-1.7 MRayl soft tissue)", "unit": "MRayl", "basis": "Published tissue acoustic properties", "evidence_class": "EXTERNAL_PRECEDENT"},
                {"name": "Acoustic impedance air", "value": "EXTERNAL_PRECEDENT (~0.0004 MRayl)", "unit": "MRayl", "basis": "Published acoustic properties", "evidence_class": "EXTERNAL_PRECEDENT"},
                {"name": "CSF attenuation coefficient", "value": "EXTERNAL_PRECEDENT (~0.002 dB/cm/MHz^2, similar to water)", "unit": "dB/(cm·MHz^2)", "basis": "Published water/CSF acoustic properties", "evidence_class": "EXTERNAL_PRECEDENT"},
                {"name": "Classifier accuracy target", "value": "UNKNOWN — clinical utility threshold TBD", "unit": "%", "basis": "UNKNOWN", "evidence_class": "UNKNOWN"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — published IVUS catheter literature (PMC5515670) and Doppler ultrasound establish that catheter-based acoustic detection is technically feasible. They do NOT establish that the proposed obstruction detection system achieves clinically useful performance in CSF shunt context.",
            "proposed_design": {
                "input": "Acoustic drive pulse + received echo",
                "mechanism": "Pulse-echo ultrasound with classifier",
                "transformation": "Transmit pulse -> propagation -> reflection at obstruction -> receive echo -> classify",
                "output": "Obstruction presence + type + location",
                "component_architecture": "Acoustic transducer (catheter-tip or side-looking) -> drive/receive electronics -> signal processor -> classifier -> alert"
            },
            "failure_modes": [
                {"mode": "Low impedance contrast (tissue obstruction)", "mechanism": "Tissue obstruction has similar Z to CSF -> weak reflection", "design_feature": "Detection sensitivity", "evidence": "Published acoustic properties", "mitigation": "Higher transmit power (limited by safety); better classifier; multi-frequency interrogation", "verification_test": "Bench test with tissue proxy", "residual_uncertainty": "UNKNOWN achievable sensitivity for tissue obstructions"},
                {"mode": "Attenuation limits detection range", "mechanism": "High-frequency pulses attenuate before reaching distant obstruction", "design_feature": "Frequency selection", "evidence": "Standard ultrasound physics", "mitigation": "Lower frequency (tradeoff with resolution); multiple frequency zones", "verification_test": "Range test at chosen frequency", "residual_uncertainty": "UNKNOWN optimal frequency"},
                {"mode": "Multipath / reverberation", "mechanism": "Catheter walls and structures cause spurious reflections", "design_feature": "Catheter geometry", "evidence": "Standard ultrasound challenge in confined geometry", "mitigation": "Signal processing (averaging, gating); catheter design with acoustic windows", "verification_test": "Phantom with controlled reflectors", "residual_uncertainty": "UNKNOWN multipath severity in vivo"},
                {"mode": "Transducer failure", "mechanism": "Piezoelectric element degrades or disconnects", "design_feature": "Transducer", "evidence": "Standard transducer failure", "mitigation": "Redundant transducer; self-test protocol", "verification_test": "Reliability test", "residual_uncertainty": "UNKNOWN failure rate"},
                {"mode": "Classifier misclassification", "mechanism": "ML or threshold classifier produces wrong result", "design_feature": "Classifier", "evidence": "Standard ML challenge", "mitigation": "Diverse training data; conservative thresholds; human review", "verification_test": "Cross-validation + prospective test", "residual_uncertainty": "UNKNOWN achievable accuracy"},
                {"mode": "Acoustic window failure", "mechanism": "CSF does not fill lumen (air bubble, dry)", "design_feature": "Catheter integration", "evidence": "Standard acoustic coupling challenge", "mitigation": "Design ensures CSF coupling; air-bubble detection", "verification_test": "Air bubble test", "residual_uncertainty": "UNKNOWN coupling reliability in vivo"},
                {"mode": "False positives (clinically significant)", "mechanism": "Classifier flags normal variation as obstruction", "design_feature": "Classifier threshold", "evidence": "Standard detection challenge", "mitigation": "Conservative threshold; confirmatory imaging", "verification_test": "Clinical specificity study", "residual_uncertainty": "UNKNOWN false positive rate clinically"},
                {"mode": "EMC interference", "mechanism": "External EM affects electronics", "design_feature": "Electronics", "evidence": "Standard active device concern", "mitigation": "Shielding + IEC 60601-1-2", "verification_test": "EMC test", "residual_uncertainty": "UNKNOWN specific interferences"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "Detection sensitivity for obstruction types", "method": "Bench test with phantom obstructions (debris, tissue proxy, air)", "acceptance": "Detect >= 90% of obstructions at clinically relevant sizes", "evidence_class": "PROPOSED"},
                {"id": "VER-002", "requirement": "False positive rate", "method": "Bench test in normal (non-obstructed) condition", "acceptance": "False positive < 5% (MODEL_DERIVED target)", "evidence_class": "PROPOSED"},
                {"id": "VER-003", "requirement": "Acoustic output compliance", "method": "AIUM/NEMA UD-2 acoustic output measurement", "acceptance": "Mechanical index + thermal index within safety limits", "evidence_class": "PROPOSED", "standard": "AIUM_NEMA_UD_2"},
                {"id": "VER-004", "requirement": "Biocompatibility ISO 10993", "method": "ISO 10993 series", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "ISO_10993"},
                {"id": "VER-005", "requirement": "EMC IEC 60601-1-2", "method": "EMC test", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "IEC_60601_1_2"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "Clinical obstruction detection accuracy", "method": "Clinical study comparing acoustic detection to imaging (CT/shunt series)", "acceptance": "Sensitivity and specificity clinically useful", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Achievable detection sensitivity for tissue obstructions (low impedance contrast) — UNKNOWN (critical)",
                "Optimal frequency balancing resolution and attenuation — UNKNOWN",
                "False positive rate in clinical use — UNKNOWN",
                "Acoustic coupling reliability in vivo — UNKNOWN",
                "Classifier accuracy in vivo — UNKNOWN",
                "Regulatory pathway (likely 510(k) with IVUS predicate, or De Novo) — UNKNOWN",
                "Clinical utility threshold for obstruction size — UNKNOWN"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "Obstruction causes 30-50% of shunt failures; early detection enables preemptive intervention (R332)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "Acoustic obstruction detection via catheter-integrated transducer + classifier", "evidence_class": "MODELLED", "source": "R332"},
            {"id": "DI-003", "input": "Acoustic impedance CSF", "value": "EXTERNAL_PRECEDENT (~1.5 MRayl)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-004", "input": "Acoustic impedance tissue/debris", "value": "EXTERNAL_PRECEDENT (~1.6-1.7 MRayl soft tissue)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-005", "input": "Acoustic impedance air", "value": "EXTERNAL_PRECEDENT (~0.0004 MRayl)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-006", "input": "Catheter diameter", "value": "~2 mm (standard shunt catheter)", "evidence_class": "VERIFIED"},
            {"id": "DI-007", "input": "Detection range", "value": "0-50 mm (catheter segment length)", "evidence_class": "MODELLED"},
            {"id": "DI-008", "input": "Biocompatibility (ISO 10993)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 series"},
            {"id": "DI-009", "input": "Sterilization", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "Sterilization validation"},
            {"id": "DI-010", "input": "Acoustic output safety (AIUM/NEMA UD-2)", "value": "UNKNOWN — must comply with safety limits", "evidence_class": "UNKNOWN", "resolution_plan": "AIUM/NEMA UD-2 compliance test"},
            {"id": "DI-011", "input": "EMC", "value": "UNKNOWN — required IEC 60601-1-2", "evidence_class": "UNKNOWN", "resolution_plan": "IEC 60601-1-2 test"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Acoustic transducer design (frequency, geometry, material)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["Frequency", "Transducer geometry", "Material (PZT or PVDF)"]},
            {"id": "DO-002", "description": "Drive + receive electronics", "status": "CONCEPTUAL", "design_status": "CIRCUIT_DEVELOPMENT", "note": "Architecture proposed; not validated"},
            {"id": "DO-003", "description": "Classifier algorithm", "status": "MODELLED", "design_status": "ALGORITHM_DEFINED", "note": "Algorithm specified; not validated in vivo"},
            {"id": "DO-004", "description": "Catheter integration (acoustic window)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["Window geometry", "Material", "Coupling design"]}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "Detection sensitivity >= 90%", "method": "Bench phantom test", "acceptance": ">= 90% detection at clinically relevant sizes", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-002", "requirement": "False positive < 5%", "method": "Bench normal condition test", "acceptance": "< 5%", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-003", "requirement": "Acoustic output safety", "method": "AIUM/NEMA UD-2", "acceptance": "Within safety limits", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "AIUM_NEMA_UD_2"},
            {"id": "V-004", "requirement": "Biocompatibility ISO 10993", "method": "ISO 10993", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "ISO_10993"},
            {"id": "V-005", "requirement": "EMC IEC 60601-1-2", "method": "EMC test", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "IEC_60601_1_2"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "Clinical obstruction detection accuracy", "method": "Clinical study vs imaging", "acceptance": "Sensitivity + specificity clinically useful", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "Acoustic transducer (piezoelectric)", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "EXTERNAL_PRECEDENT (IVUS transducers)", "material": "PZT or PVDF", "supplier": "UNKNOWN — custom fabrication", "criticality": "CRITICAL", "verification": "Acoustic characterization + biocompatibility"},
            {"item": "02", "description": "Drive + receive electronics", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard pulser/receiver + ADC", "material": "N/A (PCB + components)", "supplier": "Multiple", "criticality": "HIGH", "verification": "Circuit simulation + bench"},
            {"item": "03", "description": "Signal processor / MCU", "qty": "1", "component_type": "COTS_CANDIDATE", "source_basis": "Standard low-power MCU or FPGA", "material": "N/A (COTS)", "supplier": "Multiple", "criticality": "HIGH", "verification": "Software V&V per IEC 62304"},
            {"item": "04", "description": "Catheter body with acoustic window", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard catheter + custom window", "material": "UNKNOWN — silicone/polyurethane with acoustic-transparent window", "supplier": "UNKNOWN", "criticality": "HIGH", "verification": "Acoustic coupling + biocompatibility"}
        ],
        "materials": [
            {"component": "Acoustic transducer", "candidate_material": "PZT (lead zirconate titanate)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard ultrasound transducer material", "verification_required": "ISO 10993 (with encapsulation due to lead) + acoustic characterization", "status": "CANDIDATE — encapsulation required"},
            {"component": "Acoustic transducer", "candidate_material": "PVDF (polyvinylidene fluoride)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Polymer piezoelectric; biocompatible", "verification_required": "ISO 10993 + acoustic characterization", "status": "CANDIDATE — preferred for biocompatibility but lower coupling"},
            {"component": "Catheter body", "candidate_material": "Silicone elastomer", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard CSF shunt material", "verification_required": "ISO 10993 + acoustic transparency", "status": "CANDIDATE"},
            {"component": "Acoustic window", "candidate_material": "Polyurethane (acoustically transparent)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard ultrasound window material", "verification_required": "ISO 10993 + acoustic characterization", "status": "CANDIDATE"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Piezoelectric transducer microfabrication", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard ultrasound transducer manufacturing", "tolerance_implication": "±5 μm feature tolerance", "note": "Custom for catheter-scale size"},
                {"process": "Hybrid circuit assembly (transducer + electronics)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard hybrid assembly", "tolerance_implication": "SMT tolerance", "note": "Miniaturization required"},
                {"process": "Catheter extrusion + acoustic window integration", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard catheter manufacturing", "tolerance_implication": "±0.05 mm typical", "note": "Custom for acoustic window"},
                {"process": "Hermetic encapsulation (if PZT used)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard implantable encapsulation", "tolerance_implication": "Encapsulation affects acoustic coupling", "note": "Tradeoff between encapsulation and acoustic performance"}
            ],
            "status": "ENGINEERING_CANDIDATE — no catheter-integrated acoustic obstruction detector process validated"
        },
        "failure_analysis": [
            {"failure_mode": "Low impedance contrast (tissue obstruction)", "mechanism": "Tissue Z similar to CSF -> weak reflection", "design_feature_affected": "Detection sensitivity", "evidence": "Published acoustic properties", "mitigation": "Higher power (limited); better classifier; multi-frequency", "verification_test": "Bench with tissue proxy", "residual_uncertainty": "UNKNOWN achievable sensitivity"},
            {"failure_mode": "Attenuation limits range", "mechanism": "High freq attenuates before reaching obstruction", "design_feature_affected": "Frequency selection", "evidence": "Standard ultrasound physics", "mitigation": "Lower frequency (tradeoff with resolution)", "verification_test": "Range test", "residual_uncertainty": "UNKNOWN optimal frequency"},
            {"failure_mode": "Multipath / reverberation", "mechanism": "Catheter walls cause spurious reflections", "design_feature_affected": "Catheter geometry", "evidence": "Standard ultrasound challenge", "mitigation": "Signal processing + acoustic windows", "verification_test": "Phantom with reflectors", "residual_uncertainty": "UNKNOWN in vivo severity"},
            {"failure_mode": "Transducer failure", "mechanism": "Piezo element degrades or disconnects", "design_feature_affected": "Transducer", "evidence": "Standard transducer failure", "mitigation": "Redundant transducer + self-test", "verification_test": "Reliability test", "residual_uncertainty": "UNKNOWN failure rate"},
            {"failure_mode": "Classifier misclassification", "mechanism": "ML or threshold produces wrong result", "design_feature_affected": "Classifier", "evidence": "Standard ML challenge", "mitigation": "Diverse training + conservative thresholds", "verification_test": "Cross-validation + prospective", "residual_uncertainty": "UNKNOWN achievable accuracy"},
            {"failure_mode": "Acoustic window failure", "mechanism": "CSF doesn't fill lumen (air bubble)", "design_feature_affected": "Catheter integration", "evidence": "Standard acoustic coupling challenge", "mitigation": "Design ensures coupling + air bubble detection", "verification_test": "Air bubble test", "residual_uncertainty": "UNKNOWN coupling reliability"},
            {"failure_mode": "False positives", "mechanism": "Classifier flags normal variation as obstruction", "design_feature_affected": "Classifier threshold", "evidence": "Standard detection challenge", "mitigation": "Conservative threshold + confirmatory imaging", "verification_test": "Specificity study", "residual_uncertainty": "UNKNOWN clinical FP rate"},
            {"failure_mode": "EMC interference", "mechanism": "External EM affects electronics", "design_feature_affected": "Electronics", "evidence": "Standard active device concern", "mitigation": "Shielding + IEC 60601-1-2", "verification_test": "EMC test", "residual_uncertainty": "UNKNOWN specific interferences"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "Acoustic transducer prototypes (various frequencies + geometries)", "equipment": "VNA, hydrophone, ultrasound characterization bench", "design_work": "Transducer design + frequency selection", "measurement": "Sensitivity, bandwidth, directivity", "acceptance_criterion": "Sensitivity + bandwidth meet detection requirement", "dependency": "Transducer fabrication", "deliverable": "Transducer spec", "estimated_effort": "12 weeks"},
            {"work_package": "WP-02", "test_article": "Acoustic phantom with obstruction proxies", "equipment": "Phantom, transducer, data acquisition", "design_work": "Phantom + obstruction protocol", "measurement": "Detection sensitivity for various obstruction types/sizes", "acceptance_criterion": ">= 90% detection at clinically relevant sizes", "dependency": "WP-01", "deliverable": "Detection sensitivity report", "estimated_effort": "8 weeks"},
            {"work_package": "WP-03", "test_article": "Classifier algorithm + training data", "equipment": "Compute, datasets from WP-02", "design_work": "ML model + training protocol", "measurement": "Classifier accuracy (sensitivity + specificity)", "acceptance_criterion": "Sensitivity >= 90%; specificity >= 95%", "dependency": "WP-02", "deliverable": "Classifier report", "estimated_effort": "10 weeks"},
            {"work_package": "WP-04", "test_article": "Acoustic output measurement articles", "equipment": "AIUM/NEMA UD-2 measurement system", "design_work": "Acoustic output protocol", "measurement": "Mechanical index + thermal index", "acceptance_criterion": "Within safety limits", "dependency": "WP-01", "deliverable": "Acoustic output report", "estimated_effort": "6 weeks"},
            {"work_package": "WP-05", "test_article": "Biocompatibility specimens", "equipment": "ISO 10993 lab", "design_work": "Material selection frozen", "measurement": "ISO 10993 series", "acceptance_criterion": "Pass", "dependency": "Material selection", "deliverable": "ISO 10993 report", "estimated_effort": "12 weeks (external)"},
            {"work_package": "WP-06", "test_article": "EMC test articles", "equipment": "EMC lab", "design_work": "Protocol per IEC 60601-1-2", "measurement": "EMC emissions + immunity", "acceptance_criterion": "Pass", "dependency": "Production-equivalent prototype", "deliverable": "EMC report", "estimated_effort": "8 weeks (external)"},
            {"work_package": "WP-07", "test_article": "In vivo obstruction detection prototype", "equipment": "Animal facility", "design_work": "IACUC protocol", "measurement": "Detection accuracy in animal model", "acceptance_criterion": "Clinically useful sensitivity + specificity", "dependency": "WP-03 + WP-05", "deliverable": "In vivo detection report", "estimated_effort": "20 weeks"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "Acoustic obstruction detection concept + mechanism description",
                "Acoustic impedance + reflection + TOA governing equations",
                "Bench test protocols (detection sensitivity, false positives, acoustic output, EMC)",
                "External precedent catalog (IVUS, Doppler, AIUM/NEMA UD-2)",
                "Critical UNKNOWN disclosure (tissue obstruction sensitivity, optimal frequency, false positive rate)",
                "This engineering dossier with failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Production transducer design (frequency, geometry, material)",
                "Production drive + receive electronics + signal processor",
                "Production classifier (validated in vivo)",
                "Manufacturing process for catheter-integrated acoustic detector",
                "Regulatory submission (510(k) with IVUS predicate, or De Novo)",
                "Clinical validation (sensitivity + specificity vs imaging)"
            ]
        }
    }
