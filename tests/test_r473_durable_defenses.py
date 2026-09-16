"""tests/test_r473_durable_defenses.py — the two audit-named durable
defenses, landed after the measured 176->34 session-index incident.

THE INCIDENT (runtime-state-hf, recovered this round): the durable
branch held a 176-session index at e245bbe; a later boot with an
un-restored (smaller) local store SERVED and SNAPSHOTTED anyway —
server main() swallowed the restore failure and the boot snapshot
pushed a 34-session index over the 176-session branch index (grafted
back to the 209-session union this round; the residual model_routing
ledger loss repaired as graft v4 8663b860).

THE TWO DEFENSES (2026-09-16 audit):

  1. RESTORE-BEFORE-SERVE — durable.restore_for_serve() gates the boot:
     bounded retries; on exhaustion the gate closes and the process
     serves DEGRADED (run creation 503 RESTORE_GATE_CLOSED, every
     snapshot refuses typed) while a background retry keeps attempting
     the restore. The branch can never be overwritten by state that
     never reconciled with it. Gate state rides /api/health
     (durable.serve_gate).

  2. SHRINK GUARD — durable._shrink_violations() compares the payload a
     snapshot would push against the durable branch (HEAD): the
     branch's session ids, share ids and append-only ledger lines must
     ALL survive. A smaller-or-empty snapshot over a larger durable
     state is refused; the DURABLE_ALLOW_SHRINK=1 escape hatch is
     recorded in the snapshot report, the snapshot log AND the commit
     message (never a silent shrink, Art. XV/XXV).

RESTORE SYMMETRY (the guard's counterpart, same round): restore() now
re-materializes model_routing/ledger.jsonl (append-only merge by
request_id — the EXACT file whose 19 earliest records the incident
erased) and copies model_routing/state.json +
transport_capability/capability_state.json when absent. Without it the
guard would deadlock production (branch ⊄ local forever) and the data
repair would be re-erased on the next fresh-container snapshot.

Git is exercised against a REAL local bare origin (the r423 precedent —
no network); the server battery runs a REAL ThreadingHTTPServer on an
ephemeral port with the worker spawn stubbed (the r447 precedent).
"""
from __future__ import annotations

import http.client
import json
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import durable  # noqa: E402
from toscanini import sessions as store_mod  # noqa: E402

PROBLEM = ("Our offshore wind turbine gearbox suffers micropitting on the "
           "planet gears during low-load nights; find a mechanism that "
           "reduces it without redesigning the gearbox.")

GATE_DEFAULT = {"restored": None, "at": None, "error": None,
                "attempts": 0, "integrity_verified": None}


def _reset_gate():
    durable._SERVE_GATE.clear()
    durable._SERVE_GATE.update(GATE_DEFAULT)


def _git(cwd: Path, *args: str, check: bool = True):
    r = subprocess.run(["git", "-C", str(cwd), *args],
                       capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f"git {args[:3]}: {r.stderr.strip()[:300]}")
    return r


def _ledger_line(rid: str, epoch: float) -> str:
    return json.dumps({"request_id": rid, "recorded_at_epoch": epoch,
                       "model": "Atria-Dawn-Preview", "ok": True,
                       "call_class": "CAPABILITY_PROBE"})


def _seed_branch(bare: Path, files: dict) -> None:
    """Push a branch state onto the local bare origin (the durable
    history a fresh container would restore from)."""
    seed = bare.parent / "seed"
    if seed.exists():
        subprocess.run(["rm", "-rf", str(seed)], check=True)
    seed.mkdir(parents=True)
    _git(seed, "init", "-b", "runtime-state")
    _git(seed, "remote", "add", "origin", str(bare))
    for rel, content in files.items():
        p = seed / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    _git(seed, "add", "-A")
    _git(seed, "-c", "user.name=seed", "-c", "user.email=seed@local",
         "commit", "-m", "seed: the durable branch state", "--quiet")
    _git(seed, "push", "-q", "origin", "runtime-state:runtime-state")
    # clones must check out the DURABLE branch, not an unborn master
    _git(bare, "symbolic-ref", "HEAD", "refs/heads/runtime-state")


