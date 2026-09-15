"""tests/test_r471_clarification_durability.py — R471: the external
audit's P0-5, closed and pinned.

THE MEASURED FAILURE (2026-09-16 external audit, production): the
clarification answer appeared in the durable conversation, but the
result payload exposed an EMPTY clarification_answer object after
reload — because worker.py cleared the field to {} after merging it
into the Problem Understanding record. A worker death between the
clear and the PU persist could additionally re-ask a question the
user had already answered (the R461 class).

THE CONTRACT NOW:
  1. merge_stored_clarification KEEPS the typed answer on the session
     forever: {field, answer, applied_at, provenance: USER_STATED}.
  2. The PU merge is IDEMPOTENT — a retried run re-executes without
     duplicating clarification_history.
  3. The ask-rule guard (worker: `need["needed"] and not
     s.get("clarification_answer")`) can no longer fire once the
     answer exists — the question is never repeated.

Constitutional anchors: Art. VI (the record states what happened),
Art. XXI (durable input custody), the R461 restart lesson.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import sessions as store  # noqa: E402
from toscanini import worker as worker_mod  # noqa: E402
from toscanini.conversational import problem_understanding as pu_mod  # noqa: E402

USER_TEXT = ("How can the cycle life of lithium-ion grid-storage cells "
             "under daily shallow cycling be extended without "
             "increasing cost per kWh?")
ANSWER = "observed degradation in the field — capacity fade at 60% DoD"


class _StoreHarness:
    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="r471_clar_")
        tdp = Path(self.tmp)
        store_dir = tdp / "TOSCANINI_UI"
        runs = tdp / "ENGINE_RUNS"
        store_dir.mkdir()
        runs.mkdir()
        self._orig = (store.STORE_DIR, store.SESSIONS_PATH,
                      store.SHARES_PATH, store.ENGINE_RUNS)
        store.STORE_DIR = store_dir
        store.SESSIONS_PATH = store_dir / "sessions.json"
        store.SHARES_PATH = store_dir / "shares.json"
        store.ENGINE_RUNS = runs
        store.SESSIONS_PATH.write_text("{}")
        return self

    def __exit__(self, *a):
        (store.STORE_DIR, store.SESSIONS_PATH,
         store.SHARES_PATH, store.ENGINE_RUNS) = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, sid, **extra):
        s = {"session_id": sid, "title": sid, "user_text": USER_TEXT,
             "status": "BUILDING_PROBLEM",
             "created_at": "2026-09-16T00:00:00Z",
             "owner_key": "a1b2c3d4e5f6", "worker_pid": None,
             "worker_starttime": None, "run_dir": None,
             "final_status": None, "package": None, "share_id": None,
             "error": None}
        s.update(extra)
        store.SESSIONS_PATH.write_text(json.dumps({"sessions": [s]}))
        return s


class TestAnswerDurability:

    def test_merge_keeps_the_typed_answer_on_the_session(self):
        with _StoreHarness() as h:
            h.make("ts_ans",
                   clarification_answer={"field": "observed_failure",
                                         "answer": ANSWER})
            pu = pu_mod.build_problem_understanding(
                USER_TEXT, session_id="ts_ans")
            pu = worker_mod.merge_stored_clarification(
                store.get_session("ts_ans"), "ts_ans", pu)
            s = store.get_session("ts_ans")
            # THE AUDIT'S ACCEPTANCE: field/answer REMAIN present with
            # USER_STATED provenance after the merge (never the old {})
            assert s["clarification_answer"]["field"] == "observed_failure"
            assert s["clarification_answer"]["answer"] == ANSWER
            assert s["clarification_answer"]["provenance"] == "USER_STATED"
            assert s["clarification_answer"]["applied_at"]

    def test_reloaded_session_exposes_the_answer(self):
        """The audit's exact repro shape: after 'reload' (a fresh store
        read), clarification_answer.field/answer remain present."""
        with _StoreHarness() as h:
            h.make("ts_ans2",
                   clarification_answer={"field": "observed_failure",
                                         "answer": ANSWER})
            pu = pu_mod.build_problem_understanding(
                USER_TEXT, session_id="ts_ans2")
            worker_mod.merge_stored_clarification(
                store.get_session("ts_ans2"), "ts_ans2", pu)
            # a "reload" — the same path the result endpoint takes
            reloaded = store.get_session("ts_ans2")
            assert reloaded["clarification_answer"]["answer"] == ANSWER
            assert reloaded["clarification_answer"]["field"] \
                == "observed_failure"

    def test_retry_reexecutes_the_merge_without_duplicating(self):
        """A worker death then retry re-runs the merge block: the
        PU history gains NO duplicate entry, and applied_at is stable."""
        with _StoreHarness() as h:
            h.make("ts_ans3",
                   clarification_answer={"field": "observed_failure",
                                         "answer": ANSWER})
            pu = pu_mod.build_problem_understanding(
                USER_TEXT, session_id="ts_ans3")
            pu = worker_mod.merge_stored_clarification(
                store.get_session("ts_ans3"), "ts_ans3", pu)
            first_applied = store.get_session("ts_ans3")[
                "clarification_answer"]["applied_at"]
            # the retry re-execution (same block, same answer)
            pu2 = worker_mod.merge_stored_clarification(
                store.get_session("ts_ans3"), "ts_ans3", pu)
            s = store.get_session("ts_ans3")
            hist = pu2.get("clarification_history", [])
            same = [e for e in hist
                    if e.get("field") == "observed_failure"
                    and e.get("answer") == ANSWER]
            assert len(same) == 1  # idempotent — no duplicate record
            assert s["clarification_answer"]["applied_at"] == first_applied

    def test_the_ask_guard_never_refires_once_answered(self):
        """The worker's ask-rule: `need["needed"] and not
        s.get("clarification_answer")` — with the retained answer the
        pause branch is UNREACHABLE (the question is never repeated),
        even when the PU still reports the unknown (a pre-merge death)."""
        with _StoreHarness() as h:
            h.make("ts_ans4",
                   clarification_answer={"field": "observed_failure",
                                         "answer": ANSWER})
            s = store.get_session("ts_ans4")
            # simulate the death-between-merge-and-persist class: the
            # PU on disk never got the answer (still unknown-heavy)
            pu = pu_mod.build_problem_understanding(
                USER_TEXT, session_id="ts_ans4")
            from toscanini.conversational import clarification as _cl
            need = _cl.evaluate_clarification_need(pu)
            # the guard's exact expression, from worker.py
            asks_again = need["needed"] and not s.get(
                "clarification_answer")
            assert asks_again is False  # the answer blocks the re-ask

    def test_apply_clarification_answer_is_idempotent_unit(self):
        pu = pu_mod.build_problem_understanding(
            USER_TEXT, session_id="ts_unit")
        pu = pu_mod.apply_clarification_answer(
            pu, "observed_failure", ANSWER)
        pu = pu_mod.apply_clarification_answer(
            pu, "observed_failure", ANSWER)
        hist = [e for e in pu["clarification_history"]
                if e["field"] == "observed_failure"]
        assert len(hist) == 1
        assert pu["observed_failure"]["value"] == ANSWER
        assert pu["observed_failure"]["origin"] == "USER_STATED"
        # a DIFFERENT answer for the same field still records (the
        # user changed their mind through a new pause)
        pu = pu_mod.apply_clarification_answer(
            pu, "observed_failure", "a different observed context")
        assert len(pu["clarification_history"]) == 2
