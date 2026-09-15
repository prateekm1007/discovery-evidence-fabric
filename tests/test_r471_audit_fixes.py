"""tests/test_r471_audit_fixes.py — the external product audit's P0
contract fixes (2026-09-16 audit, checkout 3b2298, verdict 6.1/10).

The audit measured, on the live production surface:

  P0-2  the retry path is not contract-safe: an accepted retry was a
        bare session view; a refusal was a 409 whose body looked like a
        session; the frontend treats non-2xx as an exception, so the
        advertised Resume silently did nothing. Also: a retry arriving
        while the ledger still said RUNNING (worker freshly dead, sweep
        not yet run) was refused against a stale row — the audit's
        exact measured sequence (retry -> 409 -> session later
        INTERRUPTED, nobody resumed it).
  P0-5  the clarification answer is present in the conversation but the
        typed `clarification_answer` field is EMPTY after reload — the
        worker's one-shot write (clarification_answer={}) consumed the
        record.
  P0-6  the URL input is described by the product language but absent:
        no URL field, no URL reference contract.

This battery pins the closed contracts:

  * retry acceptance = 202 + typed retry_id + session view;
  * the retry-path dead-worker reconciliation (the race, reproduced);
  * refusal = 409 TYPED (refusal/session_status, no session body);
  * 404 for an unknown session; attempts increment; ids distinct;
  * the clarification answer record is born USER_STATED, is marked
    consumed IN PLACE (never emptied), and the PU merge is idempotent;
  * URL ingestion: SSRF-guarded (scheme + every resolved address
    public), typed failure states (blocked / fetch-failed / empty /
    too-large), and a success path that lands in the SAME custody
    chain as an upload (sha256, bounded extract, owner-scoped).

Runs against a REAL handler instance (ThreadingHTTPServer on an
ephemeral port; the r423/r447 precedent) with the worker spawn stubbed,
the URL fetcher injected (the SSRF guard refuses loopback hosts, so a
live success path cannot be exercised in-process), and the session
store pointed at a temp dir. Hermetic: no subprocess, no network, no
LLM.
"""
from __future__ import annotations

import http.client
import json
import os
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import attachments as att  # noqa: E402
from toscanini import sessions as store  # noqa: E402
from toscanini import server as srv  # noqa: E402
from toscanini.conversational import problem_understanding as pu_mod  # noqa: E402

PROBLEM = ("Our offshore wind turbine gearbox suffers micropitting on the "
           "planet gears during low-load nights; find a mechanism that "
           "reduces it without redesigning the gearbox.")


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def _dead_pid() -> int:
    """A pid that is verifiably NOT running (spawned, reaped, gone)."""
    p = subprocess.Popen([sys.executable, "-c", "pass"])
    p.wait()
    return p.pid


@pytest.fixture()
def server(tmp_path):
    """A real HTTP handler with the session store in a temp dir and the
    discovery worker spawn stubbed (route semantics only)."""
    sessions_path = tmp_path / "sessions.json"
    shares_path = tmp_path / "shares.json"

    real_sessions, real_shares = store.SESSIONS_PATH, store.SHARES_PATH
    store.SESSIONS_PATH = sessions_path
    store.SHARES_PATH = shares_path

    real_runs = store.ENGINE_RUNS
    runs_dir = tmp_path / "engine_runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    store.ENGINE_RUNS = runs_dir
    att.ATTACHMENTS_DIR = runs_dir / "attachments"

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
        yield {"port": port, "tmp": tmp_path}
    finally:
        httpd.shutdown()
        httpd.server_close()
        store.SESSIONS_PATH, store.SHARES_PATH = real_sessions, real_shares
        store.ENGINE_RUNS = real_runs


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


def _create_run(port, owner=None):
    headers = {"X-Tosca-Owner": owner} if owner else None
    status, _, raw = _request(port, "POST", "/api/run",
                              headers=headers, body={"text": PROBLEM})
    assert status == 200, raw
    body = _json_body(raw)
    return body["session_id"], body.get("owner_key")


# ---------------------------------------------------------------------------
# P0-2 — the retry contract
# ---------------------------------------------------------------------------

