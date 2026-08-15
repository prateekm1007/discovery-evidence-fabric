# Adversarial Model Tournament V6 Protocol

**Frozen BEFORE first V6 API call.**

## V5 Disposition
- Contract effect: CONFIRMED (kill bias eliminated)
- Kill bias reduction: CONFIRMED (0.7143 → 0.0)
- Adjudicator selection: BLOCKED_INSUFFICIENT_COVERAGE
- V5 coverage: 0.119 (model abstained on 88% of cases)

## Coverage Gate (Preregistered)

| Gate | Threshold | Justification |
|------|-----------|---------------|
| Overall coverage | ≥ 50% | Model must adjudicate at least half the cases. Prevents passing by abstention. |
| Critical-category coverage | ≥ 30% per category | Model must adjudicate at least ~2/6 cases in each critical category. |

## New Acceptance Gate (A-J, ALL required)

| Condition | Requirement |
|-----------|-------------|
| A | Determinate accuracy ≥ 80% |
| B | False-kill rate ≤ 20% |
| C | False-survival rate ≤ 20% |
| D | Overall coverage ≥ 50% |
| E | Critical-category coverage ≥ 30% |
| F | Critical-category determinate accuracy ≥ 70% |
| G | Evaluator failure rate ≤ 20% |
| H | Zero fabricated evidence |
| I | Zero fabricated patent citations |
| J | Zero prior-art firewall violations |

## Abstention Quality
- ABSTENTION_CORRECT: INSUFFICIENT_EVIDENCE when evidence genuinely insufficient
- ABSTENTION_INCORRECT: INSUFFICIENT_EVIDENCE when GOLD has clear expected verdict
- unjustified_abstention_rate reported per model

## Three-State Confusion Matrix
3×3 matrix per model: TRUE (SURVIVE/INSUFFICIENT/KILL) × PREDICTED (PASS/INSUFFICIENT/KILL)

## Unchanged
- 42-case GOLD oracle (root 26f8f51e6d355e84)
- V2 three-state contract (SHA 973ab72...)
- Same 6 models
- Same temperature (0.0), max_tokens (8000)
- V5 results preserved
- LENS_UNAVAILABLE preserved (Google Patents = primary)
