# Constitutional Amendment — Articles LXXIV–LXXIX: Sandbox / Execution Durability Principles

> **STATUS: SUPERSEDED BY THE UNION (race instance 6 — see
> R485/LINEAGE_RECONCILIATION.json).** Both lines amended the
> Constitution v2.5.0 → v2.6.0 from the operator's identical
> 2026-09-17 directive. The parallel line's single Article LXXIV
> (Observer-Independent Durable Execution) landed first on origin/main
> (93fec61c, certified hash 17464afd…) and is CANONICAL. This
> six-article proposal — the second line's — carries the SAME
> operator principles (A–M + FAIL CLOSED, PROGRESS OPEN) in a
> distributed structure; per Art. LXIV it is RETIRED as law and
> preserved here as the honest history of the amendment race. The
> second line's surviving deltas in the canonical tree:
> `execution_states.recovery_decision()` (principle M as an
> executable typed decision) + `tests/test_r485_recovery_order.py` +
> `R485/ATTEMPT5_LIFECYCLE.json` (the four-domain lifecycle evidence).
> The operator's directive text below is verbatim either way — the
> LAW's content was never in dispute, only its sectioning.

**Round:** R485
**Ratified:** 2026-09-17
**Amends:** Constitution v2.5.0 → v2.6.0
**Sponsor:** Operator directive (verbatim below) — delivered after the
measured event: the Z.ai sandbox reaped all local background processes
mid-run while the server-side run continued (R485/ATTEMPT5_LIFECYCLE.json).

---

## THE OPERATOR'S DIRECTIVE (VERBATIM)

