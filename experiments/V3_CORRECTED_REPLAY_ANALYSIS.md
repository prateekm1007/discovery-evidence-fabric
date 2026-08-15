# V3 Corrected Replay Analysis — Historical

Generated: 2026-08-15T07:50:40.464672+00:00

V3 historical root hash: `4d10e01c5c246133`

V3 historical commit: `70f68d3`


**DISCLAIMER: This is a HISTORICAL ANALYSIS. V3 historical artifacts are NOT modified.**

This analysis shows what V3 results WOULD have been under the 8 auditor corrections.


## Corrections Applied

- Correction 7: source hash reconstruction (Phase D packet join)
- Correction 9: boundary pre-filter (conditional + no citation → INSUFFICIENT_EVIDENCE)
- Correction 10: prior-art firewall (non-kill states cannot become PRIOR_ART=KILL)
- Correction 11: evidence→adversarial ordering (skip adversarial if evidence fails)
- Correction 6: ADVERSARIAL_INVALID disposition
- Correction 8: preliminary M0 promotion rule

## Original V3 Result

- Winner: **NO_WINNER**
- Reason: M4 does not exceed either control (M4B=0.01, M4C=0.03, M4=0.0). No recursive lift detected.

| Arm | Original AICs | Original AIC Yield |
|-----|--------------|-------------------|
| M0 | 5 | 0.0500 |
| M1 | 0 | 0.0000 |
| M2 | 0 | 0.0000 |
| M3 | 0 | 0.0000 |
| M4 | 0 | 0.0000 |
| M4B | 1 | 0.0100 |
| M4C | 3 | 0.0300 |

## Corrected Replay Result

| Arm | Corrected AICs | Corrected AIC Yield | Original AICs | Yield Delta | Corrections Applied |
|-----|----------------|--------------------|--------------|-------------|--------------------|
| M0 | 60 | 0.6000 | 5 | +0.5500 | 95 |
| M1 | 67 | 0.6700 | 0 | +0.6700 | 100 |
| M2 | 57 | 0.5700 | 0 | +0.5700 | 99 |
| M3 | 54 | 0.5400 | 0 | +0.5400 | 99 |
| M4 | 64 | 0.6400 | 0 | +0.6400 | 100 |
| M4B | 58 | 0.5800 | 1 | +0.5700 | 99 |
| M4C | 56 | 0.5600 | 3 | +0.5300 | 94 |

### Corrected Winner

- Outcome: **NO_WINNER**
- Reason: Best arm M1 does not meet lift (3.0pp < 5pp) or significance (adj_p=0.0000 >= 0.05)
- Lift: 3.0pp
- Adjusted p: 4e-05

## Correction Breakdown

| Arm | Prior-Art Firewall | Boundary Pre-filter | Adversarial Invalid | Evidence Blocked |
|-----|-------------------|--------------------|--------------------|-----------------|
| M0 | 38 | 77 | 18 | 6 |
| M1 | 82 | 70 | 40 | 5 |
| M2 | 69 | 82 | 37 | 7 |
| M3 | 46 | 83 | 23 | 7 |
| M4 | 60 | 79 | 28 | 5 |
| M4B | 34 | 87 | 22 | 9 |
| M4C | 37 | 83 | 17 | 6 |

## Difference Analysis

| Arm | Original Yield | Corrected Yield | Delta | AIC Delta |
|-----|---------------|----------------|-------|-----------|
| M0 | 0.0500 | 0.6000 | +0.5500 | +55 |
| M1 | 0.0000 | 0.6700 | +0.6700 | +67 |
| M2 | 0.0000 | 0.5700 | +0.5700 | +57 |
| M3 | 0.0000 | 0.5400 | +0.5400 | +54 |
| M4 | 0.0000 | 0.6400 | +0.6400 | +64 |
| M4B | 0.0100 | 0.5800 | +0.5700 | +57 |
| M4C | 0.0300 | 0.5600 | +0.5300 | +53 |

## Replay Root Hash
`e55a6ba49a7c2a09`
