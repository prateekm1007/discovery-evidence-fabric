# Amendment to Art. XXI.3 — Bounded Inference

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Proposed amendment:** Constitution v2.9.0 → v2.10.0 (appends a clause to Art. XXI clause 3; original text byte-intact)
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD AMEND, verbatim rule text below.

## Operator's stated gap

The current rule correctly prevents absence from being inferred from search failure. But it has been applied so broadly that even structural gaps (zero mechanisms from five of six problems, physics_beats_baseline = 0 across 16 problems) get reported as UNKNOWN rather than as evidence of systematic failure. There is a difference between "provider failed to respond, so we don't know if evidence exists" and "the system ran 16 problems and produced zero instances of physics_beats_baseline."

## The amendment (appended to Art. XXI clause 3, original text unchanged)

```text
Amendment to Art. XXI.3:
Absence may not be inferred from a single search failure.
However, a systematic pattern across N ≥ 5 independent
runs where a capability measure is zero is not UNKNOWN —
it is a measured systematic zero. The Art. XXI.3
protection applies to individual measurements, not to
aggregates across independently-run problems. A zero that
is consistent across 16 problems and 2 batteries is a
finding, not an unknown.
```
