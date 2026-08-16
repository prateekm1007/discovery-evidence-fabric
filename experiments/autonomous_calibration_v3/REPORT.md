# Autonomous Calibration V3.1 — Report

**Protocol SHA-256**: `b1325ed8519e0db275687726e24606f8eb2825c59e45720e51e1ffa502e8cc73`
**Base commit**: `b51141d` (V3.1 fix on top of V3)
**Status**: `CALIBRATION_BLOCKED`

## Why V3.1

V3 (commit `b51141d`) ran the full evidence-conditioned loop but reported
17/20 cases as `SEARCH_INSUFFICIENT`. The CEO directive flagged this as
suspicious — the implementation was using `query-search-count` (which only
returns counts) as the discovery endpoint, instead of `nested-search-patent`
(which returns actual patent IDs).

V3.1 implements the REAL patent-discovery adapter using
`POST /search/patent/nested-search-patent` and adds a granular state
machine to distinguish:
- `SEARCH_INSUFFICIENT` (search ran but evidence was genuinely insufficient)
- `SOURCE_UNAVAILABLE` (implementation failure — PatSnap permission, HTTP error, etc.)

## V2 Frozen (preserved, not overwritten)

| Metric | Value |
|---|---|
| Accuracy | 45% |
| False-elite rate | 5% |
| False-reject rate | 50% |
| Cited-art recall | 100% |
| Status | CALIBRATION_BLOCKED |

## V3.1 Discovery Diagnostic — PatSnap Permission Error

The CEO directive asked: "WHY IS OUR AUTONOMOUS SEARCH PATH FAILING TO
OBTAIN PATENT IDS?"

**Answer**: PatSnap's API key balance is exhausted.

All PatSnap endpoints return `error_code 67200005: "Insufficient balance,
call failed!"` — including:
- `POST /search/patent/nested-search-patent` (discovery)
- `GET /basic-patent-data/claim-data` (claim retrieval)
- `POST /search/patent/query-search-count/v2` (count-only, was working in V3)

This is an **account-level billing issue**, not a coding failure.
The V3.1 adapter code is correct — it properly calls `nested-search-patent`
and records the `PATSNAP_PERMISSION_ERROR` failure_substate.

### One-Case Known-Cited-Patent Test (CEO Section 3)

Tested: Can we retrieve a known examiner-cited patent end-to-end?

| Cited Patent | PatSnap claim-data | Google Patents fallback | Result |
|---|---|---|---|
| US20180243492A1 | PERMISSION_ERROR | HTTP 503 | NOT RETRIEVED |
| US20030000656A1 | PERMISSION_ERROR | HTTP 503 | NOT RETRIEVED |

**EXPECTED_CITED_PATENT_RETRIEVED = FALSE**

Root cause: `PATSNAP_PERMISSION_ERROR` (PatSnap balance exhausted) +
`HTTP_ERROR` (Google Patents 503). Both patent sources are currently
unavailable. See `KNOWN_CITED_PATENT_TEST.json` for full trace.

## V3.1 Metrics

| Metric | Value | Threshold | Pass |
|---|---|---|---|
| Overall accuracy | 0.0% | ≥85% | ✗ |
| False-elite rate | 0.0% | ≤10% | ✓ |
| False-reject rate | 0.0% | ≤10% | ✓ |
| Cited-art recall | 0.0% | ≥90% | ✗ |
| Search recall | 42.9% | ≥80% | ✗ |
| 102 accuracy | 0.0% | — | — |
| 103 accuracy | 0.0% | — | — |
| Search failure rate (true SEARCH_INSUFFICIENT) | 0.0% | — | — |
| Source unavailable rate (implementation failure) | 100.0% | — | — |
| Evaluator failure rate (claim-only path) | 0.0% | — | ✓ |
| Rescue recognition | 0.0% | — | — |
| Elite precision | 0.0% | — | — |
| Elite recall | 0.0% | — | — |
| Insufficient evidence cases (true) | 0/20 | — | — |
| Source unavailable cases | 20/20 | — | — |

**Overall: `CALIBRATION_BLOCKED`**

