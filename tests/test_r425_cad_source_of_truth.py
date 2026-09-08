"""tests/test_r425_cad_source_of_truth.py — R425 §2 regression.

ONE CAD SOURCE OF TRUTH. The package's MODEL/PARAMETRIC_MODEL_SOURCE.py
must be DERIVED from the exact canonical engineering geometry program
(engineering_geometry.FORM_LIBRARY) — never an independently handwritten
reimplementation in the package layer.

Proven here:
  1. the exported source IS the canonical builder (verbatim source,
     matching identity hashes);
  2. clean regeneration — the SHIPPED parameter source reconstructs the
     same geometry as the canonical builder (executed standalone as a
     subprocess, exactly the way a recipient would run it);
  3. the package layer contains no parallel handwritten geometry
     definitions (the R424-era _FORM_SOURCE class is closed);
  4. mutation detection — a mutated canonical builder is DETECTED by
     the package provenance (verify_cad_source_provenance -> DRIFT);
  5. a tampered shipped source FAILS the regeneration check (the
     adversarial demonstration, Art. XVII: attack the control);
  6. CAD_SOURCE_PROVENANCE.json records the complete relationship:
     canonical builder identity, form, source hash, parameter hash,
     derived artifact hashes, regeneration relationship.
"""
from __future__ import annotations

import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.invention_bridge.bridge import (
    bridge as run_bridge)
from discovery_fabric.engine.invention_bridge import (
    engineering_geometry as eg)
from discovery_fabric.engine.invention_bridge import (
    elite_model_layer as eml)

CATHETER_PARAMS = {
    "outer_diameter": 3.0, "primary_lumen_diameter": 1.1,
    "floor_lumen_diameter": 0.6, "floor_offset": 1.0, "length": 100.0}


def _eng_run() -> dict:
    return {
        "session_id": "ts_r425_cad",
        "user_text": "keep minimum drainage when primary lumen obstructs",
        "final_state": {"final_status": "EVOLVED_INVENTION_CANDIDATE",
                        "causal_chain": {"intervention_site":
                                         "catheter"}},
        "invention_specification": {
            "causal_chain": {"value": {
                "intervention_site": "dual lumen catheter"}},
            "problem": {"value": {"device": "dual lumen catheter"}}},
        "engineering_specification": {
            "parameters": [
                {"param_id": "outer_diameter_mm", "value": 3.0,
                 "unit": "mm", "envelope": [2.5, 3.5],
                 "value_class": "MODELLED"},
                {"param_id": "primary_lumen_diameter_mm", "value": 1.1,
                 "unit": "mm", "envelope": [0.8, 1.4],
                 "value_class": "MODELLED"},
                {"param_id": "floor_lumen_diameter_mm", "value": 0.6,
                 "unit": "mm", "envelope": [0.4, 0.8],
                 "value_class": "MODELLED"},
                {"param_id": "floor_offset_mm", "value": 1.0,
                 "unit": "mm", "envelope": [0.7, 1.3],
                 "value_class": "MODELLED"},
                {"param_id": "length_mm", "value": 100.0,
                 "unit": "mm", "envelope": [60, 140],
                 "value_class": "MODELLED"}],
            "system_architecture": {"subsystems": []},
            "engineering_core": {}},
        "run_state": {"generations": {"generations": []}},
        "evidence_pack": {"retrieval": []},
    }


@pytest.fixture(scope="module")
def eng_pkg(tmp_path_factory):
    """A full ENGINEERING_3D package built through the REAL bridge."""
    work = tmp_path_factory.mktemp("r425_cad")
    result = run_bridge(_eng_run(), None, str(work), build_renders=False)
    return result, work


