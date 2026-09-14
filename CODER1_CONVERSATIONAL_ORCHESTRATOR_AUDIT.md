# CODER1_CONVERSATIONAL_ORCHESTRATOR_AUDIT.md — R446-C1

**Round:** R446-C1 — CODER 1, Discovery Intelligence / Claude-like problem processing
**Directive:** "Make Toscanini behave like one intelligent conversational discovery engine rather than a user-operated sequence of internal stages."
**Constitution:** v2.4.0 read IN FULL at round start (2084+71 lines, the Art. LXXI amendment); re-read before the final commit.
**Baseline (Art. XXII/XXIII):** the round opened on a STALE_LOCAL_CHECKOUT (local HEAD `2d52fc62`, R445). `git ls-remote` (PAT-authenticated) showed the REAL main at `caf9fa54` — 111 commits ahead (R446–R453-C2). The checkout was realigned to `caf9fa54` BEFORE any code was written, and the audit below is against THAT state (the R453-C2 Claude-class UI reconstruction, the R453-LEAN-CORE admission machinery, and Constitution v2.4.0 were all already merged).

---

## 1. What this audit covers

The directive's own framing: "Do not rewrite the existing epistemic pipeline merely because it has many stages. The repository's own R389 audit says the active path was already minimized for its epistemic guarantees. Your job is to make that machinery adaptive, selectively executed, and cleanly consumable by the product."

This audit therefore examines, per directive section: (a) what ALREADY existed at `caf9fa54` (rounds R446–R453 built substantial adjacent machinery — this audit refuses to re-implement any of it, Art. LXIV discipline), (b) what was MISSING, and (c) what R446-C1 built, with the measured acceptance evidence.

## 2. What already existed at the realigned baseline (do not duplicate)

| Directive concern | Already built (round, module) | Gap that remained |
|---|---|---|
| Adaptive admission ("stop spending intelligence on empty stages") | R453-LEAN-CORE: `SKIPPED_ADMISSION` on `ADAPTIVE_ADMISSION_STAGES` with typed skip reasons; `synthesis_capability_state` + `retained_candidate_facts` (engine/stage_entry.py) | The vocabulary covered ONE refusal class (empty-input admission). No RUN/SKIP/DEFER/BLOCK/STOP policy, no low-value class, no STOP semantics |
| Distinct non-execution states | R451-C2: the five-state retrieval vocabulary (RETRIEVED split); R441–R443: visual-gate NOT_RUN/SKIPPED_INFRA_UNAVAILABLE/RENDER_SKIPPED_LOW_MEMORY typed records | No UNIFIED six-state stage-level vocabulary (NOT_REQUIRED/NOT_REACHED/NOT_RUN/BLOCKED/FAILED/SKIPPED_LOW_VALUE) with a total mapping from engine statuses |
| Killed-invention honesty | R452: `challenge.killed` and evidence verification AUTHORITATIVE over `final_status` (user_state, run_state `_lineage_challenge_verdict`) | The artifact tail (worker bridge phase) had no policy layer — the R418 contract auto-generated artifacts for completed runs with a CIO |
| Completion authority | R446-C1 Task 4 (prior session, merged): `completion.py` — run_manifest.json as the TRUE completion marker | Not consumed by a clean product-facing run contract (directive §11) |
| Model cost/provenance | R451: `model_cost_policy.py` (cost basis on every call result); R451-C1.3: `call_context.py` (run-owned ledger lines) | No §18 work-routing declaration (deterministic vs LLM), no §19 downgrade detector (cheap fallback inheriting strong-route authority) |
| Causal learning | R452 Phase 7: `causal_learning.py` (deterministic causal loop with explicit causal edges) | Not projected into product events (directive §9/§20) |
| Conversational Q&A | R395: `/api/run/{id}/ask` (run_qa, read-only over artifacts) | No INPUT-side conversational layer: no Problem Understanding contract, no clarification rule, no conversation-memory isolation |
| Claude-class UI | R453-C2: the frontend reconstruction ("one conversation → one discovery") | The backend semantics the UI needs (§9 events, §11 contract) had no single clean source |

## 3. What R446-C1 built (the conversational orchestration layer)

New package `toscanini/conversational/` — a layer ABOVE the canonical pipeline. The engine `STAGE_ORDER`, the stage adapters, the gates, the release chain, and the package contract are UNTOUCHED (the loop is the authority; the layer makes it adaptive, never weaker).

