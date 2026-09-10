"""R441 — THE VISUAL COMPILER tests.

The round directive: make it impossible for Toscanini to generate
another ugly 3D artifact — the pipeline, not prompts, guarantees
presentation quality. Constitutional anchors:

- Article LXXII (new): no 3D artifact ships without passing the Visual
  Compiler; the gate verdict suppresses the hero and blocks release.
- Art. III / XLV: the gate re-measures with its own tools; generator
  and verifier share no state.
- Art. XXVII: every camera/gate threshold carries provenance; none is
  invented per render.
- Art. XXV: not-applicable stays not-applicable (single-part exploded
  skip is typed, never faked).
- Art. LXIV: the Blender hero path is retired EXPLICITLY (archived in
  the same commit; the legacy backend is reachable only by choice).
- Art. XXIII-like hygiene for the R423 boundary: the renderer
  subprocess env allowlist carries to Chromium (absent-by-construction).
"""
from __future__ import annotations

import ast
import inspect
import json
import os
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.visual_compiler import camera_solver  # noqa: E402
from discovery_fabric.engine.visual_compiler import gltf_doc  # noqa: E402
from discovery_fabric.engine.visual_compiler import material_mapper  # noqa: E402
from discovery_fabric.engine.visual_compiler import render_worker  # noqa: E402
from discovery_fabric.engine.visual_compiler import scene_builder  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_compiler as vc  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_gate  # noqa: E402

VC_DIR = REPO / "discovery_fabric" / "engine" / "visual_compiler"
RETIRED = (REPO / "discovery_fabric" / "engine" / "invention_bridge"
           / "r441_retired")


def _write_solid_png(path: Path, w: int = 100, h: int = 100,
                     model_box: tuple = (20, 20, 80, 78),
                     shadow_band: tuple | None = (20, 79, 80, 86),
                     shadow_alpha: int = 90) -> None:
    """A synthetic RGBA render: an opaque 'model' rectangle + an
    optional semi-transparent 'shadow' band below it."""
    from PIL import Image
    img = np.zeros((h, w, 4), dtype=np.uint8)
    x0, y0, x1, y1 = model_box
    img[y0:y1, x0:x1] = (200, 190, 180, 255)
    if shadow_band:
        sx0, sy0, sx1, sy1 = shadow_band
        img[sy0:sy1, sx0:sx1] = (40, 40, 40, shadow_alpha)
    Image.fromarray(img).save(path)


# ---------------------------------------------------------------------------
# A. the camera solve (Article XXVII: provenance, anti-clip, determinism)
# ---------------------------------------------------------------------------
class TestCameraSolver:
    def _spec(self, w, h, d):
        return {
            "normalized_size": [w, h, d],
            "grounding_fit_radius": 2.6,
        }

    def test_every_threshold_carries_provenance(self):
        for name, entry in camera_solver.DIRECTIVE_THRESHOLDS.items():
            assert "value" in entry and "source" in entry, name

    def test_solve_is_deterministic(self):
        spec = self._spec(3.0, 30.0, 3.0)
        a = camera_solver.solve(spec)
        b = camera_solver.solve(spec)
        assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)

    def test_tall_model_solves_without_clipping(self):
        """The R441 acceptance failure mode: a tall model solved by a
        bounding-sphere loop CLIPS — the projected-extent solve cannot:
        the vertical constraint contains the projected height."""
        spec = self._spec(0.5, 5.0, 0.5)
        hero = camera_solver.solve_hero(spec)
        ext = hero["solve_basis"]
        # the frame span at the solved distance contains the projection
        import math
        v_span = 2 * hero["distance"] * math.tan(
            math.radians(hero["fov"]) / 2)
        assert v_span >= ext["projected_height"] / 0.85

    def test_wide_model_takes_the_max_constraint(self):
        spec = self._spec(5.0, 2.8, 2.9)
        hero = camera_solver.solve_hero(spec)
        basis = hero["solve_basis"]
        assert hero["distance"] == max(basis["distance_vertical_constraint"],
                                       basis["distance_horizontal_constraint"])

    def test_ground_band_is_reserved(self):
        hero = camera_solver.solve_hero(self._spec(1, 1, 1))
        assert 0.0 < hero["ground_band_fraction"] < 0.2
        assert hero["desired_base_fraction"] == \
            hero["ground_band_fraction"]


