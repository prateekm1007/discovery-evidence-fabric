"""R447 Package/Visual Join Attack — Phase 7 battery.

Operator directive: deliberately inject
  1. visual PASS but package failure
  2. package PASS but visual identity mismatch
  3. geometry exists but canonical identity mismatch
  4. experiment exists but falsification field absent
The system must NEVER collapse these states — each pair must surface
as TWO distinct, honest canonical fields (never one borrowed from the
other, never a merge that hides the failing half).

The battery attacks the CANONICAL SURFACES (run_state / CIO / dossier)
with crafted run dirs carrying each inconsistent pair and asserts:
  - attack 1: visual gate COMPLETE_PASS + PACKAGE_BUILD_BLOCKED ->
      package_state BLOCKED with the compiler's own stage/reason (the
      visual pass must NOT leak into the package state); the CIO
      carries BOTH truths distinctly
  - attack 2: a promoted zip (READY) + HERO_RELEASE_STATE blocked ->
      release_verdict VISUAL_RELEASE_BLOCKED (Art. LXXII outranks the
      package gate) + package_state READY + next_action
      RESOLVE_VISUAL_GATE — never a release-ready presentation
  - attack 3: geometry present + the gate's node_identity FAIL (the
      R446 Case B class) -> the visual verdict FAIL with the failed
      rules; the CIO geometry block stays present=true (honest) while
      the visual block stays FAIL (never collapsed to 'complete')
  - attack 4: an experiment record with FALSIFICATION_THRESHOLD absent
      -> the /state experiment block carries
      falsification_contract.contract_complete=False (Art. LII via the
      R444-D instrument) — never a fine-looking experiment
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import cio as _cio  # noqa: E402
from toscanini import run_state as _rs  # noqa: E402


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def _base_run(td: str) -> Path:
    rd = Path(td) / "run"
    (rd / "MODEL").mkdir(parents=True, exist_ok=True)
    (rd / "MODEL" / "model-001.glb").write_bytes(b"\x00glTF-fixture")
    _write(rd / "INVENTION_SPECIFICATION.json", {
        "invention_id": "inv:fixture:join", "problem_id": "fixture:join"})
    return rd


def _session(rd: Path, status: str = "COMPLETE") -> dict:
    return {"session_id": "ts_join_fixture", "run_dir": str(rd),
            "status": status}


# ---------------------------------------------------------------------------
# Attack 1 — visual PASS but package failure
# ---------------------------------------------------------------------------
class TestAttack1VisualPassPackageFailure:
    def test_package_stays_blocked_with_reason(self):
        with tempfile.TemporaryDirectory() as td:
            rd = _base_run(td)
            _write(rd / "MODEL" / "3D" / "render_record.json", {
                "status": "OK",
                "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE"})
            _write(rd / "MODEL" / "3D" / "visual_gate.json", {
                "verdict": "COMPLETE_PASS", "hero_suppressed": False})
            _write(rd / "MODEL" / "3D" / "HERO_RELEASE_STATE.json", {
                "artifact": "HERO_RELEASE_STATE",
                "release_blocked": False,
                "gate_verdict": "COMPLETE_PASS"})
            _write(rd / "PACKAGE_BUILD_BLOCKED.json", {
                "state": "PACKAGE_BUILD_BLOCKED",
                "stage": "QUALITY_GATE_BLOCKED",
                "detail": {"failed_gates": ["W-DEPTH"]}})
            _write(rd / "PACKAGE_QUALITY_GATE_VERDICT.json", {
                "package_quality": "BLOCKED",
                "failed_gates": ["W-DEPTH"], "warned_gates": []})
            out = _rs.package_terminal_state(_session(rd), rd)
            # the package state is BLOCKED — the visual pass does NOT
            # leak into it (no collapse in either direction)
            assert out["package_state"] == "BLOCKED"
            assert out["blocked_stage"] == "QUALITY_GATE_BLOCKED"
            assert "W-DEPTH" in (out["blocked_reason"] or "")
            assert out["release_verdict"]["verdict"] == "BLOCKED"
            assert out["zip_name"] is None
            assert out["next_action"]["action"] == "RESOLVE_GATE_FAILURES"
            # the CIO carries BOTH truths distinctly
            obj = _cio.build_cio(_session(rd))
            dl = obj["downloads"]
            term = dl["package_terminal"]
            assert term["package_state"] == "BLOCKED"
            assert dl["package_zip"] is None
            vis = (obj.get("visualization") or {}).get("renders") or {}
            assert (vis.get("visual_gate") or {}).get("verdict") == \
                "COMPLETE_PASS"


# ---------------------------------------------------------------------------
# Attack 2 — package PASS but visual identity mismatch
# ---------------------------------------------------------------------------
class TestAttack2PackagePassVisualMismatch:
    def test_release_verdict_visual_blocked_over_package_ready(self):
        with tempfile.TemporaryDirectory() as td:
            rd = _base_run(td)
            (rd / "TECHNOLOGY_TRANSFER_PACKAGE_fixture.zip").write_bytes(
                b"PK\x03\x04fixture-zip")
            _write(rd / "BRIDGE_REPORT.json", {
                "package_out": {
                    "state": "ZIP_READY", "zip_emitted": True,
                    "zip_name": "TECHNOLOGY_TRANSFER_PACKAGE_fixture.zip",
                    "package_maturity": "ENGINEERING_EVALUATION"}})
            _write(rd / "PACKAGE_QUALITY_GATE_VERDICT.json", {
                "package_quality": "PASS", "failed_gates": [],
                "warned_gates": []})
            # the VISUAL half fails: identity mismatch, hero suppressed,
            # release blocked (the R446 Case B class at the release gate)
            _write(rd / "MODEL" / "3D" / "HERO_RELEASE_STATE.json", {
                "artifact": "HERO_RELEASE_STATE",
                "release_blocked": True,
                "gate_verdict": "FAIL"})
            out = _rs.package_terminal_state(_session(rd), rd)
            # package READY (the zip exists) BUT the release verdict is
            # the typed VISUAL_RELEASE_BLOCKED — two fields, no collapse
            assert out["package_state"] == "READY"
            assert out["release_verdict"]["verdict"] == \
                "VISUAL_RELEASE_BLOCKED"
            assert out["release_verdict"]["visual_gate_verdict"] == "FAIL"
            assert out["release_verdict"]["source"] == \
                "MODEL/3D/HERO_RELEASE_STATE.json"
            assert out["next_action"]["action"] == "RESOLVE_VISUAL_GATE"
            assert "Article LXXII" in out["release_verdict"]["note"]

    def test_clean_visual_pass_gives_download_action(self):
        with tempfile.TemporaryDirectory() as td:
            rd = _base_run(td)
            (rd / "TECHNOLOGY_TRANSFER_PACKAGE_fixture.zip").write_bytes(
                b"PK\x03\x04fixture-zip")
            _write(rd / "BRIDGE_REPORT.json", {
                "package_out": {
                    "state": "ZIP_READY", "zip_emitted": True,
                    "zip_name": "TECHNOLOGY_TRANSFER_PACKAGE_fixture.zip",
                    "package_maturity": "ENGINEERING_EVALUATION"}})
            _write(rd / "PACKAGE_QUALITY_GATE_VERDICT.json", {
                "package_quality": "PASS", "failed_gates": [],
                "warned_gates": []})
            _write(rd / "MODEL" / "3D" / "HERO_RELEASE_STATE.json", {
                "artifact": "HERO_RELEASE_STATE",
                "release_blocked": False,
                "gate_verdict": "COMPLETE_PASS"})
            out = _rs.package_terminal_state(_session(rd), rd)
            assert out["package_state"] == "READY"
            assert out["release_verdict"]["verdict"] == "PASS"
            assert out["next_action"]["action"] == "DOWNLOAD_PACKAGE"


# ---------------------------------------------------------------------------
# Attack 3 — geometry exists but canonical identity mismatch
# ---------------------------------------------------------------------------
class TestAttack3GeometryIdentityMismatch:
    def test_gate_fails_and_geometry_stays_honestly_present(self):
        """The R446 Case B class at the SURFACE level: the run carries
        geometry (CIO geometry.present=true, honest) while the visual
        gate verdict is FAIL with node_identity in the failed rules —
        the surface never collapses to 'visual complete'."""
        with tempfile.TemporaryDirectory() as td:
            rd = _base_run(td)
            _write(rd / "MODEL" / "3D" / "render_record.json", {
                "status": "OK",
                "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE"})
            _write(rd / "MODEL" / "3D" / "visual_gate.json", {
                "verdict": "FAIL", "hero_suppressed": True,
                "failed_rules": ["node_identity", "geometry_identity"]})
            _write(rd / "MODEL" / "3D" / "HERO_RELEASE_STATE.json", {
                "artifact": "HERO_RELEASE_STATE",
                "release_blocked": True,
                "gate_verdict": "FAIL"})
            obj = _cio.build_cio(_session(rd))
            geo = obj["geometry"]
            vis = (obj.get("visualization") or {}).get("renders") or {}
            gate = vis.get("visual_gate") or {}
            # geometry present AND gate FAIL — both honest, distinct
            assert geo["present"] is True
            assert gate.get("verdict") == "FAIL"
            assert "node_identity" in (gate.get("failed_rules") or [])
            assert gate.get("hero_suppressed") is True
            # and the package terminal carries the visual block
            term = obj["downloads"]["package_terminal"]
            assert term["release_verdict"]["verdict"] == \
                "VISUAL_RELEASE_BLOCKED"

    def test_gate_level_identity_attack_detected(self):
        """The gate-level half (the Phase 1 battery's class, proven here
        through the exported-hero identity check): a renamed node in the
        exported hero GLB fails node_identity — geometry exists, the
        canonical identity does not agree, and the gate says so."""
        from discovery_fabric.engine.visual_compiler import (
            scene_builder, visual_gate, gltf_doc)
        from discovery_fabric.engine.invention_bridge import (
            conceptual_geometry)
        built = conceptual_geometry.build_system_architecture(
            ["load path / structural backbone", "sensor grid",
             "sensor grid"], "test site")
        with tempfile.TemporaryDirectory() as td:
            glb = Path(td) / "canonical.glb"
            glb.write_bytes(built["glb_bytes"])
            spec = scene_builder.build_scene_spec(str(glb))
            hero = Path(td) / "hero.glb"
            hero.write_bytes(glb.read_bytes())
            import struct

            def mutate(doc):
                for node in doc["nodes"]:
                    if node.get("name") and "load_path" in node["name"]:
                        node["name"] = node["name"] + "_renamed"
            raw = hero.read_bytes()
            magic, version, length = struct.unpack("<4sII", raw[:12])
            offset, chunks = 12, []
            while offset < length:
                clen, ctype = struct.unpack("<I4s",
                                            raw[offset:offset + 8])
                chunks.append((ctype, raw[offset + 8:offset + 8 + clen]))
                offset += 8 + clen
            doc = json.loads(chunks[0][1].decode())
            mutate(doc)
            js = json.dumps(doc, separators=(",", ":")).encode()
            js += b" " * ((4 - len(js) % 4) % 4)
            out = bytearray(struct.pack(
                "<4sII", b"glTF", 2,
                12 + 8 + len(js) + 8 + len(chunks[1][1])))
            out += struct.pack("<I4s", len(js), b"JSON") + js
            out += struct.pack("<I4s", len(chunks[1][1]),
                               b"BIN\x00") + chunks[1][1]
            hero.write_bytes(bytes(out))
            chk = visual_gate.check_canonical_node_identity(hero, spec)
            assert not chk["pass"]
            gi = visual_gate.independent_geometry_identity(
                str(glb), hero)
            assert not gi["pass"]


# ---------------------------------------------------------------------------
# Attack 4 — experiment exists but falsification field absent
# ---------------------------------------------------------------------------
class TestAttack4ExperimentFalsificationAbsent:
    def test_surface_exposes_incomplete_contract(self):
        with tempfile.TemporaryDirectory() as td:
            rd = _base_run(td)
            # the experiment EXISTS with every field except the one
            # that answers what outcome kills the mechanism
            _write(rd / "DECISIVE_EXPERIMENT.json", {
                "HYPOTHESIS": "fixture hypothesis",
                "TREATMENT": "fixture treatment",
                "CONTROL": "fixture control",
                "MEASUREMENT": "fixture measurement",
                "APPARATUS": "fixture apparatus",
                "SAMPLE": "fixture sample",
                "ACCEPTANCE_THRESHOLD": "fixture threshold",
                "FALSIFICATION_THRESHOLD": None,
                "UNCERTAINTY": "fixture uncertainty",
                "COST": "fixture cost",
                "TIME": "fixture time",
                "SAFETY": "fixture safety",
            })
            state = _rs.canonical_run_state(_session(rd))
            exp = (state.get("experiment_state") or {})
            fc = exp.get("falsification_contract") or {}
            assert fc.get("contract_complete") is False
            assert fc.get("falsification_threshold_answered") is False
            assert "FALSIFICATION_THRESHOLD" in (fc.get("unknown_fields")
                                                 or {})
            assert exp.get("decisive_experiment_present") is True

    def test_complete_contract_passes(self):
        with tempfile.TemporaryDirectory() as td:
            rd = _base_run(td)
            _write(rd / "DECISIVE_EXPERIMENT.json", {
                "HYPOTHESIS": "h", "TREATMENT": "t", "CONTROL": "c",
                "MEASUREMENT": "m", "APPARATUS": "a", "SAMPLE": "s",
                "ACCEPTANCE_THRESHOLD": "at",
                "FALSIFICATION_THRESHOLD":
                    "deposition mass unchanged kills the mechanism",
                "UNCERTAINTY": "u", "COST": "co", "TIME": "ti",
                "SAFETY": "sa",
            })
            state = _rs.canonical_run_state(_session(rd))
            exp = (state.get("experiment_state") or {})
            fc = exp.get("falsification_contract") or {}
            assert fc.get("contract_complete") is True
            assert fc.get("falsification_threshold_answered") is True

    def test_no_experiment_stays_not_specified(self):
        with tempfile.TemporaryDirectory() as td:
            rd = _base_run(td)
            state = _rs.canonical_run_state(_session(rd))
            exp = (state.get("experiment_state") or {})
            assert exp.get("state") == "NOT_SPECIFIED"
            assert exp.get("falsification_contract") is None
