# AUTONOMOUS CALIBRATION V3.5 — PROTOCOL

**Status**: `CALIBRATION_BLOCKED` (pre-registered, frozen before inference)
**Base commit**: `ff3be20`
**Protocol SHA-256**: `fc4123790fb5e464a0d1ce17a963549e3bd482b026b8018f9d90c07cc7791325`

## Why V3.5

V3.4 achieved 85% 102 accuracy (passage-grounded 102 works), but 103 accuracy
remains 15%. The 103 adversary is too lenient — it survives abandoned cases
that should be rejected.

V3.5 does NOT simply make 103 more aggressive. Instead, it builds a
**prosecution-grounded forensic table** to determine WHY the system disagrees
with known prosecution outcomes.

## V3.4 Frozen (True Numbers)

| Metric | Value | Threshold | Pass? |
|---|---|---|---|
| Accuracy | 75% | ≥85% | ✗ |
| False-elite | 0% | ≤10% | ✓ |
| False-reject | 0% | ≤10% | ✓ |
| Cited-art recall | 100% | ≥90% | ✓ |
| Search recall | 78.6% | ≥80% | ✗ |
| 102 accuracy | 85% | ≥85% | ✓ |
| 103 accuracy | 15% | ≥80% | ✗ |

**4/7 thresholds met.** 103 is the sole remaining blocker.

## V3.5 Approach

### 1. Case-by-Case 103 Forensic Table

For every case with known 103 outcome, compare:
- `examiner_103_reference_A` vs `system_closest_prior_art`
- `examiner_103_reference_B` vs `system_secondary_reference`
- `examiner_motivation` vs `system_motivation`
- `examiner_reason_to_combine` vs `system_motivation_evidence`
- `examiner_expectation_of_success` vs `system_expectation`
- `examiner_teaching_away` vs `system_teaching_away`
- `examiner_technical_effect` vs `system_technical_effect`

### 2. 103 Error Classification (No Generic MODEL_FAILURE)

- `GROUND_TRUTH_EXTRACTION_FAILURE`
- `SEARCH_FAILURE`
- `REFERENCE_SELECTION_FAILURE`
- `DIFFERENCE_IDENTIFICATION_FAILURE`
- `MOTIVATION_FAILURE`
- `EXPECTATION_OF_SUCCESS_FAILURE`
- `TEACHING_AWAY_FAILURE`
- `TECHNICAL_EFFECT_FAILURE`
- `HINDSIGHT_FAILURE`
- `FINAL_ADJUDICATION_FAILURE`

### 3. Examiner Ground Truth ≠ Unquestionable Oracle

Preserve both:
- `EXAMINER_GROUND_TRUTH`
- `SYSTEM_INDEPENDENT_ANALYSIS`

If system has defensible alternative rationale: record `ALTERNATIVE_REASONING`.
Do NOT force model to imitate examiner language.

### 4. 3-Candidate Closest Prior Art

Construct ≥3 candidates, score by:
- technical field
- purpose
- technical effect
- structural similarity
- functional similarity

Select `CLOSEST_PRIOR_ART` with provenance.

### 5. Difference Vector

`CLAIM minus CLOSEST_PRIOR_ART`

Every difference:
- `element_id`
- `exact_claim_span`
- `prior_art_status`
- `technical_significance`

### 6. Motivation Evidence

Require evidence from one of:
- EXPRESS_MOTIVATION
- KNOWN_PROBLEM
- DESIGN_PRESSURE
- MARKET_ENGINEERING_CONSTRAINT
- REFERENCE_TEACHING
- ESTABLISHED_ART_KNOWLEDGE
- PREDICTABLE_SUBSTITUTION

Record: `motivation_source` + `exact_passage` + `why_it_supports_combination`

If no support: `MOTIVATION_INSUFFICIENT`

### 7. Expectation of Success

Separate `CAN_WORK` from `EXPECTED_TO_WORK`.

Require technical basis:
- compatible mechanism
- compatible operating regime
- known substitution
- same function
- established design principle
- experimental evidence
- reference teaching

No "PHOSITA would know this" without evidence.

### 8. Teaching Away

Search explicit and implicit teaching-away signals.
Record: `supporting_passage` + `contradicting_passage` + `strength`

### 9. Technical Effect

For each difference:
- `predicted_effect`
- `documented_effect`
- `unexpected_effect`

If unexpectedly superior: record why.

### 10. Anti-Hindsight Two-Pass

- Pass A: invention hidden
- Pass B: invention visible
- Compare: problem definition, reference selection, motivation, difference, expected success
- If reasoning appears only after seeing invention: `HINDSIGHT_HIGH`

### 11. Prosecution-Cited 103 Art Recall

Retrieve every substantive examiner-cited reference relevant to 103.
Measure `CITED_103_ART_RECALL` (separate from overall cited-art recall).

### 12. 103 Search Expansion

Search:
- forward citations
- backward citations
- family members
- CPC neighbors
- same assignee
- same inventor
- same technical problem

Objective: determine whether system can find same or materially equivalent
obviousness evidence (not reproduce examiner's exact search).

### 13. Model Separation

- `SEARCHER_MODEL` ≠ `OBVIOUSNESS_MODEL` ≠ `ADJUDICATOR_MODEL`
- Adjudicator receives structured evidence, not searcher's conclusion

### 14. Score Evidence, Not Confidence

Every 103 conclusion must have:
- `evidence_count`
- `strongest_evidence`
- `weakest_link`
- `uncertainty`
- `alternative_explanation`

No model confidence field can substitute for evidence.

## Acceptance Gate

| Metric | Threshold |
|---|---|
| Overall accuracy | ≥ 85% |
| False-elite rate | ≤ 10% |
| False-reject rate | ≤ 10% |
| Cited-art recall | ≥ 90% |
| Search recall | ≥ 80% |
| 102 accuracy | ≥ 85% |
| 103 accuracy | ≥ 80% |

If 103 remains <80%: `CALIBRATION_BLOCKED`.

## Output Artifacts

`PROTOCOL.json` · `PROTOCOL.sha256` · `PROTOCOL.md` · `PROSECUTION_GROUND_TRUTH.json` ·
`103_CASE_FORENSICS.json` · `103_CITED_ART_RECALL.json` · `SEARCH_EXPANSION.json` ·
`ERROR_ANALYSIS.json` · `METRICS.json` · `REPORT.md`

## Stop Condition

DO NOT RUN 50→5. STOP FOR CEO AUDIT.
