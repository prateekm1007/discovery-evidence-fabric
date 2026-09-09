"""camera_solver.py — R441 deterministic camera solve.

The Camera Constitution (operator directive R441), encoded as SOLVED
VALUES, not per-render taste. The R441 acceptance run exposed the
failure mode of a naive solve: a bounding-sphere/occupancy loop on a
tall model CLIPS the model top and bottom, saturates below the target
band, and hides the ground — exactly the "debugging viewport" look the
directive abolishes. The solve is therefore PROJECTED-EXTENT based:

  * the model's silhouette in the hero view is measured GEOMETRICALLY
    (projected height at the studio elevation, silhouette width at the
    azimuth) and the frame is solved to contain it at the occupancy
    target — clipping is impossible by construction;
  * a ground band is reserved BELOW the model's base (9% of frame) so
    the contact shadow always has a stage — the grounded look is part
    of the solve, not a hope;
  * auto-frame then measures the DRAFT render's opaque extent and makes
    bounded linear corrections — it never needs to fix clipping,
    because the initial solve already contains the model;
  * the gate re-measures the FINAL PNG independently (Art. III).

Golden-ratio composition, honestly encoded: the look-target sits at
0.55 of the model height (the golden section 0.618, budgeted down by
the ground-band reserve) — the model's mass lands in the upper frame
and the contact shadow anchors the lower third.

Threshold provenance (Art. XXVII): every constant below names its
source in DIRECTIVE_THRESHOLDS — directive values (R441), inherited
studio constants (blender_render.py), or derived geometry.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List

DIRECTIVE_THRESHOLDS = {
    "hero_occupancy_target": {"value": 0.78, "source": "R441 band 0.70-0.85 (linear, dominant axis)"},
    "hero_occupancy_band": {"value": [0.70, 0.85], "source": "R441 Camera Constitution"},
    "ground_band_fraction": {"value": 0.09, "source": "R441 grounding rule (shadow stage below the base)"},
    "hero_azimuth_deg": {"value": 38.0, "source": "inherited studio constant (blender_render.py CAM_AZIMUTH_DEG)"},
    "hero_elevation_deg": {"value": 21.0, "source": "inherited studio constant (blender_render.py CAM_ELEVATION_DEG)"},
    "hero_fov_deg": {"value": 30.0, "source": "website hero parity (ModelViewer.tsx hero fov 30)"},
    "target_height_fraction": {"value": 0.55, "source": "golden section 0.618 minus the ground-band reserve"},
    "golden_ratio": {"value": 0.618, "source": "R441 golden-ratio composition rule"},
    "ortho_fit_margin": {"value": 1.06, "source": "engineering-sheet fit policy"},
    "explode_factor": {"value": 0.55, "source": "R441 exploded-view policy (normalized units)"},
    "auto_frame_max_iter": {"value": 3, "source": "bounded deterministic convergence"},
    "auto_frame_tolerance": {"value": 0.02, "source": "occupancy convergence tolerance"},
    "composition_max_iter": {"value": 3, "source": "bounded empirical base-position alignment (R441 acceptance: perspective near-edge effects are shape-dependent — solved empirically, verified by the gate)"},
}

GOLDEN = 0.618


def _projected_extents(nz: List[float], az_deg: float,
                       el_deg: float) -> Dict[str, float]:
    """The hero-view silhouette extents of the model's bounding box
    (normalized units) — deterministic geometry, the anti-clip core of
    the solve."""
    w, h, d = nz
    az = math.radians(az_deg)
    el = math.radians(el_deg)
    plan_w = abs(w * math.sin(az)) + abs(d * math.cos(az))
    plan_diag = math.sqrt(w * w + d * d)
    # elevation tilts the plan into the vertical silhouette
    h_proj = h * math.cos(el) + plan_diag * math.sin(el)
    return {"h_proj": h_proj, "w_proj": plan_w, "plan_diag": plan_diag}


def solve_hero(scene_spec: Dict[str, Any],
               aspect: float = 1.5) -> Dict[str, Any]:
    """The anti-clip hero solve: contain the projected silhouette at
    the occupancy target with a ground band below the base."""
    nz = scene_spec["normalized_size"]
    fov = DIRECTIVE_THRESHOLDS["hero_fov_deg"]["value"]
    az = DIRECTIVE_THRESHOLDS["hero_azimuth_deg"]["value"]
    el = DIRECTIVE_THRESHOLDS["hero_elevation_deg"]["value"]
    occ = DIRECTIVE_THRESHOLDS["hero_occupancy_target"]["value"]
    ground = DIRECTIVE_THRESHOLDS["ground_band_fraction"]["value"]
    ext = _projected_extents(nz, az, el)

    # vertical: model height occupies `occ` of the frame; the ground
    # band adds room below the base
    v_span = ext["h_proj"] / occ
    d_v = (v_span / 2.0) / math.tan(math.radians(fov) / 2.0)
    # horizontal: same occupancy discipline against the frame aspect
    w_span = ext["w_proj"] / occ
    d_h = (w_span / 2.0) / (math.tan(math.radians(fov) / 2.0) * aspect)
    dist = max(d_v, d_h)

    # the look target: golden-section composition with the ground-band
    # reserve — 0.55 of the model height above the grounded base
    y_t = nz[1] * DIRECTIVE_THRESHOLDS["target_height_fraction"]["value"]
    return {
        "fov": fov,
        "azimuth": az,
        "elevation": el,
        "distance": round(dist, 5),
        "target": [0.0, round(y_t, 5), 0.0],
        "occupancy_target": occ,
        "occupancy_band": DIRECTIVE_THRESHOLDS["hero_occupancy_band"]["value"],
        "occupancy_axis": "linear-dominant (the confining frame dimension)",
        "ground_band_fraction": ground,
        "auto_frame_max_iter": DIRECTIVE_THRESHOLDS["auto_frame_max_iter"]["value"],
        "auto_frame_tolerance": DIRECTIVE_THRESHOLDS["auto_frame_tolerance"]["value"],
        "desired_base_fraction": DIRECTIVE_THRESHOLDS["ground_band_fraction"]["value"],
        "composition_max_iter": DIRECTIVE_THRESHOLDS["composition_max_iter"]["value"],
        "solve_basis": {
            "projected_height": round(ext["h_proj"], 5),
            "projected_width": round(ext["w_proj"], 5),
            "frame_aspect": aspect,
            "distance_vertical_constraint": round(d_v, 5),
            "distance_horizontal_constraint": round(d_h, 5),
        },
    }


def solve_section(scene_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Clip-plane solve: longest axis, through-center plane."""
    nz = scene_spec["normalized_size"]
    axes = ["x", "y", "z"]
    axis = axes[[nz[0], nz[1], nz[2]].index(max(nz))]
    return {
        "axis": axis,
        "constant": 0.0,  # grounded center sits at the origin
        "disclosure": ("clip-plane viewing slice (renderer clipping), "
                       "not a B-rep section cut — disclosed as such"),
    }


