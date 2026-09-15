"""tests/test_r461_durability.py — R461: the durability fixes for the
independent audit's P0-5, reproduced and root-caused live on production
(2026-09-14, run ts_1090d724ca33, boot 23:36:13Z):

    The user answered the investigation's one clarification question.
    The engine merged the answer as USER_STATED and ran. A container
    restart inside the run's active window restored the LAST durable
    snapshot — the pre-answer pause — and the engine re-asked the user
    a question they had already answered. The user's words were
    silently discarded by the restart.

Root cause (three co-conspirators, all fixed here):
  1. nothing snapshots between the pause and the next terminal state
     (the answer lived only in ephemeral sessions.json),
  2. the merged Problem Understanding INPUT record — the only durable
     carrier of the USER_STATED fields after the worker clears the
     session's answer field — was not part of the snapshot payload,
  3. the worker REBUILT the PU from user_text on every resume,
     discarding any merge the rebuild could not reproduce.

Each fix is pinned by an executable test (Art. XVI).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from toscanini import durable
from toscanini import sessions as store
from toscanini import worker as worker_mod
from toscanini.conversational import clarification as cl_mod
from toscanini.conversational import problem_understanding as pu_mod


USER_TEXT = ("Investigate how to detect downstream infusion-pump "
             "occlusion before patient harm, with a low-cost retrofit "
             "constraint.")
ANSWER = ("Detect occlusion at least 10 minutes earlier than current "
          "alarms, using only a disposable-path retrofit.")


# ---------------------------------------------------------------------------
# fix 2 — the merged PU record rides the durable payload
# ---------------------------------------------------------------------------

def test_pu_files_ride_the_durable_payload(tmp_path, monkeypatch):
    """The snapshot payload must include problem_understanding_*.json —
    previously only sessions/shares/evidence/run-dirs rode the push."""
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    (tmp_path / "sessions.json").write_text(json.dumps({"sessions": []}))
    pu = tmp_path / "problem_understanding_ts_x.json"
    pu.write_text(json.dumps({"problem_statement": {"value": USER_TEXT}}))

    payload = durable._collect_payload()

    assert "problem_understanding/problem_understanding_ts_x.json" in payload
    assert payload["problem_understanding/problem_understanding_ts_x.json"] == pu


def test_pu_payload_absent_when_no_records(tmp_path, monkeypatch):
    """No PU records → no PU payload keys (honest absence, no invention)."""
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    (tmp_path / "sessions.json").write_text(json.dumps({"sessions": []}))
    payload = durable._collect_payload()
    assert not [k for k in payload if k.startswith("problem_understanding/")]


# ---------------------------------------------------------------------------
# fix 3 — the worker LOADS the persisted record instead of rebuilding
# ---------------------------------------------------------------------------

def test_worker_loads_persisted_pu(tmp_path, monkeypatch):
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    pu = tmp_path / "problem_understanding_ts_load.json"
    pu.write_text(json.dumps({"desired_outcome": {
        "value": ANSWER, "origin": "USER_STATED"}}))
    loaded = worker_mod._load_problem_understanding("ts_load")
    assert loaded is not None
    assert loaded["desired_outcome"]["origin"] == "USER_STATED"


def test_worker_pu_absent_or_junk_returns_none(tmp_path, monkeypatch):
    """Absent / corrupt / empty records rebuild — the historical path,
    never a fabricated record (Art. XXV: honest absence)."""
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    assert worker_mod._load_problem_understanding("ts_missing") is None
    (tmp_path / "problem_understanding_ts_bad.json").write_text("{oops")
    assert worker_mod._load_problem_understanding("ts_bad") is None
    (tmp_path / "problem_understanding_ts_empty.json").write_text("{}")
    assert worker_mod._load_problem_understanding("ts_empty") is None
    (tmp_path / "problem_understanding_ts_list.json").write_text("[1, 2]")
    assert worker_mod._load_problem_understanding("ts_list") is None


# ---------------------------------------------------------------------------
# THE acceptance — the measured failure is now impossible
# ---------------------------------------------------------------------------

def _build_and_merge_and_persist(session_id: str) -> None:
    """The exact lifecycle the worker executes, as code: build → merge
    the user's answer as USER_STATED → persist the input record."""
    pu = pu_mod.build_problem_understanding(USER_TEXT,
                                            session_id=session_id)
    pu = pu_mod.apply_clarification_answer(pu, "desired_outcome", ANSWER)
    (store.STORE_DIR /
     f"problem_understanding_{session_id}.json").write_text(
        json.dumps(pu, indent=1, ensure_ascii=False))


def test_restart_cannot_resurrect_the_answered_question(tmp_path, monkeypatch):
    """The measured failure, replayed: build + merge + persist, then a
    restart re-materializes the store from the durable copy. The loaded
    record must still carry the USER_STATED answer, and the ask rule
    must REFUSE to re-ask the answered field."""
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    _build_and_merge_and_persist("ts_restart")

    # --- the restart: the durable copy re-materializes (restore's
    # copy-when-absent contract), the ephemeral live file is GONE ---
    repo = tmp_path / "state_repo"
    (repo / "problem_understanding").mkdir(parents=True)
    (store.STORE_DIR /
     "problem_understanding_ts_restart.json").rename(
        repo / "problem_understanding" /
        "problem_understanding_ts_restart.json")
    copied = durable._restore_problem_understanding(repo)
    assert copied == 1

    # --- the resumed worker loads the record and re-evaluates the ask ---
    pu = worker_mod._load_problem_understanding("ts_restart")
    assert pu is not None
    rec = pu.get("desired_outcome") or {}
    assert rec.get("origin") == "USER_STATED"
    assert ANSWER in json.dumps(rec.get("value"))

    need = cl_mod.evaluate_clarification_need(pu)
    fields = [c["field"] for c in need.get("candidates_considered", [])]
    if need.get("needed"):
        # SOME other field may still be material — but it must NEVER be
        # the one the user already answered
        assert need["field"] != "desired_outcome"
    assert "desired_outcome" not in fields or all(
        c["field"] != "desired_outcome" or c["uncertainty"] <= 0.0
        for c in need.get("candidates_considered", []))


def test_restore_never_overwrites_a_live_record(tmp_path, monkeypatch):
    """Copy-when-absent: a newer live record is never clobbered by the
    durable copy (the restore contract every file class shares)."""
    monkeypatch.setattr(store, "STORE_DIR", tmp_path)
    repo = tmp_path / "state_repo"
    (repo / "problem_understanding").mkdir(parents=True)
    durable_copy = (repo / "problem_understanding" /
                    "problem_understanding_ts_live.json")
    durable_copy.write_text(json.dumps({"generation": "old"}))
    live = tmp_path / "problem_understanding_ts_live.json"
    live.write_text(json.dumps({"generation": "new"}))

    copied = durable._restore_problem_understanding(repo)
    assert copied == 0
    assert json.loads(live.read_text())["generation"] == "new"
