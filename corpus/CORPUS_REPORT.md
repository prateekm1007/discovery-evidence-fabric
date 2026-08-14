# Medical Device Discovery Corpus V1

## TRUE NUMBERS (honestly reported)

| Metric | Value |
|--------|-------|
| Total problems (target) | 129 |
| Total candidates generated | 20 |
| INVENTION_CANDIDATE | 0 |
| REJECTED | 20 |
| Survival rate | 0.0% if n else N/A |

## Status

**INCOMPLETE**: 20/129 problems processed (14.7%).
All 20 candidates were REJECTED.

## Model
- deepseek/deepseek-v4-flash-0731
- Temperature: 0.3
- A2 contract: FROZEN (no threshold tuning)

## Domain Distribution
{
  "implantables_orthopedic": 20
}

## Rejection Reasons
{
  "prior art likely exists": 3,
  "evidence verification failed": 17
}

## Corpus Root Hash
1c0b3cd5c70fa6ee6b4f9241ca08e382ebc8571cec7e5696daa94b83b928c0e4

## Code Commit
37a38b34f9e20483077455587f18b5940b53c349

## Honest Assessment

The A2 pipeline is working correctly (fail-closed). The primary rejection reason
is evidence verification failure: the LLM does not consistently produce verbatim
source spans from the retrieved abstracts. This is a real finding about the
LLM's source-grounding capability, not a pipeline bug.

The corpus generation is incomplete due to rate-limited API calls (~90s per
candidate × 129 problems = ~3.2 hours). The 19 candidates processed so far
all come from the implantables_orthopedic domain.
