# MACRO BASELINE V1 — Final Report

## Dual Denominators (NEVER MIX)

| Metric | Value |
|--------|-------|
| problem_count (all-attempt denominator) | 100 |
| successful_calls (successful-call denominator) | 100 |
| generation_failures | 0 |
| final_generation_unresolved | 0 |
| nonterminal_failure_residual | 0 (must be 0) |

## Frozen Configuration

| Field | Value |
|-------|-------|
| Prompt hash | 84fd622650e67baf |
| Temperature | 0.0 |
| Max tokens | 2000 |
| Per-call retry | 3 attempts × 90s timeout |
| Max outer rounds | 4 |
| Outer rounds executed | 1 |
| Candidate budget per problem | 1 |
| Routing policy SHA256 | 79a928166bce6fb9faf2368c9aba2ffc9f1aaeacc4e73bbade25218d4f76470d |
| Evidence packet set | frozen Phase D (100 packets) |
| Problem universe | frozen Phase C (100 problems) |

## Status Distribution (over successful-call denominator)

| Status | Count | Rate |
|--------|-------|------|
| MACRO_MECHANISM_SUPPORTED_HYPOTHESIS | 96 | 0.9600 |
| MACRO_HYPOTHESIS | 2 | 0.0200 |
| MACRO_UNSUPPORTED | 2 | 0.0200 |
| GENERATION_CALL_FAILED (transient) | 0 | n/a (generation outcome) |
| FINAL_GENERATION_UNRESOLVED (terminal) | 0 | n/a (generation outcome) |

## Primary Baseline Metric

**MACRO_MECHANISM_SUPPORTED_HYPOTHESIS_RATE** = 0.9600

## Audit Pass Rates (over all 100)

| Audit | Pass Rate |
|-------|-----------|
| problem_evidence_pass_rate | 1.0 |
| mechanism_evidence_pass_rate | 0.96 |
| transfer_supported_rate | 0.98 |
| falsifiable_hypothesis_rate | 1.0 |

## By Provider/Model

| Provider/Model | Total | Mech-Supp | Hypo | Unsupp | Wrong-Tgt | Non-Func | Failures | Unresolved | Mech-Supp Rate | Hypo Rate | Unsupp Rate | Call-Fail Rate | Median Latency | p95 Latency |
|----------------|-------|-----------|------|--------|-----------|---------|---------|-----------|----------------|-----------|-------------|---------------|-----------------|-------------|
| Mistral/mistral-medium-latest | 100 | 96 | 2 | 2 | 0 | 0 | 0 | 0 | 0.96 | 0.02 | 0.02 | 0.0 | 8.7 | 19.8 |

## Model Quality Comparison

**MODEL_QUALITY_COMPARISON = NOT_IDENTIFIABLE**

This run establishes the Macro architecture baseline. Routing is operational, not balanced for model comparison. Model quality comparison is a separate future experiment.

## Root hash

`1968b35ac5a2c09e`

## Tournament Precondition Status

- Micro-2 frozen: ✓ (100/100, 0 inconsistent)
- Macro baseline frozen: ✓ (this run, 100/100)
- Routing policy frozen: ✓ (SHA256 79a928166bce6fb9faf2368c9aba2ffc9f1aaeacc4e73bbade25218d4f76470d)
- Schemas frozen: V2 ontology frozen (Micro + Macro share same evidence ontology)
