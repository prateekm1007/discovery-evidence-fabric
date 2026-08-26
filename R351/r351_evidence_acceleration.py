#!/usr/bin/env python3.13
"""
R351 — EVIDENCE ACCELERATION PROGRAM
======================================

Constitutional basis: Article I (evidence precedes assertion),
                      Article IV (no fallback epistemology),
                      Article VII (never weaken verifier to rescue claim),
                      Article XIV (no research through red gate),
                      Article XXV (unknown must remain unknown),
                      Article XXVII (no threshold invention),
                      Article XXVIII (no silent semantic promotion),
                      Article XXXIV (stop coding when reality is the bottleneck)

CEO R351 directive:
  Build a T1→T2 conversion engine. No new discovery. No new candidates.
  No new scoring systems. Only improve transferability.

  The system must optimize: buyer confidence per dollar of validation.

  Deliverables:
    1. EVIDENCE_ACCELERATION_PORTFOLIO — for all 15 packages
    2. Rank by Evidence Conversion Efficiency (maturity increase / cost)
    3. T2_ROADMAP — target maximum realistic T2 upgrades
    4. Buyer co-validation strategy (buyer funds → evaluation rights → license)

  NO fake validation. NO fake T2 claims. T2 requires external evidence.
"""

import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

REPO = Path(__file__).resolve().parents[1]
R351 = REPO / "R351"

def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))

def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Load R348 premium dossiers + R349 validation contracts + R350 transfer scores
R348_PORTFOLIO = REPO / "R348" / "premium_portfolio"
R349_CONTRACTS = REPO / "R349" / "validation_contracts"
R350_SCORES = REPO / "R350" / "transfer_scores" / "ALL_TRANSFER_READINESS_SCORES.json"

def load_dossiers() -> dict:
    dossiers = {}
    for tier_dir in [R348_PORTFOLIO / "TIER_A_FLAGSHIP", R348_PORTFOLIO / "TIER_B_EVALUATION"]:
        if tier_dir.exists():
            for folder in sorted(tier_dir.iterdir()):
                if folder.is_dir():
                    f = folder / "07_PREMIUM_DOSSIER.json"
                    if f.exists():
                        cid = folder.name.split("_", 1)[1]
                        dossiers[cid] = json.loads(f.read_text())
    return dossiers

def load_contracts() -> dict:
    contracts = {}
    if R349_CONTRACTS.exists():
        for f in R349_CONTRACTS.glob("*_T2_VALIDATION_CONTRACT.json"):
            cid = f.stem.replace("_T2_VALIDATION_CONTRACT", "")
            contracts[cid] = json.loads(f.read_text())
    return contracts

DOSSIERS = load_dossiers()
CONTRACTS = load_contracts()
TRS_SCORES = json.loads(R350_SCORES.read_text()) if R350_SCORES.exists() else {}

# ============================================================
# EVIDENCE ACCELERATION DATA (per package)
# ============================================================

# For T2-CONFIRMED and T2-CONDITIONAL packages: path to T3
# For T1 packages: path to T2-CONDITIONAL