class TestRetryContract:
    def test_accepted_retry_is_202_with_typed_retry_id(self, server):
        port = server["port"]
        sid, owner = _create_run(port)
        # the worker died with the container: typed INTERRUPTED
        assert store.update_session(sid, status="INTERRUPTED",
                                    error="worker process is no longer "
                                          "running — service restarted")
        status, _, raw = _request(port, "POST",
                                  f"/api/sessions/{sid}/retry",
                                  headers={"X-Tosca-Owner": owner})
        assert status == 202, raw
        body = _json_body(raw)
        # the explicit state transition carries its own identity
        assert body["retry_id"] and str(body["retry_id"]).startswith("rt_")
        assert body["session_id"] == sid
        assert body["status"] == "PENDING"
        assert body["retry_attempts"] == 1
        # the session record keeps the identity (provenance discipline)
        s = store.get_session(sid)
        assert s.get("retry_id") == body["retry_id"]
        assert s.get("status") == "PENDING"
        # the acceptance body carries the session view WITHOUT the
        # operational internals
        assert body["session"]["session_id"] == sid
        assert "worker_pid" not in body["session"]

    def test_the_audit_race_reconciles_before_refusing(self, server):
        """The audit's measured sequence: the worker dies, the sweep has
        not yet run, the retry arrives against the stale RUNNING row.
        The old handler refused 409; the reconciled handler flips the
        verifiably-dead worker to INTERRUPTED FIRST and accepts."""
        port = server["port"]
        sid, owner = _create_run(port)
        assert store.update_session(
            sid, status="RUNNING", worker_pid=_dead_pid(),
            worker_starttime="1")
        status, _, raw = _request(port, "POST",
                                  f"/api/sessions/{sid}/retry",
                                  headers={"X-Tosca-Owner": owner})
        assert status == 202, raw
        body = _json_body(raw)
        assert body["status"] == "PENDING"

    def test_refusal_is_typed_and_sessionless(self, server):
        port = server["port"]
        sid, owner = _create_run(port)
        # a COMPLETE verdict is a research outcome, never retryable
        assert store.update_session(sid, status="COMPLETE")
        status, _, raw = _request(port, "POST",
                                  f"/api/sessions/{sid}/retry",
                                  headers={"X-Tosca-Owner": owner})
        assert status == 409
        body = _json_body(raw)
        # the refusal is TYPED — no session-shaped body to misread
        assert body["refusal"] == "RETRY_NOT_PERMITTED"
        assert body["session_status"] == "COMPLETE"
        assert body["retryable"] is False
        assert "session" not in body
        assert "status" not in body  # not a session view under another name

    def test_unknown_session_is_404(self, server):
        port = server["port"]
        status, _, _ = _request(port, "POST",
                                "/api/sessions/ts_nope/retry")
        assert status == 404

    def test_second_retry_gets_a_distinct_id(self, server):
        port = server["port"]
        sid, owner = _create_run(port)
        ids = []
        for attempt in (1, 2):
            assert store.update_session(sid, status="INTERRUPTED")
            status, _, raw = _request(port, "POST",
                                      f"/api/sessions/{sid}/retry",
                                      headers={"X-Tosca-Owner": owner})
            assert status == 202
            ids.append(_json_body(raw)["retry_id"])
        assert ids[0] != ids[1]
        assert store.get_session(sid)["retry_attempts"] == 2


# ---------------------------------------------------------------------------
# P0-5 — the clarification answer record survives
# ---------------------------------------------------------------------------

