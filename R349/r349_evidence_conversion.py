#!/usr/bin/env python3.13
"""
R349 — EVIDENCE CONVERSION PROGRAM
====================================

Constitutional basis: Article I (evidence precedes assertion),
                      Article IV (no fallback epistemology),
                      Article VII (never weaken verifier to rescue claim),
                      Article XIV (no research through red gate),
                      Article XXVII (no threshold invention),
                      Article XXVIII (no silent semantic promotion),
                      Article XXXIV (stop coding when reality is the bottleneck)

CEO R349 directive:
  R348 reached "professional transfer package" stage. No more packaging rounds.
  Next value creation: select top 5 T1 packages, create T2 validation contracts,
  show the buyer "Current T1 → $X experiment → T2 path."

  CRITICAL: NO fake promotions. T2 requires evidence. T1→T2 cannot happen through
  better writing. It requires external verification, independent reproduction,
  physical experiment, external dataset, or third-party validation.

  Gates:
    1. Rank T1 packages by T2 conversion ROI (5 criteria, each 0-5)
    2. Select top 5 T1→T2 pathways
    3. Create T2_VALIDATION_CONTRACT.json per selected package
    4. Buyer-facing upgrade: show evidence ladder path
    5. NO fake promotions — document what's missing for T2
    6. Generate evidence-conversion portfolio index
"""

import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

REPO = Path(__file__).resolve().parents[1]
R349 = REPO / "R349"

def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))

def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Load R348 premium dossiers
R348_PORTFOLIO = REPO / "R348" / "premium_portfolio"

def load_premium_dossiers() -> dict:
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

DOSSIERS = load_premium_dossiers()

# ============================================================
# GATE 1: T2 Conversion Priority Matrix
# ============================================================

# Score each T1 package on 5 criteria (0-5 each, max 25)
# CEO criteria: buyer_value, validation_cost (inverse — lower cost = higher score),
#               time_to_evidence, probability_of_success, strategic_buyer_interest

T1_PACKAGES = {cid: d for cid, d in DOSSIERS.items()
               if d["three_axes"]["technical_readiness"] == "T1"}

