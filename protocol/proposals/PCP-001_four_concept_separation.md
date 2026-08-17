# PCP-001: Four-Concept Separation + BELOW_BUYER_THRESHOLD Terminal Status

**Filed:** 2026-08-17T15:43:16.629513+00:00
**Filed by:** Main agent (Super Z) — per CEO directive 2026-08-17
**Status:** PROPOSED
**Supersedes:** None (new addition to V1)

## Rationale

V3 FINAL (commit `278907c`) had a silent-promotion bug: composite 68.1 < 70 but verdict said `WOULD_CONSIDER_WITH_MILESTONES`. The root cause was conflating four distinct concepts into one `final_status` field. V3.1_FINAL (commit `b034142`) fixed this operationally by separating `PATENT_STATUS`, `ENGINEERING_STATUS`, `BUYER_SENTIMENT`, and `BUYER_READINESS`, but did so outside the constitution. This PCP formalizes the separation so future inventions use it canonically.

## Proposed Changes

### 1. Add `BELOW_BUYER_THRESHOLD` as a 4th terminal status in §16

**Current:** `WOULD_NOT_PAY | WOULD_CONSIDER_WITH_MILESTONES | LEVEL_4_BUYER_READY`

**Proposed:** `WOULD_NOT_PAY | BELOW_BUYER_THRESHOLD | WOULD_CONSIDER_WITH_MILESTONES | LEVEL_4_BUYER_READY`

**Definition:** `BELOW_BUYER_THRESHOLD` — composite < 70 OR any soft gate < threshold, but hard gates (Patent + Evidence) PASS and buyer sentiment is conditionally positive. Distinct from `WOULD_NOT_PAY` (hard gates fail or buyer sentiment is negative).

**Use case:** Invention #1 V3.1_FINAL: hard gates PASS (102 proven, evidence primary), but technical (58<65) and commercial (62<65) below threshold. Calling this `WOULD_NOT_PAY` would be misleading — the IP is proven, the engineering just needs physical validation. `BELOW_BUYER_THRESHOLD` is the honest label.

### 2. Formalize 4-concept separation in §7 and §16

**Field definitions:**
- `PATENT_STATUS` — 102_STATUS + 103_STATUS (e.g., `102_PROVEN / 103_UNCERTAIN`)
- `ENGINEERING_STATUS` — TECHNICAL_GATE + SAFETY_GATE status (e.g., `BELOW_THRESHOLD`)
- `BUYER_SENTIMENT` — Blind buyer test result + `BUYER_SENTIMENT_SOURCE` (`INTERNAL_SIMULATION | EXTERNAL_AUDIT`)
- `BUYER_READINESS` — Mechanical state: `READY` (all gates pass + composite >= 70) | `NOT_READY` (any gate fails or composite < 70). This is NOT a sentiment — it is a machine computation.

### 3. Update `22_FINAL_ADJUDICATION.json` template

Add fields: `patent_status`, `engineering_status`, `buyer_sentiment`, `buyer_sentiment_source`, `buyer_readiness`. The `final_status` field is derived from `buyer_readiness` per the state machine.

## Constitutional Invariants Preserved

- Non-compensable status of Patent and Evidence gates (§7.2) — unchanged
- 102 single-reference rule (§5.9, §9.4) — unchanged
- 103 motivation/expectation requirement (§5.10, §9.5) — unchanged
- Provenance chain requirement (§3.4, §9.3, §10) — unchanged
- Historical permanence (§7 Law 7) — V2 verdicts preserved, V4 supersedes

## Approval Criteria

1. CEO reviews and approves the 4th terminal status (`BELOW_BUYER_THRESHOLD`)
2. CEO reviews and approves the 4-concept separation schema
3. PCP is merged into V1 constitution via Protocol Evolution Workflow (§14)
4. V1 constitution remains frozen; PCP-001 creates V1.1

## Impact on Existing Inventions

- `CEREVASC_INVENTION_001_V2`: preserved (historical), verdict unchanged
- `CEREVASC_INVENTION_001_V4` (new): uses 4-concept schema, `BUYER_READINESS=NOT_READY`, `final_status=BELOW_BUYER_THRESHOLD`
- `CEREVASC_INVENTION_002_V1`: requires re-adjudication under V1.1 (currently has inflation pattern — 75% model-derived evidence but Evidence gate scored 70/PASS)
- Future inventions (#3-#150): use V1.1 schema from start
