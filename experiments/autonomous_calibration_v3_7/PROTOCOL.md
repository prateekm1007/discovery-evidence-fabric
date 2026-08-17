# V3.7 PROTOCOL — Pre-Filing Motivation Graph + Hindsight Diagnostic

**Status**: `CALIBRATION_BLOCKED` (pre-registered, frozen before inference)
**Base commit**: `0f36316`
**Protocol SHA-256**: `a4a4173943144bae6505cffb399962a4ec306ec74ac605964b2046563f84ebf4`

## V3.6 Frozen
| Metric | Value |
|---|---|
| Accuracy | 80% |
| 103 accuracy | 30% |
| Hindsight HIGH | 17/20 |

## V3.7 Key Fix: Hindsight ≠ Evidence Retrieval

V3.6 conflated "evidence found after search" with "evidence not available pre-filing."
V3.7 separates these with PreFilingEvidence object + fixed hindsight test.

## Acceptance Gate
| Metric | Threshold |
|---|---|
| Overall accuracy | ≥ 85% |
| False-elite | ≤ 10% |
| False-reject | ≤ 10% |
| 102 accuracy | ≥ 85% |
| 103 accuracy | ≥ 80% |

## Stop Condition
DO NOT RUN 50→5. STOP FOR CEO AUDIT.
