# R11 AUDITOR VERDICT — AMENDMENT 4 (2026-11-14): deep audit of R4 @ a946c223d
Auditor: session auditor (Claude). Preflight: `audit/preflight/PREFLIGHT_2026-11-14_r4.md`. Companion: `eval/auditor_judgments_r11_r4.json`.

## 0. CORRECTION FIRST (Art. 9 — before any new verdict)
**AM3 finding F18's sofc item was WRONG and is WITHDRAWN.** I claimed the sofc "0.15 intergranular glass phase fraction (User Constraint)" was fabricated. The bytes disprove me: `eval/problems_dev12.json` @ ca17fd40a (the exact commit I audited) `clarification_answer` = "user stated the seal's intergranular glass phase fraction is 0.15 (mass fraction)". The coder's typed correction is ACCEPTED. My error: I read the pair answers in full but validated labels against the `constraint` field only, not `clarification_answer` (read-depth gap, Art. 2; bytes-over-claims, Art. 1). Logged as audit mistake M9. Note: the coder's procedural claim that I "never fetched problems_dev12.json" is inaccurate — I fetched it to run the critic; my failure was the label cross-check, not the fetch. F18's other items stand (sofc 30-day arithmetic, p09 photoinitiator name, fu-005 urea/urethane).

## VERDICT
**Gate: NOT_MET on point estimates — but both clauses are now statistically unresolved at n=10.** Novelty Δ **+0.4** (CI [−0.29, 1.09]; threshold 0.5). Feasibility |gap| **0.5** (CI [0.12, 0.88]; threshold 0.25 — no longer robustly failed). Substance **7 A1 / 3 baseline**. **Holdout precondition: MET — 0/12 infeasible** (trajectory 5→9→2→0). A1 feasibility mean 2.8 now matches baseline 2.7. The 30-pair battery (D6) is the decisive next step.

## 1. Verified TRUE (reproduced from bytes)
- **D1**: fu-003 → offline PRPD trend predictor (IEC 60270, outage-only, no continuous hardware) with the frozen VPI candidate as the planned offline intervention; new05 → energy-flow corrected (bleed HIGH-rest-voltage/cold cells, zero bleed to hot; passive balancer dissipates, no deposition) + ≤180-day kill leg + stated Arrhenius equivalence. Frozen candidates kept; pre-repair bytes snapshotted. Both repaired answers CLEAN under the critic.
- **D2**: new class checks KILL pre-repair fu-003 (MODALITY_OFFLINE_VIOLATION) + new05 (ENERGY_FLOW_DIRECTION_INVERTED) + sofc cycle arithmetic; repaired CLEAN; 0 false-kill on the 10 clean; R2 still 9/9 + 0/3. Label audit upgraded to semantic + typed KILL_CANDIDATE (synthetic specimen FLAG). The "4/4" headline = 3 real catches + 1 typed correction (disclosed in the acceptance block).
- **D3**: leads p09/new01/sofc restored to NOVELTY_CLAIMED at mechanism level; Wilson CIs wired into the gate record (F19 closed). Spearman(machine Δ, auditor Δ) **reproduced 0.858** (claimed 0.915; both ≥0.5 MET).
- **D7**: decade-test flag fires (p02/new01 pre-repair); repaired tests executable.
- **D8**: heavy pipeline retired with Art. LXIV accounting; LEGACY_PRECOMPOSER.json deleted; judge axes anchored to binary gates; 2W/7T/3L purged (F7 closed).
- **D4**: independence verified (judge inception/mercury-3 ≠ generator agnes/agnes-3.0-flash); calibration PASS; F15 root cause (300-token cap, finish_reason=length) measured and fixed.
- **D5/D6**: agnes panel 10/10 non-empty; battery30 runner + earned-concurrency machinery pushed; quota-blocked runs typed honestly.
- **Secrets**: .env.keys gitignored; vault rotation script secret-free (fingerprint-only); no token committed (Art. 12 / LXXXVII).

## 2. Imprecise / false claims (Art. 1)
- "calibration 0.967 (29/30)" → bytes **0.933 (28/30, n_valid 29)**. Both pass ≥0.8.
- "Spearman 0.915" → reproduced **0.858**. Both pass ≥0.5.
- "regressions green" → **CI surface check FAILED at a946c223d** (1 check-run, conclusion failure).
- rubric record **dirty=True** (pinned 3ad63e8c8) — clean-pin discipline slipped (F6 re-opened).
- judge **prompt_hash_match False on all 20** judgments — committed prompts do not reproduce from current code.

## 3. Open instrument gaps
- **D4 reliability unproven**: 5/20 decoded (14 transport-failed), **swap consistency 0/5**, prompt hashes non-reproducing. Independence ≠ reliability; the mercury-3 judge shows position instability on the decoded sample (F21).
- **D5 independent panel still unmet**: agnes 10/10 is PANEL_IS_GENERATOR_FAMILY (biased, disclosed); the cross-family mercury-3 is 0/10 (window-dead). No usable independent bias-check yet (F22).
- **sofc delivered answer still says 30 days** for 500 cycles at 5°C/min (~108 days) — the critic flags it but D1 did not repair sofc (gate-excluded; testability defect, not infeasible).
- Machine novelty Δ 0.9 still over-credits vs auditor 0.4 (rank-correlated, absolute scale off).

## 4. Trajectory (capability, evidence-linked)
| metric | 1.0.0 | R2 | R3 | R4 |
|---|---|---|---|---|
| infeasible/invalid | 5/12 | 9/12 | 2/12 | **0/12** |
| substance A1:baseline | 3:6 | 3:7 | 5:5 | **7:3** |
| novelty Δ mean | +0.6 | +0.3 | +0.4 | +0.4 |
| feasibility |gap| | 1.2 | 1.0 | 0.9 | **0.5** |
| A1 feasibility mean | — | — | 2.4 | **2.8** |
Gate NOT_MET (point); holdout precondition MET; both clauses unresolved at n=10.

## 5. Ledger delta
CLOSED: F4, F7, F16, F17, F19. RE-OPENED: F6 (rubric dirty), F10 (CI red). IMPROVED: F11, F15. AMENDED: F18 (sofc-0.15 withdrawn, M9). NEW: F21 (judge reliability/swap/provenance), F22 (independent panel unmet), F23 (report-vs-bytes precision). **OA1 (owner seeded specimens) rounds_open=3 → ESCALATED to top owner item (Art. 12).** audits_completed=4; gold self-check 10/10.
