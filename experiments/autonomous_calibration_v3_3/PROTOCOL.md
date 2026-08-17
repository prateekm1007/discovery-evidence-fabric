# AUTONOMOUS CALIBRATION V3.3 — PROTOCOL

**Status**: `CALIBRATION_BLOCKED` (pre-registered, frozen before inference)
**Base commit**: `38df888`
**Protocol SHA-256**: `1c609a013f80dbaa541a8b279064f7511b96333e912bb14542016e76a15af27b`
**Created**: 2026-08-17

## Why V3.3

V3.2 was the first valid evidence-conditioned calibration (65% accuracy, 10%
false-elite, 10% false-reject), but it has critical defects:

1. **CLAIM_IDENTITY_FAILURE** (CV2_A_01, CV2_A_02): PatSnap returned claims for
   different patents than the case metadata described.
2. **103_FAILURE** (15% accuracy): OBVIOUSNESS_ADVERSARY is too lenient and
   doesn't distinguish COULD from WOULD.
3. **SEARCH_FAILURE** (70% recall): Not all families contributing to recall.

V3.3 fixes these three defects.

## V3.2 Frozen (preserved, not overwritten)

| Metric | Value |
|---|---|
| Accuracy | 65% |
| False-elite rate | 10% |
| False-reject rate | 10% |
| Cited-art recall | 100% |
| Search recall | 70% |
| 102 accuracy | 75% |
| 103 accuracy | 15% |
| Rescue recognition | 100% |

## V3.3 Critical Fixes

### Fix 1: CLAIM_IDENTITY_VALIDATION

Before ANY claim enters the pipeline, validate:
- case patent number
- retrieved patent number
- title
- assignee
- priority date
- claim text

States: `IDENTITY_CONFIRMED` / `IDENTITY_MISMATCH` / `IDENTITY_UNRESOLVED`

If `IDENTITY_MISMATCH`: STOP CASE. Do NOT run 102/103/commercial/rescue.
Status: `EVIDENCE_CORRUPTED`.

### Fix 2: claim_subject_fingerprint

Build fingerprint from:
- title
- abstract
- claim terminology
- device class
- technical mechanism

Compare to case metadata. If similarity is materially inconsistent:
`CLAIM_IDENTITY_UNRESOLVED`.

### Fix 3: 103 Rebuild

**Explicit 103 evidence object:**
- closest_prior_art
- differences
- objective_technical_problem
- secondary_reference
- motivation
- technical_effect
- expectation_of_success
- teaching_away
- could
- would
- why
- hindsight

**COULD ≠ WOULD rule:**
- COULD = capability
- WOULD = evidence of motivation + expectation of success
- `OBVIOUSNESS_RISK` requires `WOULD=YES` AND `MOTIVATION_SUPPORTED=TRUE` AND
  `EXPECTED_SUCCESS_SUPPORTED=TRUE`

**Closest prior art selection:**
- Similar purpose/effect OR same/closely related field
- Minimal structural/functional modification
- Do NOT select a convenient patent merely because it shares one keyword

**103 combination matrix:**
- REFERENCE_A + REFERENCE_B
- ELEMENTS_FROM_A + ELEMENTS_FROM_B
- MOTIVATION_TO_COMBINE
- EXPECTED_BENEFIT
- TECHNICAL_COMPATIBILITY
- TEACHING_AWAY
- PRE_FILING_REASON_TO_COMBINE

**103 two-pass anti-hindsight:**
- Pass A: Hide the final invention solution. Ask: "What would a skilled person
  do to solve the objective problem?"
- Pass B: Reveal the actual claimed invention. Compare.
- Large divergence → `HINDSIGHT_RISK_HIGH`

**Technical effect:**
- effect_source + effect_strength + documented/inferred/hypothesized
- If unexpected and technically significant, require evidence linking effect
  to claimed feature
- Do NOT use commercial success as substitute

### Fix 4: 102 Remains Strict

- One reference must disclose all limitations + required arrangement
- Inherency requires necessity (MPEP §2131)

### Fix 5: Model Role Separation

OBVIOUSNESS_ADVERSARY must NOT receive the generator's narrative rationale.
It receives:
- canonical claim
- prior art
- claim mappings
- technical evidence

It constructs its own rationale.

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

If 103 remains < 80%: `CALIBRATION_BLOCKED`.

## Output Artifacts

`PROTOCOL.json` · `PROTOCOL.sha256` · `PROTOCOL.md` · `CLAIM_IDENTITY_AUDIT.json` ·
`SEARCH_RECALL_ANALYSIS.json` · `102_RESULTS.json` · `103_RESULTS.json` ·
`HINDSIGHT_RESULTS.json` · `ERROR_ANALYSIS.json` · `METRICS.json` · `REPORT.md`

## Stop Condition

DO NOT RUN 50→5.

STOP FOR CEO AUDIT.
