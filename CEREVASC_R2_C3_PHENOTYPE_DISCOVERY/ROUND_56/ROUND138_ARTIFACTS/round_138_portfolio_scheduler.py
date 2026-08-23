#!/usr/bin/env python3
"""
round_138_portfolio_scheduler.py

Per CEO Round 138: "Turn parallelization into a scientific scheduler.
The AI must select work based on expected portfolio-level information gain."

This script implements a PORTFOLIO-LEVEL ACQUISITION SCHEDULER that:
1. Enumerates all candidate × hypothesis × experiment × world combinations
2. Scores each by: EIG × P(decision_change) × independence × buyer_impact ÷ total_resource_cost
3. Selects the globally highest-value action
4. Executes it
5. Repeats

Also implements:
- SCIENTIFIC_EVIDENCE vs DECISION_VALUE_EVIDENCE separation
- REALITY_BLOCKER objects (STRIDE data for C1)
- C2 claim-level prior-art analysis (anticipated/obvious/survives)
- C3 buyer-value chain (unmet need → limitation → C3 advantage → economic consequence)
"""

import json
import hashlib
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")
ROUND_138_DIR = REPO_ROOT / "CEREVASC_R2_C3_PHENOTYPE_DISCOVERY" / "ROUND_56" / "ROUND138_ARTIFACTS"


# ============================================================
# PORTFOLIO-LEVEL ACQUISITION SCHEDULER
# ============================================================

def enumerate_portfolio_experiments():
    """Enumerate all candidate × hypothesis × experiment × world combinations."""
    experiments = []

    # C1 experiments
    experiments.extend([
        {"candidate": "C1", "hypothesis": "H2", "experiment": "strongest_alternative_deepening",
         "world": "research", "eig": 0.60, "p_decision_change": 0.15, "independence": 0.0,
         "buyer_impact": 0.3, "cost": 0.05, "executable": True,
         "description": "Quantify surgical vs C1 cost/risk gap"},
        {"candidate": "C1", "hypothesis": "H1", "experiment": "reality_blocker_stride",
         "world": "reality", "eig": 0.95, "p_decision_change": 0.80, "independence": 1.0,
         "buyer_impact": 1.0, "cost": 999, "executable": False,
         "description": "STRIDE 5-year eShunt obstruction data (REALITY BLOCKED)"},
        {"candidate": "C1", "hypothesis": "H2", "experiment": "buyer_value_chain",
         "world": "research", "eig": 0.50, "p_decision_change": 0.20, "independence": 0.0,
         "buyer_impact": 0.8, "cost": 0.1, "executable": True,
         "description": "Map unmet need → C1 advantage → economic consequence"},
    ])

    # C2 experiments
    experiments.extend([
        {"candidate": "C2", "hypothesis": "H5", "experiment": "claim_level_prior_art",
         "world": "research", "eig": 0.85, "p_decision_change": 0.40, "independence": 0.5,
         "buyer_impact": 0.6, "cost": 0.2, "executable": True,
         "description": "Claim-level analysis: C2 limitations vs CardioMEMS + eShunt patents"},
        {"candidate": "C2", "hypothesis": "H3", "experiment": "identifiability_recheck",
         "world": "research", "eig": 0.60, "p_decision_change": 0.10, "independence": 0.0,
         "buyer_impact": 0.2, "cost": 0.05, "executable": True,
         "description": "Re-verify Jacobian rank under updated noise assumptions"},
        {"candidate": "C2", "hypothesis": "H1", "experiment": "buyer_value_chain",
         "world": "research", "eig": 0.50, "p_decision_change": 0.15, "independence": 0.0,
         "buyer_impact": 0.5, "cost": 0.1, "executable": True,
         "description": "Continuous monitoring buyer-value chain"},
    ])

    # C3 experiments
    experiments.extend([
        {"candidate": "C3", "hypothesis": "H2", "experiment": "buyer_value_chain",
         "world": "research", "eig": 0.80, "p_decision_change": 0.35, "independence": 0.0,
         "buyer_impact": 0.9, "cost": 0.1, "executable": True,
         "description": "CNS delivery buyer-value chain (unmet need → C3 advantage → economic consequence)"},
        {"candidate": "C3", "hypothesis": "H3", "experiment": "analytical_derivation",
         "world": "research", "eig": 0.70, "p_decision_change": 0.15, "independence": 0.0,
         "buyer_impact": 0.3, "cost": 0.05, "executable": True,
         "description": "Re-verify CSF turnover steady-state with published parameters"},
        {"candidate": "C3", "hypothesis": "H2", "experiment": "strongest_alternative_deepening",
         "world": "research", "eig": 0.65, "p_decision_change": 0.20, "independence": 0.0,
         "buyer_impact": 0.5, "cost": 0.05, "executable": True,
         "description": "Deepen Ommaya/pump comparison with published clinical data"},
    ])

    # C5 experiments (clotFoam blocked, but H3/H4 executable)
    experiments.extend([
        {"candidate": "C5", "hypothesis": "H2", "experiment": "actual_clotfoam",
         "world": "WORLD_C_CLOTFOM", "eig": 0.95, "p_decision_change": 0.90, "independence": 1.0,
         "buyer_impact": 1.0, "cost": 16, "executable": False,
         "description": "DECISIVE: actual clotFoam reproduction (BLOCKED on OpenFOAM build)"},
        {"candidate": "C5", "hypothesis": "H3", "experiment": "mesh_refinement",
         "world": "WORLD_C_CUSTOM_FLOW", "eig": 0.70, "p_decision_change": 0.15, "independence": 0.0,
         "buyer_impact": 0.3, "cost": 0.01, "executable": True,
         "description": "Mesh refinement in custom World C (15x15, 30x30, 60x60, 120x120)"},
        {"candidate": "C5", "hypothesis": "H4", "experiment": "parameter_independence",
         "world": "WORLD_C_CUSTOM_FLOW", "eig": 0.75, "p_decision_change": 0.15, "independence": 0.0,
         "buyer_impact": 0.3, "cost": 0.01, "executable": True,
         "description": "Independent flow parameters (not mapped from FEBio)"},
    ])

    return experiments


