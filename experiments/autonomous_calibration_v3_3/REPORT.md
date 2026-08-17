# Autonomous Calibration V3.3 — Report

**Protocol SHA-256**: `1c609a013f80dbaa541a8b279064f7511b96333e912bb14542016e76a15af27b`
**Run timestamp**: 2026-08-16T19:55:24.195627+00:00
**Base commit**: 38df888
**Status**: `CALIBRATION_BLOCKED`

## Why V3.3

V3.2 had critical defects: CLAIM_IDENTITY_FAILURE (CV2_A_01/CV2_A_02), 103_FAILURE (15% accuracy), SEARCH_FAILURE (70% recall). V3.3 fixes these with claim identity validation, rebuilt 103, and search recall audit.

## V3.2 Frozen (preserved)

| Metric | Value |
|---|---|
| Accuracy | 65% |
| False-elite rate | 10% |
| False-reject rate | 10% |
| Cited-art recall | 100% |
| Search recall | 70% |
| 102 accuracy | 75% |
| 103 accuracy | 15% |
| Status | CALIBRATION_BLOCKED |

## V3.3 Metrics

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Overall accuracy | 60.0% | ≥85% | ✗ |
| False-elite rate | 0.0% | ≤10% | ✓ |
| False-reject rate | 20.0% | ≤10% | ✗ |
| Cited-art recall | 100.0% | ≥90% | ✓ |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 60.0% | ≥85% | ✗ |
| 103 accuracy | 15.0% | ≥80% | ✗ |
| Hindsight HIGH | 0 | — | — |
| Identity confirmed | 20/20 | — | — |
| Identity mismatch | 0/20 | — | — |
| Evidence corrupted | 0/20 | — | — |
| Rescue recognition | 80.0% | — | — |

**Overall: `CALIBRATION_BLOCKED`**

## Per-Case Results

| Case | Patent | GT | Predicted | Identity | Correct? | Error |
|---|---|---|---|---|---|---|
| CV2_G_01 | US11912894B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_02 | US10919033B2 | SURVIVED | REJECT | IDENTITY_CONFIRMED | ✗ | FALSE_REJECT |
| CV2_G_03 | US11747519B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_04 | US12350407B2 | SURVIVED | REJECT | IDENTITY_CONFIRMED | ✗ | FALSE_REJECT |
| CV2_G_05 | US10448970B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_06 | US4610256A | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_07 | AU2021204165B2 | SURVIVED | REJECT | IDENTITY_CONFIRMED | ✗ | FALSE_REJECT |
| CV2_G_08 | CN110461375B | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_09 | US12534549B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_10 | EP3397675B1 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_A_01 | US20030000656A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_02 | US20110215414A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_03 | US20180243492A1 | REJECTED | REJECT | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_A_04 | US20090131732A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_05 | US20080216841A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_M_01 | CN110358006B | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_M_02 | CN108137841B | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_M_03 | CN110448287B | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_M_04 | US12350407B2 | AMENDED | REJECT | IDENTITY_CONFIRMED | ✗ | FALSE_REJECT |
| CV2_M_05 | US11747519B2 | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |

## Error Analysis

- **102_FAILURE**: 7 cases
  - Cases: CV2_G_02, CV2_G_04, CV2_G_07, CV2_A_01, CV2_A_02, CV2_A_04, CV2_M_04
- **103_FAILURE**: 1 cases
  - Cases: CV2_A_05

## V3.3 Fixes Applied

1. **CLAIM_IDENTITY_VALIDATION**: 
   - Confirmed: 20/20
   - Mismatch: 0/20
   - Unresolved: 0/20
   - Cases stopped (EVIDENCE_CORRUPTED): 0/20

2. **103 Rebuild**: COULD≠WOULD rule, explicit evidence object, two-pass anti-hindsight, combination matrix
   - 103 accuracy: 15.0% (V3.2 was 15%)
   - Hindsight HIGH: 0
   - Hindsight MEDIUM: 3
   - Hindsight LOW: 10

3. **Search Recall Audit**: See SEARCH_RECALL_ANALYSIS.json

## Stop Condition

DO NOT RUN 50→5.

Only after V3.3 passes all thresholds including 102≥85% and 103≥80%: `UNBLOCK_50_TO_5`.

Otherwise: `CALIBRATION_BLOCKED`.

STOP FOR CEO AUDIT.