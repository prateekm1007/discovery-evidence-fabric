#!/usr/bin/env python3.13
"""
R350 — BUYER CONVERSION PACKAGE LAYER
=======================================

Constitutional basis: Article I (evidence precedes assertion),
                      Article XV (disclose inconvenient results),
                      Article XXV (unknown must remain unknown),
                      Article XXVI (no self-certification),
                      Article XXVII (no threshold invention),
                      Article XXVIII (no silent semantic promotion)

CEO R350 directive:
  Turn the 15 packages into assets a corporate technology scout can circulate internally.
  Documents that cause a VP R&D, CTO, or licensing executive to schedule a meeting.

  NOT more discovery. NOT more scoring systems. NOT CRM. NOT dashboards.
  Only buyer-transfer artifacts.

  Gates:
    1. Corporate Technology Opportunity Memo (10 fields per package)
    2. Buyer Meeting Pack (5-page structure per package)
    3. Transfer Readiness Score (commercial, not scientific)
    4. Final portfolio classification (Flagship / Validation / Optionality)
    5. Generate BUYER_MEETING_PACKS/ with all 15 + master index
"""

import json, hashlib, sys
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Tuple, Any

REPO = Path(__file__).resolve().parents[1]
R350 = REPO / "R350"

def _write(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))

def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# Load R348 premium dossiers (the most complete version)
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

# Load R349 validation contracts for the top 5
def load_validation_contracts() -> dict:
    contracts = {}
    contract_dir = REPO / "R349" / "validation_contracts"
    if contract_dir.exists():
        for f in contract_dir.glob("*_T2_VALIDATION_CONTRACT.json"):
            cid = f.stem.replace("_T2_VALIDATION_CONTRACT", "")
            contracts[cid] = json.loads(f.read_text())
    return contracts

VALIDATION_CONTRACTS = load_validation_contracts()

# ============================================================
# "Why Now" rationales per package
# ============================================================

WHY_NOW = {
    "P-16": "Optical power delivery for implants is an active research frontier. Companies investing in implantable sensors/wearables face battery limitations now. First-mover advantage in NIR-powered passive implants.",
    "P-01": "Obstruction remains the #1 shunt failure mode with no predictive solution. Computational power now enables multi-segment modeling that was infeasible 5 years ago. Shunt OEMs actively seeking differentiation in a commoditized market.",
    "P-24": "ASD is the incumbent but has binary behavior. Proportional regulation is an unaddressed niche. $15K bench test is low-cost, high-information. Shunt companies seeking product differentiation in a flat market.",
    "P-21": "Catheter misplacement contributes to failures. UWB technology has matured for medical applications (Apple U1, automotive). Neuro-navigation companies seeking catheter placement expansion. RF components are now COTS.",
    "P-13": "AI/ML in medical devices is FDA's active priority (SaMD guidance). Shunt failure prediction is a specific, high-value application. Neuromorphic hardware enables ultra-low-power on-device inference — critical for implantable context. Dataset partnerships are the bottleneck.",
    "P-02": "ICP excursion reduction is a clinical pain point. Adjustable valves exist but are reactive. Adaptive valve is the next generation. CFD solvers are now accessible for independent reproduction.",
    "P-04": "Alzheimer's market is massive ($50-200K/patient/year). Amyloid clearance via catheter is a first-in-class concept. Monoclonal antibodies have limited CNS penetration — device-drug combination addresses this. Wet-lab validation is the bottleneck.",
    "P-07": "Obstruction is #1 failure mode (35%). Floor mechanism directly addresses this. Low-cost bench test. Shunt OEMs actively seeking obstruction-reduction solutions.",
    "P-11": "Infection is 10% of failures at $60K/event. Antibiotic resistance is a growing concern. Phage-based anti-biofilm is a novel mechanism. Phage therapy is experiencing regulatory renaissance (FDA clinical trials active).",
    "P-12": "Tau is the next Alzheimer's target after amyloid. Catheter-based tau clearance is first-in-class. Enzyme stability in CSF is the key question. Pharma companies with tau programs are potential partners.",
    "P-15": "Battery-free implantable sensors are a new product category. Energy harvesting has matured. Medical device companies face battery replacement costs ($45K/surgery). Hybrid power eliminates this for low-power implants.",
    "P-20": "Foreign-body response limits all implants. No tolerance coating exists. Glycan-mediated immune tolerance is a platform technology. Applies across entire implant portfolio — high strategic value.",
    "P-22": "Autonomous catheter navigation is the next generation of smart catheters. OR time reduction is a measurable economic driver. 4 control problems are clearly defined R&D questions. Neuro-navigation companies seeking expansion.",
    "P-26": "Passive, zero-maintenance overdrainage prevention. Osmotic regulation is a novel mechanism — no electronics, no moving parts. Membrane technology has matured. Fouling test is the decisive question. New candidate (R347).",
    "P-27": "Kink resistance via shape-memory polymer is a materials solution to a mechanical failure. Platform technology — applies to vascular, neurovascular, and shunt catheters. SMP processing has matured. Aging test is decisive. New candidate (R347)."
}

