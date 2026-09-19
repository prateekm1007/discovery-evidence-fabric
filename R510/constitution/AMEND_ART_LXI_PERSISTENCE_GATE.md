# Amendment to Art. LXI — Persistence Gate

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Proposed amendment:** Constitution v2.9.0 → v2.10.0 (appends a clause to Art. LXI; original text byte-intact)
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD AMEND, verbatim rule text below.

## Operator's stated gap

The article is correct that infrastructure failure ≠ scientific absence. But it has no rule about what happens when infrastructure failure is the persistent state. Execution #1 produced 6× INCOMPLETE_INFRASTRUCTURE_FAILURE. That is correctly typed. But the Constitution had no mechanism to say "this happened once — investigate; this happened twice — it is a P0 blocker."

## The amendment (appended to Art. LXI, original text unchanged)

```text
Amendment to Art. LXI:
An INCOMPLETE_INFRASTRUCTURE_FAILURE that recurs across
2 consecutive executions of the same problem set is a
P0 INFRASTRUCTURE_BLOCKER. It may not be addressed by
re-typing or re-submitting without a diagnosed root cause
and a tested fix committed to the durable record. The
diagnosis must explain the mechanism of failure, not
merely re-describe the symptom.
```
