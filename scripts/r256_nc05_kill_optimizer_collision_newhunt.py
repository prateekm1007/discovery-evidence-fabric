"""
Round 256 — NC-05 Kill + Optimizer Repair (Novelty-First) + NC-01..NC-04 Collision + New-Hunt Redesign

CEO R256 directive:
  P0: Kill NC-05 (5 prior-art patents). Downgrade to NOVELTY_THREATENED.
  P1: Repair optimizer: NOVELTY FIRST → COMMERCIAL EV SECOND.
  P2: Deep collision attack on NC-01..NC-04.
  P3: New-hunt using information bottleneck: hidden variable → inability to
      observe → expensive workaround → new measurement/inference → technical
      effect → buyer economics.

Output:
  CANONICAL_STATE/R256_NC05_KILL_OPTIMIZER_COLLISION_NEWHUNT.json
"""
import json
from pathlib import Path
from datetime import datetime, timezone

OUTPUT_PATH = Path(
    "/home/z/my-project/discovery-evidence-fabric/CANONICAL_STATE/"
    "R256_NC05_KILL_OPTIMIZER_COLLISION_NEWHUNT.json"
)


# ===========================================================================
# P0 — NC-05 Killed: NOVELTY_THREATENED
# ===========================================================================

NC05_KILL = {
    "candidate": "NC-05: MRI Coil Failure Predictor from Usage Telemetry",
    "action": "DOWNGRADE FROM INVEST TO NOVELTY_THREATENED",
    "reason": "5 prior-art patents directly cover the proposed mechanism. The claim 'No tool uses telemetry to predict failure' is NOT supportable.",
    "prior_art_found": [
        {
            "patent": "US 12,386,345 (Siemens, issued Aug 2025)",
            "covers": "Predicting potential failure of MRI modules including flexible coils, using sensors, remote evaluation, and prediction models. Explicitly covers failure prediction and maintenance planning.",
            "url": "https://patents.justia.com/patent/12386345",
        },
        {
            "patent": "US 2024/0241197 A1",
            "covers": "MRI coil with embedded diagnostic interface module. Remote/cloud monitoring, AI tracking of electrical properties, predicting imminent hard/soft coil failure.",
            "url": "https://patents.google.com/patent/US20240241197A1",
        },
        {
            "patent": "US 2025/0199104 A1 (June 2025)",
            "covers": "Monitoring technologies for MRI coils/arrays: resonant frequency, ring-down, coupling, temperature. Cloud aggregation and AI to predict future coil failure.",
            "url": "https://patents.justia.com/patent/20250199104",
        },
        {
            "patent": "US 2026/0122134 A1 (Siemens, April 2026)",
            "covers": "MRI system monitoring with cloud-enabled abnormality prediction, including coils, using telemetry trends and predictive warnings.",
            "url": "https://patents.justia.com/patent/20260122134",
        },
        {
            "patent": "US 2024/0103112 A1",
            "covers": "ML-based MRI coil fault detection, including failure type/location and real-time automated detection.",
            "url": "https://patents.google.com/patent/US20240103112A1",
        },
    ],
    "verdict": "NOVELTY_THREATENED. The mechanism (telemetry → ML → failure prediction → maintenance recommendation) is directly covered by at least 5 patents. NC-05 cannot reach INVEST without a genuinely different mechanism. No simulation.",
    "lesson": "Commercial EV was positive (+0.0047) but novelty is zero. The optimizer must be EV × novelty_confidence, not raw EV. A cheap-to-test candidate with zero novelty has NEGATIVE effective value.",
}


# ===========================================================================
# P1 — Optimizer Repair: Novelty-First Pipeline
# ===========================================================================

