"""tests/test_r425_package_quality_audit.py — R425 §8/§9 regression.

THE INDEPENDENT AUDITOR:
  * imports no factory module (the factory cannot grade itself);
  * verifies the actual generated package bytes (hashes re-computed);
  * distinguishes STRUCTURAL PARITY from SEMANTIC PARITY against the
    released elite portfolio P-07 content benchmark — and never claims
    semantic parity merely because the file list matches;
  * catches tampered bytes (adversarial: the control is attacked).
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.invention_bridge.bridge import (
    bridge as run_bridge)  # test-side package builder only

AUDITOR = REPO / "scripts" / "r425_package_quality_audit.py"
BENCHMARK = REPO / "tests" / "fixtures" / "r425" / "p07_benchmark.json"


def _load_auditor():
    spec = importlib.util.spec_from_file_location(
        "r425_package_quality_audit", AUDITOR)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _eng_run() -> dict:
    return {
        "session_id": "ts_r425_aud",
        "user_text": "keep minimum drainage when primary lumen "
                     "obstructs",
        "final_state": {"final_status": "EVOLVED_INVENTION_CANDIDATE",
                        "causal_chain": {"intervention_site":
                                         "catheter"}},
        "invention_specification": {
            "causal_chain": {"value": {
                "intervention_site": "dual lumen catheter"}},
            "problem": {"value": {"device": "dual lumen catheter"}}},
        "engineering_specification": {
            "parameters": [
                {"param_id": "outer_diameter_mm", "value": 3.4,
                 "unit": "mm", "envelope": [2.5, 3.5],
                 "value_class": "MODELLED"},
                {"param_id": "primary_lumen_diameter_mm", "value": 1.3,
                 "unit": "mm", "envelope": [0.8, 1.4],
                 "value_class": "MODELLED"},
                {"param_id": "floor_lumen_diameter_mm", "value": 0.7,
                 "unit": "mm", "envelope": [0.4, 0.8],
                 "value_class": "MODELLED"},
                {"param_id": "floor_offset_mm", "value": 1.1,
                 "unit": "mm", "envelope": [0.7, 1.3],
                 "value_class": "MODELLED"},
                {"param_id": "length_mm", "value": 77.0,
                 "unit": "mm", "envelope": [60, 140],
                 "value_class": "MODELLED"}],
            "design_inputs": [
                {"id": f"DI-{i:03d}", "input": f"input {i}",
                 "value": f"v{i}", "evidence_class": "MODELLED",
                 "evidence_refs": ["core"]} for i in range(1, 7)],
            "design_outputs": [
                {"id": f"DO-{i:03d}", "parent_ids": [f"DI-{i:03d}"],
                 "description": f"output {i}",
                 "status": "CONCEPTUAL", "missing_inputs": []}
                for i in range(1, 4)],
            "failure_analysis": [
                {"graph_id": f"FM-{i:03d}",
                 "failure_mode": f"mode {i}",
                 "severity": f"UNKNOWN (basis {i})",
                 "verification": f"VF-{i:03d}"}
                for i in range(1, 5)],
            "verification_matrix": [
                {"id": f"VF-{i:03d}", "requirement": f"req {i}",
                 "method": f"method {i}", "result": "NOT_TESTED",
                 "acceptance": f"rule {i}",
                 "invention_tie": {"linkage_kind": "domain_check",
                                   "targets": [f"FM-{i:03d}"]}}
                for i in range(1, 5)],
            "engineering_build_plan": [
                {"work_package": f"WP-{i:02d}",
                 "test_article": f"article {i}",
                 "design_work": f"design {i}",
                 "equipment": f"equipment {i}"}
                for i in range(1, 6)],
            "engineering_core": {"remaining_unknowns": [
                {"unknown": "value of critical parameter floor lumen "
                            "roughness [UNKNOWN]",
                 "reason": "no sourced value exists (value_status "
                           "UNKNOWN); required before any numeric "
                           "design decision"}]},
            "system_architecture": {"subsystems": []}},
        "run_state": {"generations": {"generations": []}},
        "evidence_pack": {"retrieval": []}}


@pytest.fixture(scope="module")
def eng_pkg(tmp_path_factory):
    work = tmp_path_factory.mktemp("aud")
    result = run_bridge(_eng_run(), None, str(work),
                        build_renders=False)
    return result["package_out"]


@pytest.fixture(scope="module")
def auditor():
    return _load_auditor()


class TestIndependence:
    def test_auditor_imports_no_factory_module(self):
        """R425 §8's core clause: the audit path is NOT the same
        factory functions that produced the package. The check scans
        the auditor's actual IMPORT STATEMENTS (not prose — the
        docstring honestly names what it does not import)."""
        import ast
        tree = ast.parse(AUDITOR.read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith(
                        ("discovery_fabric", "toscanini")), \
                        f"auditor imports the factory: {alias.name}"
            elif isinstance(node, ast.ImportFrom):
                assert not (node.module or "").startswith(
                    ("discovery_fabric", "toscanini")), \
                    f"auditor imports the factory: {node.module}"

    def test_auditor_reads_bytes_only(self, auditor, eng_pkg):
        audit = auditor.Auditor(
            Path(eng_pkg["zip_path"]), None, None).run()
        assert audit["independence"]
        assert audit["schema"] == "R425_PACKAGE_QUALITY_AUDIT/2.0"


class TestTwelveDimensions:
    def test_all_pass_on_engineering_package(self, auditor, eng_pkg):
        audit = auditor.Auditor(
            Path(eng_pkg["zip_path"]), None,
            json.loads(BENCHMARK.read_text())).run()
        assert audit["overall"]["verdict"] == "PASS"
        assert audit["overall"]["all_twelve_pass"] is True
        assert len(audit["checks"]) == 12

    def test_regeneration_executes_shipped_source(self, auditor,
                                                  eng_pkg):
        audit = auditor.Auditor(
            Path(eng_pkg["zip_path"]), None, None).run()
        regen = audit["checks"][
            "canonical_source_regeneration_equivalence"]
        result = regen["independent_regeneration"]
        assert result["ok"] is True, regen
        assert result["volume_matches_record"] is True

    def test_manifest_hashes_reverified(self, auditor, eng_pkg):
        audit = auditor.Auditor(
            Path(eng_pkg["zip_path"]), None, None).run()
        prov = audit["checks"]["provenance_integrity"]
        assert prov["hashes_verified_against_bytes"] == \
            prov["manifest_entries"]


class TestAdversarial:
    def test_tampered_bytes_fail_the_audit(self, auditor, eng_pkg,
                                           tmp_path):
        """Art. XVII: attack the control. Flip one byte inside a
        manifest-listed file — the audit must FAIL (the factory's own
        manifest no longer describes the bytes)."""
        src = Path(eng_pkg["zip_path"])
        tampered = tmp_path / "tampered.zip"
        with zipfile.ZipFile(src) as zin, \
                zipfile.ZipFile(tampered, "w",
                                zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith(
                        "UNKNOWN_ROADMAP.json"):
                    doc = json.loads(data)
                    if doc.get("unknowns"):
                        # a value change the manifest hash will catch
                        doc["unknowns"][0]["priority"] = \
                            "TAMPERED_PRIORITY"
                    data = json.dumps(doc).encode()
                zout.writestr(item, data)
        audit = auditor.Auditor(tampered, None, None).run()
        assert audit["overall"]["verdict"] == "FAIL"
        assert audit["checks"]["provenance_integrity"]["verdict"] == \
            "FAIL"

    def test_hollow_package_fails_not_silently_passes(self, auditor,
                                                      tmp_path):
        hollow = tmp_path / "hollow.zip"
        with zipfile.ZipFile(hollow, "w") as zf:
            zf.writestr("TECHNOLOGY_PACKAGE/README.txt", "empty")
        audit = auditor.Auditor(hollow, None, None).run()
        assert audit["overall"]["verdict"] == "FAIL"

    def test_filler_prose_fails_experiment_check(self, auditor,
                                                 eng_pkg, tmp_path):
        src = Path(eng_pkg["zip_path"])
        poisoned = tmp_path / "filler.zip"
        with zipfile.ZipFile(src) as zin, \
                zipfile.ZipFile(poisoned, "w",
                                zipfile.ZIP_DEFLATED) as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith(
                        "04_DECISIVE_EXPERIMENT.json"):
                    doc = json.loads(data)
                    doc["contract"]["baseline_control"] = {
                        "value": "further testing required",
                        "status": "DEFINED",
                        "provenance_basis": "generic filler"}
                    data = json.dumps(doc).encode()
                zout.writestr(item, data)
        audit = auditor.Auditor(poisoned, None, None).run()
        assert audit["checks"]["decisive_experiment_completeness"][
            "verdict"] == "FAIL"


class TestBenchmarkComparison:
    def test_structural_vs_semantic_distinguished(self, auditor,
                                                  eng_pkg):
        audit = auditor.Auditor(
            Path(eng_pkg["zip_path"]), None,
            json.loads(BENCHMARK.read_text())).run()
        bc = audit["benchmark_comparison"]
        assert bc["status"] == "COMPARED"
        for dim in bc["dimensions"]:
            assert "structural_parity" in dim
            assert "semantic_parity" in dim
            assert dim["semantic_parity"] in (
                "PARITY", "PARTIAL", "GAP")
            assert "semantic_ratio" in dim
        assert bc["rule"]

    def test_semantic_parity_never_from_file_list_alone(self, auditor,
                                                        tmp_path):
        """A package whose FILE LIST matches but whose CONTENT is
        hollow must NOT get semantic parity — the §9 rule."""
        hollow = tmp_path / "files_only.zip"
        with zipfile.ZipFile(hollow, "w") as zf:
            root = "TECHNOLOGY_PACKAGE/"
            for d in ("00_PACKAGE_README.pdf",
                      "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf",
                      "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf",
                      "03_BUYER_DECISION_CARD.pdf",
                      "04_EVIDENCE_SUMMARY.pdf",
                      "05_TRANSFER_MANIFEST.pdf"):
                zf.writestr(root + d, b"%PDF-1.4 hollow")
            zf.writestr(root + "02_ENGINEERING_DEFINITION.json",
                        json.dumps({"design_inputs": []}))
            zf.writestr(
                root + "ENGINEERING_TRACEABILITY.json",
                json.dumps({"links": [], "coverage": {}}))
            zf.writestr(root + "UNKNOWN_ROADMAP.json",
                        json.dumps({"unknowns": []}))
        audit = auditor.Auditor(
            hollow, None, json.loads(BENCHMARK.read_text())).run()
        assert audit["overall"]["verdict"] == "FAIL"
        bc = audit["benchmark_comparison"]
        semantic = [d["semantic_parity"]
                    for d in bc["dimensions"]]
        assert "GAP" in semantic or "PARTIAL" in semantic
        assert bc["semantic_parity_verdict"] != "SEMANTIC_PARITY"

    def test_benchmark_provenance_recorded(self, auditor, eng_pkg):
        audit = auditor.Auditor(
            Path(eng_pkg["zip_path"]), None,
            json.loads(BENCHMARK.read_text())).run()
        prov = audit["benchmark_comparison"]["benchmark_provenance"]
        assert prov["portfolio_commit"]
        assert prov["extractor"]


class TestCLI:
    def test_cli_pass_returns_zero(self, eng_pkg, tmp_path):
        out = tmp_path / "audit.json"
        proc = subprocess.run(
            [sys.executable, str(AUDITOR), eng_pkg["zip_path"],
             "--benchmark", str(BENCHMARK), "--out", str(out)],
            capture_output=True, text=True, timeout=600)
        assert proc.returncode == 0, proc.stdout + proc.stderr
        assert json.loads(out.read_text())["overall"][
            "verdict"] == "PASS"

    def test_cli_missing_package_returns_two(self, tmp_path):
        proc = subprocess.run(
            [sys.executable, str(AUDITOR),
             str(tmp_path / "nonexistent.zip")],
            capture_output=True, text=True, timeout=60)
        assert proc.returncode == 2
