# Constitutional Amendment — Article LXXIV
## Observer-Independent Durable Execution (the SANDBOX / EXECUTION DURABILITY PRINCIPLES)

**Round:** R484
**Ratified:** 2026-09-17
**Amends:** Constitution v2.5.0 → v2.6.0
**Sponsor:** Operator directive, 2026-09-17 (verbatim below)

---

## The operator's directive (verbatim)

> Add more principles to the constitution: Yes. This is a **serious architectural issue**, because Toscanini is supposed to be an end-to-end AI. If the orchestration depends on a local sandbox process remaining alive while the external AI computation continues, the execution model is fragile.
>
> The important pattern is consistent: **long-running work should be represented as a durable job, not as a long-lived foreground tool call**.
>
> So I would **not accept "manual foreground polling" as the permanent architecture**. It is a temporary diagnostic protocol.
>
> ### NEW — SANDBOX / EXECUTION DURABILITY PRINCIPLES
>
> **A. Execution is not observation** — The lifetime of a caller, tool invocation, terminal session, polling process, or sandbox MUST NOT define the lifetime of an AI run. A caller disappearing does not mean the run failed. A polling process disappearing does not mean the run failed. A sandbox being reaped does not mean the remote computation failed.
>
> **B. Remote work must be durable** — Any operation capable of exceeding the execution environment's foreground/tool-call lifetime MUST be represented as a durable server-side job with a stable run identity. The durable identity must survive: polling termination, browser refresh, worker restart, sandbox destruction, network interruption, tool timeout.
>
> **C. Observation failure ≠ execution failure** — Failure to observe a running operation MUST NOT be classified as failure of the operation itself. Therefore: `POLL_TIMEOUT` is not `RUN_FAILED`; `SANDBOX_REAPED` is not `REMOTE_JOB_FAILED`; `NO_LOCAL_PROCESS` is not `NO_SERVER_WORK`.
>
> **D. Never depend on a local background process for canonical state** — A local background process MAY assist observation, diagnostics, or development, but MUST NOT be the sole authority for execution state, completion, artifacts, or provenance. Canonical state belongs server-side.
>
> **E. Every long-running operation has a durable state machine** — At minimum: `QUEUED / STARTING / RUNNING / WAITING_EXTERNAL / COMPLETED / FAILED / CANCELLED / EXPIRED / UNKNOWN`. Critically: `UNKNOWN` must remain distinct from `FAILED`. This directly reinforces the existing Article XXV doctrine that unknown remains unknown.
>
> **F. Polling is an observation mechanism, not an execution mechanism** — Polling MUST only observe durable state. Polling MUST NOT be required to keep computation alive.
>
> **G. Reconnection is normal** — Any client must be able to disconnect and later reconnect to the same run without loss of canonical execution state. This should become an explicit E2E test.
>
> **H. Completion must be independently observable** — A completed run MUST be recoverable from durable server-side state without relying on the process that initiated or polled the run. The UI can disappear for 20 minutes and come back to: Discovery still running → 63% / current stage → completed artifacts. Rather than: Connection lost → start again.
>
> **I. Provider execution and sandbox execution are separate boundaries** — Toscanini MUST distinguish provider execution state from local execution environment state. `LOCAL_SANDBOX = REAPED / REMOTE_PROVIDER = RUNNING` is a valid state. `LOCAL_SANDBOX = ALIVE / REMOTE_PROVIDER = FAILED` is a valid state. They must never be collapsed into one `failed` boolean.
>
> **J. Timeout semantics must be typed** — Do not have one generic timeout. Use distinct categories such as: `TOOL_TIMEOUT / SANDBOX_TIMEOUT / LOCAL_PROCESS_REAPED / REMOTE_PROVIDER_TIMEOUT / REMOTE_PROVIDER_UNAVAILABLE / POLL_TIMEOUT / POLL_INTERRUPTED / JOB_EXPIRED / JOB_FAILED / JOB_UNKNOWN`. The distinction matters scientifically and operationally.
>
> **K. Long-running work must be background-first** — If expected runtime exceeds the reliable foreground execution budget, Toscanini MUST launch durable asynchronous work and return a run/job identity rather than holding a foreground invocation open.
>
> **L. Retry must be idempotent** — A retry after timeout, disconnect, or lost observation MUST NOT silently duplicate an external AI operation or corrupt canonical state. Every externally meaningful operation should therefore have an identity such as: `run_id / operation_id / attempt_id / provider / model / model_revision / request_hash`. A retry should be able to answer: "Did this operation actually execute?" before launching another one.
>
> **M. Never restart merely because observation was lost** — Toscanini MUST NOT restart an expensive AI computation solely because the observer lost contact with it. First: LOOK UP DURABLE RUN → IS IT RUNNING? → IS IT COMPLETE? → IS IT FAILED? → ONLY THEN CONSIDER RETRY. This will save enormous model/API waste.
>
> ### One principle especially prominent
>
> **ARTICLE — FAIL CLOSED, PROGRESS OPEN**: The system must fail closed with respect to truth, but remain open with respect to recoverable execution. If Toscanini cannot determine whether the remote computation completed: **do not claim completion.** But also: **do not throw away the run.** Keep `UNKNOWN` and recover observation. That is much stronger than simply "retry on timeout."
>
> The permanent acceptance criterion is **observer-independent execution**.
>
> (Full directive context, including the external references the operator cited — HF Jobs, agent-sandbox designs, the agent/tool-boundary literature — is preserved in the round records; the normative content is the principles above.)

