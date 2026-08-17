# Autonomous Calibration V3.4 — Report

**Protocol SHA-256**: `80ea371692acd1eec178b34ad113049f4cc10ddff707a0c2eddf678904db483f`
**Run timestamp**: 2026-08-16T20:18:02.513944+00:00
**Base commit**: 1e93a51
**Status**: `CALIBRATION_BLOCKED`

## Why V3.4

V3.3 had 102_FAILURE (7 cases) and 103_FAILURE (15% accuracy). V3.4 fixes with passage-grounded 102, inherency firewall, arrangement firewall, and independent 103 with COULD/WOULD rule.

## V3.3 Frozen (True Numbers)

| Metric | Value |
|---|---|
| Accuracy | 60% |
| False-elite rate | 0% |
| False-reject rate | 20% |
| Cited-art recall | 100% |
| Search recall | 78.6% |
| 102 accuracy | 60% |
| 103 accuracy | 15% |

## V3.4 Metrics

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Overall accuracy | 75.0% | ≥85% | ✗ |
| False-elite rate | 0.0% | ≤10% | ✓ |
| False-reject rate | 0.0% | ≤10% | ✓ |
| Cited-art recall | 100.0% | ≥90% | ✓ |
| Cited-art mapping accuracy | 0.0% | — | — |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 85.0% | ≥85% | ✓ |
| 103 accuracy | 15.0% | ≥80% | ✗ |
| Hindsight HIGH | 0 | — | — |
| Hindsight MEDIUM | 6 | — | — |
| Hindsight LOW | 1 | — | — |
| Identity confirmed | 20/20 | — | — |
| 102 kill legal | 1 | — | — |
| Rescue recognition | 100.0% | — | — |

**Overall: `CALIBRATION_BLOCKED`**

## Per-Case Results

| Case | Patent | GT | Predicted | Identity | Correct? | Error |
|---|---|---|---|---|---|---|
| CV2_G_01 | US11912894B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_02 | US10919033B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_03 | US11747519B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_04 | US12350407B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_05 | US10448970B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_06 | US4610256A | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_07 | AU2021204165B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_08 | CN110461375B | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_09 | US12534549B2 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_G_10 | EP3397675B1 | SURVIVED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_A_01 | US20030000656A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_02 | US20110215414A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_03 | US20180243492A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_04 | US20090131732A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_05 | US20080216841A1 | REJECTED | PROMISING | IDENTITY_CONFIRMED | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_M_01 | CN110358006B | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_M_02 | CN108137841B | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_M_03 | CN110448287B | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_M_04 | US12350407B2 | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |
| CV2_M_05 | US11747519B2 | AMENDED | PROMISING | IDENTITY_CONFIRMED | ✓ | CORRECT |

## Error Analysis

- **102_FAILURE**: 3 cases
  - Cases: CV2_A_01, CV2_A_02, CV2_A_04
- **103_FAILURE**: 2 cases
  - Cases: CV2_A_03, CV2_A_05

## V3.4 Fixes Applied

1. **Passage-Grounded 102**: every limitation requires exact_passage + claim_number + mapping_rationale
   - Allowed: EXPRESS / NECESSARILY_INHERENT / NOT_DISCLOSED / UNCERTAIN
   - Forbidden: POSSIBLE / PLAUSIBLE / TOPICAL / SEMANTICALLY_SIMILAR
   - 102 kill legal: 1 cases

2. **Inherency Firewall**: NECESSARILY_INHERENT requires inherency_necessity_proof
3. **Arrangement Firewall**: A+B disclosed ≠ A+B arranged as claimed
4. **Independent 103**: adversary does NOT receive generator rationale
5. **COULD≠WOULD Rule**: 103 requires COULD=YES AND WOULD=YES AND MOTIVATION AND EXPECTATION
6. **Two-Pass Anti-Hindsight**: Pass A (hide) vs Pass B (reveal)
   - Hindsight HIGH: 0
   - Hindsight MEDIUM: 6
   - Hindsight LOW: 1

## Stop Condition

DO NOT RUN 50→5.

Only after V3.4 passes all thresholds including 102≥85% and 103≥80%: `UNBLOCK_50_TO_5`.

Otherwise: `CALIBRATION_BLOCKED`.

STOP FOR CEO AUDIT.