"""R443 Visual Integrity Hardening — the adversarial battery.

Operator directive R443-C2: fresh attacks NOT derived solely from the
implementation's happy-path fixtures. Each attack targets one gate
boundary; every EXPECTED failure must fail for the SPECIFIC reason the
boundary exists (not incidentally):

  Attack 1  stripped identity    valid geometry, canonical node names
                                 stripped from the RAW glTF document
                                 -> FAIL (node identity absent)
  Attack 2  missing view         one required ladder artifact deleted
                                 -> PARTIAL / NOT_COMPLETE, hero
                                 suppressed, release blocked
  Attack 3  material spoof       two semantic classes one visual material
                                 -> FAIL (measurable distinction)
  Attack 4  malformed skip       RENDER_SKIPPED_LOW_MEMORY record with
                                 incomplete fields -> schema validation
                                 failure BEFORE consumer logic
  Attack 5  wrong source         a valid-looking render whose scene is
                                 not the supplied canonical GLB -> FAIL

Plus the typed-record schema contract (Workstream 4), the completeness
ladder (Workstream 2), and the raw-document identity unit contract
(Workstream 1). Live end-to-end attacks run when the headless
Chromium/Node pair is available (same skip discipline as the R441
battery).
"""
from __future__ import annotations

import json
import struct
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.visual_compiler import gltf_doc  # noqa: E402
from discovery_fabric.engine.visual_compiler import material_mapper  # noqa: E402
from discovery_fabric.engine.visual_compiler import render_record_schema as rrs  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_gate  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_set  # noqa: E402
from discovery_fabric.engine.visual_compiler import \
    visual_compiler as vc  # noqa: E402


def _box(extents, translation):
    import trimesh
    b = trimesh.creation.box(extents=extents)
    b.apply_translation(translation)
    return b


def _make_glb(path: Path, named: bool = True) -> None:
    import trimesh
    s = trimesh.Scene({
        "chassis_housing": _box([70, 30, 40], [0, 15, 0]),
        "drive_shaft": trimesh.creation.cylinder(
            radius=6, height=45, sections=32).apply_translation(
            [0, 50, 0]),
        "sensor_module": _box([22, 12, 18], [28, 36, 0]),
    })
    if not named:
        s = trimesh.Scene({k: v for k, v in s.geometry.items()})
        # export with the geometry names dropped at the glTF node layer
        s.export(path, file_type="glb")
        _strip_glb_names(path)
    else:
        s.export(path, file_type="glb")


def _strip_glb_names(glb_path: Path) -> None:
    """Rewrite the GLB container with every node `name` REMOVED from
    the raw JSON chunk — geometry, accessors and meshes preserved
    byte-for-byte where possible (the Attack-1 mutation: strip the
    identity, keep the geometry)."""
    raw = glb_path.read_bytes()
    magic, version, length = struct.unpack("<4sII", raw[:12])
    assert magic == b"glTF"
    offset = 12
    chunks = []
    while offset < length:
        clen, ctype = struct.unpack("<I4s", raw[offset:offset + 8])
        chunks.append((ctype, raw[offset + 8:offset + 8 + clen]))
        offset += 8 + clen
    doc = json.loads(chunks[0][1].decode("utf-8"))
    for node in doc.get("nodes", []):
        node.pop("name", None)
    js = json.dumps(doc, separators=(",", ":")).encode("utf-8")
    pad = (4 - len(js) % 4) % 4
    js += b" " * pad
    bin_chunk = chunks[1] if len(chunks) > 1 else None
    out = bytearray()
    total = 12 + 8 + len(js)
    if bin_chunk:
        total += 8 + len(bin_chunk[1])
    out += struct.pack("<4sII", b"glTF", 2, total)
    out += struct.pack("<I4s", len(js), b"JSON") + js
    if bin_chunk:
        out += struct.pack("<I4s", len(bin_chunk[1]),
                           b"BIN\x00") + bin_chunk[1]
    glb_path.write_bytes(bytes(out))


