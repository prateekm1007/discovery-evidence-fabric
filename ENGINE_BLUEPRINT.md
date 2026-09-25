# ENGINE_BLUEPRINT.md — E14 Final Architecture

**Directive:** CEO E1–E14 — "SURVIVING DISCOVERY → AUTOMATIC ENGINEERING
SPECIFICATION → AUTOMATIC 15-DOSSIER-LEVEL PACKAGE"
**Date:** 2026-08-27
**Supersedes:** nothing; extends ACTIVE_PATH.md / RUNTIME_CAPABILITY_REGISTRY.json
**Constitution:** v1.8.0 read before this work (Art. I–XXXVIII acknowledged)

---

## The product (CEO E14, as built)

```
               DISCOVERY ENGINE  (discovery_fabric/engine/run.py, D6/D8)
                     │  13 stages: RETRIEVE→…→RANK
                     ▼
              PROBLEM FORMATION  (problem.json, custodied+hashed)
                     │
                     ▼
                EVIDENCE FABRIC  (a2/retrieve + orchestrator/evidence_custody)
                     │
                     ▼
             MECHANISM DISCOVERY  (a2/synthesize via E1 llm_registry)
                     │
                     ▼
           CROSS-DOMAIN COLLISION  (a2/prior_art + prior_art_v2 sources)
                     │
                     ▼
             NOVELTY / PRIOR ART  (explicit vocabulary map, Art. XXVII)
                     │
                     ▼
                 ATTACK  (a2/adversarial via E1 llm_registry)
                     │
                     ▼
            KILLER EXPERIMENT  (bayesian_eig, MODEL_DERIVED priors)
                     │
                     ▼
               ADJUDICATION  (deterministic hash-bound council)
                     │
                     ▼
                 SURVIVOR  (survivor gate: no promotion by narrative)
                     │
                     ▼
            INVENTION SPECIFICATION  (engine/invention_spec.py, E2)
                     │        every field: SOURCE_FACT|COMPUTED|MODELLED|
                     │        ENGINEERING_PROPOSED|UNKNOWN
                     ▼
          ENGINEERING SPECIFICATION  (engine/engineering_spec.py, E3)
                     │   + domains.py (E6) + equations.py (E7)
                     │   + structural design graph DI→DO→FM→VF→VA (E8)
                     ▼
             DOSSIER GENERATOR  (engine/package_factory.py, E4)
                     │   reuses FROZEN build_portfolio_v4 builders
                     ▼
              BUYER PACKAGE  (engine/package_factory.py, E10)
                     │   00..05 PDFs + PACKAGE_MANIFEST.json
                     │   + ENGINEERING_TRACEABILITY.json (E12)
                     │   + MATURITY_BASIS.json + zip
                     ▼
                  BUYER
                     │
                     ▼
               ENGINEER / LAB
                     │
                     ▼
              REAL EXPERIMENT  ── (reality's job, not the engine's)
                     │
                     ▼
                  REAL DATA
                     │
                     ▼
              PROVENANCE CHECK  (frozen r370g REALITY_EVENT gate, E13)
                     │
                     ▼
               BELIEF UPDATE  (engine/learning_loop.py, E13: deterministic
                     │         Bayes; EXPERIMENTALLY_ESTIMATED observation)
                     ▼
              PACKAGE V2 / V3  (same factory; V2_MUTATION_ADDENDUM)
                     │
                     ▼
            SEARCH-SPACE UPDATE  (LEARNING_CONSTRAINTS.jsonl)
                     │
                     └──────────────► DISCOVERY ENGINE
```

---

## What each E-directive landed as

| Directive | Deliverable | Module |
|---|---|---|
| E1 | LLM_PROVIDER_REGISTRY — 7 providers, explicit selection ledger, `PROVIDER_UNAVAILABLE ≠ NO_INVENTION`, no silent substitution | `discovery_fabric/engine/llm_registry.py` (bridged into `a2/synthesize.py`, `a2/adversarial.py`) |
| E2 | Canonical `INVENTION_SPECIFICATION` (16 fields, epistemic-tagged, fact-promotion checker) | `discovery_fabric/engine/invention_spec.py` |
| E3 | 12-section engineering content with inherited epistemic classes; generator cannot turn a model into a fact | `discovery_fabric/engine/engineering_spec.py` |
| E4 | Dossier factory REUSE — frozen `build_portfolio_v4.py` builders invoked per-package (no template recreation) | `discovery_fabric/engine/package_factory.py` |
| E5 | Evidence-bound generation — claims require evidence → field → stage chains; standards are `EXTERNAL_PRECEDENT_CANDIDATE` with verify flags | `package_factory.survivor_to_canonical_package` |
| E6 | Automatic domain detection (10 templates) with recorded keyword signals; unknown stays `NOT ESTABLISHED` | `discovery_fabric/engine/domains.py` |
| E7 | Domain equation library (15 equations) — `equation_id/variables/source/applicability/assumptions`; numbers ONLY from SOURCE_FACT/COMPUTED inputs, else SYMBOLIC_ONLY | `discovery_fabric/engine/equations.py` |
| E8 | Design graph `USER_NEED→DI→DO→FM→VF→VA` with explicit IDs, structural parent links, integrity checks, recorded gaps | `engineering_spec.build_design_graph` |
| E9 | Cheapest decisive experiment — cross-join of KILLER_EXPERIMENT (EIG/cost) × NEXT_BEST_ACTION (score) + why-sentence | `discovery_fabric/engine/experiment_selector.py` |
| E10 | Automatic buyer package → `DOWNLOAD/<nn>_<short>/` + `.zip` | `package_factory.generate_buyer_package` |
| E11 | True E2E smoke — 29 links, fails loudly; real mode + labeled rehearsal mode | `discovery_fabric/engine/smoke_e2e.py` |
| E12 | End-to-end provenance — `PACKAGE_CLAIM→INVENTION_FIELD→CANDIDATE_STAGE→EVIDENCE_ID→SOURCE→HASH`, structural (never keyword) | `package_factory.build_traceability` |
| E13 | Learning loop — frozen r370g REALITY_EVENT validation + ledger, belief update, causal mutation, dossier V2, discovery constraints; AI-source events rejected | `discovery_fabric/engine/learning_loop.py` |
| E14 | This blueprint + 7 new capability rows in RUNTIME_CAPABILITY_REGISTRY.json | `ENGINE_BLUEPRINT.md` |