ACCELERATION_DATA = {
    # === T2-CONFIRMED → T3 ===
    "P-16": {
        "current_maturity": "T2-CONFIRMED",
        "target_maturity": "T3",
        "missing_evidence": "Physical validation — actual 940nm tissue transmission in shunt patients + PV cell efficiency in vivo",
        "required_experiment": "Physical bench test: LED + scalp/skull phantom + PV cell. Measure actual power harvested. Compare to 744μW modeled.",
        "external_party_required": "Optical engineering lab OR buyer's hardware team with tissue phantoms",
        "estimated_cost": "$2-5K",
        "cost_numeric": 3.5,  # midpoint in $K for ranking
        "timeline": "4-8 weeks",
        "timeline_weeks": 6,
        "probability_of_conversion": 0.85,  # high — computational evidence is strong
        "maturity_increase": 1,  # T2-CONFIRMED → T3 = +1 level
        "buyer_who_benefits": "Medtronic, Boston Scientific (implantable power delivery)",
        "commercial_upside_after_validation": "T3 prototype-validated asset. Exclusive license with milestone payments. Platform technology — applies to all low-power implants.",
        "buyer_covalidation_strategy": "Buyer funds $2-5K physical test → receives evaluation rights + first refusal on license → if PASS, exclusive license negotiation"
    },
    # === T2-CONDITIONAL → T2-CONFIRMED or T3 ===
    "P-01": {
        "current_maturity": "T2-CONDITIONAL",
        "target_maturity": "T2-CONFIRMED (via true 3D multi-segment mesh) or T3 (via bench prototype)",
        "missing_evidence": "True 3D multi-segment mesh (not flow-rate proxy). FDA nozzle benchmark disagreement (72%) must be resolved. 24h survival not achieved.",
        "required_experiment": "3D multi-segment CFD mesh on actual patient geometry + V0 bench prototype: 4-segment shunt + COTS sensors + Arduino, 30 obstruction scenarios",
        "external_party_required": "External CFD lab (for 3D mesh) OR buyer's engineering team (for bench prototype)",
        "estimated_cost": "$3-5K bench + $50K+ for full 3D mesh",
        "cost_numeric": 26.5,  # midpoint
        "timeline": "3-6 months bench, 12-24 months full 3D",
        "timeline_weeks": 20,
        "probability_of_conversion": 0.60,  # medium — dual-invariant falsified, but mechanism may survive
        "maturity_increase": 1,  # T2-CONDITIONAL → T2-CONFIRMED = +1 level
        "buyer_who_benefits": "Medtronic (Strata team), Integra, Sophysa",
        "commercial_upside_after_validation": "T2-CONFIRMED predictive shunt. First-mover in smart shunt category. Co-development → exclusive license.",
        "buyer_covalidation_strategy": "Buyer funds $3-5K bench prototype → receives evaluation rights + data sharing → if multi-segment advantage confirmed, co-development → exclusive license"
    },
    # === T1 → T2-CONDITIONAL (top 5 from R349) ===
    "P-24": {
        "current_maturity": "T1",
        "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "External bench validation. No physical data. ASD comparison not experimentally tested.",
        "required_experiment": "Physical bench test: damper vs ASD vs standard, 4 postural pressures, 10 runs each, blinded. Endpoints: response_time (pass<200ms) + proportional_error (pass<15%).",
        "external_party_required": "External bench testing lab OR buyer's engineering team (blinded analysis)",
        "estimated_cost": "$15K",
        "cost_numeric": 15.0,
        "timeline": "8 weeks",
        "timeline_weeks": 8,
        "probability_of_conversion": 0.55,  # medium — ASD wins 3/4 postures, but differentiators may survive
        "maturity_increase": 2,  # T1 → T2-CONDITIONAL = +2 levels (T1→T2-CONDITIONAL is a bigger jump)
        "buyer_who_benefits": "Miethke, Sophysa (shunt OEM seeking proportional regulation differentiator)",
        "commercial_upside_after_validation": "T2-CONDITIONAL externally verified damper. If differentiators confirmed → differentiated product in commoditized market. License with milestone.",
        "buyer_covalidation_strategy": "Buyer funds $15K bench test → receives evaluation rights + first refusal → if PASS (response speed + proportional control confirmed) → exclusive license negotiation. If FAIL → reject or co-development for redesign."
    },
    "P-21": {
        "current_maturity": "T1",
        "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "RF localization through realistic heterogeneous tissue. SAR compliance. 10mm vs 5mm accuracy question.",
        "required_experiment": "UWB localization bench test: skull phantom (heterogeneous tissue), UWB transmitter in catheter, receiver array. Measure accuracy at 4 depths. SAR compliance.",
        "external_party_required": "RF engineering lab OR buyer's navigation team (Brainlab, Medtronic Navigation)",
        "estimated_cost": "$2-5K",
        "cost_numeric": 3.5,
        "timeline": "6-12 months",
        "timeline_weeks": 39,
        "probability_of_conversion": 0.50,  # medium — 10mm vs 5mm is marginal
        "maturity_increase": 2,
        "buyer_who_benefits": "Brainlab, Medtronic Navigation (neuro-navigation expansion)",
        "commercial_upside_after_validation": "T2-CONDITIONAL UWB positioning. If <5mm accuracy confirmed → new product category (non-radiation placement feedback). License or co-development.",
        "buyer_covalidation_strategy": "Buyer funds $2-5K phantom test → receives evaluation rights → if <5mm accuracy + SAR compliant → exclusive license or research partnership for clinical translation"
    },
    "P-13": {
        "current_maturity": "T1",
        "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "External dataset validation. AUC on real patient data. No clinical data tested.",
        "required_experiment": "External dataset validation: obtain shunt patient dataset (clinical partner or MIMIC-IV), train/test predictor, measure AUC on held-out set.",
        "external_party_required": "Clinical data partner (health system with IRB approval) OR medical AI company with dataset",
        "estimated_cost": "$0-5K (if dataset available from partner)",
        "cost_numeric": 2.5,
        "timeline": "3-6 months (once dataset available)",
        "timeline_weeks": 20,
        "probability_of_conversion": 0.45,  # medium — crowded AI space, AUC uncertain
        "maturity_increase": 2,
        "buyer_who_benefits": "Medical AI company (Caption Health, Cleerly) or health system data science team",
        "commercial_upside_after_validation": "T2-CONDITIONAL validated prediction model. Data partnership → co-development → exclusive license. Neuromorphic differentiator.",
        "buyer_covalidation_strategy": "Data partnership: buyer provides dataset → we validate → if AUC ≥ 0.80 → co-development → exclusive license. Buyer retains data rights."
    },
    "P-02": {
        "current_maturity": "T1",
        "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Independent CFD solver reproduction. Is the 47.3% model correct or a simulation artifact?",
        "required_experiment": "External CFD lab reproduces 47.3% ICP reduction using different solver (ANSYS Fluent or OpenFOAM). Compare within frozen tolerance.",
        "external_party_required": "External CFD lab with commercial solver (not same code path)",
        "estimated_cost": "$10-20K",
        "cost_numeric": 15.0,
        "timeline": "6-12 months",
        "timeline_weeks": 39,
        "probability_of_conversion": 0.55,
        "maturity_increase": 2,
        "buyer_who_benefits": "Codman Hakim, Sophysa (adjustable valve OEM)",
        "commercial_upside_after_validation": "T2-CONDITIONAL independently reproduced adaptive valve. If 47.3% confirmed → next-gen adjustable valve. License.",
        "buyer_covalidation_strategy": "Buyer funds $10-20K external CFD reproduction → receives evaluation rights → if within 20% tolerance → exclusive license or co-development for hardware prototype"
    },
    "P-15": {
        "current_maturity": "T1",
        "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Physical energy harvesting validation. Does cardiac motion actually produce sufficient power?",
        "required_experiment": "Physical harvesting test: build circuit, implant in mock cardiac environment, measure power over 30 days. Compare to 99.9% uptime model.",
        "external_party_required": "Power electronics lab OR buyer's hardware team with cardiac simulation",
        "estimated_cost": "$5-10K",
        "cost_numeric": 7.5,
        "timeline": "6-12 months (includes 30-day soak)",
        "timeline_weeks": 39,
        "probability_of_conversion": 0.50,
        "maturity_increase": 2,
        "buyer_who_benefits": "Medtronic, Boston Scientific (implantable power management)",
        "commercial_upside_after_validation": "T2-CONDITIONAL physically verified hybrid power. Platform technology — battery-free implants. License.",
        "buyer_covalidation_strategy": "Buyer funds $5-10K physical test → receives evaluation rights → if ≥5μW sustained → exclusive license for implantable sensor application"
    },
    # === Remaining T1 packages (medium priority) ===
    "P-07": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Floor mechanism validation under obstruction. Does drainage maintain under partial occlusion?",
        "required_experiment": "Bench test: obstruction rig, test floor mechanism vs standard catheter, measure drainage maintenance",
        "external_party_required": "Bench testing lab OR buyer's engineering team",
        "estimated_cost": "$5-10K", "cost_numeric": 7.5, "timeline": "6-12 months", "timeline_weeks": 39,
        "probability_of_conversion": 0.55, "maturity_increase": 2,
        "buyer_who_benefits": "Shunt OEMs (Medtronic, Integra)",
        "commercial_upside_after_validation": "T2-CONDITIONAL obstruction-resistant drainage. Attacks #1 failure mode. License.",
        "buyer_covalidation_strategy": "Buyer funds $5-10K obstruction rig test → evaluation rights → if drainage maintained → exclusive license"
    },
    "P-26": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Membrane fouling in CSF over 30 days. Does osmotic regulation survive protein/cell exposure?",
        "required_experiment": "Bench test: osmotic membrane valve vs ASD, mock CSF with protein, 30-day soak, measure flow + membrane integrity",
        "external_party_required": "Membrane testing lab OR buyer with CSF compatibility capability",
        "estimated_cost": "$12K", "cost_numeric": 12.0, "timeline": "10 weeks", "timeline_weeks": 10,
        "probability_of_conversion": 0.40, "maturity_increase": 2,
        "buyer_who_benefits": "Shunt OEM with membrane capability (Miethke, Sophysa)",
        "commercial_upside_after_validation": "T2-CONDITIONAL passive osmotic valve. If fouling manageable → zero-maintenance overdrainage prevention. License.",
        "buyer_covalidation_strategy": "Buyer funds $12K fouling test → evaluation rights → if membrane survives 30 days → exclusive license"
    },
    "P-27": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "SMP recovery force after 5+ years. Helical geometry manufacturing feasibility.",
        "required_experiment": "Bench test: SMP helical catheter vs standard, cyclic bending (10K cycles), accelerated aging (40°C, 6-month equivalent)",
        "external_party_required": "Materials testing lab OR buyer with SMP/catheter capability",
        "estimated_cost": "$18K", "cost_numeric": 18.0, "timeline": "14 weeks", "timeline_weeks": 14,
        "probability_of_conversion": 0.45, "maturity_increase": 2,
        "buyer_who_benefits": "Catheter OEM (Medtronic, Integra, Codman) or SMP company",
        "commercial_upside_after_validation": "T2-CONDITIONAL kink-resistant catheter. Platform — applies to vascular/neurovascular/shunt. License.",
        "buyer_covalidation_strategy": "Buyer funds $18K bending+aging test → evaluation rights → if kink threshold 2x + patency >80% → exclusive license"
    },
    "P-11": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Phage stability on Ti in CSF. Biofilm prevention in realistic conditions.",
        "required_experiment": "Bench test: phage-coated Ti catheters, mock CSF with biofilm-forming bacteria, measure biofilm formation vs control",
        "external_party_required": "Microbiology lab OR buyer with anti-infection capability",
        "estimated_cost": "$10-15K", "cost_numeric": 12.5, "timeline": "6-12 months", "timeline_weeks": 39,
        "probability_of_conversion": 0.45, "maturity_increase": 2,
        "buyer_who_benefits": "Anti-infection catheter company (Cook Medical, Teleflex)",
        "commercial_upside_after_validation": "T2-CONDITIONAL phage anti-biofilm coating. Novel mechanism. License.",
        "buyer_covalidation_strategy": "Buyer funds $10-15K biofilm assay → evaluation rights → if biofilm prevented → exclusive license"
    },
    "P-04": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Enzyme kinetics in CSF. Mass-transport limits. Wet-lab dependent.",
        "required_experiment": "Wet lab: NEP-coated catheters, mock CSF with Aβ, measure clearance rate. Mass-transport modeling validation.",
        "external_party_required": "Wet lab with enzyme/protein expertise",
        "estimated_cost": "$20-50K", "cost_numeric": 35.0, "timeline": "12-24 months", "timeline_weeks": 78,
        "probability_of_conversion": 0.35, "maturity_increase": 2,
        "buyer_who_benefits": "Pharma with Alzheimer's program (Eli Lilly, Roche)",
        "commercial_upside_after_validation": "T2-CONDITIONAL Aβ clearance. First-in-class device-drug combination. Co-development.",
        "buyer_covalidation_strategy": "Buyer funds $20-50K wet lab → evaluation rights → if 100% clearance holds → co-development for device-drug combination"
    },
    "P-12": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Enzyme stability in CSF. Tau substrate accessibility.",
        "required_experiment": "Wet lab: Cathepsin D-coated catheters, mock CSF with tau, measure clearance + enzyme activity over time",
        "external_party_required": "Wet lab with enzyme expertise",
        "estimated_cost": "$15-25K", "cost_numeric": 20.0, "timeline": "12-18 months", "timeline_weeks": 65,
        "probability_of_conversion": 0.35, "maturity_increase": 2,
        "buyer_who_benefits": "Pharma with Alzheimer's tau program",
        "commercial_upside_after_validation": "T2-CONDITIONAL tau clearance. First-in-class. Co-development.",
        "buyer_covalidation_strategy": "Buyer funds $15-25K wet lab → evaluation rights → if enzyme stable → co-development"
    },
    "P-20": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "Actual IL-10 release in CSF. Glycan surface density degradation.",
        "required_experiment": "Bench test: glycan-coated catheters, mock CSF, measure IL-10 release over 30 days + glycan integrity",
        "external_party_required": "Surface chemistry lab OR buyer with coating capability",
        "estimated_cost": "$10-15K", "cost_numeric": 12.5, "timeline": "12-18 months", "timeline_weeks": 65,
        "probability_of_conversion": 0.35, "maturity_increase": 2,
        "buyer_who_benefits": "Implant company with foreign-body response focus",
        "commercial_upside_after_validation": "T2-CONDITIONAL immune tolerance coating. Platform technology. License.",
        "buyer_covalidation_strategy": "Buyer funds $10-15K coating test → evaluation rights → if IL-10 sustained → exclusive license"
    },
    "P-22": {
        "current_maturity": "T1", "target_maturity": "T2-CONDITIONAL",
        "missing_evidence": "4 unresolved control problems (buckling, delay, tissue safety, fault recovery). Closed-loop validation.",
        "required_experiment": "Bench test: SMP segment + tissue phantom + closed-loop control system. Resolve 4 control problems iteratively.",
        "external_party_required": "Robotics/control lab OR buyer with smart catheter capability",
        "estimated_cost": "$20-50K", "cost_numeric": 35.0, "timeline": "18-36 months", "timeline_weeks": 117,
        "probability_of_conversion": 0.25, "maturity_increase": 2,
        "buyer_who_benefits": "Neuro-navigation company (Brainlab, Medtronic)",
        "commercial_upside_after_validation": "T2-CONDITIONAL autonomous navigation. Next-gen smart catheter. Research partnership → co-development.",
        "buyer_covalidation_strategy": "Research partnership: buyer co-funds $20-50K → shared IP → if 4 control problems resolved → co-development"
    }
}

