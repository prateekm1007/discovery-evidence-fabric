# CAPABILITY-ROUND LOG (max 10 lines per round, no new round dirs)
R1 (2026-11-09): EVAL harness built (eval/: problems.json 18, run.py, score/).
  Run C1 (chrome subject): pipeline 18/18 RUN_BLOCKED_CAPABILITY (gate: CHEAP-only
  zero-paid rung); win-rate null — hard-limit STOP, gate preserved.
  Run C2 (with operator keys): pipeline 18/18 MECHANISM_GENERATION_FAILED
  (real retrieval 12-21 items/probe; synthesizer's ladder refused every
  rung: apinex AUTH_FAILURE suspended, unorouter busy/invalid, bai 0 balance,
  xkiro/bynara model-404, tokenrouter invalid, atria 503). Baseline arm:
  18/18 ok on localqwen (strongest rung the engine admits right now).
  BLIND PAIRWISE WIN-RATE = 0.0 (n=18, CI ±0.23); criterion diffs A -3.03
  B -3.83 C -3.61 D -3.50 (judge shares the baseline's route model; disclosed).
  Root cause: no zero-paid STRONG rung currently ADMITS generation; pipeline
  answers were honest transport-refusal notices, so the judge scored the
  baseline's answers higher on every criterion. Next blocker: a live rung.

R1 (2026-11-10): DEV6 measurement committed. Funnel 3/6 completed, 3/6 mechanisms_found, 3/6 distinct (starved: predictors, GENERATION_NO_OPERATOR_CONTRACT). Speed p50 295.2 s, p95 300.1 s, 3 timeouts (budget breached). Calibration 20/20 passed. Root cause: multi-operator generation 3x LLM calls inflated MECHANISM_SPACE to 70 s; EF channel bounded to 20 s. Actions: EF default off, OWNER_INCEPTION_ACCOUNT vocab, cemetery membrane regression test, routing-pin + cost-policy pins updated. Next: KPI sweep MAX_OP_CALLS {3,6,9}, stated-variable propagation, prune.

R1 (2026-11-10): DEV6 win-rate 0.1 (0-4-1, n=5, CI +-0.44); funnel 6/6 found+6/6 distinct; p09 TIMEOUT; judge 20/20; gauntlet specificity 0.80 on 10 clean controls (n=20 needs a second sealed cohort); attackers kill unsupported_mechanism (4/6); mutated_survivors=0 because IMPROVE stage was removed from lean STAGE_ORDER (R515); scripts cut to 48; collection 5106/0 errs; prev. R412 attacker NOT_CALIBRATED (FPR 0.8-1.0) stands.

R2 (2026-11-10): packet-aware judge (evidence in prompt + fabrication check); 30 calibration pairs (29/30 pass); raw pairs committed eval/pairs/. Critique-revise: attack_survivors 2/6 -> 3/6; mutated_survivors 0 -> 1 (p02); 3 killed candidates withheld from judge (refusal, never a fake invention). Win-rate 0.167 (0-2-1, n=3, CI +-0.73). Funnel-before corrected: committed YIELD_FUNNEL.json shows 25 mechanisms/22 distinct, not 23/23. Fire R452/R401-WC2/R458 + scripts/archive to tag (tracked 713.7 -> 355.0 MB); collection 0 errs. ATTACK 17->54 s = 3-worker provider contention (not code).

R5 (2026-11-11): P0 fixes pushed a7c77edb+f05fd9aa: fresh-run harness (typed INCOMPLETE_INFRASTRUCTURE on stale-dir unestablishable; stale outputs never scored; deterministic fail-closed test); score math corrected (baseline_wins from full_scoreable only; Wilson -> normal-approx CI on per-problem {0,0.5,1}; NOT_MEASURED CI when judge invalid; DEV6->DEV7 rename); judge calibration corpus SHA256 bound; answer contract strengthened (INDICATOR/THRESHOLD/VALIDATION markers; THRESHOLD number traceable; EVIDENCE-BACKED must bind to packet source id). Sealed holdout NOT run; auditor clearance still pending.
