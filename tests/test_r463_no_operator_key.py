"""tests/test_r463_no_operator_key.py — R463 (operator architectural
ruling): **there is no ENGINE_OPERATOR_KEY and no second service
secret.** One legitimate credential path exists — the provider
credentials the deployment is given (HF_TOKEN etc.) — and Toscanini's
own workers are observable through the session's OWN owner capability,
never through a separate operator credential.

The three acceptance surfaces this suite pins:

  A. RETIREMENT — the operator-key architecture is gone (source scan +
     dead endpoints + access model TypeError), per Art. LXIV (a
     superseded implementation is retired, not accumulated).
  B. SPAWN FORENSICS — every spawn leaves durable, attributable
     evidence (SPAWN_REQUESTED/SPAWNED/SPAWN_FAILED) in the forensics
     ledger and a PER-SESSION worker log; a spawn failure is typed
     ERROR_SPAWN on the session, never an untyped 500 and never an
     engine verdict (Art. LXI).
  C. OWNER-SCOPED DIAGNOSTICS — /api/run/{id}/worker-diagnostics
     serves ONLY the owning caller; forged/foreign/absent capabilities
     get the enumeration-safe 404 (Art. XVII: attempted bypasses).
"""
from __future__ import annotations

import json
import shutil
import socket
import sys
import tempfile
import threading
import urllib.request as urlreq
from http.server import ThreadingHTTPServer
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import server as srv  # noqa: E402
from toscanini import sessions as store  # noqa: E402


# ---------------------------------------------------------------------------
# A. retirement — the operator-key architecture is gone
# ---------------------------------------------------------------------------

def test_no_source_reads_engine_operator_key():
    """The env var must not be READ anywhere in the live toscanini
    package. (Historical records in R*/ and archive/ are history —
    Art. XI — and are not scanned; retirement disclosures in comments
    are disclosures, not reads.)"""
    offenders = []
    pats = ('os.environ.get("ENGINE_OPERATOR_KEY"',
            "os.environ.get('ENGINE_OPERATOR_KEY'",
            'os.environ["ENGINE_OPERATOR_KEY"]',
            "os.environ['ENGINE_OPERATOR_KEY']")
    for py in (REPO / "toscanini").rglob("*.py"):
        text = py.read_text(errors="replace")
        if "__pycache__" in str(py):
            continue
        if any(p in text for p in pats):
            offenders.append(str(py.relative_to(REPO)))
    assert offenders == [], \
        f"toscanini still reads the retired operator key: {offenders}"
    # and no module-level binding survives either
    assert not hasattr(srv, "OPERATOR_KEY"), \
        "server module still exposes an OPERATOR_KEY binding"


def test_ops_endpoints_are_retired():
    """/api/ops/* answered only the operator key; with the key retired
    the routes must not exist at all (404, enumeration-safe)."""
    with _ServerHarness() as h:
        for path in ("/api/ops/worker-log",
                     "/api/ops/artifact-log"):
            code, _ = h.get(path, headers={"X-Operator-Key": "anything"})
            assert code == 404, path


def test_access_model_has_no_operator_parameter():
    """The store's access model accepts ONLY an owner capability — the
    retired parameter raises TypeError (executable proof)."""
    with pytest.raises(TypeError):
        store.session_access("ts_x", "owner", operator_key="OP")
    with pytest.raises(TypeError):
        store.list_sessions_visible_to("owner", "OP")


# ---------------------------------------------------------------------------
# harness — a REAL handler over temp store paths (production untouched,
# Art. IX; the same pattern the R420 model-route tests use)
# ---------------------------------------------------------------------------

class _ServerHarness:
    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="r463_noopkey_")
        tdp = Path(self.tmp)
        store_dir = tdp / "TOSCANINI_UI"
        runs = tdp / "ENGINE_RUNS"
        (store_dir / "worker_forensics").mkdir(parents=True)
        runs.mkdir()
        self._orig = (store.STORE_DIR, store.SESSIONS_PATH,
                      store.SHARES_PATH, store.ENGINE_RUNS)
        store.STORE_DIR = store_dir
        store.SESSIONS_PATH = store_dir / "sessions.json"
        store.SHARES_PATH = store_dir / "shares.json"
        store.ENGINE_RUNS = runs
        store.SESSIONS_PATH.write_text("{}")
        # the forensics ledger lives under the STORE tree
        import toscanini.worker_forensics as wfx
        self._wfx_root = None
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            self.port = s.getsockname()[1]
        self.httpd = ThreadingHTTPServer(("127.0.0.1", self.port),
                                         srv.Handler)
        t = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        t.start()
        self._thread = t
        return self

    def __exit__(self, *a):
        self.httpd.shutdown()
        (store.STORE_DIR, store.SESSIONS_PATH,
         store.SHARES_PATH, store.ENGINE_RUNS) = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def get(self, path, headers=None):
        req = urlreq.Request(f"http://127.0.0.1:{self.port}{path}",
                             headers=headers or {})
        try:
            with urlreq.urlopen(req, timeout=20) as r:
                return r.status, json.loads(r.read().decode())
        except urlreq.HTTPError as e:
            return e.code, {}

    def make_session(self, owner_key, status="RUNNING"):
        s = store.create_session("t", "problem text for the run",
                                 owner_key=owner_key)
        store.update_session(s["session_id"], status=status)
        return s


