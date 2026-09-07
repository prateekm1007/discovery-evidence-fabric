"""CIO update — canonical invention object mutation (handoff section 20).

The CIO is the backend-owned authority. The frontend renders it; it never
invents maturity, evidence counts, simulation status, pass/fail, invention
identity, or validation claims. This module is the ONLY writer of geometry/
package state in the bridge, and it preserves every epistemic guard:

  * geometry.present/class/glb + hash + cad_pipeline_status from the real build
  * downloads.package_zip + package_maturity
  * maturity.design basis — honest: conceptual visualization != engineering CAD
  * EXPERIMENTALLY VERIFIED untouched unless real reality-loop evidence exists
  * language guards on all new copy
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import epistemics as ep


def update_cio(cio: Dict[str, Any], geometry_out: Dict[str, Any],
               package_out: Dict[str, Any],
               visualizability: Dict[str, Any]) -> Dict[str, Any]:
    """Return an updated copy of the CIO with geometry + package state attached."""
    updated = dict(cio or {})
    vis_class = geometry_out.get("visualizability_class") or ep.CONCEPTUAL_3D
    is_engineering = vis_class == ep.ENGINEERING_3D

    # --- geometry ---------------------------------------------------------------
    geometry = dict(updated.get("geometry") or {})
    geometry.update({
        "present": True,
        "visualizability_class": vis_class,
        "visualizability_meaning": ep.VISUALIZABILITY_MEANINGS[vis_class],
        "classification_basis": visualizability.get("classification_basis"),
        "glb": geometry_out.get("glb_endpoint") or package_out.get("glb_endpoint"),
        "glb_sha256": geometry_out.get("glb_sha256"),
        "step": geometry_out.get("step_files") or [],
        "stl": geometry_out.get("stl_files") or [],
        "svg_views": [],
        "parametric_model_present": bool(
            is_engineering and geometry_out.get("parametric_source")),
        "cad_pipeline_status": geometry_out.get("cad_pipeline_status"),
        "key_dimensions": geometry_out.get("key_dimensions") or {},
        "components": geometry_out.get("components") or [],
        "validation": geometry_out.get("validation"),
        "authority": (
            "CadQuery/OCCT parametric build is the engineering geometry authority; "
            "meshes and renders are derived artifacts (R413 geometry authority "
            "boundary — a render can never originate or validate geometry)"
        ),
    })
    ep.guard_no_engineering_dimensions(vis_class, geometry.get("key_dimensions") or {})
    updated["geometry"] = geometry

    # --- engineering (parameters only on the engineering path) ------------------
    engineering = dict(updated.get("engineering") or {})
    if is_engineering:
        engineering["parameters"] = geometry_out.get("parameters") or []
        engineering["specification_present"] = True
    else:
        engineering.setdefault("parameters", [])
        engineering["specification_present"] = bool(
            engineering.get("specification_present"))
    updated["engineering"] = engineering

    # --- downloads ----------------------------------------------------------------
    downloads = dict(updated.get("downloads") or {})
    downloads.update({
        "package_zip": package_out.get("package_endpoint"),
        "package_maturity": package_out.get("package_maturity"),
        "package_zip_sha256": package_out.get("zip_sha256"),
        "counsel_package": downloads.get("counsel_package"),
        "note": (
            "technology package = buyer-facing product; counsel package = technical "
            "evidence export for IP counsel review — not a legal document"
        ),
    })
    updated["downloads"] = downloads

    # --- maturity (invention existence != package maturity) ----------------------
    maturity = dict(updated.get("maturity") or {})
    basis = dict(maturity.get("maturity_basis") or {})
    maturity["design"] = True
    basis["design"] = (
        f"{vis_class} visualization produced by the CadQuery/OCCT geometry authority"
        + (" with measured geometry and deterministic validation gates"
           if is_engineering else
           " — conceptual architecture only; engineering CAD is not yet earned "
           "(no sourced geometry parameters on this run)")
    )
    maturity["maturity_basis"] = basis
    ladder = list(maturity.get("maturity_ladder") or [None, None, None, None])
    while len(ladder) < 4:
        ladder.append(None)
    ladder[0] = "DESIGNED"
    maturity["maturity_ladder"] = ladder
    ep.guard_experimental_language(maturity)  # reality cannot be simulated into existence
    updated["maturity"] = maturity

    # --- visualization section (viewer hints, frontend renders only these) -------
    updated["visualization"] = {
        "viewer_required": ["orbit", "zoom", "pan", "reset", "wireframe", "clip"],
        "component_inspection": [
            {"from": "component name", "explain": ["function", "mechanism",
             "evidence", "simulation", "unknowns"]},
        ],
        "generation_models": geometry_out.get("generation_models") or [],
        "disclaimer": ep.conceptual_disclaimer(vis_class) if not is_engineering else None,
    }

    # --- provenance extension ------------------------------------------------------
    provenance = dict(updated.get("provenance") or {})
    provenance.update({
        "geometry_sha256": geometry_out.get("glb_sha256"),
        "package_zip_sha256": package_out.get("zip_sha256"),
        "bridge_version": geometry_out.get("bridge_version"),
    })
    updated["provenance"] = provenance

    # language gate on the copy we added
    ep.guard_language(json_copy(updated))
    return updated


def json_copy(obj: Any) -> str:
    import json
    try:
        return json.dumps(obj)
    except TypeError:
        return str(obj)