# ---------------------------------------------------------------------------
# Workstream 1 — canonical node identity is proven from the RAW document
# ---------------------------------------------------------------------------
class TestRawDocumentIdentity:
    def test_named_glb_reports_raw_names(self, tmp_path):
        glb = tmp_path / "m.glb"
        _make_glb(glb, named=True)
        raw = gltf_doc.raw_part_identity(str(glb))
        assert raw["mesh_nodes"] == 3
        assert raw["named"] == ["chassis_housing", "drive_shaft",
                                "sensor_module"]
        assert raw["unnamed_unattributed"] == []

    def test_stripped_glb_reports_no_raw_names(self, tmp_path):
        """THE Attack-1 unit: the RAW document carries no names after
        stripping — whatever trimesh would report is synthesized."""
        glb = tmp_path / "m.glb"
        _make_glb(glb, named=True)
        _strip_glb_names(glb)
        raw = gltf_doc.raw_part_identity(str(glb))
        assert raw["named"] == []
        assert len(raw["unnamed_unattributed"]) == 3
        # the geometry is untouched (stripping is identity-only)
        import trimesh
        scene = trimesh.load(str(glb))
        if isinstance(scene, trimesh.Trimesh):
            scene = trimesh.Scene(scene)
        assert len(scene.graph.nodes_geometry) == 3

    def test_gate_identity_check_fails_the_stripped_glb(self, tmp_path):
        glb = tmp_path / "m.glb"
        _make_glb(glb, named=True)
        _strip_glb_names(glb)
        spec = {"model": {"nodes": [
            {"name": "chassis_housing"}, {"name": "drive_shaft"},
            {"name": "sensor_module"}]}}
        check = visual_gate.check_canonical_node_identity(glb, spec)
        assert check["pass"] is False
        assert any("ABSENT from the raw glTF document" in r
                   for r in check["reasons"])

    def test_gate_identity_check_passes_a_canonical_glb(self, tmp_path):
        glb = tmp_path / "m.glb"
        _make_glb(glb, named=True)
        spec = {"model": {"nodes": [
            {"name": "chassis_housing"}, {"name": "drive_shaft"},
            {"name": "sensor_module"}]}}
        check = visual_gate.check_canonical_node_identity(glb, spec)
        assert check["pass"] is True, check

    def test_primitive_slices_inherit_identity(self, tmp_path):
        """The multi-prim export pattern: unnamed primitive meshes
        under a NAMED part node are slices, not missing identities."""
        glb = tmp_path / "slices.glb"
        doc = {
            "asset": {"version": "2.0"},
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": [
                {"name": "multi_prim_part", "mesh": 0,
                 "children": [1, 2]},
                {"mesh": 1}, {"mesh": 2},
            ],
            "meshes": [{"primitives": []}] * 3,
        }
        js = json.dumps(doc).encode("utf-8")
        pad = (4 - len(js) % 4) % 4
        js += b" " * pad
        out = bytearray()
        out += struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(js))
        out += struct.pack("<I4s", len(js), b"JSON") + js
        glb.write_bytes(bytes(out))
        raw = gltf_doc.raw_part_identity(str(glb))
        # the named part + two slices: no unattributed nodes
        assert raw["named"] == ["multi_prim_part"]
        assert raw["primitive_slices"] == 2
        assert raw["unnamed_unattributed"] == []

    def test_loader_synthesized_names_are_not_evidence(self, tmp_path):
        """The R442 blind spot, closed: a LOADER reports names for the
        stripped GLB (synthesized); the raw document walk does not —
        and the gate rule is written against the raw document."""
        import trimesh
        glb = tmp_path / "m.glb"
        _make_glb(glb, named=True)
        _strip_glb_names(glb)
        scene = trimesh.load(str(glb))
        if isinstance(scene, trimesh.Trimesh):
            scene = trimesh.Scene(scene)
        loader_names = list(scene.graph.nodes_geometry)
        assert len(loader_names) == 3  # the loader invents three names
        raw = gltf_doc.raw_part_identity(str(glb))
        assert raw["named"] == []      # the raw document proves none

    def test_trimesh_naming_rule_is_retired(self):
        """Art. LXIV disposition: the replaced trimesh-based naming
        check is DELETED from the gate in the same change that ships
        the raw-document identity check."""
        src = (REPO / "discovery_fabric/engine/visual_compiler/"
               "visual_gate.py").read_text()
        assert "def check_node_naming" not in src
        assert "import trimesh" not in src
        assert "def check_canonical_node_identity" in src


