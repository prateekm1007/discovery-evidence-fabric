# MICRO-2 V2 FINAL — Reconciled Report (post forensic reconciliation)

Reconciled: 2026-08-15T03:21:04.837288+00:00

## Reconciliation Summary

- Records audited: 100
- Inconsistent before: 2
- Corrections applied: 8
- Inconsistent after: 0
- MICRO_2_CLASSIFICATION_CONSISTENCY_CLOSED: True

## Dual Denominators

| Metric | Value |
|--------|-------|
| all-attempt denominator | 100 |
| successful-call denominator | 100 |
| generation_failure_count | 0 |
| final_generation_unresolved_count | 0 |

## Status Distribution (post-reconciliation)

| Status | Count | Rate |
|--------|-------|------|
| MICRO_HYPOTHESIS | 23 | 0.2300 |
| MICRO_MECHANISM_SUPPORTED_HYPOTHESIS | 26 | 0.2600 |
| MICRO_UNSUPPORTED | 51 | 0.5100 |

## Audit Pass Rates (over all 100 records)

| Audit | Pass Rate |
|-------|-----------|
| problem_evidence_pass_rate | 1.0 |
| mechanism_evidence_pass_rate | 0.26 |
| mechanism_evidence_pass_or_partial_rate | 0.93 |
| transfer_supported_rate | 0.43 |
| falsifiable_hypothesis_rate | 0.97 |
| hypothesis_boundary_pass_rate | 1.0 |
| provenance_pass_rate | 1.0 |

## By Provider/Model

| Provider/Model | Total | Mech-Supp | Hypo | Unsupp | Mech-Supp Rate | Hypo Rate | Unsupp Rate | PE Pass | ME Pass | Tr Supp | Falsifiable | Median Latency | p95 Latency |
|----------------|-------|-----------|------|--------|----------------|-----------|-------------|---------|---------|---------|-------------|-----------------|-------------|
| Mistral/mistral-medium-latest | 83 | 19 | 23 | 41 | 0.2289 | 0.2771 | 0.494 | 1.0 | 0.2289 | 0.506 | 0.9639 | 2.6 | 7.6 |
| NVIDIA/deepseek-ai/deepseek-v4-flash-0731 | 17 | 7 | 0 | 10 | 0.4118 | 0.0 | 0.5882 | 1.0 | 0.4118 | 0.0588 | 1.0 | 46.4 | 110.7 |

## Model Performance Note

- MISTRAL_OPERATIONALLY_SUPERIOR: True
- MODEL_QUALITY_WINNER: UNDETERMINED
- Reason: Mistral showed higher throughput (2.6s median vs 46.4s), lower p95 latency (7.6s vs 110.7s), and 100% completion reliability (0 failures on 83 seeds vs 7/24 NVIDIA failures before fallback). However, no controlled downstream quality comparison has been run. Model quality winner remains UNDETERMINED pending a controlled head-to-head with frozen seeds, frozen prompt, frozen ontology, and blinded downstream evaluation.

## Root hash
`1d4d54bf930dc225`
