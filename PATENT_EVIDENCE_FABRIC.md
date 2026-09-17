# The Patent Evidence Fabric — Technical Policy

**Version:** 1.1.0 (R499 — the free-source legs installed; §5 build state measured)
**Governing article:** LXXV — Patent Evidence Is Not Patent Truth (Constitution 2.7.0)
**Source registry:** `PATENT_SOURCE_REGISTRY.json` (the per-source measured instance data)
**Provenance:** architecture per the operator's 2026-09-18 free/open patent-source
research sweep (quoted properties typed `OPERATOR_RESEARCH_UNVERIFIED` until measured);
machine integration per the standing stages of the discovery loop (Art. LV).

---

## 1. What this document is — and is not

This is the **technical policy** for how the machine turns patent sources into
evidence. It is NOT constitutional law (the Four Layers rule): the invariant
layer is Article LXXV; this document is the implementation policy that can
change as sources and transports change. Nothing here authorizes a novelty
verdict (Art. XLVI) or treats any source as authoritative (LXXV clause 1).

The operator's strategic conclusion is adopted as the design thesis:

> The real challenge is not finding more sources. It is building the machinery
> that turns those sources into: high-recall discovery → normalized evidence →
> family-aware retrieval → claim-level attack → mechanism comparison →
> falsifiable novelty hypotheses.

## 2. The four tiers (per the operator's research; roles, not rankings of trust)

```text
TIER 1 — PRIMARY AUTHORITATIVE      USPTO, EPO (OPS/Publication Server), WIPO
                                    establish primary-source evidence; verify
                                    consequential assertions (LXXV clause 3)
TIER 2 — DISCOVERY / INDEX          Google Patents, Espacenet, The Lens,
                                    PatentBear (integrated-live)
                                    accelerate discovery and cross-linking;
                                    never verify (they discover)
TIER 3 — ML / RAG CORPORA           Hugging Face, GitHub, Zenodo, academic
                                    retrieval, embeddings, classifiers,
                                    benchmarks, offline evaluation
TIER 4 — KNOWLEDGE GRAPH            the machine's OWN normalized evidence
                                    graph — never an external source
```

Trust flows UP the tiers, never down: a Tier-2 hit can propose; only record-level
byte binding (and, for consequential assertions, Tier-1 primary text where
reachable) can verify. `SECONDARY_ONLY_VERIFICATION` is the honest typed state
when no primary source is reachable (LXXV clause 3).

## 3. The canonical chain (operator architecture → machine stages)

```text
USER PROBLEM
  ↓  problem representation                     (existing: problem decomposition, Art. LV)
  ↓  multi-query generation                     (search-space neutral, Art. XLIII)
PATENT DISCOVERY                                (existing stage: search_patents —
  |   patentbear, google_patents live today;    multi-provider, typed states)
  |   patentsview/epo_ops/wipo when registered
  ↓  normalization + family collapse            (TO BUILD: publication identity,
  |   citation graph, family/INPADOC awareness)  the five LXXV custody fields
  ↓  claim extraction + semantic retrieval      (TO BUILD on Tier-3 corpora)
  ↓  mechanism retrieval                        (existing: mechanism stage feeds it)
  ↓  PRIOR-ART CANDIDATES
  ↓  ATTACK — collision adjudication            (EXISTING + SEALED: the RBG —
  |   byte-verified passages, typed transport   record-level byte binding,
  |   states, no-verdict vocabulary)            3/3 unanimous R495 + R498)
  ↓  CONTRADICTION → novelty/obviousness HYPOTHESES (hypotheses only — Art. XLVI:
     no novelty verdict exists)
  ↓  EXPERIMENT (the falsification contract, Art. LII)
```

Every patent-derived assertion carries source provenance end to end (LXXV
clause 1) and enters the same provenance custody as every other evidence
object (Art. XII/XXI.9).

## 4. What exists today (measured, R495–R498)

- **Multi-provider search transport** with typed per-provider states
  (`sources.py::search_patent_bear` — the R497 patents-first false-absence fix;
  google transport with typed 503s; lens/patsnap typed out-of-scope/unopened).
