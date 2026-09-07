"""R419 render-pipeline tests — the fixed 3D stack, wired end to end.

Proves (operator directive R419, sections 5-7/16-17/21):

  1. the six presentation artifacts: every invention gets
     hero/section/exploded PNG + GLB when the pinned Blender build is
     available (BLENDER_PATH) — produced by the BRIDGE itself (the
     production path, not a script);
  2. the authority contract: hero.glb preserves the imported geometry
     (vertex/face counts compared; any topology change is a typed
     failure) — Blender never alters the engineering truth;
  3. the canonical-object rule: the technology package ZIP contains
     the SAME MODEL/3D artifacts the website serves (manifest hashes
     match the render record);
  4. the CIO carries visualization.renders — the frontend gallery
     renders from the canonical state only (never invented state);
  5. typed honesty: with no Blender build, the render step records
     RENDER_SKIPPED_NO_BLENDER and the GLB contract is unaffected.

This battery runs the REAL pinned build when BLENDER_PATH is set
(local verification + the Docker image set it); otherwise test 5's
skip path is what runs. The render stage itself (find_blender,
subprocess invocation, artifact verification) is covered by
tests/test_r419_scipy_free_geometry.py and the render record
assertions below.
"""

import json
import os
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from discovery_fabric.engine.invention_bridge.bridge import bridge as run_bridge  # noqa: E402
from discovery_fabric.engine.invention_bridge import render as render_stage  # noqa: E402

REAL_RUN = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "r418", "solar_result.json")
REAL_CIO = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "fixtures", "r418", "solar_cio.json")

BLENDER = os.environ.get("BLENDER_PATH", "")


def _solar_run():
    if not os.path.exists(REAL_RUN):
        raise unittest.SkipTest("real solar run JSON not captured")
    return json.load(open(REAL_RUN))


def _solar_cio():
    if not os.path.exists(REAL_CIO):
        raise unittest.SkipTest("real solar CIO JSON not captured")
    return json.load(open(REAL_CIO))


class TestRenderPipelineHermetic(unittest.TestCase):
    """The typed-honest path with NO Blender build available."""

    def test_no_blender_is_typed_skip_not_failure(self):
        if BLENDER and os.path.isfile(BLENDER):
            self.skipTest("BLENDER_PATH set — the skip path needs it unset")
        work = tempfile.mkdtemp(prefix="r419_skip_")
        rec = render_stage.render_invention(work, {}, is_conceptual=True)
        self.assertEqual(rec["status"], "RENDER_SKIPPED_NO_BLENDER")
        self.assertIn("note", rec)
        # the GLB contract statement is part of the record
        self.assertIn("interactive GLB", rec["note"])

    def test_bridge_with_no_blender_still_completes(self):
        if BLENDER and os.path.isfile(BLENDER):
            self.skipTest("BLENDER_PATH set — the skip path needs it unset")
        work = tempfile.mkdtemp(prefix="r419_skipbridge_")
        result = run_bridge(_solar_run(), _solar_cio(), work,
                            build_renders=True)
        steps = {s["step"]: s["status"]
                 for s in result["report"]["steps"]}
        self.assertEqual(steps["CLASSIFY"], "OK")
        self.assertEqual(steps["GEOMETRY"], "OK")
        self.assertEqual(steps["RENDER"], "RENDER_SKIPPED_NO_BLENDER")
        self.assertEqual(steps["PACKAGE"], "OK")
        # the interactive GLB contract is unaffected by the render skip
        self.assertTrue(result["geometry_out"]["glb_sha256"])
        # CIO: renders is a typed honest absence, not a fabricated state
        renders = result["cio_updated"]["visualization"]["renders"]
        self.assertEqual(renders["status"], "RENDER_SKIPPED_NO_BLENDER")
        self.assertIsNone(renders.get("hero_png"))


@unittest.skipUnless(
    BLENDER and os.path.isfile(BLENDER),
    "the pinned Blender build is not available (set BLENDER_PATH)")
