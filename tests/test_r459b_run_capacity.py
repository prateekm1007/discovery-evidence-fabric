"""R459-reaudit (P1-1) — the run-capacity semaphore battery.

The binary run.lock (one engine run at a time) was superseded by an
N-slot flock semaphore with arrival-priority queuing. This battery
attacks the replacement the way an adversary would:

  - capacity is env-configurable and clamped (no 0-slot engine, no
    unbounded pool);
  - a held slot is honestly invisible to the probe (free decreases);
  - the pool actually allows CONCURRENT engine runs (the whole point
    of the change — proven with real threads on real slot files);
  - a full-capacity hold (the heavy render) excludes single-slot
    acquirers completely;
  - a waiter yields to an EARLIER registered waiter (arrival priority)
    and proceeds once that waiter is gone;
  - a marker of a DEAD owner is pruned and cannot stall the queue
    (the crashed-waiter stall attack);
  - the kernel releases a slot when the holder dies (the property the
    single lock was chosen for — proven with a real subprocess that
    exits holding its slot);
  - the queue-visibility payload (position) is wired in the server.
"""
import os
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toscanini import sessions as store  # noqa: E402


@pytest.fixture()
def slots_one():
    """Pin capacity to 1 for the binary-semantics special case."""
    old = os.environ.get("TOSCANINI_RUN_SLOTS")
    os.environ["TOSCANINI_RUN_SLOTS"] = "1"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("TOSCANINI_RUN_SLOTS", None)
        else:
            os.environ["TOSCANINI_RUN_SLOTS"] = old


@pytest.fixture()
def slots_three():
    old = os.environ.get("TOSCANINI_RUN_SLOTS")
    os.environ["TOSCANINI_RUN_SLOTS"] = "3"
    try:
        yield
    finally:
        if old is None:
            os.environ.pop("TOSCANINI_RUN_SLOTS", None)
        else:
            os.environ["TOSCANINI_RUN_SLOTS"] = old


def test_capacity_defaults_and_clamps(monkeypatch):
    monkeypatch.delenv("TOSCANINI_RUN_SLOTS", raising=False)
    assert store.run_slot_count() == 3  # the audited default
    for raw, expected in (("0", 1), ("99", 8), ("-4", 1),
                          ("garbage", 3), ("", 3)):
        monkeypatch.setenv("TOSCANINI_RUN_SLOTS", raw)
        assert store.run_slot_count() == expected, raw


def test_held_slot_is_honestly_invisible_to_the_probe(slots_one):
    assert store.run_capacity()["free"] == 1
    handle = store.acquire_run_slot(timeout_s=2)
    assert handle is not None
    try:
        cap = store.run_capacity()
        assert cap["free"] == 0
        assert cap["slots"] == 1
    finally:
        handle.close()
    assert store.run_capacity()["free"] == 1


def test_pool_allows_concurrent_engine_runs(slots_three):
    """THE property this change exists for: two engine runs at once."""
    import threading

    acquired: list = []
    errors: list = []

    def grab():
        try:
            h = store.acquire_run_slot(timeout_s=5)
            acquired.append(h)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=grab) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(10)
    assert not errors
    assert len(acquired) == 2
    assert store.run_capacity()["free"] == 1  # 3 - 2
    for h in acquired:
        h.close()
    assert store.run_capacity()["free"] == 3


def test_full_capacity_hold_excludes_single_slot(slots_one):
    held = store.acquire_run_slots_all(timeout_s=2)
    assert len(held) == 1  # the heavy render holds EVERYTHING
    try:
        # a discovery worker cannot slip in
        assert store.acquire_run_slot(timeout_s=0.3) is None
        cap = store.run_capacity()
        assert cap["free"] == 0
    finally:
        for h in held:
            h.close()
    assert store.acquire_run_slot(timeout_s=2) is not None


def test_waiter_yields_to_earlier_registered_waiter(slots_three, monkeypatch):
    """Arrival priority: an older live marker defers a newer acquirer
    even while a slot is free — the newer waiter proceeds once the
    older marker is gone (the older waiter took its turn)."""
    store._RUN_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    older = store._RUN_QUEUE_DIR / "00000000000000000000-1.wait"
    older.touch()
    try:
        assert store.acquire_run_slot(timeout_s=0.6) is None
    finally:
        older.unlink(missing_ok=True)
    handle = store.acquire_run_slot(timeout_s=2)
    assert handle is not None  # my turn, immediately
    handle.close()


def test_dead_waiter_marker_is_pruned_not_stalling(slots_three):
    """The crashed-waiter stall attack: a marker whose owner is gone
    must not defer live acquirers. PID 999999 is dead on any sane
    container; the marker is older than the 10 s grace, so the
    priority gate clears it instead of honoring it."""
    marker = store._RUN_QUEUE_DIR / "00000000000000000001-999999.wait"
    store._RUN_QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    marker.touch()
    old = time.time() - 30
    os.utime(marker, (old, old))
    handle = store.acquire_run_slot(timeout_s=2)
    assert handle is not None  # did NOT wait on the dead marker
    handle.close()
    assert not marker.exists()  # pruned by the hygiene pass


def test_kernel_releases_slot_when_holder_dies(slots_one):
    """The property the single lock was chosen for, proven on the
    replacement: a worker killed mid-run can never wedge the pool."""
    code = (
        "import sys; sys.path.insert(0, "
        f"{str(Path(__file__).resolve().parents[1])!r}); "
        "from toscanini import sessions as s; "
        # the handle MUST be kept referenced — an unreferenced file
        # object is closed (and its flock released) by refcounting
        "h = s.acquire_run_slot(timeout_s=5); "
        "print('held', h is not None, flush=True); "
        "import time; time.sleep(30)"
    )
    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    try:
        assert proc.stdout.readline().decode().strip().endswith("True")
        cap = store.run_capacity()
        assert cap["free"] == 0  # the child holds the only slot
        proc.kill()
        proc.wait(10)
        deadline = time.time() + 5
        while time.time() < deadline:
            if store.run_capacity()["free"] == 1:
                break
            time.sleep(0.1)
        assert store.run_capacity()["free"] == 1  # kernel released it
    finally:
        if proc.poll() is None:
            proc.kill()


def test_server_queue_payload_names_capacity_and_position():
    """The queue-visibility contract rides the result endpoint: a
    queued run says it is queued with the pool's capacity — the
    position field is part of the honest queue copy."""
    src = Path(store.__file__).with_name("server.py").read_text()
    assert 'cap["free"] == 0' in src
    assert '"position"' in src
    assert 'run_capacity()' in src
    # the honest copy never names the machinery, only the capacity
    assert "run slots are busy" in src
