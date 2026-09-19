"""tests/test_r510_reality_loop.py — R510 P0 production reality-loop battery
(auditor §13). Exercises the production entrypoint
(execute_reality_event), never pure helpers alone:

  valid real event / missing provenance / invalid hash / duplicate /
  concurrent duplicate / CONTROLLED_REHEARSAL / rehearsal KILL /
  real KILL / KEEP / MODIFY / MIXED routing / child creation /
  duplicate-child prevention / restart before+after launch / child
  consumes knowledge / verdict-flip behavior change / learning-without-
  change attack / infra-failure stays non-scientific / no fabricated
  observation.

Cemetery is redirected to tmp via CEMETERY_PATH patch (canonical state
never touched, Art. IX). Launchers are fakes except where noted; the
default EngineRun launcher is exercised only in keyed fresh proof.
"""

import json
import sys
import threading
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import reality_ingestion as ri  # noqa: E402
from orchestrator import mechanism_cemetery as mc  # noqa: E402

H1 = "ab" * 32
H2 = "cd" * 32

PARENT_PROBLEM = {
    "problem_id": "pp0",
    "device": "engine cooling system",
    "failure": "coolant vapor leak under driving conditions",
    "constraint": "no engine removal",
}
PARENT_RUN = "engrun:pp0:test"


def _event(eid, verdict="KEEP", source="EXTERNAL_SYSTEM", **kw):
    ev = {
        "event_id": eid,
        "package_id": "PKG-1",
        "experiment_id": "EXP-1",
        "timestamp": "2026-09-19T00:00:00Z",
        "apparatus_id": "RIG-1",
        "operator": "op1",
        "raw_data_hash": H1,
        "processed_data_hash": H2,
        "measurement_units": {"unit": "mL/min"},
        "uncertainty": {"plus_minus": 0.1},
        "baseline_result": 1.0,
        "candidate_result": 1.1,
        "pre_registered_threshold": 0.4,
        "decision": {"verdict": verdict,
                     "rule_id": "P04-KILL-B-NOPROTECTION",
                     "rule_trace": ["zero protection measured"]},
        "source_type": source,
        "organization": "lab",
        "custody_chain": [{"actor": "op1", "action": "measured"}],
        "attestation": {"attestation_text": "measured",
                        "attestation_hash": "h"},
        "provenance_validated": True,
    }
    ev.update(kw)
    return ev


def _cemetery(tmp_path):
    return mock.patch.object(mc, "CEMETERY_PATH",
                             tmp_path / "cemetery" / "CEMETERY.json")


def _fake_launcher(calls):
    def _launch(req):
        calls.append(req["trigger_event_id"])
        return {"child_run_id": req["child_run_id"],
                "launcher": "fake", "launched_at": "t"}
    return _launch


def _kill_cemetery(tmp_path):
    return str(tmp_path / "cemetery" / "CEMETERY.json")


