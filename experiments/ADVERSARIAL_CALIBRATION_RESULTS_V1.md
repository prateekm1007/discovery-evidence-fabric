# Adversarial Calibration Results V1

Status: **CALIBRATION_BLOCKED**
Root hash: `dcb6324675e7437f`

## Summary

| Metric | Value |
|--------|-------|
| Total cases | 35 |
| Scientific results | 0 |
| Evaluator call failed | 35 |
| Overall accuracy | 0 |
| False kill rate | 0 |
| False survival rate | 0 |

## Acceptance

- aggregate_pass: False
- per_category_pass: True
- zero_fabricated_evidence: True
- zero_fabricated_patent_references: True
- zero_evaluator_failure_as_kill: True
- zero_firewall_violations: True
- CALIBRATION_PASS: False
- CALIBRATION_STATUS: CALIBRATION_BLOCKED

## Per-Category

| Category | Accuracy | Correct | Scientific | Eval Failed |
|----------|----------|---------|-----------|-------------|
| MECHANISM_VALID | 0 | 0 | 0 | 5 |
| TRANSFER_VALID | 0 | 0 | 0 | 5 |
| BOUNDARY_CONDITION | 0 | 0 | 0 | 5 |
| NON_BOUNDARY | 0 | 0 | 0 | 5 |
| SPECIFIC_PRIOR_ART | 0 | 0 | 0 | 5 |
| TOPICAL_ONLY_PRIOR_ART | 0 | 0 | 0 | 5 |
| OBVIOUSNESS_NON_OBVIOUSNESS | 0 | 0 | 0 | 5 |

## Failure Mode

All 35 cases returned EVALUATOR_CALL_FAILED. The OpenRouter API (deepseek/deepseek-v4-flash-0731) 
is unavailable — the API key is expired or rate-limited. No scientific evaluation was possible.

This is an OPERATIONAL failure, not a scientific result. The calibration is BLOCKED 
until a working evaluator endpoint is available.