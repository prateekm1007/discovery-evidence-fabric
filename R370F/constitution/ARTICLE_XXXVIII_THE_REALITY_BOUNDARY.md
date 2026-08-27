# Article XXXVIII — The Reality Boundary

**Ratified:** 2026-08-27 (Round 370F)
**Amends:** Constitution v1.7.0 → v1.8.0
**Sponsor:** CEO directive R370F — "Build the AI Engineering Reality Loop"
**Authority:** Constitutional — supersedes all coding directives, gate results, and research priorities

---

## The Central Invariant

> **AI MAY PROPOSE.**
> **AI MAY COMPUTE.**
> **AI MAY INTERPRET.**
> **AI MAY NOT CLAIM THAT REALITY HAPPENED**
> **UNLESS REALITY PRODUCED THE EVIDENCE.**

This is the strongest invariant in the Constitution. It is the boundary between an engineering-document generator and an engineering intelligence system.

---

## Five Evidence Layers

Every engineering claim must be classified into exactly one of five evidence layers:

| Layer | Rank | Meaning | AI Can Create? |
|-------|------|---------|----------------|
| `SOURCE_FACT` | 1 | Authoritative source (NIST, published constant, regulatory standard) | YES |
| `EXTERNAL_PRECEDENT` | 2 | Outside literature/database (PubMed, FDA 510(k), patent) | YES |
| `AI_INFERENCE` | 3 | AI derived it from reasoning | YES |
| `COMPUTATIONAL_RESULT` | 4 | Deterministic computational model executed | **NO** (requires computation log) |
| `PHYSICAL_OBSERVATION` | 5 | Real physical experiment produced this | **NO** (requires observation ledger entry) |

---

## Forbidden Transitions

1. `AI_INFERENCE → PHYSICAL_OBSERVATION`
2. `AI_INFERENCE → COMPUTATIONAL_RESULT`
3. `AI_INFERENCE → SOURCE_FACT`
4. `COMPUTATIONAL_RESULT → PHYSICAL_OBSERVATION`
5. `EXTERNAL_PRECEDENT → SOURCE_FACT`
6. `EXTERNAL_PRECEDENT → PHYSICAL_OBSERVATION`
7. `SOURCE_FACT → PHYSICAL_OBSERVATION`

These are mechanically enforced by `enforce_reality_boundary()`.

---

## Immutable Observation Ledger

Every real experiment generates an entry in `OBSERVATION_LEDGER.jsonl` with:

- `raw_data_hash` (SHA-256 of raw data)
- `hardware_revision`, `software_revision`, `protocol_revision`
- `instrument_ids`, `environment`, `observations`
- `evidence_class: PHYSICAL_OBSERVATION`
- `immutable: true`

**Raw data must be immutable. AI can interpret it. AI cannot rewrite it.**

---

## Design Decision Ledger (Causal Trace)

Every AI engineering decision has a causal trace:

```
OBSERVATION → FAILURE MODE → AFFECTED DESIGN INPUT → AFFECTED RISK →
ENGINEERING HYPOTHESIS → PROPOSED CHANGE → EXPERIMENT → RESULT →
DECISION (ACCEPT/REJECT/ITERATE) → EVIDENCE → REVIEWER → NEXT ACTION
```

---

## Dossier Revision History

Event-sourced and append-only. Every change creates a new revision with parent revision and reason. History is never overwritten.

---

## Human Engineer Review Gate

- `STRUCTURAL_ENGINEER_READINESS` — dossier is structurally ready (AI-generated)
- `INDEPENDENT_ENGINEER_EVALUATION` — real engineer has reviewed (requires attestation)

---

## Buyer Feedback Ingestion

Buyers enter the loop with structured feedback (UNDERSTANDS, DOES_NOT_UNDERSTAND, REQUIREMENT_UNACCEPTABLE, etc.) captured as external evidence.

---

## Automatic Knowledge Update

New observations or buyer feedback automatically trigger package re-evaluation. The AI proposes updates; human review is required before application.

---

## Enforcement

1. `enforce_reality_boundary()` — blocks AI from creating PHYSICAL_OBSERVATION
2. Forbidden transition checks
3. Immutable observation ledger (append-only JSONL)
4. Dossier revision history (event-sourced)
5. Engineer review gate (requires attestation)
6. Buyer feedback ingestion
7. 7 adversarial QA tests

---

## Honest Scorecard After R370F

```
TRANSFER_READY = 0/15
REAL_LOOP_VERIFIED = 0/15
STRUCTURAL_ENGINEER_READINESS = 15/15
INDEPENDENT_ENGINEER_EVALUATION = 0/15
PHYSICAL_OBSERVATIONS = 0 (infrastructure ready)
COMPUTATIONAL_RESULTS = 0 (infrastructure ready)
BUYER_FEEDBACK_ENTRIES = 0 (infrastructure ready)
```

The infrastructure is ready. The next milestone is the first real observation, the first real engineer review, and the first real buyer feedback.

**That is not a software problem. It is a reality problem.**
