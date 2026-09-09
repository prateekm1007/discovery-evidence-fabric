"""scene_builder.py — R441 canonical scene builder.

The Automatic Scene Builder (operator directive R441): every GLB enters

    GLB -> bounding box -> centering -> grounding -> [camera solve]
         -> HDRI -> material mapping -> shadow -> poster

This module is the Python half. It reads the authoritative GLB through
gltf_doc.walk_scene (the DIRECT glTF document walk — deterministic
canonical node names, spec-required accessor bounds; the R441
acceptance found live that loader-synthesized names are unstable, so
the scene identity comes from the document itself, never from a
loader's naming policy) and emits a DETERMINISTIC scene_spec.json:

  * parts: every mesh-bearing node — canonical name (the glTF name
    when present, else "part-NNN" in depth-first order — the same
    order three.js builds its graph), world bounds, naming provenance;
  * grounding: uniform scale normalization + translation that puts the
    model's X/Z center at the origin and its LOWEST point at y=0 — the
    structural "no floating parts" guarantee;
  * fit radius for lights/cameras/shadow plane.

Determinism: same GLB -> same scene_spec bytes (no clocks, no
randomness, rounded fixed-precision fields). The spec sha256 is
recorded in the render record; the gate re-derives and re-checks it —
the renderer cannot silently see a different scene than the solver
specified (Art. III).
"""
from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional

import numpy as np

from . import gltf_doc

# normalization target: the model's max dimension becomes VIEW_UNITS in
# the renderer's normalized space (mirrors the website viewer's
# scale-to-fit convention, ModelViewer.tsx FittedModel)
VIEW_UNITS = 5.0
# fit radius = half diagonal of the normalized bbox (drives lights,
# camera distances, shadow-plane extents) — derived, not tuned
_FIT_MARGIN = 1.02


def _round(v: float, nd: int = 6) -> float:
    return float(np.round(float(v), nd))


def inspect_glb(glb_path: str) -> Dict[str, Any]:
    """Independent inventory of the canonical GLB — the deterministic
    document walk (gltf_doc). This is the claim the renderer must
    match and the gate re-verifies (Art. III)."""
    w = gltf_doc.walk_scene(glb_path)
    return {
        "nodes": [
            {"name": p["name"],
             "named_in_gltf": p["named_in_gltf"],
             "extents": [_round(v) for v in
                         (np.array(p["max"]) - np.array(p["min"]))],
             "min": [_round(v) for v in p["min"]],
             "max": [_round(v) for v in p["max"]]}
            for p in w["parts"]],
        "min": [float(v) for v in w["min"]],
        "max": [float(v) for v in w["max"]],
        "center": [float(v) for v in w["center"]],
        "raw_size": [float(v) for v in w["raw_size"]],
        "min_y": float(w["min_y"]),
    }


def build_scene_spec(glb_path: str,
                     geometry_spec: Optional[Dict[str, Any]] = None,
                     material_mapping: Optional[Dict[str, Any]] = None,
                     ) -> Dict[str, Any]:
    """The canonical scene spec — deterministic bytes for a given GLB."""
    inv = inspect_glb(glb_path)
    raw_size = inv["raw_size"]
    max_dim = max(raw_size) or 1.0
    scale = VIEW_UNITS / max_dim
    # after grounding: X/Z centered at origin, min-Y at 0
    nz = [d * scale for d in raw_size]
    fit_radius = _round(_FIT_MARGIN *
                        0.5 * math.sqrt(nz[0] ** 2 + nz[1] ** 2 + nz[2] ** 2))
    spec: Dict[str, Any] = {
        "spec_version": "R441-2",
        "model": {
            "raw_size": [_round(v) for v in raw_size],
            "center": [_round(v) for v in inv["center"]],
            "min_y": _round(inv["min_y"]),
            "min": [_round(v) for v in inv["min"]],
            "max": [_round(v) for v in inv["max"]],
            "node_count": len(inv["nodes"]),
            "nodes": inv["nodes"],
        },
        "grounding": {
            "scale": _round(scale),
            "translate": [0.0, _round(-inv["min_y"] * scale), 0.0],
            "policy": ("uniform scale to "
                       f"{VIEW_UNITS} max-dim units; X/Z centered; "
                       "min-Y grounded at 0 (no floating parts)"),
        },
        "normalized_size": [_round(v) for v in nz],
        "grounding_fit_radius": fit_radius,
    }
    if material_mapping:
        spec["materials"] = material_mapping
    if geometry_spec:
        spec["canonical_spec_sha256_note"] = (
            "material classes resolved from the canonical geometry spec")
    return spec


def scene_spec_bytes(spec: Dict[str, Any]) -> bytes:
    """Canonical bytes (sorted keys, fixed separators) — the sha256 the
    render record and the gate both carry."""
    return json.dumps(spec, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")
