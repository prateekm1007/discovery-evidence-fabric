# Audit Loop Protocol v1 — Auditor ↔ Coder

## Purpose

Create a repeatable control loop between the external AI auditor and the project coder so that neither party relies on memory, stale handoffs, or the other party's confidence. The objective is continual improvement of the discovery and invention machine while preserving the Constitution, experimental integrity, provenance, and product mission.

## Authority order

1. `EPISTEMIC_CONSTITUTION.md` — project-level epistemic authority.
2. `GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md` — auditor behavior.
3. `GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md` — known auditor failure modes.
4. This protocol — operational coordination between auditor and coder.
5. Task-specific directives, worklogs, screenshots, reports, and handoffs.

If two artifacts conflict, use the higher authority and explicitly report the conflict.

## Mutual reminder contract

Before a coding session:

- **Coder reminds Auditor:** read the current auditor governance files before the audit.
- **Auditor reminds Coder:** read the current Constitution in full before coding.

Before a final coder commit:

- **Coder rereads the Constitution in full.**
- **Auditor rereads the applicable governance and blind-spot entries before issuing an acceptance assessment.**

Neither reminder counts as proof that the other party complied. Compliance should be stated and, where practical, recorded in the worklog.

## Phase 0 — Common starting state

The auditor and coder must establish the same baseline:

- engine repository and exact commit;
- buyer/technology-transfer repository and exact commit;
- deployed service URL and deployment identity;
- current Constitution version and hash;
- current auditor governance versions and hashes;
- current active branches and pull requests;
- known unresolved standing notes;
- current product acceptance target.

Do not rely on a stale handoff to establish these facts.

## Phase 1 — Auditor preparation

The auditor reads:

1. `EPISTEMIC_CONSTITUTION.md` or confirms the coder has done so for implementation work;
2. `AUDITOR_SELF_GOVERNANCE_v1.md`;
3. `AUDITOR_BLINDSPOT_REGISTER.md`;
4. the most recent relevant worklog/directive;
5. the current deployed UI/API where applicable.

The auditor states the claims to be tested and identifies at least one plausible falsifier for each major claim.

## Phase 2 — Coder preparation

The coder reads the full Constitution before making code changes.

The coder identifies:

- current repository state;
- exact files/components to change;
- preservation obligations for sealed artifacts;
- tests expected to cover the change;
- production acceptance path;
- deployment/release requirements.

## Phase 3 — Independent audit first

The auditor audits current state before prescribing implementation.

Required observation channels when relevant:

- repository;
- deployed website;
- direct API;
- generated artifacts;
- logs/telemetry;
- browser interaction;
- buyer package;
- provenance records.

The auditor must distinguish observed facts from coder claims.

## Phase 4 — Coder response

The coder receives:

- observed defects;
- severity;
- exact reproduction;
- required product contract;
- acceptance criteria;
- preservation constraints.

The coder must not merely patch the visible symptom if the audit identifies an upstream cause.

## Phase 5 — Implementation

The coder implements the smallest coherent change that closes the defect while preserving the Constitution and frozen history.

Before adding substantial new infrastructure, the coder should state:

- what bottleneck it removes;
- what metric should improve;
- why current infrastructure cannot solve it;
- how removal/retirement would work if it fails to earn its complexity.

## Phase 6 — Evidence loop

After implementation:

1. focused unit/regression tests;
2. integration test;
3. full curated regression;
4. fresh production-path acceptance where relevant;
5. artifact inspection;
6. deployment identity verification;
7. re-audit.

A passing unit test without a production-path test does not close a product defect.

## Phase 7 — Blind-spot update

If the audit discovered a new auditor blind spot:

- add it to `AUDITOR_BLINDSPOT_REGISTER.md`;
- state why existing governance missed it;
- identify the preventative check;
- increment the register version;
- reread the updated register before the next substantive audit.

If the blind spot arose from a sealed experiment, do not alter the sealed artifact retroactively. Record the lesson in a new artifact.

## Phase 8 — Mutual challenge

The auditor must challenge the coder's strongest completion claim.

The coder must challenge the auditor's strongest negative claim when there is evidence that the auditor's observation channel was incomplete.

Examples:

- "Bridge exists" → auditor asks "is it on the fresh production path?"
- "No 3D" → coder asks "did the auditor inspect the geometry bridge or only the UI?"
- "Provider unavailable" → auditor asks "was alternate provider routing exercised?"
- "No evidence" → coder asks "were sources actually reachable?"

Neither side wins by rhetoric; the decisive test is a reproducible observation.

## Phase 9 — Product standard

The end-to-end acceptance target is not merely technical cleanliness.

A world-class Toscanini release should let a real user:

1. enter a difficult problem;
2. trigger a genuine discovery run;
3. receive an invention attempt;
4. see the architecture explained clearly;
5. inspect a suitable 3D representation when the invention is representable;
6. understand evidence, uncertainty and challenge history;
7. see frontier capability transfer and causal change where applicable;
8. determine what experiment should happen next;
9. obtain a coherent buyer-facing technology package;
10. separately obtain technical material for IP counsel.

Toscanini is not a patent court. Legal patentability and FTO remain downstream legal work.

## Phase 10 — Release gate

A release is complete only when:

- Constitution read before coding and before final commit;
- auditor governance read before audit;
- known blind spots checked;
- repository state verified;
- deployment identity verified;
- no frozen artifact modified improperly;
- relevant tests pass;
- fresh user path exercised;
- UI truth matches backend truth;
- generated artifacts are real and retrievable;
- package and website derive from canonical invention state;
- unresolved limitations are explicitly stated;
- no self-reported "world-class" claim is accepted without independent evidence.

## Standing loop

```text
AUDITOR GOVERNANCE READ
        ↓
AUDIT CURRENT STATE
        ↓
IDENTIFY DEFECT / BOTTLENECK
        ↓
CODER READS CONSTITUTION
        ↓
IMPLEMENT
        ↓
TEST
        ↓
FRESH E2E PROOF
        ↓
AUDITOR RE-AUDIT
        ↓
NEW BLIND SPOT?
   ┌────┴────┐
  YES        NO
   ↓          ↓
UPDATE      RELEASE
REGISTER     GATE
   ↓
REREAD
   ↓
NEXT LOOP
```

## Anti-drift rule

Do not allow the audit process itself to become a checklist ritual. Each round must ask a fresh question: **what could still be false even if everything reported so far is true?**

That question is mandatory whenever a release is called complete.