# TOSCANINI / DISCOVERY-EVIDENCE-FABRIC — MASTER HANDOFF TO NEXT CHAT

**Handoff purpose:** cold-start a new auditor/coder chat without requiring the operator to paste old files, logs, code, or history into the chat window.

**Canonical handoff path:** `HANDOFF_NEXT_CHAT_R510_MASTER.md`

**Canonical handoff policy:** update this file in place when continuity materially changes. Do not create `HANDOFF_NEXT_CHAT_R510_MASTER_v2.md`, `FINAL_HANDOFF.md`, `NEXT_HANDOFF2.md`, or parallel continuity files. Parallel handoffs create entropy.

**Current repository:** `prateekm1007/discovery-evidence-fabric`

**Current default branch:** `main`

**Remote HEAD policy:** the exact current remote HEAD MUST be fetched and verified by every new chat. This handoff intentionally does not treat a hard-coded HEAD as authority; the latest measured engine/proof publication baseline is `bfbb5bfdd345037f0af84ad5823ec1c2d4d7eec4`, followed by docs-only handoff publication commits.

**Known handoff publication lineage:** `587ea8be503a552b1c94172f864bfa91b18163a1` and subsequent docs-only state-refresh commits. These commits do not replace the measured engine/proof commit identities.

**Accepted support-cliff baseline:** `13e0a3b21364395df2a6ad540622dfface19a69e`

**Measured support-fix engine commit:** `d4e87d1c6bc71692e7e0e648b22307381600942a`

**Measured attack-instrumentation engine commit:** `f6a990a37a9d6cfbedf7fad6d75d0db43e625201`

**Current proof-publication commit:** `bfbb5bfdd345037f0af84ad5823ec1c2d4d7eec4`

**Important provenance distinction:** the six current dry-run proof executions were executed under `f6a990a3...`; the current `R510/DRYRUN_PROOF_RECORD.json` was later regenerated/published at `bfbb5bf...`. The proof record deliberately reports the measured execution commit, not the generation-time HEAD. The publication commit is therefore NOT the execution commit.

**Current Constitution:** v2.10.1; blob SHA `ac128b1c83ee01035deda2ba7592db77b84182ce`.

**Current auditor governance files:**
- `GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md` — SHA `ab2b10b76308a1ebea57ce8fff92fa3dcca9b8f0`
- `GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md` — SHA `1c7c108eee2b37aecd8289ed035ea6858be94a92`
- `GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md` — SHA `ad6f6561ad1b6dc9c13254d35fabd27f889a5e89`
- `GOVERNANCE/AUDITOR_REMEMBERED_STATE.md` — SHA `775c2b1897eceafe1d5cd2b3d5940a729a9fc051`

**Frozen discovery-yield instrument:** `R506/YIELD_INSTRUMENT.json`, v1.0.0, script SHA `831f1a0e075cb9dd370c18325bf2b19fac9f7fa69d1218b980d8c4b22946a2ac`.

**Current tests reported by the latest coder round:** `47 passed, 0 failed`.

**Current dry-run live/paid calls:** `0 / 0`.

**Current world-class claim:** explicitly false / not established.

---

# 0. NON-NEGOTIABLE OPERATING MODE

The operator does not perform terminal work manually. The operator does not open files, edit files, copy repository contents into chat, manually run tests, manually push commits, or manually reconstruct context for a new chat.

The new chat must reconstruct state itself from the authoritative repository using autocommands/tool calls.

## 0.1 Autocommands only

Every machine action must be executable by the coding/auditor agent:

- repository inspection;
- file reads;
- hashes;
- tests;
- benchmark/dry-run execution;
- record generation;
- file modifications;
- commit;
- push;
- remote verification;
- deployment verification where required;
- artifact inspection;
- provenance validation.

Do not issue the operator instructions such as:

```text
open this file
copy this section
run this command
edit this JSON
push these changes
send me the output
```

Instead, the coder must execute those actions itself through its available shell/connectors.

## 0.2 No chat-window file pasting

A new chat MUST NOT require the operator to paste old files.

The correct bootstrap is:

```text
new chat
→ discover repository
→ fetch current main
→ read canonical handoff
→ read governance
→ read Constitution
→ inspect current code/artifacts
→ verify live state
→ continue from authoritative bytes
```

This handoff is a continuity aid, not the source of truth. When this file conflicts with live repository bytes, live bytes win and the discrepancy must be recorded.

## 0.3 No speculative feature expansion

The current objective is controlled optimization, not broad product development.

Do not add:
- new invention concepts merely to create volume;
- new model providers without a measured need;
- new ranking formulas without a measured portfolio problem;
- new mechanism operators without a measured mechanism-space deficit;
- new UI features during this optimization loop;
- duplicate frameworks;
- replacement architectures;
- unrelated refactors;
- new governance documents when an existing canonical document can be updated.

## 0.4 One-cliff optimization law

The current optimization process is governed by `R510/constitution/ONE_CLIFF_FIX_RULE.md` and Constitution Article LXXXIII.

The operational sequence is:

```text
FRESH CONTROLLED BATTERY
        ↓
DURABLE FUNNEL MEASUREMENT
        ↓
NAME LARGEST VALID DROPOUT
        ↓
ONE FIX ONLY
        ↓
IDENTICAL BATTERY
        ↓
COMPARE BEFORE / AFTER
        ↓
NEXT MEASURED CLIFF
```

A transport failure is not a scientific cliff.

A measurement gap is not a scientific kill.

A package count is not discovery evidence.

A green unit test is not proof of production behavior.

---

# 1. AUTHORITY ORDER — NEVER VIOLATE THIS HIERARCHY

When documents conflict, authority flows downward only after the higher level is satisfied.

```text
1. EPISTEMIC_CONSTITUTION.md
2. GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md
3. GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md
4. GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md
5. ACTIVE_PATH.md
6. CANONICAL_MODEL_FLOW.md
7. CANONICAL_STATE/ and other explicitly canonical registries
8. Frozen benchmark/instrument definitions
9. Current round artifacts and proof records
10. Implementation code
11. Tests
12. Worklogs / handoffs / narrative reports
13. Chat claims
```

Tests are evidence about implementation. Tests do not override the Constitution.

A handoff is memory/navigation. It does not override repository truth.

A report can state a result. Only the underlying artifact can prove it.

---

# 2. PROJECT MISSION AND PRODUCT CONTRACT

The project is Toscanini: an AI discovery and invention machine intended to take a difficult user problem through an evidence-constrained, mechanistic, adversarial, experimental, engineering, reality, learning, and buyer-transfer loop.

The target conceptual loop is:

```text
PROBLEM
→ EVIDENCE
→ MECHANISM
→ CANDIDATES
→ ATTACK
→ DIAGNOSIS
→ IMPROVEMENT / MUTATION
→ TECHNICAL EVALUATION
→ 3D / SYSTEM DESIGN
→ DECISIVE EXPERIMENT
→ REALITY
→ OUTCOME
→ CAUSAL UPDATE
→ NEXT EXPERIMENT / NEXT DESIGN
→ ENGINEERING DOSSIER
→ BUYER PACKAGE
```

The runtime D6 stage order is:

```text
RETRIEVE
→ FREEZE
→ PREMISE_GATE
→ SYNTHESIZE
→ VERIFY
→ MECHANISM_SPACE
→ MULTI_SOURCE_DISCOVERY
→ COLLISION
→ PHYSICS
→ ATTACK
→ CONTRADICTION
→ KILLER_EXPERIMENT
→ IMPROVE
→ ADJUDICATION
→ CLASSIFY
→ NEXT_BEST_ACTION
→ RANK
```

## 2.1 User-facing candidate contract

The website is deliberately Claude-like / conversational.

The critical product requirement established by the operator is:

> whenever a valid user request reaches successful candidate generation, the system should return a candidate rather than erase the candidate because a downstream stage is unavailable.

Therefore:

```text
CANDIDATE GENERATION SUCCESS
    ↓
candidate remains visible
    ↓
EVIDENCE / ATTACK / EXPERIMENT / REALITY state attaches honestly
```

A downstream transport failure must not retroactively pretend that no candidate existed.

Conversely, a candidate that has not survived a required scientific gate must not be presented as a discovery/invention merely because it was generated.

---

# 3. CURRENT GOVERNING CONSTITUTION — KEY ARTICLES FOR THE NEXT CHAT

