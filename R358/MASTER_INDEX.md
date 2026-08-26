# R358 — PATENT INTELLIGENCE CONNECTOR CORRECTION

**Generated:** 2026-08-26T07:57:46.596592+00:00

## Connector Status

| Provider | Status | Detail |
|----------|--------|--------|
| PatentBear | ✅ WORKING | MCP, Bearer auth, 15/15 searched, 1/20 remaining |
| PatSnap | ❌ NOT WORKING | Keys rejected on documented endpoint. Auth error 67200202. |
| Lens | ❌ NOT WORKING | 401 — token lacks patent scope |
| EPO OPS | ❌ Not implemented | Requires OAuth registration |
| USPTO/WIPO | 🟡 Web only | Not API-integrated |

## PatentBear Results (REAL — not web search)

| Package | Hits | Unique Refs | Verdict |
|---------|------|-------------|---------|
| P-16 | 5 | 5 | PASS |
| P-01 | 0 | 0 | PASS |
| P-24 | 0 | 0 | PASS |
| P-21 | 5 | 5 | PASS |
| P-13 | 0 | 0 | PASS |
| P-02 | 0 | 0 | PASS |
| P-04 | 0 | 0 | PASS |
| P-07 | 0 | 0 | PASS |
| P-11 | 0 | 0 | PASS |
| P-12 | 0 | 0 | PASS |
| P-15 | 0 | 0 | PASS |
| P-20 | 0 | 0 | PASS |
| P-22 | 0 | 0 | PASS |
| P-26 | 0 | 0 | PASS |
| P-27 | 0 | 0 | PASS |

## Adversarial Verdicts: 15 PASS, 0 CONDITIONAL, 0 REPAIR

## Honest Scoreboard

- Coder-completable: **11/20** items addressed
- Reality-dependent: **4/20** items require real buyer/experiment
- The 4 reality-dependent items CANNOT be completed by coding. They require:
  1. Real external experiment (CEO commissions)
  2. Real buyer feedback (CEO contacts buyers)
  3. Buyer-funded experiment (CEO negotiates)
  4. V2 based on real evidence (data ingested via R341)

## Key Correction

PatentBear MCP is WORKING. Real patent search results retrieved for all 15 packages.
This is NOT web search — this is a real patent database with full metadata (CPC, inventors, dates, abstracts).

PatSnap keys are rejected on the documented endpoint (/search/patent/query-search-patent/v2).
The keys work on the legacy endpoint (/api/search) but return balance errors (67200203).
Contact PatSnap support to verify key type and account status.

Lens token returns 401 — log into lens.org and verify patent scope is authorized.
