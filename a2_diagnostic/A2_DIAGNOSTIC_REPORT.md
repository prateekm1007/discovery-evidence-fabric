# A2 Zero-Survival Diagnostic Report

## TRUE NUMBERS (honestly reported)

### Original Corpus (temp=0.3, max_tokens=2000)
- 20 candidates generated, 0 survivors, 20 rejected
- 17/20 (85%) rejected for evidence verification failure
- 3/20 (15%) rejected for prior art

### Frozen Failures Analysis (19 evidence failures)
- Source depth: 16 ABSTRACT_ONLY, 2 UNKNOWN, 1 METADATA_ONLY
- Source relevant to problem: 0/19 (0%) — RETRIEVAL QUALITY is also a major issue
- Span in full abstract: 0/19 (0%) — LLM does not produce verbatim spans at temp=0.3

### Positive Control V2 (temp=0.0, max_tokens=8000, first attempt)
- 4 candidates generated, 0 verified, 0 INVENTION_CANDIDATE
- All 4 spans wrapped in quotes → not verbatim
- Span text may exist in abstract but beyond the 500-char source_span window

### Root Cause Analysis (TWO issues identified)

**Issue 1: LLM wraps spans in quotes (temp=0.3 and temp=0.0)**
The LLM (deepseek-v4-flash-0731) wraps mechanism_source_span values in double quotes.
The verify step correctly rejects these as non-verbatim.
FIX: Strip surrounding quotes before checking.

**Issue 2: source_span is only first 500 chars of abstract**
The source_span field stored in candidate.source_evidence was truncated to 500 chars.
The LLM's mechanism span may be from a later part of the abstract.
FIX: Store full abstract (up to 2000 chars) in source_span.

**Issue 3: Retrieval quality is poor (0/19 relevant sources)**
The Europe PMC search queries return papers that are NOT relevant to the device/failure.
Example: searching for "Hip Implant CORROSION mechanism" returned a paper about e-cigarettes.
FIX: Improve query construction (add device name, use more specific queries).

### Fixes Applied (not yet fully tested)

1. **verify.py**: Strip surrounding quotes from mechanism_source_span before checking
2. **verify.py**: Check against full abstract (from evidence[0]["abstract"]), not just source_span
3. **synthesize.py**: Store full abstract (2000 chars) in source_span
4. **Model config**: temp=0.0 (was 0.3), max_tokens=8000 (was 2000)

### Preliminary Test Result
With temp=0.0 and max_tokens=8000, a direct test of verbatim extraction PASSED.
The LLM correctly copied "Gd2O3 could refine grain size, form compressive stress..."
as a verbatim substring.

### Decision
**Outcome B (modified): A2 GENERATION/GROUNDING is the primary bottleneck, with TWO fixable causes:**
1. Quote wrapping (fixed in verify.py — strip quotes)
2. Truncated source_span (fixed in synthesize.py — store 2000 chars)

**Secondary bottleneck: RETRIEVAL QUALITY (0/19 sources relevant)**
The Europe PMC query construction returns irrelevant papers for many device/failure combinations.

### No Threshold Tuning
No evidence thresholds were changed. No prior-art thresholds were changed.
No adversarial thresholds were changed. The fixes are:
- Quote stripping (a verifier implementation fix, not a threshold change)
- Full abstract storage (a data storage fix, not a threshold change)
- Temperature 0.0 (a model configuration fix, not a threshold change)
