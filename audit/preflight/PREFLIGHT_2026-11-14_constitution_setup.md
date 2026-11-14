# AUDIT_PREFLIGHT — constitution-setup — 2026-11-14
Session: new auditor setup (owner directive). INFRASTRUCTURE task, not a result audit; no new verdict issued. Prior verdicts V1/V2 stand (ledger).

## 1. Read order (exact SHAs)
- [x] (1) Builder `EPISTEMIC_CONSTITUTION.md` @ 5569ecba86fb536365eefc63ec994209e5815451 — sha256 b235c6cbb6b5ef6cd218457fe3983be8958727cea7ac459be800dbda9db89e75 — 85 articles, 127,701 bytes; amendment chain through v2.11.0 (Art. LXXXVI Invention Gate).
- [x] (2) `AUDITOR_CONSTITUTION.md` v1.0.0 — created this session (self-read; 12 articles, 850 words, <= 2 pages).
- [x] (3) `AUDIT_LEDGER.json` v1.0.0 — seeded this session from the authoritative audit record; 14 findings, 2 amendments, 2 verdicts, 8 audit-mistake mappings.

## 2. Open-finding re-check
F1-F14 last re-checked at 5569ecba86fb536365eefc63ec994209e5815451 during Amendment 2 (same day): F1/F2/F4/F5/F6/F8/F9/F10 OPEN (F4 WORSENED), F7 OPEN-MITIGATED (frozen), F3 CLOSED-RETIRED (successor F11), F11-F14 OPEN. No status change since; carried into the seeded ledger.

## 3. Corrections issued before this task (Art. 9)
Already on record: 8W/2T/0L -> 4W/6T/0L (M1); 2W/7T/3L superseded by full-read 3W/6L/1T (M2); 54% -> ~48% OWNER_ASSESSED (M3); ~90% withdrawn (M4). No new corrections this session.

## 4. Scope + read depth
Setup deliverables only. Source material for the ledger/gold set was read IN FULL in the prior audits (all 12 R11 1.0.0 pairs, all 12 R2 answers, driver/rubric/critic/guard code, calibration + ablation + novelty artifacts). Gold-set labels derive from those full reads.

## 5. Commands run (PAT redacted — never committed, Art. 12)
    GET /repos/prateekm1007/discovery-evidence-fabric/git/ref/heads/queue/dev12_r7                 -> 5569ecba86fb536365eefc63ec994209e5815451
    GET /repos/prateekm1007/discovery-evidence-fabric/git/ref/heads/audit/r11-auditor-verdict-20261114 -> 1d68be9ec224f64c39742a7d5e418d0287b96ef6
    GET /repos/prateekm1007/discovery-evidence-fabric/commits/eff419506                            -> eff41950660ce8eae35cf75cf943c79cbbbbc1df
    GET /repos/prateekm1007/discovery-evidence-fabric/commits?sha=audit/r11-auditor-verdict-20261114&per_page=10
    GET /repos/prateekm1007/discovery-evidence-fabric/contents/EPISTEMIC_CONSTITUTION.md?ref=5569ecba8  (Accept: raw; hashed)
    PUT /repos/prateekm1007/discovery-evidence-fabric/contents/<deliverable>   # branch=audit/r11-auditor-verdict-20261114
    # Authorization: token $PAT  (env/header only)

## 6. Independence disclosure (Art. 4)
Auditor: Claude session. Prior exposure: coder arm summaries + full pair reads (disclosed in V1/V2 records). Cross-family panel: PENDING (directive issued; not yet run). Shared-family blind-spot caveat active (AM1 A5).

## 7. Instrument checklist
Not applicable to this infrastructure task; checklist embedded in the report template for every future result audit. Gold set pre-registered: sha256 7541e2649548c865ede13529401ea7b7c3303e1b509ed725ddbca178da139a80 (canonical JSON), 10 specimens (4 good / 6 bad), owner custody, burn-on-exposure rule.

## 8. Deliverables pushed this session
AUDITOR_CONSTITUTION.md; AUDIT_LEDGER.json; audit/AUDIT_PREFLIGHT_TEMPLATE.md; audit/AUDIT_REPORT_TEMPLATE.md; audit/gold_set/AUDITOR_GOLD_SET_v1.json; this preflight. Push SHAs are in the branch history (ledger references the pre-setup tip 1d68be9ec224f64c39742a7d5e418d0287b96ef6).
