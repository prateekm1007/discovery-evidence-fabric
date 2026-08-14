# Patent Access Recovery — Status Report

## Status: CALIBRATION_BLOCKED

## Block Type Classification

| Block Type | Sources |
|-----------|---------|
| CREDENTIAL_BLOCKED | EPO OPS, USPTO Open Data Portal, Lens.org |
| ACCESS_BLOCKED | Google Patents (pages), USPTO PatentsView, WIPO Patentscope, USPTO PEDS, USPTO Bulk Data |
| INTEGRATION_BLOCKED | HuggingFace AIPD (has claims but ~90% software patents, rate-limited) |
| DATA_NOT_FOUND | None — patent data exists globally but is not machine-accessible from this environment |

## Sources with Real Patent Claim Text

### ACTIVE but insufficient:
1. **Google Patents (search API)** — returns snippets only (100-200 chars), not full claims
2. **HuggingFace AIPD_nlp_granted_claims** — has real US patent claims but:
   - Dataset is ~90% software patents
   - Medical device/material patents are rare (~5-12% of rows)
   - Rate-limited after 6600 rows (429 Too Many Requests)
   - Could not find enough device-specific claims for 20-case oracle

### PENDING_CREDENTIALS (would provide full claim text):
1. **EPO OPS** — OAuth 2.0 registration at epo.org (FREE for non-commercial use)
2. **USPTO Open Data Portal** — API key at developer.uspto.gov
3. **Lens.org** — API token at lens.org

## Path to Unblock

### Option 1: EPO OPS Registration (RECOMMENDED)
- Register at: https://developers.epo.org/
- Get OAuth 2.0 client_id and client_secret
- Provides: Full claim text for EP, WO, US, JP, CN, KR patents
- Free for non-commercial use (quota-based)
- This is the FASTEST path to unblocking calibration

### Option 2: USPTO Open Data Portal Registration
- Register at: https://developer.uspto.gov
- Get API key
- Provides: US patent data (scope unknown without key)

### Option 3: Lens.org API Token
- Register at: https://www.lens.org/
- Get API token
- Provides: Patent claims, metadata, citations

## What NOT to do
- Do NOT use Google Patents snippets as oracle (insufficient for SPECIFIC vs NOT_SPECIFIC)
- Do NOT use LLM-generated patent claims as oracle
- Do NOT lower the 80% calibration threshold
- Do NOT modify the prior-art kill rule

## Current State
- Regression matrix: PASS (all 6 rows)
- classify.py fix: APPLIED (only SPECIFIC_DISCLOSURE kills)
- V1/V2/V3 reclassification: COMPLETE (95.8% false kill rate)
- Calibration: BLOCKED (no full patent claim text accessible)
- Corpus generation: BLOCKED (pending calibration)
- Simulation: BLOCKED (pending corpus)