OPTIMIZER_FIX = {
    "the_problem": (
        "R255's new-hunt engine generated candidates based on commercial EV "
        "BEFORE performing novelty collision. That is backwards. NC-05 had "
        "positive EV but zero novelty — 5 patents cover the exact mechanism."
    ),
    "the_fix": {
        "pipeline_order": "NOVELTY FIRST → COMMERCIAL EV SECOND",
        "minimum_invest_condition": "Novelty confidence >= Level 2 AND positive evidence-acquisition EV",
        "states": {
            "INVEST": {
                "condition": "Novelty >= Level 2 AND EV > 0",
                "action": "Proceed with §103 + killer experiment",
            },
            "WATCH": {
                "condition": "Novelty >= Level 1 AND EV >= -0.05 (close to break-even)",
                "action": "Monitor; re-evaluate when new info arrives",
            },
            "NOVELTY_THREATENED": {
                "condition": "Prior art directly covers the mechanism",
                "action": "Do NOT simulate. Preserve for resurrection only if a genuinely different mechanism is found.",
            },
            "RESET": {
                "condition": "Novelty < Level 1 OR EV < -0.05",
                "action": "Return to discovery queue. Do not invest.",
            },
        },
        "novelty_levels": {
            "Level_0": "Prior art directly covers the full mechanism. NOVELTY_THREATENED.",
            "Level_1": "Prior art covers components but not the specific combination. MARGINAL.",
            "Level_2": "Prior art covers adjacent domains but NOT the specific mechanism in this domain. SURVIVES initial collision.",
            "Level_3": "No prior art found after deep search. STRONG novelty candidate.",
        },
        "effective_value_formula": "effective_EV = raw_EV × novelty_confidence (0.0 to 1.0)",
        "example": "NC-05: raw_EV = +0.0047, novelty_confidence = 0.0 (5 patents cover mechanism). effective_EV = 0.0047 × 0.0 = 0.0. NOT INVEST.",
    },
    "rule": "A candidate cannot reach INVEST merely because EV > 0. Novelty must be assessed FIRST, before any simulation budget is spent.",
}


# ===========================================================================
# P2 — Deep Collision Attack on NC-01..NC-04
# ===========================================================================