PRIORITY_SCORES = {
    "P-24": {
        "buyer_value": 5,           # Overdrainage prevention, clear clinical problem, $25K/complication
        "validation_cost": 5,       # $15K is low cost → high score (inverse)
        "time_to_evidence": 5,      # 8 weeks is fast
        "probability_of_success": 3, # ASD wins 3/4 postures — uncertain, but experiment is decisive
        "strategic_buyer_interest": 5, # Miethke/Sophysa identified, clear differentiator
        "total": 23,
        "rationale": "Clear bench experiment, low cost, fast timeline, identified buyer. Highest ROI."
    },
    "P-21": {
        "buyer_value": 4,           # Catheter placement, real clinical need
        "validation_cost": 5,       # $2-5K is very low
        "time_to_evidence": 4,      # 6-12 months
        "probability_of_success": 3, # 10mm vs 5mm accuracy is marginal
        "strategic_buyer_interest": 4, # Brainlab/Medtronic Navigation identified
        "total": 20,
        "rationale": "Low cost validation, physics-based, industry buyer exists. SAR unresolved."
    },
    "P-13": {
        "buyer_value": 4,           # Shunt failure prediction, high-value AI application
        "validation_cost": 5,       # $0-5K if dataset available
        "time_to_evidence": 5,      # 3-6 months with data
        "probability_of_success": 2, # Crowded AI space (R296), AUC uncertain
        "strategic_buyer_interest": 4, # Medical AI companies identified
        "total": 20,
        "rationale": "Fast and cheap IF dataset available. Data partnership is the key."
    },
    "P-02": {
        "buyer_value": 4,           # ICP excursion reduction, clinical problem
        "validation_cost": 4,       # $10-20K
        "time_to_evidence": 4,      # 6-12 months
        "probability_of_success": 3, # 47.3% modeled — needs hardware validation
        "strategic_buyer_interest": 4, # Codman/Sophysa identified
        "total": 19,
        "rationale": "Clear model, needs hardware reproduction. Medium cost/timeline."
    },
    "P-15": {
        "buyer_value": 4,           # Battery-free implants, platform technology
        "validation_cost": 4,       # $5-10K physical test
        "time_to_evidence": 4,      # 6-12 months
        "probability_of_success": 3, # 99.9% uptime modeled — needs physical confirmation
        "strategic_buyer_interest": 4, # Medtronic/Boston Scientific
        "total": 19,
        "rationale": "Platform technology, medium cost. Physical harvesting test is decisive."
    },
    "P-07": {
        "buyer_value": 4,           # Obstruction is #1 failure mode
        "validation_cost": 5,       # $5-10K
        "time_to_evidence": 4,      # 6-12 months
        "probability_of_success": 3, # Floor mechanism — needs testing
        "strategic_buyer_interest": 3, # Shunt OEMs
        "total": 19,
        "rationale": "Directly attacks #1 failure mode. Low cost bench test."
    },
    "P-26": {
        "buyer_value": 4,           # Overdrainage prevention, passive
        "validation_cost": 4,       # $12K (includes 30-day soak)
        "time_to_evidence": 4,      # 10 weeks
        "probability_of_success": 3, # Membrane fouling is primary risk
        "strategic_buyer_interest": 3, # Shunt OEMs with membrane capability
        "total": 18,
        "rationale": "Novel passive mechanism. Fouling test is decisive. New candidate (R347)."
    },
    "P-27": {
        "buyer_value": 3,           # Kink resistance, 8% of failures
        "validation_cost": 4,       # $18K (includes aging)
        "time_to_evidence": 4,      # 14 weeks
        "probability_of_success": 3, # SMP recovery uncertain over 5+ years
        "strategic_buyer_interest": 4, # Platform — applies to all catheters
        "total": 18,
        "rationale": "Platform technology (all catheters). Aging test is decisive. New (R347)."
    },
    "P-11": {
        "buyer_value": 4,           # Infection is 10% of failures, $60K/event
        "validation_cost": 4,       # $10-15K
        "time_to_evidence": 4,      # 6-12 months
        "probability_of_success": 3, # Phage stability on Ti unknown
        "strategic_buyer_interest": 3, # Anti-infection catheter companies
        "total": 18,
        "rationale": "Novel anti-infection mechanism. Phage coating bench test."
    },
    "P-04": {
        "buyer_value": 5,           # Alzheimer's — massive market
        "validation_cost": 2,       # $20-50K wet lab
        "time_to_evidence": 2,      # 12-24 months
        "probability_of_success": 2, # Wet-lab dependent, mass-transport uncertain
        "strategic_buyer_interest": 4, # Pharma with Alzheimer's programs
        "total": 15,
        "rationale": "High value but high cost and long timeline. Wet-lab dependent."
    },
    "P-12": {
        "buyer_value": 4,           # Tau clearance, Alzheimer's
        "validation_cost": 3,       # $15-25K
        "time_to_evidence": 3,      # 12-18 months
        "probability_of_success": 2, # Enzyme stability in CSF uncertain
        "strategic_buyer_interest": 3, # Pharma with Alzheimer's
        "total": 15,
        "rationale": "High value, medium cost. Enzyme stability is the question."
    },
    "P-20": {
        "buyer_value": 4,           # Foreign-body response, platform
        "validation_cost": 3,       # $10-15K
        "time_to_evidence": 3,      # 12-18 months
        "probability_of_success": 2, # IL-10 release in CSF uncertain
        "strategic_buyer_interest": 3, # Implant companies
        "total": 15,
        "rationale": "Platform technology. Glycan coating validation needed."
    },
    "P-22": {
        "buyer_value": 4,           # Autonomous navigation, OR time reduction
        "validation_cost": 2,       # $20-50K
        "time_to_evidence": 2,      # 18-36 months (4 control problems)
        "probability_of_success": 2, # 4 unresolved control problems
        "strategic_buyer_interest": 4, # Smart catheter companies
        "total": 14,
        "rationale": "High value but long timeline and 4 unresolved problems. Research partnership."
    }
}

