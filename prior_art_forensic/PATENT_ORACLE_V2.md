# PATENT ORACLE V2 — Built from Real Patent Text

## Oracle Version: V2
## Created: 2026-08-14T15:13:08.798369+00:00
## Source Commit: 233fd76d0d6fda32a2a6b4386a2a9f833b0d949b

## True Numbers

| Metric | Value |
|--------|-------|
| Total cases | 20 |
| SPECIFIC_DISCLOSURE | 5 |
| NOT_SPECIFIC_DISCLOSURE | 5 |
| POSSIBLE_RELEVANCE | 5 |
| CONTRADICTORY | 5 |

## Mining Summary

| Metric | Value |
|--------|-------|
| Patents scanned | 14561 |
| Candidates mined | 11 |
| Verified A/B (SPECIFIC) | 5 |
| Verified C (POSSIBLE) | 2 |
| Oracle review required | 4 |

## Models Used

- **Primary auditor**: deepseek/deepseek-v4-flash-0731
- **Secondary auditor**: meta-llama/llama-3.3-70b-instruct

## Construction Method

### SPECIFIC_DISCLOSURE (5 cases)
Each case was built by:
1. Streaming real patents from HuggingFace `allenai/us-patents`.
2. Detecting co-occurrence of (device, mechanism) seed terms within 1500-char window.
3. Deterministically extracting verbatim spans: device_span, mechanism_span, intervention_span, relationship_span.
4. Computing evidence_offsets (start/end positions in full patent text).
5. Classifying disclosure type with primary model (deepseek-v4-flash) AND secondary model (llama-3.3-70b).
6. Only VERIFIED A/B cases (both models agree it's a positive disclosure) are accepted.

### NOT_SPECIFIC_DISCLOSURE (5 cases)
Preserved from V1 oracle — patents where the device and mechanism do NOT co-occur in the patent text.

### POSSIBLE_RELEVANCE (5 cases)
From TYPE C candidates (terms appear but no functional relationship) and ORACLE_REVIEW_REQUIRED candidates (models disagree).

### CONTRADICTORY (5 cases)
Constructed from real patent-vs-science conflicts:
1. Drug-eluting stent vs late stent thrombosis (NEJM 2005, 2007)
2. CGM biocompatible membrane vs fibrous encapsulation (J Diabetes Sci Tech 2016)
3. Hip implant hydroxyapatite coating vs aseptic loosening (Lancet 2012)
4. IOL silver coating vs retinal toxicity (IOVS 2014)
5. Insulin pump closed-loop vs hypoglycemia (NEJM 2010)

Each contradictory case records: patent disclosure, scientific evidence, relationship, why they conflict.

## Per-Case Evidence (SPECIFIC_DISCLOSURE)

Each positive case includes:
- `patent_number`: corpus_id from HuggingFace
- `claim_number`: best estimate from regex
- `claim_text`: the claim text (or context if no claim found)
- `device_span`: verbatim text mentioning the device
- `mechanism_span`: verbatim text mentioning the mechanism
- `intervention_span`: verbatim text describing the intervention
- `relationship_span`: verbatim text describing the functional relationship
- `evidence_offsets`: dict with start, end, text, match_type for each span
- `source_hash`: SHA256 of full patent text
- `ground_truth_rationale`: deterministic from spans + offsets + claim_number

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED (only SPECIFIC/IDENTICAL kill)
- No prompt tuning to fit cases
- No corpus resumption
- No simulation start
- TEE still quarantined

## SHA256

- PATENT_ORACLE_V2.json: `e839360489e703b8d3c3564228b4c1ff3c55f2fa0569a6729ae032e534df27b4`
