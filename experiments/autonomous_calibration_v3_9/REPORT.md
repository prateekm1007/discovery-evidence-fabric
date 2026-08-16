# V3.9 Report

**Status**: `CALIBRATION_BLOCKED`

## V3.8 Frozen
| Metric | Value |
|---|---|
| Accuracy | 50% |
| False-reject | 50% |
| 103 accuracy | 70% |

## V3.9 Metrics
| Metric | Value | Threshold | Pass |
|---|---|---|---|
| overall_accuracy | 15.0% | >=85% | ✗ |
| false_elite_rate | 0.0% | <=10% | ✓ |
| false_reject_rate | 75.0% | <=10% | ✗ |
| cited_art_recall | 100.0% | >=90% | ✓ |
| search_recall | 78.6% | >=80% | ✗ |
| 102_accuracy | 85.0% | >=85% | ✓ |
| 103_accuracy | 75.0% | >=80% | ✗ |
| 103_precision | 83.3% | >=85% | ✗ |

| hindsight_high | 0 | — | — |
| hindsight_medium | 3 | — | — |
| hindsight_low | 17 | — | — |
| evidence_found | 18/20 | — | — |
| motivation_bridge_complete | 18/20 | — | — |
| compatibility_conflicting | 0/20 | — | — |
| expectation_reasonable | 18/20 | — | — |
| mere_aggregation | 2/20 | — | — |
| 103_tp | 15 | 103_fp | 3 | 103_fn | 2 | 103_tn | 0 |

**Overall: `CALIBRATION_BLOCKED`**

## Per-Case
| Case | GT | Predicted | Correct? |
|---|---|---|---|
| CV2_G_01 | SURVIVED | REJECT | ✗ |
| CV2_G_02 | SURVIVED | REJECT | ✗ |
| CV2_G_03 | SURVIVED | REJECT | ✗ |
| CV2_G_04 | SURVIVED | REJECT | ✗ |
| CV2_G_05 | SURVIVED | REJECT | ✗ |
| CV2_G_06 | SURVIVED | REJECT | ✗ |
| CV2_G_07 | SURVIVED | REJECT | ✗ |
| CV2_G_08 | SURVIVED | REJECT | ✗ |
| CV2_G_09 | SURVIVED | REJECT | ✗ |
| CV2_G_10 | SURVIVED | REJECT | ✗ |
| CV2_A_01 | REJECTED | REJECT | ✓ |
| CV2_A_02 | REJECTED | REJECT | ✓ |
| CV2_A_03 | REJECTED | REJECT | ✓ |
| CV2_A_04 | REJECTED | PROMISING | ✗ |
| CV2_A_05 | REJECTED | PROMISING | ✗ |
| CV2_M_01 | AMENDED | REJECT | ✗ |
| CV2_M_02 | AMENDED | REJECT | ✗ |
| CV2_M_03 | AMENDED | REJECT | ✗ |
| CV2_M_04 | AMENDED | REJECT | ✗ |
| CV2_M_05 | AMENDED | REJECT | ✗ |

DO NOT RUN 50→5. STOP FOR CEO AUDIT.