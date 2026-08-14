# HISTORICAL RECOVERY V1.1 — FORENSIC CLOSEOUT

## Corrected Statistics

| Category | Count |
|----------|-------|
| CONFIRMED_SPECIFIC_PRIOR_ART | 5 |
| CONFIRMED_FALSE_KILL | 18 |
| UNRESOLVED_CALL_FAILURE | 0 |
| RECOVERED_AIC | 0 |
| RECOVERED_CANDIDATE | 1 |

## Rates

| Rate | Value |
|------|-------|
| CONFIRMED_FALSE_KILL_RATE | 18/24 |
| CONFIRMED_SPECIFIC_PRIOR_ART_RATE | 5/24 |
| UNRESOLVED_RATE | 0/24 |
| RECOVERED_CANDIDATE_COUNT | 1 |
| RECOVERED_AIC_COUNT | 0 |

## AIC Forensic Check: AIC:V1:p0002

### Status: RECOVERED_CANDIDATE_PENDING_ADVERSARIAL

The candidate passed prior-art re-evaluation (NO_MATCH_FOUND) and target alignment (ON_TARGET),
but **FAILED all 7 adversarial dimensions**. Per spec Section 5: "UNKNOWN is NOT PASS" and
"KILLED is NOT PASS." The candidate cannot be promoted to AUTOMATED_INVENTION_CANDIDATE.

### Adversarial Dimensions

| Dimension | Verdict | Reason |
|-----------|---------|--------|
| mechanism_validity | KILLED | The proposed mechanism lacks sufficient evidence and engineering justification t |
| transfer_validity | KILLED | The transfer validity is undermined by insufficient evidence and unclear mechani |
| boundary_failure | KILLED | The proposed intervention introduces a boundary failure by overcomplicating the  |
| obvious_combination | KILLED | The proposed intervention is an obvious combination of existing locking mechanis |
| engineering_feasibility | KILLED | The proposed intervention lacks sufficient engineering justification and regulat |
| regulatory_feasibility | KILLED | The proposed intervention lacks sufficient regulatory feasibility due to insuffi |
| falsifiability | KILLED | The candidate's claim lacks falsifiability due to insufficient evidence and unte |

**Overall adversarial verdict: KILLED**

The candidate is preserved as a recovered historical candidate (prior-art false kill confirmed)
but is NOT an AUTOMATED_INVENTION_CANDIDATE.

## Per-Candidate Results (all 24)

| Problem ID | Version | Device | PA State | Recovery Status |
|------------|---------|--------|----------|-----------------|
| p0001 | V1 | Hip Implant | TOPICAL_RELATED | TOPICAL_ONLY |
| p0002 | V1 | Hip Implant | NO_MATCH_FOUND | RECOVERED_AIC |
| p0019 | V1 | Shoulder Implant | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00001 | V2 | Hip Implant | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00002 | V2 | Hip Implant | SPECIFIC_DISCLOSURE | SPECIFIC_PRIOR_ART |
| v2_00006 | V2 | Hip Implant | EVALUATOR_CALL_FAILED | TOPICAL_ONLY |
| v2_00007 | V2 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00008 | V2 | Hip Implant | SPECIFIC_DISCLOSURE | SPECIFIC_PRIOR_ART |
| v2_00009 | V2 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00010 | V2 | Hip Implant | POSSIBLE_RELEVANCE | POSSIBLE_RELEVANCE |
| v2_00011 | V2 | Hip Implant | EVALUATOR_CALL_FAILED | SPECIFIC_PRIOR_ART |
| v2_00012 | V2 | Hip Implant | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00013 | V2 | Hip Implant | TOPICAL_RELATED | TOPICAL_ONLY |
| v2_00014 | V2 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00015 | V2 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v2_00017 | V2 | Hip Implant | EVALUATOR_CALL_FAILED | SPECIFIC_PRIOR_ART |
| v3_00005 | V3 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v3_00007 | V3 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v3_00008 | V3 | Hip Implant | SPECIFIC_DISCLOSURE | SPECIFIC_PRIOR_ART |
| v3_00009 | V3 | Hip Implant | TOPICAL_RELATED | TOPICAL_ONLY |
| v3_00010 | V3 | Hip Implant | EVALUATOR_CALL_FAILED | TOPICAL_ONLY |
| v3_00011 | V3 | Hip Implant | TOPICAL_RELATED | TOPICAL_ONLY |
| v3_00012 | V3 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |
| v3_00014 | V3 | Hip Implant | NO_MATCH_FOUND | NO_MATCH_FOUND |

## Recovery Dependency

| Field | Value |
|-------|-------|
| Calibration pass commit | 2620112c05401d6104b25bc4a828ce4b3c8c9542 |
| Evaluator commit | 5276d414660ff0e551428064c999468e060c7ed9 |
| Prompt hash | 70bb690572d1fec1 |
| Ontology version | c8ae93b52fb2c09d |
| Searched universe hash | e7eb148aafe51fbe |

## Key Findings

1. **18/24 (75%) confirmed false kills** — the old LIKELY_PRIOR_ART_EXISTS state was over-killing
2. **5/24 (20.8%) confirmed specific prior art** — correctly killed under new state machine
3. **0/24 unresolved** — all 4 previously CALL_FAILED cases resolved on retry
4. **0 AICs promoted** — the 1 recovered candidate failed adversarial review (all 7 dimensions KILLED)
5. The candidate (p0002) was a false prior-art kill but does NOT survive adversarial review

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED (6/6 regression PASS, 11/11 tests PASS)
- No new candidates generated
- No simulation started
- TEE still quarantined
- Frozen evaluator unchanged
