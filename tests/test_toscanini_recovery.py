"""Hermetic tests — Toscanini service failure recovery (CEO directive #8:
transport reliability, queueing, RESUMABILITY, failure recovery).

Covers toscanini/sessions.py::mark_stuck_sessions / retry_session and the
server's /retry wiring semantics (tested at the store level; the endpoint
only re-exposes them).

Attack cases (Art. XVII):
- stuck detection must NOT fabricate research outcomes (ERROR_STUCK says
  'worker disappeared', never a science verdict — Art. XXV)
- COMPLETE verdicts must NOT be retryable (append-only history)
- retry keeps the error history (last_error) and counts attempts
- fresh RUNNING sessions must NOT be marked stuck
"""

from __future__ import annotations

import importlib
import json
import time
from pathlib import Path

import pytest


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("toscanini.sessions.STORE_DIR", tmp_path)
    monkeypatch.setattr("toscanini.sessions.SESSIONS_PATH",
                        tmp_path / "sessions.json")
    return importlib.import_module("toscanini.sessions")


def _mk(store, sid, status, age_hours=0.0, **extra):
    s = store.create_session("t", "some problem text long enough")
    data = json.loads(store.SESSIONS_PATH.read_text())
    for row in data["sessions"]:
        if row["session_id"] == s["session_id"]:
            row["session_id"] = sid
            row["status"] = status
            ts = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(time.time() - age_hours * 3600))
            row["created_at"] = ts
            row.pop("updated_at", None)
            row.update(extra)
    store.SESSIONS_PATH.write_text(json.dumps(data))


class TestStuckDetection:
    def test_old_running_marked_stuck(self, store):
        _mk(store, "ts_old", "RUNNING", age_hours=5)
        stuck = store.mark_stuck_sessions()
        assert stuck == ["ts_old"]
        s = store.get_session("ts_old")
        assert s["status"] == "ERROR_STUCK"
        assert "worker died or service restarted" in s["error"]

    def test_fresh_running_not_touched(self, store):
        _mk(store, "ts_new", "RUNNING", age_hours=0.1)
        assert store.mark_stuck_sessions() == []
        assert store.get_session("ts_new")["status"] == "RUNNING"

    def test_complete_never_marked_stuck(self, store):
        _mk(store, "ts_done", "COMPLETE", age_hours=48)
        assert store.mark_stuck_sessions() == []
        assert store.get_session("ts_done")["status"] == "COMPLETE"

    def test_stuck_is_infra_not_science(self, store):
        _mk(store, "ts_old2", "RUNNING", age_hours=4)
        store.mark_stuck_sessions()
        s = store.get_session("ts_old2")
        # the error message describes the WORKER, never a research verdict
        assert "REJECTED" not in s["error"]
        assert "SURVIVOR" not in s["error"]


class TestRetry:
    def test_error_session_requeueable(self, store):
        _mk(store, "ts_err", "ERROR_TRANSPORT", error="gateway down")
        out = store.retry_session("ts_err")
        assert out["status"] == "PENDING"
        assert out["error"] is None
        assert out["retry_attempts"] == 1
        assert out["last_error"] == "gateway down"  # history kept

    def test_complete_not_retryable(self, store):
        _mk(store, "ts_done2", "COMPLETE")
        out = store.retry_session("ts_done2")
        assert "error" in out
        assert "append-only" in out["error"]
        assert store.get_session("ts_done2")["status"] == "COMPLETE"

    def test_attempts_accumulate(self, store):
        _mk(store, "ts_e2", "ERROR_RUN", retry_attempts=2)
        out = store.retry_session("ts_e2")
        assert out["retry_attempts"] == 3

    def test_missing_session_none(self, store):
        assert store.retry_session("ts_ghost") is None

    def test_stuck_then_retry_lifecycle(self, store):
        _mk(store, "ts_cyc", "RUNNING", age_hours=6)
        store.mark_stuck_sessions()
        out = store.retry_session("ts_cyc")
        assert out["status"] == "PENDING"
        assert out["retry_attempts"] == 1