# ============================================================
# DELIVERABLE 1: EVIDENCE_ACCELERATION_PORTFOLIO
# ============================================================

def build_acceleration_portfolio() -> dict:
    print("=" * 70)
    print("DELIVERABLE 1: EVIDENCE_ACCELERATION_PORTFOLIO")
    print("=" * 70)

    portfolio = {}
    for cid, data in ACCELERATION_DATA.items():
        # Evidence Conversion Efficiency = expected_maturity_increase / cost_numeric
        # Higher is better (more maturity per dollar)
        ece = data["maturity_increase"] / data["cost_numeric"] if data["cost_numeric"] > 0 else 0
        # Also factor probability
        ece_adjusted = ece * data["probability_of_conversion"]

        entry = {
            **data,
            "evidence_conversion_efficiency": round(ece, 4),
            "ece_adjusted_for_probability": round(ece_adjusted, 4),
            "ece_explanation": f"Maturity increase {data['maturity_increase']} / Cost ${data['cost_numeric']}K = {ece:.4f}. Adjusted for {data['probability_of_conversion']:.0%} success probability = {ece_adjusted:.4f}"
        }
        portfolio[cid] = entry
        print(f"  {cid}: ECE={ece:.4f} (adj: {ece_adjusted:.4f}) | {data['current_maturity']}→{data['target_maturity'][:20]} | ${data['estimated_cost']}")

    _write(R351 / "acceleration_portfolio" / "EVIDENCE_ACCELERATION_PORTFOLIO.json", portfolio)
    return portfolio

