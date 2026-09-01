# ACTIVE_PATH.md — The One Canonical Production Loop (R388)

> Distilled at R388 per the CEO directive (distill → verify → productize).
> This file replaces the A2-era ACTIVE_PATH (preserved in git history and on
> `archive/rounds-R309-R383`). It is the single authority for what the
> production path IS; anything not listed here is either evidence custody,
> governance, or archive.
>
> **R389 addendum — the PRODUCT layer** (CEO order: stop adding general
> infrastructure; productize). The loop below is UNCHANGED; the new surface
> puts it behind a Claude-like product:
>
> | Layer | Module | Notes |
> |---|---|---|
> | Job API (Phase 7) | `toscanini/server.py` | `POST /api/run`, `GET /api/run/{id}/stream` (SSE), `GET /api/run/{id}/result` — ALIASES of the same session/worker path; the frontend never touches internal Python modules |
> | Frontend (Phases 4–6) | `TOSCANINI_UI/webapp/` (Next.js + React Three Fiber) | three experiences: CONVERSATION → DESIGN/3D → RESULT; reasoning display = the 8-step engineering argument from artifacts (never chain-of-thought); single DOWNLOAD TECHNOLOGY PACKAGE action |
> | Showcase (Phase 8) | `toscanini/showcase.py` | serves the REAL portfolio packages (Art. XXXIX authority) with interactive 3D |
> | Interactive evaluator (Phase 5) | `toscanini/showcase.py::evaluate_parameter` → `cad_pipeline.rebuild_with_mutation` | parameter inside its DECLARED envelope → real sandbox rebuild → re-measured geometry + preview GLB; out-of-envelope/unbound → explicit refusal (never clamped) |
> | Reality layer (Phase 2) | `discovery_fabric/engine/reality_provider.py` | provider-neutral REALITY_PROVIDER (World Labs/Marble first adapter, verified live); REALITY_MODEL (10 fields, origin-tagged); DESIGN_WORLD ↔ REALITY_COMPARISON ↔ REALITY_WORLD. Providers emit RECONSTRUCTED/COMPUTATIONAL only — MEASURED requires R370G-attested events; a reconstruction can never become PHYSICAL_VALIDATION (Art. XXXVIII, structurally enforced) |
> | Phase 1 audit | `R389_PIPELINE_AUDIT.{md,json}` | final call-graph audit: 13 stages KEEP, 37/41 modules reachable, 4 tooling-only, zero dead code — measured, not assumed |
>
> Final audit verdict: the active path is already minimal for its epistemic
> guarantees; the correct move was exactly what the CEO ordered — stop
> pruning, build the product.

## The loop

```
PROBLEM → EVIDENCE → MECHANISM → CANDIDATES → ATTACK → INVENTION DIAGNOSTIC
→ IMPROVE → TECHNICAL EVALUATION → 3D DESIGN → DECISIVE EXPERIMENT
→ ENGINEERING DOSSIER → BUYER PACKAGE
```

Every stage carries a gate; no stage's pass credit transfers to the next
(Art. XXVIII — no silent semantic promotion).

## Stage → module map (one implementation per stage)

