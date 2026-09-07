"""toscanini/artifact_worker.py — R419 §21 + R420: the async render job.

The render job (Blender 5.2 LTS headless over the run's authoritative
GLB) is a DETACHED subprocess — the web request that enqueues it never
waits for Blender (operator directive section 21: POST artifact-build
-> job -> worker -> Blender -> artifacts -> persisted).

R420 (operator directive, sections 1/3/7) — the render path is
AUTONOMOUS and RESTART-SAFE:

  * AUTO-ENQUEUE: when the in-worker render is skipped or fails for a
    typed infrastructure reason (RENDER_SKIPPED_LOW_MEMORY,
    RENDER_TIMEOUT, RENDER_FAILED, ...), the production WORKER calls
    auto_enqueue() at the end of the run (after the gauntlet worker's
    memory is freed). No operator intervention, no copied JSON, no
    user-side regeneration. The boot sweep additionally re-enqueues
    runs that died before their render ever completed.
  * RESTART CONTRACT (implemented, not claimed): the job record
    MODEL/3D/RENDER_JOB.json is the authority (Art. X). A job whose
    record says RUNNING is live ONLY while its recorded pid+starttime
    still resolves to a live process. At boot,
    recover_interrupted_jobs() marks every dead-RUNNING job INTERRUPTED
    and re-enqueues it — deterministic, observable (the record itself,
    the boot log line, and /api/ops/artifact-log). A terminal record
    (OK / PARTIAL / typed skip / FAILED) is never re-run by recovery;
    renders already on disk are never re-rendered (idempotent).
  * QUALITY LADDER: each job makes up to three bounded attempts
    (48 samples / 1152x768 / 900 s -> 16 / 960x640 / 420 s ->
    6 / 768x512 / 240 s; provenance:
    discovery_fabric/engine/invention_bridge/render_threshold_provenance.json).
    The achieved quality is recorded and projected — a degraded render
    is disclosed, never passed off as full quality. Three rungs, then
    the honest terminal typed state. No infinite retry.
  * SERIALIZATION: one Blender process per container at a time
    (flock ENGINE_RUNS/render.lock) — concurrent jobs wait; a render
    never competes with itself for the instance's memory.
  * PERSISTENCE: completed renders are snapshotted to the durable
    runtime-state branch immediately (durable.snapshot), so they
    survive the next container restart (the filesystem is ephemeral).

Job contract:
    * idempotent: existing renders are never re-run (the job inspects
      MODEL/3D/ before starting; re-enqueue is a no-op read-back)
    * typed: every outcome is a JSON record, never a silent gap
      (OK / PARTIAL / INTERRUPTED / RENDER_SKIPPED_NO_BLENDER /
      RENDER_SKIPPED_LOW_MEMORY / RENDER_FAILED / RENDER_TIMEOUT —
      the render stage's own vocabulary, Art. LXI: infrastructure
      failure is never science)
    * presentation-only: Blender never alters the engineering truth
      (operator section 7; the render record carries the topology
      comparison). A successful render changes NO epistemic field of
      the run (Art. XXVIII/LXI) — maturity, class and evidence are
      untouched by this module.

This module is a thin enqueue/job-record layer; the render itself is
discovery_fabric.engine.invention_bridge.render (the pinned-build
orchestrator) and blender_render.py (the Blender-side script).
"""
from __future__ import annotations

import fcntl
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import sessions as store

REPO_ROOT = Path(__file__).resolve().parent.parent

_JOB_LOCK = "RENDER_JOB.json"


