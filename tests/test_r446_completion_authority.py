"""tests/test_r446_completion_authority.py — R446-C1 Task 4: the
false-complete state attacks at the product boundary, closed against
the canonical completion marker (run_manifest.json — the R445-C
completion authority).

THE SIX ATTACK STATES (the directive's list), each injected and each
required to FAIL CLOSED (no user-visible COMPLETE):

  A. final_state.json exists but evolution incomplete
     (final_state.json is persisted PRE-evolution — the R445-C measured
     defect class: a killed slice left runs LOOKING complete)
  B. worker dies after state serialization
     (session RUNNING + dead worker pid + partial run dir)
  C. package exists but later stage incomplete
     (DOWNLOAD/*.zip + PACKAGE_REPORT.json complete, no marker)
  D. CIO succeeds while package fails
     (invention artifacts present -> build_cio returns present=true,
      but the run never completed: CIO-200/present=true is NOT
      completion evidence — the two axes never collapse)
  E. visual typed-skip while the website would claim complete
     (COMPLETE marker + render record SKIPPED_LOW_MEMORY: the run axis
      is complete, the visual axis honestly is not — hero suppressed,
      typed skip surfaced, no visual-complete claim)
  F. resumed run after sandbox/process interruption
     (partial run dir -> NOT_MARKED -> marker lands on completion ->
      COMPLETE_MARKED; a partial marker stays NOT_MARKED)

Constitutional anchors: Art. X (one authority — the marker), Art. XXV
(absence of the marker is not a verdict), Art. LXI (infrastructure
states never scientific), Art. IX (the reconciliation is read-only —
the session record is not mutated during observation).
"""
from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import completion  # noqa: E402
from toscanini.completion import (  # noqa: E402
    COMPLETE_MARKED,
    NOT_MARKED,
    completion_marker_state,
    completion_proves_run,
)


# ---------------------------------------------------------------------------
# run-dir builders (the attack fixtures)
# ---------------------------------------------------------------------------
def _write(p: Path, obj) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, indent=1, default=str))


def _full_marker(final_status="INVENTION_REQUIRES_EXPERIMENT"):
    return {
        "run_id": "r446-attack",
        "finished_at": "2026-09-11T00:00:00Z",
        "failed_stages": {},
        "final_status": final_status,
        "final_envelope_hash": "abc123",
    }


def _final_state(final_status="INVENTION_REQUIRES_EXPERIMENT"):
    return {"final_status": final_status,
            "timestamp": "2026-09-11T00:00:00Z",
            "evolution": {"n_generations": 2}}


@pytest.fixture()
def run_dir(tmp_path):
    return tmp_path / "ENGINE_RUNS" / "ts_attack"


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("toscanini.sessions.STORE_DIR", tmp_path)
    monkeypatch.setattr("toscanini.sessions.SESSIONS_PATH",
                        tmp_path / "sessions.json")
    monkeypatch.setattr("toscanini.sessions.SHARES_PATH",
                        tmp_path / "shares.json")
    return importlib.import_module("toscanini.sessions")


# ---------------------------------------------------------------------------
# The completion authority itself
# ---------------------------------------------------------------------------
class TestCompletionMarkerState:
    def test_no_run_dir_is_not_marked(self):
        out = completion_marker_state(None)
        assert out["completion"] == NOT_MARKED

    def test_empty_dir_is_not_marked(self, tmp_path):
        out = completion_marker_state(tmp_path / "empty")
        assert out["completion"] == NOT_MARKED
        assert out["reason"]

    def test_existing_dir_without_marker_not_marked(self, tmp_path):
        d = tmp_path / "present_but_empty"
        d.mkdir()
        out = completion_marker_state(d)
        assert out["completion"] == NOT_MARKED
        assert "NOT completion evidence" in out["reason"]

    def test_full_marker_is_complete_marked(self, run_dir):
        _write(run_dir / "run_manifest.json", _full_marker())
        out = completion_marker_state(run_dir)
        assert out["completion"] == COMPLETE_MARKED
        assert completion_proves_run(run_dir) is True

    def test_partial_marker_names_missing_fields(self, run_dir):
        m = _full_marker()
        del m["finished_at"]  # the run() tail never executed
        _write(run_dir / "run_manifest.json", m)
        out = completion_marker_state(run_dir)
        assert out["completion"] == NOT_MARKED
        assert out["missing_marker_fields"] == ["finished_at"]

    def test_corrupt_marker_is_not_marked(self, run_dir):
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "run_manifest.json").write_text("{not json")
        out = completion_marker_state(run_dir)
        assert out["completion"] == NOT_MARKED


