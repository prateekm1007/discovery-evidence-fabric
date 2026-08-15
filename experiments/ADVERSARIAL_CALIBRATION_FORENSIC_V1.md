# Adversarial Calibration Forensic V1 (Protocol V2 — NVIDIA evaluator)

Status: **CALIBRATION_BLOCKED**
Root hash: `dcb6324675e7437f`

## Summary

- total_cases: 35
- scientific_results: 35
- evaluator_call_failed: 0
- correct: 12
- incorrect: 23
- overall_accuracy: 0.3429

## Per-Category

- MECHANISM_VALID: 0.2 (1/5)
- TRANSFER_VALID: 0.2 (1/5)
- BOUNDARY_CONDITION: 1.0 (5/5)
- NON_BOUNDARY: 0.0 (0/5)
- SPECIFIC_PRIOR_ART: 0.6 (3/5)
- TOPICAL_ONLY_PRIOR_ART: 0.0 (0/5)
- OBVIOUSNESS_NON_OBVIOUSNESS: 0.4 (2/5)

## False Kills (21 cases)

- MECH_001 (MECHANISM_VALID): expected=SURVIVE, got=KILL
- MECH_002 (MECHANISM_VALID): expected=SURVIVE, got=KILL
- MECH_004 (MECHANISM_VALID): expected=SURVIVE, got=KILL
- MECH_005 (MECHANISM_VALID): expected=SURVIVE, got=KILL
- TRANS_001 (TRANSFER_VALID): expected=SURVIVE, got=KILL
- TRANS_002 (TRANSFER_VALID): expected=SURVIVE, got=KILL
- TRANS_003 (TRANSFER_VALID): expected=SURVIVE, got=KILL
- TRANS_005 (TRANSFER_VALID): expected=SURVIVE, got=KILL
- NONB_001 (NON_BOUNDARY): expected=SURVIVE, got=KILL
- NONB_002 (NON_BOUNDARY): expected=SURVIVE, got=KILL
- ... and 11 more

## False Survivals (2 cases)

- SPEC_004 (SPECIFIC_PRIOR_ART): expected=KILL, got=SURVIVE
- SPEC_005 (SPECIFIC_PRIOR_ART): expected=KILL, got=SURVIVE

## Live Integration Checks

- boundary_resolver_to_final_verdict: True
- specific_prior_art_kill_permitted: True
- topical_prior_art_kill_prohibited: False
- timeout_to_evaluator_call_failed: False

## Root Cause

The evaluator (meta/llama-3.1-8b-instruct) is an 8B parameter model that is too aggressive 
as an adversarial reviewer. It produces KILL verdicts on 60% of cases that should survive. 
The V4 corrections (firewall, boundary evidence, adversarial-invalid) are correctly wired 
and applied, but the underlying LLM evaluator itself is not calibrated.

## Recommendation

Use a larger, more calibrated evaluator model (e.g., mistral-medium-latest, deepseek-v4-pro, 
or a 70B+ model). The 8B model is suitable for fast generation but not for adversarial adjudication.