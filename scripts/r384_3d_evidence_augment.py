#!/usr/bin/env python3
"""r384_3d_evidence_augment — build the 3D EVIDENCE layer for every
package of the technology-transfer portfolio, answering the external
re-review audit ("0 STEP/STL/PNG in every package").

Per package with 3D status PRESENT_AND_VALIDATED this script adds, under
MODEL/3D_EVIDENCE/ (existing recorded artifacts are NEVER touched):
  - {pid}_section_longitudinal_solid.step/.stl  — true cut solid at the
    longitudinal mid-plane (same plane as the shipped section SVG)
  - {pid}_section_transverse_solid.step/.stl   — true cut solid at
    mid-length (exposes the cross-section of the critical lumens)
  - {pid}_render_isometric.png / _render_exploded.png (multi-object)
  - {pid}_render_section_longitudinal.png / _render_section_transverse.png
  - REGENERATION_CHECK.json   — independent rebuild from the SHIPPED
    parametric source + parameter map, measured vs shipped KEY_DIMENSIONS
  - PARAMETER_FEATURE_LOG.json — parameter -> measured-feature mapping
  - STL_INDEPENDENT_WATERTIGHT_CHECK.json — trimesh re-verification of
    every shipped STL
  - FILE_INVENTORY.json — sha256 + bytes of every CAD file in MODEL/
  - 3D_EVIDENCE_README.json

The engine module (discovery_fabric.engine.cad_pipeline) is imported for
the SAME sandboxed build executor and geometry measurer that produced the
shipped models. Package 06 (3D_NOT_APPLICABLE, software-only) gets no
files — honest not-applicable, never forced.

Outputs portfolio summary: <build_root>/R384_3D_EVIDENCE_SUMMARY.json
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from pathlib import Path

sys.path.insert(0, "/home/z/my-project/discovery-evidence-fabric")
sys.path.insert(0, "/home/z/my-project/scripts")

from discovery_fabric.engine import cad_pipeline as cp  # noqa: E402

import cadquery as cq  # noqa: E402
import trimesh  # noqa: E402

from r384_render_lib import decimate, render_scene  # noqa: E402

BUILD_ROOT = Path(os.environ.get(
    "TTP_PORTFOLIO_ROOT",
    "/home/z/my-project/technology-transfer-portfolio-15"))
REPO_ROOT = Path("/home/z/my-project/discovery-evidence-fabric")
TIERS = ["DOWNLOAD", "HOLDING", "RETIRED", "SPECIALIST_TRACK"]
TOL_DIM = 1e-3   # engine MEASURED_VS_CLAIMED_TOLERANCE (mm)
TOL_MATCH = 1e-6  # exact linear feature match tolerance (mm)


def sha256_file(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def kind_of(ext: str) -> str:
    return {"step": "STEP", "stl": "STL", "glb": "GLB", "svg": "SVG",
            "py": "PARAMETRIC_SOURCE", "png": "PNG_RENDER",
            "json": "JSON"}.get(ext, ext.upper())


def flatten_params(pj: dict) -> dict:
    return {p["param_id"]: p["value"] for p in pj["parameters"]}


def object_stl_paths(model_dir: Path, base: str, manifest: dict) -> list:
    """Shipped per-object STLs in declared object order (fallback: glob)."""
    out = []
    arts = manifest.get("derived_artifacts", {})
    for obj in manifest.get("objects", []):
        oid = obj["object_id"]
        a = arts.get(f"STL:{oid}")
        if a and "path" in a:
            p = model_dir.parent / a["path"] if not a["path"].startswith("/") else Path(a["path"])
            # paths in manifest are like MODEL/P-07_x.stl relative to package root
            if not p.exists():
                p = model_dir / Path(a["path"]).name
            if p.exists():
                out.append((oid, str(p)))
    if not out:
        for p in sorted(model_dir.glob(f"{base}_*.stl")):
            oid = p.name[len(base) + 1:-4]
            out.append((oid, str(p)))
    return out


STL_BYTES_CAP = 8_000_000        # deliverable budget for one cut-solid STL
STEP_BYTES_CAP = 20_000_000      # deliverable budget for one cut-solid STEP
STL_TOL_LADDER = ((0.02, 0.1), (0.05, 0.3), (0.08, 0.5), (0.15, 0.8))


def export_cut_solid(cut, ev: Path, pid: str, oid: str, plane: str,
                     suffix: str = "") -> dict:
    """STEP always attempted (compact B-rep reference), STL adaptively
    tessellated to stay inside the deliverable budget; size caps are
    recorded honestly (never silently shipped oversized or silently
    dropped - every omission carries its measured reason)."""
    info = {"object_id": oid}
    stp = ev / f"{pid}_{oid}_section_{plane}{suffix}_solid.step"
    cut.exportStep(str(stp))
    if stp.stat().st_size > STEP_BYTES_CAP:
        b = stp.stat().st_size
        stp.unlink()
        info["step"] = None
        info["step_note"] = (f"B-rep section solid omitted: {b} bytes "
                             "exceeds the 20 MB deliverable budget (a cut "
                             "through a swept helical surface can fragment "
                             "into excessive trimmed faces); the shipped SVG "
                             "section drawing + the mesh-level cutaway "
                             "render remain the section evidence for this "
                             "object and plane")
    else:
        info["step"] = (f"MODEL/3D_EVIDENCE/"
                        f"{pid}_{oid}_section_{plane}{suffix}_solid.step")
        info["step_bytes"] = stp.stat().st_size
    stl = ev / f"{pid}_{oid}_section_{plane}{suffix}_solid.stl"
    chosen = None
    for tol, atol in STL_TOL_LADDER:
        # R387: OCCT caches face triangulation inside the shape — without
        # clearing it, every ladder attempt after the first silently
        # reuses the first mesh (measured on the helical-antenna coupon:
        # 9.7 MB at every tolerance). Clear before each attempt so the
        # declared tolerance actually applies.
        try:
            from OCP.BRepTools import BRepTools  # noqa: PLC0415
            BRepTools.Clean_s(cut.wrapped)
        except Exception:  # noqa: BLE001 — best-effort cache clear
            pass
        cut.exportStl(str(stl), tolerance=tol, angularTolerance=atol)
        b = stl.stat().st_size
        chosen = {"tolerance": tol, "angularTolerance": atol, "bytes": b}
        if b <= STL_BYTES_CAP:
            break
    if stl.exists() and stl.stat().st_size > 2 * STL_BYTES_CAP:
        stl.unlink()
        info["stl"] = None
        info["stl_note"] = ("mesh derivative omitted: tessellation exceeds "
                            "the deliverable budget even at the coarsest "
                            "declared tolerance - the STEP B-rep is the "
                            "reference section solid where present")
        info["stl_export"] = chosen
        return info
    try:
        m = trimesh.load_mesh(str(stl), force="mesh")
        chosen["faces"] = int(len(m.faces))
        chosen["trimesh_watertight"] = bool(m.is_watertight)
    except Exception as exc:  # noqa: BLE001
        chosen["trimesh_check_error"] = f"{type(exc).__name__}: {exc}"
    info["stl"] = (f"MODEL/3D_EVIDENCE/"
                   f"{pid}_{oid}_section_{plane}{suffix}_solid.stl")
    info["stl_export"] = chosen
    return info


def per_object_cuts(shapes: dict, plane: str, bbox) -> tuple:
    """Cut EVERY OBJECT individually with the same half-space. Robust:
    no compound boolean - per-object OCCT cuts are fast and stable even
    for swept helical surfaces. Returns ({oid: cut_shape}, desc,
    {oid: error})."""
    big = 3.0 * float(max(bbox.xlen, bbox.ylen, bbox.zlen)) + 10.0
    cx = (bbox.xmin + bbox.xmax) / 2.0
    cy = (bbox.ymin + bbox.ymax) / 2.0
    cz = (bbox.zmin + bbox.zmax) / 2.0
    if plane == "longitudinal":
        ymid = (bbox.ymin + bbox.ymax) / 2.0
        cutter = (cq.Workplane("XY").box(big, big, big,
                                         centered=(True, False, True))
                  .translate((cx, ymid, cz)))
        desc = f"longitudinal mid-plane y = {ymid:.4f} mm (y > ymid removed)"
    else:
        zmid = (bbox.zmin + bbox.zmax) / 2.0
        cutter = (cq.Workplane("XY").box(big, big, big,
                                         centered=(True, True, False))
                  .translate((cx, cy, zmid)))
        desc = f"transverse mid-length plane z = {zmid:.4f} mm (z > zmid removed)"
    cuts, errors = {}, {}
    cutter_val = cutter.val()
    for oid, sh in shapes.items():
        val = sh.val() if hasattr(sh, "val") else sh
        try:
            cut = val.cut(cutter_val)
            if cut is None or not cut.isValid() or cut.Volume() <= 1e-9:
                errors[oid] = "cut produced invalid or empty solid"
            else:
                cuts[oid] = cut
        except Exception as exc:  # noqa: BLE001
            errors[oid] = f"{type(exc).__name__}: {exc}"
    return cuts, desc, errors


def parameter_feature_log(params_json: dict, measured: dict) -> dict:
    rows = []
    pool = []  # (object_id, feature_name, measured_value)
    for oid, m in measured.get("objects", {}).items():
        bb = m.get("bbox", {})
        for k in ("xlen", "ylen", "zlen"):
            if k in bb:
                pool.append((oid, f"bbox.{k}", float(bb[k])))
        for i, r in enumerate(m.get("cylinder_face_radii", [])):
            pool.append((oid, f"cylinder_face_radius[{i}]", float(r)))
        if "min_wall_thickness_mm" in m:
            pool.append((oid, "min_wall_thickness_mm",
                         float(m["min_wall_thickness_mm"])))
        for i, w in enumerate(m.get("signed_containment_walls_mm", [])):
            pool.append((oid, f"signed_containment_wall[{i}]", float(w)))
    for p in params_json["parameters"]:
        val = float(p["value"])
        matches = []
        for oid, feat, mv in pool:
            for factor, rel in ((1.0, "measured = value"),
                                (0.5, "measured = value * 0.5 (radius of a diameter parameter)"),
                                (2.0, "measured = value * 2.0 (diameter span of a radius parameter)")):
                if abs(mv - val * factor) <= TOL_MATCH:
                    matches.append({"object_id": oid, "feature": feat,
                                    "measured_value": round(mv, 6),
                                    "relation": rel,
                                    "delta_mm": round(abs(mv - val * factor), 9)})
        rows.append({
            "param_id": p["param_id"], "value": p["value"],
            "unit": p.get("unit"), "envelope": p.get("envelope"),
            "value_class": p.get("value_class"),
            "measured_feature_matches": matches,
            "match_count": len(matches),
            "binding_note": (
                "the shipped build program consumes every parameter "
                "(G5/G5b gates); matches above are the measured solid "
                "features linearly equal to this parameter"
                if matches else
                "no linear 1:1/2:1 measured feature — the parameter "
                "modulates geometry non-linearly or is a non-geometry "
                "quantity (material/flow/process); it is still bound in "
                "the build program (G5)"),
        })
    matched = sum(1 for r in rows if r["match_count"] > 0)
    return {"artifact": "PARAMETER_FEATURE_LOG",
            "method": ("parameters from MODEL/PARAMETERS.json compared against "
                       "features MEASURED on the independently rebuilt solid "
                       "(OCCT Shape.BoundingBox / BRepAdaptor_Cylinder.Radius / "
                       "Volume), tolerance 1e-6 mm"),
            "parameters_total": len(rows),
            "parameters_with_linear_feature_match": matched,
            "rows": rows,
            "evidence_class": "COMPUTATIONAL_RESULT"}


def regenerate_check(shapes: dict, measured: dict, key_dims: dict) -> dict:
    res = {"artifact": "REGENERATION_CHECK",
           "method": ("independent rebuild: execute the SHIPPED "
                      "MODEL/PARAMETRIC_MODEL_SOURCE.py with the SHIPPED "
                      "MODEL/PARAMETERS.json through the engine sandbox "
                      "(discovery_fabric.engine.cad_pipeline."
                      "_execute_build_program), then measure with "
                      "measure_geometry and compare against the SHIPPED "
                      "MODEL/KEY_DIMENSIONS.json"),
           "tolerance_mm": TOL_DIM,
           "objects": {}}
    ok = True
    ship = key_dims.get("objects", {})
    for oid, m in measured.get("objects", {}).items():
        s = ship.get(oid)
        if s is None:
            res["objects"][oid] = {"status": "NO_SHIPPED_RECORD"}
            ok = False
            continue
        dv = abs(float(m["volume_mm3"]) - float(s["volume_mm3"]))
        bbm, bbs = m["bbox"], s["bbox"]
        dd = {k: round(abs(float(bbm[k]) - float(bbs[k])), 9)
              for k in ("xlen", "ylen", "zlen")}
        obj_ok = dv <= 1e-4 and all(v <= TOL_DIM for v in dd.values())
        ok = ok and obj_ok
        res["objects"][oid] = {
            "status": "MATCH" if obj_ok else "MISMATCH",
            "volume_mm3_rebuilt": round(float(m["volume_mm3"]), 6),
            "volume_mm3_shipped": s["volume_mm3"],
            "volume_delta": round(dv, 9),
            "bbox_dim_deltas_mm": dd}
    res["regeneration_status"] = "REPRODUCIBLE" if ok else "MISMATCH"
    res["evidence_class"] = "COMPUTATIONAL_RESULT"
    return res


def watertight_check(model_dir: Path, base: str, manifest: dict) -> dict:
    entries = []
    for oid, p in object_stl_paths(model_dir, base, manifest):
        try:
            mesh = trimesh.load_mesh(p, force="mesh")
            entries.append({"object_id": oid, "file": Path(p).name,
                            "watertight": bool(mesh.is_watertight),
                            "faces": int(len(mesh.faces)),
                            "vertices": int(len(mesh.vertices))})
        except Exception as exc:  # noqa: BLE001
            entries.append({"object_id": oid, "file": Path(p).name,
                            "error": f"{type(exc).__name__}: {exc}"})
    n_ok = sum(1 for e in entries if e.get("watertight") is True)
    return {"artifact": "STL_INDEPENDENT_WATERTIGHT_CHECK",
            "verifier": f"trimesh {trimesh.__version__} (independent of OCCT)",
            "checked": len(entries), "watertight_pass": n_ok,
            "status": "ALL_WATERTIGHT" if n_ok == len(entries) and entries
                      else "CHECK_FAILED",
            "entries": entries,
            "evidence_class": "COMPUTATIONAL_RESULT"}


def file_inventory(model_dir: Path) -> dict:
    files = []
    for p in sorted(model_dir.rglob("*")):
        if not p.is_file():
            continue
        rel = str(p.relative_to(model_dir))
        ext = p.suffix.lstrip(".").lower()
        files.append({
            "path": f"MODEL/{rel}",
            "bytes": p.stat().st_size,
            "sha256": sha256_file(p),
            "kind": kind_of(ext),
            "origin": "r384_3d_evidence" if rel.startswith("3D_EVIDENCE/")
                      else "shipped_r381_r382",
        })
    by_kind = {}
    for f in files:
        by_kind[f["kind"]] = by_kind.get(f["kind"], 0) + 1
    return {"artifact": "FILE_INVENTORY",
            "policy": "real sha256 of real bytes on disk (Art. VI)",
            "counts_by_kind": by_kind, "files": files,
            "evidence_class": "COMPUTATIONAL_RESULT"}


def augment_package(tier: str, folder: str) -> dict:
    pkg_dir = BUILD_ROOT / tier / folder
    model_dir = pkg_dir / "MODEL"
    num = folder.split("_")[0]
    pm = json.load(open(pkg_dir / "PACKAGE_MANIFEST.json"))
    pid = pm.get("package_id")
    status = json.load(open(model_dir / "3D_DESIGN_STATUS.json"))
    tech = pm.get("technology_name", folder)
    summary = {"portfolio_number": num, "package_id": pid,
               "tier": tier, "folder_name": folder,
               "technology_name": tech,
               "3d_design_status": status.get("3d_design_status"),
               "model_id": status.get("model_id"),
               "kernel": status.get("kernel"),
               "augmentation": {}}
    if status.get("3d_design_status") != "PRESENT_AND_VALIDATED":
        summary["augmentation"] = {
            "status": "NOT_AUGMENTED",
            "reason": ("3D status is "
                       f"{status.get('3d_design_status')} — the package's own "
                       "record classifies it as having no transferable device "
                       "geometry (software-only); no 3D artifact may be added "
                       "or implied (honest not-applicable)"),
        }
        return summary

    ev = model_dir / "3D_EVIDENCE"
    ev.mkdir(parents=True, exist_ok=True)
    created: list = []
    problems: list = []

    params_json = json.load(open(model_dir / "PARAMETERS.json"))
    pmap = flatten_params(params_json)
    src = (model_dir / "PARAMETRIC_MODEL_SOURCE.py").read_text()
    shapes, errs = cp._execute_build_program(src, pmap)
    if shapes is None:
        summary["augmentation"] = {"status": "FAILED",
                                   "errors": errs}
        return summary

    measured = cp.measure_geometry(shapes)
    key_dims = json.load(open(model_dir / "KEY_DIMENSIONS.json"))
    manifest = json.load(open(model_dir / "MODEL_MANIFEST.json"))

    # 1. regeneration check (independent rebuild from shipped source)
    regen = regenerate_check(shapes, measured, key_dims)
    (ev / "REGENERATION_CHECK.json").write_text(json.dumps(regen, indent=1))
    created.append("REGENERATION_CHECK.json")

    # 2. independent trimesh watertight re-verification of shipped STLs
    wt = watertight_check(model_dir, pid, manifest)
    (ev / "STL_INDEPENDENT_WATERTIGHT_CHECK.json").write_text(
        json.dumps(wt, indent=1))
    created.append("STL_INDEPENDENT_WATERTIGHT_CHECK.json")

    # 3. parameter -> measured feature log
    pfl = parameter_feature_log(params_json, measured)
    (ev / "PARAMETER_FEATURE_LOG.json").write_text(json.dumps(pfl, indent=1))
    created.append("PARAMETER_FEATURE_LOG.json")

    # 4. true section solids per object (longitudinal + transverse)
    compound = cq.Compound.makeCompound(
        [sh.val() if hasattr(sh, "val") else sh for sh in shapes.values()])
    bbox = compound.BoundingBox()
    uncut_volume = compound.Volume()
    sec_info = {}
    section_stls = {"longitudinal": [], "transverse": []}
    for plane in ("longitudinal", "transverse"):
        cuts, desc, cut_errors = per_object_cuts(shapes, plane, bbox)
        entry = {"plane": desc,
                 "cut_method": ("per-object OCCT half-space cut at the plane "
                                "above (every object sectioned individually; "
                                "no compound boolean - robust for swept "
                                "surfaces)"),
                 "objects": {},
                 "cut_errors": cut_errors}
        for oid, cut in cuts.items():
            entry["objects"][oid] = export_cut_solid(cut, ev, pid, oid, plane)
            entry["objects"][oid]["cut_volume_mm3"] = round(cut.Volume(), 6)
            stl_name = f"{pid}_{oid}_section_{plane}_solid.stl"
            if (ev / stl_name).exists():
                section_stls[plane].append(str(ev / stl_name))
            if entry["objects"][oid].get("step"):
                created.append(f"{pid}_{oid}_section_{plane}_solid.step")
            if entry["objects"][oid].get("stl"):
                created.append(f"{pid}_{oid}_section_{plane}_solid.stl")
            else:
                # mesh-level half-shell fallback (object whose B-rep/mesh
                # cut exceeded the size budget): slice the SHIPPED STL at
                # the same plane, export the open half, use it in the
                # cutaway render. Honest label: open half-shell, not a
                # closed solid.
                shipped = dict(object_stl_paths(model_dir, pid,
                                                manifest)).get(oid)
                if shipped:
                    try:
                        mesh = trimesh.load_mesh(shipped, force="mesh")
                        if plane == "longitudinal":
                            origin = [bbox.xmin + bbox.xlen / 2,
                                      (bbox.ymin + bbox.ymax) / 2,
                                      bbox.zmin + bbox.zlen / 2]
                            normal = [0.0, 1.0, 0.0]
                        else:
                            origin = [bbox.xmin + bbox.xlen / 2,
                                      bbox.ymin + bbox.ylen / 2,
                                      (bbox.zmin + bbox.zmax) / 2]
                            normal = [0.0, 0.0, 1.0]
                        half = mesh.slice_plane(plane_origin=origin,
                                                plane_normal=normal)
                        half, decim = decimate(half, target_faces=35000)
                        half_path = ev / (f"{pid}_{oid}_section_{plane}"
                                          "_mesh_half.stl")
                        half.export(str(half_path))
                        entry["objects"][oid]["mesh_half"] = (
                            f"MODEL/3D_EVIDENCE/{pid}_{oid}_section_"
                            f"{plane}_mesh_half.stl")
                        note = ("open mesh half-shell at the section plane "
                                "(mesh-level slice of the shipped STL; NOT "
                                "a closed solid - shipped because the B-rep "
                                "cut exceeded the size budget; two-sided "
                                "shaded in the render)")
                        if decim:
                            note += ("; decimated for the deliverable budget: "
                                     + json.dumps(decim[
                                         "render_only_decimation"]))
                        entry["objects"][oid]["mesh_half_note"] = note
                        section_stls[plane].append(str(half_path))
                        created.append(half_path.name)
                    except Exception as exc:  # noqa: BLE001
                        entry["objects"][oid]["mesh_half_error"] = (
                            f"{type(exc).__name__}: {exc}")
        if cuts:
            entry["status"] = "EXPORTED"
            entry["assembly_cut_volume_mm3"] = round(
                sum(c.Volume() for c in cuts.values()), 6)
            entry["uncut_assembly_volume_mm3"] = round(uncut_volume, 6)
        else:
            entry["status"] = "FAILED"
            problems.append(f"{plane} section solids: {cut_errors}")
        sec_info[plane] = entry

    # 4b. transverse SECTION COUPON for slender (catheter-class) models:
    # a short stub around the mid-length plane so the invention-critical
    # cross-section face is large enough to inspect (a 100 mm x 3 mm tube
    # renders its end face invisibly small otherwise).
    coupon_stls = []
    coupon_stub = None
    slender = bbox.zlen > 3.0 * max(bbox.xlen, bbox.ylen)
    if slender:
        zmid = (bbox.zmin + bbox.zmax) / 2.0
        coupon_stub = max(2.0 * max(bbox.xlen, bbox.ylen), 3.0)
        big = 3.0 * float(max(bbox.xlen, bbox.ylen, bbox.zlen)) + 10.0
        cx = (bbox.xmin + bbox.xmax) / 2.0
        cy = (bbox.ymin + bbox.ymax) / 2.0
        below = (cq.Workplane("XY").box(big, big, big, centered=(True, True, True))
                 .translate((cx, cy, zmid - coupon_stub - big / 2.0))).val()
        cuts, _, _ = per_object_cuts(shapes, "transverse", bbox)
        entry = {
            "plane": (f"transverse section coupon: stub z in "
                      f"[{zmid - coupon_stub:.4f}, {zmid:.4f}] mm "
                      f"(the invention-critical cross-section at mid-length "
                      f"plus a {coupon_stub:.1f} mm context stub)"),
            "purpose": ("slender catheter-class model: the coupon makes the "
                        "cross-section face inspectable in CAD and render; "
                        "the full-length cut solid above remains the "
                        "complete section solid"),
            "objects": {}}
        for oid, cut in cuts.items():
            try:
                coupon = cut.cut(below)
                if coupon is None or not coupon.isValid() \
                        or coupon.Volume() <= 1e-9:
                    entry["objects"][oid] = {"status": "EMPTY_CUT"}
                    continue
                entry["objects"][oid] = export_cut_solid(
                    coupon, ev, pid, oid, "transverse", suffix="_coupon")
                stl_name = f"{pid}_{oid}_section_transverse_coupon_solid.stl"
                if (ev / stl_name).exists():
                    coupon_stls.append(str(ev / stl_name))
                if entry["objects"][oid].get("step"):
                    created.append(
                        f"{pid}_{oid}_section_transverse_coupon_solid.step")
                if entry["objects"][oid].get("stl"):
                    created.append(
                        f"{pid}_{oid}_section_transverse_coupon_solid.stl")
            except Exception as exc:  # noqa: BLE001
                entry["objects"][oid] = {"status": "FAILED",
                                         "error": f"{type(exc).__name__}: {exc}"}
        sec_info["transverse_coupon"] = entry

    # 5. PNG renders (from shipped STL derivatives + new cut solids)
    renders = {}
    decim_log = {}
    obj_stls = object_stl_paths(model_dir, pid, manifest)
    stl_files = [p for _, p in obj_stls]
    oids = [o for o, _ in obj_stls]

    def _record_render(key, r):
        renders[key] = Path(r["png"]).name
        created.append(Path(r["png"]).name)
        if r.get("render_only_decimation"):
            decim_log[key] = r["render_only_decimation"]

    try:
        r = render_scene(stl_files, str(ev / f"{pid}_render_isometric.png"),
                         title=f"{pid} - {tech}",
                         subtitle="Isometric assembly view (all objects, world positions)",
                         view=(22, -60))
        _record_render("isometric", r)
    except Exception as exc:  # noqa: BLE001
        problems.append(f"isometric render: {type(exc).__name__}: {exc}")
    if len(stl_files) > 1:
        try:
            r = render_scene(stl_files, str(ev / f"{pid}_render_exploded.png"),
                             title=f"{pid} - {tech}",
                             subtitle="Exploded view (objects separated along their spread axis; part labels)",
                             view=(22, -60), explode=True,
                             labels=dict(enumerate(oids)))
            _record_render("exploded", r)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"exploded render: {type(exc).__name__}: {exc}")
    for plane, view in (("longitudinal", (12, 75)), ("transverse", (28, -60))):
        stl_list = section_stls[plane]
        if stl_list:
            try:
                r = render_scene(
                    stl_list, str(ev / f"{pid}_render_section_{plane}.png"),
                    title=f"{pid} - {tech}",
                    subtitle=(f"Section cutaway - "
                              f"{sec_info[plane]['plane']} (all cut parts)"),
                    view=view,
                    single_color=(0.31, 0.47, 0.65))
                _record_render(f"section_{plane}", r)
            except Exception as exc:  # noqa: BLE001
                problems.append(f"{plane} section render: {type(exc).__name__}: {exc}")
        else:
            problems.append(f"{plane} section render skipped: no cut-solid STLs")

    # 5b. coupon render (zoomed cross-section view)
    if coupon_stls:
        try:
            r = render_scene(
                coupon_stls, str(ev / f"{pid}_render_section_transverse_coupon.png"),
                title=f"{pid} - {tech}",
                subtitle=(f"Transverse section coupon at mid-length "
                          f"(stub L = {coupon_stub:.1f} mm) - the "
                          "invention-critical cross-section"),
                view=(62, -55),
                single_color=(0.31, 0.47, 0.65))
            _record_render("section_transverse_coupon", r)
        except Exception as exc:  # noqa: BLE001
            problems.append(f"coupon render: {type(exc).__name__}: {exc}")

    # 6. file inventory (shipped + new, hashed)
    inv = file_inventory(model_dir)
    (ev / "FILE_INVENTORY.json").write_text(json.dumps(inv, indent=1))
    created.append("FILE_INVENTORY.json")

    # 7. evidence readme
    readme = {
        "artifact": "3D_EVIDENCE_README",
        "purpose": ("this directory is the r384 3D EVIDENCE layer added in "
                    "response to the independent external re-review "
                    "('Toscanini 3D Technology Package Reality & "
                    "Design-Quality Review'). It adds section solids, PNG "
                    "renders, an independent regeneration check, a "
                    "parameter-to-measured-feature log, an independent "
                    "trimesh watertight re-check and a hashed file "
                    "inventory. Nothing outside this directory was modified."),
        "source_of_truth": ("MODEL/PARAMETRIC_MODEL_SOURCE.py + "
                            "MODEL/PARAMETERS.json (the parametric "
                            "definition); every file here is a derivative "
                            "with a real sha256"),
        "rebuild_executor": ("discovery_fabric.engine.cad_pipeline."
                             "_execute_build_program (the same deterministic "
                             "sandbox that built the shipped model)"),
        "render_policy": "RENDER_IS_NOT_VALIDATION (CEO R380 / Art. XXVIII)",
        "render_only_decimation": decim_log,
        "files_created": created,
        "problems": problems,
        "evidence_class": "COMPUTATIONAL_RESULT"}
    (ev / "3D_EVIDENCE_README.json").write_text(json.dumps(readme, indent=1))
    created.append("3D_EVIDENCE_README.json")

    counts = inv["counts_by_kind"]
    summary["augmentation"] = {
        "status": "AUGMENTED",
        "files_created": created,
        "problems": problems,
        "regeneration_status": regen["regeneration_status"],
        "watertight_status": wt["status"],
        "parameter_feature_coverage": {
            "parameters_total": pfl["parameters_total"],
            "with_linear_feature_match":
                pfl["parameters_with_linear_feature_match"]},
        "section_solids": sec_info,
        "renders": renders,
        "render_only_decimation": decim_log,
        "model_file_counts": counts,
    }
    return summary


def main() -> None:
    import time
    summaries = []
    sdir = BUILD_ROOT / "R384_SUMMARIES"
    sdir.mkdir(exist_ok=True)
    for tier in TIERS:
        tier_dir = BUILD_ROOT / tier
        if not tier_dir.is_dir():
            continue
        for folder in sorted(tier_dir.iterdir()):
            if not folder.is_dir():
                continue
            marker = folder / "MODEL" / "3D_EVIDENCE" / "3D_EVIDENCE_README.json"
            side = sdir / f"{folder.name}.json"
            if marker.exists() and side.exists():
                print(f"[r384] {tier}/{folder.name} SKIP (already complete)",
                      flush=True)
                continue
            t0 = time.time()
            print(f"[r384] {tier}/{folder.name} ...", flush=True)
            try:
                s = augment_package(tier, folder.name)
                summaries.append(s)
                (sdir / f"{folder.name}.json").write_text(json.dumps(s, indent=1))
            except Exception as exc:  # noqa: BLE001
                traceback.print_exc()
                err = {
                    "folder_name": folder.name, "tier": tier,
                    "augmentation": {"status": "ERROR",
                                     "error": f"{type(exc).__name__}: {exc}"}}
                summaries.append(err)
                (sdir / f"{folder.name}.json").write_text(json.dumps(err, indent=1))
            print(f"[r384]   -> {time.time()-t0:.1f}s", flush=True)
    # collect ALL summaries (sidecars written above; earlier runs re-loaded)
    for tier in TIERS:
        tier_dir = BUILD_ROOT / tier
        if not tier_dir.is_dir():
            continue
        for folder in sorted(tier_dir.iterdir()):
            if not folder.is_dir() or folder.name in {s.get("folder_name")
                                                      for s in summaries}:
                continue
            side = sdir / f"{folder.name}.json"
            if side.exists():
                summaries.append(json.load(open(side)))
    out = {"artifact": "R384_3D_EVIDENCE_SUMMARY",
           "generated_at": utc_now(),
           "trigger": ("independent external re-review verdict FAIL "
                       "(0 CAD/mesh/image files in every package of the "
                       "audited V2 artifact) — this summary records the "
                       "3D evidence layer of the CURRENT release tree, "
                       "now shipped as the 3D-EVIDENCE edition"),
           "packages": sorted(summaries, key=lambda s: s["folder_name"])}
    (BUILD_ROOT / "R384_3D_EVIDENCE_SUMMARY.json").write_text(
        json.dumps(out, indent=1))
    ok = [s for s in summaries
          if s.get("augmentation", {}).get("status") == "AUGMENTED"]
    na = [s for s in summaries
          if s.get("3d_design_status") == "NOT_APPLICABLE"]
    print(f"[r384] augmented {len(ok)}/15, not-applicable {len(na)}, "
          f"total {len(summaries)}")


if __name__ == "__main__":
    main()
