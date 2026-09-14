"""discovery_fabric/engine/invention_bridge/ocp_guard.py — R452: the OCP
(CadQuery/OCCT) memory guard.

Constitution v2.5.0, Article LXI (class separation — an infrastructure
failure is a typed record, never a silent success and never a run
failure):

    OCCT geometry kernels can allocate unboundedly on pathological
    parameter sets. An in-process blowup kills the RUN WORKER — a
    presentation/engineering defect escalating into a run-infrastructure
    failure (exactly the class collision Article LXI forbids).

THE GUARD (two APIs):

    run_guarded_build(form, params, out_dir, name)   — the PRODUCTION
        path. Runs the CadQuery/OCCT FORM_LIBRARY build + measure +
        export in a SPAWNED clean subprocess (fresh interpreter, own
        cadquery import) with an RLIMIT_AS memory ceiling applied before
        exec and a parent-side wall-clock timeout. Returns a typed
        record; files land in out_dir; binary payloads never cross the
        boundary (the exported FILES are the authority, Art. X).

        Why spawn and not fork: MEASURED (this round) — after the parent
        process has performed ANY OCCT build, a forked child deadlocks
        inside its own build (OCCT internal locks are not fork-safe;
        classic fork-in-multithreaded-process deadlock). Spawn costs a
        fresh cadquery import (~3-5 s measured) and is safe by
        construction.

    run_guarded(fn)                                   — the GENERIC path
        for pure-Python closures (no OCCT state). Fork-based, same
        RLIMIT_AS ceiling + wall clock. CONSTRAINT: only safe when the
        parent has not built OCCT geometry before the call — the
        production geometry path must use run_guarded_build.

    Both return TYPED records:
        OK            -> {"status": "OK", "result": ...}
        OOM_KILLED    -> child died by signal / MemoryError under the cap
        TIMEOUT       -> child exceeded the wall clock and was killed
        ERROR         -> child raised (typed error recorded)

    Fail-closed: a guard that cannot run is itself a typed failure.
    The bridge demotes honestly through its existing failure ladder —
    never a silent "No 3D".

Determinism note (Art. LXII): the guard changes WHERE the build runs,
not WHAT is built — identical parameters produce identical solids.

reviewer_provenance: AI_REVIEW (Art. LXVII).
"""
from __future__ import annotations

import json
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

GUARD_VERSION = "2.0.0"

DEFAULT_MEMORY_LIMIT_MB = 1536
DEFAULT_TIMEOUT_S = 300
_SPAWN_IMPORT_BUDGET_NOTE = (
    "spawned clean interpreter; includes the child's own cadquery import "
    "(measured 3-5 s this round)")

GUARD_BASIS = (
    "spawned subprocess with pre-exec RLIMIT_AS ceiling + parent "
    "wall-clock timeout (R452, Art. LXI class separation); fork was "
    "measured unsafe after any parent OCCT build (deadlock) — see module "
    "docstring")

REPO_ROOT = Path(__file__).resolve().parents[3]


def _memory_limit_bytes(memory_limit_mb: int) -> int:
    return int(memory_limit_mb) * 1024 * 1024


# ---------------------------------------------------------------------------
# The PRODUCTION path: spawn-based guarded FORM_LIBRARY build
# ---------------------------------------------------------------------------

_CHILD_ARGV = [
    sys.executable, "-m",
    "discovery_fabric.engine.invention_bridge.ocp_guard",
]