# ---------------------------------------------------------------------------
# ATTACK A — final_state.json exists but evolution incomplete
# ---------------------------------------------------------------------------
class TestAttackAFinalStateWithoutMarker:
    def test_final_state_alone_is_not_completion_evidence(self, run_dir):
        # exactly the R445-C measured defect class: final_state.json
        # persisted PRE-evolution, process died before the run() tail
        _write(run_dir / "final_state.json", _final_state())
        out = completion_marker_state(run_dir)
        assert out["completion"] == NOT_MARKED
        assert "final_state.json" in out["reason"]
        assert "NOT completion evidence" in out["reason"]

    def test_worker_phase4_interrupted_not_complete(self, run_dir):
        # the phase-4 decision (worker._phase4_terminal_state) on the
        # attack-A dir: INTERRUPTED, never COMPLETE
        from toscanini import worker
        _write(run_dir / "final_state.json", _final_state())
        status, final_status, error = worker._phase4_terminal_state(
            run_dir, json.loads(
                (run_dir / "final_state.json").read_text()),
            {"final_status": "INVENTION_REQUIRES_EXPERIMENT"})
        assert status == "INTERRUPTED"
        assert "canonical completion marker" in error
        # the final_status still travels honestly (Art. LXI)
        assert final_status == "INVENTION_REQUIRES_EXPERIMENT"

    def test_projection_never_claims_complete(self, run_dir):
        # a session record that SAYS complete (pre-authority era /
        # stale durable snapshot) reconciles read-only to INTERRUPTED
        from toscanini import run_state as rs
        _write(run_dir / "final_state.json", _final_state())
        session = {"session_id": "ts_attack_a", "status": "COMPLETE",
                   "final_status": "INVENTION_REQUIRES_EXPERIMENT",
                   "run_dir": str(run_dir)}
        state = rs.canonical_run_state(session)
        assert state["status"] == "INTERRUPTED"
        assert state["outcome"] == rs.OUTCOME_RUN_BLOCKED
        rec = state["completion_reconciliation"]
        assert rec["session_record_says"] == "COMPLETE"
        assert rec["projected_status"] == "INTERRUPTED"
        assert "run_manifest.json" in rec["authority"]
        # read-only: the input session record is untouched (Art. IX)
        assert session["status"] == "COMPLETE"


# ---------------------------------------------------------------------------
# ATTACK B — worker dies after state serialization
# ---------------------------------------------------------------------------
class TestAttackBWorkerDeath:
    def test_dead_worker_session_interrupted_not_complete(
            self, store, run_dir, monkeypatch):
        # RUNNING session whose worker pid is verifiably dead + a run
        # dir with a serialized final_state but NO marker: the restart
        # sweep marks INTERRUPTED; nothing ever promotes it to COMPLETE
        _write(run_dir / "final_state.json", _final_state())
        created = store.create_session("attack b", "user text")
        sid = created["session_id"]
        # a pid that is dead by construction (negative pid is never
        # alive; worker_alive returns False, not a guess)
        store.update_session(sid, status="RUNNING",
                             worker_pid=-1, worker_starttime="0",
                             run_dir=str(run_dir))
        # run the R392 restart sweep
        interrupted = store.mark_interrupted_sessions()
        assert sid in interrupted
        row = store.get_session(sid)
        assert row["status"] == "INTERRUPTED"
        # and the completion authority agrees: this run is NOT complete
        assert completion_proves_run(run_dir) is False

    def test_phase4_on_death_leftover_state(self, run_dir):
        # even if a NEW worker picks the session up and reaches phase 4
        # with the leftover serialized state, the marker check holds
        from toscanini import worker
        _write(run_dir / "final_state.json", _final_state())
        _write(run_dir / "envelope_RANK.json", {"stage_log": []})
        status, _, _ = worker._phase4_terminal_state(
            run_dir, _final_state(), {})
        assert status == "INTERRUPTED"


