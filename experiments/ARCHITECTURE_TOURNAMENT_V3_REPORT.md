# Architecture Tournament V3 — Final Report

Generated: 2026-08-15T06:55:42.526458+00:00

Root hash: `4d10e01c5c246133`


## Architecture Scoreboard

| Arm | Architecture | AICs | AIC Yield | Evidence Pass | Prior Art Pass | Adversarial Pass | Sim Ready | Median Latency | Total Tokens |
|-----|-------------|------|-----------|---------------|----------------|-----------------|-----------|----------------|-------------|
| M0 | MACRO_ONLY | 5 | 0.0500 | 94/100 | 94/100 | 5/100 | n/a | 3.9s | 391,233 |
| M1 | MICRO_ONLY | 0 | 0.0000 | 95/100 | 97/100 | 0/100 | n/a | 2.5s | 96,092 |
| M2 | MACRO_TO_MICRO | 0 | 0.0000 | 93/100 | 98/100 | 0/100 | n/a | 2.4s | 107,746 |
| M3 | MICRO_TO_MACRO | 0 | 0.0000 | 93/100 | 96/100 | 1/100 | n/a | 3.8s | 395,119 |
| M4 | RECURSIVE_MACRO_MICRO | 0 | 0.0000 | 95/100 | 97/100 | 0/100 | n/a | 3.5s | 248,765 |
| M4B | INFORMATION_MATCHED_NON_RECURSIVE | 1 | 0.0100 | 91/100 | 99/100 | 1/100 | n/a | 3.8s | 420,670 |
| M4C | COMPUTE_MATCHED_NON_RECURSIVE | 3 | 0.0300 | 94/100 | 91/100 | 3/100 | n/a | 3.9s | 388,279 |

## Winner Determination

**Outcome: NO_WINNER**

Reason: M4 does not exceed either control (M4B=0.01, M4C=0.03, M4=0.0). No recursive lift detected.

Details: {
  "m4_vs_m4b": false,
  "m4_vs_m4c": false
}


## Recursive Lift Analysis

- M4 AIC yield: 0.0000
- M4B AIC yield: 0.0100
- M4C AIC yield: 0.0300
- M4 > M4B: False
- M4 > M4C: False
- Best independent baseline (max M0-M3): 0.0500

## Per-Arm Status Distribution

### M0 — MACRO_ONLY

- Total candidates: 100
- Terminal: 100
- AICs: 5
- Generation failures: 0
- Unresolved: 0
- Status distribution: {'MACRO_MECHANISM_SUPPORTED_HYPOTHESIS': 96, 'MACRO_HYPOTHESIS': 2, 'MACRO_UNSUPPORTED': 2}
- Median latency: 3.9s, p95: 4.7s
- Total tokens: 391,233 (input: 346,277, output: 44,956)
- Synthesis calls: 100

### M1 — MICRO_ONLY

- Total candidates: 100
- Terminal: 100
- AICs: 0
- Generation failures: 0
- Unresolved: 0
- Status distribution: {'MICRO_MECHANISM_SUPPORTED_HYPOTHESIS': 95, 'MICRO_WRONG_TARGET': 1, 'MICRO_UNSUPPORTED': 4}
- Median latency: 2.5s, p95: 3.3s
- Total tokens: 96,092 (input: 65,226, output: 30,866)
- Synthesis calls: 100

### M2 — MACRO_TO_MICRO

- Total candidates: 100
- Terminal: 100
- AICs: 0
- Generation failures: 0
- Unresolved: 0
- Status distribution: {'MICRO_MECHANISM_SUPPORTED_HYPOTHESIS': 93, 'MICRO_WRONG_TARGET': 3, 'MICRO_HYPOTHESIS': 3, 'MICRO_UNSUPPORTED': 1}
- Median latency: 2.4s, p95: 3.1s
- Total tokens: 107,746 (input: 76,220, output: 31,526)
- Synthesis calls: 100

### M3 — MICRO_TO_MACRO