> Yes. This is a **serious architectural issue**, because Toscanini is
> supposed to be an end-to-end AI. If the orchestration depends on a
> local sandbox process remaining alive while the external AI
> computation continues, the execution model is fragile.
>
> I would **not accept "manual foreground polling" as the permanent
> architecture**. It is a temporary diagnostic protocol.
>
> ### NEW — SANDBOX / EXECUTION DURABILITY PRINCIPLES
>
> **A. Execution is not observation**
> > The lifetime of a caller, tool invocation, terminal session,
> > polling process, or sandbox MUST NOT define the lifetime of an AI
> > run.
> > A caller disappearing does not mean the run failed.
> > A polling process disappearing does not mean the run failed.
> > A sandbox being reaped does not mean the remote computation failed.
>
> **B. Remote work must be durable**
> > Any operation capable of exceeding the execution environment's
> > foreground/tool-call lifetime MUST be represented as a durable
> > server-side job with a stable run identity.
> > The durable identity must survive: polling termination, browser
> > refresh, worker restart, sandbox destruction, network interruption,
> > tool timeout.
>
> **C. Observation failure ≠ execution failure**
> > Failure to observe a running operation MUST NOT be classified as
> > failure of the operation itself.
> > Therefore `POLL_TIMEOUT` is not `RUN_FAILED`, and
> > `SANDBOX_REAPED` is not `REMOTE_JOB_FAILED`, and
> > `NO_LOCAL_PROCESS` is not `NO_SERVER_WORK`.
>
> **D. Never depend on a local background process for canonical state**
> > A local background process MAY assist observation, diagnostics, or
> > development, but MUST NOT be the sole authority for execution
> > state, completion, artifacts, or provenance.
> > Canonical state belongs server-side.
>
> **E. Every long-running operation has a durable state machine**
> > At minimum: QUEUED / STARTING / RUNNING / WAITING_EXTERNAL /
> > COMPLETED / FAILED / CANCELLED / EXPIRED / UNKNOWN.
> > Critically, `UNKNOWN` must remain distinct from `FAILED`.
> > This directly reinforces your existing Article XXV doctrine that
> > unknown remains unknown.
>
> **F. Polling is an observation mechanism, not an execution mechanism**
> > Polling MUST only observe durable state. Polling MUST NOT be
> > required to keep computation alive.
>
> **G. Reconnection is normal**
> > Any client must be able to disconnect and later reconnect to the
> > same run without loss of canonical execution state.
> > This should become an explicit E2E test.
>
> **H. Completion must be independently observable**
> > A completed run MUST be recoverable from durable server-side state
> > without relying on the process that initiated or polled the run.
> > That means the UI can disappear for 20 minutes and come back to:
> > **Discovery still running → 63% / current stage → completed
> > artifacts** rather than **Connection lost → start again.**
>
> **I. Provider execution and sandbox execution are separate boundaries**
> > Toscanini MUST distinguish provider execution state from local
> > execution environment state.
> > `LOCAL_SANDBOX = REAPED` + `REMOTE_PROVIDER = RUNNING` is a valid
> > state. `LOCAL_SANDBOX = ALIVE` + `REMOTE_PROVIDER = FAILED` is a
> > valid state. They must never be collapsed into one `failed`
> > boolean.
>
> **J. Timeout semantics must be typed**
> > Do not have one generic timeout. Use distinct categories such as:
> > TOOL_TIMEOUT / SANDBOX_TIMEOUT / LOCAL_PROCESS_REAPED /
> > REMOTE_PROVIDER_TIMEOUT / REMOTE_PROVIDER_UNAVAILABLE /
> > POLL_TIMEOUT / POLL_INTERRUPTED / JOB_EXPIRED / JOB_FAILED /
> > JOB_UNKNOWN. The distinction matters scientifically and
> > operationally.
>
> **K. Long-running work must be background-first**
> > If expected runtime exceeds the reliable foreground execution
> > budget, Toscanini MUST launch durable asynchronous work and return
> > a run/job identity rather than holding a foreground invocation
> > open.
>
> **L. Retry must be idempotent**
> > A retry after timeout, disconnect, or lost observation MUST NOT
> > silently duplicate an external AI operation or corrupt canonical
> > state. Every externally meaningful operation should therefore have
> > an identity such as: run_id / operation_id / attempt_id / provider
> > / model / model_revision / request_hash. A retry should be able to
> > answer: "Did this operation actually execute?" before launching
> > another one.
>
> **M. Never restart merely because observation was lost**
> > Toscanini MUST NOT restart an expensive AI computation solely
> > because the observer lost contact with it. First: LOOK UP DURABLE
> > RUN → IS IT RUNNING? → IS IT COMPLETE? → IS IT FAILED? → ONLY THEN
> > CONSIDER RETRY. This will save enormous model/API waste.
>
> ### One principle I would make especially prominent
>
> **FAIL CLOSED, PROGRESS OPEN**
>
> > The system must fail closed with respect to truth, but remain open
> > with respect to recoverable execution.
> >
> > If Toscanini cannot determine whether Z.ai completed: **do not
> > claim completion.** But also: **do not throw away the run.** Keep
> > `UNKNOWN` and recover observation.
>
> ### What I would tell the coders now
>
> > Read the Constitution before touching this.
> > The Z.ai sandbox timing problem is now treated as an
> > execution-architecture issue, not merely a polling inconvenience.
> > The current observation: "All local background processes were
> > reaped by the sandbox, while attempt 5 continues server-side" must
> > be modeled as two independent execution domains.
> > Do not introduce `ENGINE_OPERATOR_KEY`.
> > Do not make local background processes a prerequisite for the AI
> > run.
> > Do not classify local process death as remote AI failure.
> > Do not rely on manual foreground polling as the permanent solution.
> > First establish the actual lifecycle of attempt 5 and produce
> > evidence showing: `local observer state → remote job state →
> > provider state → canonical Toscanini run state`.
> > Then implement the minimum durable execution contract required so
> > that: **sandbox death, browser disconnect, polling interruption, or
> > tool timeout cannot destroy or invalidate a server-side AI run.**
> > The user must be able to reconnect to the same run and recover its
> > state and artifacts.
> > A fresh E2E test must demonstrate: **start run → intentionally
> > lose local observer → remote work continues → reconnect → recover
> > run → complete → canonical artifacts available.**
> > Do not claim the problem solved from successful manual polling.
> > The permanent acceptance criterion is **observer-independent
> > execution**.
>
> ### And this changes the current priority
>
> > **P0 — Durable end-to-end execution** before **P1 — browser
> > showcase matrix**, because a beautiful Claude-like interface is
> > irrelevant if the underlying AI discovery can disappear when its
> > sandbox observer dies. The real target is: **Claude-like simplicity
> > at the surface + durable autonomous execution underneath.**

