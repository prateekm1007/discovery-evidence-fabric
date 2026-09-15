"""tests/test_r471_retry_contract.py — R471: the external audit's P0-2
core-workflow failure, closed and pinned.

THE MEASURED FAILURE (2026-09-16 external audit, production): a worker
died during a deploy leaving its session stale-active; the retry
endpoint answered 409 "status 'PENDING' is not retryable" (a body the
auditor read as a pending-session shape), the frontend helper threw on
the non-2xx, and the advertised Resume path failed silently. The run
was unrecoverable from the product surface.

THE CONTRACT NOW (retry v2 — reconcile-then-retry, drafted by the
engineer Atria-Dawn-Preview, integrated with CTO corrections):

  1. A stale-active session whose worker is VERIFIABLY dead (recorded
     pid dead, or unregistered past the grace window) is reconciled to
     a typed INTERRUPTED and the retry is ACCEPTED.
  2. A LIVE worker is refused, typed WORKER_ALIVE — never interrupted,
     never double-spawned.
  3. A fresh spawn inside the registration grace is refused, typed
     REGISTRATION_GRACE_OPEN — a death the evidence does not show is
     never guessed (Art. XXV).
  4. COMPLETE stays append-only (typed COMPLETE_APPEND_ONLY).
  5. The route speaks the aligned contract: 202 + typed retry_id on
     acceptance; 409 with the typed reason vocabulary and NO
     session-shaped fields on refusal.

Constitutional anchors: Art. XVII (pid identity — a reused pid can
never masquerade), Art. XXV (honest interruption states), the R422
append-only rule (a completed verdict is history).
"""
from __future__ import annotations

import http.client
import json
import shutil
import sys
import tempfile
import threading
import time
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import sessions as store  # noqa: E402


class _StoreHarness:
    """Isolated STORE_DIR / ENGINE_RUNS (the R463/R465 discipline)."""

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="r471_retry_")
        tdp = Path(self.tmp)
        store_dir = tdp / "TOSCANINI_UI"
        runs = tdp / "ENGINE_RUNS"
        store_dir.mkdir()
        runs.mkdir()
        self._orig = (store.STORE_DIR, store.SESSIONS_PATH,
                      store.SHARES_PATH, store.ENGINE_RUNS)
        store.STORE_DIR = store_dir
        store.SESSIONS_PATH = store_dir / "sessions.json"
        store.SHARES_PATH = store_dir / "shares.json"
        store.ENGINE_RUNS = runs
        store.SESSIONS_PATH.write_text("{}")
        return self

    def __exit__(self, *a):
        (store.STORE_DIR, store.SESSIONS_PATH,
         store.SHARES_PATH, store.ENGINE_RUNS) = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, sid, status, **extra):
        s = {"session_id": sid, "title": sid, "user_text": "x" * 40,
             "status": status, "created_at": "2026-09-16T00:00:00Z",
             "owner_key": "a1b2c3d4e5f6", "worker_pid": None,
             "worker_starttime": None, "run_dir": None,
             "final_status": None, "package": None, "share_id": None,
             "error": None}
        s.update(extra)
        data = {"sessions": [s]}
        store.SESSIONS_PATH.write_text(json.dumps(data))
        return s

    def refresh(self, sid):
        return store.get_session(sid)


# ---------------------------------------------------------------------------
# store level — the state machine
# ---------------------------------------------------------------------------