# ---------------------------------------------------------------------------
# B. spawn forensics — durable, attributable, typed
# ---------------------------------------------------------------------------

class _FakeProc:
    def __init__(self, log_fh):
        self.pid = 424242
        self._fh = log_fh


def _patched_popen(recorder, fail=False):
    """A subprocess.Popen stand-in that records the spawn and can fail
    like the real one (OSError) without launching a worker."""

    def _popen(args, **kwargs):
        if fail:
            raise OSError("injected spawn failure (adversarial test)")
        recorder.append({"args": args, "kwargs_path":
                         str(getattr(kwargs.get("stdout"), "name", ""))})
        return _FakeProc(kwargs.get("stdout"))
    return _popen


def test_spawn_records_forensics_and_per_session_log(monkeypatch):
    with _ServerHarness() as h:
        s = h.make_session("a1a1a1a1a1a1a1a1")
        recorder: list = []
        monkeypatch.setattr(srv.gw, "gateway_up", lambda: False)
        monkeypatch.setattr(srv.gw, "external_base_url", lambda: None)
        monkeypatch.setattr(srv.subprocess, "Popen",
                            _patched_popen(recorder))
        sid = s["session_id"]
        srv.Handler._spawn_worker(object.__new__(srv.Handler), sid)
        # per-session log file — not the shared legacy file
        log = store.ENGINE_RUNS / "worker_logs" / f"{sid}.log"
        assert log.exists(), "spawn must open the per-session worker log"
        # the WORKER spawn (other Popen calls — git identity resolution —
        # are recorded too and are not the spawn under test)
        spawns = [r for r in recorder
                  if any("toscanini.worker" in str(a) for a in r["args"])]
        assert spawns and spawns[0]["kwargs_path"] == str(log)
        assert spawns[0]["args"][-1] == sid
        # forensics: SPAWN_REQUESTED then SPAWNED with the worker pid
        import toscanini.worker_forensics as wfx
        events = [e for e in wfx.read_tail(wfx.durable_root())
                  if e.get("session_id") == sid]
        kinds = [e["event"] for e in events]
        assert kinds[:2] == ["SPAWN_REQUESTED", "SPAWNED"], kinds
        assert events[1].get("worker_pid") == 424242
        # the session record carries the registered pid
        fresh = store.get_session(sid)
        assert fresh.get("worker_pid") == 424242


def test_spawn_failure_is_typed_error_spawn(monkeypatch):
    """A Popen failure classifies on the session (ERROR_SPAWN + honest
    reason + SPAWN_FAILED forensics) — never an untyped 500, never a
    fabricated run (Art. VI/LXI)."""
    with _ServerHarness() as h:
        s = h.make_session("a1a1a1a1a1a1a1a1")
        sid = s["session_id"]
        recorder: list = []
        monkeypatch.setattr(srv.gw, "gateway_up", lambda: False)
        monkeypatch.setattr(srv.gw, "external_base_url", lambda: None)
        monkeypatch.setattr(srv.subprocess, "Popen",
                            _patched_popen(recorder, fail=True))
        # must NOT raise
        srv.Handler._spawn_worker(object.__new__(srv.Handler), sid)
        fresh = store.get_session(sid)
        assert fresh.get("status") == "ERROR_SPAWN"
        assert "could not be started" in (fresh.get("error") or "")
        assert fresh.get("worker_pid") is None
        import toscanini.worker_forensics as wfx
        events = [e for e in wfx.read_tail(wfx.durable_root())
                  if e.get("session_id") == sid]
        kinds = [e["event"] for e in events]
        assert "SPAWN_REQUESTED" in kinds and "SPAWN_FAILED" in kinds
        failed = [e for e in events if e["event"] == "SPAWN_FAILED"][0]
        assert failed.get("error_class") == "OSError"
        # ERROR_SPAWN is retryable — the recovery path accepts it
        from toscanini.sessions import retry_session
        r = retry_session(sid)
        assert r.get("status") == "PENDING"