class TestExportIsCanonical:
    def test_exported_source_is_verbatim_canonical_builder(self):
        file_text, identity = eg.export_parametric_source(
            "dual_lumen_catheter", CATHETER_PARAMS)
        canonical_src = __import__("inspect").getsource(
            eg.FORM_LIBRARY["dual_lumen_catheter"])
        assert canonical_src in file_text, \
            "the exported source must contain the canonical builder " \
            "VERBATIM (R425 §2: derived, not reimplemented)"
        live = eg.canonical_source_identity("dual_lumen_catheter")
        assert identity["builder_source_sha256"] == \
            live["builder_source_sha256"]
        assert identity["builder_function"] == \
            "build_dual_lumen_catheter"

    def test_no_parallel_geometry_source_in_package_layer(self):
        """The package factory must not carry an independent handwritten
        reimplementation of the canonical builders (the closed R424
        defect class)."""
        layer_src = Path(eml.__file__).read_text()
        assert "_FORM_SOURCE = {" not in layer_src, \
            "a handwritten form-source map would be a SECOND source " \
            "of truth (R425 §2)"
        # no builder-body signatures authored in the package layer
        for fragment in ('box(length, width, thickness',
                         'circle(od * 0.5).extrude(length)',
                         'extrude(h - 2 * wall)'):
            assert fragment not in layer_src
        # and the emission path routes through the canonical export
        assert "export_parametric_source" in layer_src

    def test_unknown_form_exports_nothing(self):
        file_text, identity = eg.export_parametric_source(
            "nonexistent_form", CATHETER_PARAMS)
        assert file_text is None
        assert "UNKNOWN_FORM" in identity["status"]