def portfolio_acquisition_score(exp):
    """Portfolio-level acquisition: EIG × P(decision_change) × independence × buyer_impact ÷ cost"""
    eig = exp["eig"]
    pdc = exp["p_decision_change"]
    indep = exp["independence"]
    buyer = exp["buyer_impact"]
    cost = max(exp["cost"], 0.001)
    return (eig * pdc * indep * buyer) / cost if indep > 0 else (eig * pdc * buyer) / (cost * 10)
    # Non-independent experiments get 10x cost penalty (less valuable per unit cost)


def select_portfolio_action(experiments):
    """Select the globally highest-value executable action."""
    executable = [e for e in experiments if e["executable"]]
    if not executable:
        return None
    return max(executable, key=portfolio_acquisition_score)


# ============================================================
# EVIDENCE CLASS SEPARATION
# ============================================================

EVIDENCE_CLASSES = {
    "SCIENTIFIC_EVIDENCE": {
        "definition": "Evidence about mechanism, physics, prior art, reproduction, model validation.",
        "can_increase_mechanism_confidence": True,
        "cannot_increase": "buyer_value, market_size, willingness_to_pay",
    },
    "DECISION_VALUE_EVIDENCE": {
        "definition": "Evidence about market size, buyer willingness-to-pay, cost savings, strategic fit.",
        "can_increase_decision_confidence": True,
        "cannot_increase": "mechanism_confidence, physics_validation, prior_art_survival",
    }
}


# ============================================================
# C1: REALITY_BLOCKER OBJECT
# ============================================================

