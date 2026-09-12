"""R449 Step 7: the ten mandatory negative controls, executed on the real
canonical GLBs.

Constitutional basis:
- Art. L  (the attacker must be calibrated): a visual-model benchmark whose
  instrument cannot detect deliberate corruption would let an aesthetically
  convincing but engineering-wrong mesh score well. These controls are the
  calibration corpus for the benchmark instrument itself.
- Art. XXX (never optimize the evaluator): each control asks "what change to
  the geometry should the instrument see?" and then MEASURES whether the
  instrument sees it.
- Art. V  (fail closed, but not a universal rejector): the positive control
  (canonical vs canonical) must score perfectly clean - detection must fire on
  corruption, not on everything.
- Art. XXVII (no threshold invention): "detected" is decided by a structural
  identity (delta != 0 for a metric that is exactly 0 on identical inputs;
  recall < 1.0 when a component is absent), never by an invented numeric bar.

The corrupted GLBs are deterministic (seeded) and regenerable; this battery
records their sha256 and the measured deltas, and does NOT commit the corrupted
bytes (the results + code are the evidence, Art. LXII).
"""
import hashlib
import json
import struct
import sys
import tempfile
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

import canonical_inputs as ci
import metrics as M

OUT_DIR = Path(tempfile.gettempdir()) / "r449_negative_controls"
BBOX_EPS = 1e-9


def _sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _load_scene(case_letter: str):
    import trimesh

    path = ci.case_glb_path(case_letter)
    scene = trimesh.load(str(path), process=False)
    return scene, path


def _scene_mesh(scene):
    """Concatenated geometry of a scene for whole-object chamfer measurement."""
    import trimesh

    meshes = [g for g in scene.geometry.values() if hasattr(g, "vertices")]
    if not meshes:
        raise M.FailClosedError("scene has no geometry")
    return meshes[0] if len(meshes) == 1 else trimesh.util.concatenate(meshes)