| Stage | Canonical module(s) | Gate / evidence anchor |
|---|---|---|
| PROBLEM | `toscanini/problem_builder.py` (user problem → structured hypothesis; MODEL_DERIVED extraction flagged as such) | problem existence gate (Art. XX) |
| EVIDENCE | `discovery_fabric/connectors/` + `discovery_fabric/a2/retrieve.py` + `discovery_fabric/source_registry/` (RETRIEVE → FREEZE with content hashes) | per-source status ledger; freeze hashes |
| MECHANISM + CANDIDATES | `discovery_fabric/a2/synthesize.py` + `engine/candidate_diversity.py` + `orchestrator/multi_source_discovery.py` (four-search attack: discovery/destruction/transfer/reality) | exploration grid ≥10 recorded angles |
| ATTACK | `discovery_fabric/a2/adversarial.py` + `discovery_fabric/prior_art_v2/` + `discovery_fabric/v4_corrections.py` firewalls | adversarial gate; prior-art firewall; boundary/invalid guards |
| INVENTION DIAGNOSTIC + IMPROVE | `discovery_fabric/engine/improvement_engine.py` (R379 technical state), `engine/collision.py`, `engine/engineering_attack.py` | adversarial call graph (`PRODUCTION_ADVERSARIAL_CALL_GRAPH.md`) |
| TECHNICAL EVALUATION | `discovery_fabric/engine/equations.py` (R383 analytical evaluator: 9 closed-form relations, deterministic binding, margins, bisection solve, K8 keep gate) | `ADR_R383_ANALYTICAL_EVALUATOR.md`; live demos `TOSCANINI/R383_LIVE_QUANTITATIVE/` |
| 3D DESIGN | `discovery_fabric/engine/cad_pipeline.py` (R380: sandboxed AST-scanned build programs, G1–G8, trimesh as independent verifier) + `premium_package_factory/r381/` (14 parametric package templates, KEEP-KILL mutation loop) | `ADR_R380_CAD_PIPELINE.md`; `TOSCANINI/R380_LIVE_POSITIVE/` |
| DECISIVE EXPERIMENT | `discovery_fabric/engine/experiment_selector.py` (killer-experiment stage, engine stage order) | stage ledger `KILLER_EXPERIMENT` |
| ENGINEERING DOSSIER | `premium_package_factory/` (gates + templates + `r371/builder.py`; frozen state in R332/R370-family trees) | gate certificates |
| BUYER PACKAGE | `premium_package_factory/` r384 3D-evidence augment + `scripts/r385_root_docs_regeneration.py` (builder script pinned by the chain) + `scripts/r386_release_chain.py` (four-state verifier) | Article XXXIX chain: ENGINE RECORD ↔ CANONICAL MANIFEST ↔ PORTFOLIO TREE ↔ BUYER ZIP; 21 hermetic negative controls in `tests/test_r386_release_chain.py` |

Engine stage order (runtime): `RETRIEVE → FREEZE → SYNTHESIZE → VERIFY →
MULTI_SOURCE_DISCOVERY → COLLISION → ATTACK → CONTRADICTION →
KILLER_EXPERIMENT → ADJUDICATION → CLASSIFY → NEXT_BEST_ACTION → RANK`
(`discovery_fabric/engine/adapters.py`).

## What is NOT in the active path (and where it lives now)

- A2-era diagnostic/forensic trees, generation-era corpora, campaign
  byproducts, the stale `WORKLOG.md` fork, round scripts R310–R378:
  **archived** at `archive/rounds-R309-R383` + git history (inventory:
  `ARCHIVE_MANIFEST.json`). Retrieval: `git checkout archive/rounds-R309-R383
  -- <path>` or `git log --all -- <path>`.
- TEE mechanism extraction / abstraction / transfer: QUARANTINED (historical
  decision, unchanged).
- Simulation for invention validation: not authorized (reality-boundary
  discipline, Art. XXXIV/XXXVIII).

## Non-negotiable invariants of this path

1. Evidence precedes assertion (Art. I); exact evidence beats semantic
   plausibility (Art. II).
2. The verifier never trusts the claimant (Art. III): trimesh re-measures
   STLs, clean-clone verification certifies the release, GitHub Actions —
   not local runs — certifies the repo (Art. XXVI).
3. The buyer-distribution repository is the final authority (Art. XXXIX);
   the chain verifier must pass from clean clones before any release claim.
4. Negative knowledge is kept: `MECHANISM_CEMETERY/` and the honest
   `PHYSICALLY_VALIDATED: NONE` discipline are the moat.
5. No candidate is called an invention until evidence and novelty checks
   justify the classification (epistemic states never silently promoted).
