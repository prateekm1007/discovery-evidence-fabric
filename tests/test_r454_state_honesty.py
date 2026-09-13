"""R454-C2 — THE VISUAL DEADWEIGHT + STATE HONESTY battery.

Operator directive R454-C2 ("CODER 2 — VISUAL DEADWEIGHT + STATE
HONESTY"), the pytest side of the round's four code workstreams:

  §2  Do not render rejected inventions — the automatic artifact path
      (bridge_gate.ensure_artifacts) and the automatic render path
      (artifact_worker.auto_enqueue) NEVER spend engineering,
      packaging, or Visual-Compiler compute on a candidate the
      machine's own challenge killed. The explicit invocation remains
      the audit-artifact escape hatch. Blocked/under-development runs
      are NOT dead (Art. LXI / BS-010) and keep today's contract.

  §3  Unknown stays unknown — an unrecognized backend pipeline status
      is never silently styled/translated as NOT_REACHED (Art. XXV).

  §5  The contradiction fixture — status RUN_BLOCKED_TRANSPORT + a
      stale COMPLETED_CANDIDATE projection + visual_complete +
      ENGINEERING authority resolves to INFRASTRUCTURE_PAUSED, through
      the REAL compiled presentationState.ts (the Node battery
      scripts/r451_c2_ui_tests.mjs has pinned this since R451-C2-
      CLOSURE Direction C; this battery brings the same fixture into
      the pytest suite so CI enforces it against the compiled source).

  §6  Provenance — verified by measurement in the round audit (the
      Visual Compiler record carries renderer_stack + binary_resolution
      on every path and source_glb_sha256/scene_spec_sha256 for exact
      inputs; the visual-lab sidecar pins model_revision, input hashes,
      hardware/job identity, and engineering_authority=
      NONE_PRESENTATION_ONLY). The battery pins the record paths
      structurally so a regression cannot reintroduce the gap.

reviewer_provenance=AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Dict

import pytest

REPO = Path(__file__).resolve().parents[1]

from toscanini import artifact_worker as aw  # noqa: E402
from toscanini import bridge_gate  # noqa: E402
from toscanini import run_state as run_state_mod  # noqa: E402
from toscanini import sessions as store  # noqa: E402

WEBAPP = REPO / "TOSCANINI_UI" / "webapp"

# a GENUINE scientific kill reason (never the capability-failure
# signature — that class is Art. LXI, not a rejection)
_KILL_REASON = ("adversarial verdict: baseline equivalence — the "
                "candidate offers no measured advantage")


def _killed_lineage() -> Dict[str, Any]:
    """The R452-measured defect shape: a lineage whose current (and
    only) generation was GENUINELY killed, no survivor reached."""
    return {
        "generations": [
            {"gen": 1,
             "state": "INVENTION_REJECTED",
             "challenge": {"killed": True, "kill_reason": _KILL_REASON,
                           "kill_stage": "ATTACK"},
             "evidence_verified": False},
        ],
        "current_invention": {"gen": 1},
        "survivor_reached": False,
        "n_generations": 1,
    }


def _survivor_lineage() -> Dict[str, Any]:
    return {
        "generations": [
            {"gen": 1, "state": "SURVIVED",
             "challenge": {"killed": False},
             "evidence_verified": True},
        ],
        "current_invention": {"gen": 1},
        "survivor_reached": True,
        "n_generations": 1,
    }


def _killed_session(run_dir: Path) -> Dict[str, Any]:
    """A terminal COMPLETE run whose own lineage verdict says KILLED
    (the positive final_status + authoritative challenge verdict —
    exactly the 7/7 production-shape defect the R452 audit measured)."""
    return {
        "session_id": "ts_r454_dead",
        "status": "COMPLETE",
        "final_status": "EVOLVED_INVENTION_CANDIDATE",
        "run_dir": str(run_dir),
        "user_text": "a killed candidate",
    }


# ---------------------------------------------------------------------------
# §5 — THE DIRECTIVE CONTRADICTION FIXTURE (compiled presentationState.ts)
# ---------------------------------------------------------------------------
class TestTheDirectiveContradictionFixture:
    """status RUN_BLOCKED_TRANSPORT + stale COMPLETED_CANDIDATE +
    visual_complete + ENGINEERING -> INFRASTRUCTURE_PAUSED, through the
    REAL compiled mapping (the pytest-side pin of the R451-C2-CLOSURE
    Direction C fixture the directive names as 'the missing
    contradiction fixture')."""

    @pytest.fixture(scope="class")
    def compiled_mapping(self, tmp_path_factory):
        out_dir = tmp_path_factory.mktemp("r454-map-")
        tsc = WEBAPP / "node_modules" / ".bin" / "tsc"
        subprocess.run(
            [str(tsc), str(WEBAPP / "lib" / "presentationState.ts"),
             "--outDir", str(out_dir), "--module", "commonjs",
             "--target", "es2020", "--skipLibCheck", "--noEmitOnError"],
            check=True, capture_output=True)
        compiled = sorted(out_dir.rglob("presentationState.js"))
        assert compiled, "the mapping module did not compile"
        return compiled[0]

    def _resolve(self, compiled, detail: Dict[str, Any],
                 dossier: Dict[str, Any]) -> Dict[str, Any]:
        driver = Path(compiled).parent / "r454_spec.json"
        driver.write_text(json.dumps({
            "require": str(compiled), "detail": detail,
            "dossier": dossier}))
        runner = Path(compiled).parent / "r454_drive.js"
        runner.write_text(
            "const fs = require('fs');\n"
            "const spec = JSON.parse(fs.readFileSync(process.argv[2]));\n"
            "const ps = require(spec.require);\n"
            "const view = ps.resolvePresentationState(spec.detail,\n"
            "  spec.dossier);\n"
            "console.log(JSON.stringify(view));\n")
        proc = subprocess.run(["node", str(runner), str(driver)],
                              capture_output=True, text=True, check=True)
        return json.loads(proc.stdout.strip().splitlines()[-1])

    def _contradiction_payload(self, status="RUN_BLOCKED_TRANSPORT"):
        """The directive's EXACT contradiction: a maximally convincing
        stale projection (every scientific-looking field positive, the
        full visual chain complete, the ENGINEERING authority recorded)
        riding on a transport-blocked terminal run. Returns the
        (detail, dossier) pair."""
        detail = {
            "status": status, "final_status": None,
            "user_state_view": {
                "user_state": "COMPLETED_CANDIDATE",
                "finished": True, "found_something": True,
                "rejected": False, "package_available": True,
                "outcome": "INVENTION_SURVIVED",
                "outcome_label": "stale scientific outcome label"},
            "run_state": None}
        dossier = {"tabs": {"design": {
            "availability": "AVAILABLE",
            "geometry_state": "visual_complete",
            "engineering_authority": "ENGINEERING",
            "engineering_geometry_ready": True,
            "visual_input_ready": True,
            "renders": {"status": "OK",
                        "visual_gate": {"verdict": "COMPLETE_PASS"}},
        }, "evidence": None}}
        return detail, dossier

    def test_the_exact_fixture_resolves_infrastructure_paused(
            self, compiled_mapping):
        view = self._resolve(compiled_mapping,
                             *self._contradiction_payload())
        assert view["state"] == "INFRASTRUCTURE_PAUSED"
        assert view["infrastructurePaused"] is True
        # no ready surface, no viewer mount, no engineering claim
        assert view["state"] != "VISUAL_READY"
        assert "glbReadyButRenderBlocked" not in view
        assert view.get("engineeringAuthority") is None
        assert view["blocked"]["verdictLine"] == \
            "No scientific conclusion was reached."

    def test_the_transport_family_holds_without_the_projection(
            self, compiled_mapping):
        # the canonical status alone is the transport authority — the
        # family holds even with NO user_state_view at all
        for status in ("RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_ENGINE"):
            detail = {"status": status, "final_status": None,
                      "user_state_view": None, "run_state": None}
            view = self._resolve(compiled_mapping, detail, {"tabs": None})
            assert view["state"] == "INFRASTRUCTURE_PAUSED", status

    def test_stale_infrastructure_user_state_holds_even_complete(
            self, compiled_mapping):
        # the projection-side authority: a stale COMPLETED_CANDIDATE
        # payload whose recorded user_state is an INFRASTRUCTURE state
        # can never become a ready surface either
        detail, dossier = self._contradiction_payload(status="COMPLETE")
        detail["user_state_view"]["user_state"] = "BLOCKED_TRANSPORT"
        view = self._resolve(compiled_mapping, detail, dossier)
        assert view["state"] == "INFRASTRUCTURE_PAUSED"

    def test_negative_control_valid_chain_still_reaches_visual_ready(
            self, compiled_mapping):
        """Art. V — the positive control: the SAME fully-valid chain
        without the transport-terminal status must still reach
        VISUAL_READY (the fixture must pass because of the authority
        rule, never because the mapping broke)."""
        detail, dossier = self._contradiction_payload(status="COMPLETE")
        view = self._resolve(compiled_mapping, detail, dossier)
        assert view["state"] == "VISUAL_READY"
        assert view["infrastructurePaused"] is False
        assert view["engineeringAuthority"] == "ENGINEERING"


# ---------------------------------------------------------------------------
# §2 — the dead candidate is never bridged (bridge_gate)
# ---------------------------------------------------------------------------
class TestDeadCandidateNeverBridges:
    @pytest.fixture()
    def killed_run(self, tmp_path, monkeypatch):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "INVENTION_LINEAGE.json").write_text(
            json.dumps(_killed_lineage()))
        session = _killed_session(run_dir)
        detail = {"run_state": {"generations": {
            "generations": _killed_lineage()["generations"]}}}
        monkeypatch.setattr(store, "get_session",
                            lambda sid: dict(session))
        monkeypatch.setattr(store, "update_session",
                            lambda sid, **f: dict(session))
        monkeypatch.setattr(store, "session_detail", lambda sid: detail)
        launched = []
        monkeypatch.setattr(aw, "enqueue", lambda sid, **kw:
                            launched.append((sid, kw)) or {})
        return {"run_dir": run_dir, "session": session,
                "launched": launched}

    def test_terminal_outcome_reads_the_kill(self, killed_run):
        outcome = run_state_mod.terminal_outcome(
            killed_run["session"], killed_run["run_dir"])
        assert outcome["outcome"] == \
            run_state_mod.OUTCOME_KILLED_BY_CHALLENGE
        assert outcome.get("invention_found") is False

    def test_gate_records_dead_candidate_and_spends_nothing(
            self, killed_run):
        gate = bridge_gate.ensure_artifacts("ts_r454_dead")
        assert gate["outcome"] == "DEAD_CANDIDATE_NO_ARTIFACTS"
        assert gate["case"] == "DEAD"
        assert gate["canonical_outcome"] == \
            run_state_mod.OUTCOME_KILLED_BY_CHALLENGE
        assert gate.get("outcome_basis")
        # the kill basis is the lineage's own verdict, recorded
        assert "challenge KILLED" in gate["outcome_basis"] or \
            "KILLED" in gate["outcome_basis"]
        # nothing was built, nothing was enqueued
        assert killed_run["launched"] == []
        assert not (killed_run["run_dir"] / "MODEL").exists()
        assert not list(killed_run["run_dir"].glob("*.zip"))
        # the record is the persisted authority (read back from disk)
        report = json.loads(
            (killed_run["run_dir"] / "BRIDGE_REPORT.json").read_text())
        assert report["outcome"] == "DEAD_CANDIDATE_NO_ARTIFACTS"
        assert report["reviewer_provenance"] == "AI_REVIEW"

    def test_idempotent_reread_never_rewrites_history(self, killed_run):
        first = bridge_gate.ensure_artifacts("ts_r454_dead")
        # a second call returns the PRIOR report (idempotent contract)
        second = bridge_gate.ensure_artifacts("ts_r454_dead")
        assert second["outcome"] == first["outcome"] == \
            "DEAD_CANDIDATE_NO_ARTIFACTS"

    def test_surviving_and_blocked_runs_keep_their_contract(
            self, tmp_path, monkeypatch):
        """Art. V positive controls — the hold is narrow:
        survived / requires-experiment / under-development / blocked /
        pending runs are NOT dead (Art. LXI, BS-010) and the gate must
        proceed past the liveness check for them."""
        run_dir = tmp_path / "alive"
        run_dir.mkdir()
        (run_dir / "INVENTION_LINEAGE.json").write_text(
            json.dumps(_survivor_lineage()))
        session = {
            "session_id": "ts_r454_alive", "status": "COMPLETE",
            "final_status": "EVOLVED_INVENTION_CANDIDATE",
            "run_dir": str(run_dir), "user_text": "a live candidate"}
        detail = {"run_state": {"generations": {
            "generations": _survivor_lineage()["generations"]}}}
        monkeypatch.setattr(store, "get_session",
                            lambda sid: dict(session))
        monkeypatch.setattr(store, "update_session",
                            lambda sid, **f: dict(session))
        monkeypatch.setattr(store, "session_detail", lambda sid: detail)
        monkeypatch.setattr(aw, "enqueue", lambda sid, **kw: {})
        outcome = run_state_mod.terminal_outcome(session, run_dir)
        assert outcome["outcome"] != \
            run_state_mod.OUTCOME_KILLED_BY_CHALLENGE
        # the gate proceeds PAST the dead-candidate check (its outcome
        # is whatever the bridge contract produces — never the hold)
        gate = bridge_gate.ensure_artifacts("ts_r454_alive")
        assert gate["outcome"] != "DEAD_CANDIDATE_NO_ARTIFACTS"

    def test_escape_hatch_is_the_explicit_invocation(self):
        """SOURCE PIN (§2 escape hatch): the hold lives ONLY in the
        automatic paths — auto_enqueue and ensure_artifacts. The
        explicit `enqueue` entry (enqueued_by="api", the audit-artifact
        case) and INTERRUPTED-job recovery never consult it."""
        worker_src = (REPO / "toscanini" / "artifact_worker.py"
                      ).read_text()
        # exactly two call sites: the guard's own body + auto_enqueue
        assert worker_src.count("dead_candidate_hold(") == 2
        enqueue_start = worker_src.index("def enqueue(")
        enqueue_end = worker_src.index("\ndef ", enqueue_start + 1)
        assert "dead_candidate_hold" not in \
            worker_src[enqueue_start:enqueue_end]
        recover_start = worker_src.index("def recover_interrupted_jobs(")
        recover_end = worker_src.index("\ndef ", recover_start + 1)
        assert "dead_candidate_hold" not in \
            worker_src[recover_start:recover_end]
        gate_src = (REPO / "toscanini" / "bridge_gate.py").read_text()
        # the gate consults it exactly once, before any build work
        assert gate_src.count("_dead_candidate_outcome(") == 2  # def+call


