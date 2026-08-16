# Autonomous Calibration V3 — Report

**Protocol SHA-256**: `b1325ed8519e0db275687726e24606f8eb2825c59e45720e51e1ffa502e8cc73`
**Run timestamp**: 2026-08-16T17:36:06.266318+00:00
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
| Overall accuracy | 33.3% | ≥85% | ✗ |
| False-elite rate | 0.0% | ≤10% | ✓ |
| False-reject rate | 0.0% | ≤10% | ✓ |
| Cited-art recall | 100.0% | ≥90% | ✓ |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 33.3% | — | — |
| 103 accuracy | 0.0% | — | — |
| Search failure rate | 85.0% | — | — |
| Evaluator failure rate | 0.0% | — | — |
| Rescue recognition | 0.0% | — | — |
| Elite precision | 0.0% | — | — |
| Elite recall | 0.0% | — | — |
| Insufficient evidence cases | 17/20 | — | — |

**Overall: `CALIBRATION_BLOCKED`**

## Per-Case Results

| Case | Patent | GT | Predicted | Correct? | Error |
|---|---|---|---|---|---|
| CV2_G_01 | US11912894B2 | SURVIVED | PROMISING | ✓ | CORRECT |
| CV2_G_02 | US10919033B2 | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_03 | US11747519B2 | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_04 | US12350407B2 | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_05 | US10448970B2 | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_06 | US4610256A | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_07 | AU2021204165B2 | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_08 | CN110461375B | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_09 | US12534549B2 | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_G_10 | EP3397675B1 | SURVIVED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_A_01 | US20030000656A1 | REJECTED | PROMISING | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_02 | US20110215414A1 | REJECTED | PROMISING | ✗ | MODEL_JUDGMENT_FAILURE |
| CV2_A_03 | US20180243492A1 | REJECTED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_A_04 | US20090131732A1 | REJECTED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_A_05 | US20080216841A1 | REJECTED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_M_01 | CN110358006B | AMENDED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_M_02 | CN108137841B | AMENDED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_M_03 | CN110448287B | AMENDED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_M_04 | US12350407B2 | AMENDED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |
| CV2_M_05 | US11747519B2 | AMENDED | SEARCH_INSUFFICIENT | ✗ | INSUFFICIENT_EVIDENCE |

## Error Analysis

- **SEARCH_FAILURE**: 17 cases
  - Cases: CV2_G_02, CV2_G_03, CV2_G_04, CV2_G_05, CV2_G_06, CV2_G_07, CV2_G_08, CV2_G_09, CV2_G_10, CV2_A_03, CV2_A_04, CV2_A_05, CV2_M_01, CV2_M_02, CV2_M_03, CV2_M_04, CV2_M_05
- **MODEL_JUDGMENT_FAILURE**: 2 cases
  - Cases: CV2_A_01, CV2_A_02

## Generator/Evaluator Separation

Each case used 5 distinct computational roles with distinct prompts:

- **GENERATOR** — prompt_hash=`b1329becef4c1c4e...`
- **SEARCHER** — prompt_hash=`0516a31de75a551e...`
- **NOVELTY_ADVERSARY** — prompt_hash=`d685ed68b45bf56a...`
- **OBVIOUSNESS_ADVERSARY** — prompt_hash=`9b1d43da9f9b1dda...`
- **FINAL_ADJUDICATOR** — prompt_hash=`177e7d7cfee90b24...`

## Claim-Only Path Status

Claim-only path taken: **0 / 20** (must be 0)
Search-insufficient outcomes: 17 / 20

## Anti-Hindsight

- HIGH confidence (no hindsight): 19
- MEDIUM confidence: 1
- LOW confidence (possible hindsight): 0

## Stop Condition

DO NOT RUN 50→5.

Only after V3 passes the preregistered calibration gate: `UNBLOCK_50_TO_5`.

Otherwise: `CALIBRATION_BLOCKED`.

STOP FOR CEO AUDIT.