def gate1_priority_matrix() -> dict:
    print("=" * 70)
    print("GATE 1: T2 Conversion Priority Matrix")
    print("=" * 70)

    # Sort by total score
    ranked = sorted(PRIORITY_SCORES.items(), key=lambda x: -x[1]["total"])

    matrix = {
        "gate": "GATE 1: T2 Conversion Priority Matrix",
        "scoring_criteria": {
            "buyer_value": "0-5 — clinical/commercial value of the problem",
            "validation_cost": "0-5 — inverse of cost (lower cost = higher score)",
            "time_to_evidence": "0-5 — speed to T2 (faster = higher score)",
            "probability_of_success": "0-5 — likelihood experiment succeeds",
            "strategic_buyer_interest": "0-5 — buyer identified and interested"
        },
        "max_score": 25,
        "ranked_packages": [
            {
                "rank": i+1,
                "candidate_id": cid,
                "scores": {k: v for k, v in scores.items() if k != "rationale"},
                "total": scores["total"],
                "rationale": scores["rationale"]
            }
            for i, (cid, scores) in enumerate(ranked)
        ]
    }

    _write(R349 / "priority_matrix" / "T2_CONVERSION_PRIORITY_MATRIX.json", matrix)

    for entry in matrix["ranked_packages"]:
        print(f"  #{entry['rank']} {entry['candidate_id']}: {entry['total']}/25 — {entry['rationale'][:60]}")

    return matrix

# ============================================================
# GATE 2: Select Top 5 T1→T2 Pathways
# ============================================================

def gate2_select_top5(matrix: dict) -> dict:
    print("\n" + "=" * 70)
    print("GATE 2: Select Top 5 T1→T2 Pathways")
    print("=" * 70)

    top5 = [entry["candidate_id"] for entry in matrix["ranked_packages"][:5]]

    result = {
        "gate": "GATE 2: Top 5 Selection",
        "selected": top5,
        "ceo_expected": ["P-24", "P-21", "P-13", "P-02", "P-15"],
        "match": top5 == ["P-24", "P-21", "P-13", "P-02", "P-15"],
        "rationale": "Top 5 by T2 conversion ROI. These are the packages where a defined experiment at defined cost can move T1→T2.",
        "not_selected": [e["candidate_id"] for e in matrix["ranked_packages"][5:]]
    }

    print(f"  Selected: {top5}")
    print(f"  CEO expected match: {result['match']}")
    print(f"  Not selected (remain T1): {result['not_selected']}")

    _write(R349 / "priority_matrix" / "TOP5_SELECTION.json", result)
    return result

# ============================================================
# GATE 3: T2 Validation Contracts
# ============================================================

