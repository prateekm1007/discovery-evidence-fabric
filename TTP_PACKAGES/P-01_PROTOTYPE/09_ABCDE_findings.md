# P-01 V1.2 — A/B/C/D/E Findings (STRONGEST-BASELINE + ORACLE)

**Date:** 2026-08-25 (R279)
**Simulator:** `08_ABCDE_comparison.py`
**Results:** `p01_v1_2_ABCDE_comparison_results_{none,misspecification,sensor-noise}.json`
**Constitutional basis:** Articles XXX (never optimize the evaluator), XXXI (self-correction), XXVIII (no silent semantic promotion)

## The central question (R279 CEO directive)

> **Does our particular prediction → isolation → redistribution controller materially outperform existing predictive/closed-loop shunt approaches?**

## The honest answer: NO

P-01's isolation mechanism does NOT add value beyond generic predictive closed-loop control. Under normal conditions, D (closed-loop modulation without isolation) survives LONGER than C (predictive isolation). Under sensor noise, D dramatically outperforms C.

## The five arms

| Arm | What it represents | Isolation? | Prediction? |
|-----|-------------------|-----------|-------------|
| **A** (conventional) | Single-segment, fixed valve, no control | No | No |
| **B** (reactive) | 4 segments, isolate on actual failure | Yes (reactive) | No |
| **C** (predictive isolation) | P-01: 4 segments, isolate on trend prediction | Yes (predictive) | Yes |
| **D** (predictive closed-loop) | Strongest published approach: 4 segments, modulate valves based on prediction, NO isolation | No | Yes |
| **E** (oracle) | Perfect knowledge, isolate at lesion onset | Yes (perfect) | Yes (perfect) |

Arm D represents our reproduction of US20210338992A1 (closed-loop shunt with sensors + controller + valve + feedback) + 2023 ML study (predictive risk model). It is NOT the actual published system — it is our simulation of that approach.

## Results (no attack, 5 seeds)

| Metric | A | B | C | D | E | C vs D | C vs E |
|--------|---|---|---|---|---|--------|--------|
| Peak ICP (mmHg) | 59.0 | 37.1 | **22.4** | 30.3 | **20.0** | C better by 8.0 | C worse by 2.4 |
| Time to failure (hr) | 1.3 | 0.8 | 7.7 | **8.9** | 7.7 | C WORSE by 1.3 | C = E |
| Drainage capacity (%) | 5.4 | 3.5 | 31.9 | **37.2** | 31.9 | C worse by 5.3 | C = E |
| Controller energy (chg/hr) | 0.2 | 0.9 | 4380 | 4502 | 4297 | C better by 122 | C worse by 83 |

## Three critical findings

### Finding 1: C does NOT outperform D on time-to-failure

D (predictive closed-loop without isolation) survives 8.9h vs C's 7.7h — **14% longer**. The isolation mechanism is actually HARMFUL to time-to-failure.

**Why:** When C isolates a segment (alpha → 0), that segment's conductance drops to zero immediately. This causes a sudden ICP spike. D never isolates — it gradually reduces alpha on at-risk segments. The gradual reduction avoids the spike and maintains drainage longer.

**Implication:** P-01's "isolation" mechanism is counterproductive for time-to-failure. Soft modulation (D) is strictly better.

### Finding 2: C only wins on peak ICP (and only under low noise)

C's peak ICP is 22.4 mmHg vs D's 30.3 mmHg — 8 mmHg lower. This is the ONLY metric where C outperforms D. Both are above the 20 mmHg hard limit, but C is in the "mildly elevated" range while D is in the "moderately elevated" range.

**But this advantage disappears under sensor noise** (see Finding 3).

### Finding 3: Under sensor noise, D dramatically outperforms C

Under 3x sensor noise (attack mode):

| Metric | C (predictive isolation) | D (closed-loop) | C vs D |
|--------|-------------------------|-----------------|--------|
| Peak ICP | 29.7 mmHg | 29.3 mmHg | C worse by 0.4 |
| Time to failure | 3.5h | **8.9h** | C worse by 5.4h (−61%) |
| Drainage capacity | 14.5% | **37.1%** | C worse by 22.6% |