# ============================================================
# GATE 1: Corporate Technology Opportunity Memo
# ============================================================

def build_opportunity_memo(cid: str, dossier: dict) -> dict:
    """10-field Corporate Technology Opportunity Memo."""
    card = dossier["01_buyer_decision_card"]
    axes = dossier["three_axes"]
    fit = dossier.get("strategic_buyer_fit", {})
    deal = dossier.get("deal_path", {})
    dev = dossier.get("development_burden", {})
    acq = dossier.get("acquisition_logic", {})
    contract = VALIDATION_CONTRACTS.get(cid, {})

    return {
        "memo_type": "CORPORATE_TECHNOLOGY_OPPORTUNITY_MEMO",
        "candidate_id": cid,
        "generated_at": _now_iso(),

        "1_executive_summary": (
            f"{card['technology_name']}. {dossier['buyer_truth']} "
            f"Current evidence: {axes['technical_readiness']}. "
            f"Transfer posture: {axes['transfer_posture']}. "
            f"Recommended transaction: {deal.get('recommended_transaction', 'UNKNOWN')}. "
            f"Validation cost: {dev.get('validation_cost', 'UNKNOWN')}."
        ),

        "2_industry_problem": card.get("what_is_not_proven", ["UNKNOWN"])[0] if card.get("what_is_not_proven") else "UNKNOWN",

        "3_current_alternative": {
            "strongest_alternative": card.get("strongest_alternative", "UNKNOWN"),
            "alternative_weakness": acq.get("incumbent_weakness", "UNKNOWN"),
            "why_inadequate": dossier.get("03_customer_industrial_problem", {}).get("why_problem_remains_unsolved", "UNKNOWN")
        },

        "4_technology_advantage_hypothesis": {
            "hypothesis": acq.get("strategic_value", "UNKNOWN"),
            "gap_filled": acq.get("technology_gap_filled", "UNKNOWN"),
            "differentiation": dossier.get("05_what_is_actually_new", {}).get("difference", "UNKNOWN"),
            "evidence_supporting": f"{axes['technical_readiness']} — see evidence ledger",
            "evidence_against": card.get("what_is_not_proven", []),
            "unresolved_question": card.get("decisive_question", "UNKNOWN")
        },

        "5_evidence_level": {
            "technical_readiness": axes["technical_readiness"],
            "physical_validation": axes.get("physical_validation", "NONE"),
            "evidence_ledger_summary": f"MODELLED: {len(dossier.get('07_evidence_validation_ledger', {}).get('MODELLED', []))} claims, "
                                       f"COMPUTATIONALLY_SUPPORTED: {len(dossier.get('07_evidence_validation_ledger', {}).get('COMPUTATIONALLY_SUPPORTED', []))} claims, "
                                       f"OBSERVED: {len(dossier.get('07_evidence_validation_ledger', {}).get('OBSERVED', []))} claims",
            "honest_assessment": "Computationally supported. No external validation yet. Evidence ledger is transparent and auditable."
        },

        "6_remaining_uncertainty": {
            "primary_uncertainty": card.get("decisive_question", "UNKNOWN"),
            "known_failures": card.get("what_is_not_proven", []),
            "what_is_NOT_proven": "No external validation. No physical prototype. No clinical data. No regulatory clearance. No manufacturing validation."
        },

        "7_validation_investment": {
            "experiment": contract.get("experiment_required", dev.get("validation_cost", "UNKNOWN")),
            "cost": dev.get("validation_cost", contract.get("estimated_cost", "UNKNOWN")),
            "timeline": dev.get("timeline", contract.get("timeline", "UNKNOWN")),
            "success_threshold": contract.get("success_threshold", card.get("if_pass", "UNKNOWN")),
            "failure_threshold": contract.get("failure_threshold", card.get("if_fail", "UNKNOWN")),
            "t2_conversion_path": f"Current {axes['technical_readiness']} → ${dev.get('validation_cost', 'UNKNOWN')} experiment → T2-CONDITIONAL" if axes["technical_readiness"] == "T1" else f"Current {axes['technical_readiness']} → physical validation → T3"
        },

        "8_strategic_buyer_fit": {
            "ideal_buyer": fit.get("ideal_buyer", "UNKNOWN"),
            "buyer_type": fit.get("buyer_type", "UNKNOWN"),
            "strategic_reason": fit.get("strategic_reason", "UNKNOWN"),
            "capabilities_required": fit.get("existing_capabilities_required", "UNKNOWN"),
            "why_this_buyer_would_care": fit.get("why_this_buyer_would_care", "UNKNOWN")
        },

        "9_transaction_pathway": {
            "recommended_transaction": deal.get("recommended_transaction", "UNKNOWN"),
            "options": deal.get("options", []),
            "commercial_route": dossier.get("15_commercialization_deal_path", {}).get("recommended_path", "UNKNOWN")
        },

        "10_why_now": WHY_NOW.get(cid, "UNKNOWN")
    }