class TestCleanRegeneration:
    @staticmethod
    def _nondefault_run():
        run = _eng_run()
        params = run["engineering_specification"]["parameters"]
        # NON-default values: outer 3.4 (default 3.0), length 77
        # (default 100) — defeats the defaults-coincidence where a
        # broken key-normalization would silently measure defaults.
        # NON-degenerate by construction: r_primary + r_floor = 0.85 <
        # floor_offset 1.2 (a 0.35 mm inter-lumen wall) — the original
        # 1.3/0.7/1.0 combination was EXACTLY TANGENT (0.65 + 0.35 =
        # 1.0), a zero-wall degenerate design honestly rejected by
        # G1 (see test_exactly_tangent_lumens_are_honestly_rejected).
        for p in params:
            if p["param_id"] == "outer_diameter_mm":
                p["value"] = 3.4
            if p["param_id"] == "primary_lumen_diameter_mm":
                p["value"] = 1.2
            if p["param_id"] == "floor_lumen_diameter_mm":
                p["value"] = 0.5
            if p["param_id"] == "floor_offset_mm":
                p["value"] = 1.2
            if p["param_id"] == "length_mm":
                p["value"] = 77.0
        return run

    def test_nondefault_parameters_regenerate_exactly(self,
                                                      tmp_path):
        """The shipped source must reconstruct the ACTUAL shipped
        parameters (not builder defaults) — the PARAMETERS.json key
        normalization (_mm suffixes) is exercised with values that
        differ from every builder default."""
        work = tmp_path / "nondef"
        work.mkdir()
        result = run_bridge(self._nondefault_run(), None, str(work),
                            build_renders=False)
        pkg = result["package_out"]
        model_dir = Path(pkg["package_dir"]) / "MODEL"
        proc = subprocess.run(
            [sys.executable,
             str(model_dir / "PARAMETRIC_MODEL_SOURCE.py")],
            capture_output=True, text=True, timeout=300,
            cwd=str(model_dir))
        assert proc.returncode == 0, proc.stderr[-300:]
        out = json.loads(proc.stdout)
        kd = json.loads(
            (model_dir / "KEY_DIMENSIONS.json").read_text())
        assert abs(out["volume_mm3"] - kd["volume_mm3"]) <= 1e-3
        for k in ("xlen", "ylen", "zlen"):
            assert abs(out["bbox"][k] - kd["bbox"][k]) <= 1e-3
        assert abs(out["parameters"]["length"] - 77.0) < 1e-9
        assert abs(out["parameters"]["outer_diameter"] - 3.4) < 1e-9

    def test_exactly_tangent_lumens_are_honestly_rejected(self, tmp_path):
        """Adversarial regression (Art. XVII): the EXACTLY TANGENT
        parameter set (r_primary + r_floor == floor_offset — a zero
        inter-lumen wall) must be REJECTED by the G1 watertight gate
        and the bridge must demote honestly to conceptual, never
        shipping a non-manifold engineering STL. Found live while
        closing R425: primary 1.3 / floor 0.7 / offset 1.0 makes the
        two lumens tangent; the OCCT solid is valid but the exported
        tessellation carries one non-manifold edge — unusable
        downstream. The gate catching it is the system working."""
        run = _eng_run()
        params = run["engineering_specification"]["parameters"]
        for p in params:
            if p["param_id"] == "primary_lumen_diameter_mm":
                p["value"] = 1.3
            if p["param_id"] == "floor_lumen_diameter_mm":
                p["value"] = 0.7
        # tangency: 0.65 + 0.35 == floor_offset 1.0 exactly
        work = tmp_path / "tangent"
        work.mkdir()
        result = run_bridge(run, None, str(work), build_renders=False)
        pkg = result["package_out"]
        model_dir = Path(pkg["package_dir"]) / "MODEL"
        # the engineering CAD was NOT earned — no shipped source, no
        # STEP/STL engineering artifacts, honest conceptual demotion
        assert not (model_dir / "PARAMETRIC_MODEL_SOURCE.py").exists(), \
            "a degenerate (non-manifold) geometry must never ship as " \
            "an engineering source"
        assert not list(model_dir.glob("*.step")), \
            "degenerate geometry must not ship engineering STEP"
        assert not list(model_dir.glob("*.stl")), \
            "degenerate geometry must not ship engineering STL"
        ds = json.loads(
            (model_dir / "3D_DESIGN_STATUS.json").read_text())
        assert ds["3d_design_status"] == "PRESENT_CONCEPTUAL"
        assert ds["visualizability_class"] == "SYSTEM_3D"
        # and the demotion reason is recorded, not silent
        basis = (result["visualizability"]
                ["classification_basis"]["reason"])
        assert "demoted to conceptual" in basis, basis
        # the conceptual policy honestly declares no engineering dims
        pol = json.loads(
            (model_dir / "PARAMETERS.json").read_text())
        assert pol["parameters"] == []

    def test_shipped_source_reconstructs_canonical_geometry(
            self, eng_pkg):
        """R425 §2's clean regeneration test: the shipped parameter
        source reconstructs the SAME geometry as the canonical builder —
        executed standalone as a subprocess (a recipient's run)."""
        result, work = eng_pkg
        pkg = result["package_out"]
        with zipfile.ZipFile(pkg["zip_path"]) as zf:
            names = [n for n in zf.namelist()
                     if n.endswith("PARAMETRIC_MODEL_SOURCE.py")]
            assert names, "ENGINEERING package must ship the source"
            src_rel = names[0]
            src_text = zf.read(src_rel).decode("utf-8")
        run_dir = Path(pkg["package_dir"])
        src_file = run_dir / "MODEL" / "PARAMETRIC_MODEL_SOURCE.py"
        assert src_file.read_text() == src_text
        # standalone regeneration, exactly as shipped (reads its own
        # sibling PARAMETERS.json when present)
        proc = subprocess.run(
            [sys.executable, str(src_file)],
            capture_output=True, text=True, timeout=300,
            cwd=str(run_dir / "MODEL"))
        assert proc.returncode == 0, proc.stderr[-400:]
        out = json.loads(proc.stdout)
        canonical = eg.measure(
            eg.FORM_LIBRARY[out["form"]](out["parameters"]))
        assert abs(out["volume_mm3"] - canonical["volume_mm3"]) <= 1e-3
        for k in ("xlen", "ylen", "zlen"):
            assert abs(out["bbox"][k] - canonical["bbox"][k]) <= 1e-3
        # and it agrees with the shipped KEY_DIMENSIONS (the record)
        kd = json.loads(
            (run_dir / "MODEL" / "KEY_DIMENSIONS.json").read_text())
        assert abs(out["volume_mm3"] - kd["volume_mm3"]) <= 1e-3

    def test_regen_check_proves_shipped_equals_canonical(self, eng_pkg):
        result, work = eng_pkg
        pkg = result["package_out"]
        with zipfile.ZipFile(pkg["zip_path"]) as zf:
            regen = json.loads(zf.read(
                "TECHNOLOGY_PACKAGE/MODEL/3D_EVIDENCE/"
                "REGENERATION_CHECK.json"))
        assert regen["shipped_source_executed"] is True
        assert regen["regeneration_status"] == "REPRODUCIBLE", regen
        obj = next(iter(regen["objects"].values()))
        assert obj["shipped_source_equals_canonical_builder"] == "MATCH"


