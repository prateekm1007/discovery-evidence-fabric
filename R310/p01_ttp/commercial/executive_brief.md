# Executive Brief — P-01

**Candidate:** P-01 — Predictive Occlusion-Isolation Controller
**For:** Buyer executive (1-page brief)

---

## What it is

A control law for a multi-segment CSF shunt that predicts impending catheter obstruction and pre-emptively redistributes drainage to healthy segments, maintaining two safety invariants simultaneously (global ICP in band + no path overloaded).

## Why it matters

Catheter obstruction causes 30-50% of shunt failures. Current shunts are reactive — they fail, then the patient needs emergency surgery. P-01 predicts failure hours to days ahead and prevents it.

## What has actually been demonstrated

- **Reference implementation complete:** Python simulator, 25 scenarios reproducible
- **225 ablations + 180 comparisons:** rate-limiting confirmed as critical mechanism in 41/45 runs
- **Honest falsification (Article XV):** the strict dual-invariant claim was FALSIFIED by the simulator. Peak ICP reaches 22 mmHg (vs. 20 mmHg target). Both P-01 and baseline fail 24h survival.
- **Partial improvement confirmed:** multi-segment peak 22 mmHg vs. baseline 59 mmHg. INV-2 preserved 5/5.

## What failed

- The strict dual-invariant claim (INV-1 violated by ~2 mmHg)
- The 24h survival claim (both designs break at ~14h)
- The initial R277 audit overclaimed "survival 5/5" — corrected after re-analyzing actual data

## What remains uncertain

- 30% revision rate reduction is MODELLED, not measured
- Implantable flow sensor does not exist commercially (blocking unknown for V1)
- No clinical data exists
- Simulator has not been confirmed on hardware

## How an engineer can reproduce it

See `transfer/reproduction.md`. A competent engineer can reproduce the simulator results in < 60 seconds on a standard laptop. V0 bench prototype buildable in 3-6 months with $3-5K COTS components.

## What would falsify it

- V0 bench prototype fails to reproduce the simulator's partial improvement
- Clinical trial shows revision rate reduction < 15%
- Implantable flow sensor cannot be developed at viable cost

## What economic problem it solves

Shunt revision surgery costs $35K-$50K per procedure. At 30% reduction (MODELLED), P-01 creates $2.15M-$5.5M net annual value per 1000 patients. Path to PUBLICLY_VERIFIED requires clinical data (4-8 years, $20-50M).

## What exactly is being transferred

- Complete technology-transfer package (this folder)
- Reference implementation + simulator code + raw results
- V0 bench prototype design
- Tuned parameters (know-how, under NDA)
- Engineering consultation during V0/V1 development

Rights differentiated by price (R275): same evidence at every tier; price changes rights and scope, not evidence quality.

## The honest bottom line

P-01 is a designed and partially-validated control law with a real partial improvement (peak ICP, INV-2 preservation) and honest limitations (no 24h survival, no clinical data, implantable flow sensor unknown). It is ready for V0 bench prototype evaluation. It is NOT ready for clinical use.