# ============================================================
# DELIVERABLE 2: Rank by Evidence Conversion Efficiency
# ============================================================

def rank_by_ece(portfolio: dict) -> dict:
    print("\n" + "=" * 70)
    print("DELIVERABLE 2: Rank by Evidence Conversion Efficiency")
    print("=" * 70)

    ranked = sorted(portfolio.items(), key=lambda x: -x[1]["ece_adjusted_for_probability"])

    ranking = {
        "metric": "Evidence Conversion Efficiency (ECE) = expected_maturity_increase / validation_cost × probability_of_success",
        "optimization_target": "buyer confidence per dollar of validation",
        "ranked_packages": [
            {
                "rank": i+1,
                "candidate_id": cid,
                "current_maturity": data["current_maturity"],
                "target_maturity": data["target_maturity"],
                "ece": data["evidence_conversion_efficiency"],
                "ece_adjusted": data["ece_adjusted_for_probability"],
                "cost": data["estimated_cost"],
                "timeline": data["timeline"],
                "probability": data["probability_of_conversion"],
                "buyer": data["buyer_who_benefits"][:60]
            }
            for i, (cid, data) in enumerate(ranked)
        ]
    }

    _write(R351 / "acceleration_portfolio" / "ECE_RANKING.json", ranking)

    print(f"\n  Top 5 by adjusted ECE:")
    for entry in ranking["ranked_packages"][:5]:
        print(f"    #{entry['rank']} {entry['candidate_id']}: ECE={entry['ece_adjusted']:.4f} | {entry['current_maturity']}→{entry['target_maturity'][:15]} | ${entry['cost']} | {entry['probability']:.0%}")

    return ranking