# ---------------------------------------------------------------------------
# §2 — the dead candidate is never auto-rendered (artifact_worker)
# ---------------------------------------------------------------------------
class TestDeadCandidateNeverAutoRenders:
    def _held_session(self, run_dir: Path) -> Dict[str, Any]:
        return _killed_session(run_dir)

    def test_hold_fires_for_killed_and_only_killed(
            self, tmp_path, monkeypatch):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "INVENTION_LINEAGE.json").write_text(
            json.dumps(_killed_lineage()))
        session = self._held_session(run_dir)
        held = aw.dead_candidate_hold(session)
        assert held is not None
        assert held["outcome"] == \
            run_state_mod.OUTCOME_KILLED_BY_CHALLENGE
        # a blocked run with a GLB is NOT dead (Art. LXI): its render
        # followup stays live — the pixels are geometry truth, the
        # INFRASTRUCTURE_PAUSED surface comes from the status
        blocked = dict(session, status="RUN_BLOCKED_TRANSPORT",
                       final_status=None)
        assert aw.dead_candidate_hold(blocked) is None
        # under-development is NOT dead (BS-010: never a rejection)
        unverified = dict(session)
        (run_dir / "INVENTION_LINEAGE.json").write_text(json.dumps({
            "generations": [{"gen": 1, "challenge": {"killed": False},
                             "evidence_verified": False}],
            "current_invention": {"gen": 1}, "survivor_reached": True}))
        assert aw.dead_candidate_hold(unverified) is None

    def test_auto_enqueue_holds_and_records_the_decision(
            self, tmp_path, monkeypatch):
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        (run_dir / "INVENTION_LINEAGE.json").write_text(
            json.dumps(_killed_lineage()))
        session = self._held_session(run_dir)
        # a render WAS owed (GLB present, artifacts missing, job spoke
        # already) — the hold, not the queue, is the outcome
        monkeypatch.setattr(store, "get_session",
                            lambda sid: dict(session))
        monkeypatch.setattr(aw, "renderables_present",
                            lambda s: True)
        monkeypatch.setattr(aw, "render_artifacts_complete",
                            lambda s: False)
        monkeypatch.setattr(aw, "job_record", lambda sid: None)
        enqueued = []
        monkeypatch.setattr(aw, "enqueue",
                            lambda sid, **kw: enqueued.append(1) or {})
        decision = aw.auto_enqueue("ts_r454_dead",
                                   enqueued_by="production_worker")
        assert decision is not None
        assert decision["status"] == "HELD_DEAD_CANDIDATE"
        assert decision["held_outcome"] == \
            run_state_mod.OUTCOME_KILLED_BY_CHALLENGE
        assert decision.get("held_basis")
        # the queue was never touched
        assert enqueued == []

    def test_explicit_enqueue_remains_the_audit_artifact_escape(
            self, tmp_path, monkeypatch):
        """The escape hatch is structural: an EXPLICIT enqueue on a
        killed run still enqueues (deliberate invocation = the audit-
        artifact case the directive allows). The enqueue entry itself
        performs no liveness gating — proven live with the spawn
        intercepted."""
        run_dir = tmp_path / "run"
        run_dir.mkdir()
        session = self._held_session(run_dir)
        monkeypatch.setattr(store, "get_session",
                            lambda sid: dict(session))
        monkeypatch.setattr(aw, "job_record", lambda sid: None)
        captured = {}

        class _FakeProc:
            pid = 424242

        def _fake_spawn(sid: str):
            captured["spawned"] = sid
            return _FakeProc()

        monkeypatch.setattr(aw, "_spawn_job", _fake_spawn)
        monkeypatch.setattr(store, "_proc_stat_starttime",
                            lambda pid: "1")
        monkeypatch.setattr(aw, "_write_job",
                            lambda sid, rec: captured.update(
                                {"written": rec}) or rec)
        rec = aw.enqueue("ts_r454_dead", enqueued_by="api")
        assert captured.get("spawned") == "ts_r454_dead"
        assert rec.get("enqueued_by") == "api"
        assert rec.get("status") == "RUNNING"