The full Constitution MUST be reread before coding. The following are the most relevant invariants for the current optimization:

## Evidence and verifier discipline

- **I** — evidence precedes assertion.
- **II** — exact evidence beats semantic plausibility.
- **III** — verifier never trusts claimant.
- **IV** — no fallback epistemology.
- **V** — fail closed but allow valid evidenced claims; use positive/negative/metamorphic/E2E tests.
- **VI** — never manufacture provenance; UNKNOWN is legitimate.
- **VII** — never weaken verifier to rescue a claim.
- **VIII** — certification attacks itself.
- **IX** — certification is observational.
- **X** — one canonical state authority.
- **XII** — provenance custody chain.
- **XIII** — research and infrastructure are separate authorities.
- **XIV** — RED gate means STOP.
- **XV** — coder discloses inconvenient results.
- **XVI** — implementation is hypothesis; tests are evidence.
- **XVII** — P0 controls require attempted bypasses.
- **XVIII** — LLM is untrusted.
- **XIX** — optimize truth, not gate color.
- **XXI** — search count is not evidence; absence/provider failure is not absence; relevance must be adjudicated; triangulation independence and provenance matter.
- **XXIV** — summary is not artifact.
- **XXV** — UNKNOWN stays UNKNOWN; infrastructure failure does not become scientific rejection.
- **XXIX** — implementation failure and mechanism failure are distinct.
- **XXX** — evaluator must be adversarially optimized/tested.
- **XXXI** — corrections must create memory; learned knowledge must actually affect future behavior.

## Discovery / mechanism discipline

- **XLI** — canonical mechanism:
  `PROBLEM → FAILURE/UNMET NEED → CAUSAL MECHANISM → INTERVENTION → PHYSICAL/CHEMICAL/COMPUTATIONAL EFFECT → BOUNDARY CONDITIONS → DESIGN VARIABLES → PREDICTED EFFECT → FAILURE MODES → TESTABLE PREDICTION`.
- **XLII** — distinctness verdicts are `DISTINCT / EQUIVALENT / INDETERMINATE`; INDETERMINATE never counts as DISTINCT.
- **XLIII** — search-space neutral.
- **XLIV** — evidence boundary/freeze.
- **XLV** — generator/verifier separation.
- **XLVI** — retrieval absence is not novelty.
- **XLVII** — baseline supremacy.
- **XLVIII** — diversity via MMD / materially distinct mechanisms.
- **XLIX** — multi-domain discovery benchmark.
- **L** — attacker calibration.
- **LI** — learning must change future search; archive-only does not count.
- **LII** — killer experiment is a falsification contract.
- **LIII** — reality ladder:
  `MODEL_DERIVED → COMPUTATIONAL_RESULT → EXTERNAL_REFERENCE_DATA → PHYSICAL_OBSERVATION → REAL_LOOP_VERIFIED → REPEATED_REALITY_VERIFIED`.
- **LIV** — every invention needs a kill condition.
- **LV** — autonomous discovery loop has typed stages/failures/provenance.
- **LVI** — information gain matters.
- **LVII** — search different mechanism-space regions.
- **LIX** — frozen benchmark, no tuning between scored problems.
- **LX** — classification ladder.
- **LXI** — infrastructure failure != scientific rejection.
- **LXII** — reproducibility.
- **LXIII** — buyer reality.

## Current R510 firewall additions

- **LXXI** — production URL / deployment identity is delivery standard.
- **LXXII** — no 3D artifact without passing visual compiler.
- **LXXIII** — operator secrets registry / lookup order.
- **LXXIV** — observer-independent durable execution.
- **LXXV** — patent evidence != patent truth.
- **LXXVI** — credential custody; rotation is CEO-only.
- **LXXVII** — discovery performance is distinct from pipeline completion.
- **LXXVIII** — only candidates surviving adversarial + evidence + contradiction + technical gates earn discovery credit.
- **LXXIX** — capability claims require blind fresh problems and corpus-disjointness.
- **LXXX** — every mechanism needs a >=8 contiguous-word verbatim span from frozen evidence; otherwise `UNGROUNDED_SYNTHESIS`, UNKNOWN, no advance.
- **LXXXI** — attacker with FPR > 0.30 cannot issue terminal KILL; may issue `ESCALATED_OBJECTION`.
- **LXXXII** — UNKNOWN with same typed reason for 5 consecutive rounds becomes `CHRONIC_UNKNOWN`.
- **LXXXIII** — discovery funnel is authoritative measurement instrument.
- **LXXXIV** — fewer than 2 materially distinct candidates => `MECHANISM_STARVED` and no attack/contradiction/experiment discovery evidence.
- **LXXXV** — unpushed work is `LOCAL_UNVERIFIED`; push promptly and verify remote reachability.

---

# 4. GOVERNANCE FILES — THEIR JOBS AND HOW NOT TO CORRUPT THEM

## `GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md`

Governs auditor behavior. Important rules:
- live-state beats narrative;
- built is not wired;
- local proof is not production proof;
- API success is not semantic success;
- infrastructure failure is not scientific absence;
- audit the joins between stages;
- maintain remembered project state;
- no silent reconciliation;
- benchmark gaming guard;
- reproduce before escalating;
- separate code defects from environment defects;
- stop only for information gain.

Do not move project-specific scientific rules into this file. It is auditor-governance, not engine law.

## `GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md`

Known auditor failure modes. Current particularly relevant entries include:
- **BS-034** — self-reported completion bias.
- **BS-035** — audit tunnel vision.
- **BS-036** — recursive governance drift.
- **BS-037** — auditor forgetting project state and direction.

New blind spots must be added only when a real observed miss demonstrates a new recurring failure class. Do not grow the register speculatively.

## `GOVERNANCE/AUDITOR_REMEMBERED_STATE.md`

Continuity aid. It is allowed to remember:
- mission;
- authoritative repositories;
- settled architecture;
- current blockers;
- rejected paths;
- latest accepted directive;
- last verified behavior;
- next decisive verification.

It is NOT evidence. Refresh it against live state.

## `GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md`

Operational coordination between auditor and coder. It reinforces:
- auditor reads governance;
- coder reads Constitution;
- independent audit first;
- minimal coherent fixes;
- tests + fresh end-to-end proof;
- blind-spot update if new failure class appears;
- release/deployment verification.

---

# 5. THE THREE MOST IMPORTANT CANONICAL MAPS

## 5.1 `EPISTEMIC_CONSTITUTION.md`

Supreme authority. No implementation may silently redefine its scientific meaning.

## 5.2 `ACTIVE_PATH.md`

The primary documented production-path map. It should be treated as the authoritative description of what production is intended to execute. Its historical addenda are useful evidence, but the next chat must verify the actual code path rather than trusting narrative.

## 5.3 `CANONICAL_MODEL_FLOW.md`

Binds invention state to engineering/3D/browser rendering. Test-enforced one-canonical-model architecture:

```text
canonical invention state
→ domain/engineering geometry specification
→ deterministic geometry
→ geometry quality gate
→ Blender presentation layer
→ canonical GLB / identity
→ one browser viewer
```

CadQuery/OCP/OCCT is engineering geometry authority. Blender is presentation-only. Three.js/browser viewer is presentation layer.

Do not create a second invention→geometry mapping.

---

# 6. CURRENT ARCHITECTURE — ROLE MAP

The live `discovery_fabric/` package has many historical and active modules. The next chat must avoid recreating existing responsibilities under new filenames.

## Top-level `discovery_fabric/`

Current high-level subpackages:

```text
discovery_fabric/
├── a2/                    # run-level adversarial/gauntlet path
├── benchmark/             # benchmark helpers
├── connectors/             # external connector surfaces
├── directional/            # directional hypothesis / challenge evolution
├── discovery_modes/        # discovery-mode orchestration/selection
├── engine/                 # canonical D6 engine implementation
├── evidence_fabric/        # evidence retrieval/fabric support
├── knowledge_graph/        # graph/state representations
├── physics_stack/          # physics subsystem support
├── prior_art_v2/           # prior-art subsystem
├── quarantine/             # quarantine / retired or isolated material
├── retrieval_fabric/       # retrieval source logic
├── source_registry/        # source registry
├── prior_art_v2_bridge.py  # bridge compatibility surface
├── portable_flock.py       # portability/locking utility
└── v4_corrections.py       # authoritative adversarial corrections
```

