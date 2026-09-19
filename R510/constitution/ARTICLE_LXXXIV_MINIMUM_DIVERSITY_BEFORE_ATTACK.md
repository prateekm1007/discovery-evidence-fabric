# Article LXXXIV — Minimum Candidate Diversity Before Attack

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Proposed amendment:** Constitution v2.9.0 → v2.10.0
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD ADD, verbatim rule text below.

## Operator's stated gap

The system currently allows a run with 0 distinct mechanisms to reach the attack stage and report results as if the pipeline functioned. This conflates a pipeline completion with a discovery event.

## The rule

```text
New Article LXXXIV:
A discovery run that produces fewer than 2 materially
distinct candidate mechanisms (per the Art. XLII
distinctness definition) must be classified
MECHANISM_STARVED before advancing. A MECHANISM_STARVED
run may not report attack, contradiction, or experiment
results as discovery evidence. The run terminal state
is MECHANISM_STARVED, not INVENTION_REQUIRES_EXPERIMENT.
The distinction matters: INVENTION_REQUIRES_EXPERIMENT
means the system invented something but couldn't test it.
MECHANISM_STARVED means the system did not generate
anything worth attacking.
```
