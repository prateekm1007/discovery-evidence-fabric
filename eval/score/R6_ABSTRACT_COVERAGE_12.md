# R6 A3/A4 — per-problem abstract coverage + refined queries

Deterministic over committed envelopes and committed problem facts; zero LLM, zero new retrieval.
Source run: `eval\runs\2505e43b9003`.

| problem | records | abstract >=50 | coverage (pre-fix) | failure terms reach query | constraint terms reach query |
|---|---:|---:|---:|---|---|
| `bench-p02-leadacid-grid-corrosion` | 16 | 10 | 0.625 | yes | yes |
| `bench-p05-bridge-bearing-aging` | 17 | 11 | 0.647 | yes | yes |
| `bench-p09-packaging-barrier` | 16 | 13 | 0.812 | yes | yes |
| `dev-fu-001-bearing-spalling` | 16 | 13 | 0.812 | yes | yes |
| `dev-fu-002-hvac-filter` | 14 | 6 | 0.429 | yes | yes |
| `dev-fu-003-motor-insulation` | 16 | 8 | 0.500 | yes | yes |
| `dev-fu-004-fouling` | 16 | 9 | 0.562 | yes | yes |
| `dev-fu-005-bridge-bearing` | 16 | 10 | 0.625 | yes | yes |
| `dev-fu-006-pump-cavitation` | 14 | 6 | 0.429 | yes | yes |
| `eval-new02-slipring-predictor` | 16 | 10 | 0.625 | yes | yes |
| `eval-new06-bearing-vibration-predictor` | 16 | 13 | 0.812 | yes | yes |
| `eval-new09-hvac-filter-predictor` | 16 | 9 | 0.562 | yes | yes |

Problems with a failure-text variant: 12/12.
Problems with a constraint-targeted variant: 12/12.
Pre-fix evidence-pool coverage median: 0.625 (min 0.429, max 0.812).

## Disclosures

- The committed retrieve envelopes predate the A3 abstract backfill. The coverage column is the PRE-FIX baseline — the starvation number, not a claim that the fix already paid off.
- Post-fix abstract coverage and backfill counts require a live retrieval run; they are NOT_MEASURED here (no credentials in this environment).
- The refined query variants are computed by the shipped A4 code from the committed problem's own failure/constraint text: zero LLM, problem facts only (Art. XLIII). They are a query-plan measurement, not a retrieval result.
- A problem with no failure-text variant has no extractable content term beyond the primary query; that is a measured property of its text, not a silent skip.
- The 12-problem plan is the committed run's lexicographic first 12 directories; eval-sofc-thermal-cycling is the deterministic 13th.
