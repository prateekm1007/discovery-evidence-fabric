"""tests/test_r423_async_render_gate.py — R423A Phase 2 + Phase 3.

Phase 2 — the bridge gate NEVER blocks on premium rendering:
  * DISCOVERY COMPLETE != PRESENTATION RENDER COMPLETE: the gate's
    record carries the render REQUEST (RENDER_REQUESTED), the async
    job owns execution, and no Blender subprocess is ever launched
    from inside the gate.
  * Fresh-run proof shape: terminal state is reachable with renders
    absent; the async job (stubbed here to the typed skip path) then
    records its own state — the run record is never mutated by render
    outcomes.
  * Adversarial: a poisoned BLENDER_PATH that would "succeed instantly"
    if launched inline MUST NOT be launched — the gate's timing and
    record prove non-execution.

Phase 3 — ONE canonical technology transfer package:
  * the bridge writes TECHNOLOGY_TRANSFER_PACKAGE_*.zip
  * the package carries the 13 content items (problem, evidence,
    mechanism/invention, causal difference, engineering definition
    + build path, technical evaluation, 3D artifacts, uncertainty,
    decisive experiment, provenance, maturity)
  * historical TECHNOLOGY_PACKAGE_*.zip names still resolve
  * the CIO projects ONE package concept (no counsel_package field)

Constitutional pins:
  Art. X  — the files on disk are the authority.
  Art. IV — the one package's maturity label stays honest; buyer
            release gates untouched.
  Art. XI — historical artifacts are never rewritten.
  Art. LXI — a render failure/skip is never a run failure.
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toscanini import bridge_gate  # noqa: E402
from toscanini import cio as cio_mod  # noqa: E402
from toscanini import sessions as store  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "r418"


def _solar_detail() -> dict:
    return json.loads((FIXTURES / "solar_result.json").read_text())


class _FakeArtifactWorker:
    """Records enqueue calls; never spawns anything."""

    def __init__(self):
        self.calls = []
        self.enqueue_result = {
            "artifact": "RENDER_JOB", "session_id": "ts_r423_test",
            "status": "RUNNING", "enqueued_at": "2026-09-08T00:00:00Z",
            "worker_pid": 424242, "worker_starttime": "1",
        }

    def enqueue(self, session_id, enqueued_by="api"):
        self.calls.append((session_id, enqueued_by))
        return dict(self.enqueue_result)


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    detail = _solar_detail()
    for name in ("INVENTION_SPECIFICATION.json", "final_state.json",
                 "ENGINEERING_SPECIFICATION.json",
                 "DECISIVE_EXPERIMENT.json"):
        if detail.get(name.replace(".json", "")):
            (run_dir / name).write_text(
                json.dumps(detail[name.replace(".json", "")]))
    session = {
        "session_id": "ts_r423_test",
        "status": "COMPLETE",
        "run_dir": str(run_dir),
        "user_text": "make a solar panel which is the most efficient "
                     "in the world",
        "final_status": "EVOLVED_INVENTION_CANDIDATE",
    }
    monkeypatch.setattr(store, "get_session", lambda sid: dict(session))
    monkeypatch.setattr(store, "update_session",
                        lambda sid, **f: dict(session))
    monkeypatch.setattr(store, "session_detail",
                        lambda sid: _solar_detail())
    fake = _FakeArtifactWorker()
    import toscanini.artifact_worker as aw
    monkeypatch.setattr(aw, "enqueue", fake.enqueue)
    # adversarial canary: if the gate EVER launches a subprocess this
    # binary would answer --version instantly and succeed inline
    canary = tmp_path / "canary_blender"
    canary.write_text("#!/bin/sh\necho 'Blender 5.2.1 LTS'\n")
    canary.chmod(0o755)
    monkeypatch.setenv("BLENDER_PATH", str(canary))
    return {"run_dir": run_dir, "session": session, "fake": fake,
            "tmp_path": tmp_path}


class TestPhase2AsyncRenderGate:
    def test_gate_completes_with_render_requested_not_executed(self,
                                                               isolated):
        """Case B: the gate finishes fast, the record says
        RENDER_REQUESTED with the job identity, and no Blender ran."""
        t0 = time.perf_counter()
        gate = bridge_gate.ensure_artifacts("ts_r423_test")
        wall = time.perf_counter() - t0
        rd = isolated["run_dir"]
        report = json.loads((rd / "BRIDGE_REPORT.json").read_text())

        assert gate["outcome"] == "COMPLETED"
        assert report["renders"]["status"] == "RENDER_REQUESTED"
        assert report["renders"]["job"]["worker_pid"] == 424242
        assert isolated["fake"].calls == [
            ("ts_r423_test", "bridge_gate")]
        # DISCOVERY COMPLETE != RENDER COMPLETE — the artifacts are NOT
        # on disk yet, and the gate did not fail because of that
        assert not (rd / "MODEL" / "3D" / "hero.png").exists()
        # the gate never blocked on premium rendering (the canary
        # blender would have taken real time; the gate is sub-second
        # over conceptual geometry + package assembly)
        assert wall < 60, f"gate took {wall:.1f}s — rendering inline?"

    def test_no_blender_subprocess_from_the_gate(self, isolated,
                                                 monkeypatch):
        """Adversarial: ANY Blender launch during the gate is a
        violation (the canary blender answers --version instantly and
        would prove inline execution). Non-render subprocesses are
        allowed ONLY for provenance resolution (the engine-identity
        git fallback in local runs; the hosted engine reads the baked
        artifact json with no subprocess at all)."""
        launched = []
        orig_popen = subprocess.Popen
        orig_run = subprocess.run

        def spy_popen(*a, **kw):
            launched.append(list(a[0])[:3])
            return orig_popen(*a, **kw)

        def spy_run(*a, **kw):
            launched.append(list(a[0])[:3])
            return orig_run(*a, **kw)

        monkeypatch.setattr(subprocess, "Popen", spy_popen)
        monkeypatch.setattr(subprocess, "run", spy_run)
        bridge_gate.ensure_artifacts("ts_r423_test")
        blender_launches = [
            c for c in launched
            if any("blender" in str(x).lower() for x in c)
            or "--version" in c or "--background" in c
            or "--factory-startup" in c]
        assert not blender_launches, \
            f"Blender launched by the gate: {blender_launches}"
        # everything the gate DID launch must be provenance-only
        for c in launched:
            assert "git" in c or "python" in str(c[0]).lower(), \
                f"unexpected subprocess from the gate: {c}"

    def test_render_state_visible_before_and_after(self, isolated):
        """The CIO surfaces the async job's state (RENDERING while the
        job is RUNNING) — presentation-only, never a maturity field."""
        rd = isolated["run_dir"]
        bridge_gate.ensure_artifacts("ts_r423_test")
        # simulate the async job's RUNNING record
        d3 = rd / "MODEL" / "3D"
        d3.mkdir(parents=True, exist_ok=True)
        (d3 / "RENDER_JOB.json").write_text(json.dumps({
            "artifact": "RENDER_JOB", "status": "RUNNING",
            "worker_pid": 424242}))
        cio = cio_mod.build_cio(isolated["session"])
        renders = (cio.get("visualization") or {}).get("renders") or {}
        assert renders.get("status") in ("RENDERING", "RUNNING")
        assert (cio.get("maturity") or {}).get(
            "experimentally_verified") is not True  # presentation-only

    def test_idempotent_gate_does_not_re_request(self, isolated):
        bridge_gate.ensure_artifacts("ts_r423_test")
        bridge_gate.ensure_artifacts("ts_r423_test")
        assert len(isolated["fake"].calls) == 1  # resume-safe


class TestPhase3OnePackage:
    def test_canonical_zip_name(self, isolated):
        bridge_gate.ensure_artifacts("ts_r423_test")
        rd = isolated["run_dir"]
        zips = list(rd.glob("TECHNOLOGY_TRANSFER_PACKAGE_*.zip"))
        assert zips, "the one canonical artifact must exist"
        assert not list(rd.glob("TECHNOLOGY_PACKAGE_*.zip")), \
            "new runs must not write the historical name"

    def test_package_carries_the_thirteen_content_items(self, isolated):
        bridge_gate.ensure_artifacts("ts_r423_test")
        rd = isolated["run_dir"]
        pkg_dir = rd / "TECHNOLOGY_PACKAGE"
        assert (pkg_dir / "00_PACKAGE_README.pdf").is_file()
        assert (pkg_dir / "01_EXECUTIVE_TECHNOLOGY_BRIEF.pdf").is_file()
        assert (pkg_dir /
                "02_ENGINEERING_TECHNOLOGY_TRANSFER_DOSSIER.pdf").is_file()
        assert (pkg_dir / "03_BUYER_DECISION_CARD.pdf").is_file()
        assert (pkg_dir / "04_EVIDENCE_SUMMARY.pdf").is_file()
        assert (pkg_dir / "05_TRANSFER_MANIFEST.pdf").is_file()
        # 02 carries the build path (Phase 3 content item)
        eng = json.loads(
            (pkg_dir / "02_ENGINEERING_DEFINITION.json").read_text())
        assert "build_path" in eng
        assert eng["build_path"]["geometry_sources"]
        assert (pkg_dir / "03_EVIDENCE_SUMMARY.json").is_file()
        assert (pkg_dir / "04_DECISIVE_EXPERIMENT.json").is_file()
        # R423A: the technical evaluation section exists and is honest
        ev = json.loads(
            (pkg_dir / "05_TECHNICAL_EVALUATION.json").read_text())
        assert ev["physical_validation"]["status"] == "NOT_PERFORMED"
        assert ev["package_maturity"]
        assert ev["reviewer_provenance"] == "AI_REVIEW"
        assert (pkg_dir / "PROVENANCE.json").is_file()
        assert (pkg_dir / "PACKAGE_MANIFEST.json").is_file()
        # 3D artifacts where earned (conceptual run -> GLB, honestly
        # labeled, no engineering disclaimers violated)
        assert list((pkg_dir / "MODEL").glob("*.glb"))
        disclaimers = list((pkg_dir / "MODEL").glob(
            "CONCEPTUAL_3D_DISCLAIMER.json"))
        assert disclaimers  # conceptual class is labeled, never faked

    def test_cio_projects_one_package_concept(self, isolated):
        bridge_gate.ensure_artifacts("ts_r423_test")
        cio = cio_mod.build_cio(isolated["session"])
        dl = cio["downloads"]
        assert "counsel_package" not in dl
        assert dl["package_kind"] == "TECHNOLOGY_TRANSFER_PACKAGE"
        assert dl["package_origin"] == "INVENTION_BRIDGE"
        assert dl["package_zip"] == \
            "/api/sessions/ts_r423_test/package"
        assert dl["package_maturity"] == "EARLY_TECHNICAL_EVALUATION"

    def test_historical_zip_name_still_resolves(self, isolated):
        """Art. XI — a run whose package predates R423A keeps its old
        name and still serves."""
        rd = isolated["run_dir"]
        bridge_gate.ensure_artifacts("ts_r423_test")
        # rename to the historical convention (simulate an old run)
        zips = list(rd.glob("TECHNOLOGY_TRANSFER_PACKAGE_*.zip"))
        old = zips[0].rename(
            zips[0].with_name(zips[0].name.replace(
                "TECHNOLOGY_TRANSFER_PACKAGE_", "TECHNOLOGY_PACKAGE_")))
        info = cio_mod._bridge_package_info(rd)
        assert info is not None
        assert info["zip_name"] == old.name
        assert info["package_kind"] == "TECHNOLOGY_TRANSFER_PACKAGE"
        assert info["package_origin"] == "INVENTION_BRIDGE"

    def test_gate_report_names_the_one_package(self, isolated):
        gate = bridge_gate.ensure_artifacts("ts_r423_test")
        assert gate["package_out"]["package_kind"].startswith(
            "TECHNOLOGY_TRANSFER_PACKAGE")
