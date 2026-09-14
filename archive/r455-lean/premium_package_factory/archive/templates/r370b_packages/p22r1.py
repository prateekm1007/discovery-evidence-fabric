"""
p22r1.py — P-22-R1 Autonomous Catheter Navigation engineering core (revised after R1 fix).
Domain: catheter mechanics / buckling / hydraulic actuation / tissue interaction.

Governing model: Euler buckling + bending stiffness + hydraulic force + tissue interaction.
External precedent: steerable catheter literature + ISO 10555-1.
"""
from .constants import EQUATIONS, STANDARDS


def get_data():
    return {
        "technology_domain": "Catheter Mechanics + Hydraulic Actuation + Tissue Interaction",
        "engineering_disciplines": [
            "Mechanical engineering (catheter mechanics, buckling)",
            "Hydraulic actuation",
            "Tissue biomechanics",
            "Control systems (closed-loop navigation)",
            "Sterilization and biocompatibility"
        ],
        "system_architecture": {
            "description": "Steerable CSF shunt catheter with hydraulic actuation for autonomous navigation during placement. R1 fix: original P-22 assumed fully autonomous navigation without addressing buckling failure modes; R1 redesign adds buckling analysis, tissue damage safety, and human-in-the-loop fallback.",
            "subsystems": [
                {"id": "SS-01", "name": "Catheter body (multi-lumen, flexible)", "function": "Carries CSF flow + houses steering lumens + sensor channels", "status": "MODELLED", "evidence_source": "R332 mechanism"},
                {"id": "SS-02", "name": "Hydraulic steering actuator", "function": "Inflatable/deflatable balloon or bellows at catheter tip; bends catheter when pressurized", "status": "PROPOSED", "evidence_class": "PROPOSED", "evidence_source": "External precedent (Advanced Science 2025 hydraulically steerable catheter)"},
                {"id": "SS-03", "name": "Tip position sensor", "function": "Measures catheter tip position and orientation for closed-loop navigation", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-04", "name": "Navigation controller", "function": "Closed-loop controller computing actuator pressures to track target trajectory; human-in-the-loop fallback (R1 fix)", "status": "MODELLED", "evidence_class": "MODELLED"}
            ],
            "mechanical_model": {
                "key_equations": [
                    EQUATIONS["euler_buckling"],
                    "Bending stiffness: EI (flexural rigidity)",
                    "Bending radius: R_bend = EI / M   [moment-curvature relationship]",
                    "Hydraulic force: F = P * A_piston"
                ],
                "buckling_regime": "Catheter subject to axial compression during insertion; Euler buckling load P_cr = pi^2 * E * I / L^2 sets maximum axial force before buckling",
                "tissue_interaction": "Catheter-tissue contact forces must remain below tissue damage threshold (UNKNOWN specific threshold)",
                "critical_parameter": "EI (flexural rigidity), actuator force, buckling threshold",
                "R1_correction": "Original P-22 assumed unlimited autonomous navigation; R1 redesign adds buckling failure mode + tissue safety + human-in-the-loop fallback",
                "evidence_class": "MODELLED"
            }
        },
        "mechanism_architecture": {
            "physical_changes": "Hydraulic pressure in steering lumen deflects catheter tip; coordinated multi-lumen pressure changes navigate catheter through anatomy",
            "key_physics": "Catheter bending governed by beam theory: curvature kappa = M / (E*I), where M is bending moment from actuator force. Buckling failure when axial compression exceeds Euler load P_cr = pi^2*E*I/L^2.",
            "navigation_model": {
                "input": "Target trajectory (from preoperative imaging) + sensed tip position",
                "model": "Closed-loop control: delta = target - sensed; controller computes actuator pressures; catheter bends to reduce delta",
                "safety_envelope": "Max axial force < P_cr (buckling); max contact force < tissue damage threshold (UNKNOWN); human-in-the-loop fallback if trajectory diverges",
                "status": "MODELLED — no in vivo validation"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "Hydraulic beam steering with buckling constraint. Catheter is modeled as flexible beam with hydraulically-actuated bending moment; axial compression limited by Euler buckling.",
                "equations": [
                    EQUATIONS["euler_buckling"],
                    "kappa = M / (E * I)   [beam curvature]",
                    "F_hydraulic = P_actuator * A_actuator   [actuator force]",
                    "M_tip = F_hydraulic * d_moment_arm   [bending moment at tip]",
                    "F_contact_tissue < F_damage_threshold   [tissue safety constraint]"
                ],
                "assumptions": [
                    "Catheter is slender beam (L >> D)",
                    "Material is linear elastic (small strain)",
                    "Actuator response quasi-static",
                    "Tissue is elastic with damage threshold (UNKNOWN specific value)",
                    "Anatomy known from preoperative imaging"
                ],
                "boundary_conditions": [
                    "Proximal: insertion force applied by clinician/robot",
                    "Distal: free tip with actuator moment",
                    "Wall contact: tissue reaction force",
                    "Axial compression < P_cr (buckling constraint)"
                ],
                "input_variables": ["Actuator pressure P", "Insertion force F_axial", "Catheter geometry (EI, L, D)", "Tissue properties"],
                "output_variables": ["Tip position", "Tip orientation", "Bending radius", "Contact forces"],
                "parameter_sensitivities": [
                    "EI (flexural rigidity) — too stiff: cannot bend; too soft: buckles easily",
                    "L (length) — P_cr scales as 1/L^2; longer catheter buckles more easily",
                    "Actuator area A — linear scaling of force",
                    "Tissue stiffness — affects contact force magnitude"
                ],
                "failure_regimes": [
                    "Buckling (axial force > P_cr) — catheter collapses",
                    "Tissue damage (contact force > threshold) — puncture or trauma",
                    "Actuator saturation — cannot achieve required bending",
                    "Navigation error — trajectory diverges from target",
                    "Tissue property variation — model mismatch"
                ]
            },
            "critical_parameters": [
                {"name": "Flexural rigidity EI", "value": "UNKNOWN — design choice balancing bendability and buckling resistance", "unit": "N·m^2", "basis": "Material + geometry selection", "evidence_class": "UNKNOWN", "verification_requirement": "Bench bending test per ISO 10555-1"},
                {"name": "Catheter length L", "value": "UNKNOWN — anatomy-dependent (cranial to peritoneal ~30-50 cm typical)", "unit": "m", "basis": "Anatomical constraint", "evidence_class": "UNKNOWN"},
                {"name": "Actuator pressure P", "value": "UNKNOWN", "unit": "Pa", "basis": "Actuator design", "evidence_class": "UNKNOWN", "verification_requirement": "Pressure test"},
                {"name": "Actuator area A", "value": "UNKNOWN", "unit": "m^2", "basis": "Geometry", "evidence_class": "UNKNOWN"},
                {"name": "Buckling threshold P_cr", "value": "DERIVED from EI and L", "unit": "N", "basis": "Euler formula", "evidence_class": "MODELLED", "verification_requirement": "Bench buckling test"},
                {"name": "Tissue damage threshold", "value": "UNKNOWN — varies by tissue type", "unit": "N", "basis": "UNKNOWN", "evidence_class": "UNKNOWN", "verification_requirement": "Literature review + animal study"},
                {"name": "Tip position sensor accuracy", "value": "UNKNOWN", "unit": "mm", "basis": "Sensor selection", "evidence_class": "UNKNOWN"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — published steerable catheter literature (Advanced Science 2025, PMC9809155) establishes that hydraulic steerable catheters are technically feasible. It does NOT establish that the proposed autonomous navigation system achieves clinically useful accuracy or safety in CSF shunt placement.",
            "proposed_design": {
                "input": "Target trajectory from preoperative imaging + sensed tip position",
                "mechanism": "Hydraulic actuator deflects catheter tip; closed-loop controller navigates to target",
                "transformation": "(target, sensed) -> actuator pressures -> catheter bending -> tip motion",
                "output": "Catheter tip at target position with bounded contact forces",
                "component_architecture": "Catheter body (multi-lumen) + hydraulic actuators + tip sensor + navigation controller + human-in-the-loop override"
            },
            "failure_modes": [
                {"mode": "Buckling", "mechanism": "Axial compression exceeds Euler load P_cr", "design_feature": "Catheter body", "evidence": "Standard beam theory", "mitigation": "Increase EI; reduce L; limit insertion force; monitor axial force", "verification_test": "Bench buckling test", "residual_uncertainty": "UNKNOWN in vivo buckling threshold"},
                {"mode": "Tissue damage", "mechanism": "Contact force exceeds tissue damage threshold", "design_feature": "Tip + contact surface", "evidence": "UNKNOWN — threshold tissue-specific", "mitigation": "Force sensing + force limit + soft tip design", "verification_test": "Animal study with tissue damage monitoring", "residual_uncertainty": "UNKNOWN damage threshold"},
                {"mode": "Navigation error", "mechanism": "Controller diverges from target trajectory", "design_feature": "Navigation controller", "evidence": "Standard closed-loop challenge", "mitigation": "Human-in-the-loop fallback (R1 fix); trajectory monitoring; abort criteria", "verification_test": "Phantom navigation test", "residual_uncertainty": "UNKNOWN achievable accuracy"},
                {"mode": "Actuator failure", "mechanism": "Hydraulic leak or pump failure", "design_feature": "Hydraulic actuator", "evidence": "Standard hydraulic failure", "mitigation": "Redundant actuator; manual override; fail-safe position", "verification_test": "Failure mode test", "residual_uncertainty": "UNKNOWN failure rate"},
                {"mode": "Sensor failure", "mechanism": "Tip position sensor malfunction", "design_feature": "Tip sensor", "evidence": "Standard sensor failure", "mitigation": "Redundant sensing; imaging-based fallback", "verification_test": "Sensor failure test", "residual_uncertainty": "UNKNOWN failure rate"},
                {"mode": "Anatomical variation not modeled", "mechanism": "Patient anatomy differs from preoperative model", "design_feature": "Navigation model", "evidence": "Standard anatomical variation", "mitigation": "Intraoperative imaging update; human oversight", "verification_test": "Phantom with anatomical variation", "residual_uncertainty": "UNKNOWN anatomical variation distribution"},
                {"mode": "Catheter jamming", "mechanism": "Mechanical obstruction in actuator lumen", "design_feature": "Hydraulic actuator", "evidence": "Standard hydraulic failure", "mitigation": "Flush protocol; redundant lumen", "verification_test": "Jam simulation", "residual_uncertainty": "UNKNOWN jam rate"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "Buckling threshold > expected insertion forces", "method": "Bench buckling test", "acceptance": "P_cr > max expected axial force with safety margin (>= 2x)", "evidence_class": "PROPOSED"},
                {"id": "VER-002", "requirement": "Contact force < tissue damage threshold", "method": "Bench contact force measurement + tissue study", "acceptance": "F_contact < threshold (UNKNOWN specific value)", "evidence_class": "PROPOSED", "standard": "ISO_10555_1"},
                {"id": "VER-003", "requirement": "Navigation accuracy in phantom", "method": "Anatomical phantom navigation test", "acceptance": "Targeting accuracy <= target (UNKNOWN specific target — likely 2-5 mm)", "evidence_class": "PROPOSED"},
                {"id": "VER-004", "requirement": "Biocompatibility ISO 10993", "method": "ISO 10993 series", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "ISO_10993"},
                {"id": "VER-005", "requirement": "ISO 10555-1 compliance (intravascular catheter general requirements)", "method": "ISO 10555-1 series", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "ISO_10555_1"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "Navigation accuracy in animal model", "method": "In vivo navigation study (IACUC required)", "acceptance": "Targeting accuracy clinically useful; no tissue damage", "evidence_class": "UNKNOWN"},
                {"id": "VAL-002", "requirement": "Clinical placement accuracy", "method": "Clinical study comparing autonomous navigation to standard placement", "acceptance": "Non-inferior or superior to standard", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Achievable EI balancing bendability and buckling resistance — UNKNOWN",
                "Tissue damage threshold for relevant anatomies — UNKNOWN (critical)",
                "Navigation accuracy in vivo — UNKNOWN",
                "Actuator failure rate — UNKNOWN",
                "Sensor failure rate — UNKNOWN",
                "Regulatory pathway (autonomous navigation adds complexity; likely Class III) — UNKNOWN",
                "Clinical placement accuracy requirement — UNKNOWN",
                "Anatomical variation distribution — UNKNOWN"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "Catheter placement accuracy affects shunt function; current placement is manual and operator-dependent (R332)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "Autonomous catheter navigation via hydraulic actuation; R1 fix: bounded by buckling + tissue safety + human-in-the-loop", "evidence_class": "MODELLED", "source": "R332 + R1 correction"},
            {"id": "DI-003", "input": "Anatomical trajectory", "value": "Cranial to peritoneal; ~30-50 cm typical", "evidence_class": "VERIFIED"},
            {"id": "DI-004", "input": "Catheter diameter", "value": "Constrained to ~2 mm (standard shunt catheter)", "evidence_class": "VERIFIED"},
            {"id": "DI-005", "input": "Buckling constraint", "value": "Axial force < P_cr = pi^2*E*I/L^2", "evidence_class": "MODELLED"},
            {"id": "DI-006", "input": "Tissue damage threshold", "value": "UNKNOWN — tissue-specific", "evidence_class": "UNKNOWN", "resolution_plan": "Literature review + animal study"},
            {"id": "DI-007", "input": "Biocompatibility (ISO 10993)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 series"},
            {"id": "DI-008", "input": "Sterilization", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 11135 or 11137"},
            {"id": "DI-009", "input": "Navigation accuracy target", "value": "UNKNOWN — clinical utility threshold TBD", "evidence_class": "UNKNOWN"},
            {"id": "DI-010", "input": "Human-in-the-loop requirement (R1 fix)", "value": "Operator must be able to override or abort navigation (R1 fix)", "evidence_class": "MODELLED"},
            {"id": "DI-011", "input": "EMC (if electronic controller)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "IEC 60601-1-2"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Multi-lumen catheter body design (geometry, materials, stiffness profile)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["EI target", "Material selection", "Multi-lumen layout"]},
            {"id": "DO-002", "description": "Hydraulic actuator design (balloon or bellows)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["Actuator area", "Pressure range", "Material"]},
            {"id": "DO-003", "description": "Tip position sensor", "status": "CONCEPTUAL", "design_status": "COTS_IDENTIFIED", "note": "EM tracking or fiber optic sensors candidates"},
            {"id": "DO-004", "description": "Navigation controller", "status": "MODELLED", "design_status": "ALGORITHM_DEFINED", "note": "Algorithm specified; not validated in vivo"}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "Buckling threshold > expected forces", "method": "Bench buckling test", "acceptance": "P_cr >= 2x max expected force", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-002", "requirement": "Contact force < damage threshold", "method": "Bench + tissue study", "acceptance": "F_contact < threshold", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "ISO_10555_1"},
            {"id": "V-003", "requirement": "Navigation accuracy in phantom", "method": "Phantom navigation test", "acceptance": "Targeting accuracy <= target", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-004", "requirement": "Biocompatibility ISO 10993", "method": "ISO 10993", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "ISO_10993"},
            {"id": "V-005", "requirement": "ISO 10555-1 compliance", "method": "ISO 10555-1", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "ISO_10555_1"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "Navigation accuracy in animal model", "method": "In vivo study (IACUC)", "acceptance": "Clinically useful accuracy; no tissue damage", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"},
            {"id": "VAL-002", "requirement": "Clinical placement accuracy", "method": "Clinical trial (IDE)", "acceptance": "Non-inferior or superior to standard", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "Multi-lumen catheter body", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED", "material": "UNKNOWN — likely Pebax or polyurethane (standard catheter materials)", "supplier": "UNKNOWN — extrusion vendor", "criticality": "CRITICAL", "verification": "Mechanical + biocompatibility"},
            {"item": "02", "description": "Hydraulic actuator (balloon or bellows)", "qty": "1+", "component_type": "CUSTOM_COMPONENT", "source_basis": "EXTERNAL_PRECEDENT for hydraulic steerable catheters", "material": "UNKNOWN — likely silicone or polyurethane", "supplier": "UNKNOWN — custom", "criticality": "CRITICAL", "verification": "Pressure + fatigue + leak test"},
            {"item": "03", "description": "Tip position sensor", "qty": "1", "component_type": "COTS_CANDIDATE", "source_basis": "EM tracking (e.g., NDI Aurora) or fiber optic", "material": "N/A (COTS)", "supplier": "Multiple (NDI, etc.)", "criticality": "HIGH", "verification": "Calibration + integration"},
            {"item": "04", "description": "Hydraulic pump + valves", "qty": "1 set", "component_type": "COTS_CANDIDATE", "source_basis": "Standard micro-pump + valves", "material": "N/A (COTS)", "supplier": "Multiple", "criticality": "HIGH", "verification": "Calibration + reliability"},
            {"item": "05", "description": "Controller (real-time MCU)", "qty": "1", "component_type": "COTS_CANDIDATE", "source_basis": "Standard real-time MCU", "material": "N/A (COTS)", "supplier": "Multiple (TI, STM)", "criticality": "HIGH", "verification": "Software V&V per IEC 62304"}
        ],
        "materials": [
            {"component": "Catheter body", "candidate_material": "Pebax (polyether block amide)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard catheter material with tunable stiffness", "verification_required": "ISO 10993 + mechanical characterization", "status": "CANDIDATE"},
            {"component": "Catheter body", "candidate_material": "Polyurethane", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard catheter material", "verification_required": "ISO 10993 + mechanical", "status": "CANDIDATE"},
            {"component": "Hydraulic actuator", "candidate_material": "Silicone elastomer", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard balloon material", "verification_required": "ISO 10993 + fatigue + pressure", "status": "CANDIDATE"},
            {"component": "Reinforcement braid (if needed)", "candidate_material": "Stainless steel or nitinol braid", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard catheter reinforcement", "verification_required": "ISO 10993 + mechanical", "status": "CANDIDATE"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Multi-lumen extrusion (catheter body)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard medical tubing process", "tolerance_implication": "±0.05 mm typical", "note": "Requires custom extrusion die"},
                {"process": "Balloon/bellows fabrication (actuator)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard balloon catheter manufacturing", "tolerance_implication": "±0.02 mm typical", "note": "Custom for small catheter size"},
                {"process": "Catheter assembly (bonding, tipping)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard catheter assembly", "tolerance_implication": "Standard medical device tolerance", "note": "Requires assembly vendor"}
            ],
            "status": "ENGINEERING_CANDIDATE — no autonomous steerable shunt catheter process validated"
        },
        "failure_analysis": [
            {"failure_mode": "Buckling", "mechanism": "Axial compression > Euler load", "design_feature_affected": "Catheter body", "evidence": "Standard beam theory", "mitigation": "Increase EI; reduce L; limit insertion force; force monitoring", "verification_test": "Bench buckling test", "residual_uncertainty": "UNKNOWN in vivo threshold"},
            {"failure_mode": "Tissue damage", "mechanism": "Contact force > damage threshold", "design_feature_affected": "Tip + contact surface", "evidence": "UNKNOWN threshold", "mitigation": "Force sensing + limit + soft tip", "verification_test": "Tissue study", "residual_uncertainty": "CRITICAL UNKNOWN — threshold tissue-specific"},
            {"failure_mode": "Navigation error", "mechanism": "Controller divergence", "design_feature_affected": "Controller", "evidence": "Standard closed-loop challenge", "mitigation": "Human-in-the-loop fallback (R1 fix); abort criteria", "verification_test": "Phantom navigation", "residual_uncertainty": "UNKNOWN achievable accuracy"},
            {"failure_mode": "Actuator failure (leak)", "mechanism": "Hydraulic leak or pump failure", "design_feature_affected": "Hydraulic actuator", "evidence": "Standard hydraulic failure", "mitigation": "Redundant actuator; manual override", "verification_test": "Failure mode test", "residual_uncertainty": "UNKNOWN failure rate"},
            {"failure_mode": "Sensor failure", "mechanism": "Tip position sensor malfunction", "design_feature_affected": "Tip sensor", "evidence": "Standard sensor failure", "mitigation": "Redundant sensing; imaging fallback", "verification_test": "Sensor failure test", "residual_uncertainty": "UNKNOWN failure rate"},
            {"failure_mode": "Anatomical variation", "mechanism": "Patient anatomy differs from model", "design_feature_affected": "Navigation model", "evidence": "Standard anatomical variation", "mitigation": "Intraoperative imaging update; human oversight", "verification_test": "Phantom with variation", "residual_uncertainty": "UNKNOWN variation distribution"},
            {"failure_mode": "Catheter jamming", "mechanism": "Obstruction in actuator lumen", "design_feature_affected": "Hydraulic actuator", "evidence": "Standard hydraulic failure", "mitigation": "Flush protocol; redundant lumen", "verification_test": "Jam simulation", "residual_uncertainty": "UNKNOWN jam rate"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "Catheter mechanical specimens (various EI)", "equipment": "Mechanical test frame, bending rig", "design_work": "Material + geometry selection", "measurement": "EI, buckling threshold P_cr", "acceptance_criterion": "EI in target range; P_cr >= 2x max expected force", "dependency": "Material selection", "deliverable": "Catheter mechanical spec", "estimated_effort": "10 weeks"},
            {"work_package": "WP-02", "test_article": "Hydraulic actuator prototypes", "equipment": "Pressure source, displacement measurement", "design_work": "Balloon/bellows design", "measurement": "Tip deflection vs pressure; fatigue lifetime", "acceptance_criterion": "Deflection meets navigation need; fatigue > 10^4 cycles", "dependency": "WP-01", "deliverable": "Actuator spec", "estimated_effort": "10 weeks"},
            {"work_package": "WP-03", "test_article": "Anatomical phantom", "equipment": "Phantom, imaging, navigation system", "design_work": "Phantom + navigation protocol", "measurement": "Navigation accuracy + contact forces", "acceptance_criterion": "Accuracy <= target; forces < threshold", "dependency": "WP-01 + WP-02 + sensor + controller", "deliverable": "Phantom navigation report", "estimated_effort": "12 weeks"},
            {"work_package": "WP-04", "test_article": "Tissue damage specimens (animal)", "equipment": "Animal facility, histology", "design_work": "IACUC protocol", "measurement": "Tissue damage vs contact force", "acceptance_criterion": "Threshold established", "dependency": "WP-03", "deliverable": "Tissue damage threshold report", "estimated_effort": "16 weeks"},
            {"work_package": "WP-05", "test_article": "Biocompatibility specimens", "equipment": "ISO 10993 lab", "design_work": "Material selection frozen", "measurement": "ISO 10993 series", "acceptance_criterion": "Pass", "dependency": "Material selection", "deliverable": "ISO 10993 report", "estimated_effort": "12 weeks (external)"},
            {"work_package": "WP-06", "test_article": "In vivo navigation prototype", "equipment": "Animal facility, imaging", "design_work": "IACUC protocol", "measurement": "Navigation accuracy + safety in animal model", "acceptance_criterion": "Accuracy clinically useful; no tissue damage", "dependency": "WP-03 + WP-04", "deliverable": "In vivo navigation report", "estimated_effort": "20 weeks"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "Autonomous navigation concept + R1 correction (buckling + tissue safety + human-in-the-loop)",
                "Beam theory + buckling + hydraulic governing equations",
                "Bench test protocols (buckling, navigation accuracy, tissue damage, biocompatibility)",
                "External precedent catalog (steerable catheter literature)",
                "Critical UNKNOWN disclosure (tissue damage threshold, achievable accuracy)",
                "This engineering dossier with failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Production catheter design (multi-lumen, actuator integrated)",
                "Production navigation controller (software V&V per IEC 62304)",
                "Manufacturing process for steerable shunt catheter",
                "Regulatory submission (autonomous navigation adds complexity; likely Class III)",
                "Clinical validation (placement accuracy endpoint)",
                "Tissue damage threshold establishment (animal studies)"
            ]
        }
    }
