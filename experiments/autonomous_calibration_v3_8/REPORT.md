# V3.8 Report

**Status**: `CALIBRATION_BLOCKED`

## Metrics
| Metric | Value | Threshold | Pass |
|---|---|---|---|
| overall_accuracy | 50.0% | >=85% | ✗ |
| false_elite_rate | 0.0% | <=10% | ✓ |
| false_reject_rate | 50.0% | <=10% | ✗ |
| cited_art_recall | 100.0% | >=90% | ✓ |
| search_recall | 78.6% | >=80% | ✗ |
| 102_accuracy | 85.0% | >=85% | ✓ |
| 103_accuracy | 70.0% | >=80% | ✗ |

| hindsight_high | 0 | — | — |
| hindsight_medium | 5 | — | — |
| hindsight_low | 15 | — | — |
| avg_motivation_edges | 4.25 | — | — |
| avg_expectation_edges | 2.0 | — | — |

## Per-Case
| Case | GT | Predicted | Correct? |
|---|---|---|---|
| CV2_G_01 | SURVIVED | STRONG | ✓ |
| CV2_G_02 | SURVIVED | REJECT | ✗ |
| CV2_G_03 | SURVIVED | PROMISING | ✓ |
| CV2_G_04 | SURVIVED | REJECT | ✗ |
| CV2_G_05 | SURVIVED | PROMISING | ✓ |
| CV2_G_06 | SURVIVED | REJECT | ✗ |
| CV2_G_07 | SURVIVED | REJECT | ✗ |
| CV2_G_08 | SURVIVED | REJECT | ✗ |
| CV2_G_09 | SURVIVED | REJECT | ✗ |
| CV2_G_10 | SURVIVED | REJECT | ✗ |
| CV2_A_01 | REJECTED | REJECT | ✓ |
| CV2_A_02 | REJECTED | REJECT | ✓ |
| CV2_A_03 | REJECTED | REJECT | ✓ |
| CV2_A_04 | REJECTED | REJECT | ✓ |
| CV2_A_05 | REJECTED | REJECT | ✓ |
| CV2_M_01 | AMENDED | REJECT | ✗ |
| CV2_M_02 | AMENDED | REJECT | ✗ |
| CV2_M_03 | AMENDED | PROMISING | ✓ |
| CV2_M_04 | AMENDED | REJECT | ✗ |
| CV2_M_05 | AMENDED | PROMISING | ✓ |

DO NOT RUN 50→5. STOP FOR CEO AUDIT.