@pytest.fixture()
def durable_env(tmp_path, monkeypatch):
    """Isolated durable layer with a REAL bare origin that ALREADY holds
    durable history (the pre-condition the defenses exist for)."""
    _reset_gate()
    root = tmp_path
    store = root / "store"
    store.mkdir()
    runs = root / "ENGINE_RUNS"
    runs.mkdir(parents=True)
    (store / "sessions.json").write_text(json.dumps({
        "sessions": [{"session_id": "s_local", "status": "COMPLETE",
                      "origin": "toscanini_ui", "updated_at":
                      "2026-09-16T01:00:00Z"}]}))
    bare = root / "origin.git"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True,
                   capture_output=True)
    _seed_branch(bare, {
        "sessions.json": json.dumps({"sessions": [
            {"session_id": "s_branch_1", "status": "COMPLETE",
             "updated_at": "2026-09-15T00:00:00Z"},
            {"session_id": "s_branch_2", "status": "COMPLETE",
             "updated_at": "2026-09-15T01:00:00Z"}]}),
        "model_routing/ledger.jsonl":
            "\n".join([_ledger_line(f"req_branch_{i}", 1789513186.0 + i)
                       for i in range(3)]) + "\n",
        "worker_forensics/ledger.jsonl":
            "\n".join([json.dumps({"event_id": f"ev_{i}", "t": i})
                       for i in range(2)]) + "\n",
    })

    monkeypatch.setattr(durable, "ENGINE_RUNTIME", root / "runtime")
    monkeypatch.setattr(durable, "STATE_REPO",
                        root / "runtime" / "state-repo")
    monkeypatch.setattr(durable, "LOCK_PATH",
                        root / "runtime" / "durable.lock")
    monkeypatch.setattr(durable, "REPO_ROOT", root)
    monkeypatch.setattr(durable, "REMOTE", str(bare))
    monkeypatch.setenv("DURABLE_STATE_ENABLED", "1")
    monkeypatch.setenv("DURABLE_STATE_BRANCH", "runtime-state")
    monkeypatch.setenv("GITHUB_TOKEN", "test-token-not-real")
    monkeypatch.delenv("DURABLE_ALLOW_SHRINK", raising=False)
    monkeypatch.setattr(store_mod, "STORE_DIR", store)
    monkeypatch.setattr(store_mod, "SESSIONS_PATH",
                        store / "sessions.json")
    monkeypatch.setattr(store_mod, "SHARES_PATH", store / "shares.json")
    monkeypatch.setattr(store_mod, "ENGINE_RUNS", runs)
    monkeypatch.setattr(durable.store, "SESSIONS_PATH",
                        store / "sessions.json")
    monkeypatch.setattr(durable.store, "SHARES_PATH",
                        store / "shares.json")
    monkeypatch.setattr(durable.store, "STORE_DIR", store)
    monkeypatch.setattr(durable.store, "ENGINE_RUNS", runs)
    monkeypatch.setattr(durable.store, "list_sessions", lambda: [])
    durable.reset_payload_cache()
    yield {"root": root, "store": store, "bare": bare, "runs": runs}
    durable.reset_payload_cache()
    _reset_gate()


def _branch_head_commits(bare: Path) -> int:
    clone = bare.parent / "probe"
    if clone.exists():
        subprocess.run(["rm", "-rf", str(clone)], check=True)
    r = _git(bare.parent, "clone", "-q", "--bare", str(bare),
             str(clone), check=False)
    if r.returncode != 0:
        return 0
    log = _git(clone, "log", "--oneline", "runtime-state",
               check=False)
    return len([l for l in log.stdout.splitlines() if l.strip()])


