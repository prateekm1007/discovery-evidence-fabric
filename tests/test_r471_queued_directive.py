"""tests/test_r471_queued_directive.py — R471: the external audit's
P1-2, closed and pinned.

THE MEASURED GAP (2026-09-16 external audit, red-team row "Steer while
running"): a steering request during a live run met a typed HTTP 409
RUN_IN_PROGRESS and the user's direction was LOST — "no queued intent;
collaboration is paused."

THE CONTRACT NOW:
  1. The refusal stays a refusal — no action is falsely applied
     mid-stage (the 409 contract is unchanged).
  2. The direction is RECORDED durably on the session as
     queued_directive {verb, params, directive, queued_at} + a durable
     snapshot; the 409 body gains queued=true + a plain note.
  3. Non-RUN_IN_PROGRESS refusals (unknown verb, pending answer) do
     NOT queue anything.
  4. The terminal surface offers the saved direction as the next
     action through the SAME canonical action endpoint (webapp
     present.ts deriveNextAction — pinned in the webapp suite).

Constitutional anchors: Art. XV (the queue is disclosed, never
silent), Art. XXV (a recorded intent is not an applied intent), the
R422 append-only rule (the child round is a NEW session when run).
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

from toscanini import actions as actions_mod  # noqa: E402
from toscanini import sessions as store  # noqa: E402

OWNER = "a1b2c3d4e5f6"


class _StoreHarness:
    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="r471_queue_")
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
        s = {"session_id": sid, "title": sid,
             "user_text": "make the desalination membrane cheaper to "
                          "manufacture at scale",
             "status": status,
             "created_at": "2026-09-16T00:00:00Z",
             "owner_key": OWNER, "worker_pid": None,
             "worker_starttime": None, "run_dir": None,
             "final_status": None, "package": None, "share_id": None,
             "error": None}
        s.update(extra)
        store.SESSIONS_PATH.write_text(json.dumps({"sessions": [s]}))
        return s


class TestQueueing:

    def _server(self, monkeypatch):
        from toscanini import server as sv

        monkeypatch.setattr(sv.Handler, "_spawn_worker",
                            lambda self, sid: None)

        class _Quiet(ThreadingHTTPServer):
            def handle_error(self, request, client_address):
                pass

        srv = _Quiet(("127.0.0.1", 0), sv.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        return srv

    def _post_action(self, srv, sid, action, params=None):
        conn = http.client.HTTPConnection(
            "127.0.0.1", srv.server_address[1], timeout=10)
        conn.request(
            "POST", f"/api/run/{sid}/actions",
            body=json.dumps({"action": action, "params": params or {}}),
            headers={"Content-Type": "application/json",
                     "X-Tosca-Owner": OWNER})
        resp = conn.getresponse()
        data = json.loads(resp.read() or b"{}")
        conn.close()
        return resp.status, data

    def test_run_in_progress_refusal_queues_the_direction(self,
                                                          monkeypatch):
        with _StoreHarness() as h:
            h.make("ts_live", "RUNNING", worker_pid=999995,
                   worker_starttime="1")
            srv = self._server(monkeypatch)
            try:
                code, body = self._post_action(
                    srv, "ts_live", "RESEARCH",
                    {"direction": "make it cheaper"})
                assert code == 409
                assert body["accepted"] is False
                assert body["code"] == "RUN_IN_PROGRESS"
                # THE AUDIT'S FIX: the direction is SAVED, and the
                # refusal says so
                assert body["queued"] is True
                assert "saved" in body["note"]
                s = store.get_session("ts_live")
                q = s["queued_directive"]
                assert q["verb"] == "RESEARCH"
                assert "make it cheaper" in q["directive"]
                assert q["queued_at"]
                # the status was NOT mutated — no false application
                assert s["status"] == "RUNNING"
            finally:
                srv.shutdown()
                srv.server_close()

    def test_unknown_verb_refusal_does_not_queue(self, monkeypatch):
        with _StoreHarness() as h:
            h.make("ts_unk", "RUNNING", worker_pid=999994,
                   worker_starttime="1")
            srv = self._server(monkeypatch)
            try:
                code, body = self._post_action(
                    srv, "ts_unk", "TELEPORT", {"direction": "x"})
                assert code == 409
                assert "queued" not in body
                assert "queued_directive" not in (
                    store.get_session("ts_unk"))
            finally:
                srv.shutdown()
                srv.server_close()

    def test_answer_pending_refusal_does_not_queue(self, monkeypatch):
        with _StoreHarness() as h:
            h.make("ts_wait", "AWAITING_CLARIFICATION",
                   clarification={"field": "observed_failure",
                                  "question": "failure or opportunity?"})
            srv = self._server(monkeypatch)
            try:
                code, body = self._post_action(
                    srv, "ts_wait", "RESEARCH", {"direction": "cheaper"})
                assert code == 409
                assert body["code"] == "ANSWER_PENDING"
                assert "queued" not in body
            finally:
                srv.shutdown()
                srv.server_close()

    def test_terminal_action_still_works_and_forks(self, monkeypatch):
        """The queued direction's execution path: on a terminal session
        the SAME endpoint accepts and opens the child round (the R467
        chain) — the queue surfaces, the canonical path executes."""
        with _StoreHarness() as h:
            h.make("ts_done", "COMPLETE", final_status="UNKNOWN",
                   run_dir=None)
            srv = self._server(monkeypatch)
            try:
                code, body = self._post_action(
                    srv, "ts_done", "RESEARCH",
                    {"direction": "use recycled materials"})
                assert code == 202
                assert body["accepted"] is True
                assert body["run_id"] and body["run_id"] != "ts_done"
                # the child carries the directive in its problem text
                child = store.get_session(body["run_id"])
                assert "use recycled materials" in child["user_text"]
                # the parent is untouched (append-only)
                assert store.get_session("ts_done")["status"] == "COMPLETE"
            finally:
                srv.shutdown()
                srv.server_close()

    def test_directive_text_carries_user_words(self):
        d = actions_mod.directive_text(
            "RESEARCH", {"direction": "make it cheaper"})
        assert "make it cheaper" in d