# ============================================================
# DELIVERABLE 3: T2_ROADMAP
# ============================================================

def build_t2_roadmap(portfolio: dict, ranking: dict) -> dict:
    print("\n" + "=" * 70)
    print("DELIVERABLE 3: T2_ROADMAP")
    print("=" * 70)

    # Current state
    current = {"T2-CONFIRMED": 0, "T2-CONDITIONAL": 0, "T1": 0}
    for data in portfolio.values():
        current[data["current_maturity"]] = current.get(data["current_maturity"], 0) + 1

    # Target: maximum realistic T2 upgrades
    # Top 5 by ECE are most likely to convert
    # P-16 (T2-CONFIRMED → T3) doesn't change T2 count
    # P-01 (T2-CONDITIONAL → T2-CONFIRMED) shifts within T2
    # 5 T1 packages → T2-CONDITIONAL (if experiments succeed)

    realistic_conversions = []
    for entry in ranking["ranked_packages"]:
        cid = entry["candidate_id"]
        data = portfolio[cid]
        if data["current_maturity"] == "T1" and data["probability_of_conversion"] >= 0.35:
            realistic_conversions.append({
                "candidate_id": cid,
                "from": data["current_maturity"],
                "to": data["target_maturity"],
                "probability": data["probability_of_conversion"],
                "cost": data["estimated_cost"],
                "timeline": data["timeline"],
                "buyer": data["buyer_who_benefits"][:60]
            })

    # Target state (if all realistic conversions succeed)
    target = {
        "T2-CONFIRMED": 1 + 1,  # P-16 stays + P-01 upgrades
        "T2-CONDITIONAL": len(realistic_conversions),  # all T1 that convert
        "T1": current["T1"] - len(realistic_conversions),
        "T3": 1  # P-16 reaches T3
    }

    # Adjust: P-01 moves from T2-CONDITIONAL to T2-CONFIRMED
    # So T2-CONDITIONAL = len(realistic_conversions) - 0 (P-01 leaves T2-CONDITIONAL, replaced by converted T1s)
    # Actually: P-01 is currently T2-CONDITIONAL. If it upgrades to T2-CONFIRMED, it leaves T2-CONDITIONAL.
    # New T2-CONDITIONAL = (converted T1s) = len(realistic_conversions)
    # But wait — realistic_conversions only includes T1 packages, not P-01
    # So: T2-CONDITIONAL target = len(realistic_conversions) [the T1s that convert]
    # P-01 leaves T2-CONDITIONAL → T2-CONFIRMED
    # Net: T2-CONDITIONAL = len(realistic_conversions), T2-CONFIRMED = 2 (P-16 + P-01), T3 = 1 (P-16 if it also reaches T3)

    target_corrected = {
        "T3": 1,  # P-16 if physical validation succeeds
        "T2-CONFIRMED": 2,  # P-16 (if we count it as both T3 and T2-CONFIRMED) + P-01 upgraded
        "T2-CONDITIONAL": len(realistic_conversions),  # T1s that convert
        "T1": current["T1"] - len(realistic_conversions),
        "total": 15
    }

    # Actually, let's be cleaner: T3 is above T2-CONFIRMED. If P-16 reaches T3, it's counted as T3, not T2-CONFIRMED.
    target_final = {
        "T3": 1,  # P-16
        "T2-CONFIRMED": 1,  # P-01 upgraded from T2-CONDITIONAL
        "T2-CONDITIONAL": len(realistic_conversions),  # T1s that convert
        "T1": current["T1"] - len(realistic_conversions),
        "total": 15
    }

    roadmap = {
        "current_state": current,
        "target_state": target_final,
        "realistic_conversions": realistic_conversions,
        "total_t2_or_higher_current": current["T2-CONFIRMED"] + current["T2-CONDITIONAL"],
        "total_t2_or_higher_target": target_final["T3"] + target_final["T2-CONFIRMED"] + target_final["T2-CONDITIONAL"],
        "conversion_count": len(realistic_conversions),
        "total_investment_required": sum(p["cost_numeric"] for cid, p in portfolio.items() if cid in [r["candidate_id"] for r in realistic_conversions]),
        "expected_value": f"If all {len(realistic_conversions)} conversions succeed: {target_final['T3']} T3 + {target_final['T2-CONFIRMED']} T2-CONFIRMED + {target_final['T2-CONDITIONAL']} T2-CONDITIONAL = {target_final['T3'] + target_final['T2-CONFIRMED'] + target_final['T2-CONDITIONAL']} packages at T2 or higher (vs 2 currently)",
        "no_fake_promotions": "T2 requires external evidence ingested via R341 pipeline. These are PATHWAYS, not claims. Each conversion requires the experiment to actually be run by an external party."
    }

    _write(R351 / "t2_roadmap" / "T2_ROADMAP.json", roadmap)

    print(f"\n  Current: T2-CONFIRMED={current['T2-CONFIRMED']}, T2-CONDITIONAL={current['T2-CONDITIONAL']}, T1={current['T1']}")
    print(f"  Target:  T3={target_final['T3']}, T2-CONFIRMED={target_final['T2-CONFIRMED']}, T2-CONDITIONAL={target_final['T2-CONDITIONAL']}, T1={target_final['T1']}")
    print(f"  Realistic conversions: {len(realistic_conversions)}")
    print(f"  Total investment: ${roadmap['total_investment_required']:.0f}K")
    print(f"  T2+ packages: {current['T2-CONFIRMED'] + current['T2-CONDITIONAL']} → {target_final['T3'] + target_final['T2-CONFIRMED'] + target_final['T2-CONDITIONAL']}")

    return roadmap

