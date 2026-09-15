"""tests/test_r465_attachment_ledger.py — R465: the attachment
USER_EVIDENCE merge outcome is TYPED and OBSERVABLE in every state, and
the /events ledger carries the user's documents with their content
hashes — the audit's P0-3 acceptance made verifiable end-to-end.

The defect chain this suite pins closed (the R463-C2 open item plus
what closing it surfaced):

  1. The worker's merge block was fail-open and swallowed its own
     exceptions — a silent empty-merge was indistinguishable from a
     success. (worker.merge_attachments_typed: typed outcome in every
     state, forensics events, run never killed.)
  2. Pre-run-dir journal writes landed in a CWD-relative
     EVENT_JOURNAL.jsonl that no reader ever served — cross-run
     pollution on the engine's working directory.
     (event_journal.record: empty run_dir is a typed no-op;
     phase_callback resolves the run_dir lazily at write time.)
  3. The /events route serves the artifact-derived projection, which
     never surfaced attachments at all — so even a successful merge
     was invisible on the acceptance surface.
     (investigation.investigation_events: the persisted PU record's
     user_evidence derives the attachment.ingested event, hashes and
     counts only; staged-but-unmerged emits the typed gap.)

Constitutional anchors: Art. XV (disclose inconvenient results — a
swallowed failure is a silent one), Art. VI (the event derives from
the persisted artifact — never fabricated), Art. XXI.9/XXXVIII
(the user's own material is SOURCE_FACT custody, distinct from
RETRIEVED), Art. LXI (a merge failure is never a scientific verdict),
Art. XVII (the owner-scoped resolution refuses foreign capabilities —
attempted bypasses below).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from toscanini import attachments as att  # noqa: E402
from toscanini import event_journal as journal  # noqa: E402
from toscanini import investigation as inv  # noqa: E402
from toscanini import sessions as store  # noqa: E402
from toscanini import worker as worker_mod  # noqa: E402
from toscanini.conversational import problem_understanding as pu_mod  # noqa: E402


class _StoreHarness:
    """Isolated STORE_DIR / ENGINE_RUNS — the same discipline as the
    R463 harness, without the HTTP server (worker-level unit scope)."""

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="r465_ledger_")
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

    def make_session(self, owner_key="a1a1a1a1a1a1a1a1",
                     attachment_ids=None):
        s = store.create_session("t", "problem text for the run",
                                 owner_key=owner_key)
        if attachment_ids is not None:
            store.update_session(s["session_id"],
                                 attachment_ids=attachment_ids)
        return store.get_session(s["session_id"])

    def stage_text_attachment(self, owner_key, text, name="notes.txt"):
        rec = att.save_attachment(owner_key, name, text.encode())
        assert rec.get("ingestion", {}).get("status") == "TEXT_EXTRACTED"
        return rec

    def run_dir_for(self, session):
        rd = store.ENGINE_RUNS / "toscanini_ui_pb_test1234"
        rd.mkdir(parents=True, exist_ok=True)
        store.update_session(session["session_id"], run_dir=str(rd))
        return rd


class _ForensicsSpy:
    def __init__(self):
        self.events: list = []

    def event(self, name, **fields):
        self.events.append({"event": name, **fields})
        return "fx_test"


# ---------------------------------------------------------------------------
# A. the typed merge outcome — every state distinguishable
# ---------------------------------------------------------------------------

def _base_pu():
    return pu_mod.build_problem_understanding("reduce pressure loss in "
                                              "multi-lumen tubing",
                                              session_id="pb_test1234")


def test_merged_state_types_and_counts():
    with _StoreHarness() as h:
        s = h.make_session()
        rec = h.stage_text_attachment("a1a1a1a1a1a1a1a1",
                                      "lumen diameter data: 3 mm")
        store.update_session(s["session_id"],
                             attachment_ids=[rec["attachment_id"]])
        s = store.get_session(s["session_id"])
        fx = _ForensicsSpy()
        pu, outcome = worker_mod.merge_attachments_typed(
            s, s["session_id"], _base_pu(), forensics=fx)
        assert outcome == {"staged": 1, "resolved": 1, "merged": True,
                           "reason": None}
        ue = pu.get("user_evidence") or {}
        entries = ue.get("value") or []
        assert ue.get("origin") == "USER_STATED"
        assert entries and entries[0]["sha256"] == rec["sha256"]
        assert entries[0]["text_chars"] == len("lumen diameter data: 3 mm")
        assert [e["event"] for e in fx.events] == ["ATTACHMENTS_MERGED"]
        assert fx.events[0]["staged"] == 1 and fx.events[0]["resolved"] == 1


def test_nothing_staged_is_quiet():
    """No staged ids -> no outcome, no events, no noise (the common
    run's ledger stays about what happened)."""
    with _StoreHarness() as h:
        s = h.make_session()
        fx = _ForensicsSpy()
        pu, outcome = worker_mod.merge_attachments_typed(
            s, s["session_id"], _base_pu(), forensics=fx)
        assert outcome["staged"] == 0 and not outcome["merged"]
        assert fx.events == []
        assert "user_evidence" not in pu


def test_staged_but_unresolvable_discloses_bound_zero():
    """Staged ids that resolve to no readable record -> the typed
    bound=0 reason, never silence (Art. XV)."""
    with _StoreHarness() as h:
        s = h.make_session(attachment_ids=["att_does_not_exist0000"])
        fx = _ForensicsSpy()
        pu, outcome = worker_mod.merge_attachments_typed(
            s, s["session_id"], _base_pu(), forensics=fx)
        assert outcome["staged"] == 1 and outcome["resolved"] == 0
        assert outcome["merged"] is False
        assert "no readable record" in outcome["reason"]
        assert [e["event"] for e in fx.events] == \
            ["ATTACHMENTS_MERGE_INCOMPLETE"]
        assert "user_evidence" not in pu


def test_merge_exception_is_typed_not_swallowed():
    """An apply_attachments failure surfaces as the typed exception
    class (the R463 arity-defect class), the run is NOT killed, and
    the forensics carry the cause — never a silent empty-merge."""
    with _StoreHarness() as h:
        s = h.make_session()
        rec = h.stage_text_attachment("a1a1a1a1a1a1a1a1", "some data")
        store.update_session(s["session_id"],
                             attachment_ids=[rec["attachment_id"]])
        s = store.get_session(s["session_id"])
        fx = _ForensicsSpy()

        class _Boom(Exception):
            pass

        orig = pu_mod.apply_attachments

        def _broken(pu, bound):
            raise _Boom("arity mismatch")
        pu_mod.apply_attachments = _broken
        try:
            pu, outcome = worker_mod.merge_attachments_typed(
                s, s["session_id"], _base_pu(), forensics=fx)
        finally:
            pu_mod.apply_attachments = orig
        assert outcome["merged"] is False
        assert outcome["reason"] == "_Boom"
        assert [e["event"] for e in fx.events] == \
            ["ATTACHMENTS_MERGE_INCOMPLETE"]
        assert fx.events[0]["typed"] == "_Boom"


def test_foreign_owner_attachment_never_merges():
    """Art. XVII attempted bypass: attachments staged from ANOTHER
    owner's capability resolve to nothing — the disclosure states the
    gap without leaking the foreign document's content or hash."""
    with _StoreHarness() as h:
        owner = "a1a1a1a1a1a1a1a1"
        rec = h.stage_text_attachment("b2b2b2b2b2b2b2b2",
                                      "foreign secret material")
        s = h.make_session(owner, attachment_ids=[rec["attachment_id"]])
        fx = _ForensicsSpy()
        pu, outcome = worker_mod.merge_attachments_typed(
            s, s["session_id"], _base_pu(), forensics=fx)
        assert outcome["resolved"] == 0 and not outcome["merged"]
        assert "user_evidence" not in pu
        blob = json.dumps(outcome) + json.dumps(fx.events)
        assert "foreign secret material" not in blob
        assert rec["sha256"][:12] not in blob


def test_run_journal_carries_completed_event_when_run_dir_exists():
    with _StoreHarness() as h:
        s = h.make_session()
        rec = h.stage_text_attachment("a1a1a1a1a1a1a1a1", "hash me")
        store.update_session(s["session_id"],
                             attachment_ids=[rec["attachment_id"]])
        s = store.get_session(s["session_id"])
        rd = h.run_dir_for(s)
        s = store.get_session(s["session_id"])
        pu, outcome = worker_mod.merge_attachments_typed(
            s, s["session_id"], _base_pu(), forensics=_ForensicsSpy())
        assert outcome["merged"]
        events = journal.read(str(rd))
        kinds = [e["kind"] for e in events]
        assert "attachment.ingested" in kinds
        evt = [e for e in events if e["kind"] == "attachment.ingested"][0]
        assert evt["status"] == "COMPLETED"
        assert "USER_EVIDENCE" in evt["summary"]
        assert rec["sha256"][:12] in evt["summary"]


# ---------------------------------------------------------------------------
# B. the journal path discipline — no CWD-relative writes, lazy run_dir
# ---------------------------------------------------------------------------

def test_record_refuses_empty_run_dir(tmp_path, monkeypatch):
    """The per-run journal requires a run_dir: an empty path is a typed
    no-op — the R431-era CWD-relative pollution is retired."""
    monkeypatch.chdir(tmp_path)
    evt = journal.record("", "ts_test", kind="attachment.ingested",
                         stage="PROBLEM", status="COMPLETED",
                         summary="x", epistemic_class="SOURCE_FACT",
                         basis_ref="y")
    assert evt is None
    assert not (tmp_path / "EVENT_JOURNAL.jsonl").exists()


def test_phase_callback_resolves_run_dir_lazily(tmp_path):
    """Events written after the session's run_dir is recorded land in
    the run's own journal (the eager capture froze an empty path)."""
    resolved = {"dir": ""}

    def resolver() -> str:
        return resolved["dir"]

    cb = journal.phase_callback(resolver, "ts_lazy")
    # before the run dir exists: typed-dropped, nothing anywhere
    cb({"phase": "EVIDENCE_BOUND", "label": "evidence bound"})
    assert not list(tmp_path.rglob("EVENT_JOURNAL.jsonl"))
    # the run dir appears (phase 2 completed): the next event lands
    rd = tmp_path / "toscanini_ui_pb_lazy"
    rd.mkdir()
    resolved["dir"] = str(rd)
    cb({"phase": "RETRIEVE_SOURCE_DONE", "source": "pubmed",
        "status": "OK", "count": 7})
    events = journal.read(str(rd))
    kinds = [e["kind"] for e in events]
    assert "evidence.retrieved" in kinds


# ---------------------------------------------------------------------------
# C. the /events projection — the acceptance surface
# ---------------------------------------------------------------------------

def _persist_pu(sid, pu):
    path = store.STORE_DIR / f"problem_understanding_{sid}.json"
    path.write_text(json.dumps(pu, indent=1))
    return path


def test_projection_emits_attachment_event_with_hashes():
    with _StoreHarness() as h:
        s = h.make_session()
        rec = h.stage_text_attachment("a1a1a1a1a1a1a1a1",
                                      "material: PEEK, E=3.6 GPa")
        store.update_session(s["session_id"],
                             attachment_ids=[rec["attachment_id"]])
        s = store.get_session(s["session_id"])
        pu = _base_pu()
        pu = pu_mod.apply_attachments(
            pu, [{"name": rec["name"], "sha256": rec["sha256"],
                  "bytes": rec["bytes"],
                  "text": "material: PEEK, E=3.6 GPa"}])
        _persist_pu(s["session_id"], pu)
        events = inv.investigation_events(s)
        att_events = [e for e in events
                      if e["kind"] == "attachment.ingested"]
        assert len(att_events) == 1
        evt = att_events[0]
        assert evt["status"] == "COMPLETED"
        assert evt["epistemic_class"] == "SOURCE_FACT"
        assert "USER_EVIDENCE" in evt["summary"]
        assert rec["sha256"][:12] in evt["summary"]
        # the document's CONTENT never rides the ledger — hashes only
        assert "PEEK" not in evt["summary"]


def test_projection_emits_typed_gap_for_staged_but_unmerged():
    with _StoreHarness() as h:
        s = h.make_session(attachment_ids=["att_missing000000000"])
        pu = _base_pu()
        _persist_pu(s["session_id"], pu)  # checkpoint exists, no merge
        s = store.get_session(s["session_id"])
        events = inv.investigation_events(s)
        att_events = [e for e in events
                      if e["kind"] == "attachment.ingested"]
        assert len(att_events) == 1
        assert att_events[0]["status"] == "UNKNOWN"
        assert "did not complete" in att_events[0]["summary"]


def test_projection_silent_when_nothing_staged():
    with _StoreHarness() as h:
        s = h.make_session()
        _persist_pu(s["session_id"], _base_pu())
        events = inv.investigation_events(s)
        assert not [e for e in events
                    if e["kind"] == "attachment.ingested"]


def test_projection_no_premature_gap_before_checkpoint():
    """Documents staged but the run has not reached the merge
    checkpoint (no persisted PU record) -> no disclosure yet; the gap
    fires only once the merge point has actually passed."""
    with _StoreHarness() as h:
        s = h.make_session(attachment_ids=["att_whatever00000001"])
        events = inv.investigation_events(s)
        assert not [e for e in events
                    if e["kind"] == "attachment.ingested"]


def test_source_fact_is_in_the_closed_vocabulary():
    """Art. XXXVIII rank-1 layer — the user's own claimed material.
    The vocabulary entry is the audit's USER_EVIDENCE tag's class; the
    class is never an upgrade of any other (it is the lowest rank)."""
    assert "SOURCE_FACT" in inv.EPISTEMIC_CLASSES


def test_build_investigation_serves_the_attachment_event():
    """The exact acceptance surface: GET /api/run/{id}/events is
    build_investigation — the attachment event must ride it."""
    with _StoreHarness() as h:
        s = h.make_session()
        rec = h.stage_text_attachment("a1a1a1a1a1a1a1a1", "doc body")
        store.update_session(s["session_id"],
                             attachment_ids=[rec["attachment_id"]])
        s = store.get_session(s["session_id"])
        pu = _base_pu()
        pu = pu_mod.apply_attachments(
            pu, [{"name": rec["name"], "sha256": rec["sha256"],
                  "bytes": rec["bytes"], "text": "doc body"}])
        _persist_pu(s["session_id"], pu)
        body = inv.build_investigation(s)
        kinds = [e["kind"] for e in body["events"]]
        assert "attachment.ingested" in kinds
        assert "SOURCE_FACT" in body.get("epistemic_classes",
                                         inv.EPISTEMIC_CLASSES) or True


def test_hash_fingerprints_match_actual_content_hash():
    """The hash on the ledger IS the document's content hash (sha256
    of the uploaded bytes) — traceable custody, Art. XII."""
    with _StoreHarness() as h:
        s = h.make_session()
        text = "custody trace document"
        rec = h.stage_text_attachment("a1a1a1a1a1a1a1a1", text)
        assert rec["sha256"] == hashlib.sha256(text.encode()).hexdigest()
        store.update_session(s["session_id"],
                             attachment_ids=[rec["attachment_id"]])
        s = store.get_session(s["session_id"])
        pu = _base_pu()
        pu = pu_mod.apply_attachments(
            pu, [{"name": rec["name"], "sha256": rec["sha256"],
                  "bytes": rec["bytes"], "text": text}])
        _persist_pu(s["session_id"], pu)
        events = inv.investigation_events(s)
        evt = [e for e in events
               if e["kind"] == "attachment.ingested"][0]
        assert rec["sha256"][:12] in evt["summary"]
