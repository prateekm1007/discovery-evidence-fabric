---
Task ID: R510-C11
Agent: new coder line (Windows fresh-clone session, R510-C1..C10 lineage)
Task: GATES OPEN ("2.9.0 stands" + "(b) resubmit") — execution #2 through harvest, then STOP.

Work Log:
- Rulings recorded verbatim in R510/GATE_RULINGS.json (transcript is authority). Baseline: HEAD == origin/main, frozen trio + constitution hold, prod d15aaa75/2.9.0.
- Pre-flight: first run exit 3 IDENTITY_MOVED (pin d7520b9b vs served d15aaa75) — typed, never bypassed. Re-baselined pin to the authorized nil-delta build (one constant + citation comment; old pin in history). Second run: GO exit 0, all six checks green (freeze/identity/durable/watchdog/act2/ruling). PREFLIGHT_GO.json in R510/.
- Observers armed pre-submit: kill-switch self-test 3/3; --loop cannot persist in sandbox (child reaped — playbook finding reconfirmed) so per-cycle --once substitution; ticks TICK_OK each cycle.
- Submit: first attempt refused (Windows cp1252 verbatim corruption — PYTHONUTF8=1 fix, no code change). All six submitted with capabilities persisted (ts_8c18df17b526, ts_e26b0ac86f54, ts_a5b990f9abcc, ts_7c70e5479fe6, ts_803b285dff01, ts_2951e2cceea5). Clarifications answered with own-verbatim text (HTTP 200).
- Terminals: 6/6 COMPLETE live; 6/6 terminal transitions durable (push path ALIVE — unlike execution #1).
- Harvest blockers fixed (harness-only): durable WORKTREE env override + local ./r506_durable worktree (gitignored); sys.executable one-token fix. First harvest 0/6 (no run dirs yet); waited for 6/6 durable terminals; re-harvest 6/6 rows.
- Rules merge: contamination 6/6 CLEAN; clarification 6/6 ABSENT-in-durable-record (rule-typed; live answers measured but unprovable from durable bytes — disclosed both).
- FUNNEL: 6/6 submitted→premise→evidence; 1/6 mechanisms; 1/6 distinct; 3/6 attack; 5/6 contradiction; 0/6 experimental; 1/6 mutated; 0/6 buyer_ready. BOTTLENECK: NO_CANDIDATES x5 >> ATTACK_KILLED x1. Families: mech 3 / therm 2 / elec 1, survived_all 0.
- Costs: per-run debits UNKNOWN (Art. XXV); zero direct metered calls; bucket 19/20 untouched by me.
- BS-021: R506/BATTERY_SESSIONS.json (capabilities) gitignored, never staged; pre-commit scan clean; remote clean. Scope: rulings + preflight record + driver harness fixes (2 minimal) + .gitignore worktree line + YIELD_MEASUREMENT.json + 6 YIELD_ROW files + harvest record + worklog. Zero engine delta.
- STOPPING per order: nothing beyond harvest is authorized.

Stage Summary:
- Execution #2 complete: six terminals, one bottleneck named by measurement (mechanisms_found::NO_CANDIDATES x5). True number moves only on auditor verdict — reported, not claimed. Awaiting funnel review + further word-acts.
- reviewer_provenance=AI_REVIEW
