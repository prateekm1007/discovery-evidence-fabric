# Article LXXXI — The Attacker Deployment Gate

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Proposed amendment:** Constitution v2.9.0 → v2.10.0
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD ADD, verbatim rule text below.

## Operator's stated gap

Art. L already requires calibration. It does not say an uncalibrated instrument cannot deploy. The result is three rounds of terminal kill authority held by an instrument with FPR=1.0. The current fail-closed behavior is correct but arrived by inference, not by constitutional mandate.

## The rule

```text
New Article LXXXI:
An attacker instrument with FPR > 0.30 on its sealed
calibration corpus may not issue terminal KILL verdicts.
It may issue ESCALATED_OBJECTION. This is a hard gate,
not advisory. The gate applies to every attacker instrument
separately. A new instrument version resets calibration
status to UNCALIBRATED and must earn deployment authority
independently. An instrument's deployment authority is
revoked automatically if its calibration corpus is
superseded and the instrument has not been re-measured
against the new corpus within 5 rounds.
```