VALIDATION_CONTRACTS = {
    "P-24": {
        "candidate_id": "P-24",
        "current_state": "T1",
        "target_state": "T2-CONDITIONAL",
        "experiment_required": "Physical bench test: damper vs ASD vs standard shunt, 4 postural pressures (10/20/30/40 mmHg), 10 runs each, blinded analysis. Endpoints: response_time_damper_ms (pass<200ms, fail>1000ms) and proportional_error_pct (pass<15%, fail>30%). 95% two-sided CI.",
        "independent_party_required": "External bench testing lab OR buyer's engineering team (blinded analysis — machine does not know result beforehand)",
        "success_threshold": "Both endpoints PASS: 95% CI entirely below pass threshold (200ms, 15%)",
        "failure_threshold": "Either endpoint FAIL: 95% CI entirely above fail threshold (1000ms, 30%)",
        "ambiguous_threshold": "CI spans pass/fail boundary → AMBIGUOUS (no silent promotion to T2)",
        "estimated_cost": "$15,000",
        "timeline": "8 weeks",
        "evidence_required_for_T2": "External bench test PASS result + raw data file + custody chain + independent verification artifact. Ingested via R341 ingest_external_data_v2(AdmissibilityBundle). Article XXXVII transition: SYNTHETIC_LOOP_VERIFIED → REAL_LOOP_VERIFIED.",
        "what_T2_means": "T2-CONDITIONAL: external bench verification confirms the mechanism works as modeled. Does NOT mean clinical validation, manufacturing readiness, or regulatory approval.",
        "what_T2_does_NOT_mean": "Does NOT mean superiority over ASD (ASD may still win on other metrics). Does NOT mean commercial readiness. Does NOT mean the technology is validated for clinical use.",
        "buyer_value_of_T2_conversion": "Buyer sees externally verified evidence, not just computational model. Licensing value increases. Risk decreases.",
        "no_fake_promotion": "T2 is granted ONLY when external data is ingested through the R341 pipeline with admissibility bundle. No narrative promotion. Article XXVIII compliant."
    },
    "P-21": {
        "candidate_id": "P-21",
        "current_state": "T1",
        "target_state": "T2-CONDITIONAL",
        "experiment_required": "UWB localization bench test: skull phantom (realistic heterogeneous tissue), UWB transmitter in catheter, receiver array external. Measure localization accuracy at 4 depths. Compare to 5mm target. SAR compliance measurement.",
        "independent_party_required": "RF engineering lab OR buyer's navigation team. Must have UWB equipment and tissue phantoms.",
        "success_threshold": "Localization accuracy <5mm at all 4 depths (95% CI below 5mm). SAR below FCC limit.",
        "failure_threshold": "Localization accuracy >10mm at any depth. SAR exceeds FCC limit.",
        "ambiguous_threshold": "5-10mm accuracy → AMBIGUOUS (marginal, needs redesign)",
        "estimated_cost": "$2-5K",
        "timeline": "6-12 months",
        "evidence_required_for_T2": "External RF lab test result + raw data + SAR compliance report + independent verification. Ingested via R341 pipeline.",
        "what_T2_means": "T2-CONDITIONAL: UWB localization verified in phantom tissue. SAR compliant.",
        "what_T2_does_NOT_mean": "Does NOT mean clinical validation. Does NOT mean the system works in real patients.",
        "buyer_value_of_T2_conversion": "Resolves the 10mm vs 5mm accuracy question. Resolves SAR. Buyer can make informed licensing decision.",
        "no_fake_promotion": "T2 only with external data ingestion."
    },
    "P-13": {
        "candidate_id": "P-13",
        "current_state": "T1",
        "target_state": "T2-CONDITIONAL",
        "experiment_required": "External dataset validation: obtain shunt patient dataset (clinical partner or MIMIC-IV credentialed access), train/test neuromorphic predictor, measure AUC on held-out test set. Compare to existing baselines.",
        "independent_party_required": "Clinical data partner (health system or research institution with IRB approval). Must provide de-identified shunt patient data.",
        "success_threshold": "AUC >= 0.80 on held-out test set (95% CI above 0.75)",
        "failure_threshold": "AUC < 0.70 on held-out test set",
        "ambiguous_threshold": "AUC 0.70-0.80 → AMBIGUOUS (needs more data or better features)",
        "estimated_cost": "$0-5K (if dataset available from partner)",
        "timeline": "3-6 months (once dataset is available)",
        "evidence_required_for_T2": "External dataset validation result + AUC measurement + independent verification (data partner attestation). Ingested via R341 pipeline.",
        "what_T2_means": "T2-CONDITIONAL: prediction model validated on external clinical data. AUC meets threshold.",
        "what_T2_does_NOT_mean": "Does NOT mean FDA AI/ML clearance. Does NOT mean clinical deployment ready.",
        "buyer_value_of_T2_conversion": "Resolves the 'needs real data' question. Data partnership becomes a validated asset.",
        "no_fake_promotion": "T2 only with external dataset validation."
    },
    "P-02": {
        "candidate_id": "P-02",
        "current_state": "T1",
        "target_state": "T2-CONDITIONAL",
        "experiment_required": "External model reproduction: independent CFD lab reproduces the 47.3% ICP excursion reduction using a different solver (e.g., ANSYS Fluent or OpenFOAM). Compare results within frozen tolerance.",
        "independent_party_required": "External CFD lab with commercial solver (not the same code path as internal model). Must run independently.",
        "success_threshold": "Independent solver reproduces ICP reduction within 20% of modeled 47.3% (i.e., 37.8% to 56.8%)",
        "failure_threshold": "Independent solver shows <20% reduction or disagrees by >50%",
        "ambiguous_threshold": "20-37% reduction → AMBIGUOUS (model overestimated)",
        "estimated_cost": "$10-20K",
        "timeline": "6-12 months",
        "evidence_required_for_T2": "External CFD solver result + comparison report + independent verification. Ingested via R341 pipeline.",
        "what_T2_means": "T2-CONDITIONAL: computational model verified by independent solver.",
        "what_T2_does_NOT_mean": "Does NOT mean physical valve validation. Does NOT mean the 47.3% holds in hardware.",
        "buyer_value_of_T2_conversion": "Resolves 'is the model correct?' question. Independent reproduction increases confidence.",
        "no_fake_promotion": "T2 only with external solver verification."
    },
    "P-15": {
        "candidate_id": "P-15",
        "current_state": "T1",
        "target_state": "T2-CONDITIONAL",
        "experiment_required": "Physical energy harvesting test: build harvesting circuit (cardiac motion + buffer), implant in mock cardiac environment, measure power output over 30 days. Compare to 99.9% uptime model.",
        "independent_party_required": "Power electronics lab OR buyer's hardware team. Must have cardiac simulation capability.",
        "success_threshold": "Sustained power output >= 5 μW for 30 days (sufficient for pacemaker-grade operation). Uptime >= 95%.",
        "failure_threshold": "Power output < 1 μW or uptime < 80%",
        "ambiguous_threshold": "1-5 μW or 80-95% uptime → AMBIGUOUS",
        "estimated_cost": "$5-10K",
        "timeline": "6-12 months (includes 30-day soak)",
        "evidence_required_for_T2": "External power harvesting test result + raw data + independent verification. Ingested via R341 pipeline.",
        "what_T2_means": "T2-CONDITIONAL: energy harvesting physically verified in mock cardiac environment.",
        "what_T2_does_NOT_mean": "Does NOT mean in-vivo validation. Does NOT mean 99.9% uptime holds in real implant.",
        "buyer_value_of_T2_conversion": "Resolves 'does harvesting actually work?' question. Physical evidence for platform technology.",
        "no_fake_promotion": "T2 only with external physical test."
    }
}