Conductor integration: `run.py --with-package` runs the post-RANK pipeline
(survivor gate enforced) without altering the exact D8 13-stage order.

---

## How to run

```bash
# REAL end-to-end (needs any one provider credential in env or .env.keys):
python3 -m discovery_fabric.engine.smoke_e2e --problem-id p01 --with-package
#   or directly:
python3 -m discovery_fabric.engine.run --problem-id p01 --with-package

# CONTROLLED REHEARSAL (no credentials needed; proves all 19+ links on a
# recorded fixture; output labeled SYNTHETIC_REHEARSAL=TRUE — never for buyers):
python3 -m discovery_fabric.engine.smoke_e2e --rehearsal

# Learning loop (after a real buyer/engineer/lab event):
python3 - <<'PY'
from discovery_fabric.engine.learning_loop import ingest_external_event
ingest_external_event(event, package_context, out_dir)
PY
```

---

## Honest status (Art. XV — inconvenient truths disclosed)

1. **Full autonomous real E2E is blocked ONLY by credentials.** No provider
   key exists in this environment (OPENROUTER…DEEPSEEK all absent since the
   credential scrub). REAL smoke fails at SYNTHESIZE with
   `PROVIDER_UNAVAILABLE` + the exact unblock list. That is an infrastructure
   state, not a capability gap — the E1 registry accepts ANY of the seven
   providers via env or `.env.keys`.
2. **The bridge machinery is proven** — 25 offline tests + rehearsal smoke
   (19 links) + full repo suite: 786 passed; 2 pre-existing environmental
   failures (PATENT_BEAR NO_KEY; secret-scan baseline) verified pre-existing
   on clean HEAD 7776141.
3. **Generated packages are honest by construction:** maturity EARLY_CONCEPT
   until ≥5 design inputs, ≥3 failure modes, ≥4 build-plan steps and a
   governing model exist (same rule as the frozen portfolio);
   `transfer_ready=false`; `real_loop_verified=false` (derived state — never
   assignable); rehearsal packages are visibly flagged and must never reach
   buyers.
4. **The generator does not invent engineering.** All parameter values are
   UNKNOWN until reality (measurement) or computation (logged) produces
   them; equations are emitted symbolically without sourced inputs; DOs are
   ABSENT; verifications NOT_TESTED; validations NOT_POSSIBLE_YET. This is
   the Reality Boundary (Art. XXXVIII) enforced in code, not prose.
5. **Physical reality loop** remains open by design: it starts when the first
   validated REALITY_EVENT arrives through `learning_loop.ingest_external_event`
   — the machine is ready for that dataset (Art. XXXVII/R339 GATE 9 posture).

---

## F-SERIES UPDATE (CEO FINAL INTEGRATION DIRECTIVE, 2026-08-27)

The bridge is no longer optional. Directives 1-10 are implemented and
proven by `tests/test_f_series_integration.py` (22 tests) on top of the
E-suite (40 tests in dossier_bridge + engine_integration):

1. **AUTOMATIC survivor -> package** (Directive 1): `EngineRun` default is
   `with_package=True`; the only opt-out is the test-only `--no-package`
   CLI flag / explicit constructor argument. A surviving RANK ALWAYS
   produces INVENTION_SPECIFICATION -> ENGINEERING_SPECIFICATION ->
   DECISIVE_EXPERIMENT -> BUYER_PACKAGE (6 PDFs + 3 JSONs + zip).
2. **DISCOVERY_RELEASE.json** (Directive 2): written for EVERY run by
   `engine/release.py`; binds run/candidate/invention/problem ids to
   evidence/candidate/spec/manifest/zip SHA-256 hashes with an explicit
   status vocabulary (RELEASED / NOT_A_SURVIVOR / PIPELINE_FAILED /
   PACKAGE_INCOMPLETE / DISCOVERY_INCOMPLETE / DISABLED_BY_CONFIG).
