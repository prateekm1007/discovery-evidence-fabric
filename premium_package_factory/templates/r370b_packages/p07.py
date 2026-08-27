"""
p07.py — P-07 Drainage Priority Clearing engineering core.
Domain: pressure-flow / valve mechanics / failure modes.

Governing model: passive multi-lumen conductance with differential pressure thresholds.
External precedent: FDA-cleared CSF shunt systems + passive safety mechanisms.
"""
from .constants import EQUATIONS, STANDARDS


def get_data():
    return {
        "technology_domain": "Hydraulic Passive Safety + Multi-Lumen Valve Mechanics",
        "engineering_disciplines": [
            "Hydraulic conductance engineering",
            "Multi-lumen catheter design",
            "Failure mode analysis (FMEA)",
            "Polymer extrusion"
        ],
        "system_architecture": {
            "description": "CSF shunt with passive safety floor: a secondary drainage path with lower conductance that maintains minimum drainage when the primary path obstructs. Differential pressure thresholds activate the floor path.",
            "subsystems": [
                {"id": "SS-01", "name": "Primary drainage lumen", "function": "Primary CSF drainage path with higher conductance G_primary", "status": "MODELLED", "evidence_source": "R332 mechanism"},
                {"id": "SS-02", "name": "Secondary (safety floor) lumen", "function": "Lower-conductance path that opens when primary obstructs (pressure threshold or mechanical backup)", "status": "PROPOSED", "evidence_class": "PROPOSED", "evidence_source": "R332 mechanism"},
                {"id": "SS-03", "name": "Pressure-activated switch (optional)", "function": "Mechanical switch that activates floor path when primary path dP exceeds threshold", "status": "PROPOSED", "evidence_class": "PROPOSED"},
                {"id": "SS-04", "name": "Outlet catheter (common)", "function": "Drains CSF to peritoneal/atrial/pleural destination", "status": "MODELLED"}
            ],
            "hydraulic_model": {
                "key_equations": [
                    EQUATIONS["hagen_poiseuille"],
                    "Q_total = Q_primary + Q_floor",
                    "G_total = G_primary + G_floor (parallel conductance)"
                ],
                "flow_regime": "Laminar (Re << 2300 at CSF flow rates)",
                "critical_parameter": "G_floor / G_primary ratio — sets drainage floor fraction when primary is patent; sets minimum drainage when primary obstructs",
                "safety_invariants": {
                    "INV-1": "Q_floor >= Q_min when primary obstructs (minimum drainage floor)",
                    "INV-2": "Q_total <= Q_max when primary patent (prevents over-drainage)",
                    "evidence_class": "MODELLED"
                }
            }
        },
        "mechanism_architecture": {
            "physical_changes": "When primary lumen obstructs (debris, tissue ingrowth, protein aggregation), pressure upstream rises; secondary lumen either passively continues to drain (always open, lower conductance) or opens via pressure-activated switch.",
            "key_physics": "Parallel hydraulic conductance: G_total = G_primary + G_floor. When G_primary -> 0 (obstruction), G_total -> G_floor. Floor conductance sized to maintain minimum drainage Q_min = G_floor * dP.",
            "activation_model": {
                "input": "Primary lumen conductance G_primary(t)",
                "model": "Two-mode operation: (1) normal: G_primary >> G_floor, primary dominates; (2) obstructed: G_primary -> 0, floor dominates",
                "transition_mechanism": "Either always-open floor (passive) OR pressure-threshold-activated floor (semi-active)",
                "status": "MODELLED — no hardware validation"
            }
        },
        "engineering_core": {
            "governing_model": {
                "summary": "Parallel hydraulic conductance model. Two drainage paths in parallel: primary (high conductance) and floor (lower conductance). When primary obstructs, floor maintains minimum drainage.",
                "equations": [
                    EQUATIONS["hagen_poiseuille"],
                    "Q_total = Q_primary + Q_floor",
                    "G_total = G_primary + G_floor   [parallel conductance]",
                    "Q_floor_min = G_floor * dP_max   [minimum drainage at worst-case pressure]"
                ],
                "assumptions": [
                    "Both paths laminar (Re < 2300)",
                    "Paths are hydraulically independent (no cross-talk)",
                    "Outlet pressure identical for both paths",
                    "Floor path is immune to the same obstruction mechanism (CRITICAL ASSUMPTION — may not hold)"
                ],
                "boundary_conditions": [
                    "Inlet: ICP 5-40 mmHg",
                    "Outlet: peritoneal pressure ~5-15 mmHg",
                    "dP across shunt: 0-35 mmHg"
                ],
                "input_variables": ["ICP", "Primary obstruction state", "Outlet pressure"],
                "output_variables": ["Q_primary", "Q_floor", "Q_total"],
                "parameter_sensitivities": [
                    "G_floor / G_primary ratio — determines drainage distribution",
                    "Floor lumen diameter d_floor (scales as d^4 per Hagen-Poiseuille)",
                    "Floor lumen length L_floor (inverse)",
                    "Obstruction mode of primary — must NOT affect floor"
                ],
                "failure_regimes": [
                    "Floor lumen obstructs by same mechanism as primary (common-cause failure)",
                    "G_floor too high -> over-drainage when primary patent",
                    "G_floor too low -> under-drainage when primary obstructed",
                    "Floor lumen too small -> manufacturing tolerance dominates"
                ]
            },
            "critical_parameters": [
                {"name": "G_floor (floor conductance)", "value": "UNKNOWN", "unit": "mL/(min·mmHg)", "basis": "Design choice balancing Q_min vs over-drainage", "evidence_class": "UNKNOWN", "verification_requirement": "Bench flow measurement"},
                {"name": "G_primary (primary conductance)", "value": "UNKNOWN", "unit": "mL/(min·mmHg)", "basis": "Standard shunt catheter geometry", "evidence_class": "UNKNOWN", "verification_requirement": "Bench flow measurement"},
                {"name": "Floor lumen diameter d_floor", "value": "UNKNOWN", "unit": "mm", "basis": "Derived from G_floor target via Hagen-Poiseuille", "evidence_class": "MODELLED", "verification_requirement": "Geometric inspection"},
                {"name": "Q_min (minimum drainage floor)", "value": "UNKNOWN", "unit": "mL/min", "basis": "Clinical need (prevents over-drainage collapse)", "evidence_class": "UNKNOWN", "verification_requirement": "Clinical literature review"},
                {"name": "Obstruction resistance threshold", "value": "UNKNOWN", "unit": "mmHg/(mL/min)", "basis": "Pressure at which floor dominates", "evidence_class": "UNKNOWN", "verification_requirement": "Obstruction bench test"}
            ],
            "external_precedent": "EXTERNAL_PRECEDENT ≠ INVENTION_VALIDATION — existing CSF shunts (Codman Hakim, Medtronic Strata, Miethke proGAV) establish that fixed-pressure and programmable valves are manufacturable. None implement a true passive drainage floor with parallel lumen. The proposed mechanism is distinct from existing anti-siphon or gravitational devices.",
            "proposed_design": {
                "input": "ICP and primary lumen obstruction state",
                "mechanism": "Parallel multi-lumen catheter with differential conductance",
                "transformation": "ICP -> (Q_primary + Q_floor) depending on obstruction state",
                "output": "Total drainage with guaranteed minimum",
                "component_architecture": "Multi-lumen extruded catheter -> inlet (ventricular) -> primary lumen + floor lumen -> outlet (peritoneal)"
            },
            "failure_modes": [
                {"mode": "Common-cause obstruction", "mechanism": "Same debris/tissue that obstructs primary also obstructs floor", "design_feature": "Floor lumen", "evidence": "Critical UNKNOWN — no published data on differential obstruction susceptibility", "mitigation": "Different lumen geometry, material, or surface treatment", "verification_test": "Comparative obstruction bench test", "residual_uncertainty": "UNKNOWN whether floor is genuinely independent"},
                {"mode": "Over-drainage when primary patent", "mechanism": "G_floor too high relative to G_primary", "design_feature": "Conductance ratio", "evidence": "MODELLED via Hagen-Poiseuille", "mitigation": "Tune ratio to maintain Q_total within safety bounds", "verification_test": "Bench flow test", "residual_uncertainty": "UNKNOWN optimal ratio"},
                {"mode": "Under-drainage when primary obstructed", "mechanism": "G_floor too low", "design_feature": "Floor lumen diameter", "evidence": "MODELLED", "mitigation": "Increase d_floor", "verification_test": "Obstruction bench test", "residual_uncertainty": "UNKNOWN optimal G_floor"},
                {"mode": "Manufacturing tolerance violation", "mechanism": "Floor lumen too small -> tolerance dominates", "design_feature": "Floor lumen diameter", "evidence": "Standard extrusion tolerance", "mitigation": "Process capability study (Cpk >= 1.33)", "verification_test": "Cpk measurement", "residual_uncertainty": "UNKNOWN Cpk for multi-lumen extrusion"},
                {"mode": "Floor lumen collapse (kink)", "mechanism": "Mechanical deformation closes floor lumen", "design_feature": "Catheter body", "evidence": "Standard catheter failure", "mitigation": "Reinforcement or larger diameter", "verification_test": "Kink test per ISO 10555-1", "residual_uncertainty": "UNKNOWN kink resistance of multi-lumen design"}
            ],
            "verification": [
                {"id": "VER-001", "requirement": "Q_floor >= Q_min when primary obstructed", "method": "Bench obstruction test: occlude primary, measure Q_floor", "acceptance": "Q_floor >= Q_min target", "evidence_class": "PROPOSED"},
                {"id": "VER-002", "requirement": "Q_total <= Q_max when primary patent", "method": "Bench flow test", "acceptance": "Q_total within safety bounds", "evidence_class": "PROPOSED"},
                {"id": "VER-003", "requirement": "Multi-lumen extrusion process capability", "method": "Cpk study on production-equivalent samples", "acceptance": "Cpk >= 1.33 for critical dimensions", "evidence_class": "PROPOSED"},
                {"id": "VER-004", "requirement": "Kink resistance", "method": "ISO 10555-1 kink test", "acceptance": "No flow occlusion at specified bend radius", "evidence_class": "PROPOSED", "standard": "ISO_10555_1"}
            ],
            "validation": [
                {"id": "VAL-001", "requirement": "Reduced revision rate vs standard shunt", "method": "Clinical trial (IDE required)", "acceptance": "Statistically significant reduction in obstruction-related revisions", "evidence_class": "UNKNOWN"}
            ],
            "remaining_unknowns": [
                "Achievable G_floor / G_primary ratio given manufacturing constraints — UNKNOWN",
                "Whether floor is genuinely immune to common-cause obstruction — UNKNOWN (critical)",
                "Optimal Q_min for clinical safety — UNKNOWN (clinical literature gap)",
                "Multi-lumen extrusion process capability — UNKNOWN",
                "Regulatory pathway (510(k) with substantial equivalence to existing shunts, or De Novo if no predicate for multi-lumen floor) — UNKNOWN",
                "Clinical benefit magnitude — UNKNOWN until trial"
            ]
        },
        "design_inputs": [
            {"id": "DI-001", "input": "Clinical need", "value": "Obstruction causes 30-50% of shunt failures; no passive safety floor exists (R332)", "evidence_class": "VERIFIED", "source": "R332"},
            {"id": "DI-002", "input": "Functional requirement", "value": "Passive safety mechanism maintaining minimum drainage when primary paths obstructed", "evidence_class": "MODELLED", "source": "R332"},
            {"id": "DI-003", "input": "Flow regime", "value": "Laminar, Re << 2300", "evidence_class": "COMPUTATIONALLY_SUPPORTED"},
            {"id": "DI-004", "input": "ICP range", "value": "5-40 mmHg (normal to pathological)", "evidence_class": "VERIFIED"},
            {"id": "DI-005", "input": "Q_min target (minimum drainage)", "value": "UNKNOWN — MODEL_DERIVED candidate ~0.05 mL/min (per R332)", "evidence_class": "MODELLED", "source": "R332 mechanism"},
            {"id": "DI-006", "input": "Q_max target (over-drainage limit)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "Clinical literature review + clinical input"},
            {"id": "DI-007", "input": "Biocompatibility (ISO 10993)", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 10993 series"},
            {"id": "DI-008", "input": "Sterilization", "value": "UNKNOWN — likely EtO or gamma", "evidence_class": "UNKNOWN", "resolution_plan": "ISO 11135 or 11137"},
            {"id": "DI-009", "input": "Multi-lumen extrusion tolerance", "value": "UNKNOWN", "evidence_class": "UNKNOWN", "resolution_plan": "Process capability study with extrusion vendor"},
            {"id": "DI-010", "input": "Catheter body material", "value": "UNKNOWN — likely silicone or polyurethane (external precedent)", "evidence_class": "EXTERNAL_PRECEDENT"}
        ],
        "design_outputs": [
            {"id": "DO-001", "description": "Multi-lumen catheter geometry (primary + floor lumen diameters, length, layout)", "status": "ABSENT", "design_status": "CAD_BLOCKED", "missing_inputs": ["G_floor target", "G_primary target", "Multi-lumen layout"]},
            {"id": "DO-002", "description": "Extrusion process specification", "status": "ABSENT", "design_status": "PROCESS_DEVELOPMENT_BLOCKED", "missing_inputs": ["Vendor selection", "Tolerance requirements", "Material selection frozen"]},
            {"id": "DO-003", "description": "Bench test protocol for obstruction", "status": "CONCEPTUAL", "design_status": "PROTOCOL_DEVELOPMENT", "note": "Protocol sketched in R332"}
        ],
        "verification_matrix": [
            {"id": "V-001", "requirement": "Q_floor >= Q_min when primary obstructed", "method": "Bench obstruction test", "acceptance": "Q_floor >= Q_min target", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-002", "requirement": "Q_total within bounds when primary patent", "method": "Bench flow test", "acceptance": "Q_total within safety range", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-003", "requirement": "Process capability Cpk >= 1.33", "method": "Cpk study", "acceptance": "Cpk >= 1.33", "result": "NOT_TESTED", "evidence_class": "PROPOSED"},
            {"id": "V-004", "requirement": "Kink resistance per ISO 10555-1", "method": "ISO 10555-1 kink test", "acceptance": "Pass", "result": "NOT_TESTED", "evidence_class": "PROPOSED"}
        ],
        "validation_matrix": [
            {"id": "VAL-001", "requirement": "Reduced revision rate vs standard shunt", "method": "Clinical trial", "acceptance": "Statistically significant reduction", "result": "NOT_PERFORMED", "evidence_class": "UNKNOWN"}
        ],
        "bom": [
            {"item": "01", "description": "Multi-lumen catheter body", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "ENGINEERING_PROPOSED", "material": "UNKNOWN — silicone or polyurethane (external precedent)", "supplier": "UNKNOWN — extrusion vendor required", "criticality": "CRITICAL", "verification": "Dimensional + flow + kink"},
            {"item": "02", "description": "Inlet (ventricular) catheter connector", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard CSF shunt component", "material": "UNKNOWN — likely radiopaque polymer", "supplier": "Multiple", "criticality": "HIGH", "verification": "Dimensional + biocompatibility"},
            {"item": "03", "description": "Outlet (peritoneal) catheter", "qty": "1", "component_type": "CUSTOM_COMPONENT", "source_basis": "Standard CSF shunt component", "material": "UNKNOWN", "supplier": "Multiple", "criticality": "HIGH", "verification": "Dimensional + biocompatibility"}
        ],
        "materials": [
            {"component": "Multi-lumen catheter body", "candidate_material": "Silicone elastomer (radiopaque)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard CSF shunt material", "verification_required": "ISO 10993 + multi-lumen extrusion capability", "status": "CANDIDATE"},
            {"component": "Multi-lumen catheter body", "candidate_material": "Polyurethane (radiopaque)", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Some shunts use polyurethane", "verification_required": "ISO 10993 + multi-lumen extrusion capability", "status": "CANDIDATE"}
        ],
        "manufacturing": {
            "candidate_processes": [
                {"process": "Multi-lumen extrusion", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Standard medical tubing process (multiple lumens achievable)", "tolerance_implication": "±0.05 mm typical for medical-grade multi-lumen", "note": "Requires custom extrusion die; vendor capability varies"},
                {"process": "Radiopaque compound compounding", "evidence_class": "EXTERNAL_PRECEDENT", "source": "Barium sulfate or bismuth trioxide loading", "tolerance_implication": "Loading 10-25% typical", "note": "Affects mechanical properties"}
            ],
            "status": "ENGINEERING_CANDIDATE — no multi-lumen floor process validated for this specific design"
        },
        "failure_analysis": [
            {"failure_mode": "Common-cause obstruction (CRITICAL)", "mechanism": "Same obstruction mechanism affects both lumens", "design_feature_affected": "Floor lumen", "evidence": "UNKNOWN — no published data", "mitigation": "Different geometry, material, or surface treatment", "verification_test": "Comparative obstruction bench test", "residual_uncertainty": "CRITICAL UNKNOWN — may invalidate concept"},
            {"failure_mode": "Over-drainage when primary patent", "mechanism": "G_floor too high", "design_feature_affected": "Conductance ratio", "evidence": "MODELLED", "mitigation": "Tune ratio", "verification_test": "Bench flow test", "residual_uncertainty": "UNKNOWN optimal ratio"},
            {"failure_mode": "Under-drainage when primary obstructed", "mechanism": "G_floor too low", "design_feature_affected": "Floor lumen diameter", "evidence": "MODELLED", "mitigation": "Increase d_floor", "verification_test": "Obstruction bench", "residual_uncertainty": "UNKNOWN optimal d_floor"},
            {"failure_mode": "Manufacturing tolerance violation", "mechanism": "Tolerance > margin", "design_feature_affected": "Multi-lumen geometry", "evidence": "Standard extrusion tolerance", "mitigation": "Cpk study + tolerance stack analysis", "verification_test": "Cpk measurement", "residual_uncertainty": "UNKNOWN Cpk"},
            {"failure_mode": "Kink-induced occlusion", "mechanism": "Mechanical deformation closes lumen", "design_feature_affected": "Catheter body", "evidence": "Standard catheter failure", "mitigation": "Reinforcement or larger diameter", "verification_test": "ISO 10555-1", "residual_uncertainty": "UNKNOWN kink resistance of multi-lumen"}
        ],
        "engineering_build_plan": [
            {"work_package": "WP-01", "test_article": "Multi-lumen extruded samples (various d_floor/d_primary ratios)", "equipment": "Extrusion line, microscope, flow bench", "design_work": "Multi-lumen die design + extrusion parameters", "measurement": "G_floor, G_primary, dimensional accuracy", "acceptance_criterion": "G_ratio within design range; Cpk >= 1.33", "dependency": "Extrusion vendor selection", "deliverable": "Extrusion process spec + samples", "estimated_effort": "10 weeks"},
            {"work_package": "WP-02", "test_article": "Bench obstruction rig", "equipment": "Obstruction simulator, flow sensors, pressure transducers", "design_work": "Test fixture + protocol", "measurement": "Q_total vs obstruction level", "acceptance_criterion": "Q_floor >= Q_min when primary obstructed", "dependency": "WP-01", "deliverable": "Obstruction bench report", "estimated_effort": "6 weeks"},
            {"work_package": "WP-03", "test_article": "Kink test specimens", "equipment": "ISO 10555-1 kink test rig", "design_work": "Test protocol", "measurement": "Flow vs bend radius", "acceptance_criterion": "No occlusion at specified bend radius", "dependency": "WP-01", "deliverable": "Kink test report", "estimated_effort": "4 weeks"},
            {"work_package": "WP-04", "test_article": "Comparative obstruction specimens (primary vs floor)", "equipment": "Obstruction rig, debris/tissue proxy", "design_work": "Comparative protocol", "measurement": "Differential obstruction susceptibility", "acceptance_criterion": "Floor obstructs slower/differently than primary", "dependency": "WP-02", "deliverable": "Common-cause obstruction report", "estimated_effort": "8 weeks"},
            {"work_package": "WP-05", "test_article": "Biocompatibility specimens", "equipment": "ISO 10993 test lab", "design_work": "Material selection frozen", "measurement": "Standard ISO 10993 series", "acceptance_criterion": "ISO 10993 pass", "dependency": "Material selection", "deliverable": "ISO 10993 report", "estimated_effort": "12 weeks (external lab)"}
        ],
        "transfer_boundary": {
            "buyer_receives": [
                "Passive floor concept + mechanism description",
                "Parallel conductance governing equation",
                "Bench test protocol (obstruction, kink, Cpk)",
                "Critical common-cause obstruction UNKNOWN disclosure",
                "This engineering dossier with failure analysis + build plan"
            ],
            "buyer_must_create": [
                "Production multi-lumen catheter design (dimensioned, toleranced)",
                "Multi-lumen extrusion process + vendor qualification",
                "Common-cause obstruction validation evidence",
                "Regulatory submission (510(k) or De Novo)",
                "Clinical validation (revision rate endpoint)",
                "Manufacturing scale-up"
            ]
        }
    }
