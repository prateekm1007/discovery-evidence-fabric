# TOSCANINI / DISCOVERY-EVIDENCE-FABRIC — MASTER HANDOFF TO NEXT CHAT

**Purpose:** Give a new auditor/coder chat enough authoritative context to continue the project without asking the operator to repaste old files, while explicitly preventing architectural entropy, duplicated work, stale assumptions, or accidental reversal of settled decisions.

**Date of handoff:** 2026-09-07
**Author:** External AI auditor continuity handoff
**Important:** This document is a continuity aid. It is NOT authority over the Constitution, current GitHub state, deployment state, sealed artifacts, or fresh evidence. Always re-verify live state.

---

# 0. FIRST INSTRUCTION TO THE NEXT CHAT

Before doing any substantive audit, planning, or coding:

1. Read the current `EPISTEMIC_CONSTITUTION.md` in full.
2. Read all auditor governance files in `GOVERNANCE/` that are currently authoritative:
   - `GOVERNANCE/README.md`
   - `GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md`
   - `GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md`
   - `GOVERNANCE/AUDITOR_REMEMBERED_STATE.md`
   - `GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md`
3. Read `ACTIVE_PATH.md` in full.
4. Read the latest relevant worklog/directive and current commit history.
5. Verify the current engine repository `main` SHA, current buyer repository `main` SHA, current deployment identity, active branches/PRs, and current production health.
6. Reconstruct the current project state/direction before issuing new instructions.
7. The **coder must remind the auditor to read the governance files**.
8. The **auditor must remind the coder to read the full Constitution before coding**.
9. Before a final coder commit, the coder must read the full Constitution again.
10. Before an acceptance verdict, the auditor must reread the applicable governance, remembered-state, and blind-spot entries.

Do not start by coding. Establish the live baseline first.

---

# 1. AUTHORITY ORDER

When artifacts conflict, use this order:

1. `EPISTEMIC_CONSTITUTION.md`
2. `GOVERNANCE/AUDITOR_SELF_GOVERNANCE_v1.md`
3. `GOVERNANCE/AUDITOR_BLINDSPOT_REGISTER.md`
4. `GOVERNANCE/AUDIT_LOOP_PROTOCOL_v1.md`
5. `ACTIVE_PATH.md`
6. current authoritative repository/deployment state
7. current worklog/directives
8. screenshots, reports, handoffs
9. remembered conversational context

The Constitution is the highest authority. Governance controls how the auditor audits; it cannot weaken the Constitution. Remembered state prevents entropy but is never evidence.

The project has repeatedly suffered from stale local work, stale handoffs, built-but-unwired infrastructure, and demo artifacts being mistaken for fresh-run product behavior. Assume these can recur.

---

# 2. NON-NEGOTIABLE PROJECT MISSION

Build a **world-class AI discovery and invention machine** that turns difficult user problems into credible technology packages that a real company can:

- evaluate;
- license;
- build;
- acquire; or
- commission the decisive experiment for.

Public product:

`https://toscanini-engine-docker.onrender.com/`

Toscanini is **not a patent court**.

Its job is to:

`DISCOVER → INVENT → DEVELOP → EXPLAIN → VISUALIZE → CHALLENGE → EVOLVE → PACKAGE`

Formal patentability, claim drafting, infringement/FTO, and legal opinions are downstream work for qualified legal counsel.

Do not optimize the product into a rejection engine.

---

# 3. CORE PRODUCT CONTRACT

Every valid user problem should create a genuine discovery/invention attempt.

The creative loop is:

```text
USER PROBLEM
   ↓
PROBLEM UNDERSTANDING
   ↓
EVIDENCE ACQUISITION
   ↓
MECHANISM ANALYSIS
   ↓
INVENTION 01
   ↓
CHALLENGE / ATTACK
   ↓
DIAGNOSE FAILURE OR WEAKNESS
   ↓
30-YEAR EVOLUTION
   ↓
FRONTIER TECHNOLOGY TRANSFER
   ↓
CAUSAL ARCHITECTURE REDESIGN
   ↓
INVENTION 02+
   ↓
ENGINEERING / PHYSICS
   ↓
3D REPRESENTATION
   ↓
EXPERIMENT
   ↓
TECHNOLOGY PACKAGE
   ↓
REAL BUYER EVALUATION / REAL EXPERIMENT
   ↓
REALITY → LEARNING → NEXT DISCOVERY
```

A failed architecture is not equivalent to “no invention.” Failure is information that should feed evolution when the territory remains worth exploring.

However, never fabricate evidence, measurements, physical validation, prior art, or simulation results merely to satisfy the product contract.

The system may invent hypotheses and architectures. It must distinguish generated/inferred content from evidence-supported or experimentally verified content.

---

