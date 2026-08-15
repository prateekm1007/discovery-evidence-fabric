# Adversarial Calibration Results V1 (Protocol V2 — NVIDIA evaluator)

Status: **CALIBRATION_BLOCKED**
Protocol V2 SHA256: 75ccba6699c0a84f186d61ad765f76e9eda560a4800456647dff84605ef735ed
Root hash: `dcb6324675e7437f`

## Summary

| Metric | Value |
|--------|-------|
| Total cases | 35 |
| Scientific results | 35 |
| Evaluator call failed | 0 |
| Correct | 12 |
| Overall accuracy | 0.3429 |
| False kill rate | 0.6 |
| False survival rate | 0.0571 |

## Per-Category Accuracy

| Category | Accuracy | Correct/Total | Expected |
|----------|----------|--------------|----------|
| MECHANISM_VALID | 0.2 | 1/5 | SURVIVE |
| TRANSFER_VALID | 0.2 | 1/5 | SURVIVE |
| BOUNDARY_CONDITION | 1.0 | 5/5 | KILL |
| NON_BOUNDARY | 0.0 | 0/5 | KILL |
| SPECIFIC_PRIOR_ART | 0.6 | 3/5 | KILL |
| TOPICAL_ONLY_PRIOR_ART | 0.0 | 0/5 | SURVIVE |
| OBVIOUSNESS_NON_OBVIOUSNESS | 0.4 | 2/5 | KILL |

## Acceptance

- aggregate_pass: False
- per_category_pass: False
- zero_fabricated_evidence: True
- zero_fabricated_patent_references: True
- zero_evaluator_failure_as_kill: True
- zero_firewall_violations: True
- CALIBRATION_PASS: False
- CALIBRATION_STATUS: CALIBRATION_BLOCKED

## Failure Analysis

The evaluator (meta/llama-3.1-8b-instruct) is **too aggressive**:

- **False kill rate: 60%** — kills 60% of candidates that should survive
- **TOPICAL_ONLY_PRIOR_ART: 0/5** — kills candidates with only topical relevance (firewall protects PRIOR_ART dimension, but LLM kills on other dimensions)
- **NON_BOUNDARY: 0/5** — kills candidates that do not cross boundaries
- **MECHANISM_VALID: 1/5** — kills candidates with valid source-supported mechanisms
- **TRANSFER_VALID: 1/5** — kills candidates with valid documented transfers

The evaluator kills almost everything across all dimensions. This is NOT a calibrated evaluator.

## What Worked

- **BOUNDARY_CONDITION: 5/5 (100%)** — correctly kills when boundary evidence exists
- **SPECIFIC_PRIOR_ART: 3/5 (60%)** — mostly correct on specific disclosure
- **OBVIOUSNESS (obvious cases): 2/2** — correctly identifies obvious combinations
- **Zero evaluator failures** — all 35 cases produced scientific verdicts
- **Zero fabricated evidence** — oracle used real external evidence
- **Zero firewall violations on PRIOR_ART dimension** — corrections applied correctly