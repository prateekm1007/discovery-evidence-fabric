"""Session store — the UI's conversation history.

Constitutional note (Art. X): the ENGINE RUN DIRECTORY is the authoritative
record of what happened. This store is an INDEX: session_id -> where the
truth lives (run_dir, final_state, package), plus UI-only metadata (title,
timestamps, share ids). If the store and a run artifact disagree, the run
artifact wins — session_detail() always re-reads the run dir.

Seeding: the six-domain benchmark runs (2026-08-30) are ingested as REAL
historical sessions with their actual outcomes — labeled with their true
origin, never presented as UI-generated.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
STORE_DIR = REPO_ROOT / "TOSCANINI_UI"
SESSIONS_PATH = STORE_DIR / "sessions.json"
SHARES_PATH = STORE_DIR / "shares.json"
ENGINE_RUNS = REPO_ROOT / "ENGINE_RUNS"

STAGES = ["RETRIEVE", "FREEZE", "PREMISE_GATE", "SYNTHESIZE",
          "VERIFY", "MULTI_SOURCE_DISCOVERY", "COLLISION", "PHYSICS",
          "ATTACK", "CONTRADICTION", "KILLER_EXPERIMENT", "ADJUDICATION",
          "CLASSIFY", "NEXT_BEST_ACTION", "RANK"]

# ---------------------------------------------------------------------------
# Run-dir derived detail (the AUTHORITY — re-read from disk every time)
# ---------------------------------------------------------------------------

def _locked_read(path: Path):
    if not path.exists():
        return {}
    with open(path, "r") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            return json.load(f)
        except (json.JSONDecodeError, ValueError):
            # A store file truncated by a crashed writer is absent data,
            # not fabricated data — read as empty (Art. XXV: honest absent).
            return {}
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def _locked_write(path: Path, data: Dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        json.dump(data, f, indent=1, ensure_ascii=False)
        fcntl.flock(f, fcntl.LOCK_UN)


def list_sessions() -> List[Dict[str, Any]]:
    return sorted(_locked_read(SESSIONS_PATH).get("sessions", []),
                  key=lambda s: s.get("created_at", ""), reverse=True)


# ---------------------------------------------------------------------------
# R394 section 15 — ownership (session owner == run owner == artifact
# owner; one session maps to one run and its artifacts)
#
# MEASURED DEFECT (public deployment, consultant claim 3,
# CONFIRMED_CURRENT): anonymous GET /api/sessions returned ALL 32 users'
# engineering problems with worker pids and filesystem paths. This is
# the enterprise release blocker: no user may see another user's
# engineering problem by default.
#
# Model:
#   - every session stores an opaque owner_key (issued as a cookie by
#     the server; never a user identity, never a login — privacy
#     scoping without identity infrastructure)
#   - a caller sees a session iff owner_key matches, the session is
#     explicitly public (curated demo content, labeled origin), or the
#     caller holds the operator key (env ENGINE_OPERATOR_KEY)
#   - public sharing of a specific run stays the EXPLICIT deliberate
#     path (create_share) — unchanged
#   - legacy sessions with no owner_key belong to NO cookie holder
#     (fail-closed: visible only to the operator key)
# ---------------------------------------------------------------------------

def list_sessions_visible_to(owner_key: str,
                             operator_key: str = "") -> List[Dict[str, Any]]:
    """Sessions the given owner may see: their own + explicitly public.
    Legacy ownerless sessions are NOT visible to cookie holders."""
    out = []
    for s in list_sessions():
        if _session_access(s, owner_key, operator_key) != "DENY":
            out.append(s)
    return sorted(out, key=lambda s: s.get("created_at", ""), reverse=True)


def _session_access(session: Dict[str, Any], owner_key: str,
                    operator_key: str = "") -> str:
    if operator_key and owner_key == operator_key:
        return "OWNER"  # the operator key grants full visibility
    if session.get("public"):
        return "PUBLIC"
    if owner_key and session.get("owner_key") == owner_key:
        return "OWNER"
    # legacy ownerless session: pre-scoping history — invisible to every
    # cookie holder (fail-closed); only the operator key reaches it above
    return "DENY"


def session_access(session_id: str, owner_key: str,
                   operator_key: str = "") -> Optional[str]:
    """OWNER | PUBLIC | OPERATOR_ONLY | DENY | None (no such session)."""
    s = get_session(session_id)
    if not s:
        return None
    return _session_access(s, owner_key, operator_key)


def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    for s in list_sessions():
        if s.get("session_id") == session_id:
            return s
    return None


def update_session(session_id: str, **fields) -> Optional[Dict[str, Any]]:
    data = _locked_read(SESSIONS_PATH)
    for s in data.get("sessions", []):
        if s.get("session_id") == session_id:
            s.update(fields)
            s["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            _locked_write(SESSIONS_PATH, data)
            return s
    return None


# ---------------------------------------------------------------------------
# Failure recovery (CEO directive 2026-08-30 #8: transport reliability,
# queueing, RESUMABILITY, failure recovery)
# ---------------------------------------------------------------------------

STUCK_AFTER_HOURS = 3  # MODEL_DERIVED operational bound, disclosed per use

ERROR_STATUSES = ("ERROR_TRANSPORT", "ERROR_BUILD", "ERROR_RUN",
                  "ERROR_STUCK")

# R392 (directive 7): the explicit durable job lifecycle. A run is
# PENDING (created, queued) -> RUNNING (worker alive, any phase) ->
# COMPLETE | ERROR_* | INTERRUPTED. INTERRUPTED means the worker process
# died without a terminal verdict (service restart / crash / spin-down):
# it is RECOVERABLE through the same retry path, never silently reported
# as successful or still-running (Art. XXV).
ACTIVE_STATUSES = ("PENDING", "BUILDING_PROBLEM", "RUNNING")
RETRYABLE_STATUSES = ERROR_STATUSES + (
    "INTERRUPTED", "RUN_BLOCKED_TRANSPORT")   # R415: a blocked run
#   re-enters the same worker path (the problem is saved, never lost)


def _proc_stat_starttime(pid: int) -> Optional[str]:
    """Linux /proc/<pid>/stat field 22 (starttime, clock ticks since boot).

    Recorded when a worker is spawned and compared on liveness checks so
    a REUSED pid can never masquerade as the original worker (Art. XVII:
    every control gets an attempted bypass). Returns None when the pid is
    not alive (or /proc is unavailable, e.g. non-Linux hosts)."""
    try:
        stat = Path(f"/proc/{int(pid)}/stat").read_text()
        # field 2 (comm) may contain spaces inside parens — split after ')'
        after_comm = stat.rsplit(")", 1)[1].split()
        return after_comm[19]  # fields 3.. => index 19 is field 22
    except Exception:  # noqa: BLE001
        return None


def worker_alive(session: Dict[str, Any]) -> Optional[bool]:
    """True/False when decidable from /proc; None when unknown (no pid
    recorded — e.g. sessions seeded from the benchmark, or non-Linux)."""
    pid = session.get("worker_pid")
    if not pid:
        return None
    starttime = session.get("worker_starttime")
    live = _proc_stat_starttime(pid)
    if live is None:
        return False
    if starttime and live != str(starttime):
        return False  # pid reused by a different process
    return True


def mark_interrupted_sessions() -> List[str]:
    """R392: pid-liveness sweep. ACTIVE sessions whose worker process is
    verifiably dead become INTERRUPTED (recoverable). Sessions with no
    recorded pid (legacy / seeded) are left to the time-based stuck
    detector — never guessed (Art. XXV)."""
    interrupted: List[str] = []
    for s in list_sessions():
        if s.get("status") not in ACTIVE_STATUSES:
            continue
        alive = worker_alive(s)
        if alive is False:
            update_session(
                s["session_id"], status="INTERRUPTED",
                error=(f"worker process (pid {s.get('worker_pid')}) is no "
                       "longer running — service restarted or worker "
                       "crashed; retry to resume"))
            interrupted.append(s["session_id"])
    return interrupted


def mark_stuck_sessions(max_age_hours: float = STUCK_AFTER_HOURS) -> List[str]:
    """HONEST stuck detection: a session RUNNING/PENDING with no update for
    > max_age_hours is marked ERROR_STUCK with reason.

    Never fabricates a research outcome (Art. XXV): the session says the
    worker disappeared (server restart, crash, OOM), nothing about the
    science. Retried sessions resume through the SAME worker path (the
    engine itself resumes from persisted run-dir stage snapshots).
    """
    import datetime as _dt
    cutoff = (_dt.datetime.utcnow()
              - _dt.timedelta(hours=max_age_hours)).strftime(
        "%Y-%m-%dT%H:%M:%SZ")
    stuck = []
    for s in list_sessions():
        if s.get("status") not in ("RUNNING", "PENDING"):
            continue
        # a fresh session has no updated_at until first update; created_at
        # is the honest fallback
        marker = s.get("updated_at") or s.get("created_at") or ""
        if marker and marker < cutoff:
            update_session(
                s["session_id"], status="ERROR_STUCK",
                error=(f"no worker progress for >{max_age_hours}h (last "
                       f"update {marker}) — worker died or service "
                       "restarted; retry to resume"))
            stuck.append(s["session_id"])
    return stuck


def mark_boot_pending_interrupted() -> List[str]:
    """R419c: BOOT-ONLY sweep — PENDING/BUILDING_PROBLEM sessions at boot
    had their worker die with the previous container and can never resume
    on their own (retry accepts ERROR_*/INTERRUPTED, not PENDING).

    Safe ONLY at boot: mark_interrupted_sessions() also runs inside the
    /api/sessions handler, where a just-created PENDING session's worker
    is mid-spawn with no pid yet — sweeping no-pid PENDING there would
    kill live jobs. This sweep runs exclusively from server main() BEFORE
    serve_forever(), when no worker process can exist by construction.

    Observed on the production deploy (R419c acceptance): sessions created
    minutes before a container crash stayed PENDING forever — 3+ hours
    from any recovery path, contradicting the R392 directive-7 contract
    ("recoverable, never spinning").
    """
    interrupted: List[str] = []
    for s in list_sessions():
        if s.get("status") not in ("PENDING", "BUILDING_PROBLEM"):
            continue
        alive = worker_alive(s)
        if alive is True:
            # impossible at boot; defensive — never interrupt a live job
            continue
        update_session(
            s["session_id"], status="INTERRUPTED",
            error=("worker died before the run registered (service "
                   "restarted during spawn/early phase); retry to resume"))
        interrupted.append(s["session_id"])
    return interrupted


# ---------------------------------------------------------------------------
# R459-reaudit (P1-1) — THE RUN-CAPACITY SEMAPHORE.
#
# The binary run.lock (one engine run at a time across all users) is
# superseded by a counting semaphore over N flock'd slot files
# (TOSCANINI_UI/runslots/run.{i}.lock, N = TOSCANINI_RUN_SLOTS, default
# 3, clamped 1..8). flock keeps the property the single lock was chosen
# for: the kernel releases it when the holder process dies, so a killed
# worker can never wedge the queue. A heavy artifact render still
# excludes engine runs completely — it acquires ALL slots (a
# full-capacity hold), preserving the measured OOM protection
# ("exactly one heavy process" generalized to "all capacity or
# nothing"). Arrival priority: each waiter registers a marker in
# TOSCANINI_UI/runqueue/ and yields to older markers, so a run that
# asked first starts first (FIFO among heavy work); markers of dead
# owners are pruned by /proc liveness so a crashed waiter cannot stall
# the queue. Transport protection is unchanged in kind: the R456
# router cascade (4 distinct account domains, typed RATE_LIMITED
# handling) is what makes measured concurrency tolerable — a slot
# burst that trips a provider advances the cascade exactly as a
# single run's burst would.
# ---------------------------------------------------------------------------

_RUN_SLOTS_DIR = STORE_DIR / "runslots"
_RUN_QUEUE_DIR = STORE_DIR / "runqueue"


def run_slot_count() -> int:
    """Configured engine run capacity (slots). Env-overridable, clamped."""
    try:
        n = int(os.environ.get("TOSCANINI_RUN_SLOTS", "3"))
    except (TypeError, ValueError):
        n = 3
    return max(1, min(n, 8))


def _prune_stale_waiters() -> None:
    """Remove queue markers whose owner is provably gone: a marker
    carries its pid; when /proc/<pid> no longer exists and the marker
    is >10 s old (fork/exec grace), the waiter is dead. A marker older
    than 1 h is pruned regardless (belt and braces for exotic PIDs)."""
    import time as _time

    try:
        _RUN_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        now = _time.time()
        for p in _RUN_QUEUE_DIR.glob("*.wait"):
            try:
                age = now - p.stat().st_mtime
            except OSError:
                continue
            if age > 3600:
                p.unlink(missing_ok=True)
                continue
            stem = p.name[:-5] if p.name.endswith(".wait") else p.name
            pid_part = stem.rsplit("-", 1)[-1]
            try:
                pid = int(pid_part)
            except ValueError:
                if age > 600:
                    p.unlink(missing_ok=True)
                continue
            if age > 10 and not Path(f"/proc/{pid}").exists():
                p.unlink(missing_ok=True)
    except OSError:
        return  # queue hygiene is best-effort; never blocks a run


def _register_waiter() -> Path:
    """Record this waiter's arrival (the queue's priority order)."""
    import time as _time

    _RUN_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    marker = _RUN_QUEUE_DIR / (
        f"{_time.time_ns():020d}-{os.getpid()}.wait")
    try:
        marker.touch()
    except OSError:
        marker = Path("/dev/null")  # no priority order; slots still work
    return marker


def _waiters_before(marker: Path) -> int:
    """How many LIVE waiters registered before this one (0 → my turn).
    A marker outside the queue directory (the /dev/null fallback) never
    blocks on priority — capacity alone decides."""
    try:
        if marker.parent != _RUN_QUEUE_DIR:
            return 0
        return sum(
            1 for p in sorted(_RUN_QUEUE_DIR.glob("*.wait"))
            if p.name < marker.name)
    except OSError:
        return 0


def _open_slot(i: int, blocking: bool):
    """Open slot file i; flock it exclusively (non-blocking or blocking).
    Returns the open handle or None (non-blocking + contended)."""
    import fcntl

    _RUN_SLOTS_DIR.mkdir(parents=True, exist_ok=True)
    f = open(_RUN_SLOTS_DIR / f"run.{i}.lock", "w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX if blocking
                    else fcntl.LOCK_EX | fcntl.LOCK_NB)
        return f
    except (BlockingIOError, OSError):
        f.close()
        return None


def acquire_run_slot(timeout_s: float = 0.0):
    """Acquire ONE engine-run slot (the discovery worker's whole-run
    hold). Arrival-priority: yields to older live waiters. Returns the
    open slot handle (hold it for the run's lifetime; the kernel
    releases the flock if the process dies). timeout_s 0 = wait
    forever (the worker's historical semantics)."""
    import time as _time

    n = run_slot_count()
    marker = _register_waiter()
    try:
        _prune_stale_waiters()
        deadline = _time.monotonic() + timeout_s if timeout_s else None
        while True:
            if _waiters_before(marker) == 0:
                for i in range(n):
                    f = _open_slot(i, blocking=False)
                    if f is not None:
                        return f
            if deadline is not None and _time.monotonic() >= deadline:
                return None
            _time.sleep(0.25)
    finally:
        try:
            if marker.parent == _RUN_QUEUE_DIR:
                marker.unlink(missing_ok=True)
        except OSError:
            pass


def acquire_run_slots_all(timeout_s: float = 0.0):
    """Acquire ALL slots (the heavy render's full-capacity hold — a
    Blender/Chromium attempt never shares instance memory with an
    engine run, extending today's measured exclusion rather than
    weakening it). Slots are taken in index order; a partial hold is
    released before retrying. Returns a list of open handles."""
    import time as _time

    n = run_slot_count()
    marker = _register_waiter()
    try:
        _prune_stale_waiters()
        deadline = _time.monotonic() + timeout_s if timeout_s else None
        while True:
            if _waiters_before(marker) == 0:
                held = []
                for i in range(n):
                    f = _open_slot(i, blocking=False)
                    if f is None:
                        break
                    held.append(f)
                if len(held) == n:
                    return held
                for f in held:  # partial hold → release, retry calmly
                    f.close()
            if deadline is not None and _time.monotonic() >= deadline:
                return []
            _time.sleep(0.5)
    finally:
        try:
            if marker.parent == _RUN_QUEUE_DIR:
                marker.unlink(missing_ok=True)
        except OSError:
            pass


def run_capacity() -> Dict[str, int]:
    """Non-blocking probe of the run-capacity semaphore (R459 audit
    P1-2's visibility contract, generalized to the pool): slots, free
    slots, and live waiters. Lets a queued run SAY it is queued — and
    from R459-reaudit, say how deep the queue is. The probe never
    enqueues, never blocks, never mutates."""
    import fcntl

    n = run_slot_count()
    free = 0
    for i in range(n):
        f = _open_slot(i, blocking=False)
        if f is not None:
            free += 1
            f.close()
    try:
        _RUN_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
        waiting = len(list(_RUN_QUEUE_DIR.glob("*.wait")))
    except OSError:
        waiting = 0
    return {"slots": n, "free": free, "waiting": waiting}


def retry_session(session_id: str) -> Optional[Dict[str, Any]]:
    """Re-enqueue an errored session through the SAME worker path.

    Allowed only from ERROR_* states (never from COMPLETE — a completed
    verdict is a research outcome, not a transport artifact; re-running
    it must be a NEW session so history stays append-only). Attempt
    count is recorded; a session that keeps failing stays honestly
    errored with its full history.
    """
    s = get_session(session_id)
    if not s:
        return None
    if s.get("status") not in RETRYABLE_STATUSES:
        return {"error": (f"session status {s.get('status')!r} is not "
                          "retryable — only ERROR_*/INTERRUPTED sessions "
                          "can re-enter the queue (completed verdicts are "
                          "append-only)")}
    attempts = int(s.get("retry_attempts") or 0) + 1
    return update_session(
        session_id,
        status="PENDING",
        error=None,
        retry_attempts=attempts,
        last_error=s.get("error"))


def create_session(title: str, user_text: str, domain_hint: str = "",
                   owner_key: str = "") -> Dict[str, Any]:
    session = {
        "session_id": f"ts_{uuid.uuid4().hex[:12]}",
        "title": title[:120],
        "user_text": user_text[:4000],
        "domain_hint": domain_hint,
        "origin": "toscanini_ui",
        # R394 s15: ownership is recorded at creation — the creator's
        # cookie owner_key; empty only for operator-side/test creates
        "owner_key": owner_key or "",
        "status": "PENDING",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "worker_pid": None,
        "worker_starttime": None,
        "run_dir": None,
        "problem_id": None,
        "final_status": None,
        "package": None,
        "share_id": None,
        "error": None,
    }
    data = _locked_read(SESSIONS_PATH)
    data.setdefault("sessions", []).append(session)
    _locked_write(SESSIONS_PATH, data)
    return session


# ---------------------------------------------------------------------------
# Share registry (read-only public invention views)
# ---------------------------------------------------------------------------

def create_share(session_id: str) -> Optional[str]:
    s = get_session(session_id)
    if not s:
        return None
    if s.get("share_id"):
        return s["share_id"]
    share_id = uuid.uuid4().hex[:16]
    data = _locked_read(SHARES_PATH)
    data[share_id] = {"session_id": session_id,
                      "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                                  time.gmtime())}
    _locked_write(SHARES_PATH, data)
    update_session(session_id, share_id=share_id)
    return share_id


def share_session(share_id: str) -> Optional[str]:
    data = _locked_read(SHARES_PATH)
    entry = data.get(share_id)
    return entry["session_id"] if entry else None


# ---------------------------------------------------------------------------
# Run-dir derived detail (the AUTHORITY — re-read from disk every time)
# ---------------------------------------------------------------------------

def _read_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:  # noqa: BLE001
        return None


def stage_summaries(run_dir: Path) -> List[Dict[str, Any]]:
    """One digest per engine stage, in canonical order, from persisted
    envelopes. Absent envelope = stage not reached yet (honest)."""
    out = []
    for stage in STAGES:
        env = _read_json(run_dir / f"envelope_{stage}.json")
        if env is None:
            continue
        log = None
        for entry in reversed(env.get("stage_log") or []):
            if entry.get("stage") == stage:
                log = entry
                break
        digest: Dict[str, Any] = {
            "stage": stage,
            "status": (log or {}).get("status", "UNKNOWN"),
            "started_at": (log or {}).get("started_at"),
            "finished_at": (log or {}).get("finished_at"),
        }
        if stage == "RETRIEVE":
            digest["records_found"] = len(env.get("evidence") or [])
            digest["sources"] = sorted({
                (e.get("source") or "?") for e in (env.get("evidence") or [])})
            digest["sample_titles"] = [
                (e.get("title") or "")[:140]
                for e in (env.get("evidence") or [])[:5]]
        elif stage == "PREMISE_GATE":
            pg = env.get("premise_gate") or {}
            digest["verdict"] = pg.get("verdict")
            digest["explanation"] = (pg.get("explanation") or "")[:240]
        elif stage == "SYNTHESIZE":
            mm = env.get("mechanism_map") or {}
            digest["mechanism"] = mm.get("mechanism")
            digest["intervention"] = mm.get("intervention")
            digest["expected_effect"] = mm.get("expected_effect")
            digest["falsification_test"] = mm.get("falsification_test")
        elif stage == "MULTI_SOURCE_DISCOVERY":
            pa = env.get("prior_art") or []
            if isinstance(pa, dict):
                pa = pa.get("results") or []
            digest["prior_art_count"] = len(pa) if isinstance(pa, list) else 0
            digest["prior_art_titles"] = [
                (p.get("title") or "")[:140]
                for p in (pa[:5] if isinstance(pa, list) else [])]
        elif stage == "COLLISION":
            cr = env.get("collision_results")
            # R396 P6: the run record carries the determinism block —
            # verdict, relevance model version, evidence-set identity,
            # variance summary, DETERMINISTIC/ NON_DETERMINISTIC class
            det = env.get("determinism")
            if isinstance(det, dict):
                digest["determinism"] = {
                    k: det.get(k) for k in (
                        "classification", "verdict",
                        "relevance_model_version",
                        "evidence_set_identity", "n_prior_replays",
                        "variance_summary") if k in det}
            digest["collisions"] = []
            if isinstance(cr, dict):
                for universe, blk in list(cr.items())[:5]:
                    if isinstance(blk, dict):
                        digest["collisions"].append({
                            "universe": universe,
                            "verdict": blk.get("mapped_status")
                            or blk.get("legacy_status"),
                            "result_count": blk.get("result_count"),
                        })
            elif isinstance(cr, list):
                for c in cr[:5]:
                    digest["collisions"].append({
                        "verdict": (c.get("verdict")
                                    or c.get("collision_risk") if isinstance(c, dict) else str(c)[:80]),
                        "note": ((c.get("note") or c.get("reason") or "")
                                 [:200] if isinstance(c, dict) else ""),
                    })
        elif stage == "PHYSICS":
            # R397 Phase 2: the first-class physics stage digest — the
            # lifecycle verdict + baseline comparison the run UI shows
            ph = env.get("physics") or {}
            if isinstance(ph, dict):
                digest["lifecycle_verdict"] = ph.get("lifecycle_verdict")
                comp = ph.get("baseline_comparison") or {}
                digest["baseline_outcome"] = comp.get("outcome")
                digest["relative_improvement"] = comp.get(
                    "relative_improvement")
                digest["chain"] = ph.get("chain_executed")
                fm = ph.get("failure_mode_contract") or {}
                digest["failure_modes"] = fm.get("candidate")
        elif stage == "ATTACK":
            ar = env.get("attack_results") or {}
            if isinstance(ar, dict):
                digest["overall"] = ar.get("overall")
                digest["challenges"] = [
                    {"challenge": dim, "verdict": verdict,
                     "response": (ar.get("reason") or "")[:240]}
                    for dim, verdict in (ar.get("attacks") or {}).items()]
            elif isinstance(ar, list):
                digest["challenges"] = [
                    {"challenge": (a.get("challenge")
                                   or a.get("attack") or "")[:200],
                     "verdict": a.get("verdict") or a.get("result"),
                     "response": (a.get("response") or "")[:240]}
                    for a in ar[:6] if isinstance(a, dict)]
                verdicts = [a.get("verdict") or a.get("result")
                            for a in ar if isinstance(a, dict)]
                digest["overall"] = (
                    "FAIL" if any(v == "FAIL" for v in verdicts)
                    else "PASS" if verdicts else "UNKNOWN")
        elif stage == "CONTRADICTION":
            ct = env.get("contradictions") or {}
            items = ct.get("contradictions") if isinstance(ct, dict) else ct
            items = items if isinstance(items, list) else []
            digest["contradictions"] = [
                ((c.get("description") or str(c))
                 [:240] if isinstance(c, dict) else str(c)[:240])
                for c in items[:4]]
            digest["count"] = len(items)
        elif stage == "KILLER_EXPERIMENT":
            ke = env.get("killer_experiment") or {}
            digest["experiment"] = ke
        elif stage == "ADJUDICATION":
            ad = env.get("adjudication") or {}
            council = ad.get("council") or {}
            digest["verdict"] = council.get("verdict")
            digest["evidence_verified"] = (
                ad.get("evidence_verification") or {}).get("verified")
            digest["reason"] = (council.get("reason")
                                or (ad.get("evidence_verification")
                                    or {}).get("evidence_class") or "")[:300]
        elif stage == "CLASSIFY":
            digest["epistemic_state"] = env.get("epistemic_state")
        elif stage == "NEXT_BEST_ACTION":
            digest["action"] = env.get("next_best_action")
        elif stage == "RANK":
            rk = env.get("ranking") or {}
            digest["score"] = rk.get("score") or rk.get("total")
            digest["breakdown"] = rk.get("breakdown") or {}
        out.append(digest)
    return out


def package_info(run_dir: Path) -> Optional[Dict[str, Any]]:
    report = _read_json(run_dir / "PACKAGE_REPORT.json")
    if not report:
        return None
    zip_path = None
    dl = run_dir / "DOWNLOAD"
    if dl.exists():
        zips = sorted(dl.glob("*.zip"))
        if zips:
            zip_path = str(zips[0])
    return {
        "complete": report.get("complete"),
        "maturity": report.get("maturity"),
        "posture": report.get("posture"),
        "traceability_passed": report.get("traceability_passed"),
        "depth_contract_passed": report.get("depth_contract_passed"),
        "folder": report.get("folder"),
        "zip": zip_path,
        "zip_name": Path(zip_path).name if zip_path else None,
        "rendered": report.get("rendered"),
        # R422 (directive 3 — package UX): honest document count for the
        # run-inspector Downloads block — from the DOWNLOAD tree's own
        # manifest when present, else the tree count; never hardcoded.
        "document_count": _download_document_count(run_dir),
    }


def _download_document_count(run_dir: Path) -> Optional[int]:
    try:
        dl = run_dir / "DOWNLOAD"
        if not dl.is_dir():
            return None
        m = _read_json(dl / "MANIFEST.json")
        if m and isinstance(m.get("file_count"), int):
            return m["file_count"]
        return sum(1 for p in dl.rglob("*") if p.is_file())
    except Exception:  # noqa: BLE001 — absent stays absent
        return None


def session_detail(session_id: str) -> Optional[Dict[str, Any]]:
    s = get_session(session_id)
    if not s:
        return None
    detail = dict(s)
    run_dir = Path(s["run_dir"]) if s.get("run_dir") else None
    if run_dir and run_dir.exists():
        detail["stages"] = stage_summaries(run_dir)
        detail["final_state"] = _read_json(run_dir / "final_state.json")
        manifest = _read_json(run_dir / "run_manifest.json") or {}
        detail["failed_stages"] = manifest.get("failed_stages") or {}
        if s.get("status") == "COMPLETE":
            detail["package"] = package_info(run_dir)
        inv = _read_json(run_dir / "INVENTION_SPECIFICATION.json")
        if inv:
            detail["invention_specification"] = inv
        eng = _read_json(run_dir / "ENGINEERING_SPECIFICATION.json")
        if eng:
            detail["engineering_specification"] = eng
        dex = _read_json(run_dir / "DECISIVE_EXPERIMENT.json")
        if dex:
            detail["decisive_experiment"] = dex
        surv = _read_json(run_dir / "SURVIVOR_SELECTION.json")
        if surv:
            detail["survivor_selection"] = surv
        cem = _read_json(run_dir / "cemetery_update.json")
        if cem:
            detail["cemetery_update"] = cem
    else:
        detail["stages"] = []
    detail.pop("evidence_pack", None)
    ep_path = STORE_DIR / f"evidence_{session_id}.json"
    ep = _read_json(ep_path)
    if ep:
        detail["evidence_pack"] = ep
    # R414 (directive §4): the canonical DiscoveryRun state, derived
    # backend-side from this record + the run dir's own artifacts. The
    # frontend READS this; it never re-derives states client-side and
    # never infers an invention exists because a GLB exists.
    from . import run_state as _rs
    detail["run_state"] = _rs.canonical_run_state(detail)
    return detail


def save_evidence_pack(session_id: str, pack: Dict) -> None:
    _locked_write(STORE_DIR / f"evidence_{session_id}.json", pack)


# ---------------------------------------------------------------------------
# Seeding: six-domain benchmark as historical sessions (REAL, labeled)
# ---------------------------------------------------------------------------

SEED_CAMPAIGN = REPO_ROOT / "discovery_campaigns" / "TOSCANINI_6DOMAIN_2026-08-30"

DEMO_TITLES = {
    "medical": "Why do infusion pumps fail to detect downstream occlusion in time?",
    "energy": "How can EV traction-battery thermal runaway initiation be prevented?",
    "aerospace": "Why do aircraft lithium-battery installations suffer thermal events?",
    "materials": "Why do rails fracture in service under fatigue loading?",
    "industrial": "Why does rolling-stock equipment fail en route?",
    "electronics": "Why do consumer lithium-ion products catch fire?",
}


def seed_benchmark_sessions() -> int:
    """Ingest the real six-domain runs as history. Idempotent."""
    added = 0
    existing_ids = {s.get("problem_id") for s in list_sessions()}
    for domain in ("medical", "energy", "aerospace", "materials",
                   "industrial", "electronics"):
        rec = _read_json(SEED_CAMPAIGN / f"RUN_{domain}.json")
        if not rec:
            continue
        run_dir = REPO_ROOT / rec.get("run_dir", "_missing_")
        if rec.get("problem_id") in existing_ids:
            continue
        if not run_dir.exists():
            continue
        # R446-C1 Task 4: the seeded session's COMPLETE is bound to the
        # canonical completion marker (run_manifest.json), NOT to
        # final_state.json — a seed run dir without the marker is
        # seeded with its TRUE state (INTERRUPTED — historical, never
        # presented complete). No state may become user-visible
        # COMPLETE until the marker proves the run finished (Art. X /
        # XXV; the R445-C completion authority).
        from . import completion as _completion
        marker = _completion.completion_marker_state(run_dir)
        fs = _read_json(run_dir / "final_state.json") or {}
        seeded_status = ("COMPLETE"
                         if marker["completion"]
                         == _completion.COMPLETE_MARKED
                         else "INTERRUPTED")
        session = {
            "session_id": f"ts_seed_{domain}",
            "title": DEMO_TITLES.get(domain, rec.get("problem_id")),
            "user_text": DEMO_TITLES.get(domain, ""),
            "domain_hint": domain,
            "origin": "six_domain_benchmark_2026-08-30",
            # R394 s15: curated demo content is EXPLICITLY public —
            # deliberate, labeled, operator-chosen (the directive's
            # "public sharing must be explicit and deliberate")
            "public": True,
            "status": seeded_status,
            "completion_basis": (
                "run_manifest.json (canonical marker)"
                if seeded_status == "COMPLETE" else
                "seed run dir lacks the canonical completion marker — "
                "seeded with its true interrupted state (R446-C1)"),
            "created_at": (fs.get("timestamp")
                           or "2026-08-30T12:00:00Z"),
            "run_dir": str(run_dir),
            "problem_id": rec.get("problem_id"),
            "final_status": fs.get("final_status"),
            "package": package_info(run_dir),
            "share_id": None,
            "error": None if seeded_status == "COMPLETE" else (
                marker.get("reason", "")[:300]),
        }
        data = _locked_read(SESSIONS_PATH)
        data.setdefault("sessions", []).append(session)
        _locked_write(SESSIONS_PATH, data)
        added += 1
    return added


# ---------------------------------------------------------------------------
# Cemetery (engine's own MECHANISM_CEMETERY — summarized for the UI)
# ---------------------------------------------------------------------------

def cemetery_summary(limit: int = 50) -> Dict[str, Any]:
    path = REPO_ROOT / "MECHANISM_CEMETERY" / "CEMETERY.json"
    data = _read_json(path)
    if not data:
        return {"entries": [], "total": 0}
    entries = data.get("entries") or []
    out = []
    for e in entries[-limit:]:
        out.append({
            "entry_id": e.get("entry_id"),
            "territory_id": e.get("territory_id"),
            "mechanism_name": (e.get("mechanism_name") or "")[:220],
            "kill_reason": (e.get("kill_reason") or "")[:220],
            "what_was_proposed": (e.get("what_was_proposed") or "")[:300],
            "reusable_constraint": (e.get("reusable_constraint")
                                    or e.get("what_we_learned") or "")[:300],
            "killed_at": e.get("killed_at") or e.get("timestamp"),
        })
    return {"entries": list(reversed(out)), "total": len(entries)}