# ---------------------------------------------------------------------------
# B. semantic materials (Material Constitution: from component TYPE)
# ---------------------------------------------------------------------------
class TestMaterialMapper:
    def test_directive_table_is_semantic(self):
        table = material_mapper.SEMANTIC_MATERIALS
        for cls in ("battery", "silicon", "machined_metal", "body_metal",
                    "glass", "conduit_power", "circuit"):
            assert cls in table, cls
        assert table["battery"]["base"] != \
            table["silicon"]["base"]  # battery != solar

    def test_classification_is_deterministic_and_prompt_free(self):
        names = ["battery_pack_01", "solar_panel", "drive_motor",
                 "chassis_frame", "glass_dome", "coolant_loop"]
        first = {n: material_mapper.classify_node_name(n) for n in names}
        second = {n: material_mapper.classify_node_name(n) for n in names}
        assert first == second
        assert first["battery_pack_01"] == "battery"
        assert first["solar_panel"] == "silicon"
        assert first["coolant_loop"] == "conduit_power"

    def test_mapping_covers_every_node(self):
        out = material_mapper.build_mapping(
            ["battery_pack", "weird_unnamed_thing"])
        assert set(out["mapping"]) == {"battery_pack",
                                       "weird_unnamed_thing"}
        assert all(m.get("class") for m in out["mapping"].values())

    def test_geometry_spec_wins_over_keywords(self):
        spec = {"parts": [{"component_id": "solar_panel",
                           "material_class": "battery"}]}
        out = material_mapper.build_mapping(["solar_panel_a1"], spec)
        assert out["mapping"]["solar_panel_a1"]["class"] == "battery"
        assert out["provenance"]["solar_panel_a1"] == "geometry_spec"


# ---------------------------------------------------------------------------
# C. the canonical scene identity (the R441 naming lesson)
# ---------------------------------------------------------------------------
class TestGltfDoc:
    def test_unstable_loader_names_are_not_used(self, tmp_path):
        import trimesh
        box = trimesh.creation.box(extents=[1, 1, 1])
        s = trimesh.Scene({"part_a": box, "part_b": box})
        glb = tmp_path / "m.glb"
        s.export(glb, file_type="glb")
        w1 = gltf_doc.walk_scene(str(glb))
        w2 = gltf_doc.walk_scene(str(glb))
        # the SAME document walks to the SAME names — no loader synthesis
        assert [p["name"] for p in w1["parts"]] == \
            [p["name"] for p in w2["parts"]]
        assert {p["name"] for p in w1["parts"]} >= {"part_a", "part_b"}

    def test_unnamed_nodes_get_stable_ordinal_names(self, tmp_path):
        import struct
        # hand-build a minimal GLB with TWO unnamed mesh nodes
        def node_mesh(name):
            positions = [0, 0, 0, 1, 0, 0, 0, 1, 0]
            payload = struct.pack("<9f", *positions)
            j = {
                "asset": {"version": "2.0"},
                "scene": 0,
                "scenes": [{"nodes": [0, 1]}],
                "nodes": [
                    {"mesh": 0, "translation": [0, 0, 0]},
                    {"mesh": 0, "translation": [3, 0, 0]},
                ],
                "meshes": [{"primitives": [{
                    "attributes": {"POSITION": 0},
                    "mode": 4}]}],
                "accessors": [{
                    "bufferView": 0, "componentType": 5126,
                    "count": 3, "type": "VEC3",
                    "min": [0, 0, 0], "max": [1, 1, 0]}],
                "bufferViews": [{"buffer": 0, "byteOffset": 0,
                                 "byteLength": len(payload)}],
                "buffers": [{"byteLength": len(payload)}],
            }
            return j, payload

        j, payload = node_mesh(None)
        jbytes = json.dumps(j).encode()
        pad = (4 - len(jbytes) % 4) % 4
        jbytes += b" " * pad
        payload += b"\x00" * ((4 - len(payload) % 4) % 4)
        total = 12 + 8 + len(jbytes) + 8 + len(payload)
        out = b"glTF" + struct.pack("<II", 2, total)
        out += struct.pack("<I4s", len(jbytes), b"JSON") + jbytes
        out += struct.pack("<I4s", len(payload), b"BIN\x00") + payload
        glb = tmp_path / "unnamed.glb"
        glb.write_bytes(out)
        w = gltf_doc.walk_scene(str(glb))
        names = [p["name"] for p in w["parts"]]
        assert names == ["part-001", "part-002"]
        w2 = gltf_doc.walk_scene(str(glb))
        assert [p["name"] for p in w2["parts"]] == names


