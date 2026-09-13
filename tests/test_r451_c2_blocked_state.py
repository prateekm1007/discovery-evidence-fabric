"""R451-C2 — the blocked-state + geometry-to-visual join battery.

Operator directive R451-C2 (Visual State Integrity + Guaranteed
Geometry-to-Visual Join). This battery covers the BACKEND half of the
round; the frontend half is scripts/r451_c2_ui_tests.mjs (the
presentation-state mapping, the regression matrix, Attacks A–E) plus
the fresh-browser DOM proof recorded in the round record.

Covered here:

  1. C2.5 / Article XXV — the dossier evidence ledger carries a typed
     `retrieval_state`, and numeric counts exist ONLY when retrieval
     actually executed. "Never reached retrieval" and "measured zero"
     are different facts; the ledger makes them different fields.

  2. C2.9 — the Visual Compiler writes VISUAL_COMPILER_INVOCATION.json
     on EVERY exit (typed skips AND renders), with the directive's
     required fields, so "GLB exists" vs "GLB was passed to the
     renderer" is machine-distinguishable (BS-003/BS-030).

  3. C2.10 — the deterministic product watchdog: every integrity rule
     holds on a healthy fixture, and every tampered fixture fails for
     the SPECIFIC rule it violates (Art. XVI/XVII: adversarial
     demonstration, not happy-path proof).

  4. The projection fields the blocked-state UI renders are pinned at
     the source (auditor governance 7: frontend claims trace to backend
     truth) — the user-state projection, the dossier design tab's
     honest unavailability notes, and the typed render skip the
     GEOMETRY_READY_RENDER_BLOCKED surface reads.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import dossier as dossier_mod  # noqa: E402
from toscanini import user_state as user_state_mod  # noqa: E402
from discovery_fabric.engine.visual_compiler import render_worker  # noqa: E402
from discovery_fabric.engine.visual_compiler import visual_compiler  # noqa: E402

WATCHDOG = REPO / "scripts" / "r451_c2_watchdog.py"
sys.path.insert(0, str(REPO / "scripts"))
import r451_c2_watchdog as watchdog  # noqa: E402


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------
def _session(status="COMPLETE", run_dir=None, final_status=None,
             package=None) -> dict:
    return {
        "session_id": "ts_r451c2_test",
        "title": "hydropower turbine sediment erosion",
        "user_text": "hydropower turbine sediment erosion",
        "status": status,
        "final_status": final_status,
        "run_dir": str(run_dir) if run_dir else None,
        "package": package or {},
    }


# ---------------------------------------------------------------------------
# 1. the evidence ledger's typed retrieval state (C2.5)
# ---------------------------------------------------------------------------
class TestEvidenceRetrievalState:
    def test_blocked_run_never_reached_retrieval_no_counts(self, tmp_path):
        """A blocked terminal run with no run dir: retrieval_state is
        NOT_REACHED and NO numeric counts exist (the invented-zero fix)."""
        s = _session(status="RUN_BLOCKED_TRANSPORT")
        tab = dossier_mod.evidence_ledger(s)
        assert tab["retrieval_state"] == "NOT_REACHED"
        assert "retrieved_count" not in tab
        assert "used_count" not in tab

    def test_terminal_run_without_envelope_is_not_reached(self, tmp_path):
        s = _session(status="COMPLETE", run_dir=tmp_path)
        tab = dossier_mod.evidence_ledger(s)
        assert tab["retrieval_state"] == "NOT_REACHED"
        assert "retrieved_count" not in tab

    def test_running_run_is_pending(self, tmp_path):
        s = _session(status="RUNNING", run_dir=tmp_path)
        tab = dossier_mod.evidence_ledger(s)
        assert tab["retrieval_state"] == "PENDING"
        assert "retrieved_count" not in tab

    def test_recorded_retrieval_failure_is_failed_never_zero(self, tmp_path):
        """Art. XXI.3: provider failure is not absence — the manifest's
        failed RETRIEVE stage yields FAILED, never a numeric zero."""
        (tmp_path / "run_manifest.json").write_text(json.dumps(
            {"failed_stages": {"RETRIEVE": "TRANSPORT_TIMEOUT"}}))
        s = _session(status="COMPLETE", run_dir=tmp_path)
        tab = dossier_mod.evidence_ledger(s)
        assert tab["retrieval_state"] == "FAILED"
        assert "retrieved_count" not in tab
        assert "measured zero" not in tab["note"].lower().replace(
            "never a measured zero", "")

    def test_envelope_with_zero_records_is_a_measured_zero(self, tmp_path):
        """The one case a numeric zero is honest: the envelope exists —
        retrieval executed and measured zero records."""
        (tmp_path / "envelope_RETRIEVE.json").write_text(json.dumps(
            {"evidence": []}))
        s = _session(status="COMPLETE", run_dir=tmp_path)
        tab = dossier_mod.evidence_ledger(s)
        assert tab["retrieval_state"] == "RETRIEVED"
        assert tab["retrieved_count"] == 0
        assert tab["used_count"] == 0

    def test_envelope_with_records_carries_counts(self, tmp_path):
        (tmp_path / "envelope_RETRIEVE.json").write_text(json.dumps(
            {"evidence": [
                {"title": "sediment erosion in Pelton runners",
                 "source": "openalex", "content_hash": "a" * 64},
                {"title": "cavitation damage review",
                 "source": "crossref", "content_hash": "b" * 64},
            ]}))
        s = _session(status="COMPLETE", run_dir=tmp_path)
        tab = dossier_mod.evidence_ledger(s)
        assert tab["retrieval_state"] == "RETRIEVED"
        assert tab["retrieved_count"] == 2


# ---------------------------------------------------------------------------
# 2. the projection the blocked-state UI renders (source pinning)
# ---------------------------------------------------------------------------
class TestBlockedProjectionSource:
    def test_blocked_run_user_state_projection(self):
        """The user-state projection the frontend mapping consumes is
        the infrastructure state — never a scientific verdict."""
        view = user_state_mod.user_state_view(
            _session(status="RUN_BLOCKED_TRANSPORT"))
        assert view["user_state"] == "BLOCKED_TRANSPORT"
        assert view["found_something"] is False
        assert view["rejected"] is False
        assert "infrastructure" in view["label"].lower()
        assert "not a rejection" in view["meaning"].lower() or \
            "no conclusion was reached" in view["meaning"].lower()

    def test_the_epistemic_sentence_is_backend_truth(self):
        """Directive §8: 'this is an infrastructure state, never a
        scientific verdict' — the sentence the blocked hero renders is
        the backend's own semantics (the decision line carries it)."""
        view = user_state_mod.user_state_view(
            _session(status="RUN_BLOCKED_TRANSPORT"))
        blob = (view["label"] + " " + view["decision"] + " "
                + view["meaning"]).lower()
        assert "infrastructure" in blob
        assert "resume" in blob or "saved" in blob

    def test_engine_error_is_infrastructure_too(self):
        for status in ("INTERRUPTED", "ERROR_TRANSPORT", "ERROR_STUCK"):
            view = user_state_mod.user_state_view(_session(status=status))
            assert view["user_state"] in (
                "INTERRUPTED", "FAILED_TRANSPORT", "FAILED_ENGINE"), status