def gate3_validation_contracts(top5: dict) -> dict:
    print("\n" + "=" * 70)
    print("GATE 3: T2 Validation Contracts")
    print("=" * 70)

    contracts = {}
    for cid in top5["selected"]:
        contract = VALIDATION_CONTRACTS[cid]
        contracts[cid] = contract
        contract_file = R349 / "validation_contracts" / f"{cid}_T2_VALIDATION_CONTRACT.json"
        _write(contract_file, contract)
        print(f"  {cid}: {contract['current_state']} → {contract['target_state']} | ${contract['estimated_cost']} | {contract['timeline']}")

    return contracts

# ============================================================
# GATE 4: Buyer-Facing Evidence Ladder Upgrade
# ============================================================

def gate4_buyer_facing_upgrade(contracts: dict) -> dict:
    print("\n" + "=" * 70)
    print("GATE 4: Buyer-Facing Evidence Ladder Upgrade")
    print("=" * 70)

    upgrades = {}
    for cid, contract in contracts.items():
        upgrade = {
            "candidate_id": cid,
            "current_state": contract["current_state"],
            "target_state": contract["target_state"],
            "evidence_ladder_message": f"Current evidence: T1. A defined ${contract['estimated_cost']} experiment upgrades this to T2. Timeline: {contract['timeline']}. Here is the exact path.",
            "experiment_summary": contract["experiment_required"][:200],
            "cost": contract["estimated_cost"],
            "timeline": contract["timeline"],
            "success_threshold": contract["success_threshold"],
            "failure_threshold": contract["failure_threshold"],
            "buyer_action_if_interested": f"Commission the ${contract['estimated_cost']} validation experiment. If PASS, package upgrades to T2-CONDITIONAL with externally verified evidence.",
            "what_t2_means": contract["what_T2_means"],
            "what_t2_does_NOT_mean": contract["what_T2_does_NOT_mean"],
            "no_fake_promotion": contract["no_fake_promotion"]
        }
        upgrades[cid] = upgrade
        print(f"  {cid}: T1 → ${contract['estimated_cost']} experiment → T2-CONDITIONAL")

    _write(R349 / "evidence_ladder" / "BUYER_FACING_EVIDENCE_LADDER.json", upgrades)
    return upgrades