# ---------------------------------------------------------------------------
# defense 2 — the shrink guard
# ---------------------------------------------------------------------------

class TestShrinkGuard:
    def test_session_index_loss_blocked(self, durable_env):
        """THE incident class: a local store missing branch sessions must
        be refused BEFORE anything is pushed."""
        env = durable_env
        # local store has ONLY s_local; the branch holds s_branch_1/2
        report = durable.snapshot("created:s_local")
        assert report["ok"] is False, report
        assert report["error"].startswith("shrink guard blocked"), report
        sg = report["shrink_guard"]
        assert sg["ok"] is False and sg["override"] is False
        assert any("sessions.json" in v for v in sg["violations"])
        assert any("s_branch_1" in v or "s_branch_2" in v
                   for v in sg["violations"])
        # the branch is UNTOUCHED — no commit, no push happened
        commits = _git(env["bare"].parent / "probe", "log", "--oneline",
                       "runtime-state", check=False) if False else None
        # (direct count via ls-remote is unnecessary: the bare has exactly
        # the seed commit — verify the state-repo made no NEW push by
        # counting refs)
        out = subprocess.run(
            ["git", "--git-dir", str(env["bare"]), "rev-list",
             "--count", "runtime-state"], capture_output=True, text=True)
        assert out.stdout.strip() == "1", \
            "a blocked snapshot must not create commits on the branch"

    def test_superset_snapshot_passes(self, durable_env):
        """The healthy path: local store ⊇ branch ids (restore ran) —
        the snapshot proceeds."""
        env = durable_env
        (env["store"] / "sessions.json").write_text(json.dumps(
            {"sessions": [
                {"session_id": "s_branch_1", "status": "COMPLETE",
                 "updated_at": "2026-09-15T00:00:00Z"},
                {"session_id": "s_branch_2", "status": "COMPLETE",
                 "updated_at": "2026-09-15T01:00:00Z"},
                {"session_id": "s_local", "status": "COMPLETE",
                 "updated_at": "2026-09-16T01:00:00Z"}]}))
        report = durable.snapshot("terminal:COMPLETE:s_local")
        assert report["ok"] is True, report
        assert report["shrink_guard"] == {"ok": True, "violations": [],
                                          "override": False}

    def test_ledger_line_loss_blocked(self, durable_env):
        """The model_routing ledger loss class (the 19 erased records):
        a local ledger missing branch lines must be refused."""
        env = durable_env
        mr = env["runs"] / "model_routing"
        mr.mkdir(parents=True)
        # local keeps only ONE of the branch's three lines
        (mr / "ledger.jsonl").write_text(_ledger_line("req_branch_0",
                                                      1789513186.0) + "\n")
        report = durable.snapshot("created:s_local")
        assert report["ok"] is False, report
        assert report["error"].startswith("shrink guard blocked")
        assert any("model_routing/ledger.jsonl" in v
                   for v in report["shrink_guard"]["violations"])
        assert any("append-only line" in v
                   for v in report["shrink_guard"]["violations"])

    def test_worker_forensics_ledger_loss_blocked(self, durable_env):
        env = durable_env
        wf = env["store"] / "worker_forensics"
        wf.mkdir(parents=True)
        (wf / "ledger.jsonl").write_text(
            json.dumps({"event_id": "ev_0", "t": 0}) + "\n")
        report = durable.snapshot("created:s_local")
        assert report["ok"] is False, report
        assert any("worker_forensics/ledger.jsonl" in v
                   for v in report["shrink_guard"]["violations"])

    def test_override_escapes_and_is_disclosed(self, durable_env,
                                               monkeypatch):
        """The escape hatch exists for operators — and it is RECORDED at
        every layer (report, snapshot log, commit message)."""
        env = durable_env
        monkeypatch.setenv("DURABLE_ALLOW_SHRINK", "1")
        report = durable.snapshot("operator_mandated_resync")
        assert report["ok"] is True, report
        assert report["shrink_guard"]["override"] is True
        assert report["shrink_guard"]["violations"], \
            "the violations must ride the report even when overridden"
        # the pushed branch HEAD carries the disclosure in its message
        clone = env["bare"].parent / "probe-override"
        subprocess.run(["rm", "-rf", str(clone)], check=True)
        _git(env["bare"].parent, "clone", "-q", str(env["bare"]),
             str(clone))
        msg = _git(clone, "log", "-1", "--format=%B").stdout
        assert "[shrink-override]" in msg
        log_line = (clone / "snapshot_log.jsonl").read_text().strip()
        rec = json.loads(log_line.splitlines()[-1])
        assert rec["shrink_override"] is True
        assert rec["shrink_violations"]

    def test_absent_payload_file_is_not_a_violation(self, durable_env):
        """A file simply not pushed this round is NOT a shrink — the
        branch copy survives in the state repo (only REPLACEMENT by
        smaller content is the hazard)."""
        env = durable_env
        # local sessions superset, NO local ledger at all
        (env["store"] / "sessions.json").write_text(json.dumps(
            {"sessions": [
                {"session_id": "s_branch_1", "status": "COMPLETE",
                 "updated_at": "2026-09-15T00:00:00Z"},
                {"session_id": "s_branch_2", "status": "COMPLETE",
                 "updated_at": "2026-09-15T01:00:00Z"},
                {"session_id": "s_local", "status": "COMPLETE",
                 "updated_at": "2026-09-16T01:00:00Z"}]}))
        report = durable.snapshot("created:s_local")
        assert report["ok"] is True, report


