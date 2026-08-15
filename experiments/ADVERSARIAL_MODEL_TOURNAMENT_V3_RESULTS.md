# Adversarial Model Tournament V3 Results

Generated: 2026-08-15T16:21:52.045790+00:00

Protocol SHA256: `cb2698c80a2964f824fe23e60ab9f5962249cbf477bbe89708b6e7ec4192acc4`

Root hash: `fd4ea78510fe753b`


## Models Tested: 3

| ID | Model | Status | Accuracy | False Kill | False Surv | Median Lat |

|---|-------|--------|----------|-----------|-----------|------------|

| A | meta/llama-3.1-8b-instruct | CALIBRATION_BLOCKED | 0.5143 | 0.4571 | 0.0286 | 2.1s |
| B | z-ai/glm-5.2 | CALIBRATION_BLOCKED | 0.0 | 1.0 | 0.0 | 3.5s |
| C | google/gemma-4-31b-it | CALIBRATION_BLOCKED | 0.3438 | 0.6562 | 0.0 | 10.7s |

## Selection

**CALIBRATION_BLOCKED_NO_MODEL**

No model passed the acceptance gate.

- A: accuracy=0.5143, false_kill=0.4571, per_cat_pass=False
- B: accuracy=0.0, false_kill=1.0, per_cat_pass=False
- C: accuracy=0.3438, false_kill=0.6562, per_cat_pass=False

## Per-Model Details


### A: meta/llama-3.1-8b-instruct

- Status: CALIBRATION_BLOCKED
- Overall accuracy: 0.5143
- False kill rate: 0.4571
- False survival rate: 0.0286
- Call failure rate: 0.0
- Median latency: 2.1s, p95: 5.8s
- Per-category:
  - MECHANISM_VALID: 0.4 (2/5)
  - TRANSFER_VALID: 0.8 (4/5)
  - BOUNDARY_CONDITION: 1.0 (5/5)
  - NON_BOUNDARY: 0.0 (0/5)
  - SPECIFIC_PRIOR_ART: 0.8 (4/5)
  - TOPICAL_ONLY_PRIOR_ART: 0.2 (1/5)
  - OBVIOUSNESS_NON_OBVIOUSNESS: 0.4 (2/5)

### B: z-ai/glm-5.2

- Status: CALIBRATION_BLOCKED
- Overall accuracy: 0.0
- False kill rate: 1.0
- False survival rate: 0.0
- Call failure rate: 0.9143
- Median latency: 3.5s, p95: 3.7s
- Per-category:
  - MECHANISM_VALID: 0.0 (0/2)
  - TRANSFER_VALID: 0 (0/0)
  - BOUNDARY_CONDITION: 0 (0/0)
  - NON_BOUNDARY: 0.0 (0/1)
  - SPECIFIC_PRIOR_ART: 0 (0/0)
  - TOPICAL_ONLY_PRIOR_ART: 0 (0/0)
  - OBVIOUSNESS_NON_OBVIOUSNESS: 0 (0/0)

### C: google/gemma-4-31b-it

- Status: CALIBRATION_BLOCKED
- Overall accuracy: 0.3438
- False kill rate: 0.6562
- False survival rate: 0.0
- Call failure rate: 0.0857
- Median latency: 10.7s, p95: 63.4s
- Per-category:
  - MECHANISM_VALID: 0.0 (0/5)
  - TRANSFER_VALID: 0.0 (0/4)
  - BOUNDARY_CONDITION: 1.0 (4/4)
  - NON_BOUNDARY: 0.0 (0/5)
  - SPECIFIC_PRIOR_ART: 1.0 (5/5)
  - TOPICAL_ONLY_PRIOR_ART: 0.0 (0/5)
  - OBVIOUSNESS_NON_OBVIOUSNESS: 0.5 (2/4)