# ============================================================
# GATE 5: No Fake Promotions — Document What's Missing
# ============================================================

def gate5_no_fake_promotions(contracts: dict) -> dict:
    print("\n" + "=" * 70)
    print("GATE 5: No Fake Promotions — Document What's Missing for T2")
    print("=" * 70)

    missing = {}
    for cid, contract in contracts.items():
        missing[cid] = {
            "candidate_id": cid,
            "what_is_missing_for_T2": f"External evidence has NOT been ingested. The package remains T1 until: (1) the defined experiment is executed by an independent party, (2) raw data + custody chain + independent verification artifact are delivered to ingest_external_data_v2(AdmissibilityBundle), (3) the R341 pipeline verifies admissibility (16 checks), (4) the evidence class becomes PHYSICALLY_VALIDATED, (5) Article XXXVII transition to REAL_LOOP_VERIFIED.",
            "current_state_honest": "T1 — computationally supported only. No external verification. No physical validation. No independent reproduction.",
            "what_would_constitute_fake_promotion": "Claiming T2 without external data ingestion. Claiming 'validated' without independent verification. Claiming 'buyer-ready' without the experiment being run. Claiming superiority without the decisive experiment.",
            "article_XXVIII_compliance": "No silent semantic promotion. T1 remains T1 until evidence arrives.",
            "article_XXV_compliance": "Unknown must remain unknown. The absence of external data is a legitimate unknown state.",
            "estimated_T2_arrival": f"CEO-dependent. Could be {contract['timeline']} if a buyer/partner commissions the experiment tomorrow. Could be never if no buyer engages."
        }
        print(f"  {cid}: T1 — missing external evidence. No fake promotion.")

    _write(R349 / "evidence_ladder" / "NO_FAKE_PROMOTIONS.json", missing)
    return missing

# ============================================================
# GATE 6: Evidence-Conversion Portfolio Index
# ============================================================

