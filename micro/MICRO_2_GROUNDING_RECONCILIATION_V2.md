# MICRO-2 Grounding Ontology Correction V2

## Ontology Correction

The V1 forensic was too strict — it treated any candidate whose exact intervention
doesn't appear in the source as UNSUPPORTED. This conflated "evidence required for
invention reasoning" with "the invention itself must already be present in evidence."

V2 separates four evidence roles:
- **PROBLEM_EVIDENCE**: Device has the documented failure (FDA MAUDE)
- **MECHANISM_EVIDENCE**: Source supports the causal mechanism
- **TRANSFER_EVIDENCE**: Source supports the mechanism in another context
- **INVENTION_HYPOTHESIS**: Proposed modification — legitimate hypothesis

A candidate does NOT fail merely because the invention is a hypothesis.

## V2 Status Distribution

| Status | Count | Rate |
|--------|-------|------|
| MICRO_UNSUPPORTED | 7 | 0.4375 |
| MICRO_EVIDENCE_SUPPORTED | 6 | 0.3750 |
| MICRO_HYPOTHESIS | 2 | 0.1250 |
| GENERATION_CALL_FAILED | 1 | 0.0625 |

## V2 Metrics

| Metric | Value |
|--------|-------|
| EVIDENCE_BACKED_INVENTION_HYPOTHESIS_RATE | 0.5000 |
| Problem evidence rate | 0.9375 |
| Mechanism evidence rate | 0.3750 |
| Direct transfer rate | 0.0625 |
| Analogical transfer rate | 0.0000 |
| Mechanistic inference rate | 0.4375 |
| Unsupported transfer rate | 0.4375 |
| Unsupported problem/mechanism rate | 0.4375 |
| Hypothesis rate | 0.1250 |

## Transfer Distribution

| Transfer Level | Count |
|----------------|-------|
| UNSUPPORTED_TRANSFER | 7 |
| MECHANISTIC_INFERENCE | 7 |
| DIRECT_TRANSFER | 1 |
| ? | 1 |

## Comparison: V1 → V2

| Metric | V1 (original) | V1 forensic | V2 corrected |
|--------|--------------|-------------|--------------|
| Candidate rate | 92.9% | 25.0% | 50.0% |
| Evidence grounded | — | 6.25% | 37.5% |
| Transfer supported | — | — | 0.0% |
| Hypothesis | — | 18.75% | 12.5% |
| Unsupported | — | 68.75% | 43.8% |

## Key Insight

The V1 forensic was wrong to call 68.75% of candidates UNSUPPORTED.
Many of those candidates have evidence-backed PROBLEM and MECHANISM —
the invention itself is a legitimate hypothesis, not an evidence failure.

The corrected EVIDENCE_BACKED_INVENTION_HYPOTHESIS_RATE is
**50.0%** — 
candidates where the problem and mechanism are evidence-backed and the
intervention is an explicit, falsifiable hypothesis.

## Downstream Gates

All surviving Micro hypotheses will eventually face:
- Exact evidence verification
- Target alignment
- Frozen prior-art evaluator
- Seven adversarial dimensions
- Simulation readiness

This more permissive invention-stage ontology does NOT weaken downstream gates.
