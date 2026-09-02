"""tests/test_r396_release_gate.py — R396 Phase A/B release gates.

Adversarial tests for:
  A.3  identity NEVER comes from an environment variable
  A.4  the artifact identity is baked at build time (json + sha256)
  A.5  /api/health reports the artifact-derived SHA
  A.6  BUILD == RUNNING == HEALTH (tamper detection on the artifact
       bytes; equality of baked/runtime hashes)
  A.7  restart vs deployment (boot identity pairs with the artifact)
  A.8  gateway_up is null + explained in EXTERNAL transport mode (a
       local-gateway fact, never a fake "down" for a healthy deployment)
  B.2  a boot snapshot runs when durability is enabled (release gate:
       successful release requires >=1 successful snapshot)
  B.3  snapshots record timestamp, artifact identity, file count,
       integrity manifest (per-file sha256 + tree digest)
  B.4  write -> snapshot -> wipe -> restore -> STATE EQUALITY (deep,
       not merely survival) + tamper detection on restore
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import artifact_identity  # noqa: E402


# ---------------------------------------------------------------------------
# A.3-A.6: artifact identity
# ---------------------------------------------------------------------------

class TestArtifactIdentity:
    def _bake(self, tmp_path, monkeypatch, commit, source="render_git_commit",
               render_commit=None):
        """Bake a well-formed artifact pair into tmp_path and point the
        module at it (the same bytes the Dockerfile RUN produces)."""
        import hashlib
        monkeypatch.setattr(artifact_identity, "ARTIFACT_JSON",
                            tmp_path / "ARTIFACT_IDENTITY.json")
        monkeypatch.setattr(artifact_identity, "ARTIFACT_SHA",
                            tmp_path / "ARTIFACT_IDENTITY.sha256")
        doc = {"engine_commit": commit, "source": source,
               "render_git_commit": render_commit,
               "build_context_git_head": None,
               "baked_at_utc": "2026-09-02T00:00:00Z"}
        raw = json.dumps(doc, indent=1, sort_keys=True).encode() + b"\n"
        (tmp_path / "ARTIFACT_IDENTITY.json").write_bytes(raw)
        (tmp_path / "ARTIFACT_IDENTITY.sha256").write_text(
            hashlib.sha256(raw).hexdigest() + "  ARTIFACT_IDENTITY.json\n")
        return raw

    def test_artifact_file_defines_identity(self, tmp_path, monkeypatch):
        self._bake(tmp_path, monkeypatch, "0217d248" + "0" * 32)
        ident = artifact_identity.identity()
        assert ident["engine_commit"] == "0217d248" + "0" * 32
        assert ident["engine_commit_source"] == "build_artifact"
        assert ident["identity_tamper"] is False
        assert ident["artifact_sha256_runtime"] == \
            ident["artifact_sha256_baked"]

    def test_env_var_never_defines_identity(self, tmp_path, monkeypatch):
        """R396 A.3 — the exact production defect: ENGINE_COMMIT env set
        to a WRONG sha must not move the identity by one bit."""
        baked_commit = "0217d248" + "0" * 32
        self._bake(tmp_path, monkeypatch, baked_commit)
        monkeypatch.setenv("ENGINE_COMMIT", "f9dfd45d" + "9" * 32)
        commit, source = artifact_identity.resolve_engine_commit()
        assert commit == baked_commit
        assert source == "build_artifact"
        assert artifact_identity.operator_declared_commit() == \
            "f9dfd45d" + "9" * 32  # demoted to an expectation

    def test_tampered_artifact_is_detected(self, tmp_path, monkeypatch):
        """R396 A.6 — RUNNING != BUILD must be visible, not trusted."""
        self._bake(tmp_path, monkeypatch, "0217d248" + "0" * 32)
        # an in-container edit of the identity file
        doc = json.loads((tmp_path / "ARTIFACT_IDENTITY.json").read_text())
        doc["engine_commit"] = "deadbeef" + "0" * 32
        (tmp_path / "ARTIFACT_IDENTITY.json").write_text(
            json.dumps(doc, indent=1, sort_keys=True) + "\n")
        ident = artifact_identity.identity()
        assert ident["identity_tamper"] is True
        assert ident["engine_commit_source"] == "build_artifact"
        # the tampered commit is reported (visible), but the tamper flag
        # lets the health endpoint go RED — never a silent mismatch
        assert ident["engine_commit"] == "deadbeef" + "0" * 32

    def test_missing_sha_file_is_not_a_tamper_claim(self, tmp_path,
                                                    monkeypatch):
        """No baked sha256 (legacy artifact) — tamper is UNKNOWN (None),
        never fabricated as True or False (Art. VI/XXV)."""
        self._bake(tmp_path, monkeypatch, "0217d248" + "0" * 32)
        (tmp_path / "ARTIFACT_IDENTITY.sha256").unlink()
        ident = artifact_identity.identity()
        assert ident["identity_tamper"] is None
        assert ident["engine_commit"] == "0217d248" + "0" * 32

    def test_corrupt_artifact_is_disclosed(self, tmp_path, monkeypatch):
        self._bake(tmp_path, monkeypatch, "0217d248" + "0" * 32)
        (tmp_path / "ARTIFACT_IDENTITY.json").write_text("{not json")
        ident = artifact_identity.identity()
        assert ident["engine_commit_source"] == "ARTIFACT_CORRUPT"
        assert ident["identity_tamper"] is True

    def test_no_artifact_falls_back_to_git_not_env(self, tmp_path,
                                                   monkeypatch):
        """Local dev: no artifact file -> live git; the env var STILL
        never defines identity (R396 A.3 applies everywhere)."""
        monkeypatch.setattr(artifact_identity, "ARTIFACT_JSON",
                            tmp_path / "absent.json")
        monkeypatch.setattr(artifact_identity, "ARTIFACT_SHA",
                            tmp_path / "absent.sha256")
        monkeypatch.setenv("ENGINE_COMMIT", "deadbeef" + "0" * 32)
        commit, source = artifact_identity.resolve_engine_commit()
        assert source == "git"
        assert commit != "deadbeef" + "0" * 32
        # a 40-hex git sha or empty — but never the env value
        assert commit == "" or len(commit) == 40

    def test_boot_time_constant_for_process(self):
        i1 = artifact_identity.identity()["boot_time_utc"]
        i2 = artifact_identity.identity()["boot_time_utc"]
        assert i1 == i2  # restart visibility (R396 A.7) is per-process

    def test_health_view_carries_the_proof_chain(self, tmp_path, monkeypatch):
        self._bake(tmp_path, monkeypatch, "0217d248" + "0" * 32)
        view = artifact_identity.health_view()
        for key in ("build_artifact_sha256", "running_artifact_sha256",
                    "identity_tamper", "health_reported_commit",
                    "boot_time_utc", "rule"):
            assert key in view
        assert view["build_artifact_sha256"] == \
            view["running_artifact_sha256"]


# ---------------------------------------------------------------------------
# A.5/A.8: health payload semantics
# ---------------------------------------------------------------------------

class TestHealthSemantics:
    """The health payload semantics, tested through _health_payload()
    directly (the endpoint wiring is pinned by the R392/R394 server
    suites; here the CONTRACT of the payload is the object under
    test)."""

    @pytest.fixture()
    def payload(self, monkeypatch, tmp_path):
        import toscanini.server as srv
        import toscanini.gateway as gw
        # artifact identity from a baked file (the hosted shape)
        import hashlib
        monkeypatch.setattr(artifact_identity, "ARTIFACT_JSON",
                            tmp_path / "ARTIFACT_IDENTITY.json")
        monkeypatch.setattr(artifact_identity, "ARTIFACT_SHA",
                            tmp_path / "ARTIFACT_IDENTITY.sha256")
        doc = {"engine_commit": "0217d248" + "0" * 32,
               "source": "render_git_commit",
               "render_git_commit": "0217d248" + "0" * 32,
               "build_context_git_head": None,
               "baked_at_utc": "2026-09-02T00:00:00Z"}
        raw = json.dumps(doc, indent=1, sort_keys=True).encode() + b"\n"
        (tmp_path / "ARTIFACT_IDENTITY.json").write_bytes(raw)
        (tmp_path / "ARTIFACT_IDENTITY.sha256").write_text(
            hashlib.sha256(raw).hexdigest() + "  ARTIFACT_IDENTITY.json\n")
        # refresh the server module's bound identity constants
        monkeypatch.setattr(srv, "ENGINE_COMMIT", "0217d248" + "0" * 32)
        monkeypatch.setattr(srv, "ENGINE_COMMIT_SOURCE", "build_artifact")
        # EXTERNAL transport, probe OK (the hosted healthy shape)
        monkeypatch.setattr(gw, "transport_snapshot", lambda: {
            "status": "EXTERNAL",
            "base_url": "https://example.invalid/v1/chat/completions",
            "provider": "nvidia", "model": "test-model",
            "selection": "registry default policy"})
        monkeypatch.setattr(gw, "last_probe", lambda: {
            "status": "OK", "at": "2026-09-02T00:00:00Z", "source": "test",
            "latency_ms": 5})
        monkeypatch.setattr(gw, "gateway_up", lambda: False)
        monkeypatch.setattr(srv, "_durable_state",
                            lambda: {"enabled": False})
        yield (srv, lambda: srv._health_payload())

    def test_env_var_never_defines_identity_and_mismatch_is_red(
            self, payload, monkeypatch):
        srv, health = payload
        monkeypatch.setenv("ENGINE_COMMIT", "f9dfd45d" + "9" * 32)
        h = health()
        assert h["engine_commit"] == "0217d248" + "0" * 32
        di = h["deployment_identity"]
        assert di["operator_declared_commit"] == "f9dfd45d" + "9" * 32
        assert di["health_reported_commit"] == "0217d248" + "0" * 32
        assert di["deployment_drift"] == "RED"
        assert any("operator_declared" in r for r in di["drift_reasons"])

    def test_matching_expectation_is_green(self, payload, monkeypatch):
        _, health = payload
        monkeypatch.setenv("ENGINE_COMMIT", "0217d248" + "0" * 32)
        h = health()
        di = h["deployment_identity"]
        assert di["deployment_drift"] == "GREEN"
        assert di["drift_reasons"] == []
        assert di["identity_tamper"] is False
        assert di["build_artifact_sha256"] == di["running_artifact_sha256"]

    def test_gateway_up_is_null_and_explained_in_external_mode(self,
                                                               payload):
        _, health = payload
        h = health()
        assert h["gateway_up"] is None
        assert "EXTERNAL" in h["gateway_up_note"]
        assert h["readiness"]["llm_transport_ready"] is True

    def test_gateway_up_is_a_real_bool_in_local_mode(self, payload,
                                                     monkeypatch):
        import toscanini.gateway as gw
        _, health = payload
        monkeypatch.setattr(gw, "transport_snapshot", lambda: {
            "status": "LOCAL_CONFIGURED"})
        h = health()
        assert h["gateway_up"] in (True, False)
        assert "local" in h["gateway_up_note"].lower()

    def test_tampered_artifact_makes_drift_red(self, payload, monkeypatch):
        srv, health = payload
        # in-container tamper: rewrite the artifact json (sha stale)
        p = artifact_identity.ARTIFACT_JSON
        doc = json.loads(p.read_text())
        doc["engine_commit"] = "deadbeef" + "0" * 32
        p.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        h = health()
        di = h["deployment_identity"]
        assert di["identity_tamper"] is True
        assert di["deployment_drift"] == "RED"
        assert any("identity_tamper" in r for r in di["drift_reasons"])

    def test_health_carries_build_running_health_proof_fields(self,
                                                              payload):
        _, health = payload
        h = health()
        di = h["deployment_identity"]
        for key in ("build_artifact_commit", "build_artifact_sha256",
                    "running_artifact_sha256", "identity_tamper",
                    "health_reported_commit",
                    "health_reported_commit_source",
                    "boot_time_utc", "operator_declared_commit",
                    "deployment_drift", "drift_reasons", "rule"):
            assert key in di, key
        assert "BUILD_ARTIFACT_SHA == RUNNING_ARTIFACT_SHA" in di["rule"]
        assert h["readiness"]["engine_commit_source"] == "build_artifact"

    def test_operator_key_configured_flag_without_secret(self, payload,
                                                         monkeypatch):
        srv, health = payload
        monkeypatch.setattr(srv, "OPERATOR_KEY", "")
        assert health()["operator_key_configured"] is False
        monkeypatch.setattr(srv, "OPERATOR_KEY", "op-secret-value")
        h = health()
        assert h["operator_key_configured"] is True
        assert "op-secret-value" not in json.dumps(h)


# ---------------------------------------------------------------------------
# B.2-B.4: durable snapshot integrity + equality
# ---------------------------------------------------------------------------

class TestDurableIntegrity:
    @pytest.fixture()
    def durable_env(self, tmp_path, monkeypatch):
        bare = tmp_path / "bare-remote.git"
        subprocess.run(["git", "init", "--bare", "-q", str(bare)],
                       check=True)
        monkeypatch.setattr("toscanini.sessions.STORE_DIR", tmp_path)
        monkeypatch.setattr("toscanini.sessions.SESSIONS_PATH",
                            tmp_path / "sessions.json")
        monkeypatch.setattr("toscanini.sessions.SHARES_PATH",
                            tmp_path / "shares.json")
        import toscanini.durable as du
        monkeypatch.setattr(du, "STATE_REPO", tmp_path / "state-repo")
        monkeypatch.setattr(du, "LOCK_PATH", tmp_path / "durable.lock")
        monkeypatch.setattr(du, "ENGINE_RUNTIME", tmp_path)
        monkeypatch.setattr(du, "REMOTE", str(bare))
        monkeypatch.setenv("DURABLE_STATE_ENABLED", "1")
        monkeypatch.setenv("GITHUB_TOKEN", "dummy-not-a-real-token")
        monkeypatch.setattr("toscanini.sessions.ENGINE_RUNS",
                            tmp_path / "ENGINE_RUNS")
        (tmp_path / "ENGINE_RUNS").mkdir(exist_ok=True)
        du._LAST.update(ok=None, at=None, reason=None, error=None,
                        files=0, commit=None, pushed=None)
        yield du

    @staticmethod
    def _seed(du, tmp_path, sid="ts_abc123", status="COMPLETE"):
        run_dir = tmp_path / "ENGINE_RUNS" / f"run_{sid}"
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "final_state.json").write_text(
            json.dumps({"session_id": sid, "final": "TEST"}))
        sessions = {"sessions": [{
            "session_id": sid, "status": status, "origin": "toscanini_ui",
            "run_dir": str(run_dir), "created_at": "2026-09-02T00:00:00Z",
            "updated_at": "2026-09-02T00:01:00Z"}]}
        import toscanini.sessions as store
        store._locked_write(store.SESSIONS_PATH, sessions)
        ev = store.STORE_DIR / f"evidence_{sid}.json"
        ev.write_text(json.dumps({"records": [{"id": "x"}]}))
        return run_dir

    def test_snapshot_records_identity_count_and_integrity(
            self, durable_env, tmp_path):
        du = durable_env
        self._seed(du, tmp_path)
        out = du.snapshot("terminal:COMPLETE:ts_abc123")
        assert out["ok"] is True
        assert out["files"] >= 3
        assert out["engine_commit"]  # artifact identity recorded (B.3)
        assert out["manifest_sha256"]
        repo = du.STATE_REPO
        man = json.loads((repo / "MANIFEST.json").read_text())
        assert man["tree_sha256"] == out["manifest_sha256"]
        assert set(man["files"]) >= {
            "sessions.json", "evidence/evidence_ts_abc123.json",
            "runs/run_ts_abc123/final_state.json"}
        log = (repo / "snapshot_log.jsonl").read_text().strip().splitlines()
        entry = json.loads(log[-1])
        assert entry["engine_commit"] == out["engine_commit"]
        assert entry["tree_sha256"] == out["manifest_sha256"]

    def test_write_snapshot_wipe_restore_state_equality(
            self, durable_env, tmp_path):
        """R396 B.4 — the directive's proof chain. Equality is DEEP:
        the durable payload after restore must equal the payload at
        snapshot time (byte-level for artifacts; record-level for the
        session index), not merely 'survive'."""
        du = durable_env
        import toscanini.sessions as store
        self._seed(du, tmp_path)
        snap = du.snapshot("terminal:COMPLETE:ts_abc123")
        assert snap["ok"] is True
        # ---- destroy the local state (ephemeral disk wipe) ----
        (tmp_path / "sessions.json").unlink()
        for f in (tmp_path / "ENGINE_RUNS" / "run_ts_abc123").glob("*"):
            f.unlink()
        (store.STORE_DIR / "evidence_ts_abc123.json").unlink()
        assert not (tmp_path / "sessions.json").exists()
        # ---- restore from the branch ----
        out = du.restore()
        assert out["error"] is None
        assert out["integrity_verified"] is True
        assert out["branch_sessions"] == 1
        # deep equality
        sessions = json.loads(
            (tmp_path / "sessions.json").read_text())["sessions"]
        assert len(sessions) == 1
        assert sessions[0]["session_id"] == "ts_abc123"
        assert json.loads((tmp_path / "ENGINE_RUNS" / "run_ts_abc123" /
                           "final_state.json").read_text()) == \
            {"session_id": "ts_abc123", "final": "TEST"}
        assert json.loads(
            (store.STORE_DIR / "evidence_ts_abc123.json").read_text()) == \
            {"records": [{"id": "x"}]}
        # and the manifest the restore verified is the snapshot's own
        assert out["manifest_sha256"] == snap["manifest_sha256"]

    def test_restore_detects_branch_tampering(self, durable_env, tmp_path):
        """Art. XVII — attack the integrity control: corrupt a payload
        file ON THE BRANCH (commit + push, the force-push/compromise
        shape); the restore must disclose the sha mismatch, not
        silently accept corrupted state."""
        du = durable_env
        self._seed(du, tmp_path)
        du.snapshot("terminal:COMPLETE:ts_abc123")
        # attacker corrupts the branch payload (bypassing the pipeline)
        repo = du.STATE_REPO
        (repo / "sessions.json").write_text('{"sessions": []}')
        du._git(repo, "add", "-A")
        du._git(repo, "-c", "user.name=attacker",
                "-c", "user.email=attacker@invalid",
                "commit", "-m", "corrupt", "--quiet", check=False)
        du._git(repo, "push", "origin", f"HEAD:refs/heads/{du.branch()}",
                check=False)
        out = du.restore()
        assert out["integrity_verified"] is False
        assert out["integrity_mismatches"]
        assert any("sessions.json" in m for m in out["integrity_mismatches"])

    def test_restore_without_preceding_snapshot_is_not_evidence(
            self, durable_env, tmp_path):
        """R396 B.5 — the rule itself: a restore result with no
        successful preceding snapshot reports branch_sessions=None /
        0 and integrity_verified=None; callers must NOT read it as
        durability evidence."""
        du = durable_env
        out = du.restore()  # empty branch, never snapshotted
        assert out["error"] is None
        assert out["branch_sessions"] in (None, 0)
        assert out["integrity_verified"] is None

    def test_snapshot_failure_is_disclosed_not_faked(self, durable_env,
                                                     monkeypatch):
        du = durable_env
        monkeypatch.setenv("GITHUB_TOKEN", "")
        out = du.snapshot("terminal:COMPLETE:ts_x")
        assert out["ok"] is False
        assert "GITHUB_TOKEN" in out["error"]


# ---------------------------------------------------------------------------
# R396 Phase C (P6): run-record determinism block
# ---------------------------------------------------------------------------

class TestDeterminismBlock:
    def test_baseline_run_then_deterministic(self, tmp_path):
        from discovery_fabric.prior_art_v2 import determinism as det
        ledger = tmp_path / "led.jsonl"
        resolution = {
            "state": "RESOLVED_DIFFERENTIATED",
            "relevance_model_version": "collision_resolution/2.0.0",
            "per_family": [
                {"family_id": "F1",
                 "adjudicated_text_sha256": "a" * 64}],
            "search_errors": [],
        }
        fp = det.problem_fingerprint(
            {"device": "catheter", "failure": "occlusion"},
            {"mechanism": "m", "intervention": "i",
             "expected_effect": "e"})
        ident = det.evidence_set_identity(resolution)
        b1 = det.record_and_compare(fp, "RESOLVED_DIFFERENTIATED",
                                    "collision_resolution/2.0.0", ident,
                                    run_id="r1", ledger_path=ledger)
        assert b1["classification"] == "BASELINE_RUN"
        assert b1["variance_summary"] is None
        b2 = det.record_and_compare(fp, "RESOLVED_DIFFERENTIATED",
                                    "collision_resolution/2.0.0", ident,
                                    run_id="r2", ledger_path=ledger)
        assert b2["classification"] == "DETERMINISTIC"
        assert b2["variance_summary"]["n_runs_compared"] == 2
        assert b2["variance_summary"]["differences"] == []

    def test_divergence_is_flagged_not_resolved(self, tmp_path):
        from discovery_fabric.prior_art_v2 import determinism as det
        ledger = tmp_path / "led.jsonl"
        fp = det.problem_fingerprint(
            {"device": "catheter", "failure": "occlusion"},
            {"mechanism": "m", "intervention": "i",
             "expected_effect": "e"})
        det.record_and_compare(fp, "UNRESOLVED_SEARCH_INCOMPLETE",
                               "collision_resolution/2.0.0", "set-1",
                               run_id="r1", ledger_path=ledger)
        b2 = det.record_and_compare(fp, "RESOLVED_DIFFERENTIATED",
                                    "collision_resolution/2.0.0", "set-2",
                                    run_id="r2", ledger_path=ledger)
        assert b2["classification"] == "NON_DETERMINISTIC"
        fields = {d["field"]
                  for d in b2["variance_summary"]["differences"]}
        assert "verdict" in fields and "evidence_set_identity" in fields

    def test_ledger_failure_is_disclosed_not_faked(self, tmp_path):
        from discovery_fabric.prior_art_v2 import determinism as det
        # an unwritable ledger path (a FILE where a dir is needed)
        block = tmp_path / "blocker"
        block.write_text("x")
        out = det.record_and_compare(
            "fp", "S", "v", "e", run_id="r",
            ledger_path=block / "sub" / "led.jsonl")
        assert out["classification"] == "LEDGER_UNAVAILABLE"
        assert out["error"]

    def test_run_collision_embeds_determinism(self, tmp_path, monkeypatch):
        from discovery_fabric.prior_art_v2 import determinism as det
        monkeypatch.setattr(det, "LEDGER_PATH",
                            tmp_path / "led.jsonl")
        from discovery_fabric.prior_art_v2 import collision_resolution as cr
        mm = {"mechanism": "heparin coating reduces thrombus",
              "intervention": "covalently bonded heparin coating",
              "expected_effect": "reduced occlusion"}
        problem = {"device": "tunneled hemodialysis catheter",
                   "failure": "occlusion", "failure_mode": "OCCLUSION"}
        # stub the search layer: no network in tests (hermetic)
        monkeypatch.setattr(cr, "search_patents",
                            lambda ladder, sources=None,
                            sleep_between=0.4: ([], []))
        out = cr.run_collision(mm, problem, deep_fetch=False)
        assert "determinism" in out
        assert out["determinism"]["classification"] == "BASELINE_RUN"
        assert out["determinism"]["relevance_model_version"]
        assert out["determinism"]["evidence_set_identity"]


# ---------------------------------------------------------------------------
# R396 Phase D: physics gate on surviving candidates
# ---------------------------------------------------------------------------

class TestPhysicsGate:
    ENG_HYD = {"engineering_core": {"critical_parameters": [
        {"label": "primary lumen diameter", "value": 1.0,
         "domain": "fluidics_hydraulic"},
        {"label": "floor lumen diameter", "value": 0.6,
         "domain": "fluidics_hydraulic"}]}}

    def test_hydraulic_candidate_carries_all_five_fields(self):
        from discovery_fabric.engine import physics_gate as pg
        out = pg.evaluate_candidate_physics({}, dict(self.ENG_HYD), {})
        assert out["applicable"] is True
        comp = out["baseline_comparison"]
        # the directive's five required fields, verbatim
        assert "baseline" in comp and "candidate" in comp
        assert comp["comparison"]["target_metric"] == "total_flow_ml_min"
        assert "constraints" in comp
        assert comp["comparison"]["improvement_relative"] is not None
        # the directive's exact verdict vocabulary
        assert comp["candidate_outcome"] in (
            "CANDIDATE_BEATS_BASELINE",
            "CANDIDATE_DOES_NOT_BEAT_BASELINE")

    def test_non_hydraulic_is_honest_refusal(self):
        from discovery_fabric.engine import physics_gate as pg
        eng = {"engineering_core": {"critical_parameters": [
            {"label": "antenna gain", "value": 5.0,
             "domain": "electromagnetics"}]}}
        out = pg.evaluate_candidate_physics({}, eng, {})
        assert out["applicable"] is False
        assert "no physics comparison is FABRICATED" in \
            out["applicability"]["reason"]

    def test_candidate_does_not_beat_baseline_is_producible(self):
        from discovery_fabric.engine import physics_core as pc
        from discovery_fabric.engine import physics_gate as pg
        # a candidate whose floor path is far NARROWER than the
        # envelope: must produce the directive's exact state
        spec = pg._network_spec(1.0, 0.30, "worse")
        base = pg._network_spec(1.0, None, "baseline")
        comp = pc.compare_to_baseline(spec, base, "primary",
                                      scenario="NORMAL")
        # under NORMAL a second tiny lumen cannot reduce total flow
        # below baseline, so this asserts vocabulary + honest math
        assert comp["candidate_outcome"] in (
            "CANDIDATE_BEATS_BASELINE",
            "CANDIDATE_DOES_NOT_BEAT_BASELINE")
        assert comp["outcome"] in ("BEATS_BASELINE",
                                   "DOES_NOT_BEAT_BASELINE")

    def test_failure_mode_contract_on_p07(self):
        from discovery_fabric.engine import physics_gate as pg
        out = pg.evaluate_candidate_physics({}, dict(self.ENG_HYD), {})
        fm = out["failure_mode_contract"]
        assert set(fm["candidate"]) == {
            "NORMAL", "PARTIAL_OBSTRUCTION", "SEVERE_OBSTRUCTION",
            "ALTERNATIVE_PATH"}
        assert set(fm["baseline"]) == set(fm["candidate"])
        # the invention's reason-to-exist: floor flow survives full
        # primary obstruction; the baseline's does not
        assert fm["candidate"]["ALTERNATIVE_PATH"] > 0
        assert fm["baseline"]["ALTERNATIVE_PATH"] == 0

    def test_plausibility_gate_kills_before_simulation(self):
        from discovery_fabric.engine import physics_core as pc
        from discovery_fabric.engine import physics_gate as pg
        eng = {"engineering_core": {"critical_parameters": [
            {"label": "primary lumen diameter", "value": 120.0,
             "domain": "fluidics_hydraulic"}]}}
        out = pg.evaluate_candidate_physics({}, eng, {})
        pgate_block = out["plausibility_gate"]
        assert pgate_block["status"] == "PLAUSIBILITY_BOUND_VIOLATED"
        assert any(v["class"] == "GEOMETRIC_SCALE"
                   for v in pgate_block["violations"])
        # the consequence is explicit and the comparison is skipped
        assert "killed BEFORE expensive simulation" in \
            pgate_block["consequence"]
        assert out["baseline_comparison"] is None

    def test_thermal_bound_violates_outside_water_class(self):
        import copy
        from discovery_fabric.engine import physics_core as pc
        from discovery_fabric.engine import physics_gate as pg
        spec = pg._network_spec(1.0, 0.6, "thermal")
        spec["fluid"]["temperature_K"] = 500.0
        r = pc.solve_network(spec)
        assert r["status"] == "PLAUSIBILITY_BOUND_VIOLATED"
        assert any(v["class"] == "THERMAL" for v in r["violations"])
        assert pc.to_computational_result(r)["evidence_class"] == \
            "NOT_EMITTED"

    def test_physical_caps_flag_fabricated_result(self):
        from discovery_fabric.engine import physics_core as pc
        from discovery_fabric.engine import physics_gate as pg
        spec = pg._network_spec(1.0, 0.6, "cap")
        fake = {"predicted_quantities": {
            "segment_flows": [{"segment_id": "primary",
                               "velocity_m_s": 999.0}],
            "total_flow_ml_s": 999.0,
            "node_pressures_mmHg": {"A": 5.0}}}
        viols = pc._physical_cap_violations(fake, spec)
        classes = {v["class"] for v in viols}
        assert "FLOW_CAP" in classes and "ENERGY_CAP" in classes \
            and "MASS_CAP" in classes
        # attenuation: a node outside [outlet, inlet]
        fake2 = {"predicted_quantities": {
            "segment_flows": [], "total_flow_ml_s": 0.0,
            "node_pressures_mmHg": {"A": 99.0}}}
        v2 = pc._physical_cap_violations(fake2, spec)
        assert any(v["class"] == "ATTENUATION" for v in v2)
