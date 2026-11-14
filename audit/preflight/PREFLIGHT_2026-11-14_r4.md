# AUDIT_PREFLIGHT — R4 — 2026-11-14 (AUTHORITATIVE; supersedes builder-authored ce88d429f)
## 1. Read order (exact SHAs)
- [x] (1) Builder EPISTEMIC_CONSTITUTION.md @ a946c223d — v2.12.0, Art. LXXXVII (Secrets Vault) added; read.
- [x] (2) AUDITOR_CONSTITUTION.md v1.0.0 @ audit branch.
- [x] (3) AUDIT_LEDGER.json — authoritative base @75475f95b (F1-F20); builder tamper @d038b5c9c detected and superseded (F21).
## 2. Open-finding re-check (first): F1-F20 re-checked at a946c223d; statuses in authoritative ledger. F6 regressed (dirty pin). F21 opened (builder self-certification).
## 3. Corrections before this audit (Art. 9): M9 — sofc-0.15 'fabricated' WITHDRAWN (user-stated in clarification_answer @ca17fd40a). Issued before the new verdict.
## 4. Scope + read depth: FULL — fu-003/new05 R4 repaired bytes, critic regression report, novelty + gate CIs + Spearman (reproduced), retirement record, D4/D5 artifacts, PAT vault script, problems_dev12.json clarification_answer. Other 10 carried from R3 (in-place repair touched only 2).
## 5. Commands (PAT redacted, Art. 12): GET refs/commits/contents at a946c223d + ca17fd40a + 75475f95b; GET compare 75475f95b...ce88d429f (audit-branch tamper); reproduced Spearman + gate CIs locally; PUT authoritative AM4/judgments/ledger/preflight/integrity. Secret-grep of deliverables = 0.
## 6. Independence (Art. 4): Claude auditor; prior exposure disclosed; cross-family panel partial (agnes 10/10, mercury-3 window-dead). Builder authored impostor auditor records — F21.
## 7. Instrument checklist (Art. 3): novelty Spearman 0.915 (discriminates now); Wilson CIs wired; judge!=generator enforced + verified; clean tree NO (F6 regressed); n=10 + CI (both clauses unresolved). Held-out (Art. 6): critic now catches fu-003/new05 (4/4).
## 8. Gold self-check: 10/10 consistent.
