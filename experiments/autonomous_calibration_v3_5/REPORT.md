# Autonomous Calibration V3.5 — Report

**Protocol SHA-256**: `fc4123790fb5e464a0d1ce17a963549e3bd482b026b8018f9d90c07cc7791325`
**Run timestamp**: 2026-08-16T20:41:06.497682+00:00
**Base commit**: ff3be20
**Status**: `CALIBRATION_BLOCKED`

## Why V3.5

V3.4 achieved 85% 102 accuracy but 103 remained at 15%. V3.5 builds prosecution-grounded 103 forensics to determine WHY the system disagrees with known prosecution outcomes.

## V3.4 Frozen

| Metric | Value |
|---|---|
| Accuracy | 75% |
| False-elite | 0% |
| False-reject | 0% |
| 102 accuracy | 85% |
| 103 accuracy | 15% |

## V3.5 Metrics

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Overall accuracy | 75.0% | ≥85% | ✗ |
| False-elite rate | 0.0% | ≤10% | ✓ |
| False-reject rate | 5.0% | ≤10% | ✓ |
| Cited-art recall | 100.0% | ≥90% | ✓ |
| Cited-103 art recall | 100.0% | — | — |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 85.0% | ≥85% | ✓ |
| 103 accuracy | 25.0% | ≥80% | ✗ |
| Hindsight HIGH | 17 | — | — |
| Hindsight MEDIUM | 1 | — | — |
| Hindsight LOW | 2 | — | — |
| Rescue recognition | 100.0% | — | — |

**Overall: `CALIBRATION_BLOCKED`**

## 103 Motivation Sources Distribution

- MOTIVATION_INSUFFICIENT: 17
- REFERENCE_TEACHING: 2
- ESTABLISHED_ART_KNOWLEDGE: 1

## 103 Expectation Sources Distribution

- EXPECTATION_INSUFFICIENT: 18
- REFERENCE_TEACHING: 2

## 103 Error Classification

- GROUND_TRUTH_EXTRACTION_FAILURE: 3
- FINAL_ADJUDICATION_FAILURE: 1
- REFERENCE_SELECTION_FAILURE: 1

## Per-Case Results

| Case | Patent | GT | Predicted | Correct? | 103 Class |
|---|---|---|---|---|---|
| CV2_G_01 | US11912894B2 | SURVIVED | REJECT | ✗ | FINAL_ADJUDICATION_FAILURE |
| CV2_G_02 | US10919033B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_03 | US11747519B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_04 | US12350407B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_05 | US10448970B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_06 | US4610256A | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_07 | AU2021204165B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_08 | CN110461375B | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_09 | US12534549B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_10 | EP3397675B1 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_A_01 | US20030000656A1 | REJECTED | REJECT | ✓ | CORRECT |
| CV2_A_02 | US20110215414A1 | REJECTED | PROMISING | ✗ | REFERENCE_SELECTION_FAILURE |
| CV2_A_03 | US20180243492A1 | REJECTED | PROMISING | ✗ | GROUND_TRUTH_EXTRACTION_FAILURE |
| CV2_A_04 | US20090131732A1 | REJECTED | PROMISING | ✗ | GROUND_TRUTH_EXTRACTION_FAILURE |
| CV2_A_05 | US20080216841A1 | REJECTED | PROMISING | ✗ | GROUND_TRUTH_EXTRACTION_FAILURE |
| CV2_M_01 | CN110358006B | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_02 | CN108137841B | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_03 | CN110448287B | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_04 | US12350407B2 | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_05 | US11747519B2 | AMENDED | PROMISING | ✓ | CORRECT |

## Stop Condition

DO NOT RUN 50→5. STOP FOR CEO AUDIT.