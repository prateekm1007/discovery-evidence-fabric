"""
worker_forensics.py — durable, append-only forensic ledger for run/retry/render workers.

R421 Directive 2 (the a5a7 anomaly): transient worker deaths must leave durable,
pushed, diff-able forensic evidence BEFORE the container reaps them.

R422 (live confirmation of the anomaly class, 2026-09-08T06:33Z): a retry
worker (pid 3256, session ts_e3657d751977) died within ~83 s of spawn with NO
terminal session state and NO durable record of the death cause — observed
live from the public URL. The container's worker log is EPHEMERAL, so the
evidence died with (or will die with) the container. This module is the fix.

Design contract (see download/toscanini_r421_patches/02_forensic_logging.patch.md):
  - Append-only. Never mutates run records, invention objects, or sealed artifacts.
  - Durable-before-next-action: every event is appended + flushed + fsync'd before
    the worker proceeds.
  - Lives in the SAME durable store tree as sessions.json (TOSCANINI_UI/), so
    events ride the existing runtime-state snapshot/push system out of the
    container (durable._collect_payload carries worker_forensics/). No new transport.
  - Deterministic boot reconciliation from heartbeats, not from RUNNING states.
  - Fail-open for the product (forensics errors never block a worker), fail-closed
    for observability (degradation is reported).

Python 3.12, stdlib only. New file — no merge conflicts.
"""

from __future__ import annotations

import json
import os
import signal
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterator, Optional

LEDGER_BASENAME = "ledger.jsonl"
HEARTBEAT_INTERVAL_S = 30.0
ROTATE_BYTES = 8 * 1024 * 1024  # 8 MB — append-only history is kept, never truncated


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _boot_id() -> str:
    """Stable per-container-boot identity (not per-process)."""
    # Prefer an environment-injected boot id if the platform provides one.
    env = os.environ.get("TOSCANINI_BOOT_ID")
    if env:
        return env
    # Fall back to the process-1 start time: constant for the life of the container,
    # changes across restarts. Deterministic, observable, no secrets.
    try:
        p1_start = os.stat("/proc/1").st_mtime
        return f"boot-{int(p1_start)}"
    except OSError:
        return f"boot-fallback-{int(time.time())}"


def _engine_commit() -> Optional[str]:
    """R452 C5 (external audit) — MERGED UNION: the forensics ledger
    must attribute every line to a deployed commit — the audit measured
    `engine_commit: null` on ALL 509 lines including the 9 TERMINAL_STATE
    events, so a failure can never be attributed to the deployed engine
    (exactly what Article LXXI diagnosis needs on a blocked run).

    Resolution order: the env-var pins first (cheap), then the CANONICAL
    build-artifact identity (the same one-authority resolution the
    server's /api/health consumes — `resolve_engine_commit` derives the
    commit from the build artifact, never from the env expectation),
    then the identity dict's engine_commit field, then the live git
    head, then None (recorded honestly)."""
    for var in ("ENGINE_COMMIT", "BUILD_ARTIFACT_COMMIT", "RENDER_GIT_COMMIT"):
        val = os.environ.get(var)
        if val:
            return val
    try:
        from .artifact_identity import resolve_engine_commit
        commit, _source = resolve_engine_commit()
        if commit:
            return commit
    except Exception:  # noqa: BLE001 — identity resolution is best-effort
        pass
    try:
        from . import artifact_identity
        ident = artifact_identity.identity()
        commit = ident.get("engine_commit")
        if commit:
            return commit
    except Exception:  # noqa: BLE001 — identity resolution is best-effort
        pass
    try:
        import subprocess
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], capture_output=True,
            text=True, timeout=10).stdout.strip()
        if out:
            return out
    except Exception:  # noqa: BLE001
        pass
    return None


class ForensicsDegraded(Exception):
    """Raised only by callers who choose to care; the ledger itself never raises."""


@dataclass
class _ForensicsState:
    degraded: bool = False
    last_write_error: Optional[str] = None
    events_written: int = 0


