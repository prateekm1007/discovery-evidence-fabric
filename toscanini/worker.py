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

R415 (P0 directive §§1, 8, 9):
  - The preflight is LADDER-AWARE: the probe is a real completion through
    the routing registry's fallback ladder (model A -> B -> C across
    providers), so a single retired model (410 GONE) no longer kills the
    run — the cascade moves to the next rung and every hop is recorded.
  - A genuinely exhausted transport (every rung failed) terminates as
    RUN_BLOCKED_TRANSPORT — a distinct infrastructure state that is
    NEVER a discovery verdict (Art. LXI), keeps the user's problem
    saved, and stays resumable through the retry path.
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


def _route_detail(probe: dict) -> str:
    """R415 (directive §1): the typed failure record for the blocked-
    transport terminal state — provider, HTTP status, model, attempt,
    timestamp, failure_class — taken from the probe's own recorded route
    (the cascade records every hop; this projects the last ones). Never
    a bare "failed"; never a key."""
    route = probe.get("route") or []
    if not route:
        return ""
    parts = []
    for hop in route[-3:]:
        parts.append(
            f"provider={hop.get('provider_attempted')} "
            f"model={hop.get('model')} "
            f"attempt={hop.get('attempts')} "
            f"failure_class={hop.get('failure_type')} "
            f"timestamp={hop.get('timestamp')}")
    return " | ".join(parts)


def run(session_id: str) -> None:
    # R419c heartbeat: the FIRST line in the worker log for every run —
    # the operator-scoped /api/ops/worker-log route serves this file's
    # tail, so a worker that dies before phase 0 is VISIBLE, not silent
    # (observed live: sessions stuck PENDING with an empty log tail gave
    # no evidence of even attempting the import chain)
    print(f"[worker] start sid={session_id} pid={os.getpid()} "
          f"blender={os.environ.get('BLENDER_PATH', '') or 'unset'}",
          file=sys.stderr, flush=True)
    s = store.get_session(session_id)
    if not s:
        print(f"session {session_id} not found", file=sys.stderr)
        sys.exit(2)

    # --- phase 0: job lifecycle (durable, restart-safe) ----------------------
    _register_running(session_id)

    # Serialize engine runs (transport protection). Held for the whole run.
    _lock_handle = _serialize_run()

    # --- phase 1: transport -------------------------------------------------
    # R415 (P0 directive §§1, 6-9): the probe is a REAL completion through
    # the routing registry's fallback LADDER — llm_registry.generate()
    # now cascades across (provider, model) rungs, so one retired model
    # (HTTP 410 GONE) demotes that model and the next rung serves the run.
    # The probe failing means EVERY rung failed — but we still give it one
    # real retry with backoff (cooldowns expire, gateways restart) before
    # declaring the routes genuinely exhausted. A second failure is
    # RUN_BLOCKED_TRANSPORT: infrastructure, never a verdict (Art. LXI),
    # the problem stays saved, resumable via retry.
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
        # directive §1: the failure record carries provider / endpoint /
        # HTTP status / model / attempt / timestamp / failure_class from
        # the probe's own typed route (never a bare "failed")
        route_detail = _route_detail(probe)
        store.update_session(
            session_id, status="RUN_BLOCKED_TRANSPORT",
            error=(f"Discovery temporarily blocked by infrastructure. "
                   f"Your problem is saved and ready to resume. "
                   f"[transport exhausted: gateway={g.get('status')} "
                   f"probe={probe.get('status')} {route_detail} "
                   f"{probe.get('error', '')}")[:400])
        _snapshot(session_id, f"terminal:RUN_BLOCKED_TRANSPORT:{session_id}")
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

    # --- phase 3.5: the automatic artifact contract (R418) -----------------
    # Operator P0 product correction: every completed run with an
    # invention gets its visual artifact + technology package
    # automatically — Case A (artifact exists -> render), Case B
    # (invention exists, artifact missing -> generate), Case C (not
    # visualizable -> conceptual fallback, labeled). No operator
    # script, no copied JSON, no manual post-processing. A bridge
    # failure is an honest typed record — it NEVER changes the run's
    # epistemic state (Art. VI/XV/LXI) and never blocks completion.
    try:
        from toscanini import bridge_gate
        gate = bridge_gate.ensure_artifacts(session_id)
        print(f"  [worker] bridge gate: {gate.get('outcome')}",
              file=sys.stderr)
        store.update_session(
            session_id,
            bridge_outcome=gate.get("outcome"),
            bridge_case=gate.get("case"))
    except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
        print(f"  [worker] bridge gate failed: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)
        store.update_session(
            session_id, bridge_outcome="GATE_ERROR",
            bridge_error=f"{type(exc).__name__}: {exc}"[:400])

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
