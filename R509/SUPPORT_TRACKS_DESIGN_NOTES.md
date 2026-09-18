# R509 Support Tracks — Design Notes (Tracks 10 & 12)

Directive anchor: CEO "all bottlenecks, one ordered campaign", parallel tracks 10-12.
Scope law honored: design records only — no engine code lands until its named phase
(track 12: post-harvest; track 10: rehearsal-only execution window).

## Track 12 — Engine-side respawn design (design only; code lands post-harvest)

**Measured inputs this round (all from the Phase-1 autopsy bytes):**

1. Boot-time orphan reconciliation EXISTS and never ran (`orphans_reconciled_this_boot=0`
   at R508 health bytes; no Space restart occurred inside boot-1789685856's 13h window).
2. The execution #1 failure was NOT worker death: all six workers reached
   `TERMINAL_STATE(COMPLETE, phase 5, FINAL_SNAPSHOT)` (preserved capture) — the silent
   stage was the durable push path (zero snapshots after 00:09:15Z,
   `last_write_error=null`, `forensics_degraded=false`).
3. Worker heartbeat cadence measured ~30s on live workers (durable forensics ledger,
   11 heartbeats for s1 across 00:04:38–00:09:08Z); the run-duration distribution is
   n=98 / p50=11min / p90=41min (R508 evidence).

**Design (three mechanisms, each with its Art. XXVII threshold source):**

- **M1 — DURABLE-PUSH CUSTODY WATCHDOG (engine layer; the missing piece execution #1
  actually exposed).** A terminal `FINAL_SNAPSHOT` phase that produces no durable
  snapshot within `T_push` must retry with backoff and then type
  `PUSH_RETRY_EXHAUSTED(session_id, attempts, last_error)` into the worker log tail —
  never silent. `T_push` derives from the measured snapshot-latency distribution
  (`snapshot_log.jsonl` inter-event latencies on `runtime-state-hf`; derive at
  implementation time from those bytes — NOT from the 2×p90 run bound, which measures
  a different quantity).
- **M2 — HEARTBEAT-AGE REAPING.** A worker registry entry whose heartbeat age exceeds
  `T_reap` is reaped and its session typed `WORKER_REAPED_HEARTLESS` (LXXIV state
  machine; never `FAILED` by inference). `T_reap` derives from the measured healthy
  heartbeat-gap distribution on the durable forensics ledger (max healthy gap ×
  disclosed factor k; derive at implementation time). Composes with the existing
  boot-time reconciliation: reaping also runs at boot (reconciliation already exists)
  and mid-boot (new).
- **M3 — IDEMPOTENT RESUME.** A session non-terminal on the durable authority but
  terminal in the ephemeral store (exactly execution #1's shape) reconciles by PUSHING
  the terminal state, never re-running: the persisted artifact is the authority
  (R401 resume discipline; LXXIV s3 — "did this operation actually execute?" answered
  from the run identity before any retry).

**Test cases (measure against execution #1's deaths, as directed):**

- TC1: six terminal phases with a silently-dropped push path → engine retries, types
  `PUSH_RETRY_EXHAUSTED`, zero silent custody loss (execution #1 replay).
- TC2: worker heartbeats stop mid-phase → reaped at `T_reap`, session typed
  `WORKER_REAPED_HEARTLESS`, no false reap of a healthy worker replayed from the
  2026-09-17 healthy-closure forensics (max measured healthy gap 37.3 min).
- TC3: durable-nonterminal + ephemeral-terminal after restart → M3 pushes, does not
  re-run; the R401 identity fields answer "executed?" first.

**Landing gate:** post-harvest, as its own measured change with regression proof
(directive item 12); nothing here authorizes touching `toscanini/` now.

## Track 10 — R370G door rehearsal (harness spec; execution window noted)

**The door (mapped at R507, unchanged):** `reality_ingestion` validate → ingest →
ledger → decide → causal_learning learn; the survivor campaign consumes a REAL packet
only after a survivor exists (directive: "no REAL packet until a survivor exists").

**Harness spec (`scripts/r510_r370g_door_rehearsal.py`, to be written in its named
window):**

1. Labeled rehearsal fixture: one synthetic REALITY packet, stamped
   `fixture_class=REHEARSAL_SYNTHETIC` in every field that reaches the ledger —
   structurally indistinguishable from production bytes to the door, but marked at
   the ledger layer so a rehearsal row can never promote (never REAL).
2. End-to-end walk: validate (schema + origin-tag refusals) → ingest → ledger append
   → decide → learn; each stage's typed outcome recorded; a rehearsal asserts the
   door REFUSES malformed inputs at each stage (negative controls, Art. XVII).
3. Acceptance: rehearsal produces a REAL_LOOP-candidate record with
   `fixture_class=REHEARSAL_SYNTHETIC` and `REAL_LOOP_VERIFIED` derivation asserted
   UNREACHABLE for the fixture (a rehearsal can never mint the real thing).

**Status: NOT_RUN_THIS_ROUND (typed, Art. LXI/LXXIV).** Unblock: the post-harvest
window (or the survivor campaign's own gate) opening the rehearsal execution window;
engine import verification happens then. Nothing was promoted; no REAL packet touched.