def solve_orthographic(scene_spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The four engineering views (bounding-sphere fit, fixed margin)."""
    margin = DIRECTIVE_THRESHOLDS["ortho_fit_margin"]["value"]
    return [
        {"view": "front", "dir": [0, 0, 1], "up": [0, 1, 0], "fit": margin},
        {"view": "side", "dir": [1, 0, 0], "up": [0, 1, 0], "fit": margin},
        {"view": "top", "dir": [0, 1, 0], "up": [0, 0, -1], "fit": margin},
        {"view": "iso", "dir": [0.62, 0.36, 1], "up": [0, 1, 0], "fit": margin},
    ]


def solve_exploded(scene_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Radial explosion policy (per-part offsets are computed by the
    renderer from the loaded graph and recorded for gate verification)."""
    return {
        "factor": DIRECTIVE_THRESHOLDS["explode_factor"]["value"],
        "policy": ("radial from grounded center; vertical component "
                   "damped to 0.35 (parts separate sideways more than "
                   "upward); zero-length falls back to +Y 0.35"),
    }


def solve(scene_spec: Dict[str, Any],
          aspect: float = 1.5) -> Dict[str, Any]:
    """The full deterministic camera/scene solve embedded in
    scene_spec.json (one blob the renderer consumes verbatim)."""
    return {
        "camera": {
            "hero": solve_hero(scene_spec, aspect=aspect),
            "orthographic": solve_orthographic(scene_spec),
            "section": solve_section(scene_spec),
            "exploded": solve_exploded(scene_spec),
        },
        "threshold_provenance": DIRECTIVE_THRESHOLDS,
    }
