# Auditor Blind-Spot Register v1

This register records places where previous audits were empirically blindsided. It is a living control document for future audits. Each entry must be updated when new evidence reveals a failure mode not previously anticipated.

## BS-001 — Remote state drift

**Observed:** Local work and live remote repository state diverged; a local V2 branch was stale by dozens of commits while main contained missing work.

**Failure mode:** Auditor trusted local/hand-off state and could have misclassified completed work as missing or vice versa.

**Principle:** Verify live default branch, branch topology, commit SHA, compare base, and relevant PRs before assessing completion.

**Required check:** `HEAD`, `origin/main`, active feature branches, PR state, and deployment SHA.

## BS-002 — Deployment branch/commit mismatch

**Observed:** A deployment served an accepted branch SHA while main had a rebased equivalent with a different SHA; the operator-declared `ENGINE_COMMIT` pin temporarily remained stale, making drift RED.

**Failure mode:** "Deployed" was treated as synonymous with "current main."

**Principle:** Deployment identity is a tuple, not a label: repository commit, build artifact, running commit, health-reported commit, and operator expectation must agree according to the release protocol.

**Required check:** Compare all five identities before calling a release complete.

## BS-003 — Built but not wired

**Observed:** A bridge could generate real 3D and packages from captured run state, but fresh production runs never invoked the engineering/CAD/package stage.

**Failure mode:** A passing bridge test was mistaken for an end-to-end product capability.

**Principle:** A subsystem is incomplete until a fresh ordinary user path exercises it automatically.

## BS-004 — Captured-run success masquerading as product success

**Observed:** Real historical runs had 3D and packages while fresh runs did not.

**Failure mode:** Existing showcase artifacts created a false impression that current discovery runs produced the same artifacts.

**Principle:** Audit at least one fresh run in addition to historical/released examples whenever the claim concerns current product behavior.

## BS-005 — API existence mistaken for semantic connectivity

**Observed:** CIO and model/package endpoints existed, but fresh-run CIO had no geometry and no package because the upstream stage never executed.

**Failure mode:** Endpoint 200/202 existence was treated as proof of pipeline integration.

**Principle:** Follow one object end-to-end across state creation, persistence, transformation, endpoint response, and frontend rendering.

## BS-006 — Honest absence masking an engineering bug

**Observed:** The UI correctly said there was "No 3D" because no geometry existed, but the underlying invention already contained enough structured information for a visual artifact.

**Failure mode:** Epistemic honesty was mistaken for acceptable product behavior.

**Principle:** An honest missing artifact can still be an unacceptable engineering failure. Audit whether recovery was possible and required.

## BS-007 — Engineering specification without geometry conversion

**Observed:** Rich subsystem/engineering data existed, yet nothing translated it into 3D.

**Failure mode:** The existence of an engineering specification was treated as if it implied an engineering artifact.

**Principle:** Audit explicit transformations: invention → engineering representation → geometry → measurement → asset.

## BS-008 — Good package quality hidden by poor presentation

**Observed:** Released P-07/P-11 style artifacts were strong, but the fresh-run product rendered a long machine-like report and no visual artifact.

**Failure mode:** Package correctness and product UX were assessed together rather than independently.

**Principle:** Audit package substance and user-facing presentation as separate quality dimensions, then audit their join.

## BS-009 — Raw machine state leaking into human UX

**Observed:** JSON-like mechanism/hypothesis data, route details, scores, and audit state appeared in the normal product experience.

**Failure mode:** Backend truthfulness was achieved at the cost of usability and narrative clarity.

**Principle:** Preserve raw artifacts for audit/debugging, but render human-readable technical prose in the primary interface.

## BS-010 — Rejection-state vocabulary hijacking the product mission

**Observed:** The product displayed `NO DEFENSIBLE INVENTION SURVIVED THIS RUN` even though the intended machine was supposed to evolve challenged architectures.

**Failure mode:** Verification/attack stages accidentally became the creative terminal state.

**Principle:** Verification constrains maturity and action; it must not silently redefine the product as a rejection engine. Challenge → diagnosis → evolution must remain distinct from terminal failure.