The package is not a blank-slate framework. Before adding a subsystem, search for an existing canonical implementation.

## `discovery_fabric/engine/`

This is the core active orchestration layer. Important current files and roles:

```text
run.py                     # canonical EngineRun conductor; actual D6 lifecycle
adapters.py                # stage adapters / orchestration seam
stage_entry.py             # stage entry contract/support
call_context.py            # request/run execution context; fixture binding
llm_registry.py            # provider selection / model calls / availability
model_routing.py           # model/provider routing policies
provider_health.py         # observed provider health
transport_capability.py    # transport capability surface

mechanism_space.py         # candidate generation, dedupe, support verification, cemetery consultation
candidate.py               # candidate/state object definitions
candidate_diversity.py     # exploration grid and distinctness paths
transition_trace.py        # R510 candidate transition measurement

dry_run.py                # controlled dry-run transport, portfolio/funnel measurement
independent_attack.py     # per-candidate independent adversarial attack
engineering_attack.py     # engineering-level attack/repair/selection
attacker_calibration.py   # attacker calibration gate/consumption logic

premise_gate.py            # premise gate
cheap_screen.py            # cheap candidate screening
evidence_classification.py# evidence classification

domain_reasoning.py        # domain reasoning
quantitiy_reasoning.py     # quantity reasoning (existing module)
technical_evaluator.py     # technical evaluation
physics_stage.py           # physics lifecycle
physics_gate.py            # physics gate
technical_equations.py     # technical equation subsystem
equations.py               # equation subsystem

contradiction handling via orchestrator/contradiction_queue.py

improve_stage.py           # IMPROVE stage
improvement_engine.py      # causal improvement engine
technical_improvement_engine.py # technical improvement path
design_learning.py         # design learning
causal_learning.py         # causal learning

decisive_experiment.py     # decisive experiment selection
experiment_selector.py     # experiment selection logic
evolution.py               # evolution chain

engineering_spec.py        # engineering specification
invention_spec.py           # invention specification
package_compiler.py        # canonical package compilation
package_registry.py        # package identity/registry
package_quality_gate/      # package quality controls

invention_bridge/           # invention-to-geometry bridge subsystem
visual_compiler/            # 3D visual compiler
cad_pipeline.py             # CAD pipeline

state_integrity.py          # canonical state integrity
release.py                  # release logic
runtime_admission.py        # runtime admission
```

### Critical anti-entropy rule

When changing attack behavior, the canonical per-candidate module is:

```text
discovery_fabric/engine/independent_attack.py
```

not `a2/adversarial.py`.

When changing run-level A2 behavior, the canonical module is:

```text
discovery_fabric/a2/adversarial.py
```

These are different attack systems with different contracts.

When changing the conductor, modify `run.py`; do not build a second runner.

When changing the dry-run transport/measurement instrument, modify `engine/dry_run.py` and its R510 test/fixture surface; do not build a new dry-run engine.

---

# 7. CRITICAL ATTACK ARCHITECTURE — TWO ATTACKS, NOT ONE

This is the single most important context discovery for the next chat.

## 7.1 Attack path A — run-level A2 adversarial gauntlet

Canonical file:

```text
discovery_fabric/a2/adversarial.py
```

Canonical function:

```text
adversarial_challenge(candidate, evidence_verified, prior_art_state)
```

Its LLM call path includes:

```text
llm_chat()
→ llm_registry.generate(... purpose="attack" ...)
```

Current controlled fixtures DO contain a matching:

```json
{"purpose_exact":"attack", ...}
```

Existing direct test:

```text
tests/test_r510_dryrun.py::test_attack_fixtures_kill_through_real_instrument
```

proves that the A2 attack text can travel through `adversarial_challenge()` and produce a `KILLED` result in the direct fixture test.

That is valid evidence for path A only.

## 7.2 Attack path B — per-candidate independent attack

Canonical file:

```text
discovery_fabric/engine/independent_attack.py
```

Canonical function:

```text
independent_attack(...)
```

Actual LLM call:

```text
from .mechanism_space import llm_generate

llm_generate(
    prompt,
    system=..., 
    purpose="independent_attack",
    exclude_providers=[generator_provider] if generator_provider else None,
    max_tokens=1600,
    hard_pin_provider=require_provider,
)
```

This is what the real `EngineRun._post_rank_pipeline` invokes for each `mech-*` or `grid-*` candidate.

Each result is persisted as:

```text
INDEPENDENT_ATTACK_{key}.json
```

Then consumption applies:

```text
attacker_calibration.apply_at_consumption(...)
```

and only then do KILL/escalation semantics affect downstream selection.

## 7.3 Why the current 34 attack failures happen

The current controlled fixture bundle in:

```text
tests/fixtures/dryrun/problems.py
```

contains:

```text
purpose_prefix = synthesis
purpose_prefix = operator_
purpose_exact = attack
purpose_prefix = diversity_exploration
```

It does NOT contain:

```text
purpose_exact = independent_attack
```

Therefore the real per-candidate independent attacker sends a request for:

```text
purpose="independent_attack"
```

The deterministic fixture matcher finds no matching specification and correctly returns:

```text
PROVIDER_UNAVAILABLE
```

The resulting per-candidate attack state becomes:

```text
ATTACK_INCOMPLETE
transport=TRANSPORT_UNAVAILABLE
```

This is the root cause of the current 34 transport-unavailable candidate states.

This is an implementation/fixture-coverage defect in the dry-run path, not evidence that 34 candidates are scientifically killed.

## 7.4 Why simply reusing the A2 fixture is unsafe

The A2 fixture text uses a different response contract:

```text
UNSUPPORTED_MECHANISM: ...
WEAK_TRANSFER: ...
OBVIOUS_COMBINATION: ...
...
OVERALL: KILLED
```

The independent attacker parser expects:

```text
MECHANISM_FAILURE: <KILL|RISK|SURVIVE> — ... GROUNDED_IN: ...
BOUNDARY_CONDITION_FAILURE: ...
EVIDENCE_CONTRADICTION: ...
BASELINE_EQUIVALENCE: ...
IMPLEMENTATION_IMPOSSIBILITY: ...
MEASUREMENT_AMBIGUITY: ...
```

Therefore the correct dry-run fix is a dedicated deterministic `independent_attack` fixture response matching the actual independent attacker contract.

Do not merge the contracts merely because both are “attack.”

---

# 8. CURRENT ATTACK-INSTRUMENT FINDINGS THAT MUST BE PRESERVED

## 8.1 What has already been improved

R510 attack measurement instrumentation now persists, per candidate:

```text
attack_reached
independent_attack_attempted
independent_attack_status
engineering_attack_status
attack_transport_state
attack_independence_state
attack_drop_transition
```

and aggregates:

```text
NOT_REACHED
ATTEMPTED
COMPLETED
INCOMPLETE
KILLED
SURVIVED
UNKNOWN
```

This is a measurement improvement, not a scientific discovery result.

## 8.2 Current semantic concern — `independent_attack_attempted`

The current helper treats a persisted record whose `overall != NOT_RUN` as attempted.

That means a transport-refused request can currently result in:

```text
independent_attack_attempted=true
```

while also having:

```text
llm_status=PROVIDER_UNAVAILABLE
attack_transport_state=TRANSPORT_UNAVAILABLE
```

This is potentially overbroad naming.

The next chat should audit whether the state machine needs separate mechanical distinctions:

```text
attack_requested
attack_execution_started
attack_execution_completed
independent_attack_attempted
```

Do not automatically refactor this. First inspect all consumers and prove whether the ambiguity affects authoritative classification or is merely a label.

## 8.3 Current semantic concern — top-level `attack_naive_overall`

The funnel currently reads `naive_attack_overall` from:

```text
envelope_ATTACK.json
```

The current proof sample can show:

```text
attack_naive_overall = KILLED
```

while the per-candidate independent attack pool simultaneously reports:

```text
ATTACK_INCOMPLETE
TRANSPORT_UNAVAILABLE
```

This is not automatically a bug because the two are different attack paths.

It IS a dangerous semantic surface because a reader or downstream consumer can interpret the top-level `KILLED` as if it represented the 34 candidate-level independent attacks.

The next chat must trace every consumer of `attack_naive_overall` before deciding whether to rename, scope, or remove it from authoritative interpretation.

Do not casually delete it if historical or current A2 semantics require it. Make the distinction explicit and mechanically impossible to confuse.

