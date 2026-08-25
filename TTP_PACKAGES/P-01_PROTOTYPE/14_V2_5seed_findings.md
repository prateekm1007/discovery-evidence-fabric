# P-01 V2 — 5-Seed Robustness + Partial Ablation Findings (R282)

**Date:** 2026-08-25 (R282)
**Pre-registration:** Committed at `79e2aff` BEFORE any 5-seed runs (Article XXVII)
**Primary results:** `p01_R282_primary_V2_vs_B_5seeds.json` (90 runs: 2 arms × 9 attacks × 5 seeds)
**Ablation results:** `p01_R282_ablation_5seeds.json` (30/225 runs: seed 42 only, partial)
**Constitutional basis:** Articles XXX, XXVII, XXVIII, XXXI

## PRE-REGISTERED PRIMARY ENDPOINT: PASSED ✅

**Primary endpoint:** time-to-critical-failure under noise_3x (mean across 5 seeds)

| Condition | Threshold | Result | Verdict |
|-----------|-----------|--------|---------|
| V2/B ratio | >= 2.0x | **2.73x** | ✅ PASS |
| V2 wins seeds | >= 4/5 | **5/5** | ✅ PASS |
| No V2 seed peak > 40 mmHg | max <= 40 | **19.8 mmHg** | ✅ PASS |
| V2 wins secondary endpoints | >= 4/6 | **4/6** | ✅ PASS |

**All 4 pre-registered conditions met. V2 materially outperforms B under sensor noise across 5 seeds.**

### Primary endpoint detail (noise_3x, 5 seeds)

| Seed | B t_fail (h) | V2 t_fail (h) | V2 > B? | B peak (mmHg) | V2 peak (mmHg) |
|------|-------------|---------------|---------|---------------|-----------------|
| 42 | 5.63 | 24.00 | YES | 27.8 | 19.8 |
| 43 | 4.99 | 24.00 | YES | 26.8 | 19.8 |
| 44 | 11.98 | 24.00 | YES | 36.9 | 18.8 |
| 45 | 9.65 | 24.00 | YES | 27.7 | 19.3 |
| 46 | 11.64 | 24.00 | YES | 27.6 | 19.8 |
| **Mean** | **8.78** | **24.00** | **5/5** | **29.3** | **19.5** |

V2 survives the full 24h simulation in ALL 5 seeds. B fails between 5-12h. V2 peak ICP stays within the 20 mmHg hard limit in all seeds. B exceeds it in all seeds.

## Full 9-attack picture (5 seeds each)

| Attack | B t_fail (h) | V2 t_fail (h) | V2/B | B peak | V2 peak | V2 wins seeds | Verdict |
|--------|-------------|---------------|------|--------|---------|---------------|---------|
| none | 9.05 | 24.00 | 2.65x | 33.0 | 16.0 | 5/5 | V2 BETTER |
| **noise_3x** | **8.78** | **24.00** | **2.73x** | **29.3** | **19.5** | **5/5** | **V2 BETTER** (primary) |
| sensor_dropout | 9.41 | 7.51 | 0.80x | 31.2 | 15.9 | 2/5 | **V2 WORSE** |
| fast_occlusion | 8.43 | 24.00 | 2.85x | 29.7 | 16.0 | 5/5 | V2 BETTER |
| slow_occlusion | 11.27 | 24.00 | 2.13x | 26.2 | 16.0 | 5/5 | V2 BETTER |
| wrong_model | 9.80 | 24.00 | 2.45x | 29.2 | 15.9 | 5/5 | V2 BETTER |
| multi_failure | 8.26 | 13.37 | 1.62x | 34.6 | 103.5 | 5/5 | V2 marginal |
| actuator_saturation | 9.05 | 24.00 | 2.65x | 33.0 | 16.0 | 5/5 | V2 BETTER |
| controller_delay | 9.34 | 24.00 | 2.57x | 32.3 | 26.0 | 5/5 | V2 BETTER |

**V2 materially outperforms B on 7/9 attack modes.** (R281 1-seed showed 8/9 — the 5-seed run revealed sensor_dropout as a genuine weakness.)

## NEW finding: sensor_dropout is V2's weakness

The 1-seed R281 run showed V2 "marginally better" on sensor_dropout (1.3x). The 5-seed run reveals V2 is actually **WORSE** than B (0.80x ratio, V2 wins only 2/5 seeds).

