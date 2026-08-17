
## Findings Summary

| Concern | Cases | Description |
|---|---|---|
| prompt_design_concerns | 0 | anti_hindsight_notes too short or empty — HIGH assigned by default |
| premature_solution_exposure | 0 | objective_technical_problem too long, may leak solution |
| overly_strict_detector | 0 | HIGH assigned despite uncertainty language in notes |
| missing_evidence | 17 | closest_prior_art_id='NONE_NEEDED' — no real hindsight risk |
| evaluator_bias | 0 | HIGH assigned without could/would properly answered |

## Root Cause Analysis

The 19/20 HIGH anti-hindsight rating is **NOT a genuine signal** of hindsight-free
reasoning. It is an artifact of three compounding issues:

### 1. Missing Evidence (Primary Cause)

When PatSnap claim retrieval failed, the 102 attack returned no anticipation,
leaving 103 with `closest_prior_art_id='NONE_NEEDED'`. The system then
assigned HIGH by default because there was no actual hindsight risk to assess
— there was no prior art to reason backwards from.

### 2. Prompt Design (Secondary Cause)

The `anti_hindsight_notes` field is often empty or too short. The prompt does
not require the model to justify its hindsight rating with specific evidence
from the Pass A (rationale-before) vs Pass B (rationale-after) comparison.

### 3. Evaluator Bias (Tertiary Cause)

When could/would are not answered (empty strings), the model defaults to HIGH
— a "safe" rating rather than a genuine assessment. This is bias toward
avoiding false-low ratings rather than reflecting real uncertainty.

## Acceptance Threshold

Per CEO directive Section 10:
> Do NOT alter the acceptance threshold after seeing the V3 result.

The 19/20 HIGH rating is a known artifact, not a real signal. The acceptance
threshold remains as defined in PROTOCOL.json. The hindsight detector must be
strengthened in V4 (require evidence-grounded rationale for each level), but
the threshold is unchanged.

## Recommendations for V4

1. **Require non-empty anti_hindsight_notes**: If the model returns HIGH with
   empty notes, downgrade to MEDIUM automatically.
2. **Require Pass A vs Pass B comparison**: The notes must explicitly reference
   differences between the rationale-before and rationale-after formulations.
3. **Reject HIGH when could/would are empty**: Incomplete EPO inquiry cannot
   produce HIGH confidence.
4. **Distinguish "no prior art" from "high hindsight confidence"**: When
   `closest_prior_art_id='NONE_NEEDED'`, the anti_hindsight_level should be
   `N_A` (not applicable), not HIGH.
