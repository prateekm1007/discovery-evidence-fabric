# FORWARD DISCOVERY V1 — Phase D: Cross-Source Retrieval Report

## Summary

| Metric | Value |
|--------|-------|
| Problems processed | 100/100 |
| Total sources retrieved | 1023 |
| Retrieval failures | 1 |
| Root hash | b9faf80e8aabf16b |

## Sources by Type

| Source Type | Count |
|-------------|-------|
| PUBLICATION | 951 |
| PATENT | 72 |

## Retrieval Metrics

| Metric | Value |
|--------|-------|
| Full text rate | 0.0000 |
| Relevance rate | 0.9013 |
| Mechanism density (avg) | 1.62 |
| Cross-domain hit rate | 199/400 (49.8%) |

## Query Type Distribution

| Query Type | Count |
|------------|-------|
| INTRA_DOMAIN | 200 |
| CROSS_DOMAIN | 200 |

## Relevance Distribution

| Relevance | Count |
|-----------|-------|
| PARTIALLY_RELEVANT | 469 |
| RELEVANT | 453 |
| IRRELEVANT | 101 |

## Source Classes Attempted

| Source Class | Status | Route |
|--------------|--------|-------|
| SCIENTIFIC (Europe PMC) | ACTIVE | europepmc_api |
| SCIENTIFIC (OpenAlex) | ACTIVE | openalex_api |
| PATENT (Europe PMC patent filter) | ACTIVE | europepmc_patent_search |
| REGULATORY (FDA MAUDE) | NOT_CONNECTED | No existing connector |
| CLINICAL (ClinicalTrials.gov) | NOT_CONNECTED | No existing connector |
| TECHNICAL (Government) | NOT_CONNECTED | No existing connector |

## Gaps

- FDA MAUDE connector: NOT implemented — regulatory evidence not retrieved
- ClinicalTrials.gov connector: NOT implemented — clinical evidence not retrieved
- Patent full text: Only abstract-level via Europe PMC patent filter

## No Invention Fields

Phase D output contains ONLY evidence retrieval. No candidate interventions,
no mechanisms, no inventions, no DeepSeek synthesis calls.

## Governance

- 11/11 tests PASS
- 6/6 regression PASS
- Problem corpus root hash preserved: 40adb5d0157f624a
- All source hashes computed and stored
- All retrieval failures explicitly recorded
