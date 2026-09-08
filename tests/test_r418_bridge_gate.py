"""tests/test_r418_bridge_gate.py — the automatic artifact contract.

R418 (operator P0 product correction): every completed run with an
invention gets its visual artifact + technology package AUTOMATICALLY
through the production worker path (toscanini/bridge_gate.py). The
three legitimate cases:

  Case A — artifact already exists -> projections render it
  Case B — invention exists, artifact missing -> generated (conceptual
           classes via the invention bridge, honest labels)
  Case C — not visualizable -> conceptual fallback (explicit labels)

Plus: idempotency (resume-safe), no-invention honesty, the CIO/run_state
projections, and the language guard on the shipped report.

Constitutional pins:
  Art. XXVIII — a conceptual model never presents as engineering
  geometry (class + authority fields).
  Art. IV — the bridge package is a distinct artifact class
  (package_kind), never a buyer release.
  Art. X — BRIDGE_REPORT.json + the files on disk are the authority.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toscanini import bridge_gate  # noqa: E402
from toscanini import cio as cio_mod  # noqa: E402
from toscanini import run_state as rs  # noqa: E402
from toscanini import sessions as store  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "r418"


def _solar_detail() -> dict:
    return json.loads((FIXTURES / "solar_result.json").read_text())


@pytest.fixture()
def isolated(tmp_path, monkeypatch):
    """A session + run_dir isolated from the real store; session_detail
    returns the REAL captured solar run detail (the same fixture the
    bridge was proven against end-to-end). The run_dir carries the
    invention-side artifacts the engine would have written (so the CIO
    projection finds invention state, exactly like production)."""
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
        "session_id": "ts_r418_test",
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
    return {"run_dir": run_dir, "session": session}


class TestCaseB:
    def test_solar_run_gets_conceptual_artifacts(self, isolated):
        gate = bridge_gate.ensure_artifacts("ts_r418_test")
        rd = isolated["run_dir"]
        assert gate["outcome"] == "COMPLETED", gate
        assert gate["case"] == "B"
        assert gate["conceptual"] is True
        assert gate["visualizability_class"] in (
            "SYSTEM_3D", "CONCEPTUAL_3D", "PROCESS_3D")
        # per-generation models at the canonical route names
        assert (rd / "MODEL" / "model-001.glb").exists()
        assert (rd / "MODEL" / "model-002.glb").exists()
        # the report is the authority
        report = json.loads((rd / "BRIDGE_REPORT.json").read_text())
        assert report["outcome"] == "COMPLETED"
        assert report["reviewer_provenance"] == "AI_REVIEW"
        # R423A Phase 3: the ONE canonical package zip exists and is
        # recorded (new runs carry the TECHNOLOGY_TRANSFER_PACKAGE name)
        zips = list(rd.glob("TECHNOLOGY_TRANSFER_PACKAGE_*.zip")) \
            + list(rd.glob("TECHNOLOGY_PACKAGE_*.zip"))
        assert zips, "bridge package zip missing"
        assert report["package_out"]["zip_name"] == zips[0].name
        assert report["package_out"]["zip_sha256"]
        # honest maturity label
        assert report["package_out"]["package_maturity"]

    def test_cio_projection_carries_conceptual_class(self, isolated):
        bridge_gate.ensure_artifacts("ts_r418_test")
        session = dict(isolated["session"])
        cio_obj = cio_mod.build_cio(session)
        assert cio_obj is not None
        geo = cio_obj["geometry"]
        assert geo["present"] is True
        assert geo["class"] in ("SYSTEM_3D", "CONCEPTUAL_3D", "PROCESS_3D")
        assert geo["conceptual"] is True
        assert geo["glb"], "CIO must serve the model route"
        # Art. XXVIII: the authority note says CONCEPTUAL, not engineering
        assert "CONCEPTUAL" in geo["authority"]
        assert "NOT engineering geometry" in geo["authority"]
        dl = cio_obj["downloads"]
        assert dl["package_zip"], "package route missing"
        assert dl["package_kind"] == "TECHNOLOGY_TRANSFER_PACKAGE"
        assert dl["package_origin"] == "INVENTION_BRIDGE"
        assert dl["package_maturity"]

    def test_run_state_package_and_generations(self, isolated):
        bridge_gate.ensure_artifacts("ts_r418_test")
        session = dict(isolated["session"])
        state = rs.canonical_run_state(session)
        pkg = state["package_state"]
        assert pkg["state"] == "READY"
        assert pkg["package_kind"] == "TECHNOLOGY_TRANSFER_PACKAGE"
        assert pkg["package_origin"] == "INVENTION_BRIDGE"
        assert pkg["zip_name"]
        rd = isolated["run_dir"]
        assert rs._gen_model_available(rd, 1) is True
        assert rs._gen_model_available(rd, 2) is True


class TestCaseA:
    def test_already_complete_skips(self, isolated, monkeypatch):
        rd = isolated["run_dir"]
        model = rd / "MODEL"
        model.mkdir()
        (model / "model-001.glb").write_bytes(b"fakeglb-not-a-real-model")
        dl = rd / "DOWNLOAD"
        dl.mkdir()
        (dl / "buyer.zip").write_bytes(b"zip")
        (rd / "PACKAGE_REPORT.json").write_text(
            json.dumps({"complete": True, "maturity": "ENGINEERING"}))
        gate = bridge_gate.ensure_artifacts("ts_r418_test")
        assert gate["outcome"] == "ALREADY_COMPLETE"
        assert gate["case"] == "A"
        # no bridge artifacts added
        assert not list(rd.glob("TECHNOLOGY_PACKAGE_*.zip"))

    def test_geometry_present_package_missing_builds_package(
            self, isolated):
        rd = isolated["run_dir"]
        model = rd / "MODEL"
        model.mkdir()
        (model / "model-001.glb").write_bytes(b"fakeglb")
        gate = bridge_gate.ensure_artifacts("ts_r418_test")
        assert gate["outcome"] == "PACKAGE_ADDED_TO_EXISTING_GEOMETRY"
        assert gate["case"] == "A+package"
        assert list(rd.glob(
            "TECHNOLOGY_TRANSFER_PACKAGE_*.zip")) \
            or list(rd.glob("TECHNOLOGY_PACKAGE_*.zip"))


class TestCaseC:
    def test_algorithmic_invention_gets_conceptual_fallback(
            self, isolated, monkeypatch):
        detail = {
            "session_id": "ts_r418_test",
            "user_text": "predict equipment failures from telemetry",
            "final_state": {
                "final_status": "INVENTION_UNDER_DEVELOPMENT",
                "causal_chain": {
                    "mechanism": "a statistical ensemble algorithm "
                                 "forecasts equipment failure from "
                                 "telemetry streams",
                },
            },
            "invention_specification": {
                "mechanism": {"value": "ensemble forecasting algorithm"},
            },
            "engineering_specification": {},
            "run_state": {},
        }
        monkeypatch.setattr(store, "session_detail", lambda sid: detail)
        gate = bridge_gate.ensure_artifacts("ts_r418_test")
        rd = isolated["run_dir"]
        assert gate["outcome"] == "CONCEPTUAL_FALLBACK"
        assert gate["case"] == "C"
        assert gate["fallback_class"] == "CONCEPTUAL_3D"
        assert (rd / "MODEL" / "model-001.glb").exists()
        report = json.loads((rd / "BRIDGE_REPORT.json").read_text())
        assert "NOT_VISUALIZABLE" in json.dumps(
            report.get("classification") or {})
        assert "engineering CAD remains unearned" in gate["fallback_basis"]


class TestHonesty:
    def test_no_invention_no_artifacts(self, isolated, monkeypatch):
        monkeypatch.setattr(store, "session_detail",
                            lambda sid: {"session_id": sid,
                                         "run_state": {}})
        monkeypatch.setattr(cio_mod, "build_cio", lambda s: None)
        gate = bridge_gate.ensure_artifacts("ts_r418_test")
        assert gate["outcome"] == "NO_INVENTION"
        rd = isolated["run_dir"]
        assert not (rd / "MODEL").exists()
        assert not list(rd.glob("TECHNOLOGY_PACKAGE_*.zip"))

    def test_idempotent_resume_safe(self, isolated):
        first = bridge_gate.ensure_artifacts("ts_r418_test")
        rd = isolated["run_dir"]
        m1 = (rd / "MODEL" / "model-002.glb").read_bytes()
        report1 = (rd / "BRIDGE_REPORT.json").read_text()
        second = bridge_gate.ensure_artifacts("ts_r418_test")
        assert second["outcome"] == first["outcome"]
        assert second["at"] == first["at"]  # same record, not re-run
        assert (rd / "MODEL" / "model-002.glb").read_bytes() == m1
        assert (rd / "BRIDGE_REPORT.json").read_text() == report1

    def test_report_language_guard(self, isolated):
        """The shipped report must not assert patentability (directive
        §3 — the same banned-phrase list the CIO enforces)."""
        bridge_gate.ensure_artifacts("ts_r418_test")
        rd = isolated["run_dir"]
        text = (rd / "BRIDGE_REPORT.json").read_text().lower()
        for phrase in cio_mod.BANNED_PHRASES:
            assert phrase not in text, f"banned phrase in report: {phrase}"

    def test_conceptual_never_claims_engineering(self, isolated):
        """Art. XXVIII pin: the conceptual authority text can never
        appear on an engineering-class geometry and vice versa."""
        bridge_gate.ensure_artifacts("ts_r418_test")
        session = dict(isolated["session"])
        cio_obj = cio_mod.build_cio(session)
        geo = cio_obj["geometry"]
        if geo["conceptual"]:
            assert "parametric build is the engineering geometry" \
                   not in geo["authority"]
            # no STEP/STL exported for conceptual artifacts
            assert geo["step"] == []
            assert geo["stl"] == []