class TestSceneBuilder:
    def test_spec_bytes_are_deterministic(self, tmp_path):
        import trimesh
        s = trimesh.Scene({"part_a": trimesh.creation.box(extents=[2, 4, 2])})
        glb = tmp_path / "m.glb"
        s.export(glb, file_type="glb")
        spec1 = scene_builder.build_scene_spec(str(glb))
        spec2 = scene_builder.build_scene_spec(str(glb))
        assert scene_builder.scene_spec_bytes(spec1) == \
            scene_builder.scene_spec_bytes(spec2)

    def test_grounding_policy_declares_no_floating(self, tmp_path):
        import trimesh
        s = trimesh.Scene({"p": trimesh.creation.box(extents=[2, 4, 2])})
        glb = tmp_path / "m.glb"
        s.export(glb, file_type="glb")
        spec = scene_builder.build_scene_spec(str(glb))
        assert "min-Y grounded at 0" in spec["grounding"]["policy"]
        assert spec["grounding"]["scale"] > 0


# ---------------------------------------------------------------------------
# D. the gate (Art. III: the verifier measures pixels itself)
# ---------------------------------------------------------------------------
class TestVisualGate:
    def _hero(self, tmp_path, **kw):
        png = tmp_path / "hero.png"
        _write_solid_png(png, **kw)
        return visual_gate.measure_occupancy(visual_gate._load_rgba(png))

    def test_occupancy_measures_extents(self, tmp_path):
        m = self._hero(tmp_path, model_box=(20, 20, 80, 78),
                       shadow_band=None)
        assert m["height_frac"] == pytest.approx(0.59, abs=0.02)
        assert m["width_frac"] == pytest.approx(0.61, abs=0.02)
        assert m["dominant"] == pytest.approx(0.61, abs=0.02)
        assert m["clipped"] is False

    def test_clip_witness_fires_on_edge_touch(self, tmp_path):
        m = self._hero(tmp_path, model_box=(20, 0, 80, 78),
                       shadow_band=None)
        assert m["clipped"] is True

    def test_solid_base_ignores_the_soft_shadow(self, tmp_path):
        """The base row is the BODY's base (alpha > 154) — the shadow
        (alpha ~90) may fade toward the frame bottom without moving the
        measured base."""
        m = self._hero(tmp_path, model_box=(20, 20, 80, 60),
                       shadow_band=(20, 61, 80, 99), shadow_alpha=90)
        assert m["base_row"] == 59  # the body's last row (0-based)

    def test_gate_not_run_fails_closed(self):
        out = str(tmp_path := Path(self.__class__.__name__))
        gate = visual_gate.evaluate(out, {}, {}, "RENDER_SKIPPED_NO_RENDERER")
        assert gate["verdict"] == "NOT_RUN"
        assert gate["hero_suppressed"] is True
        assert gate["release_blocked"] is True

    def test_gate_fail_suppresses_the_poster_parity(self, tmp_path):
        # an EMPTY frame (no model, no shadow) fails occupancy AND
        # shadow AND parity — the verdict is FAIL with reasons
        hero = tmp_path / "hero.png"
        from PIL import Image
        Image.fromarray(np.zeros((100, 100, 4), np.uint8)).save(hero)
        spec = {"grounding": {"scale": 0.5},
                "materials": {"mapping": {"a": {"class": "battery"}}},
                "model": {"nodes": [{"name": "a"}]}}
        rec = {"topology_comparison": {"identical": True}}
        (tmp_path / "poster.png").write_bytes(b"nope-not-a-png")
        gate = visual_gate.evaluate(str(tmp_path), spec, rec, "OK")
        assert gate["verdict"] == "FAIL"
        assert gate["hero_suppressed"] is True

    def test_single_viewer_static_scan(self):
        res = visual_gate.check_single_viewer()
        assert res["pass"] is True
        assert res["primary_surface_viewers"] == 1


