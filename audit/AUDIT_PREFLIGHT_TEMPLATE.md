# AUDIT_PREFLIGHT — <round id> — <date>
*One page. File as `audit/preflight/PREFLIGHT_<date>_<round>.md` BEFORE any verdict. No preflight, no verdict (Auditor Constitution, read-order rule).*

## 1. Read order (check + exact SHA)
- [ ] (1) Builder `EPISTEMIC_CONSTITUTION.md` @ `<sha>` — sha256: `<hash>` — articles/version: `<...>`
- [ ] (2) `AUDITOR_CONSTITUTION.md` @ `<sha>` — version: `<...>`
- [ ] (3) `AUDIT_LEDGER.json` @ `<sha>` — open findings: `<ids>` — last verdict: `<id/state>`

## 2. Open-finding re-check (Art. 8 — FIRST, before new work)
| finding | last checked SHA | re-checked at SHA | status now |
|---|---|---|---|
| F# | ... | ... | OPEN / CLOSED / WORSENED |

## 3. Corrections issued before this audit (Art. 9)
- `<wrong figure/verdict>` -> `<correction>` (ledger entry `<id>`) — or NONE.

## 4. Scope + read depth plan (Art. 2)
- Audited branch/SHA: `<...>`; diff base: `<...>`
- Will read IN FULL: `<pairs/artifacts>`; PARTIAL (provisional only): `<...>`

## 5. Commands run (secrets redacted — Art. 12)
    GET /repos/<owner>/<repo>/git/ref/heads/<branch>          # tip SHA
    GET /repos/<owner>/<repo>/contents/<path>?ref=<sha>       # bytes (Accept: raw)
    # Authorization: token $PAT  (env only; NEVER committed)

## 6. Independence disclosure (Art. 4)
- Auditor model family: `<...>`; prior exposure to arm summaries: `<yes/no>`; cross-family panel: `<planned/done/not-needed>`

## 7. Instrument checklist (Art. 3 — complete before result audit)
clone-passable? / circular? / tuned-to-order? / saturated? / judge=generator (provider AND model)? / close-pair calibration? / clean tree? / n + 95% CI?
