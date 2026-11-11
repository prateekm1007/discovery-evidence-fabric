# R6 RUNBOOK — the remaining measurement (owner directive 2026-11-11)

State when this runbook was last updated (post-audit, 2026-11-11):
- HEAD: R6 audit P0 fixes applied — certification suite restored
  (test_r6_cad_kernel), deterministic gates hardened, composer
  subordinated to discovery eligibility, answer-contract claim-level
  provenance, call-budget instrument v2 (ledger-anchored, audit P0-9),
  run-identity isolation (audit P0-8: unique run root per measured
  attempt, judge-record input binding). The R6 fresh-run-2 artifacts
  are committed (SCORE_TABLE + pairs + CALL_BUDGET v2 under 983cad20).
- The upstream provider quota went 429 during run2 (xkiro probes
  failed at 20.3/20.4 s -> NO_CALIBRATED_JUDGE_ROUTE; judge-dependent
  measurements are NOT_MEASURED, Art. LXI). EVERYTHING below needs a
  live quota window again.
- Probes: `z-ai chat --prompt "Reply: OK" -o /tmp/zq.json` — dead while
  the body contains "status 429".
- SANDBOX RULE (measured): processes die at tool-call boundaries. Every
  block below is ONE tool call that starts its own gateway
  (scripts/r6_run_dev7.sh handles the gateway lifetime itself) and must
  finish inside ~9.5 min. Do NOT launch background processes across
  calls.

## Run identity and isolation (audit P0-8) — read before any block
- Every invocation of eval/run.py mints a UNIQUE run root:
  `eval/runs/<commit>/r{repeat}-{arms}-{utc19}/`. Pipeline, baseline
  and judge arm records, timeout records and pair custody for THIS
  attempt live ONLY under that root. Two attempts never share a root,
  so no record is ever overwritten (speed repeats and scored repeats
  are separate roots by construction).
- `--repeat N` labels which repeat of the (commit, arms, dataset)
  block this invocation is; it appears in the run id and in
  `_run_meta.json` + SCORE_TABLE `run_id`. Omit it and the repeat
  still gets a distinct root (the timestamp in the id guarantees it);
  declare it when you want the block's identity in the record.
- Child processes (per-problem pipeline workers, the two-turn round-2
  spawn) inherit the parent's run id verbatim via `--run-id`, so one
  attempt = one root end to end. Route probes and the two-turn
  snapshot cache stay COMMIT-level (commit-scoped capability cache;
  cross-commit reuse remains forbidden).
- Scoring is bound to one IMMUTABLE scoring root: a SCORE_TABLE build
  reads only `eval/runs/<commit>/<run-id>/`. Each judge record carries
  `bound_inputs` (pipeline/baseline answer sha256, evidence snapshot
  hash, judge route, rubric version); a scoring pass re-verifies them
  and EXCLUDES any judgment whose inputs no longer match
  (INCOMPLETE_INPUT_MISMATCH) or which predates binding
  (UNBOUND_LEGACY). Excluded counts ride the table as
  `n_input_mismatches` / `n_unbound_legacy`.
- Speed repeats protocol (owner directive item: P0-10): run BOTH
  `--workers 1` and `--workers 3`, each >= 3 repeats, as SEPARATE
  invocations (each its own unique root). Report p50/p95/max from the
  per-repeat wall sets, labelled by worker count; a single worker
  count is not a speed claim.
- Call budget (audit P0-9, v3 instrument — canonical ledger): run
  `python scripts/r6_call_budget.py <run-root-dir>` per run root.
  TWO separate measures per stage row: `provider_attempts` (one
  record_call_outcome line per provider request — retries,
  transport failures and provider fallbacks INCLUDED, distinct by
  generate_call_id) and `logical_calls` (provider attempts grouped
  into call intents: a retry/fallback chain of the same intent is
  ONE logical call; unrecorded chain heads are flagged, never
  fabricated). The twelve-call target STATED to apply to the
  LOGICAL measure only (target_applies_to / target_statement in the
  output); total_provider_attempts is reported as quota cost, never
  certified against the target. Without the run ledger, envelope
  attribution measures the logical measure only and provider
  attempts are NOT_MEASURED (0 only when stage attribution records
  0 LLM calls — a no provider request). Observed post-rank stages
  (POST_RANK_*) get rows and enter the totals; conditional work
  that did not run creates no row and blocks nothing. Any
  NOT_MEASURED expected stage blocks that measure's total
  (within_target = null). A stage with attribution but zero
  ledger lines is provenance-incomplete: NOT_MEASURED, never zero.

