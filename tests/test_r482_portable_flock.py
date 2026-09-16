"""R482 — the portable_flock battery (CTO-authored, Art. III: the
implementer never authors its own verification).

The external auditor's re-audit finding (P2 portability): an unguarded
module-level `import fcntl` in quota_breaker.py (conftest-reachable at
COLLECTION time) made the entire suite uncollectable on Windows —
their --noconftest workaround. package_registry.py carried the same
class (also conftest-reachable). The fix: discovery_fabric/
portable_flock.py (posix real / msvcrt 1-byte / honest noop) + both
sites rewired.

This battery pins:
  1. the backend closed vocabulary + the posix identity on Linux
  2. REAL cross-process exclusion through the shim (a holder process
     blocks the parent's acquire)
  3. LOCK_UN actually releases
  4. THE REGRESSION: with fcntl AND msvcrt blocked (the Windows class
     simulated on Linux), the shim resolves "noop" and BOTH conftest-
     reachable modules import cleanly — collection survives
  5. the honest degradation contract (noop flock returns None)
  6. the static negative: no bare fcntl remains in either file
  7. R484 (the auditor's live-proven fix, EXECUTED here): a simulated
     msvcrt module makes the msvcrt branch RUN on Linux — every
     msvcrt.locking call must carry the file object's fileno() (the
     R482 shape omitted the fd and raised TypeError on Windows).

The Linux-only assertions skip cleanly off-Linux (the auditor's
"2 flock tests are Linux-assuming" finding); the msvcrt branch is
now EXECUTION-verified with the simulated module — the code-verified
label narrows to the real msvcrt's blocking semantics only."""
from __future__ import annotations

import io
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.portable_flock import (  # noqa: E402
    BACKEND, LOCK_EX, LOCK_SH, LOCK_UN, flock)

QB_SRC = (REPO_ROOT / "discovery_fabric" / "prior_art_v2"
          / "quota_breaker.py").read_text()
PR_SRC = (REPO_ROOT / "discovery_fabric" / "engine"
          / "package_registry.py").read_text()


def test_backend_closed_vocabulary():
    """R482: BACKEND is one of the three recorded backends (universal
    — holds on every platform)."""
    assert BACKEND in ("posix", "msvcrt", "noop")


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="the posix identity is a Linux-machine assertion "
           "(the auditor's portability finding R484: this test and "
           "the fcntl-constants twin were Linux-assuming)")
def test_backend_is_posix_on_linux():
    """R482/R484: on this Linux machine the shim must resolve the
    real posix backend."""
    assert BACKEND == "posix"


@pytest.mark.skipif(
    not sys.platform.startswith("linux"),
    reason="imports fcntl directly — Linux-only by construction")
def test_constants_match_fcntl_on_posix():
    """R482: on posix the shim's constants ARE fcntl's (identity, not
    a re-derivation)."""
    import fcntl
    assert LOCK_EX == fcntl.LOCK_EX
    assert LOCK_UN == fcntl.LOCK_UN
    assert LOCK_SH == fcntl.LOCK_SH


HOLDER_CODE = (
    "import sys, time\n"
    "from discovery_fabric.portable_flock import flock, LOCK_EX, LOCK_UN\n"
    "lf = open(sys.argv[1], 'w')\n"
    "flock(lf, LOCK_EX)\n"
    "print('HELD', flush=True)\n"
    "time.sleep(1.5)\n"
    "flock(lf, LOCK_UN)\n")


