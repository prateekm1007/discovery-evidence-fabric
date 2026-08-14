# Patent Claim Access Report V4

## Status: CALIBRATION_BLOCKED

## Endpoint Test Results

| Endpoint | Status | Claims? | Auth Required |
|----------|--------|---------|---------------|
| PatentsView g_claim | ENDPOINT_UNAVAILABLE | No | N/A (decommissioned) |
| PatentsView pg_claim | ENDPOINT_UNAVAILABLE | No | N/A (decommissioned) |
| search.patentsview.org | ENDPOINT_UNAVAILABLE | No | N/A (DNS fails) |
| USPTO ODP api.uspto.gov | AUTHENTICATION_BLOCKED | Unknown | API key |
| EPO OPS | AUTHENTICATION_BLOCKED | Yes (with auth) | OAuth 2.0 |
| Google Patents search | NO_CLAIM_DATA | No (snippets) | None |
| Google Patents pages | ENDPOINT_UNAVAILABLE | Yes (blocked) | None (503) |

## Classification

- **ENDPOINT_UNAVAILABLE**: 4 endpoints (PatentsView g_claim, pg_claim, search host, Google Patents pages)
- **AUTHENTICATION_BLOCKED**: 2 endpoints (USPTO ODP, EPO OPS)
- **NO_CLAIM_DATA**: 1 endpoint (Google Patents search — snippets only)

## Medical Device Coverage Test

Cannot be completed — no endpoint provides machine-readable claim text.

## Existing Repository Connectors

The discovery-evidence-fabric repository has NO patent connectors implemented.
The connectors README lists USPTO, EPO, WIPO as TODO items.
Only the OpenAlex mapper (scientific papers) is implemented.

## Path to Unblock

### Option 1: EPO OPS (RECOMMENDED — fastest)
- Register at: https://developers.epo.org/
- Get OAuth 2.0 client_id and client_secret
- Provides: Full claim text for EP, WO, US, JP, CN, KR patents
- Free for non-commercial use
- API endpoint: ops.epo.org/3.2/rest-services/

### Option 2: USPTO Open Data Portal
- Register at: https://developer.uspto.gov
- Get API key
- May provide claim text (untested — requires auth)

### Option 3: Google Patents (if rate-limit clears)
- Wait for 503 to clear
- Scrape patent pages for claim text
- Not reliable for automated pipeline

## What Passed (unchanged from previous tasks)
- Regression matrix: ALL 6 ROWS PASS
- classify.py fix: APPLIED (only SPECIFIC_DISCLOSURE kills)
- V1/V2/V3 reclassification: COMPLETE (95.8% false kills)

## What Failed
- Patent claim text access: BLOCKED (CREDENTIAL_BLOCKED + ENDPOINT_UNAVAILABLE)
- Calibration oracle: Cannot build without claim text
- Calibration accuracy: Cannot measure without oracle