---

# 9. CURRENT DRY-RUN SYSTEM

## `discovery_fabric/engine/dry_run.py`

Responsibilities:

- deterministic `FixtureTransport`;
- specificity-aware matching;
- honest `PROVIDER_UNAVAILABLE` refusal;
- zero live/paid call telemetry;
- deterministic candidate identity;
- deterministic ranking;
- durable portfolio reconstruction;
- per-candidate attack measurement;
- funnel construction.

Fixture matching precedence is explicitly:

```text
exact purpose
→ exact route
→ narrower prompt
→ purpose prefix
→ stable tie-break
```

No-match must remain a typed transport refusal.

## Ranking

Current deterministic selection-aid weights:

```text
mechanism_support = 3
span_bound = 2
distinctness_distinct = 2
evidence_refs = 1
attack_survived = 2
testability = 1
```

Tie-break:

```text
candidate_id ascending
```

The ranking is NOT an epistemic quality score. It is a deterministic portfolio selection aid.

Do not reinterpret score or rank as evidence of discovery.

---

# 10. FROZEN DISCOVERY-YIELD INSTRUMENT

Canonical file:

```text
R506/YIELD_INSTRUMENT.json
```

Version:

```text
1.0.0
```

Script SHA:

```text
831f1a0e075cb9dd370c18325bf2b19fac9f7fa69d1218b980d8c4b22946a2ac
```

Authoritative funnel order:

```text
1. fresh_submitted
2. premise_coherent
3. evidence_verified
4. mechanisms_found
5. candidates_generated_distinct
6. attack_survivors
7. contradiction_survivors
8. experimentally_discriminated
9. mutated_survivors
10. buyer_ready
```

Rules:

- counts derive from durable bytes;
- candidate count uses distinctness authority;
- `INDETERMINATE` does not count as DISTINCT;
- grid-advanced is not automatically survivor credit;
- no novelty claim from missing search coverage;
- no cost inference where unmetered;
- no pipeline-completion signal can be promoted into discovery evidence.

Do not edit this instrument during a scored battery.

If the instrument itself must change, it becomes a new instrument/version and old measurements stand unchanged.

---

# 11. CURRENT R510 DRY-RUN MEASUREMENTS

Current post-support-fix A/B baseline:

```text
P1 A/B:
  support_not_enough_evidence = 0
  support_partial = 1
  pipeline_retained = 1
  survivor_eligible = true

P2 A/B:
  cemetery_block = 1
  drop = CEMETERY_BLOCK
  invariant unchanged

P3 A/B:
  support_not_enough_evidence = 0
  support_partial = 1
  pipeline_retained = 1
  survivor_eligible = true
```

Previous support cliff:

```text
BEFORE:
  support_nee = 1/run
  survivor_eligible = false
  drop = SUPPORT_VERIFICATION

AFTER:
  support_nee = 0
  support_partial = 1
  survivor_eligible = true
```

Regression status:

```text
false
```

Current candidate transition aggregate:

```text
generated = 36
structural_loss = 0
cemetery_loss = 2
 distinctness_loss = 0
support_loss = 0
attack_incomplete = 34
attack_killed = 0
other_loss = 0
```

Candidate pool count by run is effectively:

```text
P1 = 6
P2 = 5
P3 = 6
```

Across A/B:

```text
6 + 5 + 6 = 17 candidates/run
17 × 2 = 34 independent-attack pool candidates
```

All 34 current independent-attack pool states are classified as transport-unavailable/incomplete.

Therefore:

> The current measurement does NOT establish that the candidate portfolio loses 34 scientific candidates to attack.

It establishes that the current dry-run transport fixture does not serve the real independent-attack purpose.

---

# 12. CURRENT R510 PROOF RECORD

Canonical artifact:

```text
R510/DRYRUN_PROOF_RECORD.json
```

Current proof record contains:

- Constitution version;
- measured run summaries;
- repeatability state;
- candidate-transition measurement;
- attack measurement;
- attack aggregate;
- sample funnel;
- stage timings;
- ranked portfolio sample;
- deterministic fixture-matching declaration;
- reviewer provenance.

Current proof record must remain clearly classified as:

```text
CONTROLLED TEST MATERIAL ONLY
```

The problems are machine-authored dry-run fixtures.

They are NOT blind fresh problems under Article LXXIX.

They are NOT discovery evidence under Article LXXVII.

`r506_eligible=False` is required.

---

# 13. CURRENT CONTROLLED DRY-RUN FIXTURES

Canonical file:

```text
tests/fixtures/dryrun/problems.py
```

Contains three machine-authored controlled problems:

```text
dry-p1
  family = thermal-management
  device = engine cooling system
  failure = coolant vapor leak under driving conditions
  constraint = no engine removal

dry-p2
  family = fluid-power
  device = hydraulic lift actuator
  failure = pressure decay during sustained hold
  constraint = no system drain-down

dry-p3
  family = structural-dynamics
  device = cable/damper system
  failure = crosswind lock-in
  constraint = no cable replacement
```

These are dry-run fixtures only.

They must never be presented as blind capability evidence.

Each pack contains deterministic evidence and generated candidate bodies.

The A2 attack fixture exists and uses `purpose_exact="attack"`.

The missing coverage is the real per-candidate independent-attack purpose.

---

# 14. CURRENT TEST ARCHITECTURE

## Primary R510 dry-run tests

```text
tests/test_r510_dryrun.py
```

Current coverage includes:

- fixture precedence;
- exact-purpose precedence;
- route precedence;
- prompt specificity;
- honest refusal;
- deterministic ranking;
- support state reads;
- distinctness governance;
- attack-drop semantics;
- attack-transport classification;
- attack-independence classification;
- dry-run constructor isolation;
- cemetery sandboxing;
- direct A2 attack fixture;
- proof counts;
- repeatability.

Important gap:

> `test_attack_fixtures_kill_through_real_instrument` directly exercises `a2.adversarial.adversarial_challenge`; it does not prove the complete `EngineRun → independent_attack()` per-candidate path executes under dry-run fixtures.

A new end-to-end dry-run test must cover the latter.

## Transition tests

```text
tests/test_r510_transitions.py
```

Controls A-D:

```text
A = cemetery block
B = no cemetery block
C = distinctness drop
D = support loss
```

The tests enforce the transition taxonomy and candidate retention logic.

## Diversity tests

```text
tests/test_r510_diversity_adapter.py
```

Covers:

- canonical mapping;
- empty field preservation;
- true distinctness;
- identical equivalence;
- knob-only equivalence;
- metamorphic rewording;
- fixture refusal;
- deterministic grid wiring.

---

# 15. CURRENT EXECUTION / PROOF AUTOMATION

## `scripts/r510_dryrun_proof.py`

Runs one controlled problem/round through the real `EngineRun` with deterministic fixture transport.

Required behavior:

- fresh output directory;
- no live credentials required;
- no live calls;
- no paid calls;
- persisted per-run proof summary;
- cemetery before/after comparison;
- durable funnel/portfolio outputs.

## `scripts/r510_dryrun_repeat.py`

Compares A/B repeatability using deterministic identities and normalized permitted runtime metadata.

The permitted timestamp-derived MS candidate-id variation is normalized because it is runtime metadata, not scientific identity.

## `scripts/r510_dryrun_record.py`

Consumes the six per-run proof outputs and writes:

```text
R510/DRYRUN_PROOF_RECORD.json
```

The current implementation derives the reported `code_commit` from the proof runs' own summaries via `_run_commit` and fails closed if run commits disagree.

## `scripts/r510_dryrun_record.py` provenance rule

Current ordering is:

```text
commit engine
→ execute proof runs
→ generate proof record
→ publish proof record
```

This closes the prior Article XXXI stale-commit defect.

---

# 16. FILE STRUCTURE — AUTHORITATIVE ROLE CLASSIFICATION

The repository is intentionally large because it contains years of research rounds, historical proofs, product experiments, and active infrastructure. The presence of a file does not mean it is the current authority.

The next chat should use the following role model.

## A. GOVERNANCE / CONSTITUTION — highest human/process authority