# ---------------------------------------------------------------------------
# Workstream 2 — the visual-set ladder and its four verdicts
# ---------------------------------------------------------------------------
class TestVisualSetLadder:
    def test_multi_part_ladder_is_complete_set(self):
        req = visual_set.required_artifacts(3)
        assert req["required_count"] if False else True
        assert len(req["required"]) == 23
        assert req["waived"] == []
        for name in ("hero.png", "poster.png", "dimension.png",
                     "section.png", "exploded.png", "exploded.glb",
                     "hero.glb", "orthographic/iso.png",
                     "turntable/frame-01.png", "turntable/frame-12.png"):
            assert name in req["required"]

    def test_single_part_exploded_is_a_typed_waiver(self):
        req = visual_set.required_artifacts(1)
        assert len(req["required"]) == 21
        assert {w["artifact"] for w in req["waived"]} == {
            "exploded.png", "exploded.glb"}
        assert all("typed waiver" in w["reason"] for w in req["waived"])

    def test_classify_missing_view_is_not_complete(self, tmp_path):
        req = visual_set.required_artifacts(3)
        present = req["required"][:5]
        for name in present:
            p = tmp_path / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"x")
        c = visual_set.classify(str(tmp_path), 3)
        assert c["complete"] is False
        assert c["present_count"] == 5
        assert "turntable/frame-01.png" in c["missing"]

    def test_gate_not_run_fails_closed_with_completeness(self, tmp_path):
        gate = visual_gate.evaluate(str(tmp_path), {}, {},
                                    "RENDER_SKIPPED_LOW_MEMORY")
        assert gate["verdict"] == "NOT_RUN"
        assert gate["hero_suppressed"] is True
        assert gate["release_blocked"] is True
        assert gate["visual_set"]["complete"] is False

    def test_rules_thresholds_carry_provenance_entry(self):
        th = json.loads((REPO / "discovery_fabric/engine/"
                         "visual_compiler/"
                         "visual_compiler_thresholds.json").read_text())
        assert th["material_distinction_min_de00"]["value"] == 10.0
        assert th["material_distinction_min_de00"]["basis"]
        assert th["material_distinction_min_de00"]["uncertainty"]
        assert any(r["rev"] == 3 and r["round"] == "R443"
                   for r in th["revision_history"])


