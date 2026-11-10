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