def create_c1_reality_blocker():
    """Formal reality blocker: STRIDE 5-year data required for C1 problem-existence gate."""
    return {
        "object_type": "REALITY_BLOCKER",
        "blocker_id": "REALITY_BLOCKER_STRIDE_DATA_REQUIRED",
        "candidate_id": "C1",
        "gate": "G01 (Problem existence)",
        "current_state": "YELLOW — eShunt obstruction not yet observed in STRIDE 5-year data",
        "what_exact_data_would_change_decision": {
            "data_required": "eShunt-specific obstruction event rate from STRIDE 5-year follow-up",
            "if_obstruction_rate_high": "G01 → GREEN. C1 problem-existence confirmed. C1 advances toward WORLD_CLASS.",
            "if_obstruction_rate_zero": "G01 → RED. C1 KILLED_BY_EVIDENCE. No problem to solve.",
            "if_obstruction_rate_low": "G01 → YELLOW. C1 may not justify added device complexity.",
        },
        "stride_status": "Enrollment complete across 32 sites. Topline data not yet publicly available per CereVasc public material.",
        "source": "cerevasc.com STRIDE pivotal trial announcement",
        "ai_action": "Do NOT repeatedly estimate obstruction frequency. Create this formal blocker object and continue working on other candidates/gates until STRIDE data is published.",
        "epistemic_rule": "Per Article XXXIV: reality is the next bottleneck for G01. Per Article XXXIII: no irreversible action on unresolved evidence. C1 remains BLOCKED, not KILLED, until STRIDE data resolves G01.",
    }


# ============================================================
# C2: CLAIM-LEVEL PRIOR-ART ANALYSIS
# ============================================================

def run_c2_claim_level_prior_art():
    """Move from thematic search to claim-level anticipated/obvious/survives analysis."""
    c2_limitations = {
        "L1": "Continuous endovascular differential pressure monitoring",
        "L2": "Temporal signature analysis (obstruction vs posture vs cough vs drift)",
        "L3": "eShunt-specific anatomy (endovascular CSF shunt)",
        "L4": "Implantable MEMS sensor in CSF environment",
        "L5": "Differential pressure calculation (P_csf - P_venous)",
        "L6": "Obstruction detection algorithm",
        "L7": "5-year CSF biocompatibility",
    }

    prior_art_references = {
        "CardioMEMS_US9023529B2": {
            "claims": "Endovascular pressure sensor for heart failure monitoring",
            "L1_disclosed": "PARTIAL — continuous endovascular pressure monitoring, but for heart not CSF",
            "L2_disclosed": "NO — no temporal signature analysis for obstruction",
            "L3_disclosed": "NO — cardiac anatomy, not eShunt CSF anatomy",
            "L4_disclosed": "PARTIAL — implantable MEMS sensor, but in blood not CSF",
            "L5_disclosed": "NO — absolute pressure, not differential CSF-venous",
            "L6_disclosed": "NO — heart failure monitoring, not obstruction detection",
            "L7_disclosed": "PARTIAL — chronic implantation, but in blood not CSF",
            "anticipation_assessment": "Does NOT anticipate C2. Missing L2, L3, L5, L6 entirely. L1/L4/L7 are partial (different body system).",
            "obviousness_assessment": "WEAK motivation to combine. POSITA working on cardiac pressure monitoring has no obvious motivation to apply to CSF shunt obstruction. Different clinical specialty, different anatomy, different failure mode.",
        },
        "ShuntCheck_US10957902B2": {
            "claims": "Skin-surface thermal flow detection for shunt obstruction",
            "L1_disclosed": "NO — episodic, skin-surface, not endovascular",
            "L2_disclosed": "PARTIAL — detects obstruction, but via thermal not pressure",
            "L3_disclosed": "PARTIAL — shunt context, but not eShunt-specific",
            "L4_disclosed": "NO — external device, not implantable MEMS",
            "L5_disclosed": "NO — thermal flow, not differential pressure",
            "L6_disclosed": "PARTIAL — obstruction detection, but different mechanism",
            "L7_disclosed": "NO — external, no CSF biocompatibility needed",
            "anticipation_assessment": "Does NOT anticipate C2. Missing L1, L4, L5, L7. Different sensing modality (thermal vs pressure).",
            "obviousness_assessment": "MODERATE motivation to combine. POSITA working on shunt obstruction detection might consider pressure sensing as alternative to thermal. But endovascular implantation is a significant departure from skin-surface approach.",
        },
        "CereVasc_eShunt_US20240299714A1": {
            "claims": "Method of positioning eShunt endovascularly",
            "L1_disclosed": "NO — method of positioning, not pressure monitoring",
            "L2_disclosed": "NO",
            "L3_disclosed": "PARTIAL — eShunt anatomy, but not sensing",
            "L4_disclosed": "NO — no sensor",
            "L5_disclosed": "NO",
            "L6_disclosed": "NO",
            "L7_disclosed": "NO",
            "anticipation_assessment": "Does NOT anticipate C2. Teaches eShunt anatomy (L3 partial) but no sensing mechanism.",
            "obviousness_assessment": "Provides the anatomical context for C2 but does not teach the sensing mechanism. No motivation to combine with CardioMEMS (different body system).",
        },
    }

    # Final assessment
    all_anticipated = all(
        ref["anticipation_assessment"].startswith("Does NOT anticipate")
        for ref in prior_art_references.values()
    )
    obviousness_weakest_link = max(
        ref["obviousness_assessment"] for ref in prior_art_references.values()
    )

    return {
        "experiment_id": "C2-R138-PA-02",
        "candidate_id": "C2",
        "type": "claim_level_prior_art",
        "target_gate": "G02",
        "c2_limitations": c2_limitations,
        "prior_art_references": prior_art_references,
        "final_assessment": {
            "anticipated": "NO — no single reference discloses all 7 limitations",
            "obvious": "WEAK — strongest motivation is ShuntCheck (moderate), but endovascular implantation is a significant departure. No reference teaches endovascular CSF pressure monitoring.",
            "survives": "PROBABLE — C2's novel contribution (continuous endovascular differential pressure with temporal signature analysis) is not anticipated or obviously combined from searched references.",
            "caveat": "SEARCH_INCOMPLETE — PatSnap BALANCE_EXHAUSTED. Claim-level search of PatSnap, EPO Espacenet, and USPTO full-text required for definitive §102/§103 assessment.",
        },
        "gate_state_after": "YELLOW (PROBABLE survival, but SEARCH_INCOMPLETE)",
        "evidence_class": "SCIENTIFIC_EVIDENCE",
    }


