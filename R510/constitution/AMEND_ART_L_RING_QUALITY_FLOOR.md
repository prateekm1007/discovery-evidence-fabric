# Amendment to Art. L — Ring Quality Floor

**Status:** RATIFIED 2026-09-19 (Round R510) — enacted into constitution v2.10.0 per the operator's 2026-09-19 governance directive (constitutional update); see R510/constitution/AMENDMENT_RECORD.json
**Proposed amendment:** Constitution v2.9.0 → v2.10.0 (appends a clause to Art. L; original text byte-intact)
**Sponsor:** Operator governance directive, 2026-09-19, section WHAT I WOULD AMEND, verbatim rule text below.

## Operator's stated gap

The article requires calibration but has no minimum standard for the ring used to perform it. The free-tier qwen ring produces 1–2 second, 50-token responses on attack calls. That is not a calibration environment; it is a measurement environment for degenerate model behavior. The current system correctly identified this as "ring-quality-bound" — but this identification has no constitutional backing.

## The amendment (appended to Art. L, original text unchanged)

```text
Amendment to Art. L:
A ring used for calibration measurement must satisfy a
pre-calibration probe: response length ≥ 200 tokens,
latency ≥ 5 seconds, on a calibration-class prompt.
A ring that fails this probe is classified
INSUFFICIENT_QUALITY_RING. Its calibration outputs are
classified RING_QUALITY_INVALID, not as a measurement
of the instrument. RING_QUALITY_INVALID is not
NOT_CALIBRATED — the instrument's calibration state
remains UNMEASURED_ON_CAPABLE_RING, which is distinct
from the cases where calibration was attempted and failed.
```

## Provenance note (coder-recorded, Art. XV)

The numeric bars in this amendment (≥ 200 tokens, ≥ 5 seconds) carry operator-directive provenance (Art. XXVII: explicitly operator-defined, stated with the directive as justification). They are not coder-invented thresholds.
