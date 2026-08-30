"""Discovery run worker — executes ONE UI discovery end-to-end.

Runs as a detached subprocess started by the server:

    python3 -m toscanini.worker <session_id>

Phases (all real, all persisted — the UI streams them from artifacts):
  1. ensure zai gateway transport (disclosed if unavailable)
  2. evidence-bound problem build (live retrieval; MODEL_DERIVED extraction)
  3. EngineRun through the full 13-stage chain + automatic package on
     survivor (canonical factory, QA gates — the SAME path as the 15
     portfolio packages; nothing about the dossier is edited manually)
  4. terminal status recorded from the run manifest (never fabricated)

Art. XXV: transport/infrastructure failure -> status ERROR_* with reason;
NEVER a research kill.
"""
from __future__ import annotations

import fcntl
import sys
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


def run(session_id: str) -> None:
    s = store.get_session(session_id)
    if not s:
        print(f"session {session_id} not found", file=sys.stderr)
        sys.exit(2)

    # Serialize engine runs (transport protection). Held for the whole run.
    _lock_handle = _serialize_run()

    # --- phase 1: transport -------------------------------------------------
    g = gw.ensure_gateway()
    probe = gw.preflight_probe() if g["status"] in ("UP", "ALREADY_UP") else {
        "status": "GATEWAY_DOWN", "error": str(g)}
    if probe.get("status") != "OK":
        store.update_session(
            session_id, status="ERROR_TRANSPORT",
            error=(f"LLM transport unavailable: gateway={g.get('status')} "
                   f"probe={probe.get('status')} {probe.get('error', '')}"
                   )[:400])
        return

    # --- phase 2: evidence-bound problem ------------------------------------
    try:
        built = problem_builder.build_problem(s["user_text"])
    except Exception as exc:  # noqa: BLE001
        store.update_session(session_id, status="ERROR_BUILD",
                             error=f"{type(exc).__name__}: {exc}"[:400])
        return
    problem = built["problem"]
    store.save_evidence_pack(session_id, built["evidence_pack"])
    run_dir = store.ENGINE_RUNS / f"toscanini_ui_{problem['problem_id']}"
    store.update_session(session_id, status="RUNNING",
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


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python3 -m toscanini.worker <session_id>", file=sys.stderr)
        sys.exit(2)
    run(sys.argv[1])
