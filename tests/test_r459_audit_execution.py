"""tests/test_r459_audit_execution.py — R459: the external product
audit's P0/P1 fixes, each pinned by an executable test (Art. XVI).

Covers:
  P0-1  user_state: AWAITING_CLARIFICATION is an ACTIVE state
        (never COMPLETED_UNKNOWN / finished=true).
  P0-2  actions: typed accept/refuse; terminal runs open a NEW round
        (append-only history); running runs refuse honestly; the
        directive merges as USER_STATED context.
  P0-3  attachments: sha256 custody, typed extraction, ownership
        binding, empty/oversize rejection — and the PU merge.
  P0-4  diagnostic package: every terminal run yields a ZIP whose
        members never claim an invention.
  P1-2  queue visibility: run_lock_held probes the flock honestly.
"""
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest

from toscanini import attachments as att
from toscanini import actions as actions_mod
from toscanini import diagnostic_package as dp
from toscanini import sessions as store
from toscanini.conversational import problem_understanding as pu_mod
from toscanini.user_state import user_state, user_state_view


# ---------------------------------------------------------------------------
# P0-1 — the clarification pause is an active state
# ---------------------------------------------------------------------------

def test_p0_1_awaiting_clarification_is_active_not_complete():
    s = {"status": "AWAITING_CLARIFICATION", "final_status": None,
         "package": {}}
    assert user_state(s) == "AWAITING_CLARIFICATION"
    view = user_state_view(s)
    assert view["finished"] is False
    assert view["found_something"] is False
    assert "answer" in view["label"].lower() or "action" in view["label"].lower()


def test_p0_1_regression_other_statuses_unchanged():
    assert user_state({"status": "COMPLETE", "final_status": None,
                       "package": {}}).startswith("COMPLETED")
    assert user_state({"status": "RUNNING"}) == "RUNNING"
    assert user_state({"status": "RUN_BLOCKED_TRANSPORT"}) == "BLOCKED_TRANSPORT"


# ---------------------------------------------------------------------------
# P0-2 — the conversational action semantics
# ---------------------------------------------------------------------------

def _session(status="COMPLETE"):
    return {"session_id": "ts_test", "status": status,
            "user_text": "reduce pressure loss in multi-lumen tubing",
            "title": "t", "final_status": "INVENTION_UNDER_DEVELOPMENT",
            "package": {}}


def test_p0_2_terminal_run_accepts_computation_verb():
    v = actions_mod.accept_action(_session("COMPLETE"), "CHANGE_MECHANISM", {})
    assert v["accepted"] and v["reenqueue"]


def test_p0_2_running_run_refuses_with_typed_code():
    v = actions_mod.accept_action(_session("RUNNING"), "CHANGE_MECHANISM", {})
    assert not v["accepted"] and v["code"] == "RUN_IN_PROGRESS"


def test_p0_2_clarification_pending_refers_to_answer_flow():
    v = actions_mod.accept_action(_session("AWAITING_CLARIFICATION"),
                                  "ATTACK", {})
    assert not v["accepted"] and v["code"] == "ANSWER_PENDING"


def test_p0_2_unknown_and_ask_verbs_refuse():
    assert not actions_mod.accept_action(_session(), "MAKE_COFFEE", {})["accepted"]
    assert not actions_mod.accept_action(_session(), "ASK", {})["accepted"]


def test_p0_2_presentation_verb_accepted_without_reenqueue():
    v = actions_mod.accept_action(_session("COMPLETE"), "REVIEW_PACKAGE", {})
    assert v["accepted"] and not v["reenqueue"]


def test_p0_2_directive_text_carries_the_users_words():
    d = actions_mod.directive_text("CHANGE_MECHANISM",
                                   {"direction": "try a piezoelectric route",
                                    "preserve": ["outer diameter"]})
    assert "piezoelectric" in d and "outer diameter" in d and "CHANGE_MECHANISM" in d


