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
  OpenAlex, Semantic Scholar, **Elsevier Scopus**), biochem (PubChem,
  UniProt, ChEMBL, RCSB), patents (thin wrappers REUSING `prior_art_v2`
  adapters — no second factory: Google Patents, **Lens patent**, **Lens
  scholarly**, **PatentBear**, PatSnap, EPO OPS, USPTO ODP, BigQuery).
- `retrieval_log.py` — hash-chained append-only custody log at
  `artifacts/source_health/retrieval_log.jsonl`. Entries may carry
  `rate_limit_remaining` — the PROVIDER's own metering accounting
  (e.g. PatentBear usage.monthly_remaining), stored verbatim.
- `health.py` — measured LIVE / DEGRADED / UNAVAILABLE / NOT_INTEGRATED
  with recorded derivation.
- `keys.py` — runtime credential loader (.env.keys, gitignored, 600).
  Keys are read at call time and sent as HEADERS, never URL params, so
  credentials cannot land in the custody log (S-01 discipline).

## Provider-metered sources (PatentBear class)

Some sources bill per request (PatentBear: **20 requests/month** across
search_patents + get_patent_record, provider-reported in every response
usage block). For these, `registry.py` carries a `metered_quota` wiring
block and `health.py` enforces:

1. **Automated health checks NEVER live-probe a metered source** — health
   derives from the freshest live retrieval-log proof inside the metered
   window (default 31 days), with the last-live-proof timestamp disclosed.
2. **No proof inside the window → UNAVAILABLE** (never silently LIVE).
3. **Provider-reported remaining == 0 → connector guard returns
   RATE_LIMITED without making the call** (quota exhaustion is a provider
   state, never 'no results' — Art. XXI.3).
4. `run_lab` / `get_lab_result` on PatentBear BILL CREDITS and are
   prohibited (never called by this engine).
5. The hermetic test suite (tests/conftest.py) neutralizes source-layer
   keys so NO test ever burns metered quota (ENGINE_LIVE=1 opts in).

## The Lens is TWO sources (CEO Section 4 — never merged)

`lens_patent` (PATENT role, POST /patent/search) and `lens_scholarly`
(SCIENTIFIC role, POST /scholarly/search) are separate registry entries
with separate connectors. Measured 2026-08-29: both authenticate with the
provisioned token (one transient 401 observed 14 min after provisioning,
disclosed in the registry entry). The Lens API SILENTLY IGNORES structured
DSL queries (returns newest records regardless of relevance) — the
adapters use the string form `title:(...)`, pinned by regression test
(tests/test_key_unlock_cycle.py, Art. XXXI memory artifact).

## Measured state (last health run; see SOURCE_HEALTH_REPORT)

See `artifacts/source_health/SOURCE_HEALTH_REPORT.json` — the committed,
reproducible measurement. The README never outranks the artifact (Art. XXIV).

## Reproduction

`python scripts/source_health_report.py` re-measures every source and
writes `artifacts/source_health/SOURCE_HEALTH_REPORT.json` plus the
coverage matrix. Third parties can re-run it (Art. XXVI disclosure:
builder-measured, reproducible on demand).