def gate6_portfolio_index(matrix: dict, top5: dict, contracts: dict, upgrades: dict, missing: dict) -> dict:
    print("\n" + "=" * 70)
    print("GATE 6: Evidence-Conversion Portfolio Index")
    print("=" * 70)

    index_lines = [
        "# EVIDENCE CONVERSION PORTFOLIO (R349)",
        "",
        f"**Generated:** {_now_iso()}",
        f"**Objective:** Convert top 5 T1 packages toward T2 via defined validation experiments.",
        f"**NO fake promotions.** T2 requires external evidence ingested through R341 pipeline.",
        "",
        "## The Evidence Ladder",
        "",
        "```",
        "T0 → T1 → T2-CONDITIONAL → T2-CONFIRMED → T3 → T4 → T5",
        "```",
        "",
        "**T2 requires evidence. T1→T2 cannot happen through better writing.**",
        "It requires: external verification, independent reproduction, physical experiment,",
        "external dataset, or third-party validation — ingested via AdmissibilityBundle.",
        "",
        "## Top 5 T1→T2 Conversion Pathways",
        "",
        "| Rank | Package | Current | Target | Experiment | Cost | Timeline | Probability |",
        "|------|---------|---------|--------|------------|------|----------|-------------|"
    ]

    for i, entry in enumerate(matrix["ranked_packages"][:5]):
        cid = entry["candidate_id"]
        contract = contracts[cid]
        prob = entry["scores"]["probability_of_success"]
        index_lines.append(f"| {i+1} | {cid} | T1 | T2-CONDITIONAL | {contract['experiment_required'][:50]}... | {contract['estimated_cost']} | {contract['timeline']} | {prob}/5 |")

    index_lines.extend([
        "",
        "## What Each T2 Conversion Means",
        "",
        "**T2-CONDITIONAL means:** external verification of the claimed mechanism/model.",
        "**T2-CONDITIONAL does NOT mean:** clinical validation, manufacturing readiness, regulatory approval, or commercial superiority.",
        "",
        "## No Fake Promotions",
        "",
        "Every package honestly states:",
        "- Current state: T1 (computationally supported only)",
        "- What is missing: external evidence (not yet ingested)",
        "- What would constitute fake promotion: claiming T2 without external data",
        "- Estimated T2 arrival: CEO-dependent (buyer must commission experiment)",
        "",
        "## Current Portfolio Maturity",
        "",
        "| Level | Count | Packages |",
        "|-------|------:|----------|"
    ])

    t2_confirmed = [cid for cid, d in DOSSIERS.items() if d["three_axes"]["technical_readiness"] == "T2-CONFIRMED"]
    t2_conditional = [cid for cid, d in DOSSIERS.items() if d["three_axes"]["technical_readiness"] == "T2-CONDITIONAL"]
    t1 = [cid for cid, d in DOSSIERS.items() if d["three_axes"]["technical_readiness"] == "T1"]

    index_lines.append(f"| T2-CONFIRMED | {len(t2_confirmed)} | {', '.join(t2_confirmed)} |")
    index_lines.append(f"| T2-CONDITIONAL | {len(t2_conditional)} | {', '.join(t2_conditional)} |")
    index_lines.append(f"| T1 (climbing) | 5 | {', '.join(top5['selected'])} |")
    index_lines.append(f"| T1 (evaluation) | {len(t1)-5} | {', '.join([cid for cid in t1 if cid not in top5['selected']])} |")

    index_lines.extend([
        "",
        "## Target Maturity (after T2 conversion of top 5)",
        "",
        "| Level | Count |",
        "|-------|------:|",
        "| T2-CONFIRMED | 1 |",
        "| T2-CONDITIONAL | 6 | (1 existing + 5 converted)",
        "| T1 | 8 |",
        "",
        "## The Valuable Claim",
        "",
        "> An AI system that continuously creates, kills, validates, and packages technologies",
        "> into buyer-ready opportunities — with 5 actively climbing the evidence ladder",
        "> toward investable/licensable assets.",
        "",
        "## CEO Next Action",
        "",
        "1. Review the 5 validation contracts in `R349/validation_contracts/`",
        "2. Identify buyers/partners who can commission the experiments",
        "3. When a buyer returns data, deliver to `ingest_external_data_v2(AdmissibilityBundle)`",
        "4. Machine processes reality → T2-CONDITIONAL → package regenerates",
        ""
    ])

    _write_text(R349 / "evidence_ladder" / "EVIDENCE_CONVERSION_PORTFOLIO_INDEX.md", "\n".join(index_lines))
    print(f"  Index generated: 5 climbers on the evidence ladder")
    return {"index_generated": True}

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("R349 — EVIDENCE CONVERSION PROGRAM")
    print("Constitutional basis: Article I, IV, VII, XIV, XXVII, XXVIII, XXXIV")
    print("NO FAKE PROMOTIONS. T2 requires evidence.")
    print("=" * 70)

    matrix = gate1_priority_matrix()
    top5 = gate2_select_top5(matrix)
    contracts = gate3_validation_contracts(top5)
    upgrades = gate4_buyer_facing_upgrade(contracts)
    missing = gate5_no_fake_promotions(contracts)
    gate6_portfolio_index(matrix, top5, contracts, upgrades, missing)

    # Audit
    audit = {
        "round": 349,
        "date": _now_iso(),
        "ceo_directive": "Evidence conversion program. Rank T1 packages, select top 5, create T2 validation contracts, show evidence ladder path. NO fake promotions.",
        "gates_executed": 6,
        "gate_results": {
            "gate_1_priority_matrix": f"DONE — {len(PRIORITY_SCORES)} T1 packages scored on 5 criteria (max 25). Top: P-24 (23/25).",
            "gate_2_top5_selection": f"DONE — Selected: {top5['selected']}. CEO expected match: {top5['match']}.",
            "gate_3_validation_contracts": f"DONE — 5 T2_VALIDATION_CONTRACT.json files created. Each has experiment, independent party, thresholds, cost, timeline, evidence required.",
            "gate_4_buyer_facing_upgrade": "DONE — Each package shows 'Current T1 → $X experiment → T2 path' not just 'this is T1.'",
            "gate_5_no_fake_promotions": "DONE — Every package documents what's missing for T2. No silent semantic promotion. Article XXV/XXVIII compliant.",
            "gate_6_portfolio_index": "DONE — EVIDENCE_CONVERSION_PORTFOLIO_INDEX.md generated. Shows 5 climbers on evidence ladder."
        },
        "top5_conversion_pathways": {
            "P-24": {"cost": "$15K", "timeline": "8 weeks", "target": "T2-CONDITIONAL"},
            "P-21": {"cost": "$2-5K", "timeline": "6-12 months", "target": "T2-CONDITIONAL"},
            "P-13": {"cost": "$0-5K", "timeline": "3-6 months", "target": "T2-CONDITIONAL"},
            "P-02": {"cost": "$10-20K", "timeline": "6-12 months", "target": "T2-CONDITIONAL"},
            "P-15": {"cost": "$5-10K", "timeline": "6-12 months", "target": "T2-CONDITIONAL"}
        },
        "current_maturity": {
            "T2-CONFIRMED": 1,
            "T2-CONDITIONAL": 1,
            "T1_climbing": 5,
            "T1_evaluation": 8,
            "total": 15
        },
        "target_maturity_after_conversion": {
            "T2-CONFIRMED": 1,
            "T2-CONDITIONAL": 6,
            "T1": 8,
            "total": 15
        },
        "honest_state": "5 T1 packages have defined T2 conversion pathways with experiments, costs, timelines, and success/failure thresholds. NO package has been fake-promoted. T2 requires external evidence ingested through R341 pipeline.",
        "ceo_next_action": "Review 5 validation contracts. Identify buyers/partners to commission experiments. When data returns, machine processes reality → T2-CONDITIONAL."
    }
    _write(R349 / "audit" / "ROUND_349_AUDIT.json", audit)

    md = [
        "# R349 AUDIT — Evidence Conversion Program",
        "",
        f"**Round:** 349",
        f"**Date:** {audit['date']}",
        "",
        "## Top 5 T1→T2 Conversion Pathways",
        "",
        "| Package | Cost | Timeline | Target |",
        "|---------|------|----------|--------|"
    ]
    for cid, info in audit["top5_conversion_pathways"].items():
        md.append(f"| {cid} | {info['cost']} | {info['timeline']} | {info['target']} |")
    md.extend([
        "",
        "## Current vs Target Maturity",
        "",
        "| Level | Current | Target (after conversion) |",
        "|-------|--------:|--------------------------:|"
    ])
    for level in ["T2-CONFIRMED", "T2-CONDITIONAL", "T1"]:
        current = audit["current_maturity"].get(level, audit["current_maturity"].get(f"{level}_climbing", 0) + audit["current_maturity"].get(f"{level}_evaluation", 0))
        target = audit["target_maturity_after_conversion"].get(level, 0)
        md.append(f"| {level} | {current} | {target} |")
    md.extend([
        "",
        "## No Fake Promotions",
        "",
        audit["honest_state"],
        "",
        "## CEO Next Action",
        "",
        audit["ceo_next_action"],
        ""
    ])
    _write_text(R349 / "audit" / "ROUND_349_AUDIT.md", "\n".join(md))

    print("\n" + "=" * 70)
    print("R349 COMPLETE")
    print("=" * 70)
    print(f"  Top 5 selected: {top5['selected']}")
    print(f"  Validation contracts: 5 created")
    print(f"  No fake promotions: T2 requires external evidence")
    print(f"  Target: 6 T2-CONDITIONAL (after conversion) + 1 T2-CONFIRMED")

if __name__ == "__main__":
    main()
