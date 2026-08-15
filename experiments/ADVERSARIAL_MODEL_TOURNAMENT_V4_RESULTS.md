# Adversarial Model Tournament V4 Results

Generated: 2026-08-15T17:38:07.120196+00:00

Root hash: `590d8e06ca47cab2`


## Models Tested: 6

| ID | Model | Status | Accuracy | False Kill | False Surv | Call Fail | Med Lat |

|---|-------|--------|----------|-----------|-----------|-----------|----------|

| A | meta/llama-3.1-8b-instruct | CALIBRATION_BLOCKED | 0.4762 | 0.4762 | 0.0476 | 0.0 | 1.8s |
| B | z-ai/glm-5.2 | CALIBRATION_BLOCKED | 0.0 | 1.0 | 0.0 | 0.9524 | 0.3s |
| C | google/gemma-4-31b-it | CALIBRATION_BLOCKED | 0.3529 | 0.6471 | 0.0 | 0.1905 | 5.8s |
| D | minimaxai/minimax-m3 | CALIBRATION_BLOCKED | 0.25 | 0.75 | 0.0 | 0.9048 | 0.3s |
| E | google/diffusiongemma-26b-a4b-it | CALIBRATION_BLOCKED | 0.3571 | 0.6429 | 0.0 | 0.0 | 1.0s |
| F | nvidia/nemotron-3-nano-omni-30b-a3b-reasoning | CALIBRATION_BLOCKED | 0.3902 | 0.6098 | 0.0 | 0.0238 | 7.0s |

## Selection: **CALIBRATION_BLOCKED_NO_MODEL**

No model passed the acceptance gate.

- A (meta/llama-3.1-8b-instruct): acc=0.4762, fk=0.4762, cfr=0.0
- B (z-ai/glm-5.2): acc=0.0, fk=1.0, cfr=0.9524
- C (google/gemma-4-31b-it): acc=0.3529, fk=0.6471, cfr=0.1905
- D (minimaxai/minimax-m3): acc=0.25, fk=0.75, cfr=0.9048
- E (google/diffusiongemma-26b-a4b-it): acc=0.3571, fk=0.6429, cfr=0.0
- F (nvidia/nemotron-3-nano-omni-30b-a3b-reasoning): acc=0.3902, fk=0.6098, cfr=0.0238