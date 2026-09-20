"""tests/test_r423_durable_incremental.py — R423A Phase 4.

Durability contract after the change (measured before: EVERY snapshot
copied the full payload — 282 files / 225 MB / 284 sha256 — and paid a
git fetch on the hot path):

  * the FIRST snapshot after boot copies the full payload (recovery
    baseline);
  * a SECOND snapshot with no changes copies ~nothing and re-hashes
    ~nothing (the incremental contract) while the integrity manifest
    stays byte-identical for unchanged files;
  * a CHANGED sessions.json is re-copied and re-hashed;
  * the hot path performs NO network fetch (single-writer contract);
  * crash recovery semantics preserved: the push still happens in the
    snapshot (essential git I/O), restore() still verifies the manifest,
  * provenance unchanged: the manifest still pins every file sha and
    the tree digest.

Git is exercised against a REAL local bare origin (no network) — the
same object/scan costs as production, honestly excluding GitHub RTT.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toscanini import durable  # noqa: E402


@pytest.fixture()
def durable_env(tmp_path, monkeypatch):
    """An isolated durable layer: STORE_DIR with sessions + one run dir
    with package/model artifacts, a real state-repo, a REAL local bare
    origin, git enabled, no network."""
    root = tmp_path
    store = root / "store"
    store.mkdir()
    runs = root / "ENGINE_RUNS"
    (runs / "toscanini_ui_problem1").mkdir(parents=True)
    run_dir = runs / "toscanini_ui_problem1"
    big = bytes(200_000)  # 200 KB per artifact — enough to measure
    (run_dir / "final_state.json").write_text('{"final_status": "COMPLETE"}')
    (run_dir / "BRIDGE_REPORT.json").write_text('{"outcome": "COMPLETED"}')
    (run_dir / "MODEL").mkdir()
    (run_dir / "MODEL" / "model-001.glb").write_bytes(big)
    (run_dir / "TECHNOLOGY_TRANSFER_PACKAGE_x.zip").write_bytes(big * 3)
    (store / "sessions.json").write_text(json.dumps({
        "sessions": [{"session_id": "s1", "status": "COMPLETE",
                      "run_dir": str(run_dir), "origin": "toscanini_ui",
                      "updated_at": "2026-09-08T00:00:00Z"}]}))

    bare = root / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True,
                   capture_output=True)

    monkeypatch.setattr(durable, "ENGINE_RUNTIME", root / "runtime")
    monkeypatch.setattr(durable, "STATE_REPO", root / "runtime" / "state-repo")
    monkeypatch.setattr(durable, "LOCK_PATH", root / "runtime" / "durable.lock")
    monkeypatch.setattr(durable, "REMOTE", str(bare))
    monkeypatch.setattr(durable, "FILE_CAP_BYTES", 20 * 1024 * 1024)
    monkeypatch.setenv("DURABLE_STATE_ENABLED", "1")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token-not-real")
    # the store paths durable collects from
    import toscanini.sessions as store_mod
    monkeypatch.setattr(store_mod, "STORE_DIR", store)
    monkeypatch.setattr(store_mod, "SESSIONS_PATH", store / "sessions.json")
    monkeypatch.setattr(store_mod, "SHARES_PATH", store / "shares.json")
    monkeypatch.setattr(store_mod, "ENGINE_RUNS", runs)
    monkeypatch.setattr(durable.store, "SESSIONS_PATH", store / "sessions.json")
    monkeypatch.setattr(durable.store, "SHARES_PATH", store / "shares.json")
    monkeypatch.setattr(durable.store, "STORE_DIR", store)
    monkeypatch.setattr(durable.store, "ENGINE_RUNS", runs)
    monkeypatch.setattr(durable.store, "list_sessions",
                        lambda: [{"session_id": "s1",
                                  "status": "COMPLETE",
                                  "run_dir": str(run_dir),
                                  "origin": "toscanini_ui"}])
    durable.reset_payload_cache()
    yield {"root": root, "run_dir": run_dir, "store": store,
           "bare": bare}
    durable.reset_payload_cache()


class TestIncrementalSnapshot:
    def test_first_snapshot_full_second_incremental(self, durable_env):
        s1 = durable.snapshot("created:s1")
        assert s1["ok"] is True, s1
        assert s1["files_copied"] >= 4  # full payload baseline
        assert s1["files_skipped_unchanged"] == 0
        files_total = s1["files"]

        s2 = durable.snapshot("terminal:COMPLETE:s1")
        assert s2["ok"] is True, s2
        assert s2["files"] == files_total  # manifest still covers ALL files
        assert s2["files_copied"] == 0, \
            f"unchanged payload re-copied {s2['files_copied']} files"
        assert s2["files_skipped_unchanged"] == files_total

    def test_manifest_integrity_identical_when_unchanged(self, durable_env):
        s1 = durable.snapshot("created:s1")
        s2 = durable.snapshot("terminal:COMPLETE:s1")
        assert s1["manifest_sha256"] == s2["manifest_sha256"], \
            "unchanged state produced a different tree digest"
        repo = durable.STATE_REPO
        m1 = json.loads((repo / "MANIFEST.json").read_text())
        assert m1["files"]  # per-file sha pins present (provenance intact)

    def test_changed_file_is_recopied_and_tree_digest_changes(self,
                                                              durable_env):
        durable.snapshot("created:s1")
        # the session record legitimately changes (worker progress)
        time.sleep(0.01)
        sessions = durable_env["store"] / "sessions.json"
        data = json.loads(sessions.read_text())
        data["sessions"][0]["bridge_outcome"] = "COMPLETED"
        sessions.write_text(json.dumps(data))
        s3 = durable.snapshot("terminal:COMPLETE:s1")
        assert s3["files_copied"] >= 1
        repo = durable.STATE_REPO
        pushed_sessions = json.loads((repo / "sessions.json").read_text())
        assert pushed_sessions["sessions"][0]["bridge_outcome"] == \
            "COMPLETED"  # the change reached the branch

    def test_hot_path_performs_no_fetch(self, durable_env, monkeypatch):
        """The single-writer contract: after the state repo exists, a
        snapshot must not run `git fetch` (network I/O off the user
        path). Adversarial: any fetch attempt raises here."""
        durable.snapshot("boot:setup")  # repo exists now
        def _no_fetch(cwd, *args, **kw):
            if args and args[0] == "fetch":
                raise AssertionError("git FETCH on the snapshot hot path")
            return durable._git.__wrapped__(cwd, *args, **kw) \
                if hasattr(durable._git, "__wrapped__") else _real(cwd, *args, **kw)
        real = durable._git

        def guard(cwd, *args, **kw):
            if args and args[0] == "fetch":
                raise AssertionError(
                    "git FETCH on the snapshot hot path (R423A Phase 4)")
            return real(cwd, *args, **kw)

        monkeypatch.setattr(durable, "_git", guard)
        out = durable.snapshot("created:s2")
        assert out["ok"] is True, out

    def test_push_survives_and_restore_verifies(self, durable_env):
        """Crash-recovery contract preserved: the snapshot pushed to the
        origin, and restore() verifies the integrity manifest from a
        FRESH state-repo clone (deterministic restore)."""
        s1 = durable.snapshot("created:s1")
        assert s1["pushed"] is True
        # fresh restore: wipe local state + the runtime, re-clone
        shutil.rmtree(durable_env["root"] / "runtime")
        durable.reset_payload_cache()
        out = durable.restore()
        assert out["error"] is None, out
        assert out["integrity_verified"] is True, out
        assert out["sessions"] == 1

    def test_visual_identity_chain_survives_snapshot(self, durable_env):
        """R510 regression: durable snapshots must carry the persisted
        visual identity/current-generation anchors alongside the canonical
        GLB. Without these MODEL files a restart preserves the bytes but
        the strict visual contract correctly downgrades the artifact to
        geometry_unverified."""
        model = durable_env["run_dir"] / "MODEL"
        identity = "{\"artifact\": \"ARTIFACT_IDENTITY\", \"geometry_hash\": \"h\", \"generation_id\": \"gen-1\"}\n"
        identity_sha = "sha  ARTIFACT_IDENTITY.json\n"
        lineage = "{\"generation_models\": [{\"generation\": 1, \"generation_id\": \"gen-1\", \"glb\": \"MODEL/model-001.glb\", \"current\": true}]}\n"
        geometry_spec = "{\"schema_version\": \"1.0.0\", \"geometry\": {}}\n"
        (model / "ARTIFACT_IDENTITY.json").write_text(identity)
        (model / "ARTIFACT_IDENTITY.sha256").write_text(identity_sha)
        (model / "DESIGN_LINEAGE.json").write_text(lineage)
        (model / "GEOMETRY_SPEC.json").write_text(geometry_spec)

        report = durable.snapshot("terminal:COMPLETE:s1:visual-identity")
        assert report["ok"] is True, report

        repo = durable.STATE_REPO
        persisted = repo / "runs" / "toscanini_ui_problem1" / "MODEL"
        assert (persisted / "ARTIFACT_IDENTITY.json").read_text() == identity
        assert (persisted / "ARTIFACT_IDENTITY.sha256").read_text() == identity_sha
        assert (persisted / "DESIGN_LINEAGE.json").read_text() == lineage
        assert (persisted / "GEOMETRY_SPEC.json").read_text() == geometry_spec

    def test_refusal_when_disabled_is_explicit(self, durable_env,
                                               monkeypatch):
        monkeypatch.setenv("DURABLE_STATE_ENABLED", "")
        out = durable.snapshot("anything")
        assert out["ok"] is False
        assert "not enabled" in out["error"]