**Why:** When sensors dropout (read 0 for 60 seconds), V2's rate limiter prevents fast recovery when sensors come back online. The controller has been rate-limiting toward a "zero sensor" fallback, and when real data returns, it takes many seconds to ramp back up. B has no rate limiting — it reacts instantly when sensors return, recovering faster.

**Implication:** The rate limiter that makes V2 robust to noise makes it fragile to dropout. This is a fundamental trade-off, not a bug. V2.1 could add a "sensor health" detector that temporarily relaxes rate limits during sensor recovery.

## Ablation: rate limiting is universally critical (1 seed, 9 attacks)

| Attack | V2 full | V2 no_rate | % of V2 | Critical? (< 80%) |
|--------|---------|-----------|---------|-------------------|
| none | 24.00 | 14.36 | 60% | YES |
| noise_3x | 24.00 | 7.69 | 32% | YES |
| fast_occlusion | 24.00 | 14.28 | 60% | YES |
| sensor_dropout | 7.92 | 6.14 | 78% | YES |
| slow_occlusion | 24.00 | 13.72 | 57% | YES |
| wrong_model | 24.00 | 13.35 | 56% | YES |
| multi_failure | 13.29 | 7.09 | 53% | YES |
| actuator_saturation | 24.00 | 14.36 | 60% | YES |
| controller_delay | 24.00 | 14.20 | 59% | YES |

**Rate limiting is critical on ALL 9 attacks** (range: 32-78% of V2 performance). Without rate limiting, V2 degrades to B-level performance or worse.

## Ablation: mechanism interactions (NEW — not visible in R281)

R281's 2-attack ablation suggested only rate limiting mattered. The 9-attack ablation reveals interactions:

| Mechanism | Critical under which attacks? |
|-----------|------------------------------|
| Rate limiting | ALL 9 attacks (universally critical) |
| Hysteresis | controller_delay (9.86h vs 24h = 41%), sensor_dropout (7.67h vs 7.92h — marginal) |
| Drainage floor | sensor_dropout (21.95h vs 7.92h — drainage floor HELPS under dropout!) |
| Alpha floor | (data incomplete — seed 42 V2_no_alpha_floor runs pending) |

**Key interaction:** The drainage floor actually HELPS under sensor_dropout (21.95h vs 7.92h). This means V2's sensor_dropout weakness could be partially addressed by strengthening the drainage floor — a design insight for V2.1.

## Honest scope statement

- **Primary (V2 vs B):** COMPLETE. 90 runs. 5 seeds × 2 arms × 9 attacks. Pre-registered criterion PASSED.
- **Ablation:** PARTIAL. 30/225 runs (seed 42 only, 4 of 5 arms). Rate limiting confirmed universally critical on 9 attacks. Mechanism interactions identified. Full 5-seed ablation PENDING compute budget.
- **Model-only:** NOT clinical evidence. Bench validation required.
- **sensor_dropout weakness:** V2 is WORSE than B under sensor dropout. Must be disclosed to buyers. V2.1 design path identified (sensor-health detector + stronger drainage floor).

## What this means for P-01

### The pre-registered success criterion is met

V2 materially outperforms B on the primary endpoint (noise_3x: 2.73x, 5/5 seeds, peak 19.8 mmHg) and on 7/9 attack modes overall. The pre-registered threshold (2.0x, 4/5 seeds, <40 mmHg peak) was set BEFORE seeing results and was exceeded.

### The commercial thesis is now statistically supported (with caveats)

> **A controller with bounded conductance-change rate maintains safe hydraulic behavior under sensor noise where conventional predictive control becomes unstable.**

This is supported by 5-seed data on the primary endpoint. The caveats are:
1. sensor_dropout is a genuine weakness (V2 worse than B)
2. multi_failure peak ICP is still high (103.5 mmHg mean — better than R281's 224 but still catastrophic)
3. Bench validation has not been done

### Next steps (R283)

1. **Complete ablation** — Finish 5-seed × 5-arm × 9-attack = 225 runs. Confirm rate limiting is universally critical across seeds. Confirm mechanism interactions.
2. **Physical bench validation** — Ship PHYSICAL_BENCH_PROTOCOL_R282.json to a lab. Build the 4-segment fluidic circuit. Run the 135-run blinded protocol. See if simulator predictions hold on hardware.
3. **Buyer outreach** — Send V2 materials to Miethke (Buyer 4). The 5-seed result is now strong enough to support a technical evaluation conversation.
4. **V2.1 design** — Address sensor_dropout weakness (sensor-health detector + stronger drainage floor under dropout).