# ---------------------------------------------------------------------------
# E. Article LXIV — the Blender hero path is retired, explicitly
# ---------------------------------------------------------------------------
class TestBlenderRetirement:
    def test_live_blender_script_is_gone(self):
        assert not (REPO / "discovery_fabric/engine/invention_bridge/"
                    "blender_render.py").exists()

    def test_retired_script_is_archived_with_a_record(self):
        archived = RETIRED / "blender_render.py"
        assert archived.is_file()
        readme = (RETIRED / "README.md").read_text()
        assert "ARCHIVED_TO" in readme
        assert "KEPT_BECAUSE" in readme

    def test_zero_live_references_to_the_retired_script(self):
        """No Python module IMPORTS the retired script; the dispatcher's
        only remaining path reference points INTO the retirement archive
        (the legacy backend runs the archived copy, acknowledged)."""
        offenders = []
        for py in (REPO / "discovery_fabric").rglob("*.py"):
            if "r441_retired" in str(py):
                continue
            tree = ast.parse(py.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    if any("blender_render" in a.name
                           for a in node.names):
                        offenders.append(f"{py}: import")
                elif isinstance(node, ast.ImportFrom):
                    if "blender_render" in (node.module or ""):
                        offenders.append(f"{py}: import-from")
        assert offenders == []
        import discovery_fabric.engine.invention_bridge.render as render
        assert "r441_retired" in str(render.RENDER_SCRIPT)

    def test_dispatcher_default_is_the_visual_compiler(self):
        import discovery_fabric.engine.invention_bridge.render as render
        src = inspect.getsource(render.render_invention)
        assert 'os.environ.get("TOSCANINI_RENDER_BACKEND")' in src
        assert '"visual_compiler"' in src
        tree = ast.parse(src)
        calls = [n.func.attr for n in ast.walk(tree)
                 if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Attribute)]
        assert "compile_visuals" in calls

    def test_legacy_backend_is_labeled_legacy(self):
        import discovery_fabric.engine.invention_bridge.render as render
        src = inspect.getsource(render.render_invention)
        assert 'BLENDER_HEADLESS_LEGACY' in src


# ---------------------------------------------------------------------------
# F. the renderer boundary carries the R423 env contract
# ---------------------------------------------------------------------------
class TestRendererEnvBoundary:
    SECRETS = {
        "GITHUB_TOKEN": "ghp_x", "NVIDIA_API_KEY": "nvapi_x",
        "ZAI_API_KEY": "zai_x", "DATABASE_URL": "db://x",
    }

    def test_allowlist_strips_every_secret(self, monkeypatch):
        for k, v in self.SECRETS.items():
            monkeypatch.setenv(k, v)
        env = render_worker._render_subprocess_env()
        for k in self.SECRETS:
            assert k not in env
            assert self.SECRETS[k] not in json.dumps(env)

    def test_chrome_resolution_fails_closed(self, monkeypatch, tmp_path):
        monkeypatch.delenv("CHROME_PATH", raising=False)
        monkeypatch.setenv("HOME", str(tmp_path))  # empty puppeteer cache
        assert render_worker.find_chrome() is None
        trail = render_worker.last_resolution()
        assert trail["accepted_chrome"] is None

    def test_memory_guard_is_cgroup_aware(self, monkeypatch):
        monkeypatch.setattr(render_worker, "_cgroup_avail_mb", lambda: 90)
        monkeypatch.setattr(render_worker, "_host_avail_mb", lambda: 3500)
        guard = render_worker.memory_guard("test", mode="async")
        assert guard is not None
        assert guard["status"] == "RENDER_SKIPPED_LOW_MEMORY"
        # the R420d lesson: the CONTAINER's limit governs, not the host
        assert guard["mem_available_mb"] == 90

    def test_thresholds_carry_measured_provenance(self):
        th = json.loads(
            (VC_DIR / "visual_compiler_thresholds.json").read_text())
        assert th["chrome_baseline_measurement"]["status"] == "MEASURED"
        assert "basis" in th["memory_guard_mb"]