# ---------------------------------------------------------------------------
# ATTACK C — package exists but later stage incomplete
# ---------------------------------------------------------------------------
class TestAttackCPackageWithoutCompletion:
    def test_package_artifacts_are_not_completion_evidence(self, run_dir):
        # a full package tree + final_state + release artifacts, but the
        # run() tail (which writes the marker) never executed
        _write(run_dir / "final_state.json", _final_state())
        _write(run_dir / "PACKAGE_REPORT.json",
               {"complete": True, "maturity": "TECHNOLOGY_TRANSFER"})
        _write(run_dir / "DOWNLOAD" / "TECHNOLOGY_PACKAGE_x.zip",
               {"bytes": "fixture"})
        _write(run_dir / "RELEASE_PROOF.json", {"status": "RECORDED"})
        out = completion_marker_state(run_dir)
        assert out["completion"] == NOT_MARKED
        assert completion_proves_run(run_dir) is False

    def test_projection_with_package_still_not_complete(self, run_dir):
        from toscanini import run_state as rs
        _write(run_dir / "final_state.json", _final_state())
        _write(run_dir / "PACKAGE_REPORT.json",
               {"complete": True, "maturity": "TECHNOLOGY_TRANSFER"})
        session = {"session_id": "ts_attack_c", "status": "COMPLETE",
                   "final_status": "AUTOMATED_INVENTION_CANDIDATE",
                   "run_dir": str(run_dir)}
        state = rs.canonical_run_state(session)
        assert state["status"] == "INTERRUPTED"
        # a package existing never converts the state (Art. XXV)
        assert state["outcome"] == rs.OUTCOME_RUN_BLOCKED


# ---------------------------------------------------------------------------
# ATTACK D — CIO succeeds while package fails
# ---------------------------------------------------------------------------
class TestAttackDCioSucceedsPackageFails:
    def _invention_run_dir(self, run_dir):
        # invention-side artifacts ONLY (no package, no marker): the CIO
        # builds present=true from these — honestly presenting the
        # artifacts the run DID produce
        _write(run_dir / "INVENTION_SPECIFICATION.json", {
            "invention_id": {"value": "ts_attack_d"},
            "problem": {"value": "the attack problem"},
            "mechanism": {"value": {
                "mechanism": "staged header-side filtration with "
                             "dP-triggered backflush",
                "intervention": "wedge-wire cascade",
                "expected_effect": "clogging below 0.5 per campaign"}},
            "killer_experiment": {"value": {
                "selected": "campaign clogging count"}},
        })
        _write(run_dir / "final_state.json",
               _final_state("AUTOMATED_INVENTION_CANDIDATE"))
        return run_dir

    def test_cio_present_true_is_not_completion_evidence(self, run_dir):
        from toscanini import cio as _cio
        rd = self._invention_run_dir(run_dir)
        obj = _cio.build_cio({"session_id": "ts_attack_d",
                              "run_dir": str(rd),
                              "user_text": "attack",
                              "final_status":
                              "AUTOMATED_INVENTION_CANDIDATE",
                              "origin": "test"})
        # the CIO honestly presents the invention artifacts...
        assert obj is not None
        assert obj["identity"]["mechanism"]
        # ...while the completion authority honestly says NOT complete:
        # CIO-200/present=true is artifact evidence, never completion
        # evidence (the two axes never collapse)
        assert completion_proves_run(rd) is False
        assert (obj.get("downloads") or {}).get("package_zip") is None

    def test_extractor_and_authority_agree_on_axes(self, run_dir):
        # the join with Task 1: the CIO extractor may verify FIELDS on
        # the CIO body while the completion authority still says the
        # RUN is incomplete — field extraction is not run completion
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from r446_cio_extraction import extract_cio_fields
        from toscanini import cio as _cio
        rd = self._invention_run_dir(run_dir)
        obj = _cio.build_cio({"session_id": "ts_attack_d",
                              "run_dir": str(rd),
                              "user_text": "attack",
                              "final_status":
                              "AUTOMATED_INVENTION_CANDIDATE",
                              "origin": "test"})
        obj["present"] = True
        (obj.get("provenance") or {}).pop("run_dir", None)
        out = extract_cio_fields(200, obj)
        # fields extracted (or typed missing) — either way the
        # extraction state is about THE CIO's fields...
        assert out["extraction_state"] in (
            "CIO_FIELDS_VERIFIED", "CIO_MISSING_CANONICAL_FIELDS")
        # ...and the completion authority is about THE RUN — different
        # question, never collapsed
        assert completion_proves_run(rd) is False


