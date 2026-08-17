# CereVasc V4 Hostile Search — Audit Report

## Final Status: OBVIOUSNESS_RISK

## Critical Finding

CereVasc OWN patent US20160051801A1 (claim 5) already discloses:
- At least TWO transducers on a CSF catheter
- At least one PRESSURE SENSOR
- At least one FLOW SENSOR

This means the core sensing architecture of RESCUE_001 (pressure sensing on CSF catheter) is ALREADY CLAIMED by CereVasc itself.

## 102 Result: SURVIVES (but weakened)
- No single reference discloses ALL 6 limitations
- But 2/6 limitations (L1, L6) are in CereVasc own patent US20160051801A1
- The 102 survives only because L2 (venous sinus pressure), L3 (differential), and L5 (occlusion prediction) are not in any single reference

## 103 Result: HIGH RISK
- CereVasc already has dual sensing (US20160051801A1)
- eShunt already accesses venous sinus (US8672871B2, US10307577B2)
- Adding venous pressure sensor is a predictable extension
- Differential calculation is trivial math
- Occlusion algorithm is generic trend detection
- MERE AGGREGATION — no functional interaction beyond sum of parts

## LLM Hallucination (V3)
- V3 LLM fabricated US20180301441A1 as 102 killing reference
- Actual patent: LED display manufacturing
- Caught by PatSnap claim verification
- Lesson: LLM patent analysis MUST be verified against actual claims

## Recommendation
KILL RESCUE_001. The invention cannot survive 103 over CereVasc own US20160051801A1.

## True Numbers
- CereVasc verified patents: 10 (7 CSF-related)
- CereVasc monitoring language: 5 patents have monitoring keywords
- CereVasc dual-sensor patent: US20160051801A1 (claim 5)
- PatSnap queries: 18
- 102: SURVIVES (weakened)
- 103: HIGH RISK
- Final: OBVIOUSNESS_RISK
