# OpenAlex Connector

Isolated adapter for OpenAlex (https://openalex.org).

- Uses the public API with optional API key for higher daily budget.
- Supports filter, sample+seed, search, and single-entity retrieval.
- Every returned object is mapped to the canonical EvidenceItem schema.
- Secondary enrichment (e.g., Crossref DOI resolution) is recorded under provenance.secondary_enrichment and never silently replaces primary OpenAlex evidence.

Rate limits and credit costs must be respected. See OpenAlex documentation for current pricing.