# ---------------------------------------------------------------------------
# ATTACK E — visual typed-skip while the website would claim complete
# ---------------------------------------------------------------------------
class TestAttackEVisualTypedSkip:
    def _complete_run_with_typed_skip(self, run_dir):
        _write(run_dir / "final_state.json", _final_state())
        _write(run_dir / "run_manifest.json", _full_marker())
        _write(run_dir / "MODEL" / "3D" / "render_record.json", {
            "schema_version": "r443-render-record/1.0.0",
            "status": "SKIPPED_LOW_MEMORY",
            "status_detail": {
                "reason": "RENDER_SKIPPED_LOW_MEMORY",
                "note": "typed skip — the free plan cannot render "
                        "(Art. LXI honest state)"},
            "render_pipeline": "VISUAL_COMPILER_HEADLESS_THREE",
        })
        _write(run_dir / "MODEL" / "3D" / "visual_gate.json", {
            "verdict": "NOT_RUN",
            "hero_suppressed": True,
            "failed_rules": [],
        })
        return run_dir

    def test_run_complete_visual_axis_honestly_skipped(self, run_dir):
        from toscanini import cio as _cio
        rd = self._complete_run_with_typed_skip(run_dir)
        # the RUN axis: complete (the marker proves it)
        assert completion_proves_run(rd) is True
        # the VISUAL axis: honestly NOT complete — the typed skip
        # surfaces verbatim; no hero, no visual-complete claim
        obj = _cio.build_cio({"session_id": "ts_attack_e",
                              "run_dir": str(rd),
                              "user_text": "attack",
                              "final_status":
                              "INVENTION_REQUIRES_EXPERIMENT",
                              "origin": "test"})
        assert obj is not None
        renders = (obj.get("visualization") or {}).get("renders") or {}
        assert renders.get("status") == "SKIPPED_LOW_MEMORY"
        gate = renders.get("visual_gate") or {}
        assert gate.get("verdict") == "NOT_RUN"
        assert gate.get("hero_suppressed") is True

    def test_completion_never_promotes_visual_state(self, run_dir):
        # a COMPLETE run marker is not visual evidence either: the two
        # axes stay orthogonal (Art. XXVIII — no silent promotion)
        rd = self._complete_run_with_typed_skip(run_dir)
        assert completion_proves_run(rd) is True
        from toscanini import cio as _cio
        obj = _cio.build_cio({"session_id": "ts_attack_e",
                              "run_dir": str(rd),
                              "user_text": "attack",
                              "final_status":
                              "INVENTION_REQUIRES_EXPERIMENT",
                              "origin": "test"})
        maturity = (obj.get("maturity") or {})
        # design maturity is about GEOMETRY presence, not render success
        renders = (obj.get("visualization") or {}).get("renders") or {}
        assert renders.get("status") == "SKIPPED_LOW_MEMORY"