# ---------------------------------------------------------------------------
# §3 — unknown pipeline status stays unknown (the strip)
# ---------------------------------------------------------------------------
class TestUnknownPipelineStatusStaysUnknown:
    def test_strip_source_pins(self):
        src = (WEBAPP / "components" / "DiscoveryPipelineStrip.tsx"
               ).read_text()
        # NOT_REACHED maps to its own class — and is enumerated
        # EXPLICITLY, so the default branch can never swallow it
        assert 'case "NOT_REACHED":' in src
        assert 'return "unreached";' in src
        # the default branch is the UNKNOWN class, never unreached
        default_idx = src.index("default:")
        block = src[default_idx:src.index("}", default_idx)]
        assert 'return "unknown";' in block
        assert 'return "unreached";' not in block
        # an unknown status renders a distinct mark, never the
        # not-reached dash
        assert 'STATUS_MARK[row.status] ?? "?"' in src

    def test_css_carries_the_unknown_class(self):
        css = (WEBAPP / "app" / "globals.css").read_text()
        assert ".pr-unknown .pipeline-mark" in css
        # it is visually distinct from the unreached rule (its own
        # block, italic — a state the reader can tell apart)
        assert css.count(".pr-unknown") >= 2


# ---------------------------------------------------------------------------
# §6 — provenance: the renderer identity rides EVERY record path
# ---------------------------------------------------------------------------
class TestRendererIdentityOnEveryRecordPath:
    def test_compiler_records_binary_resolution_before_every_exit(self):
        """SOURCE PIN: binary_resolution is recorded on the early
        renderer-skip path AND merged from run_renderer (which sets it
        before its own skip/fail branches) on every other path — the
        binary identity is part of every record (Art. VI)."""
        src = (REPO / "discovery_fabric" / "engine" / "visual_compiler"
               / "visual_compiler.py").read_text()
        early = src.index('record["binary_resolution"] = '
                          "_rw.last_resolution()")
        skip_branch = src.index("if not _rw.find_node()")
        assert skip_branch < early < src.index("record[\"source_glb\"]")
        # run_renderer sets the identity BEFORE its own branches
        rw = (REPO / "discovery_fabric" / "engine" / "visual_compiler"
              / "render_worker.py").read_text()
        set_idx = rw.index('record["binary_resolution"] = '
                           "last_resolution()")
        branch_idx = rw.index("if not node or not chrome:")
        assert set_idx < branch_idx
        # the success path merges the FULL subprocess record (which
        # carries renderer_stack + binary_resolution) into the record
        assert 'record.update({k: v for k, v in rec.items() ' \
               'if k != "stage"})' in src

    def test_schema_requires_source_identity_on_success(self):
        from discovery_fabric.engine.visual_compiler import \
            render_record_schema as schema
        # the exact input hash + artifact inventory are REQUIRED on a
        # succeeded record (Art. VI/LXII — exact input hashes)
        for field in ("source_glb", "source_glb_sha256", "artifacts",
                      "missing_artifacts"):
            assert field in schema.SUCCEEDED_REQUIRED

    def test_lab_sidecar_pins_visual_model_identity(self):
        """The Hunyuan/DA3-class producers: the canonical provenance
        helper pins the model revision + license + hardware/job
        identity + exact input/output hashes, and every generated
        artifact is NONE_PRESENTATION_ONLY (never engineering-
        authoritative — Art. XXVIII; the Coder 2 boundary)."""
        import importlib.util
        import sys
        lab_benchmark = REPO / "visual-lab" / "benchmark"
        sys.path.insert(0, str(lab_benchmark))
        try:
            spec = importlib.util.spec_from_file_location(
                "r454_lab_provenance",
                lab_benchmark / "provenance.py")
            provenance = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(provenance)  # noqa: E402
        finally:
            sys.path.remove(str(lab_benchmark))
        # the visual-model identity + runtime identity + exact inputs
        for field in ("model_id", "model_revision", "model_license",
                      "hf_space_or_job", "hardware", "input_hash",
                      "output_hash", "source_glb_sha"):
            assert field in provenance.REQUIRED_FIELDS
        # presentation-only is structural: any other engineering
        # authority on a GENERATED artifact is a typed error
        record = provenance.make_sidecar(
            source_glb_sha="sha256:" + "a" * 64,
            model_id="tencent/Hunyuan3D-Omni", model_revision="abc",
            model_license="license:other", hf_space_or_job="job-x",
            hardware="cpu-8gb", input_hash="sha256:" + "b" * 64,
            output_hash="sha256:" + "c" * 64, timestamp="t",
            benchmark_version=provenance.BENCHMARK_VERSION,
            visual_role="PRESENTATION_CANDIDATE")
        assert record["engineering_authority"] == "NONE_PRESENTATION_ONLY"
        with pytest.raises(provenance.ProvenanceError):
            record2 = dict(record)
            record2["engineering_authority"] = "ENGINEERING"
            provenance.validate(record2)