class TestMutationDetection:
    def test_mutated_canonical_builder_is_detected(self, eng_pkg,
                                                   monkeypatch):
        """R425 §2's mutation regression: mutate the canonical builder
        and prove the package provenance DETECTS the change."""
        result, work = eng_pkg
        pkg = result["package_out"]
        model_dir = Path(pkg["package_dir"]) / "MODEL"
        before = eg.verify_cad_source_provenance(str(model_dir))
        assert before["verdict"] == "CANONICAL_SOURCE_CONFIRMED", before

        # mutate the canonical builder (a different program, same form)
        def mutated_builder(params):  # noqa: ARG001
            import cadquery as cq
            od = params.get("outer_diameter", 3.0)
            length = params.get("length", 100.0)
            pd_ = params.get("primary_lumen_diameter", 1.1)
            body = cq.Workplane("XY").circle(od / 2).extrude(length * 0.5)
            primary = (cq.Workplane("XY").workplane(offset=-1)
                       .circle(pd_ / 2).extrude(length + 2))
            return body.cut(primary)

        monkeypatch.setitem(eg.FORM_LIBRARY, "dual_lumen_catheter",
                            mutated_builder)
        after = eg.verify_cad_source_provenance(str(model_dir))
        assert after["verdict"] == "DRIFT_DETECTED", after
        assert "builder_source_sha256" in after["mismatched_fields"]

    def test_missing_provenance_record_is_a_typed_verdict(
            self, tmp_path):
        verdict = eg.verify_cad_source_provenance(str(tmp_path))
        assert verdict["verdict"] == "PROVENANCE_RECORD_ABSENT"


class TestTamperedShippedSource:
    def test_tampered_source_fails_regeneration(self, eng_pkg):
        """Adversarial demonstration (Art. XVII): replace the shipped
        source with a TAMPERED variant and the regeneration check must
        flag NOT_REPRODUCIBLE — the control is attacked, not trusted."""
        result, work = eng_pkg
        pkg = result["package_out"]
        model_dir = Path(pkg["package_dir"]) / "MODEL"
        original = (model_dir / "PARAMETRIC_MODEL_SOURCE.py").read_text()
        try:
            # tamper: a different geometry for the same parameters (a
            # doubled primary-lumen cut radius — a REAL geometry change)
            tampered = original.replace(
                ".circle(pd_ / 2).extrude(length + 2)",
                ".circle(pd_).extrude(length + 2)")
            assert tampered != original
            (model_dir / "PARAMETRIC_MODEL_SOURCE.py").write_text(
                tampered)
            layer = {"files": [], "evidence_files": []}
            geometry_out = result["bridge_out"] if "bridge_out" in \
                result else None
            # rebuild ONLY the evidence layer over the tampered source
            ev_dir = model_dir / "3D_EVIDENCE"
            geo = result.get("geometry_out") or {}
            eml._build_3d_evidence(
                ev_dir, str(Path(pkg["package_dir"])), geo,
                pkg["invention_label"],
                json.loads((model_dir / "PARAMETERS.json").read_text())[
                    "parameters"],
                None, layer)
            regen = json.loads(
                (ev_dir / "REGENERATION_CHECK.json").read_text())
            assert regen["regeneration_status"] == "NOT_REPRODUCIBLE", \
                regen
            obj = next(iter(regen["objects"].values()))
            assert obj["shipped_source_equals_canonical_builder"] == \
                "MISMATCH"
        finally:
            (model_dir / "PARAMETRIC_MODEL_SOURCE.py").write_text(
                original)


class TestProvenanceRecord:
    def test_cad_source_provenance_completeness(self, eng_pkg):
        result, work = eng_pkg
        pkg = result["package_out"]
        model_dir = Path(pkg["package_dir"]) / "MODEL"
        rec = json.loads(
            (model_dir / "CAD_SOURCE_PROVENANCE.json").read_text())
        cb = rec["canonical_builder"]
        assert cb["form"] == "dual_lumen_catheter"
        assert cb["builder_function"] == "build_dual_lumen_catheter"
        assert cb["builder_source_sha256"]
        assert cb["module_sha256"]
        assert rec["exported_source_sha256"]
        assert rec["parameter_hash"] == eg.parameter_map_hash(
            rec["parameter_map"])
        # derived artifact hashes are REAL (Art. VI: re-hash the bytes)
        derived = rec["derived_artifacts"]
        assert derived, "must list the derived STEP/STL/GLB"
        for entry in derived:
            f = Path(pkg["package_dir"]) / entry["path"]
            assert f.is_file(), entry["path"]
            h = eg.parameter_map_hash  # noqa: F841 — readability alias
            import hashlib
            assert entry["sha256"] == hashlib.sha256(
                f.read_bytes()).hexdigest()
        assert rec["regeneration_relationship"]["verification"] == \
            "MODEL/3D_EVIDENCE/REGENERATION_CHECK.json"
        # the manifest carries the canonical identity too
        manifest = json.loads(
            (model_dir / "MODEL_MANIFEST.json").read_text())
        assert manifest["canonical_builder"]["form"] == \
            "dual_lumen_catheter"
