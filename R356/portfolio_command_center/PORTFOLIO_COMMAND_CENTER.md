# PORTFOLIO COMMAND CENTER (R356)

**Generated:** 2026-08-26T07:14:52.971069+00:00

## Portfolio Dashboard

| Package | Patent | Evidence Class | Validation Cost | Timeline | Buyer | Transaction | Build-vs-Buy | 60-min Test |
|---------|--------|---------------|-----------------|----------|-------|-------------|-------------|-------------|
| P-16 | 67/100 | INDEPENDENTLY_COMPUTATIONALLY_VALIDATED | $2-5K | 6-12 months to T3 | Medtronic, Boston Scientific,  | EXCLUSIVE_LICENSE with milesto | BUY (license) if strategic fit | PASS |
| P-01 | 58/100 | INDEPENDENTLY_COMPUTATIONALLY_VALIDATED | $3-5K bench + $50K+ for 3D multi-segment mesh | 12-24 months to T3 | Medtronic (Strata valve team), | CO_DEVELOPMENT with computatio | BUY (license) if strategic fit | PASS |
| P-24 | 50/100 | MODEL_PREDICTED | $15K | 8 weeks to T2, 12-18 months to T3 | Miethke (German precision valv | SPONSORED_VALIDATION ($15K ben | BUY (license) if strategic fit | PASS |
| P-21 | 62/100 | MODEL_PREDICTED | $2-5K | 6-12 months to T2 | Medtronic (navigation division | RESEARCH_PARTNERSHIP for RF/ti | BUY (license) if strategic fit | PASS |
| P-13 | 52/100 | MODEL_PREDICTED | $0-5K (if dataset available) | 3-6 months to T2 with data | Medical AI company (e.g., Capt | DATA_PARTNERSHIP (buyer provid | BUY (license) if strategic fit | PASS |
| P-02 | 67/100 | MODEL_PREDICTED | $10-20K | 6-12 months to T2 | Codman Hakim (adjustable valve | SPONSORED_VALIDATION ($10-20K  | BUY (license) if strategic fit | PASS |
| P-04 | 75/100 | MODEL_PREDICTED | $20-50K wet lab | 12-24 months to T2 | Pharma company with Alzheimer' | CO_DEVELOPMENT (wet-lab depend | BUY (license) if strategic fit | PASS |
| P-07 | 67/100 | MODEL_PREDICTED | $5-10K | 6-12 months to T2 | Shunt OEM (Medtronic, Integra) | SPONSORED_VALIDATION (obstruct | BUY (license) if strategic fit | PASS |
| P-11 | 78/100 | MODEL_PREDICTED | $10-15K | 6-12 months to T2 | Anti-infection catheter compan | SPONSORED_VALIDATION (phage co | BUY (license) if strategic fit | PASS |
| P-12 | 75/100 | MODEL_PREDICTED | $15-25K | 12-18 months to T2 | Pharma with Alzheimer's progra | SPONSORED_VALIDATION (enzyme s | BUY (license) if strategic fit | PASS |
| P-15 | 67/100 | MODEL_PREDICTED | $5-10K physical test | 6-12 months to T2 | Medical device OEM with implan | TECHNICAL_EVALUATION → LICENSE | BUY (license) if strategic fit | PASS |
| P-20 | 78/100 | MODEL_PREDICTED | $10-15K | 12-18 months to T2 | Implantable device company wit | SPONSORED_VALIDATION (IL-10 re | BUY (license) if strategic fit | PASS |
| P-22 | 55/100 | MODEL_PREDICTED | $20-50K | 18-36 months to T2 (4 control problems) | Neuro-navigation company (same | RESEARCH_PARTNERSHIP (4 contro | BUY (license) if strategic fit | PASS |
| P-26 | 67/100 | MODEL_PREDICTED | $12K (includes 30-day soak) | 10 weeks to T2, 12-18 months to T3 | Shunt OEM seeking passive regu | SPONSORED_VALIDATION ($12K ben | BUY (license) if strategic fit | PASS |
| P-27 | 67/100 | MODEL_PREDICTED | $18K (includes accelerated aging) | 14 weeks to T2, 12-18 months to T3 | Catheter OEM (Medtronic, Integ | SPONSORED_VALIDATION ($18K ben | BUY (license) if strategic fit | PASS |

## Summary

- Total packages: **15**
- Patent threshold met (80+): **0**
- PHYSICALLY_VALIDATED: **0**
- INDEPENDENTLY_COMPUTATIONALLY_VALIDATED: **2**
- MODEL_PREDICTED: **13**
- Buyer-ready (physical/verified): **0**

## API Status

| Database | Status | Action |
|----------|--------|--------|
| patsnap | VALID key, EXHAUSTED balance (error 67200203) | Recharge ~$3,000 |
| patentbear | REJECTED — Supabase auth returns 'Invalid API key' | Verify key is correct or get service_rol |
| lens | 401 — 'Unable to authorize user to this resource' | Token may need patent scope authorizatio |
| google_patents | PUBLIC — accessible via web search | None — working |
| uspto | PUBLIC — accessible via web | None — working |
| epo_ops | NOT_CONFIGURED — requires OAuth registration | Register at epo.org for OPS access |
| wipo_patentscope | PUBLIC — accessible via web | None — working |

## 60-Minute Buyer Test

A skeptical MedTech/Pharma buyer can open any package and in 60 minutes understand:
1. What is it?
2. Why it matters?
3. Whether they can own it?
4. What remains risky?
5. What experiment removes the remaining uncertainty?

Each package has a BUYER_ATTACK_REPORT.md that anticipates and resolves objections from:
- R&D Director (build-vs-buy)
- IP Counsel (patent/FTO)
- Manufacturing (scale-up)
- Regulatory (FDA pathway)

## Evidence Classes (preserved, not collapsed)

- MODEL_PREDICTED: internal simulation only
- INDEPENDENTLY_COMPUTATIONALLY_VALIDATED: external solver executed
- PHYSICALLY_VALIDATED: external experiment ingested via AdmissibilityBundle
- No package is marked VALIDATED without admissible external evidence
