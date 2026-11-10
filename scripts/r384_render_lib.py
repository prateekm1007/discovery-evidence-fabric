"""r384_render_lib — raster render helpers for the 3D EVIDENCE edition.

Renders PNG images FROM THE SHIPPED STL MESH DERIVATIVES (and from the
r384 section-cut solids). A render is PRESENTATION, never engineering
validation (CEO R380 / Art. XXVIII) — every image carries that footer.
"""
from __future__ import annotations

import textwrap
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np
import trimesh

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

# tableau-muted palette, one color per object
PALETTE = [
    (0.31, 0.47, 0.65),  # steel blue
    (0.95, 0.56, 0.17),  # orange
    (0.35, 0.63, 0.31),  # green
    (0.88, 0.34, 0.35),  # red
    (0.46, 0.72, 0.70),  # teal
    (0.69, 0.48, 0.63),  # purple
    (0.60, 0.60, 0.60),  # grey
]

FOOTER = ("Units: mm  |  Source: shipped STL mesh derivative (cadquery-occt)  |  "
          "RENDER IS PRESENTATION, NOT ENGINEERING VALIDATION (R380)")


def decimate(mesh: trimesh.Trimesh,
             target_faces: int = 35000
             ) -> Tuple[trimesh.Trimesh, Optional[dict]]:
    """Deterministic render-only decimation by vertex clustering.

    Used ONLY for raster rendering of very dense shipped meshes (e.g. a
    605k-face helical antenna): vertices are snapped to a uniform voxel
    grid and averaged, degenerate/duplicate faces dropped. The shipped
    STL on disk is NEVER modified. Render-only — not an engineering
    artifact."""
    n = len(mesh.faces)
    if n <= target_faces:
        return mesh, None
    v = np.asarray(mesh.vertices, dtype=float)
    f = np.asarray(mesh.faces, dtype=np.int64)
    area = float(mesh.area)
    h = max(np.sqrt(2.0 * area / target_faces), 1e-9)
    origin = v.min(axis=0)
    info = None
    for _ in range(8):
        key = np.floor((v - origin) / h).astype(np.int64)
        uniq, inv = np.unique(key, axis=0, return_inverse=True)
        new_v = np.zeros((len(uniq), 3))
        np.add.at(new_v, inv, v)
        counts = np.bincount(inv, minlength=len(uniq))
        new_v = new_v / counts[:, None]
        new_f = inv[f]
        keep = ((new_f[:, 0] != new_f[:, 1]) & (new_f[:, 1] != new_f[:, 2])
                & (new_f[:, 0] != new_f[:, 2]))
        new_f = new_f[keep]
        fs = np.sort(new_f, axis=1)
        _, idx = np.unique(fs, axis=0, return_index=True)
        new_f = new_f[np.sort(idx)]
        out = trimesh.Trimesh(vertices=new_v, faces=new_f, process=False)
        info = {"render_only_decimation": {
            "original_faces": int(n),
            "decimated_faces": int(len(out.faces)),
            "voxel_mm": round(float(h), 6),
            "note": "shipped STL on disk is untouched"}}
        if len(out.faces) <= target_faces * 1.25 or len(out.faces) < 200:
            return out, info
        h *= 1.7
    return out, info


def load_mesh(path: str) -> trimesh.Trimesh:
    m = trimesh.load_mesh(path, force="mesh")
    if not isinstance(m, trimesh.Trimesh):
        raise TypeError(f"not a single mesh: {path}")
    return m


def _shaded_facecolors(mesh: trimesh.Trimesh,
                       base_rgb: Tuple[float, float, float],
                       light: Tuple[float, float, float] = (0.35, -0.55, 0.75)
                       ) -> np.ndarray:
    n = np.asarray(mesh.face_normals, dtype=float)
    ln = np.array(light, dtype=float)
    ln = ln / np.linalg.norm(ln)
    lam = n @ ln
    if not bool(mesh.is_watertight):
        lam = np.abs(lam)  # two-sided shading for open section half-shells
    inten = 0.32 + 0.68 * np.clip(lam, 0.0, 1.0)
    cols = np.empty((len(n), 4))
    cols[:, 0] = base_rgb[0] * inten
    cols[:, 1] = base_rgb[1] * inten
    cols[:, 2] = base_rgb[2] * inten
    cols[:, 3] = 1.0
    return np.clip(cols, 0, 1)