# 4. IMPORTANT DISTINCTION: CREATIVE AUTHORITY VS VERIFICATION AUTHORITY

The previous product behavior allowed verification/attack to hijack creativity.

The intended model is:

```text
CREATIVE ENGINE
    ↓
architectures / hypotheses
    ↓
VERIFICATION ENGINE
    ↓
status / objections / maturity / experiment
    ↓
CREATIVE ENGINE
    ↓
evolution
```

Not:

```text
VERIFIER KILLS ONE CANDIDATE
→ ENTIRE USER PROBLEM ENDS
```

The attacker was empirically measured at **FPR 1.00 / TPR 1.00** on a sealed 40-case corpus: a universal killer. Therefore its objections are preserved but its KILL verdict is not authoritative while uncalibrated. The existing R417 abstain/escalate gate is deliberate and must not be bypassed for demo cleanliness.

This is not weakening verification. It is refusing to assign authority to an instrument whose discriminative power was measured to be zero on the calibration corpus.

---

# 5. TWO-REPOSITORY ARCHITECTURE

## Engine repository

`https://github.com/prateekm1007/discovery-evidence-fabric`

Role: the factory.

It contains:

- discovery machinery;
- retrieval/evidence;
- mechanism synthesis;
- candidate/invention generation;
- attack and verification;
- evolution;
- physics/equations;
- CAD/engineering;
- 3D bridge;
- runtime/server/worker;
- provider routing;
- durability;
- provenance;
- tests;
- governance;
- release-chain machinery.

## Buyer/technology-transfer repository

`https://github.com/prateekm1007/technology-transfer-portfolio-15`

Role: **buyer-distribution authority for released technology packages**.

The Buyer repo is the final authority for what an external buyer actually receives. Engine-side copies, local workspaces, and summaries are not final buyer truth.

The historical release chain is:

```text
ENGINE REPO
  → CANONICAL RELEASE MANIFEST
  → PORTFOLIO REPO
  → BUYER ZIP
  → VERIFICATION
```

The portfolio release chain is protected by `CANONICAL_RELEASE_MANIFEST.json` and the engine `ENGINE_RELEASE_REGISTRY.json` where applicable.

---

# 6. CURRENT AUTHORITATIVE STATE AT HANDOFF CREATION

The current remote `main` of `discovery-evidence-fabric` was verified at:

`a3b602a71f0f1e750031366a3f31fca71632841e`

with commit message:

`Document durable auditor remembered-state checkpoint`

This means the remote canonical Constitution still needs to be treated as **v2.1.0** unless a newer constitutional amendment has been formally committed and verified.

Canonical Constitution hash currently observed remotely:

`084c8dd5f8f7218fdf3aa70ed2c8f8b6edd2c772`

**Important discrepancy:** the coder's local R419 work reported a drafted English-only amendment as `Constitution v2.2.0`, but that draft was uncommitted in the local workspace at the time of the handoff. Therefore:

- do NOT treat v2.2.0 as authoritative yet;
- do NOT assume Article LXX exists in remote `main`;
- inspect live remote state first;
- if the English-only amendment is to be adopted, use the formal Constitution amendment path; never silently modify the constitutional text.

This discrepancy itself is evidence of why remembered state and live state must be separated.

---

# 7. ACTIVE PRODUCTION PATH

The current `ACTIVE_PATH.md` describes the canonical runtime loop:

```text
PROBLEM → EVIDENCE → MECHANISM → CANDIDATES → ATTACK → INVENTION DIAGNOSTIC
→ IMPROVE → TECHNICAL EVALUATION → 3D DESIGN → DECISIVE EXPERIMENT
→ ENGINEERING DOSSIER → BUYER PACKAGE
```

Runtime EngineRun stage order:

```text
RETRIEVE
→ FREEZE
→ SYNTHESIZE
→ VERIFY
→ MULTI_SOURCE_DISCOVERY
→ COLLISION
→ ATTACK
→ CONTRADICTION
→ KILLER_EXPERIMENT
→ ADJUDICATION
→ CLASSIFY
→ NEXT_BEST_ACTION
→ RANK
```

The reality loop is also part of the established architecture:

```text
REAL OBSERVATION
→ REALITY MODEL
→ DESIGN/REALITY COMPARISON
→ DISCREPANCY
→ CAUSAL HYPOTHESIS
→ TECHNICAL STATE UPDATE
→ MUTATION
→ NEW DESIGN
→ RE-EVALUATION
```

The core product and engineering modules currently include:

- `toscanini/problem_builder.py`
- `toscanini/server.py`
- `toscanini/worker.py`
- `toscanini/run_state.py`
- `toscanini/cio.py`
- `toscanini/gateway.py`
- `toscanini/bridge_gate.py`
- `toscanini/durable.py`
- `toscanini/counsel.py`
- `toscanini/run_qa.py`
- `discovery_fabric/engine/*`
- `discovery_fabric/connectors/*`
- `discovery_fabric/a2/*`
- `discovery_fabric/engine/cad_pipeline.py`
- `discovery_fabric/engine/equations.py`
- `discovery_fabric/engine/experiment_selector.py`
- `premium_package_factory/*`
- `TOSCANINI_UI/webapp/*`

Do not revive archived superseded modules casually. `ACTIVE_PATH.md` is the starting point for what is live.

---

# 8. FILE-STRUCTURE / ANTI-ENTROPY MAP

The engine repository has accumulated a lot of historical round material. The purpose of this structure is to stop old rounds from becoming shadow implementations.

## Root governance / authority files

```text
EPISTEMIC_CONSTITUTION.md        ← highest authority
ACTIVE_PATH.md                   ← canonical production path
HANDOFF...                       ← continuity only, never authority
GOVERNANCE/                      ← auditor governance only
```

## `GOVERNANCE/`

```text
README.md
AUDITOR_SELF_GOVERNANCE_v1.md
AUDITOR_BLINDSPOT_REGISTER.md
AUDIT_LOOP_PROTOCOL_v1.md
AUDITOR_REMEMBERED_STATE.md
```

These govern the **auditor**, not the application's runtime logic.

Do not put product logic into governance files.

## `toscanini/`

This is the production product/runtime facade.

Important responsibilities:

```text
problem_builder.py    user problem → structured problem/evidence-bound input
server.py             HTTP/API/product boundary
worker.py             one discovery run end-to-end
run_state.py          persisted UI/run projection
cio.py                canonical invention object projection
bridge_gate.py        automatic invention → artifact/package bridge
 gateway.py           transport/provider entry
 durable.py           durable state snapshots
 counsel.py            legal-counsel export, not buyer package authority
```

Do not duplicate these responsibilities elsewhere.

## `discovery_fabric/`

This is the engine/factory core.

Major conceptual zones:

```text
discovery_fabric/a2/
    retrieval/synthesis/adversarial legacy-active pieces as mapped by ACTIVE_PATH

discovery_fabric/connectors/
    external source acquisition

discovery_fabric/source_registry/
    source identity/status/coverage

discovery_fabric/engine/
    canonical current engine stages and engineering/reality machinery

discovery_fabric/prior_art_v2/
    prior-art/collision subsystem

discovery_fabric/engine/cad_pipeline.py
    engineering geometry authority

discovery_fabric/engine/equations.py
    analytical technical evaluation

discovery_fabric/engine/experiment_selector.py
    decisive experiment selection
```

Use the canonical module for the stage rather than creating a second implementation.

## `premium_package_factory/`

Buyer/engineering package generation and package templates.

This remains important for released package quality.

Do not confuse it with `toscanini/counsel.py`.

## `TOSCANINI_UI/webapp/`

The public frontend.

Current conceptual contract:

```text
CONVERSATION
→ DESIGN / 3D
→ RESULT
```

The website should not reconstruct backend truth.

The frontend receives the Canonical Invention Object / run projection and renders it.

## `R*/`

Many round directories and measurements exist.

Treat round artifacts as historical evidence unless `ACTIVE_PATH.md` explicitly keeps them active.

Never edit sealed historical artifacts to make a new result prettier.

## `BENCHMARK_ENGINEERING_DOSSIERS/`

Benchmark/reference corpus.

It is useful for independent checks and baseline comparison.

Do not allow benchmark-specific code to become a hidden production shortcut.

## `archive/`

Historical material preserved for reproducibility.

Do not resurrect it merely because a newer implementation has a regression.

First identify the current canonical implementation and decide whether a specific archived artifact is needed as evidence.

---

# 9. THE MOST IMPORTANT 3D ARCHITECTURE

The 3D experience has been a recurring source of false completion claims.

The settled toolchain is:

### Engineering geometry

**CadQuery + OCP/OCCT**

Authority for engineering geometry.

### Visual/rendering layer

**Blender 5.2 LTS**

Free/open-source visualization and rendering layer. Blender is not the engineering or physics authority.

### Browser

**Three.js / React Three Fiber**, consuming GLB/glTF.

### Fixed pipeline

```text
INVENTION
→ ENGINEERING SPECIFICATION
→ CadQuery/OCP/OCCT
→ MEASURE
→ GLB
→ Blender presentation/rendering where required
→ PNG renders
→ Three.js/R3F
→ WEB
```

Conceptual inventions:

```text
INVENTION
→ CAUSAL/SYSTEM GRAPH
→ Blender 3D visualization
→ conceptual GLB
→ Three.js
```

Do not introduce a runtime choice among multiple competing 3D engines.

Do not make Blender the engineering truth source.

Do not make Blender the physics validation source.