# ---------------------------------------------------------------------------
# G. the package layer enforces Article LXXII
# ---------------------------------------------------------------------------
class TestPackageEnforcement:
    def test_hero_release_state_is_written_and_enforced(self):
        src = (REPO / "discovery_fabric/engine/invention_bridge/"
               "package.py").read_text()
        assert "HERO_RELEASE_STATE" in src
        assert "hero_suppressed" in src
        # R443 reconciliation: the release rule is now the typed helper
        # _visual_release_ok (COMPLETE_PASS is the only release-passing
        # verdict; the R441 '!= "PASS"' string no longer exists)
        assert "_visual_release_ok(gate)" in src or \
            gate_check_present(src)

    def test_pdf_cover_exists_only_on_gate_pass(self):
        src = (REPO / "discovery_fabric/engine/invention_bridge/"
               "package.py").read_text()
        # R443 reconciliation: the cover exists ONLY through the same
        # typed release check (COMPLETE_PASS vocabulary)
        assert "_visual_release_ok(gate)" in src

    def test_pdf_constitution_page_order(self, tmp_path):
        """The PDF Constitution: p1 hero, p2 exploded, p3 ortho,
        p4 dimensions — then the narrative. A gate FAIL ships
        text-only (the hero is suppressed in EVERY medium)."""
        import io
        import discovery_fabric.engine.invention_bridge.package as pkg
        from pypdf import PdfReader
        hero = tmp_path / "hero.png"
        exploded = tmp_path / "exploded.png"
        dim = tmp_path / "dimension.png"
        ortho = tmp_path / "orthographic"
        ortho.mkdir()
        _write_solid_png(hero, 60, 60)
        _write_solid_png(exploded, 60, 60, model_box=(10, 10, 50, 50))
        _write_solid_png(dim, 60, 60, model_box=(5, 10, 55, 50))
        # DISTINCT fills: reportlab dedupes identical images into one
        # XObject, which would defeat the per-page count assertion
        from PIL import Image
        for i, v in enumerate(("front", "side", "top", "iso")):
            arr = np.zeros((60, 60, 4), np.uint8)
            arr[10:50, 10:50] = (30 + 50 * i, 90, 200, 255)
            Image.fromarray(arr).save(ortho / f"{v}.png")
        essay = {"section_order": ["M"], "titles": {"M": "M"},
                 "sections": {"M": "body text " * 40},
                 "__cover__": {
                     "gate": "PASS", "label": "t",
                     "hero": str(hero), "exploded": str(exploded),
                     "dimension": str(dim),
                     "orthographic": [str(ortho / f"{v}.png")
                                      for v in ("front", "side", "top",
                                                "iso")]}}
        r = PdfReader(io.BytesIO(pkg._pdf("t", "t", dict(essay))))
        assert len(r.pages) >= 5
        img_counts = [len(p.get("/Resources", {}).get("/XObject", {}) or {})
                      for p in r.pages]
        assert img_counts[0] == 1  # p1: the hero
        assert img_counts[1] == 1  # p2: exploded
        assert img_counts[2] == 4  # p3: the ortho grid
        assert img_counts[3] == 1  # p4: dimensions
        failed = dict(essay)
        failed["__cover__"] = {"gate": "FAIL", "hero": str(hero)}
        r2 = PdfReader(io.BytesIO(pkg._pdf("t", "t", failed)))
        assert all(len(p.get("/Resources", {}).get("/XObject", {}) or {})
                   == 0 for p in r2.pages)