## Block A — fresh run (pipeline arm, workers=3)
    timeout 560 bash scripts/r6_run_dev7.sh pipeline 3 --repeat 1
  ~5-7 min. Each launch prints its run id (the unique root under
  eval/runs/<commit>/); note it for the report. Then snapshot the
  per-problem walls + completion from THAT root:
    python3 -c "import json,glob;
    [print(p.split('/')[-3], p.split('/')[-2], json.load(open(p)).get('wall_s'),
           json.load(open(p)).get('completed')) for p in
    glob.glob('eval/runs/*/*/bench-*/pipeline_record.json')]"
  Gate: median wall <= 120 s, worst <= 300 s (Task 7 instruments the
  repeats; this is repeat 1 of 3 on the final code).

## Block B — baseline + judge arms (completes the scored root)
    bash scripts/r6_run_dev7.sh baseline,judge 3 --repeat 1
  ~3-5 min. The scored root (run id shown on stdout at launch, also in
  SCORE_TABLE `run_id`) is IMMUTABLE from here on; later repeats get
  their own roots and never rewrite it. Snapshot
  eval/score/SCORE_TABLE.json afterwards. Judge arms need a CALIBRATED
  judge route (run_judge_calibration passes on 24/30); while the
  quota is 429 the arms run but scoring is NOT_MEASURED — do not
  pretend a score exists.

## Block C — speed repeats (Task 7; the P0-10 protocol)
  1-worker block, 3 repeats, each its OWN unique run root:
    bash scripts/r6_run_dev7.sh pipeline 1 --repeat 1
    bash scripts/r6_run_dev7.sh pipeline 1 --repeat 2
    bash scripts/r6_run_dev7.sh pipeline 1 --repeat 3
  3-worker block, 3 repeats, same discipline:
    bash scripts/r6_run_dev7.sh pipeline 3 --repeat 1
    bash scripts/r6_run_dev7.sh pipeline 3 --repeat 2
    bash scripts/r6_run_dev7.sh pipeline 3 --repeat 3
  Speed statistics (p50/p95/max, per worker count) are read from each
  root's pipeline_record.json walls; per-problem stage_times are kept
  on timeout (INCOMPLETE_INFRASTRUCTURE, not a speed sample beyond the
  cutoff). Report both worker sets; one is not a speed claim.
  Also run the call-budget instrument on EACH root (v2, ledger-
  anchored) and commit the outputs with the table.

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
  Audit P1-11: each ablation judgment is bound to its OWN calibration
  record (route + rubric version + calibration sha); judgments from a
  shared-family or uncalibrated judge route are labelled and can NOT
  carry a REMOVAL_CANDIDATE verdict past the auditor's adjudication.

## Block H — seeded-defect sweep on the OWNER-HELD specimens
    python3 scripts/r6_seeded_sweep.py \
        --specimens <owner-held path to seeded_specimens_v1.json> \
        --expected-selection-sha256 <full-64-hex> [--prefix-match]
  (FAIL-CLOSED on absent file or hash mismatch; the sweep is
  DETERMINISTIC — zero LLM calls — and reports per-class catch and
  false-kill AGGREGATES only; per-specimen rows go to gitignored
  ENGINE_RUNS scratch, never committed, never pasted into the report.
  The R6 circular sweep (self-authored defects scored by the same
  hand) was retired, not repaired. Art. XIX, XXV, LXIV.)

## Block I — two-turn token test + holdout gate statement
    timeout 300 python -m pytest tests/test_two_turn_no_leak.py -q
    (holdout: NOT run — gate is auditor-judged DEV wins+ties >= 50% on
    >=10 pairs; report the gate status honestly)

## Final report
  Commit every artifact (per-run-root pairs + SCORE_TABLE, ablation
  tables, call-budget v2 outputs, seeded sweep) per the repo
  convention, then push ALL commits with the PAT:
    git push https://<PAT>@github.com/prateekm1007/discovery-evidence-fabric.git
  ...and write the owner report (committed pairs, my-judged win/tie/loss,
  per-stage ablation table, speed by worker count, LLM call budget v2
  per run root, files changed, article per change).