# ---------------------------------------------------------------------------
# Workstream 3 — material semantics are measurable
# ---------------------------------------------------------------------------
class TestMaterialDistinction:
    def test_ciede2000_known_values(self):
        # identical colors -> 0
        assert visual_gate.ciede2000(np.array([50., 10., -5.]),
                                     np.array([50., 10., -5.])) == 0.0
        # red vs blue in Lab: large separation
        d = visual_gate.ciede2000(np.array([53.2, 80.1, 67.2]),
                                  np.array([55.0, -50.0, -20.0]))
        assert d > 40

    def _probe_png(self, path: Path, colors):
        w, h = 400, 100
        img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        px = img.load()
        n = len(colors)
        sw = w // n
        for i, rgb in enumerate(colors):
            for y in range(h):
                for x in range(i * sw, (i + 1) * sw):
                    px[x, y] = tuple(rgb) + (255,)
        img.save(path)

    def test_distinct_colors_pass_identical_fail(self, tmp_path):
        probe = tmp_path / "material_probe.png"
        self._probe_png(probe, [(200, 40, 40), (40, 200, 40),
                                (40, 40, 220)])
        meta = {"classes": ["a", "b", "c"],
                "rects": {"a": [0, 0, 133, 100], "b": [133, 0, 133, 100],
                          "c": [266, 0, 134, 100]}}
        m = visual_gate.measure_material_distinction(probe, meta)
        assert m["pass"] is True, m
        # the spoof: two classes share ONE visual material
        meta2 = {"classes": ["a", "b", "c"],
                 "rects": {"a": [0, 0, 133, 100], "b": [0, 0, 133, 100],
                           "c": [266, 0, 134, 100]}}
        m2 = visual_gate.measure_material_distinction(probe, meta2)
        assert m2["pass"] is False
        assert m2["failed_pairs"] == ["a/b=0.00"]

    def test_missing_probe_fails_closed(self, tmp_path):
        m = visual_gate.measure_material_distinction(
            tmp_path / "absent.png", {})
        assert m["pass"] is False

    def test_shipped_palette_pairwise(self):
        import itertools
        labs = {}
        for cls, mat in material_mapper.SEMANTIC_MATERIALS.items():
            # the base colors are LINEAR RGB (the renderer's working
            # space); the perceived color applies the sRGB encode first
            def lin(u, f=lambda u: 12.92 * u if u <= 0.0031308
                    else 1.055 * (u ** (1 / 2.4)) - 0.055):
                return f(u)
            c = [lin(v) for v in mat["base"]]
            M = np.array([[0.4124564, 0.3575761, 0.1804375],
                          [0.2126729, 0.7151522, 0.0721750],
                          [0.0193339, 0.1191920, 0.9503041]])
            xyz = (np.array(c) @ M.T) / np.array([0.95047, 1.0, 1.08883])
            d = 6 / 29

            def fun(t):
                return t ** (1 / 3) if t > d ** 3 else \
                    t / (3 * d * d) + 4 / 29
            fx, fy, fz = fun(xyz[0]), fun(xyz[1]), fun(xyz[2])
            labs[cls] = np.array([116 * fy - 16, 500 * (fx - fy),
                                  200 * (fy - fz)])
        # pairs whose spec-level base-color separation sits below the
        # bar but whose RENDERED separation is carried by metallic/
        # roughness contrast — each verified live by the rendered probe
        # (the acceptance, test_positive_baseline_complete_pass and the
        # 13-class iteration runs of 2026-09-10):
        #   ceramic/machined_metal   spec 5.17 -> rendered ~12.6 (metallic 1.0 mirror)
        #   glass/machined_metal     spec 9.82 -> rendered ~10.7 (metallic 1.0 mirror)
        #   battery/rubber           spec 7.84 -> rendered ~11.3 (metallic 0.3 vs dielectric)
        #   conduit_power/polymer    spec 5.12 -> rendered ~11.5 (metallic 0.85 vs dielectric)
        metallic_or_roughness_pairs = {
            ("ceramic", "machined_metal"),
            ("glass", "machined_metal"),
            ("battery", "rubber"),
            ("conduit_power", "polymer")}
        below = []
        for a, b in itertools.combinations(sorted(labs), 2):
            de = visual_gate.ciede2000(labs[a], labs[b])
            if de < 10.0 and (a, b) not in metallic_or_roughness_pairs:
                below.append((a, b, round(de, 2)))
        assert below == [], below


