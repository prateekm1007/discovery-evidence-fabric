"""
p24.py — P-24 Gravity Compensation Hydraulic Damper engineering core.
Domain: hydraulic valve physics / pressure-flow / proportional control.

Governing model: gravity head + orifice equation + damper equation.
External precedent: anti-siphon devices (Miethke ShuntAssistant, Aesculap).
"""
from .constants import EQUATIONS, STANDARDS, CSF_DENSITY_KG_M3, G_GRAVITY_M_S2, MMHG_TO_PA, CM_H2O_TO_PA


def get_data():
    return {
        "technology_domain": "Hydraulic Valve Mechanics + Proportional Damping",
        "engineering_disciplines": [
            "Hydraulic valve engineering",
            "Proportional control (mechanical)",
            "Fluid mechanics (gravity-driven flow)",
            "Polymer engineering (damper element)"
        ],
        "system_architecture": {
            "description": "CSF shunt with hydraulic damper that proportionally attenuates postural pressure transients. Unlike fixed anti-siphon devices (ASD) that switch open/closed, this provides continuous proportional damping based on gravity head.",
            "subsystems": [
                {"id": "SS-01", "name": "Damper element (proportional)", "function": "Hydraulic resistance that varies with flow rate or pressure differential; provides damping coefficient c", "status": "MODELLED", "evidence_source": "R332 mechanism"},
                {"id": "SS-02", "name": "Gravity reference chamber", "function": "References valve setting to gravity (postural); provides dP_gravity = rho * g * dh", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-03", "name": "Main catheter lumen", "function": "Carries CSF flow from ventricle to peritoneum", "status": "MODELLED"},
                {"id": "SS-04", "name": "Outlet (peritoneal) catheter", "function": "Drains CSF to peritoneal cavity", "status": "MODELLED"}
            ],
            "hydraulic_model": {
                "key_equations": [
                    EQUATIONS["gravity_head"],
                    EQUATIONS["damper_force"],
                    EQUATIONS["orifice"],
                    EQUATIONS["hagen_poiseuille"]
                ],
                "postural_pressure": "When upright, hydrostatic head dP_gravity = rho * g * dh (e.g., 30 cm H2O ~ 22 mmHg for cranial-to-peritoneal differential)",
                "damper_response": "Flow rate Q proportional to (dP_total - dP_gravity); damper coefficient c controls proportional attenuation",
                "critical_parameter": "Damper coefficient c, gravity head range, response time",
                "comparison_to_ASD": "ASD switches open/closed at threshold; this damper provides continuous proportional response (potentially smoother ICP profile, but UNKNOWN clinical advantage)",
                "evidence_class": "MODELLED"
            }
        },
        "mechanism_architecture": {
            "physical_changes": "Postural change creates hydrostatic pressure differential; damper element provides hydraulic resistance proportional to flow, attenuating the transient",
            "key_physics": "Gravity head: dP_gravity = rho * g * dh. Damper equation: F = c * v (force proportional to velocity). For hydraulic damper: dP_damper = c_h * Q, where c_h is hydraulic damping coefficient.",
            "dynamic_model": {
                "input": "Postural change (head-up tilt creates dP_gravity step)",
                "model": "First-order system: dQ/dt = (dP_total - dP_gravity - c_h * Q) / I_hydraulic, where I_hydraulic is fluid inertia (small)",
                "response_time": "Settling time ~ 5 * tau where tau = I_hydraulic / c_h",
                "status": "MODELLED — comparative advantage over ASD UNKNOWN"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "Hydraulic damper provides flow-proportional resistance. Postural transients excite the system; damper coefficient c_h determines settling time and overshoot.",
                "equations": [
                    EQUATIONS["gravity_head"],
                    EQUATIONS["damper_force"],
                    "dP_total = dP_valve + dP_gravity - dP_damper",
                    "dP_damper = c_h * Q   [hydraulic damping]",
                    "Settling time: tau = I_h / c_h   [first-order response]"
                ],
                "assumptions": [
                    "CSF is incompressible (valid at these pressures)",
                    "Damper response is linear (F = c*v)",
                    "Gravity reference is stable",
                    "No cavitation",
                    "Catheter compliance negligible"
                ],
                "boundary_conditions": [
                    "Postural range: supine to upright (dh up to ~50 cm H2O ~ 37 mmHg)",
                    "ICP safety range: 5-20 mmHg normal",
                    "Flow range: 0.05-0.5 mL/min typical"
                ],
                "input_variables": ["Postural state (dh)", "ICP", "Outlet pressure"],
                "output_variables": ["Drainage rate Q(t)", "ICP transient attenuation"],
                "parameter_sensitivities": [
                    "c_h (damping coefficient) — too low: insufficient damping; too high: excessive resistance, underdrainage",
                    "Gravity reference dh — must match anatomical head-to-peritoneal distance",
                    "Response time tau — must be < postural transient duration (~seconds)"
                ],
                "failure_regimes": [
                    "c_h too low — no damping benefit; behaves like fixed valve",
                    "c_h too high — underdrainage; chronic intracranial hypertension",
                    "Damper element failure — reverts to fixed valve behavior",
                    "Gravity reference drift — postural compensation inaccurate"
                ]
            },
            "critical_parameters": [
                {"name": "Damper coefficient c_h", "value": "UNKNOWN", "unit": "mmHg/(mL/min)", "basis": "Design choice", "evidence_class": "UNKNOWN", "verification_requirement": "Bench flow test"},
                {"name": "Gravity head range", "value": "EXTERNAL_PRECEDENT (postural cranial-to-peritoneal differential 0-50 cm H2O)", "unit": "cm H2O", "basis": "Published physiology", "evidence_class": "EXTERNAL_PRECEDENT"},
                {"name": "Response time tau", "value": "UNKNOWN — target < postural transient duration (~seconds)", "unit": "s", "basis": "MODELLED", "evidence_class": "MODELLED"},
                {"name": "Damper element material", "value": "UNKNOWN", "unit": "n/a", "basis": "Material selection", "evidence_class": "UNKNOWN"},
                {"name": "Damper element geometry", "value": "UNKNOWN", "unit": "mm", "basis": "Design choice", "evidence_class": "UNKNOWN"},
                {"name": "Drainage floor (minimum Q)", "value": "UNKNOWN — MODEL_DERIVED candidate 0.05 mL/min", "unit": "mL/min", "basis": "Clinical need", "evidence_class": "MODELLED"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — published anti-siphon device literature (PMC9133390 review of ASD mechanisms; Miethke ShuntAssistant, Aesculap) establishes that gravity-compensating shunt components are manufacturable and clinically used. It does NOT establish that the proposed proportional damper achieves clinical advantage over existing ASDs.",
            "proposed_design": {
                "input": "Postural state + ICP",
                "mechanism": "Hydraulic damper provides flow-proportional resistance to attenuate postural transients",
                "transformation": "Postural step -> gravity head -> damper-mediated flow response -> attenuated ICP transient",
                "output": "Drainage rate with reduced postural excursion amplitude",
                "component_architecture": "Ventricular catheter -> damper element (proportional) -> gravity reference chamber -> main valve -> peritoneal catheter"
            },
            "failure_modes": [
                {"mode": "Damper element degradation", "mechanism": "Mechanical fatigue or material creep changes c_h", "design_feature": "Damper element", "evidence": "Standard polymer degradation", "mitigation": "Material selection + lifetime derating", "verification_test": "Aging study with periodic c_h measurement", "residual_uncertainty": "UNKNOWN degradation rate"},
                {"mode": "Insufficient damping (c_h too low)", "mechanism": "Damper provides negligible attenuation", "design_feature": "Damper coefficient", "evidence": "MODELLED", "mitigation": "Increase c_h; redesign damper", "verification_test": "Bench flow test", "residual_uncertainty": "UNKNOWN optimal c_h"},
                {"mode": "Excessive damping (c_h too high)", "mechanism": "Damper causes underdrainage", "design_feature": "Damper coefficient", "evidence": "MODELLED", "mitigation": "Reduce c_h; ensure drainage floor", "verification_test": "Bench flow test", "residual_uncertainty": "UNKNOWN threshold"},
                {"mode": "Gravity reference drift", "mechanism": "Reference chamber leaks or shifts", "design_feature": "Gravity reference", "evidence": "Standard chamber failure", "mitigation": "Sealed reference; mechanical stops", "verification_test": "Aging study", "residual_uncertainty": "UNKNOWN achievable stability"},
                {"mode": "Air entrapment", "mechanism": "Air bubble in damper chamber compresses, spoiling damping", "design_feature": "Damper chamber", "evidence": "Standard hydraulic system failure", "mitigation": "Priming protocol; de-airing design", "verification_test": "Air entrapment bench test", "residual_uncertainty": "UNKNOWN clinical priming reliability"},
                {"mode": "Catheter obstruction (separate)", "mechanism": "Debris or tissue blocks lumen", "design_feature": "Catheter body", "evidence": "Standard shunt failure (30-50%)", "mitigation": "Standard obstruction mitigation", "verification_test": "Obstruction bench", "residual_uncertainty": "UNKNOWN whether damper affects obstruction rate"},
                {"mode": "Manufacturing tolerance violation", "mechanism": "Damper geometry tolerance > c_h margin", "design_feature": "Damper element", "evidence": "Standard manufacturing tolerance", "mitigation": "Cpk study + tolerance stack analysis", "verification_test": "Cpk measurement", "residual_uncertainty": "UNKNOWN achievable Cpk"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "Damper coefficient c_h within target range", "method": "Bench flow test", "acceptance": "c_h in target range", "evidence_class": "PROPOSED"},
                {"id": "VER-002", "requirement": "Postural ICP excursion attenuation vs standard shunt", "method": "Bench postural simulation (tilt table)", "acceptance": "Excursion amplitude reduced >= 30% vs fixed valve (MODEL_DERIVED target)", "evidence_class": "PROPOSED"},
                {"id": "VER-003", "requirement": "Minimum drainage floor maintained", "method": "Bench flow at worst-case pressure", "acceptance": "Q >= Q_min", "evidence_class": "PROPOSED"},
                {"id": "VER-004", "requirement": "Damper stability over simulated lifetime", "method": "Aging study with periodic c_h measurement", "acceptance": "c_h drift < 20% over target lifetime", "evidence_class": "PROPOSED"},
                {"id": "VER-005", "requirement": "Biocompatibility ISO 10993 + ISO 7437", "method": "ISO 10993 + ISO 7437", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "ISO_7437"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "Reduced ICP excursion vs standard shunt in patient cohort", "method": "Clinical trial (IDE required)", "acceptance": "Statistically significant reduction in ICP excursion amplitude", "evidence_class": "UNKNOWN"},
                {"id": "VAL-002", "requirement": "Clinical benefit (symptom reduction, complication rate)", "method": "Clinical trial", "acceptance": "Statistically significant clinical improvement", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Optimal damper coefficient c_h — UNKNOWN",
                "Achievable c_h given manufacturing constraints — UNKNOWN",
                "Comparative advantage over existing ASDs — UNKNOWN (critical for clinical adoption)",
                "Damper element long-term stability — UNKNOWN",
                "Regulatory pathway (likely 510(k) with substantial equivalence to existing ASD, or De Novo) — UNKNOWN",
                "Clinical benefit magnitude — UNKNOWN until trial"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "Postural ICP excursions cause symptoms and complications; existing ASDs switch but don't damp proportionally (R332)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "Proportional hydraulic damping of postural pressure transients", "evidence_class": "MODELLED", "source": "R332"},
            {"id": "DI-003", "input": "Postural head range", "value": "EXTERNAL_PRECEDENT (0-50 cm H2O typical cranial-to-peritoneal)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-004", "input": "Flow regime", "value": "Laminar, Re << 2300", "evidence_class": "COMPUTATIONALLY_SUPPORTED"},
            {"id": "DI-005", "input": "Damper coefficient target", "value": "UNKNOWN — to be optimized", "evidence_class": "UNKNOWN", "resolution_plan": "Bench optimization"},
            {"id": "DI-006", "input": "Response time target", "value": "MODELLED (< postural transient ~seconds)", "evidence_class": "MODELLED"},
            {"id": "DI-007", "input": "Biocompatibility (ISO 10993 + ISO 7437)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 + ISO 7437 series"},
            {"id": "DI-008", "input": "Sterilization", "value": "UNKNOWN — likely EtO or gamma", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 11135 or 11137"},
            {"id": "DI-009", "input": "Comparative clinical endpoint vs ASD", "value": "UNKNOWN — needs clinical input", "evidence_class": "UNKNOWN", "resolution_plan": "Clinical advisory input"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Damper element design (geometry, material, c_h target)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["c_h target", "Material selection", "Geometry"]},
            {"id": "DO-002", "description": "Gravity reference chamber design", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["Reference mechanism", "Stability spec"]},
            {"id": "DO-003", "description": "Integrated valve + damper assembly", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["Component layout", "Housing design"]},
            {"id": "DO-004", "description": "Bench test protocol (postural simulation)", "status": "CONCEPTUAL", "design_status": "PROTOCOL_DEVELOPMENT", "note": "Tilt table + mock CSF loop"}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "c_h within target range", "method": "Bench flow test", "acceptance": "c_h in target", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-002", "requirement": "ICP excursion attenuation >= 30% vs fixed valve", "method": "Tilt table bench", "acceptance": ">= 30% reduction", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-003", "requirement": "Minimum drainage Q >= Q_min", "method": "Bench flow at worst-case", "acceptance": "Q >= Q_min", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-004", "requirement": "c_h stability over lifetime", "method": "Aging study", "acceptance": "Drift < 20%", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-005", "requirement": "ISO 7437 + ISO 10993 compliance", "method": "ISO 7437 + ISO 10993", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "ISO_7437"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "ICP excursion reduction in patient cohort", "method": "Clinical trial (IDE)", "acceptance": "Significant reduction vs fixed valve", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"},
            {"id": "VAL-002", "requirement": "Clinical benefit", "method": "Clinical trial", "acceptance": "Symptom or complication reduction", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "Damper element (proportional)", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED", "material": "UNKNOWN — likely silicone or polyurethane", "supplier": "UNKNOWN — custom", "criticality": "CRITICAL", "verification": "c_h measurement + fatigue"},
            {"item": "02", "description": "Gravity reference chamber", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "EXTERNAL_PRECEDENT (existing ASD designs)", "material": "UNKNOWN — likely polymer + radiopaque marker", "supplier": "UNKNOWN — custom", "criticality": "HIGH", "verification": "Stability test"},
            {"item": "03", "description": "Valve housing", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard CSF shunt housing", "material": "UNKNOWN — likely silicone/Ti composite", "supplier": "UNKNOWN", "criticality": "HIGH", "verification": "Dimensional + biocompatibility"},
            {"item": "04", "description": "Inlet + outlet catheters", "qty": "2", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard CSF catheters", "material": "UNKNOWN — silicone or polyurethane", "supplier": "Multiple", "criticality": "HIGH", "verification": "Dimensional + biocompatibility"}
        ],
        "materials": [
            {"component": "Damper element", "candidate_material": "Silicone elastomer", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard CSF shunt material; tunable viscoelastic properties", "verification_required": "ISO 10993 + c_h characterization + fatigue", "status": "CANDIDATE"},
            {"component": "Damper element", "candidate_material": "Polyurethane", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Some shunt components use polyurethane", "verification_required": "ISO 10993 + c_h + fatigue", "status": "CANDIDATE"},
            {"component": "Gravity reference chamber", "candidate_material": "Polymer housing + radiopaque marker", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard ASD construction", "verification_required": "ISO 10993 + radiopacity per ASTM F640", "status": "CANDIDATE", "standard": "ASTM_F640"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Injection molding (damper element + housing)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard CSF shunt manufacturing", "tolerance_implication": "±0.02 mm typical", "note": "Damper geometry requires tight tolerance"},
                {"process": "Assembly (damper + reference + valve + catheters)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard shunt assembly", "tolerance_implication": "Standard medical device tolerance", "note": "Custom fixture for damper alignment"},
                {"process": "Radiopaque marker integration", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard radiopacity process", "tolerance_implication": "Marker placement ±0.1 mm", "note": "Required for post-implant visualization"}
            ],
            "status": "ENGINEERING_CANDIDATE — no proportional damper process validated"
        },
        "failure_analysis": [
            {"failure_mode": "Damper element degradation", "mechanism": "Polymer creep/fatigue changes c_h", "design_feature_affected": "Damper element", "evidence": "Standard polymer failure", "mitigation": "Material selection + derating", "verification_test": "Aging with c_h measurement", "residual_uncertainty": "UNKNOWN degradation rate"},
            {"failure_mode": "Insufficient damping", "mechanism": "c_h too low", "design_feature_affected": "Damper coefficient", "evidence": "MODELLED", "mitigation": "Increase c_h; redesign", "verification_test": "Bench flow", "residual_uncertainty": "UNKNOWN optimal c_h"},
            {"failure_mode": "Excessive damping", "mechanism": "c_h too high; underdrainage", "design_feature_affected": "Damper coefficient", "evidence": "MODELLED", "mitigation": "Reduce c_h; drainage floor", "verification_test": "Bench flow", "residual_uncertainty": "UNKNOWN threshold"},
            {"failure_mode": "Gravity reference drift", "mechanism": "Chamber leak or shift", "design_feature_affected": "Gravity reference", "evidence": "Standard chamber failure", "mitigation": "Sealed reference; mechanical stops", "verification_test": "Aging study", "residual_uncertainty": "UNKNOWN achievable stability"},
            {"failure_mode": "Air entrapment", "mechanism": "Air bubble compresses, spoils damping", "design_feature_affected": "Damper chamber", "evidence": "Standard hydraulic failure", "mitigation": "Priming protocol; de-airing design", "verification_test": "Air entrapment test", "residual_uncertainty": "UNKNOWN clinical priming reliability"},
            {"failure_mode": "Catheter obstruction", "mechanism": "Debris/tissue blocks lumen", "design_feature_affected": "Catheter body", "evidence": "Standard shunt failure (30-50%)", "mitigation": "Standard obstruction mitigation", "verification_test": "Obstruction bench", "residual_uncertainty": "UNKNOWN damper effect on obstruction rate"},
            {"failure_mode": "Manufacturing tolerance violation", "mechanism": "Damper geometry tolerance > margin", "design_feature_affected": "Damper element", "evidence": "Standard manufacturing", "mitigation": "Cpk study + tolerance analysis", "verification_test": "Cpk measurement", "residual_uncertainty": "UNKNOWN achievable Cpk"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "Damper element prototypes (various geometries)", "equipment": "Bench flow loop, Transonic flow sensor, pressure transducer", "design_work": "Damper geometry + material selection", "measurement": "c_h vs flow rate", "acceptance_criterion": "c_h in target range with stable response", "dependency": "Material selection", "deliverable": "Damper geometry spec", "estimated_effort": "8 weeks"},
            {"work_package": "WP-02", "test_article": "Integrated valve + damper + gravity reference", "equipment": "Tilt table, mock CSF loop, sensors", "design_work": "Integrated assembly design", "measurement": "ICP excursion attenuation vs fixed valve", "acceptance_criterion": ">= 30% reduction in excursion amplitude", "dependency": "WP-01 + reference chamber", "deliverable": "Integrated performance report", "estimated_effort": "10 weeks"},
            {"work_package": "WP-03", "test_article": "Damper element aging specimens", "equipment": "Aging chamber at 37°C in CSF mimic", "design_work": "Aging protocol", "measurement": "c_h vs time", "acceptance_criterion": "c_h drift < 20% over target lifetime", "dependency": "WP-01", "deliverable": "Stability report", "estimated_effort": "12-24 weeks (chronic)"},
            {"work_package": "WP-04", "test_article": "Manufacturing process specimens", "equipment": "Extrusion / molding line", "design_work": "Process development + Cpk study", "measurement": "Critical dimensions, c_h", "acceptance_criterion": "Cpk >= 1.33 for critical dimensions and c_h", "dependency": "WP-01", "deliverable": "Manufacturing process spec", "estimated_effort": "12 weeks"},
            {"work_package": "WP-05", "test_article": "Biocompatibility specimens", "equipment": "ISO 10993 + ISO 7437 test lab", "design_work": "Material selection frozen", "measurement": "ISO 10993 + ISO 7437 series", "acceptance_criterion": "Pass", "dependency": "Material selection", "deliverable": "Biocompatibility report", "estimated_effort": "12 weeks (external)"},
            {"work_package": "WP-06", "test_article": "Air entrapment test articles", "equipment": "Bench flow loop with air injection", "design_work": "Air entrapment protocol", "measurement": "Effect of air on c_h", "acceptance_criterion": "Damper tolerates specified air volume without failure", "dependency": "WP-02", "deliverable": "Air entrapment report", "estimated_effort": "4 weeks"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "Proportional damper concept + mechanism description",
                "Gravity head + damper + orifice governing equations",
                "Bench test protocols (c_h measurement, postural simulation, aging, Cpk)",
                "External precedent catalog (ASD literature: PMC9133390, Miethke ShuntAssistant)",
                "Critical UNKNOWN disclosure (optimal c_h, comparative advantage over ASD)",
                "This engineering dossier with failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Production damper element design (geometry, material, tolerances)",
                "Manufacturing process for damper + gravity reference + valve integration",
                "Comparative clinical evidence vs existing ASDs",
                "Regulatory submission (510(k) with substantial equivalence to ASD, or De Novo)",
                "Clinical validation (ICP excursion endpoint)",
                "Long-term reliability testing"
            ]
        }
    }
