# Protocol Evolution Workflow

> **The only permitted mechanism for changing `INVENTION_PROTOCOL_V1.md`.**
>
> Per Section 14 of `INVENTION_PROTOCOL_V1.md`.
>
> This document is the operating procedure. It is itself a frozen artifact.
> Changes to this document require the same Protocol Evolution Workflow applied recursively (a Protocol Evolution Workflow to change the Protocol Evolution Workflow).

---

## 1. When Evolution Is Permitted

### 1.1 Permitted Triggers

A protocol change is permitted ONLY when:

1. A `23_LESSONS_LEARNED.json` from a completed invention identifies a protocol-level deficiency (not a coding bug).
2. The deficiency is reproducible (a second invention would hit the same issue).
3. The deficiency is structural (a missing rule, an ambiguous definition, an unenforced invariant) — not aesthetic.

### 1.2 Forbidden Triggers

A protocol change is **forbidden** if:

1. The change would weaken any non-compensable gate (Patent ≥70 / Evidence ≥70).
2. The change would weaken the 102 single-reference rule.
3. The change would weaken the 103 motivation/expectation requirement.
4. The change would weaken the provenance chain requirement.
5. The change would weaken the limitation freeze immutability.
6. The change would weaken the "no silent promotion" rule.
7. The change would weaken the mandatory artifact list.
8. The change would weaken the Protocol Evolution Workflow itself.

These are the **constitutional invariants** (Section 14.4 of V1). They cannot be weakened by V2, V3, or any future version. They can only be strengthened.

### 1.3 Cannot Edit During A Run

A protocol change cannot be applied to a run in progress. If invention #N is mid-run and a lesson is learned, the lesson is recorded in #N's `23_LESSONS_LEARNED.json`, but the protocol does not change until #N completes. #N+1 onward runs under the new version.

---

## 2. The Workflow

```text
Step 1 — LESSONS_LEARNED
   An invention completes and produces 23_LESSONS_LEARNED.json
   with a protocol_changes_proposed entry.
        ↓
Step 2 — PROTOCOL_CHANGE_PROPOSAL
   A PROTOCOL_CHANGE_PROPOSAL.md is filed in protocol/proposals/
   with: proposed change diff, motivating lessons, expected impact.
        ↓
Step 3 — AUDIT
   An independent reviewer audits the proposal against:
     - Justification evidence
     - Constitutional invariants (Section 1.2 above)
     - Retroactivity (forbidden)
     - Loophole check (silent promotion risk)
        ↓
Step 4 — DECISION
   APPROVED → proceed to Step 5
   REJECTED → proposal archived; original lesson remains in 23_LESSONS_LEARNED.json
   DEFERRED → proposal held pending additional evidence from future inventions
        ↓
Step 5 — SUPERSESSION
   INVENTION_PROTOCOL_V<N+1>.md is created.
   INVENTION_PROTOCOL_V<N>.md is preserved (not deleted).
   README at repository root is updated to indicate current version.
        ↓
Step 6 — ANNOUNCEMENT
   Inventions #N+1 onward run under V<N+1>.
   Inventions #1..#N are NOT re-adjudicated.
```

---

## 3. Proposal Format

File: `protocol/proposals/PCP-<NNN>_<short_slug>.md`

```markdown
# PCP-<NNN>: <short title>

## Proposal Status
- [ ] Filed
- [ ] Audited
- [ ] Approved / Rejected / Deferred
- [ ] Supersession completed

## Proposing Invention
- Invention ID: <COMPANY>_INVENTION_<NNN>_V<M>
- Lesson Evidence ID: <evidence_id from 23_LESSONS_LEARNED.json>

## The Problem
<2-3 paragraphs describing the structural deficiency identified>

## The Proposed Change
<diff against current INVENTION_PROTOCOL_V<N>.md>
<exact section numbers and old/new text>

## Motivating Lessons
- <evidence_id list from one or more 23_LESSONS_LEARNED.json files>
- For each, quote the specific entry that motivates this change

## Expected Impact
- Which sections of the protocol are affected?
- Would existing inventions (already adjudicated) re-pass under the new version? (Note: existing inventions are NOT re-adjudicated, but the question is whether the new rule would have changed their verdict.)
- Does the change affect any constitutional invariant? (If yes, proposal is INVALID.)

## Constitutional Invariant Check
- [ ] Does not weaken non-compensable Patent/Evidence gates
- [ ] Does not weaken 102 single-reference rule
- [ ] Does not weaken 103 motivation/expectation requirement
- [ ] Does not weaken provenance chain requirement
- [ ] Does not weaken limitation freeze immutability
- [ ] Does not weaken mandatory artifact list
- [ ] Does not weaken "no silent promotion" rule
- [ ] Does not weaken the Protocol Evolution Workflow itself

## Audit Notes
<completed by independent reviewer>
- Reviewer: <name>
- Date: <ISO-8601>
- Verdict: APPROVED | REJECTED | DEFERRED
- Rationale: <required if REJECTED or DEFERRED>
```

