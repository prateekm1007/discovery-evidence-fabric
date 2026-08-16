# Autonomous Calibration V3.7 — Report

**Protocol SHA-256**: `a4a4173943144bae6505cffb399962a4ec306ec74ac605964b2046563f84ebf4`
**Run timestamp**: 2026-08-16T21:36:00.787832+00:00
**Status**: `CALIBRATION_BLOCKED`

## V3.7 Key Fix: Hindsight ≠ Evidence Retrieval

V3.6 had 17/20 HIGH hindsight because it conflated 'evidence found after search' with 'evidence not available pre-filing'. V3.7 fixes this with PreFilingEvidence object and fixed hindsight test.

## V3.6 Frozen

| Metric | Value |
|---|---|
| Accuracy | 80% |
| 103 accuracy | 30% |
| Hindsight HIGH | 17/20 |

## V3.7 Metrics

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Overall accuracy | 80.0% | ≥85% | ✗ |
| False-elite rate | 0.0% | ≤10% | ✓ |
| False-reject rate | 5.0% | ≤10% | ✓ |
| Cited-art recall | 100.0% | ≥90% | ✓ |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 85.0% | ≥85% | ✓ |
| 103 accuracy | 30.0% | ≥80% | ✗ |
| Hindsight HIGH | 17 | — | — |
| Hindsight MEDIUM | 3 | — | — |
| Hindsight LOW | 0 | — | — |
| Counterfactual STRONG | 3 | — | — |
| Counterfactual MEDIUM | 0 | — | — |
| Avg pre-date motivation edges | 0.15 | — | — |
| Avg pre-date expectation edges | 0.15 | — | — |

**Overall: `CALIBRATION_BLOCKED`**

## Per-Case Results

| Case | GT | Predicted | Hindsight | Correct? |
|---|---|---|---|---|
| CV2_G_01 | SURVIVED | REJECT | MEDIUM | ✗ |
| CV2_G_02 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_03 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_04 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_05 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_06 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_07 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_08 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_09 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_G_10 | SURVIVED | PROMISING | HIGH | ✓ |
| CV2_A_01 | REJECTED | REJECT | MEDIUM | ✓ |
| CV2_A_02 | REJECTED | REJECT | MEDIUM | ✓ |
| CV2_A_03 | REJECTED | PROMISING | HIGH | ✗ |
| CV2_A_04 | REJECTED | PROMISING | HIGH | ✗ |
| CV2_A_05 | REJECTED | PROMISING | HIGH | ✗ |
| CV2_M_01 | AMENDED | PROMISING | HIGH | ✓ |
| CV2_M_02 | AMENDED | PROMISING | HIGH | ✓ |
| CV2_M_03 | AMENDED | PROMISING | HIGH | ✓ |
| CV2_M_04 | AMENDED | PROMISING | HIGH | ✓ |
| CV2_M_05 | AMENDED | PROMISING | HIGH | ✓ |

## Stop Condition
DO NOT RUN 50→5. STOP FOR CEO AUDIT.