def test_sweep_attaches_typed_cause_from_log_evidence():
    """The never-registered sweep reads the run's own log and attaches a
    TYPED cause (never guessed — Art. XXV); diagnostics never reach the
    public projection."""
    with _ServerHarness() as h:
        s = h.make_session("a1a1a1a1a1a1a1a1", status="PENDING")
        sid = s["session_id"]
        log_dir = store.ENGINE_RUNS / "worker_logs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / f"{sid}.log").write_text(
            "[worker] start sid=...\n"
            "Traceback (most recent call last):\n"
            "MemoryError\n")
        # force the session past the registration grace window
        # (update_session stamps updated_at=now on every write, so the
        # backdated marker is written at the file level afterwards)
        old = "2026-09-14T00:00:00Z"
        data = json.loads(store.SESSIONS_PATH.read_text())
        for rec in data["sessions"]:
            if rec["session_id"] == sid:
                rec["created_at"] = old
                rec["updated_at"] = old
        store.SESSIONS_PATH.write_text(json.dumps(data))
        marked = store.mark_unregistered_pending()
        assert sid in marked
        fresh = store.get_session(sid)
        assert fresh.get("status") == "INTERRUPTED"
        assert "ran out of memory" in (fresh.get("error") or "")
        diag = fresh.get("spawn_diagnostics") or {}
        assert diag.get("cause") == "the worker process ran out of memory"
        assert diag.get("evidence_lines")
        # the diagnostics carry pids/paths — NEVER in the customer view
        view = __import__("toscanini.user_state",
                          fromlist=["public_session_view"]
                          ).public_session_view(fresh)
        assert "spawn_diagnostics" not in view


# ---------------------------------------------------------------------------
# C. owner-scoped diagnostics — the bypass attempts (Art. XVII)
# ---------------------------------------------------------------------------

def test_worker_diagnostics_owner_scoped():
    with _ServerHarness() as h:
        s = h.make_session("a1a1a1a1a1a1a1a1")
        sid = s["session_id"]
        log_dir = store.ENGINE_RUNS / "worker_logs"
        log_dir.mkdir(exist_ok=True)
        (log_dir / f"{sid}.log").write_text(
            "[worker] start sid=%s\n" % sid)
        # the owner sees ONLY their run's diagnostics
        code, body = h.get(f"/api/run/{sid}/worker-diagnostics",
                           headers={"X-Tosca-Owner": "a1a1a1a1a1a1a1a1"})
        assert code == 200
        assert body["session_id"] == sid
        assert body["worker_log_tail"] == ["[worker] start sid=%s" % sid]
        assert "spawn_forensics" in body
        # the alias route serves the same contract
        code2, _ = h.get(f"/api/sessions/{sid}/worker-diagnostics",
                         headers={"X-Tosca-Owner": "a1a1a1a1a1a1a1a1"})
        assert code2 == 200
        # BYPASS ATTEMPTS — all enumeration-safe 404:
        # (1) a different owner's capability
        code3, _ = h.get(f"/api/run/{sid}/worker-diagnostics",
                         headers={"X-Tosca-Owner": "b2b2b2b2b2b2b2b2"})
        assert code3 == 404
        # (2) no capability at all
        code4, _ = h.get(f"/api/run/{sid}/worker-diagnostics")
        assert code4 == 404
        # (3) the retired operator header carries NO authority
        code5, _ = h.get(f"/api/run/{sid}/worker-diagnostics",
                         headers={"X-Operator-Key": "ownerA"})
        assert code5 == 404
        # (4) a forged uuid-shaped capability
        code6, _ = h.get(
            f"/api/run/{sid}/worker-diagnostics",
            headers={"X-Tosca-Owner": "deadbeefdeadbeefdeadbeef"})
        assert code6 == 404


def test_health_payload_declares_owner_scoped_diagnostics():
    payload = srv._health_payload()
    assert "operator_key_configured" not in payload
    assert payload["worker_diagnostics"]["owner_scoped"] is True
    assert payload["worker_diagnostics"]["spawn_forensics"] is True


def test_worker_pu_loader_call_signature_matches_def():
    """R463 regression (measured live, run ts_fa75e009ed5e): the R461
    loader takes the session_id alone, but the call site passed a
    second argument — a TypeError fired on EVERY fresh run and the
    disclosed fallback silently skipped problem understanding. The
    defect stayed invisible while the worker log was operator-gated;
    the R463 owner-scoped per-session log surfaced it on its first
    production run. This contract pins the arity match structurally
    (AST-level, Art. XVI: executable evidence)."""
    import ast
    tree = ast.parse((REPO / "toscanini" / "worker.py").read_text())
    fn_def = None
    call_args = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) \
                and node.name == "_load_problem_understanding":
            fn_def = node
        if isinstance(node, ast.Call) \
                and isinstance(node.func, ast.Name) \
                and node.func.id == "_load_problem_understanding":
            n = len(node.args) + len(node.keywords)
            call_args = (call_args or []) + [n]
    assert fn_def is not None, "the loader definition is missing"
    required = len(fn_def.args.args) - len(fn_def.args.defaults)
    for n in call_args:
        assert required <= n <= len(fn_def.args.args), \
            f"call passes {n} args; the def accepts " \
            f"{required}..{len(fn_def.args.args)}"
    assert call_args == [1], \
        "the call must pass exactly the session_id (the R463 fix)"