# ---------------------------------------------------------------------------
# 3. the invocation receipt on every compiler exit (C2.9)
# ---------------------------------------------------------------------------
def _chrome_available() -> bool:
    return bool(render_worker.find_node() and render_worker.find_chrome())


def _make_glb(path: Path) -> None:
    import trimesh
    path.parent.mkdir(parents=True, exist_ok=True)
    s = trimesh.Scene({
        "chassis_housing": trimesh.creation.box(extents=[70, 30, 40]),
        "drive_shaft": trimesh.creation.cylinder(
            radius=6, height=45, sections=32),
    })
    s.export(path, file_type="glb")


class TestInvocationReceipt:
    def test_skip_exit_writes_receipt_with_typed_reason(self, tmp_path,
                                                        monkeypatch):
        """The cheapest real skip: a renderer-less environment. The
        boundary was REACHED and did NOT render — the receipt says so
        with the typed reason (BS-003: built is not wired; the receipt
        is the wire proof either way)."""
        monkeypatch.setattr(render_worker, "find_node", lambda: None)
        monkeypatch.setattr(render_worker, "find_chrome", lambda: None)
        _make_glb(tmp_path / "MODEL" / "engineering_model.glb")
        rec = visual_compiler.compile_visuals(str(tmp_path))
        assert rec["status"].startswith("RENDER_SKIPPED")
        receipt = json.loads(
            (tmp_path / "MODEL" / "3D"
             / "VISUAL_COMPILER_INVOCATION.json").read_text())
        assert receipt["kind"] == "VISUAL_COMPILER_INVOCATION"
        assert receipt["run_id"] == tmp_path.name
        assert receipt["invocation_status"] == rec["status"]
        assert receipt["skip_reason"]
        assert receipt["glb_sha256"]
        assert receipt["render_record_reference"] is None
        assert receipt["visual_compiler_version"]
        assert receipt["schema_version"] == "1.1.0"
        assert receipt["output_directory"].endswith("MODEL/3D")

    def test_no_source_glb_exit_writes_receipt(self, tmp_path, monkeypatch):
        """A renderer present but no GLB: the boundary was reached,
        nothing was invoked, and the receipt records exactly that (no
        invented hashes). The no-renderer guard deliberately stays the
        cheapest first check — a renderer-less environment skips before
        source resolution, so this test stubs the renderer present."""
        monkeypatch.setattr(render_worker, "find_node",
                            lambda: "/usr/bin/true")
        monkeypatch.setattr(render_worker, "find_chrome",
                            lambda: "/usr/bin/true")
        # the dependency contract would also need stubbing; instead go
        # one layer deeper: the renderer path with a GLB present but a
        # scene that cannot solve is the RENDER_FAILED typed exit — for
        # the no-GLB receipt test, stub deps present too
        monkeypatch.setattr(render_worker, "renderer_deps_present",
                            lambda: None)
        # hermetic memory guard: THIS test exercises the no-source exit,
        # not the guard — a tight host must not reorder the exits
        # (BS-020: the environment is never the product)
        monkeypatch.setattr(render_worker, "memory_guard",
                            lambda *a, **k: None)
        rec = visual_compiler.compile_visuals(str(tmp_path))
        assert rec["status"] == "RENDER_SKIPPED_NO_SOURCE_GLB"
        receipt = json.loads(
            (tmp_path / "MODEL" / "3D"
             / "VISUAL_COMPILER_INVOCATION.json").read_text())
        assert receipt["invocation_status"] == "RENDER_SKIPPED_NO_SOURCE_GLB"
        assert receipt["glb_sha256"] is None
        assert receipt["skip_reason"]

    def test_receipt_fields_complete(self, tmp_path, monkeypatch):
        """Every directive-required field exists on every receipt."""
        monkeypatch.setattr(render_worker, "find_node", lambda: None)
        monkeypatch.setattr(render_worker, "find_chrome", lambda: None)
        visual_compiler.compile_visuals(str(tmp_path))
        receipt = json.loads(
            (tmp_path / "MODEL" / "3D"
             / "VISUAL_COMPILER_INVOCATION.json").read_text())
        for field in ("run_id", "generation_id", "glb_sha256",
                      "geometry_spec_sha256", "visual_compiler_version",
                      "invoked_at", "invocation_status", "skip_reason",
                      "render_record_reference", "output_directory",
                      "schema_version"):
            assert field in receipt, field

    @pytest.mark.skipif(not _chrome_available(),
                        reason="headless Chromium/Node pair unavailable")
    def test_render_exit_writes_receipt_and_watchdog_passes(self, tmp_path):
        """The full positive: a REAL render through the real renderer —
        the receipt says the renderer ran, and the watchdog's R1–R7 all
        hold on the produced directory."""
        _make_glb(tmp_path / "MODEL" / "engineering_model.glb")
        rec = visual_compiler.compile_visuals(str(tmp_path),
                                              is_conceptual=False)
        receipt = json.loads(
            (tmp_path / "MODEL" / "3D"
             / "VISUAL_COMPILER_INVOCATION.json").read_text())
        assert receipt["invocation_status"] == rec["status"]
        assert receipt["glb_sha256"]
        report = watchdog.run_watchdog(tmp_path)
        assert report["verdict"] == "PASS", report["violations"]


