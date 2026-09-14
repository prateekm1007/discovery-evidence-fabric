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
> | Phase 1 audit | R389_PIPELINE_AUDIT.{md,json} (R455: both archived to `archive/r455-lean/docs/` — superseded; the R389-era "zero dead code" claim was scoped to 41 modules and is corrected by the R455 deadweight elimination: 418 modules measured unreachable from production at R454, 370 files archived this round) | superseded by the R455 measurement |
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
| 3D DESIGN | `discovery_fabric/engine/cad_pipeline.py` (R380: sandboxed AST-scanned build programs, G1–G8, trimesh as independent verifier). R455: the historical `premium_package_factory/r381/` template set is ARCHIVED_TO `archive/r455-lean/` (unreachable from production); the live package path is `engine/package_compiler.py` + `invention_bridge/` | `ADR_R380_CAD_PIPELINE.md`; `TOSCANINI/R380_LIVE_POSITIVE/` |
| DECISIVE EXPERIMENT | `discovery_fabric/engine/experiment_selector.py` (killer-experiment stage, engine stage order) | stage ledger `KILLER_EXPERIMENT` |
| ENGINEERING DOSSIER | `engine/package_compiler.py` (the live compiler) + `invention_bridge/package.py`; R455: the historical `premium_package_factory/` is ARCHIVED_TO `archive/r455-lean/` (the R374 `pathway.py` chain verifier retained for the cemetery cross-check) | gate certificates |
| BUYER PACKAGE | `engine/package_compiler.py` + `invention_bridge/package.py` (the live path) + `scripts/r386_release_chain.py` (four-state verifier; R455: `scripts/r385_root_docs_regeneration.py`'s factory dependency is archived — rebuild-from-source of R371-era docs now requires git history; delivery verification unaffected) | Article XXXIX chain: ENGINE RECORD ↔ CANONICAL MANIFEST ↔ PORTFOLIO TREE ↔ BUYER ZIP; 21 hermetic negative controls in `tests/test_r386_release_chain.py` |

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

<!-- MERGE UNION (PRs #4 -> #5 delivery): the two parallel rounds (canonical main R449-C1..R452-C1 and the visual-benchmark branch R451-C2..R452-C2) are both recorded below; each addendum carries its own date and directive -->

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

## R451-C1.3 addendum (2026-09-13) — the production transport authority + provenance closure

Operator directive R451-C1.3: the runtime admission authority and
run-level routing provenance, delivered and DEPLOYED to production.

| Component | Module | Notes |
|---|---|---|
| THE runtime admission authority | `engine/runtime_admission.py` | the five closed states (NOT_PROBED / PROBE_OK / PROBE_FAILED / PROBE_EXPIRED / POLICY_REFUSED); a route is runtime-admissible ONLY with a current measured successful capability probe through the rung's REAL transport (the existing TTL mechanism — no per-call probing); successful real calls refresh the window; real-call transport failures invalidate it; the LOCAL route uses the SAME rule (test-enforced); transient probe failures get one bounded retry, permanent classes never |
| Run-level routing provenance | `engine/call_context.py` + `run.py` + `model_routing.record_call_outcome/ledger_for_run` | `run_owned_call => run_id != null` FAILS CLOSED in the ledger; the 13 directive fields + capability_state + task_degradation on every line; provider probes are call_class=CAPABILITY_PROBE with run_id=null (legitimately not run-owned); ROUTING_LEDGER_RUN.json isolates one run BY RUN ID (no time-window/ledger-tail inference); the worker passes session_id; the durable push carries the ledger + capability store off the ephemeral container |
| Explicit task degradation | `llm_registry.generate()` + `mechanism_space.assemble_candidate` | requested_task / actual_task_capability / task_capability_match / degraded_reason on every selected line and in the candidate's derivation trace — a CHEAP_EMERGENCY_FALLBACK candidate is never read as STRONG reasoning |
| Catalog-discovered semantics | `model_routing._catalog_records` | DISCOVERED -> only catalog-present models are candidates (pinned-but-absent defaults are stale identifiers, never attempted); UNDISCOVERED -> PINNED_DEFAULT explicitly marked; the family allowlist stays |
| MODEL_NOT_FOUND recovery | `model_routing.clear_known_dead_if_relisted` | a FRESH catalog relisting clears the known-dead mark and invalidates the stale capability record (deterministic, append-only recovery events; a TTL cache hit does not clear) |
| THE unified admission semantic | `llm_registry.select_provider()` + `generate()` | one runtime_admission() (available AND cost_policy_eligible AND measured_capability_eligible); no legacy weaker selector |
| The Space's OWN zero-paid route | `scripts/r447_hf_deploy.py` hunks + `toscanini/container-entrypoint.sh` | llama.cpp llama-server built from the pinned tag b10930 + the sha-pinned Qwen3-1.7B Q4_K_M GGUF (fail-closed acquisition — the sha256 gate rejected a malformed 63-char transcription during the third deploy build: THE PIN WORKED); env-gated LOCAL_QWEN_ENABLE=1; the entrypoint starts the server before the engine serves |

Measured this round (Art. XV): the zero-paid acceptance rerun closed
with ALL 14 gates on the run-level provenance invariants (a genuinely
fresh third-domain problem, 14 run-owned localqwen calls / 0 paid / 0
null-run_id lines, one live MODEL_FAILURE -> probe recovery measured in
the window, the task degradation explicit); the ZeroGPU experiment
closed at its honest structural terminal (HTTP 400 "ZeroGPU Spaces
only work with Gradio SDK" — the resource class cannot attach to the
Docker production Space; the two operator unblock paths recorded, not
taken); the production deployment at the pushed commit e50d56c0 with
the Article LXXI tuple VERIFIED (BUILD == RUNNING == HEALTH ==
ls-remote; drift GREEN; identity_tamper false) after three measured
build failures each root-caused and fixed; the fresh production run
(a genuinely fresh fourth-domain lyophilization problem) completed ON
PRODUCTION through the real user path: 22 evidence records -> mechanism
-> gen-1 candidate -> ATTACK/ADJUDICATION (CONTESTED) -> the package
honestly BLOCKED at the DOMAIN_INTEGRITY quality gate -> HELD_FOR_HUMAN
REVIEW, with 31 run-owned ledger lines (all 13 fields, run_id non-null,
0 paid) + 8 capability-probe lines + the capability store persisted and
verified from OUTSIDE the container through the durable push. Round
record: R451/R451_C13_ROUND_RECORD.json.

## R452 addendum (2026-09-13) — fresh discovery quality + the mechanistic falsification loop + the reachability restoration

Operator directive R452 (Phases 0-9) + the independent external audit's
Coder-1 fix mandate. The active-path stage map GAINS its missing organ:

| Component | Module | Notes |
|---|---|---|
| THE VALUE_SOURCING STAGE (audit A1) | `engine/value_sourcing.py` | the evidence->dimension binding the engine lacked: SOURCE_FACT (the problem statement's own number+unit, exact span + sha256) > COMPUTED (the mechanistic chain) > MODELLED (the candidate's declared design); NO source STAYS UNKNOWN with the explicit derivation — the Article XXVII <-> Article LX collision resolved explicitly (sourcing from evidence with a provenance hash is not threshold invention). Wired INTO the producer; the sourcing summary rides every engineering spec |
| THE MECHANISTIC SOLVER (Phase 5) | `engine/mechanistic_solver.py` | the R452 chain: candidate parameters -> canonical variables (all classified) -> Poiseuille equations -> baseline (never inherits the candidate's override, Art. XLVII) -> the problem's OWN threshold (requirement-context only, Art. XXVII) -> computed outcome; the closed epistemic vocabulary on every output; MODEL_INVALIDITY flags the solver's own validity limits |
| THE DECISIVE-EXPERIMENT CONTRACT (Phase 6) | `engine/decisive_experiment.py` | the 13-field constitutional experiment object; THE INVARIANT enforced mechanically — an experiment whose kill outcome is vacuous (can only confirm) is REJECTED as incomplete |
| THE CAUSAL LEARNING LOOP (Phase 7) | `engine/causal_learning.py` | CANDIDATE -> MECHANISTIC MODEL -> VIRTUAL EXPERIMENT -> FALSIFICATION/SUPPORT -> TECHNICAL STATE UPDATE -> AUTOMATIC MUTATION (the closed-form inverse of the experiment's own deficit — never an unrelated LLM proposal) -> NEW CANDIDATE -> RE-EVALUATION; the causal edge's six fields; SYNTHETIC_LOOP_VERIFIED honestly (computation, never external reality) |
| THE REACHABILITY JOIN (audit A2/A4/AT-6) | `invention_bridge/classifier.py` + `engineering_geometry.py` | param_id = the SEMANTIC name (never CP-nnn); the physical-site vocabulary widened to the domain families' own nouns; a routed-default form carries ENGINEERING_PARAMETRIC_DEFAULT_FORM + form_basis |
| LAZY OCP (audit C2) | `invention_bridge/bridge.py` | the ~500 MB cadquery/OCP import is paid ONLY on the ENGINEERING_3D path; the classifier is cadquery-free |
| CAPABILITY vs SCIENCE (audit B1) | `a2/classify.py` + `engine/run.py` | the output-contract failure classes are typed INFRASTRUCTURE_CAPABILITY / INCOMPLETE_INFERENCE_FAILURE — promotion still blocked (the verifier NOT weakened), but a model-capability failure is never again laundered into a scientific kill_reason (Art. LXI) |
| FORENSICS IDENTITY (audit C5) | `toscanini/worker_forensics.py` | engine_commit resolved from the BUILD-ARTIFACT identity (the /api/version authority) when the env pins are absent — new forensics lines attribute failures to the deployed commit |

The frozen discovery-quality instrument (scripts/r452_quality_instrument.py)
measures the ten directive metrics from the runs' OWN artifacts; the
reachability contract test (tests/test_r452_engineering_geometry_is_
reachable.py) spans producer -> classifier -> normalize -> builder ->
export on REAL inputs only — the chain the audit proved had ZERO test
coverage (its fixtures used a schema production never emitted).

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

## R451-C2.2 addendum (2026-09-13) — the presentation state is artifact-contract-driven and the geometry→visual join has NO silent gap

Operator directive R451-C2.2 (Canonical Presentation-State Integrity +
Automatic Geometry-to-Visual Continuity): `not_attempted` never reads
as renderer absence; the geometry state is decided by the recorded
engineering CHAIN (never by PARAMETRIC_MODEL.json alone); the strip's
milestones are canonical-record predicates; package BLOCKED is typed,
never auto-infrastructure; and the join
GEOMETRY READY → INVOCATION → RENDER → GATE → HERO is machine-provable
in both directions.

| Component | Module | Notes |
|---|---|---|
| THE visual-join evaluator | `toscanini/visual_join.py` (NEW) | closed 8-state vocabulary (NOT_APPLICABLE / NOT_REACHED / INVOCATION_PENDING / INVOCATION_MISSING / RENDER_BLOCKED / RENDER_RECORD_MISSING / STOPPED_GATE / VISUAL_READY) derived ONLY from canonical records (receipt, render record, gate, job record); observational — it writes nothing (Art. IX); undecided (None) when no records exist — never a guess (Art. XXV) |
| The artifact contract | `toscanini/dossier.py::_geometry_artifact_contract` | audits PARAMETRIC_MODEL → CAD_PIPELINE_LEDGER (outcome) → ENGINEERING_SPECIFICATION → BRIDGE_REPORT → STEP/GLB; PARAMETRIC_MODEL.json alone NEVER promotes into "engineering model ready" (pm-only COMPLETE runs classify geometry_generation_failed; live runs stay upstream_not_reached); CAD-ledger BLOCKED_TRANSPORT/NO_MODEL_NO_LLM are infrastructure, never failures (Art. LXI) |
| Receipt schema 1.1.0 | `visual_compiler/visual_compiler.py::_write_invocation_receipt` | the directive's exact field contract: run_id, generation_id, geometry_spec_sha256, glb_sha256, visual_compiler_version, invocation_status, skip_reason, render_record_reference (+ gate_version, invoked_at, output_directory); the 1.0.0 names superseded in the same change (Art. LXIV); historical 1.0.0 receipts stay READABLE (era normalization in both readers) |
| The join watchdog | `scripts/r451_c2_watchdog.py` | R8 (valid GLB + no invocation and no pending job → FAIL) + R9 (invocation claims pixels + no render record → FAIL) + the derived join_state in the report; the four directive implications each proven by an adversarial fixture |
| Strip predicates | `toscanini/dossier.py::pipeline_projection` + `_canonical_stage_record` | Mechanism = a canonical mechanism RECORD (envelope SYNTHESIZE/MECHANISM_SPACE/COLLISION with status OK) — the always-executing PREMISE_GATE never stands in; Invention = the canonical invention record (stage credit never substitutes); Engineering = realization exists AND its authoritative state says valid; Problem = the problem record (problem.json or the recorded submission) |
| Package blocked classes | `toscanini/dossier.py::_package_blocked_class` | VISUAL_GATE (release_verdict VISUAL_RELEASE_BLOCKED — outranks all) / SCIENTIFIC (failed gates B-/F-/G-/U-) / PACKAGE_INTEGRITY (other gate families, MODEL_VALIDATION_FAILED, COMPILE_ERROR) / INFRASTRUCTURE (transport-class stage/reason → PAUSED_INFRASTRUCTURE) / UNKNOWN (recorded verbatim, never guessed into infra); the row carries `blocked_class` and the strip renders it verbatim |
| The copy split | `TOSCANINI_UI/webapp/lib/presentationState.ts` + `TechStage.tsx` | five causes, five distinct sentences: renderer_unavailable ("Presentation renderer unavailable."), not_attempted ("Presentation render not yet started." — NEW), infrastructure ("Presentation rendering paused by infrastructure."), rendering_in_progress ("Presentation render in progress."), gate_not_passed (State D unchanged); an empty render status is not_attempted, never renderer absence |

Batteries: `tests/test_r451_c22_join.py` (50 — the contract negative
controls incl. the PARAMETRIC_MODEL-alone promotion block; the join
evaluator's eight states from records; the watchdog's four directive
implications; the strip predicate negative controls incl.
premise-gate-only ≠ mechanism; the package blocked-class matrix; the
structural C1/C2 boundary pins); r451 C2/C2.1 regression 48 passed;
r441+r443+r444+r446 83 passed; r447/r420/r419/r430 family 128 passed
(2 failures identical at the pristine baseline — the standing BS-020
environment pair); UI battery 54 checks (five distinct sentences,
Attacks F1–F5 re-pinned); tsc clean; next build green. Fresh-browser
DOM proof (R451/C2_PRODUCT/E2E_C22/): the not_attempted ribbon and
JOIN_FAILURE strip class, the infrastructure/in-progress sentences,
the VISUAL_GATE package class, and the A/E regressions all verified in
the DOM; the LIVE mechanical join auto-healed a seeded no-receipt
fixture end-to-end before the terminal-record guard was added to the
fixtures — §5's automatic invocation proven live. Constitution v2.4.0
(hash b54a1be9 == origin/main) read IN FULL at round start and re-read
IN FULL before this commit. No Coder-1 canonical state changed: the
CAD pipeline, the bridge, the package compiler, and the Visual Gate
are consumed, never modified.

## R451-C2.3 addendum (2026-09-13) — VISUAL_READY requires the release chain, and the identity chain is ONE

Operator directive R451-C2.3: the system must prove the exact
engineering geometry → canonical GLB → Visual Compiler join WITHOUT
trusting filenames, booleans, reports, or stale projections. Route
strings never establish geometry; a STEP never claims visual
readiness; reports never constitute realizations; and every identity
mismatch fails closed INSIDE the evaluator — not merely in a later
watchdog report.

| Component | Module | Notes |
|---|---|---|
| THE geometry artifact contract | `toscanini/visual_join.py::evaluate_geometry_contract` (moved from dossier.py — ONE implementation, two consumers) | geometry_available requires ALL seven conditions: artifact exists AND non-zero AND valid artifact identity AND generation identities match AND every recorded SHA matches the bytes on disk AND engineering authority is explicit AND no contradicting terminal failure. Authority reads RECORDED identity documents only (ARTIFACT_IDENTITY.json, the bridge report's class fields, the CAD ledger) — the CIO's derived class is never an authority source. Missing class stays UNKNOWN; legacy boolean-only stays readable but establishes nothing |
| ENGINEERING_GEOMETRY_READY vs VISUAL_INPUT_READY | the contract's two typed fields | A valid STEP (byte-checked ISO-10303-21 header) establishes the first and NEVER the second — the visual boundary requires the canonical GLB contract |
| THE release chain | `visual_join.verify_release_chain` | seven rungs verified from bytes: canonical GLB identity → receipt identity (glb_sha256 == bytes, run_id == run, geometry_spec_sha256 == the spec file) → render record source → gate PASS → required ladder on disk → hero exists → hero source identity (render record source == canonical; an exported hero.glb must match the record's own view hash) |
| Release-chain join states | `VISUAL_JOIN_STATES` (8 → 10) | gate PASS + any broken rung → RELEASE_UNVERIFIED (fail closed, per rung detail); engineering-ready but no canonical GLB → VISUAL_INPUT_NOT_READY. VISUAL_READY now means the full chain |
| One evaluator, two consumers | `scripts/r451_c2_watchdog.py` | the watchdog-local derive_join_state is DELETED (Art. LXIV disposition: superseded in the same change); the watchdog derives the state from `evaluate_visual_join` and keeps the record-level invariant rules (R1–R10: R10 couples the evaluator's announced state to the record invariants); the pre-C2.3 engineering-by-filename fallback is retired — missing class is UNKNOWN |
| Invention milestone validity | `toscanini/dossier.py::_invention_record_validity` | the strip's Invention row RECEIVES only on the record's REQUIRED VALIDITY STATE: {} → INVALID_EMPTY, truncated JSON → INVALID_MALFORMED (never silently absent), placeholder core fields → INVALID_PLACEHOLDER, missing core fields → INVALID_MINIMAL, recorded adjudication rejection → INVALID_ADJUDICATION |
| Engineering milestone | `toscanini/dossier.py::pipeline_projection` | RECEIVED requires the typed-valid geometry state AND the contract's ENGINEERING authority; the bridge-report fallback promotion is DELETED (a bridge report describes a realization, it does not constitute one); CONCEPTUAL/UNKNOWN never receive |
| Typed package classification | `toscanini/dossier.py::_package_blocked_class` | the free-text inference ("transport" in reason.lower(), "quality gate" in reason) is DELETED; the class consumes the compiler's typed stages only (QUALITY_GATE_BLOCKED → failed-gate prefixes B-/F-/G-/U- → SCIENTIFIC else PACKAGE_INTEGRITY; MODEL_VALIDATION_FAILED/COMPILE_ERROR → PACKAGE_INTEGRITY; typed infra codes → INFRASTRUCTURE; anything else → UNKNOWN verbatim) |
| Authority-aware ribbon | `presentationState.ts::renderBlockedTitle` + `TechStage.tsx` | the ENGINEERING MODEL READY claim exists only on the contract's recorded ENGINEERING authority; CONCEPTUAL → CONCEPTUAL MODEL; UNKNOWN/legacy → GEOMETRY AUTHORITY UNVERIFIED; two new typed causes with their own sentences: visual_input_missing, release_unverified (the cause vocabulary is closed at seven) |

Batteries: `tests/test_r451_c23_identity_chain.py` (the fourteen
directive false-positive attacks — fake GLB path, empty GLB, wrong GLB
SHA, wrong generation, wrong run_id, STEP only, legacy present=true,
empty/placeholder/minimal/malformed/adjudication-rejected invention
records, bridge report without realization, render record with wrong
GLB, receipt with wrong GLB, gate PASS + hero absent, gate PASS +
incomplete ladder — plus the identity-chain equations, the
one-evaluator coupling (dossier and watchdog announce the SAME state
on every fixture), and the clean-state byte-identical replay);
test_r451_c22_join.py 61 (supersessions disclosed in-file);
test_r451_c21_states.py 29 + test_r451_c2_blocked_state.py 20;
visual family 83 (== the pristine baseline); product family green
except the stash-verified pre-existing failures (BS-020 class); UI
battery 60 checks ALL PASS; tsc clean; next build green.
Fresh-browser DOM proof (R451/C2_PRODUCT/E2E_C23/): the complete chain
still reaches State E through the strict release chain (the
false-negative guard), the no-silent-gap failure stays visible, and a
mutated render-record source GLB fails closed live — STOPPED
[RELEASE_UNVERIFIED], never "Technology ready". Constitution v2.4.0
(hash b54a1be9 == origin/main) read IN FULL at round start and re-read
IN FULL immediately before the commit. No Coder-1 canonical state
changed: the CAD pipeline, the bridge, the package compiler, the
Visual Gate, and the visual-set ladder are consumed, never modified.

## R452-A3 addendum (2026-09-13/14) — the stronger-model experiment, measured

Operator directive (the model survey answering the A3 escalation):
three recommended experiment paths, each MEASURED live before any arm
ran (R452/MODEL_EXPERIMENT/ROUTE_AUTHORITY.json): HF-hosted inference
402 credits-depleted + zero is_free catalog models (re-measured);
local GLM-5.2/GPT-OSS-120B structurally infeasible on the 4 GB no-GPU
host; OpenRouter paid, excluded; the sandbox z-ai tier-2 grant's
platform token wiped by the mid-session environment reset (401
missing X-Token, re-measured). Per the operator's own
quantize-and-retry flowchart logic, the operative zero-cost comparison
is the self-hosted 4B step-up.

| Component | Module | Notes |
|---|---|---|
| THE EXPERIMENT DRIVER | `scripts/r452_model_experiment.py` | two arms, the frozen R452 assay problems imported byte-identical, the SAME deployed default policy on both arms (ZERO_PAID_COST), the MODEL WEIGHTS as the only variable (1.7B @8790 vs 4B @8791, same llama-server b10930, same Q4_K_M discipline); the model-purity + zero-cost invariant verified per run from the run-owned routing-ledger lines (a PAID_API or cross-arm model line fails the experiment closed) |
| THE MEASUREMENT | the FROZEN `r452_quality_instrument._case_metrics` imported UNMODIFIED + typed extractors | the eight directive dimensions from the runs' OWN artifacts; UNKNOWN/NOT_REACHED typed, never zero-filled (Art. XXV) |
| THE RECORD | `R452/MODEL_EXPERIMENT.json` | the honest reading is MIXED, dimension by dimension: evidence grounding 0.1367 -> 0.6459 (4.7x), the adversarial attack EXECUTED once (case C, honestly KILLED), the first live VALUE_SOURCING spec (5 SOURCE_FACT of 7, geometry_reachable) — but ZERO mechanism-space candidates retained (vs the 1.7B's 2), 2 of 3 attacks still NOT_RUN, no STEP exported; NO prose superiority claim |
| THE A3 ESCALATION | `R452/OWNER_GATED_ESCALATION_A3.json` | escalation_count 2 with the measurement attached; the elite-class question stays unmeasured at zero cost — the operator's three unblock paths are the only route to a tier-2 ceiling |


## R446-C1 addendum (2026-09-14) — the conversational orchestration layer

Operator directive R446-C1 (CODER 1 — Discovery Intelligence /
Claude-like problem processing): the machinery above is UNCHANGED
(the loop and the 16-stage STAGE_ORDER stay the authority); a layer
ABOVE them makes them adaptive, selectively executed, and cleanly
consumable by the product.

| Component | Module | Notes |
|---|---|---|
| Problem Understanding contract | `toscanini/conversational/problem_understanding.py` | the 12-field structured interpretation BEFORE the pipeline; every field typed {value, origin, basis, confidence} over USER_STATED / INFERRED_MODEL / MODEL_DERIVED_LLM / UNKNOWN; deterministic constructor (zero LLM) + guarded LLM enrichment (USER_STATED never overridden); persisted to the run dir before the engine starts — an INPUT record, never a discovery claim |
| Clarification rule | `toscanini/conversational/clarification.py` | ask iff materiality × uncertainty × answerability >= 0.35; at most ONE question per pause; "select your industry" structurally refused (directive §4's own bad example) |
| Adaptive stage policy | `toscanini/conversational/stage_policy.py` | RUN/SKIP/DEFER/BLOCK/STOP with reason + next_action + prerequisite evidence; the six-state non-execution vocabulary (NOT_REQUIRED / NOT_REACHED / NOT_RUN / BLOCKED / FAILED / SKIPPED_LOW_VALUE) with a TOTAL one-way mapping from engine/bridge statuses; the §14 evidence-sufficiency stopping rule; the weak-premise STOP (typed PROBLEM_EXISTENCE_UNESTABLISHED terminal — never a scientific rejection); the §23 lazy-execution artifact policy |
| NBA as controller | `toscanini/conversational/nba_controller.py` | re-computed from the CURRENT recorded envelope before every stage; the standing V4 formula (one scoring authority with orchestrator/next_best_action.py, two sites); preferred action + full ranked ledger persisted to NBA_CONTROLLER.json — the action actually determines the next execution path (directive §8) |
| Engine integration | `discovery_fabric/engine/run.py` (stage_gate) | ONE surgical site: an optional pre-stage callback; typed policy statuses persisted on the stage entries (SKIPPED_POLICY_LOW_VALUE / _NOT_REQUIRED / BLOCKED_POLICY / DEFERRED_POLICY / STOPPED_POLICY + downstream NOT_REACHED); gate failure fails OPEN to RUN; ABSENT gate → the conductor is byte-identical to pre-R446 (pinned by test) |
| Product events | `toscanini/conversational/product_events.py` | the directive §9 event vocabulary (+ CLARIFICATION_REQUESTED, RUN_BLOCKED) derived EXCLUSIVELY from persisted artifacts (basis_ref on every event); NOT_RUN attack can never emit CANDIDATE_SURVIVED; infra states emit RUN_BLOCKED never a verdict (Art. LXI); PACKAGE_READY requires the package report's own field |
| Run contract | `toscanini/conversational/run_contract.py` | the ~7-field product view (run_id, current_state, human_progress, next_action, artifacts, blocking_reason, uncertainties) — a projection of canonical state (completion marker + run_state phases + NBA), never a second state store |
| Conversation memory guard | `toscanini/conversational/conversation_memory.py` | "We proved candidate B" is CONTEXT-ONLY; the conversation path writes exactly three context fields — every scientific field refused with a typed record (directive §12) |
| Model provenance | `toscanini/conversational/model_provenance.py` | the §18 work-routing declaration (deterministic work has zero LLM call sites, by audit); the §19 provenance pack + AUTHORITY_DOWNGRADED detector (a cheap fallback never inherits a strong route's scientific authority) |
| Worker phases | `toscanini/worker.py` | phase 1.9 (PU + clarification pause → AWAITING_CLARIFICATION, resumable via POST /api/run/{id}/answer); phase 2.1 (enrichment + run-dir persistence); phase 3 (the NBA-driven gate closure); phase 3.5 (the artifact policy consulted before the bridge — a killed candidate generates no CAD/visual/package) |
| Product surface | `toscanini/server.py` | POST /api/run/{id}/answer, GET /api/run/{id}/contract, GET /api/run/{id}/product-events |

Acceptance: `tests/test_r446_conversational_orchestrator.py` (the
directive §24 A–J battery, 48/48) + the §25 benchmark
(`scripts/r446_adaptive_pipeline_benchmark.py` →
CODER1_ADAPTIVE_PIPELINE_BENCHMARK.json: 10/10 quality gates
preserved, LLM calls −33%, compute ops −13%, planning latency −22%,
verdict ADAPTIVE_SUCCESSFUL). Audit:
CODER1_CONVERSATIONAL_ORCHESTRATOR_AUDIT.md.

## R455 addendum (2026-09-14) — the deadweight elimination: subtraction, not architecture

Operator directive ("delete the useless code"), executing the independent
external audit EXT-AUDIT-LEAN-R454's deadweight register. **No stage, gate,
or epistemic control was removed.** The 16-stage conductor, the R453
adaptive admission, the R446 conversational layer, the visual compiler, and
the entire §O.7/§N do-not-touch set are byte-identical.

| Component | Disposition | Notes |
|---|---|---|
| THE archive | `archive/r455-lean/` | 370 files / 130,583 py LOC moved by `git mv` (Art. LXIV.3 step 1: move-to-archive; history preserved, Art. XI). Full per-group accounting + KEPT_BECAUSE dispositions: `archive/r455-lean/README.md` |
| Curated Python tree | 267,695 → 151,958 LOC | **−115,737 LOC (−43%)**; the production import closure from the 3 entrypoints is UNCHANGED (168 files / 90,817 LOC before == after) |
| `premium_package_factory/` | ARCHIVED_TO `archive/r455-lean/` | superseded by `engine/package_compiler.py` + `invention_bridge/package.py` (both reachable); the stage map above is corrected to the live path; `r374/pathway.py` retained as the cemetery-chain cross-verifier |
| `prior_art_v2` version families | ARCHIVED_TO (20 siblings) | one canonical per family retained (calibration_v3_9, obviousness_v39, elite_v3, retrieval_v3) + their hard dependency keeps |
| orchestrator dead subsystems | ARCHIVED_TO (16 files) | providers never constructed in production; **coverage_engine + alternative_ledger retained — the audit's "unreachable" claim is falsified by measurement** (orchestrator/__init__ imports them; the live engine lazily imports orchestrator) |
| `r411/` + `r412/` + unreachable benchmark/engine modules | ARCHIVED_TO | 19 historical round scripts that import them no longer run without `git checkout archive/r455-lean -- …` (evidence trees sealed, Art. XI) |
| Dead-surface tests | ARCHIVED_TO (48 files) | each retired test pins ONLY archived modules; every live-behavior test retained; zero new failures vs the recorded baseline (r424 17 / e21 8 / routing 1 pre-existing sets byte-identical) |
| Stale authority docs | ARCHIVED_TO (8 files) | R389 audit, RUNTIME_MODULE_PARTICIPATION_AUDIT, RELEASE_CHAIN_VERIFICATION ×3, HANDOFF_TO_NEXT_CHAT.md, DEPLOYMENT_CONFIG.json (contradicted live state on every axis — BS-019/BS-002) |
| Audit defect found (Art. XV) | disclosed | the audit's import-closure method missed lazy imports: `orchestrator/__init__.py` → coverage_engine/alternative_ledger are runtime-loaded despite being "unreachable" in a static closure. The audit's own §M rule ("removes unnecessary machinery, not necessary epistemic protection") was applied as the tie-breaker for every KEPT_BECAUSE deviation |
| Deferred (not this round) | — | the audit's behavioral items (survivor gate §O.1, capability-before-retrieval §O.2, skip envelopes §O.3, model_route truth §O.4, mechanism invariant §O.5), the §N.1 epistemic_integrity determination, the module-inventory merge (§B.3), round-artifact trees out of the image (§C.10), Blender tarball removal (§J) |