| Module | Directive § | What it does |
|---|---|---|
| `problem_understanding.py` | §3 | The 12-field Problem Understanding contract; every field typed `{value, origin, basis, confidence}` over the closed origin vocabulary USER_STATED / INFERRED_MODEL / MODEL_DERIVED_LLM / UNKNOWN. Deterministic zero-LLM constructor; LLM enrichment never overrides USER_STATED (disagreements recorded); persisted to the run dir BEFORE the engine runs (an INPUT record, never a discovery claim) |
| `clarification.py` | §4 | The ask-only-when-material rule: `materiality × uncertainty × answerability ≥ 0.35`, at most ONE question per pause, each question names the current reading + the real alternative + the decision it changes. "Select your industry" is structurally impossible (domain is in the never-ask set). The directive's own tubing example runs with ZERO questions |
| `stage_policy.py` | §5/§6/§7/§14/§23 | The five-decision vocabulary (RUN/SKIP/DEFER/BLOCK/STOP) with reason + next_action + prerequisite evidence; the six-state non-execution vocabulary with a TOTAL one-way mapping from engine/bridge statuses; the evidence-sufficiency stopping rule (≥3 verified items across ≥2 source families); the weak-premise STOP (classification ran + adequate 8-record base + zero mechanism support → `PROBLEM_EXISTENCE_UNESTABLISHED`, never a scientific rejection); the expensive-artifact lazy-execution policy |
| `nba_controller.py` | §8 | The Next Best Action as the REAL controller: re-computed from the CURRENT recorded envelope before every stage; the standing V4 scoring formula (one scoring authority, two sites); the preferred action + the full ranked ledger persisted to `NBA_CONTROLLER.json`; the honest action vocabulary (RETRIEVE_MORE / COMPETING_MECHANISM / ATTACK / ENGINEERING_ESCALATION / DECISIVE_EXPERIMENT / ASK_CLARIFICATION / STOP_HONEST / PACKAGE_READY) |
| `product_events.py` | §9/§10 | The 17 directive event types (+ CLARIFICATION_REQUESTED, RUN_BLOCKED) derived EXCLUSIVELY from persisted artifacts (basis_ref on every event); attack NOT_RUN can never emit CANDIDATE_SURVIVED; infrastructure states emit RUN_BLOCKED, never a scientific verdict; PACKAGE_READY requires the package report's own field |
| `run_contract.py` | §11 | The ~7-field high-level contract (run_id, current_state, human_progress, next_action, artifacts, blocking_reason, uncertainties) — a projection of canonical state (completion marker + run_state phases + NBA), never a second state store |
| `conversation_memory.py` | §12 | The mechanical guard: user messages classified (QUESTION / ASSERTION_PROOF / ASSERTION_PREFERENCE / ASSERTION_CORRECTION / NEW_PROBLEM); "We proved candidate B" is CONTEXT-ONLY with the required REALITY_EVENT path stated; the conversation path can write exactly three context fields — every scientific field is refused with a typed, auditable record |
| `model_provenance.py` | §18/§19 | The work-routing declaration (14 deterministic work classes with zero LLM call sites, 6 LLM classes with required task tiers); the §19 provenance pack (provider/model/revision/configuration/capability_tier/run_id) with the AUTHORITY_DOWNGRADED detector — a CHEAP/FAST route serving a STRONG request carries only its own class authority |

**Engine integration (surgical, one site):** `EngineRun` gains an optional `stage_gate` callback — called before each stage with the CURRENT recorded envelope. Returning a §6 decision persists the typed stage entry (`SKIPPED_POLICY_LOW_VALUE` / `SKIPPED_POLICY_NOT_REQUIRED` / `BLOCKED_POLICY` / `DEFERRED_POLICY` / `STOPPED_POLICY`, downstream of a STOP: `SKIPPED_POLICY_NOT_REACHED`). A gate exception fails OPEN to RUN (the orchestration layer can never hold the epistemic chain hostage). **Absent gate → the conductor is byte-identical to pre-R446** (pinned by test).

**Worker wiring:** phase 1.9 (deterministic PU + clarification pause → `AWAITING_CLARIFICATION`, resumable); phase 2.1 (LLM enrichment + run-dir persistence); phase 3 (the NBA-driven stage gate closure); phase 3.5 (the expensive-artifact policy consulted before the bridge — a killed candidate generates no CAD/visual/package, typed).

**Server routes:** `POST /api/run/{id}/answer` (the clarification answer, guarded, worker re-spawned), `GET /api/run/{id}/contract` (§11), `GET /api/run/{id}/product-events` (§9/§10).

## 4. Acceptance evidence (directive §24, measured)