## BS-011 — Uncalibrated attacker acting as an absolute judge

**Observed:** The product attacker measured TPR 1.00 and FPR 1.00 on a sealed 40-case corpus: a universal killer.

**Failure mode:** Substantive objections were useful, but terminal KILL verdicts carried no discriminative information.

**Principle:** Objection content and verdict authority are separate. Until calibration is earned, preserve the objection and escalate rather than treating KILL as authoritative.

## BS-012 — Attacker authority multiplied through evolution

**Observed:** In R416, uncalibrated attack verdicts could have been propagated into successive generations, multiplying a flawed judgment 3–5x per run.

**Failure mode:** A weak terminal instrument contaminated the evolutionary search path.

**Principle:** The reliability of a judge must be assessed before its decisions are allowed to drive recursive search.

## BS-013 — Retrieval failure misread as evidence absence

**Observed:** OpenAlex was rate-limited during R412 V3; source unavailability initially produced an apparent empty quantitative pool.

**Failure mode:** Transport failure could have been interpreted as lack of frontier evidence.

**Principle:** RATE_LIMITED/UNAVAILABLE/EMPTY are distinct epistemic states. Source substitution must preserve provenance.

## BS-014 — Parser information loss mistaken for source weakness

**Observed:** Canonicalization discarded years/metadata when shorter abstracts replaced richer metadata records; 388/483 records lost year data in one measurement.

**Failure mode:** An upstream/source-quality diagnosis would have been false because the bug was local information loss.

**Principle:** Audit every transformation between source retrieval and evidence pool for lossy behavior.

## BS-015 — Query-form bias

**Observed:** A query-form change materially altered numeric-bearing evidence density; a comparison-targeted form improved the dev A/B directionally.

**Failure mode:** Retrieval quality was treated as source capability rather than query-design capability.

**Principle:** Query formulation is an experimental variable. Negative knowledge about query forms must change future search.

## BS-016 — Benchmark circularity

**Observed:** The existing V3 benchmark used an acquisition form that made it unsafe to claim independent improvement using that same form; a blind second corpus was required.

**Failure mode:** A benchmark could be "passed" by optimizing the acquisition process toward the benchmark itself.

**Principle:** When a benchmark instrument becomes part of the intervention, require an independent blind re-verification path.

## BS-017 — Demo artifacts versus generated artifacts

**Observed:** The released catalog had high-quality 3D packages while a fresh run had none.

**Failure mode:** Visual catalog quality made the current generation pipeline appear more capable than it was.

**Principle:** Label released/reference artifacts separately from artifacts produced by the current run.

## BS-018 — User-visible state stale while backend state advances

**Observed:** A run page hung on "Loading run…" because the browser lost the owner cookie while backend stage data continued updating.

**Failure mode:** A session/authorization continuity bug looked like a stalled discovery process.

**Principle:** Long-running runs must be tested across refresh, new-tab, reconnect, and cookie/session rotation paths.

## BS-019 — Stale metadata mistaken for current truth

**Observed:** README and handoff documents retained old Constitution versions even though the canonical Constitution had advanced.

**Failure mode:** Documentation could silently override actual authority in a handoff.

**Principle:** Version/hash-bind governance and use the canonical source, not narrative documents.

## BS-020 — Environment defect mistaken for product defect

**Observed:** pytest failures were caused by stale `/tmp` ownership rather than code regression.

**Failure mode:** The auditor could have escalated a false regression.

**Principle:** Classify failures into code, environment, dependency, network, credentials, and data before interpreting them.

## BS-021 — Local security problem hidden inside useful work

**Observed:** The bridge repo contained a live session cookie and `.env` in git history before push; the coder detected and purged them.

**Failure mode:** Audit artifacts could have turned into credential leakage.

**Principle:** Security and provenance are inseparable. Scan repositories and generated artifacts for credentials before publishing.

## BS-022 — Package audience confusion

**Observed:** A technically valid counsel evidence ZIP was mistaken for the buyer-facing technology package.

