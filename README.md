# Discovery Evidence Fabric V1

**Global scientific + patent discovery engine** that continuously interrogates external knowledge infrastructures while preserving provenance, licensing, epistemic state, and reproducibility.

## Core Principle

GitHub repositories are **not** the corpus.  
They are connectors, parsers, schemas, retrieval clients, query infrastructure, and reference implementations.

We do **not** blindly clone datasets.  
We build an **external-evidence architecture**.

## Architecture

```
Live external sources (OpenAlex, Semantic Scholar, arXiv, PubMed, Crossref,
USPTO, EPO, WIPO, CN/IN patent sources, Google Patents/BigQuery where permitted)
        │
        ▼
   SOURCE CONNECTORS  (isolated adapters)
        │
        ▼
  EVIDENCE NORMALIZER  →  canonical EvidenceItem
        │
        ▼
   KNOWLEDGE GRAPH  (papers, patents, claims, mechanisms, materials, processes…)
        │
        ▼
  MECHANISM EXTRACTION  (structured causal chains, not keywords)
        │
        ▼
   DISCOVERY OPERATORS  (cross-domain transfer, analogy, contradiction, whitespace…)
        │
        ▼
  ADVERSARIAL REVIEW  +  PRIOR-ART FIREWALL
        │
        ▼
   EPISTEMIC STATE MACHINE  (OBSERVED → … → INVENTION_CANDIDATE)
        │
        ▼
   SIMPLE USER INTERFACE
```

## Critical Separation

| System              | Role                                      | State          |
|---------------------|-------------------------------------------|----------------|
| **Discovery Fabric**| Continuously changing external world      | Live           |
| **TEE**             | Frozen independent scientific evaluation  | Isolated       |

The discovery engine may query enormous external corpora.  
TEE must remain completely isolated. Never merge the two.

## First Milestone

10,000 real scientific/patent evidence objects retrieved through legitimate sources, normalized, hashed where applicable, provenance-preserved, and queryable.

Then: 100 cross-domain candidate discoveries → adversarial review → manual inspection of the strongest 20.

No candidate is called an “invention” until evidence and novelty checks justify that classification.

## Directory Layout

```
discovery_fabric/
├── connectors/          # Isolated source adapters
├── evidence/            # Retrieved + normalized EvidenceItems
├── normalization/       # Schema + mappers
├── knowledge_graph/     # Graph construction & queries
├── mechanisms/          # Structured mechanism extraction
├── discovery_modes/     # The 15 discovery operators
├── prior_art/           # Prior-art / novelty firewall
├── adversarial_review/  # Attack every candidate
├── provenance/          # Hashes, licenses, retrieval logs
├── evaluation/          # Internal quality metrics (not TEE)
└── reports/             # Discovery reports & audit trails
```

## Epistemic States (never silently promoted)

```
OBSERVED
INFERRED
ANALOGY
CANDIDATE_CONNECTION
MECHANISTIC_HYPOTHESIS
EXPERIMENTAL_PROPOSAL
INVENTION_CANDIDATE
```

## Anti-Hallucination Rule

Never output “Nobody has done this.”  
Always output “No matching evidence was found within the searched universe” together with the exact search universe, queries, databases, time range, timestamp, result counts, and limitations.
