"""tests/test_r447_owner_transport.py — the run-not-found fix battery.

The defect (operator report, R447): a user starts a run on the HuggingFace
Space and the workspace shows "Run not found … it belongs to a different
visitor … if the rail is empty, the run did not register". Root cause: HF
Spaces serve the app inside a third-party iframe on huggingface.co — the
tosca_owner cookie (SameSite=Lax, third-party context) is never stored nor
sent there, so EVERY browser request arrived as a NEW visitor; runs 404'd
and the history rail was empty while the runs existed on disk the whole
time (the BS-018 class: session/authorization continuity, not a stalled
discovery).

The fix: the SAME opaque owner capability travels via a SECOND transport
that does not depend on cookie policy —
  * run creation + /api/sessions responses carry the caller's own
    owner_key;
  * the client persists it and sends it as the X-Tosca-Owner header;
  * EventSource (no headers) carries it as the stream route's `owner`
    query parameter;
  * behind an HTTPS proxy the cookie is emitted SameSite=None; Secure;
    Partitioned (CHIPS) so Chromium-based embedded contexts keep it.

Constitutional basis:
- Art. XVI/XVII: the control is attacked here — the OLD failure mode is
  REPRODUCED as a negative control, and forged/oversized/mis-shaped
  tokens are attempted bypasses.
- Art. V: privacy is NOT weakened — a second visitor still gets the
  enumeration-safe 404; possession of the token IS the capability
  (identical semantics to the cookie, R394 s15).
- Art. LXI: an infrastructure state (blocked cookie) was never a
  scientific result — the fix separates them by making the capability
  transport survive the infrastructure.

Runs against a REAL handler instance (ThreadingHTTPServer on an
ephemeral port; the r423 precedent) with the session store pointed at a
temp file and the worker spawn stubbed (hermetic: no subprocess, no
network, no LLM).
"""
from __future__ import annotations

import http.client
import json
import re
import socket
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import sessions as store  # noqa: E402
from toscanini import server as srv  # noqa: E402

PROBLEM = ("Our offshore wind turbine gearbox suffers micropitting on the "
           "planet gears during low-load nights; find a mechanism that "
           "reduces it without redesigning the gearbox.")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture(scope="module")
def server(tmp_path_factory):
    """A real HTTP handler with the session store in a temp dir and the
    discovery worker spawn stubbed (route semantics only — the worker
    itself is out of scope for this battery)."""
    tmp = tmp_path_factory.mktemp("r447_owner")
    sessions_path = tmp / "sessions.json"
    shares_path = tmp / "shares.json"

    real_sessions, real_shares = store.SESSIONS_PATH, store.SHARES_PATH
    store.SESSIONS_PATH = sessions_path
    store.SHARES_PATH = shares_path

    from http.server import ThreadingHTTPServer

    class TestHandler(srv.Handler):
        def _spawn_worker(self, session_id: str) -> None:  # hermetic stub
            pass

    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), TestHandler)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    try:
        yield {"port": port, "sessions_path": sessions_path}
    finally:
        httpd.shutdown()
        httpd.server_close()
        store.SESSIONS_PATH, store.SHARES_PATH = real_sessions, real_shares