**Failure mode:** A package optimized for legal evidence was judged as a commercial/engineering product.

**Principle:** Separate buyer package, counsel package, engineering package, and raw audit artifacts by audience and purpose.

## BS-023 — Invention drift from the user's actual objective

**Observed:** The solar query generated a PV panel + heating element/cooking architecture despite the user asking for maximal PV efficiency.

**Failure mode:** Retrieval of an available related mechanism redirected the invention toward a tangential application.

**Principle:** Maintain a problem-objective fidelity test: every candidate must explicitly map to the user's requested outcome and target bottleneck.

## BS-024 — Obvious combination mistaken for causal invention

**Observed:** Adding an Arduino/adaptive-control layer was presented as a causal change even though the underlying architecture remained near-conventional.

**Failure mode:** Novel-sounding language substituted for a genuine new interaction, regime, or architecture.

**Principle:** Require explicit causal delta, new interaction, new operating regime, or demonstrably new system architecture before treating a transfer as meaningful invention progress.

## BS-025 — Physics visualization mistaken for physics validation

**Observed:** The proposed UX risked allowing Blender/3D to imply physical validation.

**Failure mode:** A visual artifact could be mistaken for evidence that a physical law was satisfied.

**Principle:** Visualization is downstream of engineering/simulation evidence. Blender is never a physics authority.

## BS-026 — Multiple-solver accumulation before coverage measurement

**Observed:** A proposal to add Blender + OpenFOAM + FEM + SOFA + Chrono + EM + optimization would have created a large unearned stack.

**Failure mode:** Tool accumulation replaced measured prioritization.

**Principle:** Build a Physics Coverage Registry first, then add one solver at a time based on information gain divided by integration cost.

## BS-027 — Bridge repository becoming architectural fragmentation

**Observed:** The 3D/package bridge solved a real gap but initially existed as a separate repository/module.

**Failure mode:** Useful infrastructure could remain an island and never become the production path.

**Principle:** Every standalone subsystem has an explicit integration deadline and production acceptance test.

## BS-028 — Model availability assumed static

**Observed:** A 410 transport failure came from an unavailable/retired route while later NVIDIA health showed 19 healthy models and OpenRouter was independently degraded.

**Failure mode:** Static model priority lists became stale.

**Principle:** Model selection must use current and historical availability telemetry with automatic fallback.

## BS-029 — One provider failure killing the whole product

**Observed:** OpenRouter/LLM transport failure previously surfaced as a user-facing dead end.

**Failure mode:** Infrastructure topology leaked into the product's primary outcome.

**Principle:** Provider failure must degrade routing, not terminate discovery, until all viable routes are exhausted.

## BS-030 — Tests proving a narrow path while the user path fails

**Observed:** Bridge unit tests and engineering parity tests passed while the live fresh-run path still lacked 3D.

**Failure mode:** High test counts created false confidence.

**Principle:** Every major feature needs both deterministic unit/regression tests and a fresh public-path acceptance test.

## BS-031 — Artifact parity proved with the wrong artifact class

**Observed:** P-07 engineering output matched a released STL byte-for-byte, but the fresh solar invention was actually SYSTEM_3D/conceptual at the time.

**Failure mode:** A strong parity result for a reference object could obscure that the new invention had different geometry maturity.

**Principle:** Verify artifact claims against the exact current invention class, not merely against a known-good reference.

## BS-032 — A credible package can still solve the wrong problem

**Observed:** The generated package was internally coherent about solar-powered heating while the user's objective concerned PV efficiency.

**Failure mode:** Internal consistency was mistaken for problem relevance.

**Principle:** Buyer usefulness requires problem fidelity before engineering polish.

## BS-033 — Auditor tool blind spots

**Observed:** Web fetchers failed on the Render app while browser screenshots showed it functioning; GitHub private repository access also depended on available credentials/tools.

**Failure mode:** Tool inability could look like application failure or application success.

**Principle:** For each audit, explicitly record which tools can and cannot observe the target. Use multiple observation channels when practical: browser, API, repository, artifact, and deployment identity.

