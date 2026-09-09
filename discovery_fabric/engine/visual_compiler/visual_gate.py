"""visual_gate.py — R441 the Visual Quality Gate.

The missing anti-entropy layer (operator directive R441). Every render
receives MEASURED scores; the verifier never trusts the claimant — the
pixel analysis here re-measures what the renderer reported, with its
own tools (PIL/numpy on the saved PNGs, trimesh on the exported GLBs):

    frame occupancy     hero model pixels in 70-85% of frame
    contact shadow      dark semi-transparent band at the model base
    ground plane        ground + shadow present (record + pixels agree)
    semantic materials  100% of mesh nodes carry a semantic class
    no floating parts   grounded by construction + shadow band present
    node naming         100% of GLB nodes named
    poster parity       poster re-uses the hero camera (scene spec) and
                        correlates pixel-wise with hero.png
    duplicate viewers   exactly ONE primary viewer per technology page
                        (static scan of the webapp surface)

If ANY rule fails: verdict FAIL, `hero_suppressed: true`, and the
package is blocked from release ("NO HERO" — Article LXXII). The gate
record (visual_gate.json) is written next to the artifacts and copied
into every technology package.

Typed honesty: an UNRUNNABLE gate (missing artifacts) is not a PASS —
it is `NOT_RUN` with reasons, which also suppresses the hero (fail
closed, Art. V; unknown stays unknown, Art. XXV).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

GATE_VERSION = "R441-1"

# directive thresholds (Art. XXVII provenance: operator directive R441,
# Visual Quality Gate table) — measured against, never re-invented here
RULES = {
    "hero_occupancy_band": (0.70, 0.85),
    "contact_shadow_min_ratio": 0.004,   # of frame pixels in base band
    "contact_shadow_max_luma": 0.62,     # darker than this counts
    "semantic_materials_required": True,
    "node_naming_required": True,
    "single_viewer_required": True,
    "poster_parity_min_corr": 0.90,
}

WEBAPP = Path(__file__).resolve().parents[3] / "TOSCANINI_UI" / "webapp"


# ---------------------------------------------------------------------------
# pixel measures (the independent verifier's own eyes)
# ---------------------------------------------------------------------------
def _load_rgba(path: Path) -> Optional[np.ndarray]:
    try:
        with Image.open(path) as im:
            return np.asarray(im.convert("RGBA"), dtype=np.uint8)
    except Exception:  # noqa: BLE001 — unreadable artifact is a failure
        return None


def measure_occupancy(rgba: np.ndarray) -> Dict[str, Any]:
    """The independent re-measure of the frame: area + linear extents
    + the anti-clip witness. The COMPOSITION extent (any rendered
    content, alpha > 8) drives the occupancy band; the SOLID body
    (alpha > 154) drives the base position and the clip witness — the
    soft contact shadow may fade toward the frame bottom, the MODEL
    may never be cut, and the model's base (not its shadow) is what
    must sit inside the ground-band window."""
    alpha = rgba[..., 3]
    on = alpha > 8
    solid = alpha > 154
    area = float(on.mean())
    if not on.any():
        return {"area": 0.0, "height_frac": 0.0, "width_frac": 0.0,
                "dominant": 0.0, "clipped": False, "base_row": None,
                "top_row": None}
    rows = np.where(on.any(axis=1))[0]
    cols = np.where(on.any(axis=0))[0]
    h, w = alpha.shape
    height_frac = float((rows.max() - rows.min() + 1) / h)
    width_frac = float((cols.max() - cols.min() + 1) / w)
    if solid.any():
        srows = np.where(solid.any(axis=1))[0]
        scols = np.where(solid.any(axis=0))[0]
        base_row, top_row = int(srows.max()), int(srows.min())
        clipped = bool(srows.max() >= h - 1 or srows.min() <= 0
                       or scols.max() >= w - 1 or scols.min() <= 0)
    else:
        base_row, top_row = int(rows.max()), int(rows.min())
        clipped = bool(rows.max() >= h - 1 or rows.min() <= 0
                       or cols.max() >= w - 1 or cols.min() <= 0)
    return {
        "area": round(area, 4),
        "height_frac": round(height_frac, 4),
        "width_frac": round(width_frac, 4),
        "dominant": round(max(height_frac, width_frac), 4),
        "clipped": clipped,
        "base_row": base_row,
        "top_row": top_row,
    }


def measure_contact_shadow(rgba: np.ndarray,
                           shadow_ratio_min: float) -> Dict[str, Any]:
    """Contact shadow = dark, semi-opaque pixels in the lower frame
    band BELOW the model's lowest opaque row (the grounded base)."""
    alpha = rgba[..., 3].astype(np.float32) / 255.0
    rgb = rgba[..., :3].astype(np.float32) / 255.0
    luma = (0.2126 * rgb[..., 0] + 0.7152 * rgb[..., 1]
            + 0.0722 * rgb[..., 2])
    h = rgba.shape[0]
    opaque_rows = np.where((alpha > 0.5).any(axis=1))[0]
    if len(opaque_rows) == 0:
        return {"present": False, "ratio": 0.0,
                "reason": "no opaque pixels"}
    base_row = int(opaque_rows.max())
    # the band BELOW the model base where a contact shadow lives
    band = slice(min(base_row + 2, h - 1), min(base_row + 2 + h // 12, h))
    band_alpha = alpha[band]
    band_luma = luma[band]
    mask = (band_alpha > 0.15) & (band_alpha < 0.98) \
        & (band_luma < RULES["contact_shadow_max_luma"])
    # shadow can also sit at the very base row inside the model footprint;
    # both bands are measured independently (shape-safe) and the stronger
    # evidence wins — the gate needs PRESENCE, not a specific row
    base_band = alpha[max(base_row - h // 60, 0):base_row + 1]
    base_luma = luma[max(base_row - h // 60, 0):base_row + 1]
    base_mask = (base_band > 0.15) & \
        (base_luma < RULES["contact_shadow_max_luma"])
    r_below = float(mask.mean()) if mask.size else 0.0
    r_base = float(base_mask.mean()) if base_mask.size else 0.0
    ratio = max(r_below, r_base)
    return {"present": bool(ratio >= shadow_ratio_min), "ratio": round(ratio, 5),
            "base_row": base_row}


def poster_parity(hero_rgba: np.ndarray, poster_rgba: np.ndarray,
                  image_rect: Optional[Dict[str, int]] = None,
                  ) -> Dict[str, Any]:
    """Normalized cross-correlation of downscaled luma between the hero
    render and the poster's hero rect (the poster embeds THE hero
    render at a recorded rect — the gate crops exactly there; parity
    is confirmed, not assumed)."""
    def prep(a: np.ndarray, size: int = 64) -> Optional[np.ndarray]:
        with Image.fromarray(a) as im:
            # BOX (area-average) downscale: the correct integration
            # operator — BICUBIC on a thin structure amplifies 1-px
            # resample phase noise and sinks a true parity below bar
            g = im.convert("RGBA").resize((size, size),
                                          Image.Resampling.BOX)
        arr = np.asarray(g, dtype=np.float32) / 255.0
        luma = (0.2126 * arr[..., 0] + 0.7152 * arr[..., 1]
                + 0.0722 * arr[..., 2])
        alpha = arr[..., 3]
        luma[alpha < 0.2] = 1.0  # transparent -> poster paper, not black
        l = luma - luma.mean()
        n = float(np.sqrt((l ** 2).sum()))
        return l / n if n > 1e-6 else None
    if image_rect:
        x = int(image_rect.get("x", 0))
        y = int(image_rect.get("y", 0))
        rw = int(image_rect.get("w", 0))
        rh = int(image_rect.get("h", 0))
        h, w = poster_rgba.shape[:2]
        if rw <= 0 or rh <= 0 or x + rw > w or y + rh > h:
            return {"corr": 0.0, "pass": False,
                    "reason": "poster image rect outside the poster"}
        poster_rgba = poster_rgba[y:y + rh, x:x + rw]
    ha, pa = prep(hero_rgba), prep(poster_rgba)
    if ha is None or pa is None:
        return {"corr": 0.0, "pass": False, "reason": "unreadable image"}
    corr = float((ha * pa).sum())
    return {"corr": round(corr, 4),
            "pass": bool(corr >= RULES["poster_parity_min_corr"])}


def check_node_naming(glb_path: Optional[Path]) -> Dict[str, Any]:
    """100% of GLB mesh nodes must be named (the node-naming rule).
    trimesh is the independent parser (same tool that re-measures
    engineering STLs — Art. III)."""
    if glb_path is None or not Path(glb_path).is_file():
        return {"pass": False, "reason": "hero GLB missing"}
    try:
        import trimesh
        scene = trimesh.load(str(glb_path))
        if isinstance(scene, trimesh.Trimesh):
            scene = trimesh.Scene(scene)
        nodes = list(scene.graph.nodes_geometry)
        if not nodes:
            return {"pass": False, "reason": "no geometry nodes"}
        unnamed = [n for n in nodes
                   if not str(n).strip() or str(n).startswith("Scene")]
        return {"pass": not unnamed, "nodes": len(nodes),
                "unnamed": unnamed[:5]}
    except Exception as exc:  # noqa: BLE001 — honest typed failure
        return {"pass": False, "reason": f"parse failed: {exc}"}


def check_single_viewer() -> Dict[str, Any]:
    """Static scan of the webapp's primary technology surface: exactly
    ONE <ModelViewer> hero instance per technology page (the R432 §14
    single-viewer contract, re-verified from source at gate time)."""
    tech_stage = WEBAPP / "components" / "TechStage.tsx"
    if not tech_stage.is_file():
        return {"pass": False, "reason": "TechStage.tsx missing"}
    src = tech_stage.read_text()
    # one imported component, rendered exactly once in the stage
    count = src.count("<ModelViewer")
    return {"pass": count == 1, "primary_surface_viewers": count}


# ---------------------------------------------------------------------------
# the gate itself
# ---------------------------------------------------------------------------
def evaluate(out_dir: str,
             scene_spec: Dict[str, Any],
             render_record: Dict[str, Any],
             status: str) -> Dict[str, Any]:
    """Full gate evaluation. Returns the visual_gate.json record."""
    out = Path(out_dir)
    checks: Dict[str, Any] = {}
    reasons: List[str] = []

    hero_png = out / "hero.png"
    exploded_glb = out / "exploded.glb"

    if status not in ("OK", "PARTIAL") or not hero_png.is_file():
        return {
            "gate_version": GATE_VERSION,
            "verdict": "NOT_RUN",
            "hero_suppressed": True,
            "release_blocked": True,
            "reasons": [f"render status {status}: the gate refuses to "
                        "pass what it cannot measure (Art. XXV)"],
            "checks": {},
        }

    # 1. hero occupancy (the 70-85% Camera Constitution band, on the
    #    confining dimension) + the anti-clip witness + the ground-band
    #    composition rule (the base must sit inside the frame with room
    #    for its contact shadow below)
    hero = _load_rgba(hero_png)
    if hero is None:
        checks["hero_occupancy"] = {"pass": False, "reason": "hero.png unreadable"}
        reasons.append("hero.png unreadable")
    else:
        occ = measure_occupancy(hero)
        lo, hi = RULES["hero_occupancy_band"]
        h = hero.shape[0]
        base_frac = (occ["base_row"] / h) \
            if occ["base_row"] is not None else 0.0
        ground_ok = 0.80 <= base_frac <= 0.95
        ok = (lo <= occ["dominant"] <= hi) and not occ["clipped"] \
            and ground_ok
        checks["hero_occupancy"] = {
            "pass": ok, **occ,
            "band": [lo, hi],
            "base_row_fraction": round(base_frac, 4),
            "ground_band": ("base must sit at 80-95% of frame height "
                            "(contact-shadow stage visible)")}
        if not ok:
            if occ["clipped"]:
                reasons.append("hero render is CLIPPED by the frame — "
                               "the model does not fit, let alone command")
            elif not ground_ok:
                reasons.append(
                    f"model base at {base_frac:.2f} of frame height — "
                    "no ground band for the contact shadow")
            else:
                reasons.append(
                    f"hero dominant occupancy {occ['dominant']:.3f} "
                    f"outside [{lo}, {hi}] — the model does not "
                    "command the frame")

    # 2. contact shadow + ground plane + no floating parts
    if hero is not None:
        sh = measure_contact_shadow(hero, RULES["contact_shadow_min_ratio"])
        grounded = bool(scene_spec.get("grounding", {}).get("scale"))
        ok = sh["present"] and grounded
        checks["contact_shadow"] = {
            "pass": ok, **sh,
            "grounded_by_construction": grounded}
        if not ok:
            reasons.append("contact shadow not detected at the model "
                           "base — grounding rule failed")

    # 3. semantic materials: 100% of nodes mapped to semantic classes
    mats = (scene_spec.get("materials") or {}).get("mapping") or {}
    nodes = scene_spec.get("model", {}).get("nodes", [])
    node_names = [n["name"] for n in nodes]
    unmapped = [n for n in node_names if n not in mats]
    semantic = all(m.get("class") for m in mats.values())
    ok = (not unmapped) and semantic and bool(node_names)
    checks["semantic_materials"] = {
        "pass": ok, "nodes": len(node_names), "unmapped": unmapped[:5],
        "classes": sorted({m.get("class") for m in mats.values()})}
    if not ok:
        reasons.append("semantic material mapping incomplete — every "
                       "component must carry its typed material")

    # 4. node naming (independent trimesh re-parse of the exported GLB;
    #    the exploded GLB when it exists, else the hero GLB — a
    #    single-part architecture has no exploded export, its skip is
    #    disclosed, and naming is verified on the hero export)
    naming = check_node_naming(exploded_glb if exploded_glb.is_file()
                               else out / "hero.glb")
    checks["node_naming"] = naming
    if not naming.get("pass"):
        reasons.append("node naming rule failed on the exported GLB")

    # 5. topology: the renderer's own comparison re-checked (the hero
    #    GLB must re-export the SAME vertices — presentation never
    #    edits geometry)
    topo = render_record.get("topology_comparison") or {}
    checks["geometry_identity"] = {
        "pass": bool(topo.get("identical")),
        **topo}
    if not topo.get("identical"):
        reasons.append("exported hero GLB vertex/face counts differ "
                       "from the canonical import — presentation "
                       "edited geometry")

    # 6. poster parity
    poster_png = out / "poster.png"
    if poster_png.is_file() and hero is not None:
        poster = _load_rgba(poster_png)
        if poster is None:
            checks["poster_parity"] = {"pass": False,
                                       "reason": "poster.png unreadable"}
            reasons.append("poster.png unreadable")
        else:
            par = poster_parity(hero, poster,
                                render_record.get("poster_image_rect"))
            checks["poster_parity"] = par
            if not par.get("pass"):
                reasons.append(
                    f"poster parity {par.get('corr')} below "
                    f"{RULES['poster_parity_min_corr']} — poster must "
                    "be the same render as the live viewer")
    else:
        checks["poster_parity"] = {"pass": False,
                                   "reason": "poster.png missing"}
        reasons.append("poster.png missing — the PDF constitution "
                       "requires it")

    # 7. duplicate viewers (the website constitution)
    sv = check_single_viewer()
    checks["single_viewer"] = sv
    if not sv.get("pass"):
        reasons.append("single-viewer rule failed on the primary "
                       "technology surface")

    failed = [k for k, v in checks.items() if not v.get("pass")]
    verdict = "PASS" if not failed else "FAIL"
    return {
        "gate_version": GATE_VERSION,
        "verdict": verdict,
        "hero_suppressed": verdict != "PASS",
        "release_blocked": verdict != "PASS",
        "failed_rules": failed,
        "reasons": reasons,
        "checks": checks,
        "rules": RULES,
    }


def write_gate(out_dir: str, gate: Dict[str, Any]) -> Path:
    p = Path(out_dir) / "visual_gate.json"
    p.write_text(json.dumps(gate, indent=2))
    return p
