# AUTONOMOUS CALIBRATION V3 — PROTOCOL

**Status**: `CALIBRATION_BLOCKED` (pre-registered, frozen before inference)
**Base commit**: `d942366`
**Protocol SHA-256**: `b1325ed8519e0db275687726e24606f8eb2825c59e45720e51e1ffa502e8cc73`
**Created**: 2026-08-17

## Why V3

V2 reached 45% accuracy with 50% false-reject because the final adjudicator judged
claims without performing the actual search → evidence → claim mapping → 102 → 103
pipeline. The CEO directive: V3 MUST test the REAL autonomous loop.

## V2 Frozen Results (preserved, not overwritten)

| Metric | Value |
|---|---|
| Accuracy | 45% |
| False-elite rate | 5% |
| False-reject rate | 50% |
| Cited-art recall | 100% |
| Status | CALIBRATION_BLOCKED |

## V3 Real Pipeline

```
CASE
↓
CANONICAL CLAIM
↓
SEARCH CONCEPT GRAPH
↓
14 SEARCH FAMILIES
↓
PATENT DISCOVERY
↓
ACTUAL PATENT RECORD
↓
ACTUAL CLAIM RETRIEVAL
↓
ELEMENT MAPPING  (L1, L2, ..., Ln)
↓
RELATIONSHIP MAPPING  (A→B, B→C, A+B+C)
↓
102  (single-reference, ALL limitations + arrangement)
↓
CLOSEST PRIOR ART
↓
OBJECTIVE TECHNICAL PROBLEM
↓
103  (COULD + WOULD + WHY)
↓
ANTI-HINDSIGHT  (rationale-before vs rationale-after)
↓
FINAL ADJUDICATION
```

## Claim-Only Path DISABLED

The final adjudicator MUST NOT receive claim-only + generic model knowledge.
If evidence retrieval fails, the system returns `SEARCH_INSUFFICIENT` — NOT
`REJECT`, NOT `NOVEL`, NOT `ELITE`.

## 14 Search Families

Q1 CONCEPT · Q2 MECHANISM · Q3 STRUCTURE · Q4 MATERIAL · Q5 RELATIONSHIP ·
Q6 TECHNICAL_EFFECT · Q7 FULL_COMBINATION · Q8 FUNCTIONAL_EQUIVALENT ·
Q9 STRUCTURAL_EQUIVALENT · Q10 CPC/IPC · Q11 COMPETITOR_PORTFOLIO ·
Q12 CITATION_NEIGHBORHOOD · Q13 NEGATIVE_SEARCH · Q14 SEMANTIC_SEARCH

Each family records: `attempted`, `source`, `query`, `results`, `failure_state`.

## Search Failure States

`SUCCESS` · `SEARCH_INSUFFICIENT` · `NO_RELEVANT_PRIOR_ART_FOUND` ·
`SOURCE_UNAVAILABLE` · `PATENT_EVIDENCE_UNAVAILABLE` · `RATE_LIMITED` ·
`TEMPORARILY_UNAVAILABLE`

A zero-result search with fewer than 8/14 families attempted is **never**
classified as `NO_RELEVANT_PRIOR_ART_FOUND` — it is `SEARCH_INSUFFICIENT`.

## Generator/Evaluator Separation

| Role | Responsibility |
|---|---|
| GENERATOR | Parses canonical claim, builds concept graph |
| SEARCHER | Runs 14 families, retrieves claims |
| NOVELTY_ADVERSARY | 102 single-reference attack |
| OBVIOUSNESS_ADVERSARY | 103 with closest prior art + COULD/WOULD + anti-hindsight |
| FINAL_ADJUDICATOR | Combines evidence → outcome |

Each role uses distinct prompt + distinct context + distinct evidence path.
Model name and prompt hash recorded per role per case.

## 102 — Novelty

For every relevant patent, map `L1, L2, ..., Ln` and every relationship.
102 succeeds only when ONE reference discloses ALL required limitations + required
arrangement. Inherency requires `NECESSITY_REQUIRED` evidence.

## 103 — Obviousness (EPO 2026)

Closest prior art = most promising single-reference starting point, normally with
similar purpose/effect or closely related technical field.

Then: objective technical problem → distinguishing features → technical effect →
secondary reference → motivation → reasonable expectation of success →
COULD → WOULD → WHY.

EPO explicitly requires WOULD, not merely COULD.

## Anti-Hindsight

1. Build inventive-step rationale BEFORE exposing the final solution.
2. Compare with post-disclosure reasoning.
3. Record LOW / MEDIUM / HIGH.

The system MUST NOT construct the problem backwards from the claimed invention.

## Ground Truth Construction

Do NOT define `GRANTED = PATENTABLE` / `ABANDONED = UNPATENTABLE`.
Construct case-level ground truth from:

- claim at issue
- examiner-cited prior art
- 102 rejection(s)
- 103 rejection(s)
- amendments
- final claim
- final disposition

Record `GROUND_TRUTH_CONFIDENCE`.

## Rescue Calibration (Amended Cases)

AI must determine whether final amended claim is technically different from earlier
rejected claim. Metric: `RESCUE_RECOGNITION_ACCURACY`.
Do NOT treat every amendment as successful rescue.

## Acceptance Gate

| Metric | Threshold |
|---|---|
| Overall accuracy | ≥ 85% |
| False-elite rate | ≤ 10% |
| False-reject rate | ≤ 10% |
| Cited-art recall | ≥ 90% |
| Search recall | ≥ 80% |

If any fails: `CALIBRATION_BLOCKED`. Do NOT run 50→5.

## Output Artifacts

`PROTOCOL.json` · `PROTOCOL.sha256` · `PROTOCOL.md` · `GROUND_TRUTH.json` ·
`SEARCH_TRACE.json` · `CLAIM_MAPPINGS.json` · `102_RESULTS.json` ·
`103_RESULTS.json` · `ADJUDICATION.json` · `METRICS.json` ·
`ERROR_ANALYSIS.json` · `REPORT.md`

## Stop Condition

DO NOT RUN 50→5.

Only after V3 passes the preregistered calibration gate: `UNBLOCK_50_TO_5`.

Otherwise: `CALIBRATION_BLOCKED`.

STOP FOR CEO AUDIT.