def _holder(lockfile: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(REPO_ROOT) + os.pathsep \
        + env.get("PYTHONPATH", "")
    p = subprocess.Popen(
        [sys.executable, "-c", HOLDER_CODE, str(lockfile)],
        stdout=subprocess.PIPE, text=True, env=env, cwd=str(REPO_ROOT))
    assert p.stdout.readline().strip() == "HELD"  # the lock is held NOW
    return p


def test_flock_exclusive_blocks_second_process(tmp_path):
    """R482: real exclusion THROUGH the shim — a holder process keeps
    the lock 1.5 s; the parent's acquire must block until release."""
    lockfile = tmp_path / "excl.lock"
    holder = _holder(lockfile)
    try:
        t0 = time.time()
        with open(lockfile, "w") as lf:
            flock(lf, LOCK_EX)
            blocked_for = time.time() - t0
            flock(lf, LOCK_UN)
        assert blocked_for >= 1.0, (
            f"acquire returned after {blocked_for:.2f}s — no real "
            f"exclusion through the shim")
    finally:
        holder.wait(timeout=10)


def test_flock_unlock_releases(tmp_path):
    """R482: LOCK_UN releases — after the holder exits (unlock +
    close), a fresh acquire is immediate."""
    lockfile = tmp_path / "rel.lock"
    holder = _holder(lockfile)
    holder.wait(timeout=10)
    t0 = time.time()
    with open(lockfile, "w") as lf:
        flock(lf, LOCK_EX)
        acquired_in = time.time() - t0
        flock(lf, LOCK_UN)
    assert acquired_in < 1.0


@pytest.fixture
def windows_class(monkeypatch):
    """Simulate the auditor's machine ON LINUX: both fcntl and msvcrt
    unimportable (sys.modules None entries raise ImportError), the
    dependents purged so they re-import fresh through the shim.
    Restores everything on exit."""
    import importlib
    for m in ("discovery_fabric.portable_flock",
              "discovery_fabric.prior_art_v2.quota_breaker",
              "discovery_fabric.engine.package_registry"):
        sys.modules.pop(m, None)
    monkeypatch.setitem(sys.modules, "fcntl", None)
    monkeypatch.setitem(sys.modules, "msvcrt", None)
    yield importlib
    for m in ("discovery_fabric.portable_flock",
              "discovery_fabric.prior_art_v2.quota_breaker",
              "discovery_fabric.engine.package_registry"):
        sys.modules.pop(m, None)
    monkeypatch.undo()
    importlib.import_module("discovery_fabric.portable_flock")
    importlib.import_module("discovery_fabric.prior_art_v2.quota_breaker")
    importlib.import_module("discovery_fabric.engine.package_registry")


def test_windows_collection_class_dead(windows_class):
    """R482 — THE REGRESSION: the exact class the auditor measured.
    With no fcntl and no msvcrt, the shim resolves "noop" and BOTH
    conftest-reachable modules import cleanly — pytest collection on
    Windows survives (the --noconftest workaround retires)."""
    pf = windows_class.import_module("discovery_fabric.portable_flock")
    assert pf.BACKEND == "noop"
    qb = windows_class.import_module(
        "discovery_fabric.prior_art_v2.quota_breaker")
    pr = windows_class.import_module(
        "discovery_fabric.engine.package_registry")
    assert callable(qb._write) and callable(pr.allocate)


def test_noop_backend_honest_degradation(windows_class, tmp_path):
    """R482: the noop contract — callable, returns None, never raises
    (Art. XV: the degradation is typed on the module, never silent)."""
    pf = windows_class.import_module("discovery_fabric.portable_flock")
    lockfile = tmp_path / "noop.lock"
    with open(lockfile, "w") as lf:
        assert pf.flock(lf, pf.LOCK_EX) is None
        assert pf.flock(lf, pf.LOCK_UN) is None


def test_no_bare_fcntl_remains_in_the_reachable_tree():
    """R482: the pinned negative — neither conftest-reachable file
    imports fcntl or calls fcntl.* anymore (the shim is the only
    fcntl surface in discovery_fabric/)."""
    for name, src in (("quota_breaker", QB_SRC), ("package_registry", PR_SRC)):
        assert "import fcntl" not in src, f"{name}: bare fcntl import"
        assert "fcntl.flock" not in src, f"{name}: direct fcntl call"
    assert "from ..portable_flock import" in QB_SRC
    assert "from ..portable_flock import" in PR_SRC


def test_msvcrt_branch_present_and_translates():
    """R482/R484: the msvcrt branch pinned STATICALLY — the branch
    exists, translates LOCK_EX to a 1-byte LK_LOCK at offset 0 and
    LOCK_UN to LK_UNLCK, AND (the auditor's live-proven fix) every
    msvcrt.locking call carries the file descriptor. The R482 shape
    — msvcrt.locking(mode, nbytes) with the fd OMITTED — raised
    TypeError on every Windows call; their checkout measured it."""
    src = (REPO_ROOT / "discovery_fabric" / "portable_flock.py").read_text()
    assert 'import msvcrt as _msvcrt' in src
    assert "fd = fileobj.fileno()" in src
    assert "_msvcrt.locking(fd, _msvcrt.LK_UNLCK, 1)" in src
    assert "_msvcrt.locking(fd, _msvcrt.LK_LOCK, 1)" in src
    # the class-level negative: the fd-omitting call shape is dead
    assert "_msvcrt.locking(_msvcrt." not in src, (
        "msvcrt.locking called without the fd — the R482 TypeError "
        "class (the auditor's P2)"
    )
    assert 'BACKEND = "noop"' in src
    assert 'return None' in src


def test_msvcrt_branch_executes_and_passes_the_fd(tmp_path, monkeypatch):
    """R484 — the auditor's fix pinned by EXECUTION on Linux: a fake
    msvcrt module (recording every locking(fd, mode, nbytes) call)
    makes the msvcrt branch RUN here. The fd MUST be the file
    object's fileno() — the R482 shim omitted it (TypeError on
    Windows, measured live on the auditor's checkout; their fix
    proven there, EXECUTED here). This narrows the honest
    code-verified label to the real msvcrt's blocking semantics."""
    import importlib
    calls: list = []

    class _FakeMsvcrt:
        LK_LOCK = 0
        LK_UNLCK = 1

        @staticmethod
        def locking(fd, mode, nbytes):
            calls.append((fd, mode, nbytes))

    sys.modules.pop("discovery_fabric.portable_flock", None)
    monkeypatch.setitem(sys.modules, "fcntl", None)
    monkeypatch.setitem(sys.modules, "msvcrt", _FakeMsvcrt)
    try:
        pf = importlib.import_module("discovery_fabric.portable_flock")
        assert pf.BACKEND == "msvcrt"
        lockfile = tmp_path / "ms.lock"
        with open(lockfile, "w") as lf:
            expected_fd = lf.fileno()
            pf.flock(lf, pf.LOCK_EX)
            pf.flock(lf, pf.LOCK_SH)
            pf.flock(lf, pf.LOCK_UN)
        assert calls == [
            (expected_fd, _FakeMsvcrt.LK_LOCK, 1),
            (expected_fd, _FakeMsvcrt.LK_LOCK, 1),
            (expected_fd, _FakeMsvcrt.LK_UNLCK, 1),
        ], (
            f"msvcrt.locking must receive (fileobj.fileno(), mode, 1) "
            f"on every call; got {calls} — the fd-omission TypeError "
            f"class is back"
        )
    finally:
        sys.modules.pop("discovery_fabric.portable_flock", None)
        monkeypatch.undo()
        importlib.import_module("discovery_fabric.portable_flock")
