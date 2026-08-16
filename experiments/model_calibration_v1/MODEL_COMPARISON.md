# Model Comparison: Gemma vs Nemotron

## Metrics Comparison

| Metric | Gemma 4 31B | Nemotron 3.5 Lightning 30B | Delta |
|---|---|---|---|
| overall_accuracy | 15.0% | 75.0% | +60.0pp |
| false_elite_rate | 0.0% | 10.0% | +10.0pp |
| false_reject_rate | 75.0% | 0.0% | -75.0pp |
| 102_accuracy | 85.0% | 85.0% | +0.0pp |
| 103_accuracy | 75.0% | 15.0% | -60.0pp |
| 103_precision | 83.3% | 0.0% | -83.3pp |
| 103_recall | 88.2% | 0.0% | -88.2pp |
| hindsight_high | 0.0% | 0.0% | +0.0pp |

| 103_tp | 15 | 0 | -15 |
| 103_fp | 3 | 0 | -3 |
| 103_fn | 2 | 17 | +15 |
| 103_tn | 0 | 3 | +3 |

## Per-Case Comparison

| Case | GT | Gemma | Nemotron | Gemma✓? | Nemotron✓? |
|---|---|---|---|---|---|
| CV2_G_01 | SURVIVED | REJECT | STRONG | ✗ | ✓ |
| CV2_G_02 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_03 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_04 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_05 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_06 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_07 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_08 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_09 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_G_10 | SURVIVED | REJECT | PROMISING | ✗ | ✓ |
| CV2_A_01 | REJECTED | REJECT | STRONG | ✓ | ✗ |
| CV2_A_02 | REJECTED | REJECT | STRONG | ✓ | ✗ |
| CV2_A_03 | REJECTED | REJECT | PROMISING | ✓ | ✗ |
| CV2_A_04 | REJECTED | PROMISING | PROMISING | ✗ | ✗ |
| CV2_A_05 | REJECTED | PROMISING | PROMISING | ✗ | ✗ |
| CV2_M_01 | AMENDED | REJECT | PROMISING | ✗ | ✓ |
| CV2_M_02 | AMENDED | REJECT | PROMISING | ✗ | ✓ |
| CV2_M_03 | AMENDED | REJECT | PROMISING | ✗ | ✓ |
| CV2_M_04 | AMENDED | REJECT | PROMISING | ✗ | ✓ |
| CV2_M_05 | AMENDED | REJECT | PROMISING | ✗ | ✓ |

## Key Findings

1. **Accuracy**: Gemma=15.0%, Nemotron=75.0%
2. **103 accuracy**: Gemma=75.0%, Nemotron=15.0%
3. **103 precision**: Gemma=83.3%, Nemotron=0.0%
4. **False reject**: Gemma=75.0%, Nemotron=0.0%
5. **False elite**: Gemma=0.0%, Nemotron=10.0%

## Analysis

- Nemotron **reduces false rejects** compared to Gemma
- Nemotron **preserves low false elite**