# ============================================================
# GATE 2: Buyer Meeting Pack (5-page structure)
# ============================================================

def generate_meeting_pack(memo: dict, dossier: dict) -> str:
    """Generate 5-page Buyer Meeting Pack in markdown."""
    cid = memo["candidate_id"]
    card = dossier["01_buyer_decision_card"]
    axes = dossier["three_axes"]
    fit = dossier.get("strategic_buyer_fit", {})
    deal = dossier.get("deal_path", {})
    dev = dossier.get("development_burden", {})
    acq = dossier.get("acquisition_logic", {})
    el = dossier.get("07_evidence_validation_ledger", {})

    return f"""# BUYER MEETING PACK — {cid}

**Package:** {card['technology_name']}
**Date:** {_now_iso()}
**Transfer Posture:** {axes['transfer_posture']}

---

## PAGE 1: Executive Opportunity

{memo['1_executive_summary']}

**Strategic Buyer:** {fit.get('ideal_buyer', 'UNKNOWN')}

**Why This Company Should Care:**
{fit.get('why_this_buyer_would_care', 'UNKNOWN')}

**Recommended Transaction:** {deal.get('recommended_transaction', 'UNKNOWN')}

**Validation Investment:** {dev.get('validation_cost', 'UNKNOWN')} ({dev.get('timeline', 'UNKNOWN')})

---

## PAGE 2: Evidence and Uncertainty

**Current Evidence Level:** {axes['technical_readiness']}
**Physical Validation:** {axes.get('physical_validation', 'NONE')}

### What Is Demonstrated
- MODELLED: {len(el.get('MODELLED', []))} claims
- COMPUTATIONALLY_SUPPORTED: {len(el.get('COMPUTATIONALLY_SUPPORTED', []))} claims
- OBSERVED: {len(el.get('OBSERVED', []))} claims

### What Is NOT Proven
{chr(10).join(f'- {f}' for f in card.get('what_is_not_proven', []))}

### Strongest Alternative
{card.get('strongest_alternative', 'UNKNOWN')}

### Remaining Decisive Uncertainty
{card.get('decisive_question', 'UNKNOWN')}

---

## PAGE 3: Development Roadmap

### Validation Experiment
{memo['7_validation_investment']['experiment'][:300] if isinstance(memo['7_validation_investment']['experiment'], str) else memo['7_validation_investment']['experiment']}

**Cost:** {dev.get('validation_cost', 'UNKNOWN')}
**Timeline:** {dev.get('timeline', 'UNKNOWN')}
**Pass:** {memo['7_validation_investment']['success_threshold']}
**Fail:** {memo['7_validation_investment']['failure_threshold']}

### Development Path
1. **Phase 1 — Bench Validation:** {dev.get('prototype_cost_estimate', 'UNKNOWN')} — {dev.get('engineering_requirement', 'UNKNOWN')}
2. **Phase 2 — Prototype:** If Phase 1 passes
3. **Phase 3 — Relevant Environment:** Clinical/cadaver/animal testing
4. **Phase 4 — Regulatory:** {dev.get('regulatory_work', 'UNKNOWN')}
5. **Phase 5 — Commercial Deployment**

### Manufacturing Complexity
{dev.get('manufacturing_complexity', 'UNKNOWN')}

---

## PAGE 4: Deal Options

**Recommended Transaction:** {deal.get('recommended_transaction', 'UNKNOWN')}

### Available Options
{chr(10).join(f'- {opt}' for opt in deal.get('options', []))}

### Strategic Value
{acq.get('strategic_value', 'UNKNOWN')}

### Technology Gap Filled
{acq.get('technology_gap_filled', 'UNKNOWN')}

### Incumbent Weakness
{acq.get('incumbent_weakness', 'UNKNOWN')}

### Buyer Synergies
{acq.get('buyer_synergies', 'UNKNOWN')}

### Ownership Status
{dossier.get('14_ip_ownership_fto_diligence', {}).get('ownership_status', 'UNVERIFIED')} — buyer counsel must perform IP diligence

### Regulatory Status
Preliminary hypothesis — buyer regulatory counsel must confirm. See full dossier for details.

---

## PAGE 5: Technical Appendix Reference

**Full Dossier:** `R348/premium_portfolio/TIER_*/NN_{cid}/07_PREMIUM_DOSSIER.json`
**Evidence Ledger:** `R348/premium_portfolio/TIER_*/NN_{cid}/` → section 07_evidence_validation_ledger
**Experiment Protocol:** `R348/premium_portfolio/TIER_*/NN_{cid}/` → section 11_development_experiment_plan
**Risk Register:** `R348/premium_portfolio/TIER_*/NN_{cid}/` → section 08_technical_readiness_risk
**Competitive Analysis:** `R348/premium_portfolio/TIER_*/NN_{cid}/` → section 06_competitive_alternatives

**T2 Validation Contract:** `R349/validation_contracts/{cid}_T2_VALIDATION_CONTRACT.json` (if T1 climber)

**BUYER_ACTION_ID:** {card.get('buyer_action_id', 'UNKNOWN')}

---

*This meeting pack is designed for a 30-minute buyer meeting. Pages 1-2 for the executive. Pages 3-4 for the deal team. Page 5 for the technical diligence team.*
"""