---

# 10. 3D PRODUCT CONTRACT

**Every representable invention must have a visual artifact.**

Preferred classifications:

- `ENGINEERING_3D`
- `SYSTEM_3D`
- `CONCEPTUAL_3D`
- `PROCESS_3D`
- `NOT_VISUALIZABLE` only when genuinely justified

Important principle:

> We are not allowed to fabricate engineering truth, but we are expected to visualize the invention.

Therefore:

```text
engineering geometry exists
→ ENGINEERING_3D

engineering geometry not yet earned but invention is visualizable
→ CONCEPTUAL_3D / SYSTEM_3D / PROCESS_3D
```

A failed CAD build is a **recoverable engineering defect**, not evidence that the invention does not deserve a visual representation.

---

# 11. KNOWN 3D FAILURE HISTORY

A fresh solar invention repeatedly produced:

```text
INVENTION
→ bridge
→ no 3D
```

and the bridge eventually exposed:

`CONCEPTUAL_BUILD_FAILURE: No module named 'scipy'`

The root cause was traced to a trimesh `face_colors` path that indirectly required SciPy. The coder removed the SciPy dependency from that coloring path and added adversarial enforcement. 43 bridge tests passed in the relevant local round.

Blender 5.2.1 LTS was confirmed available and headless rendering was tested locally.

The coder also found and fixed:

- Z-up/raw-coordinate orientation problem;
- empty section render due to bad cutter geometry;
- cutter swallowing entire model;
- section cap coloring/frame issues.

A live P-07 browser acceptance passed with:

- interactive 3D;
- downloads;
- live parameter rebuild;
- essay beside model.

However, a fresh generated solar run still had an earlier provider/structured-generation blocker, so **do not claim fresh-run invention → 3D → package is fully proven until a fresh production run passes it.**

---

# 12. WORLD-CLASS WEBSITE EXPERIENCE

The target is a calm, high-quality, Claude-influenced research/invention workspace.

Do NOT clone Claude branding.

Use the product lesson:

**calm conversation on the left/center + dedicated artifact surface on the right.**

Toscanini's artifact is the invention itself.

## Landing

```text
Toscanini                                  Discovery ready

             DISCOVER. INVENT. ANYTHING.

        What problem should Toscanini investigate?

        ┌──────────────────────────────────────┐
        │ Describe a real technical problem... │
        │                            [Discover]│
        └──────────────────────────────────────┘
```

## Result

```text
LEFT / CENTER

What Toscanini invented
technical essay

Why it could work

What changed

Frontier capability transferred

Evidence

What could kill it

Decisive experiment

RIGHT

THE INVENTION
large 3D model

GEN 1 / GEN 2 / GEN 3
Explore / Section / Explode
```

Do not expose raw JSON or the complete internal audit log as the main user experience.

Raw provenance remains inspectable through an audit/evidence surface.

---

# 13. THE TECHNICAL ESSAY

Every invention should have a strong technical narrative generated from the canonical invention state.

Required sections:

1. **What Toscanini invented**
2. **Why it could work**
3. **What is genuinely different**
4. **Frontier capability transferred**
5. **How the architecture works**
6. **What evidence establishes**
7. **What remains unknown**
8. **What could kill it**
9. **Decisive experiment**
10. **How it could be built**

Do not show internal JSON as primary prose.

---

# 14. GENERATION-LINEAGE EXPERIENCE

When evolution happens:

```text
GEN 1 → challenged
GEN 2 → evolved
GEN 3 → current
```

The user should be able to select a generation and see:

- corresponding 3D artifact;
- corresponding essay/explanation;
- challenge that caused the change;
- causal delta;
- frontier capability transfer;
- maturity.

`WHAT CHANGED?` must connect the textual causal change to the highlighted 3D component where possible.

---

# 15. CANONICAL INVENTION OBJECT

The backend must be the single source of client-visible truth.

Conceptually:

```text
CIO
├── identity
├── problem
├── invention
├── maturity
├── generations
├── evidence
├── engineering
├── geometry
├── visualization
├── simulation
├── attack
├── experiment
├── reality_loop
├── downloads
└── provenance
```

The frontend must not infer maturity, evidence counts, simulation status, validation, pass/fail, or invention identity.

Website, PDF, ZIP, 3D, experiment plan, and package metadata should derive from the same canonical invention state or a traceable versioned derivative.

---

# 16. PACKAGE STANDARD

The primary product is the **Technology Package**, not the counsel export.

For a physical invention, the ideal package contains approximately:

```text
TECHNOLOGY_PACKAGE/
├── 00_EXECUTIVE_SUMMARY.pdf
├── 01_TECHNICAL_ESSAY.pdf
├── 02_ENGINEERING_DEFINITION.pdf
├── 03_EVIDENCE/
├── 04_CAUSAL_ARCHITECTURE/
├── 05_SIMULATION/
├── 06_DECISIVE_EXPERIMENT/
├── 07_MANUFACTURING/
├── 08_3D/
│   ├── hero.glb
│   ├── section.glb
│   ├── exploded.glb
│   ├── hero.png
│   ├── section.png
│   └── exploded.png
├── 09_REPRODUCTION/
└── MANIFEST.json
```

Exact naming may follow existing release conventions, but the artifact classes should exist where applicable.

Separate:

- buyer technology package;
- engineering working package;
- counsel package;
- raw audit/provenance artifacts.

Do not call a counsel ZIP the finished buyer product.

---

# 17. LEGAL BOUNDARY

Use a button such as:

**Prepare for IP counsel**

with language such as:

> Technical evidence and provenance for formal legal review.

Do not say:

- patentable;
- patent guaranteed;
- patent cleared;
- FTO confirmed.

unless supplied as counsel-derived information and explicitly attributed as such.

---

# 18. RETRIEVAL STRATEGY

Retrieval has historically been a major weakness.

Known lessons:

- OpenAlex can rate-limit;
- query formulation materially affects quantitative evidence yield;
- local parsers can discard useful metadata;
- retrieval failure must never be interpreted as evidence absence.

When primary sources are unavailable, legitimate substitutes may include:

- Crossref;
- Europe PMC;
- CORE;
- OSTI;
- institutional repositories;
- GitHub;
- Hugging Face;
- public government/laboratory datasets;
- public/open versions of papers.

Do not bypass paywalls, authentication, or access controls.

Source substitution must preserve:

- upstream identity;
- freshness;
- source class;
- provenance;
- transformation history;
- coverage limitations.

---

# 19. MODEL/PROVIDER RESILIENCE

The engine needs NVIDIA and OpenRouter as server-side providers.

Expected environment variables include:

```text
NVIDIA_API_KEY
OPENROUTER_API_KEY
```

Never expose credentials in:

- browser code;
- API response;
- logs;
- Git;
- package artifacts;
- health responses.

The router should select models using measured:

- current health;
- recent success rate;
- task suitability;
- rate-limit state;
- latency;
- cost;
- structured-output compliance;
- context requirements.

Do not treat an HTTP 200 probe as proof that a model can actually perform Toscanini's structured generation protocol.

The R418 incident showed precisely why: the free Nemotron route was reachable but leaked prompt instructions into fields and broke structured generation.

Therefore model health is:

```text
HTTP reachability
AND
protocol suitability
AND
task suitability
```

---

# 20. PROVIDER FAILOVER

A single provider/model outage must not terminate discovery.

Conceptually:

```text
MODEL A
 ↓ failure
MODEL B
 ↓ failure
MODEL C
 ↓ success
RUN CONTINUES
```

Internal telemetry must record:

- provider;
- model;
- attempt;
- latency;
- status;
- failure class;
- fallback source/destination.

Do not silently convert provider failure into scientific failure.

---

# 21. RETRY SEMANTICS

A known defect was recorded in R418:

- final product copy said a failed completed run was resumable;
- retry gate refused the same completed state.

This must be resolved through one authoritative state machine.

Suggested conceptual states:

```text
RUNNING
FAILED_RETRYABLE
FAILED_TERMINAL
COMPLETE
```

The UI and API should derive retry behavior from the same state machine.

---

# 22. PHYSICS

Current architecture:

- Physics Coverage Registry;
- deterministic solver-domain selection;
- measured selection of additional solver domains;
- analytical evaluator;
- engineering geometry authority.

Do not add many solvers at once.

Choose additional physics tooling based on:

```text
expected candidates unlocked
× information gain
÷ integration/validation cost
```

Blender is not physics validation.

Simulation results must carry:

- solver;
- version;
- equations/model;
- assumptions;
- operating regime;
- uncertainty;
- artifact identity.

---

# 23. REBUILD

The `/rebuild` feature is intended to become an interactive engineering hypothesis.

Conceptual flow:

```text
USER CHANGES PARAMETER
↓
CONSTRAINT VALIDATION
↓
CAD REBUILD
↓
MEASUREMENTS
↓
PHYSICS IF APPLICABLE
↓
DELTA
↓
NEW GLB
↓
NEW PROVENANCE
```

No mesh stretching masquerading as engineering.

For expensive rebuilds:

```text
POST /rebuild
→ 202
→ job_id
→ status polling
```

---

# 24. REALITY LOOP

There are currently **zero true physical validations** for the new generated invention system.

Do not change that statement unless actual measured events are added through the prescribed reality gate.

The reality system must distinguish:

- reconstructed;
- computational;
- physically observed/measured.

A simulation or visualization must never be promoted to physical validation.

---

