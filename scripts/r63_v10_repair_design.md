# V10 REPAIR-LOOP DESIGN — plan layer (claim c-0086)

**Session:** builder-r63s1 · **Base:** `b8117977d` (audit `b35dc0adf`, AM57)
**Mandate:** auditor Finding 1 / direction 7 — "no row converges; repairs ≈ negative value → v10 repair-loop work; V7.7 loop frozen for v9; do not tune the repair budget to pass."
**Scope:** design + offline prototype + tests. Zero engine lines, zero z-ai probes, zero changes to the sealed v9 instrument.

## 1. The measured problem

The V8.1 pre-run census (9/9 rows, `eval/v81_run/rows/`):

| evidence | value |
|---|---|
| rows | 9/9 burned the **full repair budget** (`repairs: 3`) |
| convergence | **6/9 rows ended critic=FLAG** — budget exhausted, verdict non-clean |
| the 3 CLEAN rows | also spent all 3 repairs to get there |
| ledger | `v81_events_ledger.json`: no per-repair value record exists |

The auditor's Finding 1 words are the honest summary: **no row converges, and the repairs are approximately negative value** — the loop spends its budget without measurably improving the answer.

## 2. The mechanism, read from the frozen code

`scripts/r40_machine_v77.py` (`machine_generate_v77`, the loop the v9 instrument byte-reuses):

1. Draft → critic + type-gate + ~10 deterministic scans + LLM direction check → collect `problems`.
2. If any problem: append **the full static directive stack** (`V77_REPAIR_DIRECTIVE` = V7.6 stack + the four AM37 clauses, several hundred lines) to the ORIGINAL question and **regenerate the entire bill**.
3. Repeat to `REPAIR_BUDGET = 3`; disclose residuals.

Three defects follow directly:

- **(a) Untargeted re-roll.** The repair re-rolls the whole answer against a static mega-prompt. Findings already fixed can regress (churn); the deterministic scans carry precise anchors, but the loop truncates messages to 110 chars and discards position — the model cannot see *what* to fix *where*.
- **(b) No convergence detection.** Nothing compares attempt *N*'s finding set to attempt *N−1*'s. A finding the model cannot fix from prose (e.g. a mechanism class the constraint forbids) keeps the loop re-rolling the same axis — the stuck-axis burn the census shows.
- **(c) No value accounting.** Nothing records whether repair *N* reduced the violation load, so the loop cannot stop when marginal value ≤ 0. "Repairs ≈ negative value" is precisely the unpriced tail of this loop.

## 3. The v10 strategy (what the prototype implements)

`scripts/r63_machine_v10_proto.py` — machinery byte-reused, strategy new:

1. **Targeted directives.** Each finding key maps to a typed remediation bind (`_V10_BINDS`, real keys from the real scans: `PHYSICS_DIRECTION_INVERTED` → "replace the mechanism, never reword"; `INPUT_UNAVAILABLE` → "re-choose the mechanism, do not invent instrumentation"; `UNPRICED_DUTY_CYCLE` → "add the OPERATIONAL COST line"; …), quotes the offending evidence, and carries a **BYTE-KEEP CONSTRAINT**: every section not named by a finding stays byte-identical — the repair is an edit, not a re-roll. Critic anchors are carried verbatim.
2. **Convergence guard.** `finding_signature()` = the normalized finding-key set (scan keys + critic anchors + gate mismatch). An identical signature on **two consecutive attempts** is a STUCK AXIS → typed `EARLY_STOP:STUCK_AXIS` with residual disclosure — budget preserved for the set, churn ended.
3. **Value ledger.** Every attempt records `violations_n`, `critic_flags_n` and `value_delta` vs the previous attempt. **Two consecutive value-zero-or-worse repairs** → `EARLY_STOP:NO_MARGINAL_VALUE` — the loop stops when it demonstrably stops adding value, instead of pricing the tail at negative.
4. **Budget untouched.** `REPAIR_BUDGET_V10 = REPAIR_BUDGET` imported from the frozen machine (identity-tested). The guard does the work; the budget is never the mechanism. The design makes rows converge by *stopping honest work on stuck axes and editing instead of re-rolling* — not by spending more, and not by loosening any check.

## 4. What is proven offline (9/9 tests, `tests/test_r63_v10_repair_proto.py`)

- CLEAN path: zero repairs, zero churn (`test_1`).
- Stuck axis: same finding set twice → stop after ONE repair, residuals disclosed (`test_2`) — the budget slot saved is the churn the census shows.
- Value-flat axis: findings swap but the load never drops → stop after TWO repairs (`test_3`, deltas `[0, 0]`).
- Improving axis: the loop legitimately runs to the unchanged budget and types `BUDGET_EXHAUSTED` (`test_4`).
- The directive is targeted and short, and does NOT re-quote the mega-stack (`test_5`, distinctive clause header absent, length < half the stack).
- Byte-reuse by function identity with `r40_machine_v77` (`test_6`); budget constant untouched, source-checked (`test_7`).
- The REAL production scan composition executes on a real holdout problem (`test_8`).
- Signature semantics (`test_9`).

## 5. What is NOT yet proven (honest bounds)

- **No LLM-connected run exists.** Direction 1: the 429 window stays dark; the real gen/critic/direction functions are injected but unwired. The first live validation happens after the window clears, in the challenger/v9 lanes' order, never inside the sealed v9 run.
- **The value metric is violation-load-based**, not rubric-based. The load (finding count) is a proxy; the true value measure is the auditor's rubric. v10's ledger gives the loop a stop rule it can compute; whether stops trade residual-disclosure for higher rubric scores is an acceptance-run question, judged from the run's own events ledger.
- **The v9 instrument stays byte-frozen.** This prototype changes nothing the sealed run imports; wiring v10 into a generation run is a NEW claim (and, per Finding 2 sequencing, follows the adoption-verdict order on the plan layer).

## 6. Sequence from here

1. 429 window clears (Art. 15 typed; environmental).
2. c-0079 lease expires 2026-11-19T00:00:00Z → challenger resume (lease-holder's lane) → rows 5–36 → adoption verdict (ADOPT/DELETE on the plan layer).
3. c-0082 (holdout-v9-generation) → the frozen v9 one-shot on the engine-route machine.
4. Auditor scoring vs the private-repo rubric (mean ≥ 3.0, 0/0/0, CI excludes 3.0).
5. Finding 1's live half: wire v10 behind a NEW claim, validate on the dev corpus, then the acceptance question re-opens for v10 on its own evidence.