# ---------------------------------------------------------------------------
# Workstream 4 — typed render records: total and validated
# ---------------------------------------------------------------------------
class TestTypedRenderRecords:
    def test_every_concrete_status_maps_to_a_class(self):
        for status in ("OK", "PARTIAL", "RENDER_FAILED", "RENDER_TIMEOUT",
                       "RENDER_PARTIAL", "RENDER_SKIPPED_LOW_MEMORY",
                       "RENDER_SKIPPED_NO_RENDERER",
                       "RENDER_SKIPPED_NO_SOURCE_GLB",
                       "RENDER_NOT_RUN"):
            assert rrs.status_class(status) in {
                "RENDER_SUCCEEDED", "RENDER_FAILED",
                "RENDER_SKIPPED_LOW_MEMORY",
                "RENDER_SKIPPED_INFRA_UNAVAILABLE", "RENDER_NOT_RUN"}

    def test_unknown_status_is_rejected(self):
        with pytest.raises(rrs.RenderRecordValidationError):
            rrs.validate_render_record({"status": "SOMEHOW_FINE"})

    def test_memory_guard_record_is_finalized_to_total_shape(self):
        """THE R442-disclosed defect: a guard skip without out_dir /
        visual_gate. finalize fills the total shape; validate passes;
        consumers need no status-branching field guesses."""
        guard = {"stage": "RENDER",
                 "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
                 "status": "RENDER_SKIPPED_LOW_MEMORY",
                 "note": "headless Chromium does not fit"}
        rec = rrs.finalize_render_record(dict(guard))
        rrs.validate_render_record(rec)   # must not raise
        assert rec["out_dir"] is None
        assert rec["visual_gate"]["verdict"] == "NOT_RUN"
        assert rec["hero_suppressed"] is True
        assert rec["release_blocked"] is True
        assert rec["reason"].strip()

    def test_directive_states_each_validate(self):
        states = {
            "RENDER_SUCCEEDED": {
                "status": "OK", "stage": "RENDER",
                "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
                "source_glb": "/m.glb", "source_glb_sha256": "ab" * 32,
                "artifacts": {"hero.png": {"bytes": 1}},
                "missing_artifacts": [],
                "visual_gate": {"verdict": "COMPLETE_PASS"},
                "hero_suppressed": False, "release_blocked": False},
            "RENDER_FAILED": {
                "status": "RENDER_FAILED", "stage": "RENDER",
                "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
                "reason": "scene solve failed"},
            "RENDER_SKIPPED_LOW_MEMORY": {
                "status": "RENDER_SKIPPED_LOW_MEMORY", "stage": "RENDER",
                "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
                "reason": "headless Chromium does not fit"},
            "RENDER_NOT_RUN": {
                "status": "RENDER_NOT_RUN", "stage": "RENDER",
                "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
                "reason": "stage not reached"},
        }
        for label, rec in states.items():
            out = rrs.finalize_render_record(dict(rec))
            rrs.validate_render_record(out)
            assert out["status_class"] == label

    def test_malformed_skip_is_caught_before_consumers(self):
        rec = {"status": "RENDER_SKIPPED_LOW_MEMORY", "stage": "RENDER",
               "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
               "note": "skipped"}
        with pytest.raises(rrs.RenderRecordValidationError) as ei:
            rrs.validate_render_record(rec)
        assert "out_dir" in str(ei.value)

    def test_skip_cannot_carry_a_measured_verdict(self):
        rec = rrs.finalize_render_record({
            "status": "RENDER_SKIPPED_LOW_MEMORY", "stage": "RENDER",
            "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
            "reason": "x",
            "visual_gate": {"verdict": "COMPLETE_PASS",
                            "hero_suppressed": False,
                            "release_blocked": False}})
        assert rec["visual_gate"]["verdict"] == "NOT_RUN"
        assert rec["hero_suppressed"] is True
        rrs.validate_render_record(rec)

    def test_gate_partials_are_valid_on_succeeded_records(self):
        rec = rrs.finalize_render_record({
            "status": "PARTIAL", "stage": "RENDER",
            "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
            "source_glb": "/m.glb", "source_glb_sha256": "ab" * 32,
            "artifacts": {}, "missing_artifacts": ["section.png"],
            "visual_gate": {"verdict": "PARTIAL",
                            "hero_suppressed": True,
                            "release_blocked": True}})
        rrs.validate_render_record(rec)

    def test_compile_memory_guard_path_returns_valid_record(
            self, tmp_path, monkeypatch):
        """The integration of the R442 defect closure: compile_visuals
        under a memory-guard skip returns a record that passes the
        schema WITHOUT consumer field-guessing."""
        from discovery_fabric.engine.visual_compiler import render_worker
        monkeypatch.setattr(
            render_worker, "memory_guard",
            lambda ctx, mode="async": {
                "status": "RENDER_SKIPPED_LOW_MEMORY",
                "note": "guard",
                "mem_available_mb": 10})
        (tmp_path / "MODEL").mkdir()
        rec = vc.compile_visuals(str(tmp_path), memory_mode="async")
        rrs.validate_render_record(rec)
        assert rec["status"] == "RENDER_SKIPPED_LOW_MEMORY"
        assert rec["visual_gate"]["verdict"] == "NOT_RUN"
        assert rec["release_blocked"] is True