def run_guarded_build(form: str, params: Dict[str, float],
                      out_dir: str, name: str = "engineering_model",
                      memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
                      timeout_s: int = DEFAULT_TIMEOUT_S,
                      ) -> Dict[str, Any]:
    """Build + measure + export one FORM_LIBRARY form in a spawned,
    memory-capped, time-limited child process.

    Returns {"status": "OK", "result": {"key_dimensions": ...,
    "exported": {paths + hashes, no binary}}} on success, else a typed
    failure record. The exported files (STEP/STL/GLB) in out_dir are the
    authority (Art. X); the parent re-reads bytes from disk.
    """
    record: Dict[str, Any] = {
        "guard": "OCP_MEMORY_GUARD",
        "guard_version": GUARD_VERSION,
        "guard_basis": GUARD_BASIS,
        "memory_limit_mb": int(memory_limit_mb),
        "timeout_s": int(timeout_s),
        "form": form,
    }
    fd, result_path = tempfile.mkstemp(prefix="ocp_guard_", suffix=".json")
    os.close(fd)
    try:
        payload = json.dumps({"form": form, "params": params,
                              "out_dir": out_dir, "name": name,
                              "result_path": result_path})
        proc = subprocess.Popen(
            _CHILD_ARGV + [payload],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True,
            env=_child_env(),
            preexec_fn=_make_rlimit(memory_limit_mb),
        )
    except OSError as exc:
        _cleanup(result_path)
        record.update({"status": "ERROR",
                       "error": f"guard spawn failed: {exc}"})
        return record

    try:
        stdout, stderr = proc.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.communicate()
        _cleanup(result_path)
        record.update({
            "status": "TIMEOUT",
            "error": (f"child exceeded the {timeout_s}s wall clock and "
                      "was killed"),
            "note": _SPAWN_IMPORT_BUDGET_NOTE,
        })
        return record

    exit_code = proc.returncode
    loaded = None
    try:
        if Path(result_path).is_file():
            loaded = json.loads(Path(result_path).read_text())
    except Exception as exc:  # noqa: BLE001 — corrupt record is typed
        record.update({"status": "ERROR",
                       "error": f"guard result unreadable: {exc}",
                       "exit_code": exit_code})
        _cleanup(result_path)
        return record
    _cleanup(result_path)

    if loaded is not None and loaded.get("status") == "OK":
        record.update(loaded)
        record["exit_code"] = exit_code
        return record
    if loaded is not None:
        record.update(loaded)
        record["exit_code"] = exit_code
        record.setdefault(
            "error", loaded.get("error") or "typed child failure")
        return record
    # no result file: signal death or crash before writing
    if exit_code is not None and exit_code < 0:
        sig = -exit_code
        record.update({
            "status": "OOM_KILLED" if sig in (signal.SIGKILL, signal.SIGSEGV)
            else "ERROR",
            "signal": int(sig),
            "error": (f"child died on signal {sig} — memory ceiling "
                      f"{memory_limit_mb} MB or kernel fault"),
        })
    else:
        record.update({
            "status": "ERROR",
            "exit_code": exit_code,
            "error": (f"child exited {exit_code} without a typed record; "
                      f"stderr: {stderr[-500:] if stderr else ''}"),
        })
    return record


def _child_env() -> Dict[str, str]:
    env = dict(os.environ)
    py = str(REPO_ROOT)
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = f"{py}{os.pathsep}{existing}" if existing else py
    return env


def _make_rlimit(memory_limit_mb: int) -> Callable[[], None]:
    def _apply():  # runs in the child BEFORE exec — safe
        limit = _memory_limit_bytes(memory_limit_mb)
        resource.setrlimit(resource.RLIMIT_AS, (limit, limit))
    return _apply


def _child_main(payload_json: str) -> None:
    """The spawned child entry: build, measure, export, write the typed
    result JSON. Never raises into the parent — every failure is typed."""
    status = "OK"
    out: Dict[str, Any] = {}
    exit_code = 0
    try:
        spec = json.loads(payload_json)
        from discovery_fabric.engine.invention_bridge import (
            engineering_geometry)
        builder = engineering_geometry.FORM_LIBRARY[spec["form"]]
        solid = builder(spec["params"])
        key_dims = engineering_geometry.measure(solid)
        exported = engineering_geometry.export(
            solid, spec["name"], spec["out_dir"],
            component_solids=[(spec["name"], solid)])
        out = {"result": {
            "key_dimensions": key_dims,
            "exported": {k: v for k, v in exported.items()
                         if k != "glb_bytes"},
        }}
    except MemoryError:
        status, exit_code = "OOM_KILLED", 4
        out = {"error": "MemoryError under the RLIMIT_AS cap"}
    except BaseException as exc:  # noqa: BLE001 — typed, never silent
        status, exit_code = "ERROR", 3
        out = {"error": f"{type(exc).__name__}: {exc}"}
    try:
        Path(spec["result_path"]).write_text(json.dumps(
            {"status": status, **out}, default=str))
    except BaseException:  # noqa: BLE001 — record best effort
        pass
    sys.exit(exit_code)


# ---------------------------------------------------------------------------
# The GENERIC path: fork-based guard for pure-Python closures (NO OCCT
# state in the parent — see module docstring for the measured constraint)
# ---------------------------------------------------------------------------