# valid real KEEP -------------------------------------------------------
def test_valid_real_keep_mutates_with_linkage(tmp_path):
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            _event("EV-KEEP-1"), str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert rec["executed"] is True
    assert rec["execution_state"] == "EXECUTED_REAL"
    assert rec["branch"] == "KEEP"
    layers = rec["branch_record"]["layers"]
    assert layers["evidence"]["state"] == "LINKED"
    for layer in ("package_state", "commercial_state"):
        assert layers[layer]["state"] == "MUTATED", layers[layer]
    assert ri.verify_ledger(
        str(tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json"))["valid"]


# missing provenance / invalid hash --------------------------------------
def test_missing_provenance_invalid(tmp_path):
    ev = _event("EV-BAD-1")
    del ev["attestation"]
    rec = ri.execute_reality_event(ev, str(tmp_path / "ledger"))
    assert rec["executed"] is False
    assert rec["execution_state"] == "EXECUTION_INVALID"
    assert not (tmp_path / "ledger").exists()


def test_invalid_hash_invalid(tmp_path):
    ev = _event("EV-BAD-2", raw_data_hash="xyz")
    rec = ri.execute_reality_event(ev, str(tmp_path / "ledger"))
    assert rec["executed"] is False
    assert any("sha256" in p for p in rec["problems"])


# duplicate / concurrent duplicate ----------------------------------------
def test_duplicate_returns_stored_result(tmp_path):
    kw = dict(parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    with _cemetery(tmp_path):
        r1 = ri.execute_reality_event(_event("EV-DUP-1"),
                                      str(tmp_path / "ledger"), **kw)
        r2 = ri.execute_reality_event(_event("EV-DUP-1"),
                                      str(tmp_path / "ledger"), **kw)
    assert r2["duplicate"] is True and r2["replayed"] is True
    assert r2["entry_sha256"] == r1["entry_sha256"]
    led = json.loads((tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json")
                     .read_text())
    assert led["entry_count"] == 1


def test_concurrent_duplicate_single_ingest(tmp_path):
    kw = dict(parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    results = []
    with _cemetery(tmp_path):
        def _one():
            results.append(ri.execute_reality_event(
                _event("EV-RACE-1"), str(tmp_path / "ledger"), **kw))
        threads = [threading.Thread(target=_one) for _i in range(8)]
        [t.start() for t in threads]
        [t.join() for t in threads]
    assert sum(1 for r in results if r.get("executed")) == 1, results
    led = json.loads((tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json")
                     .read_text())
    assert led["entry_count"] == 1
    assert ri.verify_ledger(
        str(tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json"))["valid"]


# rehearsal isolation ------------------------------------------------------
def test_rehearsal_never_counts_never_appends(tmp_path):
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            _event("EV-REH-1", source="CONTROLLED_REHEARSAL"),
            str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert rec["execution_state"] == "EXECUTED_REHEARSAL"
    assert rec["counts_as_physical_learning"] is False
    assert not (tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json").exists()
    assert not (tmp_path / "cemetery" / "CEMETERY.json").exists()


def test_rehearsal_kill_isolation_attack(tmp_path):
    calls = []
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            _event("EV-REH-K-1", verdict="KILL",
                   source="CONTROLLED_REHEARSAL"),
            str(tmp_path / "ledger"), run_launcher=_fake_launcher(calls),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert calls == [], "rehearsal must never invoke the launcher"
    assert rec["branch_record"]["rehearsal_cemetery_skipped"]
    assert not (tmp_path / "cemetery" / "CEMETERY.json").exists()
    assert rec["child"]["request_status"] == "REQUESTED"
    assert rec["counts_as_physical_learning"] is False


# real KILL -----------------------------------------------------------------
def test_real_kill_appends_constrains_requests(tmp_path):
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            _event("EV-KILL-1", verdict="KILL"),
            str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert rec["branch"] == "KILL"
    assert rec["branch_record"]["cemetery_appended"] is True
    data = json.loads((tmp_path / "cemetery" / "CEMETERY.json")
                      .read_text())
    assert any("EV-KILL-1" in (e.get("evidence_sources") or [])
               for e in data["entries"])
    link = json.loads((tmp_path / "ledger" / "cemetery_links" /
                       "EV-KILL-1.json").read_text())
    assert link["cemetery_entry_id"] == \
        rec["branch_record"]["cemetery_entry_id"]
    child = rec["child"]
    assert child["request_status"] == "REQUESTED"
    impact = rec["search_impact"]
    for key in ("parent_run_id", "trigger_event_id",
                "knowledge_record_id", "search_state_before",
                "knowledge_added", "search_state_after",
                "behavioral_change_expected",
                "behavioral_change_observed", "child_run_id"):
        assert key in impact, key
    assert (impact["search_state_before"]["parent_problem_sha256"]
            != impact["search_state_after"]["child_problem_sha256"])


# MODIFY + MIXED -------------------------------------------------------------
def test_modify_registers_hypothesis_and_delta(tmp_path):
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            _event("EV-MOD-1", verdict="MODIFY"),
            str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    hyp = rec["branch_record"]["hypothesis"]
    assert hyp["hypothesis_id"] == "HYP-EV-MOD-1"
    assert hyp["delta"]["direction"] == "up"
    assert hyp["delta"]["threshold_met"] is True
    assert (tmp_path / "ledger" / "hypotheses" / "EV-MOD-1.json").exists()


def test_mixed_routes_modify_conservatively(tmp_path):
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            _event("EV-MIX-1", verdict="MIXED"),
            str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert rec["branch"] == "MODIFY"
    assert "mixed_routing" in rec["branch_record"]


# child creation / duplicates / restart ---------------------------------------
def test_child_launch_and_no_duplicate(tmp_path):
    calls = []
    kw = dict(parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    with _cemetery(tmp_path):
        r1 = ri.execute_reality_event(
            _event("EV-CH-1", verdict="KILL"), str(tmp_path / "ledger"),
            run_launcher=_fake_launcher(calls), **kw)
        r2 = ri.execute_reality_event(
            _event("EV-CH-1", verdict="KILL"), str(tmp_path / "ledger"),
            run_launcher=_fake_launcher(calls), **kw)
    assert calls == ["EV-CH-1"], calls
    assert r1["child"]["request_status"] == "LAUNCHED"
    assert r2["duplicate"] is True
    req = json.loads((tmp_path / "ledger" / "child_requests" /
                      "EV-CH-1.json").read_text())
    assert req["status"] == "LAUNCHED"


def test_restart_before_launch_then_after(tmp_path):
    calls = []
    kw = dict(parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    with _cemetery(tmp_path):
        r1 = ri.execute_reality_event(
            _event("EV-RS-1", verdict="KILL"), str(tmp_path / "ledger"),
            run_launcher=None, **kw)
        assert r1["child"]["request_status"] == "REQUESTED"
        assert calls == []
        resumed = ri.resume_pending_children(
            str(tmp_path / "ledger"), _fake_launcher(calls))
        assert [l["trigger"] for l in resumed["launched"]] == ["EV-RS-1"]
        resumed2 = ri.resume_pending_children(
            str(tmp_path / "ledger"), _fake_launcher(calls))
        assert resumed2["launched"] == []
        assert calls == ["EV-RS-1"], calls


# consumption + behavior change -------------------------------------------------
def test_child_consumes_knowledge_with_measured_delta(tmp_path):
    calls = []
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            _event("EV-CO-1", verdict="KILL"), str(tmp_path / "ledger"),
            run_launcher=_fake_launcher(calls),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    req_path = tmp_path / "ledger" / "child_requests" / "EV-CO-1.json"
    req = json.loads(req_path.read_text())
    child_problem = req["child_problem"]
    assert child_problem["reality_constraints"]["trigger_event_id"] == \
        "EV-CO-1"
    assert child_problem["reality_constraints"]["knowledge_record_id"] == \
        rec["branch_record"]["cemetery_entry_id"]
    assert "[REALITY EV-CO-1:" in child_problem["constraint"]
    assert req["parent_problem_sha256"] != req["child_problem_sha256"]
    assert child_problem["problem_id"] != PARENT_PROBLEM["problem_id"]


def test_verdict_flip_proves_consumption(tmp_path):
    # Single-variable flip: an EMPTY cemetery (pre-seeded file, so the
    # builtin INITIAL lessons cannot interfere) + a probe drawn from
    # the to-be-appended entry's own vocabulary. BEFORE: PROCEED.
    # AFTER kill+append: the new entry hard-blocks the same probe.
    # The probe vocabulary comes from the entry fields the code
    # actually writes (mechanism_name/lesson/constraint), measured
    # against entry_domain_terms — not assumed.
    probe = ("PKG-1 mechanism killed frozen experiment contract "
             "measurement confront architecture family future")
    (tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
    (tmp_path / "cemetery" / "CEMETERY.json").write_text(
        json.dumps({"description": "test-empty", "entries": []}))
    with _cemetery(tmp_path):
        before = mc.check_candidate_against_cemetery(probe)
        assert before.get("verdict") == "PROCEED", before
        assert before.get("hard_blocks") == []
        ri.execute_reality_event(
            _event("EV-FL-1", verdict="KILL"), str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
        after = mc.check_candidate_against_cemetery(probe)
    assert any(b.get("cemetery_entry") == "KA-PKG-1-EXP-1-001"
               for b in after.get("hard_blocks", [])), after


# learning-without-change attack / infra failure / fabrication ------------------
def test_learning_without_numbers_stays_false(tmp_path):
    ev = _event("EV-LN-1")
    ev["baseline_result"] = "warm"
    ev["candidate_result"] = "warmer"
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            ev, str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert rec["counts_as_physical_learning"] is False
    assert rec["branch_record"]["adjudication"]["verdict"] == \
        "INSUFFICIENT_DATA"


def test_infra_failure_never_scientific_kill(tmp_path):
    ev = _event("EV-INF-1")
    ev["decision"] = {"verdict": "EXECUTION_BLOCKED"}
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            ev, str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert rec["executed"] is False
    assert rec["execution_state"] == "EXECUTION_BLOCKED"
    assert "branch_record" not in rec
    assert not (tmp_path / "cemetery" / "CEMETERY.json").exists()


def test_no_fabricated_observation(tmp_path):
    ev = _event("EV-FAB-1")
    with _cemetery(tmp_path):
        rec = ri.execute_reality_event(
            ev, str(tmp_path / "ledger"),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    led = json.loads((tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json")
                     .read_text())
    stored = [e for e in led["entries"]
              if e["event_id"] == "EV-FAB-1"][0]["record"]
    for key in ("candidate_result", "baseline_result", "raw_data_hash",
                "decision"):
        assert stored[key] == ev[key], key
    assert rec["entry_sha256"]
