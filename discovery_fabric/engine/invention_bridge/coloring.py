"""Scipy-free uniform mesh coloring for the invention bridge.

R419 production defect (operator directive section 2):

    CONCEPTUAL_BUILD_FAILURE: No module named 'scipy'

Root cause (traced empirically, 2026-09-07):

    trimesh's ``ColorVisuals.face_colors`` setter converts through
    ``trimesh.grouping`` (unique_rows / group_rows), which uses
    ``scipy.spatial.cKDTree`` and ``scipy.sparse`` AT USE TIME. The
    production image does not install scipy, so every bridge path that
    set face colors died at export/copy time even though the conceptual
    geometry path needs NO numerical scipy functionality.

Measured matrix (scipy import blocked, trimesh 4.11.1):

    operation                                   result
    ------------------------------------------  ----------------------
    plain mesh GLB export                       OK
    mesh.copy() after face_colors               FAILS (scipy.sparse)
    GLB export after face_colors                FAILS (scipy.sparse)
    vertex_colors = (n,4) array                 OK
    GLB export after vertex_colors              OK (COLOR_0 attribute)
    multi-mesh named-node Scene export          OK (uncolored + vertex)

Decision (operator rule: "eliminate SciPy if the conceptual geometry
path does not actually need numerical SciPy functionality"):

    The bridge geometry path does not need numerical scipy. Color is
    carried through the glTF COLOR_0 vertex attribute instead — the
    same uniform component color, zero scipy involvement, and a
    smaller dependency surface on the production image. scipy is NOT
    added to requirements; the scipy-free property is enforced by an
    adversarial test (tests/test_r419_scipy_free_geometry.py) that
    runs the full bridge geometry path in a subprocess with scipy
    import-blocked (Art. XVII: every control gets an attempted bypass).
"""
from __future__ import annotations

import math
from typing import Sequence, Tuple

import numpy as np
import trimesh

Color = Tuple[int, int, int, int]

# CadQuery/OCCT author geometry Z-up; glTF (and every web viewer,
# including Three.js and Blender's importer) is Y-up. R419 measured the
# R418 defect: the bridge exported raw Z-up coordinates, so the flat
# substrate platform rendered as a VERTICAL WALL in the browser and in
# Blender. This single canonical rotation at export time makes ONE
# representation correct everywhere (Art. X).
_ROT_X = trimesh.transformations.rotation_matrix(
    -math.pi / 2.0, [1.0, 0.0, 0.0])


def apply_gltf_yup(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Rotate a Z-up-authored mesh into the glTF Y-up convention."""
    mesh.apply_transform(_ROT_X)
    return mesh


def set_uniform_color(mesh: trimesh.Trimesh, color: Sequence[int]) -> None:
    """Assign one uniform RGBA color to a mesh WITHOUT scipy.

    Writes the (n_vertices, 4) uint8 vertex-color array directly. For a
    uniform component color this is visually identical to the old
    face_colors assignment and exports through the glTF COLOR_0
    attribute (glTF 2.0 spec; Three.js GLTFLoader applies COLOR_0 with
    material.vertexColors automatically).
    """
    rgba = np.asarray(color, dtype=np.uint8).reshape(4)
    n = int(len(mesh.vertices))
    if n == 0:  # degenerate tessellation — nothing to color
        return
    mesh.visual.vertex_colors = np.tile(rgba, (n, 1))
