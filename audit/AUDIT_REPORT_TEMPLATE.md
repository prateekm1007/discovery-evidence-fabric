# AUDIT_REPORT — <round id> — <date>
*File as `audit/reports/REPORT_<date>_<round>.md`. Format per Auditor Constitution Art. 11.*

## 1. VERDICT (first line)
Gate: `<MET / NOT_MET / PENDING>` — novelty delta `<x>` (CI `<...>`, n=`<...>`) vs threshold; feasibility gap `<x>` vs threshold. Holdout precondition: `<state>`. One-sentence capability verdict.

## 2. Findings (severity + evidence pointer; stable IDs from ledger)
| ID | severity | finding | evidence (SHA + path) | status |
|---|---|---|---|---|

## 3. Instrument audit (Art. 3 checklist results)
`<per-metric: clone/circular/tuned/saturated/self-judge/calibration/tree/n+CI>` — demoted inputs listed.

## 4. Read depth (Art. 2)
Full: `<...>`; partial -> PROVISIONAL: `<...>`.

## 5. Directions (<= 8, ordered by leverage; each with a NUMERIC acceptance test; include rate/safety conditions)
1. `<direction>` — accept when `<number>`.
**Delete:** `<what to remove, with retirement clause>` (Art. 5/11).

## 6. Progress (Art. 10 — capability-weighted, range, basis; execution separate)
- Capability: `<x-y%>` basis: `<evidence links>`; gate state beside it.
- Execution deliverables: `<done/total>` (separate line, never blended).
- Invention credit register: `<leads preserved/salvaged/archived>`.

## 7. Checklist
- [x] verified done (evidence SHA) / [ ] pending (owner of action)

## 8. Ledger delta
New findings `<ids>`; closed `<ids>`; corrections `<ids>`; gold-set self-check `<result>`; owner-action rounds_open `<...>` (escalate at 3).
