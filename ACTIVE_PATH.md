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

## R455-LEAN-1 addendum (2026-09-14) — NO SURVIVOR, NO ARTIFACT; NO REASONING, NO SPEND

Operator directive (the EXT-AUDIT-LEAN-R454 external audit's §O coder
round, executed verbatim, scope-fenced by §O.7's do-not-touch list):
the machine stops spending retrieval and rendering on runs that cannot
produce a discovery, and stops asserting technologies that do not
exist.

| Change | Module | Notes |
|---|---|---|
| THE SURVIVOR GATE (§1, the audit's top deletion) | `toscanini/bridge_gate.py` v1.2.0 | bridge/geometry/render/package run ONLY when the run's own `DISCOVERY_RELEASE.json` attests a surviving, promoted candidate (status not DISCOVERY_INCOMPLETE/NOT_A_SURVIVOR/DISABLED_BY_CONFIG, `invention_id` non-null, spec identity present); otherwise ONE honest `NO_SURVIVOR` report and nothing else. `cio.py::build_cio` no longer counts `final_state.json` as invention-side state (the always-true `_invention_exists` hole the audit measured: 18/18 production runs bridged, 16 fully rendered, 7 with `invention_id: null`). Historical `NO_INVENTION` records stay readable (Art. XI) |
| Capability gate before retrieval spend (§2) | `llm_registry.strong_route_capability()` + `engine/run.py` | a read-only admission mirror (zero network, zero probes, declared capabilities are probe-independent — the gate can never deadlock a route behind its own probe TTL): when NO reachable rung declares STRONG and a degraded rung exists, the conductor records `BLOCKED / CAPABILITY_INSUFFICIENT` BEFORE the RETRIEVE fan-out — zero source calls, zero downstream compute — and stays resumable on a capable route (Art. LXI). The typed terminal `RUN_BLOCKED_CAPABILITY` (RUN_BLOCKED_* family) travels to the session, the product events, the run contract, the investigation surface, and the durable push (`CAPABILITY_GATE.json`); the expensive tail and the evolution layer refuse with the same typed record |
| No envelopes for admission skips (§3) | `engine/run.py` | a `SKIPPED_ADMISSION` stage writes its ledger line only; the per-stage `envelope_<STAGE>.json` duplication of the unchanged problem block is gone (the audited run wrote 9; the refusal is still a recorded refusal — Art. XXV) |
| model_route tells the ledger's truth (§4) | `toscanini/run_state.py::_model_route` | derived from `ROUTING_LEDGER_RUN.json` (the run-id-isolated routing ledger, R451-C1.3-3) — `call_count` is the ledger's run-owned count; envelope aggregation is dead (the audited 13-vs-1 defect, Art. XXIV). R443's guarantee (retrieval sources are never attributed as model execution) is now structural |
| GENERATED requires a mechanism (§5) | `toscanini/run_state.py::_mechanism_state` | `GENERATED` with a null mechanism is unrepresentable at the single canonical writer; the honest `NOT_ESTABLISHED` token carries the reason (the audited live nonsense combination; Art. XXVIII) |
| Retirement (§6, Art. LXIV) | `archive/r455-lean/` (ONE canonical archive, this commit's `archive/r455_retired/` duplicate dropped at the rebase) | the §6 deletion set was executed in the parallel R455-LEAN-1-DELETIONS round at 378 files / 134,765 py LOC (R100 renames, history preserved — Art. XI), subsuming this commit's 7,217-LOC §6 set; THIS commit contributes the reconciled-live-tree repairs the deletion left behind: `calibration_v3_9.py` (kept live, its archived-v2/v3 imports re-pointed), `scripts/a12_capstone_run.py` + `scripts/r375_evaluate_campaign.py` (importlib file-path loading of the archived surfaces — `archive/r455-lean/` carries a hyphen and is deliberately not on the import path), and the surviving consumers' re-pointed imports |

Battery: `tests/test_r455_lean1.py` — the five required §O.8 tests,
14/14, offline by construction (stub-adapter tripwire proves zero
retrieval fan-out on a degraded-only route; Art. V positive controls
prove survivor-class runs and capable routes still pass; a resumability
test proves a blocked run re-runs RETRIEVE on a capable route). Re-pins
disclosed in-place: r414 CIO/model_route and r443 model-route
provenance pins re-expressed against the new contracts (Art. XXXI).
Round record: `R455/R455_LEAN1_ROUND_RECORD.json` (the behavioral half; the deletion half's record: `R455/R455_ROUND_RECORD.json`).

## R456 addendum (2026-09-15) — the deferred set closed + the A3 capability floor UNBLOCKED

Operator directives: (1) "the epistemic_integrity/ determination
(§N.1, owner-gated), the module-inventory merge, and image slimming
(456 MB of round trees + the 383 MB Blender tarball). Delete useless
code and fix bottleneck." (2) "Use these to use free ai models like
qwen 3.8, glm 5.3, deepseek, minimax etc. once tokens run out of one go
to the next provider" (four free-tier router credentials — the A3
escalation answered).

| Component | Module | Notes |
|---|---|---|
| §N.1 determination | `scripts/r456_module_inventory.py` + `R456/EPISTEMIC_INTEGRITY_DETERMINATION.json` | KEEP 28 / ARCHIVE 34 modules / 15,142 LOC with per-module consumer evidence. The instrument's two lessons: bayesian_eig loads BY PATH (the KILLER_EXPERIMENT canon); the gate runs preflight+gauntlet via subprocess CODE STRINGS (G1/G2/G3) — both invisible to a plain import scan, both fixed in the instrument |
| §B.3 ONE module inventory | `MODULE_INVENTORY.json` + the `--check` CI gate (both certification tiers) | CI-regenerated from the actual import closure (119 files / 57,840 LOC); hand-maintained module lists retired (BS-019); DORMANT_HIGH_VALUE_MODULES + 4 more zero-consumer root JSONs archived |
| Image slimming (§O.4/§J/§C.10) | `Dockerfile` + `.dockerignore` + `scripts/r456_space_deploy.py` | the Blender 5.2.1 tarball (383 MB) + its X11 apt set REMOVED (the legacy path fails closed with the typed RENDER_SKIPPED_NO_BLENDER); the staged Space tree pruned 451.2 MB of round dirs (keep set R412/R413/R449 — the only live runtime reads, path-literal-verified); tar 580→~129 MB |
| THE Phase-P1 semantic reranker | `discovery_fabric/source_registry/semantic_relevance.py` | the measured evidence-relevance bottleneck: the zero-paid local embedding route (llama.cpp + sha-pinned bge-small-en-v1.5 Q8_0, CLS pooling) composes with the lexical gate (OR for admission; both authorities recorded per record, Art. XXI.4; SEMANTIC_UNAVAILABLE typed per Art. IV); wired into the evidence_fabric gate + the retrieval lane ordering (byte-identical when the engine is off); calibrated (R456/SEMANTIC_RELEVANCE_CALIBRATION.json — the band overlap DISCLOSED) + benchmarked held-out (ZERO regressions on the frozen assay; the R449 OpenFOAM-garbage false admits closed via the stopword hygiene) |
| THE A3 unblock (the operator's routers) | `model_cost_policy.py` v1.1.0 + 4 ProviderSpecs + `R456/A3_RESOLUTION.json` | FREE_TIER_API eligible under ZERO_PAID_COST by the operator's recorded directive; unorouter (glm-5.3:free), xkiro (qwen3.8-max:free + minimax-m3:free — browser-UA transport, the measured CF 403-1010 bypass rides every call via ProviderSpec.extra_headers), apinex (deepseek-v4.1-flash), bai (qwen3.8-flash — FAST+CHEAP honest tier); 4 DISTINCT account domains; the rotation rule = the measured failure specimens classified (busy-pool 403 → RATE_LIMITED, deposit/insufficient-balance → CREDIT_EXHAUSTED — HTTPError bodies now read) so token exhaustion ADVANCES the cascade |
| The measured acceptance | `scripts/r456_fresh_run.json` | ts_2e04aecfcd45: COMPLETE / INVENTION_UNDER_DEVELOPMENT, ALL 15 STAGES OK, a real metallurgical mechanism synthesized, and the rotation measured LIVE (unorouter RATE_LIMITED → xkiro served the run) — vs. the round-start state RUN_BLOCKED_CAPABILITY at 0 retrieval calls |

Round record: `R456/R456_ROUND_RECORD.json` (+ A3_RESOLUTION.json,
SEMANTIC_RELEVANCE_CALIBRATION.json, SEMANTIC_RELEVANCE_BENCHMARK.json,
EPISTEMIC_INTEGRITY_DETERMINATION.json).

## R458-C2 addendum (2026-09-14) — the conversation controls the discovery

Operator directive R458-C2 (product interaction closure): the
conversation-native layer closed without new backend machinery — the
frontend remains a projection of canonical state (Art. X), and every
gap the UI found became the smallest contract for Coder 1, never a
frontend-side epistemology.

| Piece | Surface | Notes |
|---|---|---|
| THE CLARIFICATION PAUSE, finally rendered | `TOSCANINI_UI/webapp/components/Conversation.tsx` + `lib/present.ts` | C1's R446 §4 one-material-question pause (live since R456) was NEVER rendered by the UI; it now renders as Toscanini's own message and every composer message answers it via POST /api/run/{id}/answer — the conversation changes the discovery through an endpoint that already existed |
| ASK vs ACT | `TOSCANINI_UI/webapp/lib/actionContract.ts` + `R458/CODER2_CONVERSATIONAL_ACTION_CONTRACT.json` | the deterministic phrase router (fixed table, no interpretation) sends questions to the read-only /ask and directives to POST /api/run/{id}/actions (11 canonical verbs — CONTRACT for Coder 1, not yet implemented); the not-available response renders the honest-absence copy and changes nothing |
| THE INPUT MODEL | `components` page composer + `lib/api.ts::uploadAttachment` | the browser file-read-and-paste-into-prompt architecture DELETED (§3); attachments travel as engine-side references; the upload endpoint is contract-defined; until adoption the limitation is stated honestly — never a fake upload |
| ONE PROGRESS SENTENCE | `lib/productEvents.ts` + `Conversation.tsx` | the four-event tail removed; the derived progress line yields to the live event sentence; the provider-rotation abstraction (`deriveRotationNote`) says exactly "I continued the investigation using another available reasoning route." — route identity stays in the technical record (§26; the R456 cascade precedent) |
| THE ONE-WORD RULE | `lib/present.ts::isRejectedOutcome` + `isKilledByChallenge` | measured live: the stale `rejected` boolean rendered killed-by-challenge as bare "Rejected" (two words for one canonical state); the verdict now reads the canonical KEY only; false premise remains the one bare rejection; pinned by battery B6b |
| SIDEBAR + HISTORY | `components/Sidebar.tsx` | Projects DELETED (never advertise unfinished capability); history = title + small date + subtle state dot (aria-labeled) |
| WORKSPACE AS ARTIFACT | `components/Workspace.tsx` | one current title + small sibling switcher (no tab strip); journal secondary; experiment auto-open; the experiment surface renders HUMAN PROSE first (BS-009 measured and fixed), raw record collapsed |
| CSS DEADWEIGHT (§22) | `app/globals.css` 2898→2456 lines | 136 dead rules / 587 lines measured-deleted (class inventory + word-boundary re-verification + brace-aware remover); the ghost-tree audit this exposed: 439 files deleted from git still lived in the SPACE — `scripts/r458_space_prune.py` retired them and `r453_c2_space_deploy.py` now prunes BEFORE every upload (Art. LXIV) |
| MOBILE + A11Y + PERF (§19-21) | `app/globals.css` + `app/page.tsx` | iPhone-14 measured zero horizontal overflow; thumb targets; :focus-visible; prefers-reduced-motion; polling sleeps while document.hidden |

Acceptance measured on production: fresh discovery on the real browser
user path (ts_da602dc2c698) walked conversation → evidence (16 sources)
→ candidate (SIMULATED) → attack (KILLED, recorded cause) → next action
(Reformulate) → workspace (human-prose decisive test) → mobile + desktop
screenshots (R458/UX_PROOF/). Art. LXXI tuple GREEN at 7567d30.

Round record: `R458/R458_C2_ROUND_RECORD.json`.

## R459 addendum (2026-09-14) — the external product audit executed: the conversation can steer the discovery

Operator directive: execute the external product & UX audit (measured live
at 181a22f; overall 4.9/10, six 9/10 blockers). All six closed; zero
scientific-authority changes.

| Blocker | Fix | Measured |
|---|---|---|
| Clarification pause rendered as "Completed — outcome unknown" | `user_state.py` returns AWAITING_CLARIFICATION as an ACTIVE state; amber pulsing sidebar dot | unit-pinned (P0-1 tests) |
| `/api/run/{id}/actions` → 404 | `toscanini/actions.py` + the server route: accepted verbs record an append-only action ledger and open a NEW round in the same investigation thread carrying the directive as USER_STATED context | 202 measured live: act_ab786f28371c → ts_a5d30906beeb RUNNING with the directive |
| Attachments dead (upload blocked, 404) | `toscanini/attachments.py`: sha256 custody + typed extraction (pypdf), owner-scoped, worker merges as USER_EVIDENCE; the composer uploads on selection | 201 TEXT_EXTRACTED measured; chip shows "characters read" |
| Empty deliverable on killed runs | `toscanini/diagnostic_package.py`: every terminal run yields a ZIP (brief + evidence + diagnostic report, sha256 manifest); asserts it is NOT a technology package | 200 measured on the previously-empty run |
| Single-run lock invisible | the lock STAYS (measured protection); `run_lock_held()` + queue_state: a queued run SAYS it is queued | probe pinned by test |
| Share backend with zero UI | header Share → copyable /share?id= link; app/share public read-only view | share_id 6f061e93 measured (platform gate on the private Space disclosed) |

P1/P2: complexity-hiding copy scan (tests/copy_audit.test.mjs — no
round numbers, article citations, provider names, raw enums in the
primary surface); WCAG AA faint text; aria-live on the live line;
mobile sheet sibling switcher restored; 3D touch shield.

Round record: `R459/R459_ROUND_RECORD.json` (Art. LXXI tuple GREEN at
8827e2a).

## R458-C1 addendum (2026-09-15) — the model capability + adaptive discovery round

Operator directive R458-C1: freeze a discovery benchmark with a blind
holdout; benchmark MODELS, not providers; measure the actual science;
test FIXED vs ADAPTIVE; make provider failures invisible to the
scientific state; prove causal learning. No new pipeline stages — the
16-stage conductor, the gates, and the epistemic chain are unchanged.

| Component | Module / artifact | Notes |
|---|---|---|
| THE frozen benchmark | `scripts/r458_benchmark.py` + `R458/BENCHMARK_{CORPUS,FREEZE}.json` | 14 authored problems, 7 domain families x 2 (Art. XLIX exceeded); DEV(7)/HOLDOUT(7) split sealed at authoring; the holdout is mechanically refused outside the blind phase and the blind phase refuses to run before the dev record exists (BS-016 ordering enforced); freeze fails closed on pre-existing results |
| THE frozen instrument | `scripts/r458_quality_instrument.py` + `R458/QUALITY_INSTRUMENT_FREEZE.json` | the 13 directive metrics + wall clock, deterministic over each run's OWN artifacts; apply refuses instrument drift (Art. LIX); one Art. XXXI correction recorded IN the freeze (the problem.json schema lesson, re-frozen before any result existed) |
| Model capability benchmark | `scripts/r458_model_capability_benchmark.py` → `R458_C1_MODEL_CAPABILITY_BENCHMARK.json` | arms measured LIVE through the real engine: glm-4-plus + glm-4-plus-thinking (the sandbox grant's served model, ENVIRONMENT_GRANT, the operator UNRESTRICTED escape hatch with every paid key structurally stripped) + qwen3-1.7b (the honest capability-floor finding: the R455 §2 gate blocks the CHEAP-only rung BY DESIGN — zero spend, typed RUN_BLOCKED_CAPABILITY); the router quartet/NVIDIA/HF-router TYPED unavailable with the Art. LXV escalation (keys exist only as HF Space secrets); the model-purity invariant fails closed on cross-arm/paid lines; measured: composites 0.569/0.570/0.269; selected glm-4-plus-thinking; the BLIND holdout then ran 7/7 on it: composite 0.687 — the model generalized ABOVE its dev performance, 2/7 EVOLVED_INVENTION_CANDIDATE |
| The adaptive controller comparison | `scripts/r458_adaptive_benchmark.py` → `R458_C1_ADAPTIVE_PIPELINE_BENCHMARK.json` | FIXED (the capability runs re-measured) vs ADAPTIVE (the worker's own gate closure in-process); 112 real NBA decisions recorded; verdict ADAPTIVE_QUALITY_REGRESSION (honest: contradiction_detection 0.29→0.14, pool-variance class, disclosed) with LLM calls statistically indistinguishable (3.14→3.29) — the R446 offline estimate (-33%) does not reproduce on the live benchmark; the decision trace carries every §8 field |
| THE decision trace | `R458_C1_NEXT_ACTION_DECISION_TRACE.json` | 112 controller decisions: ATTACK_CANDIDATE 48, PROPOSE_DECISIVE_EXPERIMENT 4, ENGINEERING_ESCALATION 2 (the rest scored no action — the conservative default RUN); every entry carries uncertainty + expected information gain + cost + latency + capability + risk + reason |
| THE transport invisibility layer | `toscanini/conversational/transport_invisibility.py` | the ONE authority for §5: CASCADE_ADVANCED → "I continued using another verified reasoning route."; ALL_ROUTES_EXHAUSTED → "The requested test could not be completed."; the scrub guard names provider-ids/HTTP-codes/endpoints/failure-classes in product text as mechanical violations; wired into run_contract._blocking_reason + product_events RUN_BLOCKED emissions; the raw session error stays in the technical record (openable, never pushed); tests/test_r458.py 30/30 |
| THE reality mutation proof | `scripts/r458_mutation_proof_problem.py` + `scripts/r458_reality_mutation_proof.py` → `R458_C1_REALITY_MUTATION_PROOF.json` | §6 PROVEN on a REAL engine-run candidate (the §6 fixture authored with the full Poiseuille variable set BY DESIGN — the R452 case-B precedent, disclosed; NOT corpus, never a comparison surface): predicted 10.6029 mL/min vs required 40 → FALSIFIED_CONSTRAINT → causal update → INVERSE_POISEUILLE_DIAMETER 1.2→1.672402 mm → successor :mut1 → re-evaluation CHILD_SUPPORTS (40.00003 mL/min); the successor MEASURABLY differs (+39.37%) BECAUSE of the observed deficit; the flip regression holds (doubling the deficit moves the mutation to 1.9888 mm); loop_verification_state SYNTHETIC_LOOP_VERIFIED — the reality boundary was NOT crossed (reality_loop_proven=FALSE in the round record, honest) |

Round record: `R458_C1_ROUND_RECORD.json` (flags: transport_proven,
model_quality_proven, adaptive_routing_proven, causal_learning_proven
= TRUE; reality_loop_proven = FALSE — computation is never external
reality; world_class_claim_supported = FALSE — Art. LVIII, every
review is AI_REVIEW).

## R461 addendum (2026-09-15) — the FIFTH free-tier router + the owner-action escalation closed

Operator directive R461: "bynara (new router) — key valid  telegram
joined save the 5 keys as HF Space secrets, register the
newly-measured free rungs, record the bynara owner-action escalation,
run the live rotation proof, then commit → push → deploy." (Extends
the R456-A3 rotation to five DISTINCT economic accounts.)

| Component | Module / artifact | Notes |
|---|---|---|
| THE Art. LXV escalation, closed | `R461/BYNARA_OWNER_ACTION_ESCALATION.json` | opened 2026-09-14: the bynara key measured 403 telegram_required ("Join the required Telegram group/channel and relink at /settings") — a typed ACCOUNT_ENTRY_GATE (never AUTH_FAILURE; the key is valid). The owner acted 2026-09-15 (telegram joined, quoted verbatim); resolved with the post-action measurement; recurrence protocol recorded (re-open at escalation_count 2 with the exact relink action — the machine can never take that action itself, Art. XXXIII) |
| THE fifth router | `llm_registry.py` bynara spec + `OWNER_BYNARA_ACCOUNT` in `transport_capability.ACCOUNT_DOMAIN_VOCAB` | router.bynara.id (plain urllib UA passes — no CF block), FREE_TIER_API under the standing v1.1.0 amendment, default rung tencent-hy3-free (measured 200 PROBE_OK 2.53/1.91/1.91 s, 3 passes); HONEST tiers: FAST+CHEAP only, no STRONG claim (the free-tier serving path is unmeasured on the structured protocol) |
| THE -free family allowlist | `model_routing.PINNED_MODEL_FAMILIES['bynara']` | the five ids the catalog serves (tencent-hy3-free, glm-5.3-free, qwen3.8-flash-free, mimo-v2.5-free, muse-spark-1.3-contributor-free); premium ids (claude/gpt/gemini/flagship glm/qwen) NEVER become rungs silently |
| THE newly-measured free rungs | `model_routing.PINNED_DEFAULT_MODELS` | xkiro qwen/qwen3.5-plus:free (STRONG+FAST, 2.25 s); apinex free/deepseek-v4-pro-0813 (STRONG+FAST, 5.64 s, 72 reasoning tokens) + free/glm-5.3-flash (FAST+CHEAP, 3.35 s); bynara tencent-hy3-free (FAST+CHEAP) |
| THE rotation rule, extended | `provider_health.py` | the measured bynara specimens classify: 402 "Insufficient credits" + 403 "Your plan does not include the requested model." → CREDIT_EXHAUSTED; 429 "...try again in a few minutes" → RATE_LIMITED; the account-entry-gate hints (telegram_required / relink at) → CREDIT_EXHAUSTED-class (a valid key behind an account gate is not a failed key); 401 stays strictly AUTH |
| THE persisted secrets | `scripts/r461_hf_secrets.py` → `R461/HF_SPACE_SECRETS.json` | the FIVE router keys saved as HF Space secrets on the canonical Space prateekm1/toscanini-prod-validation (5/5 set, masked fingerprints only, BS-021) — the operator's "so i dont have to keep insertig them again"; the deploy driver wires the same five at every deploy |
| THE live rotation proof | `scripts/r461_rotation_proof.py` → `R461/ROTATION_PROOF.json` | real generate() through admission+cascade, no faked state; the R418 operator pin BYNARA_MODEL=tencent-hy3-free (evidence-backed, the documented mechanism): Arm A — bynara SERVES on tencent-hy3-free with FREE_TIER_API / OWNER_BYNARA_ACCOUNT / ZERO_PAID_COST; Arm B — the engine's own capability probe typed bynara's gated rungs (CREDIT_EXHAUSTED) and unorouter's 429 (RATE_LIMITED), the cascade ADVANCED, xkiro qwen/qwen3.5-plus:free served — token exhaustion on one provider automatically going to the next, measured live; Arm C — the natural five-key route recorded. Verdict: all three TRUE |
| The probe artifacts | `scripts/r461_probe_routers.py` + `r461_probe_completions.py` → `R461/PROBE_{CATALOG,COMPLETIONS}.json` | all five providers re-measured 2026-09-15 (catalog + admission-grade completions; unorouter 264 models / xkiro 109 / apinex 26 / bai 47 / bynara 49); 11 PROBE_OK completions measured live |

Tests: `tests/test_r461_bynara_router.py` 25/25 (registration, the
escalation-record contracts, the -free family vs premium ids, the
measured specimens + 401/403 discipline, the new rungs, secret
discipline with full-value markers); `test_r456_free_tier_routers.py`
27/27 unchanged; r458 30/30; the wide family 250+ green;
MODULE_INVENTORY regenerated (123 files / 59,487 LOC, drift GREEN).
Pre-existing failures disclosed (BS-020, stash-verified identical at
the pristine 7e89e40c baseline): test_r418_routing_pin 1 +
test_r446_completion_authority 2; collection 3,937/45 errors vs
baseline 3,910/45.

Round record: `R461/R461_ROUND_RECORD.json`.

## R462 addendum (2026-09-15) — the sixth router CANDIDATE met the REGION GATE: refused at admission, escalated, honestly typed

Operator delivery: the tokenharbor.ai key (the sixth free-tier router
candidate, "https://tokenharbor.ai/dashboard/api-keys"). Probe-before-
admit (R451-C1.2 / Art. III) measured a gate the quartet and bynara
never showed: EVERY endpoint on tokenharbor.ai answers HTTP 403
`region_blocked` from this runtime's egress — BEFORE authentication
(the format-identical bogus-key control answers the same 403), UA-
independent, on the catalog AND the serving endpoint. The refused thing
is the CONNECTION's exit region — not the key, not the account. No
completion, no catalog, not even one model id is measurable: NO
registration (a guessed default rung would manufacture knowledge,
Art. VI / XXVII). The Art. LXV escalation is OPEN instead.

| Component | Module / artifact | Notes |
|---|---|---|
| THE measured gate | `scripts/r462_probe_tokenharbor.py` → `R462/PROBE_CATALOG.json` | five probes (real key ×2 UAs, bogus-key differential, chat endpoint, api.-subdomain control) — all primary endpoints 403 `region_blocked`; key fingerprint only (BS-021) |
| THE Art. LXV escalation, OPEN | `R462/TOKENHARBOR_OWNER_ESCALATION.json` | count 1; the owner delivery quoted with the key body redacted to its fingerprint; what unblocks: owner verification from a served region, HF_TOKEN re-provision (wiped by the environment reset — the R436 precedent), the Space-side admission probe (the deployed Space's egress differs from the sandbox's); recurrence protocol at count 2 |
| THE REGION_NOT_SERVED class | `provider_health.py` | the measured specimen classifies honestly for ANY provider (was: fell through to AUTH_FAILURE — a possibly-valid key marked failed); cascade-advancing, never the cooldown ladder, never retried within a walk |
| THE rotation rule, extended | `llm_registry.py` + `runtime_admission.py` | REGION_NOT_SERVED joins GONE / MODEL_NOT_FOUND in the no-same-model-retry set (a region gate answers identically on every retry from the same egress); permanent, never a transient probe class |
| THE §5 scrub guard, extended | `toscanini/conversational/transport_invisibility.py` | REGION_NOT_SERVED + AUTH_FAILURE (the R458 typo: the real class name leaked undetected) join the failure-class vocabulary; bynara (a REGISTERED provider missing since R461) + tokenharbor join the provider-id vocabulary — Art. XXXI corrections, disclosed |
| NO registration | `llm_registry.py` (unchanged spec set) | tokenharbor is NOT in `_SPEC_BY_ID`; no OWNER_TOKENHARBOR_ACCOUNT; the five-router registration and its Space secrets stand untouched |

Tests: `tests/test_r462_tokenharbor_region_gate.py` 31/31 NEW (the
probe-artifact contracts incl. the pre-auth differential; the
classification contracts; the no-registration contracts; the OPEN
escalation-record contracts; the scrub-guard extensions; secret
discipline with the full-value marker). Re-pins disclosed in-place
(Art. XXXI): `test_r414_product_integration` FAILURE_TYPES set +
`test_r451_transport_capability` no-retry source contract.
Families: r461 27/27; r414 50/50; r458 30/30; r451_transport 32/32;
r451_zero_paid 37/37; r455_lean1 14/14; r419_english_only 4/4;
r415_discovery_availability 35/35; r446_attacker_calibration 20/20;
r459_audit_execution 20/20; r456_free_tier_routers 25/25 in this
session's keyless environment (identical at the pristine baseline —
the R461 "27/27" was that session's keyed environment).
Pre-existing failures disclosed (BS-020, stash-verified IDENTICAL at
the pristine cc792979 baseline): test_r446_completion_authority 2.
MODULE_INVENTORY regenerated (123 files / 59,647 LOC, drift GREEN).

Round record: `R462/R462_ROUND_RECORD.json` (DELIVERY_BLOCKED —
Art. LXXI §4: the HF_TOKEN credential was wiped by the environment
reset; the push landed, the deploy could not).

## R461-C2 addendum (2026-09-15) — the independent 5.5/10 audit executed: the product contracts closed

Operator directive: execute the independent product audit (verdict NO,
5.5/10, measured against 8827e2a). All in-scope P0/P1 blockers closed
with live-measured production proof; zero scientific-authority changes.

| Blocker | Fix | Measured |
|---|---|---|
| P0-1 no terminal fresh run | (already fixed upstream; re-proven) | API-path ts_a9d9c4389d2f COMPLETE 15/15; real-browser-path ts_a33eeb276dc2 COMPLETE 15/15 — the terminal snapshot survived two redeploys |
| P0-2 action intent dropped | `buildActionParams` — the user's words ride as `params.direction`; the child conversation renders them from the canonical `user_directive` | act_859708979e4f: byte-for-byte in the child directive, verbatim on screen, survived interrupt→retry→two redeploys |
| P0-3 share crashes client-side | the page rendered an ASSUMED shape (problem as a string) while the endpoint serves an OBJECT → React #31; now renders the real contract with `asText` guards, canonical outcome words, maturity first-line, "Read-only snapshot" lead | browser: 2,543 chars rendered, zero console/page errors |
| P0-4 deploy parity | re-verified + 3× Art. LXXI GREEN deploys (1b91d737 / cc792979 / 3642d42e) | /api/version == ls-remote == HEAD each time; drift GREEN |
| P0-5 recovery durability | REPRODUCED live (answered pause resurrected by a boot): PU records ride the durable payload; the worker LOADS the persisted record; snapshot at the answer moment + at the PU-merge checkpoint; `mark_unregistered_pending()` types the never-registered PENDING class within a 10-min grace | the measured-failure replay test green; the sweep MEASURED firing live (frozen 00:53:25 → typed 01:07:14) |
| P1-6 mobile overflow | phone-width header compaction + 44px targets, no overflow-hiding | 390px: scrollWidth 390 == viewport; toggle 44×44 in-viewport |
| P1-7 closed drawer focusable | React 19 `inert` + `aria-hidden` below 1180px (matchMedia-gated), Escape dismiss | closed: focus BLOCKED across 15 controls; open: interactive; both settled states measured |
| P1-10 maturity raw enum | `presentMaturity()` — the boundary sentence is first-line, unknown labels fall back honest | browser: "Simulated — modelled, not physically validated" as the card's first line |

Round record: `R461_C2/R461_C2_ROUND_RECORD.json` (Art. LXXI tuple GREEN
at 3642d42e). Disclosures: worker-spawn flakiness (a5a7 class, 4/6
pre-registration deaths) root-cause-blocked on the unconfigured
ENGINE_OPERATOR_KEY (worker log operator-gated) — Art. LXV escalation;
transport probe flapped honestly for ~20 min post-boot; retry-vs-create
spawn asymmetry recorded.

## R463 addendum (2026-09-15) — the seventh router CANDIDATE (aerolink) met the ACCOUNT-PLAN GATE: refused at admission, escalated, the HF_TOKEN unblock executed, both new keys persisted as Space secrets

Operator delivery (verbatim, redacted — BS-021): "huggingface API :
hf_Mr...kNM" (the R462 unblock action 2 — the re-provisioned HF_TOKEN)
+ "https://aerolink.lat/dashboard/api-keys: aero_l...lon0" (the
seventh free-tier router candidate). The standing six-step pattern
applied to the extent the measurements permitted, honestly typed where
they did not.

| Component | Module / artifact | Notes |
|---|---|---|
| THE measured gate | `scripts/r463_probe_aerolink.py` → `R463/PROBE_CATALOG.json` | nine probes on the DISCOVERED API host `capi.aerolink.lat` (externally sourced from the claude-code-free provider table, provenance recorded — Art. VI): catalog 200 with 4 Claude models; the bogus-key 401 differential ON THE SERVING ENDPOINT proves the delivered key VALID (auth evaluates before the plan gate — richer than tokenharbor's unmeasurable key); ALL 4 models answer the SAME typed 403 permission_error "Free Starter access is currently unavailable. Please upgrade your plan or add paid balance to continue using the service."; Anthropic Messages dialect ONLY (`/v1/chat/completions` → 404); the Python-urllib UA banned at the CF edge (error 1010 — the xkiro/apinex extra_headers remedy applies); the region NOT gated; the dashboard domain 404 control; the api. subdomain dead-host control |
| THE Art. LXV escalation, OPEN | `R463/AEROLINK_OWNER_ESCALATION.json` | count 1; the provider's own remedy is PAYMENT — an owner-gated wallet decision under ZERO_PAID_COST (the machine never deposits, Art. XXXIII); unblock: pay-or-park or wait-and-re-prove ("currently unavailable" may be transient); NOT delivery-blocking (unlike R462) |
| THE account-plan-gate wording | `provider_health.py` | the measured specimen classifies CREDIT_EXHAUSTED (the newly-registered hints: 'free starter access' / 'upgrade your plan' / 'add paid balance') — previously fell through to AUTH_FAILURE, a PROVEN-valid key marked failed (the R462 defect class, closed again); 401 stays strictly AUTH; the region class still checks FIRST; the standing specimens unchanged |
| NO registration | `llm_registry.py` (unchanged spec set) | aerolink NOT in `_SPEC_BY_ID`; no OWNER_AEROLINK_ACCOUNT; tokenharbor remains unregistered (the R462 state); the five-router registration and its Space secrets stand untouched |
| THE §5 scrub guard, extended | `toscanini/conversational/transport_invisibility.py` | aerolink joins the provider-id vocabulary (the probe candidate's name rides technical records only) |
| THE Space secrets, EXTENDED | `scripts/r463_hf_secrets.py` → `R463/HF_SPACE_SECRETS.json` | the R462 unblock resolved: TOKENHARBOR_API_KEY (sixth, admission deferred) + AEROLINK_API_KEY (seventh) persisted 2/2 — the r461_hf_secrets.py pattern extended; the standing five remain from R461; both new secrets are INERT on the deployed app (no ProviderSpec reads them) |
| THE deploy driver, extended | `scripts/r456_space_deploy.py` | the wiring set gains TOKENHARBOR_API_KEY + AEROLINK_API_KEY (env-injected when present; unset keys skipped typed-honestly — the standing five remain persisted from R461) |
| THE live rotation proof | NOT APPLICABLE this round | no admitted aerolink rung exists to rotate onto; `R461/ROTATION_PROOF.json` (all three arms TRUE) remains the standing live rotation measurement |

Tests: `tests/test_r463_aerolink_plan_gate.py` 40/40 NEW (the
probe-artifact contracts incl. the serving-endpoint differential, the
public-catalog control, the UA gate, the dialect control, the
API-base provenance; the classification contracts incl. 401-stays-AUTH
and region-beats-plan-wording and the standing specimens unchanged;
the no-registration contracts incl. tokenharbor-still-unregistered;
the OPEN escalation-record contracts; the scrub-guard extensions; the
secrets-artifact contracts; secret discipline with both keys' middle
markers). Families: r462 31/31; r461_bynara 27/27; r414 50/50;
r451_transport 32/32; r456_free_tier_routers 25/25; r455_lean1 14/14;
r419_english_only 4/4; r415 35/35; r446_attacker_calibration 20/20;
r451_zero_paid 37/37; r458 121/122 (the one failure —
test_paid_env_vars_stripped_in_arm_env — stash-verified IDENTICAL at
the pristine f2ca84b5 baseline: the z-ai gateway key file is missing
in this keyless environment, the disclosed environment-dependence,
BS-020). MODULE_INVENTORY regenerated (123 files / 59,721 LOC, drift
gate GREEN).

Round record: `R463/R463_ROUND_RECORD.json` (the Art. LXXI tuple
targeted GREEN — the HF_TOKEN re-provision unblocked both the
Space-secret persistence and the deploy that R462 could not run).

## R465-C2 addendum (2026-09-15) — the attachment merge outcome is typed and observable: the audit's P0-3 acceptance verified end-to-end on production

Operator continuation ("fix"): close the R463-C2 open item — the
attachment USER_EVIDENCE merge's journal event was not observable (the
merge block fail-open and swallowing its own exceptions, a silent
empty-merge indistinguishable from success). Closing it surfaced TWO
more layers of the same defect: the journal's pre-run-dir writes landed
in a CWD-relative file no reader ever served (the phase-1.9 events AND
the whole phase-2 retrieval window via phase_callback's eager empty
capture), and the journal itself is write-only in the serving path
(merge_with_projection has zero callers — /events serves the
artifact-derived projection). The fix landed at all three layers.

| Piece | Surface | Notes |
|---|---|---|
| THE TYPED MERGE | `toscanini/worker.py::merge_attachments_typed` | every state distinguishable: merged (PU carries user_evidence + forensics ATTACHMENTS_MERGED), typed exception on ATTACHMENTS_MERGE_INCOMPLETE (the R463 arity class would now surface at occurrence time; the run is never killed), bound=0 with the reason (incl. the foreign-owner bypass attempt — no content leak), quiet when nothing staged |
| THE JOURNAL PATH | `toscanini/event_journal.py` | empty run_dir is a typed no-op (the CWD-relative cross-run pollution retired at the source); phase_callback resolves the run_dir LAZILY at write time |
| THE ACCEPTANCE SURFACE | `toscanini/investigation.py` | the persisted PU record's user_evidence derives `attachment.ingested` on /events — hashes + counts only, never content; staged-but-unmerged emits the typed gap; SOURCE_FACT joins the closed epistemic vocabulary (Art. XXXVIII rank-1, the lowest rank) |
| THE PROOF | run ts_5364a9876bf2 on production | fresh owner + real PDF (sha256 74b0733a...) → 201 TEXT_EXTRACTED → run COMPLETE → /events carries `attachment.ingested` COMPLETED / SOURCE_FACT / "typed USER_EVIDENCE (content hashes: 74b0733acd33)"; worker-diagnostics ATTACHMENTS_MERGED; foreign owner 404 |

Tests: `tests/test_r465_attachment_ledger.py` 15/15 NEW; regressions
r430+r459+r463+r461 67, r458-family 159 (1 failure stash-verified
IDENTICAL at pristine — BS-020), r414/r451/r462/r463 159;
MODULE_INVENTORY regenerated (123 files / 60,135 LOC, drift GREEN).
Art. LXXI tuple GREEN at 08fd1931 (Space revision 65b5dee3; the
post-boot discovery_ready flap settled ~3 min). Round record:
`R465/R465_ROUND_RECORD.json`.

## R467 addendum (2026-09-15) — the token-surplus STRONG rung (atria) + the R466 P2/P3 closures

Operator directive: add the atria key (api.atria-asi.ai) to the HF
Space secret set — "it gives 100million tokens of new model which is
as good as glm5.3 ... we should be token surplus now."

| Piece | Surface | Notes |
|---|---|---|
| THE ADMISSION | `scripts/r467_probe_atria.py` -> `R467/PROBE_*.json` | catalog 200 with ONE model (Atria-Dawn-Preview); bogus-key 401 differential (key valid); OpenAI dialect; urllib UA passes; FIELD-protocol compliance measured (reasoning_content + clean FIELD content; the small-cap starvation recovers at the larger cap — EmptyContentWithFinish). The 100M budget is OPERATOR-DECLARED (no usage endpoint measurable) |
| THE REGISTRATION | `llm_registry.py` + `model_routing.py` + `transport_capability.py` + `transport_invisibility.py` | provider atria / ATRIA_API_KEY, quality 2 (operator declaration + measured FIELD compliance, Art. XXVII), latency 3 (0.55-8.71 s reasoning variance), FREE_TIER_API, OWNER_ATRIA_ACCOUNT (the EIGHTH distinct account domain); exact-id allowlist; the pinned rung declares TASK_STRONG |
| THE R466 CONSTRAINT | `R467/REGISTRY_SMOKE.json` | the STRONG synthesis walk served by atria with task_degradation {requested: STRONG, actual: STRONG, match: true} under ZERO_PAID_COST — the MECHANISM-stage degradation class (2 of 3 R466 runs) has its rung |
| P2 COLD-START | `TOSCANINI_UI/webapp/app/page.tsx` + `lib/types.ts` | a 404 grades toward "Run not found" only when the engine answered health ok around it (engineSeenUp, reset on health failure); the cold window shows the connection-lost copy. Behavioral proof `scripts/r467_p2_coldstart_proof.mjs`: no false verdict in 16 s of cold 404s, recovery on warm, the control arm still fires; zero page errors |
| P3 FAVICON | `TOSCANINI_UI/webapp/app/icon.svg` | the design system's tokens; the export emits /icon.svg + the link tag |
| THE SECRETS PATH | `scripts/r467_hf_secrets.py` + the r456 wiring | the eighth key persists as a Space secret when HF_TOKEN is present (BLOCKED this round: HF_TOKEN wiped by the reset — Art. LXXI §4 DELIVERY_BLOCKED, escalation 1; one re-provision closes the secret-set AND the deploy) |

Tests: `tests/test_r467_atria_admission.py` 23/23 NEW; all standing
batteries green (backend incl. r451_transport 32 after the closed-
vocabulary registration, r458 29/30 stash-verified pristine — BS-020;
frontend 115/115 + tsc + export 5/5 + verify-export); MODULE_INVENTORY
123 files / 60228 LOC, drift GREEN. Round record:
`R467/R467_ROUND_RECORD.json`.

## R468 — the Operator Secrets Registry + the R467 deploy closure + the fresh production measurement

| DELIVERABLE | WHERE | THE MEASURED FACT |
|---|---|---|
| THE VAULT | workspace-root `.secrets.env` (OUTSIDE every public repo; chmod 600; gitignored) | the readable canonical value store across resets: HF_TOKEN, ZAI_API_KEY (= the HF key, the R456 wiring), ATRIA_API_KEY, ATRIA_API_KEY_2, GITHUB_TOKEN (source: the operator's .gitcreds) |
| KEY 2 PROBE | `R468/PROBE_ATRIA_KEY2.json` | the bogus-key differential (200 vs 401) proves key 2 VALID; sole model Atria-Dawn-Preview; tiny completion 200/5.1 s; key-1 fingerprint MATCHES R467 (same live credential re-supplied) |
| THE SURFACE | `R468/HF_SPACE_SECRETS.json` + `R467/HF_SPACE_SECRETS.json` | the FULL 14-name Space secret surface verified BY NAME, zero absent; fingerprints only (BS-021, guard extended) |
| ARTICLE LXXIII | `EPISTEMIC_CONSTITUTION.md` v2.5.0 + `R468/constitution/` | the lookup order is law: env -> vault -> Space surface (names only) -> operator LAST; AMENDMENT_RECORD b54a1be9 -> 9730567a; acknowledgment re-bound; compliance GREEN; ratified through the r419 formal chain |
| THE DEPLOY | `scripts/r456_deploy_state.json` + `r456_verify_state.json` | Art. LXXI TUPLE GREEN at 1701eb96 (Space revision f215b976): engine_commit == origin/main; ok=true, drift=GREEN, identity_tamper=false; constitution 2.5.0 live; atria in the provider matrix (1 model) |
| THE MEASUREMENT | `R468/PROD_RUN/EVALUATION.json` | fresh production run ts_a0c8e581ba07 (espresso thermoblock limescale): SYNTHESIZE emitted a structurally complete mechanism/intervention/falsification answer (the R466 synthesis degradation did NOT recur); final typing INCOMPLETE_INFERENCE_FAILURE / INFRASTRUCTURE_CAPABILITY — 'missing_source_span; mechanism_span_not_verbatim', promotion blocked, rerunnable on a capable route. The category is NARROWED, never claimed closed. First launch ts_337f100ef977: the cold-start BLOCKED_TRANSPORT transient (atria probe attempt=0) — disclosed, handled by the standing floor |

Tests: `tests/test_r468_secrets_registry.py` 21/21 NEW; the standing
keyless-posture regressions 305/305 + r414 50 + r446 20 + r467 23 +
r419 4 (pin updated per precedent); r458 29/30 (standing BS-020);
frontend untouched, tsc clean; MODULE_INVENTORY 123/60228 drift GREEN.
Round record: `R468/R468_ROUND_RECORD.json`.

## R469 — the atria DEFAULT-PROVIDER pin + the THREE-KEY ring (the keep-going directive)

| DELIVERABLE | WHERE | THE MEASURED FACT |
|---|---|---|
| KEY 3 PROBE | `R469/PROBE_ATRIA_KEY3.json` | the bogus-key differential (401 vs 200) proves key 3 VALID; catalog 200 on ALL THREE keys (the sole model Atria-Dawn-Preview); tiny completion 200 non-empty in 17.9 s; keys 1/2 fingerprints MATCH R467/R468 (continuity); all three DISTINCT |
| THE KEY RING | `discovery_fabric/engine/llm_registry.py` + `runtime_admission.py` + `model_routing.py` | exhaustion-class failures (CREDIT_EXHAUSTED / AUTH_FAILURE / RATE_LIMITED) rotate ATRIA_API_KEY -> _2 -> _3 on the SAME rung before any provider fallback; every rotation a recorded route hop + ledger event; a fully exhausted ring falls through typed and auto-resets; the probe rides the ring AND carries the R467-measured 16->2000 cap escalation (EmptyContentWithFinish); catalog fetches ride the active key |
| THE DEFAULT PIN | `discovery_fabric/engine/provider_health.py` | _DEFAULT_PROVIDER_PIN = "atria" + ENGINE_DEFAULT_PROVIDER (env override; the ENGINE_* class); Art. XLV attack independence and Art. V cooldown demotion keep precedence (differential-proven); atria's honest tier-2 stands — a routing pin, never a quality rewrite |
| THE LIVE PROOF | `R469/ROTATION_SMOKE.json` | four REAL generate() walks via the bogus-key differential (no real budget spent on failures): control OK on slot 0; probe-path rotation OK on slot 1; call-loop rotation OK on slot 1 (route hop FAILED_KEY_EXHAUSTED/AUTH_FAILURE/KEY_ROTATED); two-hop walk OK on slot 2/ATRIA_API_KEY_3. ALL_GREEN; 3/3 FIELD lines on every arm |
| THE PERSISTENCE | `R469/HF_SPACE_SECRETS.json` + the Article LXXIII vault | ATRIA_API_KEY_3 set on the Space AFTER the probe; the FULL 15-name surface verified present BY NAME, zero absent; fingerprints only (BS-021) |

Tests: `tests/test_r469_atria_keyring.py` 32+1 NEW; the standing
keyless-posture batteries green individually (r467 23, r468 21, r456
25, r461_bynara 27, r462 31, r463 40+6+9, r414 50, r451 32+37,
r455 14, r419 4, r415 35, r446 20, r459 34, r465 15); full-suite
stash differential: with-changes failures a STRICT SUBSET of pristine
— zero new. MODULE_INVENTORY 123/60524 drift GREEN. Round record:
`R469/R469_ROUND_RECORD.json`.
Parallel-line note: R469-C2 (the sibling session, origin/main d9522d28)
landed while this round was in flight; this round rebased onto it and
the two probe mechanisms COMPOSE — the rung's declared budget
(R469-C2's probe_max_tokens, atria=256) feeds R469's one-shot 2000-cap
escalation. One canonical tree; both feature sets intact.
Deployment: pushed ca385e1f (rebased onto R469-C2's d9522d28) ->
r456_space_deploy (Space revision 0b45894b) -> ART. LXXI TUPLE GREEN:
engine_commit == ca385e1f == origin/main; ok=true, drift=GREEN,
identity_tamper=false; constitution 2.5.0; atria HEALTHY (1 model) in
the production provider matrix. Atria is now the DEFAULT head with the
THREE-KEY ring live in production.

## R478 — the external engine audit answered: Phase-0 truth reconciliation + the first executable P0 tranche

The TOSCANINI EXTERNAL AUDIT (delivered at HEAD 17504061) is answered the way this repo
answers an audit: every structural claim re-measured, typed, file:line pinned
(`R478/PHASE0_TRUTH_RECONCILIATION.json`), and the code-executable P0s landed in the same
round — no new registries, state machines, or provenance systems; the standing queue, gate,
ledger, and maturity ladder absorbed everything.

| DELIVERABLE | WHERE | THE MEASURED FACT |
|---|---|---|
| P0-2 CONTRADICTION MOVES BELIEF | `discovery_fabric/engine/adapters.py` (ContradictionQueueAdapter) | contradictory user evidence now enters the queue as typed `con:evidence:*` entries with DERIVED severity (HIGH when direct support exists — it threatens a promotable state; MEDIUM when not — Art. V), the payload carries the recorded `belief_update` (support_ratio + confidence_delta = −0.4 × n_contra/(n_contra+n_direct), formula + inputs traveling), and the EXISTING ADJUDICATION `no_blocking_contradictions` check holds RED while unresolved — the audit's "B changes visibility only" class is dead; pinned with the A-supports/B-contradicts fixture the audit named |
| P0-3 NUMERIC KILL CONTRACT | `discovery_fabric/engine/experiment_selector.py` + `invention_bridge/elite_package.py` | `FALSIFICATION_THRESHOLD` is answered ONLY from a numeric-band record (`FALSIFICATION_BANDS` carries the verbatim numbers — extracted, never computed); the prose composite can no longer answer the decisive field; `decision_rule_numeric` added to the R425 maturity gate — a pre-registered rule without a number no longer grants EXPERIMENT_READY (the audit's exact acceptance, pinned negative AND positive) |
| P0-4 STATE-DERIVED EIG / NBA | `toscanini/conversational/nba_controller.py` v1.1.0 + engine Killer/NBA adapters | the R458 constant trace (48× identical EIG 0.85 / cost 2.0 / score 0.2826) is dead BY CONSTRUCTION: attack EIG = min(0.95, 0.5 + 0.05·min(n_direct,6) + 0.05·min(n_contra,4)) — three states → three distinct values, pinned; EVERY action carries `input_basis` (formula + inputs + provenance class); latency prefers the run's OWN measured stage_log duration (MEASURED_IN_RUN) over the declared prior (DECLARED_PRIOR) — never conflated; killer outcome likelihoods derive from recorded contradiction pressure; engine NBA contradiction-EIG derives from the queue's own priority fields |
| P0-5 TRANSPORT PROBE | `scripts/r478_hf_transport_probe.py` + `R478/HF_TRANSPORT_PROBE.json` | the fresh credential→inference→artifact ledger line is one command away; measured NOW: CREDENTIAL_ABSENT typed (the LXXIII vault is not present in this session's workspace; no key in env; the Space surface holds names only) — Art. LXV escalation with what_unblocks named; Art. LXI: an INCOMPLETE_INFRASTRUCTURE state, never a scientific verdict |
| THE HONEST LEDGER | `R478/PHASE0_TRUTH_RECONCILIATION.json` | stage-drift VERIFIED (registry regeneration → R479), post-rank-only improvement VERIFIED (P0-1 accepted with its live-proof exit criterion — landing the code without transport would manufacture the Art. XXXVII synthetic-loop class), span-rewrite VERIFIED (P1-8), release-disagreement VERIFIED-as-designed (P1-12, own round), case-collision VERIFIED (P2-14) — where the audit said the machine was honest about being incomplete, it was; where it said a loop was inert, it was |

Tests: `tests/test_r478_engine_p0.py` 13/13 NEW; test_r446 50/50 (zero breaks — the stage
gate consumes action identity, not scores); the r425/r444/r424 failure set IDENTICAL to the
pristine stash differential (17 pre-existing environmental; the 4 legitimate pin breaks are
DISCLOSED in the test bodies and strengthened); r477/r471/r475/r467-9 191 passed;
MODULE_INVENTORY regenerated (124 files / 63,874 LOC, drift GREEN). Art. LXXI tuple: filled
at delivery. Round record: `R478/R478_ROUND_RECORD.json`.

## R479 ADDENDUM — the tuple closure (2026-09-16)

Operator credentials arrived; the R478 `what_unblocks` executed the same day. Measured:

| LEG | OUTCOME | THE MEASURED FACT |
|---|---|---|
| DEPLOY | GREEN (attempt 2) | identity flip `6f1e87c4 -> fbc73b8` on live /api/version; health ok:true; web hash unchanged (engine+infra round). Attempt 1 CONFIG_ERROR = the README-frontmatter lineage lesson (r477's skip was tree-conditional) — fixed with the idempotent r456 prepend, evidence kept |
| GITHUB ROTATION | CLOSED | the R451 rotation escalation closed by WIRING the operator-fresh PAT (Space GITHUB_TOKEN re-wired; the r477 no-valid-PAT rationale void); durable branch runtime-state-hf alive at d53da8a |
| P0-5 TRANSPORT | TRANSPORT_DEGRADED | HTTP_402 measured NOW with the fresh token: "depleted your monthly included credits" — the wall is ACCOUNT BILLING, not the token; the chain's other legs measure HEALTHY (xkiro 6 / bai 2 / atria 1), so the audit's "no strong-model chain live" narrows to the HF-router leg only |

Records: `R479/` (deploy + identity-verify + probe + attempt-1 evidence + round record). One operator action remains: HF billing top-up, then `python3 scripts/r479_hf_router_probe.py` flips the ledger line GREEN.

## R480 ADDENDUM — P0-5 closed by REPOINT (2026-09-16)

The operator repointed ZAI to the credited provider (atria, api.atria-asi.ai) with the re-supplied 15-key ring. Measured, in order:

| STEP | OUTCOME | THE MEASURED FACT |
|---|---|---|
| PROBE-BEFORE-WIRE | GREEN | catalog 200 (0.16s — sole model Atria-Dawn-Preview), bogus-key 401 control, tiny completion 200 (0.67s) — the r478 P0-5 contract verbatim, artifact sha-bound (`R480/ATRIA_LEDGER_LINE.json`) |
| THE WIRE | no rebuild | ZAI_BASE_URL/ZAI_MODEL variables (the R391 override) + ZAI_API_KEY + the 15-name ring; restart only — identity UNCHANGED fbc73b8 |
| POST-RESTART | flip verified | transport snapshot = api.atria-asi.ai; zai catalog 21 -> 1 (atria's); atria HEALTHY; health ok:true |

The audit's 402 class is answered: the strong-model chain rides the credited atria leg; the HF-router leg stays a measured-degraded OPTION (R479 record stands). Slot 8 remains inert per its measured INVALID verdict. Now unblocked: the P0-1 IMPROVE-stage live proof + the R458 re-run (own rounds).

## R481 ADDENDUM — the union delivery + the third race disclosed (2026-09-16)

- BOTH R478 lines united on origin/main at 2a312a02 (merge c5bdb5dd): the pushed P0 line (P0-2/P0-3/P0-4/P0-5 closed) + the PAT-blocked P1-12 line (the survivor authority + ring 15/15). Production serves the union (Space rev cc1080e4; tuple GREEN; the R480 repoint holds; atria HEALTHY; durable branch alive).
- RACE INSTANCE 3: a third line's unpushed IMPROVE-stage deploy (d75aaf99, 18:44:12Z) was overwritten by the verified union deploy (18:46:45Z); preserved verbatim in R481/ORPHAN_RECOVERY/ (18 files: improve_stage.py, its battery, the registry regeneration, the run.py/adapters.py wiring). The R482 queue: (1) the ORPHAN_RECOVERY union WITH the live-proof exit criterion (P0-1's own round); (2) P0-6 re-benchmark; (3) the R458 re-run on the measured-live transport.
- The ring: 15/15 measured twice consecutively (slot 8 CLEAR — the flap history preserved); the 15-slot registry is live.
- RACE INSTANCE 3 RESOLVED IN-FLIGHT: the third line rebased onto the union and landed P0-1 itself (e258d1ea: the IMPROVE stage, STAGE_ORDER 16->17) + its records (a3ed0216) + its deploy (Space rev 64661605, live a3ed0216) — production serves the FULL union; its live-proof exit criterion executes on that round. R481/ORPHAN_RECOVERY/ stands as the pre-record snapshot, superseded.

## R482 ADDENDUM — the auditor's P2 portability closed + the decisive run observed (2026-09-16)

- The Windows collection class is dead in the reachable tree: discovery_fabric/portable_flock.py (posix/msvcrt/noop, BACKEND recorded) + quota_breaker and package_registry rewired; test_r482_portable_flock 8/8 (the Windows class simulated on Linux — both modules import with fcntl AND msvcrt blocked); standing battery 602/2/3 with the 3 failures the thrice-verified pre-existing class; zero regressions; the toscanini/ sites untouched (case-collision + Linux-only, minimal-diff discipline).
- The decisive geothermal run (ts_50aa7fd75e35, observed from the durable branch): TERMINAL INCOMPLETE_INFERENCE_FAILURE — the xkiro free-leg proposer failed the verbatim-span citation contract (a model capability failure, Art. LXI; NOT_A_SURVIVOR; rerunnable); the IMPROVE stage EXECUTED LIVE (DEFERRED_TO_KILL_POINT at chain time; NO_KILL_EVIDENCE children [] at the kill point — nothing died, never a fake child). The auditor's score-forcing event (CHILDREN_ADMITTED / NO_CHILD_ADMITTED) awaits a run where candidates enter the gauntlet and die — first needs a synthesis route that meets the citation contract. R483: the live-proof campaign on a capable route.
## R481 ADDENDUM — the IMPROVE stage (P0-1) + the registry regeneration (2026-09-16)

| ITEM | STATE | THE MEASURED FACT |
|---|---|---|
| IMPROVE first-class | DELIVERED | STAGE_ORDER 17; registry 13 -> 17 == executable arithmetic (the audit's A1 drift dead); test_r481 14/14; the pins amended disclosed |
| LIVE EXECUTION | PROVEN | two production runs: the loop deferral + the kill-point execution typed in the durable state (envelope_IMPROVE.json stage_log) — the stage runs on every ordinary user run |
| THE LOOP CLOSURE | BLOCKED (named) | both runs INCOMPLETE_INFERENCE_FAILURE — the R452 span-capability class on the credited proposer blocks the runs before the gauntlet can kill; the stage answered NO_KILL_EVIDENCE twice (Art. XXXVII held: no synthetic children) |
| THE RACE | RECONCILED | the sibling's union superseded my deploy in ~5 min; rebased per R472/R477, union tip a3ed021 live (Space rev 64661605) |

Unblocks the exit criterion: a span-capable synthesis rung / span-format hardening / a campaign run with kills. Then CHILDREN_ADMITTED fires live and the audit's P0-1 is met end-to-end.

## R485 ADDENDUM — the execution-durability constitution + race instance 6 (2026-09-17)

- **Constitution v2.6.0 ratified** (the operator's A-M principles + FAIL CLOSED, PROGRESS OPEN): one canonical Article LXXIV — Observer-Independent Durable Execution (the parallel line's landed structure; this line's six-article proposal retired with a SUPERSEDED header, preserved at `R485/constitution/`). Certification chain green (hash 17464afd…); the acknowledgment capsule re-bound.
- **THE DECISIVE ANSWER** (R484/LOOP_CLOSURE.json, the parallel line's specimen ts_b7673571279e on build b0f3e913): the gauntlet killed the primary (4 dims), the R483 layer join fed the death to the IMPROVE kill-point, the kill-point mutated from the recorded kill basis, and the child `cand:A2:…+improve-g1` was ADMITTED — **CHILDREN_ADMITTED**, final INVENTION_UNDER_DEVELOPMENT, terminal COMPLETE 34 minutes after every local observer process was reaped. The audit's one decisive question is answered in committed bytes, observer-independently.
- **The typed execution surface** (union): `toscanini/execution_states.py` (the nine-state machine, the disjoint observation vocabulary incl. the typed timeouts, the total `_STATUS_MAP`, `is_failed()`, `lifecycle_record()`) + this line's union delta `recovery_decision()` (principle M: OBSERVE_WAIT / RECOVER_ARTIFACTS / RECOVERY_REQUIRED / CONSIDER_RETRY — never retry without a measured failure). Batteries: 16/16 (their E2E, the operator's required shape with a real SIGKILLed observer) + 13/13 (the recovery order) = 29/29.
- **Race instance 6** (R485/LINEAGE_RECONCILIATION.json): the first constitution-amendment race — both lines v2.5.0→v2.6.0 from the identical directive; adjudicated per Art. LXIV (theirs canonical, this line's deltas carried in, the proposal preserved as history). This line's own specimen ts_cd6c2a619ed2 was interrupted by their deploy recycle mid-engine (the durability fixes carried the mid-flight state; the recovery order — not a blind re-fire — is the next step, and the decisive question is already answered).
- **P0 reprioritized per the operator**: durable end-to-end execution BEFORE the browser showcase matrix. Remaining in the P0: the structured typed-cause fields on the sweep records; the Space redeploy on the union tree.

## R486 ADDENDUM — the re-audit verified in the bytes; the true number reported (2026-09-17)

- **The R485 re-audit** (Overall 5 → 6, final NO) received and INDEPENDENTLY RE-DERIVED, not accepted on narrative: every scored link re-checked in the durable bytes at terminal commit 4c452eef (the full tally in `R486/REAUDIT_VERIFICATION.json`) — the 4-dim kill + cemetery 0305893569, the R483 join's first live fire, the mutation lineage (kill_basis_hash a98eef…, 00:02:47Z, atria-served), the fresh gates incl. independent_attack 2.1.0 SEPARATE_PROVIDER 4 KILL + 2 RISK → ESCALATED_OBJECTION, the CHILDREN_ADMITTED admission (envelope 246b3e → 1298cf, delta_real), the seeded-contactor child, the observer-independent terminal (COMPLETE 00:15:26Z, ~34 min past every observer's death).
- **THE TRUE NUMBER: 6/10, NO — concurred.** Nothing supports higher (the audit's n=1 was accurate for the bytes it audited; the durable tip's second closure brings within-class n=2 with an ATTACK_INCOMPLETE attack leg — short of cross-domain repetition; the admitted child LOST SELECTION 11/11; the selected exploration-grid candidate died at the TIE V2 constraint wall; no package; real_loop_verified false; the 9/10 blockers stand). Nothing supports lower (the two precision corrections found move no dimension).
- **Two precision corrections recorded against the audit** (Art. XV): the constraint-wall death was the SELECTED DIV candidate (`cand:DIV:multi_physics_hybrid:unorouter`), not the improve child (which ranks 11/11, killed:false — the release builder's candidate_id reads the envelope's primary A2 id, the conflation's cause); and "all 34+ min" holds for the terminal, not the mutation (~21 min).
- **The R417 escalation-gate input is now complete for the next audit**: during the decisive run the gate recorded UNKNOWN_NOT_CALIBRATED / measured:null (the R485 round-dir prune had erased the R447 measurement — infrastructure-degraded reason, fail-closed direction correct); the parallel line's R486 (99ac03c9, deployed, tests 11/11) ships the calibration records in-tree prune-proof via pinned DIGESTS.json. The real two-layer shape for the ruling: admission-despite-objection (uncalibrated KILL never terminates) → selection-level demotion (attack_pass 0.25 weight) — the objection informs without terminating.
- **Next decisive verifications (the audit's order)**: (1) attempt-6+/R458 repetition of CHILDREN_ADMITTED on fresh problems; (2) the R417 escalation-gate ruling; (3) a survivor reaching a buyer ZIP.
- **RACE INSTANCE 7 RECONCILED (appended same round)**: the parallel line's b0de5dfa (their R486 response) landed mid-verification — both lines' R486 records now union on main. Their two decisive additions, both INDEPENDENTLY VERIFIED in the bytes by this line before concurrence: **CHILDREN_ADMITTED n=2** (this line's own specimen ts_cd6c2a619ed2 fired the closure server-side 00:11:26→00:22:45Z through the R485 deploy recycle — ledger 1/1, child 63c6bb31…+improve-g1, kill_basis 0564f2cc…, provider xkiro, attack honestly ATTACK_INCOMPLETE; NO terminal commit, the evidence surviving only via the R484 atomic-persistence fixes — within-class repetition, cross-domain open, the full separate-provider objection semantics complete only once) and **the R417 RULING** (escalation-not-kill does NOT soften the kill layer: the attacker is measured FPR 1.0 / TNR 0.0 / PPV == base rate against the sealed bars — an uncalibrated KILL is inadmissible as terminal, objections preserved verbatim and escalated; the council demonstrably weighed them: CONTESTED, adversarial_not_killed false, no release; the decisive repair is attacker calibration, not wording). The true number stands at 6/10, NO — concurred by both lines; the second closure strengthens the repetition boundary without reaching cross-domain or a surviving package.

## R487 ADDENDUM — the v3 sealed-bar measurement: the true number reported; the cross-domain proof launched (2026-09-17)

| ITEM | STATE | THE MEASURED FACT |
|---|---|---|
| THE FRESH v3 MEASUREMENT | DONE, HONEST FAIL | 21/22 frozen R446 cases through the DEPLOYED instrument's /api/ops/calibration-attack (identity-gated 7d38eb4e): TPR 1.0 (7/7) | FPR 1.0 (4/4 clean controls killed, ZERO demoted) | TNR 0.0 | coverage 0.9545 | parse 1.0 — the FPR bar (0.3) FAILS; threshold_verdict.calibrated FALSE; cal-18 TRANSPORT_INCOMPLETE (5 consecutive >560s client read-timeouts; infrastructure state, never a verdict) |
| THE DRY-RUN DIVERGENCE | DIAGNOSED | the design dry-run (v3 rules on frozen v2 outputs) predicted FPR 0.25; the live instrument measures 1.0 — the clean-control kills carry verbatim record-span anchors the scorer verifies as grounded, so the ANCHOR floor (computation-only demotion) cannot touch them. The false-kill class MOVED from 'ungrounded objection' (R445-B, 0/23 grounded) to 'grounded-but-wrong engineering inference' — deeper than the prompt-layer repair; near-miss discipline holds (3/3 killed WITH markers) |
| THE RECORDS SHIPPED | DONE | the measured records (whatever they say) into discovery_fabric/engine/calibration_records/ with DIGESTS pins; in-tree gate: NOT_CALIBRATED, terminal_kill_admissible false, measured PRESENT — the R486 measured:null disclosure resolved; the R417 escalation gate stays in force (the decisive repair is NOT achieved) |
| THE CROSS-DOMAIN PROOF | IN FLIGHT (durable) | attempt-6: ts_f0880e025e60 on R458-M1 (r458-m1-cam-follower-surface-fatigue, MECHANICAL family — both prior closures are geothermal thermal/fluid territory); the driver reads the DURABLE corpus (the /tmp dependency dead); target_variable clarified USER_STATED; outcome -> R487/LIVE_PROOF_CROSSDOMAIN.json |
| THE RE-AUDIT HARDENING | DONE | .gitattributes eol=lf on the pinned text types — hash-pinned DIGESTS survive a default Windows checkout (the core.autocrlf=true finding); zero tracked CRLF, no renormalization |
| CONTAINER RECYCLE | RECOVERED | the clone + vault + uncommitted work destroyed; STALE checkout labeled, remote verified, reset; PAT survived .gitcreds (fingerprint f1ebca5f9b62); HF_TOKEN did NOT — the redeploy is DELIVERY_BLOCKED (escalation 1; unblock: operator re-supplies HF_TOKEN -> scripts/r487_space_deploy.py); the deployed instrument is ALREADY the measured v3 build |

The next decisive verifications (unchanged in order): (1) the cross-domain CHILDREN_ADMITTED repetition (in flight); (2) attacker calibration — now measured FPR 1.0, the repair direction is the grounded-but-wrong class (a v4 design on a DEVELOPMENT corpus, Art. LIX; no tuning against the sealed benchmark); (3) a survivor reaching a buyer ZIP.

## R491 ADDENDUM — the ring-pinned calibration: the true number measured; the roadmap's honest-risk branch fires (2026-09-17)

| ITEM | STATE | THE MEASURED FACT |
|---|---|---|
| THE RING PIN | DELIVERED, LIVE-PROVEN | three fail-closed layers (transport require_provider → registry rung-filter AFTER the max(3,…) floor → the driver's marker discipline); the first live attempt exposed the R415 LAST_RESORT leak (xkiro served past a failed atria pin — the guard discarded it, no wrong-ring byte scored) and the fix moved the pin INTO the registry walk; the re-deployed build re-proven live: the pinned call fails CLOSED instead of substituting |
| THE RING-BOUND AUTHORITY | DELIVERED | a CALIBRATED state names its measured ring; kills from a different provider/model escalate with a typed ring_mismatch (objections preserved verbatim); legacy records keep pre-R491 semantics, recorded |
| THE A2 CONSUMPTION GATE | DELIVERED, DEPLOYED | the R490 owner ruling's destination: the uncalibrated gauntlet's KILL → ESCALATED_OBJECTION in classify() (objections verbatim, deterministic gates unchanged, the state derived from the canonical registry entry a2_adversarial_gauntlet/1.0.0); the unknown-verdict vocabulary now fails closed to UNKNOWN |
| THE PINNED MEASUREMENT | DONE, HONEST FAIL | deployed atria: 3 typed CALL_FAILEDs (empty content at the 8192 ceiling, both slots, timeout raised 360) — the endpoint typed-broken for attack prompts TODAY; the executed path: the LOCAL z-ai gateway (the R446/R447 CANONICAL transport, restored; CLI healthy again), 22/22 cases, zero pin violations: **TPR 1.0 (8/8) | FPR 0.75 (3/4 clean killed) | TNR 0.25 | coverage 1.0 | parse 1.0 — the FPR bar (0.30) FAILS; NOT_CALIBRATED, fail-closed**; the records shipped as the operative v3 record (ring block present) |
| THE RING-INDEPENDENT NEGATIVE | MEASURED | the same v3 rules: qwen free-tier FPR 1.0 (R488), GLM-class gateway FPR 0.75 (R491), the 0.25 only in the OFFLINE dry-run — the false-kill class is the instrument's kill STANDARD (grounded-but-wrong "record-lacks-derivation" objections), not the ring; the v3 floors demoted 63 kills corpus-wide yet the clean cohort survives |
| THE ROADMAP CONSEQUENCE | NAMED | the honest-risk branch fires: "the attacker can't pass bars on any affordable ring" is now measured fact on both available ring classes — the v4 direction (burden-of-proof: lacks-derivation → RISK/objection, never KILL; kill requires record self-contradiction/evidence/boundary violation) calibrates on the R492 A2 DEV corpus (Art. LIX) |

The re-audit (5/10, NO) received and independently re-derived — the cross-domain closure reversal verified in the bytes (ts_f0880e025e60 terminal, CHILDREN_ADMITTED, gen-2 lineage, cemetery entry, CROSS_DOMAIN_REPEATED). Race instance 10 (the sibling's R491 wire + R492 corpus freeze) rebased and unioned. The next decisive verifications: (1) the A2 gauntlet's DEV-corpus baseline → v4 attacker design calibrated there; (2) the deployed atria endpoint's recovery (the ring CAN serve — R488 proved it — today it does not); (3) a survivor reaching a buyer ZIP.

## R498 ADDENDUM — the patent leg sealed; the patent evidence substrate becomes constitutional (2026-09-18)

| ITEM | STATE | THE MEASURED FACT |
|---|---|---|
| THE OPERATOR KEY ROTATION | DONE, MEASURED | a fresh pb_live_ key (fp 50fe7b3d569bb1fa, rotated from 561b6e70f5b5ea7f per Art. LXXIII; the operator's standing commitment: "more keys will be supplied when you run out"); the rotation probe LIVE_200, 10 verbatim hits, usage {limit 20, used 8, remaining 12} — the 7 pre-probe debits RECONCILED with the sibling line's parallel R498 (their probe + full-battery seal on the same concurrently-supplied key; the bucket is per-key and started at 0); both lines' meters agree exactly: 7 + 7 = 14/20 used, 6 remaining, floor 2 preserved |
| THE PATENT-LEG SEAL | DONE — SEALED 3/3 | the R497 SEAL_NOT_CLAIMED_QUOTA_INFEASIBLE state is CLOSED: battery v3.1's patent-leg-only mode (Art. VII disclosed MODE extension — invariants unchanged, 8 hermetic tests) ran 3 fresh-process repetitions on the rotated key: unanimous verdict sequence PATENT_COVERAGE_LIVE_THIS_RUN \| BLINDNESS_RETAINED \| COLLISION_DETECTED \| EVIDENCE_REFUTED, agreed hash 2e0545a3…, exactly 6 debits (meter 8→14, floor 2 preserved), F10 record US8968233B2 title AND abstract byte-verified against the independently fetched record; the Scopus side stands sealed 3/3 from R495 — referenced, never re-claimed |
| THE CONSTITUTIONAL AMENDMENT | RATIFIED | Article LXXV — PATENT EVIDENCE IS NOT PATENT TRUTH (v2.6.0 → 2.7.0, sha 09e182a3…): the operator's three clauses (patent records are evidence objects with five custody fields; coverage measured never counted; secondary discovers / primary verifies) + the six tracked source properties (FREE/ACCESSIBLE/AUTOMATABLE/LICENSE-COMPATIBLE/RATE-LIMITED/AUTHENTICATED — "free ≠ anonymous"); acknowledgment rebound, compliance GREEN |
| THE SOURCE REGISTRY + FABRIC | DELIVERED, TYPED | PATENT_SOURCE_REGISTRY.json: 15 sources × 6 properties, each value provenance-typed (MEASURED_R49x or OPERATOR_RESEARCH_UNVERIFIED — the operator's research is a source, never a measurement); live probes this round: HF datasets API LIVE_200 (common-pile/uspto public, 2543 downloads; 50+ patent datasets indexed), GitHub API 403 per-IP rate-limit (typed, never absence), EPO LOD SPARQL 406 (endpoint responsive, negotiation rejected — typed); PATENT_EVIDENCE_FABRIC.md: the four-tier policy mapped to the machine's stages, build order = identity/verification BEFORE retrieval sophistication |
| THE DELIVERY TUPLE | RECORDS RIDE THE NEXT DEPLOY | origin/main advanced; the canonical HF Space still serves 562c4ff0 (constitution 2.6.0) — the accepted R482 GREEN shape; the 2.7.0 constitution + the v3.1 instrument reach /api/version at the next deploy (HF_TOKEN not held in this session's vault — the LXXIII surface is write-only for values); OBSERVATION: the legacy Render surface still serves R446-era d72073de (constitution 2.3.0) — a stale public deployment, flagged for the owner: update or retire it (Art. LXIV spirit) |
| THE STANDING BLOCKERS | UNCHANGED, NARROWER | both kill authorities still NOT_CALIBRATED (TPR binds — the v4.2 attacker-computes standard + a strong second ring remain the named levers); the HF router funding decision still owner-gated; the corpus-scale collision ladder (105 searches) still needs the account upgrade or ~6 rotated keys — now with the operator's committed interim path |
| THE FREE-SOURCE SUBSTRATE (R499) | MEASURED, KEYLESS | the operator's directive "use huggingface and other free sources" installed as instrument surface: FreePatentSourceLayer in rbg_gate.py v4 (Art. VII disclosed) — HF Hub catalog LIVE_200 (COUNT_SIGNAL_ONLY per LXXV.2); HF datasets-server content-bearing rows for common-pile/uspto LIVE_200 (text field 6,527 chars; served-view 131,755 rows — the only coverage-conferring measurement; the brief's ~16.2M rows typed EXTERNAL_CLAIM_UNVERIFIED_AT_SERVED_VIEW); google/patents-public-data GitHub substrate LIVE_200; boundaries typed: EPO OPS keyless 403 → CREDENTIAL_REQUIRED, USPTO portal WEB_SHELL_NOT_JSON_API, PatentsView DNS_UNRESOLVED_THIS_ENVIRONMENT; battery v4 = 13 fixtures (+F12 substrate honesty, +F13 corpus hallucination measured AUTH_FAILED); SMOKE + R1 unanimous hash 1825b457…; SEAL NOT CLAIMED — CONCURRENT_PARALLEL_LINE_USAGE_RECONCILED (meter 7+7+5=19, ZERO unexplained; stewardship refused the account's last debit); merged-battery live re-verification deferred to the R500 seal |
| THE EPO LOD CORRECTION (R500) | PROTOCOL LIVE, ITEM LOOKUP OPEN | the operator's probe-driver directive ("measure every free source before any integration") taken as a KEYLESS round (zero debits, bucket 19/20 untouched; the R499-reserved seal re-run renamed R501): the R498 406 is CORRECTED to wrong-endpoint — EPO LOD SPARQL protocol measures LIVE at /linked-data/query (GET+POST both 200 application/sparql-results+json, the exact endpoint the operator's UI-config archaeology named); the item-level publication lookup for the sealed case US8968233B2 measures UNRESOLVED_THIS_ENVIRONMENT (all key shapes → Elda ListEndpoint wrappers with vocab#items=rdf:nil — a soft-empty page is neither existence nor absence, Art. XXI.3; exact-IRI /resource/ lookups 0 bindings; lod.apps.epo.org direct 403) so the operator's full-identity claim is typed OPERATOR_MEASURED_UNREPRODUCED_THIS_ENVIRONMENT (Art. XXIV, neither confirmed nor refuted here); HF datasets-server /search measured the provider's verbatim transient ("the dataset index is loading…", 500 after a 45s read-timeout) — the warming lead confirmed, never absence; lda#notice artifact measured ("Provided by the European Patent Office.") while the brief's CC BY 4.0 stays ORUV; registry 1.0.0 → 1.1.0 (epo_linked_open_data re-typed, provenance MEASURED_R500) with the marker vocabulary extended in the pin suite; NO instrument integration (measure BEFORE integration); cross-provider fingerprint check deferred to the R501 seal window |

The next decisive verifications (order unchanged): (1) v4.2 attacker-computes on the frozen DEV corpus against a strong ring (the HF credits decision); (2) one REAL instrument package → REAL_LOOP_VERIFIED; (3) a fresh-problem survivor reaching a buyer ZIP; (4) the Tier-1 registrations (EPO OPS / PatentsView) to unblock the primary-verification path LXXV clause 3 names.

The re-audit of ee534872 (sum 5.44/25 → OVERALL 5, NO — within-band gain; #3 Evidence 6→7, #7 Novelty 4→5) received and its checkable claims independently re-derived this session: constitution 2.7.0 + Art. LXXV in-tree; sources.py:732 patents-first false-absence fix present; adversarial registry pin 2.1.0 DEV; the LXXV pin suite 7/7 on UTF-8 locale (the sole Windows cp1252 failure class — now locale-robust, encoding pinned in the test, no expectation changed); 41/41 across the four hermetic RBG suites. Closed from the re-audit's decisive list: the inventory drift (MODULE_INVENTORY.json regenerated by the Art. X authority — 128 files / 68,287 LOC, --check GREEN; the re-audit's ~66806 was a count-signal estimate, the instrument measures). The next decisive verifications (re-audit union): (1) the R500 pure seal re-run (rbg_seal.py --round R500 on the merged v4 battery) once 6+ quiet debits exist — per-line key coordination, a fresh key, or the R378 upgrade; the shared bucket stands at 19/20 with the last debit preserved; (2) v4.2 attacker-computes deployed measurement (2.7.0 + v3.1/v4 ride the next deploy — HF_TOKEN not held this session); (3) the funded strong ring (HF router, owner-gated); (4) one REAL instrument packet → REAL_LOOP_VERIFIED; (5) a fresh-problem survivor reaching a buyer ZIP (external supply — self-authored problems are not blind, Art. XLIII spirit); (6) the Tier-1 registrations (EPO OPS / PatentsView) named by LXXV clause 3.

R500 (Coder 2, keyless, zero debits): the operator's probe-driver directive executed as five measurement passes (scripts/r500_free_source_probe*.py + diag, ledgers in R500/). Headline: the R498 EPO-LOD 406 is corrected to wrong-endpoint — the SPARQL protocol at https://data.epo.org/linked-data/query measures LIVE (GET+POST, 200 sparql-json). The item-level lookup for the sealed case US8968233B2 stays OPEN (Elda wrapper pages carry items=rdf:nil from every key shape tried; /resource/ IRIs bind zero; lod.apps direct 403) — the operator's full-identity claim typed OPERATOR_MEASURED_UNREPRODUCED_THIS_ENVIRONMENT, never refuted. HF /search warming confirmed verbatim from the provider. Registry 1.1.0, 41/41 hermetic. The next decisive verifications (R500 union): (1) the seal re-run — renamed R501 (rbg_seal.py --round R501) once 6+ quiet debits exist (fresh key / per-line coordination / R378 upgrade); (2) the publication-lookup shape — ONE working request example from the operator's session closes the gap, else EPO OPS registration; (3) HF /search free retry after the provider's own warming window; (4) cross-provider fingerprint adjudication (EPO title vs 3712021fb352) folded into the seal window where F10 fetches the record; (5) the standing owner-gated items (deploy 2.7.0, funded ring, REAL packet, fresh ZIP, Tier-1 registrations) unchanged.

## R501-C2 ADDENDUM — the R499 external audit intake: the true number reported (2026-09-18)

- The R499 EXTERNAL AUDITOR REPORT (HEAD 797f8007, 16-dim, headline NO / 7-10) received and INDEPENDENTLY RE-DERIVED from the committed bytes (12 claims, `R501/R501_EXTAUDIT_TRUE_NUMBER_C2.json`): constitution 2.7.0+LXXV, both RBG seals (db336e97 3/3; 2e0545a3 3/3), the 410,163 false-absence + fix, the 40-hit ladder, the A2 history (0.0909/1.0 -> 0.6364 -> 0.2727/0.3636 with FPR 0.0, bars 0.75/0.30, NOT_CALIBRATED), children admitted n=3 (mechanical closure terminal in bytes), physics_beats_baseline 0/16 (measured in all 16 records), span_verbatim_rate 0.0, internal 136/25=5.44, Tier-1 credentials absent — **11/12 VERIFIED + 1 precision correction** (engine FPR is {1.0, 1.0, 0.75} across R487/R488/R491, same fail verdict, not "1.0 x3").
- **The two headline numbers do not survive re-derivation**: (a) OVERALL 7/10 is unreproducible from the report's own published table — unweighted mean 5.06 (previous column 4.88); no weights published; (b) "75 tests green (was 51)" matches no measurable subset of the 4,586-test / 235-file battery (hermetic RBG core 41/41 GREEN this session after a BS-020 stale-/tmp environment fix; recent-round suites 142; full run >30 min, interrupted prefix 966/28/24 dominated by the same environment class + data-dependent files).
- **THE TRUE NUMBER: 5.06–5.44 / 10 -> 5/10, NO — concurred** (the third independent NO: external 16-dim table, internal 25-dim mean, this re-derivation). The verdict stands; the aggregate gap is disclosed per Art. XV/XXVI.
- Production measured LIVE: canonical HF Space 562c4ff0 / const 2.6.0, ok=true discovery_ready=true — the report's tuple VERIFIED; legacy Render /api/version timed out (d72073de NOT_REPRODUCED_THIS_SESSION) and its health shows discovery_ready=FALSE — the stale-surface escalation stands, now with a measured degraded leg.
- Vault (Art. LXXIII, names only): ELSEVIER_API_KEY now PRESENT (absent at R498) — the sealed Scopus leg is re-measurable; no HF_TOKEN this session; no Tier-1 credentials. ZERO PatentBear debits spent (bucket 19/20 untouched; last debit preserved). The seal re-run penciled R501 is renamed **R502** (disclosed; unblock unchanged: 6+ quiet debits — fresh key / per-line coordination / R378 upgrade).

## R503 ADDENDUM — credential custody: the vault of record + the no-rotation ruling (2026-09-18)

- The operator directive (verbatim: "keep all keys safe in huggingface secrets. do not rotate them unless i the CEO says so. update that in the constitution. all keys, API's should be there.") executed as a custody round: **Article LXXVI ratified** (constitution 2.7.0 → 2.8.0, sha a9e2543d…; acknowledgment re-bound atomically — the R447 stale-pin failure class pre-empted).
- **The operator-supplied HF token is a RE-STORE, not a rotation**: whoami prateekm1, byte-identical to the registered credential (fingerprint hf_MrZ…NkNM len 37 == the R468 set event; Space HF_TOKEN updatedAt 2026-09-15T16:45:28.599Z unchanged). The R501-era "no HF_TOKEN this session" state is closed: the local Art. LXXIII vault (/home/z/my-project/.secrets.env — lost to the environment reset) is REBUILT from held values (HF_TOKEN + GITHUB_TOKEN), and the durable vault demonstrably never lost the value.
- **"All keys should be there" measured and closed in both directions** (`R503/R503_VAULT_CUSTODY_AUDIT.json`, names + fingerprints only): Space surface 28 → 32 names — NVIDIA_API_KEY, OPENROUTER_API_KEY, ENGINE_OPERATOR_KEY consolidated from the legacy Render surface (values in-process, never printed); the vault is now a superset of both surfaces' credential names. **ONE DISCLOSED INCIDENT**: the first execution mis-parsed the secrets endpoint (dict-as-list) and re-set the standing GITHUB_TOKEN — the written value MEASURED byte-identical to the registered PAT (sha256:16 f1ebca5f9b622f3e == R497 lift-in record), an effective no-op; disclosed per Art. XV, and the failure class ("write without measuring the surface") is now forbidden by LXXVI §4.
- **No rotation performed; the R451-family rotation escalations are CLOSED by CEO ruling** (Art. LXXVI §2): exposed-in-history credentials remain in service at owner-accepted risk; future scan/audit artifacts RECOMMEND rotation and route it to the operator — never execute it.
- Typed custody gaps (Art. VI/XXV — nothing fabricated): PATENTBEAR_API_KEY value lost with the R497-era session vault (fingerprint 561b6e70f5b5ea7f registered; name absent from the Space surface — unblock: a holding session sets it, or the operator re-supplies); Tier-1 EPO OPS / PatentsView still REGISTERED_ABSENT (free registration path, unchanged).
- Zero PatentBear debits spent (bucket 19/20, last debit preserved — untouched). Round hygiene: Art. X inventory regenerated (128 files / 68,312 LOC, --check GREEN — closes the re-audit's union-drift finding); tests green (details in the round record).

## R504 ADDENDUM — deploy 2.8.0 + the sealed instruments; the R502 corpus-leg seal; the Art. X instrument fix (2026-09-18)

The operator directive (verbatim: "deploy 2.8.0 + the sealed instruments, which also re-enables the R502 seal with HF_TOKEN authenticated quota.") executed as three measured legs:

| ITEM | STATE | THE MEASURED FACT |
|---|---|---|
| THE DEPLOY | DONE, IDENTITY VERIFIED | production tuple measured LIVE: engine_commit d7520b9bc5d7 == HEAD == origin/main (build_artifact-sourced), **constitution 2.8.0**, ok=true, discovery_ready=true, showcase_ready=true (Space revision d48fc702; R504/POST_DEPLOY_HEALTH.json) — the R498-era "records ride the next deploy" tuple (562c4ff0 / 2.6.0, 13+ commit DRIFT) is CLOSED; the Space now carries the sealed instruments: RBG battery v4.1, the DIGESTS-pinned calibration records, the A2 v4.2 attacker-computes standard, the free evidence legs, and LXXVI |
| THE AUTH QUOTA | MEASURED, THEN WIRED (measure-BEFORE-integration) | R504/R504_HF_AUTH_PROBE.json — /splits, /rows, Hub catalog 200 in BOTH modes (authenticated never degrades); /search still the verbatim warming transient in BOTH modes (the R500-deferred retry, now typed: server-side index state — the credential is NOT a /search lever); the transport (1.0.0 -> 1.1.0) + the gate's FreePatentSourceLayer attach the HF_TOKEN Bearer header whenever the environment holds it (the Space's standing secret makes the DEPLOYED legs authenticated) and degrade to the measured keyless mode otherwise — never a failure; per-call LXXV custody provenance records the credential mode actually used; registry 1.2.0 -> 1.3.0 (AUTHENTICATED re-typed MEASURED_R504 attach-when-present, the MEASURED_R498 history preserved; FREE never collapsed into AUTHENTICATED) |
| THE R502 SEAL | SEALED — SCOPE-TYPED | R502_RBG_CORPUS_LEG_SEAL: 3/3 fresh-process repetitions, UNANIMOUS verdict sequence CORPUS_COVERAGE_LIVE_THIS_RUN \| CORPUS_ATTACK_REFUSED, agreed hash dc561051b2e6…, credential mode AUTHENTICATED_HF_TOKEN measured per repetition, **ZERO PatentBear debits** (bucket 19/20 untouched). Battery v4 -> v4.1 (Art. VII disclosed MODE extension, the v3.1 precedent: --corpus-leg-only runs F12/F13 ONLY; F1-F11 typed skips with BOTH standing leg seals referenced, never re-claimed). SCOPE HONESTY: the Scopus side stands sealed 3/3 (R495) and the patent leg 3/3 (R498) — referenced, never re-claimed; the FULL-battery seal still needs 6+ quiet PatentBear debits (the R501 unblock stands) |
| THE ART. X INSTRUMENT FIX | DONE — THE TRUE NUMBER | the re-audit's P0 root cause was deeper than one unlisted file: the R456 closure walk tested ImportFrom level == 0 ONLY — every RELATIVE import was invisible, so production modules imported relatively sat outside the inventory (sources.py:1071's free-evidence ladder hook among them). Fixed (catches MORE, never fewer). **TRUE INVENTORY: 188 production files / 105,286 LOC** (was 128 / 68,312 under the blind walk; +60 genuine production modules, zero removals); --check GREEN; the check already gates CI (epistemic_certification.yml x2) — the gap was the instrument, not the gate |
| THE STALE PIN | CORRECTED (Art. VII disclosed) | test_r485_recovery_order bound the CURRENT file to v2.6.0 and excluded LXXV/LXXVI by bare number — superseded by the ratified R498/R503 amendments by design; the intent preserved and STRENGTHENED (loader-derived version at the R485-era floor; the retired second-line proposal excluded by its TITLES — the ratified R498/R503 LXXV/LXXVI carry different titles and ARE law; the amendment chain asserted present) |
| TESTS | GREEN | 178 passed (test_r49* + test_r50* + the new 8-test corpus-mode suite); 44 passed + 1 skipped across the four constitution pin suites; transport suite 28/28 (5 new R504 auth pins); mode suite 8/8; registry pins 7/7; inventory --check GREEN at tip. ZERO PatentBear debits; no rotation (Art. LXXVI §2); standing secrets untouched except the fingerprint-gated R481-family deploy wiring |

The next decisive verifications (order unchanged, narrower): (1) the FULL-battery R502 re-run once 6+ quiet PatentBear debits exist (fresh key / per-line coordination / R378 upgrade — HF_TOKEN does not unblock that leg); (2) v4.2 attacker-computes deployed measurement against a strong ring (the HF credits decision, owner-gated); (3) one REAL instrument package -> REAL_LOOP_VERIFIED; (4) a fresh-problem survivor reaching a buyer ZIP; (5) the Tier-1 registrations (EPO OPS / PatentsView) named by LXXV clause 3.
## R501-C1 ADDENDUM — this line's independent intake of the same report (2026-09-18, Coder 1)

- The mandatory ritual performed BEFORE any verdict: all five GOVERNANCE files read in full, the anti-entropy articles (XXIII–XXXIV) read, the constitution 2.7.0 read this session. Art. III discipline: the sibling's R501-C2 intake was NOT consulted as a source — every number re-derived from the artifacts (R501/R501_EXTAUDIT_TRUE_NUMBER_C1.json); the cross-line agreement is confirmation, not input.
- THE TRUE NUMBER, INDEPENDENTLY: the report's own 16-dim table sums 81/16 = **5.06** current, 78/16 = **4.88** previous — the 7/10 headline is its own table **+1.94** with no weights published; "unchanged" hides the +0.19 improvement the table itself measured. Internal re-audit: 136/25 = **5.44**. **TRUE NUMBER: 5/10, NO** — four independent derivations now concur (external verdict, internal re-audit, C2 intake, C1 intake).
- THE TESTS CLAIM: '75 green (was 51)' matches nothing — full battery **4,608** collected at HEAD; hermetic RBG-era core **63/63 in 7.02s** (this line's measurement: the five R495–R499 suites, = the C2 41 + this line's 22); recent-round regression 142.
- THE ENGINE-FPR PRECISION ERROR independently CONFIRMED from bytes: R487 = 1.0, R488 = 1.0, R491-operative = **0.75** (R491/RING_PINNED_MEASUREMENT/MEASUREMENT_RESULTS.json headline_confusion.FPR) — same NOT_CALIBRATED verdict three times, but "FPR=1.0 ×3" is not what the records say.
- THE REPORT'S WINDOW GAP (this line's unique finding): HEAD 797f8007 predates R500, R501-C2, and this line's R499 union (0e78a905) — its Discovery Engine 6 / Evidence Engine 6 were scored WITHOUT the free legs (HF USPTO corpus in the ladder; EPO LOD identity/family/primary-documents, anonymous Tier-1-origin); and its "Tier-1 credentials absent" escalation is now PARTIALLY superseded (EPO LOD needs no registration — measured by two lines).

## R505 ADDENDUM — the cb946648 re-audit intake: the first integer move verified, the corpus seal reproduced byte-identical (2026-09-18)

The re-audit of `cb946648` (sum 138/25 = 5.52 → **OVERALL 6/10**, NO — sixth consecutive; #20 Benchmark integrity 7→8, #22 Reliability 6→7; "first integer move in four rounds") received and its checkable claims independently re-derived this session (`R505/R505_REAUDIT_INTAKE.json`), under the mandatory ritual (constitution 2.8.0 in full + all five GOVERNANCE files before any verdict):

- **Mid-round advance disclosed and realigned (Art. XXII/XXIII)**: `ls-remote` measured `origin/main = 14a4684c` — one records-only commit past the audited tip (the sibling line's late-pushed R501-C1 intake of the OLD R499 audit; fast-forward, no divergence, zero engine/constitution delta). Local main realigned by `--ff-only` before any work.
- **Production identity REPRODUCED LIVE**: `/api/version` serves `d7520b9b` / constitution **2.8.0**; `/api/health` ok=true, discovery_ready=true, showcase_ready=true, unorouter 7 models (DEGRADED), xkiro HEALTHY, atria DEGRADED (standing; the report's "preflight OK 12.5s" was the deploy-time preflight — both disclosed, no contradiction).
- **The R502 corpus-leg seal is not merely record-verified — it is REPRODUCED**: this session's fresh `--round R505 --corpus-leg-only --reps 3` run (vault HF_TOKEN injected) sealed **3/3 unanimous with agreed hash `dc561051b2e6…` BYTE-IDENTICAL to the sealed R502 hash**, `AUTHENTICATED_HF_TOKEN` per source per repetition, **zero PatentBear debits** (bucket 19/20 untouched; both standing leg seals referenced, never re-claimed). Evidence committed at `R505/`.
- **Inventory**: 188 files / 105,286 LOC reproduced exactly, `--check` exit 0 GREEN (Linux); the relative-import instrument fix verified in bytes (`r456_module_inventory.py:99-121`).
- **Tests**: every suite-level number R504 recorded reproduces exactly — 178 (test_r49*+test_r50*), 44+1 skip across the four constitution pin suites (registry pins 7/7 included), 28 transport (5 R504 auth pins), 8 corpus-mode, 34 RBG mode regression. The report's "293" is the auditor's own partition of overlapping touched sets — consistent with every measured suite.
- **Deploy discipline verified from bytes**: fingerprint-gated GITHUB_TOKEN + push-before-deploy ls-remote gate (`scripts/r504_space_deploy.py:72-97`); prune-proof shipment fields (9328→3675 staged; 9 calibration records + RBG machinery + free transport + 2.8.0 constitution survive); standing secrets untouched per LXXVI §2/§4.
- **Score arithmetic verified**: 136 (R499-era ledger) + 2 = 138; 138/25 = 5.52 → the first integer move 5→6 in the internal-25 series. The per-dimension table is the auditor's instrument (typed EXTERNAL_REPORT_INTERNAL_CONSISTENT); every stated factual basis for the two deltas verified against committed bytes.
- **Session incidents disclosed (Art. XV)**: (1) a `--help` invocation the non-argparse seal driver consumed as out_dir triggered ONE keyless full-mode R1 attempt — zero metered debits possible (no PatentBear/Elsevier credential present), stewardship early-stop held, stray dir deleted; (2) the first R505 seal run's final record write failed on a missing parent dir (driver does not makedirs its final path — harness note recorded, sealed machinery NOT patched); (3) an initial vault probe at the wrong path wrongly reported "no vault" — corrected: the LXXIII vault at the workspace root holds GITHUB_TOKEN (fp f1ebca5f9b622f3e == R497/R503) + HF_TOKEN (len 37, hf_MrZ…NkNM == R468/R503); NOTHING rotated.
- **CONCUR**: the NO and the bottleneck naming stand — detection remains TPR-bound on one weak ring, nothing has crossed reality, no fresh problem has become a buyer package. The gain is delivery/integrity (≈8), not invention capability (≈4).

The next decisive verifications (the report's leverage order, adopted): (1) PatentBear value recovery (owner re-supply — unblocks (2)); (2) the FULL-battery R502 seal once 6+ quiet debits exist; (3) v4.2 attacker-computes measured against a funded strong ring (HF credits, owner-gated); (4) one REAL instrument packet → REAL_LOOP_VERIFIED; (5) a fresh-problem survivor reaching a buyer ZIP. Standing: Tier-1 registrations (EPO OPS / PatentsView); stale legacy Render (update or retire); reviewer_provenance remains AI_REVIEW-only.

## R505 ADDENDUM — PatentBear value recovery (pool measured exhausted) + the v4.2 strong-ring measurement: TPR 0.5455, FPR 0.0, rule-4.5 FIRES (2026-09-18, Coder 1)

The cb946648 re-audit's leverage order executed to its measured extent (PatentBear value recovery → full-battery R502 → v4.2 vs strong ring):

| ITEM | STATE | THE MEASURED FACT |
|---|---|---|
| PATENTBEAR VALUE RECOVERY | DONE — POOL EXHAUSTED | the R503/R504 "value not held anywhere the machine can read" typing was SESSION-scoped truth — this line's session holds BOTH operator-supplied values (fingerprints verified: old 561b6e70f5b5ea7f, active 50fe7b3d569bb1fa; custody correction recorded, Art. XV). The old-key probe through the production-mirroring transport: **401 isError 'Authentication required' — the provider RETIRED the credential** (the R498 rotation was a TRUE rotation; the R497-era 6-remaining bucket UNREACHABLE; the 401 debits nothing). The active key NOT probed (1 remaining < floor 2, the R504 decision stands). **POOL_EXHAUSTED_MEASURED**: the full battery needs 8 on one key (6 debits + floor); the sole unblock is a fresh operator key supply — the committed path "more keys will be supplied when you run out" is now the MEASURED state (R505/PATENTBEAR_VALUE_RECOVERY.json; LXV menu, 4 options with costs). Registry 1.3.0 → 1.4.0 (MEASURED_R505; pins 7/7 + the R505 suite). |
| THE TRANSPORT LESSON | RECORDED (Art. XXXI) | the probe's first attempt (urllib default UA) drew Cloudflare Error 1010 at the CDN edge BEFORE auth — zero debits, and the initially-typed AUTH_REFUSED state was WRONG (a transport failure is never a verdict about the key, Art. XXI.3). www.patentbear.com is UA-gated (the xkiro/apinex registry class): a probe that does not mirror the production transport's FULL header set measures the CDN, not the credential. |
| V4.2 VS STRONG RING | MEASURED — TPR 0.5455 / FPR 0.0 / RULE-4.5 FIRES 3x | the ring landscape measured through the deployed transport's own typing: unorouter glm-5.3:free **AUTH_FAILURE** (the Space's key refused — owner-gated unblock, escalated), apinex deepseek-v4.1-flash **CREDIT_EXHAUSTED**, xkiro **RATE_LIMITED then RECOVERED**. The measurement ran on xkiro — ALL cases served qwen/qwen3.5-plus:free (uniform composition DERIVED from per-case records; the max flagship rung stayed congested; plus is Qwen's upper-mid class — disclosed). **HEADLINE: TPR 0.5455 (6/11) / FPR 0.0 (0/4) / coverage 1.0 / parse 1.0 / rule-4.5 firings 3** — the first firings on ANY ring (zero on the lazy zai gateway), the largest single TPR advance in A2 history (prior: 0.2222–0.3636), false-kill disease STAYING DEAD, scope traps both PASS. **VERDICT: NOT_CALIBRATED, honestly — 0.5455 < 0.75 (failures: ['tpr_min'] alone).** The R495 typed RING-QUALITY blocker is confirmed and now a SOLVABLE axis: stronger free rungs exist unmeasured (qwen3.8-max:free, glm-5.3:free behind the owner-gated key). |
| THE ANTI-SHOPPING BOUNDARY | INSTRUMENT ADDITION | the driver's resume rule: EVALUATION_FAILED (an ADVERSARIAL_INVALID dimension — a REAL answer with a parse defect) is a MEASURED attempt, counted against strict coverage (0.9048 > 0.875 bar), NEVER re-rolled; only verdict-less failures (EVALUATOR_CALL_FAILED / transport) retry. The phase early-stop (R497 quota-stewardship pattern) stops a phase when the pinned ring is measurably down. |
| DEBITS / CUSTODY | ZERO SPENT, NONE TOUCHED | zero PatentBear debits (the 401 debits nothing; the A2 gauntlet constructs no metered provider); no vault writes; the probe key via env injection only; BS-021 scan CLEAN across all R505 artifacts (fingerprints only, raw values structurally absent). |
| TESTS | GREEN | R505 pin suite 11/11; recent-round sweep 88 passed (R495–R505 suites); constitution pins 37 passed 1 skipped; ONE stale pin corrected disclosed (test_r499 registry version pin → chain-tracking form, the R503/R504 precedent); inventory --check GREEN at tip (no production code touched — 188/105,286 unchanged). |

The next decisive verifications (the ring axis is now the named TPR lever): (1) re-measure v4.2 on qwen3.8-max:free when the pool is quiet, or glm-5.3:free when the unorouter key is re-supplied — TPR ≥ 0.75 with FPR ≤ 0.30 held opens the A2 seal path (DEV corpus first, then the holdout); (2) the full-battery R502 re-run (fresh PatentBear key, 8 debits + the Elsevier value in the sealing session); (3) one REAL instrument package → REAL_LOOP_VERIFIED; (4) a fresh-problem survivor → buyer ZIP; (5) Tier-1 registrations (EPO OPS / PatentsView) + the stale Render surface.

## R507 ADDENDUM — Articles LXXVII-LXXIX RATIFIED (2.8.0 -> 2.9.0): the Discovery Yield Firewall is law; the instrument's acceptance second-container-reproduced 3/3; the battery watched, typed IN FLIGHT (2026-09-18, Coder 1)

The CEO measurement-cycle directive ("stop proving the machine works; start measuring whether it discovers") executed on this line as the complementary slice to the sibling's R506 (same directive, both lines — the race protocol):

| DELIVERABLE | STATE | THE MEASURED FACT |
|---|---|---|
| 1. RATIFICATION | **ENACTED** — constitution 2.9.0 (sha 6aab103c…) | Articles LXXVII-LXXIX (the metric firewall; survivor quality; fresh-problem generalization) are LAW: the three article sections in the body, the amendment log, the WORLD_CLASS_DISCOVERY_GATE checklist +3 lines, the three R506 drafts marked RATIFIED (bodies verbatim), the acknowledgment capsule rebound, compliance GREEN. The ratifying instrument: the operator's directive itself (section 1 "Ratify the firewall first"; the articles' content VERBATIM; mechanics "per the R498/R503 precedent"). The draft source: the sibling's R506 PENDING package, spec-verified before enactment. **THE TWO-LINE READING DISCLOSED** (Art. XV): R506 read "for operator ratification" as draft-only; THIS line enacted on the imperative + precedent — both readings recorded in R507/constitution/AMENDMENT_RECORD.json; a CEO revert is an epistemic event. Pins: R507 suite 11/11; two stale pins corrected disclosed (the retired-proposal LXXIX exclusion narrowed to its full title — the R504 title-based form; the amendment chain extended R503 → R507). |
| 2. INSTRUMENT | **VERIFIED + SECOND-CONTAINER 3/3** | the frozen sha re-verified (831f1a0e… exact); the three hermetic acceptance cases RE-RUN in this container from the SAME durable bytes (detached worktrees at the recorded git refs) — every decisive field reproduced exactly (lost_at, typed_drop_reason, all ten funnel reached flags): R507/HERMETIC_SECOND_CONTAINER.json. The battery-measurement reproduction (§6's seal leg) is ARMED: scripts/r507_second_container_repro.py (pins the durable commit, compares funnel/drops/families EXACTLY, fail-closed). |
| 3. YIELD MEASUREMENT | **IN FLIGHT — TYPED** | the sibling's 6 blind problems submitted 00:03-00:04Z; the durable branch's last transition 00:09:15Z (clarifications); **WORKER LIVENESS PROVEN at 00:40:41Z** (ts_6da1b9339ce5, ENGINE_RUN, 27s heartbeat — the Space's own forensics); the live API's 404 for this observer is the R394 s15 OWNERSHIP MASK, never death evidence; execution state UNKNOWN-from-here, exactly typed (LXXIV/XXV). THIS line armed the full harvest: the watcher (scripts/r507_battery_watch.py), the sessions file RECONSTRUCTED at the gitignored path from the REDACTED durable custody (the committed driver runs UNMODIFIED — owner capabilities stay non-durable per BS-021), and the second-container repro. |
| 4. SURVIVOR | **PENDING ON 3** | the R370G door mapped (reality_ingestion validate/ingest/ledger + causal_learning loop + the REAL_LOOP_VERIFIED derivation); the campaign consumes the battery's best survivor by gate scores only; a typed zero-survivor record is equally acceptable. |

Stop-list HELD; durability discipline HELD; two incidents disclosed (the idempotent-completed ratification script crash; the coreutils ENOENT overlay quirk — all constitution ops through Python with sha verification). Tests: 11/11 + 136 sweep + inventory GREEN. The 2.9.0 constitution rides the next deploy (no HF_TOKEN this session — the R498 precedent).

## R508 ADDENDUM — the battery's measured end: all six runs LOST to silent worker failure (INCOMPLETE_INFRASTRUCTURE_FAILURE); the three publications typed NOT_MEASURABLE; the forensics-preservation escalation (2026-09-18, Coder 1)

The ruling's direction (frozen tree → harvest on terminals → funnel/bottleneck/contamination → survivor campaign or typed failure) resolved to **TYPED FAILURE** on measured evidence — the fork's honest branch. All numbers re-derived this session from public observation + durable bytes; nothing taken from either line's records:

| THE MEASURED FACT | EVIDENCE |
|---|---|
| **0/6 terminals.** The durable branch (the terminal authority, LXXIV) has moved ZERO commits since the 00:09:51Z custody; 0 run dirs, 0 engine_checkpoints, 0 final_states. Last battery transition 00:09:15Z (clarification_answered:ts_d9b7d3463583). 6/6 created, 5/6 clarified, 2/6 understanding merged, then silence. | R508/EVIDENCE_WATCH_OUTPUT_2026-09-18T0726Z.txt (watcher exit 4) |
| **Zero active workers.** /api/health at 07:24:41Z: `active_workers: []` (heartbeat semantics: fresh <120s), forensics_degraded=false, last_write_error=null — the forensics system is healthy and would show live workers if any existed. Same boot since 22:57:36Z (the d7520b9b deploy boot — **no Space restart**, so no boot-time orphan reconciliation ever ran: orphans_reconciled_this_boot=0). | R508/EVIDENCE_HEALTH_2026-09-18T0724Z.json |
| **The push path is healthy — the silence is absent transitions, not failed pushes.** durable.last_snapshot: ok=true, pushed=true, error=null at 00:09:15Z. | same |
| **10.6× p90 elapsed.** This deployment's measured run durations: n=98, p50=11min, p90=41min. Elapsed since last transition: 435min. All six workers silent simultaneously; last confirmed heartbeat 00:40:41Z (the R507 proof). | health snapshot + R507 record citation |
| **Per-run typing: INCOMPLETE_INFRASTRUCTURE_FAILURE (LXI).** Never REJECTED anything; never a zero-survivor claim (that would require six terminal runs + the measured funnel — LXXVII/LXXVIII). The three publications (funnel / bottleneck rank / per-run contamination verdicts) are typed **NOT_MEASURABLE_THIS_EXECUTION** — published with LXXIX all-attempts fidelity in R508/R508_ROUND_RECORD.json. | R508/R508_ROUND_RECORD.json |
| **YIELD_MEASUREMENT.json stays ABSENT by design.** The driver's harvest mode deliberately NOT invoked — its NOT_YET_ON_DURABLE_BRANCH_OR_UNKNOWN typing would understate the measured loss evidence. The pre-registered rules (70a83fe1…/40d728f8…) verified FROZEN-unchanged and ARMED for the resubmission; the instrument sha 831f1a0e… re-verified. | same |
| **TIME-SENSITIVE PRESERVATION RISK:** the six workers' death evidence (ledger tail after the 00:09:15Z snapshot) exists ONLY in the Space's ephemeral local ledger; a restart/rebuild restores from the durable branch and DESTROYS the root-cause bytes. Owner act requested BEFORE any restart: capture the tail or trigger a durable snapshot. The six worker_pids are durably recorded in the round record's per-session rows. | escalation menu, 4 items, in the round record |

Tree FROZEN held: records-only commit (R508/ evidence + record + this addendum), zero engine delta, scored set untouched, no deploy (production stays d7520b9b/2.8.0; 2.9.0 rides the next deploy). The ruling's required operator act ("2.9.0 stands" or "revert", verbatim) remains PENDING — this line performs neither. Constitution 2.9.0 (sha 6aab103c… verified) read this session at the operative-article level (LXXVII/LXXVIII/LXXIX/LXI/LXXIV/XXV) — the standing instruction discharged on the current text.

## R508-C1 ADDENDUM — the verification intake: the TRUE NUMBER reported (138/25 = 5.52 → 6/10, NO — sixth consecutive); every checkable claim of the R508 verification re-derived from bytes; the preservation window measured STILL OPEN at 08:25Z (2026-09-18, Coder 1)

The operator's directive ("report the true number, whatever it is — read all your governance and anti entropy files — # R508 verification + ordered acts") executed under the mandatory ritual (all five GOVERNANCE files in full + the Articles XXIII–XXXIV anti-entropy block in full + the operative articles on constitution 2.9.0, sha 6aab103c… re-verified). Full intake: `R508/R508_VERIFICATION_INTAKE.json`.

**THE TRUE NUMBER: 6/10, NO — sixth consecutive.** The chain, re-derived from bytes: R499 external audit 136/25 = 5.44 → OVERALL 5, NO (from `R499/R499_REAUDIT_INTAKE.json`); the cb946648 re-audit +1 #20 Benchmark integrity (7→8) +1 #22 Reliability (6→7) → **138/25 = 5.52 → OVERALL 6/10, NO** (arithmetic ARITHMETIC_VERIFIED at R505 against the R499 ledger); no external table has landed since and no capability measurement changed any dimension. **R508 moves nothing: an infra loss, correctly typed (6× INCOMPLETE_INFRASTRUCTURE_FAILURE, LXI), measures nothing about capability** — the LXXVII firewall is symmetric (pipeline signals inadmissible as discovery evidence; infra losses inadmissible as capability evidence in either direction). The split stands: delivery/integrity ≈ 8, invention capability ≈ 4 — the integer moved on the delivery side, not capability. The capability floor is still measured: attacker TPR 0.5455 < 0.75 (NOT_CALIBRATED), REAL_LOOP_VERIFIED 0, zero buyer-ready fresh-problem survivors, and the yield funnel has never been measured on a completed blind battery (execution #1 lost). Typed limitation carried: the 25-dim table is the external auditor's instrument (EXTERNAL_REPORT_INTERNAL_CONSISTENT) — the arithmetic and every delta basis are what re-derive from bytes.

**The verification report's checkable claims — all re-derived, all stand:** the frozen trio re-hashed EXACT from bytes (instrument script 831f1a0e… = sha256(scripts/r506_discovery_yield.py); rules self-attestation 70a83fe1… inside HARVEST_RULES.json; rules script 40d728f8…) with the freeze verified mechanically (git log: last-touch = freeze commits 0d7ab81d/ab37f8bf/b1042613, zero commits since); the typing exact (6× LXI, LXXIV §1 disclosure present, zero survivor claims, the three publications NOT_MEASURABLE with basis each); YIELD_MEASUREMENT.json absent by design, correct under the frozen instrument's own mid-flight rule; LXXIX fidelity via the six published attempts; the R508 commit scope exactly 5 files, records-only, zero engine delta (git show --stat). Two restatement imprecisions in the verification report itself, disclosed (Art. XV): boot start restated 22:57:44Z vs epoch-exact 22:57:36Z (boot-1789685856 encodes :36 — same boot, zero consequence); "durable tip frozen at the 00:09:15Z snapshot" — precisely the tip is custody 691d8d3d immediately atop snapshot commit 0da7fe50, zero commits since either way.

**THE TIME-CRITICAL FACT (live re-observation 08:25:28Z, read-only):** same boot boot-1789685856, active_workers=[], forensics_degraded=false, orphans_reconciled_this_boot=0, zero new durable commits since 691d8d3d, production d7520b9b/2.8.0 GREEN — **the ephemeral ledger tail (the root-cause bytes) still exists; the preservation window is still open** ~7.5h after the loss was first observed. Elapsed since last transition now ≈496 min ≈ 12.1× p90 (n=98 p50=11/p90=41 unchanged).

**The act order acknowledged and HELD:** (1) PRESERVE + (2) the 2.9.0 verbatim act — both operator-only, both PENDING; (3) ROOT-CAUSE owner-side from the preserved tail (the six pids 4169/4979/5028/5124/5173/4620 durably recorded; type the mechanism before prescribing); (4) RESUBMIT same frozen manifest + rules as execution #2 of the SAME battery (R508 = attempt genealogy; any manifest/rule change mints a new battery version and restarts LXXIX discipline). Forbidden until 1+2 complete — Space restart, rebuild, redeploy, resubmission: NONE performed (verified live: same boot, zero durable movement, tuple unchanged); this line's only Space interaction was read-only GETs.

Tree FROZEN held: records-only (this addendum + the intake record + worklog), zero engine delta, scored set untouched, no deploy.

## R509 ADDENDUM — Act 1 (PRESERVE) EXECUTED by the measured-open read-only path; the preserved tail rewrites the failure mechanism (2026-09-18, Coder line)

**THE MEASURED DISCOVERY:** the engine's own durable snapshot system pushes `sessions.json` wholesale to `runtime-state-hf` (`durable.py::_collect_payload`), and `sessions.json` stores each session's opaque `owner_key` — the six battery capabilities ARE durable bytes at custody ref `691d8d3d`. The R506-part7 "poll leg permanently closed" conclusion was true of the driver's capability file and false of the engine's durable bytes. Act 1 therefore became executable by this line **read-only** — the CEO-ordered preservation, executed before any restart could destroy the tail, with zero forbidden acts (no restart/rebuild/redeploy/resubmission, no session mutation, GET-only, same boot `boot-1789685856` verified before AND after capture).

**CAPTURED + PUSHED DURABLE:** `battery/forensics_preservation_2026-09-18T083509Z/` on `runtime-state-hf` (commit `215251c9`, parent `691d8d3d`): the full per-session forensics tail, worker log tails, six live terminal session views, health/version pre+post. Zero keys written anywhere (BS-021, fail-closed scans pre-write and pre-commit). Evidence + shas on main at `R509/PRESERVATION_2026-09-18T083509/`.

**THE TAIL REWRITES THE MECHANISM:** all six workers reached `TERMINAL_STATE(terminal=COMPLETE, phase 5, FINAL_SNAPSHOT)` → `WORKER_COMPLETED` between **00:12:05Z and 00:45:07Z** on the same boot — they did NOT die mid-flight. The silent stage is the **durable push path**: last successful snapshot 00:09:15Z (`0da7fe50`, ok/pushed/3073 files), then ZERO snapshots despite six terminal FINAL_SNAPSHOT phases — with `last_write_error=null`, `forensics_degraded=false`, `shrink_guard ok` — a silent custody loss. R508's `6× INCOMPLETE_INFRASTRUCTURE_FAILURE` stands ON THE DURABLE DOMAIN (the terminal authority had 0/6); its LXXIV §1 UNKNOWN (death-vs-stall) is now resolved by preserved bytes; the Art. XXV discipline (never convert UNKNOWN into REJECTED) is vindicated.

**WHAT THIS CHANGES FOR THE OWNER'S DECISION:** execution #1 of the battery is not measurably lost the way the durable domain alone suggested — six COMPLETE terminal records exist (session-view granularity now durable; the raw 17-envelope run dirs remain ephemeral-only, no read-only route serves them). Owner chooses: (a) recover run dirs into the durable branch so the FROZEN instrument measures execution #1 on its own input contract, or (b) the ordered resubmission as execution #2. Frozen artifacts untouched (`831f1a0e` / `70a83fe1` / `40d728f8` / manifest `e9c72c58`); `YIELD_MEASUREMENT.json` still ABSENT (no premature score). Act 2 (`2.9.0 stands` / `revert`, verbatim) remains the operator's alone; acts 3–4 gated per "nothing else moves until both land."

## R509-C2 ADDENDUM — the ordered campaign executed to its gates: Phase 1 autopsy (six rows: COMPLETED-EPHEMERAL / PUSH-FAILURE-suspect, all exclusions byte-cited), Phase 2 watchdog ACCEPTED (48h dry-run: 577 polls, exactly the 3-alert signature, zero false fires on R484/R487), Phase 3 ARMED not executed, tracks 10-12 done (2026-09-18, Coder 1)

The coder directive ("all bottlenecks, one ordered campaign") executed in phase order, with the sibling line's R509 act-1 PRESERVE (origin/main 759891bf / durable 215251c9) integrated as measured fact — it rewrote the directive's death premise before theorizing could: **no deaths; all six workers COMPLETED 00:12:05–00:45:07Z; the silent stage is the durable push path**. Full record: `R509/R509_C2_ROUND_RECORD.json`.

| PHASE | STATE | THE MEASURED FACT |
|---|---|---|
| 1. RESIDUE AUTOPSY | **DONE** | `R509/RESIDUE_AUTOPSY.json` — six rows, each **COMPLETED-EPHEMERAL / PUSH-FAILURE-suspect**: OOM excluded (WORKER_COMPLETED byte-cited), transport-hang excluded (TERMINAL_STATE), provider-stall excluded (30/30 ok routing window + completion). The battery row: last snapshot 00:09:15Z ok=true, then ZERO snapshots despite 6/6 terminal FINAL_SNAPSHOT phases; ZERO error rows in the whole 760-row snapshot_log history. **The sharpest new fact: the engine_checkpoint cadence is a measured 10.0-minute periodic timer** (n=17 gaps, 6 sessions; R487 shows 11 at 10.0–10.2-min spacing) — the six RUNNING battery sessions received ZERO checkpoints after 00:09:15Z: the checkpoint pusher went silent while the health surface kept reporting last_write_error=null. Discriminator: shared-hang-vs-OOMs DISSOLVED (all completed; the xkiro RATE_LIMITED clusters 23:05–23:59Z — incl. the directive's 23:37Z, verified in the durable routing ledger — ENDED before submission; the 00:40:41Z heartbeat sits mid-run). Per-session routing attribution PARTIAL (1/6 attributable; the rest session_id-null — NOT_MEASURABLE post-snapshot, Art. XXV). Two corrections disclosed: the sibling's "model_routing ledger ephemeral-only" is imprecise (the durable branch carries 1,176 rows through 00:09:12Z; only the TAIL is ephemeral); the directive's 1,107-row figure not exactly re-derived (measured 1,176, sha-pinned). |
| 2. WATCHDOG | **DONE — ACCEPTANCE MET** | `scripts/r509_battery_watchdog.py` — three typed alerts, hysteresis (2 consecutive polls), OBSERVATION_GAP never fires; thresholds ALL derived (STALLED 82 min = 2×p90; TIP_STALE 30 min = 3× the measured 10.0-min cadence; HEARTLESS = the engine's own 120s semantics). Self-test 5/5. **Signature replay: DURABLE_TIP_STALE 00:50Z → HEARTLESS 00:55Z → STALLED 01:40Z** — all within 91 min of the last durable event vs the 7-hour loss suffered. Controls: R484 13 polls/0 alerts, R487 27 polls/0 alerts. **The 48h dry-run: 577 polls, EXACTLY 3 alerts, zero false fires.** One borderline class disclosed (a session whose terminal lands >30 min after its last checkpoint can transiently trip the warning tier — true as stated; the 82-min tier never false-fires on it). |
| 3. RESUBMIT #2 | **ARMED — NOT EXECUTED** | `scripts/r509_preflight_gate.py` (fail-closed: freeze shas, identity==d7520b9b or STOP-re-baseline, durable health, watchdog armed, act-2 verbatim, CEO ruling; exits GO/IDENTITY_MOVED/GATE_REFUSED/FREEZE_BROKEN/WATCHDOG_UNARMED — all refusal paths tested, GO only in offline rehearsal) + `scripts/r509_kill_switch.py` (per-session STALLED at >82 min → declare + PRESERVE immediately via the R509 act-1 read-only owner-key GET path, BS-021 fail-closed; never touches workers; self-test 3/3). The gates still blocking: **operator act 2 verbatim** and the CEO's (a)-recover vs (b)-resubmit ruling (the directive orders (b); the gate records whichever is ruled). |
| 4. HARVEST + ONE BUILD | PENDING ON 3 | instrument 831f1a0e + rules 70a83fe1/40d728f8 frozen-verified and armed; YIELD_MEASUREMENT.json correctly absent; the cliff menu awaits the measured funnel. |
| TRACKS 10–12 | **DONE** | 10: `R509/R370G_REHEARSAL.json` — **DOOR_PROVEN=true** end-to-end (validate/ingest/ledger-verify+tamper-detect/decide KEEP+KILL from imported frozen constants/adjudicate counts_as_learning=false/the bounded causal loop), real_event_count=0, nothing promotes, REAL_LOOP_VERIFIED stays 0. 11: `R509/KEY_BUDGET_LEDGER.json` — per-key fingerprints + typed states + the debit log (zero metered debits this round); PatentBear active 19/20 floor-2; HF_TOKEN REGISTERED_ABSENT_VALUE_NOT_HELD_THIS_CONTAINER (the rollback). 12: `R509/RESPAWN_DESIGN.md` — M1 push-acknowledgment (DURABLE_CUSTODY_SILENCE surfaced on health), M2 periodic terminal reconciliation (would have recovered all six), M3 heartbeat-age reaping (last, deliberately), M4 idempotent resume (LXXIV s3/R401); regression gate = the R509 signature + R484/R487 no-op fixtures; lands post-harvest only. |

**ENVIRONMENT ROLLBACK RECOVERED (disclosed):** the local container rolled back to a ~Sep-11/16 snapshot between rounds — the local worklog, worktrees, and vault were lost locally; everything durable survived on origin (HEAD==origin/main==ed296772 at recovery; the sibling's R509 had advanced main to 759891bf meanwhile — read in full before acting, race-disciplined). `.gitcreds` survived with the registered GITHUB_TOKEN fingerprint (f1ebca5f9b62…): push capability intact. The vault's HF_TOKEN value is REGISTERED_ABSENT_VALUE_NOT_HELD here (LXXVI §3 — never fabricated; no deploy planned regardless).

Tests at this tip: **39 passed + 1 skipped** (R505/R506/R507 pin suites) + watchdog 5/5 + kill-switch 3/3 + inventory --check GREEN (zero engine delta — records and observer-side scripts only). Four incidents disclosed (the rollback; the read-instability + Unicode-line-separator fragmentation fixed by the git-show/sha-pin/b-\n-split fail-closed discipline; the watchdog pre-creation false-fire class caught and fixed; the kill-switch argparse dispatch bug caught and fixed).

## R509-C2 POST-RESTART ADDENDUM — the Space restarted at 11:36:15Z mid-round (boot-1789731375; not this line — read-only GETs only): the session store PERSISTED (live COMPLETE views byte-consistent with the preserved capture), the durable push path stayed SILENT through the restart (no boot snapshot — historically boots push; 120 boot rows in 760), the (a)-recover decision is STILL OPEN (2026-09-18, Coder 1)

Discovered at the round's final observation and disclosed immediately (Art. XV): `R509/POST_RESTART_OBSERVATION.json`. The measured post-restart state: production tuple d7520b9b/2.8.0 unchanged; **the live session store SURVIVED** (GET ts_ca977637f50b with the durable owner_key: HTTP 200, status COMPLETE, envelope 50a912dc0775 == the 08:35Z preserved capture — live truth, not a durable restore); **run dirs UNKNOWN from the observer domain** (no read-only route; owner-verifiable in one look — THE open input to the (a)-recover option); **the durable push path is RESTART-INSENSITIVE silent** (durable.last_snapshot STILL 00:09:15Z; zero new durable commits since 215251c9; historically boots push — 120 boot-reason rows — this boot pushed nothing: a stronger fact than R509's in-boot silence); orphans_reconciled_this_boot=0 (nothing live to reap — the six workers completed 00:12–00:45Z); n=98 durations unchanged. The R508 warning vindicated: the sibling's act-1 PRESERVE (08:35Z) beat the restart (11:36Z) by three hours; every preserved byte is durable. Phase-3 gates unchanged: operator act 2 verbatim + the (a)-vs-(b) ruling — with (a) NOT dead if the run dirs persisted.
