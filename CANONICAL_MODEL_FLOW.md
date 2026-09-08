# CANONICAL_MODEL_FLOW.md — The ONE Invention-to-Viewer Path (R433 §3)

> Authority note: this document BINDS to code — the test
> `tests/test_r433_one_canonical_model.py::test_canonical_flow_doc_binds_to_real_code`
> fails if any `module::function` token below stops resolving. The doc
> may never drift from the implementation. There is NO second
> independent invention-to-geometry mapping anywhere in the system; if
> one appears, that is a defect (Art. X / Art. LXIV).

## The chain

```text
canonical invention (recorded run state)
        |
        v  toscanini.worker::run  (the run lifecycle driver)  ──>  discovery_fabric.engine.run::EngineRun
canonical system architecture (engineering_specification.system_architecture.subsystems
                                + invention_specification records)
        |
        v  toscanini.bridge_gate::ensure_artifacts
            └─> discovery_fabric.engine.invention_bridge.classifier::classify
                 (visualizability: ENGINEERING_3D / SYSTEM_3D / PROCESS_3D / NOT_VISUALIZABLE —
                  recorded basis, never guessed)
domain geometry specification
        |
        v  discovery_fabric.engine.invention_bridge.domain_spec::select_domain_family
            (deterministic keyword score, FULL basis table recorded — auditable)
            └─> discovery_fabric.engine.invention_bridge.domain_spec::build_spec_from_state
                 └─> discovery_fabric.engine.invention_bridge.domain_spec::derive_geometry_spec
                      (canonical spec: component_ids + mapped_from fidelity + interfaces +
                       spec_sha256; every recorded subsystem appears — slot, alias, or module)
deterministic CAD geometry
        |
        v  discovery_fabric.engine.invention_bridge.bridge::bridge
            ├─ ENGINEERING_3D  -> discovery_fabric.engine.invention_bridge.bridge::_build_engineering
            │     └─> discovery_fabric.engine.invention_bridge.engineering_geometry::export
            │          (FORM_LIBRARY parametric build; STEP/STL/GLB; mm measurements)
            └─ SYSTEM_3D / conceptual -> discovery_fabric.engine.invention_bridge.bridge::_build_conceptual
                  └─> discovery_fabric.engine.invention_bridge.domain_geometry::build_domain_model
                       (7 deterministic family builders; node names = canonical component IDs;
                        no Cube.* names — R433 §5)
                       generic fallback: discovery_fabric.engine.invention_bridge.conceptual_geometry::build_system_architecture
                       (ONLY as the explicitly labeled fallback — R432 §15 / R433 §18)
validated geometry
        |
        v  discovery_fabric.engine.invention_bridge.geometry_quality_gate::run_all_gates
            (geometry gate: spec<->scene parity, NaN/Inf, bounding, islands, duplicates)
            └─> discovery_fabric.engine.invention_bridge.geometry_quality_gate::semantic_identity_gate
                 (R433 §6: canonical components vs GLB nodes; NOT VISUALIZED surfaced)
                 └─> discovery_fabric.engine.invention_bridge.geometry_quality_gate::score_technology_model
                      (R433 §13: THREE SEPARATED scores — semantic identity /
                       engineering coherence / presentation quality; never combined)
Blender presentation scene
        |
        v  discovery_fabric.engine.invention_bridge.render::render_invention
            (pinned Blender build, factory-startup, subprocess boundary)
            └─> blender_render.py executed INSIDE Blender (materials from the canonical
                 GEOMETRY_SPEC.json — one material source; studio lighting; hero camera
                 three-quarter view; section; exploded)
            Blender controls presentation ONLY — materials, lighting, camera, grouping,
            render settings. It NEVER modifies canonical dimensions or topology (R433 §9).
            artifact hashes: discovery_fabric.engine.invention_bridge.artifact_identity::build_artifact_identity
                             └─> discovery_fabric.engine.invention_bridge.artifact_identity::persist  (MODEL/ARTIFACT_IDENTITY.json)
GLB
        |
        v  run-bound artifacts (one technology = one canonical set):
            MODEL/model-00N.glb        the per-generation canonical GLBs (N = generation)
            MODEL/GEOMETRY_SPEC.json   the canonical spec (spec_sha256)
            MODEL/ARTIFACT_IDENTITY.json  run_id, generation_id, geometry_hash,
                                          source_geometry_hash (spec), blender_scene_hash,
                                          glb_matches_geometry_hash
            MODEL/3D/hero.png          the primary hero render (three-quarter, grounded)
            identity = { run_id, generation_id, canonical_geometry_hash
                        (= glb sha256), blender_scene_hash, glb_sha256 }  (R433 §11)
ONE browser viewer
        |
        v  GET /api/run/{id}/model            (the CURRENT generation's GLB)
            GET /api/run/{id}/model?gen=N     (a historical generation — loaded ONLY on
                                              explicit user request; never preloaded, R433 §16)
            GET /api/run/{id}/geometry/GEOMETRY_SPEC.json    (auditable spec)
            GET /api/run/{id}/geometry/ARTIFACT_IDENTITY.json (auditable identity)
            └─> toscanini.cio::build_cio  (geometry projection; scores + evolution carried)
                 └─> toscanini.dossier::build_dossier
                      └─> toscanini.dossier::design_tab
                           (the Design tab data: glb, components, scores, evolution,
                            generation_id/generation_count, identity, NOT VISUALIZED)
                           └─> TOSCANINI_UI/webapp/components/DossierPane.tsx :: DesignTab
                                (ONE primary viewer — [data-model-viewer] count == 1;
                                 header "TECHNOLOGY MODEL / GEN N · CURRENT";
                                 Evolution behind progressive disclosure;
                                 component chips = canonical IDs)
                                └─> TOSCANINI_UI/webapp/components/ModelViewer.tsx
                                     (lazy next/dynamic — three.js NEVER in the initial
                                      page payload; loads on Design tab open)
```

## The invariants at every boundary

1. **No second mapping.** The only invention→geometry derivation is
   `discovery_fabric.engine.invention_bridge.domain_spec::build_spec_from_state` (conceptual path) and
   `engineering_geometry` FORM_LIBRARY routing (engineering path,
   parameter-sourced). Both are deterministic; both record their basis.
2. **Component identity survives the whole chain.** Canonical IDs
   chosen by `derive_geometry_spec` become CadQuery object names in
   `build_domain_model`, become GLB node names, become the viewer's
   component-selector chips (`data-component-id`). Generic `Cube`,
   `Cube.001` names for technology components are a gate failure
   (`named_components` check).
3. **Blender is presentation-only.** `render_invention` runs the pinned
   Blender build over the AUTHORITATIVE GLB with materials assigned
   from the canonical spec; it cannot write back into the geometry
   path. `blender_scene_hash` is recorded in the artifact identity.
4. **One served model.** The current generation's GLB is the primary
   artifact (`/api/run/{id}/model`); historical generations are
   served per-request only (`?gen=N`), and the DOM contract is exactly
   one `[data-model-viewer]` element per technology page.
5. **Failure is loud.** If a domain-specific model cannot be built, the
   bridge attaches `fallback_basis` + the semantic score FAILs; the UI
   shows the NOT ESTABLISHED disclosure (§18) — never a silent
   generic slab standing in for the requested technology.