class WorkerForensics:
    """Append-only forensic ledger for one worker lifecycle.

    Usage (run / retry / render worker):
        with WorkerForensics(session_id=sid, kind="run") as fx:
            fx.event("STAGE_STARTED", stage="BUILDING_PROBLEM", attempt=1)
            ...
        # WORKER_COMPLETED or WORKER_DEATH is guaranteed on every exit path,
        # including SIGTERM (best-effort flush) and unhandled exceptions.
    """

    def __init__(
        self,
        session_id: str,
        kind: str,
        *,
        durable_root: str,
        run_id: Optional[str] = None,
        heartbeat_interval_s: float = HEARTBEAT_INTERVAL_S,
        parent_event_id: Optional[str] = None,
    ) -> None:
        self.session_id = session_id
        self.run_id = run_id
        self.kind = kind  # "run" | "retry" | "render"
        self.durable_root = durable_root
        self.heartbeat_interval_s = heartbeat_interval_s
        self.boot_id = _boot_id()
        self.engine_commit = _engine_commit()
        self.pid = os.getpid()
        self._state = _ForensicsState()
        self._dir = os.path.join(durable_root, "worker_forensics")
        self._path = os.path.join(self._dir, LEDGER_BASENAME)
        self._spawned_at = time.monotonic()
        self._last_stage: Optional[str] = None
        self._attempt = 1
        self._parent_event_id = parent_event_id
        self._closed = False
        self._prior_sigterm: Any = None

    # ------------------------------------------------------------------ plumbing

    def _ensure_dir(self) -> None:
        os.makedirs(self._dir, exist_ok=True)

    def _rotate_if_needed(self) -> None:
        try:
            if os.path.exists(self._path) and os.path.getsize(self._path) >= ROTATE_BYTES:
                n = 1
                while os.path.exists(os.path.join(self._dir, f"ledger-{n}.jsonl")):
                    n += 1
                os.replace(self._path, os.path.join(self._dir, f"ledger-{n}.jsonl"))
        except OSError:
            pass  # rotation is best-effort; append still works

    def _append(self, record: dict[str, Any]) -> Optional[str]:
        """Durable-before-return append. Never raises (fail-open for the product)."""
        if self._closed and record.get("event") not in (
            "WORKER_DEATH",
            "WORKER_COMPLETED",
            "SIGTERM_FLUSH",
        ):
            return None
        record = {
            "event_id": uuid.uuid4().hex,
            "ts_utc": _utcnow_iso(),
            "boot_id": self.boot_id,
            "engine_commit": self.engine_commit,
            "kind": self.kind,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "pid": self.pid,
            **record,
        }
        if self._parent_event_id:
            record.setdefault("parent_event_id", self._parent_event_id)
        line = json.dumps(record, separators=(",", ":"), sort_keys=False) + "\n"
        try:
            self._ensure_dir()
            self._rotate_if_needed()
            # O_APPEND keeps concurrent workers safe on a single line each.
            with open(self._path, "a", encoding="utf-8") as fh:
                fh.write(line)
                fh.flush()
                os.fsync(fh.fileno())
            self._state.events_written += 1
            self._state.degraded = False
            self._state.last_write_error = None
            return record["event_id"]
        except OSError as exc:  # fail-open; disclose degradation
            self._state.degraded = True
            self._state.last_write_error = f"{type(exc).__name__}: {exc}"
            print(
                f"[worker_forensics] DEGRADED append failed for {self.session_id}: {exc}",
                file=sys.stderr,
            )
            return None

    # -------------------------------------------------------------------- public

    def event(self, event: str, **fields: Any) -> Optional[str]:
        """Record a lifecycle event. Returns the durable event_id (or None on degrade)."""
        if stage := fields.get("stage"):
            self._last_stage = stage
        if attempt := fields.get("attempt"):
            self._attempt = int(attempt)
        fields.setdefault("stage", self._last_stage)
        fields.setdefault("attempt", self._attempt)
        fields.setdefault("age_s", round(time.monotonic() - self._spawned_at, 1))
        return self._append({"event": event, **fields})

    def heartbeat(self, **extra: Any) -> Optional[str]:
        return self.event("HEARTBEAT", heartbeat_interval_s=self.heartbeat_interval_s, **extra)

    # ------------------------------------------------------- context management

    def __enter__( self) -> "WorkerForensics":
        self.event(
            "WORKER_SPAWNED",
            heartbeat_interval_s=self.heartbeat_interval_s,
            argv_head=sys.argv[:4],
        )
        self._install_sigterm_handler()
        return self

    def _install_sigterm_handler(self) -> None:
        try:
            self._prior_sigterm = signal.getsignal(signal.SIGTERM)

            def _handler(signum: int, frame: Any) -> None:
                # Best-effort durable flush, then defer to any prior handler.
                self._append(
                    {
                        "event": "WORKER_DEATH",
                        "reason": "SIGTERM",
                        "sigterm_flushed": True,
                        "stage": self._last_stage,
                    }
                )
                self._closed = True
                if callable(self._prior_sigterm) and self._prior_sigterm not in (
                    signal.SIG_IGN,
                    signal.SIG_DFL,
                ):
                    self._prior_sigterm(signum, frame)  # type: ignore[misc]
                else:
                    signal.default_int_handler(signum, frame)

            signal.signal(signal.SIGTERM, _handler)
        except (ValueError, OSError):
            # Non-main thread or restricted platform: heartbeats still cover us.
            pass

    def _finish(self, event: str, **fields: Any) -> None:
        if self._closed:
            return
        self._append({"event": event, **fields})
        self._closed = True

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        if exc_type is not None:
            tb_head = ""
            if tb is not None:
                tb_head = "; ".join(
                    line.strip() for line in _format_tb_head(tb) if line.strip()
                )[:2000]
            self._finish(
                "WORKER_DEATH",
                reason="exception",
                error_class=type(exc).__name__ if exc is not None else "UnknownException",
                error_message=str(exc)[:1000] if exc is not None else "",
                traceback_head=tb_head,
                stage=self._last_stage,
            )
        else:
            self._finish("WORKER_COMPLETED", stage=self._last_stage)
        return False  # never swallow the worker's own exception

    # ------------------------------------------------------------------- health

    def health(self) -> dict[str, Any]:
        return {
            "enabled": True,
            "ledger": self._path,
            "boot_id": self.boot_id,
            "session_id": self.session_id,
            "kind": self.kind,
            "forensics_degraded": self._state.degraded,
            "last_write_error": self._state.last_write_error,
            "events_written": self._events_written(),
        }

    def _events_written(self) -> int:
        return self._state.events_written


