# One Cliff-Fix Rule (funnel-anchored, R510)

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD REMOVE OR SIMPLIFY, verbatim rule text below.

## Operator's stated gap

The current rule (one cliff-fix per cycle) breaks down when a cycle is an interrupted battery (execution #1 failed): multiple rounds pass with no measurement to anchor the fix selection.

## The rule (replaces the prior per-cycle formulation)

```text
One cliff-fix per FUNNEL MEASUREMENT, where a funnel
measurement is a successful battery execution with a
published harvest result. The cliff-fix must address the
named bottleneck from the most recent successful harvest.
A failed battery (INCOMPLETE_INFRASTRUCTURE_FAILURE)
resets neither the cliff-fix count nor the authorized
bottleneck — the previous harvest's bottleneck remains
authoritative until superseded by a new successful harvest.
```

## Provenance note (coder-recorded, Art. XV)

Like the scope law, the prior per-cycle formulation lived as round working-law, not as a numbered article. This file constitutionalizes its funnel-anchored replacement. See also Art. LXXXIII (the funnel as constitutional instrument), which this rule presupposes.
