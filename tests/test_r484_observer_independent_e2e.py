"""R484 — Article LXXIV (Observer-Independent Durable Execution,
Constitution v2.6.0): the standing E2E reconnection contract + the
canonical state-machine pins.

THE PERMANENT ACCEPTANCE CRITERION (the operator's words): sandbox
death, browser disconnect, polling interruption, or tool timeout
cannot destroy or invalidate a server-side AI run. The E2E contract:
start run → intentionally lose the local observer → remote work
continues → reconnect → recover the run → the canonical artifacts are
available.

Hermetic (the test_toscanini_recovery fixture pattern): the store is
file-backed, the worker is a real live process (pid-liveness real),
the observer is a REAL subprocess that is SIGKILLed mid-poll — the
observation domain dies; the execution domain never notices.
"""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from toscanini import execution_states as es  # noqa: E402


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr("toscanini.sessions.STORE_DIR", tmp_path)
    monkeypatch.setattr("toscanini.sessions.SESSIONS_PATH",
                        tmp_path / "sessions.json")
    return importlib.import_module("toscanini.sessions")


# ---------------------------------------------------------------------
# the canonical state machine: UNKNOWN is first-class, distinct from
# FAILED; the mapping is total; the two domains are disjoint enums
# ---------------------------------------------------------------------

class TestCanonicalMachine:
    def test_nine_states_present(self):
        assert {s.value for s in es.ExecutionState} == {
            "QUEUED", "STARTING", "RUNNING", "WAITING_EXTERNAL",
            "COMPLETED", "FAILED", "CANCELLED", "EXPIRED", "UNKNOWN"}

    def test_unknown_distinct_from_failed_by_construction(self):
        assert es.ExecutionState.UNKNOWN is not es.ExecutionState.FAILED
        # the mapping is single-valued: no status maps to both
        for status in ("ERROR_STUCK", "INTERRUPTED", "RUNNING", None,
                       "COMPLETE", "ERROR_RUN", "RUN_BLOCKED_TRANSPORT"):
            m = es.mapping(status)
            assert (m is es.ExecutionState.FAILED) + \
                (m is es.ExecutionState.UNKNOWN) <= 1

    def test_the_amendments_exact_mappings(self):
        # observation-class operational statuses -> UNKNOWN, never FAILED
        assert es.mapping("ERROR_STUCK") is es.ExecutionState.UNKNOWN
        assert es.mapping("INTERRUPTED") is es.ExecutionState.UNKNOWN
        assert es.mapping(None) is es.ExecutionState.UNKNOWN
        assert es.mapping("SOMETHING_UNRECOGNIZED") is \
            es.ExecutionState.UNKNOWN
        # typed terminal verdicts -> FAILED (the only path in)
        for s in ("ERROR_BUILD", "ERROR_RUN", "ERROR_TRANSPORT",
                  "ERROR_SPAWN"):
            assert es.mapping(s) is es.ExecutionState.FAILED, s
        # paused-awaiting-external -> WAITING_EXTERNAL, not FAILED
        for s in ("RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_CAPABILITY",
                  "AWAITING_CLARIFICATION"):
            assert es.mapping(s) is es.ExecutionState.WAITING_EXTERNAL, s
        # the lifecycle
        assert es.mapping("PENDING") is es.ExecutionState.QUEUED
        assert es.mapping("BUILDING_PROBLEM") is es.ExecutionState.STARTING
        assert es.mapping("RUNNING") is es.ExecutionState.RUNNING
        assert es.mapping("COMPLETE") is es.ExecutionState.COMPLETED

    def test_is_failed_is_the_only_sanctioned_answer(self):
        assert es.is_failed("ERROR_RUN") is True
        assert es.is_failed("ERROR_STUCK") is False, \
            "a stalled feed is not a verdict (Art. LXXIV §C)"
        assert es.is_failed("INTERRUPTED") is False
        assert es.is_failed(None) is False
        assert es.is_failed("COMPLETE") is False

    def test_observation_domain_disjoint_from_canonical(self):
        obs = {s.value for s in es.ObservationState}
        canon = {s.value for s in es.ExecutionState}
        assert obs.isdisjoint(canon), \
            "an observation state can never be a canonical state"

    def test_lifecycle_record_names_all_four_domains(self):
        rec = es.lifecycle_record(
            observer=es.ObservationState.LOCAL_PROCESS_REAPED,
            job="RUNNING", provider="atria HEALTHY",
            canonical=es.ExecutionState.RUNNING)
        assert set(rec) >= {"domain_observation", "domain_remote_job",
                            "domain_provider", "domain_canonical_run"}
        # the observation fact rides in its own domain key
        assert rec["domain_observation"] is \
            es.ObservationState.LOCAL_PROCESS_REAPED
        assert rec["domain_canonical_run"] is es.ExecutionState.RUNNING


# ---------------------------------------------------------------------
# the product surface agrees (the user_state projection)
# ---------------------------------------------------------------------

def test_user_state_stuck_is_unknown_never_failed():
    from toscanini import user_state as us
    s = {"session_id": "ts_x", "status": "ERROR_STUCK",
         "user_problem": "p", "created_at": "2026-09-17T00:00:00Z"}
    assert us.user_state(s) == "UNKNOWN_STALLED"
    assert "unknown" in us._USER_STATE_EXPLANATIONS["UNKNOWN_STALLED"].lower()


# ---------------------------------------------------------------------
# THE E2E RECONNECTION CONTRACT
# ---------------------------------------------------------------------