```text
EPISTEMIC_CONSTITUTION.md
GOVERNANCE/
  AUDITOR_SELF_GOVERNANCE_v1.md
  AUDIT_LOOP_PROTOCOL_v1.md
  AUDITOR_BLINDSPOT_REGISTER.md
  AUDITOR_REMEMBERED_STATE.md
R510/constitution/
  AMENDMENT_RECORD.json
  AMENDMENT_RECORD_LXXXV.json
  ARTICLE_LXXX_*.md
  ARTICLE_LXXXI_*.md
  ARTICLE_LXXXII_*.md
  ARTICLE_LXXXIII_*.md
  ARTICLE_LXXXIV_*.md
  ARTICLE_LXXXV_*.md
  ONE_CLIFF_FIX_RULE.md
  SCOPE_LAW.md
```

Policy: do not create parallel governance documents when an existing article or governance file is the correct home.

## B. PRODUCTION PATH / ARCHITECTURE DOCUMENTATION

```text
ACTIVE_PATH.md
CANONICAL_MODEL_FLOW.md
ENGINE_BLUEPRINT.md
ADR_*.md
PRODUCTION_ADVERSARIAL_CALL_GRAPH.md
```

Policy: these documents describe/bind implementation. They are not allowed to silently override Constitution semantics.

## C. CANONICAL DURABLE STATE

```text
CANONICAL_STATE/
```

This is the designated canonical-state area. Historical objects may be retained, but only explicit canonical files should be treated as current authority.

Important root registries include:

```text
MODULE_INVENTORY.json
ENGINE_RELEASE_REGISTRY.json
ENGINEERING_DOMAIN_REGISTRY.json
RUNTIME_CAPABILITY_REGISTRY.json
PACKAGE_ID_REGISTRY.json
PATENT_SOURCE_REGISTRY.json
PORTFOLIO_COMMERCIAL_STATE.json
```

Do not hand-edit a generated registry if a generator/authority script exists.

## D. ACTIVE ENGINE IMPLEMENTATION

```text
discovery_fabric/engine/
discovery_fabric/a2/
engine-related orchestrator/ modules
```

Treat existing canonical functions as owners of their responsibilities. Search before creating a new module.

## E. CONTROLLED TEST INPUTS

```text
tests/fixtures/dryrun/
```

These are controlled test fixtures, not discovery evidence.

## F. CURRENT R510 OPTIMIZATION ARTIFACTS

```text
R510/
  DRYRUN_PROOF_RECORD.json
  DIVERSITY_DRYRUN*.json
  GRID_MECHANISM_FIXTURE.json
  MECHANISM_STARVATION_BASELINE.json
  MEMORY_PROOF_COMMIT_DEFECT.json
  ...
```

R510 contains both the current dry-run line and unrelated/live R510 campaign artifacts. Do not treat every R510 file as equally authoritative.

## G. FROZEN R506 DISCOVERY MEASUREMENT

```text
R506/
  YIELD_INSTRUMENT.json
  BATTERY_PROBLEMS.json
  BATTERY_RAW/
  YIELD_MEASUREMENT.json
  HARVEST_RULES.json
  hermetic acceptance artifacts
```

These are frozen/measurement artifacts. Do not modify scored inputs or instrument bytes while relying on their existing measurement identity.

## H. RUNTIME STATE — NOT SOURCE CODE AUTHORITY

```text
ENGINE_RUNS/
ENGINE_RUNTIME/
TOSCANINI_UI/runslots/
TOSCANINI_UI/runqueue/
```

These are runtime/ephemeral or runtime-derived surfaces. Do not turn them into a second canonical state representation.

The private durable runtime-state branch has historically carried durable copies of runtime records; use the branch-specific authority when the current task actually depends on runtime-state evidence.

## I. PRODUCT SURFACES

```text
TOSCANINI/
TOSCANINI_UI/
toscanini/
```

These are product/UI/backend surfaces. UI must derive truth from canonical backend state and must not invent scientific status.

## J. ENGINEERING / 3D / PACKAGE PATH

```text
premium_package_factory/
discovery_fabric/engine/invention_bridge/
discovery_fabric/engine/visual_compiler/
visual-lab/
BENCHMARK_ENGINEERING_DOSSIERS/
artifacts/
```

Use `CANONICAL_MODEL_FLOW.md` to preserve the single mapping.

## K. HISTORICAL ROUND DIRECTORIES

The repository contains many:

```text
R309 ... R510
```

These are historical round evidence and implementation lineage.

Rule:

> Historical round content is evidence of what happened at that round, not automatically current architecture.

Do not revive retired implementations merely because they appear in an old round.

## L. HISTORICAL PORTFOLIO / INVENTION DIRECTORIES

Examples include:

```text
CEREVASC_*
LEAD_PORTFOLIO_4
other named invention/territory trees
```

These are portfolio/history material unless current canonical state explicitly points at them.

Do not use them as current engine authority merely because the content is polished.

## M. SCRIPTS

`scripts/` is historically very large and contains many round-specific automation files.

Current R510 dry-run authority is specifically:

```text
scripts/r510_dryrun_proof.py
scripts/r510_dryrun_record.py
scripts/r510_dryrun_repeat.py
```

Other `r510_*.py` scripts may be relevant to adjacent campaign/deployment tasks but must not be pulled into this optimization loop without evidence.

## N. TESTS

`tests/` is intentionally extensive. Historical tests remain valuable regression evidence but are not all the current control surface.

Current R510 optimization core:

```text
tests/test_r510_dryrun.py
tests/test_r510_transitions.py
tests/test_r510_diversity_adapter.py
```

Relevant attacker/calibration regression families include:

```text
test_r412_attacker_measurement.py
test_r417_attacker_calibration.py
test_r446_attacker_calibration.py
test_r487_attacker_v3.py
test_r495_v42_attacker_computes.py
```

Use them when changing shared attacker semantics. Do not run unrelated huge suites merely to create noise unless needed for regression confidence.

---

# 17. FILE ENTROPY RULES — THE ANTI-DUPLICATION CONTRACT

The repository's biggest structural risk is no longer lack of functionality; it is accumulated historical surface area plus repeated round-specific implementations.

The next chat must enforce these rules:

## 17.1 One canonical implementation per responsibility

Before creating a file:

```text
search repository
→ identify existing owner
→ inspect call graph/tests
→ only add if no existing authority can own the responsibility
```

Do not create:

```text
attack_v2.py
attack_final.py
attack_new.py
attack_fixed.py
r510_attack_v2.py
```

when `independent_attack.py` or `a2/adversarial.py` already owns the behavior.

## 17.2 One canonical continuity file

Use:

```text
HANDOFF_NEXT_CHAT_R510_MASTER.md
```

Do not create another master handoff.

## 17.3 One canonical instrument

Use:

```text
R506/YIELD_INSTRUMENT.json
```

Do not create a second funnel instrument to make the current result look better.

## 17.4 One canonical dry-run implementation

Use:

```text
discovery_fabric/engine/dry_run.py
```

Do not build a parallel fixture framework.

## 17.5 One canonical proof record

Use:

```text
R510/DRYRUN_PROOF_RECORD.json
```

Regenerate it from the measured run records; do not manually edit it.

## 17.6 Do not overwrite historical records

Historical measurements must remain historical.

If an old artifact is wrong, create a new corrective artifact if the Constitution requires a correction trail. Do not rewrite the underlying history to make a new result appear old.

## 17.7 Do not hand-edit generated registries

Find the generating authority and use it.

## 17.8 No naming by optimism

Avoid filenames such as:

```text
FINAL
WORLD_CLASS
COMPLETE
CERTIFIED
PROVEN
BEST
```

unless those labels are required by an existing authoritative schema.

---

# 18. CURRENT COMMIT / CHANGE HISTORY — MINIMUM CONTINUITY

The immediately relevant line is:

```text
4612801f  R510 transition instrumentation
↓
d4e87d1c  support-verification cliff fix
↓
13e0a3b2  regenerated proof record / transition measurement
↓
f6a990a3  attack measurement instrumentation
↓
13411bf4  A/B attack-state repeatability normalization
↓
bfbb5bf  proof record regenerated with attack measurement and run-commit provenance
```

## 18.1 `4612801f`

Observation-only transition instrumentation.

Added transition ledger and controls without changing core support/dedup/verifier semantics.

## 18.2 `d4e87d1c`

Single measured-cliff fix at `SUPPORT_VERIFICATION`.

Root problem:

```text
R453-LEAN evidence = only {system, abstract}
→ verifier item_mech_terms empty
→ overlap zero
→ clear/distinct candidates receive NOT_ENOUGH_EVIDENCE
```

Fix:

