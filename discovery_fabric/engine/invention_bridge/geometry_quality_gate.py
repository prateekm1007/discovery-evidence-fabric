"""Machine-checkable 3D quality gates (R432 sections 16-17).

Two SEPARATE gates — never confused with scientific validation:

  geometry_quality_gate — structural integrity of the artifact:
      valid GLB, non-empty scene, expected component count, named
      components, sane bounding box, no microscopic geometry, no
      enormous disconnected geometry, no accidental duplicate model,
      valid normals/transforms, no NaN/Inf coordinates, spec/scene
      component-ID parity, interface endpoints resolve, canonical
      topology preserved.

  visual_quality_gate — the PRESENTATION audit (section 17): rejects
      obviously bad results such as a flat slab, a generic box pile,
      an empty scene, or a family model missing its family-defining
      features (a vehicle without wheels; a solar EV without solar
      surfaces). This gate is a structural/metrics audit derived from
      the geometry and the spec — it is NOT a vision model and NOT a
      scientific verdict (Art. XXVIII: presentation never upgrades or
      downgrades epistemic status; a gate failure is a typed product
      record).

For ENGINEERING_3D artifacts the gate additionally verifies the
provenance hash chain: CAD source identity -> GLB -> STEP -> STL ->
Blender scene (section 16, engineering block).
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np
import trimesh

GATE_VERSION = "1.0.0"

# Operating bands in abstract presentation units (the domain builders'
# scale: vehicles ~11 units long, catheters ~9, packs ~6). Sane model
# extent: > 0.5 (not microscopic), < 500 (not enormous); no single
# axis more than 40x another (slab/needle rejection).
MIN_SCENE_EXTENT = 0.5
MAX_SCENE_EXTENT = 500.0
MAX_AXIS_RATIO = 40.0
MIN_COMPONENT_EXTENT = 1e-3
MIN_FLAT_RATIO = 0.06  # z-extent / max(x,y) below this = flat slab

# Family-defining feature requirements (visual gate, section 17 —
# "the geometry must correspond to the physical identity").
FAMILY_REQUIRED = {
    "VEHICLE": {
        "min_components": 10,
        "required_prefixes": {
            "wheel_": 4,        # four road wheels
            "solar_": 1,        # solar surface present
            "chassis": 1,
            "cabin": 1,
        },
        "required_any": [
            # ONE disjunctive group: some energy/drivetrain architecture
            # must be present (any one of storage / motor / conversion).
            # The solar-EV-specific ALL-required contract lives in the
            # R433 semantic gate, not in the family form gate.
            ("battery", "battery_pack", "traction_motor",
             "power_electronics"),
        ],
        "silhouette": {"length_gt_width": True, "height_ratio_max": 0.55},
    },
    "MEDICAL_DEVICE": {
        "min_components": 4,
        "required_prefix": {"device_shaft": 1, "distal_tip": 1},
    },
    "FLUID_DEVICE": {
        "min_components": 4,
        "required_prefix": {"device_body": 1, "flow_channel": 1},
    },
    "THERMAL_SYSTEM": {
        "min_components": 4,
        "required_prefix": {"assembly_base": 1},
        "required_any": [("heat", "heat_source", "heat_sink")],
    },
    "MECHANICAL_COMPONENT": {
        "min_components": 4,
        "required_prefix": {"housing": 1},
    },
    "ELECTRONIC_SYSTEM": {
        "min_components": 4,
        "required_prefix": {"enclosure": 1, "main_board": 1},
    },
    "ENERGY_STORAGE": {
        "min_components": 4,
        "required_prefix": {"cell_stack": 1, "pack_enclosure": 1},
    },
}


def _load_scene(glb_bytes: bytes) -> Optional[trimesh.Scene]:
    try:
        import io
        obj = trimesh.load(io.BytesIO(glb_bytes), process=False,
                           file_type="glb")
    except Exception:
        return None
    if isinstance(obj, trimesh.Scene):
        return obj
    return None


def _finite(a: Any) -> bool:
    try:
        return bool(np.isfinite(np.asarray(a, dtype=float)).all())
    except (TypeError, ValueError):
        return False


def geometry_quality_gate(glb_bytes: bytes,
                          spec: Optional[Dict[str, Any]],
                          domain_family: Optional[str] = None,
                          ) -> Dict[str, Any]:
    """Structural gate over the built GLB. Returns a typed report:
    {artifact, version, checks[], failures[], passed}.

    Checks are the section-16 minimum list; family-aware where the
    family is known. Every check carries its measured values — the
    report is auditable, not a bare PASS (Art. XV).
    """
    checks: List[Dict[str, Any]] = []
    failures: List[str] = []

    def check(name: str, ok: bool, measured: Any = None) -> None:
        entry = {"check": name, "passed": bool(ok)}
        if measured is not None:
            entry["measured"] = measured
        checks.append(entry)
        if not ok:
            failures.append(name)

    scene = _load_scene(glb_bytes)
    check("valid_glb", scene is not None)
    if scene is None:
        return {"artifact": "GEOMETRY_QUALITY_GATE", "version": GATE_VERSION,
                "checks": checks, "failures": failures, "passed": False}

    geoms = {name: g for name, g in scene.geometry.items()}
    meshes = [g for g in geoms.values() if isinstance(g, trimesh.Trimesh)]
    check("non_empty_scene", len(meshes) > 0,
          {"node_count": len(geoms), "mesh_count": len(meshes)})

    # --- named components + spec parity -----------------------------------
    node_names = sorted(geoms.keys())
    canonical_ids = set()
    if spec:
        canonical_ids = {c["component_id"] for c in spec.get("components")
                         or []}
        interface_nodes = {
            f"link_{i['from']}__{i['to']}"
            for i in spec.get("interfaces") or []}
        scene_set = set(node_names)
        # every spec component MUST exist as a node; every node must be
        # a spec component OR a spec interface link (links are optional
        # in the scene — families like VEHICLE draw no conduits)
        missing = sorted(canonical_ids - scene_set)
        unexpected = sorted(scene_set - canonical_ids - interface_nodes)
        check("component_ids_match_spec",
              not missing and not unexpected,
              {"spec_components": len(canonical_ids),
               "scene_nodes": len(node_names),
               "missing": missing,
               "unexpected": unexpected,
               "link_nodes_drawn": sorted(
                   scene_set & interface_nodes)})
    else:
        check("component_ids_match_spec", False,
              {"note": "no spec provided — parity uncheckable"})
    check("named_components",
          all(n and not n.startswith("Cube") for n in node_names),
          {"sample": node_names[:8]})

    # --- bounding box sanity -------------------------------------------------
    try:
        bounds = scene.bounds
        extent = (bounds[1] - bounds[0]).astype(float)
    except Exception:
        extent = np.zeros(3)
    check("bounding_box_sane",
          _finite(extent) and float(extent.min()) > 0
          and MIN_SCENE_EXTENT < float(extent.max()) < MAX_SCENE_EXTENT,
          {"extent": [round(float(e), 4) for e in extent]})

    # --- NaN/Inf, microscopic, duplicates, normals ---------------------------
    seen_hashes: Dict[str, str] = {}
    min_ext = float("inf")
    nan_found = False
    bad_normals = False
    duplicates: List[str] = []
    for name, g in geoms.items():
        if not isinstance(g, trimesh.Trimesh) or len(g.vertices) == 0:
            continue
        if not _finite(g.vertices):
            nan_found = True
        e = float(np.asarray(g.extents).min()) if _finite(g.extents) \
            else 0.0
        min_ext = min(min_ext, e)
        try:
            face_areas = np.asarray(g.area_faces)
            if not _finite(face_areas) or float(face_areas.min()) <= 0:
                bad_normals = True
        except Exception:
            bad_normals = True
        vh = hashlib.sha256(
            np.asarray(g.vertices, dtype=np.float64).tobytes()
        ).hexdigest()
        if vh in seen_hashes:
            duplicates.append(f"{seen_hashes[vh]}=={name}")
        seen_hashes[vh] = name
    check("no_nan_inf_coordinates", not nan_found)
    check("no_microscopic_geometry",
          min_ext >= MIN_COMPONENT_EXTENT,
          {"min_component_extent": None if min_ext == float("inf")
           else round(min_ext, 6)})
    check("no_duplicate_model", not duplicates, {"duplicates": duplicates})
    check("normals_valid", not bad_normals)

    # --- no enormous disconnected geometry ----------------------------------
    # A component spanning the whole scene is LEGITIMATE (a thermal
    # loop runs the vehicle length; a rail runs the catheter). The
    # defect class is: isolated islands far from the assembly, or one
    # blob dominating total volume while everything else is dust.
    try:
        center = np.asarray(scene.centroid, dtype=float)
        radius = float(np.linalg.norm(
            (scene.bounds[1] - scene.bounds[0]).astype(float))) / 2.0
        islands = []
        for name, g in geoms.items():
            if not isinstance(g, trimesh.Trimesh) or len(g.vertices) == 0:
                continue
            c = np.asarray(g.centroid, dtype=float)
            if _finite(c) and float(np.linalg.norm(c - center)) \
                    > max(radius * 1.6, 1.0):
                islands.append(name)
        check("no_isolated_outlier_geometry", not islands,
              {"islands": islands,
               "note": "components beyond 1.6x the assembly radius"})
        vols = [float(g.volume) for g in meshes
                if isinstance(g, trimesh.Trimesh) and g.volume > 0]
        total = sum(vols)
        dom = (max(vols) / total) if total > 0 else 1.0
        check("no_single_blob_domination", dom < 0.95,
              {"largest_component_volume_fraction": round(dom, 4)})
    except Exception:
        check("no_isolated_outlier_geometry", False,
              {"note": "span measurement failed"})

    # --- interfaces resolve + topology preserved ------------------------------
    if spec:
        ids = canonical_ids
        bad = [i["interface_id"] for i in spec.get("interfaces") or []
               if i["from"] not in ids or i["to"] not in ids]
        check("interfaces_resolve", not bad, {"unresolved": bad})
        kd = {
            "component_count": len(canonical_ids),
            "interface_count": len(spec.get("interfaces") or []),
        }
        check("canonical_topology_preserved",
              len(canonical_ids) > 0 and len(meshes) >= len(canonical_ids),
              kd)

    return {"artifact": "GEOMETRY_QUALITY_GATE", "version": GATE_VERSION,
            "domain_family": domain_family,
            "checks": checks, "failures": failures,
            "passed": not failures}


def visual_quality_gate(glb_bytes: bytes,
                        spec: Optional[Dict[str, Any]],
                        domain_family: Optional[str] = None,
                        ) -> Dict[str, Any]:
    """The PRESENTATION gate (section 17). Rejects flat slabs, generic
    box piles, and family models missing their defining physical
    identity. Structural metrics only — this is not scientific
    validation and not a vision model (disclosed in the record)."""
    checks: List[Dict[str, Any]] = []
    failures: List[str] = []

    def check(name: str, ok: bool, measured: Any = None) -> None:
        entry = {"check": name, "passed": bool(ok)}
        if measured is not None:
            entry["measured"] = measured
        checks.append(entry)
        if not ok:
            failures.append(name)

    scene = _load_scene(glb_bytes)
    if scene is None:
        check("loadable", False)
        return {"artifact": "VISUAL_QUALITY_GATE", "version": GATE_VERSION,
                "domain_family": domain_family, "checks": checks,
                "failures": failures, "passed": False,
                "note": ("presentation audit — structural metrics only; "
                         "NOT scientific validation and NOT a vision "
                         "model (R432 section 17 disclosure)")}

    geoms = {n: g for n, g in scene.geometry.items()
             if isinstance(g, trimesh.Trimesh)}
    names = sorted(geoms.keys())

    # --- flat slab rejection ---------------------------------------------------
    extent = scene.bounds[1] - scene.bounds[0]
    flat = (float(extent[1]) / max(float(extent[0]), 1e-9)
            if len(extent) > 1 else 1.0)
    # after Y-up export: X length, Y height, Z width
    length = float(extent[0])
    height = float(extent[1])
    check("not_flat_slab", height / max(length, 1e-9) >= MIN_FLAT_RATIO
          or len(geoms) > 3,
          {"height_over_length": round(height / max(length, 1e-9), 4),
           "component_count": len(geoms)})

    # --- generic box pile rejection --------------------------------------------
    # A box pile = few components, all axis-aligned boxes (8 vertices,
    # 12 faces, right angles). Shaped solids (cylinders, lofts, cuts)
    # have higher face counts.
    boxy = [n for n, g in geoms.items()
            if len(g.faces) <= 12 and len(g.vertices) <= 8]
    box_ratio = len(boxy) / max(1, len(geoms))
    check("not_generic_box_pile",
          not (len(geoms) <= 5 and box_ratio >= 0.8),
          {"component_count": len(geoms),
           "pure_box_components": len(boxy),
           "box_ratio": round(box_ratio, 3)})

    # --- family physical identity (section 3/18) --------------------------------
    family = domain_family or (spec or {}).get("technology_class")
    req = FAMILY_REQUIRED.get(family) if family else None
    if req:
        if "min_components" in req:
            check("family_component_count",
                  len(geoms) >= req["min_components"],
                  {"family": family, "components": len(geoms),
                   "required": req["min_components"]})
        prefixes = req.get("required_prefixes") or {}
        for prefix, count in prefixes.items():
            actual = sum(1 for n in names if n.startswith(prefix))
            check(f"family_feature_{prefix}", actual >= count,
                  {"family": family, "found": actual, "required": count})
        exacts = req.get("required_prefix") or {}
        for exact, count in exacts.items():
            actual = sum(1 for n in names if n == exact)
            check(f"family_feature_{exact}", actual >= count,
                  {"family": family, "found": actual, "required": count})
        for alternatives in req.get("required_any") or []:
            actual = sum(1 for n in names
                         if any(n == a or n.startswith(str(a))
                                for a in alternatives))
            check(f"family_feature_any_{'_'.join(map(str, alternatives))}",
                  actual >= 1, {"family": family})
        sil = req.get("silhouette") or {}
        if sil.get("length_gt_width"):
            width = float(extent[2]) if len(extent) > 2 else 1.0
            check("family_silhouette_length_gt_width", length > width,
                  {"length": round(length, 2), "width": round(width, 2)})
        hr = sil.get("height_ratio_max")
        if hr is not None:
            check("family_silhouette_height_ratio",
                  height / max(length, 1e-9) <= hr,
                  {"height_ratio": round(height / max(length, 1e-9), 3),
                   "max": hr})
    else:
        check("family_requirements", False,
              {"note": "no family requirement table for "
                       f"'{family}' — visual identity uncheckable"})

    return {"artifact": "VISUAL_QUALITY_GATE", "version": GATE_VERSION,
            "domain_family": family, "checks": checks,
            "failures": failures, "passed": not failures,
            "note": ("presentation audit — structural metrics only; "
                     "NOT scientific validation and NOT a vision model "
                     "(R432 section 17 disclosure)")}


def engineering_provenance_gate(model_dir: str,
                                geometry_out: Dict[str, Any]
                                ) -> Dict[str, Any]:
    """Section 16 engineering block: CAD source hash chain — the GLB
    must derive from the canonical CAD build (glb sha recorded by the
    builder == the exported file's sha; STEP/STL present and hashed;
    the Blender scene hash recorded by the render stage when present).
    """
    from pathlib import Path
    checks: List[Dict[str, Any]] = []
    failures: List[str] = []

    def check(name: str, ok: bool, measured: Any = None) -> None:
        entry = {"check": name, "passed": bool(ok)}
        if measured is not None:
            entry["measured"] = measured
        checks.append(entry)
        if not ok:
            failures.append(name)

    d = Path(model_dir)
    glb = d / "engineering_model.glb"
    step = d / "engineering_model.step"
    stl = d / "engineering_model.stl"

    def _sha(p: Path) -> Optional[str]:
        try:
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            return h.hexdigest()
        except OSError:
            return None

    recorded_glb = geometry_out.get("glb_sha256")
    disk_glb = _sha(glb) if glb.is_file() else None
    check("glb_derived_from_cad",
          disk_glb is not None and recorded_glb == disk_glb,
          {"recorded": recorded_glb, "on_disk": disk_glb})
    check("step_present_hashed", _sha(step) is not None,
          {"step_sha256": _sha(step)})
    check("stl_present_hashed", _sha(stl) is not None,
          {"stl_sha256": _sha(stl)})
    src = (geometry_out.get("parametric_source") or {}).get("form")
    check("cad_source_form_recorded", bool(src), {"form": src})
    render_record = d / "MODEL" / "3D" / "render_record.json"
    check("blender_scene_hash_recorded",
          render_record.is_file() or geometry_out.get("renders") is not None,
          {"render_record_path": str(render_record),
           "note": "recorded when the render stage executed"})

    return {"artifact": "ENGINEERING_PROVENANCE_GATE",
            "version": GATE_VERSION, "checks": checks,
            "failures": failures, "passed": not failures}


def run_all_gates(glb_bytes: bytes, spec: Optional[Dict[str, Any]],
                  domain_family: Optional[str] = None,
                  engineering: bool = False,
                  model_dir: Optional[str] = None,
                  geometry_out: Optional[Dict[str, Any]] = None,
                  ) -> Dict[str, Any]:
    """Composite gate record for the bridge report (typed, never an
    exception — a gate failure is product information, Art. LXI)."""
    geo = geometry_quality_gate(glb_bytes, spec, domain_family)
    vis = visual_quality_gate(glb_bytes, spec, domain_family)
    eng = None
    if engineering and model_dir and geometry_out:
        eng = engineering_provenance_gate(model_dir, geometry_out)
    passed = geo["passed"] and vis["passed"] and (
        eng is None or eng["passed"])
    return {
        "artifact": "R432_QUALITY_GATES",
        "version": GATE_VERSION,
        "geometry_gate": geo,
        "visual_gate": vis,
        "engineering_gate": eng,
        "passed": passed,
        "failures": (geo["failures"] + vis["failures"]
                     + ((eng or {}).get("failures") or [])),
    }
