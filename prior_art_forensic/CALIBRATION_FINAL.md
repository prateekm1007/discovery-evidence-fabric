# CALIBRATION FINAL

## Status: CALIBRATION_PASS

## Frozen Evaluator Configuration

| Parameter | Value |
|-----------|-------|
| Evaluator version | evaluator_v1_frozen_mistral_only |
| Primary model | mistral-large-latest |
| Primary provider | Mistral API |
| Temperature | 0.0 |
| Prompt hash | 70bb690572d1fec1 |
| Ontology version | c8ae93b52fb2c09d |
| Max retries | 3 |
| No model substitution | True |

## Corrected Oracle Case

| Field | Value |
|-------|-------|
| Case ID | 21999911 |
| Original label | SPECIFIC_DISCLOSURE |
| Corrected label | NOT_SPECIFIC_DISCLOSURE |
| Reason | IOL regex matched 'iol' as substring of 'diol' |
| Correction commit | 28d78567679fccad35fb80912af213c218e9ff8d |

## Holdout Manifest

- Hash: `f5d616f6a48b8052`
- Frozen at commit: `28d78567679fccad35fb80912af213c218e9ff8d`

## Final Metrics

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 0.8889 | >= 0.80 | ✓ |
| specific_precision | 1.0000 | >= 0.80 | ✓ |
| negative_rejection | 1.0000 | >= 0.80 | ✓ |
| call_failures | 0 | 0 | ✓ |

**CALIBRATION_PASS**

## Retry Results (3 CALL_FAILED cases)

| Case | GT | Primary | Outer Attempt | Match | Mode |
|------|----|---------|---------------|-------|------|
| 27489049 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | 1 | ✓ | TRUE_POSITIVE |
| 17371440 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | 1 | ✓ | TRUE_NEGATIVE |
| 17416717 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | 1 | ✓ | TRUE_NEGATIVE |

All 3 cases succeeded on the first outer retry attempt (Mistral rate limit had cleared).

## All Holdout Results

| Case | Device | Mechanism | GT | Primary | Secondary | Match | Mode |
|------|--------|-----------|----|---------|-----------|-------|------|
| 17767816 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | POSSIBLE_RELEVANCE | TOPICAL_RELATED | ✗ | SPECIFICATION_LINKAGE |
| 17810608 | ultrasound system | transducer array | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 25228654 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 28393619 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 21297198 | insulin pump | closed-loop control | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 25254346 | continuous glucose monitor | biocompatible membrane | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 27489049 | spinal fusion device | pedicle screw | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | TOPICAL_RELATED | ✓ | TRUE_POSITIVE |
| 27833708 | cardiac pacemaker | adaptive pacing | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 23667529 | coronary stent | drug-eluting coating | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 21999911 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17354769 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17371440 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17391298 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17397856 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17411524 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17416348 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17416717 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17432515 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17440301 | intraocular lens | antimicrobial coating | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |

## Documented Evaluator Miss (not tuned)

| Case | Mode | Note |
|------|------|------|
| 17767816 | SPECIFICATION_LINKAGE | Evaluator returned POSSIBLE_RELEVANCE instead of SPECIFIC_DISCLOSURE. Not tuned to eliminate. |

## Failure Mode Distribution

{
  "SPECIFICATION_LINKAGE": 1,
  "TRUE_POSITIVE": 8,
  "TRUE_NEGATIVE": 10
}

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED (6/6 regression PASS, 11/11 tests PASS)
- No evaluator changes
- No ontology changes
- No prompt changes
- No model substitution
- No corpus generation
- No simulation
- TEE still quarantined

## Unlock

CALIBRATION_PASS unlocks **HISTORICAL_RECOVERY_V1**.
Do NOT run historical recovery in this task.
