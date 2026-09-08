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


def _gate_summary(gates: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Compact, non-bloating projection of the R432 quality gates."""
    if not gates:
        return None
    return {
        "passed": gates.get("passed"),
        "failures": gates.get("failures") or [],
        "version": gates.get("version"),
        "geometry_gate_passed": (gates.get("geometry_gate") or {}).get(
            "passed"),
        "visual_gate_passed": (gates.get("visual_gate") or {}).get("passed"),
        "engineering_gate_passed": (
            (gates.get("engineering_gate") or {}).get("passed")
            if gates.get("engineering_gate") is not None else None),
        "note": ("presentation gate is a structural metrics audit — never a "
                 "scientific verdict (R432 section 17)"),
    }


def _identity_summary(identity: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The R432 section-20 identity chain the browser displays."""
    if not identity:
        return None
    return {
        "technology_id": identity.get("technology_id"),
        "run_id": identity.get("run_id"),
        "generation_id": identity.get("generation_id"),
        "geometry_hash": identity.get("geometry_hash"),
        "source_geometry_hash": identity.get("source_geometry_hash"),
        "blender_scene_hash": identity.get("blender_scene_hash"),
        "glb_matches_geometry_hash": identity.get("glb_matches_geometry_hash"),
        "derivation": identity.get("derivation"),
    }


def _scores_summary(scores: Optional[Dict[str, Any]]
                    ) -> Optional[Dict[str, Any]]:
    """R433 section 13 — the three SEPARATED scores, each an independent
    record; deliberately NO combined number."""
    if not scores:
        return None

    def _dim(key: str) -> Dict[str, Any]:
        d = scores.get(key) or {}
        return {
            "score": d.get("score"),
            "passed": d.get("passed"),
            "failures": d.get("failures") or [],
        }

    return {
        "semantic_identity": _dim("semantic_identity"),
        "engineering_coherence": _dim("engineering_coherence"),
        "presentation_quality": _dim("presentation_quality"),
        "not_visualized": (scores.get("semantic_identity") or {}).get(
            "not_visualized") or [],
        "note": ("three separated dimensions — never combined into one "
                 "score (R433 section 13)"),
    }


def _evolution_summary(evolution: Optional[Any]) -> Optional[list]:
    """R433 section 15 — the history rows (compact, request-loaded)."""
    if not evolution:
        return None
    rows = []
    for r in evolution:
        if not isinstance(r, dict):
            continue
        rows.append({
            "generation": r.get("generation"),
            "invention_id": r.get("invention_id"),
            "status": r.get("status"),
            "status_basis": r.get("status_basis"),
            "why": r.get("why"),
            "domain_family": r.get("domain_family"),
            "component_count": r.get("component_count"),
            "glb": r.get("glb"),
            "current": bool(r.get("current")),
        })
    return rows or None


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
        # R432: the domain layer — family, canonical spec, quality gates,
        # artifact identity, and the honest fallback label when the
        # generic diagram served instead of the domain form
        "domain_family": geometry_out.get("domain_family"),
        "geometry_spec": ("/api/run/{run}/geometry/GEOMETRY_SPEC.json"
                          if geometry_out.get("geometry_spec") else None),
        "quality_gates": _gate_summary(geometry_out.get("quality_gates")),
        "artifact_identity": _identity_summary(
            geometry_out.get("artifact_identity")),
        "fallback_basis": geometry_out.get("fallback_basis"),
        # R433: the three separated scores + the generation evolution
        # projection (history rows; per-gen GLBs load only on request)
        "scores": _scores_summary(geometry_out.get("scores")),
        "evolution": _evolution_summary(geometry_out.get("evolution")),
        "generation_id": geometry_out.get("generation_id"),
        "generation_count": geometry_out.get("generation_count"),
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
    renders = geometry_out.get("renders") or {}
    render_status = renders.get("status")
    visualization = {
        "viewer_required": ["orbit", "zoom", "pan", "reset", "wireframe", "clip"],
        "component_inspection": [
            {"from": "component name", "explain": ["function", "mechanism",
             "evidence", "simulation", "unknowns"]},
        ],
        "generation_models": geometry_out.get("generation_models") or [],
        "disclaimer": ep.conceptual_disclaimer(vis_class) if not is_engineering else None,
    }
    # R419 sections 5-6/16-17: the six presentation artifacts (hero/
    # section/exploded PNG+GLB) when the pinned Blender build ran. The
    # frontend gallery and the ZIP carry the SAME files — the CIO points
    # at them; it never fabricates one (absent = honestly absent).
    if render_status in ("OK", "RENDER_PARTIAL"):
        artifacts = renders.get("artifacts") or {}
        visualization["renders"] = {
            "status": render_status,
            "pipeline": renders.get("render_pipeline"),
            "pinned_blender": renders.get("pinned_blender"),
            "is_conceptual": renders.get("is_conceptual", not is_engineering),
            "hero_png": "/renders/hero.png" if "hero.png" in artifacts else None,
            "hero_glb": "/renders/hero.glb" if "hero.glb" in artifacts else None,
            "section_png": "/renders/section.png" if "section.png" in artifacts else None,
            "section_glb": "/renders/section.glb" if "section.glb" in artifacts else None,
            "exploded_png": "/renders/exploded.png" if "exploded.png" in artifacts else None,
            "exploded_glb": "/renders/exploded.glb" if "exploded.glb" in artifacts else None,
            "missing": renders.get("missing_artifacts") or [],
            "presentation_rule": (
                "presentation renders — the authoritative geometry is the "
                "CadQuery/OCCT GLB; section/exploded are disclosed variants"),
        }
    elif render_status:
        # typed honest absence (no Blender / timeout / failure) — the
        # interactive GLB contract is unaffected
        visualization["renders"] = {
            "status": render_status,
            "note": renders.get("note"),
            "presentation_rule": (
                "presentation renders unavailable on this run — the "
                "interactive 3D artifact is served from the authoritative "
                "geometry regardless"),
        }
    updated["visualization"] = visualization

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
