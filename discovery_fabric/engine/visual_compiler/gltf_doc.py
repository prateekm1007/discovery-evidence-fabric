"""gltf_doc.py — R441 deterministic glTF document reader.

WHY THIS EXISTS (the R441 acceptance found it live): trimesh (and any
loader) SYNTHESIZES names for unnamed glTF nodes — different on every
load. A pipeline whose material mapping, renderer application and gate
verification all key on node names cannot tolerate unstable names
(Art. X: one canonical identity per node).

This module reads the glTF JSON chunk DIRECTLY (stdlib struct + json —
no loader, no synthesis) and derives, deterministically from the glTF
document itself:

  * canonical node names: the glTF node name when it exists, else
    "part-NNN" assigned in DEPTH-FIRST scene order (the same order
    three.js's GLTFLoader builds the scene graph, so the renderer's
    rename pass and this walker agree by construction);
  * per-part world bounds: POSITION accessor min/max (required by the
    glTF spec) composed through the node transform chain;
  * the model bounds/center/raw_size for the scene spec.

The same canonical names are embedded in the scene spec, applied by the
renderer (it renames its loaded meshes identically before materials),
and re-verified by the gate on the exported GLBs — one identity, three
consumers (Art. III: the verifier can re-derive the claim).
"""
from __future__ import annotations

import json
import struct
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def read_gltf_json(glb_path: str) -> Dict[str, Any]:
    """The glTF JSON document from a GLB container (magic 'glTF',
    version 2). Raises a typed ValueError on anything else — never a
    guess."""
    with open(glb_path, "rb") as f:
        magic, version, length = struct.unpack("<4sII", f.read(12))
        if magic != b"glTF":
            raise ValueError(f"not a GLB container: {magic!r}")
        if version != 2:
            raise ValueError(f"unsupported GLB version: {version}")
        chunks = []
        while f.tell() < length:
            header = f.read(8)
            if len(header) < 8:
                break
            clen, ctype = struct.unpack("<I4s", header)
            chunks.append((ctype, f.read(clen)))
        if not chunks or chunks[0][0] != b"JSON":
            raise ValueError("GLB has no JSON chunk")
        return json.loads(chunks[0][1].decode("utf-8"))


def _node_matrix(node: Dict[str, Any]) -> np.ndarray:
    """The node's local transform as a 4x4 (glTF: column-major matrix
    or TRS; spec: matrix takes precedence, scale then rotation then
    translation otherwise)."""
    if "matrix" in node:
        m = np.array(node["matrix"], dtype=np.float64).reshape(4, 4)
        return m.T  # glTF stores column-major
    m = np.eye(4)
    t = node.get("translation", [0, 0, 0])
    r = node.get("rotation", [0, 0, 0, 1])  # xyzw quaternion
    s = node.get("scale", [1, 1, 1])
    x, y, z, w = r
    rot = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ], dtype=np.float64)
    m[:3, :3] = rot @ np.diag(s)
    m[:3, 3] = t
    return m


def _local_bounds(doc: Dict[str, Any], node: Dict[str, Any]
                  ) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """POSITION accessor min/max of the node's mesh (spec-required
    fields — present in every valid glTF mesh)."""
    mesh = (doc.get("meshes") or [])[node["mesh"]] \
        if "mesh" in node else None
    if mesh is None:
        return None
    mn = np.array([np.inf] * 3)
    mx = np.array([-np.inf] * 3)
    for prim in mesh.get("primitives", []):
        acc = (doc.get("accessors") or [])[prim["attributes"]["POSITION"]]
        if "min" in acc and "max" in acc:
            mn = np.minimum(mn, np.array(acc["min"], dtype=np.float64))
            mx = np.maximum(mx, np.array(acc["max"], dtype=np.float64))
    if not np.isfinite(mn).all():
        return None
    return mn, mx