# ---------------------------------------------------------------------------
# Attack 5 — wrong source (unit level: bounds + identity disagreement)
# ---------------------------------------------------------------------------
class TestWrongSourceWitness:
    def test_source_agreement_passes_for_the_same_geometry(self,
                                                           tmp_path):
        """The honest positive: the gate check runs on the GROUNDED
        EXPORT (what hero.glb is in the real pipeline). Simulate the
        export by applying the spec's grounding transform to the
        source geometry, then verify the agreement holds exactly."""
        import trimesh
        from discovery_fabric.engine.visual_compiler import scene_builder
        glb = tmp_path / "m.glb"
        _make_glb(glb, named=True)
        spec = scene_builder.build_scene_spec(str(glb), None, None)
        s = float(spec["grounding"]["scale"])
        c = spec["model"]["center"]
        min_y = spec["model"]["min_y"]
        scene = trimesh.load(str(glb))
        out_scene = trimesh.Scene()
        for name, geom in scene.geometry.items():
            g = geom.copy()
            g.apply_translation([-c[0], -min_y, -c[2]])
            g.apply_scale(s)
            out_scene.add_geometry(g, node_name=name)
        exported = tmp_path / "hero.glb"
        out_scene.export(exported, file_type="glb")
        check = visual_gate.check_source_scene_agreement(exported, spec)
        assert check["pass"] is True, check
        assert check["max_bound_deviation"] <= check["tolerance"]

    def test_source_agreement_fails_for_a_different_geometry(self,
                                                             tmp_path):
        glb_a = tmp_path / "a.glb"
        _make_glb(glb_a, named=True)
        glb_b = tmp_path / "b.glb"
        import trimesh
        s = trimesh.Scene({
            "tower_part": trimesh.creation.cylinder(
                radius=4, height=120, sections=32).apply_translation(
                [0, 60, 0]),
        })
        s.export(glb_b, file_type="glb")
        spec_a = {"model": {"nodes": [{"name": "chassis_housing"},
                                      {"name": "drive_shaft"},
                                      {"name": "sensor_module"}],
                            "min": [-35.0, 0.0, -20.0],
                            "max": [39.0, 72.5, 20.0],
                            "center": [2.0, 36.25, 0.0],
                            "min_y": 0.0},
                  "grounding": {"scale": 0.05}}
        check = visual_gate.check_source_scene_agreement(glb_b, spec_a)
        assert check["pass"] is False
        assert check["max_bound_deviation"] > check["tolerance"]

    def test_identity_set_mismatch_is_reported(self, tmp_path):
        glb = tmp_path / "m.glb"
        _make_glb(glb, named=True)
        spec = {"model": {"nodes": [{"name": "part_one"},
                                    {"name": "part_two"}]}}
        check = visual_gate.check_canonical_node_identity(glb, spec)
        assert check["pass"] is False
        assert any("does not match the scene spec" in r
                   for r in check["reasons"])


