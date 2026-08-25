# Portfolio State Table — R316

**Generated:** 2026-08-25T20:56:33.240279+00:00
**Authority:** Mechanically generated from gate artifacts (CEO R316 §6/§7)

## State Definitions

- **MODEL_RUNNING**: Code runs. No attack suite. No independent verification.
- **MODEL_ATTACKED**: Code has survived a serious attack suite (>= 3 hostile attacks).
- **MODEL_INDEPENDENTLY_VERIFIED**: Independent implementation or external scientific engine agrees within preregistered tolerance.
- **TECHNICALLY_EVALUABLE**: Technical package can be independently inspected and reproduced (TTP assembled).
- **TECHNOLOGY_TRANSFER_READY**: Technical + evidence + economics + differentiation + reproduction + transfer package all complete.
- **BUYER_TESTED**: Real external engineering organization has actually evaluated it. (CEO-owned, not our manufacturing requirement.)

## Portfolio Summary

| State | Count |
|-------|------:|
| MODEL_RUNNING | 10 |
| MODEL_ATTACKED | 2 |
| MODEL_INDEPENDENTLY_VERIFIED | 2 |
| TECHNICALLY_EVALUABLE | 1 |
| TECHNOLOGY_TRANSFER_READY | 0 |
| BUYER_TESTED | 0 |
| **Total active** | **15** |
| Cemetery | 5 |

## Per-Candidate Table

| ID | Model | Ext Solver | Attack | Indep Verify | Metric Valid | Economics | TTP | State | Blocker |
|----|-------|-----------|--------|-------------|-------------|-----------|-----|-------|---------|
| P-01 | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ | ✅ | MODEL_ATTACKED | 3D physics verification blocked (svFSI not installable). 1D ... |
| P-02 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | Not yet processed through R309+ completion pipeline |
| P-04 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | Wet-lab dependent (enzyme kinetics). Not yet processed. |
| P-07 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | Extracted from P-04 but not independently manufactured |
| P-09 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | Wet-lab dependent (molecule design). Not yet processed. |
| P-10 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | R308 FAIL (5.04s vs 5s limit). Repair not yet attempted. |
| P-11 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | Wet-lab dependent. Not yet processed. |
| P-12 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | Wet-lab dependent. Not yet processed. |
| P-13 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | Energy dependency on P-15/P-16. Not yet processed. |
| P-14 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | R308 FAIL (16.5% vs 30%). Repair not yet attempted. |
| P-15 | ✅ | ❌ | ✅ | ✅ | ✅ | ❌ | ❌ | MODEL_INDEPENDENTLY_VERIFIED | Independent reimplementation (not external solver). Physical... |
| P-16 | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | MODEL_INDEPENDENTLY_VERIFIED | PyTissueOptics verified (CIs overlap). MCX blocked (no CUDA)... |
| P-17 | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | MODEL_RUNNING | R308 FAIL (0.215 vs 0.3 threshold). Repair not yet attempted... |
| P-19 | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | TECHNICALLY_EVALUABLE | External solver (svFSI) not executed. Same-author reimplemen... |
| P-20 | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ❌ | MODEL_ATTACKED | Manufactured R316. IL-10 kinetics MODELLED. Wet-lab validati... |