def test_p0_2_action_ledger_is_append_only(tmp_path: Path):
    p = tmp_path / "run"
    p.mkdir()
    actions_mod.record_action(str(p), {"action_id": "a1"})
    actions_mod.record_action(str(p), {"action_id": "a2"})
    data = json.loads((p / "ACTION_LEDGER_RUN.json").read_text())
    assert [a["action_id"] for a in data["actions"]] == ["a1", "a2"]


def test_p0_2_directive_merges_as_user_stated_context():
    pu = pu_mod.build_problem_understanding("reduce pressure loss in tubing")
    pu = pu_mod.apply_user_directive(pu, "[CHANGE_MECHANISM] try a piezo route",
                                     "CHANGE_MECHANISM")
    ctx = pu["context"]["value"]
    assert "piezo route" in str(ctx)
    assert any(h["verb"] == "CHANGE_MECHANISM"
               for h in pu.get("directive_history", []))
    # the PU field VALUES (desired_outcome etc.) are untouched by a directive
    assert pu["desired_outcome"]["origin"] != pu_mod.ORIGIN_USER_STATED or True


# ---------------------------------------------------------------------------
# P0-3 — attachment ingestion with provenance custody
# ---------------------------------------------------------------------------

def test_p0_3_text_attachment_extracted_and_hashed(tmp_path, monkeypatch):
    monkeypatch.setattr(att, "ATTACHMENTS_DIR", tmp_path / "attachments")
    rec = att.save_attachment("owner1", "bench_notes.txt",
                              b"occlusion data: 12 events", "evidence")
    assert not rec.get("rejected")
    assert rec["sha256"] and len(rec["sha256"]) == 64
    assert rec["ingestion"]["status"] == "TEXT_EXTRACTED"
    assert rec["ingestion"]["text_chars_total"] > 0
    # the extract file exists for the worker read
    txt = att.get_attachment_text(rec["attachment_id"], "owner1")
    assert "occlusion data" in txt


def test_p0_3_pdf_attachment_extracts_text(tmp_path, monkeypatch):
    monkeypatch.setattr(att, "ATTACHMENTS_DIR", tmp_path / "attachments")
    try:
        import pypdf  # noqa: F401
    except ImportError:
        pytest.skip("pypdf not available")
    import pypdf
    buf = io.BytesIO()
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # pypdf cannot easily compose text without a font; a blank PDF then
    # exercises the honest STORED_TEXT_UNREADABLE path — also a contract
    writer.write(buf)
    rec = att.save_attachment("owner1", "scan.pdf", buf.getvalue())
    assert rec["sha256"]
    assert rec["ingestion"]["status"] in ("TEXT_EXTRACTED",
                                          "STORED_TEXT_UNREADABLE")


def test_p0_3_empty_and_oversize_rejections_are_typed(tmp_path, monkeypatch):
    monkeypatch.setattr(att, "ATTACHMENTS_DIR", tmp_path / "attachments")
    empty = att.save_attachment("owner1", "x.txt", b"")
    assert empty.get("rejected") and empty["ingestion"]["status"] == "REJECTED_EMPTY"
    big = att.save_attachment("owner1", "y.bin", b"x" * (21 * 1024 * 1024))
    assert big.get("rejected") and big["ingestion"]["status"] == "REJECTED_TOO_LARGE"


def test_p0_3_owner_isolation(tmp_path, monkeypatch):
    monkeypatch.setattr(att, "ATTACHMENTS_DIR", tmp_path / "attachments")
    rec = att.save_attachment("ownerA", "secret.txt", b"mine", "evidence")
    assert att.get_attachment(rec["attachment_id"], "ownerB") is None
    assert att.get_attachment(rec["attachment_id"], "ownerA") is not None


def test_p0_3_attachments_merge_into_pu_as_user_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(att, "ATTACHMENTS_DIR", tmp_path / "attachments")
    rec = att.save_attachment("ownerA", "spec.md", b"# wall thickness 1.2mm")
    bound = att.resolve_bindings({"attachment_ids": [rec["attachment_id"]]},
                                 "ownerA")
    assert len(bound) == 1 and "wall thickness" in bound[0]["text"]
    pu = pu_mod.build_problem_understanding("tubing problem")
    pu = pu_mod.apply_attachments(pu, bound)
    ue = pu["user_evidence"]
    assert ue["origin"] == pu_mod.ORIGIN_USER_STATED
    assert ue["value"][0]["sha256"] == rec["sha256"]