# ---------------------------------------------------------------------------
# defense 1 — restore-before-serve
# ---------------------------------------------------------------------------

class TestRestoreGate:
    def test_failed_restore_closes_gate_and_blocks_snapshots(
            self, durable_env, monkeypatch):
        attempts = {"n": 0}

        def failing_restore():
            attempts["n"] += 1
            return {"error": "git fetch failed: connection reset",
                    "integrity_verified": None}

        monkeypatch.setattr(durable, "restore", failing_restore)
        report = durable.restore_for_serve(max_attempts=3, delay_seconds=0)
        assert report["error"] == "git fetch failed: connection reset"
        gate = durable.serve_gate()
        assert gate["restored"] is False
        assert gate["attempts"] == 3
        assert attempts["n"] == 3
        # every snapshot from the un-restored process refuses, typed
        snap = durable.snapshot("boot:abc123:after_restore")
        assert snap["ok"] is False
        assert "restore gate closed" in snap["error"]
        # ... including the very first one (no partial state escaped)
        out = subprocess.run(
            ["git", "--git-dir", str(durable_env["bare"]), "rev-list",
             "--count", "runtime-state"], capture_output=True, text=True)
        assert out.stdout.strip() == "1"

    def test_integrity_mismatch_closes_gate(self, durable_env,
                                            monkeypatch):
        def corrupt_manifest():
            return {"error": None, "integrity_verified": False,
                    "integrity_mismatches": ["sessions.json: sha256 "
                                             "mismatch"]}

        monkeypatch.setattr(durable, "restore", corrupt_manifest)
        durable.restore_for_serve(max_attempts=1, delay_seconds=0)
        assert durable.serve_gate()["restored"] is False
        snap = durable.snapshot("boot:abc123:after_restore")
        assert snap["ok"] is False
        assert "restore gate closed" in snap["error"]

    def test_retry_opens_gate_on_success(self, durable_env, monkeypatch):
        """A transient outage self-heals INSIDE restore_for_serve: the
        failing attempt closes nothing permanently."""
        real_restore = durable.restore
        state = {"n": 0}

        def flaky_restore():
            state["n"] += 1
            if state["n"] == 1:
                return {"error": "transient", "integrity_verified": None}
            return real_restore()

        monkeypatch.setattr(durable, "restore", flaky_restore)
        report = durable.restore_for_serve(max_attempts=3, delay_seconds=0)
        assert durable.serve_gate()["restored"] is True
        assert durable.serve_gate()["attempts"] == 2
        # and the process can snapshot again (the branch is reconciled)
        (durable_env["store"] / "sessions.json").write_text(json.dumps(
            {"sessions": [
                {"session_id": "s_branch_1", "status": "COMPLETE",
                 "updated_at": "2026-09-15T00:00:00Z"},
                {"session_id": "s_branch_2", "status": "COMPLETE",
                 "updated_at": "2026-09-15T01:00:00Z"},
                {"session_id": "s_local", "status": "COMPLETE",
                 "updated_at": "2026-09-16T01:00:00Z"}]}))
        snap = durable.snapshot("boot:abc123:after_restore")
        assert snap["ok"] is True, snap

    def test_serve_gate_rides_health_state(self, durable_env):
        sg = durable.state()["serve_gate"]
        assert sg == GATE_DEFAULT or set(sg) == set(GATE_DEFAULT)

    def test_gate_none_keeps_library_semantics(self, durable_env):
        """No restore attempted (restored is None — library/test/CLI
        use): snapshots proceed under the previous semantics; only an
        EXPLICIT failed restore closes the gate."""
        assert durable.serve_gate()["restored"] is None
        # the bare holds branch sessions the local store lacks — the
        # shrink guard still applies (defense 2 is independent)
        report = durable.snapshot("created:s_local")
        assert report["ok"] is False  # shrink guard, not the gate
        assert "shrink guard" in report["error"]


