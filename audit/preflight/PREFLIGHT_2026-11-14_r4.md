# AUDIT_PREFLIGHT — R4 — 2026-11-14
## 1. Read order (exact SHAs)
- [x] (1) Builder EPISTEMIC_CONSTITUTION.md @ a946c223d6537afeff70f0e653916ac66a934068 — sha256 947e7a63b5d7f63b... — 128787 bytes, v2.12.0 (Article LXXXVII Secrets Vault added at e6c0d4f0e; read).
- [x] (2) AUDITOR_CONSTITUTION.md v1.0.0 @ 75475f95b114786cbb402c21cf0e0ff0055b397a (canonical audit branch).
- [x] (3) AUDIT_LEDGER.json @ 75475f95b114786cbb402c21cf0e0ff0055b397a — 20 findings at start; last verdict V3 NOT_MET.
## 2. Open-finding re-check (first)
F1-F20 re-checked at a946c223d6537afeff70f0e653916ac66a934068: F4/F7/F16/F17/F19 CLOSED; F6/F10 RE-OPENED (rubric dirty=True; CI surface failure); F11/F15 improved; F18 AMENDED (M9 correction). New F21-F23.
## 3. Corrections before this audit (Art. 9)
**M9 ISSUED FIRST**: AM3 F18 sofc-0.15 'fabricated' withdrawn — clarification_answer @ca17fd40a proves user-stated. Verified against bytes before any new verdict. Coder's substantive correction accepted; coder's 'auditor never fetched problems_dev12.json' claim inaccurate (fetched for critic run; label cross-check was the gap).
## 4. Scope + read depth
Audited a946c223d6537afeff70f0e653916ac66a934068; base ca17fd40a (R3). FULL reads: 2 repaired answers (fu-003,new05) + pre-repair snapshots; verified other 10 r11_a1_r3 answers byte-unchanged (only 3ad63e8c8 modified answers). Reproduced: critic regression report, Spearman (0.858), Wilson CIs, judge calibration (0.933), panel counts, retirement record, CI check-runs, secrets grep.
## 5. Commands run (PAT redacted — Art. 12)
    GET /repos/.../git/ref/heads/queue/dev12_r7 -> a946c223d6537afeff70f0e653916ac66a934068
    GET /repos/.../contents/EPISTEMIC_CONSTITUTION.md?ref=a946c223d (hashed; LXXXVII read)
    GET /repos/.../contents/eval/problems_dev12.json?ref=ca17fd40a AND ?ref=a946c223d (correction check: clarification_answer)
    GET /repos/.../commits/{3ad63e8c8,f7dcd8086,7876adbf4,ad7301c49,a946c223d} (file lists)
    GET /repos/.../contents/eval/pairs/r11_a1_r3/{fu-003,new05}.json + critic_regression_r3_report.json
    GET /repos/.../contents/eval/{invention_rubric,novelty_search,judge_independent_rerun_r11_r4,crossfamily_panel,pipeline_retirement,r4_status}...json
    GET /repos/.../commits/a946c223d6537afeff70f0e653916ac66a934068/check-runs -> 1 ('surface', failure)
    GET /repos/.../contents/.gitignore + scripts/r11_vault_pat_rotate.py (secret grep 0)
    PUT /repos/.../contents/<AM4 + r4 judgments + ledger + preflight>  # branch=audit/r11-auditor-verdict-20261114
    # Authorization: token $PAT (env/header only)
## 6. Independence disclosure (Art. 4)
Auditor: Claude session; prior full pair reads disclosed. Cross-family panel: agnes 10/10 but generator-family (biased, disclosed); mercury-3 0/10 dead — independent bias-check still unmet (F22).
## 7. Instrument checklist (Art. 3)
novelty: rank-correlated (Spearman 0.858) but absolute over-credit (machine 0.9 vs auditor 0.4) -> INPUT. feasibility: machine 0.6 vs auditor 0.5. judge: independence verified, reliability unproven (5/20 decoded, swap 0/5, prompt_hash False x20). clean tree: NO (rubric dirty=True). CIs: Wilson wired (win-rate); gate delta CIs auditor-computed. CI surface: FAILURE.
## 8. Gold-set self-check
10/10 consistent (hash 7541e264... unchanged); R4 repairs fixed G06 + new05 energy-flow; recorded in ledger.
