# Source Registry — the single authority over evidence sources

`discovery_fabric/source_registry/` implements the CEO database-layer
directive (SOURCE ROLE ARCHITECTURE).

## What is authoritative here

- `registry.py` — `SOURCE_REGISTRY`: every source with the 13 directive
  fields. `health_status` is `NOT_MEASURED` until a measured health run
  overlays a value; **LIVE is a measurement result, never an assertion**
  (Art. XXI: a README mention is not integration).
- `roles.py` — the 13 authority roles (SCIENTIFIC, PATENT, REGULATORY,
  DEVICE_IDENTITY, CLINICAL, ADVERSE_EVENT, RECALL, MATERIALS, CHEMISTRY,
  BIOLOGY, MANUFACTURING, STANDARDS, COMMERCIAL).
- `base.py` — connector base implementing the 7-step proof chain
  (CONNECTOR EXISTS → LIVE REQUEST WORKS → RESPONSE PARSES →
  NORMALIZATION WORKS → PROVENANCE STORES → RETRIEVAL LOG STORES →
  HEALTH CHECK) with the Art. XXI.3 failure vocabulary: TIMEOUT /
  SEARCH_FAILED / AUTH_FAILED / RATE_LIMITED / UNAVAILABLE / PARSE_FAILED
  are never collapsed into EMPTY; EMPTY only after a definitive provider
  answer.
- `connectors/` — openfda (MAUDE, recall, 510k, PMA, UDI, registration,
  classification), clinicaltrials, scientific (PubMed, EuropePMC, Crossref,
  OpenAlex, Semantic Scholar), biochem (PubChem, UniProt, ChEMBL, RCSB),
  patents (thin wrappers REUSING `prior_art_v2` adapters — no second
  factory).
- `retrieval_log.py` — hash-chained append-only custody log at
  `artifacts/source_health/retrieval_log.jsonl`.
- `health.py` — measured LIVE / DEGRADED / UNAVAILABLE / NOT_INTEGRATED
  with recorded derivation.

## Measured state (this session's health run; see SOURCE_HEALTH_REPORT)

- LIVE: 15 sources — the full openFDA family (7), ClinicalTrials.gov,
  EuropePMC, PubMed, Crossref, PubChem, UniProt, ChEMBL, RCSB PDB.
- DEGRADED: 2 — OpenAlex (credit budget exhausted, 429), Semantic Scholar
  (unauthenticated rate limit, 429; key not provisioned).
- UNAVAILABLE: 6 — Google Patents (503 bot-block), Lens (no token),
  PatSnap (no key), EPO OPS (no credentials + ASN blocked), USPTO ODP
  (no key), BigQuery patents (no GCP credentials).
- NOT_INTEGRATED: 11 — De Novo, WHO ICTRP, WIPO PATENTSCOPE, Materials
  Project, NIST materials, FDA recognized standards, ISO, ASTM, EUDAMED,
  manufacturing placeholder, commercial placeholder.

Role gaps that are HONEST: MATERIALS, MANUFACTURING, STANDARDS, COMMERCIAL
have no live source. The auditable coverage matrix records this rather
than papering over it.

## Reproduction

`python scripts/source_health_report.py` re-measures every source and
writes `artifacts/source_health/SOURCE_HEALTH_REPORT.json` plus the
coverage matrix. Third parties can re-run it (Art. XXVI disclosure:
builder-measured, reproducible on demand).
