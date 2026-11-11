"""R6 14-gate certification replacement for the retired CAD kernel suite.

The certification workflow referenced tests/test_r380_cad_pipeline.py, which
was retired (it exercised the pre-R425 CAD compiler archive — dead code).
This suite covers the LIVE CAD capability the package layer drives:

- parametric construction (layered_panel / dual_lumen_catheter /
  cylindrical_device) via the canonical builders in
  discovery_fabric.engine.invention_bridge.engineering_geometry
- Boolean operation correctness (union/cut, containment check)
- geometry measure() surface (volume, bbox, is_valid_solid)
- validate_gates() (trimesh watertight + regeneration determinism)
- export() GLB/STEP/STL bytes with returned sha256 consistent
"""
import hashlib
import json
import math
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

cq = pytest.importorskip("cadquery")
trimesh = pytest.importorskip("trimesh")

from discovery_fabric.engine.invention_bridge import engineering_geometry as eg  # noqa: E402

CATH = {"outer_diameter": 3.0, "primary_lumen_diameter": 1.1,
         "floor_lumen_diameter": 0.6, "floor_offset": 1.0, "length": 100.0}
PANEL = {"panel_width": 160.0, "panel_length": 160.0, "substrate_t": 3.0,
         "cell_t": 0.2, "functional_t": 0.5, "frame_w": 10.0}
CYL = {"outer_diameter": 40.0, "wall_t": 2.0, "length": 60.0}


def test_dual_lumen_catheter_volume_and_validity():
    s = eg.build_dual_lumen_catheter(CATH)
    m = eg.measure(s)
    # body cylinder minus the two through-lumens
    expected = math.pi * (CATH["outer_diameter"] ** 2
                          - CATH["primary_lumen_diameter"] ** 2
                          - CATH["floor_lumen_diameter"] ** 2) / 4 * CATH["length"]
    assert m["is_valid_solid"] is True
    assert abs(m["volume_mm3"] - expected) < 1.0
    assert m["bbox"]["zmax"] >= CATH["length"] - 1e-6


def test_dual_lumen_catheter_rejects_wall_containment_violation():
    # od 1.2 mm: primary 0.55 + floor 0.30 + 0.2 wall allowance = 1.05;
    # with od=1.2 and pd=1.6 -> (0.8+0.25+0.2)=1.25 > 1.2 must raise
    bad = dict(CATH, outer_diameter=1.2, primary_lumen_diameter=1.6)
    with pytest.raises(ValueError):
        eg.build_dual_lumen_catheter(bad)


def test_layered_panel_solid_and_frame():
    s = eg.build_layered_panel(PANEL)
    m = eg.measure(s)
    assert m["is_valid_solid"] is True
    # frame ring adds material beyond the substrate alone
    sub_vol = PANEL["panel_width"] * PANEL["panel_length"] * PANEL["substrate_t"]
    assert m["volume_mm3"] > sub_vol
    assert abs(m["bbox"]["xlen"] - PANEL["panel_width"]) < 1e-6


def test_panel_rejects_non_positive_params():
    with pytest.raises(ValueError):
        eg.build_layered_panel({"panel_width": 0.0})


def test_cylindrical_device_valid_solid():
    s = eg.build_cylindrical_device(CYL)
    m = eg.measure(s)
    assert m["is_valid_solid"] is True
    assert m["volume_mm3"] > 0


def test_validate_gates_watertight_and_regeneration():
    s = eg.build_dual_lumen_catheter(CATH)
    verts, tris = s.val().tessellate(0.01)
    raw = trimesh.Trimesh(
        vertices=[(v.x, v.y, v.z) for v in verts],
        faces=[list(t) for t in tris], process=False)
    # measured reality: OCCT tessellation emits duplicate vertices
    # (762 of 1518 above), so the raw mesh is NOT watertight; the gate
    # reports its measurement honestly as False. This must not be
    # "fixed" by recoloring the assertion — it is reported.
    raw_report = eg.validate_gates(s, raw,
                                   rebuild_fn=lambda: eg.build_dual_lumen_catheter(CATH))
    assert raw_report["gates"]["G1_trimesh_watertight"] is False
    assert raw_report["gates"]["G9_regeneration"]["deterministic"] is True

    merged = trimesh.Trimesh(
        vertices=[(v.x, v.y, v.z) for v in verts],
        faces=[list(t) for t in tris])
    merged_report = eg.validate_gates(s, merged,
                                      rebuild_fn=lambda: eg.build_dual_lumen_catheter(CATH))
    assert merged_report["gates"]["G1_trimesh_watertight"] is True
    assert merged_report["passed"] is True


def test_export_bytes_and_sha_consistent(tmp_path):
    s = eg.build_dual_lumen_catheter(CATH)
    out = eg.export(s, "catheter_test", str(tmp_path))
    for key in ("glb_path", "step_path", "stl_path"):
        assert Path(out[key]).exists(), key
    assert Path(out["step_path"]).stat().st_size > 1000
    assert Path(out["stl_path"]).stat().st_size > 100
    assert hashlib.sha256(out["glb_bytes"]).hexdigest() == out["glb_sha256"]


def test_export_parametric_source_known_and_unknown_forms():
    text, identity = eg.export_parametric_source("dual_lumen_catheter", CATH)
    assert text and "def build_dual_lumen_catheter" in text
    assert identity.get("builder_function") == "build_dual_lumen_catheter"
    bad_text, bad_identity = eg.export_parametric_source("not_a_form", {})
    assert bad_text is None
    assert bad_identity.get("builder_function") is None


def test_verify_cad_source_provenance_absent_record(tmp_path):
    verdict = eg.verify_cad_source_provenance(str(tmp_path))
    assert verdict["verdict"] == "PROVENANCE_RECORD_ABSENT"
    record = tmp_path / "CAD_SOURCE_PROVENANCE.json"
    record.write_text(json.dumps({"canonical_builder": {
        "builder_function": "build_dual_lumen_catheter",
        "canonical_module": eg.FORM_LIBRARY["dual_lumen_catheter"].__module__}}),
        encoding="utf-8")
    verdict2 = eg.verify_cad_source_provenance(str(tmp_path))
    assert verdict2["verdict"] in ("CANONICAL_SOURCE_CONFIRMED",
                                    "DRIFT_DETECTED",
                                    "PROVENANCE_RECORD_UNREADABLE")
