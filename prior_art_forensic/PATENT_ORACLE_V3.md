# PATENT ORACLE V3 — Deterministically Provable Specific Disclosure

## Oracle Version: V3
## Created: 2026-08-14T16:45:46.771454+00:00
## Source Commit: c4eae5ccc3a8527f6a9dea94171435d9eb74ece7

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
| Patents scanned | 31435 |
| Candidates mined | 20 |
| Verified A/B (SPECIFIC) | 6 |
| Deterministic validation failed | 13 |
| Oracle review required | 1 |

## Models Used (FREE models per user instruction)

- **Primary auditor**: deepseek/deepseek-v4-flash-0731
- **Secondary auditor**: qwen/qwen-2.5-72b-instruct
- **NO Gemini** (any version) was used

## Deterministic Validator (v3_deterministic)

Each SPECIFIC_DISCLOSURE case passes ALL of these checks:
1. device_span exists
2. mechanism_span exists
3. relationship_span exists
4. all spans exist in source text
5. offsets reproduce exact text
6. relationship_span connects device and mechanism (contains functional language + at least one term, with the other nearby)
7. no newlines in device_span or mechanism_span

## Evidence Graph (each SPECIFIC_DISCLOSURE case)

Every positive case contains:
- `device_span` (verbatim)
- `mechanism_span` (verbatim)
- `relationship_span` (verbatim)
- `device_span_hash` (SHA256)
- `mechanism_span_hash` (SHA256)
- `relationship_span_hash` (SHA256)
- `claim_number`
- `section_id`
- `char_start` / `char_end`
- `evidence_offsets` (start, end, text, match_type for each span)
- `source_hash` (SHA256 of full patent text)
- `deterministic_validation` (full validation result)
- `primary_model_audit` (VALID_SPECIFIC / NOT_SPECIFIC / UNSTABLE)
- `secondary_model_audit` (VALID_SPECIFIC / NOT_SPECIFIC / UNSTABLE)

## Construction Method

### SPECIFIC_DISCLOSURE (5 cases)
1. Mined from HuggingFace allenai/us-patents via (device, mechanism) co-occurrence within 2000-char window
2. Deterministic span extraction (device, mechanism, intervention, relationship)
3. Deterministic validation (7 checks per spec Section 3)
4. Dual-model secondary audit (deepseek + qwen)
5. Only VERIFIED_WITH_UNSTABLE or VERIFIED cases promoted (both models must say VALID_SPECIFIC, or one VALID + one UNSTABLE)
6. If either model says NOT_SPECIFIC → ORACLE_REVIEW_REQUIRED, excluded

### NOT_SPECIFIC_DISCLOSURE (5 cases)
Preserved from V1 oracle — patents where device and mechanism do NOT co-occur.

### POSSIBLE_RELEVANCE (5 cases)
From DETERMINISTIC_VALIDATION_FAILED candidates — terms appear but relationship not provable.

### CONTRADICTORY (5 cases)
Constructed from real patent-vs-science conflicts with:
- Actual patent disclosure (with claim text)
- Actual scientific evidence (with citations: NEJM, Lancet, IOVS, J Diabetes Sci Tech)
- Contradictory relationship
- Why they conflict

## Governance Invariants (all preserved)

- 80% threshold: UNCHANGED
- Prior-art kill semantics: UNCHANGED
- No evaluator prompt tuning
- No corpus resumption
- No simulation start
- TEE still quarantined

## SHA256

- PATENT_ORACLE_V3.json: `2ce663b9a735441212e2044d9eb671a626c492fa31223e11beaf02bae2e8b14e`
