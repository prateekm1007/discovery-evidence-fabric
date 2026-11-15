# Coordination protocol — parallel builders (constitution v3.1.0, Art. 29)

Owner decision on F25 (seven measured duplicate-run instances): both builder
sessions run CONCURRENTLY — they catch each other's errors — and no duplicate
entries. The mechanism below is structural: it stops the second session from
RE-EXECUTING and makes it the VERIFIER of the first, using the git push
itself as the lock. Parallelism is kept; duplication is forbidden.

## 1. Identity (Art. 29(a))

- Register a stable `session_id` in `eval/work_claims.json` (`sessions{}`)
  on your first push; never reuse another session's id.
- Every commit carries trailers, as the final paragraph:

      Session: <session_id>
      Work-Id: <work_id>

- Attribution cites claim ids and commit hashes, never free-text labels
  (the R17 labeling disclosure is the cautionary precedent).

## 2. Claim-before-work (Art. 29(b))

- Before starting ANY work item, push a claim into `eval/work_claims.json`
  (`claims[]`):

      {"claim_id": "c-NNN", "work_id": "<stable work id>",
       "session_id": "<your session id>", "role": "EXECUTOR",
       "kind": "measurement|one_shot|task",
       "base_sha": "<sha the claim is based on>",
       "claimed_at": "<ISO-8601 UTC>", "lease_expiry": "<ISO-8601 UTC>",
       "status": "OPEN", "takes_over": null,
       "artifact_paths": ["eval/..."],
       "notes": "what will be produced, and where"}

- The push is the mutex: the first pusher owns the item. The loser fetches,
  sees the claim, becomes VERIFIER for that item, and executes a DIFFERENT
  unclaimed item. The race window shrinks from ~30 minutes to milliseconds.

## 3. One executor, one verifier (Art. 29(c))

- Exactly one EXECUTOR per work item: one generation for sealed/one-shot
  work, one run per quota-consuming measurement.
- The VERIFIER never re-runs. It independently recomputes from the
  executor's committed bytes (Art. 13), checks pre-registration / contract /
  census / CI, and files a typed verification record: a `role: "VERIFIER"`
  claim on the same `work_id` whose notes name what was recomputed and from
  which shas.
- A DONE `measurement` or `one_shot` claim without a VERIFIER record fails
  the queue CI (this is the error-catching made structural).

## 4. Lease and takeover (Art. 29(d))

- Stage pushes (Art. 18) are heartbeats: every push that advances the work
  item refreshes `lease_expiry` on its OPEN claim (the stage commit carries
  the updated registry).
- If a claim's lease expires with no stage push (e.g. the sandbox reaped the
  process group), the other session claims takeover: a new EXECUTOR claim
  with `takes_over: "<dead claim_id>"` referencing the expired lease, and
  resumes from the committed PARTIAL rows. No double-run.

## 5. Canonical-path ownership (Art. 29(e))

- Write only paths listed in your claim's `artifact_paths`; one canonical
  artifact per `work_id` (Art. 16).
- Same-`work_id` non-fast-forward => stand down to verifier. NEVER rebase a
  duplicate. Rebase only disjoint work. Diff-against-remote before every
  push (`git fetch` + `git rev-list --left-right --count HEAD...origin/<br>`).

## 6. Registry schema (`work-claims/v1`)

- `eval/work_claims.json` = `{"schema": "work-claims/v1", "sessions": {},
  "claims": []}` at minimum. An EMPTY registry (identity registered, zero
  claims) is the lawful adoption state and passes CI.
- CI: `tests/test_article29_parallel_coordination.py` gates every queue push:
  registry schema valid (and the literal empty registry passes); no two live
  EXECUTOR claims per work_id (a second executor must reference the dead
  lease it takes over); one-shot work has exactly one generation (a single
  non-branching takeover chain); each DONE measurement carries a VERIFIER
  record; every post-adoption commit carries `Session:`/`Work-Id:` trailers;
  every canonical-measurement commit matches an EXECUTOR claim in its own
  registry snapshot (claim-before-work is enforced, not asked for).

## 7. Trigger — F25's seven measured instances

duplicate r11 battery run; duplicate Art. 19 wiring; duplicate holdout
generation; duplicate crowllm integration; census mis-type; rebase clobber;
audit-snapshot race. Art. 29 exists so none of these classes can recur.
