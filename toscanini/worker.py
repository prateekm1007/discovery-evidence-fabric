"""Discovery run worker — executes ONE UI discovery end-to-end.

Runs as a detached subprocess started by the server:

    python3 -m toscanini.worker <session_id>

Phases (all real, all persisted — the UI streams them from artifacts):
  0. job lifecycle: RUNNING + worker identity (pid/starttime) recorded
     durably (R392 directive 7 — restart never fakes success or spin)
  1. ensure LLM transport (disclosed if unavailable)
  2. evidence-bound problem build (live retrieval; MODEL_DERIVED extraction)
  3. EngineRun through the full 13-stage chain + automatic package on
     survivor (canonical factory, QA gates — the SAME path as the 15
     portfolio packages; nothing about the dossier is edited manually)
  4. terminal status recorded from the run manifest (never fabricated)
  5. durable snapshot of the epistemic record (R392 directive 5)

Art. XXV: transport/infrastructure failure -> status ERROR_* with reason;
NEVER a research kill.
"""
from __future__ import annotations

import fcntl
import os
import sys
import time
import traceback
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from toscanini import gateway as gw  # noqa: E402
from toscanini import problem_builder  # noqa: E402
from toscanini import sessions as store  # noqa: E402


def _serialize_run():
    """One engine run at a time. The zai gateway rate-limits bursts
    (measured live 2026-08-30: concurrent workers -> RATE_LIMITED_RETRY ->
    probe timeouts). Workers block on an exclusive flock instead of
    burning the transport concurrently."""
    lock = store.STORE_DIR / "run.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock, "w")
    fcntl.flock(f, fcntl.LOCK_EX)
    return f  # keep the handle open for the process lifetime


def _register_running(session_id: str) -> None:
    """R392 directive 7: the job is RUNNING with an identity a later
    process can verify — /proc pid + starttime. A restart marks this
    session INTERRUPTED (recoverable), never COMPLETE, never spinning."""
    starttime = store._proc_stat_starttime(os.getpid())
    store.update_session(session_id, status="RUNNING",
                         worker_pid=os.getpid(),
                         worker_starttime=starttime)


def _snapshot(session_id: str, reason: str) -> None:
    """Best-effort durable snapshot (R392 directive 5). Failures are
    disclosed through the health endpoint (durable.last_error), never
    silently swallowed and never fatal to the run itself."""
    try:
        from toscanini import durable
        durable.snapshot(reason)
    except Exception as exc:  # noqa: BLE001
        print(f"  [worker] durable snapshot failed ({reason}): "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)


def run(session_id: str) -> None:
    s = store.get_session(session_id)
    if not s:
        print(f"session {session_id} not found", file=sys.stderr)
        sys.exit(2)

    # --- phase 0: job lifecycle (durable, restart-safe) ----------------------
    _register_running(session_id)

    # Serialize engine runs (transport protection). Held for the whole run.
    _lock_handle = _serialize_run()

    # --- phase 1: transport -------------------------------------------------
    # R395: the public transport (registry-resolved NVIDIA) measurably
    # oscillates (R392 record: 35 s..>240 s; historical public failures
    # gateway=ALREADY_UP probe=CALL_FAILED Timeout). One REAL retry with
    # backoff before declaring ERROR_TRANSPORT — the retry is itself a
    # genuine live completion (never a skipped probe), and a second
    # failure stays exactly what it is (Art. XXV).
    g = gw.ensure_gateway()
    probeable = g["status"] in ("UP", "ALREADY_UP", "EXTERNAL")
    probe = gw.preflight_probe() if probeable else {
        "status": "NO_TRANSPORT", "error": str(g)}
    if probe.get("status") != "OK" and probeable:
        print(f"  [worker] transport probe failed ({probe.get('status')}); "
              f"one retry after 10 s backoff", file=sys.stderr)
        time.sleep(10)
        probe = gw.preflight_probe()
    if probe.get("status") != "OK":
        store.update_session(
            session_id, status="ERROR_TRANSPORT",
            error=(f"LLM transport unavailable: gateway={g.get('status')} "
                   f"probe={probe.get('status')} {probe.get('error', '')}"
                   )[:400])
        _snapshot(session_id, f"terminal:ERROR_TRANSPORT:{session_id}")
        return

    # --- phase 2: evidence-bound problem ------------------------------------
    try:
        built = problem_builder.build_problem(s["user_text"])
    except Exception as exc:  # noqa: BLE001
        store.update_session(session_id, status="ERROR_BUILD",
                             error=f"{type(exc).__name__}: {exc}"[:400])
        _snapshot(session_id, f"terminal:ERROR_BUILD:{session_id}")
        return
    problem = built["problem"]
    store.save_evidence_pack(session_id, built["evidence_pack"])
    run_dir = store.ENGINE_RUNS / f"toscanini_ui_{problem['problem_id']}"
    store.update_session(session_id,
                         problem_id=problem["problem_id"],
                         run_dir=str(run_dir),
                         domain=built["domain"])

    # --- phase 3: the engine (unchanged) -------------------------------------
    from discovery_fabric.engine.run import EngineRun
    try:
        engine = EngineRun(problem, str(run_dir), with_package=True)
        manifest = engine.run()
    except Exception as exc:  # noqa: BLE001
        store.update_session(session_id, status="ERROR_RUN",
                             error=f"{type(exc).__name__}: {exc}"[:400],
                             traceback=traceback.format_exc()[-2000:])
        _snapshot(session_id, f"terminal:ERROR_RUN:{session_id}")
        return

    # --- phase 4: honest terminal status -------------------------------------
    final = None
    fs_path = run_dir / "final_state.json"
    if fs_path.exists():
        import json
        final = json.loads(fs_path.read_text())
    store.update_session(
        session_id, status="COMPLETE",
        final_status=(final or {}).get("final_status")
        or manifest.get("final_status", "UNKNOWN"))

    # --- phase 5: durable epistemic record -----------------------------------
    _snapshot(session_id, f"terminal:COMPLETE:{session_id}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 -m toscanini.worker <session_id>", file=sys.stderr)
        sys.exit(2)
    run(sys.argv[1])