3. **Proven dossier reuse unchanged** (Directive 3): the same frozen
   build_portfolio_v4 builders render every generated package.
4. **ENGINEERING_DOMAIN_REGISTRY.json** (Directive 4): 11 domains + UNKNOWN,
   each with governing_models, critical_parameters, failure_modes,
   design_input/output_patterns, verification/validation_methods,
   manufacturing_patterns; sync-pinned to domains.py by test.
5. **No fabricated depth** (Directive 5): epistemic classes verified to
   survive INTO the rendered dossier PDF (pypdf text extraction asserts
   SOURCE_FACT / MODELLED / ENGINEERING_PROPOSED / UNKNOWN / ABSENT /
   NOT_TESTED / NOT ESTABLISHED / NOT_PERFORMED).
6. **Zero material truncation** (Directive 6): `_short`/`_shorten` removed;
   full text everywhere in authoritative artifacts; display summaries only
   through the DisplayRegister (serialized into PACKAGE_MANIFEST.json);
   static guard test scans the authoritative sources for slice patterns.
7. **Computed maturity** (Directive 7): `engine/maturity.py` evaluates the
   six-rung ladder from actual artifact state; blockers are the evaluated
   unsatisfied conditions of the next rung with evidence pointers; the
   injected generic blocker list is gone.
8. **Automatic package test** (Directive 8): fixture survivor ->
   9 files + zip + hashes + release, failing on any missing stage.
9. **Scale test** (Directive 9): 15 survivors (11 domains) -> 15 invention
   specs, 15 engineering specs, 15 full dossier sets, 15 zips; unique ids,
   unique hashes, each manifest bound only to its own run.
10. **Ablation** (Directive 10): collision/attack/killer-experiment/
    next-best-action/engineering-domain-module disabled one at a time;
    downstream artifacts proven to change where each module feeds them.

Credential state changed 2026-08-27: CEO provisioned NVIDIA + Mistral keys
(`.env.keys`, gitignored). NVIDIA now hosts the FROZEN synthesis model
`deepseek-ai/deepseek-v4-flash-0731` (verified live, ~150 s/call); the
legacy NVIDIA default llama-3.1-8b-instruct is retired (HTTP 410). The
first REAL end-to-end autonomous run is no longer credential-blocked.

---

## R533 PROVENANCE CORRECTION ADDENDUM (APPEND-ONLY, Art. XI)

Generated: 2026-09-25T07:50:20Z
Source commit: b1c9a831596a8952a305cec353873f561a877da8
Adapters file blob: discovery_fabric/engine/adapters.py @ b1c9a831596a

### Architecture authority

The executable stage order is defined by `STAGE_ORDER` in
`discovery_fabric/engine/adapters.py` (the single executable authority;
all other stage-order claims in historical docs are superseded):

```
STAGE_ORDER = [
    "RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE", "VERIFY",
    "MECHANISM_SPACE", "COLLISION", "PHYSICS",
    "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT",
    "ADJUDICATION", "CLASSIFY", "NEXT_BEST_ACTION", "RANK"
]
```

**15 linear stages + IMPROVE post-rank kill point.**

`ADAPTERS = STAGE_ORDER ∪ {"IMPROVE"}`. IMPROVE is deliberately
absent from `STAGE_ORDER` (post-rank Directive-1 kill-evidence
operation; `run.py` kill point; never in the linear D8 chain).
`MULTI_SOURCE_DISCOVERY` was removed in R513.

### Constitution authority

Current live constitution: **v2.10.1**
SHA256: `2CE42426662D6493F672CF5FD7256BF5C2B9C8412E369EE9032B253B80B6FC56`

Historical references in this file to "v1.8.0" are accurate for the
original writing date (August 2026) and are preserved unchanged per
Art. XI.

### Stale language in original blueprint (disclosed, not rewritten)

Line 15 (original): `│  13 stages: RETRIEVE→…→RANK`
  Correction: the diagram predates R394/R397/R401/R507 first-class
  stages (PREMISE_GATE, MECHANISM_SPACE, PHYSICS, KILLER_EXPERIMENT,
  CLASSIFY, NEXT_BEST_ACTION, ADJUDICATION, COLLISION, ATTACK,
  CONTRADICTION). The 15-stage chain above is current.

Line 108 (original): "without altering the exact D8 13-stage order"
  Correction: the post-RANK engineering pipeline (E1–E14) runs after
  RANK (the 15th linear stage). `IMPROVE` is the post-rank kill point
  that may also execute in the post-rank pipeline; it is not a 16th
  linear stage.

### Metadata provenance link

`ACTIVE_DISCOVERY_GRAPH.json` `generated_from_commit = b1c9a831596a8952a305cec353873f561a877da8`
`RUNTIME_CAPABILITY_REGISTRY.json` `generated_from_commit = b1c9a831596a8952a305cec353873f561a877da8`
`adapter_blob_sha` field records the exact blob SHA of
`discovery_fabric/engine/adapters.py` inspected.
