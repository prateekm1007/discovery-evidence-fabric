"""
p26.py — P-26 Osmotic Pressure Regulating Drainage Valve engineering core.
Domain: osmotic membrane transport / membrane mechanics / fouling.

Governing model: van 't Hoff osmotic pressure + Kedem-Katchalsky membrane flux.
External precedent: osmotic pumps (DURECT) + membrane literature.
"""
from .constants import EQUATIONS, STANDARDS


def get_data():
    return {
        "technology_domain": "Osmotic Membrane Transport + Membrane Mechanics",
        "engineering_disciplines": [
            "Membrane science (semipermeable membranes)",
            "Osmotic transport (van 't Hoff, Kedem-Katchalsky)",
            "Biomaterials (membrane fouling resistance)",
            "Chemical engineering (solute transport)"
        ],
        "system_architecture": {
            "description": "CSF shunt valve regulated by osmotic pressure differential across semipermeable membrane. Osmotic agent concentration on one side of membrane modulates effective drainage pressure based on CSF protein concentration or implanted osmotic reservoir.",
            "subsystems": [
                {"id": "SS-01", "name": "Semipermeable membrane", "function": "Selectively permeable to water, retains solutes; creates osmotic pressure differential", "status": "PROPOSED", "evidence_class": "PROPOSED", "evidence_source": "R332 mechanism + external membrane literature"},
                {"id": "SS-02", "name": "Osmotic agent reservoir", "function": "Contains solute at fixed concentration; provides osmotic pressure reference", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-03", "name": "CSF-facing chamber", "function": "CSF contacts membrane; osmotic differential drives water flux across membrane", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-04", "name": "Drainage outlet", "function": "Water (or CSF) drains to peritoneum based on net osmotic + hydrostatic pressure", "status": "PROPOSED", "evidence_class": "PROPOSED"}
            ],
            "osmotic_model": {
                "key_equations": [
                    EQUATIONS["vant_hoff"],
                    EQUATIONS["membrane_flux"],
                    EQUATIONS["hagen_poiseuille"]
                ],
                "osmotic_pressure": "pi = i * C * R * T (van 't Hoff); for solute concentration C, osmotic pressure pi proportional to concentration",
                "membrane_flux": "Jv = Lp * (dP - sigma * dPi), where Lp is hydraulic permeability, sigma is reflection coefficient, dPi is osmotic pressure differential",
                "critical_parameter": "Lp (membrane permeability), sigma (reflection coefficient), osmotic agent concentration C",
                "self_regulation_mechanism": "If CSF pressure rises, hydrostatic dP increases, increasing Jv (drainage); osmotic component provides additional regulation",
                "evidence_class": "MODELLED — membrane performance in CSF environment UNKNOWN"
            }
        },
        "mechanism_architecture": {
            "physical_changes": "CSF hydrostatic pressure + osmotic pressure differential across semipermeable membrane drive water flux; osmotic reservoir maintains reference pressure",
            "key_physics": "Two pressure sources in opposition: hydrostatic (ICP - outlet pressure) and osmotic (proportional to solute concentration differential). Net flux Jv = Lp * (dP_hydrostatic - sigma * dPi_osmotic).",
            "regulation_model": {
                "input": "CSF hydrostatic pressure + osmotic agent concentration",
                "model": "Membrane flux determined by net driving pressure: dP_net = dP_hydrostatic - sigma * dPi_osmotic",
                "regulation_behavior": "If CSF protein increases (raising dPi on CSF side), drainage decreases (self-regulating). If osmotic reservoir depletes, dPi drops, drainage increases.",
                "status": "MODELLED — no hardware validation"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "Semipermeable membrane flux governed by Kedem-Katchalsky equations. Net water flux depends on hydraulic pressure differential and osmotic pressure differential, scaled by membrane permeability Lp and reflection coefficient sigma.",
                "equations": [
                    EQUATIONS["vant_hoff"],
                    EQUATIONS["membrane_flux"],
                    "Jv = Lp * (dP - sigma * dPi)",
                    "Q_drainage = Jv * A_membrane   [volumetric drainage rate]",
                    "pi = i * C * R * T   [van 't Hoff osmotic pressure]"
                ],
                "assumptions": [
                    "Membrane is ideally semipermeable (sigma = 1) or partially permeable (sigma < 1)",
                    "Osmotic agent concentration stable over implantation lifetime (UNKNOWN — depends on reservoir design)",
                    "CSF protein concentration does not foul membrane significantly (UNKNOWN)",
                    "Temperature constant at 37°C",
                    "Membrane properties (Lp, sigma) stable over lifetime (UNKNOWN)"
                ],
                "boundary_conditions": [
                    "CSF side: ICP 5-40 mmHg + CSF osmotic pressure (~290 mOsm/kg physiological)",
                    "Reservoir side: hydrostatic pressure + osmotic agent concentration (design-dependent)",
                    "Membrane area A_membrane (design-dependent)",
                    "Temperature: 37°C constant"
                ],
                "input_variables": ["ICP", "CSF osmolarity", "Reservoir osmolarity", "Membrane properties (Lp, sigma, A)"],
                "output_variables": ["Drainage rate Q", "Net flux Jv"],
                "parameter_sensitivities": [
                    "Lp (hydraulic permeability) — directly scales drainage rate",
                    "sigma (reflection coefficient) — closer to 1 means stronger osmotic effect",
                    "C (osmotic agent concentration) — linear effect on osmotic pressure",
                    "A_membrane — linear effect on total drainage"
                ],
                "failure_regimes": [
                    "Lp too high -> excessive drainage (over-drainage)",
                    "Lp too low -> insufficient drainage (under-drainage)",
                    "sigma < 1 (leaky membrane) -> osmotic agent leaks, regulation lost",
                    "Membrane fouling -> Lp decreases over time, drainage drops",
                    "Osmotic reservoir depletion -> dPi drops, drainage increases (potentially over-drainage)"
                ]
            },
            "critical_parameters": [
                {"name": "Membrane hydraulic permeability Lp", "value": "UNKNOWN — design choice", "unit": "m/(Pa·s)", "basis": "Membrane selection", "evidence_class": "UNKNOWN", "verification_requirement": "ASTM D3985 permeation test"},
                {"name": "Reflection coefficient sigma", "value": "UNKNOWN — design choice", "unit": "dimensionless", "basis": "Membrane selection", "evidence_class": "UNKNOWN", "verification_requirement": "Membrane characterization"},
                {"name": "Osmotic agent concentration C", "value": "UNKNOWN — design choice (e.g., NaCl, mannitol, dextran)", "unit": "mol/L", "basis": "Design choice", "evidence_class": "UNKNOWN"},
                {"name": "Membrane area A", "value": "UNKNOWN", "unit": "m^2", "basis": "Geometry", "evidence_class": "UNKNOWN"},
                {"name": "Reservoir volume", "value": "UNKNOWN — determines lifetime before depletion", "unit": "mL", "basis": "Design choice", "evidence_class": "UNKNOWN"},
                {"name": "Membrane fouling rate", "value": "UNKNOWN in CSF environment", "unit": "%/day", "basis": "UNKNOWN", "evidence_class": "UNKNOWN", "verification_requirement": "Fouling study in CSF mimic"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — published osmotic pump literature (DURECT Alzet, Viadur) establishes that osmotic-driven devices are manufacturable and clinically used. It does NOT establish that the proposed osmotically-regulated CSF drainage valve achieves clinically useful performance in CSF environment.",
            "proposed_design": {
                "input": "CSF hydrostatic pressure + osmotic differential",
                "mechanism": "Semipermeable membrane with osmotic reservoir provides pressure-dependent drainage regulation",
                "transformation": "(dP_hydrostatic, dPi_osmotic) -> net flux Jv -> drainage rate Q",
                "output": "Drainage rate regulated by combined hydrostatic + osmotic pressure",
                "component_architecture": "Ventricular catheter -> CSF chamber with membrane -> osmotic reservoir -> drainage outlet -> peritoneal catheter"
            },
            "failure_modes": [
                {"mode": "Membrane fouling", "mechanism": "CSF proteins, cells, or debris accumulate on membrane surface, reducing Lp", "design_feature": "Semipermeable membrane", "evidence": "Standard membrane failure mode", "mitigation": "Fouling-resistant membrane coating; larger membrane area; pre-filter", "verification_test": "Fouling study in CSF mimic", "residual_uncertainty": "UNKNOWN fouling rate in vivo"},
                {"mode": "Osmotic reservoir depletion", "mechanism": "Osmotic agent diffuses across membrane over time", "design_feature": "Reservoir + membrane", "evidence": "Standard osmotic device failure", "mitigation": "Larger reservoir; membrane with low osmotic agent permeability", "verification_test": "Aging study with concentration measurement", "residual_uncertainty": "UNKNOWN depletion rate"},
                {"mode": "Membrane rupture", "mechanism": "Mechanical or chemical damage to membrane", "design_feature": "Semipermeable membrane", "evidence": "Standard membrane failure", "mitigation": "Membrane material selection + mechanical protection", "verification_test": "Burst pressure test", "residual_uncertainty": "UNKNOWN in vivo mechanical environment"},
                {"mode": "Lp out of spec (too high or low)", "mechanism": "Manufacturing variation or material drift", "design_feature": "Membrane", "evidence": "Standard manufacturing tolerance", "mitigation": "Cpk study + tolerance analysis", "verification_test": "Cpk measurement", "residual_uncertainty": "UNKNOWN achievable Cpk"},
                {"mode": "Osmotic agent biocompatibility", "mechanism": "Osmotic agent leaks into CSF or tissue, causing irritation", "design_feature": "Osmotic agent selection", "evidence": "Standard biocompatibility concern", "mitigation": "Biocompatible osmotic agent selection (e.g., NaCl, mannitol)", "verification_test": "ISO 10993 + leachability study", "residual_uncertainty": "UNKNOWN long-term biocompatibility"},
                {"mode": "Over-drainage if reservoir fails", "mechanism": "If reservoir depletes, dPi drops, drainage increases", "design_feature": "Osmotic regulation", "evidence": "MODELLED", "mitigation": "Secondary hydrostatic valve as safety floor", "verification_test": "Reservoir depletion simulation", "residual_uncertainty": "UNKNOWN failure rate"},
                {"mode": "CSF osmolarity variation", "mechanism": "Patient CSF osmolarity varies from physiological", "design_feature": "Membrane regulation", "evidence": "Standard physiological variation", "mitigation": "Margin in design", "verification_test": "Sensitivity analysis", "residual_uncertainty": "UNKNOWN clinical CSF osmolarity range"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "Membrane Lp and sigma within target range", "method": "ASTM D3985 permeation test", "acceptance": "Lp and sigma in target range", "evidence_class": "PROPOSED", "standard": "ASTM_D3985"},
                {"id": "VER-002", "requirement": "Drainage rate at physiological pressures", "method": "Bench flow test with mock CSF", "acceptance": "Q in target range (likely 0.1-0.5 mL/min)", "evidence_class": "PROPOSED"},
                {"id": "VER-003", "requirement": "Self-regulation (response to pressure change)", "method": "Bench pressure step test", "acceptance": "Drainage adjusts proportionally to pressure", "evidence_class": "PROPOSED"},
                {"id": "VER-004", "requirement": "Membrane stability over lifetime", "method": "Aging study with periodic Lp measurement", "acceptance": "Lp drift < 30% over target lifetime", "evidence_class": "PROPOSED"},
                {"id": "VER-005", "requirement": "Fouling resistance in CSF mimic", "method": "Fouling study with protein challenge", "acceptance": "Lp reduction < 30% over target lifetime", "evidence_class": "PROPOSED"},
                {"id": "VER-006", "requirement": "Biocompatibility ISO 10993", "method": "ISO 10993 series", "acceptance": "Pass", "evidence_class": "PROPOSED", "standard": "ISO_10993"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "Drainage regulation in animal model", "method": "In vivo study (IACUC)", "acceptance": "Drainage remains within safe range over physiologic pressure variation", "evidence_class": "UNKNOWN"},
                {"id": "VAL-002", "requirement": "Clinical drainage performance", "method": "Clinical trial (IDE)", "acceptance": "Comparable or superior to standard shunt", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Achievable membrane Lp and sigma in CSF environment — UNKNOWN",
                "Membrane fouling rate in CSF — UNKNOWN (critical)",
                "Osmotic reservoir depletion rate — UNKNOWN",
                "Optimal osmotic agent — UNKNOWN (NaCl vs mannitol vs dextran, etc.)",
                "Membrane lifetime in vivo — UNKNOWN",
                "Regulatory pathway (likely Class III PMA — no predicate for osmotic CSF valve) — UNKNOWN",
                "Clinical benefit magnitude — UNKNOWN until trial"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "Passive self-regulating CSF drainage; existing valves are fixed-pressure or pressure-activated (R332)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "Osmotic pressure regulating drainage valve using semipermeable membrane", "evidence_class": "MODELLED", "source": "R332"},
            {"id": "DI-003", "input": "CSF osmolarity (physiological)", "value": "EXTERNAL_PRECEDENT (~290 mOsm/kg)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-004", "input": "ICP range", "value": "5-40 mmHg (normal to pathological)", "evidence_class": "VERIFIED"},
            {"id": "DI-005", "input": "Drainage target", "value": "MODELLED ~0.3 mL/min typical", "evidence_class": "MODELLED"},
            {"id": "DI-006", "input": "Membrane properties (Lp, sigma)", "value": "UNKNOWN — design choice", "evidence_class": "UNKNOWN", "resolution_plan": "Membrane selection + characterization"},
            {"id": "DI-007", "input": "Osmotic agent", "value": "UNKNOWN — design choice (NaCl, mannitol, dextran, etc.)", "evidence_class": "UNKNOWN"},
            {"id": "DI-008", "input": "Biocompatibility (ISO 10993)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 series for membrane + osmotic agent + housing"},
            {"id": "DI-009", "input": "Sterilization", "value": "UNKNOWN — membrane may be gamma-sensitive; aseptic or EtO", "evidence_class": "UNKNOWN", "resolution_plan": "Sterilization validation"},
            {"id": "DI-010", "input": "Membrane fouling environment", "value": "CSF contains proteins, cells — fouling risk", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-011", "input": "ISO 7437 (CSF shunts)", "value": "UNKNOWN — applicability to be confirmed", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 7437 series"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Semipermeable membrane design (material, geometry, Lp, sigma)", "status": "ABSENT", "design_status": "DESIGN_BLOCKED", "missing_inputs": ["Membrane material selection", "Lp target", "sigma target", "Geometry"]},
            {"id": "DO-002", "description": "Osmotic reservoir design (volume, agent, replenishment)", "status": "ABSENT", "design_status": "DESIGN_BLOCKED", "missing_inputs": ["Agent selection", "Reservoir volume", "Lifetime target"]},
            {"id": "DO-003", "description": "Integrated valve + membrane + reservoir assembly", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["Component layout", "Housing design"]},
            {"id": "DO-004", "description": "Bench test protocol (permeation, fouling, aging)", "status": "CONCEPTUAL", "design_status": "PROTOCOL_DEVELOPMENT"}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "Membrane Lp and sigma within target", "method": "ASTM D3985", "acceptance": "Within target", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "ASTM_D3985"},
            {"id": "V-002", "requirement": "Drainage rate in physiological range", "method": "Bench flow", "acceptance": "Q in target range", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-003", "requirement": "Self-regulation (pressure response)", "method": "Pressure step bench test", "acceptance": "Proportional response", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-004", "requirement": "Membrane stability over lifetime", "method": "Aging with Lp measurement", "acceptance": "Drift < 30%", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-005", "requirement": "Fouling resistance", "method": "Protein challenge study", "acceptance": "Lp reduction < 30%", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-006", "requirement": "Biocompatibility ISO 10993", "method": "ISO 10993", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED", "standard": "ISO_10993"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "Drainage regulation in animal model", "method": "In vivo (IACUC)", "acceptance": "Drainage within safe range", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"},
            {"id": "VAL-002", "requirement": "Clinical drainage performance", "method": "Clinical trial (IDE)", "acceptance": "Comparable or superior to standard", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "Semipermeable membrane (custom)", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED", "material": "UNKNOWN — likely cellulose acetate, polyamide, or PES", "supplier": "UNKNOWN — membrane manufacturer", "criticality": "CRITICAL", "verification": "Lp + sigma + biocompatibility"},
            {"item": "02", "description": "Osmotic reservoir housing", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard implantable housing", "material": "UNKNOWN — likely polymer + radiopaque marker", "supplier": "UNKNOWN", "criticality": "HIGH", "verification": "Hermeticity + biocompatibility"},
            {"item": "03", "description": "Osmotic agent (NaCl, mannitol, or dextran)", "qty": "Reservoir volume", "component_type": "CONSUMABLE", "source_basis": "EXTERNAL_PRECEDENT (standard osmotic agents)", "material": "NaCl or mannitol or dextran", "supplier": "Multiple (USP-grade)", "criticality": "HIGH", "verification": "Purity + leachability"},
            {"item": "04", "description": "Valve housing + catheter connections", "qty": "1 set", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard CSF shunt housing", "material": "UNKNOWN — likely silicone/Ti composite", "supplier": "Multiple", "criticality": "HIGH", "verification": "Dimensional + biocompatibility"}
        ],
        "materials": [
            {"component": "Semipermeable membrane", "candidate_material": "Cellulose acetate", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard dialysis membrane material", "verification_required": "ISO 10993 + Lp/sigma characterization + fouling", "status": "CANDIDATE"},
            {"component": "Semipermeable membrane", "candidate_material": "Polyethersulfone (PES)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard membrane material", "verification_required": "ISO 10993 + Lp/sigma + fouling", "status": "CANDIDATE"},
            {"component": "Semipermeable membrane", "candidate_material": "Polyamide (nylon)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Membrane material", "verification_required": "ISO 10993 + Lp/sigma + fouling", "status": "CANDIDATE"},
            {"component": "Osmotic agent", "candidate_material": "NaCl (sodium chloride)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard physiological osmotic agent", "verification_required": "Purity + leachability + biocompatibility", "status": "CANDIDATE"},
            {"component": "Osmotic agent", "candidate_material": "Mannitol", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard osmotic agent in medical use", "verification_required": "Purity + leachability", "status": "CANDIDATE"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Membrane fabrication (phase inversion or track-etch)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard membrane manufacturing", "tolerance_implication": "Lp variation 10-30% lot-to-lot", "note": "Requires membrane manufacturer partnership"},
                {"process": "Reservoir filling + sealing", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard osmotic pump manufacturing (DURECT)", "tolerance_implication": "Fill volume ±5%", "note": "Aseptic filling required if terminal sterilization incompatible"},
                {"process": "Housing injection molding + assembly", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard implantable device manufacturing", "tolerance_implication": "±0.02 mm typical", "note": "Custom for membrane integration"}
            ],
            "status": "ENGINEERING_CANDIDATE — no osmotic CSF valve process validated"
        },
        "failure_analysis": [
            {"failure_mode": "Membrane fouling (CRITICAL)", "mechanism": "CSF proteins/cells accumulate on membrane", "design_feature_affected": "Semipermeable membrane", "evidence": "Standard membrane failure", "mitigation": "Fouling-resistant coating + larger area + pre-filter", "verification_test": "Fouling study in CSF mimic", "residual_uncertainty": "UNKNOWN fouling rate in vivo"},
            {"failure_mode": "Osmotic reservoir depletion", "mechanism": "Agent diffuses across membrane", "design_feature_affected": "Reservoir + membrane", "evidence": "Standard osmotic device failure", "mitigation": "Larger reservoir + low-permeability membrane", "verification_test": "Aging with concentration measurement", "residual_uncertainty": "UNKNOWN depletion rate"},
            {"failure_mode": "Membrane rupture", "mechanism": "Mechanical/chemical damage", "design_feature_affected": "Membrane", "evidence": "Standard membrane failure", "mitigation": "Material selection + mechanical protection", "verification_test": "Burst pressure test", "residual_uncertainty": "UNKNOWN in vivo mechanical environment"},
            {"failure_mode": "Lp out of spec (manufacturing)", "mechanism": "Manufacturing variation", "design_feature_affected": "Membrane", "evidence": "Standard manufacturing tolerance", "mitigation": "Cpk study + tolerance", "verification_test": "Cpk measurement", "residual_uncertainty": "UNKNOWN achievable Cpk"},
            {"failure_mode": "Osmotic agent biocompatibility", "mechanism": "Agent leaks into CSF/tissue", "design_feature_affected": "Osmotic agent + membrane", "evidence": "Standard biocompatibility concern", "mitigation": "Biocompatible agent + low-leak membrane", "verification_test": "ISO 10993 + leachability", "residual_uncertainty": "UNKNOWN long-term biocompatibility"},
            {"failure_mode": "Over-drainage if reservoir fails", "mechanism": "Reservoir depletion -> dPi drops -> drainage increases", "design_feature_affected": "Osmotic regulation", "evidence": "MODELLED", "mitigation": "Secondary hydrostatic valve as safety floor", "verification_test": "Reservoir depletion simulation", "residual_uncertainty": "UNKNOWN failure rate"},
            {"failure_mode": "CSF osmolarity variation", "mechanism": "Patient CSF osmolarity varies", "design_feature_affected": "Regulation", "evidence": "Standard physiological variation", "mitigation": "Margin in design", "verification_test": "Sensitivity analysis", "residual_uncertainty": "UNKNOWN clinical osmolarity range"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "Membrane specimens (various materials + geometries)", "equipment": "Permeation test cell (ASTM D3985), pressure transducer", "design_work": "Membrane material + geometry selection", "measurement": "Lp, sigma, burst pressure", "acceptance_criterion": "Lp + sigma in target range; burst > 100 mmHg", "dependency": "Membrane vendor", "deliverable": "Membrane spec", "estimated_effort": "10 weeks"},
            {"work_package": "WP-02", "test_article": "Integrated valve prototype (membrane + reservoir)", "equipment": "Bench flow loop, mock CSF, pressure sensors", "design_work": "Integrated assembly design", "measurement": "Drainage rate vs pressure; self-regulation response", "acceptance_criterion": "Q in target range; proportional response to pressure", "dependency": "WP-01 + reservoir design", "deliverable": "Integrated performance report", "estimated_effort": "10 weeks"},
            {"work_package": "WP-03", "test_article": "Fouling test articles (membrane in CSF mimic with protein)", "equipment": "Aging chamber, Lp measurement", "design_work": "Fouling protocol", "measurement": "Lp vs time with protein challenge", "acceptance_criterion": "Lp reduction < 30% over target lifetime", "dependency": "WP-01", "deliverable": "Fouling report", "estimated_effort": "12-24 weeks (chronic)"},
            {"work_package": "WP-04", "test_article": "Reservoir aging specimens", "equipment": "Aging chamber, osmotic concentration measurement", "design_work": "Aging protocol", "measurement": "Osmotic agent concentration vs time", "acceptance_criterion": "Concentration retained > 50% at target lifetime", "dependency": "WP-02", "deliverable": "Reservoir stability report", "estimated_effort": "12-24 weeks"},
            {"work_package": "WP-05", "test_article": "Biocompatibility specimens", "equipment": "ISO 10993 lab", "design_work": "Material selection frozen", "measurement": "ISO 10993 series", "acceptance_criterion": "Pass", "dependency": "Material selection", "deliverable": "ISO 10993 report", "estimated_effort": "12 weeks (external)"},
            {"work_package": "WP-06", "test_article": "In vivo drainage study", "equipment": "Animal facility", "design_work": "IACUC protocol", "measurement": "Drainage regulation in animal model", "acceptance_criterion": "Drainage within safe range over physiologic variation", "dependency": "WP-02 + WP-03", "deliverable": "In vivo drainage report", "estimated_effort": "20 weeks"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "Osmotic regulation concept + mechanism description",
                "Van 't Hoff + Kedem-Katchalsky governing equations",
                "Bench test protocols (permeation, fouling, aging, drainage)",
                "External precedent catalog (osmotic pumps: DURECT, Alzet)",
                "Critical UNKNOWN disclosure (membrane fouling rate, reservoir depletion rate)",
                "This engineering dossier with failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Production membrane design (material, geometry, Lp, sigma)",
                "Osmotic reservoir design (agent, volume, lifetime)",
                "Manufacturing process for membrane + reservoir + valve integration",
                "Regulatory submission (likely Class III PMA — no predicate for osmotic CSF valve)",
                "Clinical validation (drainage performance endpoint)",
                "Long-term fouling + depletion data"
            ]
        }
    }