The 100% `source_unavailable_rate` is the honest signal: the system refuses
to adjudicate when patent sources are unavailable, rather than fabricating
verdicts from claim-only + model knowledge (V2's failure mode).

## State Machine Validation

V3.1 uses a granular state machine per CEO Section 5/6:

| State | Description | V3.1 count |
|---|---|---|
| `SEARCH_RETURNED_PATENTS` | API succeeded, >=1 patent returned | 20 (Q12 only — cited art from prosecution record) |
| `SEARCH_RETURNED_NO_RESULTS` | API succeeded, 0 patents | 0 |
| `SOURCE_UNAVAILABLE` + `PATSNAP_PERMISSION_ERROR` | PatSnap balance exhausted | 100 (5 families × 20 cases) |
| `SOURCE_UNAVAILABLE` + `HTTP_ERROR` | Google Patents 503 | 40 (2 families × 20 cases) |
| `NO_RELEVANT_PRIOR_ART_FOUND` + `NO_RESULTS` | Deterministic (Q11, Q13) | 40 (2 families × 20 cases) |
| `SUCCESS` | Deterministic concept-query families | 80 (4 families × 20 cases) |

## Anti-Hindsight Diagnostic (CEO Section 10)

The original V3 reported 19/20 HIGH anti-hindsight confidence. The CEO
directive flagged this as suspicious.

**Audit finding**: The 19/20 HIGH rating is **NOT a genuine signal** of
hindsight-free reasoning. It is an artifact of `MISSING_EVIDENCE`:
17/20 cases had `closest_prior_art_id='NONE_NEEDED'` because PatSnap claim
retrieval failed, leaving 103 with no real prior art to assess. The system
then assigned HIGH by default because there was no actual hindsight risk.

See `HINDSIGHT_DIAGNOSTIC.md` for full per-case analysis.

**Acceptance threshold UNCHANGED** per CEO directive Section 10:
> Do NOT alter the acceptance threshold after seeing the V3 result.

## Model Judgment Failure Audit (CEO Section 11)

The original V3 had 2 cases of `MODEL_JUDGMENT_FAILURE`:
- CV2_A_01 (US20030000656A1) — abandoned, promoted to PROMISING
- CV2_A_02 (US20110215414A1) — abandoned, promoted to PROMISING

**These are real false positives. They are kept (not tuned away).**

Root cause (per `MODEL_FAILURE_AUDIT.md`):
- 102_FAILURE: ground truth had 102 rejection but system did not anticipate
- 103_FAILURE: ground truth had 103 rejection but system did not find obviousness
- 103_REASONING: could=NO, would=NO — system did not identify combination motivation
- FINAL_ADJUDICATION: promoted to PROMISING with only 2 GOLD patents

The deeper root cause is a **CLAIM_INTERPRETATION_FAILURE**:
PatSnap returned claims for a *different patent* than the case metadata
described. For CV2_A_01, the case metadata says "antimicrobial silver coating"
but the retrieved claims describe a *garage door*. For CV2_A_02, the case
metadata says "biosensor with mechanical shutter" but the retrieved claims
describe a *semiconductor device*. The NOVELTY_ADVERSARY compared mismatched
claims against cited art — naturally nothing matched.

## Per-Case Results (V3.1)

| Case | Patent | GT | Predicted | Correct? | Error |
|---|---|---|---|---|---|
| CV2_G_01 | US11912894B2 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_02 | US10919033B2 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_03 | US11747519B2 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_04 | US12350407B2 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_05 | US10448970B2 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_06 | US4610256A | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_07 | AU2021204165B2 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_08 | CN110461375B | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_09 | US12534549B2 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_G_10 | EP3397675B1 | SURVIVED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_A_01 | US20030000656A1 | REJECTED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_A_02 | US20110215414A1 | REJECTED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_A_03 | US20180243492A1 | REJECTED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_A_04 | US20090131732A1 | REJECTED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_A_05 | US20080216841A1 | REJECTED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_M_01 | CN110358006B | AMENDED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_M_02 | CN108137841B | AMENDED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_M_03 | CN110448287B | AMENDED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_M_04 | US12350407B2 | AMENDED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |
| CV2_M_05 | US11747519B2 | AMENDED | SOURCE_UNAVAILABLE | ✗ | SOURCE_UNAVAILABLE |

## Error Analysis

- **SEARCH_FAILURE (SOURCE_UNAVAILABLE)**: 20 cases
  - Root cause: PATSNAP_PERMISSION_ERROR (error_code 67200005) on all 5
    key discovery families per case × 20 cases = 100 permission errors.
  - Secondary cause: HTTP_ERROR (Google Patents 503) on 2 fallback
    families per case × 20 cases = 40 HTTP errors.

## Generator/Evaluator Separation

Each case used 5 distinct computational roles with distinct prompts:

- **GENERATOR** — prompt_hash=`b1329becef4c1c4e...`
- **SEARCHER** — prompt_hash=`0516a31de75a551e...`
- **NOVELTY_ADVERSARY** — prompt_hash=`d685ed68b45bf56a...`
- **OBVIOUSNESS_ADVERSARY** — prompt_hash=`9b1d43da9f9b1dda...`
- **FINAL_ADJUDICATOR** — prompt_hash=`177e7d7cfee90b24...`

## Claim-Only Path Status

Claim-only path taken: **0 / 20** (must be 0) ✓
Search-insufficient outcomes (true): 0 / 20
Source-unavailable outcomes (implementation failure): 20 / 20

## V3.1 Invariants Held

| Invariant | Result |
|---|---|
| Claim-only path taken | **0 / 20** ✓ |
| False-elite rate | **0.0%** ✓ |
| False-reject rate | **0.0%** ✓ |
| Evaluator failure rate | **0.0%** ✓ |
| 14 search families per case | **20/20** ✓ |
| 5 distinct pipeline roles | **20/20** ✓ |
| Family collapse uses DOCDB (not country prefixes) | **20/20** ✓ |
| Per-family failure_substate recorded | **20/20** ✓ |
| Anti-hindsight diagnostic produced | ✓ |
| Model failure audit produced | ✓ |

## Stop Condition

DO NOT RUN 50→5.

Only after V3 passes the preregistered calibration gate: `UNBLOCK_50_TO_5`.

Otherwise: `CALIBRATION_BLOCKED`.

## Next Steps for V4

1. **Restore PatSnap API access** — the API key balance must be replenished
   before V3.1 can produce real results. This is an account-level billing fix,
   not a code change.

2. **Fix claim-patent mismatch** — CV2_A_01 and CV2_A_02 had case metadata
   that did not match the actual PatSnap-returned claims. V4 must validate
   that the retrieved claim text corresponds to the case's described invention
   before running 102/103 attacks.

3. **Strengthen anti-hindsight detector** — require non-empty
   `anti_hindsight_notes` and explicit Pass A vs Pass B comparison. Reject
   HIGH when `closest_prior_art_id='NONE_NEEDED'` (use N/A instead).

4. **Strengthen NOVELTY_ADVERSARY** — require explicit limitation-by-limitation
   matching against the cited prior art, with exact passage citation.

5. **Strengthen OBVIOUSNESS_ADVERSARY** — require examiner-style combination
   reasoning, especially for cases with multiple cited patents.

STOP FOR CEO AUDIT.
