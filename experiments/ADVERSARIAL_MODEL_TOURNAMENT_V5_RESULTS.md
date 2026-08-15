# Adversarial Model Tournament V5 Results

Contract: V2 (three-state, neutral)

Root hash: `731993fe632d1631`


## V1→V2 Comparison

| Metric | V1 (binary) | V2 (three-state) |

|--------|-------------|-------------------|

| Kill bias rate | 0.7143 | (see per-model) |

| Avg false kill | 0.6043 | (see per-model) |


## Models Tested: 6

| ID | Model | Status | Det Acc | Coverage | False Kill | False Surv | Abstention | Call Fail |

|---|-------|--------|---------|----------|-----------|-----------|------------|----------|

| A | meta/llama-3.1-8b-instruct | CALIBRATED | 1.0 | 0.119 | 0.0 | 0.0 | 0.881 | 0.0 |
| B | z-ai/glm-5.2 | CALIBRATION_BLOCKED | 0 | 0.0 | 0 | 0 | 0.0476 | 0.9524 |
| C | google/gemma-4-31b-it | CALIBRATION_BLOCKED | 0.6364 | 0.2619 | 0.3636 | 0.0 | 0.4762 | 0.2619 |
| D | minimaxai/minimax-m3 | CALIBRATION_BLOCKED | 0 | 0.0 | 0 | 0 | 0.0238 | 0.9762 |
| E | google/diffusiongemma-26b-a4b-it | CALIBRATION_BLOCKED | 1.0 | 0.0238 | 0.0 | 0.0 | 0.2857 | 0.6905 |
| F | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning | CALIBRATION_BLOCKED | 0 | 0.0 | 0 | 0 | 0.9524 | 0.0476 |

## Selection: **CALIBRATED_EVALUATOR_SELECTED**

Selected: `meta/llama-3.1-8b-instruct`
fk=0.0, det_acc=1.0, cov=0.119