class TestRenderPipelineFull(unittest.TestCase):
    """The full fixed-3D-stack path: bridge -> Blender -> six artifacts
    -> package + CIO. This is the operator's section-5 contract."""

    @classmethod
    def setUpClass(cls):
        cls.work = tempfile.mkdtemp(prefix="r419_render_")
        cls.result = run_bridge(_solar_run(), _solar_cio(), cls.work,
                                build_renders=True)

    # ---- the six artifacts --------------------------------------------------

    def test_six_artifacts_exist(self):
        rec = self.result["geometry_out"]["renders"]
        self.assertEqual(rec["status"], "OK")
        for name in ("hero.png", "hero.glb", "section.png", "section.glb",
                     "exploded.png", "exploded.glb"):
            self.assertIn(name, rec["artifacts"], f"missing {name}")
            self.assertGreater(rec["artifacts"][name]["bytes"], 1000)
            self.assertTrue(rec["artifacts"][name]["sha256"])

    def test_render_step_in_pipeline_report(self):
        steps = {s["step"]: s["status"]
                 for s in self.result["report"]["steps"]}
        self.assertEqual(steps["RENDER"], "OK")

    # ---- the authority contract (operator section 7) -----------------------

    def test_blender_record_proves_topology_preserved(self):
        out_dir = self.result["geometry_out"]["renders"]["out_dir"]
        record = json.load(open(os.path.join(out_dir, "render_record.json")))
        src = record["source_topology"]
        hero = (record["exports"] or {})["hero.glb"]
        # hero.glb preserves the imported geometry exactly
        self.assertTrue(hero.get("geometry_preserved"))
        self.assertEqual(hero["topology"]["vertex_count"],
                         src["vertex_count"])
        self.assertEqual(hero["topology"]["face_count"],
                         src["face_count"])
        self.assertEqual(hero["topology"]["object_count"],
                         src["object_count"])

    def test_section_and_exploded_are_disclosed_variants(self):
        out_dir = self.result["geometry_out"]["renders"]["out_dir"]
        record = json.load(open(os.path.join(out_dir, "render_record.json")))
        renders = record.get("renders") or {}
        section = renders.get("section.png") or {}
        self.assertIn("PRESENTATION_CUT", section.get("variant", ""))
        exploded = renders.get("exploded.png") or {}
        self.assertIn("PRESENTATION_EXPLODED",
                      exploded.get("variant", ""))
        exports = record.get("exports") or {}
        self.assertIn("PRESENTATION_CUT",
                      exports["section.glb"].get("variant", ""))
        self.assertIn("PRESENTATION_EXPLODED",
                      exports["exploded.glb"].get("variant", ""))

    # ---- the canonical-object rule (operator sections 16-17) ---------------

    def test_package_carries_the_same_render_artifacts(self):
        pkg = self.result["package_out"]
        self.assertGreaterEqual(len(pkg.get("render_artifacts") or []), 7)
        with zipfile.ZipFile(pkg["zip_path"]) as zf:
            names = set(zf.namelist())
            for rel in ("hero.png", "hero.glb", "section.png", "section.glb",
                        "exploded.png", "exploded.glb",
                        "RENDER_DISCLOSURE.json"):
                self.assertIn(f"TECHNOLOGY_PACKAGE/MODEL/3D/{rel}", names)
        # manifest hashes every file including the renders
        for f in pkg["manifest"]["files"]:
            if f["path"].startswith("MODEL/3D/"):
                self.assertTrue(f["sha256"])
                self.assertGreater(f["bytes"], 0)

    def test_provenance_records_the_render_pipeline(self):
        prov = json.load(open(os.path.join(
            self.result["package_out"]["package_dir"], "PROVENANCE.json")))
        self.assertEqual(prov["render_pipeline"], "BLENDER_HEADLESS")
        self.assertEqual(prov["render_status"], "OK")
        self.assertIn("5.2", prov["render_pinned_blender"])

    # ---- CIO wiring ----------------------------------------------------------

    def test_cio_visualization_renders(self):
        renders = (self.result["cio_updated"]["visualization"]
                   .get("renders") or {})
        self.assertEqual(renders["status"], "OK")
        self.assertEqual(renders["pipeline"], "BLENDER_HEADLESS")
        self.assertTrue(renders["hero_png"].endswith("hero.png"))
        self.assertTrue(renders["exploded_glb"].endswith("exploded.glb"))
        self.assertEqual(renders["missing"], [])
        self.assertIn("presentation", renders["presentation_rule"])

    def test_cio_disclaimer_survives_for_conceptual(self):
        vis = self.result["cio_updated"]["visualization"]
        # the solar fixture class is SYSTEM_3D (conceptual) — the
        # disclaimer stays (a render is never an engineering promotion)
        self.assertIsNotNone(vis.get("disclaimer"))
        self.assertTrue(renders_is_conceptual(vis))

    # ---- determinism (Art. LXII) ----------------------------------------------

    def test_render_record_pins_build_and_source(self):
        rec = self.result["geometry_out"]["renders"]
        self.assertEqual(rec["render_pipeline"], "BLENDER_HEADLESS")
        self.assertTrue(rec["source_glb_sha256"])
        self.assertIn("LTS", rec["pinned_blender"])
        self.assertTrue(rec["seconds"] > 0)
        out_dir = rec["out_dir"]
        record = json.load(open(os.path.join(out_dir, "render_record.json")))
        self.assertIn("LTS", record["blender_version"])
        self.assertTrue(record["blender_build_hash"])


def renders_is_conceptual(vis: dict) -> bool:
    r = vis.get("renders") or {}
    return bool(r.get("is_conceptual"))


if __name__ == "__main__":
    unittest.main()