COLLISION_ATTACKS = {
    "NC-01": {
        "name": "Sterilization Validation Dose Auditor",
        "mechanism": "Given bioburden data + sterilization parameters, determine minimum dose modification maintaining SAL 10^-6 per ISO 11137",
        "prior_art_search": {
            "iso_11137": "ISO 11137 (radiation sterilization) explicitly provides methods for dose mapping, bioburden-based dose setting, and dose auditing. The standard ITSELF is the method.",
            "commercial_tools": "Sterigenics, Steris, and contract sterilization labs use ISO 11137-based software for dose calculation. AAMI TIR33 provides dose auditing methodology.",
            "optimization_methods": "Dose optimization is a well-studied problem in radiation processing. Monte Carlo dose modeling (e.g., Geant4) exists. Minimum dose determination is standard ISO 11137 practice.",
            "ai_ml_for_sterilization": "Some recent work on ML for sterilization process optimization, but primarily for cycle parameter optimization, not dose modification validation.",
        },
        "smallest_surviving_mechanism": "Apply ISO 11137 dose audit methodology with automated optimization to find minimum sufficient dose modification testing.",
        "novelty_assessment": "Level 1 (MARGINAL). The ISO standard itself provides the method. Automation + optimization is engineering, not invention. The 'minimum sufficient testing' framing is similar to MSVED's failure — claiming 'minimum' without a novel mathematical bound.",
        "verdict": "RESET. Novelty Level 1. The mechanism is ISO 11137 applied with optimization. Not an invention.",
    },
    "NC-02": {
        "name": "Implant Fatigue Life Predictor from Manufacturing Tolerances",
        "mechanism": "Given CAD + tolerance band + material fatigue data, predict distribution of in-vivo fatigue life and identify tolerance combinations causing premature failure",
        "prior_art_search": {
            "fea_with_tolerance": "Tolerance-based FEA is a well-established field. Software like Abaqus, ANSYS, and nCode DesignLife support stochastic/monte-carlo FEA with tolerance inputs.",
            "implant_fatigue_modeling": "Extensive literature on implant fatigue life prediction (ASTM F1717, ISO 14801 for dental implants, ASTM F2346 for spinal disc prostheses). FDA guidance requires fatigue testing.",
            "tolerance_propagation": "Monte Carlo tolerance propagation through FEA is standard in mechanical engineering. Commercial tools (e.g., SmartUQ, Isight, OptiY) exist for this.",
            "manufacturing_variation": "Some recent work on digital twins for manufacturing variation, but primarily for process optimization, not fatigue life prediction from tolerances.",
        },
        "smallest_surviving_mechanism": "Monte Carlo tolerance propagation through FEA for fatigue life prediction — a combination of standard techniques.",
        "novelty_assessment": "Level 1 (MARGINAL). Monte Carlo + FEA + fatigue modeling are all standard. The combination is engineering. Commercial tools (SmartUQ, nCode) already do tolerance-based FEA. No novel mathematical relationship.",
        "verdict": "RESET. Novelty Level 1. The mechanism is Monte Carlo on existing FEA. Not an invention.",
    },
    "NC-03": {
        "name": "Adaptive Trial Futility Boundary Calculator for Device Trials",
        "mechanism": "Given interim data, compute optimal futility boundary minimizing expected sample size while controlling Type I error, using Bayesian predictive power",
        "prior_art_search": {
            "bayesian_adaptive_designs": "Extensive literature. Berry et al., Spiegelhalter et al., FDA guidance on adaptive designs for medical devices (2015). Bayesian predictive power is standard.",
            "commercial_tools": "East (Cytel), PASS, RevAdapt, BayesFactor. Multiple commercial tools compute adaptive trial boundaries.",
            "futility_boundaries": "Futility boundaries are well-studied. DeMets & Ware (1980s), Proschan et al. Multiple textbooks cover the methodology.",
            "device_specific": "FDA guidance on adaptive designs for medical devices (2015) explicitly discusses futility analysis. The methodology is taught.",
        },
        "smallest_surviving_mechanism": "Bayesian predictive power futility boundary calculation — a standard adaptive design technique.",
        "novelty_assessment": "Level 0 (THREATENED). Bayesian futility boundaries are explicitly covered by FDA guidance, commercial tools, and decades of literature. The mechanism is standard biostatistics.",
        "verdict": "NOVELTY_THREATENED. Level 0. Multiple commercial tools and FDA guidance cover this exactly.",
    },
    "NC-04": {
        "name": "Assay Cross-Reactivity Predictor from Molecular Structure",
        "mechanism": "Given assay target molecule + interferent library, predict cross-reactivity using molecular similarity + assay chemistry, reducing physical tests",
        "prior_art_search": {
            "computational_chemistry": "Molecular similarity prediction (Tanimoto coefficient, fingerprint-based) is standard in computational chemistry. RDKit, Open Babel, Schrödinger provide these capabilities.",
            "ivd_cross_reactivity": "Some academic work on predicting cross-reactivity from molecular structure (primarily for small molecules). ELISA/antibody cross-reactivity prediction is harder (depends on epitope, not just molecular structure).",
            "commercial_tools": "Schrodinger, Biovia, ChemAxon provide molecular similarity tools. Some IVD companies use in-silico screening for interferent selection.",
            "fda_guidance": "FDA guidance on interferant testing for IVDs exists but does not require computational prediction.",
        },
        "smallest_surviving_mechanism": "Molecular similarity scoring to rank potential interferents — standard computational chemistry applied to IVD.",
        "novelty_assessment": "Level 1 (MARGINAL). Molecular similarity is standard. Applying it to IVD cross-reactivity prediction is an application, not an invention. For antibody-based assays, molecular similarity alone is insufficient (epitope-specific binding is not captured by molecular fingerprints).",
        "verdict": "RESET. Novelty Level 1. Standard computational chemistry applied to IVD. Not an invention.",
    },
}

# Summary of collision attacks
collision_summary = {}
for nc_id, attack in COLLISION_ATTACKS.items():
    level = attack["novelty_assessment"].split("(")[1].split(")")[0]
    collision_summary[nc_id] = {
        "name": attack["name"],
        "novelty_level": level,
        "verdict": attack["verdict"],
    }

print("=== P2: NC-01..NC-04 COLLISION ATTACKS ===")
for nc_id, s in collision_summary.items():
    print(f"  {nc_id}: {s['name'][:40]} — Novelty {s['novelty_level']} — {s['verdict']}")


# ===========================================================================
# P3 — New-Hunt Redesign: Information Bottleneck
# ===========================================================================

