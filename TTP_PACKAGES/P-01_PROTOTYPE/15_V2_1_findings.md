# P-01 V2.1 — Sensor-Health-Aware Controller (R283)

**Date:** 2026-08-25 (R283)
**Pre-registration:** `V2_1_PRE_REGISTRATION.json` committed before V2.1 testing (Article XXVII)
**Results:** `p01_V2_1_validation_results.json` (45 runs: 5 seeds × 9 attacks)
**Constitutional basis:** Articles XXVII, XXVIII, XXX, XXXI

## HEADLINE: V2.1 PASSED all 5 pre-registered criteria

V2.1 fixes V2's sensor_dropout weakness (7.51h → 24.0h) with **zero regression** on the other 8 attacks.

## The failure characterization (done BEFORE designing V2.1)

Per CEO R283 P1: "First characterize the failure. Do not immediately tune V2.1 and then report a better result."

### Dropout duration sweep (3 seeds × 7 durations)

| Dropout duration (s) | Mean t_fail (h) | Mean peak (mmHg) | Survival rate | Mean alpha during dropout |
|----------------------|-----------------|-------------------|---------------|---------------------------|
| 0 (no dropout) | 24.00 | 15.9 | 100% | 0.63 |
| 10 | 24.00 | 15.9 | 100% | 1.00 |
| 30 | 15.85 | 15.9 | 0% | 1.71 |
| 60 | 7.53 | 15.9 | 0% | 2.64 |
| 120 | 4.78 | 15.8 | 0% | 3.28 |
| 300 | 2.78 | 15.8 | 0% | 3.67 |
| 600 | 1.96 | 15.5 | 0% | 3.80 |

### The failure mechanism (precisely characterized)

1. **Dropout threshold:** Between 10s and 30s. V2 survives 10s dropouts, fails at 30s+.

2. **Controller state during dropout:** Alpha climbs from design value (~0.1) toward 1.0 (fully open). Mean alpha during 60s dropout = 2.64 (sum across 4 segments; per-segment ~0.66, far above design 0.104).

3. **Why alpha climbs:** When sensors read p_obs=0:
   - The PI controller computes: `g_total_target = Q_prod/P_TARGET + K_p*(0 - P_TARGET) = 0.025 - 0.24 = -0.215`
   - Clamped to `g_total_min = Q_prod/P_MAX = 0.015`
   - Desired alpha = `0.015 / (G_HEALTHY * 4) = 0.0625` per segment
   - BUT: the INV-2 cap `alpha_inv2_cap = F_MAX / (G_HEALTHY * p_obs)` — when p_obs=0, this divides by zero → cap goes to 1.0 (no limit)
   - The risk-aware allocation then distributes alpha based on weights, and with no INV-2 cap, alpha climbs toward 1.0
   - Rate limiter allows 0.02/s change, so alpha reaches ~1.0 in ~45 seconds

4. **Why this causes failure:** When sensors return after 60s dropout:
   - Alpha is at ~1.0 (all 4 segments fully open)
   - P_ICP is actually HIGH (segments have been occluding during dropout)
   - Fully-open valves cause massive over-drainage → P_ICP crashes below 5 mmHg
   - Cumulative ICP violation accumulates → failure at ~7.5h

5. **Safe fallback state:** During dropout, alpha should HOLD at last known good value, NOT climb toward 1.0.

6. **Maximum allowable stale-sensor interval:** 10 seconds (V2's survival threshold). V2.1 target: handle 300+ seconds.

## V2.1 design (frozen BEFORE testing)

V2.1 = V2 + sensor-health detector + safe fallback. All V2 mechanisms preserved (rate limiting, drainage floor, alpha floor, hysteresis — unchanged).

**Sensor-health detector:**
- Flag sensor as UNHEALTHY if: `p_obs <= 0.5` (real ICP never reads exactly 0) OR all flow sensors read 0 simultaneously OR `|p_obs - p_obs_prev| > 50 mmHg` (impossible jump)

**Safe fallback:**
- When sensor is UNHEALTHY: FREEZE alpha at last known good value
- Do NOT let PI controller drive alpha toward 1.0

**Sensor recovery:**
- When sensor is HEALTHY for 3 consecutive samples: gradually unfreeze using existing rate limiter

## V2.1 results (5 seeds × 9 attacks)

| Attack | V2 t_fail (h) | V2.1 t_fail (h) | V2.1 peak (mmHg) | V2.1 drain (%) | V2.1 survival |
|--------|-------------|----------------|-----------------|----------------|---------------|
| none | 24.00 | 24.00 | 14.0 | 100% | 100% |
| noise_3x | 24.00 | 24.00 | 19.5 | 100% | 100% |
| **sensor_dropout** | **7.51** | **24.00** | **15.8** | **100%** | **100%** |
| fast_occlusion | 24.00 | 24.00 | 16.0 | 100% | 100% |
| slow_occlusion | 24.00 | 24.00 | 16.0 | 100% | 100% |
| wrong_model | 24.00 | 24.00 | 15.9 | 100% | 100% |
| multi_failure | 13.37 | 13.37 | 69.8 | 55.7% | 0% |
| actuator_saturation | 24.00 | 24.00 | 16.0 | 100% | 100% |
| controller_delay | 24.00 | 24.00 | 26.0 | 100% | 100% |

## Pre-registered criteria evaluation

| Criterion | Threshold | Result | Verdict |
|-----------|-----------|--------|---------|
| C1: sensor_dropout t_fail | >= 20h | 24.00h | ✅ PASS |
| C2: wins vs V2 (7.51h) | >= 4/5 seeds | 5/5 | ✅ PASS |
| C3: peak under dropout | <= 25 mmHg | 16.0 | ✅ PASS |
| C4: no regression noise_3x | >= 20h | 24.00h | ✅ PASS |
| C5: no regression 7 others | >= 80% of V2 | 100% all | ✅ PASS |

**ALL 5 PRE-REGISTERED CRITERIA MET. V2.1 VALIDATED.**

## What V2.1 means for P-01

### V2.1 is now the bench-validation candidate

V2.1 fixes V2's only significant weakness (sensor_dropout) with zero regression on other attacks. The controller is now robust across 8 of 9 attack modes (multi_failure remains the unsolvable limit — no controller survives all segments failing).

### The commercial thesis (updated)

> **A controller with bounded conductance-change rate AND sensor-health-aware safe fallback maintains safe hydraulic behavior under sensor noise AND sensor dropout, where conventional predictive control becomes unstable.**

This is now a 2-mechanism thesis:
1. Rate-limited conductance change (addresses noise)
2. Sensor-health-aware safe fallback (addresses dropout)

### What remains unchanged

- multi_failure peak ICP is still high (69.8 mmHg mean — lower than R281's 224, but still catastrophic). No controller can survive all segments failing.
- This is still model-only evidence. Bench validation required.
- The 5-seed V2.1 result is strong simulation evidence, NOT independent validation.

## Constitutional compliance

- **Article XXVII:** V2.1 success criteria pre-registered in `V2_1_PRE_REGISTRATION.json` BEFORE any V2.1 runs.
- **Article XXX:** V2.1 was NOT tuned to pass. The sensor-health detector design was specified before testing.
- **Article XXVIII:** V2.1 earned its own validation. It did not silently inherit V2's claims.
- **Article XXXI:** V2 preserved. V2.1 documents what changed: added sensor-health detector + safe fallback.
- **Article XXXIV:** The failure was characterized BEFORE the fix was designed. Characterization → design → pre-registration → validation.