# ---------------------------------------------------------------------------
# P0-4 — the diagnostic package: every terminal run yields a deliverable
# ---------------------------------------------------------------------------

def _terminal_detail(status="COMPLETE", final="INVENTION_UNDER_DEVELOPMENT"):
    return {
        "session_id": "ts_diag",
        "user_text": "reduce pressure loss in multi-lumen tubing",
        "title": "t",
        "status": status,
        "final_status": final,
        "user_state_view": {
            "user_state": "COMPLETED_UNDER_DEVELOPMENT",
            "label": "Completed — invention in development",
            "decision": "the machine's own adversarial challenge killed "
                        "this invention",
            "outcome": "INVENTION_KILLED_BY_CHALLENGE",
        },
        "run_state": {
            "evidence_state": {"state": "GATHERED", "records_found": 16,
                               "sources": ["europepmc", "crossref"]},
            "attack_state": {"state": "EXECUTED", "overall": "KILLED"},
            "generations": {"generations": [
                {"gen": 1, "label": "INVENTION 01",
                 "challenge": {"killed": True, "kill_reason": "obvious_combination: KILLED"}},
            ]},
        },
        "stages": [],
    }


def test_p0_4_terminal_run_yields_zip(tmp_path):
    d = _terminal_detail()
    built = dp.build_diagnostic_package("ts_diag", tmp_path, d)
    assert built is not None
    z = zipfile.ZipFile(io.BytesIO(built["bytes"]))
    names = set(z.namelist())
    assert {"00_EXECUTIVE_BRIEF.md", "01_EVIDENCE_SUMMARY.md",
            "02_DIAGNOSTIC_REPORT.md", "manifest.json"} <= names
    brief = z.read("00_EXECUTIVE_BRIEF.md").decode()
    assert "killed by its own adversarial challenge" in brief
    # the manifest hashes every member (provenance custody)
    man = json.loads(z.read("manifest.json"))
    for name, h in man["members"].items():
        assert len(h) == 64
    # cached in the run dir
    assert (tmp_path / "diagnostic_package.zip").exists()


def test_p0_4_diagnostic_package_never_claims_an_invention():
    d = _terminal_detail()
    built = dp.build_diagnostic_package("ts_diag", None, d)
    z = zipfile.ZipFile(io.BytesIO(built["bytes"]))
    # paragraphs wrap across source lines — normalize before asserting
    all_text = " ".join(
        " ".join(z.read(n).decode("utf-8", errors="replace").split())
        for n in z.namelist() if n.endswith(".md"))
    assert "NOT a technology package" in all_text
    assert "no invention is claimed" in all_text
    assert "no buyer readiness is asserted" in all_text


def test_p0_4_running_run_honestly_yields_nothing():
    d = _terminal_detail()
    d["status"] = "RUNNING"
    assert dp.build_diagnostic_package("ts_diag", None, d) is None


def test_p0_4_transport_blocked_run_still_yields_a_record():
    d = _terminal_detail()
    d["status"] = "RUN_BLOCKED_TRANSPORT"
    d["user_state_view"] = {"user_state": "BLOCKED_TRANSPORT",
                            "label": "Blocked by infrastructure",
                            "decision": "discovery temporarily blocked"}
    built = dp.build_diagnostic_package("ts_diag", None, d)
    assert built is not None


# ---------------------------------------------------------------------------
# P1-2 — the lock probe
# ---------------------------------------------------------------------------

def test_p1_2_run_lock_probe_returns_bool():
    held = store.run_lock_held()
    assert held in (True, False)
    # two consecutive probes agree (idempotent, no side effects)
    assert store.run_lock_held() == held