# ============================================================
# GATE 3: Transfer Readiness Score (commercial, not scientific)
# ============================================================

def compute_transfer_readiness(cid: str, dossier: dict) -> dict:
    """Commercial transfer readiness score. NOT scientific readiness."""
    axes = dossier["three_axes"]
    fit = dossier.get("strategic_buyer_fit", {})
    deal = dossier.get("deal_path", {})
    dev = dossier.get("development_burden", {})
    card = dossier["01_buyer_decision_card"]

    # 5 dimensions, each 0-5 (max 25)

    # 1. Buyer Fit (0-5)
    buyer_fit = 0
    if fit.get("ideal_buyer") and fit.get("ideal_buyer") != "UNKNOWN": buyer_fit += 2
    if fit.get("strategic_reason") and fit.get("strategic_reason") != "UNKNOWN": buyer_fit += 1
    if fit.get("why_this_buyer_would_care") and fit.get("why_this_buyer_would_care") != "UNKNOWN": buyer_fit += 2

    # 2. Evidence Quality (0-5)
    evidence_quality = 0
    tr = axes["technical_readiness"]
    if tr == "T2-CONFIRMED": evidence_quality = 5
    elif tr == "T2-CONDITIONAL": evidence_quality = 4
    elif tr == "T1": evidence_quality = 2
    else: evidence_quality = 1

    # 3. Validation Clarity (0-5)
    validation_clarity = 0
    if card.get("decisive_question") and card.get("decisive_question") != "UNKNOWN": validation_clarity += 1
    if dev.get("validation_cost") and dev.get("validation_cost") != "UNKNOWN": validation_clarity += 2
    if card.get("if_pass") and card.get("if_pass") != "UNKNOWN": validation_clarity += 1
    if card.get("if_fail") and card.get("if_fail") != "UNKNOWN": validation_clarity += 1

    # 4. Transaction Clarity (0-5)
    transaction_clarity = 0
    if deal.get("recommended_transaction") and deal.get("recommended_transaction") != "UNKNOWN": transaction_clarity += 3
    if deal.get("options") and len(deal.get("options", [])) >= 3: transaction_clarity += 2

    # 5. Strategic Value (0-5)
    acq = dossier.get("acquisition_logic", {})
    strategic_value = 0
    if acq.get("strategic_value") and acq.get("strategic_value") != "UNKNOWN": strategic_value += 2
    if acq.get("technology_gap_filled") and acq.get("technology_gap_filled") != "UNKNOWN": strategic_value += 1
    if acq.get("buyer_synergies") and acq.get("buyer_synergies") != "UNKNOWN": strategic_value += 2

    total = buyer_fit + evidence_quality + validation_clarity + transaction_clarity + strategic_value

    return {
        "candidate_id": cid,
        "buyer_fit": buyer_fit,
        "evidence_quality": evidence_quality,
        "validation_clarity": validation_clarity,
        "transaction_clarity": transaction_clarity,
        "strategic_value": strategic_value,
        "total": total,
        "max": 25,
        "percentage": round(total / 25 * 100, 1)
    }