- **The Retrieval-Backed Gate** (RBG): adjudication of collision claims by
  byte-verified exact passages against gate-fetched provider text; battery v3.1
  (11 fixtures); **sealed 3/3 unanimous on the Scopus side (R495)** and
  **sealed 3/3 unanimous on the patent leg (R498, this round)** — scope-typed,
  never cross-claimed.
- **Per-run coverage declarations**: `PATENT_BLIND_FOR_THIS_RUN` vs
  `PATENT_COVERAGE_LIVE_THIS_RUN` — mutually exclusive, neither a verdict.
- **Quota stewardship**: metered budgets ledgered per call (R497/R498 usage
  objects); never spend the last 2 debits; early-stop when unanimity is
  impossible.
- **The source registry** (this round): every source's six properties typed
  with provenance; operator research typed `OPERATOR_RESEARCH_UNVERIFIED`
  until measured.

## 5. Build state after R499 (the operator's free-source directive)

The operator directive "use huggingface and other free sources" (2026-09-18)
changed the measured state of build order items 1–3:

1. **Family-aware identity layer** — **UNBLOCKED AND INSTALLED (R499)**. The
   R498 blocker ("Tier-1 registration") was superseded by measurement: EPO
   Linked Open Data is LIVE, anonymous, free at the discovered SPARQL 1.1
   endpoint (`https://data.epo.org/linked-data/query`; the R498 406 was an
   endpoint-URL error, not a dead service). Installed: publication identity,
   application/priority references, SIMPLE-FAMILY collapse
   (application → family → member applications → their publications),
   citation graph — `free_evidence_sources.py::epo_lod_identity /
   epo_lod_family_for_publication`. Measured coverage: EP-centric; US/
   worldwide PARTIAL — `NOT_IN_GRAPH` is a typed coverage state, never
   absence.
2. **Tier-1 primary verification path** — **PARTIALLY INSTALLED (R499)**:
   primary document representations (official EPO XML with ep-patent-document
   DTD + PDF) fetch 200 anonymously with sha256 byte binding
   (`epo_lod_fetch_document`). What remains for full primary verification:
   USPTO-side primary text (USPTO ODP measured 403 anonymous — key-gated)
   and EPO OPS breadth (measured 403 anonymous — registration-gated); both
   stay in the Tier-1 registration ledger.
3. **Claim-level attack (Tier-3 corpora)** — **SUBSTRATE INSTALLED (R499)**:
   HF datasets-server retrieval live (`/splits`, `/rows`: 131,755 full-text
   USPTO documents, per-record CC BY 4.0, structured publication ids);
   `HF_USPTO_CORPUS` wired into the discovery ladder. The `/search`
   full-text path measured INDEX_WARMING_TRANSIENT/502 across the round —
   typed, retriable, never promoted to a coverage claim. Claim extraction +
   breadth analysis on this substrate: NEXT.
4. **Corpus-scale collision measurement** (the 105-search, 21-case × 5-class
   ladder): blocked on PatentBear budget (account upgrade ≈ 6 fresh keys) —
   an owner-gated economic decision, escalated per Art. LXV. NOTE (R499):
   the HF corpus + Google Patents + EPO LOD legs now provide a FREE
   measurement path for corpus-scale discovery-stage coverage that does not
   spend the metered key — the PatentBear dependency for the ladder's
   discovery leg is re-scoped to adjudication-grade record fetch.

The order remains evidence-first: identity and verification before retrieval
sophistication — a retrieval stack without primary verification would
manufacture exactly the false confidence LXXV exists to prevent.

## 6. Standing rules for any new source integration

1. Register the source in `PATENT_SOURCE_REGISTRY.json` with all six
   properties typed BEFORE first use; measurement provenance per property.
2. Transport states are typed per call (the existing vocabulary); no state
   may ever be reported from the source's self-description alone.
3. Every hit entering the pipeline carries the five LXXV custody fields.
4. Metered budgets are ledgered per call; stewardship floors apply.
5. A single green run seals nothing (the repetition rule).
6. LICENSE-COMPATIBLE is reviewed per source (and per dataset for Tier-3)
   before corpus-scale ingestion — `UNREVIEWED_TERMS` is a blocking state
   for ingestion, not for a single-record probe.