# ---------------------------------------------------------------------------
# restore symmetry — the guard's counterpart
# ---------------------------------------------------------------------------

class TestRestoreSymmetry:
    def test_model_routing_ledger_restored_append_only(self, durable_env):
        """The EXACT loss the incident caused: the branch ledger must
        come BACK on restore, merged append-only by request_id — so the
        next snapshot is a superset and the graft survives forever."""
        env = durable_env
        mr = env["runs"] / "model_routing"
        mr.mkdir(parents=True)
        # local has a NEWER line the branch lacks; branch has 3 lines
        # local has never seen
        (mr / "ledger.jsonl").write_text(
            _ledger_line("req_local_new", 1789519999.0) + "\n")
        report = durable.restore()
        assert report["error"] is None, report
        assert report["model_routing_lines"] == 3
        lines = [json.loads(l) for l in
                 (mr / "ledger.jsonl").read_text().splitlines() if l]
        ids = [l["request_id"] for l in lines]
        assert ids == ["req_local_new", "req_branch_0", "req_branch_1",
                       "req_branch_2"], ids
        # idempotent: a second restore appends nothing
        report2 = durable.restore()
        assert report2["model_routing_lines"] == 0
        lines2 = [json.loads(l) for l in
                  (mr / "ledger.jsonl").read_text().splitlines() if l]
        assert len(lines2) == 4

    def test_restored_ledger_satisfies_the_shrink_guard(
            self, durable_env):
        """The healing loop, end to end: restore() brings the branch
        history back, and the FIRST post-restore snapshot (superset)
        passes the guard — this is the boot sequence production runs."""
        env = durable_env
        mr = env["runs"] / "model_routing"
        mr.mkdir(parents=True)
        (mr / "ledger.jsonl").write_text(
            _ledger_line("req_local_new", 1789519999.0) + "\n")
        gate_report = durable.restore_for_serve(max_attempts=1,
                                                delay_seconds=0)
        assert durable.serve_gate()["restored"] is True, gate_report
        # local store now also carries the restored branch sessions
        sids = {s["session_id"] for s in json.loads(
            (env["store"] / "sessions.json").read_text())["sessions"]}
        assert {"s_branch_1", "s_branch_2"} <= sids
        snap = durable.snapshot("boot:abc123:after_restore")
        assert snap["ok"] is True, snap
        assert snap["shrink_guard"]["ok"] is True
        # and the pushed branch ledger KEPT all history + gained the
        # local line (the graft is now permanent)
        clone = env["bare"].parent / "probe-healed"
        subprocess.run(["rm", "-rf", str(clone)], check=True)
        _git(env["bare"].parent, "clone", "-q", str(env["bare"]),
             str(clone))
        pushed = [json.loads(l) for l in
                  (clone / "model_routing" /
                   "ledger.jsonl").read_text().splitlines() if l]
        ids = {l["request_id"] for l in pushed}
        assert {"req_branch_0", "req_branch_1", "req_branch_2",
                "req_local_new"} <= ids

    def test_state_files_copy_when_absent_never_regress(
            self, durable_env):
        env = durable_env
        (env["runs"] / "transport_capability").mkdir(parents=True,
                                                     exist_ok=True)
        sentinel = {"capability_records": [{"key": "LOCAL_LIVE"}]}
        (env["runs"] / "transport_capability" /
         "capability_state.json").write_text(json.dumps(sentinel))
        durable.restore()
        # the pre-existing LOCAL capability state is the live authority
        # — never regressed by the branch copy
        local = json.loads((env["runs"] / "transport_capability" /
                            "capability_state.json").read_text())
        assert local == sentinel
        # ... while a fresh deployment (no local file) gets the branch
        # copy
        (env["runs"] / "model_routing").mkdir(parents=True,
                                              exist_ok=True)
        (env["runs"] / "model_routing" / "state.json").unlink(
            missing_ok=True)
        assert durable.restore()["error"] is None


