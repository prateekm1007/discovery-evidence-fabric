# BUYER MEETING PACK — P-21

**Package:** P-21 — UWB microsensors at catheter tip + wearable external reader for 3D position trac
**Date:** 2026-08-26T06:03:14.654485+00:00
**Transfer Posture:** DECISIVE_EXPERIMENT_REQUIRED

---

## PAGE 1: Executive Opportunity

P-21 — UWB microsensors at catheter tip + wearable external reader for 3D position trac. A computationally specified P-21 concept plus a preregistered decisive experiment — not a validated technology. Current evidence: T1. Transfer posture: DECISIVE_EXPERIMENT_REQUIRED. Recommended transaction: RESEARCH_PARTNERSHIP for RF/tissue validation. Validation cost: $2-5K.

**Strategic Buyer:** Medtronic (navigation division), Brainlab, or a neuro-navigation company

**Why This Company Should Care:**
Extends existing navigation platform into shunt placement. Adjacent market expansion. The 10mm vs 5mm accuracy question is a $2-5K bench test away from resolution.

**Recommended Transaction:** RESEARCH_PARTNERSHIP for RF/tissue validation

**Validation Investment:** $2-5K (6-12 months to T2)

---

## PAGE 2: Evidence and Uncertainty

**Current Evidence Level:** T1
**Physical Validation:** NONE

### What Is Demonstrated
- MODELLED: 2 claims
- COMPUTATIONALLY_SUPPORTED: 0 claims
- OBSERVED: 0 claims

### What Is NOT Proven
- Localization accuracy is MARGINAL (10mm vs 5mm requirement)

### Strongest Alternative
CT/MRI (radiation, expensive, not real-time). Published UWB implant work is plausible but tissue propagation challenging (PubMed 25571604).

### Remaining Decisive Uncertainty
Can the system localize catheter to <5mm through realistic head tissue while satisfying RF-exposure constraints?

---

## PAGE 3: Development Roadmap

### Validation Experiment
UWB localization bench test: skull phantom (realistic heterogeneous tissue), UWB transmitter in catheter, receiver array external. Measure localization accuracy at 4 depths. Compare to 5mm target. SAR compliance measurement.

**Cost:** $2-5K
**Timeline:** 6-12 months to T2
**Pass:** Localization accuracy <5mm at all 4 depths (95% CI below 5mm). SAR below FCC limit.
**Fail:** Localization accuracy >10mm at any depth. SAR exceeds FCC limit.

### Development Path
1. **Phase 1 — Bench Validation:** $5-10K (UWB modules + skull phantom) — Medium — RF + signal processing
2. **Phase 2 — Prototype:** If Phase 1 passes
3. **Phase 3 — Relevant Environment:** Clinical/cadaver/animal testing
4. **Phase 4 — Regulatory:** 510(k) software-as-medical-device + SAR compliance
5. **Phase 5 — Commercial Deployment**

### Manufacturing Complexity
Medium — UWB integration into catheter system

---

## PAGE 4: Deal Options

**Recommended Transaction:** RESEARCH_PARTNERSHIP for RF/tissue validation

### Available Options
- research_partnership
- sponsored_validation
- co_development
- exclusive_license

### Strategic Value
Real-time catheter placement feedback without radiation

### Technology Gap Filled
No non-radiation placement feedback exists for shunts

### Incumbent Weakness
Existing navigation is MRI/CT-based (expensive, not real-time)

### Buyer Synergies
Extends neuro-navigation platform into shunt placement

### Ownership Status
UNVERIFIED — buyer counsel must perform IP diligence

### Regulatory Status
Preliminary hypothesis — buyer regulatory counsel must confirm. See full dossier for details.

---

## PAGE 5: Technical Appendix Reference

**Full Dossier:** `R348/premium_portfolio/TIER_*/NN_P-21/07_PREMIUM_DOSSIER.json`
**Evidence Ledger:** `R348/premium_portfolio/TIER_*/NN_P-21/` → section 07_evidence_validation_ledger
**Experiment Protocol:** `R348/premium_portfolio/TIER_*/NN_P-21/` → section 11_development_experiment_plan
**Risk Register:** `R348/premium_portfolio/TIER_*/NN_P-21/` → section 08_technical_readiness_risk
**Competitive Analysis:** `R348/premium_portfolio/TIER_*/NN_P-21/` → section 06_competitive_alternatives

**T2 Validation Contract:** `R349/validation_contracts/P-21_T2_VALIDATION_CONTRACT.json` (if T1 climber)

**BUYER_ACTION_ID:** P21-EXP-001

---

*This meeting pack is designed for a 30-minute buyer meeting. Pages 1-2 for the executive. Pages 3-4 for the deal team. Page 5 for the technical diligence team.*