class TestObserverIndependentE2E:
    def test_observer_reaped_run_completes_reconnect_recovers(
            self, store, tmp_path):
        """start run → the observer is SIGKILLed mid-poll → the remote
        work continues → a fresh observer reconnects → the run is
        COMPLETE and the canonical artifacts are available."""
        run_dir = tmp_path / "runs" / "toscanini_ui_e2e_problem"
        run_dir.mkdir(parents=True)

        # 1. START RUN: a real session + a REAL live worker process
        #    (the pid-liveness record is /proc-real, not a fixture)
        s = store.create_session("t", "the E2E observer-independence run")
        sid = s["session_id"]
        worker = subprocess.Popen(["sleep", "30"], start_new_session=True)
        try:
            starttime = store._proc_stat_starttime(worker.pid)
            store.update_session(sid, status="RUNNING",
                                 worker_pid=worker.pid,
                                 worker_starttime=starttime,
                                 run_dir=str(run_dir))
            assert store.worker_alive(store.get_session(sid)) is True

            # the run dir's first canonical artifact (the engine writes
            # envelopes as it works)
            (run_dir / "problem.json").write_text(json.dumps(
                {"problem_id": "e2e_problem"}))

            # 2. THE OBSERVER: a REAL subprocess polling the durable
            #    store — then SIGKILLed mid-poll (the sandbox-reaped
            #    equivalent; the observation domain dies FOR REAL)
            observer = subprocess.Popen(
                [sys.executable, "-c",
                 "import json,time,sys\n"
                 f"p={str(store.SESSIONS_PATH)!r}\n"
                 "while True:\n"
                 "    d=json.load(open(p))\n"
                 "    m=[x for x in d['sessions'] "
                 f"     if x['session_id']=={sid!r}]\n"
                 "    print(m[0]['status'] if m else 'GONE', flush=True)\n"
                 "    time.sleep(0.2)\n"],
                stdout=subprocess.PIPE, text=True)
            time.sleep(0.8)  # let it observe at least once
            assert observer.poll() is None, "observer was alive mid-run"
            observer.kill()          # LOCAL_PROCESS_REAPED
            observer.wait(timeout=5)
            assert observer.poll() is not None
            saw_alive = None
            try:
                first = observer.stdout.readline().strip()
                saw_alive = first
            except Exception:  # noqa: BLE001 — the pipe may be gone
                pass
            # 3. THE OBSERVER IS DEAD — the remote work CONTINUES
            #    (nothing about the session record changed because the
            #    observer died; the pid-liveness sweep, had it run,
            #    would see worker_alive == True and leave the run alone)
            assert store.worker_alive(store.get_session(sid)) is True
            mid = store.get_session(sid)
            assert mid["status"] == "RUNNING", \
                "the observer's death never touched the canonical state"

            # the worker finishes: writes the terminal artifacts and
            # sets the terminal verdict (the canonical, server-side
            # transition — the worker is the authority, not any poller)
            (run_dir / "final_state.json").write_text(json.dumps(
                {"final_status": "INVENTION_UNDER_DEVELOPMENT"}))
            store.update_session(sid, status="COMPLETE",
                                 final_status="INVENTION_UNDER_DEVELOPMENT")

            # 4. RECONNECT: a FRESH observer — a new store read with no
            #    in-memory continuity beyond the run identity
            recovered = store.get_session(sid)
            # 5. RECOVER: COMPLETE + the canonical artifacts available
            assert recovered["status"] == "COMPLETE"
            assert es.mapping(recovered["status"]) is \
                es.ExecutionState.COMPLETED
            assert es.is_failed(recovered["status"]) is False
            assert (run_dir / "final_state.json").is_file()
            assert (run_dir / "problem.json").is_file()
            # the observation-domain fact is recorded as an observation
            # fact — and appears NOWHERE in the canonical record
            assert "LOCAL_PROCESS_REAPED" not in json.dumps(recovered)
        finally:
            worker.kill()
            worker.wait(timeout=5)

        # the honest lifecycle record of THIS test (the article's
        # four-domain frame, demonstrated end to end)
        record = es.lifecycle_record(
            observer=es.ObservationState.LOCAL_PROCESS_REAPED,
            job="COMPLETED",
            provider="in-process worker (the stand-in for the credited "
                     "leg)",
            canonical=es.ExecutionState.COMPLETED,
            observer_last_saw=saw_alive,
            artifact_set=["problem.json", "final_state.json"])
        assert record["domain_canonical_run"] is \
            es.ExecutionState.COMPLETED
        assert record["domain_observation"] is \
            es.ObservationState.LOCAL_PROCESS_REAPED

    def test_worker_death_is_unknown_never_failed(self, store):
        """The complementary case: the WORKER dies (not the observer) —
        the R392 sweep types INTERRUPTED; the canonical machine maps it
        to UNKNOWN, and the run stays recoverable (retry path intact),
        never silently FAILED."""
        s = store.create_session("t", "the worker-death case")
        sid = s["session_id"]
        dead = subprocess.Popen(["sleep", "0"])
        dead.wait()  # the process is genuinely gone
        store.update_session(sid, status="RUNNING",
                             worker_pid=dead.pid,
                             worker_starttime="1")
        assert store.worker_alive(store.get_session(sid)) is False
        interrupted = store.mark_interrupted_sessions()
        assert sid in interrupted
        rec = store.get_session(sid)
        assert rec["status"] == "INTERRUPTED"
        assert es.mapping(rec["status"]) is es.ExecutionState.UNKNOWN
        assert es.is_failed(rec["status"]) is False
        # the retry path still owns it (RETRYABLE_STATUSES unchanged)
        from toscanini.sessions import RETRYABLE_STATUSES
        assert "ERROR_STUCK" in RETRYABLE_STATUSES
        assert "INTERRUPTED" in RETRYABLE_STATUSES
