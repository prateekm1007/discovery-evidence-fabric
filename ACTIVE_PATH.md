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

## R449 addendum (2026-09-12) — the Evidence Fabric: federated evidence into the engine

Operator directive R449: connect HF-hosted datasets to the invention engine
(federated, no bulk warehouse, no second knowledge graph, no replacement of
the existing retrieval fabric).

| Component | Module | Notes |
|---|---|---|
| Canonical EvidenceRecord | `discovery_fabric/evidence_fabric/evidence_record.py` | ONE representation for every source (evidence_id, source_identity, exact_span{dataset/config/split/row_idx/field/verbatim text/sha256/document_ref/retrieval_query}, proposition, measurements (same-row columns), provenance, admissibility). The LLM interprets the span; it can never redefine it (Art. II/III) |
| Endpoint-aware custody | `evidence_record.py::verify_span_custody` | MEASURED LIVE: /search row_idx is NOT a stable address (the datasets-server search index numbers rows differently from /rows storage; load-balanced nodes disagree) while /filter row_idx IS aligned — filter records verify by pinned-row re-fetch, search records by RETRIEVAL REPLAY (same query re-issued, document_ref located, span bytes compared); tampered hash -> FAIL, wrong doc -> UNKNOWN |
| Source registry (frozen) | `R449/EVIDENCE_SOURCE_REGISTRY.json` + `registry.py` | the 10-seat production subset with license texts read + hashed: WOPTO (cc-by-4.0), OpenFOAM-Agent (mit), ColabFit-MP (cc-by-4.0), LeMat-Rho (cc-by-4.0), QM9 (apache-2.0, gap in HARTREE — unit discovery recorded), ChemRAG (mit); FAIL-CLOSED promotion (uspto + s2orc: license=None -> PENDING_LICENSE_VERIFICATION, never production evidence) |
| Federated connector | `evidence_fabric/connectors.py` | remote datasets-server /search //filter //rows; NOTHING bulk-downloaded; INDEX_LOADING + every failure class -> UNKNOWN (never absence, Art. XXI.3); the slash stays UNencoded in repo URLs (huggingface.co rejects encoded repo names — measured) |
| RETRIEVE integration | `engine/adapters.py::A2RetrievalAdapter` | the evidence fabric is an ADDITIVE channel inside the engine's RETRIEVE (ENGINE_EVIDENCE_FABRIC=0 disables); EVIDENCE_FABRIC_REPORT.json persisted per run; relevance adjudicated per record (Art. XXI.4) with TEXT term-overlap and STRUCTURED element-overlap modes |
| Source substitution | `evidence_fabric/substitution.py` | declared per-family ladders + coverage limitations; provenance preserved by construction; the forbidden LLM ladder has no functional representation (test-enforced) |
| Contradiction search | `evidence_fabric/contradiction.py` | contradiction-seeking queries against the same federated sources; ABSENCE != CONTRADICTION (NO_CONTRADICTING_EVIDENCE_FOUND is an index-scoped absence claim, never confirmation) |
| Novelty defense | `evidence_fabric/novelty.py` | KNOWN_MECHANISM / CAUSAL_COMBINATION (adjacency = LOW credit) / MEANINGFUL_NEW_INTERACTION / NEW_OPERATING_REGIME (+ R450's NOVEL_BEHAVIOR) |
| Two-arm evidence-power experiment | `R449/FRESH_EVIDENCE_POWERED_DISCOVERY.json` + `EVIDENCE_RETRIEVAL_RUN.json` | genuinely fresh seawater-corrosion problem, same engine/transport/gauntlet: Arm A (V2 fabric only) 13 items vs Arm B (+ evidence fabric) 25 items, 12 fabric-sourced; HONEST VERDICT: mechanism_search_changed=true BUT evidence_fabric_sourced_mechanisms_present=false (the fabric's records entered the pool and did not win the synthesis rotation — recorded as the honest negative component) |

## R450 addendum (2026-09-12) — the Directional Improvement Engine

Operator directive R450: a failed candidate produces a grounded, testable
direction of improvement; the loop executes a controlled intervention,
evaluates, and updates the causal model. Coder 1 owns the truth-generating
loop; the engine's evolution pipeline IS that loop (no second engine).

| Component | Module | Notes |
|---|---|---|
| DirectionalHypothesis (canonical primitive) | `discovery_fabric/directional/hypothesis.py` | machine-evaluable + provenance-bearing: failure_id -> causal_diagnosis_id -> target_variable/current->proposed/direction -> mechanism_affected -> causal_rationale -> predicted_effect(+magnitude) -> competing_explanations -> evidence_support/gaps -> falsifier -> measurement_required -> intervention_type -> confidence -> status; closed vocabularies (9 directions, 8 intervention classes, 7 statuses) |
| THE GROUND GATE | `hypothesis.py::ground_gate` | five mechanical checks (G1 structure+vocabularies, G2 diagnosis resolves, G3 mechanism term-grounding, G4 measurable falsifier — units/quantities/comparative-experiment forms, G5 evidence honest); UNGROUNDED -> REJECTED and the mutation NEVER executes ("increase fin size" with no causal chain is refused; brute-force mutation is not mistaken for intelligence) |
| The loop | `directional/loop.py` + `engine/run.py::_evolution_generate_next` | DIAGNOSIS -> gated hypothesis -> CONTROLLED MUTATION (the generation prompt EXECUTES the direction) -> EVALUATION (the same gauntlet) -> OBSERVATION -> CAUSAL UPDATE -> NEXT DIRECTION; stop reasons DIRECTION_REJECTED_BY_GROUND_GATE / DIRECTIONAL_PROPOSAL_TRANSPORT distinct from transport failures (Art. LXI) |
| Observation + signals | `directional/observation.py` | epistemic states (SUPPORTED/UNSUPPORTED/UNKNOWN/ABSTAIN/REQUIRES_EXPERIMENT) NEVER softened by the improvement-signal layer (objective_delta, constraint_delta, distance_to_target, information_gain, sensitivity); sensitivity ONLY from real recorded evaluation pairs (no fabricated gradients) |
| Causal update | `observation.py::causal_update` | prediction-vs-observation: MATCH -> SUPPORTED, MISMATCH -> FALSIFIED (negative knowledge), undecided -> EXECUTED/UNKNOWN (never silently support) |
| Trajectory persistence | `directional/trajectory.py` | IMPROVEMENT_TRAJECTORY.json (append-only V1->F1->D1->M1->R1->C1->V2 chain); raw counters only — NO composite score |
| Unguided control | `engine/evolution.py::UNGUIDED_MUTATION_PROMPT` | the benchmark's honest Arm B: generic improvement mutation with NEITHER the diagnosis NOR a hypothesis (same gauntlet, same budget) |
| Evidence -> direction (reverse path) | `directional/loop.py::serve_evidence_gaps` | DIRECTION -> declared gaps -> deterministic gap queries -> R449 fabric retrieval -> newly acquired support recorded ON the hypothesis (evidence_changed_direction) |
| Attacker v2.1 | `engine/independent_attack.py` | INTERVENTION suggestions with the SAME grounding discipline: GROUNDED_INTERVENTION = directional-loop SEED (still gate-bound); UNGROUND_SUGGESTION never enters the hypothesis space; calibration state inherited NOT_CALIBRATED (negative knowledge preserved; discipline NOT weakened) |
| Obvious-combination protection | `evidence_fabric/novelty.py` | NOVEL_BEHAVIOR: known A + known B -> evidenced interaction -> mechanism prediction -> RECORDED reproduction by evaluation (novelty-by-description never upgrades without the reproduction) |
| The benchmark | `scripts/r450_directional_benchmark.py` + `R450/DIRECTIONAL_BENCHMARK.json` | 2 fresh problems x 2 arms, raw metrics only. P0: both arms survived, ONLY the directional arm produced supported causal knowledge (1 falsifiable hypothesis + measurement contract). P1: the directional arm REFUSED its ungrounded proposal (vague falsifier) at ZERO evaluation cost; the unguided arm blind-rolled a survivor with no causal knowledge. Honest limitation: N=2 x 1 iteration — a first live demonstration, not a powered comparison |

The engine stage order is UNCHANGED; the directional layer lives inside the
evolution step (between the diagnosis and the generation) and after the
gauntlet (the observation/causal-update recording). No second invention
graph, no second canonical database, no new solver, no new provider.

## R451 addendum (2026-09-13) — the zero-paid local route + the transport capability layer

Operator directives R451-C1.1 (free-model closed-loop discovery) and
R451-C1.2 (transport capability and resilience): the engine survives the
HF account's credit exhaustion (402 on every router model) on a LOCAL
self-hosted route, and every future route is admitted by MEASUREMENT,
never by catalog presence.

| Component | Module | Notes |
|---|---|---|
| THE cost policy | `engine/model_cost_policy.py` | `MODEL_COST_POLICY=ZERO_PAID_COST` (the default since R451): only `ZERO_PAID_COST_SELF_HOSTED` bases are eligible; paid/env-grant/free-tier/undeclared are REFUSED fail-closed with recorded refusals; a preferred chain naming only paid providers EXTENDS to eligible rungs (recorded) instead of dead-ending POLICY_BLOCKED |
| The zero-paid provider | `engine/llm_registry.py` (`localqwen`) | Qwen/Qwen3-1.7B Q4_K_M (GGUF sha pinned, apache-2.0) on llama.cpp llama-server — an ORDINARY registry provider (same ProviderSpec shape, same rungs, no bespoke conductor branch); LOCAL_PROVIDER_READY six-rung proof chain (binary→model→server→HTTP→tiny completion→Toscanini structured output) |
| THE capability layer | `engine/transport_capability.py` | the R451-C1.2 contract: MODEL vs PROVIDER vs ACCOUNT (account_domain on every spec/rung/ledger line/provenance); FREE-CATALOG vs FREE-TO-OUR-ACCOUNT (catalog claims are class-labeled, never admission evidence); probe-before-admit; economic redundancy counted across ACCOUNT domains only (the 7 HF-router probe rows = 5+ providers on ONE account); the honest ZeroGPU separate-budget note (NOT_ACCESSIBLE_FROM_THIS_CODING_ENVIRONMENT) |
| MODEL_NOT_FOUND | `engine/provider_health.py` | a distinct failure class (404 + provider error bodies — the R450 glm-4-plus defect was INVALID_RESPONSE); marks the rung known-dead (never-retry), provider stays eligible; _CREDIT_HINTS classify 200-body credit wording |
| Transport observability | `model_routing.py` + `llm_registry.py` | every actual attempt (success OR failure) persists provider/model/attempt/status/failure_class/latency/cost_class/selected/fallback_reason; the in-result route reconstructs the exact path including the selected hop |

Measured this round (Art. XV): the acceptance chain CLOSED on a fresh
problem with every paid provider disabled (82 local / 0 paid calls →
evidence → mechanism → candidate → attack ADJUDICATED — an honestly
negative KILLED verdict); the CAD bridge closed through the
DETERMINISTIC ENGINE_TEMPLATE path (fresh geometric problem → warrants
WARRANTED → CadQuery/OCCT MODEL_BUILT_AND_VALIDATED → STEP/GLB hashed
derivatives → visual stage INVOKED with the typed low-memory skip, hero
suppressed, release blocked — Art. LXXII fail-closed held); the honest
model-quality numbers are recorded, never repaired (50% span-verbatim
synthesis; 13 validator-feedback attempts to a compliant technical
state — the gates byte-identical throughout, Art. VII). Round record:
R451/R451_C1_ROUND_RECORD.json.