- Total candidates: 100
- Terminal: 100
- AICs: 0
- Generation failures: 0
- Unresolved: 0
- Status distribution: {'MACRO_MECHANISM_SUPPORTED_HYPOTHESIS': 94, 'MACRO_HYPOTHESIS': 2, 'MACRO_WRONG_TARGET': 2, 'MACRO_UNSUPPORTED': 2}
- Median latency: 3.8s, p95: 4.9s
- Total tokens: 395,119 (input: 350,340, output: 44,779)
- Synthesis calls: 100

### M4 — RECURSIVE_MACRO_MICRO

- Total candidates: 100
- Terminal: 100
- AICs: 0
- Generation failures: 0
- Unresolved: 0
- Status distribution: {'MACRO_MECHANISM_SUPPORTED_HYPOTHESIS': 48, 'MICRO_UNSUPPORTED': 3, 'MICRO_MECHANISM_SUPPORTED_HYPOTHESIS': 47, 'MACRO_NON_FUNCTIONAL_CHANGE': 1, 'MACRO_UNSUPPORTED': 1}
- Median latency: 3.5s, p95: 4.7s
- Total tokens: 248,765 (input: 210,000, output: 38,765)
- Synthesis calls: 100

### M4B — INFORMATION_MATCHED_NON_RECURSIVE

- Total candidates: 100
- Terminal: 100
- AICs: 1
- Generation failures: 0
- Unresolved: 0
- Status distribution: {'MACRO_MECHANISM_SUPPORTED_HYPOTHESIS': 91, 'MACRO_WRONG_TARGET': 4, 'MACRO_HYPOTHESIS': 2, 'MACRO_UNSUPPORTED': 2, 'MACRO_NON_FUNCTIONAL_CHANGE': 1}
- Median latency: 3.8s, p95: 4.9s
- Total tokens: 420,670 (input: 376,705, output: 43,965)
- Synthesis calls: 100

### M4C — COMPUTE_MATCHED_NON_RECURSIVE

- Total candidates: 100
- Terminal: 100
- AICs: 3
- Generation failures: 0
- Unresolved: 0
- Status distribution: {'MACRO_MECHANISM_SUPPORTED_HYPOTHESIS': 95, 'MACRO_HYPOTHESIS': 3, 'MICRO_MECHANISM_SUPPORTED_HYPOTHESIS': 1, 'MACRO_UNSUPPORTED': 1}
- Median latency: 3.9s, p95: 4.7s
- Total tokens: 388,279 (input: 342,542, output: 45,737)
- Synthesis calls: 200

## Frozen Configuration

- Routing policy SHA256: `79a928166bce6fb9faf2368c9aba2ffc9f1aaeacc4e73bbade25218d4f76470d`
- Problem corpus root: `40adb5d0157f624a`
- Evidence packets root: `b9faf80e8aabf16b`
- Ontology: V2_FROZEN
- Temperature: 0.0
- Model: mistral-medium-latest (primary), deepseek-ai/deepseek-v4-flash-0731 (fallback)
- Candidate budget: 100 per arm, 1 per problem

## Downstream Gates (same for all arms)

1. Target alignment (rule-based)
2. Evidence verification (rule-based, span + mechanism check)
3. Prior-art search (Europe PMC API)
4. Adversarial evaluation (LLM, 7 dimensions: mechanism, transfer, obviousness, prior_art, contradiction, boundary, feasibility)
5. AIC classification (rule-based: all gates must pass)

## AIC Definition

A candidate becomes an AUTOMATED_INVENTION_CANDIDATE only if:
- Evidence passes (verified spans + mechanism evidence)
- Target aligned
- Prior-art passes (NO_MATCH_FOUND or POSSIBLE_RELEVANCE)
- All 7 adversarial dimensions pass (SURVIVED)
- Falsification test exists
- Provenance complete

## Model Quality Comparison

**MODEL_QUALITY_COMPARISON = NOT_IDENTIFIABLE**

Routing policy was the constant across all arms. Model quality comparison is a separate future experiment.

## Tournament Gate Status

- All arms 100/100: True
- All candidates terminal: True
- Routing policy frozen: True
- Ontology frozen: True

## Provenance

Every candidate carries: architecture_origin, arm, round, problem_id, provider, model, prompt_hash, response_hash, routing_policy_sha256, source_ids, evidence spans, prior_art_state, adversarial_state, aic_state, simulation_state.