class TestRetryV2Store:

    def test_error_retry_accepted_typed(self):
        with _StoreHarness() as h:
            h.make("ts_err", "ERROR_RUN", error="transport died")
            out = store.retry_session("ts_err")
            assert out.get("retryable") is not False  # accepted, typed
            assert out.get("error") is None           # the FIELD, cleared
            assert out["status"] == "PENDING"
            assert out["retry_attempts"] == 1
            assert out["last_error"] == "transport died"
            assert out["retry_id"].startswith("rt_")
            assert out["worker_pid"] is None

    def test_complete_refused_typed_append_only(self):
        with _StoreHarness() as h:
            h.make("ts_done", "COMPLETE", final_status="UNKNOWN")
            out = store.retry_session("ts_done")
            assert out["retryable"] is False
            assert out["reason"] == "COMPLETE_APPEND_ONLY"
            assert out["session_status"] == "COMPLETE"
            assert "error" in out and out["error"]

    def test_ghost_returns_none(self):
        with _StoreHarness():
            assert store.retry_session("ts_ghost") is None

    def test_the_audit_class_stale_pending_dead_pid_recovers(self):
        """The EXACT measured failure: a worker death during a deploy
        left the session PENDING with a dead pid — retry must now
        reconcile to INTERRUPTED and ACCEPT (never the 409 dead end)."""
        with _StoreHarness() as h:
            # a pid that is verifiably not running on this host
            h.make("ts_audit", "RUNNING", worker_pid=999999,
                   worker_starttime="1")
            out = store.retry_session("ts_audit")
            assert out.get("retryable") is not False  # accepted, typed
            assert out["status"] == "PENDING"
            assert out["retry_attempts"] == 1
            # the reconciliation typed the death honestly on the way in
            assert out["last_error"] and "pid 999999" in out["last_error"]

    def test_stale_pending_no_pid_past_grace_recovers(self):
        with _StoreHarness() as h:
            old = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ",
                time.gmtime(time.time() - 3600))  # 1h ago >> 10min grace
            h.make("ts_oldpend", "PENDING", created_at=old)
            out = store.retry_session("ts_oldpend")
            assert out.get("retryable") is not False  # accepted, typed
            assert out["status"] == "PENDING"
            assert "never registered" in (out["last_error"] or "")

    def test_fresh_pending_no_pid_refused_grace_open(self):
        with _StoreHarness() as h:
            now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            h.make("ts_fresh", "PENDING", created_at=now)
            out = store.retry_session("ts_fresh")
            assert out["retryable"] is False
            assert out["reason"] == "REGISTRATION_GRACE_OPEN"
            assert out["grace_minutes"] == store.PENDING_REGISTER_GRACE_MINUTES
            # and the session itself was NOT mutated
            s = h.refresh("ts_fresh")
            assert s["status"] == "PENDING"

    def test_live_worker_refused_typed(self):
        with _StoreHarness() as h:
            h.make("ts_live", "RUNNING", worker_pid=1,
                   worker_starttime=None)
            real_alive = store.worker_alive

            def _fake_alive(s):
                return True

            store.worker_alive = _fake_alive
            try:
                out = store.retry_session("ts_live")
            finally:
                store.worker_alive = real_alive
            assert out["retryable"] is False
            assert out["reason"] == "WORKER_ALIVE"
            assert h.refresh("ts_live")["status"] == "RUNNING"

    def test_awaiting_clarification_points_to_the_answer_path(self):
        with _StoreHarness() as h:
            h.make("ts_wait", "AWAITING_CLARIFICATION",
                   clarification={"field": "desired_outcome",
                                  "question": "observed failure or "
                                              "opportunity?"})
            out = store.retry_session("ts_wait")
            assert out["retryable"] is False
            assert out["reason"] == "AWAITING_ANSWER"

    def test_attempts_accumulate(self):
        with _StoreHarness() as h:
            h.make("ts_e2", "ERROR_RUN", retry_attempts=2)
            out = store.retry_session("ts_e2")
            assert out["retry_attempts"] == 3

    def test_reconcile_is_idempotent_and_typed(self):
        with _StoreHarness() as h:
            h.make("ts_rec", "PENDING", worker_pid=999998,
                   worker_starttime="1")
            first = store.reconcile_stale_active("ts_rec")
            assert first["status"] == "INTERRUPTED"
            second = store.reconcile_stale_active("ts_rec")
            # already terminal — returned unchanged, never re-typed
            assert second["status"] == "INTERRUPTED"
            assert second.get("retry_attempts") == first.get("retry_attempts")


# ---------------------------------------------------------------------------
# route level — the aligned HTTP contract (202 / typed 409)
# ---------------------------------------------------------------------------