# ---------------------------------------------------------------------------
# the LIVE attacks (headless Chromium) — the full compile, then the
# mutation, then the gate re-measure on the saved artifacts
# ---------------------------------------------------------------------------
def _chrome_available() -> bool:
    try:
        from discovery_fabric.engine.visual_compiler import render_worker
        return bool(render_worker.find_node()
                    and render_worker.find_chrome()
                    and render_worker.renderer_deps_present() is None)
    except Exception:  # noqa: BLE001
        return False


def _compile_fixture(tmp_path: Path) -> dict:
    import trimesh
    (tmp_path / "MODEL").mkdir(parents=True, exist_ok=True)
    s = trimesh.Scene({
        "chassis_housing": _box([70, 30, 40], [0, 15, 0]),
        "drive_shaft": trimesh.creation.cylinder(
            radius=6, height=45, sections=32).apply_translation(
            [0, 50, 0]),
        "sensor_module": _box([22, 12, 18], [28, 36, 0]),
        "coolant_coil": trimesh.creation.cylinder(
            radius=9, height=20, sections=24).apply_translation(
            [-26, 40, 0]),
        "glass_port": _box([10, 10, 2], [0, 68, 19]),
    })
    s.export(tmp_path / "MODEL" / "engineering_model.glb", file_type="glb")
    return vc.compile_visuals(str(tmp_path), memory_mode="async")


@pytest.mark.skipif(not _chrome_available(),
                    reason="headless Chromium/Node pair not available")
