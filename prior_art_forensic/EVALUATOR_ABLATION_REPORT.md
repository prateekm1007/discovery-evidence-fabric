# CLEAN EVALUATOR REPAIR ABLATION — Results

## Pre-Registered Decision Rule

- ACCEPT: specific_recall improves AND negative_rejection does not decrease AND specific_precision = 1.0
- REJECT: specific_recall does not improve OR negative_rejection decreases OR false positives appear
- STOP: If no individual change produces >=10pp recall improvement, STOP evaluator engineering

## Ablation Table

| Phase | specific_recall | negative_rejection | specific_precision | call_failures |
|-------|-----------------|--------------------|--------------------|---------------|
| A_baseline | 1.0000 | 1.0000 | 1.0000 | 1 |
| B_terminology | 1.0000 | 1.0000 | 1.0000 | 0 |
| C_claim_spec | 1.0000 | 1.0000 | 1.0000 | 1 |
| D_rel_extraction | 1.0000 | 1.0000 | 1.0000 | 1 |

## Decision

| Change | Recall Delta | Accepted? |
|--------|-------------|-----------|
| A→B (terminology) | 0.0000 | False |
| A→C (claim/spec) | 0.0000 | False |
| A→D (rel extraction) | 0.0000 | False |

**Any meaningful improvement (>=10pp): False**

## Conclusion

**STOP evaluator engineering.**

No individual change (terminology, claim/spec linkage, relationship extraction) produced
meaningful improvement over V1 baseline on the V3 dev set.

V1 baseline already achieves 100% specific_recall and 100% negative_rejection on V3 dev.
The remaining failures are on UNSEEN holdout cases, not dev cases.

The V1 holdout failures (77.78% specific_recall) were caused by:
1. Oracle bugs (IOL regex matching "iol" in "biological" — 2 false negatives were actually correct rejections)
2. API reliability (CALL_FAILED on 3 cases due to Mistral 429 rate limiting)
3. Genuinely hard cases (1 SPECIFICATION_LINKAGE + 1 FALSE_NEGATIVE on valid holdout cases)

No prompt change can fix API reliability or oracle bugs.
The evaluator has reached its performance ceiling on the current dev set.

## Frozen Configuration

- Ontology: c8ae93b52fb2c09d (UNCHANGED across all phases)
- Primary: mistral-large-latest
- Temperature: 0.0
- Dev set: V3 oracle dev cases (5 SPECIFIC + 5 NOT_SPECIFIC)
