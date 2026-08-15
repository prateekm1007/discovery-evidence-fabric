# MACRO/MICRO RECURSIVE EXPERIMENT V1 — PRE-REGISTRATION

## Status: PRE-REGISTERED (not yet executed)

## Date: 2026-08-15

## Experiment Arms

| Arm | Description |
|-----|-------------|
| M0 | MACRO_ONLY — broad evidence discovery + synthesis |
| M1 | MICRO_ONLY — experience-constrained invention |
| M2 | MACRO_TO_MICRO — Macro mechanisms fed to Micro |
| M3 | MICRO_TO_MACRO — Micro problems fed to Macro |
| M4 | RECURSIVE_MACRO_MICRO — alternating frozen knowledge exchange |
| M4B | BUDGET_MATCHED_NON_RECURSIVE_CONTROL — same info, non-recursive |

## No Same-Round Leakage

M4 operates in frozen rounds:
- Round 0: Macro0 and Micro0 operate independently. Freeze outputs.
- Round 1: Macro1 uses ONLY frozen Micro0. Micro1 uses ONLY frozen Macro0. Freeze.
- Round 2: Macro2 uses ONLY frozen Micro1. Micro2 uses ONLY frozen Macro1.

No engine may see the other's current-round output.

## M4B Control

M4B receives the same information as M4 Round 1 (Macro mechanisms + Micro problems)
but presented non-recursively in one context. Recursive lift is valid ONLY if M4 > M4B.

## Primary Endpoint

QUALIFIED_CANDIDATE_RATE = AIC_count / total_attempted_seeds

## Secondary Endpoints

- SIMULATION_READY_RATE
- SIMULATION_SURVIVAL_RATE
- EVIDENCE_SURVIVAL
- SPECIFIC_PRIOR_ART_SURVIVAL
- ADVERSARIAL_SURVIVAL

## Cooperative Lift

COOPERATIVE_LIFT = M4_qualified_rate - max(M0, M1, M2, M3, M4B)

## Dead-Loop Test

The recursive loop is DEAD if after the preregistered minimum rounds:
- mechanism distribution does not shift beyond baseline variance margin
- AND Macro search/query distribution does not materially shift
- AND qualified-candidate rate does not improve versus M4B

## Loop Outcome States

- RECURSIVE_LIFT_CONFIRMED
- RECURSIVE_LIFT_NOT_DETECTED
- INFORMATION_BUDGET_EFFECT_ONLY
- RECURSIVE_LOOP_DEAD
- INSUFFICIENT_POWER

## Execution Conditions

Execution begins ONLY after:
1. MICRO-2 complete (all 100 seeds with V2 ontology)
2. MACRO baseline complete
3. Both output schemas frozen

## Evolutionary Framing

This experiment uses EVOLUTIONARY_ITERATION:
variation → context-specific selection → retained knowledge → altered search → new variation

GEB/Hofstadter is inspiration only, not scientific evidence.

## Frozen Configuration (when executed)

- Same evaluation gates across all arms
- Same evidence standard
- Same prior-art evaluator (frozen mistral-large-latest)
- Same adversarial evaluator (7 dimensions)
- Same simulation readiness contract
- Same candidate budget where possible
- Same model (deepseek-v4-flash-0731 via NVIDIA)
- Same temperature (0.0)