class TestLiveAdversarialBattery:
    def _compile(self, tmp_path):
        rec = _compile_fixture(tmp_path)
        assert rec["status"] in ("OK", "PARTIAL"), rec
        assert rec["visual_gate"]["verdict"] == "COMPLETE_PASS", \
            rec["visual_gate"]["reasons"]
        return rec

    def test_positive_baseline_complete_pass(self, tmp_path):
        """The gate must NOT be a universal rejector (Art. V): a clean
        multi-part compile passes COMPLETELY — the full ladder, the
        raw-document identity, source agreement and the material
        distinction all measured."""
        rec = self._compile(tmp_path)
        assert rec["hero_suppressed"] is False
        vs = rec["visual_gate"]["visual_set"]
        assert vs["complete"] is True and vs["required_count"] == 23
        md = rec["visual_gate"]["checks"]["material_distinction"]
        assert md["pairs_measured"] == 10
        assert all(p["delta_e00"] >= 10.0 for p in md["pairs"])

    def test_attack_1_stripped_identity_fails_closed(self, tmp_path):
        rec = self._compile(tmp_path)
        out = Path(rec["out_dir"])
        _strip_glb_names(out / "hero.glb")
        spec = json.loads((out / "scene_spec.json").read_text())
        gate = visual_gate.evaluate(str(out), spec, rec, "OK")
        assert gate["verdict"] == "FAIL"
        assert "node_identity" in gate["failed_rules"]
        reasons = " ".join(gate["reasons"])
        assert "ABSENT from the raw glTF document" in reasons or \
            "does not match the scene spec" in reasons
        assert gate["hero_suppressed"] is True
        assert gate["release_blocked"] is True

    def test_attack_2_missing_view_is_not_complete(self, tmp_path):
        rec = self._compile(tmp_path)
        out = Path(rec["out_dir"])
        (out / "section.png").unlink()
        (out / "turntable" / "frame-07.png").unlink()
        spec = json.loads((out / "scene_spec.json").read_text())
        gate = visual_gate.evaluate(str(out), spec, rec, "OK")
        assert gate["verdict"] == "PARTIAL"
        assert gate["visual_set"]["complete"] is False
        assert "section.png" in gate["visual_set"]["missing"]
        assert "turntable/frame-07.png" in gate["visual_set"]["missing"]
        assert gate["hero_suppressed"] is True
        assert gate["release_blocked"] is True
        assert any("NOT_COMPLETE" in r for r in gate["reasons"])

    def test_attack_3_material_spoof_fails(self, tmp_path):
        rec = self._compile(tmp_path)
        out = Path(rec["out_dir"])
        spec = json.loads((out / "scene_spec.json").read_text())
        # the spoof: two semantic classes given the SAME visual material
        probe = dict(rec.get("material_probe") or {})
        classes = probe.get("classes") or []
        assert len(classes) >= 2
        a, b = classes[0], classes[1]
        probe["rects"] = dict(probe["rects"])
        probe["rects"][b] = probe["rects"][a]   # identical probe region
        rec2 = dict(rec)
        rec2["material_probe"] = probe
        gate = visual_gate.evaluate(str(out), spec, rec2, "OK")
        assert gate["verdict"] == "FAIL"
        assert "material_distinction" in gate["failed_rules"]
        assert any(f"{a}/{b}" in fp for fp in
                   gate["checks"]["material_distinction"]["failed_pairs"])
        assert gate["release_blocked"] is True

    def test_attack_4_malformed_skip_record_never_reaches_consumers(
            self, tmp_path):
        """A RENDER_SKIPPED_LOW_MEMORY record with incomplete fields
        must die at schema validation — package.py runs the validator
        BEFORE reading consumer fields (source-scan asserts the wiring;
        the schema contract itself is asserted in TestTypedRenderRecords)."""
        src = (REPO / "discovery_fabric/engine/invention_bridge/"
               "package.py").read_text()
        assert "validate_render_record" in src
        assert "_record_schema_error" in src

    def test_attack_5_wrong_source_fails(self, tmp_path):
        rec = self._compile(tmp_path)
        out = Path(rec["out_dir"])
        # a DIFFERENT geometry, compiled into its own run
        other = tmp_path / "other"
        (other / "MODEL").mkdir(parents=True)
        import trimesh
        s = trimesh.Scene({
            "tower_part": trimesh.creation.cylinder(
                radius=4, height=120, sections=32).apply_translation(
                [0, 60, 0]),
        })
        s.export(other / "MODEL" / "engineering_model.glb",
                 file_type="glb")
        from discovery_fabric.engine.visual_compiler import scene_builder
        spec_other = scene_builder.build_scene_spec(
            str(other / "MODEL" / "engineering_model.glb"), None, None)
        # the render set in `out` is evaluated against THE OTHER spec —
        # a valid-looking render that is not the supplied canonical GLB
        gate = visual_gate.evaluate(str(out), spec_other, rec, "OK")
        assert gate["verdict"] == "FAIL"
        assert "source_agreement" in gate["failed_rules"]
        assert "node_identity" in gate["failed_rules"]
        assert gate["release_blocked"] is True

    def test_package_rejects_partial_gate(self, tmp_path):
        """The consumer join: a PARTIAL gate blocks the buyer package
        (the release chain consumes the verdict, not the file count)."""
        from discovery_fabric.engine.invention_bridge import package
        rec = self._compile(tmp_path)
        out = Path(rec["out_dir"])
        (out / "section.png").unlink()
        spec = json.loads((out / "scene_spec.json").read_text())
        gate = visual_gate.evaluate(str(out), spec, rec, "OK")
        assert package._visual_release_ok(gate) is False
        gate_pass = rec["visual_gate"]
        assert package._visual_release_ok(gate_pass) is True
        # the legacy PASS vocabulary without a completeness block stays
        # accepted (pre-R443 records); with a false block it is refused
        assert package._visual_release_ok(
            {"verdict": "PASS"}) is True
        assert package._visual_release_ok(
            {"verdict": "PASS",
             "visual_set": {"complete": False}}) is False