def _run_lock_path() -> Path:
    """The SAME exclusive lock file the discovery run worker holds for
    its whole lifetime (worker._serialize_run: store.STORE_DIR /
    'run.lock' — the EXISTING production path, unchanged). The async
    render job acquires it around each Blender attempt — on the 512 MB
    instance there must be EXACTLY ONE heavy process at a time (an
    engine run OR a render); without this mutual exclusion the
    background recovery renders OOM-killed live run workers (observed
    live 2026-09-07: the fresh run ts_a5a7eee35361's worker died and
    the container restarted at 23:04 while the boot-recovery Blender
    held memory)."""
    p = store.STORE_DIR / "run.lock"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _try_run_lock_nonblocking():
    """(handle, acquired) — used by tests and diagnostics; the job
    itself uses the blocking acquire."""
    f = open(_run_lock_path(), "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f, True
    except OSError:
        f.close()
        return None, False

# R420 quality ladder — bounded, typed, provenance in
# render_threshold_provenance.json (Art. XXVII). Each rung:
# (samples, [width, height], budget_seconds)
QUALITY_LADDER = (
    (48, [1152, 768], 900),
    (16, [960, 640], 420),
    (6, [768, 512], 240),
)

_TERMINAL_OK = ("OK", "PARTIAL")


def _job_path(session_id: str) -> Optional[Path]:
    s = store.get_session(session_id)
    if not s or not s.get("run_dir"):
        return None
    return Path(s["run_dir"]) / "MODEL" / "3D" / _JOB_LOCK


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def renderables_present(session: Dict[str, Any]) -> bool:
    """A renderable run: an authoritative GLB exists (MODEL/*.glb or a
    root GLB). No GLB -> the job is honestly refused (409 at the API
    layer; never a fabricated render)."""
    if not session.get("run_dir"):
        return False
    run_dir = Path(session["run_dir"])
    if not run_dir.exists():
        return False
    model = run_dir / "MODEL"
    glbs = list(model.glob("*.glb")) if model.exists() \
        else list(run_dir.glob("*.glb"))
    return bool(glbs)


def _png_intact(path: Path) -> bool:
    """Structural PNG integrity: magic bytes + IEND trailer. A Blender
    subprocess killed mid-render leaves a TRUNCATED png on disk —
    size>0 is not completeness (the idempotency contract must not
    mistake a corpse for a render)."""
    try:
        with open(path, "rb") as f:
            head = f.read(8)
            f.seek(-12, os.SEEK_END)
            tail = f.read(12)
    except OSError:
        return False
    return head == b"\x89PNG\r\n\x1a\n" and b"IEND" in tail


def _render_record_sha(d: Path, name: str,
                       record: Optional[Dict[str, Any]]) -> Optional[str]:
    """The sha256 the blender-side render record declares for `name`
    (None when the record has no verdict for it)."""
    if not record:
        return None
    entry = (record.get("renders") or {}).get(name) or {}
    sha = entry.get("sha256")
    return sha if isinstance(sha, str) else None


def _file_sha(d: Path, name: str) -> Optional[str]:
    import hashlib
    h = hashlib.sha256()
    try:
        with open(d / name, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
    except OSError:
        return None
    return h.hexdigest()


def render_artifacts_complete(session: Dict[str, Any]) -> bool:
    """The observable presentation contract (hero/section/exploded PNGs)
    is already on disk — INTACT, not merely present. Per artifact:

      * when the render record declares a sha256 for it, the file MUST
        match byte-for-byte (a mismatch is corruption — never accepted,
        never 'fixed' by the structural fallback);
      * otherwise structural PNG integrity (magic + IEND) decides.

    A truncated render from a killed job is NOT complete (a size>0
    corpse must not satisfy the idempotency contract)."""
    if not session.get("run_dir"):
        return False
    d = Path(session["run_dir"]) / "MODEL" / "3D"
    if not d.exists():
        return False
    record = job_record_file(d)
    for n in ("hero.png", "section.png", "exploded.png"):
        p = d / n
        if not p.is_file() or p.stat().st_size == 0:
            return False
        declared = _render_record_sha(d, n, record)
        if declared is not None:
            if _file_sha(d, n) != declared:
                return False
            continue
        if not _png_intact(p):
            return False
    return True


def job_record_file(d: Path) -> Optional[Dict[str, Any]]:
    """The blender-side render record from MODEL/3D/render_record.json."""
    p = d / "render_record.json"
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def job_record(session_id: str) -> Optional[Dict[str, Any]]:
    """The persisted job record (the file is the authority)."""
    p = _job_path(session_id)
    if not p or not p.is_file():
        return None
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001 — corrupt record -> re-runnable
        return None


def _write_job(session_id: str, record: Dict[str, Any]) -> Dict[str, Any]:
    p = _job_path(session_id)
    if p is None:
        return record
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(record, indent=2))
    return record


def _job_alive(record: Dict[str, Any]) -> Optional[bool]:
    """Liveness of the job process recorded in the job record — the
    R392 directive-7 pattern (pid + /proc starttime) applied to render
    jobs. True/False when determinable; None when the record predates
    the identity fields (legacy record — never guessed, Art. XXV)."""
    pid = record.get("worker_pid")
    if not pid:
        return None
    starttime = record.get("worker_starttime")
    live = store._proc_stat_starttime(pid)
    if live is None:
        return False
    if starttime and live != str(starttime):
        return False  # pid reused by a different process
    return True


def enqueue(session_id: str, enqueued_by: str = "api") -> Dict[str, Any]:
    """Enqueue the detached render job. Returns the job record.

    Idempotency + liveness (R420): a RUNNING record whose recorded
    process is STILL ALIVE is returned as-is (one Blender process per
    run at a time). A RUNNING record whose process is dead (crashed
    worker, container restart) is marked INTERRUPTED in its own record
    — the deterministic recovery trail — and re-enqueued. A terminal
    record with renders already on disk reads back ALREADY_PRESENT.

    The record carries the spawned job's pid + /proc starttime FROM
    THE MOMENT OF ENQUEUE (no identity-less window: liveness is
    decidable at every instant after enqueue — R392 directive-7
    pattern applied to render jobs).
    """
    prior = job_record(session_id)
    trail: Dict[str, Any] = {}
    if prior and prior.get("status") == "RUNNING":
        alive = _job_alive(prior)
        if alive is True:
            # a live detached job owns this run's render — honest 202
            return prior
        # dead RUNNING (restart/crash) — record the interruption, re-enqueue
        interrupted = prior | {
            "status": "INTERRUPTED",
            "interrupted_at": _now(),
            "interruption_reason": (
                "job process (pid "
                f"{prior.get('worker_pid')}) no longer running — crash "
                "or container restart; recovery re-enqueued it "
                "(deterministic restart contract, R420 §3)"),
        }
        _write_job(session_id, interrupted)
        trail = {k: interrupted[k] for k in
                 ("interrupted_at", "interruption_reason",
                  "attempt_history") if k in interrupted}

    if prior and prior.get("status") in _TERMINAL_OK \
            and render_artifacts_complete(store.get_session(session_id) or {}):
        return prior | {"readback": "ALREADY_PRESENT"}

    proc = _spawn_job(session_id)
    starttime = store._proc_stat_starttime(proc.pid)
    record = {
        "artifact": "RENDER_JOB",
        "session_id": session_id,
        "status": "RUNNING",
        "enqueued_at": _now(),
        "enqueued_by": enqueued_by,
        "worker_pid": proc.pid,
        "worker_starttime": starttime,
        "pipeline": "BLENDER_HEADLESS",
        "note": ("async artifact build — the web request never waits "
                 "for Blender; poll the render routes or the CIO's "
                 "visualization.renders"),
    } | trail
    return _write_job(session_id, record)


def _spawn_job(session_id: str) -> subprocess.Popen:
    # R420b: the log parent must exist before open() (a fresh container
    # whose ENGINE_RUNS has not been restored yet must not crash the
    # enqueue path — spawn hygiene is part of the autonomous contract)
    try:
        (REPO_ROOT / "ENGINE_RUNS").mkdir(parents=True, exist_ok=True)
    except OSError:
        pass
    return subprocess.Popen(
        [sys.executable, "-m", "toscanini.artifact_worker", session_id],
        cwd=str(REPO_ROOT),
        stdout=open(REPO_ROOT / "ENGINE_RUNS" / "artifact_worker.log", "ab"),
        stderr=subprocess.STDOUT,
        start_new_session=True,
        env=dict(os.environ),
    )


def needs_render_followup(session: Dict[str, Any]) -> Optional[str]:
    """R420 §1 — the state-based decision the production worker and the
    boot sweep both use. Returns WHY the async job is required, or None.

    Rule (all must hold):
      1. the run has an authoritative GLB (there is something to render)
      2. the presentation artifacts are NOT already on disk
      3. no live render job owns the run right now
      4. no TERMINAL job record exists — once the async job has spoken
         (OK / PARTIAL / typed skip / FAILED), its verdict stands for
         this environment; re-attempting is an explicit action (the
         internal endpoint or a session retry), never an automatic
         loop (no boot-time retry storm)

    INTERRUPTED is not terminal (an interrupted job owes a retry or a
    terminal verdict). Pure function of persisted state (Art. X): no
    clocks, no guesses.
    """
    if not renderables_present(session):
        return None
    if render_artifacts_complete(session):
        return None
    prior = job_record(session.get("session_id") or "")
    if prior:
        status = prior.get("status")
        if status == "RUNNING" and _job_alive(prior) is True:
            return None  # already in flight
        if status not in ("RUNNING", "INTERRUPTED"):
            return None  # the async job already spoke — terminal
    session_id = session.get("session_id") or ""
    render_stage = _bridge_render_status(session)
    if render_stage:
        return f"in-worker render ended {render_stage} — async completion"
    if prior and prior.get("status") == "INTERRUPTED":
        return "render job was interrupted — recovery re-enqueue"
    return "presentation renders missing — async completion"


def _bridge_render_status(session: Dict[str, Any]) -> Optional[str]:
    """The typed status the in-worker render recorded in the bridge
    report (WHY the followup exists — evidenced, not asserted)."""
    if not session.get("run_dir"):
        return None
    br = Path(session["run_dir"]) / "BRIDGE_REPORT.json"
    if not br.is_file():
        return None
    try:
        report = json.loads(br.read_text())
    except Exception:  # noqa: BLE001
        return None
    renders = report.get("renders") or {}
    status = renders.get("status")
    if status in ("OK", "ALREADY_PRESENT"):
        return None
    return status if isinstance(status, str) else None


def auto_enqueue(session_id: str, enqueued_by: str = "worker") \
        -> Optional[Dict[str, Any]]:
    """R420 §1 — the automatic handoff the production worker performs
    at the END of the run (its memory is freed by then; the async
    guard decides honestly whether the instance can render now).

    Returns the job record when a followup was needed, None when the
    state already satisfies the render contract (or nothing to render).
    Never raises into the caller (the run is complete; a presentation
    followup can not be allowed to damage the terminal record)."""
    try:
        session = store.get_session(session_id)
        if not session:
            return None
        why = needs_render_followup(session)
        if not why:
            return None
        record = enqueue(session_id, enqueued_by=enqueued_by)
        return record | {"followup_reason": why}
    except Exception:  # noqa: BLE001 — disclosed via the job log, typed
        print(f"[artifact_worker] auto_enqueue failed for {session_id}: "
              f"{sys.exc_info()[0].__name__}", file=sys.stderr, flush=True)
        return None


def recover_interrupted_jobs() -> List[Dict[str, Any]]:
    """R420 §3 — BOOT-ONLY sweep: the deterministic, observable restart
    contract. A job left RUNNING across a container restart (its
    process died with the previous container) is marked INTERRUPTED in
    its own record and re-enqueued; a record already INTERRUPTED (the
    re-enqueue itself died before starting) is re-enqueued too. Safe
    only at boot, before any new job can be spawned (mirrors
    mark_boot_pending_interrupted).
    """
    recovered: List[Dict[str, Any]] = []
    for s in store.list_sessions():
        sid = s.get("session_id") or ""
        prior = job_record(sid)
        if not prior:
            continue
        if prior.get("status") == "RUNNING":
            alive = _job_alive(prior)
            if alive is True:
                # impossible at boot (defensive) — never interrupt a
                # live job
                continue
            prior = _write_job(sid, prior | {
                "status": "INTERRUPTED",
                "interrupted_at": _now(),
                "interruption_reason": (
                    "container restart killed the job process (pid "
                    f"{prior.get('worker_pid')}) — boot recovery "
                    "re-enqueued it (deterministic restart contract, "
                    "R420 §3)"),
            })
        elif prior.get("status") != "INTERRUPTED":
            continue  # terminal — its own verdict stands
        record = enqueue(sid, enqueued_by="boot_restart_recovery")
        recovered.append({"session_id": sid,
                          "interrupted": prior.get("interrupted_at"),
                          "re_enqueued": record.get("enqueued_at")})
    return recovered


def boot_render_recovery() -> List[Dict[str, Any]]:
    """R420 §1/§7 — BOOT-ONLY sweep: completed runs whose render path
    never finished (typed in-worker skip/failure with no followup —
    e.g. the pre-R420 runs) get their async job enqueued at boot. The
    job record the sweep creates makes the recovery ONE-SHOT: later
    boots see the terminal record and do not re-enqueue (no storm).

    Scope: sessions with a run_dir + authoritative GLB + missing
    presentation artifacts + no RENDER_JOB.json at all, whose run is
    terminal (COMPLETE/INTERRUPTED — never a live run mid-flight).
    """
    enqueued: List[Dict[str, Any]] = []
    for s in store.list_sessions():
        sid = s.get("session_id") or ""
        if s.get("status") not in ("COMPLETE", "INTERRUPTED"):
            continue
        if not renderables_present(s):
            continue
        if render_artifacts_complete(s):
            continue
        if job_record(sid):
            continue  # a record exists — its own state governs
        record = enqueue(sid, enqueued_by="boot_render_recovery")
        enqueued.append({"session_id": sid,
                         "enqueued_at": record.get("enqueued_at"),
                         "reason": needs_render_followup(s)})
    return enqueued


def _wait_for_run_worker_exit(session_id: str, max_s: int = 120) -> bool:
    """Bounded wait for the run worker process to exit (the async
    context's memory is only actually free once it has). Returns True
    when the worker is gone (or was never running), False on timeout —
    the render proceeds either way; the memory guard decides honestly."""
    deadline = time.time() + max_s
    while True:
        s = store.get_session(session_id)
        if not s or not s.get("worker_pid"):
            return True
        if not store.worker_alive(s):
            return True
        if time.time() >= deadline:
            print(f"[artifact_worker] {session_id}: run worker "
                  f"(pid {s.get('worker_pid')}) still alive after {max_s}s "
                  "— proceeding (the memory guard decides honestly)",
                  file=sys.stderr, flush=True)
            return False
        time.sleep(2)


def _acquire_render_lock():
    """One Blender subprocess per container at a time. Concurrent
    artifact jobs block here (they are detached — blocking is cheap);
    a render never competes with itself for instance memory."""
    lock = store.ENGINE_RUNS / "render.lock"
    lock.parent.mkdir(parents=True, exist_ok=True)
    f = open(lock, "w")
    fcntl.flock(f, fcntl.LOCK_EX)
    return f


def _acquire_run_lock_blocking():
    """R420c: block until no discovery run worker is active, then hold
    the run lock for ONE render attempt (bounded by the attempt's
    budget). A fresh user run therefore waits at most one attempt
    (<= 900 s) before its worker proceeds — the calm, correct price
    of a 512 MB instance. The run worker holds this same lock for its
    whole lifetime, so an engine run and a Blender never overlap."""
    f = open(_run_lock_path(), "w")
    fcntl.flock(f, fcntl.LOCK_EX)  # blocking — jobs are patient
    return f


def run(session_id: str) -> Dict[str, Any]:
    """The job body: run the render stage over the authoritative GLB,
    through the bounded quality ladder, under the render lock.

    Writes the terminal job record (the file is the authority) and
    snapshots the completed artifacts to the durable runtime-state
    branch so they survive the next restart."""
    from discovery_fabric.engine.invention_bridge import render

    s = store.get_session(session_id)
    if not s or not s.get("run_dir"):
        return _write_job(session_id, {
            "artifact": "RENDER_JOB", "session_id": session_id,
            "status": "FAILED", "at": _now(),
            "error": "session or run directory not found"})

    run_dir = Path(s["run_dir"])
    # honest class label from the persisted CIO when present
    vis_class = None
    cio_files = [run_dir / "CIO.json", run_dir / "cio.json"]
    for cf in cio_files:
        if cf.is_file():
            try:
                cio = json.loads(cf.read_text())
                geo = cio.get("geometry") or {}
                vis_class = geo.get("visualizability_class") \
                    or geo.get("class")
            except Exception:  # noqa: BLE001
                pass
            break

    # idempotent: renders already on disk are never re-rendered
    if render_artifacts_complete(s):
        return _write_job(session_id, {
            "artifact": "RENDER_JOB", "session_id": session_id,
            "status": "OK", "at": _now(),
            "readback": "ALREADY_PRESENT",
            "note": "presentation artifacts verified on disk — no re-render"})

    # the job's own identity: pid + starttime (the restart contract
    # reads exactly these fields — a restart kills this pid, recovery
    # observes it dead and re-enqueues). Merged over the enqueue record
    # so the enqueued_by / interruption trail survives.
    prior = job_record(session_id) or {}
    _write_job(session_id, prior | {
        "artifact": "RENDER_JOB", "session_id": session_id,
        "status": "RUNNING",
        "worker_pid": os.getpid(),
        "worker_starttime": store._proc_stat_starttime(os.getpid()),
        "pipeline": "BLENDER_HEADLESS",
        "note": "async artifact build — detached render job running"})

    # R420: the worker enqueues this job at the END of the run but the
    # worker PROCESS is still finishing its durable snapshot — the whole
    # point of the async context is the freed gauntlet memory, so the
    # job waits (bounded) for the run worker to actually exit before
    # the memory guard runs. Observable in the job log.
    _wait_for_run_worker_exit(session_id, max_s=120)

    lock_handle = _acquire_render_lock()
    try:
        attempts: List[Dict[str, Any]] = []
        rec: Dict[str, Any] = {}
        for idx, (samples, resolution, budget_s) in enumerate(
                QUALITY_LADDER, start=1):
            # R420c: mutual exclusion with the discovery runs — hold
            # the run lock for exactly one attempt (an engine run and
            # a Blender must never share the 512 MB instance)
            run_lock = _acquire_run_lock_blocking()
            try:
                try:
                    rec = render.render_invention(
                        str(run_dir), {"generation_models": None},
                        is_conceptual=vis_class != "ENGINEERING_3D",
                        memory_mode="async",
                        samples=samples, resolution=resolution,
                        timeout_s=budget_s)
                except Exception as exc:  # noqa: BLE001 — typed, never silent
                    rec = {"stage": "RENDER", "status": "RENDER_FAILED",
                           "error": f"{type(exc).__name__}: {exc}"}
            finally:
                try:
                    run_lock.close()
                except Exception:  # noqa: BLE001
                    pass
            attempts.append({
                "attempt": idx,
                "samples": samples,
                "resolution": resolution,
                "budget_seconds": budget_s,
                "status": rec.get("status", "UNKNOWN"),
            })
            print(f"[artifact_worker] {session_id} attempt {idx} "
                  f"(samples={samples}, {resolution[0]}x{resolution[1]}): "
                  f"{rec.get('status')}", file=sys.stderr, flush=True)
            if rec.get("status") in ("OK", "PARTIAL"):
                break
            # a skip that the same environment will repeat identically
            # (no pinned build at all) ends the ladder now — honest
            # terminal state, no wasted rungs
            if rec.get("status") == "RENDER_SKIPPED_NO_BLENDER":
                break
    finally:
        try:
            lock_handle.close()
        except Exception:  # noqa: BLE001
            pass

    status = {
        "OK": "OK", "RENDER_PARTIAL": "PARTIAL",
    }.get(rec.get("status", ""), rec.get("status", "UNKNOWN"))

    record = _write_job(session_id, (job_record(session_id) or {}) | {
        "artifact": "RENDER_JOB",
        "session_id": session_id,
        "status": status,
        "at": _now(),
        "quality_ladder": [
            {"samples": s_, "resolution": r, "budget_seconds": b}
            for s_, r, b in QUALITY_LADDER],
        "attempts": attempts,
        "render_record": {
            k: rec.get(k) for k in
            ("status", "render_pipeline", "pinned_blender",
             "blender_version_verified", "source_glb_sha256",
             "artifacts", "missing_artifacts", "seconds", "note",
             "error", "threshold_provenance")},
    })

    # R420 persistence: completed renders ride the durable snapshot
    # immediately — they must survive the next container restart (the
    # filesystem is ephemeral; Art. X: the branch + files agree).
    if status in _TERMINAL_OK:
        try:
            from toscanini import durable
            durable.snapshot(f"render_complete:{session_id}")
        except Exception as exc:  # noqa: BLE001 — disclosed, never fatal
            print(f"[artifact_worker] durable snapshot after render "
                  f"failed ({session_id}): {type(exc).__name__}: {exc}",
                  file=sys.stderr, flush=True)

    return record


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python -m toscanini.artifact_worker <session_id>",
              file=sys.stderr)
        sys.exit(2)
    out = run(sys.argv[1])
    print(f"[artifact_worker] {sys.argv[1]}: {out.get('status')}",
          file=sys.stderr)
    sys.exit(0 if out.get("status") in ("OK", "PARTIAL") else 1)