(The operator's message additionally cited current guidance and
comparable agent-runtime designs — Hugging Face background Jobs with
job IDs/status/logs and `InferenceTimeoutError`, agent-sandbox designs
that separate the agent loop from sandbox execution with
persist/recover on expiry, and agent-tool research on partial
execution, retries, and stale observations. Full text preserved in the
round record.)

---

## THE RATIFIED ARTICLES

The six articles below carry the operator's principles A–M and the
prominent FAIL CLOSED, PROGRESS OPEN doctrine into constitutional law.
Mapping: A/C/F/M → LXXIV; B/D/G/H/K → LXXV; E/J → LXXVI; I → LXXVII;
L → LXXVIII; the prominent doctrine → LXXIX.

The ratified article language is verbatim in the Constitution body
(between Article LXXIII and THE FOUR CONSTITUTIONAL LAYERS) and here.

---

## Article LXXIV — Execution Is Not Observation (Observer Independence)

The lifetime of a caller, tool invocation, terminal session, polling
process, or sandbox MUST NOT define the lifetime of an AI run. A
caller disappearing does not mean the run failed. A polling process
disappearing does not mean the run failed. A sandbox being reaped does
not mean the remote computation failed.

Failure to observe a running operation MUST NOT be classified as
failure of the operation itself. `POLL_TIMEOUT` is not `RUN_FAILED`;
`SANDBOX_REAPED` is not `REMOTE_JOB_FAILED`; `NO_LOCAL_PROCESS` is not
`NO_SERVER_WORK`.

Polling is an observation mechanism, not an execution mechanism.
Polling MUST only observe durable state; polling MUST NOT be required
to keep computation alive. Manual foreground polling is a temporary
diagnostic protocol, never the permanent architecture.

Toscanini MUST NOT restart an expensive AI computation solely because
the observer lost contact with it. The recovery order is mandatory:
look up the durable run — is it running? is it complete? is it
failed? — and only then consider retry.

Constitutional basis: extends Article XXV (unknown must remain
unknown — the observer's ignorance is not the run's failure), Article
XXIX (separate implementation failure from mechanism failure — the
observer is infrastructure, the run is the work), and Article LXI
(infrastructure failure is never scientific rejection). Measured
basis: R485/ATTEMPT5_LIFECYCLE.json — the run advanced 25+ minutes
past its observer's death, checkpoints on the durable branch.

## Article LXXV — Remote Work Must Be Durable (the Server-Side Job Contract)

Any operation capable of exceeding the execution environment's
foreground/tool-call lifetime MUST be represented as a durable
server-side job with a stable run identity. The durable identity must
survive: polling termination, browser refresh, worker restart, sandbox
destruction, network interruption, tool timeout.

A local background process MAY assist observation, diagnostics, or
development, but MUST NOT be the sole authority for execution state,
completion, artifacts, or provenance. Canonical state belongs
server-side. Local background processes are never a prerequisite for
the AI run.

If expected runtime exceeds the reliable foreground execution budget,
Toscanini MUST launch durable asynchronous work and return a run/job
identity rather than holding a foreground invocation open
(background-first).

A completed run MUST be recoverable from durable server-side state
without relying on the process that initiated or polled the run: the
UI can disappear for twenty minutes and return to "discovery still
running, current stage, completed artifacts" — never "connection
lost, start again". Any client must be able to disconnect and later
reconnect to the same run without loss of canonical execution state;
reconnection is a mandatory E2E test surface.

Constitutional basis: extends Article X (canonical state has one
authority — the server-side durable branch, never a local process)
and Article LXXI (the deployed production URL is the delivery
standard — the durable job lives there). Measured basis: the R484
durability fixes (atomic `_persist`, the bounded checkpoint timer,
the IN_FLIGHT IMPROVE_LEDGER) and the attempt-4 forensics
(R484/ATTEMPT4_FORENSICS.json — the class that made this law
necessary).

## Article LXXVI — The Durable State Machine and Typed Timeouts

Every long-running operation has a durable state machine. At minimum:

```text
QUEUED
STARTING
RUNNING
WAITING_EXTERNAL
COMPLETED
FAILED
CANCELLED
EXPIRED
UNKNOWN
```

`UNKNOWN` must remain distinct from `FAILED` — this reinforces
Article XXV at the execution layer: the system that cannot determine
an outcome records `UNKNOWN` and recovers observation; it never
converts ignorance into failure.

