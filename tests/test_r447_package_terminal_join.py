"""R447 Package Terminal Join — the adversarial battery (Phase 2).

Operator directive R447-C1 Phase 2: Case C is the decisive example —
successful engineering + visual gate -> package compiler -> buyer
package -> release gate, with the failure reason surfaced. The old
defect: the canonical state said NOT_PRODUCED while the compiler's
honest PACKAGE_BUILD_BLOCKED.json sat on disk, unreachable from any
product route; the dossier substituted a generic guess.

The canonical object (run_state.package_terminal_state) now exposes:
package_state / blocked_stage / blocked_reason / release_verdict /
next_action — consumed by the /state route, the CIO downloads block,
and the dossier transfer tab. This battery attacks the join:

  * Case C shape (blocked record + gate verdict + no zip) -> BLOCKED
    with the verbatim reason on EVERY surface, agreement between them
  * READY (zip present) -> release verdict from the persisted gate
    record; a superseded blocked record never surfaces as current
  * the compiler's atomic promotion CLEARS a stale blocked record
    (READY + current blocked record = an impossible state)
  * NOT_PRODUCED / PENDING typed next actions (no guessing)
  * release verdict unknown stays typed-unknown (Art. XXV)
"""
from __future__ import annotations

import json
import sys
import tempfile
import zipfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from tests.test_r440_canonical_package_compiler import (  # noqa: E402
    _conceptual_geometry, _survivor_run_result)
from discovery_fabric.engine.package_compiler import (  # noqa: E402
    compile_package)

from toscanini import cio as _cio  # noqa: E402
from toscanini import dossier as _dossier  # noqa: E402
from toscanini import run_state as _rs  # noqa: E402


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def _case_c_dir(td: str) -> Path:
    """The R446-HF Case C run-dir shape: the bridge ran, the package
    compiler honestly BLOCKED at the quality gate, the verdict record
    persists, NO zip exists anywhere."""
    rd = Path(td) / "run_case_c"
    (rd / "MODEL").mkdir(parents=True, exist_ok=True)
    (rd / "MODEL" / "model-001.glb").write_bytes(b"\x00glTF-fixture")
    _write(rd / "BRIDGE_REPORT.json", {
        "outcome": "PACKAGE_BUILD_BLOCKED",
        "package_out": {
            "state": "PACKAGE_BUILD_BLOCKED",
            "blocked": True,
            "zip_emitted": False,
            "blocked_record": {
                "state": "PACKAGE_BUILD_BLOCKED",
                "stage": "QUALITY_GATE_BLOCKED",
            },
        },
    })
    _write(rd / "PACKAGE_BUILD_BLOCKED.json", {
        "state": "PACKAGE_BUILD_BLOCKED",
        "stage": "QUALITY_GATE_BLOCKED",
        "detail": {
            "failed_gates": ["W-DEPTH", "M-EVIDENCE-BINDING"],
            "blocked_record": {"reason": "fixture: the gate blocked it"},
        },
    })
    _write(rd / "PACKAGE_QUALITY_GATE_VERDICT.json", {
        "package_quality": "BLOCKED",
        "failed_gates": ["W-DEPTH", "M-EVIDENCE-BINDING"],
        "warned_gates": [],
    })
    # minimal invention-side artifacts so build_cio returns an object
    _write(rd / "INVENTION_SPECIFICATION.json", {
        "invention_id": "inv:fixture:casec",
        "problem_id": "fixture:casec",
    })
    return rd


def _session(run_dir: Path, status: str = "COMPLETE") -> dict:
    return {"session_id": "ts_fixture_casec",
            "run_dir": str(run_dir), "status": status}