# ---------------------------------------------------------------------------
# 4. the deterministic watchdog (C2.10)
# ---------------------------------------------------------------------------
class TestWatchdog:
    def _healthy_fixture(self, tmp_path: Path, name: str = "ts_watchdog_ok") -> Path:
        """A synthetically healthy run dir: GLB (a VALID glTF 2.0
        container — R451-C2.4 §3 makes container validity a mandatory
        certification proof) + the recorded identity chain (R451-C2.3:
        the engineering authority reads recorded identity documents) +
        receipt (rendered, spec sha matching) + gate COMPLETE_PASS +
        the full ladder + render record with the true source hash +
        the hero.glb provenance hash. File-level fixture — the watchdog
        is a deterministic file-rule checker."""
        import hashlib
        import struct
        run = tmp_path / name
        m3d = run / "MODEL" / "3D"
        m3d.mkdir(parents=True)
        glb = run / "MODEL" / "engineering_model.glb"
        json_data = b'{"asset":{"version":"2.0"}}'
        json_data += b" " * ((4 - len(json_data) % 4) % 4)
        glb.write_bytes(
            struct.pack("<III", 0x46546C67, 2, 12 + 8 + len(json_data))
            + struct.pack("<I", len(json_data)) + b"JSON" + json_data)
        glb_sha = hashlib.sha256(glb.read_bytes()).hexdigest()
        spec = {"artifact": "GEOMETRY_SPEC", "parameters": []}
        spec["spec_sha256"] = hashlib.sha256(json.dumps(
            {k: v for k, v in spec.items() if k != "spec_sha256"},
            sort_keys=True).encode()).hexdigest()
        (run / "MODEL" / "GEOMETRY_SPEC.json").write_text(json.dumps(spec))
        spec_file_sha = hashlib.sha256(
            (run / "MODEL" / "GEOMETRY_SPEC.json").read_bytes()).hexdigest()
        identity = {
            "artifact": "ARTIFACT_IDENTITY", "run_id": run.name,
            "generation_id": "gen-1", "geometry_hash": glb_sha,
            "source_geometry_hash": spec["spec_sha256"],
            "glb_path": str(glb), "glb_disk_sha256": glb_sha,
            "glb_matches_geometry_hash": True,
            "visualizability_class": "ENGINEERING_3D"}
        (run / "MODEL"
         / "ARTIFACT_IDENTITY.json").write_text(json.dumps(identity))
        (run / "BRIDGE_REPORT.json").write_text(json.dumps({
            "outcome": "COMPLETED",
            "visualizability_class": "ENGINEERING_3D",
            "geometry": {"generation_id": "gen-1",
                         "visualizability_class": "ENGINEERING_3D",
                         "artifact_identity": identity}}))
        (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(json.dumps({
            "kind": "VISUAL_COMPILER_INVOCATION",
            "run_id": run.name, "generation_id": "gen-1",
            "glb_sha256": glb_sha,
            "geometry_spec_sha256": spec_file_sha,
            "visual_compiler_version": "VISUAL_COMPILER_HEADLESS_THREE",
            "invoked_at": "2026-09-12T00:00:00Z", "invocation_status": "SUCCEEDED",
            "render_record_reference": None,
            "skip_reason": None, "output_directory": str(m3d)}))
        (m3d / "visual_gate.json").write_text(json.dumps(
            {"verdict": "COMPLETE_PASS"}))
        rec = {"source_glb_sha256": glb_sha,
               "scene_spec": {"model": {"node_count": 1}}}
        (m3d / "render_record.json").write_text(json.dumps(rec))
        from discovery_fabric.engine.visual_compiler import visual_set
        required = visual_set.required_artifacts(
            1, visual_set.DEFAULT_TURNTABLE_FRAMES)["required"]
        for name in required:
            p = m3d / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b"artifact-" + name.encode().replace(b"/", b"_"))
        # R451-C2.3 §5 rung 7: the exported hero.glb's provenance hash
        # lives in the render record's own views block
        rec["views"] = {"hero.glb": {"sha256": hashlib.sha256(
            (m3d / "hero.glb").read_bytes()).hexdigest()}}
        (m3d / "render_record.json").write_text(json.dumps(rec))
        (run / "session.json").write_text(json.dumps({"status": "COMPLETE"}))
        return run

    def test_healthy_fixture_passes_every_rule(self, tmp_path):
        run = self._healthy_fixture(tmp_path)
        report = watchdog.run_watchdog(run)
        assert report["verdict"] == "PASS", report["violations"]
        rules = {c["rule"]: c["state"] for c in report["checks"]}
        assert rules["R1_engineering_glb_has_invocation_receipt"] == "PASS"
        assert rules["R2_rendered_has_gate"] == "PASS"
        assert rules["R3_complete_pass_has_full_ladder"] == "PASS"
        assert rules["R4_hero_source_matches_canonical_glb"] == "PASS"
        assert rules["R7_receipt_identity_matches_run"] == "PASS"

    def test_missing_receipt_fails_r1(self, tmp_path):
        run = self._healthy_fixture(tmp_path)
        (run / "MODEL" / "3D"
         / "VISUAL_COMPILER_INVOCATION.json").unlink()
        report = watchdog.run_watchdog(run)
        assert report["verdict"] == "FAIL"
        assert any(v["rule"] == "R1_engineering_glb_has_invocation_receipt"
                   for v in report["violations"])

    def test_swapped_hero_source_fails_r4(self, tmp_path):
        """The R443 wrong-source class, now a watchdog rule: a hero whose
        recorded source hash does not match the canonical GLB."""
        run = self._healthy_fixture(tmp_path)
        m3d = run / "MODEL" / "3D"
        rec = json.loads((m3d / "render_record.json").read_text())
        rec["source_glb_sha256"] = "d" * 64  # not the canonical GLB
        (m3d / "render_record.json").write_text(json.dumps(rec))
        report = watchdog.run_watchdog(run)
        assert report["verdict"] == "FAIL"
        assert any(v["rule"] == "R4_hero_source_matches_canonical_glb"
                   for v in report["violations"])

    def test_skip_without_reason_fails_r5(self, tmp_path):
        run = self._healthy_fixture(tmp_path)
        m3d = run / "MODEL" / "3D"
        receipt = json.loads(
            (m3d / "VISUAL_COMPILER_INVOCATION.json").read_text())
        receipt["invocation_status"] = "RENDER_SKIPPED_LOW_MEMORY"
        receipt["skip_reason"] = None
        (m3d / "VISUAL_COMPILER_INVOCATION.json").write_text(
            json.dumps(receipt))
        report = watchdog.run_watchdog(run)
        assert report["verdict"] == "FAIL"
        assert any(v["rule"] == "R5_skip_carries_typed_reason"
                   for v in report["violations"])

    def test_gate_pass_with_missing_ladder_fails_r3(self, tmp_path):
        run = self._healthy_fixture(tmp_path)
        (run / "MODEL" / "3D" / "hero.png").unlink()
        report = watchdog.run_watchdog(run)
        assert report["verdict"] == "FAIL"
        assert any(v["rule"] == "R3_complete_pass_has_full_ladder"
                   for v in report["violations"])

    def test_blocked_run_without_glb_is_not_applicable_not_fail(
            self, tmp_path):
        """A blocked run has no GLB and no receipt: every GLB-dependent
        rule is NOT_APPLICABLE (the antecedent is false) — the watchdog
        never manufactures a violation from an infrastructure stop
        (Art. LXI)."""
        run = tmp_path / "ts_blocked"
        run.mkdir()
        (run / "session.json").write_text(json.dumps(
            {"status": "RUN_BLOCKED_TRANSPORT"}))
        report = watchdog.run_watchdog(run)
        assert report["verdict"] == "PASS"
        for c in report["checks"]:
            if c["rule"] == "R6_no_glb_blocked_run_projects_upstream_state":
                assert c["state"] == "PASS"

    def test_cli_exit_codes(self, tmp_path):
        import subprocess
        run = self._healthy_fixture(tmp_path)
        ok = subprocess.run([sys.executable, str(WATCHDOG), str(run)],
                            capture_output=True, text=True)
        assert ok.returncode == 0
        bad = self._healthy_fixture(tmp_path, name="ts_watchdog_bad")
        (bad / "MODEL" / "3D"
         / "VISUAL_COMPILER_INVOCATION.json").unlink()
        failing = subprocess.run([sys.executable, str(WATCHDOG), str(bad)],
                                 capture_output=True, text=True)
        assert failing.returncode == 1
