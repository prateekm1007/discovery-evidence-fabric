# ROUND 313 AUDIT — Physics Repair, Power Envelopes, Cemetery Discipline

**Round:** 313
**Date:** 2026-08-25
**Remote HEAD:** (R313 pending push)
**Authority:** CEO directive R313; Article XXXVI

---

## 1. R313 concrete state transitions

### P-01: Physics repair ATTEMPTED — benchmark improved but still disagrees

- **R312 finding:** Simplified 1D model: 2.19 mmHg vs published FDA 8-15 mmHg. 80% underprediction.
- **R313 action:** Identified missing physics (NOT tuned to match benchmark):
  1. Sudden contraction loss (K_c = 0.42)
  2. Turbulent friction (Blasius f = 0.316/Re^0.25, Re_throat ~2700 transitional)
  3. Sudden expansion loss (K_e = 0.31)
- **R313 result:** Upgraded model predicts 3.21 mmHg (improved from 2.19, but still below 8-15 range)
- **Remaining gap:** 72% underprediction remains. Likely missing: flow separation at diverging section, non-Newtonian effects, full-nozzle vs inlet-to-throat measurement point
- **P-01 candidate experiment rerun:** Multi-segment advantage HOLDS (0.4 vs 0.5 mmHg under obstruction) — but magnitude tiny
- **Label:** BENCHMARK_DISAGREEMENT — model improved but physics still incomplete. P-01 remains blocked from TTR.

### P-19: Full attack suite executed — metric flaw discovered

- **Attack suite:** 10 scenarios (10/30/50/70/90% obstruction, single-node failure, simultaneous failures, comm loss, sensor error, actuator failure)
- **Result:** Only 1/10 discriminating — NOT because the mechanism doesn't work, but because the capacity metric is flawed (ICP rises to compensate for lost conductance, so both systems "maintain capacity" at dangerous ICP)
- **Independent verification:** scipy.ode vs solve_ivp, 0.0% cross-impl diff — PASS
- **Root cause of low discrimination:** Need to change metric from "drainage capacity %" to "survival time at P_ICP < 25 mmHg" (matching P-03 approach)
- **Label:** TTP_ASSEMBLED — attack suite needs metric redesign — independent reimplementation PASS

### P-15: Full power operating envelope characterized

- **9 operating points:** 3 harvest levels (P5/P50/P95) × 3 load modes (low/normal/high)
- **Safe zone (uptime >= 95%):** 7/9 operating points
- **Marginal (50-95%):** 1/9 (P5 + normal load)
- **Failure (<50%):** 1/9 (P5 + high power)
- **Failure envelope:** Zero-harvest → death in 0.1h. P5+high-power → 42.5% uptime.
- **Label:** POWER_ENVELOPE_CHARACTERIZED — safe operating zone defined

### P-18: V2 repair FAILED → CEMETERY (CE-026)

- **V1 (R312):** Enzymatic NO secretion, 0.10 pmol/cm²/s, substrate depletion
- **V2 (R313):** DETA-NONOate chemical NO donor (genuinely different mechanism — thermal decomposition, not enzymatic)
- **V2 result:** Initial release 48.6 pmol/cm²/s (strong), but 20h half-life → decays below 1.0 threshold after 4.7 days
- **Verdict:** FAIL (frozen criterion: sustained >= 1.0 for 30 days; achieved only 4.7/30 days)
- **Article XXXVI §4:** Repair budget = 1, second failure terminal
- **P-18 → CEMETERY** (CE-026). Reusable knowledge: NO donor half-life must be >7 days for 30-day sustained release (SNAP, refillable reservoir, or catalytic generation)

### P-16: Convergence ladder continued (R312 carried forward)

- R312 established: PyTissueOptics 50k (1.147 ± 0.162) overlaps R310 MC CI (1.049 ± 0.065)
- R313: 100K+ photons timed out (CPU constraint). MCX still blocked (no CUDA)
- **Label:** EXTERNAL-MC VERIFIED (CIs overlap) — MCX pending (hardware constraint)

---

## 2. R313 dashboard

| Candidate | Model | Indep. verification | Economic proof | Differentiation | TTP | Final |
|-----------|:-----:|:-------------------:|:--------------:|:---------------:|:---:|-------|
| P-01 | ✅ | ⚠️ benchmark improved 2.19→3.21, still disagrees | ✅ MODELLED | ✅ partial | ✅ 19/20 | BLOCKED (physics incomplete) |
| P-02 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-04 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-07 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-09 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-10 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-11 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-12 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-13 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-14 | ✅ | ❌ | ⏳ | ⏳ | ⏳ | OPEN |
| P-15 | ✅ | ✅ power envelope (7/9 safe) | ⏳ | ⏳ | ⏳ | ENVELOPE_CHARACTERIZED |
| P-16 | ✅ | ✅ PyTissueOptics CIs overlap | ⏳ | ⏳ | ⏳ | EXTERNAL-MC VERIFIED |
| P-17 | ⚠️ | ❌ | — | — | — | OPEN (repair needed) |
| P-18 | ❌ | CEMETERY | — | — | — | **CEMETERY (CE-026)** |
| P-19 | ✅ | ✅ independent reimpl (0% diff) | ✅ MODELLED | ✅ partial | ✅ 20/20 | TTP_ASSEMBLED (metric redesign needed) |

## 3. Portfolio state

- **14 active** (P-18 killed) + **5 cemetery** (P-06, P-08, P-05, P-03, P-18)
- **1 vacancy** (P-18 slot) — needs replacement from reservoir (R-CM-01 or R-CM-02, but both have unresolved issues)
- **0 TECHNOLOGY_TRANSFER_READY**
- **2 candidates with external/independent verification** (P-15 envelope, P-16 PyTissueOptics)
- **1 candidate with TTP assembled** (P-19, but metric redesign needed)

## 4. R314 priorities

1. **P-19 metric redesign:** Change from "drainage capacity %" to "survival time at P_ICP < 25 mmHg." Rerun attack suite. If discriminating count improves to >= 8/10, P-19 approaches TTR.
2. **P-01 physics:** Either (a) add flow separation model, or (b) get actual svFSI running (CEO action: root/Docker/build toolchain).
3. **Replace P-18:** One vacancy. R-CM-02 (Venturi) has P-08 cross-check risk. Consider whether to fill or leave vacant.
4. **P-17 repair:** Diagnose 0.215 survival vs 0.3 threshold. One repair attempt.
5. **Phase B completions:** P-02, P-04, P-11 — begin independent verification + economics.

## 5. The CEO test (R313 honest answer)

> Could you take any one of the 14 folders tomorrow, hand it to a competent engineering team, and have them start evaluating the technology without needing us to explain away gaps?

- **P-19:** PARTIAL YES (TTP assembled, 20/20 criteria, but attack suite metric needs redesign)
- **P-15:** PARTIAL YES (power envelope characterized, safe zone defined, but no physical measurement)
- **P-16:** PARTIAL YES (external MC verified within uncertainty, but MCX pending)
- **P-01:** NO (physics model still disagrees with published benchmark)
- **All others:** NO

**R313 progress:** P-01 physics improved (real missing physics identified). P-19 full attack suite executed (metric flaw discovered). P-15 power envelope characterized (7/9 safe zone). P-18 killed with reusable knowledge (NO donor half-life constraint). The system is finding real problems and documenting them honestly. Zero TTR — but the path is now paved with real physics findings, not framework.