# 25. KNOWN STANDING SCIENTIFIC / PRODUCT BLOCKERS

These were still materially relevant at handoff and must be refreshed from live state:

### A. Fresh-run model compatibility

The free Nemotron path previously failed FIELD-line structured generation by prompt leakage.

### B. Retrieval adequacy

R412/R417 retrieval problems remain partially addressed. A second blind re-verification corpus was still the clean path for a definitive improvement claim.

### C. Attacker calibration

Still `NOT_CALIBRATED` based on measured FPR 1.0. Abstain/escalate gate is active.

### D. Fresh invention → 3D → package reliability

The bridge is wired and P-07 works, but fresh-run production proof must be renewed after every material routing/deployment change.

### E. Invention quality

Solar test previously drifted toward PV + heating + controller rather than directly maximizing PV conversion efficiency.

Problem-objective fidelity and causal novelty need to be strengthened.

### F. Real physical validation

Still zero.

### G. Real buyer evaluation

Still zero.

---

# 26. HISTORICAL MILESTONES THAT MUST NOT BE LOST

## R401-WC external audit

Found major structural weaknesses including mechanism-distinctness false splits, hardcoded mechanism search, post-FREEZE contamination, generator/attacker independence concerns, weak cemetery learning, broken benchmark/replay, and poor attacker coverage.

## R405

Fixed a major conductance conversion inversion causing roughly 17,774.7x error.

## R406

Read full Constitution; measured truth/physical/buyer state; surfaced major P13 prior-art contestation; validated reality-loop schema and clean-clone behavior.

## R411

550 raw candidates → 400 evidence-qualified unique → 41 opportunities → 14 shortlisted → all 14 attacked/killed → 0 selected. This was a rejection campaign, not proof that no invention capacity exists.

Key learning: the system needs invention capacity, not forced quota filling.

## R412

Introduced 30-year temporal evolution and frontier-transfer concept.

Temporal arm: 13 attempted, all temporal projections, 0 present capability rediscoveries.

Gradient v1: 10 seeds, TVM schema admission failed; this was instrument failure, not proof that no frontier capabilities exist.

Gradient v2 introduced parser/calibration/normalization/signal policy infrastructure.

## R416

Changed attack behavior from terminal uncalibrated killing toward escalated objections and causal evolution.

Three live runs proved real generation/evolution behavior and caught defects in survivor pseudo-cause assignment, challenge visibility, and dropped objections.

## R417

Measured attacker as universal killer and gated it.

Repaired malformed JSON classes.

Adopted and dev-measured comparison-targeted retrieval query form.

Recorded the product directive for invention quality/3D causal experience but explicitly did not start it in that round.

## R418

Wired the automatic bridge into the production worker.

Fixed/handled the SciPy conceptual path in the local development work.

Added bridge failure persistence / WHY surfacing.

P-07 live browser acceptance passed.

Fresh solar acceptance remained blocked by structured-generation/provider incompatibility.

---

# 27. R418 TECHNICAL STATUS IN THE REMOTE HISTORY

The remote R418 acceptance record at commit `31b38c291f43fdbe8cf80bd0bfd5477747f3029e` states:

- P-07 browser acceptance passed;
- interactive 3D worked;
- downloads worked;
- live parameter rebuild worked on Render;
- fresh solar run failed during mechanism generation because the free Nemotron route leaked prompt text into fields;
- alternate free-tier models were unusable for the required FIELD-line protocol in that acceptance;
- bridge wiring was exercised;
- fresh-run end-to-end acceptance remained blocked pending a suitable provider/model route.

Treat that as the last authoritative R418 acceptance state unless newer evidence supersedes it.

---

# 28. R419 LOCAL WORK REPORTED BUT NOT NECESSARILY REMOTE-AUTHORITATIVE

The coder reported a local R419 workstream that:

- traced SciPy as a transitive trimesh color-path dependency;
- removed the unnecessary SciPy requirement for conceptual coloring;
- added adversarial test coverage;
- installed/pinned Blender 5.2.1 LTS;
- built headless rendering;
- fixed orientation and section/exploded bugs;
- added render-failure detection;
- produced hero/section/exploded artifacts locally;
- began integrating the world-class UI surface.

Because this work originated in an in-progress local workspace and not all of it was confirmed on remote `main` at the time of this handoff, the next chat must verify exactly what is committed and deployed before claiming R419 complete.

Do not assume local R419 state is remote truth.

---

# 29. SECURITY LESSONS

A prior bridge workspace contained a live session cookie and `.env` in committed history. The coder caught and purged them before publishing.

Future work must continue to scan for:

- API keys;
- access tokens;
- session cookies;
- auth headers;
- private URLs carrying credentials;
- secrets in generated PDFs/ZIPs/logs.