## BS-034 — Self-reported completion bias

**Observed:** Coder reports sometimes used phrases like "complete," "all green," or "world-class" while live product behavior still had important gaps.

**Failure mode:** Persuasive narrative substituted for independent evidence.

**Principle:** Treat coder status as a hypothesis requiring verification.

## BS-035 — Audit tunnel vision

**Observed:** Successive audits concentrated on the currently known blocker and nearly missed adjacent failure classes such as UI presentation, fresh-run artifact generation, package audience, or provider resilience.

**Failure mode:** Fixing the prior audit's checklist became the objective instead of auditing the whole product.

**Principle:** Every round must re-scan the full end-to-end chain and only then descend into the currently dominant blocker.

## BS-036 — Recursive governance drift

**Observed:** The project accumulated new rules, handoffs, reports, and directives with overlapping terminology and stale references.

**Failure mode:** Governance itself could become fragmented and contradictory.

**Principle:** Governance artifacts need versions, hashes, authority order, and an explicit supersession rule.

## BS-037 — Auditor forgetting project state and direction

**Observed:** Across long-running sessions, the auditor can lose track of which architectural decisions are settled, which directives are already completed, which blockers remain open, which repository/deployment is authoritative, and what the current product objective is. This creates a specific risk of giving the coder obsolete instructions, re-opening rejected approaches, duplicating completed work, or accidentally reversing direction even when the individual facts used in the new audit are correct.

**Failure mode:** The auditor behaves as though each audit starts from a blank slate, producing entropy through loss of continuity rather than through incorrect technical reasoning.

**Principle:** Maintain an explicit remembered-state/direction checkpoint across audits, refresh it against authoritative live state before each substantive audit, and distinguish continuity memory from evidence. Memory is a navigation aid; it is never proof.

**Required check:** Before prescribing new work, reconstruct current mission, authoritative repositories/commits, deployment identity, current production path, settled architectural decisions, standing blockers, latest accepted directive, known rejected approaches, and last verified end-to-end behavior. Do not repeat or reverse a prior decision without new evidence.

## BS-038 — Auditing only the named call sites misses parallel state-derivation paths

**Observed:** Auditing that every `public_session_view(...)` call site uses the refreshed canonical state projection is not sufficient, because a terminal stream (SSE) or another customer-visible API path can call `user_state_view(...)` directly on a stale record, bypassing the one seam the audit checked.

**Failure mode:** A finished/discovery-state inconsistency survives on exactly the paths the audit instrument did not enumerate; "all audited call sites are correct" is reported as proof while an un-audited sibling path still derives the flag from a retired or stale rule.

**Principle:** Audit the DERIVATION POINTS of a state flag, not the call sites of one named helper. Every path that can surface the flag (sync API, SSE terminal events, background workers, read-time recompute) must resolve through the single authoritative refresh seam; a structural check (e.g., no bare `user_state_view(` surviving in the serving layer) beats a call-site inventory.

## BS-039 — Commit message claims a production change the commit does not contain

**Observed:** A round's commit message described a production-file change (the R545 typed-terminal rule in `user_state.py`), the modified test asserted that new behavior and passed locally, and a closure narrative was written — yet the production file's blob in that commit was byte-identical to the pre-change tree because the implementation edit was never staged. The live/deployed tree therefore did NOT contain the fix the message claimed, and a modified test could assert behavior the committed tree does not implement (the test passed only against the uncommitted working tree).

**Failure mode:** "The commit message says the code was changed + the test passed locally" was treated as closure proof while the actual production file was absent from the commit. Deployment then shipped a SHA whose real bytes still carried the defect, and the "closed" defect resurfaced in production.

**Principle:** Commit content, test expectations, deployment SHA, and live behavior must be independently reconciled before closure. A commit message is a claim, not evidence: verify the named production file's blob actually changed in the commit (`git show <sha> -- <file>` must show the diff), run the regression suite against the committed tree (not the dirty working tree), and only then prove the exact deployed SHA serves the fixed bytes.