```text
lean evidence exposes frozen record mechanism/effect vocabulary deterministically
```

No threshold, verifier, or prompt weakening.

Result:

```text
P1/P3
NOT_ENOUGH_EVIDENCE → PARTIALLY_SUPPORTED
survivor_eligible = true
```

## 18.3 `13e0a3b2`

Regenerated proof record after the support fix and repaired top-level `_commit()` robustness.

## 18.4 `f6a990a3`

Added attack measurement instrumentation.

Scientific attack semantics were intentionally not changed.

## 18.5 `13411bf4`

Repeatability checker normalization for permitted timestamp-derived mechanism-space IDs.

## 18.6 `bfbb5bf`

Regenerated proof record and derived top-level `code_commit` from the runs' own recorded execution commits.

---

# 19. CURRENT UNRESOLVED PROBLEM — EXACTLY WHERE THE NEXT CHAT STARTS

The next chat should begin here:

```text
SUPPORT_VERIFICATION cliff
       ↓ FIXED
POST-FIX candidate pool
       ↓
34 candidates reach independent-attack path
       ↓
34 transport refusals
       ↓
ATTACK_INCOMPLETE
TRANSPORT_UNAVAILABLE
```

The immediate question is:

> Why does the real per-candidate independent attacker receive no dry-run fixture response even though the run-level A2 `attack` fixture exists?

Live code inspection has already established the answer:

```text
independent_attack.py
  purpose="independent_attack"
```

vs.

```text
tests/fixtures/dryrun/problems.py
  purpose_exact="attack"
```

Therefore the next coding change should be confined to the deterministic dry-run fixture coverage and/or narrowly associated attack-state measurement, after first tracing consumers.

---

# 20. NEXT CHAT — EXACT AUTOCOMMAND BOOTSTRAP

A new chat must run these checks itself. Do not ask the operator to run them.

## 20.1 Locate/verify repository

POSIX-compatible form:

```bash
export LANG=C.UTF-8 LC_ALL=C.UTF-8
REPO="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "$REPO" ] || [ ! -d "$REPO/.git" ]; then
  REPO="/home/z/my-project/hf_space"
fi
if [ ! -d "$REPO/.git" ]; then
  git clone https://github.com/prateekm1007/discovery-evidence-fabric.git "$REPO"
fi
cd "$REPO"
git fetch origin
git checkout main
git reset --hard origin/main
git status --short
git rev-parse HEAD
git rev-parse origin/main
```

Do not execute a hard reset if the environment contains uncommitted operator work that has not been classified. First capture status and preserve it according to the governance rules. The new chat must perform this classification itself.

Preferred safe baseline check:

```bash
git status --short
git diff --stat
git rev-parse HEAD
git rev-parse origin/main
```

If `HEAD != origin/main`, classify drift before touching files.

## 20.2 Read continuity sources automatically

```bash
cd "$REPO"
printf '%s\n' \
  EPISTEMIC_CONSTITUTION.md \
  GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md \
  GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md \
  GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md \
  GOVERNANCE/AUDITOR_REMEMBERED_STATE.md \
  ACTIVE_PATH.md \
  CANONICAL_MODEL_FLOW.md \
  HANDOFF_NEXT_CHAT_R510_MASTER.md
```

Then read the files programmatically using the agent's repository/file tool rather than asking the operator to paste them.

## 20.3 Verify current hashes

```bash
sha256sum \
  EPISTEMIC_CONSTITUTION.md \
  GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md \
  GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md \
  GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md \
  GOVERNANCE/AUDITOR_REMEMBERED_STATE.md \
  R506/YIELD_INSTRUMENT.json
```

Do not assume the hash in this handoff is still current if the repository has moved. The live bytes are authoritative.

## 20.4 Verify current commit lineage

```bash
git log --oneline --decorate -12
git show --stat --oneline bfbb5bfdd345037f0af84ad5823ec1c2d4d7eec4
git diff --stat 13e0a3b21364395df2a6ad540622dfface19a69e..bfbb5bfdd345037f0af84ad5823ec1c2d4d7eec4
```

## 20.5 Verify the critical attack purpose mismatch

```bash
grep -RIn --exclude-dir=.git --exclude='HANDOFF_NEXT_CHAT_R510_MASTER.md' \
  'purpose="independent_attack"' discovery_fabric tests scripts || true

grep -RIn --exclude-dir=.git \
  'purpose_exact.*independent_attack' tests/fixtures/dryrun scripts discovery_fabric || true

grep -RIn --exclude-dir=.git \
  'purpose_exact.*attack' tests/fixtures/dryrun/problems.py || true
```

The expected inspection result is that `independent_attack.py` requests `independent_attack`, while the dry-run pack presently defines `attack` but not `independent_attack`.

## 20.6 Trace all consumers of the dangerous attack fields

```bash
grep -RIn --exclude-dir=.git \
  'attack_naive_overall\|attack_state_aggregate\|attack_survived\|independent_attack_attempted\|attack_drop_transition' \
  discovery_fabric orchestrator scripts tests R510 | head -n 500
```

Do this BEFORE renaming/removing fields.

---

# 21. NEXT OPTIMIZATION WORK — ORDERED AND AUTOCOMMAND-ONLY

## Step 1 — Freeze the current baseline

Treat:

```text
bfbb5bfdd345037f0af84ad5823ec1c2d4d7eec4
```

as the current dry-run baseline unless remote state has moved.

Do not change:

- R506 yield instrument;
- scored problem manifests;
- Constitution thresholds;
- verifier semantics;
- ranking weights;
- mechanism operators;
- support fix;
- live R510 Battery2 artifacts.

## Step 2 — Audit the actual independent attack call path

Trace:

```text
EngineRun._post_rank_pipeline
→ independent_attack.independent_attack
→ mechanism_space.llm_generate
→ FixtureTransport.match
→ LLMCallResult
→ persisted INDEPENDENT_ATTACK_{key}.json
→ attacker_calibration.apply_at_consumption
→ candidate selection / downstream state
```

The purpose string must be recorded and verified.

## Step 3 — Verify whether only fixture coverage is missing

Do NOT immediately patch code.

First demonstrate that:

```text
matched `independent_attack` fixture
```

would be accepted by the current production parser without code changes.

If the parser/engine path itself has a defect, classify it separately.

## Step 4 — Add the minimal independent-attack fixture

Only after the trace confirms fixture coverage is the single defect:

- add `purpose_exact="independent_attack"` to the existing controlled fixture pack;
- provide response text matching `independent_attack.py`'s exact parser contract;
- preserve existing A/B deterministic identity rules;
- do not reuse incompatible A2 format blindly;
- do not change the actual attack algorithm.

The fixture should include deterministic cases representing real independent-attack outcomes.

At minimum, the fixture design should cover:

```text
transport success
valid SURVIVE/RISK path
valid KILL path through existing grounding rules
```

The test fixture must remain explicitly controlled test material.

## Step 5 — Add true end-to-end dry-run coverage

Add a test that executes an actual `EngineRun(... dry_run=True, fixture_transport=...)` and proves:

```text
purpose=independent_attack
→ fixture matched
→ independent_attack executed
→ parser returned structured items
→ existing attack evaluator determined result
→ result persisted
→ run did not call live/paid transport
```

This must be different from the existing direct A2 test.

## Step 6 — Preserve failure behavior

Also test:

```text
no independent_attack fixture
→ PROVIDER_UNAVAILABLE
→ TRANSPORT_UNAVAILABLE
→ ATTACK_INCOMPLETE
→ never KILLED
→ never SURVIVED
```

This protects the infrastructure/science boundary.

## Step 7 — Audit attack-state naming

Only if consumer tracing demonstrates a real semantic ambiguity, introduce:

```text
attack_requested
attack_execution_started
attack_execution_completed
```

or an equivalently minimal state distinction.

Do not create a large state-machine rewrite.

## Step 8 — Audit the two-path attack nomenclature

Ensure the proof record can tell readers whether a result refers to:

```text
run-level A2 attack
```

or:

```text
per-candidate independent attack
```

A field like `attack_naive_overall` must never be silently interpreted as the per-candidate independent pool result.

## Step 9 — Run the identical 3 × A/B battery

Fresh output directories only.

No tuning between A/B.

No problem changes.

No instrument changes.

No live calls.

## Step 10 — Compute the post-fix funnel from durable bytes

Recompute:

```text
fresh_submitted
premise_coherent
evidence_verified
mechanisms_found
candidates_generated_distinct
attack_survivors
contradiction_survivors
experimentally_discriminated
mutated_survivors
buyer_ready
```

## Step 11 — Classify the attack transition

Separate:

```text
not reached
requested but not executed
transport unavailable
execution incomplete
scientifically killed
scientifically survived
unknown
```

Do not collapse infrastructure states into scientific states.

## Step 12 — Identify the next real cliff

Only after the independent attack actually executes should the next scientific bottleneck be named from measurement.

Do not assume:

```text
ATTACK = next scientific cliff
```

until the attack is truly measurable.

## Step 13 — Apply exactly one scientific/engineering cliff fix

The fix must target the largest measured dropout named by the frozen funnel measurement.

No unrelated cleanup in the same optimization change.

## Step 14 — Re-run identical measurement

Compare:

```text
before
vs
same battery after fix
```

The improvement must be evidenced by durable bytes, not narrative.

## Step 15 — Rebuild proof record

Derive publication record from actual measured run outputs.

Preserve execution commit vs publication commit distinction.

## Step 16 — Run test suite

At minimum:

```bash
python3 -m pytest tests/test_r510_dryrun.py tests/test_r510_transitions.py tests/test_r510_diversity_adapter.py -q
```

Run relevant attacker/calibration regressions if shared modules were changed.

## Step 17 — Push automatically

After a coherent change set:

```bash
git add ...
git commit -m "R510 — <honest measured change>"
git push origin main
git fetch origin
git rev-parse HEAD
git rev-parse origin/main
```

No operator push step.

## Step 18 — Final acceptance

A round may be reported complete only when:

```text
code tested
+ fresh E2E proof
+ durable funnel
+ largest cliff identified
+ one fix applied
+ identical rerun
+ repeatability established
+ provenance exact
+ remote push verified
```

Otherwise report the actual incomplete state.

---

# 22. DO NOT REPEAT THESE ALREADY-COMPLETED ITEMS

A new chat MUST NOT waste time redoing already-settled work unless a new regression is found.

Do not redo solely for continuity:

- support-verification root cause discovery;
- support fix implementation;
- support cliff measurement;
- proof-record stale commit bug fix;
- current R510 transition ledger instrumentation;
- dry-run fixture precedence design;
- deterministic ranking design;
- direct A2 fixture test;
- basic cemetery sandbox control;
- A/B candidate-id normalization.

These are established current history.

The new task is to make the real independent-attack path measurable, then continue the measured one-cliff loop.

---

# 23. UNRELATED / SEPARATE CURRENT WORK THAT MUST NOT BE COLLAPSED INTO THIS DRY-RUN TASK

## R510 live battery2

`R510/BATTERY2_STATUS.json` currently describes a separate live blind-yield battery with six submitted problems and owner/custody dependencies.

That line must remain separate from the dry-run fixture optimization.

Do not mutate:

```text
R510/BATTERY2_PROBLEMS.json
R510/BATTERY2_SESSIONS.json
R510/YIELD2_* live battery state
```

unless the operator explicitly changes the active task.

## Production deployment line

Production deployment records and runtime-state branches are separate from the controlled dry-run measurement unless the user explicitly asks to audit deployment/product behavior.

## Historical R-cycles

Do not reopen R400/R401/R412/R450/etc. simply because the code references them. Their records are provenance/history. Use current canonical implementations and current tests unless the current task explicitly requires historical reconstruction.

---

# 24. SECRETS / CREDENTIAL CUSTODY

Constitution Articles LXXIII and LXXVI govern credential custody.

The rule is:

```text
secret values
→ vault / HF Space secret surface
→ fingerprints only in records
```

Never put secret values in:

- repository;
- worklog;
- proof record;
- test output;
- chat response;
- commit message.

Rotation is a CEO-only action.

Do not rotate a credential merely because the auditor sees a stale or exposed fingerprint.

If a required credential value is absent from the current environment, type the state honestly and use the operator's allowed word/supply mechanism when necessary.

Current dry-run optimization requires no paid credential because `FixtureTransport` must remain isolated from live provider credentials.

---

# 25. REALITY / DISCOVERY STATUS — DO NOT OVERCLAIM

The current dry-run evidence proves useful engineering observations about orchestration and measurement.

It does NOT establish:

- world-class discovery;
- repeated discovery capability;
- blind fresh-problem generalization;
- real physical validation;
- repeated reality validation;
- buyer acceptance;
- commercial validation;
- patentability;
- freedom to operate.

The current controlled dry-run problems are explicitly machine-authored and therefore are not admissible as Article LXXIX blind capability evidence.

The current 34 attack transport failures do not prove that candidates are scientifically bad.

The current support-fix success does not prove the candidates are inventions.

The current ranked portfolio does not prove candidate quality.

---

# 26. CURRENT USER STATUS — DONE / ACTIVE / LEFT

## Done

- [x] Constitution v2.10.1 is current and reread for this audit.
- [x] Auditor governance is current and reviewed.
- [x] Remote main is the current repository authority.
- [x] Support-verification cliff was reproduced, fixed, and rerun.
- [x] P1/P3 moved from `NOT_ENOUGH_EVIDENCE` to `PARTIALLY_SUPPORTED` without weakening verification.
- [x] P2 cemetery control remains intact.
- [x] Transition instrumentation exists.
- [x] Attack measurement instrumentation exists.
- [x] Attack transport failure is typed rather than silently turned into a scientific kill.
- [x] Six A/B dry-run runs were executed at `f6a990a3...`.
- [x] Repeatability was repaired and is PASS for P1/P2/P3.
- [x] Proof record was regenerated from run-owned commit provenance.
- [x] Current remote head is `bfbb5bf...`.
- [x] Latest reported test result is `47 passed, 0 failed`.
- [x] No live/paid calls in the dry-run proof.
- [x] No world-class claim.

## Active / immediately next

- [ ] Audit exact `independent_attack` transport fixture mismatch.
- [ ] Trace all consumers of `attack_naive_overall` and `independent_attack_attempted`.
- [ ] Add the minimal dedicated `independent_attack` deterministic fixture if confirmed necessary.
- [ ] Add true EngineRun-level independent-attack E2E tests.
- [ ] Re-run the identical 3 × A/B dry-run battery.
- [ ] Compute actual attack outcomes from durable bytes.
- [ ] Identify the next real measured scientific cliff.
- [ ] Apply one and only one cliff-targeted fix.
- [ ] Rerun the same battery and measure improvement.
- [ ] Regenerate proof record.
- [ ] Push and verify remote identity.

## Remaining broader dependencies

- [ ] Independent attack must become actually measurable before an attack-related scientific bottleneck can be called.
- [ ] Blind fresh-problem measurement remains required for genuine capability claims.
- [ ] Reality-loop evidence remains incomplete.
- [ ] Buyer evaluation remains incomplete.
- [ ] Production/deployment behavior remains a separate acceptance layer.

---

# 27. ACCEPTANCE CRITERIA FOR THE NEXT ROUND

The next round is GREEN only when all of these are machine-verifiable:

```text
1. current baseline hash is known
2. Constitution hash/version is known
3. current governance hashes are known
4. independent_attack purpose is exercised through the real EngineRun path
5. fixture transport is deterministic
6. unmatched fixture still fails closed
7. no live/paid calls occur in the dry-run
8. independent attack is parsed by the real production parser
9. attack result is determined by the existing evaluator
10. transport failure cannot become KILLED
11. attack execution is distinguishable from attack request if ambiguity is material
12. A/B repeatability passes
13. full funnel is regenerated from durable bytes
14. scientific cliff is chosen from measurement, not assumption
15. exactly one cliff fix is applied
16. identical battery reruns
17. before/after change is measured
18. tests pass
19. proof record carries the actual execution commit
20. publication is pushed to origin/main
21. HEAD == origin/main
22. worktree clean
23. no world-class claim unless the Constitution's full evidence standard is actually met
```

---

# 28. STOP CONDITIONS — WHEN THE CODER MUST NOT “IMPROVE” FURTHER

Stop coding and report the blocker when:

- the remaining problem is owner-only supply/registration;
- the issue is a provider outage that cannot be repaired in code without changing scientific scope;
- the next change would alter a frozen scored instrument;
- a battery has entered a prohibited tuning state;
- evidence for the requested fix is missing;
- a required reality experiment needs physical-world access not available to the system;
- a deployment identity is mismatched and measuring another build would invalidate the result;
- the next proposed change is not tied to a measured funnel dropout.

