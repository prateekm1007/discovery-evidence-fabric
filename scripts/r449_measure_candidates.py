"""R449: measure a generated candidate GLB set against the canonical cases.

Runs the SAME instruments with the SAME seeds used by the negative controls
(Art. XLVII baseline supremacy - identical instrument both arms):
  - normalized chamfer p95 / canonical bbox diag + sorted-axis dimension
    deviation + volume deviation (metrics.compare)
  - component-name recall/precision over canonical mesh-node identity sets
  - per-component pose deltas (centroid displacement, sorted-dims deviation)
  - six-view occupancy IoU (self-consistency + cross-view agreement)
Raw numbers only; no thresholds (PENDING_OWNER_RATIFICATION).
"""
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "visual-lab" / "benchmark"))

import canonical_inputs as ci  # noqa: E402
import metrics as M  # noqa: E402
from negative_controls import _component_pose_delta, _projected_views, _view_agreement  # noqa: E402

import trimesh  # noqa: E402

OUT = Path("/home/z/my-project/hf_space/R449")
BUCKET = "prateekm1/toscanini-visual-lab-benchmarks"


def _scene_mesh(scene):
    meshes = [g for g in scene.geometry.values() if hasattr(g, "vertices")]
    if not meshes:
        raise M.FailClosedError("scene has no geometry")
    return meshes[0] if len(meshes) == 1 else trimesh.util.concatenate(meshes)


def measure_case(letter: str, candidate_path: Path) -> dict:
    import tempfile

    canon_scene = trimesh.load(str(ci.case_glb_path(letter)), process=False)
    cand_scene = trimesh.load(str(candidate_path), process=False)
    canon_mesh, cand_mesh = _scene_mesh(canon_scene), _scene_mesh(cand_scene)

    cmp_res = M.compare(canon_mesh, cand_mesh)["metrics"]

    canon_names = set(n for n in ci.mesh_node_names(ci.parse_glb(ci.case_glb_path(letter))) if n)
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as tf:
        cand_scene.export(tf.name)
        cand_parsed = ci.parse_glb(tf.name)
    cand_names = set(n for n in ci.mesh_node_names(cand_parsed) if n)
    recall = len(canon_names & cand_names) / len(canon_names) if canon_names else None
    precision = (len(canon_names & cand_names) / len(cand_names)) if cand_names else 0.0

    pose = _component_pose_delta(letter, Path(candidate_path))

    views_c = _projected_views(canon_mesh)
    views_k = _projected_views(cand_mesh)
    view_agree = _view_agreement(views_c, views_k)

    v = np.asarray(cand_mesh.vertices)
    return {
        "case": letter,
        "candidate_glb_sha256": M.sha256_file(candidate_path) if hasattr(M, "sha256_file") else __import__("hashlib").sha256(Path(candidate_path).read_bytes()).hexdigest(),
        "geometry_preservation": {
            "normalized_chamfer_p95_over_diag": cmp_res["normalized_chamfer_p95_over_diag"],
            "chamfer_p95": cmp_res["chamfer_p95"],
            "chamfer_mean": cmp_res.get("chamfer_mean"),
            "dimension_deviation_pct": cmp_res["dimension_deviation"]["per_axis_deviation_pct"],
            "max_abs_axis_deviation_pct": cmp_res["dimension_deviation"]["max_abs_axis_deviation_pct"],
            "volume_deviation_pct": cmp_res["volume_deviation_pct"],
        },
        "component_identity": {
            "canonical_components": sorted(canon_names),
            "candidate_components": sorted(cand_names),
            "candidate_component_count": len(cand_names),
            "canonical_component_count": len(canon_names),
            "recall": recall,
            "precision": precision,
            "identity_set_preserved": canon_names == cand_names,
        },
        "topology": {
            "candidate_triangles": int(sum(len(f) for f in [cand_mesh.faces])) if hasattr(cand_mesh, "faces") else None,
            "candidate_watertight": bool(getattr(cand_mesh, "is_watertight", False)),
        },
        "component_pose_deltas": pose,
        "six_view_agreement_canonical_vs_candidate_iou": view_agree,
        "candidate_bbox": {"min": v.min(0).tolist(), "max": v.max(0).tolist()},
    }


def main() -> int:
    from huggingface_hub import hf_hub_download

    token = "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"
    results = {"artifact_type": "R449_CANDIDATE_MEASUREMENTS_HUNYUAN3D_OMNI",
               "round": "R449-C2", "created_at": "2026-09-12",
               "reviewer_provenance": "AI_REVIEW",
               "candidate": "tencent/Hunyuan3D-Omni @70e803bf (point+view conditioning, seed 1234)",
               "threshold_policy": "raw measurements only - PENDING_OWNER_RATIFICATION",
               "measurements": {}, "missing": []}
    for letter in "ABC":
        try:
            p = hf_hub_download(repo_id=BUCKET, repo_type="dataset",
                                filename=f"benchmarks/R449/outputs/hunyuan3d_omni/case_{letter}_generated.glb",
                                token=token, force_download=True)
            results["measurements"][letter] = measure_case(letter, Path(p))
            m = results["measurements"][letter]
            print(f"case {letter}: chamfer_p95/diag={m['geometry_preservation']['normalized_chamfer_p95_over_diag']:.4f} "
                  f"recall={m['component_identity']['recall']} "
                  f"maxdim%={m['geometry_preservation']['max_abs_axis_deviation_pct']:.2f} "
                  f"views_iou={m['six_view_agreement_canonical_vs_candidate_iou']:.3f}")
        except Exception as e:  # noqa: BLE001
            results["missing"].append({"case": letter, "error": f"{type(e).__name__}: {e}"})
            print(f"case {letter}: unavailable - {type(e).__name__}")
    results["epistemic_status"] = ("VERIFIED" if len(results["measurements"]) == 3
                                   else ("PARTIAL" if results["measurements"] else "NOT_RUN"))
    (OUT / "CANDIDATE_MEASUREMENTS_HUNYUAN3D_OMNI.json").write_text(json.dumps(results, indent=2, default=str) + "\n")
    print("wrote CANDIDATE_MEASUREMENTS_HUNYUAN3D_OMNI.json; status:", results["epistemic_status"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