class TestClarificationPersistence:
    def test_answer_record_born_user_stated_and_never_emptied(self, server):
        """The route stamps provenance at birth; the worker's
        consumption marks IN PLACE (the audited one-shot empty-write is
        retired)."""
        from toscanini.conversational import conversation_memory as cm
        port = server["port"]
        sid, owner = _create_run(port)
        assert store.update_session(
            sid, status="AWAITING_CLARIFICATION",
            clarification={"field": "desired_outcome",
                           "question": "What outcome matters most?"})
        status, _, raw = _request(
            port, "POST", f"/api/run/{sid}/answer",
            headers={"X-Tosca-Owner": owner},
            body={"answer": "Cut the micropitting rate without redesign."})
        assert status == 200, raw
        s = store.get_session(sid)
        rec = s.get("clarification_answer") or {}
        assert rec.get("field") == "desired_outcome"
        assert rec.get("answer") == "Cut the micropitting rate without redesign."
        # born USER_STATED (the audit's provenance requirement)
        assert rec.get("provenance") == "USER_STATED"
        assert rec.get("consumed_at") is None

        # the worker consumes: the merge happens and consumption is
        # MARKED, never emptied
        pu = pu_mod.build_problem_understanding(s["user_text"])
        answer = s.get("clarification_answer") or {}
        assert answer.get("field") and answer.get("answer")
        pu = pu_mod.apply_clarification_answer(
            pu, answer["field"], answer["answer"])
        consumed = {**answer,
                    "consumed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                 time.gmtime()),
                    "merged_into": "problem_understanding_input"}
        store.update_session(sid, clarification_answer=consumed)

        # THE AUDIT'S ACCEPTANCE: after reload, the record remains
        s2 = store.get_session(sid)
        rec2 = s2.get("clarification_answer") or {}
        assert rec2.get("field") == "desired_outcome"
        assert rec2.get("answer") == "Cut the micropitting rate without redesign."
        assert rec2.get("provenance") == "USER_STATED"
        assert rec2.get("consumed_at")
        assert rec2.get("merged_into") == "problem_understanding_input"
        # the question is not re-asked: an answer exists -> no pause
        assert not (not s2.get("clarification_answer"))

    def test_pu_merge_is_idempotent_by_content(self):
        """A retry re-enters the merge block (the record persists now) —
        the history check keeps the PU record exact."""
        pu = pu_mod.build_problem_understanding(PROBLEM)
        pu = pu_mod.apply_clarification_answer(
            pu, "desired_outcome", "Cut the micropitting rate.")
        history_after_first = list(pu.get("clarification_history"))
        # the retry re-applies the SAME (field, answer)
        pu = pu_mod.apply_clarification_answer(
            pu, "desired_outcome", "Cut the micropitting rate.")
        assert pu.get("clarification_history") == history_after_first
        # a DIFFERENT answer still merges (a real new user statement)
        pu = pu_mod.apply_clarification_answer(
            pu, "desired_outcome", "Different direction entirely.")
        assert len(pu["clarification_history"]) == 2


# ---------------------------------------------------------------------------
# P0-6 — the URL/reference leg of the input model
# ---------------------------------------------------------------------------

class TestSsrfGuard:
    def test_blocked_schemes(self):
        guarded, err = att._ssrf_guard("file:///etc/passwd")
        assert guarded is None
        assert err["status"] == "REJECTED_BLOCKED_URL"

    def test_blocked_loopback_and_metadata_hosts(self):
        for url in ("http://127.0.0.1/x", "http://localhost/x",
                    "http://169.254.169.254/latest/meta-data/",
                    "http://[::1]/x", "http://10.1.2.3/x",
                    "http://192.168.1.4/x", "http://172.16.0.9/x",
                    "http://0.0.0.0/x"):
            guarded, err = att._ssrf_guard(url)
            assert guarded is None, url
            assert err["status"] == "REJECTED_BLOCKED_URL", url

    def test_public_host_passes_guard(self):
        # the guard is scheme/host only — no request is made here
        guarded, err = att._ssrf_guard("https://example.com/paper")
        assert err is None
        assert guarded == "https://example.com/paper"

    def test_unresolvable_host_is_fetch_failed(self):
        guarded, err = att._ssrf_guard("http://definitely-not-a-host.invalid/x")
        assert guarded is None
        assert err["status"] == "REJECTED_FETCH_FAILED"


