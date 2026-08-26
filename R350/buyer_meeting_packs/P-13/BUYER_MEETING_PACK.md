# BUYER MEETING PACK — P-13

**Package:** P-13 — ML-based predictor using ICP + flow trends to forecast failure 24h before sympto
**Date:** 2026-08-26T06:03:14.654804+00:00
**Transfer Posture:** DECISIVE_EXPERIMENT_REQUIRED

---

## PAGE 1: Executive Opportunity

P-13 — ML-based predictor using ICP + flow trends to forecast failure 24h before sympto. A computationally specified P-13 concept plus a preregistered decisive experiment — not a validated technology. Current evidence: T1. Transfer posture: DECISIVE_EXPERIMENT_REQUIRED. Recommended transaction: DATA_PARTNERSHIP (buyer provides dataset). Validation cost: $0-5K (if dataset available).

**Strategic Buyer:** Medical AI company (e.g., Caption Health, Cleerly) or large health system data science team

**Why This Company Should Care:**
Data partnership opportunity. The buyer brings the dataset; we bring the mechanism and hypothesis. If AUC >= 0.80 is achievable, this is a productizable prediction service. The neuromorphic angle is the differentiator vs generic medical AI.

**Recommended Transaction:** DATA_PARTNERSHIP (buyer provides dataset)

**Validation Investment:** $0-5K (if dataset available) (3-6 months to T2 with data)

---

## PAGE 2: Evidence and Uncertainty

**Current Evidence Level:** T1
**Physical Validation:** NONE

### What Is Demonstrated
- MODELLED: 2 claims
- COMPUTATIONALLY_SUPPORTED: 0 claims
- OBSERVED: 0 claims

### What Is NOT Proven
- Conditional on P-15/P-16 energy (if those fail, P-13 has no power source)

### Strongest Alternative
Clinical monitoring (intermittent, reactive)

### Remaining Decisive Uncertainty
Prediction accuracy on real patient data. Lead time in clinical setting.

---

## PAGE 3: Development Roadmap

### Validation Experiment
External dataset validation: obtain shunt patient dataset (clinical partner or MIMIC-IV credentialed access), train/test neuromorphic predictor, measure AUC on held-out test set. Compare to existing baselines.

**Cost:** $0-5K (if dataset available)
**Timeline:** 3-6 months to T2 with data
**Pass:** AUC >= 0.80 on held-out test set (95% CI above 0.75)
**Fail:** AUC < 0.70 on held-out test set

### Development Path
1. **Phase 1 — Bench Validation:** $0-5K (dataset access + compute) — Medium — ML/AI engineering
2. **Phase 2 — Prototype:** If Phase 1 passes
3. **Phase 3 — Relevant Environment:** Clinical/cadaver/animal testing
4. **Phase 4 — Regulatory:** FDA AI/ML pathway (SaMD)
5. **Phase 5 — Commercial Deployment**

### Manufacturing Complexity
Low (software) / High (neuromorphic hardware)

---

## PAGE 4: Deal Options

**Recommended Transaction:** DATA_PARTNERSHIP (buyer provides dataset)

### Available Options
- data_partnership
- sponsored_validation
- co_development
- exclusive_license

### Strategic Value
On-device shunt failure prediction — neuromorphic differentiator

### Technology Gap Filled
No implantable prediction exists; cloud-based AI has latency/privacy issues

### Incumbent Weakness
Generic medical AI is crowded; implantable neuromorphic is not

### Buyer Synergies
Data partnership — buyer brings dataset, we bring mechanism

### Ownership Status
UNVERIFIED — buyer counsel must perform IP diligence

### Regulatory Status
Preliminary hypothesis — buyer regulatory counsel must confirm. See full dossier for details.

---

## PAGE 5: Technical Appendix Reference

**Full Dossier:** `R348/premium_portfolio/TIER_*/NN_P-13/07_PREMIUM_DOSSIER.json`
**Evidence Ledger:** `R348/premium_portfolio/TIER_*/NN_P-13/` → section 07_evidence_validation_ledger
**Experiment Protocol:** `R348/premium_portfolio/TIER_*/NN_P-13/` → section 11_development_experiment_plan
**Risk Register:** `R348/premium_portfolio/TIER_*/NN_P-13/` → section 08_technical_readiness_risk
**Competitive Analysis:** `R348/premium_portfolio/TIER_*/NN_P-13/` → section 06_competitive_alternatives

**T2 Validation Contract:** `R349/validation_contracts/P-13_T2_VALIDATION_CONTRACT.json` (if T1 climber)

**BUYER_ACTION_ID:** P13-EXP-001

---

*This meeting pack is designed for a 30-minute buyer meeting. Pages 1-2 for the executive. Pages 3-4 for the deal team. Page 5 for the technical diligence team.*