NEWHUNT_REDESIGN = {
    "the_problem": (
        "R255's new-hunt generated candidates by asking 'what domain has "
        "high buyer pain?' then proposing 'apply AI to X.' That produces "
        "candidates like NC-05 (apply AI to MRI maintenance) which are "
        "prior-art threatened. The search must start from a TECHNICAL "
        "question, not a commercial one."
    ),
    "the_new_principle": (
        "Search for candidates using the information-bottleneck structure: "
        "hidden variable → inability to observe → existing expensive "
        "workaround → new measurement/inference mechanism → measurable "
        "technical effect → buyer economics."
    ),
    "the_template": [
        "1. What technically important variable is EXPENSIVE TO OBSERVE in a medical-device context?",
        "2. What existing buyer workflow is FORCED TO OPERATE WITHOUT it?",
        "3. What expensive workaround does the buyer currently use?",
        "4. What new MEASUREMENT or INFERENCE mechanism could make the variable observable?",
        "5. What MEASURABLE TECHNICAL EFFECT does the new mechanism produce?",
        "6. What BUYER ECONOMICS does the technical effect enable?",
    ],
    "examples_of_the_structure": [
        {
            "hidden_variable": "In-vivo implant micromotion (how much an implant moves under physiological load, non-invasively)",
            "inability_to_observe": "Current methods require X-ray (radiation, episodic) or CT (expensive, radiation). No continuous, non-invasive measurement.",
            "expensive_workaround": "Surgeons use static imaging + clinical symptoms. Implant loosening is detected late, requiring revision surgery ($50K-$150K per case).",
            "new_mechanism": "Implant-integrated sensor that measures micromotion via impedance change (the implant itself becomes the sensor — no external measurement needed).",
            "technical_effect": "Continuous, non-invasive micromotion measurement with sub-micron resolution.",
            "buyer_economics": "Early detection of loosening → planned revision (cheaper) vs emergency revision (expensive). $10K-$50K per avoided emergency revision.",
            "novelty_question": "Is implant-integrated impedance-based micromotion measurement novel? (This is related to the CereVasc eShunt impedance sensing — cemetery CE-001, but applied to ORTHOPEDIC implants, not CSF shunts.)",
        },
        {
            "hidden_variable": "Real-time drug concentration at the target tissue (not in blood, but at the actual site of action)",
            "inability_to_observe": "Blood draws measure systemic concentration, not tissue concentration. Biopsies are invasive and episodic. No real-time tissue drug level measurement exists.",
            "expensive_workaround": "Dose adjustment based on blood levels + clinical response. Suboptimal dosing leads to toxicity (too high) or treatment failure (too low).",
            "new_mechanism": "Implantable microdialysis probe with continuous concentration measurement at target site, wirelessly transmitted.",
            "technical_effect": "Real-time tissue drug concentration curve, enabling pharmacokinetic modeling at the actual site of action.",
            "buyer_economics": "Optimized dosing → reduced toxicity cost ($10K-$100K per toxicity event) + improved efficacy. Mainly for oncology, CNS drug delivery, immunosuppression.",
            "novelty_question": "Is continuous tissue-level drug concentration measurement via implantable microdialysis novel? (Microdialysis exists in research, but continuous + wireless + clinical-grade is not standard.)",
        },
        {
            "hidden_variable": "Vessel wall shear stress at the implant site (not bulk flow, but LOCAL stress at the exact implant-tissue interface)",
            "inability_to_observe": "CFD can estimate bulk flow but not local wall shear at the implant interface. Measurement requires invasive techniques (not clinically feasible).",
            "expensive_workaround": "Implant design uses safety margins (over-engineering). Thrombosis risk is assessed post-hoc via clinical outcomes, not pre-deployment prediction.",
            "new_mechanism": "Implant-surface-integrated pressure sensors that measure local wall shear stress directly at the interface, enabling patient-specific thrombosis risk prediction.",
            "technical_effect": "Direct measurement of local hemodynamic stress at implant-tissue interface.",
            "buyer_economics": "Patient-specific thrombosis risk → personalized anti-coagulation regimen. $5K-$50K per avoided thrombotic event.",
            "novelty_question": "Is implant-surface-integrated wall shear stress measurement novel? (Related to CereVasc eShunt sensing territory, but the MEASUREMENT of shear stress, not pressure, is different.)",
        },
    ],
    "the_key_difference_from_R255": (
        "R255 asked 'what domain has pain?' and proposed 'apply AI to X.' "
        "R256 asks 'what variable is expensive to observe?' and proposes "
        "'new measurement mechanism.' The latter produces candidates with "
        "genuine technical novelty (new measurement capability), not just "
        "commercial packaging of existing technology."
    ),
    "next_steps": (
        "These 3 examples are CANDIDATE STRUCTURES, not yet candidates. "
        "Each must be: (1) collision-searched for prior art, (2) §103 "
        "attacked, (3) assessed for novelty level BEFORE any EV calculation "
        "or simulation. The novelty-first pipeline applies."
    ),
}