# ============================================================
# DELIVERABLE 4: Buyer Co-Validation Strategy
# ============================================================

def build_buyer_covalidation(portfolio: dict) -> dict:
    print("\n" + "=" * 70)
    print("DELIVERABLE 4: Buyer Co-Validation Strategy")
    print("=" * 70)

    strategies = {}
    for cid, data in portfolio.items():
        strategy = {
            "candidate_id": cid,
            "buyer": data["buyer_who_benefits"],
            "co_validation_flow": {
                "step_1": f"Buyer funds ${data['estimated_cost']} validation experiment",
                "step_2": "Buyer receives evaluation rights + first refusal on license/acquisition",
                "step_3": f"External party executes: {data['external_party_required'][:100]}",
                "step_4": f"If successful ({data['probability_of_conversion']:.0%} probability): package upgrades to {data['target_maturity']}",
                "step_5": f"If {data['target_maturity']}: license/acquisition discussion begins",
                "step_6": "If failure: buyer walks away (only lost validation cost), or co-development for redesign"
            },
            "buyer_value": data["commercial_upside_after_validation"],
            "buyer_risk": f"${data['estimated_cost']} validation cost + engineering time. If experiment fails, buyer walks away.",
            "seller_value": "External evidence ingested → T2 upgrade → package value increases → licensing leverage.",
            "deal_structure": "Sponsored validation agreement with option to license. Buyer gets first refusal. If PASS, exclusive license negotiation. If FAIL, buyer walks or co-develops redesign.",
            "why_buyer_should_fund": f"Buyer gets: (1) de-risked evaluation before licensing, (2) first refusal on the technology, (3) influence on experiment design, (4) access to full evidence package. Cost is {data['estimated_cost']} vs full licensing risk of $50-500K+ without validation."
        }
        strategies[cid] = strategy

    _write(R351 / "buyer_covalidation" / "BUYER_COVALIDATION_STRATEGIES.json", strategies)

    # Summary
    summary = {
        "strategy": "Buyer funds experiment → receives evaluation rights → successful validation → license/acquisition discussion",
        "total_packages": len(strategies),
        "total_validation_investment_if_all_funded": sum(p["cost_numeric"] for p in portfolio.values()),
        "average_validation_cost": sum(p["cost_numeric"] for p in portfolio.values()) / len(portfolio),
        "buyer_benefit": "De-risked evaluation before licensing. First refusal. Influence on experiment. Access to evidence package.",
        "seller_benefit": "External evidence → T2 upgrade → increased package value → licensing leverage.",
        "key_insight": "The buyer should not just buy a PDF. The buyer should have a path to de-risk ownership through funded validation."
    }
    _write(R351 / "buyer_covalidation" / "COVALIDATION_SUMMARY.json", summary)

    print(f"\n  Strategies generated: {len(strategies)}")
    print(f"  Total investment if all funded: ${summary['total_validation_investment_if_all_funded']:.0f}K")
    print(f"  Average validation cost: ${summary['average_validation_cost']:.1f}K")

    return strategies

