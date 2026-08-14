# Patent Calibration Blocked

## Status: CALIBRATION_BLOCKED

No machine-readable patent source with full claim text is currently accessible.

## Sources Tested

| Source | Status | Claims Available | Full Text | Machine Readable |
|--------|--------|-----------------|-----------|-----------------|
| USPTO PatentsView | UNAVAILABLE | False | False | False |
| USPTO Open Data Portal | PENDING_CREDENTIALS | Unknown — cannot test without API key | Unknown | True |
| EPO Open Patent Services (OPS) | PENDING_CREDENTIALS | True | True | True |
| Google Patents (search API) | ACTIVE | False | False | True |
| Google Patents (full page) | UNAVAILABLE | True | True | False |
| WIPO Patentscope | UNAVAILABLE | True | True | False |
| Lens.org | UNAVAILABLE | True | True | False |
| USPTO PEDS | UNAVAILABLE | False | False | True |
| USPTO Bulk Data | UNAVAILABLE | True | True | True |


## Why Snippets Are Insufficient

Google Patents search API returns snippets of 100-200 characters. These snippets:
1. Do not contain full patent claims
2. Do not contain enough context to determine SPECIFIC_DISCLOSURE vs NOT_SPECIFIC_DISCLOSURE
3. Are often from the patent abstract, not the claims section
4. Cannot serve as oracle evidence for calibration

Calibration V1 accuracy: 70% (7/10 non-ambiguous)
Calibration V2 accuracy: 50% (5/10 non-ambiguous)
Required: 80%

The evaluator consistently confuses SPECIFIC and NOT_SPECIFIC when given only snippets.

## Credential Requirements

### EPO OPS (best option)
- Registration: https://www.epo.org/searching-for-patents/technical/espacenet/ops.html
- Auth: OAuth 2.0 client credentials
- Provides: Full claim text, description, classification
- Coverage: EP, WO, US, JP, CN, KR

### USPTO Open Data Portal
- Registration: https://developer.uspto.gov
- Auth: API key (X-Api-Key header)
- Provides: Unknown (cannot test without key)
- Coverage: US patents

## Alternative Sources Investigated

1. Google Patents full pages → 503 Service Unavailable
2. WIPO Patentscope → 403 Forbidden
3. Lens.org → 403 Forbidden
4. USPTO PEDS → empty response
5. USPTO Bulk Data → no response
6. Europe PMC → scientific papers, not patent claims
7. OpenAlex → scientific papers, not patent claims

## Conclusion

Patent calibration cannot proceed without either:
1. EPO OPS OAuth credentials, OR
2. USPTO Open Data Portal API key

No other source provides machine-readable full patent claim text.

The regression matrix (Item 10a) PASSES — the prior-art state machine is correctly implemented.
The calibration oracle cannot be built without patent claim text access.

## Impact on Corpus Generation

Corpus generation remains BLOCKED until calibration passes.
The prior-art gate fix (classify.py) is correctly implemented and tested.
The calibration gate is the only remaining blocker.