def _explode(meshes: List[trimesh.Trimesh],
             gap_frac: float = 0.18) -> List[trimesh.Trimesh]:
    """Separate meshes along the axis of largest center variance."""
    if len(meshes) < 2:
        return list(meshes)
    centers = np.array([m.bounds.mean(axis=0) for m in meshes])
    axis = int(np.argmax(centers.std(axis=0)))
    sizes = np.array([m.extents[axis] for m in meshes])
    gap = gap_frac * float(max(sizes.max(), 1e-6))
    order = np.argsort(centers[:, axis])
    start = centers[:, axis].min() - 0.5 * gap
    new_pos: Dict[int, float] = {}
    cursor = start
    for idx in order:
        cursor += sizes[idx] / 2.0
        new_pos[idx] = cursor
        cursor += sizes[idx] / 2.0 + gap
    out: List[trimesh.Trimesh] = []
    for idx, m in enumerate(meshes):
        m2 = m.copy()
        delta = np.zeros(3)
        delta[axis] = new_pos[idx] - centers[idx, axis]
        m2.apply_translation(delta)
        out.append(m2)
    return out


def render_scene(mesh_paths: Sequence[str],
                 out_png: str,
                 title: str,
                 subtitle: str,
                 view: Tuple[float, float] = (22, -60),
                 explode: bool = False,
                 labels: Optional[Dict[int, str]] = None,
                 single_color: Optional[Tuple[float, float, float]] = None,
                 footer: str = FOOTER) -> dict:
    """Render one PNG scene from one or more STL meshes."""
    meshes = [load_mesh(p) for p in mesh_paths]
    decim_info = {}
    meshes = []
    for p in mesh_paths:
        m = load_mesh(p)
        m2, info = decimate(m)
        if info:
            decim_info[Path(p).name] = info
        meshes.append(m2)
    if explode and len(meshes) > 1:
        meshes = _explode(meshes)
    fig = plt.figure(figsize=(9.2, 7.0), constrained_layout=True)
    ax = fig.add_subplot(111, projection="3d")
    all_min = np.full(3, np.inf)
    all_max = np.full(3, -np.inf)
    for i, m in enumerate(meshes):
        base = single_color or PALETTE[i % len(PALETTE)]
        tris = np.asarray(m.triangles)
        pc = Poly3DCollection(
            tris,
            facecolors=_shaded_facecolors(m, base),
            edgecolors=np.array([*base]) * 0.55,
            linewidths=0.10,
        )
        ax.add_collection3d(pc)
        all_min = np.minimum(all_min, m.bounds[0])
        all_max = np.maximum(all_max, m.bounds[1])
        if labels and i in labels:
            c = m.bounds.mean(axis=0)
            ax.text(c[0], c[1], c[2], labels[i], fontsize=7.5,
                    color=(0.15, 0.15, 0.15), ha="center", va="center")
    pad = 0.04 * float(np.max(all_max - all_min)) + 1e-6
    ax.set_xlim(all_min[0] - pad, all_max[0] + pad)
    ax.set_ylim(all_min[1] - pad, all_max[1] + pad)
    ax.set_zlim(all_min[2] - pad, all_max[2] + pad)
    extents = np.maximum(all_max - all_min + 2 * pad, 1e-6)
    m_ = float(np.max(extents))
    ax.set_box_aspect((extents[0] / m_, extents[1] / m_, extents[2] / m_))
    ax.view_init(elev=view[0], azim=view[1])
    ax.set_xlabel("x (mm)", fontsize=8, labelpad=1)
    ax.set_ylabel("y (mm)", fontsize=8, labelpad=1)
    ax.set_zlabel("z (mm)", fontsize=8, labelpad=1)
    ax.tick_params(labelsize=7, pad=1)
    ax.grid(True, alpha=0.25)
    ttl = "\n".join(textwrap.wrap(title, width=64)[:2])
    ax.set_title(ttl + "\n" + subtitle, fontsize=10.5, pad=8)
    fig.text(0.5, 0.012, footer, ha="center", fontsize=7.0,
             color=(0.35, 0.35, 0.35))
    fig.savefig(out_png, dpi=150, facecolor="white",
                metadata={"Software": "r384 evidence render (matplotlib/trimesh)"})
    plt.close(fig)
    return {"png": out_png, "meshes": len(meshes),
            "render_only_decimation": decim_info}
