# Amendment to Art. X — Sidecar Definition

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Proposed amendment:** Constitution v2.9.0 → v2.10.0 (appends a definitional clause to Art. X; original text byte-intact)
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD AMEND, verbatim rule text below.

## Placement note (coder-recorded, Art. XV)

The directive heads this item "Amend Art. LXXI" but its content ("The Art. X canonical state requirement is clear...") unambiguously governs Art. X — Canonical state has one authority (Art. LXXI governs the deployed production URL). The directive grants placement latitude ("or new section"). This amendment is therefore filed under Art. X, with the discrepancy recorded here rather than silently resolved.

## Operator's stated gap

The Art. X canonical state requirement is clear. But the system has accumulated several "sidecar" artifacts (hash-chained mutation records, search-impact records) whose relationship to canonical state is undefined. The P0 reality loop introduced sidecars as a design pattern. The Constitution should define what a sidecar is, what it is not, and when it must be promoted.

## The amendment (appended to Art. X, original text unchanged)

```text
Amendment to Art. X (sidecars):
A sidecar is a record derived from a canonical state
change that carries audit provenance. A sidecar is not
canonical state. It does not constitute a learning event.
It does not update the next EngineRun's search parameters.
A sidecar is promoted to canonical state when and only
when: (a) it is explicitly consumed as an input to a
subsequent EngineRun's input manifest, AND (b) the
consumption is recorded with the sidecar's hash in the
child run record. Promotion not recorded is promotion
not achieved.
```
