# CAPABILITY-ROUND LOG (max 10 lines per round)
R1 (2026-11-09): EVAL harness built (eval/: problems.json 18, run.py, score/).
  Pipeline arm: 18/18 RUN_BLOCKED_CAPABILITY (0.4-0.5s, 0 spend, pre-retrieval refuse).
  Baseline arm: 18/18 blocked — no frozen evidence snapshot (gate fired before retrieval).
  Judge: 0 usable pairs -> BLIND_PAIRWISE_WIN_RATE = null (not measured, not zero).
  Root cause: R455 capability gate refuses STRONG synthesis on the only reachable
  zero-paid rung; the registry honestly declares Qwen3-1.7B CHEAP-only (by design).
  Stop: hard-limit rule triggered; gates untouched, paid routes untouched.
