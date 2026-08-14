# A2 Zero-Survival Diagnostic Report

## Decision: **B — Rich-source positives STILL FAIL evidence verification. A2 GENERATION/GROUNDING is the bottleneck.**

## True Numbers

### Frozen Failures (19)

| Metric | Value |
|--------|-------|
| Source relevant to problem | 0/19 |
| Span in full abstract | 0/19 |
| Source depth | {'ABSTRACT_ONLY': 16, 'UNKNOWN': 2, 'METADATA_ONLY': 1} |

### Positive Control (3)

| Metric | Value |
|--------|-------|
| Evidence verified | 0/3 |
| INVENTION_CANDIDATE | 0/3 |
| ALL FAILED VERIFICATION | True |

### Null Control
Not completed — positive control failure already identifies the bottleneck.

## Root Cause

**The LLM (deepseek-v4-flash-0731) does not produce verbatim source spans.**

Even with evidence-rich sources (vitamin E UHMWPE, Gd2O3 alumina, drug-eluting stents),
the mechanism_source_span field contains paraphrased or quoted text that is NOT a
verbatim substring of the source abstract.

This is an **LLM grounding capability issue**, not a retrieval or source depth issue.

The verify step correctly rejects non-verbatim spans (as designed).
The LLM fails to copy exact text from the source.

## Evidence

Positive control candidates (all FAILED evidence verification):

- pos01: span=""Highly cross-linked polyethylene has substantiall..."
  source starts: "Tribological failure remains a leading cause of re..."
  verified: False

- pos02: span=""high hardness"..."
  source starts: "Silicon carbide (SiC) ceramics are among the most ..."
  verified: False

- pos03: span=""an interlocking mechanism was established in whic..."
  source starts: "Commercially available drug-eluting stents still s..."
  verified: False

## What This Means

1. Source depth is NOT the bottleneck (all sources are ABSTRACT_ONLY but the abstracts contain mechanism evidence)
2. Retrieval quality is a secondary issue (0/19 frozen failures had relevant sources)
3. The PRIMARY bottleneck is **A2 LLM generation** — the LLM cannot produce verbatim spans
4. The evidence verifier is working correctly (it rejects non-verbatim text)
5. The A2 contract's verbatim span requirement is the correct design — the LLM just can't meet it yet

## Recommendation

The A2 pipeline architecture is correct. The bottleneck is the LLM's ability to
copy verbatim text from the source. Options:
1. Use a model with better instruction-following for verbatim extraction
2. Add a post-processing step that strips quotes/paraphrasing and attempts fuzzy matching
3. Relax to near-verbatim (allow minor whitespace/punctuation differences)
4. Use a separate extraction call dedicated to copying exact spans
