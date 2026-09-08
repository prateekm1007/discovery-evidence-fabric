"""Canonical invention-to-3D-to-package bridge — the P0 orchestrator.

Closes the gap diagnosed on 2026-09-07: fresh discovery runs end at
EVOLVED_INVENTION_CANDIDATE with NO ENGINEER stage, so inventions reach the
user without a 3D artifact or technology package ("GEN 2 has no 3D model …
honest absence").

Contract (handoff sections 15-31):

    run state (JSON)  +  CIO (JSON)
        |
        v  classify (measured, recorded)
    visualizability: ENGINEERING_3D | SYSTEM_3D | CONCEPTUAL_3D | PROCESS_3D | NOT_VISUALIZABLE
        |
        v  geometry (CadQuery/OCCT authority; failure -> diagnose -> repair -> rebuild)
    measured geometry -> GLB (+STEP/STL when engineering)
        |
        v  package (one canonical source: essay, definition, evidence, experiment, manifest)
    TECHNOLOGY_PACKAGE ZIP
        |
        v  CIO update (epistemic guards intact)
    updated CIO for the frontend to render

Every step appends to the pipeline report, which becomes
geometry.cad_pipeline_status in the CIO. Nothing here fabricates measurements,
prior art, or validation: conceptual artifacts carry no engineering dimensions,
and EXPERIMENTALLY VERIFIED is never set by this bridge.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from . import epistemics as ep
from . import classifier, conceptual_geometry, engineering_geometry, package, cio_update
from . import render as render_stage
from . import domain_spec, domain_geometry
from . import geometry_quality_gate as quality_gate
from . import artifact_identity as artifact_id

BRIDGE_VERSION = "2.0.0"
MAX_GEOMETRY_ATTEMPTS = 3


def _pipeline_step(steps: List[Dict[str, Any]], name: str, status: str,
                   detail: Optional[Dict[str, Any]] = None) -> None:
    steps.append({
        "step": name,
        "status": status,
        "detail": detail or {},
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    })


def bridge(run_result: Dict[str, Any], cio: Optional[Dict[str, Any]],
           work_dir: str,
           glb_endpoint: Optional[str] = None,
           package_endpoint: Optional[str] = None,
           build_generation_models: bool = True,
           build_renders: bool = True,
           engine_identity: Optional[tuple] = None,
           run_id: Optional[str] = None) -> Dict[str, Any]:
    """Run the full invention-to-3D-to-package path for one completed run.

    Returns {visualizability, geometry_out, package_out, cio_updated, report}.

    build_renders=False skips the Blender stage (used by hermetic tests and
    by paths that only need the interactive GLB contract).

    R432: the conceptual path is DOMAIN-AWARE — a deterministic family
    selection (recorded score table) drives canonical geometry builders
    whose node names are canonical component IDs. The generic
    substrate+blocks diagram remains ONLY as an explicitly labeled
    fallback (section 3/15), never a silent primary artifact (section 23).
    """
    steps: List[Dict[str, Any]] = []
    cio = cio or {}

    # ---------------------------------------------------------------- 1. classify
    vis = classifier.classify(run_result, cio)
    _pipeline_step(steps, "CLASSIFY", "OK", {
        "visualizability_class": vis["visualizability_class"],
        "basis": vis["classification_basis"],
    })

    geometry_out: Dict[str, Any]

    if vis["visualizability_class"] == ep.NOT_VISUALIZABLE:
        # honest terminal: report why, never fake a model (handoff section 18)
        _pipeline_step(steps, "GEOMETRY", "NOT_VISUALIZABLE", {
            "reason": vis["classification_basis"]["reason"],
        })
        return {
            "visualizability": vis,
            "geometry_out": None,
            "package_out": None,
            "cio_updated": cio,  # unchanged
            "report": {"steps": steps, "bridge_version": BRIDGE_VERSION,
                       "outcome": "NOT_VISUALIZABLE"},
        }

    # ---------------------------------------------------------------- 2. geometry
    attempts: List[Dict[str, Any]] = []
    built = None
    last_failure = None
    demoted_to_conceptual = False

    if vis["visualizability_class"] == ep.ENGINEERING_3D:
        for attempt in range(1, MAX_GEOMETRY_ATTEMPTS + 1):
            try:
                built = _build_engineering(vis, run_result, work_dir, attempt,
                                           run_id=run_id)
                attempts.append({"attempt": attempt, "status": "OK"})
                break
            except Exception as exc:  # noqa: BLE001 — failure taxonomy is the product
                failure = engineering_geometry.diagnose_failure(exc, "", {})
                attempts.append({"attempt": attempt, "status": "FAILED", **failure})
                last_failure = failure
                # repair pass: clamp parameters to envelopes (where recorded)
                for p in vis["geometry_parameters"]:
                    env = p.get("envelope")
                    if env and len(env) == 2 and isinstance(p.get("value"), (int, float)):
                        p["value"] = min(max(float(p["value"]),
                                             float(env[0])), float(env[1]))
                if attempt == MAX_GEOMETRY_ATTEMPTS:
                    # ENGINEERING path exhausted -> honest demotion to conceptual,
                    # never a silent "No 3D" (handoff sections 17-18)
                    vis = dict(vis)
                    vis["visualizability_class"] = ep.SYSTEM_3D
                    vis["classification_basis"] = dict(vis["classification_basis"])
                    vis["classification_basis"]["reason"] = (
                        "engineering geometry failed after "
                        f"{MAX_GEOMETRY_ATTEMPTS} repair attempts "
                        f"({last_failure['failure_class']}); demoted to conceptual "
                        "system architecture — engineering CAD remains unearned"
                    )
                    demoted_to_conceptual = True
                    _pipeline_step(steps, "GEOMETRY", "DEMOTED_TO_CONCEPTUAL",
                                   {"attempts": attempts})
        if demoted_to_conceptual:
            # build the conceptual artifact on the demoted classification
            try:
                built = _build_conceptual(vis, run_result, work_dir,
                                          run_id=run_id)
                attempts.append({"attempt": MAX_GEOMETRY_ATTEMPTS + 1,
                                 "status": "OK",
                                 "repair": "conceptual fallback after engineering failure"})
            except Exception as exc:  # noqa: BLE001
                attempts.append({"attempt": MAX_GEOMETRY_ATTEMPTS + 1,
                                 "status": "FAILED",
                                 "failure_class": "CONCEPTUAL_BUILD_FAILURE",
                                 "diagnosis": str(exc)})
    else:
        try:
            built = _build_conceptual(vis, run_result, work_dir,
                                       run_id=run_id)
            attempts.append({"attempt": 1, "status": "OK",
                             "domain_family": (built or {}).get(
                                 "domain_family")})
        except Exception as exc:  # noqa: BLE001
            # even the conceptual build can fail: one retry with the
            # simplest form — the GENERIC labeled fallback (R432 section 3:
            # generic blocks are acceptable ONLY as a clearly labeled
            # early conceptual fallback, never a silent primary artifact)
            attempts.append({"attempt": 1, "status": "FAILED",
                             "failure_class": "CONCEPTUAL_BUILD_FAILURE",
                             "diagnosis": str(exc)})
            try:
                built = conceptual_geometry.build_system_architecture(
                    ["subsystem 1", "subsystem 2", "subsystem 3"],
                    vis.get("intervention_site", ""))
                built["domain_family"] = "GENERIC_FALLBACK"
                built["fallback_basis"] = (
                    f"domain build failed ({type(exc).__name__}: {exc}) — "
                    "explicitly labeled generic fallback; engineering "
                    "geometry remains unearned")
                attempts.append({"attempt": 2, "status": "OK",
                                 "repair": "labeled generic fallback after "
                                           "domain build failure"})
            except Exception as exc2:  # noqa: BLE001
                attempts.append({"attempt": 2, "status": "FAILED",
                                 "diagnosis": str(exc2)})
                _pipeline_step(steps, "GEOMETRY", "FAILED_ALL_ATTEMPTS",
                               {"attempts": attempts})
                return {
                    "visualizability": vis, "geometry_out": None,
                    "package_out": None, "cio_updated": cio,
                    "report": {"steps": steps, "bridge_version": BRIDGE_VERSION,
                               "outcome": "GEOMETRY_FAILED",
                               "attempts": attempts},
                }

    if built is None:
        _pipeline_step(steps, "GEOMETRY", "FAILED_ALL_ATTEMPTS", {"attempts": attempts})
        return {
            "visualizability": vis, "geometry_out": None, "package_out": None,
            "cio_updated": cio,
            "report": {"steps": steps, "bridge_version": BRIDGE_VERSION,
                       "outcome": "GEOMETRY_FAILED", "attempts": attempts},
        }

    geometry_out = dict(built)
    geometry_out["visualizability_class"] = vis["visualizability_class"]
    geometry_out["cad_pipeline_status"] = {
        "artifact": "CAD_PIPELINE_STATUS",
        "bridge_version": BRIDGE_VERSION,
        "attempts": attempts,
        "status": "COMPLETED",
        "visualizability_class": vis["visualizability_class"],
        "geometry_authority": "CadQuery/OCCT",
        "domain_family": geometry_out.get("domain_family"),
        "measure_step": "executed" if vis["visualizability_class"] == ep.ENGINEERING_3D
                        else "topology-only (conceptual)",
    }
    geometry_out["glb_endpoint"] = glb_endpoint
    geometry_out["bridge_version"] = BRIDGE_VERSION
    _pipeline_step(steps, "GEOMETRY", "OK", {
        "visualizability_class": vis["visualizability_class"],
        "domain_family": geometry_out.get("domain_family"),
        "glb_sha256": geometry_out.get("glb_sha256"),
        "components": len(geometry_out.get("components") or []),
        "quality_gates": (geometry_out.get("quality_gates") or {}).get(
            "passed"),
        "attempts": attempts,
    })

    # generation lineage models (handoff section 25: visual invention lineage)
    if build_generation_models:
        try:
            gen_models = _generation_models(vis, run_result, work_dir)
            geometry_out["generation_models"] = gen_models
            # the CURRENT generation's canonical model is the primary
            # served artifact — keep glb_path/identity pointed at it
            for m in gen_models:
                if m.get("current") and m.get("glb_canonical_path"):
                    geometry_out["glb_path"] = m["glb_canonical_path"]
                    try:
                        doc = artifact_id.load(work_dir)
                        if doc:
                            doc["glb_path"] = m["glb_canonical_path"]
                            doc["generation_id"] = f"gen-{m.get('generation')}"
                            artifact_id.persist(work_dir, doc)
                            geometry_out["artifact_identity"] = doc
                    except Exception:  # noqa: BLE001 — identity stays honest
                        pass
                    break
            _pipeline_step(steps, "GENERATION_MODELS", "OK",
                           {"count": len(gen_models),
                            "domain_family": (gen_models[-1] or {}).get(
                                "domain_family") if gen_models else None})
            # R433 sections 2/15: the EVOLUTION projection — history
            # rows for the progressive-disclosure section; exactly one
            # CURRENT row; per-gen models load only on request
            counts = {m["generation"]: m.get("component_count")
                      for m in gen_models}
            geometry_out["evolution"] = _evolution_projection(
                gen_models, run_result, run_id,
                component_counts=counts)
            geometry_out["generation_id"] = next(
                (f"gen-{m['generation']}" for m in reversed(gen_models)
                 if m.get("current")), None)
            geometry_out["generation_count"] = len(gen_models)
        except Exception as exc:  # noqa: BLE001
            _pipeline_step(steps, "GENERATION_MODELS", "SKIPPED",
                           {"reason": str(exc)})

    # ------------------------------------------------- 2.5 render (R419 fixed 3D stack)
    # Blender 5.2 LTS headless over the authoritative GLB: hero/section/
    # exploded PNG renders + materialized presentation GLBs (operator
    # directive R419 sections 5-6). Presentation ONLY — CadQuery/OCCT
    # stays the engineering authority (section 7; render_record.json
    # carries the topology comparison). A render failure is a TYPED
    # record; the GLB contract is unaffected (Art. LXI).
    render_record: Optional[Dict[str, Any]] = None
    if build_renders:
        try:
            render_record = render_stage.render_invention(
                work_dir, geometry_out,
                is_conceptual=vis["visualizability_class"] != ep.ENGINEERING_3D)
            geometry_out["renders"] = render_record
            _pipeline_step(steps, "RENDER", render_record.get("status", "OK"), {
                k: render_record.get(k) for k in
                ("pinned_blender", "source_glb_sha256", "artifacts",
                 "missing_artifacts", "seconds", "note")
            })
        except Exception as exc:  # noqa: BLE001 — typed, never silent
            render_record = {
                "stage": "RENDER", "status": "RENDER_FAILED",
                "error": f"{type(exc).__name__}: {exc}",
            }
            geometry_out["renders"] = render_record
            _pipeline_step(steps, "RENDER", "RENDER_FAILED",
                           {"error": str(exc)})

    # ---------------------------------------------------------------- 3. package
    pkg_dir = os.path.join(work_dir, "TECHNOLOGY_PACKAGE")
    os.makedirs(pkg_dir, exist_ok=True)
    package_out = package.assemble(
        run_result, cio, geometry_out, pkg_dir,
        visualizability=vis,
        zip_name=None,
        engine_identity=engine_identity,
    )
    package_out["package_endpoint"] = package_endpoint
    package_out["glb_endpoint"] = glb_endpoint
    _pipeline_step(steps, "PACKAGE", "OK", {
        "zip_path": package_out["zip_path"],
        "zip_sha256": package_out["zip_sha256"],
        "package_maturity": package_out["package_maturity"],
        "files": package_out["manifest"]["file_count"],
    })

    # ---------------------------------------------------------------- 4. CIO update
    cio_updated = cio_update.update_cio(cio, geometry_out, package_out, vis)
    _pipeline_step(steps, "CIO_UPDATE", "OK", {
        "geometry_present": cio_updated["geometry"]["present"],
        "package_zip": cio_updated["downloads"]["package_zip"],
    })

    return {
        "visualizability": vis,
        "geometry_out": geometry_out,
        "package_out": package_out,
        "cio_updated": cio_updated,
        "report": {
            "bridge_version": BRIDGE_VERSION,
            "steps": steps,
            "outcome": "COMPLETED",
            "visualizability_class": vis["visualizability_class"],
        },
    }


# ---------------------------------------------------------------------------
# Internal builders
# ---------------------------------------------------------------------------

def _persist_conceptual_artifacts(work_dir: str, built: Dict[str, Any],
                                  spec: Optional[Dict[str, Any]],
                                  vis: Dict[str, Any],
                                  run_result: Dict[str, Any],
                                  run_id: Optional[str]) -> Dict[str, Any]:
    """Persist the domain conceptual layer: MODEL/model-001.glb (the
    canonical GLB the run routes serve), MODEL/GEOMETRY_SPEC.json, and
    MODEL/ARTIFACT_IDENTITY.json. Failure here is typed, never fatal
    to the build itself."""
    import json as _json
    try:
        model_dir = os.path.join(work_dir, "MODEL")
        os.makedirs(model_dir, exist_ok=True)
        glb_path = os.path.join(model_dir, "model-001.glb")
        with open(glb_path, "wb") as f:
            f.write(built["glb_bytes"])
        built["glb_path"] = glb_path
        if spec is not None:
            with open(os.path.join(model_dir, "GEOMETRY_SPEC.json"),
                      "w") as f:
                _json.dump(spec, f, indent=2)
        tech_id = (((run_result.get("problem") or {}).get("problem_id"))
                   or ((run_result.get("final_state") or {}).get(
                       "problem_id")) or "")
        cad_source = None
        if built.get("parametric_source"):
            from . import engineering_geometry as _eg
            cad_source = _eg.canonical_source_identity(
                built["parametric_source"].get("form", ""))
        identity = artifact_id.build_artifact_identity(
            run_dir=work_dir,
            technology_id=tech_id,
            run_id=run_id or "",
            generation_id="gen-1",
            geometry_hash=built.get("glb_sha256") or "",
            source_geometry_hash=(spec or {}).get("spec_sha256"),
            glb_path=glb_path,
            cad_source=cad_source,
            visualizability_class=vis.get("visualizability_class"),
            domain_family=built.get("domain_family"),
        )
        artifact_id.persist(work_dir, identity)
        built["artifact_identity"] = identity
    except OSError:
        pass
    return built


def _build_conceptual(vis: Dict[str, Any], run_result: Dict[str, Any],
                      work_dir: Optional[str] = None,
                      run_id: Optional[str] = None) -> Dict[str, Any]:
    """R432: the conceptual path is DOMAIN-AWARE for device-form
    classes. PROCESS_3D keeps the flow-chain representation (a process
    is honestly a flow, not a device). The generic architecture
    diagram remains ONLY as the explicitly labeled fallback (section
    3/15) — a family failure falls back LOUDLY with a recorded basis,
    never silently (section 23)."""
    vclass = vis["visualizability_class"]

    if vclass == ep.PROCESS_3D:
        built = conceptual_geometry.build_system_architecture(
            vis.get("subsystems") or [], vis.get("intervention_site", ""))
        built["domain_family"] = "PROCESS_FLOW"
        if work_dir:
            _persist_conceptual_artifacts(work_dir, built, None, vis,
                                          run_result, run_id)
        return built

    # --- domain family selection (deterministic, basis recorded) ---------
    out = domain_spec.build_spec_from_state(run_result, vis)
    selection, spec = out["selection"], out["spec"]
    family = selection["family"]

    if family == domain_spec.GENERIC_FAMILY:
        # honest labeled generic fallback (R432 section 3: acceptable
        # only as a clearly labeled early conceptual fallback)
        if vclass == ep.CONCEPTUAL_3D and not (vis.get("subsystems") or []):
            es = run_result.get("engineering_specification") or {}
            layers = [s.get("name", f"layer {i+1}")
                      for i, s in enumerate(
                          es.get("system_architecture", {}).get(
                              "subsystems") or [])
                      if isinstance(s, dict)] or None
            built = conceptual_geometry.build_conceptual_device(
                vis.get("intervention_site", ""), layers)
        else:
            built = conceptual_geometry.build_system_architecture(
                vis.get("subsystems") or [],
                vis.get("intervention_site", ""))
        built["domain_family"] = "GENERIC_ARCHITECTURE"
        built["domain_selection"] = selection
        built["fallback_basis"] = (
            "no domain family earned the minimum form score — the "
            "generic architecture diagram is shown as the clearly "
            "labeled early conceptual fallback (R432 section 3/15)")
        if work_dir:
            _persist_conceptual_artifacts(work_dir, built, None, vis,
                                          run_result, run_id)
        # R433: the generic fallback FAILS semantic identity by record
        # (honest score, never hidden — section 13)
        built["scores"] = quality_gate.score_technology_model(
            None, built["glb_bytes"], domain_family=built.get(
                "domain_family"),
            requested_problem=str((run_result or {}).get("user_text")
                                   or ""),
            identity=built.get("artifact_identity"))
        return built

    # --- deterministic domain build + quality gates -------------------------
    try:
        built = domain_geometry.build_domain_model(spec)
    except Exception as exc:  # noqa: BLE001 — LOUD fallback, never silent
        built = conceptual_geometry.build_system_architecture(
            vis.get("subsystems") or [], vis.get("intervention_site", ""))
        built["domain_family"] = "GENERIC_FALLBACK"
        built["fallback_basis"] = (
            f"domain family {family} was selected but its deterministic "
            f"builder failed ({type(exc).__name__}: {exc}) — explicitly "
            "labeled generic fallback; the failure is recorded, the "
            "generic diagram never masquerades as the domain model "
            "(R432 section 23)")
        if work_dir:
            _persist_conceptual_artifacts(work_dir, built, None, vis,
                                          run_result, run_id)
        # R433: the builder-failure fallback FAILS semantic identity by
        # record (honest score, never hidden — section 13)
        built["scores"] = quality_gate.score_technology_model(
            None, built["glb_bytes"], domain_family=family,
            requested_problem=str((run_result or {}).get("user_text")
                                   or ""),
            identity=built.get("artifact_identity"))
        return built

    gates = quality_gate.run_all_gates(
        built["glb_bytes"], spec, domain_family=family)
    built["quality_gates"] = gates
    built["domain_selection"] = selection
    built["geometry_spec"] = spec
    if not gates["passed"]:
        # The domain build exists but failed its own quality gate: keep
        # it ONLY with the typed failure record attached — the dossier
        # shows the gate failures honestly. The artifact is not
        # silently replaced (the failure is product information).
        built["quality_gate_failed"] = True
    if work_dir:
        _persist_conceptual_artifacts(work_dir, built, spec, vis,
                                      run_result, run_id)
    # R433 section 13: the three SEPARATED scores (semantic identity /
    # engineering coherence / presentation quality — never combined),
    # bound to the persisted artifact identity when available
    built["scores"] = quality_gate.score_technology_model(
        spec, built["glb_bytes"], domain_family=family,
        requested_problem=str((run_result or {}).get("user_text") or ""),
        identity=built.get("artifact_identity"))
    return built


def _build_engineering(vis: Dict[str, Any], run_result: Dict[str, Any],
                       work_dir: str, attempt: int,
                       run_id: Optional[str] = None) -> Dict[str, Any]:
    normalized = engineering_geometry.normalize_parameters(vis["geometry_parameters"])
    params = normalized["build_params"]
    meta = normalized["parameter_meta"]
    if len(params) < 3:
        raise ValueError(
            f"engineering build requires >=3 mm-family parameters; got {len(params)}")

    form = engineering_geometry.route_form(
        vis.get("intervention_site", ""), vis.get("subsystems") or [])

    builder = engineering_geometry.FORM_LIBRARY[form]

    def rebuild():
        return builder(params)

    solid = rebuild()

    # MEASURE (engineering path: real mm measurements)
    key_dims = engineering_geometry.measure(solid)
    key_dims["measurement_basis"] = "CAD_MEASURED (CadQuery/OCCT solid, mm)"
    key_dims["form"] = form
    key_dims["build_attempt"] = attempt

    # VALIDATE (deterministic gates) + EXPORT (GLB/STEP/STL)
    out_dir = os.path.join(work_dir, "MODEL")
    os.makedirs(out_dir, exist_ok=True)
    name = "engineering_model"
    component_solids = [
        (name, solid),
    ]
    exported = engineering_geometry.export(
        solid, name, out_dir, component_solids=component_solids)

    import trimesh
    mesh = trimesh.load(exported["stl_path"])
    validation = engineering_geometry.validate_gates(solid, mesh, rebuild_fn=rebuild)
    if not validation["passed"]:
        raise ValueError(f"geometry validation gates failed: {validation['gates']}")

    # R432 section 16 engineering block: the provenance hash chain +
    # the canonical artifact identity (spec-less: the engineering
    # path's canonical source IS the FORM_LIBRARY builder — identity
    # carries cad_source instead of a spec hash).
    result = {
        "glb_bytes": exported["glb_bytes"],
        "glb_sha256": exported["glb_sha256"],
        "glb_path": exported["glb_path"],
        "step_files": [exported["step_path"]],
        "stl_files": [exported["stl_path"]],
        "key_dimensions": key_dims,
        "components": [{"name": name, "type": "device",
                        "role": "parametric engineering model (measured)"}],
        "parameters": meta,
        "parametric_source": {
            "form": form,
            "parameters": params,
        },
        "validation": validation,
        "domain_family": "ENGINEERING_PARAMETRIC",
    }
    result["quality_gates"] = quality_gate.run_all_gates(
        exported["glb_bytes"], None, domain_family=None,
        engineering=True, model_dir=work_dir, geometry_out=result)
    tech_id = (((run_result.get("problem") or {}).get("problem_id"))
               or ((run_result.get("final_state") or {}).get(
                   "problem_id")) or "")
    identity = artifact_id.build_artifact_identity(
        run_dir=work_dir, technology_id=tech_id, run_id=run_id or "",
        generation_id="gen-1",
        geometry_hash=exported["glb_sha256"],
        source_geometry_hash=None,
        glb_path=exported["glb_path"],
        cad_source=engineering_geometry.canonical_source_identity(form),
        visualizability_class=ep.ENGINEERING_3D,
        domain_family="ENGINEERING_PARAMETRIC")
    artifact_id.persist(work_dir, identity)
    result["artifact_identity"] = identity
    # R433 section 13: the engineering path carries the same three
    # separated scores (the parametric form IS the semantic identity
    # here; the canonical CAD source is the coherence authority)
    result["scores"] = quality_gate.score_technology_model(
        None, exported["glb_bytes"], domain_family="ENGINEERING_PARAMETRIC",
        requested_problem=str((run_result or {}).get("user_text") or ""),
        identity=identity)
    return result


def _generation_models(vis: Dict[str, Any], run_result: Dict[str, Any],
                       work_dir: str) -> List[Dict[str, Any]]:
    """Visual invention lineage: one GLB per generation (handoff 25).

    R432: each generation's model is the DOMAIN model of that
    generation's architecture — the structural family form is present
    in every generation (a vehicle generation is always vehicle-
    shaped) and the mapped component count grows with the generation
    index so the lineage is visible in the geometry, not just in text.
    """
    gens_dir = os.path.join(work_dir, "GENERATIONS")
    os.makedirs(gens_dir, exist_ok=True)
    rs = run_result.get("run_state") or {}
    recorded = ((rs.get("generations") or {}).get("generations")) or []
    n = max(1, len(recorded)) if isinstance(recorded, list) else 1
    arch = (run_result.get("engineering_specification") or {}
            .get("system_architecture") or {}).get("subsystems") or []
    full_names = [s.get("name") if isinstance(s, dict) else str(s)
                  for s in arch if (isinstance(s, dict) and s.get("name"))
                  or isinstance(s, str)] or (vis.get("subsystems") or [])

    # the family selection is computed ONCE from the full state (the
    # technology class does not change per generation)
    out = domain_spec.build_spec_from_state(run_result, vis)
    family = out["selection"]["family"]

    models: List[Dict[str, Any]] = []
    for i in range(min(n, 5)):
        gen_no = i + 1
        rec = recorded[i] if i < len(recorded) and isinstance(recorded[i], dict) else {}
        # visual delta: generation N carries the first 1+gen recorded
        # subsystems (capped at the full list); the CURRENT generation
        # (gen_no == n) always carries the FULL architecture — the
        # served model IS the primary artifact (R432 section 20: THIS
        # MODEL = THIS INVENTION GENERATION; geometry_hash equality)
        k = len(full_names) if gen_no == n else min(1 + gen_no,
                                                    max(1, len(full_names)))
        names = list(full_names[:k]) or [f"subsystem {j+1}" for j in range(k)]
        try:
            gen_spec = domain_spec.derive_geometry_spec(
                family, names, vis.get("intervention_site", ""),
                selection=out["selection"])
            if gen_spec.get("technology_class") == domain_spec.GENERIC_FAMILY \
                    or not gen_spec.get("components"):
                built = conceptual_geometry.build_system_architecture(
                    names, vis.get("intervention_site", ""))
                built["domain_family"] = "GENERIC_ARCHITECTURE"
            else:
                built = domain_geometry.build_domain_model(gen_spec)
        except Exception:  # noqa: BLE001 — lineage stays honest per gen
            built = conceptual_geometry.build_system_architecture(
                names, vis.get("intervention_site", ""))
            built["domain_family"] = "GENERIC_FALLBACK"
        path = os.path.join(gens_dir, f"gen-{gen_no}.glb")
        with open(path, "wb") as f:
            f.write(built["glb_bytes"])
        # R418 engine integration: the server's per-generation route
        # (/api/run/{id}/model?gen=N) and the run_state/CIO projections
        # resolve MODEL/model-00N.glb — write the canonical copy so the
        # bridge's generation models are served by the EXISTING routes
        # with zero projection changes beyond class reporting.
        model_dir = os.path.join(work_dir, "MODEL")
        os.makedirs(model_dir, exist_ok=True)
        canonical = os.path.join(model_dir, f"model-{gen_no:03d}.glb")
        with open(canonical, "wb") as f:
            f.write(built["glb_bytes"])
        models.append({
            "generation": gen_no,
            "invention_id": rec.get("invention_id"),
            "parent_id": rec.get("parent_id") or rec.get("parent_invention_id"),
            "what_changed": rec.get("what_changed"),
            "domain_family": built.get("domain_family"),
            "component_count": len(built.get("components") or []),
            "glb_path": os.path.abspath(path),
            "glb_canonical_path": os.path.abspath(canonical),
            "glb_sha256": built["glb_sha256"],
            "current": gen_no == n,
        })
    return models


def _evolution_projection(gen_models: List[Dict[str, Any]],
                          run_result: Dict[str, Any],
                          run_id: Optional[str],
                          component_counts: Optional[Dict[int, int]] = None
                          ) -> Optional[List[Dict[str, Any]]]:
    """R433 sections 2/15 — generation HISTORY, not competing artifacts.

    One row per generation: the UI renders exactly ONE current primary
    model; history rows live behind progressive disclosure and may
    TEMPORARILY swap the single viewer's model on explicit request.
    Status vocabulary is the lineage's own (INVENTION_* states) — the
    projection never invents a verdict (Art. X).
    """
    if not gen_models:
        return None
    rs = run_result.get("run_state") or {}
    recorded = ((rs.get("generations") or {}).get("generations")) or []
    n = len(gen_models)
    rows: List[Dict[str, Any]] = []
    for m in gen_models:
        gen_no = m["generation"]
        rec = recorded[gen_no - 1] if gen_no <= len(recorded) \
            and isinstance(recorded[gen_no - 1], dict) else {}
        # why the CURRENT generation holds the primary slot: its own
        # recorded state (survived / requires-experiment / evolved)
        current = bool(m.get("current"))
        if current:
            status = "CURRENT"
            basis = (f"state {rec.get('state') or 'RECORDED'}"
                     f" · maturity {rec.get('maturity') or 'RECORDED'}")
            why = (m.get("what_changed")
                   or "the latest recorded architecture generation")
        else:
            # why this generation changed: the NEXT generation's
            # recorded what_changed (the delta that superseded it) —
            # never a projection-invented narrative
            nxt = recorded[gen_no] if gen_no < len(recorded) \
                and isinstance(recorded[gen_no], dict) else {}
            status = "CHALLENGED" if rec.get("state") == \
                "INVENTION_CHALLENGED" else "SUPERSEDED"
            why = (nxt.get("what_changed")
                   or rec.get("state")
                   or "superseded by a later recorded generation")
            basis = f"state {rec.get('state') or 'RECORDED'}"
        rows.append({
            "generation": gen_no,
            "invention_id": m.get("invention_id"),
            "status": status,
            "status_basis": basis,
            "why": str(why)[:240],
            "domain_family": m.get("domain_family"),
            "component_count": (component_counts or {}).get(gen_no),
            # the per-generation model route — loaded ONLY on explicit
            # request (R433 section 16: history never preloads)
            "glb": (f"/api/run/{run_id}/model?gen={gen_no}"
                    if run_id else None),
            "glb_sha256": m.get("glb_sha256"),
            "current": current,
        })
    # exactly one CURRENT row (the last) — a projection invariant the
    # tests hold: history may be long, the primary slot is singular
    if sum(1 for r in rows if r["current"]) != 1:
        rows[-1]["current"] = True
        rows[-1]["status"] = "CURRENT"
        for r in rows[:-1]:
            r["current"] = False
    return rows
