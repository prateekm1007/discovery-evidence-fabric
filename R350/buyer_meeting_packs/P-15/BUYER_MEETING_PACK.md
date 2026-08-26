# BUYER MEETING PACK — P-15

**Package:** P-15 — Cardiac motion energy harvesting (1-40 μW) + 100μF capacitor + duty-cycled sensi
**Date:** 2026-08-26T06:03:14.656823+00:00
**Transfer Posture:** DECISIVE_EXPERIMENT_REQUIRED

---

## PAGE 1: Executive Opportunity

P-15 — Cardiac motion energy harvesting (1-40 μW) + 100μF capacitor + duty-cycled sensi. A computationally specified P-15 concept plus a preregistered decisive experiment — not a validated technology. Current evidence: T1. Transfer posture: DECISIVE_EXPERIMENT_REQUIRED. Recommended transaction: TECHNICAL_EVALUATION → LICENSE. Validation cost: $5-10K physical test.

**Strategic Buyer:** Medical device OEM with implantable power management pipeline (Medtronic, Boston Scientific)

**Why This Company Should Care:**
Battery-free implantable sensors are a new product category. 99.9% uptime is the key metric.

**Recommended Transaction:** TECHNICAL_EVALUATION → LICENSE

**Validation Investment:** $5-10K physical test (6-12 months to T2)

---

## PAGE 2: Evidence and Uncertainty

**Current Evidence Level:** T1
**Physical Validation:** NONE

### What Is Demonstrated
- MODELLED: 2 claims
- COMPUTATIONALLY_SUPPORTED: 0 claims
- OBSERVED: 0 claims

### What Is NOT Proven
- Zero-harvest death in 0.1h (no backup battery)
- Arrhythmia model (70% reduction) more aggressive than published (10-30%)

### Strongest Alternative
Lithium battery (finite life, 5-8 years, requires replacement surgery)

### Remaining Decisive Uncertainty
Actual cardiac harvesting in target implant location. Whether 10 μW is achievable in shunt geometry.

---

## PAGE 3: Development Roadmap

### Validation Experiment
Physical energy harvesting test: build harvesting circuit (cardiac motion + buffer), implant in mock cardiac environment, measure power output over 30 days. Compare to 99.9% uptime model.

**Cost:** $5-10K physical test
**Timeline:** 6-12 months to T2
**Pass:** Sustained power output >= 5 μW for 30 days (sufficient for pacemaker-grade operation). Uptime >= 95%.
**Fail:** Power output < 1 μW or uptime < 80%

### Development Path
1. **Phase 1 — Bench Validation:** $5-10K (harvesting circuit + sensor) — Medium — power electronics
2. **Phase 2 — Prototype:** If Phase 1 passes
3. **Phase 3 — Relevant Environment:** Clinical/cadaver/animal testing
4. **Phase 4 — Regulatory:** 510(k) if component, PMA if active implant
5. **Phase 5 — Commercial Deployment**

### Manufacturing Complexity
Medium — hybrid power circuit

---

## PAGE 4: Deal Options

**Recommended Transaction:** TECHNICAL_EVALUATION → LICENSE

### Available Options
- technical_evaluation
- sponsored_physical_test
- exclusive_license

### Strategic Value
Platform — hybrid power for any low-power implantable sensor

### Technology Gap Filled
Battery-free implantable sensors do not exist commercially

### Incumbent Weakness
Batteries limit implant lifetime

### Buyer Synergies
Enables new sensor product category

### Ownership Status
UNVERIFIED — buyer counsel must perform IP diligence

### Regulatory Status
Preliminary hypothesis — buyer regulatory counsel must confirm. See full dossier for details.

---

## PAGE 5: Technical Appendix Reference

**Full Dossier:** `R348/premium_portfolio/TIER_*/NN_P-15/07_PREMIUM_DOSSIER.json`
**Evidence Ledger:** `R348/premium_portfolio/TIER_*/NN_P-15/` → section 07_evidence_validation_ledger
**Experiment Protocol:** `R348/premium_portfolio/TIER_*/NN_P-15/` → section 11_development_experiment_plan
**Risk Register:** `R348/premium_portfolio/TIER_*/NN_P-15/` → section 08_technical_readiness_risk
**Competitive Analysis:** `R348/premium_portfolio/TIER_*/NN_P-15/` → section 06_competitive_alternatives

**T2 Validation Contract:** `R349/validation_contracts/P-15_T2_VALIDATION_CONTRACT.json` (if T1 climber)

**BUYER_ACTION_ID:** P15-EXP-001

---

*This meeting pack is designed for a 30-minute buyer meeting. Pages 1-2 for the executive. Pages 3-4 for the deal team. Page 5 for the technical diligence team.*
