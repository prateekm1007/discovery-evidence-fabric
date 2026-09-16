"""tests/test_r477_steering_contract.py — R477: the audit's P0 batch,
engine-side pins.

P0-1 (queued mid-run steer for ALL verbs): the audit's blocker said
"extend 1559-1589 to all verbs". The R471 queue already fires on every
RUN_IN_PROGRESS refusal — this battery pins the WHOLE verb surface, so
a future vocabulary change that drops a verb from the queue breaks a
test, not a user. Every computation verb AND the presentation verb:
  * refused typed (RUN_IN_PROGRESS) on a live run,
  * queued durably with the user's words in the directive,
  * the 409 body carrying queued=true + the saved-note receipt.

P0-4 (single NBA): the run contract's next_action projects the runtime
NBA controller record with its authority field — the one decision trace
the webapp now reads (the webapp suite pins the UI half).

Constitutional anchors: Art. XV (the queue is disclosed), Art. XXV (a
recorded intent is not an applied intent), Art. X (the contract is a
projection, never a second state store).
"""
from __future__ import annotations

import http.client
import json
import shutil
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import actions as actions_mod  # noqa: E402
from toscanini import sessions as store  # noqa: E402

OWNER = "a1b2c3d4e5f6"

# EVERY canonical verb the actions endpoint knows, computation and
# presentation alike (ASK/CLARIFY are separate endpoints by contract).
ALL_VERBS = sorted(
    actions_mod.COMPUTATION_VERBS | actions_mod.PRESENTATION_VERBS
)


class _StoreHarness:
    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="r477_steer_")
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

    def make(self, sid, status, run_dir=None, **extra):
        s = {"session_id": sid, "title": sid,
             "user_text": "make the desalination membrane cheaper to "
                          "manufacture at scale",
             "status": status,
             "created_at": "2026-09-16T00:00:00Z",
             "owner_key": OWNER, "worker_pid": None,
             "worker_starttime": None, "run_dir": run_dir,
             "final_status": None, "package": None, "share_id": None,
             "error": None}
        s.update(extra)
        cur = json.loads(store.SESSIONS_PATH.read_text() or "{}")
        sessions = cur.get("sessions", [])
        sessions.append(s)
        store.SESSIONS_PATH.write_text(
            json.dumps({"sessions": sessions}))
        return s


class TestAllVerbsQueue:

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

    @pytest.mark.parametrize("verb", ALL_VERBS)
    def test_every_verb_refused_mid_run_is_queued(self, monkeypatch,
                                                  verb):
        """THE P0-1 PIN: no verb's direction is lost on a live run."""
        with _StoreHarness() as h:
            sid = f"ts_live_{verb.lower()}"
            h.make(sid, "RUNNING", worker_pid=999995,
                   worker_starttime="1")
            srv = self._server(monkeypatch)
            try:
                code, body = self._post_action(
                    srv, sid, verb,
                    {"direction": f"steer words for {verb}"})
                assert code == 409, verb
                assert body["accepted"] is False, verb
                assert body["code"] == "RUN_IN_PROGRESS", verb
                # queued=true + the receipt note — the P0-1 acceptance
                assert body.get("queued") is True, verb
                assert "saved" in body.get("note", ""), verb
                # the durable record carries the user's words
                q = store.get_session(sid)["queued_directive"]
                assert q["verb"] == verb
                assert f"steer words for {verb}" in q["directive"]
                assert q["queued_at"]
                # no false application (Art. XXV)
                assert store.get_session(sid)["status"] == "RUNNING"
            finally:
                srv.shutdown()
                srv.server_close()

    def test_directive_text_is_nonempty_for_every_verb(self):
        """The queue's precondition — every verb renders a directive
        line, so a queue drop can never hide behind an empty text."""
        for verb in ALL_VERBS:
            d = actions_mod.directive_text(
                verb, {"direction": "the user's words"})
            assert d.startswith(f"[{verb}] "), verb
            assert "the user's words" in d, verb


class TestContractNBA:

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

    def _get(self, srv, path):
        conn = http.client.HTTPConnection(
            "127.0.0.1", srv.server_address[1], timeout=10)
        conn.request("GET", path, headers={"X-Tosca-Owner": OWNER})
        resp = conn.getresponse()
        raw = resp.read()
        conn.close()
        return resp.status, json.loads(raw or b"{}")

    def test_contract_projects_nba_record_with_authority(self, monkeypatch):
        """P0-4 engine half: the contract's next_action carries the NBA
        controller's preferred_action + the authority trace the webapp's
        single-NBA surface renders."""
        with _StoreHarness() as h:
            run_dir = Path(h.tmp) / "rd_nba"
            run_dir.mkdir()
            (run_dir / "NBA_CONTROLLER.json").write_text(json.dumps({
                "preferred_action": {
                    "action": "ATTACK_CANDIDATE",
                    "target_uncertainty": "load path",
                    "reason": "one untested load path",
                },
            }))
            h.make("ts_contract", "COMPLETE", run_dir=str(run_dir))
            srv = self._server(monkeypatch)
            try:
                code, body = self._get(
                    srv, "/api/run/ts_contract/contract")
                assert code == 200
                na = body.get("next_action")
                assert na, "next_action must ride the contract"
                assert na["action"] == "ATTACK_CANDIDATE"
                assert "NBA controller" in na.get("authority", "")
            finally:
                srv.shutdown()
                srv.server_close()

    def test_contract_without_records_holds_next_action_none(self,
                                                             monkeypatch):
        """Fail-open honesty: no NBA record -> next_action is None (the
        webapp falls back to its presentation derivation; the contract
        never invents one)."""
        with _StoreHarness() as h:
            run_dir = Path(h.tmp) / "rd_empty"
            run_dir.mkdir()
            h.make("ts_empty", "COMPLETE", run_dir=str(run_dir))
            srv = self._server(monkeypatch)
            try:
                code, body = self._get(
                    srv, "/api/run/ts_empty/contract")
                assert code == 200
                assert body.get("next_action") is None
            finally:
                srv.shutdown()
                srv.server_close()
