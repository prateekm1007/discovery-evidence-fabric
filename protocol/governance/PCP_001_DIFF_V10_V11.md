# PCP-001: Deterministic Diff V1.0 → V1.1

**Status:** PROPOSED (awaiting CEO approval)
**Filed:** 2026-08-17T16:08:26.095950+00:00
**Scope:** MINIMAL — only two changes

## Change 1: Add BELOW_BUYER_THRESHOLD terminal status (§16)

**V1.0:**
```
WOULD_NOT_PAY | WOULD_CONSIDER_WITH_MILESTONES | LEVEL_4_BUYER_READY
```

**V1.1:**
```
WOULD_NOT_PAY | BELOW_BUYER_THRESHOLD | WOULD_CONSIDER_WITH_MILESTONES | LEVEL_4_BUYER_READY
```

**Definition:** `BELOW_BUYER_THRESHOLD` — hard gates (Patent + Evidence) PASS, but any soft gate FAILS OR composite < 70. Distinct from `WOULD_NOT_PAY` (hard gates fail). Distinct from `WOULD_CONSIDER_WITH_MILESTONES` (all gates pass + composite >= 70).

## Change 2: 4-concept separation (§7 + §16)

**V1.0:** Single `final_status` field

**V1.1:** 4 conceptual fields + derived `final_status`:
- `PATENT_STATUS` — 102 + 103 state
- `ENGINEERING_STATUS` — TECHNICAL + SAFETY gate state
- `BUYER_SENTIMENT` — blind test result + source (INTERNAL_SIMULATION | EXTERNAL_AUDIT)
- `BUYER_READINESS` — mechanical: READY if all gates pass + composite >= 70, else NOT_READY
- `final_status` — deterministically derived per state machine

## What does NOT change

- §7.2 non-compensable Patent + Evidence gates
- §5.9 102 single-reference rule
- §5.10 103 motivation/expectation requirement
- §3.4 provenance chain
- §9.1-9.12 all preflight checks
- Law 7 historical permanence
- §14 protocol evolution workflow
- All other sections

## Deterministic State Machine

```
Hard gate fail
    → WOULD_NOT_PAY

Hard gates pass + (any soft gate fail OR composite < 70)
    → BELOW_BUYER_THRESHOLD (V1.1) / WOULD_NOT_PAY (V1.0)

All gates pass + composite >= 70 + milestones remain
    → WOULD_CONSIDER_WITH_MILESTONES

All gates pass + composite >= 70 + no required milestones
    → LEVEL_4_BUYER_READY
```

No LLM/model may select FINAL_STATUS.

## Approval

Requires CEO approval. The agent who filed PCP-001 cannot approve it.
