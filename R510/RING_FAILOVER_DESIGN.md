# B3 Ring-Failover Design (R510) — records-only; code post-harvest per stop-list

## Measured prior (bytes, not impressions)

- R504 matrix: `xkiro` HEALTHY, `atria`/`zai`/`unorouter` DEGRADED,
  `hf`/`openrouter`/`nvidia` UNKNOWN, six more UNAVAILABLE.
- R505: `unorouter` glm-5.3 AUTH_FAILURE, `apinex` CREDIT_EXHAUSTED (round-record
  typed classes); `xkiro` the only HEALTHY strong ring, with 1-3 cases/run
  line-coherence flakiness.
- R510 rerun: `xkiro` 21/21 verdict-class, zero transport failures (this window).

## Policy (what the post-harvest code will implement)

- **R1 — dead-rung skip.** First no-verdict failure signal on a rung (transport
  CALL_FAILED with overall EVALUATOR_CALL_FAILED — the r505 early-stop
  definition) marks it policy-dead. No further attempts until a fresh PROBE_OK
  re-admits it (the `runtime_admission` pattern). Terminal AUTH/CREDIT/GONE
  classes mark dead immediately with the class recorded.
- **R2 — capability-aware preference.** Order attempts by latest measured state:
  HEALTHY first; DEGRADED only with the degradation labeled on the attempt;
  UNKNOWN only after probe-before-admit (`transport_capability` pattern). Never
  "always available" claims (BS-028).
- **R3 — substitution ledger.** Every substitution records `substituted_from` +
  degradation + cost_provenance (the `llm_registry`/`model_routing` ledger
  pattern). A degraded substitution that succeeds is labeled success-with-
  degradation, never silent equivalence (Art. XXVIII).

## Replay proof

`scripts/r510_failover_replay.py` over 25 recorded DEV attempts
(`R510/FAILOVER_REPLAY.json`): both dead rungs marked on first signal, 2
post-signal attempts suppressed, `allowed_into_known_dead == 0`, healthy
21-attempt control untouched. Acceptance true.

## Landing rule

Code lands only with the post-harvest cliff-fix IF the funnel names
substitution, otherwise with the respawn change (Part 3.1). No engine delta
this round.
