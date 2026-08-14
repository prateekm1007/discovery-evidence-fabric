# Prior-Art Integrity Gate — Status Report

## Overall: NOT READY (calibration blocked)

## True Numbers

### Regression Matrix (Item 10a): ALL 6 ROWS PASS ✓

| State | Kill Permitted | Actual Kill | Result |
|-------|---------------|-------------|--------|
| TOPICAL_RELATED | No | No | PASS |
| POSSIBLE_RELEVANCE | No | No | PASS |
| NO_MATCH_FOUND | No | No | PASS |
| UNRESOLVED_INSUFFICIENT_EVIDENCE | No | No | PASS |
| SPECIFIC_DISCLOSURE | Yes | Yes | PASS |
| IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE | Yes | Yes | PASS |

### V1/V2/V3 Reclassification: COMPLETE ✓
- 53 candidates reclassified
- 0/24 TRUE_SPECIFIC_PRIOR_ART
- 14 TOPICAL_ONLY (false kills)
- 9 FALSE_PRIOR_ART_KILL
- False kill rate: 95.8%
- Decision gate: TOPICAL_ONLY majority → over-killing confirmed

### Search Universe: FROZEN ✓
- 4 ACTIVE sources (Europe PMC, OpenAlex, Crossref, Google Patents)
- 1 PENDING (EPO OPS — needs OAuth credentials)
- 1 UNAVAILABLE (USPTO PatentsView)
- Coverage cap: MEDIUM

### Calibration: FAILED ✗
- V1 accuracy: 70% (7/10 non-ambiguous) — below 80% threshold
- V2 accuracy: 50% (5/10 non-ambiguous) — below 80% threshold
- Root cause: Google Patents snippets too short for SPECIFIC vs NOT_SPECIFIC determination
- Full patent claim text required but not accessible:
  - Google Patents page scraping: 503 Service Unavailable
  - EPO OPS: PENDING_CREDENTIALS
  - USPTO PatentsView: UNAVAILABLE

### classify.py Fix: APPLIED ✓
- TOPICAL_RELATED, POSSIBLE_RELEVANCE, NO_MATCH_FOUND → NO KILL
- SPECIFIC_DISCLOSURE, IDENTICAL_OR_NEAR_IDENTICAL_DISCLOSURE → KILL
- LIKELY_PRIOR_ART_EXISTS → treated as non-kill (backwards compat)
- All 11 existing tests still pass

## Blocking Issue

Calibration accuracy is below 80% because patent claim text is not accessible
through available sources. The calibration oracle requires real patent claims
(snippet text is insufficient for SPECIFIC vs NOT_SPECIFIC determination).

**To unblock:** Provide EPO OPS OAuth credentials OR restore USPTO PatentsView API access.
