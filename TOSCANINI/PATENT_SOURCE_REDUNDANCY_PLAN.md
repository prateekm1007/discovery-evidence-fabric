# PATENT SOURCE REDUNDANCY PLAN — Recorded Requirement + USPTO ODP Investigation

**Status:** RECORDED (CEO directive 2026-08-31: "Record the
patent-source redundancy requirement and investigate USPTO ODP, but DO
NOT allow patent-source work to derail the Technical Improvement
Engine"). This document is the requirement record; the build is a
future cycle owned by this plan, not started here.
**Source:** CEO research (2026-08-31 second-pass message) — verified
against the engine's own measured source state.

---

## 1. The measured problem (why redundancy is required)

Current patent-source state, measured live this cycle (R378):

| Source | Measured state |
|---|---|
| Lens patent | **HTTP 429 — hard 1000/month quota EXHAUSTED** ("Allowed '1000' per month"); the R377 s7/m7 grid reruns ended UNRESOLVED_INSUFFICIENT_EVIDENCE on it |
| Google Patents | HTTP 503 (bot-blocked from this ASN; claims fetch dead since R377) |
| PatentBear | LIVE but provider-metered (20/month on this key despite the CEO's "unlimited investment" statement — the account upgrade is the pending CEO action); persistent meter + reserve floor 2 enforced by the R378 guard; the w7 adversarial demo spent it to the floor mid-run |
| USPTO ODP / PatentsView | AUTH_REQUIRED — no credential provisioned (see §3) |

**Conclusion (CEO):** the Lens quota is a bottleneck, not a fundamental
patent-data bottleneck. There is no single free replacement for Lens;
the solution is a **redundant patent evidence network** built from
government/open datasets with **local custody**, making Lens an optional
enrichment source rather than the backbone.

## 2. The target architecture (CEO-specified)

```
             MULTI-SOURCE PATENT EVIDENCE NETWORK
 USPTO ─────── EPO ─────── Google ─────── WIPO
    │            │             │             │
    └────────────┴─────────────┴─────────────┘
                         ↓
                  LOCAL CUSTODY (hashed/pinned)
                         ↓
         NORMALIZED PATENT KNOWLEDGE GRAPH
   (family / claims / abstracts / citations / legal events)
                         ↓
          SEARCH (semantic + lexical) → FAMILY EXPANSION
                         ↓
             CROSS-DOMAIN COLLISION / ADJUDICATION
```

**Local custody record requirements (CEO list, verbatim):** source,
dataset version, download timestamp, hash, coverage, schema,
license/terms, document ID, family ID, publication date, priority date,
jurisdiction. External APIs become: (1) incremental update,
(2) gap filling, (3) verification, (4) freshness check — not "ask Lens
every time."

## 3. USPTO ODP investigation (measured status)

The adapter (`discovery_fabric/prior_art_v2/uspto_odp_adapter.py`)
already exists and is honest about its state:

- **Measured 2026-08-30:** legacy `api.patentsview.org/patents/query`
  is RETIRED (serves an HTML SPA with HTTP 200 — a masked endpoint
  retirement, caught by the content-type validation added then). The
  replacement PatentsView API (`search.patentsview.org`) and the USPTO
  ODP API (`api.uspto.gov`) BOTH require API keys — 403 "Missing
  Authentication Token" measured, no credential provisioned.
- **The adapter is key-ready:** reads `USPTO_ODP_API_KEY` /
  `PATENTSVIEW_API_KEY` from `.env.keys`; absent key → AUTH_FAILED
  (never absence). Key procurement path: uspto.gov/subscription-center.
- **CEO research (2026-08-31) confirms the data is free:** USPTO
  research datasets + PatentsView API/search/bulk cover ~40 years of
  US patent data (grants, applications, CPC, citations, inventors,
  assignees, foreign priorities, related applications) — bulk download
  configs exist in the PatentsView code examples repo.

**Unblock:** a single CEO action — obtain a USPTO ODP/PatentsView API
key (subscription-center registration) and add it to `.env.keys` as
`USPTO_ODP_API_KEY`. No engine change needed; the adapter takes it from
there (search + full-text + claims + continuity + citations endpoints).

## 4. Source priorities (CEO-ranked)

| Priority | Source | What it gives Toscanini |
|---|---|---|
| **P0** | USPTO bulk + **Common Pile USPTO** (Hugging Face, ~20.3M documents / ~1 TB; filtered variant ~17M / 661 GB) | A LOCAL US patent corpus searched without any external API quota — the single biggest structural fix |
| **P0** | **EPO DOCDB + EP Full Text** (bulk; ~200 GB DOCDB backfile, ~3.53 TB EP text, weekly frontfiles) | Worldwide family/bibliographic layer + European full text: family expansion, global prior art |
| **P1** | USPTO Open Data / File Wrapper | Current prosecution/application records (freshness) |
| **P1** | Google Patents Public Data (BigQuery; first 1 TB/month query processing free) | Independent worldwide + US-full-text discovery/cross-check layer. The github repo is ARCHIVED (April 2026) — reference code/schema only, not a live source |
| **P1** | EPO OPS (free tier 4 GB/week) | Targeted live retrieval + verification within quota |
| **P2** | Hugging Face specialized patent corpora (EP claims, DAPFAM, patrepeval, 2.7M US applications 2021–2026) | Reusable claim datasets / benchmarks / evaluation sets |
| **P2** | WIPO PATENTSCOPE | PCT verification/search only — bulk download and robots PROHIBITED by WIPO terms; never an architecture pillar |
| **P3** | Lens | Optional enrichment when quota is available |

## 5. Licensing discipline (CEO warning, binding)

Three distinct classes must be represented in the source registry:
1. **Public-domain government data** (USPTO patent documents) —
   strongest class.
2. **Open datasets** (Common Pile USPTO) — excellent but the dataset
   card itself warns about licensing/metadata limitations; custody must
   preserve the dataset's provenance and license fields.
3. **Free API access within quota** (EPO OPS) — NOT unlimited open
   data; the quota is part of the source's truth.

## 6. Why this did NOT get built in R378

The CEO's standing instruction: the Technical Improvement Engine (built
and measured this cycle — see TOSCANINI/
TECHNICAL_IMPROVEMENT_ENGINE_DIRECTIVE.md §7) took precedence; patent
source redundancy is the NEXT cycle's infrastructure build, gated on:

- **CEO action 1:** USPTO ODP/PatentsView API key (unblocks the live
  adapter immediately; §3).
- **CEO action 2:** PatentBear account upgrade to the investor-funded
  unlimited tier (the provider meter still reports 20/month — the
  engine's guard obeys the meter, not the intent, until the provider
  changes it).
- **Build decision:** the P0 local-custody corpus work (Common Pile +
  EPO bulk), which is a data-engineering cycle (download, hash, pin,
  normalize, index) — scoped separately so it cannot silently expand
  into an engine cycle.