Timeout semantics must be typed. One generic timeout is forbidden.
Distinct categories at minimum:

```text
TOOL_TIMEOUT
SANDBOX_TIMEOUT
LOCAL_PROCESS_REAPED
REMOTE_PROVIDER_TIMEOUT
REMOTE_PROVIDER_UNAVAILABLE
POLL_TIMEOUT
POLL_INTERRUPTED
JOB_EXPIRED
JOB_FAILED
JOB_UNKNOWN
```

The distinction matters scientifically and operationally: a provider
timeout is an Article LXI infrastructure event; a sandbox reaping is
an observer-domain event; a poll interruption carries no information
about the job at all.

Constitutional basis: extends Article XXV (unknown remains unknown),
Article XIII (research and infrastructure are separate authorities),
and Article LXI. Implementation note (the Four Layers rule): this
article fixes the invariant, not the enum's exact spelling in code —
the current session vocabulary (AWAITING_CLARIFICATION, BUILDING_
PROBLEM, RUNNING, COMPLETE, INTERRUPTED, UNKNOWN) maps onto this
machine, and the typed-timeout vocabulary is the implementation's to
complete.

## Article LXXVII — Provider Execution and Sandbox Execution Are Separate Boundaries

Toscanini MUST distinguish provider execution state from local
execution environment state. `LOCAL_SANDBOX = REAPED` with
`REMOTE_PROVIDER = RUNNING` is a valid state. `LOCAL_SANDBOX =
ALIVE` with `REMOTE_PROVIDER = FAILED` is a valid state. They must
never be collapsed into one `failed` boolean.

Constitutional basis: extends Article XXIX (implementation vs
mechanism) and Article XLV (generator/verifier separation) to the
execution domains: the observer, the job, and the provider are three
authorities with independent lifetimes and independent failure
classes.

## Article LXXVIII — Retry Must Be Idempotent

A retry after timeout, disconnect, or lost observation MUST NOT
silently duplicate an external AI operation or corrupt canonical
state. Every externally meaningful operation carries an identity:

```text
run_id
operation_id
attempt_id
provider
model
model_revision
request_hash
```

A retry must be able to answer "did this operation actually execute?"
before launching another one.

Constitutional basis: extends Article XXXIII (no irreversible
research action on unresolved evidence — a duplicate expensive
computation is exactly that) and Article XII (provenance custody —
the operation identity is the provenance of the spend).

## Article LXXIX — Fail Closed, Progress Open

The system must fail closed with respect to truth, but remain open
with respect to recoverable execution.

If Toscanini cannot determine whether a provider completed: do not
claim completion. But also: do not throw away the run. Keep `UNKNOWN`
and recover observation.

Constitutional basis: extends Article V (fail closed, but do not
become a universal rejector) from the epistemic plane to the execution
plane: truth is never fabricated (fail closed), and recoverable work
is never destroyed (progress open). The `UNKNOWN` that survives is the
same `UNKNOWN` Article XXV protects at the reasoning layer.

---

## THE PROHIBITIONS (operator directives, already enforced or now pinned)

1. **No `ENGINE_OPERATOR_KEY`.** Already enforced by
   `tests/test_r463_no_operator_key.py` (its absence from the
   production tree is pinned); this amendment re-asserts it as
   operator law.
2. **No local background process as a prerequisite for the AI run.**
   The run path is server-side from `POST /api/run` to the durable
   branch; observer processes are optional.
3. **No classification of local process death as remote AI failure.**
   The typed vocabulary of Article LXXVI makes the collapse
   unrepresentable.
4. **No manual foreground polling as the permanent architecture.**
   It is a temporary diagnostic protocol (this round's own drivers
   carry the label).

## THE ACCEPTANCE CRITERION

The permanent acceptance criterion is **observer-independent
execution**: sandbox death, browser disconnect, polling interruption,
or tool timeout cannot destroy or invalidate a server-side AI run. A
fresh E2E test must demonstrate: start run → intentionally lose local
observer → remote work continues → reconnect → recover run → complete
→ canonical artifacts available. The problem is not solved by
successful manual polling.

## PRIORITY ORDER (operator directive)

**P0 — Durable end-to-end execution** before **P1 — browser showcase
matrix**. The real target: Claude-like simplicity at the surface +
durable autonomous execution underneath.
