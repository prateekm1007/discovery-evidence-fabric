# Toscanini Audit Governance

This directory governs the independent AI auditor's behavior and the auditor↔coder operating loop.

## Files

- `AUDITOR_SELF_GOVERNANCE_v1.md` — mandatory principles for the auditor before, during, and after audits.
- `AUDITOR_BLINDSPOT_REGISTER.md` — empirically observed auditor failure modes and preventative checks.
- `AUDIT_LOOP_PROTOCOL_v1.md` — mutual auditor↔coder reminder and re-audit protocol.

## Mandatory ritual

Before every substantive audit, the auditor must read:

1. `EPISTEMIC_CONSTITUTION.md` (current version/hash as applicable to the audit),
2. `GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md`,
3. `GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md`,
4. the applicable portion of `GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md`.

The coder must remind the auditor to perform this read before the audit begins.

Before coding, the auditor must remind the coder to read the full Constitution.

Before the coder's final commit, the coder must read the full Constitution again; before issuing the acceptance verdict, the auditor must reread the applicable governance and blind-spot entries.

## Version authority

The Constitution has higher authority than this directory. This governance layer exists to improve the auditor's reliability, not to replace project-level epistemic rules.

## Living register rule

When an audit reveals a previously unrecognized auditor blind spot, the new blind spot must be recorded before the next substantive audit unless doing so would contaminate a sealed experiment. Sealed artifacts must never be rewritten retroactively to make governance changes appear contemporaneous.

## Core audit question

> **What could still be false even if everything reported so far is true?**

This question is mandatory at each release audit so that the process does not degrade into a ritualized checklist.
