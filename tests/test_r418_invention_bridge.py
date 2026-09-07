"""Test suite for toscanini_bridge — required categories (handoff section 47,
scoped to the invention-to-3D-to-package path):

  * 3D: invention -> visualization (conceptual + engineering paths)
  * CIO: frontend cannot manufacture state (geometry/maturity only from bridge)
  * Epistemic honesty: CONCEPTUAL_3D != ENGINEERING_3D; no fabricated
    measurements; EXPERIMENTALLY VERIFIED only from reality loop
  * Evidence: claims map to recorded evidence structure
  * Provenance: every artifact traceable (manifest hashes)
  * Buyer package: contents consistent with the CIO
  * Determinism: same run state -> same GLB hash
  * Geometry failure -> diagnose -> repair (never silent "No 3D")

Run: python3 -m pytest tests/ -v  (or python3 -m pytest tests/test_r418_invention_bridge.py -v)
"""

import hashlib
import io
import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery_fabric.engine.invention_bridge import bridge as run_bridge
from discovery_fabric.engine.invention_bridge import classifier, epistemics  # noqa: E402
from discovery_fabric.engine.invention_bridge import conceptual_geometry, engineering_geometry  # noqa: E402

REAL_RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "r418", "solar_result.json")
REAL_CIO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures", "r418", "solar_cio.json")


def _solar_run():
    if not os.path.exists(REAL_RUN):
        raise unittest.SkipTest("real solar run JSON not captured")
    return json.load(open(REAL_RUN))


def _solar_cio():
    if not os.path.exists(REAL_CIO):
        raise unittest.SkipTest("real solar CIO JSON not captured")
    return json.load(open(REAL_CIO))


def _engineering_run():
    """Run state with sourced geometry parameters (P-07 released values)."""
    return {
        "session_id": "ts_test_eng",
        "user_text": "keep minimum drainage when primary lumen obstructs",
        "final_state": {"final_status": "EVOLVED_INVENTION_CANDIDATE",
                        "causal_chain": {"intervention_site": "catheter"}},
        "invention_specification": {
            "causal_chain": {"value": {"intervention_site": "dual lumen catheter"}},
            "problem": {"value": {"device": "dual lumen catheter"}}},
        "engineering_specification": {
            "parameters": [
                {"param_id": "outer_diameter_mm", "value": 3.0, "unit": "mm",
                 "envelope": [2.5, 3.5], "value_class": "MODELLED"},
                {"param_id": "primary_lumen_diameter_mm", "value": 1.1, "unit": "mm",
                 "envelope": [0.8, 1.4], "value_class": "MODELLED"},
                {"param_id": "floor_lumen_diameter_mm", "value": 0.6, "unit": "mm",
                 "envelope": [0.4, 0.8], "value_class": "MODELLED"},
                {"param_id": "floor_offset_mm", "value": 1.0, "unit": "mm",
                 "envelope": [0.7, 1.3], "value_class": "MODELLED"},
                {"param_id": "length_mm", "value": 100.0, "unit": "mm",
                 "envelope": [60, 140], "value_class": "MODELLED"},
            ],
            "system_architecture": {"subsystems": []},
            "engineering_core": {}},
        "run_state": {"generations": {"generations": []}},
        "evidence_pack": {"retrieval": []},
    }


# ---------------------------------------------------------------------------
# Classifier tests
# ---------------------------------------------------------------------------

class TestClassifier(unittest.TestCase):
    def test_real_solar_run_classifies_system_3d(self):
        vis = classifier.classify(_solar_run(), _solar_cio())
        self.assertEqual(vis["visualizability_class"], epistemics.SYSTEM_3D)
        self.assertEqual(len(vis["subsystems"]), 4)
        self.assertEqual(vis["intervention_site"], "solar panel")
        self.assertEqual(vis["classification_basis"]["geometry_parameters_sourced"], 0)

    def test_parameterized_run_classifies_engineering_3d(self):
        vis = classifier.classify(_engineering_run(), None)
        self.assertEqual(vis["visualizability_class"], epistemics.ENGINEERING_3D)
        self.assertGreaterEqual(
            vis["classification_basis"]["geometry_parameters_sourced"], 3)

    def test_pure_algorithm_not_visualizable(self):
        run = {"final_state": {"causal_chain": {
            "mechanism": "a new control law optimization protocol algorithm",
            "intervention_site": ""}},
            "engineering_specification": {"parameters": [],
                                          "system_architecture": {"subsystems": []}}}
        vis = classifier.classify(run, None)
        self.assertEqual(vis["visualizability_class"], epistemics.NOT_VISUALIZABLE)

    def test_classification_basis_is_recorded(self):
        vis = classifier.classify(_solar_run(), _solar_cio())
        basis = vis["classification_basis"]
        for key in ("geometry_parameters_sourced", "subsystems_recorded",
                    "physical_site_detected", "reason", "measured_from"):
            self.assertIn(key, basis)