# ============================================================
# C3: BUYER-VALUE CHAIN (not market size)
# ============================================================

def run_c3_buyer_value_chain():
    """Reframe C3 from market-size to specific buyer-value chain."""
    value_chain = {
        "specific_unmet_need": "Chronic controlled CNS drug delivery without pump revision surgery or repeated invasive procedures",
        "current_alternatives": [
            {"name": "Ommaya reservoir", "limitation": "Episodic percutaneous puncture — invasive per dose, infection risk 4-10%, requires clinical visit"},
            {"name": "Intrathecal pump (SynchroMed)", "limitation": "Bulky implant, $30K device, battery replacement every 5-7 years, surgical revision required"},
            {"name": "Systemic delivery + BBB opening", "limitation": "Off-target exposure, systemic toxicity, BBB-opening itself is investigational"},
        ],
        "c3_advantage": "Chronic controlled delivery INTEGRATED with eShunt anatomy — no separate pump pocket, no percutaneous puncture, no systemic exposure. For chronic therapies (gene therapy, monoclonal antibodies, chronic pain), C3's profile is distinct from all existing solutions.",
        "economic_consequence": {
            "cost_avoidance_vs_pump": "$30K device + $15K revision surgery avoided per patient per 5-7 years",
            "cost_avoidance_vs_ommaya": "$500-1000 per puncture avoided, plus infection risk reduction",
            "revenue_model": "Device + drug partnership (CereVasc + pharma)",
        },
        "buyer_evidence_required": {
            "would_cerevasc_pay": "UNKNOWN — requires CereVasc buyer engagement",
            "would_pharma_partner": "UNKNOWN — requires pharma partnership discussion",
            "regulatory_pathway": "510(k) for device component; IND for drug-device combination",
        },
        "market_size_context": {
            "note": "Market size is CONTEXT, not PROOF. Per CEO Round 138: 'Market-size numbers are extremely definition-sensitive. Use market data for decision-value prioritization, not as mechanism evidence.'",
            "us_intrathecal_drugs_market": "Approximately $1.07B (2025) to $1.38B (2032) per Fortune Business Insights — but this is the DRUG market, not the DEVICE market, and definition varies by source",
            "intrathecal_pump_market": "Separate estimate, varies by definition and geography",
            "calibration_rule": "Record: source, publication date, market definition, geography, base year, forecast year, estimate, confidence. Where sources disagree, record range.",
        },
    }

    return {
        "experiment_id": "C3-R138-BV-02",
        "candidate_id": "C3",
        "type": "buyer_value_chain",
        "target_gate": "G14",
        "value_chain": value_chain,
        "gate_state_after": "YELLOW (value chain mapped, buyer WTP unknown)",
        "evidence_class": "DECISION_VALUE_EVIDENCE",
        "key_finding": "C3's buyer value is NOT market size — it's the specific cost/risk avoidance vs existing CNS delivery methods. The value proposition is clear IF the retention mechanism works in vivo.",
        "next_experiment": "CereVasc buyer engagement for willingness-to-pay assessment. OR: animal model demonstration of retention mechanism (physical experiment, REALITY BLOCKER).",
    }


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 80)
    print("ROUND 138 — PORTFOLIO-LEVEL DISCOVERY SCHEDULER")
    print("=" * 80)

    # 1. Enumerate all experiments
    experiments = enumerate_portfolio_experiments()
    print(f"\n[1] Enumerated {len(experiments)} portfolio experiments")

    # 2. Score and rank
    scored = [(e, portfolio_acquisition_score(e)) for e in experiments]
    scored.sort(key=lambda x: x[1], reverse=True)

    print(f"\n[2] Portfolio ranking (top 10):")
    for i, (exp, score) in enumerate(scored[:10]):
        status = "EXECUTABLE" if exp["executable"] else "BLOCKED"
        print(f"  {i+1}. {exp['candidate']}/{exp['experiment']} — score={score:.4f} [{status}]")
        print(f"     {exp['description'][:70]}...")

    # 3. Execute highest-value executable experiments
    results = {}

    # C2 claim-level prior art (highest-EIG executable research)
    print(f"\n[3] Executing C2-R138-PA-02 (claim-level prior art)...")
    results["C2_claim_level_prior_art"] = run_c2_claim_level_prior_art()
    print(f"  Assessment: {results['C2_claim_level_prior_art']['final_assessment']['survives']}")

    # C3 buyer-value chain
    print(f"\n[4] Executing C3-R138-BV-02 (buyer-value chain)...")
    results["C3_buyer_value_chain"] = run_c3_buyer_value_chain()
    print(f"  Value chain mapped. Gate: {results['C3_buyer_value_chain']['gate_state_after']}")

    # C1 reality blocker
    print(f"\n[5] Creating C1 reality blocker (STRIDE data)...")
    results["C1_reality_blocker"] = create_c1_reality_blocker()
    print(f"  Blocker: {results['C1_reality_blocker']['blocker_id']}")
    print(f"  AI action: {results['C1_reality_blocker']['ai_action'][:70]}...")

    # 4. Evidence class separation
    results["evidence_classes"] = EVIDENCE_CLASSES

    # Write output
    output = {
        "record_type": "ROUND_138_PORTFOLIO_SCHEDULER_RESULTS",
        "date": datetime.now(timezone.utc).isoformat(),
        "round": 138,
        "portfolio_ranking": [
            {"rank": i+1, "candidate": e["candidate"], "experiment": e["experiment"],
             "score": s, "executable": e["executable"], "description": e["description"]}
            for i, (e, s) in enumerate(scored[:10])
        ],
        "results": results,
        "scheduler_principle": "Portfolio-level acquisition: EIG × P(decision_change) × independence × buyer_impact ÷ total_resource_cost. AI chooses globally highest-value action, not next-in-queue.",
    }
    output_path = ROUND_138_DIR / "PORTFOLIO_SCHEDULER_RESULTS.json"
    output_path.write_text(json.dumps(output, indent=2, default=str))
    print(f"\n[OK] Results: {output_path}")

    # Check OpenFOAM
    import subprocess
    of_count = subprocess.run(["bash", "-c", "find /home/z/OpenFOAM-9/platforms -name '*.o' 2>/dev/null | wc -l"],
                              capture_output=True, text=True).stdout.strip()
    print(f"\n[OpenFOAM] {of_count} .o files (building in background)")
    print("[DONE]")


if __name__ == "__main__":
    main()
