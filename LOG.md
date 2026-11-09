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