**Required check:** For every round claiming a production fix: (1) `git show <commit> -- <named production file>` shows the change; (2) the suite is re-run from a clean checkout of that exact commit; (3) the deployed `/api/version` SHA matches the tested commit; (4) a fresh production request demonstrates the defect is gone.

## BS-040 — Regression test exercises a semantically similar terminal shape while missing the actual production terminal shape

**Observed:** The R545 typed-terminal regression pinned `status=COMPLETE, final_status=RUN_BLOCKED_TRANSPORT` — an equivalent-looking fixture. The actual worker's transport-exhausted branch writes the typed terminal into `status` only (`store.update_session(session_id, status="RUN_BLOCKED_TRANSPORT", error=...)` — no `final_status` is recorded on that branch, and no run-dir artifacts exist pre-pipeline). The R545 rule keyed its typed-terminal answer on `final_status + status in (<tuple>)`, so the real producer shape fell through to the legacy key-prefix derivation and the customer-facing finished flag came out True on an infrastructure terminal (the pre-retrieval capability branch's `RUN_BLOCKED_CAPABILITY` shape — status AND final_status — was also outside the rule's status tuple).

**Failure mode:** "The regression test passes on the shape I constructed" was treated as closure proof for "the production shape is handled." The test and the producer diverged on which field carries the typed state, and both directions (the bare transport shape; the capability shape with a status outside the tuple) silently regressed to finished=True on an infrastructure terminal.

**Principle:** Test the EXACT producer shape emitted by the production state machine, not merely an equivalent-looking fixture. A terminal-shape regression must be constructed from the state machine's own write site (the worker's `update_session` fields for each terminal branch), and the tested status/vocabulary must be DERIVED from the canonical execution-state mapping (e.g. `execution_states.py`), never re-invented in the test. The producer-shape test suite (R546) pins: bare `status=RUN_BLOCKED_TRANSPORT` with no final_status, the `RUN_BLOCKED_CAPABILITY` branch (status + final_status), and the full terminal-state matrix including the opposite direction (a recorded authoritative false outranks a positive-looking COMPLETED_* key).

**Required check:** For every terminal-shape regression: (1) read the worker's terminal write site and mirror its exact fields; (2) derive the tested classes from the canonical status→execution-state mapping; (3) measure the three projections (state key, flag helper, view finished) on the mirrored record; (4) include both directions — the infrastructure terminal must not become a completed discovery, AND a positive-looking key with a recorded authoritative false must not regain finished=True.

**BS-039 reminder (permanent memory):** commit-message claims do not prove that the named production bytes were actually committed — verify the blob, re-run the suite from the clean committed tree, and prove the deployed SHA serves the fixed bytes.

## BS-041 — A 404 alone does not identify which owner-capability link failed

**Observed:** The fresh production run's `POST /api/run/{id}/answer` returned 404. The initial narrative attributed it to "the serving cookie name differs from the stored owner_key" without tracing the actual capability lineage: the owner key is issued at run creation, returned in the API response, persisted in the browser's `localStorage["tosca_owner_key"]`, attached to fetch requests as the `X-Tosca-Owner` header (REST) or baked into the `?owner=` query param (SSE / direct downloads), resolved server-side by `_owner_key()` (cookie → header → issued), and matched against the session's stored `owner_key` by strict equality in `session_access()`. The 404 could have come from any of: the header not being sent (browser cleared localStorage), the header not reaching the server (proxy stripping it), the cookie-only path being selected instead of the header path, the session owner_key being absent or mismatched, or the route itself not being registered.

**Failure mode:** "A 404 means ownership is broken" substitutes for the actual causal chain. Without instrumenting each link with typed, non-secret evidence (fingerprint, presence/absence, source, match boolean), the diagnosis is a guess, and the fix may target the wrong link.

**Principle:** Capability transport must be traced from issuance → persistence → transport → server resolution → authorization → worker continuation; a 404 alone does not identify which link failed. Every link is instrumented with typed, non-secret evidence (SHA-256 fingerprint, length, source class, match boolean — never the token value, Art. LXXVI / BS-021).

