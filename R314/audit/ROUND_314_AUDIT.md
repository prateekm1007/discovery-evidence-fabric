# ROUND 314 AUDIT — Metric Redesign, Power Envelope, Reservoir Exhausted

**Round:** 314
**Date:** 2026-08-25
**Remote HEAD:** (R314 pending push)
**Authority:** CEO R314; Article XXXVI; METRIC_VALIDITY gate (new)

---

## 1. R314 concrete state transitions

### P-01: svFSI blocked — parameter-matched cross-check done

- **svFSI installation:** All pathways failed (precompiled .deb needs root; Docker not available; source build needs cmake/MPI/PETSc; pip packages don't exist; Docker layer extraction found binary in 483+531MB layers — too large to download/extract)
- **Hard blocker documented:** `R314/p01_svfsi_attempt/SVFSI_HARD_BLOCKER.md` with exact missing dependency and 4 CEO unblock options
- **Alternative:** Parameter-matched 1D model using EXACT svFSI pipe3D_RCR parameters (density 1.06, viscosity 0.04, RCR BC)
- **Result:** Windkessel RCR response validated — 0.61% difference from analytical steady state. P-01 multi-segment advantage holds with svFSI parameters (0.47 vs 2.04 mmHg, delta 1.57 mmHg — larger than R313 due to blood viscosity)
- **Label:** PARAMETER_MATCHED_CROSS_CHECK — svFSI EXECUTION BLOCKED (hard environment constraint). NOT MODEL_VERIFIED.

### P-19: SAFETY-ICP metric redesign → PASS (9/10 discriminating)

- **R313 flaw:** "drainage_capacity_pct" metric was FLAWED — controller preserves flow by allowing dangerous ICP (Article XXX violation)
- **R314 redesign:** Primary endpoint = time until ICP > 25 mmHg (CLINICAL threshold, AANS Brain Trauma Foundation)
- **METRIC_VALIDITY gate applied:** physical meaning ✓, clinical relevance ✓, comparator sensitivity ✓, failure sensitivity ✓
- **Result:** 9/10 scenarios discriminating (was 1/10 with old metric)
  - Distributed: survives 48h in 9/10 scenarios (only fails under comm loss: 12.8h)
  - Single-segment: fails in 6.5-8.9h across all scenarios
- **TTP assembled:** 20/20 criteria present (C08 at INDEPENDENTLY_REIMPLEMENTED, not svFSI_VERIFIED)
- **Label:** SAFETY_METRIC_VERIFIED — TTP_ASSEMBLED — strongest portfolio candidate

### P-15: Complete power operating envelope

- **96 operating points** across 5 dimensions: harvest level × load mode × arrhythmia × leakage × duty cycle
- **SAFE zone:** P50+ harvest, normal/low load, <5% arrhythmia, <100nA leakage → uptime ≥95%
- **MARGINAL zone:** P5 harvest + normal load, or degraded leakage + 2x duty
- **FAILURE zone:** P5 + high power, or P5 + degraded leakage + 2x duty
- **Recovery mode:** activates in 44 operating points (cap drops below 10%)
- **External cross-check:** P50 harvest (10 μW) within published range (5-50 μW). Arrhythmia model (70% reduction) is more aggressive than published (10-30%) — honest disclosure.
- **Label:** POWER_ENVELOPE_COMPLETE

### P-18 vacancy: Reservoir EXHAUSTED

- **R-CM-01 (Osmotic Valve):** NOT PROMOTED — prior art threat (US20020087111) unresolved
- **R-CM-02 (Venturi Self-Powering):** NOT PROMOTED — P-08 cross-check falsifies Venturi too. CSF flow (0.3 mL/min) too low for ANY flow-based energy harvesting (theoretical Venturi power 0.25 nW, below useful)
- **Decision:** Leave P-18 slot VACANT. Article XXXVI §11: "Do not create a new candidate merely to inflate the count."
- **Honest state:** 14 active + 5 cemetery + 1 vacant. CEO may provide new candidate or accept 14.

### METRIC_VALIDITY gate (new, CEO P7)

- Formal gate defined: 4 requirements (physical meaning, clinical relevance, comparator sensitivity, failure sensitivity)
- Retroactively applied: P-05 V1 FAIL (tautology), P-03 R308 FAIL (non-discriminating), P-19 R313 FAIL (misleading), P-19 R314 PASS, P-01 PASS, P-15 PASS, P-16 PASS
- Now mandatory preregistration field for all candidates

---

## 2. R314 dashboard

| Candidate | Model | Indep. verification | Economic proof | Differentiation | TTP | Final |
|-----------|:-----:|:-------------------:|:--------------:|:---------------:|:---:|-------|
| P-01 | ✅ | ⚠️ parameter-matched (svFSI blocked) | ✅ MODELLED | ✅ partial | ✅ 19/20 | BLOCKED (svFSI hard constraint) |
| P-02 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-04 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-07 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-09 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-10 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-11 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-12 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-13 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-14 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-15 | ✅ | ✅ envelope (96 points, 7 dims) | ⏳ | ⏳ | ⏳ | ENVELOPE_COMPLETE |
| P-16 | ✅ | ✅ PyTissueOptics CIs overlap | ⏳ | ⏳ | ⏳ | EXTERNAL-MC VERIFIED |
| P-17 | ⚠️ | ❌ | — | — | — | OPEN (repair needed) |
| P-18 | VACANT | — | — | — | — | Reservoir exhausted |
| P-19 | ✅ | ✅ safety metric (9/10) + reimpl | ✅ MODELLED | ✅ partial | ✅ 20/20 | **SAFETY_METRIC_VERIFIED** |

## 3. Portfolio state

- **14 active** + **5 cemetery** (P-06, P-08, P-05, P-03, P-18) + **1 vacant** (P-18 slot, reservoir exhausted)
- **0 TECHNOLOGY_TRANSFER_READY** (P-19 closest, blocked by C08 svFSI requirement)
- **3 candidates with independent/external verification** (P-15 envelope, P-16 PyTissueOptics, P-19 safety metric + reimpl)
- **1 candidate with complete TTP** (P-19, 20/20 criteria)

## 4. The CEO test (R314 honest answer)

- **P-19:** APPROACHING YES — TTP assembled, safety metric verified (9/10 discriminating), economics modelled, differentiation documented. Full YES pending svFSI cross-check.
- **P-15:** APPROACHING YES — power envelope complete (96 operating points, safe zone defined)
- **P-16:** PARTIAL YES — external MC verified within uncertainty, MCX pending
- **P-01:** NO — physics model still disagrees with benchmark; svFSI blocked by environment

## 5. R315 priorities

1. **CEO action for P-01/P-19:** Provide root access, Docker, or build toolchain to enable actual svFSI execution. This is the single highest-value unblock — it would allow P-19 to reach TECHNOLOGY_TRANSFER_READY.
2. **P-17 repair:** Diagnose 0.215 survival vs 0.3 threshold. One repair attempt.
3. **Phase B completions:** P-02, P-04, P-11 — begin independent verification + economics.
4. **P-18 vacancy:** CEO decision — provide new candidate or accept 14 active.
5. **Remaining 9 candidates:** Push through the 20-point finish gate using the METRIC_VALIDITY gate for each.

## 6. Key R314 insight

The METRIC_VALIDITY gate is the most important R314 addition. It would have caught:
- P-05 V1 tautology (metric: wash-out gate correlation — not clinically relevant)
- P-03 R308 non-discriminating metric (metric: drainage in-bounds — not comparator-sensitive)
- P-19 R313 misleading metric (metric: drainage capacity — not failure-sensitive)

All three were caught AFTER execution. The gate moves the check to BEFORE execution — preventing wasted rounds on invalid metrics.