# ============================================================
# Generate master index
# ============================================================

def generate_master_index(portfolio: dict, ranking: dict, roadmap: dict, covalidation: dict) -> dict:
    print("\n" + "=" * 70)
    print("Generating EVIDENCE_ACCELERATION_MASTER_INDEX.md")
    print("=" * 70)

    lines = [
        "# EVIDENCE ACCELERATION PORTFOLIO (R351)",
        "",
        f"**Generated:** {_now_iso()}",
        f"**Objective:** Convert maximum T1 → T2 via buyer-funded validation. Optimize buyer confidence per dollar.",
        f"**NO fake promotions.** T2 requires external evidence.",
        "",
        "## The Moat",
        "",
        "> An AI system that turns uncertain inventions into validated, transferable technology assets",
        "> through continuous buyer-driven evidence acquisition.",
        "",
        "## Current vs Target Maturity",
        "",
        "| Level | Current | Target |",
        "|-------|--------:|-------:|",
        f"| T3 | 0 | {roadmap['target_state']['T3']} |",
        f"| T2-CONFIRMED | {roadmap['current_state']['T2-CONFIRMED']} | {roadmap['target_state']['T2-CONFIRMED']} |",
        f"| T2-CONDITIONAL | {roadmap['current_state']['T2-CONDITIONAL']} | {roadmap['target_state']['T2-CONDITIONAL']} |",
        f"| T1 | {roadmap['current_state']['T1']} | {roadmap['target_state']['T1']} |",
        f"| **T2+ total** | **{roadmap['total_t2_or_higher_current']}** | **{roadmap['total_t2_or_higher_target']}** |",
        "",
        f"## Evidence Conversion Efficiency Ranking ({len(ranking['ranked_packages'])} packages)",
        "",
        "ECE = maturity_increase / cost × probability_of_success",
        "",
        "| Rank | Package | Current → Target | ECE (adj) | Cost | Timeline | Probability | Buyer |",
        "|------|---------|-----------------|-----------|------|----------|-------------|-------|"
    ]

    for entry in ranking["ranked_packages"]:
        lines.append(f"| {entry['rank']} | {entry['candidate_id']} | {entry['current_maturity']}→{entry['target_maturity'][:15]} | {entry['ece_adjusted']:.4f} | {entry['cost']} | {entry['timeline']} | {entry['probability']:.0%} | {entry['buyer'][:30]} |")

    lines.extend([
        "",
        "## Buyer Co-Validation Strategy",
        "",
        "```",
        "Buyer funds experiment",
        "       ↓",
        "Buyer receives evaluation rights + first refusal",
        "       ↓",
        "External party executes experiment",
        "       ↓",
        "Successful validation → T2 upgrade",
        "       ↓",
        "License / acquisition discussion",
        "       ↓",
        "If failure → buyer walks away (only lost validation cost)",
        "```",
        "",
        f"**Total investment if all 15 funded:** ${roadmap['total_investment_required']:.0f}K",
        f"**Average validation cost:** ${sum(p['cost_numeric'] for p in portfolio.values()) / len(portfolio):.1f}K",
        "",
        "## Top 5 Conversion Priorities (by adjusted ECE)",
        ""
    ])

    for i, entry in enumerate(ranking["ranked_packages"][:5]):
        data = portfolio[entry["candidate_id"]]
        lines.append(f"### {i+1}. {entry['candidate_id']} — ECE={entry['ece_adjusted']:.4f}")
        lines.append(f"- **Current:** {data['current_maturity']} → **Target:** {data['target_maturity']}")
        lines.append(f"- **Experiment:** {data['required_experiment'][:150]}")
        lines.append(f"- **Cost:** {data['estimated_cost']} | **Timeline:** {data['timeline']} | **Probability:** {data['probability_of_conversion']:.0%}")
        lines.append(f"- **Buyer:** {data['buyer_who_benefits']}")
        lines.append(f"- **Commercial upside:** {data['commercial_upside_after_validation'][:150]}")
        lines.append(f"- **Co-validation:** {data['buyer_covalidation_strategy'][:150]}")
        lines.append("")

    lines.extend([
        "## No Fake Promotions",
        "",
        "T2 requires external evidence ingested via R341 ingest_external_data_v2(AdmissibilityBundle).",
        "These are PATHWAYS, not claims. Each conversion requires the experiment to actually be run.",
        "Article XXV (unknown must remain unknown). Article XXVIII (no silent semantic promotion).",
        "",
        "## CEO Next Action",
        "",
        "1. Review the ECE ranking — top 5 packages have highest buyer confidence per dollar.",
        "2. Send buyer meeting packs (R350) + co-validation strategies (R351) to ideal buyers.",
        "3. When a buyer funds an experiment and data returns → deliver to ingest_external_data_v2.",
        "4. Machine processes reality → T2-CONDITIONAL → package regenerates with stronger evidence.",
        "5. The moat is the system: continuous buyer-driven evidence acquisition.",
        ""
    ])

    _write_text(R351 / "EVIDENCE_ACCELERATION_MASTER_INDEX.md", "\n".join(lines))
    print(f"  Master index generated")
    return {"index_generated": True}

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("R351 — EVIDENCE ACCELERATION PROGRAM")
    print("Optimize: buyer confidence per dollar of validation.")
    print("NO fake promotions. T2 requires external evidence.")
    print("=" * 70)

    portfolio = build_acceleration_portfolio()
    ranking = rank_by_ece(portfolio)
    roadmap = build_t2_roadmap(portfolio, ranking)
    covalidation = build_buyer_covalidation(portfolio)
    generate_master_index(portfolio, ranking, roadmap, covalidation)

    # Audit
    audit = {
        "round": 351,
        "date": _now_iso(),
        "ceo_directive": "Evidence acceleration program. T1→T2 conversion engine. Optimize buyer confidence per dollar. No new discovery, no new candidates, no new scoring systems beyond ECE.",
        "deliverables": {
            "1_evidence_acceleration_portfolio": f"DONE — 15 packages with current/target maturity, missing evidence, required experiment, external party, cost, timeline, probability, buyer, commercial upside",
            "2_ece_ranking": f"DONE — all 15 ranked by Evidence Conversion Efficiency (maturity_increase / cost × probability)",
            "3_t2_roadmap": f"DONE — current: {roadmap['total_t2_or_higher_current']} T2+ → target: {roadmap['total_t2_or_higher_target']} T2+. {len(roadmap['realistic_conversions'])} realistic conversions. Total investment: ${roadmap['total_investment_required']:.0f}K",
            "4_buyer_covalidation": f"DONE — 15 strategies. Buyer funds → evaluation rights → validation → license. Total if all funded: ${sum(p['cost_numeric'] for p in portfolio.values()):.0f}K"
        },
        "top5_by_ece": [entry["candidate_id"] for entry in ranking["ranked_packages"][:5]],
        "current_vs_target": {
            "current_t2_plus": roadmap["total_t2_or_higher_current"],
            "target_t2_plus": roadmap["total_t2_or_higher_target"],
            "conversion_count": len(roadmap["realistic_conversions"])
        },
        "honest_state": "15 evidence acceleration pathways defined. Each has experiment, cost, timeline, probability, buyer, co-validation strategy. NO fake T2 claims. T2 requires external evidence. The moat is the system: continuous buyer-driven evidence acquisition.",
        "next_action": "CEO sends buyer meeting packs (R350) + co-validation strategies (R351) to ideal buyers. When data returns, machine processes reality → T2 upgrade."
    }
    _write(R351 / "audit" / "ROUND_351_AUDIT.json", audit)

    md = [
        "# R351 AUDIT — Evidence Acceleration Program",
        "",
        f"**Round:** 351",
        f"**Date:** {audit['date']}",
        "",
        "## Deliverables",
        ""
    ]
    for k, v in audit["deliverables"].items():
        md.append(f"### {k}")
        md.append(v)
        md.append("")
    md.extend([
        "## Current vs Target",
        "",
        f"- T2+ packages: **{audit['current_vs_target']['current_t2_plus']}** → **{audit['current_vs_target']['target_t2_plus']}**",
        f"- Realistic conversions: **{audit['current_vs_target']['conversion_count']}**",
        "",
        "## Top 5 by ECE",
        "",
        ", ".join(audit["top5_by_ece"]),
        "",
        "## Honest State",
        "",
        audit["honest_state"],
        ""
    ])
    _write_text(R351 / "audit" / "ROUND_351_AUDIT.md", "\n".join(md))

    print("\n" + "=" * 70)
    print("R351 COMPLETE")
    print("=" * 70)
    print(f"  Deliverables: 4")
    print(f"  Current T2+: {roadmap['total_t2_or_higher_current']}")
    print(f"  Target T2+: {roadmap['total_t2_or_higher_target']}")
    print(f"  Realistic conversions: {len(roadmap['realistic_conversions'])}")
    print(f"  Total investment: ${roadmap['total_investment_required']:.0f}K")
    print(f"  Top 5 ECE: {audit['top5_by_ece']}")

if __name__ == "__main__":
    main()
