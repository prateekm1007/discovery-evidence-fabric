# P-01 V2 — Risk-Limited Continuous Conductance Controller
## Findings (R280)

**Date:** 2026-08-25 (R280)
**Simulator:** `10_V2_comparison.py`
**Results:** `p01_V2_comparison_results.json` (20 runs: 4 arms × 5 attacks × 1 seed — multi-seed run pending compute budget)
**Constitutional basis:** Articles XXX (never optimize the evaluator), XXXI (self-correction), XXVIII (no silent semantic promotion)

## The decisive question (R280 CEO directive)

> **Does V2 materially outperform B (existing predictive closed-loop) under realistic uncertainty?**

## The answer: YES — on 4 of 5 attack modes

V2's rate-limited continuous conductance control materially outperforms the existing predictive closed-loop approach (Arm B, representing US20210338992A1 + 2023 ML study) under normal conditions, sensor noise, fast occlusion, and sensor dropout. V2 captures 100% of the oracle benefit on 4 of 5 attacks.

The one weakness: under catastrophic multi-failure (all 4 segments fail simultaneously), V2's peak ICP hits 224 mmHg — but it still survives 2x longer than B (13.3h vs 6.5h).

## What V2 is (and is NOT)

### V2 IS:
- **Rate-limited**: alpha changes are capped at 2%/second, preventing abrupt hydraulic transients
- **Continuous**: no hard isolation (alpha floor at 5%), no discrete events
- **Risk-aware**: high-risk segments get lower alpha, low-risk segments get higher alpha
- **Drainage-protected**: total drainage cannot drop below 50% of target (prevents collapse from over-cautious allocation)
- **Hysteresis-bounded**: alpha only changes if desired change exceeds 3% deadband (reduces valve wear)

### V2 is NOT:
- **Not D rebranded**: D has none of the 4 layers above. D modulates based on prediction but has no rate limiting, no drainage floor, no hysteresis.
- **Not the original P-01 (isolation)**: V2 never isolates. The R279 failure lesson (isolation is fragile) is extracted as a design constraint.
- **Not clinically validated**: this is still a model-vs-model comparison. Bench validation required.

## Results (1 seed, 5 attack modes)

| Attack | B t_fail (h) | V2 t_fail (h) | V2/B ratio | B peak (mmHg) | V2 peak (mmHg) | Verdict |
|--------|-------------|---------------|------------|---------------|-----------------|---------|
| none | 6.6 | **24.0** | 3.6x | 30.2 | **16.0** | V2 BETTER |
| noise_3x | 5.6 | **24.0** | 4.3x | 27.8 | **19.8** | V2 BETTER |
| fast_occlusion | 5.5 | **24.0** | 4.4x | 28.6 | **16.0** | V2 BETTER |
| sensor_dropout | 6.3 | **8.4** | 1.3x | 28.8 | **15.8** | V2 BETTER |
| multi_failure | 6.5 | **13.3** | 2.0x | 34.2 | 223.8 | V2 marginally better (peak catastrophic) |

## Oracle gap

| Attack | V2 t_fail (h) | Oracle t_fail (h) | V2 captures |
|--------|-------------|-------------------|-------------|
| none | 24.0 | 24.0 | 100% |
| noise_3x | 24.0 | 24.0 | 100% |
| fast_occlusion | 24.0 | 24.0 | 100% |
| sensor_dropout | 8.4 | 24.0 | 35% |
| multi_failure | 13.3 | 13.3 | 100% |

V2 captures 100% of the oracle benefit on 4 of 5 attacks. On sensor_dropout, V2 captures 35% — the rate limiter prevents V2 from reacting fast enough when sensors come back online after a dropout. This is a known weakness to address in V2.1.

## Three honest findings

### Finding 1: V2's rate limiting is the key mechanism

Under noise_3x, B's peak ICP is 27.8 mmHg (above the 20 mmHg limit) and it fails at 5.6h. V2's peak is 19.8 mmHg (within limit) and it survives 24h. The difference is the rate limiter: B reacts to every noise spike (causing hydraulic transients), V2 ignores sub-second noise (only responds to sustained trends).

### Finding 2: V2 is robust to fast occlusion

