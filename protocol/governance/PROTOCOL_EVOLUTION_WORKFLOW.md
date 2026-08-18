# Protocol Evolution Workflow

**Created:** 2026-08-17T15:56:44.356790+00:00
**Authority:** INVENTION_PROTOCOL_V1 §14 (Protocol Evolution Workflow)

## The Workflow

A Protocol Change Proposal (PCP) moves through these states:

```
PROPOSED → AUDITED → PENDING_CE0_APPROVAL → APPROVED → MERGED
    ↓           ↓            ↓                  ↓         ↓
 (coder)   (auditor)     (CEO reviews)     (CEO says    (V1.N+1
            reviews       and decides       "approve")   constitution
            for bugs      to approve        in writing)  created)
```

**No state may be skipped. No self-approval. The coder who proposes a PCP cannot also approve it.**

## State Definitions

| State | Who | What happens |
|-------|-----|--------------|
| `PROPOSED` | Coder | Files PCP at `protocol/proposals/PCP-NNN_<name>.md` |
| `AUDITED` | Auditor (different agent) | Reviews PCP for bugs, contradictions, invariant violations |
| `PENDING_CE0_APPROVAL` | Auditor | Promotes PCP to CEO review queue |
| `APPROVED` | CEO | CEO explicitly says "approve PCP-NNN" in writing |
| `MERGED` | Coder | Creates V1.N+1 constitution; updates `CONSTITUTION_REGISTRY.json` |

## Current PCPs

| PCP | Status | Filed | Approved |
|-----|--------|-------|----------|
| PCP-001 | PROPOSED | 2026-08-17T15:56:44.356790+00:00 | (not yet) |

## Critical Rules

1. **The coder who files a PCP cannot approve it.** Approval requires CEO or a designated external auditor.
2. **Until APPROVED, the PCP is advisory only.** No invention may use proposed statuses as if they were constitutional.
3. **When APPROVED, a new constitution version is created** (V1.N+1). The old version is preserved (Law 7: historical permanence).
4. **Every invention must declare which protocol version it uses.** This is recorded in `00_MANIFEST.json: protocol_version`.
5. **The `CONSTITUTION_REGISTRY.json` is the single source of truth** for which version is current.

## PCP-001 Status

- **Current state:** PROPOSED
- **Filed by:** Main agent (Super Z)
- **Cannot be approved by:** Main agent (Super Z) — same agent filed it
- **Requires:** CEO approval or external auditor approval
- **Until approved:** `protocol_version = V1.0`; `BELOW_BUYER_THRESHOLD` is NOT a constitutional status