Do not convert a blocker into a speculative feature request.

Do not manufacture certainty to keep the loop moving.

---

# 29. NEW CHAT FIRST TEN ACTIONS

The new chat's first actions are deterministic:

```text
1. Locate repository and verify main/origin.
2. Read this handoff from the live remote bytes.
3. Read Constitution in full.
4. Read auditor self-governance + blindspot + remembered state + audit protocol.
5. Read ACTIVE_PATH and CANONICAL_MODEL_FLOW.
6. Verify current commits and recent history.
7. Read current R510 proof record and dry-run tests/fixtures.
8. Trace `independent_attack` purpose through EngineRun → fixture transport.
9. Trace `attack_naive_overall` / `independent_attack_attempted` consumers.
10. Only then execute the next measured dry-run optimization directive.
```

No operator file paste is required.

No manual terminal work is required from the operator.

---

# 30. FINAL OPERATING PRINCIPLE

The project is no longer blocked by lack of instrumentation at the current layer. The immediate job is to make the **real independent attack path executable and measurable**, without weakening scientific standards.

The correct sequence is:

```text
CURRENT STATE

36 generated
2 cemetery-control losses
0 support losses
34 independent-attack transport refusals

        ↓

FIX ONLY THE CONFIRMED DRY-RUN INDEPENDENT-ATTACK COVERAGE GAP

        ↓

RUN THE SAME 3 × A/B BATTERY

        ↓

MEASURE ACTUAL ATTACK OUTCOMES

        ↓

ONLY THEN IDENTIFY THE NEXT SCIENTIFIC DROP

        ↓

ONE CLIFF FIX

        ↓

SAME BATTERY

        ↓

COMPARE
```

Do not skip directly from “34 transport failures” to “attack algorithm is bad.”

Do not skip from “47 tests pass” to “world-class.”

Do not skip from “ranked portfolio exists” to “discovery.”

Do not create parallel architecture to solve a problem already owned by an existing module.

Do not create another handoff file.

Do not ask the operator to reconstruct context by copy/pasting old files.

**The new chat should be able to begin entirely from the remote repository, this handoff, the Constitution, and the existing canonical artifacts.**

---

# 31. VERIFIED FILE / AUTHORITY TABLE AT HANDOFF

| Area | Canonical file / directory | Current role | Mutation policy |
|---|---|---|---|
| Constitution | `EPISTEMIC_CONSTITUTION.md` | supreme project law | only constitutional amendment process |
| Auditor governance | `GOVERNANCE/` | auditor behavior / continuity | only governance-purpose changes |
| Production path | `ACTIVE_PATH.md` | production-path documentation authority | update only when path changes |
| Invention → 3D | `CANONICAL_MODEL_FLOW.md` | canonical model-flow binding | update when code-bound mapping changes |
| Canonical state | `CANONICAL_STATE/` | durable canonical state | authority-specific only |
| Yield instrument | `R506/YIELD_INSTRUMENT.json` | frozen discovery-capability measurement | immutable for frozen measurement |
| R510 dry-run proof | `R510/DRYRUN_PROOF_RECORD.json` | current controlled dry-run proof record | regenerate from durable proof runs |
| Dry-run engine | `discovery_fabric/engine/dry_run.py` | deterministic fixture + funnel/portfolio measurement | minimal current-round changes only |
| Run conductor | `discovery_fabric/engine/run.py` | real D6 EngineRun path | do not duplicate |
| A2 attacker | `discovery_fabric/a2/adversarial.py` | run-level A2 gauntlet | preserve separate contract |
| Independent attacker | `discovery_fabric/engine/independent_attack.py` | per-candidate independent attack | immediate next attack-path authority |
| Engineering attack | `discovery_fabric/engine/engineering_attack.py` | engineering attack / repair / selection | downstream technical authority |
| Attack calibration | `discovery_fabric/engine/attacker_calibration.py` | calibration consumption gate | do not bypass |
| Mechanism generation | `discovery_fabric/engine/mechanism_space.py` | candidate generation/support/dedupe | canonical mechanism-space authority |
| Transition measurement | `discovery_fabric/engine/transition_trace.py` | R510 transition ledger | measurement only unless evidence says otherwise |
| Dry-run fixtures | `tests/fixtures/dryrun/problems.py` | machine-authored controlled inputs | not discovery evidence |
| Dry-run proof runner | `scripts/r510_dryrun_proof.py` | real EngineRun proof execution | current R510 runner |
| Proof record generator | `scripts/r510_dryrun_record.py` | proof-record assembly | generated, do not hand-edit output |
| Repeatability | `scripts/r510_dryrun_repeat.py` | A/B comparison | deterministic comparison authority |
| R510 dry-run tests | `tests/test_r510_dryrun.py` | current dry-run controls | extend for independent_attack E2E |
| R510 transition tests | `tests/test_r510_transitions.py` | candidate transition controls | preserve taxonomy |
| R510 diversity tests | `tests/test_r510_diversity_adapter.py` | diversity/mapping controls | preserve distinctness semantics |
| Runtime output | `ENGINE_RUNS/` | ephemeral run state | do not treat as canonical code |
| Live R510 battery | `R510/BATTERY2_*` | separate live blind-yield campaign | do not perturb for dry-run task |
| Historical rounds | `R*/` | lineage/evidence | historical; do not revive as current authority |

---

# 32. HANDOFF INTEGRITY NOTE

This handoff intentionally contains enough architectural, governance, provenance, and current-bottleneck information that a new chat can reconstruct the active task without the operator copying old files into the chat window.

The handoff itself is a continuity aid, not a substitute for live verification.

When a new chat starts:

```text
READ HANDOFF
→ RE-READ AUTHORITIES
→ VERIFY REMOTE BYTES
→ RECONSTRUCT ACTIVE STATE
→ CONTINUE FROM CURRENT BOTTLENECK
```

The remote repository remains the ultimate evidence surface for the code and committed artifacts.

---

# CURRENT AUDIT — 2026-09-20

## First broken transition

Fresh durable runtime runs showed real GLB and technology-package artifacts reaching `runtime-state-hf`, while the strict visual certification chain lost its persisted identity/current-generation anchors across the durable boundary.

The first measured cliff is:

`FRESH RUN ARTIFACTS → DURABLE SNAPSHOT → PERSISTED VISUAL IDENTITY CHAIN`

The omitted files were:

- `MODEL/ARTIFACT_IDENTITY.json`
- `MODEL/ARTIFACT_IDENTITY.sha256`
- `MODEL/DESIGN_LINEAGE.json`
- `MODEL/GEOMETRY_SPEC.json`

`toscanini/visual_join.py` requires the persisted identity chain and an independent current-generation anchor. The CIO-carried identity is diagnostic only and cannot certify the artifact after restart.

## One fix

`toscanini/durable.py::_run_dir_files()` now persists those four `MODEL/*` files whenever they exist, alongside the canonical GLB and presentation records.

A regression was added to `tests/test_r423_durable_incremental.py` asserting that all four anchors survive a durable snapshot.

The compare from the pre-audit `origin/main` tip contains only those two changed paths.

## Verification

Static AST/reproduction validation of the changed selector and regression body passed.

GitHub Actions was triggered for the code changes, but the certification workflow failed in its initial path-classification job before the test/certification stages executed. Therefore this audit does not claim CI verification.

The current remote `main` is:

`1b3fe776059445c41d790c886e2239096a5c04d1`

No production deployment of this fix has been proven. The committed historical deployment record still names engine SHA:

`0ad82593d79999029f0d3529e2407995e16f12e1`

External production identity remains `UNKNOWN`.

## Current demo state

The durable runtime evidence proves the system can produce a canonical GLB and a technology package on a fresh run. The current code repair closes the durability hole that could erase the certification anchors on restart.

The post-fix production vertical slice is still unproven until the repaired commit is deployed and a fresh ordinary user request verifies:

`survivor → bridge → 3D → package → CIO → API → frontend`

The processing-time UI remains partial: current-stage/activity presentation exists, but a telemetry-backed remaining-time estimate is not yet established.

The larger scientific gaps remain unchanged: fresh mechanism yield, attacker calibration, reality validation, learning, buyer-package validation, and cross-domain/generalized discovery qualification.