def walk_scene(glb_path: str) -> Dict[str, Any]:
    """Deterministic scene walk: canonical names in DFS order + world
    bounds per part + model aggregate."""
    doc = read_gltf_json(glb_path)
    scene_idx = doc.get("scene", 0)
    scene = (doc.get("scenes") or [{}])[scene_idx]
    nodes = doc.get("nodes") or []

    parts: List[Dict[str, Any]] = []
    counter = 0

    def visit(idx: int, parent_m: np.ndarray, seen: set) -> None:
        nonlocal counter
        if idx in seen or idx >= len(nodes):
            return  # glTF forbids cycles; refuse silently-corrupt docs
        seen.add(idx)
        node = nodes[idx]
        world = parent_m @ _node_matrix(node)
        bounds = _local_bounds(doc, node)
        if bounds is not None:
            counter += 1
            name = str(node.get("name") or "").strip() \
                or f"part-{counter:03d}"
            corners = np.array([[x, y, z, 1.0]
                                for x in (bounds[0][0], bounds[1][0])
                                for y in (bounds[0][1], bounds[1][1])
                                for z in (bounds[0][2], bounds[1][2])])
            wc = (world @ corners.T).T[:, :3]
            parts.append({
                "name": name,
                "named_in_gltf": bool(str(node.get("name") or "").strip()),
                "min": wc.min(axis=0),
                "max": wc.max(axis=0),
            })
        for child in node.get("children", []):
            visit(child, world, seen)

    roots = scene.get("nodes", [])
    for root in roots:
        visit(root, np.eye(4), set())

    if not parts:
        raise ValueError("glTF scene carries no mesh-bearing nodes")

    all_min = np.min([p["min"] for p in parts], axis=0)
    all_max = np.max([p["max"] for p in parts], axis=0)
    center = (all_min + all_max) / 2.0
    return {
        "parts": [{"name": p["name"],
                   "named_in_gltf": p["named_in_gltf"],
                   "min": [float(v) for v in p["min"]],
                   "max": [float(v) for v in p["max"]]}
                  for p in parts],
        "min": all_min, "max": all_max, "center": center,
        "raw_size": all_max - all_min, "min_y": float(all_min[1]),
    }


def raw_part_identity(glb_path: str) -> Dict[str, Any]:
    """R443: RAW-document part identity — the gate's witness for
    canonical node identity (Workstream 1).

    WHY: any loader (trimesh, three.js) SYNTHESIZES names for unnamed
    glTF nodes, so a check that reads names through a loader cannot
    distinguish a canonically named GLB from one whose names were
    stripped after compilation (the R442 recorded blind spot). This
    function reads the glTF JSON chunk DIRECTLY — no loader, no
    synthesis — and reports, per mesh-bearing node:

      * name          the RAW `node.name` (None when absent/empty);
      * ancestor_name the nearest NAMED mesh-bearing ancestor's raw
                      name (None when none);
      * is_primitive_slice
                      True when the node itself is unnamed but its
                      PARENT is a named mesh-bearing node — the
                      multi-primitive export pattern (one named part
                      node whose primitive meshes the GLTFExporter
                      emits as unnamed child nodes). A slice carries
                      its parent's identity; it is NOT a missing
                      identity.

    The gate FAILS a GLB whose mesh-bearing nodes are neither named
    nor primitive slices of a named part — and that failure is
    specifically "canonical identity absent from the raw document".
    """
    doc = read_gltf_json(glb_path)
    scene_idx = doc.get("scene", 0)
    scene = (doc.get("scenes") or [{}])[scene_idx]
    nodes = doc.get("nodes") or []

    found: List[Dict[str, Any]] = []

    def visit(idx: int, anc_name: Optional[str], seen: set) -> None:
        """anc_name = nearest NAMED mesh-bearing ancestor's raw name
        (None when none) — the identity a slice inherits."""
        if idx in seen or idx >= len(nodes):
            return
        seen.add(idx)
        node = nodes[idx]
        name = str(node.get("name") or "").strip() or None
        has_mesh = "mesh" in node
        if has_mesh:
            found.append({
                "name": name,
                "ancestor_name": anc_name,
                "is_primitive_slice": bool(name is None and anc_name),
            })
        child_anc = name if (name and has_mesh) else \
            (anc_name if (name is None and has_mesh and anc_name) else None)
        # a NAMED mesh node re-anchors identity; an UNNAMED slice keeps
        # its ancestor; a non-mesh node does not pass identity down
        # (a named group without meshes is NOT a part identity)
        for child in node.get("children", []):
            visit(child, child_anc, seen)

    for root in scene.get("nodes", []):
        visit(root, None, set())

    named = [f["name"] for f in found if f["name"]]
    unnamed = [f for f in found if f["name"] is None
               and not f["is_primitive_slice"]]
    return {
        "mesh_nodes": len(found),
        "named": named,
        "unnamed_unattributed": [{"ancestor_name": f["ancestor_name"]}
                                 for f in unnamed],
        "primitive_slices": sum(1 for f in found
                                if f["is_primitive_slice"]),
    }
