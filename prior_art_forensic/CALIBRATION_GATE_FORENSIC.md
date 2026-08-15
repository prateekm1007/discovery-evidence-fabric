# CALIBRATION GATE FORENSIC

## Status: HOLDOUT_FAIL

## Oracle Bug Audit

### Case 21999911

| Field | Value |
|-------|-------|
| Original label | SPECIFIC_DISCLOSURE |
| Corrected label | NOT_SPECIFIC_DISCLOSURE |
| Device match text | 'iol' |
| Full word containing match | 'diol' |
| Is substring match | True |
| Deterministic proof | The regex pattern 'IOL' (case-insensitive) matched 'iol' as a substring of 'diol'. The patent is about an antimicrobial composition for nail infections, not intraocular lenses. |

**Verdict: ORACLE BUG PROVEN.** Label corrected from SPECIFIC_DISCLOSURE to NOT_SPECIFIC_DISCLOSURE.

## Corrected Holdout Manifest

- Hash: f5d616f6a48b8052
- SPECIFIC: 9
- NOT_SPECIFIC: 10
- Correction: Case 21999911 moved from SPECIFIC to NOT_SPECIFIC

## Holdout Re-Run Results (frozen evaluator, no cached classifications)

| Metric | Value | Threshold | Pass |
|--------|-------|-----------|------|
| specific_recall | 0.8750 | >= 0.80 | ✓ |
| specific_precision | 1.0000 | >= 0.80 | ✓ |
| negative_rejection | 1.0000 | >= 0.80 | ✓ |
| call_failures | 3 | 0 | ✗ |

**Status: HOLDOUT_FAIL**

## Pass Condition Analysis

- specific_recall >= 80%: **PASS** (0.8750)
- specific_precision >= 80%: **PASS** (1.0000)
- negative_rejection >= 80%: **PASS** (1.0000)
- call_failures = 0: **FAIL** (3 failures)

The ONLY remaining blocker is **API reliability** — 3 Mistral API calls failed with HTTP 429 (rate limiting).
The evaluator logic itself achieves 87.5% specific_recall, 100% negative_rejection, 100% specific_precision.

## Failure Mode Distribution

{
  "SPECIFICATION_LINKAGE": 1,
  "TRUE_POSITIVE": 7,
  "CALL_FAILED": 3,
  "TRUE_NEGATIVE": 8
}

## Per-Case Results

| Case | GT | Primary | Match | Mode |
|------|----|---------|-------|------|
| 17767816 | SPECIFIC_DISCLOSURE | POSSIBLE_RELEVANCE | ✗ | SPECIFICATION_LINKAGE |
| 17810608 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 25228654 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 28393619 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 21297198 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 25254346 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 27489049 | SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | ✗ | CALL_FAILED |
| 27833708 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 23667529 | SPECIFIC_DISCLOSURE | SPECIFIC_DISCLOSURE | ✓ | TRUE_POSITIVE |
| 21999911 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17354769 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17371440 | NOT_SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | ✗ | CALL_FAILED |
| 17391298 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17397856 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17411524 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17416348 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17416717 | NOT_SPECIFIC_DISCLOSURE | EVALUATOR_CALL_FAILED | ✗ | CALL_FAILED |
| 17432515 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |
| 17440301 | NOT_SPECIFIC_DISCLOSURE | NO_MATCH_FOUND | ✓ | TRUE_NEGATIVE |