"""R419 product-surface tests — the new routes and projections.

Covers (operator directive R419, sections 5-6/11-12/16-17/21):

  * GET /api/run/{id}/render/{name} — the six presentation artifacts,
    name-whitelisted, honest 404 when absent;
  * GET /api/run/{id}/essay — the 8-section technical essay JSON from
    the canonical state (raw-JSON leak guard is the essay builder's
    own, test-pinned in the r418 battery);
  * POST /api/run/{id}/artifact-build — 202 + detached job, idempotent,
    the web request never waits for Blender (the job record is the
    authority; MODEL/3D/RENDER_JOB.json);
  * build_cio's visualization.renders projection — derived from the
    MODEL/3D/ directory itself (the files are the authority), never
    invented by the frontend.

The route wiring itself is pinned by source inspection (the r389/r414
precedent: the handler's route table is part of the product contract).
"""

import inspect
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from toscanini import server as srv  # noqa: E402
from toscanini import cio as cio_mod  # noqa: E402
from toscanini import artifact_worker  # noqa: E402


class TestRouteWiring(unittest.TestCase):
    """The R419 routes exist on the production handler (the r389/r414
    source-inspection precedent — route presence is product contract)."""

    def test_render_route_wired(self):
        src = inspect.getsource(srv.Handler.do_GET)
        self.assertIn('parts[3] == "render"', src)
        self.assertIn("hero.png", src)
        self.assertIn("exploded.glb", src)

    def test_essay_route_wired(self):
        src = inspect.getsource(srv.Handler.do_GET)
        self.assertIn('parts[3] == "essay"', src)

    def test_artifact_build_route_wired(self):
        src = inspect.getsource(srv.Handler.do_POST)
        self.assertIn('parts[3] == "artifact-build"', src)

    def test_render_route_whitelists_names(self):
        # the whitelist is IN the handler source (no traversal, no
        # arbitrary file serving through the render route)
        src = inspect.getsource(srv.Handler.do_GET)
        self.assertIn('Path(parts[4]).name', src)
        self.assertIn("unknown render name", src)


class TestArtifactWorker(unittest.TestCase):
    """The async artifact-build job (operator section 21)."""

    def test_renderables_present_requires_glb(self):
        with tempfile.TemporaryDirectory() as td:
            # no GLB -> honestly not renderable
            self.assertFalse(
                artifact_worker.renderables_present({"run_dir": td}))
            # a GLB exists -> renderable
            model = Path(td) / "MODEL"
            model.mkdir()
            (model / "model-001.glb").write_bytes(b"glb")
            self.assertTrue(
                artifact_worker.renderables_present({"run_dir": td}))

    def test_job_record_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            # a stand-in session: the worker reads the store, so this
            # test pins the RECORD contract on disk (the authority)
            from toscanini import sessions as store
            orig = store.get_session
            store.get_session = lambda sid: {
                "session_id": sid, "run_dir": td}
            try:
                p = Path(td) / "MODEL" / "3D"
                p.mkdir(parents=True)
                record = {
                    "artifact": "RENDER_JOB", "session_id": "ts_x",
                    "status": "OK", "at": "now",
                    "render_record": {"status": "OK"},
                }
                (p / "RENDER_JOB.json").write_text(json.dumps(record))
                back = artifact_worker.job_record("ts_x")
                self.assertEqual(back["status"], "OK")
                self.assertEqual(back["render_record"]["status"], "OK")
            finally:
                store.get_session = orig

    def test_run_writes_typed_record_without_blender(self):
        with tempfile.TemporaryDirectory() as td:
            from toscanini import sessions as store
            orig = store.get_session
            store.get_session = lambda sid: {
                "session_id": sid, "run_dir": td}
            try:
                model = Path(td) / "MODEL"
                model.mkdir()
                (model / "model-001.glb").write_bytes(b"glb")
                out = artifact_worker.run("ts_x")
                # no Blender on this machine -> typed honest skip,
                # never a crash and never a fabricated artifact
                self.assertIn(out["status"],
                              ("RENDER_SKIPPED_NO_BLENDER", "FAILED"))
                job = json.loads(
                    (Path(td) / "MODEL" / "3D" / "RENDER_JOB.json")
                    .read_text())
                self.assertEqual(job["artifact"], "RENDER_JOB")
            finally:
                store.get_session = orig