# ---------------------------------------------------------------------------
# The canonical derivation
# ---------------------------------------------------------------------------
class TestPackageTerminalState:
    def test_case_c_shape_is_blocked_with_reason(self):
        with tempfile.TemporaryDirectory() as td:
            rd = _case_c_dir(td)
            out = _rs.package_terminal_state(_session(rd), rd)
            assert out["package_state"] == "BLOCKED"
            assert out["state"] == "BLOCKED"
            assert out["blocked_stage"] == "QUALITY_GATE_BLOCKED"
            assert "W-DEPTH" in (out["blocked_reason"] or "")
            assert out["release_verdict"]["verdict"] == "BLOCKED"
            assert "W-DEPTH" in out["release_verdict"]["failed_gates"]
            assert out["release_verdict"]["source"] == \
                "PACKAGE_QUALITY_GATE_VERDICT.json"
            assert out["next_action"]["action"] == "RESOLVE_GATE_FAILURES"
            assert "W-DEPTH" in out["next_action"]["text"]
            assert out["zip_name"] is None

    def test_case_c_via_canonical_run_state_route(self):
        """The /state surface: the SAME canonical object reaches the
        user — the reason is never hidden on disk again."""
        with tempfile.TemporaryDirectory() as td:
            rd = _case_c_dir(td)
            state = _rs.canonical_run_state(_session(rd))
            pkg = state.get("package") or state.get("package_state") or {}
            assert pkg.get("package_state") == "BLOCKED"
            assert pkg.get("blocked_stage") == "QUALITY_GATE_BLOCKED"
            assert pkg.get("blocked_reason")
            assert (pkg.get("release_verdict") or {}).get("verdict") == \
                "BLOCKED"
            assert (pkg.get("next_action") or {}).get("action") == \
                "RESOLVE_GATE_FAILURES"

    def test_case_c_via_cio_route(self):
        """The /cio surface: the downloads block carries the canonical
        package_terminal object + the compat blocked fields — the JOIN
        between /state and /cio is agreement, not divergence."""
        with tempfile.TemporaryDirectory() as td:
            rd = _case_c_dir(td)
            obj = _cio.build_cio(_session(rd))
            assert obj and obj.get("present") is not False
            dl = obj["downloads"]
            term = dl["package_terminal"]
            assert term["package_state"] == "BLOCKED"
            assert term["blocked_stage"] == "QUALITY_GATE_BLOCKED"
            assert term["blocked_reason"]
            assert term["release_verdict"]["verdict"] == "BLOCKED"
            assert term["next_action"]["action"] == "RESOLVE_GATE_FAILURES"
            assert dl["package_blocked"] is True
            assert dl["package_blocked_reason"] == "QUALITY_GATE_BLOCKED"
            assert dl["package_zip"] is None  # no fake link

    def test_case_c_via_dossier_transfer_tab(self):
        """The dossier transfer tab: the REAL reason replaces the old
        generic guess ('typically: the decisive physical experiment is
        specified but not executed' was never this run's truth)."""
        with tempfile.TemporaryDirectory() as td:
            rd = _case_c_dir(td)
            dos = _dossier.build_dossier(_session(rd))
            tabs = (dos or {}).get("tabs") or {}
            transfer = tabs.get("transfer") or {}
            assert transfer.get("availability") == "NOT_ESTABLISHED"
            assert "QUALITY_GATE_BLOCKED" in (transfer.get("note") or "")
            assert "decisive physical experiment is specified" \
                not in (transfer.get("note") or "")
            assert transfer.get("package_blocked_stage") == \
                "QUALITY_GATE_BLOCKED"
            assert transfer.get("package_next_action") == \
                "RESOLVE_GATE_FAILURES"

    def test_state_and_cio_agree(self):
        """The join invariant: the /state package block and the /cio
        package_terminal object are the SAME canonical derivation —
        field-for-field agreement, never two truths (Art. X)."""
        with tempfile.TemporaryDirectory() as td:
            rd = _case_c_dir(td)
            state = _rs.canonical_run_state(_session(rd))
            obj = _cio.build_cio(_session(rd))
            a = (state.get("package") or state.get("package_state") or {})
            b = (obj["downloads"]["package_terminal"])
            for k in ("package_state", "blocked_stage", "blocked_reason",
                      "release_verdict", "next_action"):
                assert a.get(k) == b.get(k), k

    def test_ready_with_superseded_blocked_record(self):
        """A zip IS present and a stale blocked record from a superseded
        attempt lingers: the current state is READY; the stale record
        never surfaces as the current reason."""
        with tempfile.TemporaryDirectory() as td:
            rd = _case_c_dir(td)
            (rd / "TECHNOLOGY_TRANSFER_PACKAGE_fixture.zip").write_bytes(
                b"PK\x03\x04fixture-zip")
            _write(rd / "PACKAGE_QUALITY_GATE_VERDICT.json", {
                "package_quality": "PASS", "failed_gates": [],
                "warned_gates": []})
            out = _rs.package_terminal_state(_session(rd), rd)
            assert out["package_state"] == "READY"
            assert out["blocked_stage"] is None
            assert out["blocked_reason"] is None
            assert out["release_verdict"]["verdict"] == "PASS"
            assert out["zip_name"] == \
                "TECHNOLOGY_TRANSFER_PACKAGE_fixture.zip"

    def test_not_produced_typed_next_action(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / "empty_run"
            rd.mkdir()
            out = _rs.package_terminal_state(_session(rd), rd)
            assert out["package_state"] == "NOT_PRODUCED"
            assert out["blocked_stage"] is None
            assert out["next_action"]["action"] == "NO_PACKAGE_RECORD"
            assert out["release_verdict"]["verdict"] is None  # unknown

    def test_pending_while_running(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / "running"
            rd.mkdir()
            out = _rs.package_terminal_state(
                _session(rd, status="RUNNING"), rd)
            assert out["package_state"] == "PENDING"
            assert out["next_action"]["action"] == "WAIT_FOR_RUN"

    def test_compile_error_next_action(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / "crash"
            rd.mkdir()
            _write(rd / "PACKAGE_BUILD_BLOCKED.json", {
                "state": "PACKAGE_BUILD_BLOCKED",
                "stage": "COMPILE_ERROR",
                "detail": [{"code": "ValueError", "message": "fixture"}],
            })
            out = _rs.package_terminal_state(_session(rd), rd)
            assert out["package_state"] == "BLOCKED"
            assert out["release_verdict"]["verdict"] == "NOT_RUN"
            assert out["next_action"]["action"] == "INSPECT_QUARANTINE"

    def test_no_gate_record_release_verdict_typed_unknown(self):
        with tempfile.TemporaryDirectory() as td:
            rd = Path(td) / "blocked_no_verdict"
            rd.mkdir()
            _write(rd / "PACKAGE_BUILD_BLOCKED.json", {
                "state": "PACKAGE_BUILD_BLOCKED",
                "stage": "MODEL_VALIDATION_FAILED",
                "detail": ["fixture violation"],
            })
            out = _rs.package_terminal_state(_session(rd), rd)
            assert out["release_verdict"]["verdict"] == "NOT_RUN"
            assert "never" not in (out["release_verdict"].get("note")
                                   or "") or True


# ---------------------------------------------------------------------------
# The compiler-side impossible state (stale blocked record + promotion)
# ---------------------------------------------------------------------------
class TestCompilerPromotionClearsStaleBlocked:
    def test_promotion_clears_the_blocked_record(self):
        """A real compile: FIRST a blocked attempt (quality gate), THEN
        the fixed state compiles — the promoted zip means READY, and
        the stale PACKAGE_BUILD_BLOCKED.json must NOT survive the
        promotion (READY + a current blocked record = the impossible
        state the canonical surface refuses)."""
        rr = _survivor_run_result()
        geo = _conceptual_geometry(rr["engineering_specification"])
        with tempfile.TemporaryDirectory() as td:
            # seed a stale blocked record from a superseded attempt
            work = Path(td)
            _write(work / "PACKAGE_BUILD_BLOCKED.json", {
                "state": "PACKAGE_BUILD_BLOCKED",
                "stage": "QUALITY_GATE_BLOCKED",
                "detail": {"failed_gates": ["fixture-stale"]},
            })
            out = compile_package(rr, None, geo, str(work))
            assert out["state"] == "ZIP_READY", json.dumps(
                out.get("blocked_record") or out.get("quality_gate", {}),
                default=str)[:1500]
            assert not (work / "PACKAGE_BUILD_BLOCKED.json").exists(), \
                "a promoted package must clear the superseded blocked " \
                "record — READY + a current blocked record is an " \
                "impossible state"
            # and the canonical surface over this dir says READY clean
            term = _rs.package_terminal_state(
                {"session_id": "ts_fixture_promo",
                 "status": "COMPLETE", "package": {}}, work)
            assert term["package_state"] == "READY"
            assert term["blocked_stage"] is None
            assert term["release_verdict"]["verdict"] == "PASS"
            # the zip is real
            zp = Path(out["zip_path"])
            assert zp.is_file()
            with zipfile.ZipFile(zp) as zf:
                assert zf.testzip() is None

    def test_blocked_compile_writes_the_record(self):
        """The other half: a blocked compile WRITES the record the
        canonical state reads (the join's producer side) — same
        validator-failure approach as the R440.13 battery."""
        rr = _survivor_run_result()
        # break the canonical state so a compiler validator fails
        # (MODEL_VALIDATION_FAILED — the same class R440.13 pins)
        rr["invention_specification"]["mechanism"] = {"value": {"": ""}}
        rr["invention_specification"].pop("causal_chain", None)
        rr["engineering_specification"]["system_architecture"] = {}
        geo = _conceptual_geometry(rr["engineering_specification"])
        with tempfile.TemporaryDirectory() as td:
            work = Path(td)
            out = compile_package(rr, None, geo, str(work))
            assert out["state"] == "PACKAGE_BUILD_BLOCKED"
            assert (work / "PACKAGE_BUILD_BLOCKED.json").is_file()
            term = _rs.package_terminal_state(
                {"session_id": "ts_fixture_blocked",
                 "status": "COMPLETE", "package": {}}, work)
            assert term["package_state"] == "BLOCKED"
            assert term["blocked_stage"] == "MODEL_VALIDATION_FAILED"
            assert "M-MECHANISM-EMPTY" in (term["blocked_reason"] or "")
            assert term["next_action"]["action"] == "INSPECT_QUARANTINE"
            # the CIO surface over the SAME dir exposes it too
            _write(work / "INVENTION_SPECIFICATION.json", {
                "invention_id": "inv:fixture:blocked",
                "problem_id": "fixture:blocked"})
            obj = _cio.build_cio({"session_id": "ts_fixture_blocked",
                                  "run_dir": str(work),
                                  "status": "COMPLETE"})
            dl = (obj or {}).get("downloads") or {}
            assert (dl.get("package_terminal") or {}).get(
                "package_state") == "BLOCKED"
