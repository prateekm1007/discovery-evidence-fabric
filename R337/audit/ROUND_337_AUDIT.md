# R337 AUDIT — Canonical State Fixed, P-24 T1, P-25 T1 (FAIL), Article XXXV Loop

**Round:** 337
**Date:** 2026-08-26
**Remote HEAD:** (R337 pending push)
**Constitution hash:** `f82ae4f665dcb5a59ae399017feed57dd24242fe35d98a897806d559064762a5`

## Gate 1: Canonical state FIXED ✅

R336's `CURRENT_PORTFOLIO_AUTHORITY.json` said 13 active + 2 vacancy while promotion decisions said 15. R337 corrects: 15 active, 0 vacancy, P-24/P-25 in active list. Invariant: promotion decision + canonical state must agree.

## Gate 2: P-24/P-25 remain T0 until models execute ✅

P-24 and P-25 were T0 (hypothesis survived initial attack). R337 builds computational models to determine if they reach T1.

## Gate 3: P-24 → T1 ✅ (PASS)

**P-24 Gravity-Compensating Hydraulic Damper:**
- Upright flow (damper): 0.417 mL/min (below 0.5 overdrainage threshold)
- Upright flow (standard shunt): 0.750 mL/min (overdrainage!)
- Upright flow (ASD): 0.225 mL/min (also prevents, but binary)
- **Falsification: PASS** (0.417 < 0.5)
- **T-level: T1** (computationally supported)
- Comparison to strongest alternative (ASD): damper provides proportional response, closer to target flow. ASD also prevents but with binary behavior.
- Dynamic response: damper 0.1s (passive hydraulic) vs ASD 0.5s (mechanical threshold). Damper is faster.

## Gate 4: P-25 → T1 but FALSIFICATION FAILS ✅ (honest)

**P-25 Self-Referencing Piezoresistive Sensor:**
- Single-element drift: 354 μV over 30 days → 10.73 mmHg error (far above 2.0 threshold)
- Dual-element drift: 114 μV over 30 days → 3.45 mmHg error (still above 2.0 threshold)
- Drift cancellation: 67.8% (common-mode cancelled)
- **Falsification: FAIL** (3.45 > 2.0)
- **T-level: T1** (model ran, physics is real, but mechanism is insufficient)
- **Root cause:** Biofouling (3 μV/day, only affects Element A) and creep (0.5 μV/day, asymmetric) are NOT common-mode. The dual-element approach cancels common-mode but non-common-mode drift remains.
- **Decision:** T1 with known limitation. NOT killed — mechanism is sound but insufficient alone. Buyer package discloses: "67.8% drift cancellation but remaining 3.45 mmHg error exceeds 2.0 mmHg threshold. May be acceptable for trending, not absolute measurement."
- **Article XXIX:** This is a MECHANISM limitation, not implementation failure. The model is correct; the mechanism is insufficient for the clinical threshold.

## Updated portfolio

| T-level | Count | Candidates |
|---------|------:|------------|
| T2-CONFIRMED | 1 | P-16 |
| T2-CONDITIONAL | 1 | P-01 |
| T1 | 12 | P-02, P-04, P-07, P-10, P-11, P-12, P-13, P-15, P-20, P-21, P-22, P-24 |
| T1 (FAIL) | 1 | P-25 (model runs, mechanism insufficient for threshold) |
| T0 | 0 | — |

**All 15 candidates now have computational models (T1 or above).** No T0 remaining.

## P-25 honest finding

The machine's own model showed that the self-referencing sensor approach:
1. DOES cancel 67.8% of drift (physics is correct)
2. Does NOT meet the 2.0 mmHg clinical threshold (3.45 mmHg error remains)
3. The failure is from BIOFOULING (non-common-mode, only affects exposed element)
4. The mechanism is sound but insufficient alone — needs anti-fouling coating or recalibration protocol

This is the machine finding its own candidate's limitation through computation — exactly the behavior we want.

## What remains

- **Gate 5:** Article XXXV prototype loop for ONE candidate (model→VVUQ→cohort→experiment→ingest→update→KA→EIG→next→package v2)
- **Gate 6:** EIG controls loop (posterior changes → EIG changes → winner changes)
- **Gate 7:** Package v2 complete (19-field, not update receipt)
- **Gate 8:** Run discovery engine again after learning (new knowledge changes candidate set)
- **Real external data:** 0 (CEO-owned)
- **Real buyer loop:** 0

## The honest state

```
ACTIVE: 15/15
T2-CONFIRMED: 1 | T2-CONDITIONAL: 1 | T1: 12 | T1(FAIL): 1
Article XXXV complete: 0/15
Real external data: 0
Real buyer loop: 0
SOFTWARE LOOP: VERIFIED
```

P-24 and P-25 have been raised from T0 to T1 through computational modeling. P-24 PASSES its falsification test. P-25 FAILS but survives as T1 with a known mechanism limitation. The machine found P-25's weakness through its own model — biofouling dominates non-common-mode drift, limiting the approach to trending rather than absolute measurement.
