# MICRO-2 Early Forensic — Grounding Correction

## Measurement Correction

The original MICRO_CANDIDATE rate of 92.9% was inflated because the grounding
check only verified that cited source spans existed in the evidence — it did NOT
verify that the spans actually supported the MECHANISM claims.

## Corrected Status Distribution

| Status | Count | Rate |
|--------|-------|------|
| MICRO_CANDIDATE_EVIDENCE_GROUNDED | 1 | 0.0625 |
| MICRO_CANDIDATE_INFERRED | 3 | 0.1875 |
| MICRO_UNSUPPORTED | 11 | 0.6875 |
| MICRO_WRONG_TARGET | 0 | 0.0000 |
| MICRO_NON_FUNCTIONAL_CHANGE | 0 | 0.0000 |
| GENERATION_CALL_FAILED | 1 | 0.0625 |

## Corrected Metrics

| Metric | Value |
|--------|-------|
| RAW_CANDIDATE_RATE | 0.2500 |
| EVIDENCE_GROUNDED_RATE | 0.0625 |
| INFERRED_CANDIDATE_RATE | 0.1875 |
| UNSUPPORTED_RATE | 0.6875 |
| WRONG_TARGET_RATE | 0.0000 |
| NON_FUNCTIONAL_RATE | 0.0000 |

## Key Finding

The original 92.9% MICRO_CANDIDATE rate breaks down into:
- **6.2%** EVIDENCE_GROUNDED (direct mechanism support)
- **18.8%** INFERRED (indirect/tangential evidence support)
- **68.8%** UNSUPPORTED (source spans don't support mechanism claims)

The Micro engine generates strong hypotheses (INFERRED) but most "grounded"
candidates are actually model inferences that reference real evidence tangentially,
not evidence that directly supports the proposed mechanism.

## Claim Type Analysis

| Claim Type | Description |
|-----------|-------------|
| EVIDENCE_DERIVED_FACT | Claim directly traceable to source text |
| MODEL_INFERENCE | Model's reasoning, not directly in source |
| PROPOSED_PARAMETER | Engineering parameter not in source |

## Proposed Parameters

Most candidates contain proposed engineering parameters (e.g., "2.0V", "10 million cycles",
"400 nm") that are NOT in the source evidence. These are correctly labeled as
PROPOSED_PARAMETER — they are hypotheses, not evidence-derived values.

## No Prior-Art or Adversarial

This forensic correction does NOT run prior-art or adversarial evaluation.
MICRO_CANDIDATE_INFERRED candidates are strong hypotheses but NOT evidence-grounded.
