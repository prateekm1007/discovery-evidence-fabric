# MACRO/MICRO RECURSIVE EXPERIMENT V2 — PRE-REGISTRATION

## Status: PRE-REGISTERED (not yet executed)

## Date: 2026-08-15

## Arms

| Arm | Description |
|-----|-------------|
| M0 | MACRO_ONLY |
| M1 | MICRO_ONLY |
| M2 | MACRO_TO_MICRO |
| M3 | MICRO_TO_MACRO |
| M4 | RECURSIVE_MACRO_MICRO |
| M4B | INFORMATION_MATCHED_NON_RECURSIVE_CONTROL |
| M4C | COMPUTE_MATCHED_NON_RECURSIVE_CONTROL |

## Controls

- **M4B**: Same information as M4 Round 1, non-recursive. Tests recursion vs information presentation.
- **M4C**: Same compute/token/synthesis budget as M4 total, non-recursive. Tests recursion vs computation budget.

## Winner Logic

M4 must exceed best independent baseline by >=5pp AND beat BOTH M4B and M4C.

| Condition | Outcome |
|-----------|---------|
| M4 > M4B AND M4 > M4C | RECURSIVE_LIFT_CANDIDATE |
| M4 <= M4B | INFORMATION_BUDGET_EFFECT_ONLY |
| M4 <= M4C | COMPUTE_BUDGET_EFFECT_ONLY |

## Compute Ledger

Every arm records: problem_count, candidate_count, retrieval_calls, synthesis_calls, input_tokens, output_tokens, total_tokens, wall_clock_time, source_count, context_tokens.

## Dead Loop Test

The recursive loop is DEAD if:
- mechanism distribution unchanged beyond baseline variance
- AND Macro search/query distribution unchanged
- AND qualified-candidate rate not improved vs M4B/M4C

## Execution Conditions

1. MICRO-2 complete (all 100 seeds)
2. MACRO baseline complete
3. Both output schemas frozen
4. Single model frozen across all arms

## Framing

EVOLUTIONARY_ITERATION: variation → selection → retention → altered search → new variation.

GEB/Hofstadter is inspiration only.
