# R509 — Engine-Side Respawn & Custody-Reconciliation Design (track 12; DESIGN ONLY, no code)

Directive anchor: "Engine-side respawn design (no code until post-harvest): boot-time orphan
reconciliation already exists but never ran (no restart occurred); design heartbeat-age reaping
+ idempotent resume, measure against the R508 deaths as test cases. Lands only after harvest, as
its own measured change with regression proof."

This design incorporates the R509-preserved facts (which rewrote the R508 death hypothesis:
no deaths occurred — all six workers COMPLETED; the silent stage was the durable push path).

## 1. The measured problem classes (test cases, from preserved + durable bytes)

### Class A — DURABLE_CUSTODY_SILENCE (the R509-measured mechanism; PRIMARY)

Facts (R509/RESIDUE_AUTOPSY.json, bytes cited per row):
- The engine's snapshot loop pushed successfully at 00:09:15Z (ok=true, pushed=true, files=3073)
  and then NEVER AGAIN — zero snapshots in the 760-row snapshot_log history ever carry
  ok=false or error; the log simply stops.
- Six terminal FINAL_SNAPSHOT phases (00:12:05–00:45:07Z) produced zero durable pushes.
- The measured engine_checkpoint cadence is 10.0 min (n=17 gaps, 6 historical sessions);
  the six RUNNING battery sessions received ZERO checkpoints after 00:09:15Z.
- The health surface reported healthy throughout: last_write_error=null,
  forensics_degraded=false, shrink_guard ok — the engine reported health while delivering
  nothing (a lie by omission at the observability layer, not a caught failure).

### Class B — actual mid-flight worker death (measured FALSE for the R508 battery, but the class remains real)

The R508 hypothesis (six independent OOMs / a shared hang) was dissolved by preserved bytes
(WORKER_COMPLETED 6/6). The class is still designed for: a worker that dies mid-run leaves a
non-terminal session with a stale heartbeat; today nothing reaps it inside a boot.

### Class C — boot-time-only orphan reconciliation (exists, never ran, and mislabels one case)

- ORPHANED_AT_RESTART events exist in the ledger (e.g. ts_f0880e025e60 at 2026-09-17T11:56:30Z),
  proving the boot-time reconciliation path works.
- The current boot (boot-1789685856, since 22:57:36Z) NEVER restarted →
  orphans_reconciled_this_boot=0 → the six completed-but-unpushed sessions were never
  reconciled, because reconciliation is boot-gated only.
- Oddity to handle: ts_f0880e025e60 shows WORKER_COMPLETED (11:05:58Z era) AND a later
  ORPHANED_AT_RESTART (11:56:30Z) — a completed session was still orphan-marked at the next
  boot. Reap semantics must treat terminal-in-live-store as NOT orphanable.

## 2. The design (four mechanisms, all engine-side)

### M1. Push-acknowledgment verification (closes Class A's detection gap)

After each snapshot push, the engine verifies the REMOTE tip actually advanced to the pushed
commit (fetch + rev-parse, the same observer move the R509 watchdog makes). Local push success
is not custody: N consecutive unacknowledged pushes (N=3, matching the watchdog's 3-missed-
checkpoint bound) set an engine-internal typed state DURABLE_CUSTODY_SILENCE, surfaced on
/api/health (a new field, e.g. durable.custody_silent_since) so the health surface can no
longer report healthy-while-delivering-nothing. Fail-closed: the state can only clear on a
VERIFIED remote tip advance, never on a timer.

### M2. Periodic (not boot-only) orphan/terminal reconciliation (closes Class A's repair gap + C)

A timer (piggyback the 10.0-min checkpoint cadence) diffs the live session store against the
durable sessions.json: any session whose live status is terminal (COMPLETE/ERROR_*) but whose
durable status is non-terminal (or absent) → re-push that session's state (idempotent: push
only if the durable bytes differ, keyed by a session-state hash). This mechanism alone would
have recovered all six R509 sessions (their live statuses were COMPLETE 00:12–00:45Z while
durable said RUNNING/BUILDING_PROBLEM). Terminal-in-live-store is never orphan-marked (fixes
the Class C oddity).

### M3. Heartbeat-age reaping (Class B)

A worker whose heartbeat age exceeds max(2 × heartbeat_interval, 10 min) while its session is
non-terminal → reap (kill the pid only if still alive; record the reap in the ledger with the
worker's exit status) → mark the session REAPED_STALLED (a typed execution state, never a
scientific verdict — Art. LXI). This is deliberately the LAST mechanism: reaping a live-but-
slow worker is worse than waiting (the R509 lesson — the workers were alive and completing).

### M4. Idempotent resume (Class B, the retry discipline)

Resume ONLY through Art. LXXIV §3: consult the durable run identity (run_id, attempt_id,
request_hash) and the persisted artifacts first — the R401 resume discipline (the persisted
artifact is the authority; the mutation spend is never re-burned). A resumed run continues
from the latest durable engine_checkpoint, never from scratch.

## 3. Regression-proof requirements (the landing gate, post-harvest)

The change lands only after harvest, as its own measured round, with these tests green before
any deploy:
1. Replay the R509 signature (the six preserved session views + the durable residue as
   fixtures): M2 detects all six terminal-without-durable sessions and pushes them; M1 flags
   custody silence at the first 3 unacknowledged pushes.
2. Replay the R484/R487 healthy closures (R509/REPLAY_*_CONTROL.json as the no-op fixtures):
   M2 no-ops; M1 never flags (every push acknowledged).
3. The Class C oddity fixture: a terminal-in-live-store session is never orphan-marked.
4. Tamper/identity cases: a diverged remote tip → fail-closed (never force-push; escalate).
5. The full existing suite + the R509 watchdog/kill-switch logic tests stay green.

## 4. What this design deliberately does NOT do

- No engine code this round (the tree freeze holds until harvest; this document is the design
  only, per the directive).
- No restart/rebuild/redeploy of the Space (forbidden until operator acts 1+2 land; act 1 is
  done, act 2 pending).
- No change to the frozen battery, instrument, or harvest rules (any change mints a new
  battery version and restarts LXXIX discipline).

reviewer_provenance=AI_REVIEW