Battery: `tests/test_r446_conversational_orchestrator.py` — **48/48 passed** (offline by construction; the engine conductor is exercised with typed stub adapters seeding each scenario's RECORDED state — the real adapters keep their own networked batteries; this sandbox has no transport and an offline test never claims an online capability, Art. LXI).

| Case | Assertion (measured) |
|---|---|
| A — simple problem | Weak premise (9 records, classification ran, zero support) → gate STOPs SYNTHESIZE; downstream records `SKIPPED_POLICY_NOT_REACHED`; final status the typed `PROBLEM_EXISTENCE_UNESTABLISHED`; lineage records `SKIPPED_POLICY_STOP`; NO scientific rejection, NO cemetery entry. Converse guard: a supported problem runs the chain (Art. V — not a universal rejector) |
| B — ambiguous problem | The fouling/maintenance example yields EXACTLY ONE materiality-joined question ("You mentioned heat exchanger fouling — what outcome do you want: reduce the fouling itself, or manage its cost/consequence?"); the directive's tubing example yields ZERO; "select your industry" is structurally refused |
| C — strong evidence | Sufficiency (3+ verified items, 2+ source families) → MECHANISM_SPACE (5 LLM calls) records `SKIPPED_POLICY_LOW_VALUE` with the distinctness authority preserved downstream (COLLISION/ATTACK unchanged); the connector-level stopping rule halts further retrieval once both role anchors are covered |
| D — conflicting evidence | The unresolved contradiction rides the run contract as an explicit uncertainty (field C-1); the NBA prefers ATTACK over more retrieval; the full gauntlet still executes |
| E — obvious candidate failure | attack overall=KILL (or a killed lineage generation) → the artifact tail is refused: decision SKIP, class NOT_REQUIRED, reason "no CAD, no visual package, no buyer PDF", next_action "generate a competing mechanism" — the directive's own §6 example, verbatim semantics |
| F — provider failure | The total status mapping keeps all six non-execution states distinct; a BLOCKED attack emits RUN_BLOCKED (infrastructure class), never CANDIDATE_REJECTED/SURVIVED |
| G — attack NOT_RUN | NOT_RUN / BLOCKED / SKIPPED_UPSTREAM attacks emit NO survived event and no scientific verdict; only an EXECUTED verdict emits CANDIDATE_SURVIVED (PASS) or CANDIDATE_REJECTED (KILL) |
| H — experiment contradiction | OUTCOME_RECEIVED + MODEL_UPDATED derive only from the reality-loop ledger; CANDIDATE_MUTATED + RE_EVALUATING + CANDIDATE_REJECTED derive from the lineage's own causal deltas (the R452 causal-learning loop is visible to the product) |
| I — user claims proof | "We proved candidate B." → ASSERTION_PROOF, context-only, `affects_canonical_state=false`, required path stated (a REALITY_EVENT through the Art. XXXVIII gate); the guard refuses `final_status`/`package`/`status` writes on the conversation path with a typed record |
| J — stale artifact | A run dir with final_state + bridge/package reports but NO completion marker reads `complete_marker: NOT_MARKED`; PACKAGE_READY requires the package report's own complete field (a stale bridge outcome cannot override it) |

## 5. Benchmark evidence (directive §25, measured)

Driver: `scripts/r446_adaptive_pipeline_benchmark.py` → `CODER1_ADAPTIVE_PIPELINE_BENCHMARK.json`.
Both arms run the REAL `EngineRun` conductor against the same scenario seeds: the FIXED arm has no stage gate (the pre-R446 default conductor), the ADAPTIVE arm has the R446 gate.

| Metric (aggregate over the engine scenarios) | Fixed | Adaptive | Delta |
|---|---|---|---|
| LLM calls (planning model) | 42 | 28 | **−33%** |
| Retrieval operations | 13 | 9 | −31% |
| Compute stages + artifact ops | 89 | 77 | −13% |
| Estimated latency (planning model) | 2,864 s | 2,230 s | −22% |
| Quality gates (A–J ground truths) | — | **10/10 passed** | preserved |

**Verdict: `ADAPTIVE_SUCCESSFUL`** — quality preserved (every gate passed; no epistemic stage lost on any live-candidate path) with material efficiency gains.

Cost provenance (Art. XXVII): the LLM-call table is COMPUTED from source (static count of `llm_registry.generate()` call sites per adapter); latencies are MODEL_DERIVED planning constants from the routing ledger's recorded distribution (`ENGINE_RUNS/model_routing/ledger.jsonl`, 612 lines) — used for arm-to-arm comparison only, never quoted as measured production latency. The `ADEQUATE_EVIDENCE_BASE = 8` threshold is MODEL_DERIVED and declared in the record with its derivation.

## 6. Honest limitations (Art. XV)

1. **The offline benchmark is a POLICY benchmark, not an adapter benchmark.** The stub adapters seed each scenario's recorded state; the real networked adapters have their own batteries. The benchmark proves the conductor's adaptive decisions, not the science inside the stages (which is unchanged).
2. **DEFER currently degenerates.** The engine chain is linear; a stage whose inputs are not yet recorded runs when reached (RUN-when-reached). The vocabulary and the typed record format are declared and total from day one, but no production rule emits DEFER yet — deferred actions live in the NBA ledger instead.
3. **The weak-premise STOP needs the classification on the envelope BEFORE synthesis.** In the live first pass the classification is recorded by VERIFY (after synthesis), so the engine-side STOP serves the resumed-run/re-admission shape. The live first-pass protection is the R453 admission (zero verified items → MECHANISM_SPACE and downstream refuse), the premise gate, and the NBA's RETRIEVE_MORE-before-STOP ordering (a small base never stops, Art. V).
4. **The clarification pause is a session-state pause, not an engine suspend.** The worker exits at `AWAITING_CLARIFICATION`; the answer route re-spawns the SAME worker path with the answer merged into the PU (USER_STATED). No engine compute is burned while the question is open, but a paused run's already-retrieved evidence pack is re-retrieved on resume (the pre-engine phase re-runs).
5. **No transport-complete production run this round.** The fresh production runs (`ts_c1a3864f5583`, `ts_bfe11ba5027e`) honestly terminated `RUN_BLOCKED_TRANSPORT`: the deployed Space's model routing is UNAVAILABLE (the standing owner-gated transport decision since R452 — `localqwen`/`tokenrouter` both unconfigured there). The production-path claims of this round are therefore: the deployed build serves the new routes with the honest infrastructure state, the conductor behavior is verified through the production `EngineRun.run()` in the battery, and the Art. LXXI tuple is GREEN at the deployed SHA. A transport-complete conversational production run (clarification pause → answer → adaptive chain → events → contract) requires the operator to resolve the transport decision first.
6. **The event stream derives from terminal artifacts.** Live SSE streaming still uses the R431 event journal; the §9 product-event stream is derived from the run directory (post-hoc or on-poll). A live event-journal → product-event bridge is future work.

## 7. Regression evidence + delivery state

- New battery: 50/50 passed (48 directive cases + 2 HTTP-routing pins). Combined with the touched-surface regressions (r399 gates, r430 investigation workspace, r419 english-only, status model, r443/r444 state integrity, r445 canonical domain): **171 passed + 5 subtests, 0 failed**.
- The networked engine batteries (e.g. `test_r394_benchmark.py::test_bench_04_false_premise_blocks_engine_chain`) hang in THIS sandbox (no outbound LLM transport; connector timeouts) — an environment defect (BS-020), not a code regression; the same batteries passed in the repo's CI environment per the R441–R453 round records.
- reviewer_provenance: AI_REVIEW (Art. LXVII).
- **Art. LXXI production tuple — DELIVERY COMPLETE:** pushed to origin/main and verified by `ls-remote` (`a4809b28`); deployed to the canonical Space (`prateekm1/toscanini-prod-validation`, revision `a9ea8038`) through the standing r447 deploy pipeline; `/api/version engine_commit == a4809b28` VERIFIED; `/api/health ok=True, deployment_drift=GREEN, identity_tamper=False`. The FIRST deploy's live production probe caught the GET routes mis-registered in `do_POST` (the honest no-such-endpoint 404) — fixed in `67b77a73` with the HTTP-level routing battery pinning the regression (Art. XXXI), redeployed, and re-verified. Final production smoke: `GET /api/run/{id}/contract` serves the CODER1_RUN_CONTRACT with the honest `RUN_BLOCKED_TRANSPORT` infrastructure state (the Space's model routing is UNAVAILABLE — the standing owner-gated transport decision since R452; every other subsystem on the deployed build is healthy); `GET /api/run/{id}/product-events` serves the schema with an honestly empty stream for a run with no run_dir. Two fresh production runs (`ts_c1a3864f5583`, `ts_bfe11ba5027e` — the directive's own example problems) recorded the honest blocked-transport terminal with the problems saved and resumable.

## 8. Preservation statement (the constitutional contract of this layer)

The canonical scientific loop (`PROBLEM → EVIDENCE → MECHANISM → CANDIDATES → ATTACK → INVENTION DIAGNOSTIC → IMPROVE → TECHNICAL EVALUATION → 3D DESIGN → DECISIVE EXPERIMENT → ENGINEERING DOSSIER → BUYER PACKAGE`) and the runtime stage order (16 stages) are UNCHANGED — no stage renamed, no gate weakened, no epistemic control removed. What changed: the conductor can now refuse compute that the RECORDED state makes redundant or pointless, every refusal is a typed, persisted record (Art. XXV), and the product consumes one clean conversational surface (PU → events → contract) derived from canonical state (Art. X). A safe discovery machine that cannot discover is constitutionally incomplete — and equally, a discovery engine that burns its intelligence on empty stages is not yet an organ; this round is the difference.
