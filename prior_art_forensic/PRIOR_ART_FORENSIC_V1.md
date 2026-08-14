# V1/V2/V3 Prior-Art Forensic Reclassification

## TRUE NUMBERS

| Metric | Value |
|--------|-------|
| Total candidates | 53 |
| WRONG_TARGET | 1 |
| TRUE_SPECIFIC_PRIOR_ART | 0 |
| TOPICAL_ONLY (false kill) | 14 |
| FALSE_PRIOR_ART_KILL | 9 |
| POSSIBLE_PRIOR_ART | 1 |
| EVIDENCE_FAILURE | 22 |
| ADVERSARIAL_NON_PRIOR_ART | 6 |

## Key Finding

Of 24 candidates previously rejected for "prior art likely exists":
- 0 were TRUE_SPECIFIC_PRIOR_ART (correct kill)
- 14 were TOPICAL_ONLY (false kill — papers discuss same topic but don't disclose the intervention)
- 9 were FALSE_PRIOR_ART_KILL (no match found)
- 1 were POSSIBLE_PRIOR_ART (may relate but don't specifically disclose)

**False kill rate: 37.5%**
**Topical-only rate: 58.3%**

## Target Alignment

{'ON_TARGET': 46, 'UNKNOWN': 2, 'PARTIALLY_ON_TARGET': 4, 'OFF_TARGET': 1}

## New Classification Distribution

{'TOPICAL_ONLY': 14, 'FALSE_PRIOR_ART_KILL': 9, 'EVIDENCE_FAILURE': 22, 'ADVERSARIAL_NON_PRIOR_ART': 6, 'WRONG_TARGET': 1, 'POSSIBLE_PRIOR_ART': 1}

## Prior-Art State Distribution

{'TOPICAL_RELATED': 14, 'NO_MATCH_FOUND': 9, 'NOT_EVALUATED': 29, 'POSSIBLE_RELEVANCE': 1}