def _request(port, method, path, headers=None, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        payload = None
        hdrs = dict(headers or {})
        if body is not None:
            payload = json.dumps(body).encode()
            hdrs.setdefault("Content-Type", "application/json")
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, dict(resp.getheaders()), raw
    finally:
        conn.close()


def _json_body(raw: bytes):
    return json.loads(raw.decode("utf-8")) if raw else {}


def _start_run(port, headers=None):
    """POST /api/run as the given caller; returns (status, headers, json)."""
    return _request(port, "POST", "/api/run",
                    headers=headers, body={"text": PROBLEM})


class TestEmbeddedContextDefect:
    """THE decisive sequence: the exact browser conditions of the HF
    iframe (no cookie can persist), the old failure reproduced, then the
    second transport closing it."""

    def test_the_hf_iframe_sequence(self, server):
        port = server["port"]
        # 1. the browser starts a run; no cookie can be stored (embedded
        #    third-party context), so it sends nothing
        status, hdrs, raw = _start_run(port)
        assert status == 200
        payload = _json_body(raw)
        run_id = payload["session_id"]
        # the fix: the capability rides the response body as well
        owner_key = payload.get("owner_key")
        assert owner_key, "run creation must return the caller's owner_key"
        assert re.fullmatch(r"[0-9a-f]{8,64}", owner_key)
        # the Set-Cookie is still emitted (works wherever cookies are
        # allowed; the embedded browser just cannot keep it)
        set_cookie = hdrs.get("Set-Cookie", "")
        assert f"tosca_owner={owner_key}" in set_cookie

        # 2. THE OLD DEFECT, reproduced as the negative control: the
        #    next poll arrives with NO cookie (blocked) and NO header
        #    (the pre-fix client had none) -> 404 -> "Run not found"
        status, _, _ = _request(
            port, "GET", f"/api/run/{run_id}/result")
        assert status == 404

        # 3. the history rail under the same conditions: empty (the
        #    pre-fix browser could not identify itself either)
        status, _, raw = _request(port, "GET", "/api/sessions")
        assert status == 200
        assert _json_body(raw)["sessions"] == []

        # 4. THE FIX: the SAME caller presents the capability via the
        #    header the client persisted -> the run is visible
        status, _, raw = _request(
            port, "GET", f"/api/run/{run_id}/result",
            headers={"X-Tosca-Owner": owner_key})
        assert status == 200
        assert _json_body(raw)["session_id"] == run_id

        # 5. the history rail shows the run to the header caller
        status, _, raw = _request(
            port, "GET", "/api/sessions",
            headers={"X-Tosca-Owner": owner_key})
        assert status == 200
        body = _json_body(raw)
        assert any(s["session_id"] == run_id for s in body["sessions"])
        # and the rail response also carries the caller's own capability
        # (cookie-transport visitors converge to the header transport)
        assert body["owner_key"] == owner_key


class TestCapabilityContract:
    """Both run-creation API shapes carry the capability; the cookie and
    header transports converge."""

    def test_discovery_202_shape_carries_owner_key(self, server):
        port = server["port"]
        status, hdrs, raw = _request(
            port, "POST", "/api/discovery", body={"text": PROBLEM})
        assert status == 202
        payload = _json_body(raw)
        assert payload["run_id"]
        assert re.fullmatch(r"[0-9a-f]{8,64}",
                            payload.get("owner_key", ""))

    def test_header_converges_the_cookie(self, server):
        port = server["port"]
        status, hdrs, raw = _request(
            port, "GET", "/api/sessions",
            headers={"X-Tosca-Owner": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"})
        assert status == 200
        set_cookie = hdrs.get("Set-Cookie", "")
        assert "tosca_owner=a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6" in set_cookie

    def test_cookie_transport_still_works_first_party(self, server):
        port = server["port"]
        status, hdrs, raw = _start_run(port)
        owner_key = _json_body(raw)["owner_key"]
        # the first-party browser replays the cookie exactly as before
        status, _, raw = _request(
            port, "GET", "/api/sessions",
            headers={"Cookie": f"tosca_owner={owner_key}"})
        assert status == 200
        body = _json_body(raw)
        assert body["owner_key"] == owner_key

    def test_cookie_beats_header_stale_conflict(self, server):
        """Cookie wins over a stale header (the cookie is the stronger,
        browser-managed transport; the header only fills the gap)."""
        port = server["port"]
        status, hdrs, raw = _start_run(port)
        owner_key = _json_body(raw)["owner_key"]
        run_id = _json_body(raw)["session_id"]
        status, _, raw = _request(
            port, "GET", f"/api/run/{run_id}/result",
            headers={"Cookie": f"tosca_owner={owner_key}",
                     "X-Tosca-Owner": "0000000000000000000000000000dead"})
        assert status == 200


class TestPrivacyUnchanged:
    """R394 s15 intact: possession of the token IS the capability;
    denial stays the enumeration-safe 404; forged tokens escalate
    nothing (Art. XVII — the attempted bypasses)."""

    def _owned_run(self, port):
        status, _, raw = _start_run(port)
        payload = _json_body(raw)
        return payload["session_id"], payload["owner_key"]

    def test_second_visitor_gets_enumeration_safe_404(self, server):
        port = server["port"]
        run_id, owner_key = self._owned_run(port)
        status, _, raw = _request(
            port, "GET", f"/api/run/{run_id}/result",
            headers={"X-Tosca-Owner": "b" * 32})
        assert status == 404
        assert "not found" in _json_body(raw).get("error", "")

    def test_second_visitor_rail_excludes_the_run(self, server):
        port = server["port"]
        run_id, owner_key = self._owned_run(port)
        status, _, raw = _request(
            port, "GET", "/api/sessions",
            headers={"X-Tosca-Owner": "c" * 32})
        assert status == 200
        assert not any(s["session_id"] == run_id
                       for s in _json_body(raw)["sessions"])

    @pytest.mark.parametrize("forged", [
        "FORGED!!!",              # not hex
        "A1B2C3D4E5F6A7B8",       # uppercase hex (keys are minted lowercase)
        "123",                    # too short
        "g" * 64,                 # non-hex charset at length
        "a" * 65,                 # oversized
    ])
    def test_forged_tokens_are_ignored(self, server, forged):
        port = server["port"]
        run_id, owner_key = self._owned_run(port)
        status, _, _ = _request(
            port, "GET", f"/api/run/{run_id}/result",
            headers={"X-Tosca-Owner": forged})
        assert status == 404
        # and a forged token never converges the cookie to itself
        status, hdrs, _ = _request(
            port, "GET", "/api/sessions",
            headers={"X-Tosca-Owner": forged})
        set_cookie = hdrs.get("Set-Cookie", "")
        assert forged not in set_cookie


class TestCookieShape:
    """The cookie attributes match the serving context (CHIPS behind an
    HTTPS proxy; Lax for plain-HTTP local dev)."""

    def test_https_proxy_gets_chips_attributes(self, server):
        port = server["port"]
        status, hdrs, _ = _request(
            port, "GET", "/api/sessions",
            headers={"X-Forwarded-Proto": "https"})
        assert status == 200
        set_cookie = hdrs.get("Set-Cookie", "")
        assert "SameSite=None" in set_cookie
        assert "Secure" in set_cookie
        assert "Partitioned" in set_cookie

    def test_plain_http_keeps_lax(self, server):
        port = server["port"]
        status, hdrs, _ = _request(port, "GET", "/api/sessions")
        assert status == 200
        set_cookie = hdrs.get("Set-Cookie", "")
        assert "SameSite=Lax" in set_cookie
        assert "SameSite=None" not in set_cookie


class TestStreamOwnerParameter:
    """EventSource cannot set headers — the stream routes accept the SAME
    opaque capability as the `owner` query parameter."""

    def _terminal_run(self, port, sessions_path):
        status, _, raw = _start_run(port)
        payload = _json_body(raw)
        run_id, owner_key = payload["session_id"], payload["owner_key"]
        # force a terminal status so the SSE loop exits promptly
        data = json.loads(sessions_path.read_text())
        for s in data["sessions"]:
            if s["session_id"] == run_id:
                s["status"] = "COMPLETE"
        sessions_path.write_text(json.dumps(data))
        return run_id, owner_key

    def test_stream_opens_with_owner_param(self, server):
        port = server["port"]
        run_id, owner_key = self._terminal_run(port, server["sessions_path"])
        status, hdrs, raw = _request(
            port, "GET",
            f"/api/run/{run_id}/stream?owner={owner_key}")
        assert status == 200
        assert "text/event-stream" in hdrs.get("Content-Type", "")
        assert b"hello" in raw[:400]

    def test_stream_without_owner_param_denied(self, server):
        """The embedded-context stream defect, reproduced: no cookie (it
        was blocked), no param -> denial, never a silent hang."""
        port = server["port"]
        run_id, owner_key = self._terminal_run(port, server["sessions_path"])
        status, _, _ = _request(port, "GET", f"/api/run/{run_id}/stream")
        assert status == 404

    def test_stream_with_wrong_owner_param_denied(self, server):
        port = server["port"]
        run_id, owner_key = self._terminal_run(port, server["sessions_path"])
        status, _, _ = _request(
            port, "GET", f"/api/run/{run_id}/stream?owner={'d' * 32}")
        assert status == 404

    def test_sessions_alias_stream_route_wired(self, server):
        """The /api/sessions/{id}/events alias carries the same owner
        query-parameter capability (route-wiring contract)."""
        src = srv.Handler.do_GET.__doc__ or ""
        import inspect
        body = inspect.getsource(srv.Handler.do_GET)
        assert "q_owner" in body
        assert 'parts[3] == "events"' in body


class TestSourceWiring:
    """Route-table source inspection (the r389/r414/r419 precedent):
    the transports are part of the product contract."""

    def test_owner_header_constant(self):
        assert srv.OWNER_HEADER == "X-Tosca-Owner"
        assert srv.OWNER_COOKIE == "tosca_owner"

    def test_run_creation_returns_owner_key(self):
        import inspect
        body = inspect.getsource(srv.Handler.do_POST)
        assert '"owner_key": self._owner_key_cached' in body
        assert 'payload["owner_key"] = self._owner_key_cached' in body

    def test_sessions_payload_carries_owner_key(self):
        import inspect
        body = inspect.getsource(srv.Handler.do_GET)
        assert '"owner_key": self._owner_key_cached' in body