# ---------------------------------------------------------------------------
# Conceptual geometry tests
# ---------------------------------------------------------------------------

class TestConceptualGeometry(unittest.TestCase):
    def test_build_is_deterministic(self):
        a = conceptual_geometry.build_system_architecture(
            ["sensor", "compute", "storage"], "solar panel")
        b = conceptual_geometry.build_system_architecture(
            ["sensor", "compute", "storage"], "solar panel")
        self.assertEqual(a["glb_sha256"], b["glb_sha256"])

    def test_key_dimensions_topology_only(self):
        out = conceptual_geometry.build_system_architecture(
            ["sensing stage", "transduction stage", "load interface"], "solar panel")
        with self.assertRaises(epistemics.EpistemicViolation):
            epistemics.guard_no_engineering_dimensions(
                epistemics.SYSTEM_3D,
                {**out["key_dimensions"], "volume_mm3": 123.0})
        # clean pass: no forbidden keys
        epistemics.guard_no_engineering_dimensions(
            epistemics.SYSTEM_3D, out["key_dimensions"])

    def test_component_names_mirror_subsystems(self):
        out = conceptual_geometry.build_system_architecture(
            ["ambient source characterization element",
             "transduction stage", "load interface"], "solar panel")
        names = [c["name"] for c in out["components"]]
        self.assertTrue(any("ambient source characterization element" in n for n in names))
        self.assertTrue(any("substrate: solar panel" == n for n in names))

    def test_glb_is_loadable_with_named_nodes(self):
        import trimesh
        out = conceptual_geometry.build_system_architecture(["a", "b", "c"], "panel")
        scene = trimesh.load(io.BytesIO(out["glb_bytes"]), file_type="glb")
        self.assertGreaterEqual(len(scene.geometry), 5)


# ---------------------------------------------------------------------------
# Engineering geometry tests
# ---------------------------------------------------------------------------

class TestEngineeringGeometry(unittest.TestCase):
    def test_dual_lumen_catheter_matches_released_chain(self):
        """The parametric build must reproduce the released P-07 measurements."""
        params = {"outer_diameter": 3.0, "primary_lumen_diameter": 1.1,
                  "floor_lumen_diameter": 0.6, "floor_offset": 1.0,
                  "length": 100.0}
        solid = engineering_geometry.build_dual_lumen_catheter(params)
        m = engineering_geometry.measure(solid)
        self.assertAlmostEqual(m["volume_mm3"], 583.550835, places=4)
        self.assertAlmostEqual(m["bbox"]["zlen"], 100.0)

    def test_validation_gates(self):
        import trimesh
        params = {"outer_diameter": 3.0, "primary_lumen_diameter": 1.1,
                  "floor_lumen_diameter": 0.6, "floor_offset": 1.0,
                  "length": 100.0}
        solid = engineering_geometry.build_dual_lumen_catheter(params)
        verts, tris = solid.val().tessellate(0.05)
        mesh = trimesh.Trimesh(
            vertices=[(v.x, v.y, v.z) for v in verts],
            faces=[list(t) for t in tris])
        report = engineering_geometry.validate_gates(
            solid, mesh,
            rebuild_fn=lambda: engineering_geometry.build_dual_lumen_catheter(params))
        self.assertTrue(report["passed"])
        self.assertTrue(report["gates"]["G1_trimesh_watertight"])
        self.assertTrue(report["gates"]["G9_regeneration"]["deterministic"])

    def test_wall_containment_guard(self):
        # primary (r=0.9) + floor (r=0.6) + wall margin cannot fit in od=2.0
        with self.assertRaises(ValueError):
            engineering_geometry.build_dual_lumen_catheter(
                {"outer_diameter": 1.5, "primary_lumen_diameter": 1.8,
                 "floor_lumen_diameter": 1.2, "floor_offset": 0.4, "length": 50})

    def test_failure_diagnosis_categorized(self):
        with self.assertRaises(ValueError) as cm:
            engineering_geometry.build_dual_lumen_catheter(
                {"outer_diameter": 1.5, "primary_lumen_diameter": 1.8,
                 "floor_lumen_diameter": 1.2, "floor_offset": 0.4, "length": 50})
        diag = engineering_geometry.diagnose_failure(cm.exception, "", {})
        self.assertEqual(diag["failure_class"], "PARAMETER_OUT_OF_ENVELOPE")
        self.assertIn("repair", diag)


