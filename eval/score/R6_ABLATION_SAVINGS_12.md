# R6 A1 — measured ablation savings (12-problem plan)

Deterministic arithmetic over committed run ledgers; zero LLM spend.
Source run: `eval\runs\2505e43b9003` (commit `2505e43b9003`).

A stage-memo hit saves the measured LLM calls and provider attempts of every stage STRICTLY UPSTREAM of the disabled stage. Downstream counts are shown as recompute evidence, not subtracted.

| arm | upstream stages reused | calls saved (measured subtotal) | provider attempts saved (measured subtotal) | problems measured |
|---|---:|---:|---:|---:|
| `no_RETRIEVE` | 0 | 0 | 0 | 12/12 |
| `no_SYNTHESIZE` | 3 | 0 | 0 | 10/12 |
| `no_MECHANISM_SPACE` | 5 | 20 | 16 | 10/12 |
| `no_COLLISION` | 6 | 43 | 21 | 10/12 |
| `no_ATTACK` | 8 | 43 | 21 | 10/12 |
| `no_COMPOSE` | 15 | 83 | 41 | 10/12 |
| `no_PHYSICS` | 7 | 43 | 21 | 10/12 |
| `no_CONTRADICTION` | 9 | 68 | 36 | 10/12 |
| `no_KILLER_EXPERIMENT` | 10 | 68 | 36 | 10/12 |
| `no_ADJUDICATION` | 11 | 68 | 36 | 10/12 |
| `no_RANK` | 14 | 68 | 36 | 10/12 |

## Per-problem measured calls and attempts

| problem | measured logical (pre-rank+compose) | measured provider attempts (pre-rank+compose) | not-measured stages |
|---|---:|---:|---|
| `bench-p02-leadacid-grid-corrosion` | 8 | 8 | COMPOSE |
| `bench-p05-bridge-bearing-aging` | 7 | 7 | COMPOSE |
| `bench-p09-packaging-barrier` | 8 | 6 | COMPOSE |
| `dev-fu-001-bearing-spalling` | 2 | 0 | ATTACK, COLLISION, COMPOSE, MECHANISM_SPACE, PHYSICS, RANK, RETRIEVE, SYNTHESIZE, VERIFY |
| `dev-fu-002-hvac-filter` | 7 | 2 | COMPOSE, MECHANISM_SPACE, SYNTHESIZE |
| `dev-fu-003-motor-insulation` | 0 | 0 | ATTACK, COLLISION, COMPOSE, MECHANISM_SPACE, PHYSICS, RANK, RETRIEVE, SYNTHESIZE, VERIFY |
| `dev-fu-004-fouling` | 13 | 7 | COMPOSE, MECHANISM_SPACE |
| `dev-fu-005-bridge-bearing` | 11 | 5 | COMPOSE, MECHANISM_SPACE |
| `dev-fu-006-pump-cavitation` | 8 | 3 | COMPOSE, MECHANISM_SPACE, SYNTHESIZE |
| `eval-new02-slipring-predictor` | 7 | 6 | COMPOSE |
| `eval-new06-bearing-vibration-predictor` | 9 | 8 | COMPOSE |
| `eval-new09-hvac-filter-predictor` | 5 | 6 | COMPOSE |

## Disclosures

- A stage-memo hit requires byte-identical canonical upstream state; this report sums the measured base-run counts of the upstream chain. It does not claim a post-ablation downstream vector.
- COMPOSE is absent from this pre-compose-era run root (ANSWER_COMPOSED.json missing): its row is NOT_MEASURED. Arms whose upstream chain excludes COMPOSE still have complete upstream savings; no_COMPOSE's upstream is complete because COMPOSE is the disabled stage.
- dev-fu-001-bearing-spalling and dev-fu-003-motor-insulation carry only partial pipeline stage records in this run root; their dependent arm values are NOT_MEASURED, never zero. The 12-problem plan therefore has 10 measured problems for most arms, disclosed per row.
- Post-rank ledger stages (POST_RANK_*, IMPROVE) are measured in the per-problem totals but excluded from the leave-one-out DAG: their conditional dependence on a disabled pre-rank stage is not modelled, never silently assumed.
- FREEZE, PREMISE_GATE and the post-rank deterministic chain CONTRADICTION..NEXT_BEST_ACTION are outside r6_call_budget's EXPECTED_STAGES; the committed A5 plan vector records 0 LLM calls for each. They enter this arithmetic as LABELLED structural zeros, not as measured provider calls.
- Provider attempts are quota cost (retries, failures, fallbacks included), separate from the logical-call design budget; both are reported.
- No live run was executed for this report. The breaker/governor attempt outcomes under the new code are proven by tests, not by a fresh provider run.
