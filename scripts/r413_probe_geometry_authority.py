#!/usr/bin/env python3
"""r413_probe_geometry_authority.py — MEASURED probes for the geometry
authority boundary (R413, operator directive V2 Phase 4).

The operator's boundary, verbatim:
    "CadQuery is the engineering geometry authority; Blender is a
     downstream visualization/rendering system and cannot originate or
     independently validate engineering geometry."

Art. VI: authority is MEASURED, never assumed. This probe runs in a
CLEAN SUBPROCESS:
  - import cadquery + recorded version
  - a live parametric build (box + cylinder cut, deterministic)
    with closed-form volume verification (the authority must actually
    DO parametric engineering geometry here, not merely import)
  - Blender / bpy: re-cited from the solver availability probes
    (measured NOT_INSTALLED in this environment)

Output: R413/PHYSICS_STACK_V1/GEOMETRY_AUTHORITY_PROBES.json
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OUT_PATH = (REPO / "R413" / "PHYSICS_STACK_V1"
            / "GEOMETRY_AUTHORITY_PROBES.json")

_PROBE_CODE = r"""
import json, math, sys
try:
    import cadquery as cq
except Exception as e:  # pragma: no cover
    print(json.dumps({"result": "IMPORT_FAILED", "detail": repr(e)}))
    sys.exit(0)

# deterministic parametric build: 40x20x10 box with an r=3 through-hole
L, W, H, R = 40.0, 20.0, 10.0, 3.0
part = (cq.Workplane("XY").box(L, W, H)
        .faces(">Z").workplane().hole(2 * R))
solid = part.val()
volume = solid.Volume()
expected = L * W * H - math.pi * R * R * H
rel_err = abs(volume - expected) / expected
# bounding box sanity (the parametric dimensions must be exact)
bb = solid.BoundingBox()
bbox_ok = (abs(bb.xlen - L) < 1e-9 and abs(bb.ylen - W) < 1e-9
           and abs(bb.zlen - H) < 1e-9)
print(json.dumps({
    "result": "OPERATIONAL" if (rel_err < 1e-9 and bbox_ok)
              else "BUILD_MISMATCH",
    "cadquery_version": getattr(cq, "__version__", "unknown"),
    "build": {"box_mm": [L, W, H], "hole_radius_mm": R},
    "volume_mm3": volume,
    "closed_form_volume_mm3": expected,
    "rel_error": rel_err,
    "bbox_exact": bbox_ok,
    "n_faces": len(solid.Faces()),
}))
"""


def main() -> None:
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE_CODE],
        capture_output=True, text=True, timeout=180)
    try:
        cad = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        cad = {"result": "PROBE_CRASH",
               "detail": (proc.stderr or proc.stdout)[:400]}

    # blender: re-cited from the MEASURED solver probes (same env)
    solver_probes = json.loads(
        (REPO / "R413" / "PHYSICS_STACK_V1"
         / "SOLVER_AVAILABILITY_PROBES.json").read_text())
    blender = next(p for p in solver_probes["probes"]
                   if p["solver_id"] == "blender")

    doc = {
        "artifact_type": "R413_GEOMETRY_AUTHORITY_PROBES",
        "directive": "operator directive V2 Phase 4: CadQuery is the "
                     "engineering geometry authority; Blender is "
                     "downstream visualization only and cannot "
                     "originate or independently validate engineering "
                     "geometry",
        "measured_at": "2026-09-06",
        "probes": {
            "cadquery": {
                "probe": "CLEAN_SUBPROCESS_IMPORT_AND_PARAMETRIC_BUILD",
                "result": cad.get("result"),
                "cadquery_version": cad.get("cadquery_version"),
                "detail": cad.get("detail", ""),
                "parametric_build_verification": cad,
                "interpretation": "OPERATIONAL = the engineering "
                                  "geometry authority imports and "
                                  "executes parametric builds in this "
                                  "environment, with closed-form "
                                  "volume verification (the authority "
                                  "does real geometry here, measured)",
            },
            "blender": {
                "probe": blender["probe"],
                "result": blender["result"],
                "measured_at": blender["measured_at"],
                "detail": blender.get("detail", "")[:200],
                "interpretation": "the visualization layer is NOT "
                                  "installed in this environment "
                                  "(measured) — and by the operator's "
                                  "boundary it could never originate "
                                  "or validate engineering geometry "
                                  "anyway, installed or not",
            },
        },
        "boundary_test_vector": {
            "legitimate": "GEOMETRY_SPEC with geometry_authority="
                          "cadquery, geometry_hash, parameters",
            "forbidden": "GEOMETRY_SPEC with geometry_authority="
                         "blender (or any renderer-originated "
                         "geometry) — REJECTED_GEOMETRY_AUTHORITY",
            "forbidden_2": "a geometry VALIDATION record citing "
                           "blender as the validator — renders cannot "
                           "validate engineering geometry",
        },
        "reviewer_provenance": "AI_REVIEW",
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(doc, indent=1, ensure_ascii=False)
                        + "\n")
    import hashlib
    digest = hashlib.sha256(OUT_PATH.read_bytes()).hexdigest()
    print(f"wrote {OUT_PATH}")
    print(f"sha256: {digest}")
    print("cadquery:", cad.get("result"),
          "| version:", cad.get("cadquery_version"))
    print("blender:", blender["result"], "(measured, solver probes)")


if __name__ == "__main__":
    main()
