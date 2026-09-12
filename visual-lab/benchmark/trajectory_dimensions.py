"""R450-C2: trajectory-understanding dimensions for the Visual Model
Benchmark Lab.

The operator directive upgraded the benchmark's evaluation question:

    Does the visual model improve human understanding of the engineering
    state WITHOUT introducing false engineering implications?

  ...not simply: does it produce a prettier mesh?

Four NEW dimensions join the R449 protocol (all deterministic instruments
over the canonical GLB bytes — no threshold invention: every value is
recorded raw, interpretation is PENDING_OWNER per Art. XXVII):

  1. before_after_correspondence  — does the BEFORE -> AFTER pairing keep
     component identity and make the recorded geometric delta VISIBLE?
     (directive §4/§10: same mutation -> expected delta visible; different
     mutation -> different delta visible)
  2. engineering_feature_visibility — are the declared engineering
     components (canonical node names, the R443 raw-identity discipline)
     spatially present and separable, i.e. visually knowable? measured from
     the GLB geometry itself, never from pixels.
  3. lineage_preservation — the R444 chain contract applied to benchmark
     artifacts: canonical root sha -> artifact sha hops must verify, or the
     verdict is INCOMPLETE/FAIL (missing evidence is never a pass, Art. XXV).
  4. artifact_determinism — the same input bytes yield the byte-identical
     measurement record (the instrument's determinism contract; the visual
     layer's contribution to Art. LXII reproducibility).

Every function is a pure measurement: the visual layer calculates NOTHING
that physics could claim, and returns raw numbers with the exact method
strings recorded beside them.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

_LAB = Path(__file__).resolve().parent
for _p in (str(_LAB), str(_LAB.parent / "trajectory")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import canonical_inputs as ci  # noqa: E402
from schema import record_sha256  # type: ignore  # noqa: E402

DIMENSIONS_VERSION = "1.0.0"


def _require_trimesh():
    try:
        import trimesh  # noqa: F401
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "trimesh unavailable — measurement cannot run (fail closed, "
            "never substitute a weaker instrument)") from e
    import trimesh
    return trimesh


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# 1. before / after correspondence
# ---------------------------------------------------------------------------

def before_after_correspondence(before_path: Path, after_path: Path,
                                n_samples: int = 20000, seed: int = 0
                                ) -> Dict[str, Any]:
    """Measure whether the BEFORE -> AFTER pairing preserves component
    identity and makes the geometric delta visible.

    Returns raw quantities only:
      node_jaccard              - |before ∩ after| / |before ∪ after| over
                                  mesh-node names (component identity kept?)
      nodes_only_before/after   - the unmatched names (identity changes made
                                  VISIBLE by this measure)
      per_axis_dim_deviation_pct- sorted-axis dimension deviation (the delta
                                  magnitude, rotation invariant)
      volume_deviation_pct      - signed volume change
      normalized_chamfer_p95    - surface delta p95 / before bbox diagonal
    """
    trimesh = _require_trimesh()
    before_parsed = ci.parse_glb(before_path)
    after_parsed = ci.parse_glb(after_path)
    before_nodes = [n for n in ci.mesh_node_names(before_parsed) if n]
    after_nodes = [n for n in ci.mesh_node_names(after_parsed) if n]
    sb, sa = set(before_nodes), set(after_nodes)
    union = sb | sa
    inter = sb & sa

    mesh_b = trimesh.load(str(before_path), force="scene", process=False)
    mesh_a = trimesh.load(str(after_path), force="scene", process=False)
    geom_b = mesh_b.to_mesh() if hasattr(mesh_b, "to_mesh") else mesh_b
    geom_a = mesh_a.to_mesh() if hasattr(mesh_a, "to_mesh") else mesh_a

    vb = np.asarray(geom_b.vertices, dtype=float)
    va = np.asarray(geom_a.vertices, dtype=float)
    db = vb.max(0) - vb.min(0)
    da = va.max(0) - va.min(0)
    diag_b = float(np.linalg.norm(db))

    from metrics import (chamfer_stats, dimension_deviation_sorted,  # type: ignore
                         surface_points, volume_deviation_pct)
    pb = surface_points(geom_b, n=n_samples, seed=seed)
    pa = surface_points(geom_a, n=n_samples, seed=seed)
    chamfer = chamfer_stats(pb, pa)
    dims = dimension_deviation_sorted(db, da)
    vol = volume_deviation_pct(geom_b, geom_a)

    return {
        "dimension_id": "before_after_correspondence",
        "method": ("loader-free glTF node identity + trimesh surface "
                   "measurement (deterministic, seed fixed)"),
        "before_sha256": _sha256_file(before_path),
        "after_sha256": _sha256_file(after_path),
        "node_jaccard": (len(inter) / len(union)) if union else 1.0,
        "matched_node_count": len(inter),
        "nodes_only_before": sorted(sb - sa),
        "nodes_only_after": sorted(sa - sb),
        "per_axis_dim_deviation_pct": dims["per_axis_deviation_pct"],
        "max_abs_axis_deviation_pct": dims["max_abs_axis_deviation_pct"],
        "volume_deviation_pct": vol,
        "normalized_chamfer_p95_over_diag":
            chamfer["chamfer_p95"] / diag_b if diag_b > 0 else None,
        "instrument": {
            "samples": n_samples, "seed": seed,
            "dimensions_version": DIMENSIONS_VERSION,
        },
    }


# ---------------------------------------------------------------------------
# 2. engineering feature visibility
# ---------------------------------------------------------------------------

def engineering_feature_visibility(glb_path: Path, grid: int = 48
                                   ) -> Dict[str, Any]:
    """Measure whether the declared engineering components are spatially
    present and separable in the canonical geometry — the preconditions
    for a component to be visually knowable at all.

    Per named component (canonical node names, R443 raw-identity
    discipline): vertex count, bbox extent, and the pairwise separation of
    component bounding boxes (gap fraction of the object diagonal —
    overlapping/enclosed parts separate poorly and that is REPORTED, not
    judged).
    """
    trimesh = _require_trimesh()
    scene = trimesh.load(str(glb_path), force="scene", process=False)
    parsed = ci.parse_glb(glb_path)
    names = [n for n in ci.mesh_node_names(parsed) if n]

    vertices_all = []
    per_component: List[Dict[str, Any]] = []
    for name, geom in scene.geometry.items():
        v = np.asarray(geom.vertices, dtype=float)
        if v.size == 0:
            continue
        lo, hi = v.min(0), v.max(0)
        vertices_all.append(v)
        per_component.append({
            "component_name": name,
            "vertex_count": int(len(v)),
            "bbox_min": [float(x) for x in lo],
            "bbox_max": [float(x) for x in hi],
        })
    if not vertices_all:
        raise RuntimeError(
            f"{glb_path}: no geometry — visibility is UNMEASURABLE, not "
            "zero (fail closed)")
    allv = np.vstack(vertices_all)
    lo_all, hi_all = allv.min(0), allv.max(0)
    diag = float(np.linalg.norm(hi_all - lo_all))

    # pairwise bbox separation: minimum gap (or overlap depth, negative)
    separations: List[Dict[str, Any]] = []
    comps = [c for c in per_component if c["vertex_count"] > 0]
    for i in range(len(comps)):
        for j in range(i + 1, len(comps)):
            a_lo, a_hi = np.array(comps[i]["bbox_min"]), np.array(comps[i]["bbox_max"])
            b_lo, b_hi = np.array(comps[j]["bbox_min"]), np.array(comps[j]["bbox_max"])
            gap_per_axis = np.maximum(b_lo - a_hi, a_lo - b_hi)
            gap = float(gap_per_axis.max())  # >0 -> separated on some axis
            separations.append({
                "pair": [comps[i]["component_name"], comps[j]["component_name"]],
                "bbox_gap_fraction_of_diag": (gap / diag) if diag > 0 else None,
                "separated": bool(gap > 0),
            })
    n_sep = sum(1 for s in separations if s["separated"])
    return {
        "dimension_id": "engineering_feature_visibility",
        "method": ("per-component bbox extent + pairwise bbox separation "
                   "fractions from the canonical GLB bytes (deterministic)"),
        "sha256": _sha256_file(glb_path),
        "declared_component_count": len(names),
        "components_with_geometry": len(comps),
        "object_bbox_diagonal": diag,
        "pairwise_separations": separations,
        "separated_pair_count": n_sep,
        "overlapping_pair_count": len(separations) - n_sep,
        "component_vertex_counts": {
            c["component_name"]: c["vertex_count"] for c in comps},
        "instrument": {"grid_reference": grid,
                       "dimensions_version": DIMENSIONS_VERSION},
    }


# ---------------------------------------------------------------------------
# 3. lineage preservation (the R444 chain contract, benchmark-side)
# ---------------------------------------------------------------------------

def lineage_preservation(chain: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Verify a declared hash chain: each hop {role, path, expected_sha256}
    must verify against the artifact's actual bytes. Missing evidence is
    INCOMPLETE, a mismatch is FAIL — never a pass (Art. XXV fail-closed).

    chain example:
      [{"role": "canonical_root_glb", "path": "...", "expected_sha256": "..."},
       {"role": "benchmark_candidate", "path": "...", "expected_sha256": "..."}]
    """
    hops: List[Dict[str, Any]] = []
    verdict = "VERIFIED"
    for hop in chain:
        role = hop.get("role")
        path = Path(hop.get("path") or "")
        expected = hop.get("expected_sha256")
        if not role or not path.exists() or not expected:
            hops.append({"role": role, "path": str(path),
                         "verdict": "INCOMPLETE",
                         "reason": ("missing path or expected hash — "
                                    "evidence absent, never presumed")})
            if verdict == "VERIFIED":
                verdict = "INCOMPLETE"
            continue
        actual = _sha256_file(path)
        ok = actual == expected
        hops.append({"role": role, "path": str(path),
                     "expected_sha256": expected, "actual_sha256": actual,
                     "verdict": "VERIFIED" if ok else "FAIL"})
        if not ok:
            verdict = "FAIL"
        elif verdict == "VERIFIED" and all(
                h.get("verdict") == "INCOMPLETE" for h in hops[:-1]):
            pass
    return {
        "dimension_id": "lineage_preservation",
        "method": ("sha256 re-measurement of every declared chain hop "
                   "(fail-closed: missing -> INCOMPLETE, mismatch -> FAIL)"),
        "hops": hops,
        "verdict": verdict,
        "dimensions_version": DIMENSIONS_VERSION,
    }


# ---------------------------------------------------------------------------
# 4. artifact determinism
# ---------------------------------------------------------------------------

def artifact_determinism(glb_path: Path, repeat: int = 3,
                         n_samples: int = 20000, seed: int = 0
                         ) -> Dict[str, Any]:
    """The same input bytes, measured `repeat` times, must yield the
    byte-identical measurement record. Any drift fails the dimension
    (the instrument is non-deterministic and its numbers carry no
    evidential weight until fixed — Art. LXII)."""
    records = []
    for _ in range(max(2, repeat)):
        vis = engineering_feature_visibility(glb_path)
        # strip the sha (constant anyway) and keep the measured body
        body = {k: v for k, v in vis.items() if k != "sha256"}
        records.append(record_sha256(body))
    return {
        "dimension_id": "artifact_determinism",
        "method": (f"{max(2, repeat)} repeated deterministic measurements "
                   "of the same bytes; record hashes compared"),
        "sha256": _sha256_file(glb_path),
        "record_hashes": records,
        "deterministic": len(set(records)) == 1,
        "repeat_count": max(2, repeat),
        "dimensions_version": DIMENSIONS_VERSION,
    }
