"""Toscanini Visual Lab - geometry fidelity metrics.

Real, reproducible geometry measurements comparing a candidate (AI-generated
presentation) mesh against the canonical GLB. These numbers quantify PRESENTATION
acceptance only; they never validate engineering truth (Constitution Art. XXVIII,
LXXII: a render never promotes the geometry's engineering status).

Implementation is numpy + trimesh only. If a dependency is missing the module
raises FailClosedError - it never returns invented numbers (Art. VI).
"""

import numpy as np


class FailClosedError(RuntimeError):
    """Raised when a measurement cannot be produced honestly."""


def _require_trimesh():
    try:
        import trimesh  # noqa: PLC0415
        return trimesh
    except ImportError as e:
        raise FailClosedError(
            "trimesh unavailable; refusing to fabricate geometry metrics"
        ) from e


def load_mesh(path):
    tm = _require_trimesh()
    mesh = tm.load(path, force="mesh")
    if mesh is None or len(mesh.faces) == 0:
        raise FailClosedError(f"no faces loaded from {path}")
    return mesh


def bbox_dims(mesh) -> np.ndarray:
    return np.asarray(mesh.extents, dtype=np.float64)


def surface_points(mesh, n=20000, seed=0) -> np.ndarray:
    """Deterministic surface sampling (seeded) for chamfer statistics."""
    tm = _require_trimesh()
    rs = np.random.RandomState(seed)
    state = rs.get_state()
    np.random.set_state(state)
    pts, _ = tm.sample.sample_surface(mesh, n)
    return np.asarray(pts, dtype=np.float64)


def _chunked_nn_dists(query: np.ndarray, ref: np.ndarray, chunk=512) -> np.ndarray:
    """Nearest-neighbor distances query->ref without scipy, chunked to bound
    memory. If scipy is available, cKDTree is used instead (faster)."""
    try:
        from scipy.spatial import cKDTree  # noqa: PLC0415
        return cKDTree(ref).query(query, k=1)[0]
    except ImportError:
        out = np.empty(query.shape[0], dtype=np.float64)
        for i in range(0, query.shape[0], chunk):
            block = query[i:i + chunk]
            d2 = ((block[:, None, :] - ref[None, :, :]) ** 2).sum(-1)
            out[i:i + chunk] = np.sqrt(d2.min(axis=1))
        return out


def chamfer_stats(pts_a: np.ndarray, pts_b: np.ndarray) -> dict:
    d_ab = _chunked_nn_dists(pts_a, pts_b)
    d_ba = _chunked_nn_dists(pts_b, pts_a)
    both = np.concatenate([d_ab, d_ba])
    return {
        "chamfer_mean": float(both.mean()),
        "chamfer_p95": float(np.percentile(both, 95)),
        "chamfer_max_hausdorff_approx": float(both.max()),
    }


def dimension_deviation_sorted(dims_a: np.ndarray, dims_b: np.ndarray) -> dict:
    """Rotation-invariant per-axis deviation: axes sorted by length on both
    sides, then compared. Returns sorted per-axis percent deviation."""
    sa, sb = np.sort(dims_a), np.sort(dims_b)
    denom = np.where(np.abs(sa) < 1e-12, 1e-12, sa)
    dev = (sb - sa) / denom * 100.0
    return {
        "dims_canonical_sorted": sa.tolist(),
        "dims_candidate_sorted": sb.tolist(),
        "per_axis_deviation_pct": dev.tolist(),
        "max_abs_axis_deviation_pct": float(np.abs(dev).max()),
    }


def volume_deviation_pct(mesh_a, mesh_b) -> float:
    va, vb = float(abs(mesh_a.volume)), float(abs(mesh_b.volume))
    denom = va if abs(va) > 1e-12 else 1e-12
    return (vb - va) / denom * 100.0


def compare(canonical_mesh, candidate_mesh, n=20000, seed=0) -> dict:
    dims = dimension_deviation_sorted(bbox_dims(canonical_mesh), bbox_dims(candidate_mesh))
    diag = float(np.linalg.norm(bbox_dims(canonical_mesh)))
    if diag < 1e-12:
        raise FailClosedError("canonical mesh has degenerate bounding box")
    ch = chamfer_stats(surface_points(canonical_mesh, n, seed),
                       surface_points(candidate_mesh, n, seed))
    return {
        "metrics": {
            "bbox_diag_canonical": diag,
            "dimension_deviation": dims,
            "volume_deviation_pct": volume_deviation_pct(canonical_mesh, candidate_mesh),
            **ch,
            "normalized_chamfer_p95_over_diag": ch["chamfer_p95"] / diag,
        },
        "measurement_provenance": {
            "sample_points": n,
            "seed": seed,
            "instrument": "visual-lab/metrics.py (trimesh + numpy; deterministic)",
            "metric_scope": "PRESENTATION_ACCEPTANCE_ONLY - never an engineering validation",
        },
    }