class TestRetryRoute:

    def _server(self, monkeypatch):
        from toscanini import server as sv

        monkeypatch.setattr(sv.Handler, "_spawn_worker",
                            lambda self, sid: None)
        # forensics attach is fail-open in the route; keep the test
        # hermetic by making it a no-op (it never affects the contract)
        import toscanini.worker_forensics as wfx
        monkeypatch.setattr(wfx, "attach_session",
                            lambda sid, durable_root=None: _NoFx())

        class _NoFx:
            def event(self, *a, **k):
                return None

        class _Quiet(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass

        srv = _Quiet(("127.0.0.1", 0), sv.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    def _post(self, srv, path, owner="a1b2c3d4e5f6"):
        conn = http.client.HTTPConnection("127.0.0.1",
                                          srv.server_address[1],
                                          timeout=10)
        conn.request("POST", path, body="{}",
                     headers={"Content-Type": "application/json",
                              "X-Tosca-Owner": owner})
        resp = conn.getresponse()
        data = json.loads(resp.read() or b"{}")
        conn.close()
        return resp.status, data

    def test_accepted_retry_is_202_with_typed_retry_id(self, monkeypatch):
        with _StoreHarness() as h:
            h.make("ts_r202", "INTERRUPTED",
                   error="worker died during deploy")
            srv = self._server(monkeypatch)
            try:
                code, body = self._post(srv, "/api/sessions/ts_r202/retry")
                assert code == 202
                assert body["accepted"] is True
                assert body["session_id"] == "ts_r202"
                assert body["retry_id"].startswith("rt_")
                assert body["retry_attempts"] == 1
                assert body["status"] == "PENDING"
                # the session projection rides inside the body
                assert body["session"]["session_id"] == "ts_r202"
                assert h.refresh("ts_r202")["status"] == "PENDING"
            finally:
                srv.shutdown()
                srv.server_close()

    def test_refusal_is_409_typed_no_session_shape(self, monkeypatch):
        with _StoreHarness() as h:
            h.make("ts_r409", "COMPLETE", final_status="UNKNOWN")
            srv = self._server(monkeypatch)
            try:
                code, body = self._post(srv, "/api/sessions/ts_r409/retry")
                assert code == 409
                assert body["retryable"] is False
                assert body["reason"] == "COMPLETE_APPEND_ONLY"
                assert body["session_status"] == "COMPLETE"
                assert body["refusal"] == "RETRY_NOT_PERMITTED"
                assert body["error"]
                # THE AUDIT'S AMBIGUITY DEMAND: no session-shaped fields
                # in a refusal body — nothing that can be mistaken for
                # a live session record
                for session_field in ("session", "title",
                                      "user_text", "run_dir", "package"):
                    assert session_field not in body
            finally:
                srv.shutdown()
                srv.server_close()

    def test_the_audit_class_recovers_through_the_route(self, monkeypatch):
        """The deployed failure end-to-end: stale-active session, owner
        clicks Resume -> 202, PENDING, worker respawn requested."""
        with _StoreHarness() as h:
            h.make("ts_route_audit", "RUNNING", worker_pid=999997,
                   worker_starttime="1")
            srv = self._server(monkeypatch)
            spawned = []
            monkeypatch.setattr(
                srv.RequestHandlerClass, "_spawn_worker",
                lambda self, sid: spawned.append(sid))
            try:
                code, body = self._post(
                    srv, "/api/sessions/ts_route_audit/retry")
                assert code == 202
                assert body["accepted"] is True
                assert h.refresh("ts_route_audit")["status"] == "PENDING"
                assert spawned == ["ts_route_audit"]
            finally:
                srv.shutdown()
                srv.server_close()

    def test_wrong_owner_is_enumeration_safe_404(self, monkeypatch):
        with _StoreHarness() as h:
            h.make("ts_owned", "INTERRUPTED", error="x")
            srv = self._server(monkeypatch)
            try:
                code, _ = self._post(srv, "/api/sessions/ts_owned/retry",
                                     owner="someone_else")
                assert code == 404  # deny looks like absence
            finally:
                srv.shutdown()
                srv.server_close()
