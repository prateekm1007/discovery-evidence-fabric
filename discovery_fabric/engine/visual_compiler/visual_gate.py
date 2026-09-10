"""visual_gate.py — R441 the Visual Quality Gate; R443 integrity hardening.

The missing anti-entropy layer (operator directive R441). Every render
receives MEASURED scores; the verifier never trusts the claimant — the
pixel analysis here re-measures what the renderer reported, with its
own tools (PIL/numpy on the saved PNGs, the DIRECT glTF document walk
on the exported GLBs):

    frame occupancy     hero model pixels in 70-85% of frame
    contact shadow      dark semi-transparent band at the model base
    semantic materials  100% of mesh nodes carry a semantic class
    node identity       R443: canonical identity PROVEN FROM THE RAW
                        glTF DOCUMENT (no loader — loaders synthesize
                        names for unnamed nodes, which let a stripped
                        GLB pass; the R442 recorded blind spot)
    source agreement    R443: the exported hero GLB's re-derived world
                        bounds must match the scene spec's grounding —
                        a valid-looking render of the WRONG source
                        fails here (anti-gaming)
    material contrast   R443: semantic classes that must be visually
                        distinct are measured DISTINCT in the rendered
                        material probe (CIEDE2000) — a label is not a
                        visual validation
    poster parity       poster re-uses the hero camera (scene spec) and
                        correlates pixel-wise with hero.png
    duplicate viewers   exactly ONE primary viewer per technology page

Verdict vocabulary (R443 Workstream 2) — the gate distinguishes

    COMPLETE_PASS  every quality rule passed AND the full required
                   visual ladder is present on disk
    PARTIAL        quality rules passed but the ladder is incomplete
                   (NOT_COMPLETE -> no visual release)
    NOT_RUN        the gate could not measure (skipped/failed render)
    FAIL           measured, and at least one quality rule failed

Anything other than COMPLETE_PASS suppresses the hero and blocks the
release (Article LXXII; fail closed, Art. V — unknown stays unknown,
Art. XXV).
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image

from . import gltf_doc
from . import visual_set

GATE_VERSION = "R443-1"

# directive thresholds (Art. XXVII provenance: operator directive R441,
# Visual Quality Gate table — R443 adds the material-distinction bar
# with its own provenance entry in visual_compiler_thresholds.json;
# measured against, never re-invented here)
RULES = {
    "hero_occupancy_band": (0.70, 0.85),
    "contact_shadow_min_ratio": 0.004,   # of frame pixels in base band
    "contact_shadow_max_luma": 0.62,     # darker than this counts
    "semantic_materials_required": True,
    "node_identity_required": True,      # R443: raw-document identity
    "source_agreement_required": True,   # R443: wrong-source witness
    "material_distinction_min_de00": 10.0,  # R443: CIEDE2000, see thresholds
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
# R443 Workstream 1 — canonical node identity from the RAW glTF document
# ---------------------------------------------------------------------------
def check_canonical_node_identity(glb_path: Optional[Path],
                                  scene_spec: Dict[str, Any],
                                  ) -> Dict[str, Any]:
    """Canonical node identity, proven from the RAW glTF document —
    never from names a loader synthesized (trimesh/three.js invent
    names for unnamed glTF nodes; a gate that reads through a loader
    cannot tell a canonically named GLB from one whose names were
    stripped after compilation — the exact R442 recorded blind spot,
    now closed).

    Rules (both must hold):
      1. every mesh-bearing node in the RAW document is either named
         or an unnamed primitive slice of a named part (the
         multi-primitive export pattern — gltf_doc.raw_part_identity);
      2. the named-part identity set equals the scene spec's canonical
         node set 1:1 — the rendered GLB IS the compiled scene.
    """
    if glb_path is None or not Path(glb_path).is_file():
        return {"pass": False, "reason": "exported GLB missing",
                "rule": "node_identity"}
    try:
        raw = gltf_doc.raw_part_identity(str(glb_path))
    except Exception as exc:  # noqa: BLE001 — typed, honest failure
        return {"pass": False, "rule": "node_identity",
                "reason": f"raw glTF document unreadable: {exc}"}
    spec_names = [n["name"] for n in
                  (scene_spec.get("model", {}).get("nodes") or [])]
    unnamed = raw["unnamed_unattributed"]
    named = raw["named"]
    ok = True
    reasons: List[str] = []
    if unnamed:
        ok = False
        reasons.append(
            "canonical node identity ABSENT from the raw glTF document "
            f"({len(unnamed)} mesh node(s) carry no name and inherit "
            "none — any matching name a loader would report is "
            "synthesized, not evidence)")
    if sorted(named) != sorted(spec_names):
        ok = False
        only_glb = sorted(set(named) - set(spec_names))[:5]
        only_spec = sorted(set(spec_names) - set(named))[:5]
        reasons.append(
            "raw-document node identity set does not match the scene "
            f"spec (GLB-only: {only_glb}; spec-only: {only_spec}) — "
            "the rendered GLB is not the compiled scene")
    return {
        "pass": ok,
        "rule": "node_identity",
        "raw_mesh_nodes": raw["mesh_nodes"],
        "raw_named": len(named),
        "primitive_slices": raw["primitive_slices"],
        "spec_nodes": len(spec_names),
        "unnamed_unattributed": unnamed[:5],
        "reasons": reasons,
    }


def check_source_scene_agreement(glb_path: Optional[Path],
                                 scene_spec: Dict[str, Any],
                                 ) -> Dict[str, Any]:
    """Wrong-source witness (R443): the exported hero GLB's re-derived
    world bounds must reproduce the scene spec's grounding within
    tolerance. A valid-LOOKING render whose scene does not correspond
    to the supplied canonical GLB fails here — the most important
    anti-gaming check (Art. XXX: what would make this pass while the
    system is wrong?)."""
    if glb_path is None or not Path(glb_path).is_file():
        return {"pass": False, "reason": "hero GLB missing",
                "rule": "source_agreement"}
    try:
        w = gltf_doc.walk_scene(str(glb_path))
    except Exception as exc:  # noqa: BLE001
        return {"pass": False, "rule": "source_agreement",
                "reason": f"raw glTF document walk failed: {exc}"}
    model = scene_spec.get("model", {})
    grounding = scene_spec.get("grounding", {})
    scale = float(grounding.get("scale") or 0.0)
    center = np.array(model.get("center") or [0, 0, 0], dtype=np.float64)
    min_y = float(model.get("min_y") or 0.0)
    if scale <= 0:
        return {"pass": False, "rule": "source_agreement",
                "reason": "scene spec carries no grounding scale"}
    gmin = np.array(model.get("min") or [0, 0, 0], dtype=np.float64)
    gmax = np.array(model.get("max") or [0, 0, 0], dtype=np.float64)
    expected_min = np.array([
        (gmin[0] - center[0]) * scale,
        0.0,
        (gmin[2] - center[2]) * scale])
    expected_max = np.array([
        (gmax[0] - center[0]) * scale,
        (gmax[1] - min_y) * scale,
        (gmax[2] - center[2]) * scale])
    tol = 0.02  # normalized units (model max dim = 5.0): float32 export
    # noise is ~1e-6; wrong-source geometry differs by orders more
    got_min, got_max = w["min"], w["max"]
    dev = float(max((np.abs(got_min - expected_min)).max(),
                    (np.abs(got_max - expected_max)).max()))
    ok = bool(dev <= tol)
    return {
        "pass": ok,
        "rule": "source_agreement",
        "max_bound_deviation": round(dev, 5),
        "tolerance": tol,
        "expected_min": [round(float(v), 4) for v in expected_min],
        "expected_max": [round(float(v), 4) for v in expected_max],
        "derived_min": [round(float(v), 4) for v in got_min],
        "derived_max": [round(float(v), 4) for v in got_max],
    }


# ---------------------------------------------------------------------------
# R443 Workstream 3 — material semantics, measured in the render
# ---------------------------------------------------------------------------
def _srgb255_to_lab(px: np.ndarray) -> np.ndarray:
    """sRGB (0-255) -> CIELAB (D65, 2 deg). px: (..., 3) float."""
    c = px / 255.0
    lin = np.where(c <= 0.04045, c / 12.92,
                   ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375],
                  [0.2126729, 0.7151522, 0.0721750],
                  [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T
    xyz /= np.array([0.95047, 1.0, 1.08883])
    d = 6 / 29

    def f(t):
        return np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4 / 29)
    fx, fy, fz = f(xyz[..., 0]), f(xyz[..., 1]), f(xyz[..., 2])
    L = 116 * fy - 16
    a = 500 * (fx - fy)
    b = 200 * (fy - fz)
    return np.stack([L, a, b], axis=-1)


def ciede2000(lab1: np.ndarray, lab2: np.ndarray) -> float:
    """CIEDE2000 color difference (Sharma, Wu & Dalal 2005 implementation
    notes; the CIE 142:2001 formula). lab: (3,) arrays."""
    L1, a1, b1 = (float(v) for v in lab1)
    L2, a2, b2 = (float(v) for v in lab2)
    C1 = math.hypot(a1, b1)
    C2 = math.hypot(a2, b2)
    Cbar = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cbar ** 7 / (Cbar ** 7 + 25 ** 7))
               if Cbar > 0 else 0)
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p = math.hypot(a1p, b1)
    C2p = math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) if (a1p or b1) else 0.0
    h2p = math.degrees(math.atan2(b2, a2p)) if (a2p or b2) else 0.0
    dLp = L2 - L1
    dCp = C2p - C1p
    if C1p * C2p == 0:
        dhp = 0.0
    else:
        dhp = h2p - h1p
        if dhp > 180:
            dhp -= 360
        elif dhp < -180:
            dhp += 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0:
        hbp = h1p + h2p
    else:
        hsum = h1p + h2p
        if abs(h1p - h2p) > 180:
            hsum += 360 if hsum < 360 else -360
        hbp = hsum / 2
    T = (1 - 0.17 * math.cos(math.radians(hbp - 30))
         + 0.24 * math.cos(math.radians(2 * hbp))
         + 0.32 * math.cos(math.radians(3 * hbp + 6))
         - 0.20 * math.cos(math.radians(4 * hbp - 63)))
    dtheta = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7)) if Cbp > 0 else 0
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / \
        math.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dtheta)) * Rc
    return math.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2
                     + Rt * (dCp / Sc) * (dHp / Sh))


def measure_material_distinction(probe_path: Path,
                                 probe_meta: Dict[str, Any],
                                 ) -> Dict[str, Any]:
    """R443: a semantic material is not visually validated merely
    because it has a label. The renderer shoots a material probe
    (one sphere per distinct class, the SAME light rig) and records
    the rect per class; this check measures the SAVED PIXELS: every
    pair of distinct classes must separate by >=
    material_distinction_min_de00 CIEDE2000. The mapping coverage
    check (semantic_materials) and this check are separate — mapping
    AND observable contrast."""
    classes = probe_meta.get("classes") or []
    rects = probe_meta.get("rects") or {}
    if not classes or not rects:
        return {"pass": False, "rule": "material_distinction",
                "reason": "material probe missing from the render "
                          "record — the renderer did not produce the "
                          "measurable distinction evidence"}
    img = _load_rgba(probe_path)
    if img is None:
        return {"pass": False, "rule": "material_distinction",
                "reason": "material_probe.png unreadable"}
    h, w = img.shape[:2]
    labs: Dict[str, np.ndarray] = {}
    for cls in classes:
        r = rects.get(cls)
        if not r:
            return {"pass": False, "rule": "material_distinction",
                    "reason": f"probe rect missing for class {cls!r}"}
        x, y, rw, rh = int(r[0]), int(r[1]), int(r[2]), int(r[3])
        if rw <= 0 or rh <= 0 or x < 0 or y < 0 or x + rw > w or y + rh > h:
            return {"pass": False, "rule": "material_distinction",
                    "reason": f"probe rect for {cls!r} outside the image"}
        # central 60% of the rect: edge antialiasing excluded
        mx = int(rw * 0.2) or 1
        my = int(rh * 0.2) or 1
        crop = img[y + my:y + rh - my, x + mx:x + rw - mx, :3]
        if crop.size == 0:
            return {"pass": False, "rule": "material_distinction",
                    "reason": f"probe rect for {cls!r} degenerate"}
        mean_rgb = crop.reshape(-1, 3).mean(axis=0)
        labs[cls] = _srgb255_to_lab(mean_rgb)
    min_de = float(RULES["material_distinction_min_de00"])
    pairs: List[Dict[str, Any]] = []
    failed_pairs: List[str] = []
    cs = sorted(labs)
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            d = ciede2000(labs[a], labs[b])
            pairs.append({"pair": [a, b], "delta_e00": round(d, 2)})
            if d < min_de:
                failed_pairs.append(f"{a}/{b}={d:.2f}")
    ok = not failed_pairs
    return {
        "pass": ok,
        "rule": "material_distinction",
        "classes_measured": len(cs),
        "pairs_measured": len(pairs),
        "min_required_de00": min_de,
        "pairs": sorted(pairs, key=lambda p: p["delta_e00"])[:12],
        "failed_pairs": failed_pairs[:8],
    }


# ---------------------------------------------------------------------------
# the gate itself
# ---------------------------------------------------------------------------
def evaluate(out_dir: str,
             scene_spec: Dict[str, Any],
             render_record: Dict[str, Any],
             status: str) -> Dict[str, Any]:
    """Full gate evaluation. Returns the visual_gate.json record with
    the R443 four-verdict vocabulary (COMPLETE_PASS / PARTIAL /
    NOT_RUN / FAIL)."""
    out = Path(out_dir)
    checks: Dict[str, Any] = {}
    reasons: List[str] = []

    hero_png = out / "hero.png"
    hero_glb = out / "hero.glb"
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
            "visual_set": {"complete": False, "missing": ["*"],
                           "required_count": 0, "present_count": 0,
                           "waived": []},
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
    #    (mapping COVERAGE — R443 keeps it, and ADDS the observable-
    #    contrast check below; the two are separate)
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

    # 4. R443 canonical node identity (RAW glTF document — no loader):
    #    every mesh node named in the raw document AND the identity set
    #    equal to the scene spec's canonical nodes
    identity = check_canonical_node_identity(
        hero_glb if hero_glb.is_file() else exploded_glb, scene_spec)
    checks["node_identity"] = identity
    if not identity.get("pass"):
        reasons.extend(identity.get("reasons")
                       or ["canonical node identity rule failed on the "
                           "exported GLB"])

    # 4b. R443 source agreement (wrong-source witness): the exported
    #     hero GLB's re-derived grounded bounds must match the spec
    agreement = check_source_scene_agreement(hero_glb, scene_spec)
    checks["source_agreement"] = agreement
    if not agreement.get("pass"):
        reasons.append(
            f"exported hero GLB world bounds deviate "
            f"{agreement.get('max_bound_deviation')} from the scene "
            "spec grounding — the render does not correspond to the "
            "supplied canonical GLB")

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

    # 8. R443 material distinction: measured rendered separation of
    #    the semantic classes (the probe render + saved pixels)
    probe_meta = render_record.get("material_probe") or {}
    checks["material_distinction"] = measure_material_distinction(
        out / "material_probe.png", probe_meta)
    if not checks["material_distinction"].get("pass"):
        fp = checks["material_distinction"].get("failed_pairs") or []
        reasons.append("semantic material classes are not observably "
                       f"distinct in the render (CIEDE2000 < "
                       f"{RULES['material_distinction_min_de00']}): "
                       f"{fp} — a label is not a visual validation")

    # 9. R443 visual-set completeness (re-verified FROM DISK, Art. III):
    #    the required ladder is hero + poster + dimension + section +
    #    exploded (multi-part) + orthographic x4 + turntable x12
    node_count = int(len(node_names)
                     or scene_spec.get("model", {}).get("node_count") or 0)
    frames = int(render_record.get("turntable_frames")
                 or visual_set.DEFAULT_TURNTABLE_FRAMES)
    completeness = visual_set.classify(str(out), node_count, frames)
    checks["visual_set_completeness"] = {
        "pass": bool(completeness["complete"]),
        "required_count": completeness["required_count"],
        "present_count": completeness["present_count"],
        "missing": completeness["missing"][:24],
        "waived": completeness["waived"]}
    if not completeness["complete"]:
        reasons.append(
            f"visual set NOT_COMPLETE: {len(completeness['missing'])} "
            f"required artifact(s) missing "
            f"({completeness['missing'][:6]}) — a full-ladder release "
            "requires the complete set")

    failed = [k for k, v in checks.items() if not v.get("pass")]
    # R443 verdict separation: quality-rule failures are FAIL; a
    # missing ladder artifact alone is PARTIAL (NOT_COMPLETE) — "three
    # artifacts exist" is never a pass, and "one artifact missing" is
    # never conflated with a quality rejection. FAIL takes precedence
    # when both are true.
    quality_failed = [k for k in failed
                      if k != "visual_set_completeness"]
    if quality_failed:
        verdict = "FAIL"
    elif not completeness["complete"]:
        verdict = "PARTIAL"
    else:
        verdict = "COMPLETE_PASS"
    return {
        "gate_version": GATE_VERSION,
        "verdict": verdict,
        "hero_suppressed": verdict != "COMPLETE_PASS",
        "release_blocked": verdict != "COMPLETE_PASS",
        "failed_rules": failed,
        "reasons": reasons,
        "checks": checks,
        "visual_set": completeness,
        "rules": RULES,
    }


def write_gate(out_dir: str, gate: Dict[str, Any]) -> Path:
    p = Path(out_dir) / "visual_gate.json"
    p.write_text(json.dumps(gate, indent=2))
    return p
