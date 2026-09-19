# Article LXXX — The Evidence-Synthesis Binding Contract

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Proposed amendment:** Constitution v2.9.0 → v2.10.0
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD ADD, verbatim rule text below.

## Operator's stated gap

The system retrieves evidence correctly (custody chain, freeze, content hashes) but has no constitutional requirement that synthesis actually cite it. The result is span_verbatim_rate = 0 across every benchmark run — mechanisms generated as LLM opinion rather than evidence-constrained discovery. The current Art. II says "exact evidence beats semantic plausibility" but does not operationalize this at the synthesis stage.

## The rule

```text
New Article LXXX:
Every mechanism output must contain at least one verbatim
span (≥ 8 contiguous words) from a frozen evidence record
in the run's custody chain. A mechanism without a verbatim
span is classified UNGROUNDED_SYNTHESIS. UNGROUNDED_SYNTHESIS
is UNKNOWN, not REJECTED (Art. XXV applies). It may not
advance to CANDIDATES. The span_verbatim_rate must be
recorded in every stage envelope. No stage summary may
report a mechanism count without reporting
span_verbatim_rate alongside it.
```