def gate_check_present(src: str) -> bool:
    return 'gate_verdict = gate.get("verdict")' in src


# ---------------------------------------------------------------------------
# H. the integration: the real renderer, a real GLB, the real gate
# ---------------------------------------------------------------------------
def _chrome_available() -> bool:
    try:
        return bool(render_worker.find_chrome() and render_worker.find_node()
                    and render_worker.renderer_deps_present() is None)
    except Exception:
        return False


class TestEndToEnd:
    @pytest.mark.skipif(not _chrome_available(),
                        reason="headless Chromium/Node pair not available")
    def test_full_visual_set_passes_the_gate(self, tmp_path):
        """THE acceptance: canonical GLB in, gate-approved visual set
        out. Article LXXII's own loop, executed live."""
        import shutil
        import trimesh
        (tmp_path / "MODEL").mkdir(parents=True)
        s = trimesh.Scene({
            "battery_pack": _box([40, 12, 25], [0, 6, 0]),
            "drive_motor": trimesh.creation.cylinder(
                radius=9, height=30, sections=32).apply_translation(
                [0, 27, 0]),
            "chassis_frame": _box([70, 4, 40], [0, 2, 0]),
        })
        glb = tmp_path / "MODEL" / "engineering_model.glb"
        s.export(glb, file_type="glb")
        rec = vc.compile_visuals(str(tmp_path), memory_mode="async")
        assert rec["status"] in ("OK", "PARTIAL"), rec
        gate = rec["visual_gate"]
        # R443: the gate vocabulary is COMPLETE_PASS/PARTIAL/NOT_RUN/FAIL
        assert gate["verdict"] == "COMPLETE_PASS", gate["reasons"]
        out = Path(rec["out_dir"])
        for name in ("hero.png", "poster.png", "dimension.png",
                     "section.png", "exploded.png", "exploded.glb",
                     "hero.glb", "scene_spec.json", "visual_gate.json"):
            assert (out / name).is_file(), name
        assert (out / "orthographic" / "front.png").is_file()
        assert rec["hero_suppressed"] is False
        # the record's artifact hashes re-verify (Art. III)
        import hashlib
        for name, meta in rec["artifacts"].items():
            p = out / name
            assert hashlib.sha256(p.read_bytes()).hexdigest() \
                == meta["sha256"]

    @pytest.mark.skipif(not _chrome_available(),
                        reason="headless Chromium/Node pair not available")
    def test_determinism_same_glb_same_scene_spec(self, tmp_path):
        import shutil
        import trimesh
        for sub in ("a", "b"):
            (tmp_path / sub / "MODEL").mkdir(parents=True)
            s = trimesh.Scene({"part_x": _box([10, 20, 10], [0, 10, 0])})
            s.export(tmp_path / sub / "MODEL" / "engineering_model.glb",
                     file_type="glb")
        ra = vc.compile_visuals(str(tmp_path / "a"), memory_mode="async")
        rb = vc.compile_visuals(str(tmp_path / "b"), memory_mode="async")
        # the SCENE SPEC (the deterministic solve) is byte-identical;
        # the renders it produces are pixel-deterministic per spec
        sa = (Path(ra["out_dir"]) / "scene_spec.json").read_bytes()
        sb = (Path(rb["out_dir"]) / "scene_spec.json").read_bytes()
        assert sa == sb
        assert ra["scene_spec_sha256"] == rb["scene_spec_sha256"]
        ha = (Path(ra["out_dir"]) / "hero.png").read_bytes()
        hb = (Path(rb["out_dir"]) / "hero.png").read_bytes()
        assert hashlib_sha(ha) == hashlib_sha(hb)


def _box(extents, translation):
    import trimesh
    b = trimesh.creation.box(extents=extents)
    b.apply_translation(translation)
    return b


def hashlib_sha(data: bytes) -> str:
    import hashlib
    return hashlib.sha256(data).hexdigest()
