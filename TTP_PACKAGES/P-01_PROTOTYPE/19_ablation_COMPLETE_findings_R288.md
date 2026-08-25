# P-01 Full Ablation — 5 Seeds, 225 Runs (R288)

**Date:** 2026-08-25 (R288)
**Data:** `p01_R282_ablation_5seeds.json` (225/225 runs complete)
**Constitutional basis:** Articles XXX, XXVIII, XXXI

## VERDICT: Rate limiting finding CONFIRMED across all 5 seeds

> **Removing rate limiting degrades V2 performance on 41 of 45 runs (mean ratio 0.65, critical on 8/9 attacks). The rate-limiting finding is CONFIRMED, not weakened or rejected.**

## Full 5-seed results (mean t_fail across 5 seeds)

| Attack | V2 full | no_rate_limit | no_hysteresis | no_drainage_floor | no_alpha_floor |
|--------|---------|--------------|--------------|-------------------|---------------|
| none | 24.00 | **14.32** | 24.00 | 24.00 | 24.00 |
| noise_3x | 24.00 | **10.03** | 24.00 | 24.00 | 24.00 |
| sensor_dropout | 7.51 | 8.24 | 7.40 | **22.41** | 8.32 |
| fast_occlusion | 24.00 | **14.35** | 24.00 | 24.00 | 24.00 |
| slow_occlusion | 24.00 | **15.00** | 24.00 | 24.00 | 24.00 |
| wrong_model | 24.00 | **14.38** | 24.00 | 24.00 | 24.00 |
| multi_failure | 13.37 | **9.58** | 13.52 | 13.37 | 11.74 |
| actuator_saturation | 24.00 | **14.32** | 24.00 | 24.00 | 24.00 |
| controller_delay | 24.00 | **14.10** | **16.74** | 24.00 | 24.00 |

## Mechanism criticality (5 seeds × 9 attacks = 45 data points per arm)

| Mechanism removed | Mean ratio | Range | Critical runs | Verdict |
|-------------------|-----------|-------|--------------|---------|
| **Rate limiting** | **0.65** | 0.31-1.44 | **41/45** | **CONFIRMED CRITICAL** |
| Hysteresis | 0.97 | 0.41-1.07 | 3/45 | Non-critical |
| Drainage floor | 1.22 | 1.00-3.24 | 0/45 | Non-critical (HELPS on dropout) |
| Alpha floor | 1.00 | 0.60-1.18 | 1/45 | Non-critical |

## Per-attack criticality (5 seeds each)

| Attack | no_rate_limit | no_hysteresis | no_drainage_floor | no_alpha_floor |
|--------|-------------|--------------|-------------------|---------------|
| none | **0.60 CRIT** | 1.00 ok | 1.00 ok | 1.00 ok |
| noise_3x | **0.42 CRIT** | 1.00 ok | 1.00 ok | 1.00 ok |
| sensor_dropout | 1.10 ok | 0.99 ok | **2.98 HELPS** | 1.11 ok |
| fast_occlusion | **0.60 CRIT** | 1.00 ok | 1.00 ok | 1.00 ok |
| slow_occlusion | **0.62 CRIT** | 1.00 ok | 1.00 ok | 1.00 ok |
| wrong_model | **0.60 CRIT** | 1.00 ok | 1.00 ok | 1.00 ok |
| multi_failure | **0.72 CRIT** | 1.01 ok | 1.00 ok | 0.88 ok |
| actuator_saturation | **0.60 CRIT** | 1.00 ok | 1.00 ok | 1.00 ok |
| controller_delay | **0.59 CRIT** | **0.70 CRIT** | 1.00 ok | 1.00 ok |

## Three findings (confirmed across 5 seeds)

### Finding 1: Rate limiting is CONFIRMED as the critical mechanism

Removing rate limiting degrades V2 on 41/45 runs. Mean ratio 0.65 (V2 without rate limiting survives only 65% as long as full V2). Critical on 8/9 attacks — the exception is sensor_dropout, where V2 itself fails (7.51h) and the rate limiter doesn't help.

### Finding 2: Hysteresis is conditionally critical (controller_delay only)

Hysteresis is non-critical on 8/9 attacks but CRITICAL on controller_delay (0.70 ratio). This confirms the 2-seed finding: hysteresis helps when controller latency is high (5-second delay). For standard 1-second delay, hysteresis is unnecessary.

### Finding 3: Drainage floor HELPS on sensor_dropout (design insight for V2.2)

Removing the drainage floor IMPROVES performance on sensor_dropout (2.98x ratio — V2 without drainage floor survives 22.41h vs V2's 7.51h). This is consistent across all 5 seeds. The drainage floor prevents the controller from reducing drainage enough during dropout. **V2.2 design insight: relax the drainage floor during sensor dropout.**

## Minimum transferable mechanism (CONFIRMED)

> **Bounded rate of conductance change (rate limiting at 2%/second) is the minimum transferable mechanism.**

The other three mechanisms are engineering refinements:
- **Hysteresis**: add if controller latency > 1 second
- **Drainage floor**: remove or relax during sensor dropout (V2.2)
- **Alpha floor**: optional, marginal impact

## What this means for the commercial package

The technology asset is ONE principle: **bounded rate of conductance change for multi-segment hydraulic drainage control.** This is simple, transferable, and defensible as an application of a known engineering technique to a new context.

The buyer receives:
1. The rate-limiting mechanism (the core asset)
2. The sensor-health fallback (engineering hygiene, addresses dropout)
3. Optional refinements (hysteresis for high-latency, drainage floor for non-dropout scenarios)

The buyer can tune or modify the refinements. The rate limiting is the non-negotiable core.