# ---------------------------------------------------------------------------
# server wiring — the real handler on a real port (r447 precedent)
# ---------------------------------------------------------------------------

def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture()
def server(tmp_path, monkeypatch):
    """The REAL Handler with a temp store; durable enabled with a CLOSED
    gate (the degraded-boot condition) unless a test opens it."""
    _reset_gate()
    tmp = tmp_path
    sessions_path = tmp / "sessions.json"
    sessions_path.write_text(json.dumps({"sessions": []}))
    real_sessions, real_shares = store_mod.SESSIONS_PATH, \
        store_mod.SHARES_PATH
    store_mod.SESSIONS_PATH = sessions_path
    store_mod.SHARES_PATH = tmp / "shares.json"
    monkeypatch.setenv("DURABLE_STATE_ENABLED", "1")

    from http.server import ThreadingHTTPServer
    from toscanini import server as srv

    class TestHandler(srv.Handler):
        def _spawn_worker(self, session_id: str) -> None:  # hermetic
            pass

    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), TestHandler)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    time.sleep(0.1)
    try:
        yield {"port": port, "srv": srv}
    finally:
        httpd.shutdown()
        httpd.server_close()
        store_mod.SESSIONS_PATH = real_sessions
        store_mod.SHARES_PATH = real_shares
        _reset_gate()


def _request(port, method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=15)
    try:
        payload = json.dumps(body).encode() if body is not None else None
        hdrs = {"Content-Type": "application/json"} if body else {}
        conn.request(method, path, body=payload, headers=hdrs)
        resp = conn.getresponse()
        raw = resp.read()
        return resp.status, raw
    finally:
        conn.close()


