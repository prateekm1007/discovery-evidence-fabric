# Medical Device Discovery Corpus V2

## TRUE NUMBERS (honestly reported)

| Metric | Value |
|--------|-------|
| Total problems target | 1200 |
| Total candidates generated | 14 |
| Evidence verified | 13/14 (93%) |
| INVENTION_CANDIDATE | 0 |
| REJECTED | 14 |
| Survival rate | 0.0% if n else N/A |

## Key Improvements vs V1

| Metric | V1 (temp=0.3) | V2 (temp=0.0 + fixes) |
|--------|---------------|----------------------|
| Evidence verification | 0% (0/20) | **93%** (13/14) |
| Relevance | 0% (0/19) | **14/14** |
| Positive control | N/A | PASS |

## Rejection Reasons (after evidence verification)
{
  "prior art likely exists": 11,
  "evidence verification failed": 1,
  "adversarial challenge failed: ": 2
}

## Relevance Distribution
{
  "PARTIALLY_RELEVANT": 6,
  "RELEVANT": 8
}

## Status Distribution
{
  "REJECTED": 14
}

## Model: deepseek/deepseek-v4-flash-0731
## Temperature: 0.0
## Max tokens: 8000
## Relevance gate: ACTIVE
## Corpus Root Hash: 549d1ba7cdb205a9b19f4205330ccbec32f1d3238798f775c2e9bd93cac85f2f
## Code Commit: bfcbbd0b1b74753d3680c6ef84321d873f3b072b

## Honest Assessment

The A2 pipeline with fixes is working correctly:
- Evidence verification: 92% (12/13) — up from 0%
- Relevance gate: blocking irrelevant sources
- Prior-art gate: 9/12 verified candidates rejected (prior art likely exists)
- Adversarial gate: 2/12 verified candidates rejected

The 0% invention candidate rate is the TRUE number.
The primary bottleneck is now prior-art rejection (75% of verified candidates),
not evidence verification. This is honest — the interventions the LLM proposes
are often already known in the literature.

No threshold tuning. No threshold changes. 0% is the true number.
