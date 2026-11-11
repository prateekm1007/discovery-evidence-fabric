# R6 RUNBOOK — the remaining measurement (owner directive 2026-11-11)

State when this runbook was staged (2026-11-11 ~14:20 UTC):
- HEAD: the R6 code is COMPLETE and committed (gateway AIMD pacing
  7333f6f8c, transport budget 51f5e8371, retrieval per-job budget
  1a6b845c5, contract user-citation fix d4b57a0c7, instruments
  af0f13f00+, plus Tasks 2-5 committed earlier).
- The upstream zai quota went 429 at ~11:35 UTC (the run1 measurement
  + failed smokes burned the window; the 429 body carries no retry-after
  horizon). EVERYTHING below needs the quota alive again.
- Probes: `z-ai chat --prompt "Reply: OK" -o /tmp/zq.json` — dead while
  the body contains "status 429".
- SANDBOX RULE (measured): processes die at tool-call boundaries. Every
  block below is ONE tool call that starts its own gateway
  (scripts/r6_run_dev7.sh handles the gateway lifetime itself) and must
  finish inside ~9.5 min. Do NOT launch background processes across
  calls.

## Block A — fresh run #2 (pipeline arm, workers=3)
    cd /home/z/my-project/discovery-evidence-fabric && \
    timeout 560 bash scripts/r6_run_dev7.sh pipeline 3
  ~5-7 min. Then snapshot the per-problem walls + completion:
    python3 -c "import json,glob;
    [print(p.split('/')[-2], json.load(open(p)).get('wall_s'),
           json.load(open(p)).get('completed')) for p in
    glob.glob('eval/runs/*/bench-*/pipeline_record.json')]"
  Gate: median wall <= 120 s, worst <= 300 s (Task 7 instruments the
  repeats; this is repeat 1 of 3 on the final code).

## Block B — baseline + judge arms (completes run #2)
    timeout 560 bash scripts/r6_run_dev7.sh baseline,judge 3
  ~3-5 min. Snapshot eval/score/SCORE_TABLE.json ->
  ENGINE_RUNS/r6_fresh_run2_SCORE_TABLE.json afterwards.

## Block C — fresh repeats #2 and #3 (pipeline arm only, Task 7)
    timeout 560 bash scripts/r6_run_dev7.sh pipeline 3
    (twice; the walls + completion of all three pipeline blocks are the
    >=3-repeats speed measurement on the final code)

## Block D — composer-only ablation arm (Task 6)
    timeout 560 python3 scripts/r6_ablation.py arm composer_only

## Block E — leave-one-out ablation arms (Task 6; one call EACH)
    timeout 560 python3 scripts/r6_ablation.py arm no_RETRIEVE
    timeout 560 python3 scripts/r6_ablation.py arm no_SYNTHESIZE
    timeout 560 python3 scripts/r6_ablation.py arm no_MECHANISM_SPACE
    timeout 560 python3 scripts/r6_ablation.py arm no_COLLISION
    timeout 560 python3 scripts/r6_ablation.py arm no_ATTACK
    timeout 560 python3 scripts/r6_ablation.py arm no_COMPOSE
  (no_PHYSICS / no_CONTRADICTION / no_KILLER_EXPERIMENT /
   no_ADJUDICATION / no_RANK may follow if quota allows; the scope
   decision is recorded in scripts/r6_ablation.py ABLATION_STAGES.)

## Block F — blind 0-4 judging of every arm
    timeout 560 python3 scripts/r6_ablation.py judge
  (resumable; repeats only judge unjudged/failed outcomes)

## Block G — the ablation table
    python3 scripts/r6_ablation.py report
  -> eval/runs_ablation/<commit>/judgments/ablation_table_<commit>.json+.md
  Decision rule (pre-registered): stage proves value iff majority of
  pairs dQ > 0 AND CI lower bound > 0; else REMOVAL CANDIDATE. Every
  actual removal = one commit, constitution amended by deletion.

## Block H — seeded-defect sweep on the FINAL run's envelopes
    python3 scripts/r6_seeded_defects.py <final-commit12>
  (expect 21/21 caught, 0 false kills)

## Block I — two-turn token test + holdout gate statement
    timeout 300 python -m pytest tests/test_two_turn_no_leak.py -q
    (holdout: NOT run — gate is auditor-judged DEV wins+ties >= 50% on
    >=10 pairs; report the gate status honestly)

## Final report
  Commit every artifact (pairs, score tables, ablation tables, seeded
  sweep) per the repo convention, then push ALL commits with the PAT:
    git push https://<PAT>@github.com/prateekm1007/discovery-evidence-fabric.git
  ...and write the owner report (committed pairs, my-judged win/tie/loss,
  per-stage ablation table, speed, files changed, article per change).