# ---------------------------------------------------------------------------
# Epistemic guard tests
# ---------------------------------------------------------------------------

class TestEpistemicGuards(unittest.TestCase):
    def test_experimental_language_guard(self):
        with self.assertRaises(epistemics.EpistemicViolation):
            epistemics.guard_experimental_language({
                "experimentally_verified": True,
                "reality_loop_state": "NONE",
            })

    def test_experimental_allowed_with_real_loop(self):
        epistemics.guard_experimental_language({
            "experimentally_verified": True,
            "reality_loop_state": "PHYSICAL_OBSERVATION_RECORDED",
        })

    def test_forbidden_language(self):
        with self.assertRaises(epistemics.EpistemicViolation):
            epistemics.guard_language("this invention is patentable")

    def test_conceptual_disclaimer_text(self):
        d = epistemics.conceptual_disclaimer(epistemics.SYSTEM_3D)
        self.assertIn("NO engineering dimensions", d["rule"])
        self.assertIn("CONCEPTUAL_3D != ENGINEERING_3D", d["epistemic_boundary"])


# ---------------------------------------------------------------------------
# End-to-end bridge tests (real data)
# ---------------------------------------------------------------------------

class TestBridgeEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="bridge_test_")
        cls.result = run_bridge(
            _solar_run(), _solar_cio(), cls.work,
            glb_endpoint="/api/run/x/model",
            package_endpoint="/api/run/x/package",
            build_renders=False)

    def test_all_steps_ok(self):
        steps = {s["step"]: s["status"] for s in self.result["report"]["steps"]}
        self.assertEqual(steps["CLASSIFY"], "OK")
        self.assertEqual(steps["GEOMETRY"], "OK")
        self.assertEqual(steps["PACKAGE"], "OK")
        self.assertEqual(steps["CIO_UPDATE"], "OK")

    def test_cio_geometry_from_bridge_only(self):
        cio = self.result["cio_updated"]
        geo = cio["geometry"]
        self.assertTrue(geo["present"])
        self.assertEqual(geo["visualizability_class"], epistemics.SYSTEM_3D)
        self.assertIsNotNone(geo["glb_sha256"])
        # glb hash matches the actual bytes
        glb_path = os.path.join(self.work, "TECHNOLOGY_PACKAGE", "MODEL")
        found = [f for f in os.listdir(glb_path) if f.endswith(".glb")]
        self.assertEqual(len(found), 1)
        actual = hashlib.sha256(
            open(os.path.join(glb_path, found[0]), "rb").read()).hexdigest()
        self.assertEqual(actual, geo["glb_sha256"])

    def test_cio_maturity_honest_for_conceptual(self):
        cio = self.result["cio_updated"]
        self.assertIn("conceptual architecture only",
                      cio["maturity"]["maturity_basis"]["design"])
        self.assertIn("not yet earned",
                      cio["maturity"]["maturity_basis"]["design"])
        # EXPERIMENTALLY VERIFIED must not be set by the bridge
        self.assertNotEqual(cio["maturity"].get("experimentally_verified"), True)

    def test_package_zip_contents(self):
        pkg = self.result["package_out"]
        with zipfile.ZipFile(pkg["zip_path"]) as zf:
            names = zf.namelist()
        self.assertTrue(any(n.endswith("00_PACKAGE_README.pdf") for n in names))
        self.assertTrue(any(n.endswith("01_TECHNICAL_ESSAY.pdf") for n in names))
        self.assertTrue(any(n.endswith("CONCEPTUAL_3D_DISCLAIMER.json") for n in names))
        self.assertTrue(any(n.endswith("MANIFEST.json") for n in names))
        self.assertTrue(any(n.endswith("PROVENANCE.json") for n in names))
        # conceptual package must NOT contain STEP/STL
        self.assertFalse(any(n.endswith(".step") for n in names))
        self.assertFalse(any(n.endswith(".stl") for n in names))

    def test_manifest_hashes_verify(self):
        pkg = self.result["package_out"]
        pkg_dir = pkg["package_dir"]
        for entry in pkg["manifest"]["files"]:
            path = os.path.join(pkg_dir, entry["path"])
            actual = hashlib.sha256(open(path, "rb").read()).hexdigest()
            self.assertEqual(actual, entry["sha256"], f"hash mismatch: {entry['path']}")

    def test_provenance_chain(self):
        cio = self.result["cio_updated"]
        fs = _solar_run()["final_state"]
        self.assertIsNotNone(cio["provenance"]["geometry_sha256"])
        self.assertEqual(fs["final_envelope_hash"],
                         json.load(open(os.path.join(
                             self.result["package_out"]["package_dir"],
                             "PROVENANCE.json")))["final_envelope_hash"])

    def test_essay_eight_sections_no_raw_json(self):
        essay = self.result["package_out"]["essay"]
        self.assertEqual(len(essay["sections"]), 8)
        import re
        leak = re.compile(r"\{'|\{\"|'[a-z_]+':\s|\"[a-z_]+\":\s")
        for key, text in essay["sections"].items():
            self.assertTrue(text.strip(), f"empty section {key}")
            self.assertIsNone(leak.search(text),
                              f"raw machine state leaked into {key}: "
                              f"{leak.search(text) and leak.search(text).group()}")
            self.assertNotIn('"mechanism":', text)

    def test_generation_models_present(self):
        gens_dir = os.path.join(self.work, "GENERATIONS")
        models = [f for f in os.listdir(gens_dir) if f.endswith(".glb")]
        self.assertEqual(len(models), 2)  # real run recorded 2 generations


