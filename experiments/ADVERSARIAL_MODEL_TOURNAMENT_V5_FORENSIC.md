# Adversarial Model Tournament V5 Forensic

**Adjudicator Selection: BLOCKED_INSUFFICIENT_COVERAGE**

## Contract Effect: CONFIRMED

The V2 three-state neutral contract eliminated systematic false kills:

| Metric | V1 (binary) | V2 (three-state) |
|--------|-------------|-------------------|
| Kill bias rate | 0.7143 | 0.0 |
| Avg false kill | 0.6043 | 0.0 |
| Avg false survival | 0.0 | 0.0 |

H1 is confirmed: the evaluator contract was the root cause, not model capacity.

## Why Selection Is Invalid

Model A (meta/llama-3.1-8b-instruct) achieved:
- Determinate accuracy: 1.0 (5/5 correct)
- Coverage: **0.119** (only 5/42 determinate)
- Abstention rate: **0.881** (37/42 INSUFFICIENT_EVIDENCE)

The model abstains on 88% of cases. The 5 determinate cases are all SPECIFIC_PRIOR_ART (correctly KILLed 5/5). **Zero coverage** on 6 of 7 categories.

## Per-Category Coverage

| Category | Determinate | Abstentions | Coverage |
|----------|------------|-------------|----------|
| MECHANISM_VALID | 0 | 6 | 0.0 |
| TRANSFER_VALID | 0 | 6 | 0.0 |
| NON_BOUNDARY | 0 | 6 | 0.0 |
| BOUNDARY_CONDITION | 0 | 6 | 0.0 |
| SPECIFIC_PRIOR_ART | 5 | 1 | 0.833 |
| TOPICAL_ONLY_PRIOR_ART | 0 | 6 | 0.0 |
| COMBINATION_SUPPORTED_NOT_SUPPORTED | 0 | 6 | 0.0 |

The model only adjudicates when prior_art_state=SPECIFIC_DISCLOSURE. For all other categories, it defaults to INSUFFICIENT_EVIDENCE.

## Abstention Quality

- Unjustified abstentions (GOLD has determinate verdict, model abstained): 37
- Correct abstentions (evidence genuinely insufficient): 0
- Unjustified abstention rate: 0.881

All 37 abstentions are on cases where the GOLD oracle has a determinate expected verdict.

## Gate Defect

The V5 acceptance gate did not require minimum coverage. A model could achieve 100% accuracy by abstaining on everything except 1 case.

**Fix required**: Add preregistered minimum coverage threshold, per-category coverage requirements, and abstention quality metrics.

## V5 Results Preserved

All V5 results are preserved unchanged. This forensic does not delete or rewrite any V5 artifacts.
