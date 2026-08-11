# Milestone: ≥10,000 Real Evidence Objects

**Date:** 2026-08-11  
**Status:** ACHIEVED

## Summary

| Metric | Value |
|--------|-------|
| Total EvidenceItems | **10,097** |
| Primary source | OpenAlex (live API) |
| Source type | scientific_paper |
| Epistemic state | OBSERVED |
| Content hash (JSONL) | `7a1bbed0e35637b692607331fc20c985080b22b7ca8cc4a80ef9564fc17a1b1a` |
| Retrieval method | Reproducible `sample` + `seed` queries |
| Proprietary bulk corpus stored? | **No** |

## What was built

1. **Canonical EvidenceItem schema** (`discovery_fabric/normalization/evidence_item_schema.json`)
2. **OpenAlex connector + mapper** (`discovery_fabric/connectors/openalex/`)
3. **10,097 normalized, provenance-preserved, content-hashed EvidenceItems** retrieved live from OpenAlex and stored as queryable JSONL.

Every item carries:
- source, source_id, source_uri
- retrieval_timestamp, retrieval_method
- publication_date, license/access status
- content_hash
- full provenance block
- source_specific fields retained
- epistemic_state = OBSERVED

## What was NOT done

- No static bulk download of the entire OpenAlex snapshot into this repository.
- No patent connectors yet (USPTO / EPO / WIPO / CN / IN next).
- No mechanism extraction, knowledge graph, or discovery operators yet.
- No cross-domain candidate generation yet.
- **No contact with the TEE frozen corpus or any TEE materials.**

## Separation affirmation

Discovery Evidence Fabric = live external world.  
TEE = frozen independent evaluation.  
The two systems remain completely isolated.

## Next steps (Phase 1–5)

1. Patent source connectors (USPTO PatentsView / Open Data Portal, EPO OPS where permitted, etc.).
2. Additional scientific connectors (Semantic Scholar, arXiv, PubMed/Europe PMC, Crossref).
3. Knowledge-graph construction over the normalized EvidenceItems.
4. Structured mechanism extraction.
5. First 100 cross-domain candidate discoveries → adversarial review → manual inspection of strongest 20.

The machinery beneath the interface is under construction.
