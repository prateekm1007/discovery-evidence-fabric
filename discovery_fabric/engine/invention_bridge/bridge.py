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

BRIDGE_VERSION = "1.1.0"
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
           engine_identity: Optional[tuple] = None) -> Dict[str, Any]:
    """Run the full invention-to-3D-to-package path for one completed run.

    Returns {visualizability, geometry_out, package_out, cio_updated, report}.

    build_renders=False skips the Blender stage (used by hermetic tests and
    by paths that only need the interactive GLB contract).
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
                built = _build_engineering(vis, run_result, work_dir, attempt)
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
                built = _build_conceptual(vis, run_result)
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
            built = _build_conceptual(vis, run_result)
            attempts.append({"attempt": 1, "status": "OK"})
        except Exception as exc:  # noqa: BLE001
            # even the conceptual build can fail: one retry with the simplest form
            attempts.append({"attempt": 1, "status": "FAILED",
                             "failure_class": "CONCEPTUAL_BUILD_FAILURE",
                             "diagnosis": str(exc)})
            try:
                built = conceptual_geometry.build_system_architecture(
                    ["subsystem 1", "subsystem 2", "subsystem 3"],
                    vis.get("intervention_site", ""))
                attempts.append({"attempt": 2, "status": "OK",
                                 "repair": "simplified three-block fallback"})
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
        "measure_step": "executed" if vis["visualizability_class"] == ep.ENGINEERING_3D
                        else "topology-only (conceptual)",
    }
    geometry_out["glb_endpoint"] = glb_endpoint
    geometry_out["bridge_version"] = BRIDGE_VERSION
    _pipeline_step(steps, "GEOMETRY", "OK", {
        "visualizability_class": vis["visualizability_class"],
        "glb_sha256": geometry_out.get("glb_sha256"),
        "components": len(geometry_out.get("components") or []),
        "attempts": attempts,
    })

    # generation lineage models (handoff section 25: visual invention lineage)
    if build_generation_models:
        try:
            gen_models = _generation_models(vis, run_result, work_dir)
            geometry_out["generation_models"] = gen_models
            _pipeline_step(steps, "GENERATION_MODELS", "OK",
                           {"count": len(gen_models)})
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

def _build_conceptual(vis: Dict[str, Any], run_result: Dict[str, Any]) -> Dict[str, Any]:
    if vis["visualizability_class"] in (ep.SYSTEM_3D, ep.PROCESS_3D):
        return conceptual_geometry.build_system_architecture(
            vis.get("subsystems") or [], vis.get("intervention_site", ""))
    # single device form: use recorded layer/architecture names when present
    es = run_result.get("engineering_specification") or {}
    layers = [s.get("name", f"layer {i+1}")
              for i, s in enumerate(es.get("system_architecture", {}).get("subsystems") or [])
              if isinstance(s, dict)] or None
    return conceptual_geometry.build_conceptual_device(
        vis.get("intervention_site", ""), layers)


def _build_engineering(vis: Dict[str, Any], run_result: Dict[str, Any],
                       work_dir: str, attempt: int) -> Dict[str, Any]:
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

    return {
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
    }


def _generation_models(vis: Dict[str, Any], run_result: Dict[str, Any],
                       work_dir: str) -> List[Dict[str, Any]]:
    """Visual invention lineage: one conceptual GLB per generation (handoff 25).

    The number of models mirrors the run's recorded generation count
    (run_state.generations.generations); each model's visual complexity grows
    with the generation index so the geometry visibly changes per generation.
    """
    gens_dir = os.path.join(work_dir, "GENERATIONS")
    os.makedirs(gens_dir, exist_ok=True)
    rs = run_result.get("run_state") or {}
    recorded = ((rs.get("generations") or {}).get("generations")) or []
    n = max(1, len(recorded)) if isinstance(recorded, list) else 1
    models: List[Dict[str, Any]] = []
    for i in range(min(n, 5)):
        gen_no = i + 1
        # visual delta: each generation adds a subsystem block — the lineage
        # is visible in the geometry, not just in text
        k = min(1 + gen_no, 6)
        rec = recorded[i] if i < len(recorded) and isinstance(recorded[i], dict) else {}
        names = []
        arch = (run_result.get("engineering_specification") or {}
                .get("system_architecture") or {}).get("subsystems") or []
        for j in range(k):
            base = None
            if j < len(arch) and isinstance(arch[j], dict):
                base = arch[j].get("name")
            names.append(base or f"subsystem {j+1}")
        built = conceptual_geometry.build_system_architecture(
            names, vis.get("intervention_site", ""))
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
            "glb_path": os.path.abspath(path),
            "glb_canonical_path": os.path.abspath(canonical),
            "glb_sha256": built["glb_sha256"],
            "current": gen_no == n,
        })
    return models
