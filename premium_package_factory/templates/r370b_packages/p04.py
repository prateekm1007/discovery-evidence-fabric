"""
p04.py — P-04 Catalytic Contact Time Lock engineering core.
Domain: enzyme kinetics / molecular transport / clearance / catheter delivery.

Governing model: Michaelis-Menten + Fick diffusion + Damkohler number.
External precedent: published neprilysin (NEP) kinetics literature.
"""
from .constants import EQUATIONS, STANDARDS


def get_data():
    return {
        "technology_domain": "Enzymatic Catalysis + Mass Transport",
        "engineering_disciplines": [
            "Enzyme kinetics",
            "Mass transport (diffusion + convection)",
            "Surface chemistry (enzyme immobilization)",
            "Biomaterials (catheter coatings)"
        ],
        "system_architecture": {
            "description": "Catheter with immobilized neprilysin (NEP) enzyme on inner lumen wall; CSF flows past, Aβ42 in CSF contacts enzyme for sufficient time (contact-time lock) to undergo catalytic cleavage",
            "subsystems": [
                {"id": "SS-01", "name": "Catheter body (substrate)", "function": "Carries CSF flow + supports enzyme coating", "status": "MODELLED", "evidence_source": "R332 mechanism"},
                {"id": "SS-02", "name": "NEP-immobilized coating on inner lumen", "function": "Catalytic surface cleaves Aβ42 peptides via NEP activity", "status": "PROPOSED", "evidence_class": "PROPOSED", "evidence_source": "R332 mechanism + external NEP literature"},
                {"id": "SS-03", "name": "Contact-time control geometry", "function": "Catheter length and flow rate engineered so Aβ42 residence time exceeds critical contact time for catalytic cleavage", "status": "MODELLED", "evidence_class": "MODELLED", "evidence_source": "R332 mechanism"},
                {"id": "SS-04", "name": "Stabilization matrix for enzyme", "function": "Preserves NEP activity over implantation lifetime (likely PEGylation or trehalose stabilization)", "status": "PROPOSED", "evidence_class": "PROPOSED"}
            ],
            "enzyme_kinetics": {
                "key_equations": [
                    EQUATIONS["michaelis_menten"],
                    EQUATIONS["fick_1st"],
                    EQUATIONS["damkohler"]
                ],
                "mass_transport_regime": "Convection-diffusion in CSF lumen: Pe = (v*L)/D; for catheter ID ~1 mm at 0.3 mL/min, Pe ~100 (convection-dominated)",
                "critical_parameter": "Damköhler number Da = (k_cat * Gamma * L) / (v * d), where Gamma = enzyme surface density, v = flow velocity, d = lumen diameter. Da > 1 required for transport-limited clearance.",
                "clearance_target": "Reduce Aβ42 concentration by >= 30% per catheter pass (MODELLED, NOT verified)",
                "evidence_class": "MODELLED"
            }
        },
        "mechanism_architecture": {
            "physical_changes": "Aβ42 peptides in CSF contact immobilized NEP during catheter transit; NEP catalyzes proteolytic cleavage of Aβ42 into inactive fragments, reducing CSF Aβ42 burden",
            "key_physics": "Mass-transport-limited enzyme catalysis: rate v = min(Vmax·[S]/(Km+[S]), J_conv), where J_conv is convective delivery of Aβ42 to the enzyme surface",
            "kinetic_model": {
                "input": "CSF Aβ42 concentration (typical range 100-1000 pg/mL in AD patients, per external literature)",
                "model": "1D advection-diffusion-reaction: d(Aβ)/dt = -v·d(Aβ)/dx + D·d²(Aβ)/dx² - k_cat·Γ·(Aβ)/(Km+Aβ)",
                "prediction_horizon": "Steady-state clearance per pass; long-term Aβ reduction requires chronic use",
                "status": "MODELLED — no in vitro verification of clearance magnitude yet"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "Mass-transport-limited enzyme catalysis in catheter lumen. Reaction rate is bounded by either enzyme kinetics (Michaelis-Menten) or convective delivery of substrate to enzyme surface, whichever is smaller.",
                "equations": [
                    EQUATIONS["michaelis_menten"],
                    EQUATIONS["fick_1st"],
                    EQUATIONS["damkohler"],
                    "Pe = (v * L) / D   [Péclet number, convective vs diffusive transport]",
                    "k_cat_obs = k_cat * (1 - deactivation(t))   [enzyme deactivation over time]"
                ],
                "assumptions": [
                    "NEP retains activity when immobilized (external precedent, NOT verified for this coating)",
                    "Aβ42 is the rate-limiting substrate (other peptides may compete; UNKNOWN)",
                    "CSF Aβ42 concentration in catheter inlet matches published ranges",
                    "Enzyme surface density Gamma is uniform (process-dependent)",
                    "No significant product inhibition (UNKNOWN for Aβ fragments)"
                ],
                "boundary_conditions": [
                    "Inlet: Aβ42 = 100-1000 pg/mL (pathological range, per literature)",
                    "Outlet: Aβ42 reduced by clearance fraction",
                    "Wall: enzyme-bound reaction sink (Robin BC)",
                    "Lumen: CSF flow at 0.3 mL/min typical"
                ],
                "input_variables": ["CSF flow rate Q", "Inlet Aβ42 concentration", "Catheter length L", "Lumen diameter d", "Enzyme surface density Gamma"],
                "output_variables": ["Outlet Aβ42 concentration", "Clearance fraction per pass"],
                "parameter_sensitivities": [
                    "k_cat (turnover number) — directly scales Vmax; literature values vary 10-100 s^-1 for NEP depending on assay",
                    "Gamma (surface density) — scales Vmax; UNKNOWN achievable density on catheter surface",
                    "L (catheter length) — linear increase in contact time and clearance",
                    "Q (flow rate) — inverse: lower Q = longer contact time = more clearance, but less total CSF processed",
                    "Enzyme deactivation rate — most critical unknown for chronic implantation"
                ],
                "failure_regimes": [
                    "Da << 1 (transport-limited) — clearance is limited by delivery to enzyme; increasing Gamma does NOT help",
                    "Da >> 1 (kinetics-limited) — clearance is limited by enzyme activity; increasing L does NOT help",
                    "Gamma_t << Gamma_initial (enzyme deactivation) — activity falls below useful threshold over time",
                    "Competitive inhibition by other CSF peptides — UNKNOWN magnitude"
                ]
            },
            "critical_parameters": [
                {"name": "NEP k_cat", "value": "EXTERNAL_PRECEDENT (published values 10-100 s^-1, varies by assay)", "unit": "s^-1", "basis": "Published NEP kinetics literature", "evidence_class": "EXTERNAL_PRECEDENT", "verification_requirement": "Independent assay on immobilized form"},
                {"name": "NEP Km for Aβ42", "value": "EXTERNAL_PRECEDENT (published ~5-20 μM range)", "unit": "μM", "basis": "Published NEP kinetics literature", "evidence_class": "EXTERNAL_PRECEDENT", "verification_requirement": "Independent assay on immobilized form"},
                {"name": "Enzyme surface density Gamma", "value": "UNKNOWN", "unit": "mol/m^2", "basis": "Design choice + coating process capability", "evidence_class": "UNKNOWN", "verification_requirement": "Surface assay (e.g., fluorescent labeling, activity assay)"},
                {"name": "Catheter length L", "value": "UNKNOWN", "unit": "m", "basis": "Design choice balancing clearance vs anatomy", "evidence_class": "UNKNOWN", "verification_requirement": "Geometric specification"},
                {"name": "Lumen diameter d", "value": "UNKNOWN", "unit": "m", "basis": "Standard shunt catheter ~1-1.5 mm ID", "evidence_class": "EXTERNAL_PRECEDENT", "verification_requirement": "Specification"},
                {"name": "Contact time tau", "value": "UNKNOWN", "unit": "s", "basis": "Derived: tau = L/v", "evidence_class": "MODELLED", "verification_requirement": "Flow visualization"},
                {"name": "Enzyme half-life t_1/2", "value": "UNKNOWN", "unit": "days", "basis": "UNKNOWN for immobilized NEP in CSF", "evidence_class": "UNKNOWN", "verification_requirement": "Aging study in CSF-mimicking fluid"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — published NEP kinetics and immobilization chemistry establish that NEP can cleave Aβ42 in solution and that NEP can be immobilized on surfaces. They do NOT establish that the proposed catheter achieves clinically meaningful Aβ42 clearance in CSF.",
            "proposed_design": {
                "input": "CSF containing Aβ42 at pathological concentrations",
                "mechanism": "NEP-immobilized catheter surface catalyzes Aβ42 cleavage during CSF transit",
                "transformation": "Aβ42 (substrate) -> Aβ fragments (inactive products) + clearance",
                "output": "CSF with reduced Aβ42 concentration at catheter outlet",
                "component_architecture": "Catheter body -> enzyme coating on inner lumen -> CSF flow path -> outlet"
            },
            "failure_modes": [
                {"mode": "Enzyme deactivation", "mechanism": "Protein denaturation, proteolysis, or surface desorption over time", "design_feature": "NEP coating", "evidence": "Standard protein stability challenge (PMC11651204 NEP review)", "mitigation": "Stabilization matrix (PEGylation, trehalose) + spare activity margin", "verification_test": "Chronic aging study in CSF-mimicking fluid", "residual_uncertainty": "UNKNOWN achievable half-life"},
                {"mode": "Mass transport limit", "mechanism": "If Da < 1, clearance limited by delivery, not enzyme", "design_feature": "Catheter geometry + flow rate", "evidence": "MODELLED via Pe and Da analysis", "mitigation": "Lengthen L or reduce Q (with clinical tradeoffs)", "verification_test": "Da measurement", "residual_uncertainty": "UNKNOWN actual Da in vivo"},
                {"mode": "Immune response to enzyme", "mechanism": "Host immune system recognizes NEP as foreign", "design_feature": "NEP coating", "evidence": "UNKNOWN for NEP specifically; general implantable-protein concern", "mitigation": "PEGylation or immunosuppressive coating", "verification_test": "In vivo biocompatibility study", "residual_uncertainty": "UNKNOWN immunogenicity"},
                {"mode": "Substrate competition", "mechanism": "Other CSF peptides compete for NEP active site", "design_feature": "NEP specificity", "evidence": "NEP is known to cleave multiple substrates (substance P, bradykinin, etc.)", "mitigation": "UNKNOWN — specificity engineering may be required", "verification_test": "Competition assay in CSF", "residual_uncertainty": "UNKNOWN competitive magnitude"},
                {"mode": "Coating delamination", "mechanism": "Mechanical or chemical degradation of coating-catheter bond", "design_feature": "Enzyme-catheter interface", "evidence": "Standard coating failure mode", "mitigation": "Covalent immobilization chemistry + mechanical testing", "verification_test": "ASTM D3359 adhesion + fatigue", "residual_uncertainty": "UNKNOWN long-term adhesion"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "NEP coating activity per unit area", "method": "In vitro activity assay with fluorescent substrate", "acceptance": "Achievable Gamma * k_cat meets model requirement", "evidence_class": "PROPOSED"},
                {"id": "VER-002", "requirement": "Clearance per catheter pass", "method": "Bench flow loop with Aβ42-spiked mock CSF", "acceptance": ">=30% reduction per pass (MODEL_DERIVED target)", "evidence_class": "PROPOSED"},
                {"id": "VER-003", "requirement": "Enzyme activity over simulated implantation lifetime", "method": "Aging study in CSF-mimicking fluid at 37°C", "acceptance": "Activity retained > 50% at target lifetime (UNKNOWN target lifetime)", "evidence_class": "PROPOSED"},
                {"id": "VER-004", "requirement": "Biocompatibility per ISO 10993", "method": "Standard ISO 10993 series tests", "acceptance": "Pass all applicable ISO 10993 endpoints", "evidence_class": "PROPOSED", "standard": "ISO_10993"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "CSF Aβ42 reduction in patient cohort", "method": "Clinical trial (IDE required) measuring CSF Aβ42 before/after shunt", "acceptance": "Statistically significant Aβ42 reduction vs control shunt", "evidence_class": "UNKNOWN"},
                {"id": "VAL-002", "requirement": "Clinical benefit (cognitive, functional)", "method": "Long-term clinical trial", "acceptance": "Unknown — no established clinical endpoint for chronic Aβ42 reduction", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Achievable enzyme surface density Gamma on catheter inner lumen — UNKNOWN",
                "Enzyme half-life in CSF environment — UNKNOWN",
                "In vivo clearance per pass — UNKNOWN",
                "Immunogenicity of immobilized NEP — UNKNOWN",
                "Substrate competition magnitude — UNKNOWN",
                "Clinical endpoint for chronic Aβ42 reduction — UNKNOWN (no established surrogate)",
                "Regulatory pathway — UNKNOWN (likely Class III PMA; no predicate for enzymatic catheter)"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "Aβ accumulation in CSF of Alzheimer's/NPH patients with shunts; no enzymatic clearance exists (R332 problem)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "NEP enzyme immobilized on catheter wall clears Aβ42 via mass-transport-limited contact time", "evidence_class": "MODELLED", "source": "R332"},
            {"id": "DI-003", "input": "CSF Aβ42 range (pathological)", "value": "100-1000 pg/mL (external literature, AD patients)", "evidence_class": "EXTERNAL_PRECEDENT"},
            {"id": "DI-004", "input": "Clearance target per pass", "value": ">= 30% (MODEL_DERIVED, R332)", "evidence_class": "MODELLED", "source": "R332"},
            {"id": "DI-005", "input": "Enzyme kinetics (k_cat, Km)", "value": "EXTERNAL_PRECEDENT (published values, varies by assay)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "External NEP literature"},
            {"id": "DI-006", "input": "Flow rate (CSF through shunt)", "value": "~0.3 mL/min typical (R332)", "evidence_class": "VERIFIED"},
            {"id": "DI-007", "input": "Biocompatibility (ISO 10993)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 series for enzyme coating + catheter material", "applicability": "APPLICABLE"},
            {"id": "DI-008", "input": "Sterilization", "value": "UNKNOWN — enzyme incompatible with gamma; likely EtO or aseptic assembly", "evidence_class": "UNKNOWN", "resolution_plan": "Sterilization validation per ISO 11135 (EtO); aseptic processing if EtO incompatible"},
            {"id": "DI-009", "input": "Enzyme source / manufacturing", "value": "UNKNOWN — recombinant NEP needed", "evidence_class": "UNKNOWN", "resolution_plan": "Recombinant protein manufacturing + lot release criteria"},
            {"id": "DI-010", "input": "Coating uniformity / quality", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "Coating process development + QC specs"},
            {"id": "DI-011", "input": "Shelf life (with active enzyme)", "value": "UNKNOWN — likely cold-chain dependent", "evidence_class": "UNKNOWN", "resolution_plan": "Stability study per ICH Q1A"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Catheter with NEP coating (length, ID, coating density)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["Final length L", "Coating process Gamma spec", "Coating uniformity spec"]},
            {"id": "DO-002", "description": "NEP coating process specification", "status": "ABSENT", "design_status": "PROCESS_DEVELOPMENT_BLOCKED", "missing_inputs": ["Covalent vs adsorption chemistry", "Curing protocol", "QC release criteria"]},
            {"id": "DO-003", "description": "Recombinant NEP production process", "status": "ABSENT", "design_status": "PROCESS_DEVELOPMENT_BLOCKED", "missing_inputs": ["Expression system (E. coli vs CHO)", "Purification protocol", "Lot release criteria"]},
            {"id": "DO-004", "description": "Clearance verification test method", "status": "CONCEPTUAL", "design_status": "PROTOCOL_DEVELOPMENT", "note": "Bench protocol sketched in R332; not validated"}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "NEP coating activity per unit area", "method": "Fluorescent substrate assay", "acceptance": "Gamma * k_cat meets model requirement", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-002", "requirement": "Clearance per pass >= 30%", "method": "Bench flow loop with Aβ42 mock CSF", "acceptance": ">= 30% reduction", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-003", "requirement": "Enzyme stability over implantation lifetime", "method": "Aging study at 37°C in CSF mimic", "acceptance": "Activity retained > 50% at target lifetime", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-004", "requirement": "Biocompatibility ISO 10993", "method": "Standard ISO 10993 series", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "CSF Aβ42 reduction in patient cohort", "method": "Clinical trial (IDE required)", "acceptance": "Statistically significant vs control", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"},
            {"id": "VAL-002", "requirement": "Clinical benefit", "method": "Long-term trial", "acceptance": "Unknown — no established endpoint", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "Catheter body (substrate)", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED (from mechanism)", "material": "UNKNOWN — likely silicone/polyurethane (external precedent)", "supplier": "UNKNOWN", "criticality": "CRITICAL", "verification": "Bench + biocompatibility"},
            {"item": "02", "description": "Recombinant NEP enzyme", "qty": "Micrograms per catheter", "component_type": "CUSTOM_BIOLOGIC", "source_basis": "EXTERNAL_PRECEDENT for recombinant NEP", "material": "Protein", "supplier": "UNKNOWN — recombinant protein manufacturer", "criticality": "CRITICAL", "verification": "Activity assay + purity + sterility"},
            {"item": "03", "description": "Coating chemistry reagents", "qty": "Process-scale", "component_type": "CONSUMABLE", "source_basis": "ENGINEERING_PROPOSED", "material": "EDC/NHS or similar coupling chemistry", "supplier": "Multiple (Sigma, Thermo Fisher)", "criticality": "HIGH", "verification": "Coating QC"},
            {"item": "04", "description": "Stabilization matrix (e.g., PEG, trehalose)", "qty": "Process-scale", "component_type": "CONSUMABLE", "source_basis": "EXTERNAL_PRECEDENT for protein stabilization", "material": "PEG or trehalose", "supplier": "Multiple", "criticality": "HIGH", "verification": "Stability study"}
        ],
        "materials": [
            {"component": "Catheter body", "candidate_material": "Silicone elastomer", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard CSF shunt material", "verification_required": "ISO 10993 + coating adhesion", "status": "CANDIDATE"},
            {"component": "Catheter body", "candidate_material": "Polyurethane", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Some shunts use polyurethane", "verification_required": "ISO 10993 + coating adhesion", "status": "CANDIDATE"},
            {"component": "Enzyme coating", "candidate_material": "Recombinant human NEP (neprilysin)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Published NEP literature (PMC11651204, PLOS ONE 0229850)", "verification_required": "Activity assay + stability + immunogenicity", "status": "CANDIDATE"},
            {"component": "Immobilization chemistry", "candidate_material": "Covalent EDC/NHS coupling", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard protein immobilization chemistry", "verification_required": "Coupling efficiency + leachability", "status": "CANDIDATE"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Recombinant NEP production (E. coli or CHO expression)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard recombinant protein manufacturing", "tolerance_implication": "Lot-to-lot activity variation typically 10-30%", "note": "Requires GMP manufacturer partnership"},
                {"process": "Covalent enzyme immobilization on catheter inner lumen", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard protein immobilization chemistry", "tolerance_implication": "Surface density variation depends on process control", "note": "Custom process development required"},
                {"process": "Aseptic assembly (likely; enzyme incompatible with terminal sterilization)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard aseptic processing", "tolerance_implication": "ISO Class 7 cleanroom required", "note": "EtO may be evaluated but enzyme sensitivity UNKNOWN"}
            ],
            "status": "ENGINEERING_CANDIDATE — no process validated for chronic enzyme-active catheter"
        },
        "failure_analysis": [
            {"failure_mode": "Enzyme deactivation (chronic)", "mechanism": "Protein denaturation, proteolysis, surface desorption", "design_feature_affected": "NEP coating", "evidence": "Standard protein stability challenge", "mitigation": "Stabilization matrix + spare activity margin", "verification_test": "Aging study in CSF mimic", "residual_uncertainty": "UNKNOWN achievable half-life"},
            {"failure_mode": "Mass transport limit (Da < 1)", "mechanism": "Clearance limited by Aβ42 delivery, not enzyme", "design_feature_affected": "Catheter geometry", "evidence": "MODELLED via Pe/Da analysis", "mitigation": "Lengthen L or reduce Q (clinical tradeoff)", "verification_test": "Da measurement in bench", "residual_uncertainty": "UNKNOWN actual Da in vivo"},
            {"failure_mode": "Immune response to NEP", "mechanism": "Host recognizes NEP as foreign", "design_feature_affected": "NEP coating", "evidence": "General protein implant concern", "mitigation": "PEGylation or immunosuppressive coating", "verification_test": "In vivo immunogenicity study", "residual_uncertainty": "UNKNOWN NEP-specific immunogenicity"},
            {"failure_mode": "Substrate competition", "mechanism": "Other CSF peptides compete for NEP", "design_feature_affected": "NEP specificity", "evidence": "NEP known to cleave multiple substrates", "mitigation": "UNKNOWN — specificity engineering may be required", "verification_test": "Competition assay", "residual_uncertainty": "UNKNOWN competitive magnitude"},
            {"failure_mode": "Coating delamination", "mechanism": "Mechanical/chemical bond failure", "design_feature_affected": "Coating-catheter interface", "evidence": "Standard coating failure", "mitigation": "Covalent immobilization + mechanical testing", "verification_test": "ASTM D3359 adhesion + fatigue", "residual_uncertainty": "UNKNOWN long-term adhesion in vivo"},
            {"failure_mode": "Catheter obstruction (separate from P-01 mechanism)", "mechanism": "Debris, tissue ingrowth, or protein aggregation blocks lumen", "design_feature_affected": "Catheter body", "evidence": "Standard shunt failure mode (30-50% per R332)", "mitigation": "Standard shunt obstruction mitigation + enzyme coating may affect biocompatibility", "verification_test": "Obstruction bench test", "residual_uncertainty": "UNKNOWN whether enzyme coating affects obstruction rate"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "Recombinant NEP enzyme lot", "equipment": "Activity assay (fluorescent substrate), HPLC, SDS-PAGE", "design_work": "Expression + purification protocol", "measurement": "k_cat, Km, purity, sterility", "acceptance_criterion": "Activity within target range; purity > 95%; endotoxin < limit", "dependency": "Recombinant protein manufacturer", "deliverable": "NEP lot release report", "estimated_effort": "12 weeks"},
            {"work_package": "WP-02", "test_article": "NEP-coated catheter coupons", "equipment": "Surface assay (fluorescent labeling), activity assay", "design_work": "Coating process development", "measurement": "Surface density Gamma, activity per area", "acceptance_criterion": "Gamma meets model requirement; activity stable", "dependency": "WP-01", "deliverable": "Coating process spec", "estimated_effort": "8 weeks"},
            {"work_package": "WP-03", "test_article": "NEP-coated catheter segment", "equipment": "Bench flow loop, Aβ42 ELISA", "design_work": "Flow loop protocol", "measurement": "Clearance per pass at various Q", "acceptance_criterion": ">= 30% reduction per pass at design Q", "dependency": "WP-02", "deliverable": "Bench clearance report", "estimated_effort": "6 weeks"},
            {"work_package": "WP-04", "test_article": "NEP-coated catheter in CSF mimic at 37°C", "equipment": "Aging chamber, activity assay", "design_work": "Aging protocol", "measurement": "Activity vs time", "acceptance_criterion": "Activity > 50% at target lifetime", "dependency": "WP-02", "deliverable": "Stability report", "estimated_effort": "12-24 weeks (chronic)"},
            {"work_package": "WP-05", "test_article": "NEP-coated specimens", "equipment": "ISO 10993 test lab", "design_work": "Material selection frozen", "measurement": "Cytotoxicity, sensitization, irritation, systemic toxicity", "acceptance_criterion": "ISO 10993 pass", "dependency": "Material selection frozen", "deliverable": "ISO 10993 report", "estimated_effort": "12 weeks (external lab)"},
            {"work_package": "WP-06", "test_article": "Coating adhesion specimens", "equipment": "Mechanical test frame", "design_work": "Adhesion test protocol", "measurement": "ASTM D3359 adhesion + fatigue", "acceptance_criterion": "Adhesion passes ASTM; fatigue lifetime > target", "dependency": "WP-02", "deliverable": "Adhesion report", "estimated_effort": "6 weeks"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "Conceptual design + governing equation (Michaelis-Menten + Damköhler)",
                "Mechanism description (immobilized NEP on catheter lumen)",
                "Bench test protocol (clearance per pass, stability)",
                "External precedent catalog (NEP kinetics, immobilization chemistry)",
                "This engineering dossier with failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Recombinant NEP production process (GMP-grade)",
                "Coating process specification + QC",
                "Final catheter geometry (length, diameter, coating density)",
                "Manufacturing process for enzyme-active catheter (aseptic assembly)",
                "Regulatory submission (likely Class III PMA — no predicate for enzymatic catheter)",
                "Clinical validation (CSF Aβ42 reduction + clinical benefit endpoint)",
                "Long-term stability and reliability data"
            ]
        }
    }