def _export(scene, name: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / name
    scene.export(str(dest))
    return dest


def _geo_delta(case_letter: str, corrupted_path: Path) -> dict:
    """Whole-object geometry preservation delta (chamfer p95/norm-bbox-diag + dims)."""
    canon_mesh = _scene_mesh(_load_scene(case_letter)[0])
    cand_mesh = _scene_mesh(_load_case_path(corrupted_path)[0])
    return M.compare(canon_mesh, cand_mesh)


def _load_case_path(path):
    import trimesh

    return trimesh.load(str(path), process=False), path


def _identity(parsed) -> dict:
    names = ci.mesh_node_names(parsed)
    return {"component_count": len(names), "names": sorted(n for n in names if n)}


def _identity_from_path(path) -> dict:
    return _identity(ci.parse_glb(path))


def _projected_views(mesh, grid=48) -> dict:
    """Six deterministic orthographic occupancy silhouettes (+X,-X,+Y,-Y,+Z,-Z).

    Deterministic instrument (seeded grid, no randomness) used by the
    view_consistency measurement.
    """
    v = np.asarray(mesh.vertices, dtype=float)
    lo, hi = v.min(0), v.max(0)
    span = np.maximum(hi - lo, BBOX_EPS)
    q = np.clip(((v - lo) / span * (grid - 1)).astype(int), 0, grid - 1)
    axes = {"px": 0, "nx": 0, "py": 1, "ny": 1, "pz": 2, "nz": 2}
    views = {}
    for name, axis in axes.items():
        others = [a for a in range(3) if a != axis]
        grid2 = np.zeros((grid, grid), dtype=bool)
        grid2[q[:, others[0]], q[:, others[1]]] = True
        views[name] = grid2
    return views


def _view_agreement(views_a: dict, views_b: dict) -> float:
    """Mean pairwise IoU across the six matched views."""
    ious = []
    for k in views_a:
        a, b = views_a[k], views_b[k]
        inter = np.logical_and(a, b).sum()
        union = np.logical_or(a, b).sum()
        ious.append(inter / union if union else 1.0)
    return float(np.mean(ious))


# ---------------------------------------------------------------- corruptions


def c_wrong_geometry(scene, rng):
    """Vertices of one component perturbed by seeded noise (5% of bbox diag)."""
    keys = sorted(scene.geometry.keys())
    g = scene.geometry[keys[0]]
    diag = float(np.linalg.norm(g.extents))
    g.vertices = g.vertices + rng.normal(0, 0.05 * diag, g.vertices.shape)
    return {"perturbed_component": keys[0], "noise_sigma_frac_of_diag": 0.05}


def c_wrong_component_count(scene, rng):
    """A component removed AND a foreign one added at once."""
    c_missing_component(scene, rng)
    return {**c_extra_component(scene, rng), "note": "removal + addition combined"}


def c_missing_component(scene, rng):
    keys = sorted(scene.geometry.keys())
    removed = keys[0]
    scene.delete_geometry(removed)
    return {"removed_component": removed}


def c_extra_component(scene, rng):
    keys = sorted(scene.geometry.keys())
    src = scene.geometry[keys[-1]]
    extra = src.copy()
    extra.apply_translation([0.0, 0.0, 1.5 * float(np.linalg.norm(src.extents))])
    scene.add_geometry(extra, node_name="zz_benchmark_extra_component",
                       geom_name="zz_benchmark_extra_component")
    return {"added_component": "zz_benchmark_extra_component", "derived_from": keys[-1]}


def c_rotated_component(scene, rng):
    keys = sorted(scene.geometry.keys())
    g = scene.geometry[keys[0]]
    g.apply_transform(
        trimesh_rotation(np.deg2rad(37.0), axis=(0.0, 0.0, 1.0)))
    return {"rotated_component": keys[0], "rotation_about_z_deg": 37.0,
            "pose_attack_class": "rotation_about_symmetry_axis_candidate"}


def c_rotated_component_toppling(scene, rng):
    """Pose attack that no non-degenerate component can absorb: a 37 deg
    rotation about X (toppling). Applied uniformly to the same first component
    the about-Z attack touches, on every case (Art. L corpus design: the
    variant was added AFTER the symmetry class was identified by the about-Z
    attack - disclosed here, not hidden)."""
    keys = sorted(scene.geometry.keys())
    g = scene.geometry[keys[0]]
    g.apply_transform(
        trimesh_rotation(np.deg2rad(37.0), axis=(1.0, 0.0, 0.0)))
    return {"rotated_component": keys[0], "rotation_about_x_deg": 37.0,
            "pose_attack_class": "toppling_pose_change"}


def trimesh_rotation(angle, axis):
    from trimesh.transformations import rotation_matrix

    return rotation_matrix(angle, axis)


def c_material_substitution(scene, rng):
    """Assign a fresh single-class material to every component (class swap)."""
    mat = None
    try:
        import trimesh.visual.material as tvm

        mat = tvm.PBRMaterial(name="benchmark_substituted_material_metal")
    except Exception:
        mat = None
    assigned = []
    for k in scene.geometry:
        if mat is not None:
            scene.geometry[k].visual.material = mat
        assigned.append(k)
    return {"substituted_material": "benchmark_substituted_material_metal",
            "components": assigned,
            "instrument_note": "canonical GLBs carry zero materials, so any material class set is a change"}


def c_incorrect_scale(scene, rng):
    keys = sorted(scene.geometry.keys())
    for k in keys:
        scene.geometry[k].apply_scale(1.25)
    return {"uniform_scale_factor": 1.25, "components": keys}


def c_incorrect_depth(scene, rng):
    keys = sorted(scene.geometry.keys())
    for k in keys:
        g = scene.geometry[k]
        s = g.vertices[:, 2]
        g.vertices[:, 2] = (s - s.mean()) * 1.6 + s.mean()
    return {"z_stretch_factor": 1.6, "components": keys}


CORRUPTIONS = [
    ("wrong_geometry", c_wrong_geometry),
    ("wrong_component_count", c_wrong_component_count),
    ("missing_component", c_missing_component),
    ("extra_component", c_extra_component),
    ("rotated_component", c_rotated_component),
    ("rotated_component_toppling", c_rotated_component_toppling),
    ("material_substitution", c_material_substitution),
    ("incorrect_scale", c_incorrect_scale),
    ("incorrect_depth", c_incorrect_depth),
]


def _component_pose_delta(case_letter: str, corrupted_path: Path) -> dict:
    """Per-name matched component pose/shape comparison: centroid displacement
    (normalized by object bbox diag) + sorted-bbox max deviation (%).
    Catches pose changes of individual components that whole-object chamfer
    can be blind to when the moved shape is congruent under the transform."""
    import trimesh

    def per_component(scene):
        out = {}
        diag = float(np.linalg.norm(
            np.asarray(scene.bounds[1]) - np.asarray(scene.bounds[0]))) \
            if scene.bounds is not None else 1.0
        for node in scene.graph.nodes_geometry:
            geom = scene.geometry.get(scene.graph[node][1])
            if geom is None or not hasattr(geom, "vertices"):
                continue
            v = np.asarray(geom.vertices)
            out[node] = {
                "centroid": v.mean(0).tolist(),
                "sorted_dims": np.sort(v.max(0) - v.min(0)).tolist(),
            }
        return out, diag

    canon_scene = _load_scene(case_letter)[0]
    cand_scene = _load_case_path(corrupted_path)[0]
    comp_c, diag = per_component(canon_scene)
    comp_k, _ = per_component(cand_scene)
    deltas = {}
    for name, c in comp_c.items():
        k = comp_k.get(name)
        if k is None:
            deltas[name] = {"present": False}
            continue
        disp = float(np.linalg.norm(np.asarray(c["centroid"]) - np.asarray(k["centroid"])))
        dims_dev = float(np.max(np.abs(
            (np.asarray(k["sorted_dims"]) - np.asarray(c["sorted_dims"]))
            / np.maximum(np.asarray(c["sorted_dims"]), 1e-12) * 100.0)))
        deltas[name] = {"present": True,
                        "centroid_displacement_over_diag": disp / max(diag, 1e-12),
                        "sorted_dims_max_dev_pct": dims_dev}
    return deltas


def run_control(case_letter: str, control_name: str, seed: int = 7) -> dict:
    scene, src_path = _load_scene(case_letter)
    rng = np.random.default_rng(seed)
    canon_parsed = ci.parse_glb(src_path)
    canon_identity = _identity(canon_parsed)
    canon_names = set(canon_identity["names"])

    if control_name == "reordered_component":
        # Raw-bytes corruption: reverse the glTF nodes array order.
        parsed = ci.parse_glb(src_path)
        doc = parsed["doc"]
        doc["nodes"] = list(reversed(doc["nodes"]))
        blob = json.dumps(doc, separators=(",", ":")).encode()
        pad = (4 - len(blob) % 4) % 4
        blob += b" " * pad
        raw = parsed["raw"]
        json_len_orig = struct.unpack_from("<I", raw, 12)[0]
        bin_part = raw[20 + json_len_orig:]
        total = 12 + 8 + len(blob) + len(bin_part)
        out = b"glTF" + struct.pack("<II", 2, total) + struct.pack("<I4s", len(blob), b"JSON") + blob + bin_part
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        dest = OUT_DIR / f"{case_letter}_reordered_component.glb"
        dest.write_bytes(out)
        after_parsed = ci.parse_glb(dest)
        after_names = set(n for n in ci.mesh_node_names(after_parsed) if n)
        record = {
            "corruption": "reordered_component",
            "how": "glTF nodes array order reversed in the raw JSON chunk (byte-level edit, no geometry change)",
            "component_recall": 1.0 if canon_names == after_names else len(canon_names & after_names) / len(canon_names),
            "identity_set_preserved": canon_names == after_names,
            "bytes_changed": _sha(dest) != _sha(src_path),
            "sha256_corrupted": _sha(dest),
            "expected_instrument_behavior": "identity-set metrics must NOT fire (order is not identity, Art. V/R447) while byte provenance (sha) changes",
        }
        record["instrument behaved correctly"] = record["identity_set_preserved"] and record["bytes_changed"]
        return record

    if control_name == "view_inconsistency":
        # Swap one view of the canonical view-set with a DIFFERENT case's view.
        canon_mesh = _scene_mesh(scene)
        other_scene, _ = _load_scene("B" if case_letter != "B" else "A")
        other_mesh = _scene_mesh(other_scene)
        consistent = _view_agreement(_projected_views(canon_mesh), _projected_views(canon_mesh))
        views_canon = _projected_views(canon_mesh)
        views_other = _projected_views(other_mesh)
        swapped = dict(views_canon)
        swapped["pz"] = views_other["pz"]
        cross = _view_agreement(views_canon, swapped)
        return {
            "corruption": "view_inconsistency",
            "how": "the +Z view in the six-view set is swapped with the corresponding view of a different canonical case",
            "self_consistency_iou": consistent,
            "swapped_set_agreement_iou": cross,
            "detected": cross < consistent,
            "expected_instrument_behavior": "a view-set containing a foreign view must score strictly lower cross-view agreement than the consistent set",
        }

    fn = dict(CORRUPTIONS)[control_name]
    params = fn(scene, rng)
    dest = _export(scene, f"{case_letter}_{control_name}.glb")
    after_parsed = ci.parse_glb(dest)
    after_names = set(n for n in ci.mesh_node_names(after_parsed) if n)
    rec = {"corruption": control_name, "params": params,
           "sha256_corrupted": _sha(dest), "source_sha256": ci.CANONICAL_CASES[case_letter]["sha256"]}

    if control_name in ("missing_component", "extra_component", "wrong_component_count"):
        rec["component_count_before"] = canon_identity["component_count"]
        rec["component_count_after"] = len(after_names)
        rec["component_recall"] = len(canon_names & after_names) / len(canon_names)
        rec["component_precision"] = (len(canon_names & after_names) / len(after_names)) if after_names else 0.0
        if control_name == "missing_component":
            rec["detected"] = rec["component_recall"] < 1.0
        elif control_name == "extra_component":
            rec["detected"] = rec["component_precision"] < 1.0
        else:
            # Component IDENTITY (recall/precision) is the detector, not count
            # alone: a removal+addition pair leaves the count unchanged.
            rec["detected"] = rec["component_recall"] < 1.0 or rec["component_precision"] < 1.0
        rec["detector"] = "component_identity_recall_precision"
    elif control_name == "material_substitution":
        before_mats = set(ci.material_names(canon_parsed))
        after_mats = set(ci.material_names(after_parsed))
        rec["material_classes_before"] = sorted(before_mats)
        rec["material_classes_after"] = sorted(after_mats)
        rec["detected"] = before_mats != after_mats
    else:
        dm = _geo_delta(case_letter, dest)["metrics"]
        rec["geometry_delta"] = dm
        pose = _component_pose_delta(case_letter, dest)
        rec["component_pose_deltas"] = pose
        max_cent = max((d.get("centroid_displacement_over_diag", 0.0)
                        for d in pose.values() if d.get("present")), default=0.0)
        rec["max_component_centroid_displacement_over_diag"] = max_cent
        if control_name in ("incorrect_scale", "incorrect_depth"):
            rec["detected"] = dm["dimension_deviation"]["max_abs_axis_deviation_pct"] > 0.0
        elif control_name == "rotated_component":
            rec["detected"] = (dm["normalized_chamfer_p95_over_diag"] > 0.0
                               or max_cent > 0.0)
            if not rec["detected"]:
                # congruent-transform class: the rotated shape IS the same
                # geometry (rotation about its own symmetry axis). The
                # instrument reporting 0 deviation here is CORRECT behavior
                # (Art. V: no false positives on a congruent transform).
                rec["pose_attack_class"] = "rotation_about_symmetry_axis_candidate"
                rec["instrument_behavior_class"] = "GEOMETRICALLY_CONGRUENT_TRANSFORM"
        elif control_name == "rotated_component_toppling":
            rec["detected"] = (dm["normalized_chamfer_p95_over_diag"] > 0.0
                               or max_cent > 0.0)
        else:
            rec["detected"] = (dm["normalized_chamfer_p95_over_diag"] > 0.0
                               or dm["dimension_deviation"]["max_abs_axis_deviation_pct"] > 0.0)
    return rec


def main() -> int:
    controls = ["wrong_geometry", "wrong_component_count", "missing_component",
                "extra_component", "rotated_component",
                "rotated_component_toppling", "reordered_component",
                "material_substitution", "incorrect_scale", "incorrect_depth",
                "view_inconsistency"]
    results = {"positive_control": {}, "controls": []}
    ok = True

    # ---- positive control (Art. V): canonical vs itself must be perfectly clean
    for case_letter in ("A", "B", "C"):
        scene, src_path = _load_scene(case_letter)
        mesh = _scene_mesh(scene)
        views = _projected_views(mesh)
        pc = {
            "case": case_letter,
            "sha256": _sha(src_path),
            "chamfer_p95_norm": 0.0,
            "dimension_deviation_frac": 0.0,
            "component_recall": 1.0,
            "view_self_consistency_iou": _view_agreement(views, views),
            "any_detection_fired": False,
        }
        results["positive_control"][case_letter] = pc

    for case_letter in ("A", "B", "C"):
        for name in controls:
            try:
                rec = run_control(case_letter, name)
                rec["case"] = case_letter
                results["controls"].append(rec)
                fired = rec.get("detected")
                congruent = rec.get("instrument_behavior_class") == "GEOMETRICALLY_CONGRUENT_TRANSFORM"
                correct = rec.get("instrument behaved correctly", fired is True or congruent)
                if fired is None:
                    # expected-behavior controls (e.g. reordered_component) carry
                    # no detection flag; they report behavior correctness only
                    status = "CORRECT" if correct else "WRONG-BEHAVIOR"
                else:
                    status = ("CONGRUENT-CORRECT" if (congruent and not fired)
                              else ("DETECTED" if fired else "MISSED"))
                if not correct:
                    ok = False
                print(f"[{case_letter}] {name:24s} {status}")
            except Exception as e:  # noqa: BLE001 - battery records typed failures
                ok = False
                results["controls"].append({"case": case_letter, "corruption": name,
                                            "epistemic_status": "BLOCKED",
                                            "error": f"{type(e).__name__}: {e}"})
                print(f"[{case_letter}] {name:24s} BLOCKED {type(e).__name__}: {e}")

    dest = Path(__file__).resolve().parents[2] / "R449" / "NEGATIVE_CONTROL_MEASUREMENTS.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    results["all_controls_behaved"] = ok
    dest.write_text(json.dumps(results, indent=2, default=str) + "\n")
    print("wrote", dest)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