class TestCioVisualizationProjection(unittest.TestCase):
    """build_cio projects visualization.renders from MODEL/3D/ (the
    files are the authority — Art. X), never inventing availability."""

    @staticmethod
    def _session_with_renders(td: str, with_files: bool):
        model = Path(td) / "MODEL"
        model.mkdir(parents=True, exist_ok=True)
        (model / "model-001.glb").write_bytes(b"glb")
        # the invention-side artifact build_cio requires (an invention
        # must exist before there is an object at all)
        (Path(td) / "INVENTION_SPECIFICATION.json").write_text(json.dumps({
            "mechanism": {"value": "adaptive thermal regulation"},
        }))
        r3d = model / "3D"
        r3d.mkdir(exist_ok=True)
        if with_files:
            for n in ("hero.png", "hero.glb", "section.png", "section.glb",
                      "exploded.png", "exploded.glb"):
                (r3d / n).write_bytes(b"x" * 2048)
            (r3d / "render_record.json").write_text(json.dumps({
                "render_pipeline": "BLENDER_HEADLESS",
                "blender_version": "5.2.1 LTS",
                "status": "OK",
                "source_glb_sha256": "deadbeef",
            }))
            (Path(td) / "BRIDGE_REPORT.json").write_text(json.dumps({
                "outcome": "COMPLETED",
                "visualizability_class": "SYSTEM_3D",
                "geometry": {"components": [
                    {"name": "sensing layer", "role": "measurement"},
                    {"name": "compute core", "role": "control"}]},
            }))
        else:
            (Path(td) / "BRIDGE_REPORT.json").write_text(json.dumps({
                "outcome": "COMPLETED",
                "visualizability_class": "SYSTEM_3D",
            }))
        return {"session_id": "ts_v", "run_dir": td,
                "final_status": "EVOLVED_INVENTION_CANDIDATE"}

    def test_renders_projected_when_files_exist(self):
        with tempfile.TemporaryDirectory() as td:
            s = self._session_with_renders(td, with_files=True)
            cio = cio_mod.build_cio(s)
            self.assertIsNotNone(cio)
            renders = (cio.get("visualization") or {}).get("renders") or {}
            self.assertEqual(renders.get("status"), "OK")
            self.assertEqual(renders.get("pipeline"), "BLENDER_HEADLESS")
            self.assertIn("5.2.1 LTS", renders.get("pinned_blender", ""))
            self.assertTrue(renders["hero_png"].endswith("hero.png"))
            self.assertTrue(renders["exploded_glb"].endswith("exploded.glb"))
            self.assertEqual(renders.get("missing"), [])
            self.assertIn("presentation", renders.get("presentation_rule", ""))

    def test_renders_absent_when_no_files(self):
        with tempfile.TemporaryDirectory() as td:
            s = self._session_with_renders(td, with_files=False)
            cio = cio_mod.build_cio(s)
            renders = (cio.get("visualization") or {}).get("renders") or {}
            # honest absence: empty (or typed) — NEVER a fabricated URL
            self.assertFalse(renders.get("hero_png"))

    def test_components_projected_from_bridge_report(self):
        with tempfile.TemporaryDirectory() as td:
            s = self._session_with_renders(td, with_files=True)
            cio = cio_mod.build_cio(s)
            comps = (cio.get("geometry") or {}).get("components") or []
            self.assertEqual(len(comps), 2)
            self.assertEqual(comps[0]["name"], "sensing layer")


if __name__ == "__main__":
    unittest.main()
