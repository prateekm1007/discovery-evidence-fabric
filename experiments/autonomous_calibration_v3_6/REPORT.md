# Autonomous Calibration V3.6 — Report

**Protocol SHA-256**: `c33b89c48d086f6da8e374a0df705c2cbc0de4400f83143cca717b1c2b71c7c1`
**Run timestamp**: 2026-08-16T21:09:56.521590+00:00
**Base commit**: 1b5a8ca
**Status**: `CALIBRATION_BLOCKED`

## Why V3.6

V3.5 root cause: motivation_insufficient=85%, expectation_insufficient=90%. V3.6 fixes the evidence model with edge-based graphs, 12 motivation types, 8 expectation types, and better models (gemma-4-31b-it).

## V3.5 Frozen

| Metric | Value |
|---|---|
| Accuracy | 75% |
| 103 accuracy | 25% |
| Motivation insufficient | 85% |
| Expectation insufficient | 90% |

## V3.6 Metrics

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Overall accuracy | 80.0% | ≥85% | ✗ |
| False-elite rate | 0.0% | ≤10% | ✓ |
| False-reject rate | 5.0% | ≤10% | ✓ |
| Cited-art recall | 100.0% | ≥90% | ✓ |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 85.0% | ≥85% | ✓ |
| 103 accuracy | 30.0% | ≥80% | ✗ |
| Motivation evidence recall | 17.6% | ≥80% | ✗ |
| Expectation evidence recall | 17.6% | ≥80% | ✗ |
| Motivation graph completeness | 1.2 | — | — |
| Expectation graph completeness | 1.75 | — | — |
| Hindsight HIGH | 17 | — | — |
| Hindsight MEDIUM | 1 | — | — |
| Hindsight LOW | 2 | — | — |

**Overall: `CALIBRATION_BLOCKED`**

## Motivation Evidence Types Distribution

- COMPATIBILITY_SAME_FUNCTION: 3
- COST_SIZE_SPEED_SAFETY_INCENTIVE: 3
- REGULATORY_ENGINEERING_CONSTRAINT: 3
- PREDICTABLE_SUBSTITUTION: 2
- KNOWN_PROBLEM: 2
- MARKET_FORCE: 2
- PERFORMANCE_IMPROVEMENT: 2
- KNOWN_TRADEOFF: 2
- EXPLICIT_REFERENCE_CROSS_LINK: 2
- REFERENCE_TEACHING: 1
- DESIGN_INCENTIVE: 1
- COMMON_GENERAL_KNOWLEDGE: 1

## Expectation Evidence Types Distribution

- SAME_FUNCTION_SAME_FIELD: 7
- PREDICTABLE_ENGINEERING_RESULT: 6
- KNOWN_COMPATIBLE_MECHANISM: 6
- SAME_OPERATING_REGIME: 5
- DEMONSTRATED_COMPATIBILITY: 5
- ESTABLISHED_SUBSTITUTION: 4
- COMMON_GENERAL_KNOWLEDGE: 2

## Per-Case Results

| Case | Patent | GT | Predicted | Mot | Exp | Correct? |
|---|---|---|---|---|---|---|
| CV2_G_01 | US11912894B2 | SURVIVED | REJECT | 9 | 10 | ✗ |
| CV2_G_02 | US10919033B2 | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_03 | US11747519B2 | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_04 | US12350407B2 | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_05 | US10448970B2 | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_06 | US4610256A | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_07 | AU2021204165B2 | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_08 | CN110461375B | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_09 | US12534549B2 | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_G_10 | EP3397675B1 | SURVIVED | PROMISING | 0 | 0 | ✓ |
| CV2_A_01 | US20030000656A1 | REJECTED | REJECT | 1 | 8 | ✓ |
| CV2_A_02 | US20110215414A1 | REJECTED | REJECT | 14 | 17 | ✓ |
| CV2_A_03 | US20180243492A1 | REJECTED | PROMISING | 0 | 0 | ✗ |
| CV2_A_04 | US20090131732A1 | REJECTED | PROMISING | 0 | 0 | ✗ |
| CV2_A_05 | US20080216841A1 | REJECTED | PROMISING | 0 | 0 | ✗ |
| CV2_M_01 | CN110358006B | AMENDED | PROMISING | 0 | 0 | ✓ |
| CV2_M_02 | CN108137841B | AMENDED | PROMISING | 0 | 0 | ✓ |
| CV2_M_03 | CN110448287B | AMENDED | PROMISING | 0 | 0 | ✓ |
| CV2_M_04 | US12350407B2 | AMENDED | PROMISING | 0 | 0 | ✓ |
| CV2_M_05 | US11747519B2 | AMENDED | PROMISING | 0 | 0 | ✓ |

## Stop Condition

DO NOT RUN 50→5. STOP FOR CEO AUDIT.