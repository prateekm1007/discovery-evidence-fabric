
"""R482 (external audit P2 portability) — the ONE portable advisory
file lock. The Windows collection class dies at `import fcntl`
(quota_breaker / package_registry are conftest-reachable at collection
time); every discovery_fabric lock site goes through HERE instead.
Backends, resolved once at import, RECORDED not guessed:
  "posix"  — fcntl.flock, the real thing (Linux/CI/Docker/HF).
  "msvcrt" — a 1-byte range lock at offset 0 (msvcrt.locking), the
             standard Windows advisory-mutex pattern; the locked
             region may lie past EOF (legal on Windows).
  "noop"   — neither primitive exists: NO cross-process exclusion
             (honest degradation; single-process semantics are
             preserved and the backend is queryable via BACKEND).
Art. XV: the degradation is typed on the module, never silent."""

from __future__ import annotations

try:
    import fcntl as _fcntl
    BACKEND = "posix"
    LOCK_SH = _fcntl.LOCK_SH
    LOCK_EX = _fcntl.LOCK_EX
    LOCK_UN = _fcntl.LOCK_UN
except ImportError:
    try:
        import msvcrt as _msvcrt
        BACKEND = "msvcrt"
        # fcntl op bits (the sites' vocabulary): SH=1 EX=2 UN=8
        LOCK_SH = 1
        LOCK_EX = 2
        LOCK_UN = 8
    except ImportError:
        BACKEND = "noop"
        LOCK_SH = 1
        LOCK_EX = 2
        LOCK_UN = 8

if BACKEND == "posix":
    def flock(fileobj, op):
        """posix: the real fcntl.flock (unbuffered passthrough)."""
        _fcntl.flock(fileobj, op)
elif BACKEND == "msvcrt":
    def flock(fileobj, op):
        """msvcrt: 1-byte range lock at offset 0 (msvcrt.locking
        locks from the CURRENT position; seek(0) first, then lock or
        unlock exactly 1 byte AT THE FILE DESCRIPTOR). LK_LOCK blocks
        (10 x 1s retries); LK_UNLCK releases. R484 (the auditor's
        live-proven fix): msvcrt.locking takes a DESCRIPTOR, not a
        file object — the R482 shape omitted it and raised TypeError
        on every Windows call; the fd is fileobj.fileno(), pinned
        statically AND by execution with a simulated msvcrt in
        test_r482. The seek must be restored? NO — the call
        sites re-position before reading/writing; do NOT restore the
        position (matching flock's position-independence is NOT
        possible and the sites do not rely on it)."""
        fileobj.seek(0)
        fd = fileobj.fileno()
        if op & LOCK_UN:
            _msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)
        elif op & LOCK_EX:
            _msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)
        elif op & LOCK_SH:
            _msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)
        else:
            raise ValueError(f"unsupported flock op {op!r}")
else:
    def flock(fileobj, op):
        """noop: no cross-process primitive exists — honest
        degradation, returns None (BACKEND == "noop")."""
        return None
