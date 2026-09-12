"""R449: generate the deterministic benchmark reference inputs from the
canonical GLBs, and stage them for the HF Jobs visual benchmark lab.

Per case (A/B/C):
  - 6 orthographic reference projections (px/nx/py/ny/pz/nz) as PNGs
    (deterministic matplotlib point projection - the SAME renderer will be
    used on both arms of any comparison, Art. XLVII baseline supremacy)
  - 20,000-point seeded surface sample cloud (NPZ) for point-cloud-conditioned
    candidate generation (Hunyuan3D-Omni accepts point-cloud inputs)
  - a manifest with sha256 of every artifact + the source GLB sha

Everything derives from the R446/R447-verified canonical bytes. Nothing is
invented (Art. VI). The images are REFERENCE_RENDER role: crude by design,
deterministic, disclosed.
"""
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "visual-lab" / "benchmark"))

import canonical_inputs as ci  # noqa: E402
import metrics as M  # noqa: E402
import provenance as P  # noqa: E402

OUT = Path("/home/z/my-project/download/R449_reference_inputs")
GRID = 320


def sha(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def project_png(vertices: np.ndarray, axis: int, sign: int, dest: Path) -> None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    others = [a for a in range(3) if a != axis]
    x, y = vertices[:, others[0]], vertices[:, others[1]]
    if sign < 0:
        x = -x
    fig = plt.figure(figsize=(4, 4), dpi=80)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.scatter(x, y, s=0.35, c="k", linewidths=0)
    ax.set_axis_off()
    ax.set_aspect("equal")
    fig.savefig(dest, facecolor="white")
    plt.close(fig)


def main() -> int:
    import trimesh

    OUT.mkdir(parents=True, exist_ok=True)
    manifest = {"artifact_type": "R449_REFERENCE_INPUT_MANIFEST", "cases": {}}
    for letter in ("A", "B", "C"):
        spec = ci.CANONICAL_CASES[letter]
        glb_path = ci.case_glb_path(letter)
        scene = trimesh.load(str(glb_path), process=False)
        meshes = [g for g in scene.geometry.values() if hasattr(g, "vertices")]
        mesh = meshes[0] if len(meshes) == 1 else trimesh.util.concatenate(meshes)
        v = np.asarray(mesh.vertices, dtype=float)
        lo, hi = v.min(0), v.max(0)
        span = np.maximum(hi - lo, 1e-9)
        v01 = (v - lo) / span  # normalize to unit box for BOTH arms' renders

        case_dir = OUT / f"case_{letter}"
        case_dir.mkdir(exist_ok=True)
        views = {}
        for axis, aname in ((0, "x"), (1, "y"), (2, "z")):
            for sign, sname in ((1, "p"), (-1, "n")):
                dest = case_dir / f"view_{sname}{aname}.png"
                project_png(v01, axis, sign, dest)
                views[f"{sname}{aname}"] = {"png": dest.name, "sha256": sha(dest)}

        pts = M.surface_points(mesh, n=20000, seed=0)
        pts01 = (pts - lo) / span
        npz = case_dir / "surface_points_20k_seed0.npz"
        np.savez_compressed(npz, points=pts01.astype(np.float32))
        manifest["cases"][letter] = {
            "case_id": spec["case_id"],
            "source_glb": spec["glb_rel"],
            "source_glb_sha256": spec["sha256"],
            "vertex_count": int(len(v)),
            "views": views,
            "point_cloud": {"file": npz.name, "sha256": sha(npz),
                            "n_points": 20000, "seed": 0,
                            "normalization": "unit-box (bbox min/max of canonical vertices)"},
        }
        print(f"case {letter}: {len(views)} views + point cloud -> {case_dir}")

    man = OUT / "MANIFEST.json"
    side = {
        "source_glb_sha": "see per-case source_glb_sha256 (the R446/R447-verified canonical bytes)",
        "model_id": "none (deterministic projection of canonical geometry)",
        "model_revision": "n/a",
        "model_license": "n/a",
        "hf_space_or_job": "local sandbox (staging); jobs run on HF infrastructure",
        "hardware": "local CPU",
        "input_hash": sha(OUT / "MANIFEST.json") if man.exists() else "PENDING",
        "output_hash": "n/a (inputs, not outputs)",
        "timestamp": "2026-09-12",
        "benchmark_version": P.BENCHMARK_VERSION,
        "visual_role": "REFERENCE_RENDER",
    }
    man.write_text(json.dumps({"manifest": manifest, "provenance": side}, indent=2) + "\n")
    print("wrote", man)
    return 0


if __name__ == "__main__":
    sys.exit(main())