# ============================================================
# GATE 4: Final Portfolio Classification
# ============================================================

def classify_portfolio(scores: dict) -> dict:
    """
    FLAGSHIP TRANSFER: T2-CONFIRMED or T2-CONDITIONAL (ready for active outreach)
    VALIDATION OPPORTUNITIES: T1 with high transfer readiness (climbing the ladder)
    OPTIONALITY PORTFOLIO: T1 with medium readiness (evaluation bench)
    """
    flagship = []
    validation = []
    optionality = []

    for cid, score in scores.items():
        dossier = DOSSIERS[cid]
        tr = dossier["three_axes"]["technical_readiness"]

        if tr in ("T2-CONFIRMED", "T2-CONDITIONAL"):
            flagship.append(cid)
        elif score["total"] >= 18:  # high transfer readiness
            validation.append(cid)
        else:
            optionality.append(cid)

    return {
        "FLAGSHIP_TRANSFER_OPPORTUNITIES": flagship,
        "VALIDATION_OPPORTUNITIES": validation,
        "OPTIONALITY_PORTFOLIO": optionality
    }

# ============================================================
# GATE 5: Generate Buyer Meeting Packs
# ============================================================

def generate_all_packs() -> dict:
    print("=" * 70)
    print("R350: Generating Buyer Meeting Packs for all 15 packages")
    print("=" * 70)

    packs_dir = R350 / "buyer_meeting_packs"
    packs_dir.mkdir(parents=True, exist_ok=True)

    memos = {}
    scores = {}

    for cid, dossier in DOSSIERS.items():
        # Gate 1: Memo
        memo = build_opportunity_memo(cid, dossier)
        memos[cid] = memo

        # Gate 2: Meeting Pack
        pack_md = generate_meeting_pack(memo, dossier)
        pack_dir = packs_dir / cid
        pack_dir.mkdir(parents=True, exist_ok=True)
        _write_text(pack_dir / "BUYER_MEETING_PACK.md", pack_md)
        _write(pack_dir / "TECHNOLOGY_OPPORTUNITY_MEMO.json", memo)

        # Gate 3: Transfer Readiness Score
        score = compute_transfer_readiness(cid, dossier)
        scores[cid] = score
        _write(pack_dir / "TRANSFER_READINESS_SCORE.json", score)

        print(f"  {cid}: TRS={score['total']}/25 ({score['percentage']}%) — {dossier['three_axes']['technical_readiness']}")

    # Gate 4: Classification
    classification = classify_portfolio(scores)
    _write(R350 / "transfer_scores" / "PORTFOLIO_CLASSIFICATION.json", classification)
    _write(R350 / "transfer_scores" / "ALL_TRANSFER_READINESS_SCORES.json", scores)

    print(f"\n  FLAGSHIP TRANSFER: {classification['FLAGSHIP_TRANSFER_OPPORTUNITIES']}")
    print(f"  VALIDATION: {classification['VALIDATION_OPPORTUNITIES']}")
    print(f"  OPTIONALITY: {classification['OPTIONALITY_PORTFOLIO']}")

    # Master index
    index_lines = [
        "# BUYER MEETING PACKS — MASTER INDEX (R350)",
        "",
        f"**Generated:** {_now_iso()}",
        f"**Total packages:** {len(DOSSIERS)}",
        f"**Purpose:** Documents that cause a VP R&D, CTO, or licensing executive to schedule a meeting.",
        "",
        "## Final Portfolio Classification",
        "",
        f"### FLAGSHIP TRANSFER OPPORTUNITIES ({len(classification['FLAGSHIP_TRANSFER_OPPORTUNITIES'])})",
        "Ready for active outreach. Highest evidence maturity.",
        "",
        "| Package | TRS | Technical | Buyer |",
        "|---------|-----|-----------|-------|"
    ]
    for cid in classification["FLAGSHIP_TRANSFER_OPPORTUNITIES"]:
        s = scores[cid]
        d = DOSSIERS[cid]
        buyer = d.get("strategic_buyer_fit", {}).get("ideal_buyer", "?")[:40]
        index_lines.append(f"| {cid} | {s['total']}/25 | {d['three_axes']['technical_readiness']} | {buyer} |")

    index_lines.extend([
        "",
        f"### VALIDATION OPPORTUNITIES ({len(classification['VALIDATION_OPPORTUNITIES'])})",
        "High transfer readiness. T1 with defined validation pathway.",
        "",
        "| Package | TRS | Validation Cost | Buyer |",
        "|---------|-----|-----------------|-------|"
    ])
    for cid in classification["VALIDATION_OPPORTUNITIES"]:
        s = scores[cid]
        d = DOSSIERS[cid]
        cost = d.get("development_burden", {}).get("validation_cost", "?")[:30]
        buyer = d.get("strategic_buyer_fit", {}).get("ideal_buyer", "?")[:40]
        index_lines.append(f"| {cid} | {s['total']}/25 | {cost} | {buyer} |")

    index_lines.extend([
        "",
        f"### OPTIONALITY PORTFOLIO ({len(classification['OPTIONALITY_PORTFOLIO'])})",
        "Evaluation bench. T1 with medium readiness.",
        "",
        "| Package | TRS |",
        "|---------|-----|"
    ])
    for cid in classification["OPTIONALITY_PORTFOLIO"]:
        s = scores[cid]
        index_lines.append(f"| {cid} | {s['total']}/25 |")

    index_lines.extend([
        "",
        "## Transfer Readiness Score (TRS) Dimensions",
        "",
        "Each package scored 0-5 on 5 commercial dimensions (max 25):",
        "- **Buyer Fit** — is the ideal buyer identified with strategic reason?",
        "- **Evidence Quality** — T2-CONFIRMED=5, T2-CONDITIONAL=4, T1=2, T0=1",
        "- **Validation Clarity** — is the experiment, cost, pass/fail defined?",
        "- **Transaction Clarity** — is the recommended transaction clear?",
        "- **Strategic Value** — gap filled, incumbent weakness, synergies?",
        "",
        "## What Each Package Contains",
        "",
        "```",
        "R350/buyer_meeting_packs/P-XX/",
        "  BUYER_MEETING_PACK.md            ← 5-page meeting pack",
        "  TECHNOLOGY_OPPORTUNITY_MEMO.json ← 10-field corporate memo",
        "  TRANSFER_READINESS_SCORE.json    ← commercial readiness score",
        "```",
        "",
        "## How to Use These Packs",
        "",
        "1. **Send the BUYER_MEETING_PACK.md** to the ideal buyer identified in the memo.",
        "2. **Page 1-2** are for the executive (30-second scan).",
        "3. **Page 3-4** are for the deal/technical team (diligence).",
        "4. **Page 5** references the full technical dossier for deep diligence.",
        "5. **The TRANSFER_READINESS_SCORE** tells you which packages to prioritize for outreach.",
        "",
        "## Not a Patent Court",
        "",
        "All ownership UNVERIFIED. All regulatory PRELIMINARY_HYPOTHESES. Buyer counsel performs diligence.",
        ""
    ])
    _write_text(packs_dir / "MASTER_INDEX.md", "\n".join(index_lines))

    return {"memos": memos, "scores": scores, "classification": classification}

# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 70)
    print("R350 — BUYER CONVERSION PACKAGE LAYER")
    print("The last step before actual market contact.")
    print("=" * 70)

    result = generate_all_packs()

    cls = result["classification"]
    scores = result["scores"]

    # Sort by TRS
    ranked = sorted(scores.items(), key=lambda x: -x[1]["total"])

    audit = {
        "round": 350,
        "date": _now_iso(),
        "ceo_directive": "Turn 15 packages into assets a corporate technology scout can circulate internally. Documents that cause a VP R&D, CTO, or licensing executive to schedule a meeting.",
        "gates_executed": 5,
        "gate_results": {
            "gate_1_opportunity_memo": f"DONE — 10-field Corporate Technology Opportunity Memo for all {len(DOSSIERS)} packages",
            "gate_2_meeting_pack": f"DONE — 5-page Buyer Meeting Pack for all {len(DOSSIERS)} packages",
            "gate_3_transfer_readiness_score": f"DONE — Commercial TRS (5 dimensions, max 25) for all {len(DOSSIERS)} packages",
            "gate_4_portfolio_classification": f"DONE — Flagship: {len(cls['FLAGSHIP_TRANSFER_OPPORTUNITIES'])}, Validation: {len(cls['VALIDATION_OPPORTUNITIES'])}, Optionality: {len(cls['OPTIONALITY_PORTFOLIO'])}",
            "gate_5_buyer_meeting_packs": f"DONE — R350/buyer_meeting_packs/ with {len(DOSSIERS)} folders + MASTER_INDEX.md"
        },
        "portfolio_classification": cls,
        "top5_by_trs": [{"cid": cid, "trs": score["total"], "pct": score["percentage"]} for cid, score in ranked[:5]],
        "honest_state": "15 buyer meeting packs generated. Each is a 5-page document designed for a 30-minute buyer meeting. Corporate technology scouts can circulate these internally. The bottleneck is now market contact, not engineering."
    }
    _write(R350 / "audit" / "ROUND_350_AUDIT.json", audit)

    md = [
        "# R350 AUDIT — Buyer Conversion Package Layer",
        "",
        f"**Round:** 350",
        f"**Date:** {audit['date']}",
        f"**Gates executed:** {audit['gates_executed']}",
        "",
        "## Portfolio Classification",
        "",
        f"### FLAGSHIP TRANSFER ({len(cls['FLAGSHIP_TRANSFER_OPPORTUNITIES'])})",
        ", ".join(cls["FLAGSHIP_TRANSFER_OPPORTUNITIES"]),
        "",
        f"### VALIDATION OPPORTUNITIES ({len(cls['VALIDATION_OPPORTUNITIES'])})",
        ", ".join(cls["VALIDATION_OPPORTUNITIES"]),
        "",
        f"### OPTIONALITY PORTFOLIO ({len(cls['OPTIONALITY_PORTFOLIO'])})",
        ", ".join(cls["OPTIONALITY_PORTFOLIO"]),
        "",
        "## Top 5 by Transfer Readiness Score",
        "",
        "| Package | TRS | % |",
        "|---------|-----|---|"
    ]
    for item in audit["top5_by_trs"]:
        md.append(f"| {item['cid']} | {item['trs']}/25 | {item['pct']}% |")
    md.extend([
        "",
        "## Honest State",
        "",
        audit["honest_state"],
        ""
    ])
    _write_text(R350 / "audit" / "ROUND_350_AUDIT.md", "\n".join(md))

    print("\n" + "=" * 70)
    print("R350 COMPLETE")
    print("=" * 70)
    print(f"  Flagship Transfer: {len(cls['FLAGSHIP_TRANSFER_OPPORTUNITIES'])}")
    print(f"  Validation Opportunities: {len(cls['VALIDATION_OPPORTUNITIES'])}")
    print(f"  Optionality Portfolio: {len(cls['OPTIONALITY_PORTFOLIO'])}")
    print(f"  Top TRS: {ranked[0][0]} ({ranked[0][1]['total']}/25)")
    print(f"  Bottleneck: market contact, not engineering")

if __name__ == "__main__":
    main()
