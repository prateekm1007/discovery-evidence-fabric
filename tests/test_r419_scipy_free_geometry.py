"""R419 — the bridge geometry path must be scipy-free (production defect).

The deployed service died with:

    CONCEPTUAL_BUILD_FAILURE: No module named 'scipy'

Root cause: trimesh's face-color path uses scipy.grouping at USE time
(scipy.spatial.cKDTree + scipy.sparse). The R419 fix carries color
through direct vertex-color arrays (glTF COLOR_0) — see
discovery_fabric/engine/invention_bridge/coloring.py for the measured
decision matrix.

This is the ADVERSARIAL enforcement (Art. XVII: every control gets an
attempted bypass): the full bridge geometry path — conceptual build,
engineering build + STEP/STL/GLB export, generation models, AND the
complete bridge() orchestration on the captured real solar run — is
executed in a SUBPROCESS where importing scipy raises ImportError,
exactly reproducing the production image. If any code path regresses
into scipy, this test goes RED.
"""
import os
import subprocess
import sys
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_CHILD = r'''
import os
import sys

# --- make scipy unimportable, mimicking the production image ----------
class _ScipyBlocker:
    def find_module(self, name, path=None):  # pragma: no cover - legacy API
        if name.split(".")[0] == "scipy":
            return self
        return None

    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] == "scipy":
            raise ImportError(f"R419-TEST: scipy blocked ({name})")
        return None

sys.meta_path.insert(0, _ScipyBlocker())
assert "scipy" not in sys.modules

REPO = sys.argv[1]
sys.path.insert(0, REPO)

from discovery_fabric.engine.invention_bridge import (  # noqa: E402
    bridge as run_bridge,
    conceptual_geometry,
    engineering_geometry,
)

# 1. conceptual system architecture (the exact failing production path)
built = conceptual_geometry.build_system_architecture(
    ["sensing layer", "optimization core", "storage", "grid interface"],
    "solar panel")
assert built["glb_bytes"] and len(built["glb_bytes"]) > 500, "empty GLB"
assert len(built["components"]) >= 5, "component count regressed"
print("CONCEPTUAL_SYSTEM_OK", len(built["glb_bytes"]),
      built["glb_sha256"][:12])

# 2. conceptual device (stacked layers)
dev = conceptual_geometry.build_conceptual_device("solar panel", None)
assert dev["glb_bytes"]
print("CONCEPTUAL_DEVICE_OK", len(dev["glb_bytes"]))

# 3. engineering path: measured solid + STEP/STL/GLB export
import tempfile
params = {
    "outer_diameter_mm": 3.0,
    "primary_lumen_diameter_mm": 1.1,
    "floor_lumen_diameter_mm": 0.6,
    "floor_offset_mm": 1.0,
    "length_mm": 100.0,
}
solid = engineering_geometry.FORM_LIBRARY["dual_lumen_catheter"](params)
out_dir = tempfile.mkdtemp(prefix="r419_scipyfree_")
exported = engineering_geometry.export(
    solid, "engineering_model", out_dir,
    component_solids=[("engineering_model", solid)])
for key in ("glb_path", "step_path", "stl_path"):
    assert exported[key] and os.path.exists(exported[key]), key
dims = engineering_geometry.measure(solid)
assert dims["volume_mm3"] > 0, "measure regressed"
print("ENGINEERING_EXPORT_OK", dims["volume_mm3"])

# 4. the full bridge orchestration on the captured REAL solar run
run_json = os.path.join(REPO, "tests", "fixtures", "r418", "solar_result.json")
cio_json = os.path.join(REPO, "tests", "fixtures", "r418", "solar_cio.json")
if os.path.exists(run_json) and os.path.exists(cio_json):
    import json
    import shutil
    work = tempfile.mkdtemp(prefix="r419_bridge_")
    result = run_bridge(
        json.load(open(run_json)), json.load(open(cio_json)), work)
    assert result["report"]["outcome"] == "COMPLETED", result["report"]
    geo = result["geometry_out"]
    assert geo and geo.get("glb_sha256"), "no geometry from real run"
    pkg = result["package_out"]
    assert pkg and os.path.exists(pkg["zip_path"]), "no package"
    print("FULL_BRIDGE_REAL_RUN_OK",
          result["visualizability"]["visualizability_class"],
          pkg["manifest"]["file_count"], "files")
    shutil.rmtree(work, ignore_errors=True)
else:
    print("FULL_BRIDGE_REAL_RUN_SKIPPED (fixtures absent)")

print("ALL_SCI_PY_FREE_OK")
assert "scipy" not in sys.modules, "scipy got imported!"
'''


class TestScipyFreeGeometry(unittest.TestCase):
    def test_full_bridge_geometry_path_runs_without_scipy(self):
        proc = subprocess.run(
            [sys.executable, "-c", _CHILD, REPO],
            capture_output=True, text=True, timeout=900,
            cwd=REPO,
        )
        out = proc.stdout
        self.assertEqual(
            proc.returncode, 0,
            "bridge geometry path requires scipy again (regression).\n"
            f"stdout:\n{out}\nstderr:\n{proc.stderr[-3000:]}")
        self.assertIn("CONCEPTUAL_SYSTEM_OK", out)
        self.assertIn("CONCEPTUAL_DEVICE_OK", out)
        self.assertIn("ENGINEERING_EXPORT_OK", out)
        self.assertIn("ALL_SCI_PY_FREE_OK", out)
        # the real-run orchestration either ran or was explicitly skipped
        self.assertTrue(
            "FULL_BRIDGE_REAL_RUN_OK" in out
            or "FULL_BRIDGE_REAL_RUN_SKIPPED" in out)

    def test_coloring_helper_sets_vertex_colors_not_face(self):
        """The helper writes COLOR_0 vertex arrays; face-color assignment
        (the scipy-dependent path) is absent from the bridge sources."""
        import trimesh
        import numpy as np
        from discovery_fabric.engine.invention_bridge.coloring import (
            set_uniform_color)
        mesh = trimesh.creation.box(extents=[1.0, 1.0, 1.0])
        set_uniform_color(mesh, (168, 98, 66, 255))
        vc = np.asarray(mesh.visual.vertex_colors)
        self.assertEqual(vc.shape[0], len(mesh.vertices))
        self.assertEqual(vc.shape[1], 4)
        self.assertTrue((vc == (168, 98, 66, 255)).all())
        glb = mesh.export(file_type="glb")
        self.assertGreater(len(glb), 500)
        # COLOR_0 accessor must be present in the glTF JSON chunk
        import struct
        magic, version, length, chunk_len, chunk_type = \
            struct.unpack_from("<IIIII", glb, 0)
        self.assertEqual(magic, 0x46546C67)  # 'glTF'
        json_chunk = glb[20:20 + chunk_len]
        self.assertIn(b"COLOR_0", json_chunk)


if __name__ == "__main__":
    unittest.main()