---

## 4. Audit Criteria

The independent reviewer must verify:

### 4.1 Justification
- Is the change justified by reproducible evidence from completed inventions?
- Is the change structural, not aesthetic?
- Does the change address a real failure mode, not a hypothetical one?

### 4.2 Constitutional Invariant Preservation
- Does the change preserve all 8 constitutional invariants (Section 1.2 above)?
- If any invariant is weakened, the proposal is REJECTED.

### 4.3 No Retroactivity
- Existing inventions are NOT re-adjudicated under V<N+1>.
- The change applies only to inventions #N+1 onward.
- If the proposal seeks retroactive re-adjudication, it is REJECTED.

### 4.4 Loophole Check
- Does the change introduce a way to silently promote an invention to BUYER_READY?
- Does the change introduce a way to bypass the 102 single-reference rule?
- Does the change introduce a way to skip the 103 motivation requirement?
- Does the change weaken provenance traceability?
- If any loophole is found, the proposal is REJECTED.

### 4.5 Reviewer Independence
- The reviewer MUST NOT be the same agent that filed the proposal.
- If the only available agent is the proposer, the proposal is DEFERRED until an independent reviewer is available.

---

## 5. Supersession Procedure

### 5.1 Create V<N+1>

1. Copy `INVENTION_PROTOCOL_V<N>.md` to `INVENTION_PROTOCOL_V<N+1>.md`.
2. Apply the approved change diff to V<N+1>.
3. Update the V<N+1> header:
   - `Version: V<N+1>`
   - `Supersedes: V<N>`
   - `Status: FROZEN as of <date>`
4. Preserve V<N> unchanged.

### 5.2 Update README

The repository root `README.md` is updated to indicate:
- Current protocol version: V<N+1>
- Inventions running under this version: #N+1 onward
- Inventions running under previous versions: #1 through #N

### 5.3 Update Preflight Script

If the change requires new CI checks (e.g., a new mandatory field is added to a template), `protocol/preflight_check.py` is updated to enforce the new rule. The preflight script itself is versioned and the V<N+1> preflight is the only one that runs against V<N+1> inventions.

### 5.4 Announcement

A `protocol/CHANGELOG.md` entry is added:
```
## V<N+1> — <date>
- Proposal: PCP-<NNN>
- Change: <one-sentence summary>
- Effective: Invention #N+1 onward
- Constitutional invariants preserved
```

---

## 6. What This Workflow Does NOT Permit

### 6.1 Emergency Bypass
There is no "emergency" path to bypass the protocol. If a rule is wrong, the run completes under the wrong rule, the lesson is recorded, and the next run uses the fixed rule.

### 6.2 Selective Application
The protocol applies uniformly to all inventions in its scope. There is no "this invention is special" exemption.

### 6.3 Silent Re-Adjudication
Existing inventions cannot be silently re-adjudicated under V<N+1>. If a re-adjudication is genuinely needed (e.g., a V1 rule was incorrectly applied to invention #5, producing a wrong verdict), a public RETROACTIVE_REAUDIT proposal is filed, audited, and the re-audit is documented as a separate artifact (not a silent overwrite).

### 6.4 Constitution Suspension
The constitution cannot be "suspended" for any reason. If the constitution is broken, fix it via this workflow; do not bypass it.

---

## 7. Closing

This workflow exists because every previous failure mode in the program was a bypass of process, not a failure of intelligence. PatSnap exhaustion was a process failure (no fallback specified). 102/103 mis-classification was a process failure (no single-reference check). Silent promotion was a process failure (no hard gate check). Hallucinated assertions were a process failure (no primary-source evidence requirement).

The fix is not better prompts. The fix is a constitution that cannot be bypassed.

— END OF PROTOCOL EVOLUTION WORKFLOW —