class TestBridgeEngineeringPath(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="bridge_eng_")
        cls.result = run_bridge(_engineering_run(), None, cls.work,
                                build_renders=False)

    def test_engineering_class(self):
        self.assertEqual(self.result["report"]["visualizability_class"],
                         epistemics.ENGINEERING_3D)

    def test_package_contains_step_stl(self):
        pkg = self.result["package_out"]
        with zipfile.ZipFile(pkg["zip_path"]) as zf:
            names = zf.namelist()
        self.assertTrue(any(n.endswith(".step") for n in names))
        self.assertTrue(any(n.endswith(".stl") for n in names))
        self.assertTrue(any(n.endswith("GEOMETRY_VALIDATION_REPORT.json") for n in names))

    def test_package_maturity_engineering(self):
        self.assertEqual(self.result["package_out"]["package_maturity"],
                         epistemics.PACKAGE_MATURITY_ENGINEERING)

    def test_cio_carries_measured_dimensions(self):
        geo = self.result["cio_updated"]["geometry"]
        self.assertIsNotNone(geo["key_dimensions"].get("volume_mm3"))
        self.assertTrue(geo["parametric_model_present"])


class TestBridgeFailureRecovery(unittest.TestCase):
    def test_engineering_failure_demotes_to_conceptual_not_silent(self):
        """If engineering geometry cannot build, the bridge must demote to a
        conceptual artifact — never a silent 'No 3D' (handoff section 17)."""
        run = _engineering_run()
        # sabotage: parameters that violate wall containment even after clamping
        run["engineering_specification"]["parameters"] = [
            {"param_id": "outer_diameter_mm", "value": 1.0, "unit": "mm",
             "envelope": [0.9, 1.1], "value_class": "MODELLED"},
            {"param_id": "primary_lumen_diameter_mm", "value": 1.9, "unit": "mm",
             "envelope": [1.8, 2.0], "value_class": "MODELLED"},
            {"param_id": "floor_lumen_diameter_mm", "value": 1.2, "unit": "mm",
             "envelope": [1.1, 1.3], "value_class": "MODELLED"},
            {"param_id": "floor_offset_mm", "value": 0.4, "unit": "mm",
             "envelope": [0.3, 0.5], "value_class": "MODELLED"},
            {"param_id": "length_mm", "value": 100.0, "unit": "mm",
             "envelope": [80, 120], "value_class": "MODELLED"},
        ]
        work = tempfile.mkdtemp(prefix="bridge_fail_")
        result = run_bridge(run, None, work, build_renders=False)
        # never silent: completed-as-conceptual with recorded demotion
        self.assertEqual(result["report"]["outcome"], "COMPLETED")
        self.assertEqual(result["report"]["visualizability_class"],
                         epistemics.SYSTEM_3D)
        attempts = result["geometry_out"]["cad_pipeline_status"]["attempts"]
        self.assertTrue(any(a["status"] == "FAILED" for a in attempts))
        reason = result["visualizability"]["classification_basis"]["reason"]
        self.assertIn("demoted to conceptual", reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
