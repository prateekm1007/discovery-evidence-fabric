# Protocol Directory

This directory contains the immutable constitution and enforcement layer for the discovery-evidence-fabric program.

## Files

| File | Purpose |
|---|---|
| `../INVENTION_PROTOCOL_V1.md` | The constitution. Frozen as of 2026-08-17. Applies to inventions #1-#150. |
| `PROTOCOL_EVOLUTION_WORKFLOW.md` | The only permitted mechanism for changing the constitution. |
| `CHANGELOG.md` | Audit trail of all protocol version changes. |
| `preflight_check.py` | Mechanical CI enforcement. Runs against every invention directory. Exit 0 = pass; exit 1 = fail. |
| `preflight_report.json` | Last preflight run's machine-readable report. |
| `templates/` | Canonical artifact templates that every invention must instantiate. |

## Templates

| Template | Purpose |
|---|---|
| `templates/00_MANIFEST.json` | Artifact index + hashes for an invention package. |
| `templates/08_LIMITATION_FREEZE.json` | Immutable record of L1..Ln and arrangement. |
| `templates/11_102_RESULTS.json` | Single-reference novelty attack schema. |
| `templates/12_103_RESULTS.json` | Combination + motivation attack schema. |
| `templates/14_DESIGN_AROUND_results.json` | Design-around alternatives schema. |
| `templates/16_SIMULATION_results.json` | Domain-specific simulation slot. |
| `templates/21_EVIDENCE_LEDGER.json` | Provenance chain for every conclusion. |
| `templates/22_FINAL_ADJUDICATION.json` | Final verdict with gate scores + evidence pointers. |
| `templates/23_LESSONS_LEARNED.json` | Immutable learning record per invention. |

## How to Use

### Adjudicating a new invention under V1

1. Create `INVENTION_XXX/` directory under repository root.
2. Walk the 18-stage pipeline (Section 4 of V1).
3. Instantiate each template in the order dictated by the stage number.
4. At each gate, populate `21_EVIDENCE_LEDGER.json` with the supporting evidence_ids.
5. Run `python3 protocol/preflight_check.py` to verify mechanical compliance.
6. If preflight passes, write `22_FINAL_ADJUDICATION.json` with the verdict.
7. After run completes, write `23_LESSONS_LEARNED.json` with what worked / failed / proposed protocol changes.
8. Do NOT invent #N+1 until #N's package passes preflight AND lessons are recorded.

### Proposing a protocol change

1. Identify a structural deficiency in `23_LESSONS_LEARNED.json` of a completed invention.
2. File `protocol/proposals/PCP-<NNN>_<short_slug>.md` per the workflow.
3. Await independent audit.
4. If approved, create V<N+1> per Section 5 of the workflow.
5. Update this README to indicate the new current version.

## Current Protocol Version

**V1** — Frozen 2026-08-17

Inventions under V1: #1 (CereVasc #1 V2, first to pass mechanical preflight).