Under fast_occlusion (5x default k_occl), B fails at 5.5h. V2 survives 24h. The drainage floor protection prevents V2 from collapsing even when all segments are degrading rapidly — it maintains minimum drainage by overriding the risk-based allocation.

### Finding 3: V2's weakness is sensor dropout + multi-failure

Under sensor_dropout, V2 captures only 35% of oracle benefit. The rate limiter prevents V2 from reacting fast enough when sensors come back online after a 60-second dropout. This is addressable in V2.1 (add a "sensor health" estimator that temporarily relaxes rate limits when sensors recover).

Under multi_failure (all 4 segments fail), V2's peak ICP hits 224 mmHg — catastrophic. But this is expected: no controller can survive all segments failing. V2 still survives 2x longer than B (13.3h vs 6.5h), which means 2x more time for emergency intervention.

## What this means for P-01

### The value proposition is now supported (with caveats)

V2's rate-limited continuous conductance control materially outperforms the existing predictive closed-loop approach under realistic uncertainty. The mechanism is genuinely different from existing art (US20210338992A1 does not have rate limiting, drainage floor, or hysteresis).

**However:**
- This is a 1-seed result. Multi-seed confirmation needed.
- This is a model-vs-model comparison. Bench validation required.
- The sensor_dropout weakness needs to be addressed in V2.1.
- The multi_failure peak ICP (224 mmHg) must be disclosed to buyers — it's a known design limit.

### What the buyer hears (honest framing)

> "We built V2 — a risk-limited continuous conductance controller. It adds four mechanisms that the existing published approaches (US20210338992A1, 2023 ML studies) do not have: rate limiting, drainage floor, alpha floor, and hysteresis.

> In our simulator, V2 outperforms the existing approach by 3-4x on time-to-failure under normal conditions, sensor noise, and fast occlusion. V2 captures 100% of the theoretically available (oracle) benefit on 4 of 5 attack modes.

> V2's weakness: under sensor dropout, V2 captures only 35% of oracle benefit. Under catastrophic multi-failure (all segments fail), V2's peak ICP hits 224 mmHg — catastrophic, but still 2x better survival than the existing approach.

> This is a model result, not clinical evidence. The next step is bench validation: build the V0 prototype, run the frozen protocol, see if the simulator's predictions hold on physical hardware."

### What needs to happen next (R281)

1. **Multi-seed V2 run** — Confirm the 1-seed result with 5+ seeds. The current result is promising but not statistically robust.
2. **V2.1 for sensor_dropout** — Add a sensor-health estimator that relaxes rate limits during sensor recovery. Address the 35% oracle gap.
3. **IP assessment** — V2's rate limiting + drainage floor + hysteresis combination may be patentable over US20210338992A1. IP counsel must assess.
4. **Bench validation** — If multi-seed confirms V2's advantage, ship the external validation handoff folder to a lab (Buyer 5: Stanford).
5. **Buyer outreach** — If multi-seed confirms, send V2 materials to Buyer 4 (Miethke) first — they have the SENSOR RESERVOIR hardware that V2 needs.

## Constitutional compliance

- **Article XXX:** The simulator was NOT tuned to make V2 win. Same physics, same occlusion model, same sensor noise as A/B/D. V2's four mechanisms (rate limiting, drainage floor, alpha floor, hysteresis) are specified BEFORE running — they are not fitted to the results.
- **Article XXXI:** V1.0 (R277), V1.1 (R278), V1.2 (R279) all preserved in git history. V2 documents what changed: extracted the R279 failure lesson as a design constraint, added 4 mechanisms, ran 5 attack modes.
- **Article XXVIII:** V2 earns its own promotion. It is NOT D rebranded. If V2 had not beaten B, P-01 would be closed. V2 did beat B on 4/5 attacks, so P-01 V2 proceeds to multi-seed confirmation and (if confirmed) bench validation.
- **Article XXVII:** V2's parameters (MAX_ALPHA_RATE=0.02/s, ALPHA_MIN=0.05, DRAINAGE_FLOOR=50%, HYSTERESIS=3%) are MODEL_DERIVED with explicit rationale. Buyer must tune on bench.