**Required check:** For every owner-scoping 404: (1) verify the session record's `owner_key` is present (fingerprint); (2) verify the API response returned the `owner_key` to the client; (3) verify the client persists it (localStorage key name); (4) verify the transport (REST header vs SSE query param) carries it; (5) verify the server's `_owner_key()` resolution source (cookie / header / query / issued); (6) verify the strict-equality match; (7) classify the 404 into exactly one cause from the typed vocabulary (`INCOMING_CAPABILITY_ABSENT`, `RESOLVER_ISSUED_FALLBACK`, `COOKIE_HEADER_DISAGREEMENT`, `SESSION_OWNER_MISMATCH`, `SESSION_NO_OWNER_RECORD`, `ROUTE_NOT_REGISTERED`).

## BS-042 — A closure proof artifact captured at a deployed SHA that is an ancestor of origin/main is stale evidence, not live proof

**Observed:** R546's `fresh_proof_record.json` recorded `finished=true` on a `COMPLETE + MECHANISM_STARVED + completion_states={}` terminal. The record was captured against production SHA `b4541e880`, but by the time the closure was written, `origin/main` had advanced to `09effc442` (two commits ahead: the owner-capability transport + the live-record commit). The committed `user_state.py` at `09effc442` correctly answers `finished=false` for that exact shape (verified locally), yet the closure cited the stale `finished=true` record as live projection proof. The artifact and the code it was meant to prove were not on the same SHA, and nobody reconciled them. A SECOND occurrence of the same class was measured on the `3ee39cc1d` deployment in R547: a session terminal that had been computed on an EARLIER tree kept serving the stale `finished=true` snapshot even though the deployed `user_state.py` re-derives `finished=false` from the nested `final_state.completion_states` — the served payload and the executing source disagreed, and the reconciliation required recomputing the view from the SAME served record with the committed source (Art. XXII: never assume the committed source is the executing source; measure both answers on the same record).

**Failure mode:** "The proof artifact exists and says the live projection works" substitutes for "the proof artifact was captured against the exact SHA that is currently at origin/main and currently deployed." A closure that (a) deploys, (b) commits a proof artifact about that deployment, and then (c) lets origin/main advance past the deployed SHA before writing the closure — cites a record whose SHA no longer matches the live/origin identity. The artifact is historical evidence about an earlier tree, and using it as live projection proof is a BS-039/Article XXII violation (a summary/record outranking the underlying current state).

**Principle:** A closure's proof artifacts are only live evidence when `artifact.production_sha == origin/main at closure == deployed /api/version`. If origin/main advances after the proof was captured, the proof is reclassified as historical/stale and re-captured against the new final SHA — it is never silently reused. The deployment order is fixed: implementation → tests → ALL closure/proof artifacts generated → final commit → push origin/main → deploy EXACT final origin/main → verify /api/version + /api/health → fresh production test → closure. No commit is made after the final deployment without redeploying that new SHA.

**Required check:** For every closure claiming live production proof: (1) record the exact `origin/main` SHA at the moment the closure is written; (2) verify each cited proof artifact's `production_sha` equals that SHA; (3) if any artifact's SHA is an ancestor of (not equal to) the current origin/main, re-capture it against the current SHA before citing it; (4) the deployed `/api/version` engine_commit must equal the current origin/main exactly, and the closure must be written only after that equality holds.

## BS-044 — A deploy's version endpoint reports the intended commit, not the executing source (stale build layer)

**Observed:** The R547 deploy script staged commit `7edb871a1` via `git archive` → `upload_folder` → `restart_space()`, then polled `/api/version` until `engine_commit == 7edb871a1` and declared exact-SHA convergence. But a fresh production run on that deploy still served `user_state_view.finished=true` for the `COMPLETE + MECHANISM_STARVED + nested FINISHED_DISCOVERY=false` shape — a shape the deployed tree's `user_state.py` answers `false`. The committed source and the executed source were on different trees.