def _format_tb_head(tb: Any) -> list[str]:
    import traceback

    return traceback.format_tb(tb)


# ---------------------------------------------------------------------- module API


def attach_session(session_id: str, durable_root: str) -> WorkerForensics:
    """For endpoints that log request-side events (e.g. RETRY_REQUESTED) without
    owning a worker lifecycle: a bare forensics object with no context entered."""
    fx = WorkerForensics(session_id=session_id, kind="endpoint", durable_root=durable_root)
    fx._spawned_at = time.monotonic()
    return fx


def read_tail(durable_root: str, max_events: int = 2000) -> list[dict[str, Any]]:
    """Read the most recent events (oldest→newest of the tail). Never raises."""
    path = os.path.join(durable_root, "worker_forensics", LEDGER_BASENAME)
    events: list[dict[str, Any]] = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.readlines()
        for line in lines[-max_events:]:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                # A torn final line (crash mid-append) is itself forensic evidence.
                events.append({"event": "LEDGER_TORN_LINE", "raw_head": line[:200]})
    except OSError:
        pass
    return events


def _heartbeat_age_s(ev: dict[str, Any], now: Optional[float] = None) -> float:
    try:
        ts = datetime.strptime(ev["ts_utc"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc
        )
    except Exception:
        return 1e9
    now_dt = datetime.now(timezone.utc) if now is None else None
    ref = now_dt or datetime.now(timezone.utc)
    return (ref - ts).total_seconds()


def active_workers(durable_root: str, stale_after_s: float = 120.0) -> list[dict[str, Any]]:
    """Derive live workers from the ledger (spawned, not terminal, fresh heartbeat).
    Deliberately computed at read time — no second in-memory registry that can die."""
    tail = read_tail(durable_root)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for ev in tail:
        key = (ev.get("kind", "?"), ev.get("session_id", "?"))
        latest[key] = ev
    active = []
    for (kind, session_id), ev in latest.items():
        if ev.get("event") in ("WORKER_COMPLETED", "WORKER_DEATH"):
            continue
        if ev.get("event") not in ("WORKER_SPAWNED", "HEARTBEAT", "STAGE_STARTED"):
            continue
        age = _heartbeat_age_s(ev)
        if age > stale_after_s:
            continue
        active.append(
            {
                "session_id": session_id,
                "kind": kind,
                "stage": ev.get("stage"),
                "last_heartbeat_utc": ev.get("ts_utc"),
                "age_s": round(age, 1),
            }
        )
    return sorted(active, key=lambda w: w["session_id"])


def reconcile_at_boot(
    durable_root: str,
    boot_id: Optional[str] = None,
    worker_timeout_s: float = 300.0,
) -> dict[str, Any]:
    """Run once at boot, AFTER the durable restore. Append-only reconciliation:

    any worker with a WORKER_SPAWNED/heartbeat and no terminal event, whose boot_id
    differs from this boot (or whose heartbeat is older than worker_timeout_s),
    is marked ORPHANED_AT_RESTART / ORPHANED_STALLED — as NEW ledger events.
    Never rewrites the run record; the reconciliation event IS the evidence.
    """
    boot_id = boot_id or _boot_id()
    tail = read_tail(durable_root, max_events=10000)
    latest: dict[tuple[str, str], dict[str, Any]] = {}
    for ev in tail:
        latest[(ev.get("kind", "?"), ev.get("session_id", "?"))] = ev

    orphans: list[dict[str, Any]] = []
    fx = attach_session(session_id="_boot_reconciler", durable_root=durable_root)
    for (kind, session_id), ev in latest.items():
        if kind == "endpoint" or session_id.startswith("_"):
            continue
        if ev.get("event") in ("WORKER_COMPLETED", "WORKER_DEATH", "ORPHANED_AT_RESTART", "ORPHANED_STALLED"):
            continue
        if ev.get("boot_id") == boot_id:
            # Same boot: only flag if heartbeat is stale beyond the timeout.
            if _heartbeat_age_s(ev) <= worker_timeout_s:
                continue
            reason = "ORPHANED_STALLED"
            detail = f"same-boot heartbeat stale > {worker_timeout_s:.0f}s"
        else:
            reason = "ORPHANED_AT_RESTART"
            detail = f"boot_id {ev.get('boot_id')} != {boot_id} (container restarted while worker had no terminal event)"
        rec = {
            "session_id": session_id,
            "kind": kind,
            "reason": reason,
            "last_event": ev.get("event"),
            "last_stage": ev.get("stage"),
            "last_ts_utc": ev.get("ts_utc"),
            "detail": detail,
        }
        orphans.append(rec)
        # The reconciliation event carries the ORPHANED worker's own (kind, session_id)
        # so the latest-event map treats it as terminal and reconcile is idempotent.
        fx.event(
            reason,
            kind=kind,
            session_id=session_id,
            reconciled_by_boot_id=boot_id,
            **{k: v for k, v in rec.items() if k not in ("session_id", "kind")},
        )
    return {"boot_id": boot_id, "orphans": orphans, "orphan_count": len(orphans)}


def health_summary(durable_root: str) -> dict[str, Any]:
    """Exact shape for /api/health.worker_forensics (see patch spec §3)."""
    tail = read_tail(durable_root, max_events=500)
    degraded = any(ev.get("event") == "LEDGER_TORN_LINE" for ev in tail)
    return {
        "enabled": True,
        "ledger": os.path.join(durable_root, "worker_forensics", LEDGER_BASENAME),
        "boot_id": _boot_id(),
        "active_workers": active_workers(durable_root),
        "orphans_reconciled_this_boot": sum(
            1
            for ev in tail
            if ev.get("event") in ("ORPHANED_AT_RESTART", "ORPHANED_STALLED")
            and ev.get("boot_id") == _boot_id()
        ),
        "forensics_degraded": degraded,
        "last_write_error": next(
            (ev.get("error_message") for ev in reversed(tail) if ev.get("error_class")),
            None,
        ),
    }


@contextmanager
def heartbeat_loop(fx: WorkerForensics, interval: Optional[float] = None) -> Iterator[None]:
    """Optional heartbeat thread wrapper (stage-aware if the worker updates fx._last_stage)."""
    import threading

    interval = interval or fx.heartbeat_interval_s
    stop = threading.Event()

    def _loop() -> None:
        while not stop.wait(interval):
            fx.heartbeat()

    t = threading.Thread(target=_loop, name="worker-forensics-heartbeat", daemon=True)
    t.start()
    try:
        yield
    finally:
        stop.set()
        t.join(timeout=2.0)


# ---------------------------------------------------------------------- engine glue

FORENSICS_DIRNAME = "worker_forensics"


def durable_root() -> str:
    """The engine's durable store tree — the SAME directory that holds
    sessions.json (toscanini.sessions.STORE_DIR). NOTE: the ledger path is
    <durable_root>/worker_forensics/ledger.jsonl — the module joins
    FORENSICS_DIRNAME onto this root internally, so this returns the
    PARENT (the store tree itself), never the nested ledger dir.
    durable._collect_payload carries worker_forensics/* from this tree
    into the runtime-state branch, so ledger events leave the container
    with every snapshot push."""
    from toscanini import sessions as _store
    _store.STORE_DIR.mkdir(parents=True, exist_ok=True)
    return str(_store.STORE_DIR)


def forensics_dir() -> "os.PathLike[str]":
    """The ledger directory itself (for durable payload collection)."""
    from pathlib import Path
    return Path(durable_root()) / FORENSICS_DIRNAME