def run_guarded(fn: Callable[[], Any],
                memory_limit_mb: int = DEFAULT_MEMORY_LIMIT_MB,
                timeout_s: int = DEFAULT_TIMEOUT_S) -> Dict[str, Any]:
    """Run fn() in a memory-capped, time-limited forked child.

    fn must return a JSON-serializable dict. CONSTRAINT (measured this
    round): only safe when the parent has NOT built OCCT geometry before
    this call — OCCT locks are not fork-safe. The production geometry
    path uses run_guarded_build (spawn) instead.
    """
    record: Dict[str, Any] = {
        "guard": "OCP_MEMORY_GUARD",
        "guard_version": GUARD_VERSION,
        "guard_basis": GUARD_BASIS,
        "memory_limit_mb": int(memory_limit_mb),
        "timeout_s": int(timeout_s),
    }
    try:
        fd, result_path = tempfile.mkstemp(
            prefix="ocp_guard_", suffix=".json")
        os.close(fd)
    except OSError as exc:
        record.update({"status": "ERROR",
                       "error": f"guard setup failed: {exc}"})
        return record

    pid = os.fork()
    if pid == 0:
        # ---------------- child: capped execution ----------------------
        status = "OK"
        payload: Dict[str, Any] = {}
        exit_code = 0
        try:
            resource.setrlimit(
                resource.RLIMIT_AS,
                (_memory_limit_bytes(memory_limit_mb),
                 _memory_limit_bytes(memory_limit_mb)))
            result = fn()
            payload = {"result": result}
        except MemoryError:
            status = "OOM_KILLED"
            payload = {"error": "MemoryError under the RLIMIT_AS cap"}
            exit_code = 4
        except BaseException as exc:  # noqa: BLE001 — typed, never silent
            status = "ERROR"
            payload = {"error": f"{type(exc).__name__}: {exc}"}
            exit_code = 3
        try:
            Path(result_path).write_text(json.dumps(
                {"status": status, **payload}, default=str))
        except BaseException:  # noqa: BLE001 — record best effort
            pass
        os._exit(exit_code)

    # ---------------- parent: monitor with timeout ----------------------
    deadline = time.monotonic() + timeout_s
    child_status: Optional[int] = None
    while True:
        waited, wait_stat = os.waitpid(pid, os.WNOHANG)
        if waited == pid:
            child_status = wait_stat
            break
        if time.monotonic() > deadline:
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            os.waitpid(pid, 0)
            record.update({
                "status": "TIMEOUT",
                "error": (f"child exceeded the {timeout_s}s wall clock "
                          "and was killed"),
            })
            _cleanup(result_path)
            return record
        time.sleep(0.02)

    if os.WIFSIGNALED(child_status):
        sig = os.WTERMSIG(child_status)
        record.update({
            "status": "OOM_KILLED" if sig in (signal.SIGKILL,
                                              signal.SIGSEGV) else "ERROR",
            "signal": int(sig),
            "error": (f"child died on signal {sig} — memory ceiling "
                      f"{memory_limit_mb} MB or kernel fault"),
        })
        _cleanup(result_path)
        return record

    exit_code = os.WEXITSTATUS(child_status)
    try:
        loaded = json.loads(Path(result_path).read_text())
    except Exception as exc:  # noqa: BLE001 — corrupt record is typed
        record.update({"status": "ERROR",
                       "error": f"guard result unreadable: {exc}",
                       "exit_code": exit_code})
        _cleanup(result_path)
        return record
    _cleanup(result_path)
    record.update(loaded)
    record["exit_code"] = exit_code
    return record


def _cleanup(path: str) -> None:
    try:
        os.unlink(path)
    except OSError:
        pass


def typed_failure_message(guard_record: Dict[str, Any]) -> str:
    """The bridge demotes through its existing failure ladder with this
    typed reason (Art. LXI: infrastructure failure is never a silent
    success and never a scientific rejection)."""
    return (f"OCP_MEMORY_GUARD_{guard_record.get('status')}: "
            f"{guard_record.get('error') or 'no detail'} "
            f"(cap {guard_record.get('memory_limit_mb')} MB, "
            f"timeout {guard_record.get('timeout_s')}s)")


if __name__ == "__main__":
    if len(sys.argv) == 2:
        _child_main(sys.argv[1])
    else:
        sys.exit(2)