class TestUrlIngestion:
    def test_success_lands_in_the_upload_custody_chain(self, server):
        tmp = server["tmp"]
        html = (b"<html><head><style>body{color:red}</style></head>"
                b"<body><h1>Micropitting study</h1>"
                b"<script>alert(1)</script>"
                b"<p>Surface fatigue nucleates near the flanks.</p>"
                b"</body></html>")

        def fake_fetcher(url):
            return html, "text/html; charset=utf-8", url

        rec = att.save_url_attachment("owner_r471_a",
                                      "https://example.com/papers/pit",
                                      _fetcher=fake_fetcher)
        assert not rec.get("rejected")
        assert rec["ingestion"]["status"] == "TEXT_EXTRACTED"
        assert rec["ingestion"]["text_chars_total"] > 0
        assert "Micropitting study" in rec["name"] or \
            rec["name"].startswith("example.com")
        assert rec["source_url"] == "https://example.com/papers/pit"
        assert rec["sha256"] and rec["bytes"] == len(html)
        assert rec["media_type"] == "text/html"
        # same custody as an upload: the blob + the bounded extract
        text = att.get_attachment_text(rec["attachment_id"], "owner_r471_a")
        assert "Micropitting study" in text
        assert "alert(1)" not in text  # script content dropped
        assert "Surface fatigue" in text
        stored = att.get_attachment(rec["attachment_id"], "owner_r471_a")
        assert stored is not None
        # owner-scoped: another capability sees nothing
        assert att.get_attachment(rec["attachment_id"],
                                  "owner_r471_b") is None

    def test_empty_content_is_typed(self, server):
        rec = att.save_url_attachment(
            "owner_r471_a", "https://example.com/empty",
            _fetcher=lambda url: (b"", "text/html", url))
        assert rec["rejected"]
        assert rec["ingestion"]["status"] == "REJECTED_EMPTY_CONTENT"

    def test_too_large_is_typed(self, server):
        big = b"x" * (att.MAX_UPLOAD_BYTES + 1)
        rec = att.save_url_attachment(
            "owner_r471_a", "https://example.com/huge",
            _fetcher=lambda url: (big, "text/plain", url))
        assert rec["rejected"]
        assert rec["ingestion"]["status"] == "REJECTED_TOO_LARGE"

    def test_fetch_failure_is_typed_not_a_500(self, server):
        def boom(url):
            raise OSError("the server answered HTTP 502")
        rec = att.save_url_attachment(
            "owner_r471_a", "https://example.com/flaky",
            _fetcher=boom)
        assert rec["rejected"]
        assert rec["ingestion"]["status"] == "REJECTED_FETCH_FAILED"
        assert "502" in rec["ingestion"]["note"]

    def test_blocked_url_never_fetches(self, server):
        def forbidden_fetcher(url):  # must never be reached
            raise AssertionError("the fetcher must not run for a blocked URL")
        rec = att.save_url_attachment(
            "owner_r471_a", "file:///etc/passwd",
            _fetcher=forbidden_fetcher)
        assert rec["rejected"]
        assert rec["ingestion"]["status"] == "REJECTED_BLOCKED_URL"


class TestUrlRoute:
    def test_route_accepts_and_types(self, server):
        port = server["port"]
        # blocked scheme: 201 with a TYPED rejected record (not a 500,
        # not a fabricated success)
        status, _, raw = _request(port, "POST", "/api/attachments/url",
                                  body={"url": "file:///etc/passwd"})
        assert status == 201
        body = _json_body(raw)
        assert body["rejected"], body
        rec = body["attachments"][0]
        assert rec["ingestion"]["status"] == "REJECTED_BLOCKED_URL"
        assert rec["ingestion"]["note"]
        # the capability never echoes back
        assert "owner_key" not in rec

    def test_route_requires_a_url(self, server):
        port = server["port"]
        status, _, _ = _request(port, "POST", "/api/attachments/url",
                                body={})
        assert status == 400

    def test_in_conversation_url_binds_to_the_run(self, server):
        port = server["port"]
        sid, owner = _create_run(port)

        # the URL must pass the SSRF guard before any fetch, so this
        # test exercises the ROUTE + BINDING path with a blocked
        # (never-fetched) URL: the rejected record must NOT bind
        status, _, raw = _request(
            port, "POST", f"/api/run/{sid}/attachments/url",
            headers={"X-Tosca-Owner": owner},
            body={"url": "http://127.0.0.1:9000/secret"})
        assert status == 201
        body = _json_body(raw)
        assert body["rejected"]
        assert body["bound_run"] == sid
        # the rejected record did not enter the run's custody
        s = store.get_session(sid)
        assert s.get("attachment_ids") in (None, [],) or \
            body["attachments"][0]["attachment_id"] \
            not in s.get("attachment_ids")


# ---------------------------------------------------------------------------
# P2-3 — the a11y quick wins are IN the shipped source
# ---------------------------------------------------------------------------

class TestA11yLabels:
    def test_home_inputs_carry_accessible_names(self):
        src = (REPO_ROOT / "TOSCANINI_UI" / "webapp" / "app"
               / "page.tsx").read_text()
        # the home textarea: placeholder is not an accessible name
        assert 'aria-label="Describe the problem you want to solve or invent"' in src
        # the hidden file input has an accessible name
        assert 'aria-label="Attach documents"' in src
        # the URL input is labeled
        assert 'aria-label="Reference URL"' in src
