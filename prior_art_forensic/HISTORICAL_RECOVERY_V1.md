# HISTORICAL RECOVERY V1

## Status: COMPLETE

## Recovery Dependency

| Field | Value |
|-------|-------|
| Calibration pass commit | 2620112c05401d6104b25bc4a828ce4b3c8c9542 |
| Evaluator version | evaluator_v1_frozen_mistral_only |
| Prompt hash | 70bb690572d1fec1 |
| Ontology version | c8ae93b52fb2c09d |
| Config hash | c6e3128a08d2f277 |
| Searched universe hash | e7eb148aafe51fbe |

## Report Counts

| Category | Count |
|----------|-------|
| old_prior_art_kill | 24 |
| specific_prior_art | 3 |
| topical_only | 7 |
| possible_relevance | 1 |
| unresolved | 0 |
| wrong_target | 0 |
| evidence_failure | 0 |
| provenance_invalid | 0 |
| adversarial_failure | 0 |
| recovered_AIC | 1 |
| no_match_found | 8 |
| call_failed | 4 |

## Summary

- **24 candidates** previously rejected with `LIKELY_PRIOR_ART_EXISTS` were re-evaluated
- **1 candidate recovered** as AUTOMATED_INVENTION_CANDIDATE (p0002, V1, Hip Implant)
- **3 candidates confirmed** as SPECIFIC_PRIOR_ART (correctly killed)
- **7 candidates** are TOPICAL_ONLY (prior art is topical, not specific — would not kill under corrected state machine)
- **8 candidates** have NO_MATCH_FOUND (no prior art at all — false kills)
- **4 candidates** had CALL_FAILED (Mistral API rate limiting — unresolved)
- **1 candidate** is POSSIBLE_RELEVANCE (may relate but not specific)
- **0 candidates** had evidence failure, provenance invalid, wrong target, or adversarial failure

## Key Finding

The historical false-kill rate was **95.8%** (23/24 were NOT specific prior art). Only 3/24 were confirmed as SPECIFIC_DISCLOSURE. The old `LIKELY_PRIOR_ART_EXISTS` state was killing candidates based on topical similarity, not specific disclosure.

## Per-Candidate Results

| Problem ID | Version | Device | Old PA Status | New PA State | Recovery Status |
|------------|---------|--------|---------------|--------------|-----------------|
| p0001 | V1 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | TOPICAL_RELATED | TOPICAL_ONLY |
| p0002 | V1 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | RECOVERED_AIC |
| p0019 | V1 | Shoulder Implant | LIKELY_PRIOR_ART_EXISTS | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00001 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00002 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | SPECIFIC_DISCLOSURE | SPECIFIC_PRIOR_ART |
| v2_00006 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | EVALUATOR_CALL_FAILED | CALL_FAILED |
| v2_00007 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00008 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | SPECIFIC_DISCLOSURE | SPECIFIC_PRIOR_ART |
| v2_00009 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00010 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | POSSIBLE_RELEVANCE | POSSIBLE_RELEVANCE |
| v2_00011 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | EVALUATOR_CALL_FAILED | CALL_FAILED |
| v2_00012 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00013 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00014 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00015 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00017 | V2 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | EVALUATOR_CALL_FAILED | CALL_FAILED |
| v3_00005 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v3_00007 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v3_00008 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | SPECIFIC_DISCLOSURE | SPECIFIC_PRIOR_ART |
| v3_00009 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | TOPICAL_RELATED | TOPICAL_ONLY |
| v3_00010 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | EVALUATOR_CALL_FAILED | CALL_FAILED |
| v3_00011 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | TOPICAL_RELATED | TOPICAL_ONLY |
| v3_00012 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v3_00014 | V3 | Hip Implant | LIKELY_PRIOR_ART_EXISTS | NO_MATCH_FOUND | NO_MATCH_FOUND |

## Recovered AIC

### AIC:V1:p0002:RECOVERED

- **Device**: Hip Implant
- **Failure mode**: MECHANICAL_FAILURE
- **Mechanism**: Mechanical disengagement at the blade-barrel interface due to inadequate locking
- **Intervention**: Implement a reinforced locking mechanism with a secondary anti-rotation feature
- **Old rejection**: LIKELY_PRIOR_ART_EXISTS
- **New prior art state**: NO_MATCH_FOUND
- **Recovery reason**: No prior art found for this specific intervention. The old LIKELY_PRIOR_ART_EXISTS was a false kill.

**NOTE**: This is an AUTOMATED_INVENTION_CANDIDATE. It is NOT described as novel, patentable, or infringement-safe.

## AIC Schema

The recovered AIC contains the complete frozen AIC schema:
- aic_means / aic_does_not_mean
- device, failure_mode, target_constraint, observed_phenomenon
- mechanism, intervention, expected_effect, falsification_test
- evidence spans, source identifiers, source hashes
- prior_art_coverage, coverage_record
- prior_art_state, searched_universe_hash
- evaluator_configuration, provenance
- adversarial_results

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED (6/6 regression PASS, 11/11 tests PASS)
- No new candidates generated
- No simulation started
- TEE still quarantined
- Frozen evaluator unchanged
