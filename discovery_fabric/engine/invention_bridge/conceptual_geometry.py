"""Conceptual geometry builders — SYSTEM_3D / CONCEPTUAL_3D / PROCESS_3D.

Builds an inspectable conceptual architecture visualization with CadQuery/OCCT
(the engine's geometry authority) and exports it as a named-node GLB.

HONESTY RULES (binding):
  * Abstract presentation units only — never mm, never engineering dimensions.
  * Node names are CANONICAL COMPONENT IDS in the stable vocabulary (R447);
    the recorded subsystem text survives verbatim as each part's `label`
    so the viewer's component-inspection panel can explain each component
    from the CIO (name == the GLB node id; label == the human text).
  * Deterministic: identical run state -> identical geometry -> identical hash.
  * key_dimensions reports topology only (component count, adjacency);
    it must never carry volume/diameter/wall fields (guarded in epistemics).

R447 — THE NODE-IDENTITY CLOSURE (the Case B defect fix):
  three.js's GLTFLoader sanitizes every node name it loads
  (PropertyBinding.sanitizeNodeName: whitespace -> '_', the characters
  '[', ']', '.', ':', '/' removed; createUniqueName then suffixes
  post-sanitize collisions). The webapp viewer, the Visual Compiler's
  renderer, and the exported hero GLB ALL pass through that loader, so
  a node name outside the sanitize-stable vocabulary can never survive
  to any three.js surface. The R446-HF Case B gate FAIL
  (node_identity + geometry_identity) was exactly that divergence:
  '[01] load path / structural backbone' was authored as the canonical
  identity but arrived at the hero GLB as
  '01_load_path__structural_backbone'. The engineering path's
  snake_case ids were already inside the closure; this module's
  human-readable names were not. The fix is upstream authoring (never
  a gate exception, never Coder-2 tolerance): `name` is derived by ONE
  canonicalizer into the stable vocabulary, `label` keeps the human
  text, and the identity set is pre-unique so the loader's collision
  suffixing can never fire. Closure proof: every emitted id contains
  only [0-9A-Za-z_] with no leading/trailing underscore, so applying
  the three.js sanitize rule to it is the identity function (tested
  adversarially in tests/test_r447_geometry_identity_join.py).
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Any, Dict, List, Optional, Set, Tuple

import cadquery as cq
import trimesh

from .coloring import apply_gltf_yup, set_uniform_color

# Palette: warm/terracotta editorial direction (matches the product chrome)
PALETTE = {
    "substrate": (168, 98, 66, 255),      # terracotta
    "sensing": (214, 148, 90, 255),        # warm sand
    "compute": (120, 82, 60, 255),         # umber
    "transduction": (224, 172, 118, 255),  # pale terracotta
    "storage": (152, 108, 76, 255),        # clay
    "interface": (96, 70, 52, 255),        # dark umber
    "conduit_data": (198, 140, 96, 255),   # data flow
    "conduit_power": (232, 195, 148, 255), # control flow
    "default": (160, 110, 78, 255),
}

# Abstract layout units — explicitly NOT engineering dimensions
U = 1.0
BLOCK_H = 1.0 * U
SUBSTRATE_W = 10.0 * U
SUBSTRATE_D = 6.0 * U
SUBSTRATE_T = 0.35 * U

# R447: the stable-vocabulary canonicalizer. The emitted id contains
# only ASCII alphanumerics and single interior underscores — a strict
# subset of the three.js sanitize-fixed set, so the id survives
# GLTFLoader -> scene -> GLTFExporter -> gate -> webapp viewer
# UNCHANGED (the closure is proven by construction and tested).
_NON_STABLE = re.compile(r"[^0-9A-Za-z_]+")


def stable_node_id(label: str) -> str:
    """Canonical component id from human-readable text — ONE rule,
    deterministic, closed under the three.js node-name sanitizer.

    Every character outside [0-9A-Za-z_] becomes an underscore; all
    underscore runs collapse to one; edges are trimmed; an empty
    result falls back to 'part'. Uniqueness within one scene is
    enforced by the caller-side ``_UniqueId`` helper (the loader's
    collision suffixing must never fire on authored ids — a suffix
    would be a SECOND name mutation).
    """
    s = _NON_STABLE.sub("_", label or "")
    s = re.sub(r"_+", "_", s).strip("_")
    return s or "part"


class _UniqueId:
    """Per-scene unique id allocation (deterministic _2/_3 suffixes).

    three.js createUniqueName appends _1, _2... when two names
    collide AFTER sanitization; an authored collision would therefore
    mutate a third surface. Allocation here keeps the authored set
    injective so that path is unreachable."""

    def __init__(self) -> None:
        self._used: Set[str] = set()

    def __call__(self, label: str) -> str:
        base = stable_node_id(label)
        sid, k = base, 1
        while sid in self._used:
            k += 1
            sid = f"{base}_{k}"
        self._used.add(sid)
        return sid


def _tessellate(shape: cq.Workplane) -> Dict[str, Any]:
    """Tessellate a CadQuery shape into trimesh constructor kwargs."""
    verts, tris = shape.val().tessellate(0.08)
    return {
        "vertices": [(v.x, v.y, v.z) for v in verts],
        "faces": [list(t) for t in tris],
        "process": False,
    }


def _add(scene: trimesh.Scene, shape: cq.Workplane, node: str, color) -> None:
    mesh = trimesh.Trimesh(**_tessellate(shape))
    # R419: vertex colors, not face_colors — trimesh's face-color path
    # uses scipy.grouping at use time and died on the production image
    # ("No module named 'scipy'"); see coloring.py for the measured matrix.
    set_uniform_color(mesh, color)
    # R419: canonical glTF Y-up orientation (was: raw Z-up exported as a
    # wall in every glTF consumer — see coloring.py).
    apply_gltf_yup(mesh)
    scene.add_geometry(mesh, node_name=node, geom_name=node)


def _type_for(name: str) -> str:
    low = name.lower()
    if any(k in low for k in ("sensor", "characterization", "iot", "monitor", "meter")):
        return "sensing"
    if any(k in low for k in ("optimi", "control", "algorithm", "compute", " ai", "ai-", "governor", "model")):
        return "compute"
    if any(k in low for k in ("transduc", "conversion", "convert", "piezo", "thermo", "inductive", "harvest", "photovolta", "pv")):
        return "transduction"
    if any(k in low for k in ("storage", "buffer", "battery", "reservoir")):
        return "storage"
    if any(k in low for k in ("load", "interface", "grid", "output", "export")):
        return "interface"
    return "default"


def _block_shape(kind: str, w: float, d: float, h: float) -> cq.Workplane:
    """Typed shapes make the architecture legible at a glance."""
    if kind == "sensing":
        return cq.Workplane("XY").box(w, d, h * 0.45, centered=(True, True, False))
    if kind == "compute":
        return cq.Workplane("XY").box(w * 0.8, d * 0.8, h * 1.6, centered=(True, True, False))
    if kind == "transduction":
        return cq.Workplane("XY").polygon(3, w).extrude(h)
    if kind == "storage":
        return cq.Workplane("XY").circle(min(w, d) * 0.42).extrude(h * 1.2)
    return cq.Workplane("XY").box(w, d, h, centered=(True, True, False))


def _beam(p1: Tuple[float, float, float], p2: Tuple[float, float, float],
          thickness: float) -> cq.Workplane:
    """A beam connecting two points (robust for any direction)."""
    dx, dy, dz = (p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2])
    length = math.sqrt(dx * dx + dy * dy + dz * dz)
    if length <= 1e-9:
        return cq.Workplane("XY").box(1e-6, thickness, thickness)
    beam = cq.Workplane("XY").box(length, thickness, thickness)  # along X, centered
    # orient: first rotate about Y for dz, then about Z for dy
    angle_y = math.degrees(math.atan2(dz, dx))
    beam = beam.rotate((0, 0, 0), (0, 1, 0), angle_y)
    horiz = math.sqrt(dx * dx + dz * dz)
    if abs(dy) > 1e-9 and horiz > 1e-9:
        angle_z = math.degrees(math.atan2(dy, horiz))
        beam = beam.rotate((0, 0, 0), (0, 0, 1), -angle_z)
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2, (p1[2] + p2[2]) / 2)
    return beam.translate(mid)


def build_system_architecture(
    subsystems: List[str],
    intervention_site: str = "",
) -> Dict[str, Any]:
    """Build a SYSTEM_3D conceptual architecture on a substrate platform.

    Layout: the physical substrate (intervention site, e.g. 'solar panel') as a
    flat platform; subsystems as typed blocks along the +X flow axis; data
    conduits connecting consecutive subsystems; control conduits from the
    compute/optimization core to every other subsystem. All units abstract.
    """
    subsystems = [s for s in subsystems if s] or ["unspecified subsystem"]
    scene = trimesh.Scene()
    parts: List[Dict[str, Any]] = []
    n = len(subsystems)

    # --- substrate platform (the physical intervention site) ---------------
    substrate = cq.Workplane("XY").box(
        SUBSTRATE_W, SUBSTRATE_D, SUBSTRATE_T, centered=(True, True, False)
    )
    uid = _UniqueId()
    substrate_label = "substrate: " + (intervention_site or "intervention site")
    substrate_name = uid(substrate_label)
    _add(scene, substrate, substrate_name, PALETTE["substrate"])
    parts.append({"name": substrate_name, "label": substrate_label,
                  "type": "substrate",
                  "role": "physical intervention site (schematic form — no engineering dimensions)"})

    # --- subsystem blocks along the flow axis -------------------------------
    span = SUBSTRATE_W * 0.78
    step = span / max(1, n)
    block_w = min(step * 0.62, 1.6 * U)
    block_d = min(SUBSTRATE_D * 0.30, 1.2 * U)
    x0 = -span / 2 + step / 2

    centers = []
    for i, name in enumerate(subsystems):
        kind = _type_for(name)
        shape = _block_shape(kind, block_w, block_d, BLOCK_H)
        x = x0 + i * step
        z = SUBSTRATE_T + (0.0 if kind in ("sensing", "transduction") else 0.25 * U)
        shape = shape.translate((x, 0.0, z))
        node = uid(f"[{i+1:02d}] {name}")
        _add(scene, shape, node, PALETTE.get(kind, PALETTE["default"]))
        centers.append((x, z, node, kind))
        parts.append({
            "name": node,
            "label": f"[{i+1:02d}] {name}",
            "type": kind,
            "role": "recorded subsystem (conceptual form — no engineering dimensions)",
            "subsystem_index": i + 1,
        })

    # --- data conduits: consecutive subsystems -------------------------------
    for i in range(len(centers) - 1):
        x1, z1, _, _ = centers[i]
        x2, z2, _, _ = centers[i + 1]
        p1 = (x1 + block_w * 0.35, 0.95 * U, z1 + BLOCK_H * 0.6)
        p2 = (x2 - block_w * 0.35, 0.95 * U, z2 + BLOCK_H * 0.6)
        flow_label = f"flow {i+1} -> {i+2}"
        node = uid(flow_label)
        _add(scene, _beam(p1, p2, 0.18 * U), node, PALETTE["conduit_data"])
        parts.append({"name": node, "label": flow_label, "type": "conduit",
                      "role": "recorded data/material flow (topology only)"})

    # --- control conduits: compute core -> every other subsystem -------------
    compute_idx = next((i for i, (_, _, _, k) in enumerate(centers) if k == "compute"), None)
    if compute_idx is not None and n > 2:
        cx, cz, _, _ = centers[compute_idx]
        for i, (x, z, _, kind) in enumerate(centers):
            if i == compute_idx:
                continue
            p1 = (cx, -0.95 * U, cz + BLOCK_H * 1.6 * 0.5)
            p2 = (x, -0.95 * U, z + BLOCK_H * 0.6)
            control_label = f"control -> [{i+1:02d}]"
            node = uid(control_label)
            _add(scene, _beam(p1, p2, 0.14 * U), node, PALETTE["conduit_power"])
            parts.append({"name": node, "label": control_label, "type": "conduit",
                          "role": "control/optimization coupling (topology only)"})

    glb = scene.export(file_type="glb")
    sha = hashlib.sha256(glb).hexdigest()

    key_dimensions = {
        "measurement_basis": "TOPOLOGY_ONLY",
        "note": ("conceptual artifact — component count and adjacency only; "
                 "sizes are abstract presentation units, not engineering dimensions"),
        "component_count": len(parts),
        "subsystem_count": n,
        "conduit_count": sum(1 for p in parts if p["type"] == "conduit"),
        "adjacency": [
            {"from": subsystems[i], "to": subsystems[i + 1], "kind": "data"}
            for i in range(n - 1)
        ],
    }

    return {
        "glb_bytes": glb,
        "glb_sha256": sha,
        "components": parts,
        "key_dimensions": key_dimensions,
    }


def build_conceptual_device(
    intervention_site: str,
    layer_names: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Build a CONCEPTUAL_3D single-device visualization (stacked layers).

    Used when the invention has a single device form but no sourced geometry
    parameters. Layer names come from the recorded architecture (never invented
    here). All units abstract.
    """
    layers = layer_names or ["form", "mechanism layer", "interface"]
    scene = trimesh.Scene()
    parts: List[Dict[str, Any]] = []
    uid = _UniqueId()
    z = 0.0
    w, d = 6.0 * U, 4.0 * U
    palette_cycle = ["substrate", "transduction", "compute", "sensing", "storage", "interface"]
    for i, name in enumerate(layers):
        t = 0.6 * U if i == 0 else 0.35 * U
        layer = cq.Workplane("XY").workplane(offset=z).box(w, d, t, centered=(True, True, False))
        layer_label = f"layer {i+1}: {name}"
        node = uid(layer_label)
        _add(scene, layer, node, PALETTE[palette_cycle[i % len(palette_cycle)]])
        parts.append({"name": node, "label": layer_label, "type": "layer",
                      "role": "conceptual layer (no engineering dimensions)"})
        z += t

    glb = scene.export(file_type="glb")
    sha = hashlib.sha256(glb).hexdigest()
    return {
        "glb_bytes": glb,
        "glb_sha256": sha,
        "components": parts,
        "key_dimensions": {
            "measurement_basis": "TOPOLOGY_ONLY",
            "note": "conceptual artifact — layer count only; no engineering dimensions",
            "component_count": len(parts),
            "layer_count": len(parts),
        },
    }
