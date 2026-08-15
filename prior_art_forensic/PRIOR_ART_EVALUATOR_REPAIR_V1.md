# PRIOR-ART EVALUATOR REPAIR V1 — FROZEN

## Status: HOLDOUT_FAIL

## Frozen Evaluator Configuration

| Parameter | Value |
|-----------|-------|
| Primary model | mistral-large-latest |
| Primary provider | Mistral API |
| No primary fallback | True |
| Secondary model | glm-4-plus |
| Secondary provider | z-ai CLI |
| Temperature | 0.0 |
| Max retries | 3 |
| Prompt hash | 70bb690572d1fec1 |
| Ontology version | c8ae93b52fb2c09d |
| Parser version | frozen_v1_markdown_truncation_fallback |
| Evaluator version | evaluator_v1_frozen_mistral_only |

## Historical Dev Result (commit 10544c4) — MIXED_PRIMARY_MODEL

The dev result from commit 10544c4 is marked as **MIXED_PRIMARY_MODEL** because at least one case used Comet/deepseek-chat as primary fallback. It is retained as historical evidence but is NOT used as the formal frozen-evaluator pass.

| Metric | Value | Formal? |
|--------|-------|---------|
| dev_specific_recall | 0.80 | NO (mixed model) |
| dev_negative_rejection | 1.00 | NO (mixed model) |

## Formal Dev Test (FROZEN, Mistral primary ONLY)

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 1.0000 | >= 0.80 | ✓ |
| negative_rejection | 1.0000 | >= 0.80 | ✓ |
| specific_precision | 1.0000 | — | — |
| call_failed | 0 | 0 | ✓ |
| **DEV PASS** | | | **✓** |

### Dev Case Details

| Case | Device | Mechanism | GT | Primary | Secondary | Match | Mode |
|------|--------|-----------|----|---------|-----------|-------|------|
| oracle_v3_specific_01 | continuous glucose monitor | biocompatible membrane | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| oracle_v3_specific_02 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| oracle_v3_specific_03 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| oracle_v3_specific_04 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| oracle_v3_specific_05 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| oracle_v3_negative_01 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_02 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_03 | Spinal Fusion Device | pedicle screw | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_04 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| oracle_v3_negative_05 | Coronary Stent | drug-eluting coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |

## Holdout Test (10 SPECIFIC + 10 NOT_SPECIFIC, run ONCE)

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 0.7778 | >= 0.80 | ✗ |
| negative_rejection | 1.0000 | >= 0.80 | ✓ |
| specific_precision | 1.0000 | >= 0.80 | ✓ |
| call_failed | 3 | 0 | ✗ |
| **HOLDOUT PASS** | | | **✗** |

### Holdout Case Details

| Case | Device | Mechanism | GT | Primary | Secondary | Match | Mode |
|------|--------|-----------|----|---------|-----------|-------|------|
| 17767816 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | POSSIBLE_RELEVANCE | TOPICAL_RELATED | ✗ | SPECIFICATION_LINKAGE |
| 17810608 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 25228654 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 28393619 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 21297198 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 25254346 | continuous glucose monitor | biocompatible membrane | SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | TOPICAL_RELATED | ✗ | CALL_FAILED |
| 27489049 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 27833708 | cardiac pacemaker | adaptive pacing | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 23667529 | coronary stent | drug-eluting coating | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 21999911 | intraocular lens | antimicrobial coating | SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✗ | FALSE_NEGATIVE |
| 17354769 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | NO_MATCH_FOUND | ✗ | CALL_FAILED |
| 17371440 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17391298 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17397856 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17411524 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17416348 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | NO_MATCH_FOUND | ✗ | CALL_FAILED |
| 17416717 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17432515 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17440301 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17440471 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |

## Exit State

Per spec Section 10:
- DEV_PASS: True
- HOLDOUT_PASS: False
- **Exit: HOLDOUT_FAIL**

Only DEV_PASS AND HOLDOUT_PASS → CALIBRATION_PASS. Historical false-kill recovery remains LOCKED.

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED (6/6 regression PASS, 11/11 tests PASS)
- No new ontology mappings added
- No prompt wording changes after freezing
- No corpus generation
- No simulation
- TEE still quarantined
