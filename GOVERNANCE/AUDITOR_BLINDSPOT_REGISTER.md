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

## Audit-trigger rule

When a future audit encounters a new failure mode that is not covered here, the auditor must:

1. Record the observation and evidence.
2. State why the existing governance did not prevent the miss.
3. Add a new blind-spot entry before the next substantive audit, unless doing so would contaminate a sealed experiment.
4. Reread the updated governance before issuing the next verdict.

## Non-negotiable meta-principle

The auditor must assume it is capable of being fooled by the current evidence surface. The purpose of this register is not to guarantee perfect observation; it is to make repeated classes of error progressively harder to repeat.
