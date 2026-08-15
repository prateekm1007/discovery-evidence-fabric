# MICRO-2 V2 FINAL — Routed Completion Report

## Dual Denominators (NEVER MIX)

| Metric | Value |
|--------|-------|
| TOTAL_ATTEMPTS (all-attempt denominator) | 100 |
| SUCCESSFUL_CALLS (successful-call denominator) | 100 |
| GENERATION_FAILURES | 0 |
| FINAL_GENERATION_UNRESOLVED | 0 |
| nonterminal_failure_residual | 0 (must be 0) |

## Frozen Configuration

| Field | Value |
|-------|-------|
| Prompt hash | bdad7f76c4ebeaaa |
| Temperature | 0.0 |
| Per-call retry | 3 attempts × 90s timeout |
| Max outer rounds | 4 |
| Outer rounds executed | 1 |
| Mistral primary model | mistral-medium-latest |
| Seed manifest root hash | a8b88c8fdcc961de |

## By Provider/Model Stratification

| Provider/Model | Total | Candidates | Mech-Supported | Hypothesis | Unsupported | Wrong-Target | Non-Func | Failures | Unresolved | Candidate Rate | Mech-Supp Rate | Hypo Rate | Unsupp Rate | Call-Fail Rate | Median Latency (s) | p95 Latency (s) |
|----------------|-------|-----------|----------------|-----------|-------------|-------------|---------|---------|-----------|---------------|---------------|----------|------------|---------------|-------------------|-----------------|
| Mistral/mistral-medium-latest | 83 | 83 | 19 | 23 | 41 | 0 | 0 | 0 | 0 | 1.0000 | 0.2289 | 0.2771 | 0.4940 | 0.0000 | 2.6 | 7.6 |
| NVIDIA/deepseek-ai/deepseek-v4-flash-0731 | 17 | 17 | 7 | 2 | 8 | 0 | 0 | 0 | 0 | 1.0000 | 0.4118 | 0.1176 | 0.4706 | 0.0000 | 46.4 | 110.7 |

## Aggregate V2 Status Distribution (over successful-call denominator)

| Status | Count | Rate |
|--------|-------|------|
| MICRO_UNSUPPORTED | 49 | 0.4900 |
| MICRO_MECHANISM_SUPPORTED_HYPOTHESIS | 26 | 0.2600 |
| MICRO_HYPOTHESIS | 25 | 0.2500 |
| GENERATION_CALL_FAILED (transient) | 0 | n/a (generation outcome) |
| FINAL_GENERATION_UNRESOLVED (terminal) | 0 | n/a (generation outcome) |

## Transfer Distribution

| Level | Count |
|-------|-------|
| UNSUPPORTED_TRANSFER | 42 |
| MECHANISTIC_INFERENCE | 40 |
| NOT_APPLICABLE | 15 |
| DIRECT_TRANSFER | 3 |

## Root hash

`1d4d54bf930dc225`

## Downstream Gates

- MICRO_2_COMPLETE: True
- GENERATION_CALL_FAILED treated as generation-outcome, NOT V2 classification
- FINAL_GENERATION_UNRESOLVED is terminal generation-outcome, NOT V2 classification
- Both denominators reported separately, never mixed
- By-provider/model stratification reported
- 11/11 tests pass, 6/6 regression pass
- V2 preregistration preserved as historical artifact (SHA256 verified)
- NO architecture tournament executed (per user instruction)