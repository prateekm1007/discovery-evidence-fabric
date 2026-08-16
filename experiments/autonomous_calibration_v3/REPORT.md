# Autonomous Calibration V3 — Report

**Protocol SHA-256**: `b1325ed8519e0db275687726e24606f8eb2825c59e45720e51e1ffa502e8cc73`
**Run timestamp**: 2026-08-16T19:27:52.899759+00:00
**Base commit**: d942366
**Status**: `CALIBRATION_BLOCKED`

## Why V3

V2 judged claims without performing the actual search → evidence → claim mapping → 102 → 103 pipeline. V3 runs the REAL autonomous loop end-to-end.

## V2 Frozen (preserved, not overwritten)

| Metric | Value |
|---|---|
| Accuracy | 45% |
| False-elite rate | 5% |
| False-reject rate | 50% |
| Cited-art recall | 100% |
| Status | CALIBRATION_BLOCKED |

## V3 Metrics

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Overall accuracy | 65.0% | ≥85% | ✗ |
| False-elite rate | 10.0% | ≤10% | ✓ |
| False-reject rate | 10.0% | ≤10% | ✓ |
| Cited-art recall | 100.0% | ≥90% | ✓ |
| Search recall | 70.4% | ≥80% | ✗ |
| 102 accuracy | 75.0% | — | — |
| 103 accuracy | 15.0% | — | — |
| Search failure rate | 0.0% | — | — |
| Evaluator failure rate | 0.0% | — | — |
| Rescue recognition | 100.0% | — | — |
| Elite precision | 0.0% | — | — |
| Elite recall | 0.0% | — | — |
| Insufficient evidence cases | 0/20 | — | — |

**Overall: `CALIBRATION_BLOCKED`**

## Per-Case Results

| Case | Patent | GT | Predicted | Correct? | Error |
|---|---|---|---|---|---|
| CV2_G_01 | US11912894B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_02 | US10919033B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_03 | US11747519B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_04 | US12350407B2 | SURVIVED | REJECT | ✗ | FALSE_REJECT |
| CV2_G_05 | US10448970B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_06 | US4610256A | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_07 | AU2021204165B2 | SURVIVED | REJECT | ✗ | FALSE_REJECT |
| CV2_G_08 | CN110461375B | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_09 | US12534549B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_10 | EP3397675B1 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_A_01 | US20030000656A1 | REJECTED | STRONG | ✗ | FALSE_ELITE |
| CV2_A_02 | US20110215414A1 | REJECTED | STRONG | ✗ | FALSE_ELITE |
| CV2_A_03 | US20180243492A1 | REJECTED | PROMISING | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_04 | US20090131732A1 | REJECTED | PROMISING | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_05 | US20080216841A1 | REJECTED | PROMISING | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_M_01 | CN110358006B | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_02 | CN108137841B | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_03 | CN110448287B | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_04 | US12350407B2 | AMENDED | PROMISING | ✓ | CORRECT |
| CV2_M_05 | US11747519B2 | AMENDED | PROMISING | ✓ | CORRECT |

## Error Analysis

- **MODEL_JUDGMENT_FAILURE**: 5 cases
  - Cases: CV2_A_01, CV2_A_02, CV2_A_03, CV2_A_04, CV2_A_05
- **102_FAILURE**: 2 cases
  - Cases: CV2_G_04, CV2_G_07

## Generator/Evaluator Separation

Each case used 5 distinct computational roles with distinct prompts:

- **GENERATOR** — prompt_hash=`b1329becef4c1c4e...`
- **SEARCHER** — prompt_hash=`0516a31de75a551e...`
- **NOVELTY_ADVERSARY** — prompt_hash=`d685ed68b45bf56a...`
- **OBVIOUSNESS_ADVERSARY** — prompt_hash=`9b1d43da9f9b1dda...`
- **FINAL_ADJUDICATOR** — prompt_hash=`177e7d7cfee90b24...`

## Claim-Only Path Status

Claim-only path taken: **0 / 20** (must be 0)
Search-insufficient outcomes: 0 / 20

## Anti-Hindsight

- HIGH confidence (no hindsight): 7
- MEDIUM confidence: 13
- LOW confidence (possible hindsight): 0

## Stop Condition

DO NOT RUN 50→5.

Only after V3 passes the preregistered calibration gate: `UNBLOCK_50_TO_5`.

Otherwise: `CALIBRATION_BLOCKED`.

STOP FOR CEO AUDIT.