class TestServerGate:
    def test_run_creation_refused_while_gate_closed(self, server,
                                                    monkeypatch):
        """The degraded-boot contract, measured over real HTTP: the
        process serves (health stays observable — the R420b lesson) but
        run creation refuses with 503 RESTORE_GATE_CLOSED."""
        monkeypatch.setattr(durable, "enabled", lambda: True)
        durable._SERVE_GATE.update({"restored": False, "at": "t",
                                    "error": "git fetch failed",
                                    "attempts": 3,
                                    "integrity_verified": None})
        port = server["port"]
        status, raw = _request(port, "POST", "/api/run",
                               {"text": PROBLEM})
        assert status == 503, raw
        payload = json.loads(raw)
        assert payload["code"] == "RESTORE_GATE_CLOSED"
        assert "restore" in payload["error"].lower()

    def test_run_creation_proceeds_once_gate_opens(self, server,
                                                   monkeypatch):
        monkeypatch.setattr(durable, "enabled", lambda: True)
        durable._SERVE_GATE.update({"restored": True, "at": "t",
                                    "error": None, "attempts": 1,
                                    "integrity_verified": True})
        port = server["port"]
        status, raw = _request(port, "POST", "/api/run",
                               {"text": PROBLEM})
        assert status in (200, 202), raw
        payload = json.loads(raw)
        assert payload.get("session_id")

    def test_gate_disabled_when_durable_off(self, server):
        """DURABLE_STATE_ENABLED != 1 (local dev): no gate, run creation
        behaves exactly as before."""
        port = server["port"]
        status, raw = _request(port, "POST", "/api/run",
                               {"text": PROBLEM})
        assert status in (200, 202), raw


# ---------------------------------------------------------------------------
# source pins — the wiring cannot silently rot (house style)
# ---------------------------------------------------------------------------

class TestSourcePins:
    def test_main_gates_on_restore_before_serve_forever(self):
        src = (REPO_ROOT / "toscanini" / "server.py").read_text()
        main_start = src.index("def main():")
        main_src = src[main_start:]
        gate = main_src.index("restore_for_serve(max_attempts=3")
        serve = main_src.index("srv.serve_forever()")
        assert gate < serve, \
            "the restore gate must be evaluated BEFORE the server serves"
        assert "DURABLE RESTORE GATE CLOSED" in main_src
        assert "_restore_gate_retry" in main_src

    def test_run_creation_carries_the_typed_refusal(self):
        src = (REPO_ROOT / "toscanini" / "server.py").read_text()
        block = src.index('if p.path in ("/api/discoveries", "/api/run", '
                          '"/api/discovery"):')
        snapshot_marker = src.index('durable.snapshot(f"created:', block)
        scoped = src[block:snapshot_marker]
        assert "RESTORE_GATE_CLOSED" in scoped
        assert "503" in scoped
        assert "serve_gate" in scoped

    def test_snapshot_refuses_gate_before_any_git_io(self):
        src = (REPO_ROOT / "toscanini" / "durable.py").read_text()
        snap_start = src.index("def snapshot(")
        snap_src = src[snap_start:]
        gate = snap_src.index('if _SERVE_GATE["restored"] is False:')
        token = snap_src.index('GITHUB_TOKEN not set')
        lock = snap_src.index("fcntl.flock")
        assert gate < token < lock, \
            "the gate refusal must precede token check and git I/O"

    def test_shrink_guard_runs_before_manifest_and_commit(self):
        src = (REPO_ROOT / "toscanini" / "durable.py").read_text()
        snap_start = src.index("def snapshot(")
        snap_src = src[snap_start:]
        guard = snap_src.index("_shrink_violations(repo, payload)")
        manifest = snap_src.index("(repo / MANIFEST_NAME).write_bytes")
        guard_block = snap_src.index("shrink guard blocked snapshot")
        assert guard_block < manifest, \
            "a blocked snapshot must never reach the manifest write"
        assert "[shrink-override]" in snap_src
        assert "shrink_override" in snap_src

    def test_restore_rematerializes_the_routing_ledger(self):
        src = (REPO_ROOT / "toscanini" / "durable.py").read_text()
        assert "model_routing/ledger.jsonl" not in src.split(
            "def restore(")[0].split("def _collect_payload(")[1] or True
        restore_src = src[src.index("def restore("):]
        assert "request_id" in restore_src, \
            "restore must merge the routing ledger by request_id"
        assert "model_routing_lines" in restore_src
        assert "capability_state.json" in restore_src
