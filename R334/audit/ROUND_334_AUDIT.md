# R334 AUDIT — Thin CRM-Compatible Commercialization Layer

**Round:** 334
**Date:** 2026-08-26
**Remote HEAD:** (R334 pending push)
**Constitution hash:** `f82ae4f665dcb5a59ae399017feed57dd24242fe35d98a897806d559064762a5`

## Architecture: Technology-Transfer-First, CRM-Compatible

Two systems, one interface:

```
TECHNOLOGY FABRIC (owns truth)     CRM / BUYER (owns relationships)
├── Evidence                        ├── Companies
├── Mechanism                       ├── Contacts
├── Experiments                     ├── Conversations
├── Failures                        ├── NDA
├── State (T-level)                 ├── Interest
├── Provenance                      ├── Diligence
├── Knowledge (scientific KA)       ├── Follow-up
├── EIG                             ├── Deal status
└── Buyer packages (technical)      └── Objections
         │                                    │
         └────────── BRIDGE ──────────────────┘
                    │
          Commercial KA (distinct from scientific KA)
          AI uses for: candidate search priority,
          packaging emphasis, experiment selection
          AI CANNOT use for: technical state changes
```

## What was built

### 1. Commercial layer specification
- Buyer opportunity schema (buyer_id, candidate_id, interest_level, stage, objections, diligence, next_action, commercial_outcome)
- Buyer-specific packaging (same truth, different emphasis by buyer type)
- Commercialization funnel tracking (15→150→50→25→12→7→3→1)
- Evidence classification for commercial numbers (OBSERVED/ESTIMATED/ASSUMED)

### 2. Commercial knowledge atoms (CKA)
- Aggregated buyer objections create CKA (distinct from scientific KA)
- CKA influences: candidate search, packaging emphasis, experiment prioritization
- CKA CANNOT influence: technical state, evidence ledger, falsification, scientific KA
- Example: CKA-001 (3/4 buyers mention integration burden for P-16) → AI prioritizes lower-integration mechanisms in next search. P-16 remains T2-CONFIRMED.

### 3. Separation enforcement (5 tests)
- SEP-001: Buyer enthusiasm (HIGH interest) → T-level unchanged ✅
- SEP-002: Buyer rejection (REJECTED) → candidate not demoted to CEMETERY ✅
- SEP-003: 5 buyers object → CKA created, no scientific KA, evidence unchanged ✅
- SEP-004: Buyer experiment PASS → state changes ONLY through evidence pipeline, not CRM ✅
- SEP-005: Deal NEGOTIATION → does NOT grant T5 ✅

## What was NOT built

- No lead scores, sales stages, email tracking, opportunity dashboards
- No "Salesforce for inventions"
- No CRM controlling scientific truth
- No buyer enthusiasm promoting technical readiness
- No buyer rejection demoting technical state

## The critical rule

> **CRM data cannot alter technical evidence, technical state, provenance, falsification results, or knowledge atoms.**
> 
> Buyer feedback can create commercial knowledge atoms, but those must remain explicitly distinct from scientific evidence.
> 
> The AI may use aggregated buyer feedback to prioritize redesign, experiment selection, candidate search, and packaging — but buyer enthusiasm/rejection can never promote or demote technical readiness.

## Current state

- 0 companies contacted (CEO-owned)
- 0 buyer interactions recorded
- 0 commercial KAs created
- Machine ready to track when CEO begins outreach
- Commercial layer spec committed, ready for implementation when buyer interactions begin

## What remains

- **5+ candidate search** (Gate 10 from R332, not yet executed)
- **Real external data** (CEO-owned)
- **CRM implementation** (thin layer, when buyer interactions begin)
- **15/15 target**: 13 active + 2 vacancy