**Failure mode:** `/api/version`'s `engine_commit` is a string baked into `ARTIFACT_IDENTITY.json` at Docker build time (the `RUN python3` layer that reads `ARG RENDER_GIT_COMMIT`). On HF Spaces (Docker SDK) a `restart_space()` WITHOUT `factory_reboot=True` reuses the build's cached `COPY . .` layer — the Python source layer — while the identity layer re-runs (its instruction text changed with the new ARG). The container then executes the STALE `user_state.py` from the cached layer while reporting the NEW commit from the freshly-baked identity file. "The version endpoint says the right SHA" was treated as "the executing source is the right tree" — the exact Art. XXII assumption the directive forbids.

**Principle:** Exact-SHA deployment is proven by a LIVE BEHAVIOR GATE, not by the version string. A deploy that changes both the source tree and the identity ARG must force a clean image build (`restart_space(factory_reboot=True)`, which busts the HF layer cache) and gate convergence on a probe that exercises the NEW code's own discriminating behavior (a terminal shape the new `user_state.py` answers differently from the stale one, re-derived through the committed source on the SAME served record, and the two answers must agree). The version string remains a necessary but not sufficient identity check; the behavior gate is the sufficient one.

**Required check:** For every exact-SHA deploy: (1) stage the exact final commit; (2) restart with `factory_reboot=True` (or an equivalent layer-cache bust) so the executing source is the uploaded tree, not a cached layer; (3) poll BOTH `/api/version` (`engine_commit == final SHA`) AND a live behavior probe (a terminal session's served `user_state_view.finished` re-derived with the committed source on the same record — the two must agree) before declaring convergence; (4) only then write the closure artifact, tied to that exact SHA and that passing behavior gate.

## BS-043 — A resolver-issued fallback capability defeats the "incoming capability absent" cause class

**Observed:** R546's owner-capability diagnostic classified a failed match as `HEADER_NOT_SENT` by checking `not _diag_caller`. But `_owner_key()` ISSUES a fresh capability when no cookie/header/query arrives, so `_diag_caller` is populated by the resolver itself before the diagnostic examines it — a caller who sent nothing produces a non-empty `_diag_caller` and the "header not sent" branch is never taken. The "which incoming link failed" question is answered from the RESOLVED capability, not the INCOMING presentation.

**Failure mode:** A diagnostic that measures the resolver's OUTPUT (the resolved capability) and then claims to have classified the INPUT (what the caller sent) is self-defeating: the resolver's fallback makes every "absent" case look "present-but-mismatched." The incoming presentation and the resolved capability are conflated, so a missing incoming capability is indistinguishable from a resolver-issued fallback.

**Principle:** Diagnostic instrumentation must separate the incoming caller presentation (`incoming_cookie`, `incoming_header`, `incoming_query`, each with presence + length + fingerprint, never the value) from the `resolved_capability` + `resolved_source` + `resolver_issued` + `session_owner` + `authorization_match` + `cause`. A missing incoming capability stays distinguishable from a server-issued fallback, a cookie/header disagreement, a session-owner mismatch, a missing session owner record, and a missing session. This is instrumentation only — it never changes authorization semantics (no operator-key bypass, no weakened ownership).

**Required check:** For every owner-capability diagnostic: (1) record incoming cookie/header/query presence separately from the resolved capability; (2) record `resolved_source` (cookie / header / query / issued) and the `resolver_issued` boolean; (3) only when no incoming presentation is present AND the resolver issued the capability may the cause be `RESOLVER_ISSUED_FALLBACK` (distinct from `INCOMING_CAPABILITY_ABSENT`); (4) never emit the token value (BS-021 / Art. LXXVI — fingerprint only).

## Audit-trigger rule

When a future audit encounters a new failure mode that is not covered here, the auditor must:

1. Record the observation and evidence.
2. State why the existing governance did not prevent the miss.
3. Add a new blind-spot entry before the next substantive audit, unless doing so would contaminate a sealed experiment.
4. Reread the updated governance before issuing the next verdict.

## Non-negotiable meta-principle

The auditor must assume it is capable of being fooled by the current evidence surface. The purpose of this register is not to guarantee perfect observation; it is to make repeated classes of error progressively harder to repeat.