Secrets belong in server environment/secrets stores, never Git.

When updating Render env vars through APIs, be careful with replace-vs-merge semantics. A previous bulk PUT unexpectedly replaced the full environment-variable set; this was disclosed and repaired.

---

# 30. AUTOMATION-ONLY OPERATING RULE

**Everything in this project must be done through autocommands/automation. Nothing manual.**

The coder must use:

- shell/PowerShell/autocommand scripts;
- repository APIs or scripts;
- automated builds;
- automated tests;
- automated deployment calls;
- automated verification;
- automated artifact generation;
- automated browser/API acceptance where possible.

Do not give the operator a list of manual file edits, clicking steps, or copy/paste transformations.

When a manual credential is genuinely required from the operator, ask for the credential once and then automate its injection securely. Do not ask the operator to manually edit code or configuration.

The goal is that the operator can give a single high-level instruction and the coder can execute the workflow reproducibly.

---

# 31. ENGLISH-ONLY PROJECT RULE

The operational language policy was requested by the operator and was being formalized through an Article LXX amendment in local R419 work.

As of this handoff, verify whether the amendment has been committed to remote `main`.

The intended rule is:

**All project-authored code, comments, logs, tests, test names, reports, worklogs, commit messages, documentation, governance artifacts, API descriptive text, product UI copy, and generated technology-package prose are English-only, unless a separate user-facing translation is explicitly requested.**

Do not silently edit the Constitution to add this rule. Use the project's constitutional amendment process.

---

# 32. AUDITOR GOVERNANCE / ANTI-ENTROPY LOOP

The auditor must read the governance files before every substantive audit.

The auditor must reconstruct current state before prescribing.

The coder must remind the auditor to do this.

The auditor must remind the coder to read the full Constitution before coding.

The coder must reread the Constitution before final commit.

The auditor must reread relevant governance/blindspots before acceptance.

The central questions are:

> **What could still be false even if everything reported so far is true?**

and:

> **What might I have forgotten about the project's settled direction that would make my new recommendation create entropy?**

Use these to prevent checklist ritual and direction reversal.

---

# 33. AUDIT BLIND SPOTS TO CHECK EVERY ROUND

The register currently records 37 known blind spots. Especially relevant to future product audits:

- remote state drift;
- deployment SHA mismatch;
- built-but-unwired subsystem;
- captured-run success mistaken for default behavior;
- endpoint existence mistaken for semantic connectivity;
- honest absence masking recoverable engineering defect;
- engineering spec without geometry conversion;
- good package hidden by poor presentation;
- raw machine state leaking into UI;
- rejection vocabulary hijacking invention;
- uncalibrated attacker acting as judge;
- attacker authority multiplying through evolution;
- retrieval failure mistaken for evidence absence;
- parser information loss;
- query-form bias;
- benchmark circularity;
- demo artifacts vs generated artifacts;
- stale UI state while backend advances;
- stale metadata/governance versions;
- environment defects mistaken for code defects;
- security leakage;
- package audience confusion;
- invention drift from user objective;
- obvious combination mistaken for causal invention;
- visualization mistaken for validation;
- solver accumulation before coverage measurement;
- bridge fragmentation;
- static model availability assumptions;
- single provider failure killing product;
- narrow tests while user path fails;
- artifact-class mismatch;
- internally coherent package solving wrong problem;
- auditor tool limitations;
- self-reported completion bias;
- audit tunnel vision;
- recursive governance drift;
- auditor forgetting project state/direction.

The register must be extended if a new failure mode is discovered.

---

# 34. WHAT NOT TO DO

Do not:

- start a new large infrastructure sprint without first testing whether current components can solve the bottleneck;
- revive archived implementations because they look familiar;
- add another CAD/3D engine runtime choice;
- add a second package authority;
- let the frontend manufacture backend state;
- allow the LLM to be the sole solver selector;
- allow the attacker to terminate search before calibration;
- call generated text “discovery” just because it is novel language;
- call an evidence gap a scientific negative;
- treat a beautiful historical package as proof of current fresh-run behavior;
- call a counsel export a buyer-ready technology package;
- claim physical validation without physical observation;
- claim patentability;
- manually patch artifacts;
- change sealed results retrospectively;
- use paywall/authentication bypasses to acquire sources;
- rely on a single provider/model;
- ship a fresh physical invention with no visual artifact when the system can represent it.

---

# 35. WHAT THE FINAL PRODUCT SHOULD FEEL LIKE

The user should experience:

```text
Toscanini

DISCOVER. INVENT. ANYTHING.

What problem should Toscanini investigate?

[ Discover ]
```

Then:

```text
Investigating
Evidence
Developing invention
Challenging architecture
Evolving architecture
Building artifact
Preparing package
```

And finally:

```text
WHAT TOSCANINI INVENTED

[ excellent technical essay ]

                  THE INVENTION

                  [ large 3D model ]

                  GEN 1 / GEN 2 / GEN 3

Why it could work
What changed
Frontier capability transferred
Evidence
What could kill it
Decisive experiment

[ Download technology package ]

[ Prepare for IP counsel ]
```

The user should feel that an invention has appeared, not that they have opened an audit database.

---

# 36. THE PRODUCT QUALITY BAR

Use the released P-04/P-11 family as **quality references**, not as evidence that new runs are equivalent.

A world-class package should be understandable to a real engineering/business-development team without reading raw logs.

It should show:

- problem;
- invention;
- causal mechanism;
- what is new/different;
- frontier transfer where relevant;
- evidence;
- uncertainty;
- engineering representation;
- 3D;
- simulation where applicable;
- failure/challenge history;
- decisive experiment;
- manufacturing/build path;
- provenance;
- downloadable artifacts.

---

# 37. DEFINITION OF DONE FOR THE WHOLE PRODUCT

Do not call the system world-class merely because tests are green.

The decisive acceptance is:

```text
FRESH USER
   ↓
DIFFICULT REAL PROBLEM
   ↓
REAL DISCOVERY RUN
   ↓
REAL INVENTION
   ↓
REAL TECHNICAL ESSAY
   ↓
REAL CAUSAL ARCHITECTURE
   ↓
REAL 3D ARTIFACT
   ↓
REAL PHYSICS / ENGINEERING WHERE APPLICABLE
   ↓
REAL CHALLENGE
   ↓
REAL EVOLUTION WHEN NEEDED
   ↓
REAL DECISIVE EXPERIMENT
   ↓
REAL TECHNOLOGY PACKAGE
   ↓
PUBLIC WEBSITE SHOWS THE SAME CANONICAL STATE
   ↓
BUYER CAN DOWNLOAD AND INSPECT
```

For a physical invention, the package must not end at prose.

For a generated invention, the 3D must not be an empty placeholder.

For a research result, evidence and uncertainty must remain explicit.

For an invention that has not been physically tested, say so.

---

# 38. NEXT CHAT'S FIRST DECISIVE TASK

Do not immediately add new features.

First execute a fully automated baseline audit:

```text
1. Read Constitution.
2. Read all governance/anti-entropy files.
3. Verify remote engine `main`.
4. Verify buyer repository `main`.
5. Verify deployment SHA and `/api/health`.
6. Verify active branches/PRs.
7. Inspect current R419/R418 commits.
8. Inspect current `bridge_gate.py`, `worker.py`, `cio.py`, `run_state.py`.
9. Inspect current webapp components.
10. Inspect current 3D/rendering artifacts.
11. Run automated focused tests.
12. Run automated full regression.
13. Run a fresh browser/API problem.
14. Follow the actual run into invention → 3D → package.
15. Download and inspect the produced package.
16. Challenge the coder's strongest completion claim.
17. Identify the single highest-information next fix.
```

Do not assume the outcome in advance.

The next decisive question is:

> **Can a fresh ordinary user problem now produce, without operator intervention, a coherent invention + excellent essay + real 3D artifact + real package on the public website?**

If not, fix that join before adding more architecture.

---

# 39. FINAL CONTINUITY STATEMENT

This project has already solved many hard infrastructure problems. The greatest remaining risk is not lack of code. It is **entropy**:

- forgetting what has already been decided;
- rebuilding a superseded subsystem;
- confusing a demo with the normal path;
- confusing a component with the integrated system;
- optimizing verification until creativity disappears;
- optimizing UI until epistemic honesty disappears;
- optimizing tests until product behavior is forgotten;
- optimizing beautiful artifacts while the invention solves the wrong problem.

The next chat must therefore remember both sides of the mission:

### Scientific discipline

Evidence before assertion. Exact provenance. No fabricated physics. No fabricated experiments. Calibrated verification. Immutable history.

### Product ambition

Every problem deserves a genuine invention attempt. The machine should continually evolve its architectures using 30-year reasoning and frontier technology transfer. The user should receive a compelling, inspectable invention artifact. The result should be good enough for a real company to consider acting on it.

The target is not a better research report.

The target is a **world-class invention laboratory**.

---

# 40. HANDOFF ACKNOWLEDGEMENT

The next chat should begin by reading this file only as continuity context and then validating every current-state claim against the authoritative sources.

Do not ask the operator to repaste the historical governance files unless they have disappeared from the repository.

Use the repositories as the source of truth.

Use automation for everything.

Keep the Constitution above all.

Keep the auditor governance in force.

Keep the remembering checkpoint alive.

And before giving any new directive, ask:

> **What have we already decided, what has already been built, what has already been rejected, what is actually authoritative now, and what new evidence justifies changing direction?**