# ---------------------------------------------------------------------------
# ATTACK F — resumed run after sandbox/process interruption
# ---------------------------------------------------------------------------
class TestAttackFResumedRun:
    def test_partial_then_complete_lifecycle(self, run_dir):
        # the interruption: final_state without the marker
        _write(run_dir / "final_state.json", _final_state())
        assert completion_proves_run(run_dir) is False
        # the resume: the engine completes the tail and lands the
        # marker (the only promotion path — the bytes prove it)
        _write(run_dir / "run_manifest.json", _full_marker())
        assert completion_proves_run(run_dir) is True

    def test_engine_resume_reconstruction_available(self, run_dir):
        # EngineRun.from_run_dir reconstructs a RESUMABLE run from the
        # persisted artifacts — the interrupted run is recoverable,
        # never silently promoted
        _write(run_dir / "problem.json", {
            "problem_id": "r446-attack-f",
            "device": "fixture device",
            "failure": "fixture failure",
            "constraint": "fixture constraint"})
        _write(run_dir / "final_state.json", _final_state())
        from discovery_fabric.engine.run import EngineRun
        eng = EngineRun.from_run_dir(str(run_dir))
        assert eng.resume is True
        # still not complete until the tail runs
        assert completion_proves_run(run_dir) is False

    def test_r445_driver_marker_check_uses_same_authority(self):
        # the R445-C evolution rerun driver's completion check consumes
        # the same canonical marker semantics (one authority, Art. X)
        src = (REPO_ROOT / "scripts" /
               "r445_evolution_rerun.py").read_text()
        assert "run_manifest.json" in src
        assert "TRUE completion marker" in src


# ---------------------------------------------------------------------------
# The seeding boundary
# ---------------------------------------------------------------------------
class TestSeedingBoundary:
    def test_seed_without_marker_seeds_interrupted(self, store,
                                                   tmp_path, monkeypatch):
        # a seed run dir WITHOUT the canonical marker seeds with its
        # TRUE state, never COMPLETE
        campaign = tmp_path / "campaign"
        run_dir = campaign / "ENGINE_RUNS" / "t6_fixture_domain"
        _write(run_dir / "final_state.json",
               _final_state("AUTOMATED_INVENTION_CANDIDATE"))
        _write(campaign / "RUN_medical.json", {
            "problem_id": "t6_fixture_domain",
            "run_dir": str(run_dir.relative_to(tmp_path))})
        # point the seeding at the fixture campaign
        monkeypatch.setattr(store, "SEED_CAMPAIGN", campaign)
        monkeypatch.setattr(store, "REPO_ROOT", tmp_path)
        # the campaign record's run_dir is relative to REPO_ROOT
        added = store.seed_benchmark_sessions()
        assert added == 1
        row = store.get_session("ts_seed_medical")
        assert row["status"] == "INTERRUPTED"
        assert row["completion_basis"] != "run_manifest.json (canonical" \
            " marker)"
        assert row["error"]

    def test_seed_with_marker_seeds_complete(self, store, tmp_path,
                                             monkeypatch):
        campaign = tmp_path / "campaign"
        run_dir = campaign / "ENGINE_RUNS" / "t6_fixture_domain"
        _write(run_dir / "final_state.json",
               _final_state("AUTOMATED_INVENTION_CANDIDATE"))
        _write(run_dir / "run_manifest.json", _full_marker(
            "AUTOMATED_INVENTION_CANDIDATE"))
        _write(campaign / "RUN_medical.json", {
            "problem_id": "t6_fixture_domain",
            "run_dir": str(run_dir.relative_to(tmp_path))})
        monkeypatch.setattr(store, "SEED_CAMPAIGN", campaign)
        monkeypatch.setattr(store, "REPO_ROOT", tmp_path)
        added = store.seed_benchmark_sessions()
        assert added == 1
        row = store.get_session("ts_seed_medical")
        assert row["status"] == "COMPLETE"
        assert row["completion_basis"] == \
            "run_manifest.json (canonical marker)"