C's trend predictor fires false positives under noise (1.8 interventions vs 1.0 normal), causing premature isolation of healthy segments. D doesn't isolate, so it's immune to false-positive isolation.

**Implication:** The isolation mechanism is fragile under realistic sensor noise. D's soft modulation is inherently more robust.

### Finding 4 (Oracle): C captures 100% of oracle benefit on t_fail

E (oracle) and C have identical t_fail (7.7h). This means C's trend predictor isolates early enough to capture all theoretically available t_fail benefit. The Oracle only wins on peak ICP (20.0 vs 22.4 mmHg) because it isolates slightly earlier.

**But since D outperforms both C and E on t_fail, the oracle bound is not the right benchmark.** The oracle tests "perfect isolation timing" — but the real question is "isolation vs no isolation." D shows that NO isolation is better.

## What this means for P-01

### The original value proposition is NOT supported

P-01 was positioned as "predictive isolation + redistribution." The A/B/C/D/E comparison shows:
1. Isolation is WORSE than soft modulation on time-to-failure (both normal and noise conditions)
2. Isolation is ONLY better on peak ICP under low-noise conditions
3. Under realistic sensor noise, isolation is dramatically worse

### P-01 must be reformulated

Two paths forward:

**Path 1: Drop the isolation mechanism.** P-01 becomes "predictive closed-loop multi-segment shunt controller" (Arm D). This is essentially the existing published approach (US20210338992A1) applied to multi-segment hardware. Value proposition: "multi-segment hardware + predictive closed-loop." Weaker differentiation, but honest.

**Path 2: Find a different value proposition for isolation.** The isolation mechanism might still be valuable for:
- Infection control (isolate a contaminated segment to prevent biofilm spread)
- Biofilm management (isolate a segment for localized treatment)
- Maintenance (isolate a segment for non-surgical replacement — if physically possible)

These are NOT about ICP management. They're about infection/maintenance. P-01 would need to be repositioned entirely.

### What the buyer hears (honest framing)

> "We built a simulator to test whether our predictive isolation mechanism outperforms generic predictive closed-loop control. It does NOT. Under normal conditions, soft modulation (no isolation) survives 14% longer. Under realistic sensor noise, soft modulation survives 61% longer. The isolation mechanism only wins on peak ICP under low-noise conditions.

> This means our original value proposition — 'predictive isolation' — is NOT supported by the model. We are reformulating.

> What we CAN offer: a multi-segment shunt with predictive closed-loop control (Arm D), which outperforms both conventional single-path (A) and reactive redundancy (B). But this is close to existing published approaches (US20210338992A1), so the IP position needs careful assessment.

> Alternatively, if you see value in the isolation mechanism for infection control or maintenance (not ICP management), we can explore that direction."

This is much more credible than the R278 framing ("7-9x improvement").

## What does NOT change from R278

- The finding that reactive redundancy (B) is WORSE than single-path (A) — still valid
- The finding that prediction (C or D) outperforms no prediction (A or B) — still valid
- The honest labeling: model-vs-model comparison, NOT clinical evidence

## Constitutional compliance

- **Article XXX:** The simulator was NOT tuned to make C win. D and E use the same physics, same occlusion model, same sensor noise. The result is the result.
- **Article XXXI:** V1.0 (R277) and V1.1 (R278) preserved in git history. V1.2 documents what changed: added D and E arms, ran attacks, found that C does NOT outperform D.
- **Article XXVIII:** The result determines the claim. The original "predictive isolation" claim is NOT supported. P-01 must be reformulated. This is self-correction at the value-proposition level — exactly what the loop is designed to do.

## What needs to happen next (R280)

1. **Decide: Path 1 (drop isolation, become D) or Path 2 (reposition isolation for infection/maintenance).** This is a strategic decision, not a coding decision.
2. **If Path 1:** Update P-01 TTP to reflect "predictive closed-loop multi-segment controller" (Arm D). Assess IP position vs US20210338992A1. The differentiation narrows to "multi-segment hardware + specific control law."
3. **If Path 2:** Build a new simulator for infection/biofilm scenarios. Test whether isolation helps infection control. This is a new research direction.
4. **Either way:** The buyer materials must be updated to reflect the honest finding. The R278 one-pager is now stale — it claimed "7-9x improvement" which is only true vs A (conventional), not vs D (strongest baseline).
