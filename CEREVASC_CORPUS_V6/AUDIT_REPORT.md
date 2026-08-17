# CereVasc Corpus V6 — Family Reconstruction

## Status: CORPUS_RECONSTRUCTED (PARTIAL)

## CRITICAL FINDING: 4 CereVasc Patents Have 4/6 Limitation Keywords

The following CereVasc patents contain keywords for L1 (CSF pressure), L2 (venous pressure), L3 (differential), AND L4 (endovascular context):

| Patent | Claims | L1 | L2 | L3 | L4 | L5 | L6 | Total |
|---|---|---|---|---|---|---|---|---|
| US20160136398A1 | 41 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | 4/6 |
| US10279154B2 | 11 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | 4/6 |
| US10765846B2 | 18 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | 4/6 |
| US12485256B2 | 17 | ✓ | ✓ | ✓ | ✓ | ✗ | ✗ | 4/6 |

**IMPORTANT**: These are KEYWORD matches, NOT claim-level passage analysis. The keywords may appear in the context of:
- 'Normal Pressure Hydrocephalus' (NPH) — the disease name contains 'pressure'
- 'Differential' may refer to diagnosis, not measurement
- 'Flow' may refer to CSF flow through the shunt, not flow measurement

**CRITICAL CAVEAT**: L5 (occlusion/patency prediction) and L6 (monitoring output) are NOT found in ANY of these patents. This means even if L1-L4 are genuinely about pressure sensing (which needs claim-level passage verification), the invention's predictive monitoring aspect remains novel.

## Corpus Metrics
- Discovered candidates: 24
- Verified patents: 24 (all retrieved from PatSnap)
- CSF-related patents: 14
- Families resolved: 4
- Patents with 3+ keyword limitations: 4
- Patents with L5 (occlusion prediction): 0
- Patents with L6 (monitoring output): 0 (except US20230210572A1 which is bone cement)

## Family Graph

### FAMILY 1: US8672871 (Original eShunt)
- Root: US8672871B2 (priority 2009-01-29)
- Members: US8672871B2, US9199067B2
- Description: Original endovascular CSF shunt

### FAMILY 2: US20160136398 (Hydrocephalus Treatment)
- Root: US20160136398A1 (priority 2015-10-30)
- Members: US20160136398A1, US10279154B2, US10765846B2, US10307576B2, US12011557B2
- Description: Methods and systems for treating hydrocephalus
- NOTE: 3 members have 4/6 limitation keywords — CRITICAL for RESCUE_001

### FAMILY 3: US11951270 (Endovascular Access)
- Root: US11951270B2 (priority 2015-10-30)
- Members: US11951270B2, US10272230B2, US10758718B2, US10307577B2, US12485256B2
- Description: Endovascular subarachnoid access
- NOTE: US12485256B2 has 4/6 limitation keywords

### FAMILY 4: US9861799 (Anti-occlusion)
- Root: US9861799B2
- Members: US9861799B2
- Description: CSF shunt with anti-occlusion coating

## Technology Map
- CORE_SHUNT: Families 1, 2
- FLOW: Families 1, 2, 4
- PRESSURE: Family 2 (keyword present, context unclear)
- DELIVERY: Family 3
- ACCESS: Family 3
- DEPLOYMENT: Families 2, 3
- OCCLUSION: Family 4
- MONITORING: NONE (no CereVasc family has monitoring claims)

## Monitoring White Space (Re-confirmed)
- CereVasc monitoring patents: 0
- CereVasc patents with L5 (occlusion prediction): 0
- CereVasc patents with L6 (monitoring output): 0
- The monitoring layer remains a genuine gap in CereVasc's portfolio

## RESCUE_001 Status
- 102: SURVIVES (no single patent has all 6 limitations; L5 and L6 are absent from ALL CereVasc patents)
- 103: NEEDS CLAIM-LEVEL VERIFICATION (4 patents have L1-L4 keywords but need passage-level analysis to determine if the keywords represent actual sensing claims or disease-name mentions)
- The critical question: do US20160136398A1, US10279154B2, US10765846B2, US12485256B2 actually DISCLOSE pressure differential measurement, or do the keywords appear in the context of treating NPH?

## Next Step
Claim-level passage extraction from the 4 patents with 4/6 keyword limitations to determine:
1. Is 'pressure' used as a sensor measurement or as part of 'normal pressure hydrocephalus'?
2. Is 'differential' used as a calculation or in a different context?
3. Do the claims actually teach CSF-venous pressure differential sensing?

## STOP FOR CEO AUDIT