# ===========================================================================
# Assemble output
# ===========================================================================

output = {
    "schema_version": "1.0.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "generated_by": "Round 256 — NC-05 Kill + Optimizer Repair + Collision + New-Hunt Redesign",
    "ceo_directive_round_256": (
        "P0: kill NC-05 (5 prior-art patents). P1: repair optimizer "
        "(novelty-first). P2: collision attack NC-01..NC-04. P3: new-hunt "
        "using information bottleneck."
    ),
    "p0_nc05_kill": NC05_KILL,
    "p1_optimizer_fix": OPTIMIZER_FIX,
    "p2_collision_attacks": {
        "summary": collision_summary,
        "details": COLLISION_ATTACKS,
    },
    "p3_newhunt_redesign": NEWHUNT_REDESIGN,
    "summary": {
        "p0": "NC-05 DOWNGRADED to NOVELTY_THREATENED. 5 prior-art patents cover the exact mechanism (Siemens, embedded diagnostics, cloud monitoring, ML fault detection). No simulation.",
        "p1": "Optimizer repaired: NOVELTY FIRST → COMMERCIAL EV SECOND. INVEST requires novelty >= Level 2 AND EV > 0. effective_EV = raw_EV × novelty_confidence.",
        "p2": "NC-01..NC-04 collision attacks complete. Results: NC-01 RESET (Level 1, ISO 11137 applied), NC-02 RESET (Level 1, Monte Carlo on FEA), NC-03 NOVELTY_THREATENED (Level 0, commercial tools exist), NC-04 RESET (Level 1, standard computational chemistry). NONE survive to INVEST.",
        "p3": "New-hunt engine redesigned around information-bottleneck: hidden variable → inability to observe → expensive workaround → new measurement/inference → technical effect → economics. 3 candidate structures generated (implant micromotion, tissue drug concentration, vessel wall shear stress). NOT yet candidates — must be collision-searched first.",
        "portfolio_state": {
            "world_class": "0/5",
            "commercial_tool_candidate": "1 (CC-04, not sellable)",
            "invest": "0 (NC-05 downgraded, all others RESET/THREATENED)",
            "novelty_threatened": "2 (NC-05, NC-03)",
            "reset": "9 (CC-02, CC-03, CC-05, CC-06, CC-07, CC-09, CC-10, NC-01, NC-02, NC-04)",
            "killed": "3 (MSVED CE-019, CC-08 CE-021, NC-05 threatened not killed)",
            "new_candidate_structures": "3 (information-bottleneck based, not yet candidates)",
            "sellable": "0",
            "transactions": "$0",
        },
        "key_insight": (
            "The entire NC-01..NC-05 batch failed novelty collision. The "
            "lesson: commercial EV without novelty is worthless. The new-hunt "
            "engine must start from 'what variable is expensive to observe?' "
            "not 'what domain has pain?' The information-bottleneck structure "
            "produces candidates with genuine technical novelty (new "
            "measurement capability), not commercial packaging."
        ),
        "next": "R257 will collision-search the 3 information-bottleneck candidate structures (implant micromotion, tissue drug concentration, vessel wall shear stress) using the novelty-first pipeline. Only structures that survive Level 2+ novelty will receive EV calculation.",
    },
}

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

if OUTPUT_PATH.exists():
    print(f"\n[OK] Output: {OUTPUT_PATH} ({OUTPUT_PATH.stat().st_size} bytes)")