### The coders' marching orders (verbatim, normative)

> Read the Constitution before touching this. The Z.ai sandbox timing problem is now treated as an execution-architecture issue, not merely a polling inconvenience.
> Do not introduce `ENGINE_OPERATOR_KEY`. Do not make local background processes a prerequisite for the AI run. Do not classify local process death as remote AI failure. Do not rely on manual foreground polling as the permanent solution.
> First establish the actual lifecycle of attempt 5 and produce evidence showing: `local observer state → remote job state → provider state → canonical Toscanini run state`.
> Then implement the minimum durable execution contract required so that: **sandbox death, browser disconnect, polling interruption, or tool timeout cannot destroy or invalidate a server-side AI run.**
> A fresh E2E test must demonstrate: **start run → intentionally lose local observer → remote work continues → reconnect → recover run → complete → canonical artifacts available.**
> Do not claim the problem solved from successful manual polling. The permanent acceptance criterion is **observer-independent execution**.

---

## Ratified article language (verbatim in this document AND the Constitution body)

Execution is not observation. The lifetime of a caller, tool invocation, terminal session, polling process, or sandbox MUST NOT define the lifetime of an AI run: a caller disappearing does not mean the run failed, a polling process disappearing does not mean the run failed, and a sandbox being reaped does not mean the remote computation failed. Remote work must be durable: any operation capable of exceeding the execution environment's foreground or tool-call lifetime MUST be represented as a durable server-side job with a stable run identity that survives polling termination, browser refresh, worker restart, sandbox destruction, network interruption, and tool timeout; canonical state belongs server-side, and a local background process MAY assist observation, diagnostics, or development but MUST NOT be the sole authority for execution state, completion, artifacts, or provenance. Observation failure is not execution failure: failure to observe a running operation MUST NOT be classified as failure of the operation itself — POLL_TIMEOUT is not RUN_FAILED, SANDBOX_REAPED is not REMOTE_JOB_FAILED, and NO_LOCAL_PROCESS is not NO_SERVER_WORK. Every long-running operation has a durable state machine — at minimum QUEUED, STARTING, RUNNING, WAITING_EXTERNAL, COMPLETED, FAILED, CANCELLED, EXPIRED, UNKNOWN — and UNKNOWN must remain distinct from FAILED (Article XXV: unknown remains unknown). Polling is an observation mechanism, not an execution mechanism: polling MUST only observe durable state and MUST NOT be required to keep computation alive. Reconnection is normal: any client must be able to disconnect and later reconnect to the same run without loss of canonical execution state, and completion must be independently observable — a completed run MUST be recoverable from durable server-side state without relying on the process that initiated or polled the run. Provider execution and sandbox execution are separate boundaries: LOCAL_SANDBOX = REAPED with REMOTE_PROVIDER = RUNNING is a valid state, and the two domains must never be collapsed into one failed boolean. Timeout semantics must be typed — TOOL_TIMEOUT, SANDBOX_TIMEOUT, LOCAL_PROCESS_REAPED, REMOTE_PROVIDER_TIMEOUT, REMOTE_PROVIDER_UNAVAILABLE, POLL_TIMEOUT, POLL_INTERRUPTED, JOB_EXPIRED, JOB_FAILED, JOB_UNKNOWN — distinct categories, never one generic timeout. Long-running work is background-first: if expected runtime exceeds the reliable foreground execution budget, the machine MUST launch durable asynchronous work and return a run or job identity rather than holding a foreground invocation open. Retry must be idempotent: a retry after timeout, disconnect, or lost observation MUST NOT silently duplicate an externally meaningful operation or corrupt canonical state, and every such operation carries an identity — run_id, operation_id, attempt_id, provider, model, model_revision, request_hash — sufficient to answer "did this operation actually execute?" before launching another one. The machine MUST NOT restart an expensive AI computation solely because the observer lost contact with it: first look up the durable run (is it running? complete? failed?) and only then consider retry. FAIL CLOSED, PROGRESS OPEN: the system fails closed with respect to truth but remains open with respect to recoverable execution — if the machine cannot determine whether a remote computation completed, it MUST NOT claim completion, and it MUST NOT throw the run away: the state stays UNKNOWN and observation remains recoverable. The permanent acceptance criterion for this article is observer-independent execution, demonstrated by the standing E2E contract: start a run, intentionally lose the local observer, the remote work continues, a client reconnects, recovers the run, and the canonical artifacts are available.

---

## Implementation obligations (this round)

1. `toscanini/execution_states.py` — the canonical durable state machine (the nine states) + the observation-domain vocabulary, with the mapping from the store's operational statuses; UNKNOWN distinct from FAILED by construction (tested).
2. The product surface (`toscanini/user_state.py`): a stuck-but-maybe-alive run renders as UNKNOWN-class, never as FAILED — one targeted change + test.
3. `tests/test_r484_observer_independent_e2e.py` — the standing E2E reconnection contract: start run → kill the observer → remote work continues → reconnect → recover state + artifacts.
4. The attempt-5 record (`R484/LOOP_CLOSURE.json`) carries the measured four-domain lifecycle chain as the article's first live proof case.
