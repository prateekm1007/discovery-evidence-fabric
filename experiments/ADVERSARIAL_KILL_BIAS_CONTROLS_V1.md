# Adversarial Kill Bias Controls V1


## Summary

| Metric | Value |
|--------|-------|
| Kill bias rate | 0.7143 |
| Survive bias rate | 0.2857 |
| Insufficient evidence rate | 0.0000 |
| Kill count | 10/14 |
| Survive count | 4/14 |
| Failed count | 0/14 |

## Hypothesis Test

**H1 SUPPORTED — evaluator contract is KILL-biased**

- H1 score: 6/6
- Average false-kill across 6 models: 0.6877
- Average false-survival across 6 models: 0.0079

### Evidence

- near_zero_false_survival: True
- high_false_kill_across_unrelated_families: True
- same_directional_error: True
- binary_schema_no_insufficient_evidence: True
- adversarial_framing: True
- neutrality_test_kill_bias: True

## Root Cause

**BINARY_PASS_KILL_SCHEMA_NO_INSUFFICIENT_EVIDENCE**

The adversarial prompt uses a binary PASS/KILLED schema with no INSUFFICIENT_EVIDENCE option. When evidence is ambiguous, the evaluator cannot express 'I cannot determine this' — it is forced to choose PASS or KILLED. Combined with the 'attack' framing and negative dimension phrasing, this creates systematic KILL bias across all model families.

### Fix Required

- Add INSUFFICIENT_EVIDENCE as a third state for ALL dimensions (not just BOUNDARY_CONDITION)
- Change prompt from 'attack' framing to 'neutral evidence evaluation'
- Rephrase dimensions from negative ('Is the mechanism unsupported?') to neutral ('Is the mechanism supported by evidence?')
- Add explicit instruction: 'If evidence is insufficient to determine, respond INSUFFICIENT_EVIDENCE'
- Add instruction: 'Absence of evidence is not evidence of failure'

## Control Results

| Control ID | Expected | Got | Correct |
|-----------|----------|-----|---------|
| CTRL_INSUF_001 | INSUFFICIENT_EVIDENCE | KILL | False |
| CTRL_INSUF_002 | INSUFFICIENT_EVIDENCE | KILL | False |
| CTRL_INSUF_003 | INSUFFICIENT_EVIDENCE | KILL | False |
| CTRL_INSUF_004 | INSUFFICIENT_EVIDENCE | KILL | False |
| CTRL_INSUF_005 | INSUFFICIENT_EVIDENCE | KILL | False |
| CTRL_INSUF_006 | INSUFFICIENT_EVIDENCE | KILL | False |
| CTRL_INSUF_007 | INSUFFICIENT_EVIDENCE | KILL | False |
| CTRL_SURV_001 | SURVIVE | SURVIVE | True |
| CTRL_SURV_002 | SURVIVE | SURVIVE | True |
| CTRL_SURV_003 | SURVIVE | KILL | False |
| CTRL_SURV_004 | SURVIVE | KILL | False |
| CTRL_SURV_005 | SURVIVE | SURVIVE | True |
| CTRL_SURV_006 | SURVIVE | KILL | False |
| CTRL_SURV_007 | SURVIVE | SURVIVE | True |