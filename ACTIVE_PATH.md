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
>
> **R390 addendum — the REALITY LOOP is CLOSED** (CEO directive #6). The
> production loop above ends at BUYER PACKAGE; R390 adds the loop that
> feeds REALITY back into the next design:
>
> ```
> REAL OBSERVATION → REALITY MODEL → DESIGN/REALITY COMPARISON →
> DISCREPANCY → CAUSAL HYPOTHESIS → TECHNICAL STATE UPDATE → MUTATION →
> NEW DESIGN → RE-EVALUATION
> ```
>
> | Component | Module | Notes |
> |---|---|---|
> | Acquisition | `discovery_fabric/engine/reality_loop.py::acquire_nist_water_viscosity` | live external wire fetch, raw-byte sha256 custody, R370G event through the frozen gate; first live event: `EVT-R390-NIST-WATER-VISC-310K` (NIST SRD 69 water at 310.15 K) |
> | Closure | `discovery_fabric/engine/reality_loop.py::close_reality_loop` | deterministic (zero LLM); MEASURED only via the R370G one door; discrepancy threshold = the design's OWN declared band; compensation from the package's EQ-1; envelope refusal, never clamp; canonical bytes untouched (Art. IX) |
> | Causal chain + state | R370G `record_causal_mutation` × 9 stages → `compute_real_loop_verified()` | REAL_LOOP_VERIFIED is DERIVED, never assigned; ledgers append-only and COMMITTED (R370U anchor precedent) |
> | Operator script | `scripts/r390_close_reality_loop.py` | `--rehearsal` (hermetic, state can never flip) / `--live` (canonical ledger) — same code path (Art. XXXVII) |
> | Product surface | `GET /api/showcase/{slot}/reality-loop` + webapp `RealityLoopPanel` | the decision-change proof shown to investors: observation → discrepancy → decision before/after → re-evaluated result → residual unknown |
>
> Live closure on P-07: measured η = 0.6913 mPa·s refuted the declared
> "water at 37 C" basis; `floor_lumen_diameter_mm` 0.6 → 0.5471 mm;
> conductance restored 0.99998. Art. XXXVII scorecard: REAL 0 → 1.

**R441 addendum — the 3D DESIGN stage's presentation half is now the
Visual Compiler** (operator directive; Article LXXII). The stage map's
3D DESIGN row gains its presentation pipeline:

| Component | Module | Notes |
|---|---|---|
| Visual Compiler | `discovery_fabric/engine/visual_compiler/` | canonical GLB -> deterministic scene spec (gltf_doc direct walk — canonical node names, spec-required bounds) -> semantic materials from component type -> projected-extent camera solve -> headless Chromium + Three.js (three@0.175.0, the webapp's own version — WYSIWYG) -> Hero/Turntable/Exploded/Section/Orthographic/Dimension/Poster |
| Visual Quality Gate | `visual_compiler/visual_gate.py` | independent pixel verification (occupancy band, anti-clip, contact shadow, semantic materials, node naming, geometry identity, poster parity, single viewer); FAIL/NOT_RUN suppresses the hero and blocks release (Article LXXII) |
| Renderer boundary | `visual_compiler/render_worker.py` | fail-closed Chromium/Node resolution, R423A env allowlist carried to the new subprocess, cgroup-aware memory guard (thresholds: visual_compiler_thresholds.json, measured) |
| Dispatcher | `invention_bridge/render.py::render_invention` | PRIMARY = the Visual Compiler; the pinned Blender path is LEGACY (explicit choice only, records labeled BLENDER_HEADLESS_LEGACY; blender_render.py ARCHIVED_TO r441_retired/ — Article LXIV disposition in R441/R441_ROUND_RECORD.json) |
| PDF constitution | `invention_bridge/package.py::_pdf` | gate-approved dossiers open p1 full-bleed hero, p2 exploded, p3 orthographic, p4 dimensions, then narrative + experiment; no gate pass -> no hero in ANY medium |

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

---

## R442-PREP addendum (2026-09-10) — the production visual join, proven at the byte level

The Visual Compiler path (R441) was exercised end to end from PRODUCTION
at the exact deployed SHA (33e5d6d9) with two genuinely fresh inventions
(ts_ef8a3f281c94 multi-part autosampler; ts_4c86d5642e99 helical heat
recovery module): engineering identity (GEOMETRY_SPEC spec_sha256) ->
canonical GLB (sha-verified served bytes) -> Visual Compiler -> gate ->
seven views -> package. The production visual stage itself typed-skips
(RENDER_SKIPPED_LOW_MEMORY, honest, fail-closed) on the 512 MB free
plan; the full visual join was proven on the SAME bytes at the SAME SHA
in the sandbox (gate PASS, all seven rules, independently re-measured).
The failure chain was proven both by injection (FAIL -> hero suppressed
-> release blocked) and live in production (NOT_RUN -> zero hero files
in the package ZIP, zero images in all six PDFs, render routes 404,
canonical GLB still 200). Coder 1 feedback filed: R442/FEEDBACK_TO_CODER_1.md
(generic chassis dominance + overlapping/enclosed part placement — two
different inventions rendered a byte-identical hero). The Blender
dispatcher deletion conditions are NOT all true yet (production visual
service blocked on the billing-gated memory upgrade) — retirement
deferred per the directive's own condition list. Round record:
R442/R442_ROUND_RECORD.json.

## R443-C2 addendum (2026-09-10) — the gate hardened against itself

Operator directive R443-C2 (Visual Integrity Hardening) closed the four
R442-disclosed gate blind spots WITHOUT altering engineering truth.
The stage map's VISUAL QUALITY GATE row now reads:

| Rule / boundary | Module | Notes |
|---|---|---|
| Raw-document node identity | `visual_compiler/visual_gate.py` + `gltf_doc.raw_part_identity` | canonical identity is proven from the RAW glTF JSON chunk (no loader — loaders synthesize names for unnamed nodes and a stripped GLB used to pass); the named-identity set must equal the scene spec's canonical nodes 1:1; the trimesh naming rule is DELETED (Art. LXIV disposition in the R443 record) |
| Wrong-source witness | `visual_gate.check_source_scene_agreement` | the exported hero GLB's re-derived grounded world bounds must reproduce the spec's grounding (tolerance 0.02 normalized units) — a valid-looking render of another geometry fails |
| Visual-set completeness | `visual_compiler/visual_set.py` | the required R441 ladder (hero, poster, dimension, section, exploded-when-multi-part, orthographic x4, turntable x12 = 23) re-verified FROM DISK at gate time; verdicts COMPLETE_PASS / PARTIAL / NOT_RUN / FAIL; anything but COMPLETE_PASS suppresses the hero and blocks release (Art. LXXII) |
| Material distinction | `render.js` material probe + `visual_gate.measure_material_distinction` | one sphere per distinct semantic class under the hero light rig; the gate measures CIEDE2000 >= 10.0 between every class pair on the saved pixels (threshold provenance: visual_compiler_thresholds.json rev 3, ~4x CIE JND); the R441 palette measured 15/78 pairs below the bar (body_metal/machined_metal at 1.01 = BELOW JND) and was re-derived to pass the RENDERED measurement (13 classes, min pair 10.68 live) |
| Typed render records | `visual_compiler/render_record_schema.py` | every status (SUCCEEDED / FAILED / SKIPPED_LOW_MEMORY / SKIPPED_INFRA_UNAVAILABLE / NOT_RUN) has a total typed record; finalize + validate on every compiler exit; package.py validates BEFORE reading consumer fields; skips/fails cannot carry a measured verdict |
| Release decision | `package.py::_visual_release_ok` | the single release-passing state: verdict COMPLETE_PASS (legacy PASS only while no completeness block is declared); HERO_RELEASE_STATE.json carries the verdict verbatim |

The five adversarial attacks (stripped identity, missing view, material
spoof, malformed skip, wrong source) all fail closed for the specific
reason each boundary exists (tests/test_r443_visual_integrity.py, 34
tests). Both R442 production cases replay COMPLETE_PASS from clean
state on the SAME bytes (Case B's body_metal/machined_metal now
measures 15.92 dE00 rendered where R442 measured it visually
indistinguishable). Production still type-skips the visual stage on the
512 MB free plan (billing-gated upgrade re-escalated, Art. LXV count 3)
— production visual success is NOT claimed. Round record:
R443/R443_C2_ROUND_RECORD.json.

## R444-C2 addendum (2026-09-11) — the buyer surface's lineage is re-measured

Operator directive R444-C2 (Production Visual Closure): the visual gate
remains the presentation authority (never the renderer's own claims).
Two additions, both inside the Coder 2 presentation boundary:

| Component | Module | Notes |
|---|---|---|
| Buyer-surface lineage verifier | `visual_compiler/lineage.py` | read-only re-measurement of the chain GEOMETRY_SPEC hash -> GLB hash -> render source hash -> hero/poster/view hashes -> PDF embedded page-1 image (pixel-exact, container-agnostic); verdicts VERIFIED / INCOMPLETE / FAIL, fail-closed (missing evidence is never a pass, Art. XXV); suppression contract verified too (hero absent, no cover image) |
| Persisted typed record | `visual_compiler/visual_compiler.py` | the finalized R443-schema record is persisted to `MODEL/3D/render_record.json`, superseding the renderer's contemporaneous side-record in place (Art. LXIV merge-and-replace) — the buyer surface now carries the SAME validated record consumers use |

Battery: `tests/test_r444_lineage.py` (12 tests: live full-chain
positive incl. the real `_pdf` cover contract, read-only proof, swapped
hero bytes, wrong PDF cover, suppression bypass, consistent suppressed
package, missing/legacy records, tampered engineering identity, wrong
source GLB). Production visual closure remains BLOCKED on the owner-side
capacity decision (Render plan measured 'free' at round start; Art. LXV
escalation 4) — production visual success is NOT claimed this round.

## R445 addendum (2026-09-11) — ONE canonical domain-family vocabulary

Operator directive R445-A (the F1 fix): the domain-family identity is
now ONE semantic namespace flowing unchanged through every layer
(USER PROBLEM -> PROBLEM CONTEXT -> DOMAIN SPEC -> ENGINEERING SPEC ->
GEOMETRY -> CIO -> DOSSIER -> PACKAGE).

| Component | Module | Notes |
|---|---|---|
| THE canonical family registry | `engine/domains.py::CANONICAL_DOMAIN_FAMILIES` | 11 families (thermal, fluid, materials, biomedical, software_ml, mechanical, electronic, energy, optical_photonic, acoustic, generic) + engine-domain and bridge-archetype routing DECLARED by mapping into it; published in ENGINEERING_DOMAIN_REGISTRY.json v1.1.0 (sync test enforced) |
| The upstream decision | `engineering_spec.py` | `why_this_domain.canonical_family` + `applicability.canonical_domain.canonical_family` — decided ONCE from the problem's own words (resolve_canonical_family: biomedical whole-form device-identity dominance + keyword routing, full score table recorded); the application axis, orthogonal to the E21-D physics domain (a catheter is biomedical as a family, fluidics as physics — both recorded) |
| The shared consumer ladder | `engine/domains.py::resolve_run_canonical_family` | upstream field > registry problem-words > engine-domain mapping > honest generic — the ONE function the bridge domain spec AND the package compiler both call; cross-layer agreement by construction |
| Bridge consumption | `invention_bridge/domain_spec.py` + `bridge.py` | `build_spec_from_state` consumes the ladder; the ARCHETYPE is derived FROM the family (registry routing; within-family keyword refinement); the spec declares `canonical_family` + `technology_class` (the archetype, re-labeled presentation routing — never a second namespace); PROCESS_FLOW / GENERIC_FALLBACK / ENGINEERING_PARAMETRIC survive only as `representation_class`; the bridge entry enriches run_result from the run-dir persisted ENGINEERING_SPECIFICATION.json (Art. X authority — the replay-divergence fix) |
| Package compiler | `engine/package_compiler.py` v1.1 | identity.domain_family via the shared ladder; M-DOMAIN-CONTRADICTION compares in the canonical vocabulary (upstream decision vs declared; the two axes are orthogonal) |
| Gate invariant | `package_quality_gate/gates.py` gate A | NEW `A-NONCANONICAL-DOMAIN`: every domain_family declaration must be a canonical family id ('THERMAL', 'thermal_fluid_process', 'GENERIC_ARCHITECTURE', engine-domain ids as domain_family = broken invariant); gate C/U vocabulary keys are the canonical family ids (view.py DOMAIN_VOCAB; polysemous terms excluded per Art. XXI) |

The F1 defect (A-INTERNAL-DIVERGENT ['GENERIC_ARCHITECTURE',
'thermal'], zero packages emitted in R444) is closed end-to-end: the
recorded bench-p03 battery replay now emits ZIP_READY with 19/19
domain_family declarations = 'thermal'
(scripts/r445_buyer_package_continuity.py: bench-p03 thermal +
bench-x03 software_ml, one coherent domain throughout each package).
Battery: `tests/test_r445_canonical_domain.py` (16 tests: registry
integrity, the five required families resolve deterministically,
layer continuity through engineering spec -> domain spec -> geometry ->
artifact identity -> CIO -> package -> gate A, the F1 divergence
injection detected as a broken invariant, the single-wrong-vocabulary
shape detected, upstream-consumption override).

## R445-C2 addendum (2026-09-11) — the renderer measured and slimmed, not weakened

Operator directive R445-C2 (memory): the Visual Compiler's renderer
tree was measured component by component (per-process PSS at 12.5 Hz)
and reduced by deadweight removal only.

| Change | Module | Notes |
|---|---|---|
| Chromium process tree | `renderer/render.js` | --single-process --no-zygote: 7 processes -> 1 (zygotes/utility/GPU-split/isolated renderer merged), measured -44 MB with byte-identical WebGL output; micro flags remove services a one-page deterministic render never uses (disk cache, audio, remote fonts, site isolation, process pool) |
| Page memory hygiene | `renderer/render.js` | pmrem.dispose() once the environment texture exists; one reused occupancy readback buffer; per-artifact explicit GC (--js-flags=--expose-gc) |
| Measured parity | `R445/MEMORY_BUDGET.json` | same canonical GLB sha, same scene_spec sha, same 23-artifact ladder, same gate verdict, same node/geometry identity, same poster parity on every A/B run (baseline vs optimized); hero.png byte-identical; two-run teardown flat (no leak) |
| Outcome | `R445/R445_C2_ROUND_RECORD.json` | mean -62.8 MB on Case B (636.5 -> 573.7; final verify 496.2 MB); the 450 MB cgroup target reported MEMORY_TARGET_UNACHIEVABLE_WITHOUT_PRODUCT_DEGRADATION with the irreducible decomposition (quality-locked hero surface ~61 MB + 2048 shadow map ~35 MB + PMREM rig ~16 MB + Chromium/V8/node floor ~374 MB); memory guard thresholds UNTOUCHED; visual worker != CadQuery/OCCT proven by isolated import measurement (36.2 MB vs 458.7 MB) |

New defect filed to the Coder 2 surface: poster parity fails on large
high-detail models (caseC 0.8731 < 0.9, PRE-EXISTING — identical on
baseline and optimized); fail-closed held (suppressed + blocked).

## R446-C2 addendum (2026-09-11) — poster parity closed by presentation fix, the boundary made a regression

Operator directive R446-C2 (visual closure, not renderer reinvention):
the pre-existing poster-parity defect is fixed INSIDE the presentation
boundary; the isolation proof became a standing regression; the typed
skip and the 3D truth vocabulary are surfaced honestly in the webapp.

| Change | Module | Notes |
|---|---|---|
| Poster parity fix | `visual_compiler/renderer/render.js` | MEASURED cause: the opaque paper underlay flattened the hero's soft alpha (posterRGB = heroRGB*a + paper*(1-a) verified pixel-exact; mean luma delta -149.75 over 2.62% of the frame — the 42%-opacity contact shadow; a 1024-wide resample was suspected first and FALSIFIED by the native-resolution replay, parity 0.8735 unchanged). Fix: the poster composes IMMEDIATELY after the hero shoot from the SAME canvas state at the hero's NATIVE resolution (1:1 blit), and the paper is painted ONLY in the bands outside the hero rect — the image area carries the hero's exact RGBA. Gate measurement: caseC 0.8731 FAIL -> 1.0 COMPLETE_PASS; caseA/B 0.9037 -> 1.0; threshold 0.90 UNTOUCHED; hero.png byte-identical; source GLB + scene_spec shas unchanged; every other artifact byte-identical (A/B vs the R445 optimized artifacts) |
| Isolation regression | `tests/test_r446_visual_isolation.py` | the R445 proof (worker != CadQuery/OCCT) is now mechanical: AST scan (no engineering imports), fresh-interpreter sys.modules probe, import-footprint class bound (chain 36.2 MB vs stack 458.7 MB measured R445; bound 150 MB), node-subprocess boundary; attack-proven (an injected `import cadquery` fails the battery) |
| Typed skip surfaced | `TOSCANINI_UI/webapp/components/DossierSections.tsx` | the dossier now shows the typed render state when the hero is honestly absent: RENDER_SKIPPED_LOW_MEMORY reads verbatim "Engineering geometry available; visual rendering unavailable at current deployment capacity." — never "rendering failed", never "visualization complete" |
| 3D truth badge | `TOSCANINI_UI/webapp/components/TechStage.tsx` | the gate badge now treats the canonical COMPLETE_PASS as a pass (it displayed the failing style on every post-R443 certified render); the existing vocabulary already separates engineering geometry / computational render / physical validation ("renders never validate physics") |

Battery: r441+r443+r444+r446 = 83 passed (five live adversarial attacks
included); r443_audit_fixes + r419_product_surface 32; render-era 82
passed / 6 pre-existing (pristine-identical via git stash); english-only
5 passed; production `next build` green. Memory A/B (same sandbox, R445
vs R446 render.js): caseB within run variance, caseC peak LOWER
(composing early avoids the late-ladder accumulation spike); two-run
teardown flat at 46.7 MB x3. Production visuals remain blocked ONLY by
the owner capacity decision (Art. LXV escalation 5 stands).

## R447-SPACE-OWNER addendum (2026-09-12) — ONE canonical Hugging Face Space

Operator directive R447-SPACE-OWNER: the sole owner selected the canonical
HF Space on repository/deployment evidence (never title, creation time,
or appearance). The machine-readable authority is
`R447/CANONICAL_HF_SPACE_RECORD.json` (regenerable:
`scripts/r447_canonical_space_record.py`).

| Component | Value | Notes |
|---|---|---|
| THE canonical HF Space | `prateekm1/toscanini-prod-validation` | private, Docker SDK, cpu-basic, app_port 7860; the Space repo main branch IS a git-archive tree of this engine repo + the R446-HF adapter Dockerfile hunks (byte-level relationship, verified by tree/raw probes) |
| Deployed engine identity | `23910247` at selection time | verified through the authenticated `/api/version` (build_artifact source) AND git ancestry on the engine main line — never a dashboard claim |
| Deployment-specific state | `DURABLE_STATE_ENABLED=1` → the engine repo's `runtime-state-hf` branch | ls-remote verified (9a60d0dc); the Render deployment's `runtime-state` branch is a different, separate lineage |
| Noncanonical Space | NONE EXISTS in live state | the directive's premise of two Spaces is not verified by any channel (author listings for prateekm1/FounderPass/prateekm1007, three searches, 15 direct ID probes, one-branch Space repo); no Space was deleted, created, or modified by the selection; a pre-inspection deletion cannot be ruled out and is not claimed either way (Art. XI/XXV) |
| Governance rule | The canonical Space is the ONLY HF production target | no additional Space may be created; every HF deploy goes here; the Render host is a separate legacy deployment, not an HF target, and is unchanged |

Selection identity chain (all machine-verified at selection time): HF
enumeration → Space repo = engine git-archive tree → deployed engine
commit real on main line → R446 production implementation present in the
tree → durable-state branch present on the GitHub remote → live health
ok=true, discovery_ready=true (zai HEALTHY via the HF router at GLM-5.3).

## R447 (run-not-found fix) addendum (2026-09-12) — the owner capability's second transport

The operator-reported defect: a user starts a run on the HF Space and the
workspace shows "Run not found … it belongs to a different visitor … if
the rail is empty, the run did not register". Root cause: HF Spaces serve
the app inside a third-party iframe on huggingface.co — the `tosca_owner`
cookie (SameSite=Lax, third-party context) is never stored nor sent, so
every browser request arrived as a NEW visitor; runs 404'd and the
history rail was empty while the runs existed on disk the whole time (the
BS-018 class: session/authorization continuity, never a discovery
failure). The fix keeps R394 s15 semantics exactly (possession of the
opaque token IS the capability; denial stays the enumeration-safe 404)
and adds transports that do not depend on cookie policy:

| Transport | Module | Notes |
|---|---|---|
| X-Tosca-Owner header | `toscanini/server.py::_owner_key` | validated uuid-hex shape; run creation + /api/sessions responses carry the caller's OWN owner_key; the header converges the cookie where cookies work |
| Client persistence | `TOSCANINI_UI/webapp/lib/api.ts` | localStorage `tosca_owner_key`, attached by `apiFetch` to every API call; `streamUrl` for EventSource |
| Stream owner parameter | both SSE routes | EventSource cannot set headers — the same opaque capability rides `?owner=` (validated identically; wrong owner → 404, never a silent hang) |
| CHIPS cookie | `server.py::_owner_cookie_header` | behind an HTTPS proxy (X-Forwarded-Proto) the cookie is SameSite=None; Secure; Partitioned (Chromium embedded contexts); plain-HTTP local dev keeps SameSite=Lax |

Battery: `tests/test_r447_owner_transport.py` (21 tests) — the exact
embedded-context sequence (old defect reproduced as the negative control,
then closed by the header), both run-creation API shapes, cookie/header
convergence and precedence, second-visitor enumeration-safe 404, five
forged-token bypass attempts, CHIPS-vs-Lax cookie shapes by context, the
SSE owner parameter (granted/denied/wrong-owner), and the route-wiring
contract pins.

## R451-C2 addendum (2026-09-12) — the blocked state becomes a first-class presentation state, and the geometry-to-visual join becomes machine-provable

Operator directive R451-C2 (Visual State Integrity + Guaranteed
Geometry-to-Visual Join): an infrastructure interruption must never be
visually confused with scientific absence (Art. LXI; BS-008/009/011/018),
and a legitimate engineering artifact must always be presented — while an
absent one must be explained without lying.

| Component | Module | Notes |
|---|---|---|
| THE ONE presentation-state mapping | `TOSCANINI_UI/webapp/lib/presentationState.ts` | seven states (INVESTIGATING / INFRASTRUCTURE_PAUSED / TECHNOLOGY_NOT_ESTABLISHED / GEOMETRY_UNAVAILABLE / GEOMETRY_READY_RENDER_BLOCKED / VISUAL_READY / SCIENTIFIC_REJECTION) resolved ONLY from the canonical user-state projection + dossier tabs — the frontend never re-derives state from raw fields and never reconciles conflicting signals (Attack C: infrastructure wins over stale scientific-looking fields); owns the canonical `isTerminal` (re-exported by RunNarrative — one definition) |
| The blocked surface | `TOSCANINI_UI/webapp/components/InfrastructureBlockedHero.tsx` | presentation-only; DISCOVERY PAUSED / Infrastructure temporarily unavailable. / No scientific conclusion was reached. / Your problem is saved and ready to resume.; compact (an absence state never occupies the model viewport); CTA hierarchy Resume primary · journal secondary · package disabled with its reason; the recovery rows (what happened / what was established / what remains unknown); the problem-context panel explicitly labeled "not an invention model" (no dimensional claims, no synthetic geometry) |
| Blocked insight cards | `presentationState.ts::blockedInsightCards` + `TechStage.tsx` | "Not evaluated — discovery paused before a technology state was established" class wording; the evidence card distinguishes NOT_REACHED ("Evidence retrieval not reached") from a MEASURED zero (numeric zero only when `retrieval_state == RETRIEVED`); scientific-absence phrases are structurally absent from the blocked path |
| NOT_REACHED != measured zero | `toscanini/dossier.py::evidence_ledger` | every exit carries typed `retrieval_state` (NOT_REACHED / PENDING / FAILED / RETRIEVED); numeric counts exist ONLY when the envelope exists (a RETRIEVED zero is the honest measured zero; Art. XXI.3/XXV) |
| Render-blocked state (C2.6) | `TechStage.tsx` ribbon + `lib/api.ts::retryPresentation` | GLB present + renderer skipped/failed/gate-failed -> "ENGINEERING MODEL READY — the engineering geometry exists. Presentation rendering is temporarily unavailable." with Retry presentation (POSTs the existing idempotent artifact-build job) — the canonical GLB stays interactive regardless |
| Invocation receipt (C2.9) | `visual_compiler/visual_compiler.py::_write_invocation_receipt` | `MODEL/3D/VISUAL_COMPILER_INVOCATION.json` written on EVERY compiler exit (render, typed skip, failure) with run_id / generation_id / canonical_glb_sha256 / geometry_spec_sha256 / compiler_version / invoked_at / status / skip_reason / output_directory — "GLB exists" vs "GLB was passed to the renderer" is now machine-distinguishable (BS-003/BS-030) |
| The end-to-end watchdog (C2.10) | `scripts/r451_c2_watchdog.py` | deterministic file-rule integrity check (R1 engineering GLB -> receipt exists; R2 rendered -> gate exists; R3 COMPLETE_PASS -> full 23-artifact ladder on disk; R4 hero source hash == canonical GLB hash; R5 skip -> typed reason; R6 no-GLB blocked run -> upstream projection (source-pinned); R7 receipt identity == run); NOT_APPLICABLE is never a violation (an infrastructure stop manufactures no failure) |
| Semantic colors (§10) | `TOSCANINI_UI/webapp/app/globals.css` | three documented state colors: LIVE = existing ok-green; INFRASTRUCTURE PAUSED = new calm slate --state-infra (documented reason: amber already means pending/progress, red is reserved for scientific rejection); SCIENTIFIC REJECTION = existing bad-red |
| Journal banner (§7) | `DeepDive.tsx` | PAUSED AT INFRASTRUCTURE above the recorded history; no artificial terminal failure event is manufactured |

Batteries: `tests/test_r451_c2_blocked_state.py` (20 — typed retrieval
states incl. the failed-retrieval and measured-zero cases; the receipt on
the no-renderer skip, the no-source skip and a REAL Chromium render; the
watchdog positive + four tampered fixtures each failing the SPECIFIC
rule + the CLI exit codes; the blocked user-state projection pins);
`scripts/r451_c2_ui_tests.mjs` (34 — the full §12/C2.13 regression
matrix over the compiled shipping module, Attacks A–E, the blocked-card
set, the isTerminal contract). Fresh-browser DOM proof (real server +
production build + headless Chromium): `R451/C2_PRODUCT/E2E/`
(DOM_EVIDENCE.json + blocked/success screenshots); success-state
regression green (real 3D hero, gate badge, populated cards — unchanged).
Constitution v2.4.0 read IN FULL at round start and re-read IN FULL
immediately before this commit.

## R451-C2.1 addendum (2026-09-12) — the false "3D unavailable" interpretation is impossible to reach

Operator directive R451-C2.1: the frontend must stop using the existence
of a 3D file as a proxy for the state of discovery. Five distinct
states with exact copy; a typed six-value geometry/visual vocabulary
derived by the BACKEND; and a DISCOVERY PIPELINE strip that answers
"why don't I have a 3D model?" with the recorded truth.

| Component | Module | Notes |
|---|---|---|
| Six-value geometry/visual state | `toscanini/dossier.py::_geometry_state` + `GEOMETRY_STATES` | upstream_not_reached / geometry_not_applicable / geometry_generation_failed / geometry_available / visual_render_failed / visual_complete — derived ONLY from canonical records (CIO geometry block, bridge outcome, render record, visual gate); `presentation_cause` splits State C from State D; the UI consumes it verbatim and NEVER infers it from a missing file |
| The five hero states | `TOSCANINI_UI/webapp/lib/presentationState.ts` | A blocked=DISCOVERY PAUSED; B invention-exists=**"Engineering visualization not available on this invention."** (HeroNoVisualization — never "Not established on this run" for an invention that exists); C renderer=**"Engineering model ready. Presentation renderer unavailable."**; D gate=**"Model rendered but did not pass the presentation integrity gate."**; E COMPLETE_PASS=the model shows. C/D copy selected by the backend's `presentation_cause`, never by the browser |
| DISCOVERY PIPELINE strip | `toscanini/dossier.py::pipeline_projection` + `components/DiscoveryPipelineStrip.tsx` | seven product stages (Problem/Evidence/Mechanism/Invention/Engineering/3D visualization/Package), typed statuses RECEIVED / IN_PROGRESS / NOT_REACHED / STOPPED / PAUSED_INFRASTRUCTURE derived from recorded artifacts only; the blocked run shows exactly the directive's strip (Problem RECEIVED, everything else NOT REACHED); the strip renders NOTHING when the projection is absent (never a guessed ladder) |
| No-file-inference attacks | `scripts/r451_c2_ui_tests.mjs` | F1 missing-GLB+typed-not-applicable never reads as technology absence; F2 GLB-present+no-render-record never reads VISUAL_READY; F3 gate-FAIL never reads as renderer absence; F4 upstream_not_reached falls through honestly; F5 typed visual_complete cannot override INFRASTRUCTURE_PAUSED; the vocabulary is closed (unknown values fall through) |
| Note honesty | `toscanini/dossier.py::design_tab` | the blanket "3D GEOMETRY UNAVAILABLE" note is gone; typed notes name the reach state or the State B sentence; the R430 pin test re-pinned to the new contract |

Batteries: `tests/test_r451_c21_states.py` (28 — the six states from
canonical records; the blocked strip == the directive's exact strip;
NOT_REACHED never carries a numeric zero, the RETRIEVED zero may;
source pins for the exact copy and the strip's backend-verbatim
rendering); `scripts/r451_c2_ui_tests.mjs` 55 checks (34 prior + 21:
five states, exact copy, Attacks F1–F5, closed vocabulary);
test_r430 re-pin green; regressions r441+r443+r444+r446 83 passed,
r447 join family 64 passed, r420/r419 green except two pre-existing
environment-class failures identical at the pristine baseline
(test_r419_scipy_free_geometry, test_r419_render_pipeline — BS-020
disclosed); tsc clean; next build green. Fresh-browser DOM proof with
real server + production build (R451/C2_PRODUCT/E2E_C21/): all five
states verified in the DOM with the directive's exact sentences and
the forbidden phrases verified ABSENT; the State C fixture was
auto-healed by the live mechanical join (C2.7 proof) and captured with
the artifact-build route blocked so the typed skip stayed authoritative.
