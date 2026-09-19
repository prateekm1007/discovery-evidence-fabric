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


class _FakeStore:
    """Injectable credential store (tests only): session_id ->
    issued owner capability. Mirrors TOSCANINI.sessions.session_access
    verdicts (OWNER | PUBLIC | DENY | None) without touching real
    sessions (Art. IX)."""

    def __init__(self, mapping):
        self._m = dict(mapping)

    def session_access(self, sid, key):
        if sid not in self._m:
            return None
        return "OWNER" if self._m[sid] == key else "DENY"


STORE_OK = _FakeStore({"TS-1": "owner-1"})
AUTH_OK = {"session_id": "TS-1", "owner_key": "owner-1"}


def _exec(ev, ledger, **kw):
    kw.setdefault("auth", dict(AUTH_OK))
    kw.setdefault("session_store", STORE_OK)
    return ri.execute_reality_event(ev, ledger, **kw)


def _raising_store():
    class _Raising:
        def session_access(self, sid, key):
            raise ConnectionError("vault unreachable")
    return _Raising()


def _kill_cemetery(tmp_path):
    return str(tmp_path / "cemetery" / "CEMETERY.json")


# valid real KEEP -------------------------------------------------------
def test_valid_real_keep_mutates_with_linkage(tmp_path):
    with _cemetery(tmp_path):
        rec = _exec(
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
    rec = _exec(ev, str(tmp_path / "ledger"))
    assert rec["executed"] is False
    assert rec["execution_state"] == "EXECUTION_INVALID"
    assert not (tmp_path / "ledger").exists()


def test_invalid_hash_invalid(tmp_path):
    ev = _event("EV-BAD-2", raw_data_hash="xyz")
    rec = _exec(ev, str(tmp_path / "ledger"))
    assert rec["executed"] is False
    assert any("sha256" in p for p in rec["problems"])


# duplicate / concurrent duplicate ----------------------------------------
def test_duplicate_returns_stored_result(tmp_path):
    kw = dict(parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    with _cemetery(tmp_path):
        r1 = _exec(_event("EV-DUP-1"),
                                      str(tmp_path / "ledger"), **kw)
        r2 = _exec(_event("EV-DUP-1"),
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
            results.append(_exec(
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
        rec = _exec(
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
        rec = _exec(
            _event("EV-REH-K-1", verdict="KILL",
                   source="CONTROLLED_REHEARSAL"),
            str(tmp_path / "ledger"), run_launcher=_fake_launcher(calls),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path))
    assert calls == [], "rehearsal must never invoke the launcher"
    assert rec["branch_record"]["rehearsal_cemetery_skipped"]
    assert not (tmp_path / "cemetery" / "CEMETERY.json").exists()
    assert rec["child"]["request_status"] == "NO_REQUEST", \
        "rehearsal child requests are in-memory only: nothing durable "\
        "to launch later (stronger than REQUESTED-and-held)"
    assert rec["counts_as_physical_learning"] is False


# real KILL -----------------------------------------------------------------
def test_real_kill_appends_constrains_requests(tmp_path):
    with _cemetery(tmp_path):
        rec = _exec(
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
        rec = _exec(
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
        rec = _exec(
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
        r1 = _exec(
            _event("EV-CH-1", verdict="KILL"), str(tmp_path / "ledger"),
            run_launcher=_fake_launcher(calls), **kw)
        r2 = _exec(
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
        r1 = _exec(
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
        rec = _exec(
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
        _exec(
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
        rec = _exec(
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
        rec = _exec(
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
        rec = _exec(
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


# auth binding (§4) -----------------------------------------------------------
def test_auth_accept_owner_executes(tmp_path):
    rec = _exec(_event("EV-AU-1"), str(tmp_path / "ledger"),
                parent_problem=dict(PARENT_PROBLEM),
                parent_run_id=PARENT_RUN,
                cemetery_path=_kill_cemetery(tmp_path))
    assert rec["executed"] is True
    assert rec["auth"] == {"mode": "owner-capability",
                           "session_id": "TS-1", "access": "OWNER",
                           "authenticated": True}
    assert "owner_key" not in json.dumps(rec), "key values never persist"


def test_auth_wrong_key_blocked_before_state(tmp_path):
    rec = ri.execute_reality_event(
        _event("EV-AU-2"), str(tmp_path / "ledger"),
        auth={"session_id": "TS-1", "owner_key": "wrong"},
        session_store=STORE_OK)
    assert rec["executed"] is False
    assert rec["execution_state"] == "EXECUTION_BLOCKED"
    assert rec["auth"]["access"] == "DENY"
    assert not (tmp_path / "ledger").exists(), \
        "denied callers leave no state (fail-closed)"


def test_auth_missing_blocked(tmp_path):
    rec = ri.execute_reality_event(_event("EV-AU-3"),
                                   str(tmp_path / "ledger"),
                                   session_store=STORE_OK)
    assert rec["executed"] is False
    assert "no caller capability" in rec["auth"]["reason"]


def test_auth_store_unreachable_typed(tmp_path):
    rec = ri.execute_reality_event(
        _event("EV-AU-4"), str(tmp_path / "ledger"),
        auth=dict(AUTH_OK), session_store=_raising_store())
    assert rec["executed"] is False
    assert "unreachable" in rec["auth"]["reason"]
    assert not (tmp_path / "ledger").exists()


# legacy-flag separation (§18) --------------------------------------------------
def test_legacy_learning_flag_never_proves_learning():
    ev = {"source_type": "EXTERNAL_SYSTEM"}
    assert ri._learning_countable(
        ev, {"adjudication": {"verdict": "INSUFFICIENT_DATA",
                              "counts_as_learning": True}}) is False
    assert ri._learning_countable(
        ev, {"adjudication": {"verdict": "MODEL_IMPROVED",
                              "counts_as_learning": False}}) is True
    assert ri._learning_countable(ev, {}) == "UNDETERMINED"


# claim concurrency: exactly one launch right (§10) ------------------------------
def test_concurrent_claim_single_launch(tmp_path):
    with _cemetery(tmp_path):
        rec = _exec(_event("EV-CC-1", verdict="KILL"),
                    str(tmp_path / "ledger"), run_launcher=None,
                    parent_problem=dict(PARENT_PROBLEM),
                    parent_run_id=PARENT_RUN,
                    cemetery_path=_kill_cemetery(tmp_path))
    assert rec["child"]["request_status"] == "REQUESTED"
    calls = []
    results = []

    def _resume():
        results.append(ri.resume_pending_children(
            str(tmp_path / "ledger"), _fake_launcher(calls)))

    threads = [threading.Thread(target=_resume) for _i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert calls == ["EV-CC-1"], calls
    total = sum(len(r["launched"]) for r in results)
    assert total == 1, [r["launched"] for r in results]


# phased resume: crash between request and finalize (§12 C/D) ----------------------
def test_resume_after_request_before_finalize(tmp_path):
    with _cemetery(tmp_path):
        _exec(_event("EV-PH-1", verdict="KILL"),
              str(tmp_path / "ledger"), run_launcher=None,
              parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    (tmp_path / "ledger" / "executions" / "EV-PH-1.json").unlink()
    calls = []
    with _cemetery(tmp_path):
        rec = ri.resume_execution(
            str(tmp_path / "ledger"), "EV-PH-1",
            run_launcher=_fake_launcher(calls),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path),
            auth=dict(AUTH_OK), session_store=STORE_OK)
    assert rec["executed"] is True
    assert rec["resumed_after_crash"] is True
    assert calls == ["EV-PH-1"], calls
    data = json.loads((tmp_path / "cemetery" / "CEMETERY.json")
                      .read_text())
    assert sum(1 for e in data["entries"]
               if "EV-PH-1" in (e.get("evidence_sources") or [])) == 1


def test_resume_finalized_replays_without_reexecution(tmp_path):
    with _cemetery(tmp_path):
        r1 = _exec(_event("EV-PH-2", verdict="KILL"),
                   str(tmp_path / "ledger"), run_launcher=None,
                   parent_problem=dict(PARENT_PROBLEM),
                   parent_run_id=PARENT_RUN,
                   cemetery_path=_kill_cemetery(tmp_path))
        assert r1["executed"] is True
        calls = []
        r2 = ri.resume_execution(
            str(tmp_path / "ledger"), "EV-PH-2",
            run_launcher=_fake_launcher(calls),
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path),
            auth=dict(AUTH_OK), session_store=STORE_OK)
    assert r2["duplicate"] is True and r2["replayed"] is True
    assert calls == []


def test_resume_unknown_event_and_denied_caller(tmp_path):
    r = ri.resume_execution(str(tmp_path / "ledger"), "EV-NOPE",
                            auth=dict(AUTH_OK), session_store=STORE_OK)
    assert r["executed"] is False
    assert r["execution_state"] == "UNKNOWN"
    r = ri.resume_execution(str(tmp_path / "ledger"), "EV-NOPE",
                            auth={"session_id": "TS-1",
                                  "owner_key": "wrong"},
                            session_store=STORE_OK)
    assert r["executed"] is False
    assert r["execution_state"] == "EXECUTION_BLOCKED"


# registry rebuild identity + canonical mutation (§5) --------------------------------
def test_registry_rebuild_identity_and_mutation_linkage(tmp_path):
    with _cemetery(tmp_path):
        rec = _exec(_event("EV-RG-1"), str(tmp_path / "ledger"),
                    parent_problem=dict(PARENT_PROBLEM),
                    parent_run_id=PARENT_RUN,
                    cemetery_path=_kill_cemetery(tmp_path))
    impact = rec["search_impact"]
    assert impact["measurement_basis"].startswith("mutation sidecars")
    reg_path = tmp_path / "ledger" / "REALITY_STATE.json"
    assert reg_path.exists()
    live_packages = json.loads(reg_path.read_text()).get("packages")
    pkg = live_packages["PKG-1"]
    assert pkg["status"] == "OBSERVED_KEEP"
    assert pkg["last_event_id"] == "EV-RG-1"
    assert pkg["mutation_ids"], "KEEP mutations must be registered"
    expected = ri._loop_sha({"artifact_type": "REALITY_STATE/1.0.0",
                             "packages": live_packages})
    assert ri.rebuild_reality_state(
        str(tmp_path / "ledger"))["match"] is True
    reg_path.unlink()
    rebuilt = ri.rebuild_reality_state(str(tmp_path / "ledger"))
    assert rebuilt["rebuilt_hash"] == expected, rebuilt
    assert rebuilt["match"] is False, rebuilt


# expanded impact shape (§9) ----------------------------------------------------------
def test_impact_expanded_shape_kill(tmp_path):
    with _cemetery(tmp_path):
        rec = _exec(_event("EV-IM-1", verdict="KILL"),
                    str(tmp_path / "ledger"),
                    parent_problem=dict(PARENT_PROBLEM),
                    parent_run_id=PARENT_RUN,
                    cemetery_path=_kill_cemetery(tmp_path))
    impact = rec["search_impact"]
    for key in ("knowledge_delta_id", "operator_region_before",
                "operator_region_after", "cemetery_constraints_before",
                "cemetery_constraints_after", "query_policy_before",
                "query_policy_after", "child_consumed_delta",
                "measurement_basis"):
        assert key in impact, key
    before = impact["cemetery_constraints_before"]
    after = impact["cemetery_constraints_after"]
    assert before["state"] == "UNKNOWN_NO_CEMETERY_PATH", before
    assert after["entry_count"] == 1, after
    assert after["head_sha256"]
    assert impact["query_policy_before"] == "UNKNOWN_NO_QUERY_REGISTRY"


# corruption + forgery attacks (§7) ----------------------------------------------
def test_corrupted_ledger_typed_not_traceback(tmp_path):
    (tmp_path / "ledger").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json").write_text(
        "{corrupt", encoding="utf-8")
    rec = _exec(_event("EV-COR-1"), str(tmp_path / "ledger"),
                parent_problem=dict(PARENT_PROBLEM),
                parent_run_id=PARENT_RUN,
                cemetery_path=_kill_cemetery(tmp_path))
    assert rec["executed"] is False
    assert rec["execution_state"] == "EXECUTION_BLOCKED"
    assert any("CORRUPT" in p for p in rec["problems"]), rec


def test_corrupted_registry_refuses_without_fork(tmp_path):
    with _cemetery(tmp_path):
        _exec(_event("EV-RGC-1"), str(tmp_path / "ledger"),
              parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    (tmp_path / "ledger" / "REALITY_STATE.json").write_text(
        "{corrupt", encoding="utf-8")
    with _cemetery(tmp_path):
        rec = _exec(_event("EV-RGC-2"), str(tmp_path / "ledger"),
                    parent_problem=dict(PARENT_PROBLEM),
                    parent_run_id=PARENT_RUN,
                    cemetery_path=_kill_cemetery(tmp_path))
    assert rec["executed"] is False
    assert rec["execution_state"] == "EXECUTION_BLOCKED"
    assert any("CORRUPT" in p for p in rec["problems"]), rec


def test_forged_finalized_without_ledger_is_unknown(tmp_path):
    forged = {"executed": True, "event_id": "EV-FG-1",
              "execution_state": "EXECUTED_REAL", "branch": "KEEP",
              "phase": "FINALIZED"}
    (tmp_path / "ledger" / "executions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "ledger" / "executions" / "EV-FG-1.json").write_text(
        json.dumps(forged), encoding="utf-8")
    rec = ri.resume_execution(
        str(tmp_path / "ledger"), "EV-FG-1",
        auth=dict(AUTH_OK), session_store=STORE_OK)
    assert rec["executed"] is False
    assert rec["execution_state"] == "UNKNOWN"


class _EffectLauncher:
    """Identity-preserving test double (§11): models idempotent remote
    execution as an effect registry keyed by launch_id. Retries with
    the same launch id converge on ONE effect; receipts converge on
    the same child. fail modes: None | "timeout-after-effect"
    (records the effect, then raises like a lost response) |
    "reject" (raises LauncherRejected with no effect)."""

    def __init__(self, fail=None):
        self.effects = {}
        self.calls = []
        self.fail = fail

    def __call__(self, req):
        lid = req["launch_id"]
        self.calls.append(lid)
        if lid in self.effects:
            return dict(self.effects[lid], duplicate=True)
        if self.fail == "reject":
            raise ri.LauncherRejected("admission refused (test)")
        ex = {"launch_id": lid,
              "child_run_id": req["child_run_id"], "state": "RUNNING"}
        self.effects[lid] = ex
        if self.fail == "timeout-after-effect":
            self.fail = None
            raise TimeoutError("response lost after effect (test)")
        return dict(ex, receipt=True)

    def check(self, launch_id, hint=None):
        return self.effects.get(launch_id)


def test_claimed_abandoned_recovers_single_launch(tmp_path):
    with _cemetery(tmp_path):
        _exec(_event("EV-AB-1", verdict="KILL"),
              str(tmp_path / "ledger"), run_launcher=None,
              parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    req_path = tmp_path / "ledger" / "child_requests" / "EV-AB-1.json"
    req = json.loads(req_path.read_text())
    req["status"] = "CLAIMED"
    req["claim"] = {"claimed_at": "2026-01-01T00:00:00Z",
                    "note": "simulated crash between claim and launch"}
    req_path.write_text(json.dumps(req), encoding="utf-8")
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        out = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx, fx.check)
    assert [l["trigger"] for l in out["launched"]] == ["EV-AB-1"]
    assert len(fx.effects) == 1
    out2 = ri.resume_pending_children(
        str(tmp_path / "ledger"), fx, fx.check)
    assert out2["launched"] == []
    assert len(fx.effects) == 1
    req2 = json.loads(req_path.read_text())
    assert req2["status"] == "LAUNCHED"
    assert req2["launch_id"] == req["launch_id"]


def _kill_request(tmp_path, eid="EV-ADV-1"):
    with _cemetery(tmp_path):
        _exec(_event(eid, verdict="KILL"),
              str(tmp_path / "ledger"), run_launcher=None,
              parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    return json.loads((tmp_path / "ledger" / "child_requests" /
                       (eid + ".json")).read_text())


# A. stale claim cannot fork a second child -------------------------------
def test_a_stale_claim_cannot_fork(tmp_path):
    req = _kill_request(tmp_path, "EV-ADV-A")
    lid = req["launch_id"]
    claimed, _ = ri._claim_child(str(tmp_path / "ledger"), "EV-ADV-A")
    assert claimed is True
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        out = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx, fx.check)
    assert [l["trigger"] for l in out["launched"]] == ["EV-ADV-A"]
    assert list(fx.effects) == [lid]
    cur = json.loads((tmp_path / "ledger" / "child_requests" /
                      "EV-ADV-A.json").read_text())
    assert cur["status"] == "LAUNCHED"


# B. death before receipt recovers the same launch id -----------------------
def test_b_death_before_receipt_same_id(tmp_path):
    req = _kill_request(tmp_path, "EV-ADV-B")
    lid = req["launch_id"]
    claimed, _ = ri._claim_child(str(tmp_path / "ledger"), "EV-ADV-B")
    assert claimed is True
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        out = ri.reconcile_unknown_launch(
            str(tmp_path / "ledger"), "EV-ADV-B", fx, fx.check)
    assert out["state"] == "LAUNCHED", out
    assert out["child_run_id"] == req["child_run_id"]
    assert len(fx.effects) == 1
    assert list(fx.effects) == [lid]
    cur = json.loads((tmp_path / "ledger" / "child_requests" /
                      "EV-ADV-B.json").read_text())
    assert cur["status"] == "LAUNCHED"
    assert cur["launch_id"] == lid


# C. lost response adopts the existing effect ---------------------------------
def test_c_lost_response_adopts_no_second_effect(tmp_path):
    _kill_request(tmp_path, "EV-ADV-C")
    fx = _EffectLauncher(fail="timeout-after-effect")
    with _cemetery(tmp_path):
        out = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx, fx.check)
    assert out["launched"] == [], out
    assert any("UNKNOWN" in str(f.get("error", "")) or
               "ambiguous" in str(f.get("error", ""))
               for f in out["failed"]), out
    assert len(fx.effects) == 1
    assert len(fx.calls) == 1
    cur = json.loads((tmp_path / "ledger" / "child_requests" /
                      "EV-ADV-C.json").read_text())
    assert cur["status"] == "UNKNOWN_LAUNCH", cur["status"]
    with _cemetery(tmp_path):
        out2 = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx, fx.check)
    assert [l["trigger"] for l in out2["launched"]] == ["EV-ADV-C"]
    assert out2["launched"][0]["reconciled"] is True
    assert len(fx.calls) == 1, "reconcile must adopt, never relaunch"
    assert len(fx.effects) == 1
    cur = json.loads((tmp_path / "ledger" / "child_requests" /
                      "EV-ADV-C.json").read_text())
    assert cur["status"] == "LAUNCHED"


# D. two concurrent resumers, one effective child ------------------------------
def test_d_concurrent_resume_single_effect(tmp_path):
    _kill_request(tmp_path, "EV-ADV-D")
    fx = _EffectLauncher()
    outs = []

    def _resume():
        with _cemetery(tmp_path):
            outs.append(ri.resume_pending_children(
                str(tmp_path / "ledger"), fx, fx.check))

    threads = [threading.Thread(target=_resume) for _i in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(fx.effects) == 1, fx.effects
    launched = [l for o in outs for l in o["launched"]]
    assert len(launched) == 1, launched


# E. duplicate resume after LAUNCHED: zero additional ------------------------------
def test_e_duplicate_resume_after_launched(tmp_path):
    _kill_request(tmp_path, "EV-ADV-E")
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        ri.resume_pending_children(str(tmp_path / "ledger"), fx, fx.check)
    n_calls, n_effects = len(fx.calls), len(fx.effects)
    with _cemetery(tmp_path):
        out = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx, fx.check)
    assert out["launched"] == []
    assert len(fx.calls) == n_calls
    assert len(fx.effects) == n_effects == 1


# F. malformed/corrupted request state ----------------------------------------------
def test_f_malformed_request_never_executes(tmp_path):
    (tmp_path / "ledger" / "child_requests").mkdir(parents=True,
                                                   exist_ok=True)
    (tmp_path / "ledger" / "child_requests" / "EV-ADV-F.json").write_text(
        "{broken", encoding="utf-8")
    fx = _EffectLauncher()
    out = ri.resume_pending_children(str(tmp_path / "ledger"), fx,
                                     fx.check)
    assert fx.calls == [] and not fx.effects
    assert out["failed"] and out["launched"] == []
    (tmp_path / "ledger" / "child_requests" / "EV-ADV-F.json").write_text(
        json.dumps({"status": "REQUESTED"}), encoding="utf-8")
    out2 = ri.resume_pending_children(str(tmp_path / "ledger"), fx,
                                      fx.check)
    assert fx.calls == [] and not fx.effects
    assert out2["launched"] == []


# G. tampered record fail-closed ----------------------------------------------
def test_g_tampered_launch_id_fail_closed(tmp_path):
    req = _kill_request(tmp_path, "EV-ADV-G")
    p = tmp_path / "ledger" / "child_requests" / "EV-ADV-G.json"
    tampered = json.loads(p.read_text())
    tampered["launch_id"] = "deadbeef" * 4
    p.write_text(json.dumps(tampered), encoding="utf-8")
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        out = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx, fx.check)
    assert fx.calls == [] and not fx.effects
    cur = json.loads(p.read_text())
    assert cur["status"] == "UNKNOWN_TAMPERED", cur["status"]
    assert out["launched"] == []
    assert req["launch_id"] != "deadbeef" * 4


# launch-id determinism + rejection path ----------------------------------------------
def test_launch_id_deterministic_and_recomputed(tmp_path):
    req = _kill_request(tmp_path, "EV-ADV-H")
    assert req["launch_id"] == ri._launch_id_for(
        req["trigger_event_id"], req["child_run_id"],
        req["knowledge_record_id"])
    ok, _ = ri._verify_request(req)
    assert ok is True


def test_rejected_becomes_failed_and_retries_same_id(tmp_path):
    _kill_request(tmp_path, "EV-ADV-I")
    fx = _EffectLauncher(fail="reject")
    with _cemetery(tmp_path):
        out = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx, fx.check)
    assert out["failed"] and out["launched"] == []
    assert not fx.effects
    cur = json.loads((tmp_path / "ledger" / "child_requests" /
                      "EV-ADV-I.json").read_text())
    assert cur["status"] == "LAUNCH_FAILED"
    fx2 = _EffectLauncher()
    with _cemetery(tmp_path):
        out2 = ri.resume_pending_children(
            str(tmp_path / "ledger"), fx2, fx2.check)
    assert [l["trigger"] for l in out2["launched"]] == ["EV-ADV-I"]
    assert len(fx2.effects) == 1


def test_default_execution_checker_filesystem(tmp_path):
    runs = tmp_path / "runs"
    (runs / "engrun_pp0_x").mkdir(parents=True, exist_ok=True)
    (runs / "engrun_pp0_x" / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_pp0_x"}), encoding="utf-8")
    check = ri.default_execution_checker(str(runs))
    found = check("any-launch-id", {"child_run_id": "engrun_pp0_x"})
    assert found and found["child_run_id"] == "engrun_pp0_x"
    assert check("any-launch-id",
                 {"child_run_id": "engrun_pp0_absent"}) is None


# trace integrity: recovered_from captures the prior state (§6) --------------
def test_recovered_from_claimed_on_promote(tmp_path):
    _kill_request(tmp_path, "EV-TR-1")
    p = tmp_path / "ledger" / "child_requests" / "EV-TR-1.json"
    req = json.loads(p.read_text())
    req["status"] = "CLAIMED"
    p.write_text(json.dumps(req), encoding="utf-8")
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        ri.resume_pending_children(str(tmp_path / "ledger"), fx,
                                   fx.check)
    cur = json.loads(p.read_text())
    recs = [r for r in cur.get("reconciliation_history", [])
            if r.get("action") == "promote-claimed-unknown"]
    assert recs and recs[0]["recovered_from"] == "CLAIMED", recs


def test_recovered_from_failed_on_retry(tmp_path):
    _kill_request(tmp_path, "EV-TR-2")
    p = tmp_path / "ledger" / "child_requests" / "EV-TR-2.json"
    req = json.loads(p.read_text())
    req["status"] = "LAUNCH_FAILED"
    req["launch_error"] = "LauncherRejected: bad shape (seeded)"
    p.write_text(json.dumps(req), encoding="utf-8")
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        ri.resume_pending_children(str(tmp_path / "ledger"), fx,
                                   fx.check)
    cur = json.loads(p.read_text())
    assert cur["status"] == "LAUNCHED"
    relaunch = [r for r in cur.get("reconciliation_history", [])
                if r.get("action") == "relaunch-same-id"]
    assert relaunch and relaunch[0]["recovered_from"] == \
        "LAUNCH_FAILED", relaunch


# corrupt execution record is never absence (§7) ---------------------------------
def test_corrupt_execution_record_fail_closed(tmp_path):
    with _cemetery(tmp_path):
        _exec(_event("EV-CX-1", verdict="KILL"),
              str(tmp_path / "ledger"), run_launcher=None,
              parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    (tmp_path / "ledger" / "executions" / "EV-CX-1.json").write_text(
        "{corrupt", encoding="utf-8")
    with _cemetery(tmp_path):
        rec = ri.resume_execution(
            str(tmp_path / "ledger"), "EV-CX-1",
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path),
            auth=dict(AUTH_OK), session_store=STORE_OK)
    assert rec["executed"] is False
    assert rec["execution_state"] == "UNKNOWN"


# hash-broken ledger blocks resume (§8) ----------------------------------------------
def test_hash_broken_ledger_blocks_resume(tmp_path):
    with _cemetery(tmp_path):
        _exec(_event("EV-HB-1", verdict="KILL"),
              str(tmp_path / "ledger"), run_launcher=None,
              parent_problem=dict(PARENT_PROBLEM),
              parent_run_id=PARENT_RUN,
              cemetery_path=_kill_cemetery(tmp_path))
    (tmp_path / "ledger" / "executions" / "EV-HB-1.json").unlink()
    led_path = tmp_path / "ledger" / "REALITY_EVENT_LEDGER.json"
    led = json.loads(led_path.read_text())
    led["entries"][0]["record"]["package_id"] = "TAMPERED"
    led_path.write_text(json.dumps(led), encoding="utf-8")
    with _cemetery(tmp_path):
        rec = ri.resume_execution(
            str(tmp_path / "ledger"), "EV-HB-1",
            parent_problem=dict(PARENT_PROBLEM),
            parent_run_id=PARENT_RUN,
            cemetery_path=_kill_cemetery(tmp_path),
            auth=dict(AUTH_OK), session_store=STORE_OK)
    assert rec["executed"] is False
    assert rec["execution_state"] == "UNKNOWN"
    assert rec["resume_gate"]["gate"] == "ledger-invalid", rec


# LAUNCHING reconciles without blind invoke ----------------------------------------------
def test_launching_reconciles_not_reinvokes(tmp_path):
    _kill_request(tmp_path, "EV-LG-1")
    p = tmp_path / "ledger" / "child_requests" / "EV-LG-1.json"
    req = json.loads(p.read_text())
    req["status"] = "LAUNCHING"
    p.write_text(json.dumps(req), encoding="utf-8")
    fx = _EffectLauncher()
    with _cemetery(tmp_path):
        out = ri.reconcile_unknown_launch(
            str(tmp_path / "ledger"), "EV-LG-1", fx, fx.check)
    assert out["state"] == "LAUNCHED"
    assert len(fx.effects) == 1
    cur = json.loads(p.read_text())
    assert cur["status"] == "LAUNCHED"


# consumption receipt from crafted child dir ----------------------------------------------
def test_consumption_receipt_binds_lineage(tmp_path):
    runs = tmp_path / "runs"
    child = runs / "engrun_pp0_reality_evtest01"
    child.mkdir(parents=True, exist_ok=True)
    problem = dict(PARENT_PROBLEM)
    problem["constraint"] = "base [REALITY EV-CB-1: KILL knowledge " \
        "KX constrains this search]"
    problem["reality_constraints"] = {"trigger_event_id": "EV-CB-1",
                                      "knowledge_record_id": "KX"}
    (child / "problem.json").write_text(json.dumps(problem),
                                        encoding="utf-8")
    (child / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_pp0_reality_evtest01"}),
        encoding="utf-8")
    out = ri.record_child_consumption(
        str(child), "EV-CB-1", PARENT_RUN, "KX", "kh" * 32,
        "ph" * 32)
    assert out["consumed"] is True
    rcp = out["receipt"]
    assert rcp["parent_event_id"] == "EV-CB-1"
    assert rcp["knowledge_record_id"] == "KX"
    assert rcp["constraint_clause_present"] is True
    assert rcp["parent_problem_sha256"] == "ph" * 32
    assert rcp["child_problem_sha256"] != "ph" * 32
    assert (child / "CONSUMPTION.json").exists()


# real default launcher path, stages disabled (offline-honest) --------------
def test_default_launcher_real_path_disabled_stages(tmp_path):
    from discovery_fabric.engine.adapters import STAGE_ORDER
    req = {"trigger_event_id": "EV-DL-1",
           "knowledge_record_id": "KX",
           "knowledge_artifact_sha256": "kh" * 32,
           "parent_run_id": PARENT_RUN,
           "parent_problem_sha256": "ph" * 32,
           "child_problem": dict(
               PARENT_PROBLEM, problem_id="pp0_reality_evdl01",
               constraint="base [REALITY EV-DL-1: KILL knowledge KX "
                          "constrains this search]",
               reality_constraints={
                   "trigger_event_id": "EV-DL-1",
                   "knowledge_record_id": "KX",
                   "knowledge_artifact_sha256": "kh" * 32,
                   "parent_run_id": PARENT_RUN,
                   "parent_problem_sha256": "ph" * 32,
                   "branch": "KILL",
                   "constraint_clause": "c"}),
           "child_run_id": "engrun_pp0_reality_evdl01",
           "launch_id": "lid-test-01",
           "session_id": None}
    runs = tmp_path / "runs"
    receipt = ri.default_run_launcher(
        req, str(runs), disabled_stages=list(STAGE_ORDER))
    assert receipt["child_run_id"] == "engrun_pp0_reality_evdl01"
    assert receipt["launcher"] == "default_engine_run"
    child_dir = runs / "engrun_pp0_reality_evdl01"
    assert (child_dir / "run_manifest.json").exists()
    assert (child_dir / "problem.json").exists()
    cons = receipt["consumption"]
    assert cons["consumed"] is True
    assert cons["receipt"]["knowledge_record_id"] == "KX"
    assert cons["receipt"]["parent_run_id"] == PARENT_RUN
    assert cons["receipt"]["knowledge_artifact_sha256"] == "kh" * 32
    check = ri.default_execution_checker(str(runs))
    found = check("lid-test-01",
                  {"child_run_id": "engrun_pp0_reality_evdl01"})
    assert found and found["child_run_id"] == \
        "engrun_pp0_reality_evdl01"


# full cycle on the real launcher: execute -> launch -> reconcile ------
def test_full_cycle_real_launcher_reconcile(tmp_path):
    import os as _os
    if _os.name == "nt":
        pytest = __import__("pytest")
        pytest.skip("production child_run_id values contain colons "
                    "(canonical engrun:...:... lineage format); Windows "
                    "filesystems reject them. Production runs Linux. "
                    "Covered on Windows by the colon-free launcher test "
                    "above; full-shape proof requires a POSIX host.")
    from discovery_fabric.engine.adapters import STAGE_ORDER
    dis = list(STAGE_ORDER)

    def _real(req):
        return ri.default_run_launcher(req, str(tmp_path / "runs"),
                                       disabled_stages=dis)

    with _cemetery(tmp_path):
        rec = _exec(_event("EV-FC-1", verdict="KILL"),
                    str(tmp_path / "ledger"), run_launcher=_real,
                    parent_problem=dict(PARENT_PROBLEM),
                    parent_run_id=PARENT_RUN,
                    cemetery_path=_kill_cemetery(tmp_path))
    assert rec["child"]["request_status"] == "LAUNCHED"
    child_id = rec["child"]["child_run_id"]
    with _cemetery(tmp_path):
        out = ri.reconcile_unknown_launch(
            str(tmp_path / "ledger"), "EV-FC-1", _real,
            ri.default_execution_checker(str(tmp_path / "runs")))
    assert out["state"] == "LAUNCHED"


def _vman_mut(eid, kid, art_sha, run_id, **over):
    m = {"run_id": run_id,
         "knowledge_consumed": {
             "trigger_event_id": eid,
             "knowledge_record_id": kid,
             "knowledge_artifact_sha256": art_sha,
             "parent_run_id": PARENT_RUN,
             "parent_problem_sha256": "ph" * 32,
             "branch": "KILL"}}
    m["knowledge_consumed"].update(over)
    return m


def test_manifest_run_id_mismatch_fails(tmp_path):
    problem = _vprob("EV-MM-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_mm01", problem,
                      dict(_vman("EV-MM-1", "KX", "kh" * 32,
                                 "engrun_mm01"),
                           run_id="engrun_mm01"))
    out = ri.verify_consumption(
        str(child),
        _vexp("EV-MM-1", "KX", "kh" * 32, run_id="engrun_WRONG"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False
    assert out["checks"]["manifest_run_id_match"] is False


def test_manifest_parent_run_mismatch_fails(tmp_path):
    problem = _vprob("EV-MP-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_mp01", problem,
                      _vman_mut("EV-MP-1", "KX", "kh" * 32, "engrun_mp01",
                                parent_run_id="engrun_DIFFERENT_PARENT"))
    out = ri.verify_consumption(
        str(child),
        _vexp("EV-MP-1", "KX", "kh" * 32, run_id="engrun_mp01"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False
    assert out["checks"]["manifest_parent_run_match"] is False


def test_manifest_parent_problem_mismatch_fails(tmp_path):
    problem = _vprob("EV-MQ-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_mq01", problem,
                      _vman_mut("EV-MQ-1", "KX", "kh" * 32, "engrun_mq01",
                                parent_problem_sha256="00" * 32))
    out = ri.verify_consumption(
        str(child),
        _vexp("EV-MQ-1", "KX", "kh" * 32, run_id="engrun_mq01"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False
    assert out["checks"]["manifest_parent_problem_match"] is False


def test_mentioned_not_consumed_fails(tmp_path):
    problem = dict(PARENT_PROBLEM, problem_id="pp0_mention")
    problem["constraint"] = "base mentioning KX knowledge in free text"
    child = _vrun_dir(tmp_path, "engrun_mention01", problem,
                      {"run_id": "engrun_mention01"})
    out = ri.verify_consumption(
        str(child),
        _vexp("EV-MN-1", "KX", "kh" * 32, run_id="engrun_mention01"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False


def test_cemetery_change_not_consumed_nonsubstantive(tmp_path):
    runs = tmp_path / "runs"
    for name in ("engrun_cc0", "engrun_cc1"):
        d = runs / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "problem.json").write_text(
            json.dumps(dict(PARENT_PROBLEM,
                            problem_id="pp0_cc_" + name[-1])),
            encoding="utf-8")
        (d / "run_manifest.json").write_text(
            json.dumps({"run_id": name}), encoding="utf-8")
    s0 = ri.extract_search_state(str(runs / "engrun_cc0"),
                                 cemetery_path=None)
    s1 = ri.extract_search_state(str(runs / "engrun_cc1"),
                                 cemetery_path=None)
    s0["cemetery"] = {"state": "READ", "entry_count": 0,
                      "head_sha256": "EMPTY"}
    s1["cemetery"] = {"state": "READ", "entry_count": 3,
                      "head_sha256": "h9"}
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False
    assert "knowledge_bound" not in delta["changed_fields"]


def test_real_constraint_text_alone_nonsubstantive(tmp_path):
    import hashlib as _hl
    art = dict(_VART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    runs = tmp_path / "runs"
    kbdir = runs / "engrun_rc01"
    kbdir.mkdir(parents=True, exist_ok=True)
    (kbdir / "problem.json").write_text(
        json.dumps(_vprob("EV-RC-2", "KX", art_sha)), encoding="utf-8")
    (kbdir / "run_manifest.json").write_text(
        json.dumps(dict(_vman("EV-RC-2", "KX", art_sha, "engrun_rc01"),
                        run_id="engrun_rc01")), encoding="utf-8")
    plaindir = runs / "engrun_rc00"
    plaindir.mkdir(parents=True, exist_ok=True)
    (plaindir / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_rc00")),
        encoding="utf-8")
    (plaindir / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_rc00"}), encoding="utf-8")
    s0 = ri.extract_search_state(str(plaindir))
    s1 = ri.extract_search_state(str(kbdir))
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False
    assert "knowledge_bound" in delta["changed_fields"]
    assert "clause_text_present_informational_only" in \
        delta["changed_fields"]
    assert "constraint_applied" not in delta["changed_fields"]


def test_replay_same_contract_no_duplicate_effect(tmp_path):
    import hashlib as _hl
    art = dict(_VART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    problem = _vprob("EV-RW-1", "KX", art_sha)
    child = _vrun_dir(tmp_path, "engrun_rw01", problem,
                      dict(_vman("EV-RW-1", "KX", art_sha, "engrun_rw01"),
                           run_id="engrun_rw01"))
    exp = _vexp("EV-RW-1", "KX", art_sha, run_id="engrun_rw01")
    r1 = ri.verify_consumption(str(child), exp,
                               _vresolver({"KX": art}))
    r2 = ri.verify_consumption(str(child), exp,
                               _vresolver({"KX": art}))
    assert r1["verified"] is True and r2["verified"] is True
    assert r1["contract"] == r2["contract"]


def _reality_problem(eid, kid):
    problem = dict(PARENT_PROBLEM)
    problem["constraint"] = "base [REALITY %s: KILL knowledge %s " \
        "constrains this search]" % (eid, kid)
    problem["reality_constraints"] = {
        "trigger_event_id": eid, "knowledge_record_id": kid,
        "knowledge_artifact_sha256": "kh" * 32,
        "parent_run_id": PARENT_RUN,
        "parent_problem_sha256": "ph" * 32,
        "branch": "KILL", "constraint_clause": "c"}
    problem["problem_id"] = "pp0_reality_" + eid.lower()
    return problem


# EngineRun writes the receipt from its own executed state --------------
def test_enginerun_writes_consumption_from_child(tmp_path):
    from discovery_fabric.engine.run import EngineRun
    from discovery_fabric.engine.adapters import STAGE_ORDER
    out = tmp_path / "runs" / "engrun_pp0_reality_evrc01"
    run = EngineRun(problem=_reality_problem("EV-RC-01", "KX"),
                    out_dir=str(out), run_id="engrun_pp0_reality_evrc01",
                    disabled_stages=list(STAGE_ORDER))
    run.run()
    assert (out / "problem.json").exists()
    assert (out / "CONSUMPTION.json").exists(), \
        "receipt must come from the child execution path"
    rcp = json.loads((out / "CONSUMPTION.json").read_text())
    assert rcp["parent_event_id"] == "EV-RC-01"
    assert rcp["knowledge_record_id"] == "KX"
    assert rcp["constraint_clause_present"] is True
    assert rcp["artifact_verification"] == "CARRIED_NOT_REVERIFIED"


def test_enginerun_no_block_no_receipt(tmp_path):
    from discovery_fabric.engine.run import EngineRun
    from discovery_fabric.engine.adapters import STAGE_ORDER
    out = tmp_path / "runs" / "engrun_pp0_plain01"
    run = EngineRun(problem=dict(PARENT_PROBLEM,
                                 problem_id="pp0_plain01"),
                    out_dir=str(out), run_id="engrun_pp0_plain01",
                    disabled_stages=list(STAGE_ORDER))
    run.run()
    assert not (out / "CONSUMPTION.json").exists()
    assert not (out / "CONSUMPTION_ERROR.json").exists()


def test_enginerun_rehearsal_never_receipts(tmp_path):
    from discovery_fabric.engine.run import EngineRun
    from discovery_fabric.engine.adapters import STAGE_ORDER
    out = tmp_path / "runs" / "engrun_pp0_rehearsal01"
    run = EngineRun(problem=_reality_problem("EV-RC-RH", "KX"),
                    out_dir=str(out), run_id="engrun_pp0_rehearsal01",
                    disabled_stages=list(STAGE_ORDER))
    run.rehearsal = True
    run.run()
    assert not (out / "CONSUMPTION.json").exists()


# tampered / absent artifact at consumption ------------------------------
def test_consumption_tampered_artifact_rejected(tmp_path):
    runs = tmp_path / "runs"
    child = runs / "engrun_pp0_tamper01"
    child.mkdir(parents=True, exist_ok=True)
    problem = _reality_problem("EV-CB-T", "KX")
    (child / "problem.json").write_text(json.dumps(problem),
                                        encoding="utf-8")
    (child / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_pp0_tamper01"}), encoding="utf-8")
    out = ri.record_child_consumption(
        str(child), "EV-CB-T", PARENT_RUN, "KX", "kh" * 32, "ph" * 32,
        knowledge_artifact={"different": "bytes"})
    assert out["consumed"] is False
    assert out["artifact_verification"] == "TAMPERED"
    assert not (child / "CONSUMPTION.json").exists()


def test_consumption_absent_artifact_unresolved(tmp_path):
    runs = tmp_path / "runs"
    child = runs / "engrun_pp0_absent01"
    child.mkdir(parents=True, exist_ok=True)
    problem = _reality_problem("EV-CB-A", "KX")
    (child / "problem.json").write_text(json.dumps(problem),
                                        encoding="utf-8")
    (child / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_pp0_absent01"}), encoding="utf-8")
    out = ri.record_child_consumption(
        str(child), "EV-CB-A", PARENT_RUN, "KX", "kh" * 32, "ph" * 32,
        knowledge_artifact=None)
    assert out["consumed"] is True
    assert out["receipt"]["artifact_verification"] == \
        "CARRIED_NOT_REVERIFIED"


def test_consumption_lineage_mismatch_rejected(tmp_path):
    runs = tmp_path / "runs"
    child = runs / "engrun_pp0_foreign01"
    child.mkdir(parents=True, exist_ok=True)
    problem = _reality_problem("EV-OTHER", "KX-OTHER")
    (child / "problem.json").write_text(json.dumps(problem),
                                        encoding="utf-8")
    (child / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_pp0_foreign01"}), encoding="utf-8")
    out = ri.record_child_consumption(
        str(child), "EV-CB-F", PARENT_RUN, "KX", "kh" * 32, "ph" * 32)
    assert out["consumed"] is False
    assert "lineage" in out["reason"]
    assert not (child / "CONSUMPTION.json").exists()


# full §15 chain on the real launcher (disabled stages, offline) --------
def _craft_child(tmp_path, name, problem, manifest_extra=None,
                 receipt=None):
    child = tmp_path / "runs" / name
    child.mkdir(parents=True, exist_ok=True)
    (child / "problem.json").write_text(json.dumps(problem),
                                        encoding="utf-8")
    manifest = {"run_id": name}
    manifest.update(manifest_extra or {})
    (child / "run_manifest.json").write_text(json.dumps(manifest),
                                             encoding="utf-8")
    if receipt is not None:
        (child / "CONSUMPTION.json").write_text(
            json.dumps(receipt), encoding="utf-8")
    return child


def _kb_problem(eid, kid, artifact_sha):
    problem = dict(PARENT_PROBLEM)
    problem["constraint"] = "base [REALITY %s: KILL knowledge %s " \
        "constrains this search]" % (eid, kid)
    problem["reality_constraints"] = {
        "trigger_event_id": eid, "knowledge_record_id": kid,
        "knowledge_artifact_sha256": artifact_sha,
        "parent_run_id": PARENT_RUN,
        "parent_problem_sha256": "ph" * 32,
        "branch": "KILL", "constraint_clause": "c"}
    problem["problem_id"] = "pp0_kb_" + eid.lower()
    return problem


def _kb_manifest(eid, kid, artifact_sha, run_id):
    return {"run_id": run_id,
            "knowledge_consumed": {
                "trigger_event_id": eid,
                "knowledge_record_id": kid,
                "knowledge_artifact_sha256": artifact_sha,
                "parent_run_id": PARENT_RUN,
                "parent_problem_sha256": "ph" * 32,
                "branch": "KILL"}}


def _kb_expected(eid, kid, artifact_sha):
    return {"trigger_event_id": eid, "parent_run_id": PARENT_RUN,
            "knowledge_record_id": kid, "launch_id": "lid-" + eid}


_ART = {"mechanism": "linear regulator holds bus voltage",
        "entry_id": "KA-TEST-001"}


def _resolver_for(artifact_by_kid):
    def _resolve(kid):
        return artifact_by_kid.get(kid)
    return _resolve


# §5 forgery battery: receipt never upgrades ------------------------------
def test_forged_receipt_without_binding_fails(tmp_path):
    problem = dict(PARENT_PROBLEM, problem_id="pp0_forge01")
    child = _craft_child(tmp_path, "engrun_forge01", problem,
                         {"run_id": "engrun_forge01"},
                         receipt={"consumed": True,
                                  "knowledge_record_id": "KX",
                                  "artifact_verification": "RESOLVED"})
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-F", "KX", "kh" * 32),
        _resolver_for({"KX": dict(_ART)}))
    assert out["verified"] is False
    assert "manifest does not bind" in out["reason"]


def test_hash_mismatch_fails(tmp_path):
    problem = _kb_problem("EV-HM-1", "KX", "kh" * 32)
    child = _craft_child(tmp_path, "engrun_hm01", problem,
                         dict(_kb_manifest("EV-HM-1", "KX", "kh" * 32,
                                           "engrun_hm01"),
                              run_id="engrun_hm01"))
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-HM-1", "KX", "kh" * 32),
        _resolver_for({"KX": {"mechanism": "something else entirely"}}))
    assert out["verified"] is False
    assert out["checks"]["artifact"] == "TAMPERED"


def test_different_artifact_same_id_fails(tmp_path):
    problem = _kb_problem("EV-DA-1", "KX", "kh" * 32)
    child = _craft_child(tmp_path, "engrun_da01", problem,
                         dict(_kb_manifest("EV-DA-1", "KX", "kh" * 32,
                                           "engrun_da01"),
                              run_id="engrun_da01"))
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-DA-1", "KX", "kh" * 32),
        _resolver_for({"KX": {"mechanism": "unrelated other device"}}))
    assert out["verified"] is False


def test_problem_without_manifest_binding_fails(tmp_path):
    problem = _kb_problem("EV-PM-1", "KX", "kh" * 32)
    child = _craft_child(tmp_path, "engrun_pm01", problem,
                         {"run_id": "engrun_pm01"})
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-PM-1", "KX", "kh" * 32),
        _resolver_for({"KX": dict(_ART)}))
    assert out["verified"] is False
    assert "manifest does not bind" in out["reason"]


def test_absent_knowledge_unresolved(tmp_path):
    problem = _kb_problem("EV-AB2-1", "KX", "kh" * 32)
    child = _craft_child(tmp_path, "engrun_ab201", problem,
                         dict(_kb_manifest("EV-AB2-1", "KX", "kh" * 32,
                                           "engrun_ab201"),
                              run_id="engrun_ab201"))
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-AB2-1", "KX", "kh" * 32),
        _resolver_for({}))
    assert out["verified"] is False
    assert out["checks"]["artifact"] == "UNRESOLVED_ABSENT"


def test_unused_knowledge_fails(tmp_path):
    problem = dict(PARENT_PROBLEM, problem_id="pp0_plain02")
    child = _craft_child(tmp_path, "engrun_plain02", problem,
                         {"run_id": "engrun_plain02"})
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-UN-1", "KX", "kh" * 32),
        _resolver_for({"KX": dict(_ART)}))
    assert out["verified"] is False


def test_rehearsal_refused_by_verifier(tmp_path):
    problem = _kb_problem("EV-RH-V", "KX", "kh" * 32)
    child = _craft_child(tmp_path, "engrun_rhv01", problem,
                         dict(_kb_manifest("EV-RH-V", "KX", "kh" * 32,
                                           "engrun_rhv01"),
                              run_id="engrun_rhv01"))
    exp = _kb_expected("EV-RH-V", "KX", "kh" * 32)
    exp["rehearsal"] = True
    out = ri.verify_consumption(str(child), exp,
                                _resolver_for({"KX": dict(_ART)}))
    assert out["verified"] is False
    assert "REHEARSAL" in out["reason"]


def test_verifier_replay_stable(tmp_path):
    import hashlib as _hl
    art = dict(_ART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    problem = _kb_problem("EV-RP-1", "KX", art_sha)
    child = _craft_child(tmp_path, "engrun_rp01", problem,
                         dict(_kb_manifest("EV-RP-1", "KX", art_sha,
                                           "engrun_rp01"),
                              run_id="engrun_rp01"))
    exp = _kb_expected("EV-RP-1", "KX", art_sha)
    r1 = ri.verify_consumption(str(child), exp,
                               _resolver_for({"KX": art}))
    r2 = ri.verify_consumption(str(child), exp,
                               _resolver_for({"KX": art}))
    assert r1["verified"] is True and r2["verified"] is True
    assert r1["contract"] == r2["contract"]


def test_duplicate_receipt_no_upgrade(tmp_path):
    import hashlib as _hl
    art = dict(_ART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    problem = _kb_problem("EV-DP-1", "KX", art_sha)
    foreign = dict(PARENT_PROBLEM, problem_id="pp0_foreign")
    child = _craft_child(tmp_path, "engrun_dp01", foreign,
                         {"run_id": "engrun_dp01"},
                         receipt={"consumed": True,
                                  "knowledge_record_id": "KX",
                                  "artifact_verification": "RESOLVED"})
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-DP-1", "KX", art_sha),
        _resolver_for({"KX": art}))
    assert out["verified"] is False


def test_precreated_receipt_ignored_when_supported(tmp_path):
    import hashlib as _hl
    art = dict(_ART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True,
        separators=(",", ":")).encode()).hexdigest()
    problem = _kb_problem("EV-PR-1", "KX", art_sha)
    child = _craft_child(tmp_path, "engrun_pr01", problem,
                         dict(_kb_manifest("EV-PR-1", "KX", art_sha,
                                           "engrun_pr01"),
                              run_id="engrun_pr01"),
                         receipt={"consumed": False,
                                  "reason": "planted lie"})
    out = ri.verify_consumption(
        str(child), _kb_expected("EV-PR-1", "KX", art_sha),
        _resolver_for({"KX": art}))
    assert out["verified"] is True


# SEARCH_STATE + delta (§6/§7) ----------------------------------------------
def test_search_state_stable_hash(tmp_path):
    runs = tmp_path / "runs"
    child = runs / "engrun_ss01"
    child.mkdir(parents=True, exist_ok=True)
    (child / "problem.json").write_text(
        json.dumps(_kb_problem("EV-SS-1", "KX", "kh" * 32)),
        encoding="utf-8")
    (child / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_ss01"}), encoding="utf-8")
    s1 = ri.extract_search_state(str(child))
    s2 = ri.extract_search_state(str(child))
    assert s1["canonical_state_hash"] == s2["canonical_state_hash"]
    assert s1["knowledge_binding"]["trigger_event_id"] == "EV-SS-1"
    assert s1["operator_regions"]["state"] == \
        "UNKNOWN_NO_MECHANISM_SPACE"


def test_delta_falsifier_problem_only(tmp_path):
    runs = tmp_path / "runs"
    for name, pid in (("engrun_dfa", "pp0_a"), ("engrun_dfb", "pp0_b")):
        d = runs / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "problem.json").write_text(
            json.dumps(dict(PARENT_PROBLEM, problem_id=pid)),
            encoding="utf-8")
        (d / "run_manifest.json").write_text(
            json.dumps({"run_id": name}), encoding="utf-8")
    s0 = ri.extract_search_state(str(runs / "engrun_dfa"))
    s1 = ri.extract_search_state(str(runs / "engrun_dfb"))
    assert s0["problem_sha256"] != s1["problem_sha256"]
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False
    assert delta["all_fields"]["problem_only"] is True


def test_negative_control_no_delta(tmp_path):
    runs = tmp_path / "runs"
    for name in ("engrun_nc1", "engrun_nc2"):
        d = runs / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "problem.json").write_text(
            json.dumps(dict(PARENT_PROBLEM,
                            problem_id="pp0_nc_" + name[-1])),
            encoding="utf-8")
        (d / "run_manifest.json").write_text(
            json.dumps({"run_id": name}), encoding="utf-8")
    s0 = ri.extract_search_state(str(runs / "engrun_nc1"))
    s1 = ri.extract_search_state(str(runs / "engrun_nc2"))
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False
    out = ri.verify_consumption(
        str(runs / "engrun_nc2"),
        _kb_expected("EV-NC-1", "KX", "kh" * 32),
        _resolver_for({"KX": dict(_ART)}))
    assert out["verified"] is False


def _vrun_dir(tmp_path, name, problem, manifest_extra=None,
              receipt=None):
    d = tmp_path / "runs" / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "problem.json").write_text(json.dumps(problem),
                                    encoding="utf-8")
    manifest = {"run_id": name}
    manifest.update(manifest_extra or {})
    (d / "run_manifest.json").write_text(json.dumps(manifest),
                                         encoding="utf-8")
    if receipt is not None:
        (d / "CONSUMPTION.json").write_text(json.dumps(receipt),
                                            encoding="utf-8")
    return d


def _vexp(eid, kid, art_sha, run_id=None, branch="KILL"):
    return {"trigger_event_id": eid, "parent_run_id": PARENT_RUN,
            "knowledge_record_id": kid, "launch_id": "lid-" + eid,
            "knowledge_artifact_sha256": art_sha,
            "child_run_id": run_id, "parent_problem_sha256": "ph" * 32,
            "branch": branch}


_VART = {"mechanism": "linear regulator holds bus voltage",
         "entry_id": "KA-TEST-001"}


def _vresolver(mapping):
    def _resolve(kid):
        return mapping.get(kid)
    return _resolve


def _vprob(eid, kid, art_sha):
    problem = dict(PARENT_PROBLEM)
    problem["constraint"] = "base [REALITY %s: KILL knowledge %s " \
        "constrains this search]" % (eid, kid)
    problem["reality_constraints"] = {
        "trigger_event_id": eid, "knowledge_record_id": kid,
        "knowledge_artifact_sha256": art_sha,
        "parent_run_id": PARENT_RUN,
        "parent_problem_sha256": "ph" * 32,
        "branch": "KILL", "constraint_clause": "c"}
    problem["problem_id"] = "pp0_kbv_" + eid.lower()
    return problem


def _vman(eid, kid, art_sha, run_id):
    return {"run_id": run_id,
            "knowledge_consumed": {
                "trigger_event_id": eid,
                "knowledge_record_id": kid,
                "knowledge_artifact_sha256": art_sha,
                "parent_run_id": PARENT_RUN,
                "parent_problem_sha256": "ph" * 32,
                "branch": "KILL"}}


def test_forged_receipt_without_binding_fails(tmp_path):
    problem = dict(PARENT_PROBLEM, problem_id="pp0_forge02")
    child = _vrun_dir(tmp_path, "engrun_forge02", problem,
                      {"run_id": "engrun_forge02"},
                      receipt={"consumed": True,
                               "knowledge_record_id": "KX",
                               "artifact_verification": "RESOLVED"})
    out = ri.verify_consumption(
        str(child), _vexp("EV-VF-1", "KX", "kh" * 32, run_id="engrun_forge02"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False
    assert "manifest does not bind" in out["reason"]


def test_hash_mismatch_fails(tmp_path):
    problem = _vprob("EV-VH-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_vh01", problem,
                      dict(_vman("EV-VH-1", "KX", "kh" * 32,
                                 "engrun_vh01"),
                           run_id="engrun_vh01"))
    out = ri.verify_consumption(
        str(child), _vexp("EV-VH-1", "KX", "kh" * 32, run_id="engrun_vh01"),
        _vresolver({"KX": {"mechanism": "something else entirely"}}))
    assert out["verified"] is False
    assert out["checks"]["artifact"] == "TAMPERED"


def test_different_artifact_same_id_fails(tmp_path):
    problem = _vprob("EV-VD-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_vd01", problem,
                      dict(_vman("EV-VD-1", "KX", "kh" * 32,
                                 "engrun_vd01"),
                           run_id="engrun_vd01"))
    out = ri.verify_consumption(
        str(child), _vexp("EV-VD-1", "KX", "kh" * 32, run_id="engrun_vd01"),
        _vresolver({"KX": {"mechanism": "unrelated other device"}}))
    assert out["verified"] is False


def test_problem_without_manifest_binding_fails(tmp_path):
    problem = _vprob("EV-VP-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_vp01", problem,
                      {"run_id": "engrun_vp01"})
    out = ri.verify_consumption(
        str(child), _vexp("EV-VP-1", "KX", "kh" * 32, run_id="engrun_vp01"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False
    assert "manifest does not bind" in out["reason"]


def test_absent_knowledge_unresolved(tmp_path):
    problem = _vprob("EV-VA-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_va01", problem,
                      dict(_vman("EV-VA-1", "KX", "kh" * 32,
                                 "engrun_va01"),
                           run_id="engrun_va01"))
    out = ri.verify_consumption(
        str(child), _vexp("EV-VA-1", "KX", "kh" * 32, run_id="engrun_va01"),
        _vresolver({}))
    assert out["verified"] is False
    assert out["checks"]["artifact"] == "UNRESOLVED_ABSENT"


def test_unused_knowledge_fails(tmp_path):
    problem = dict(PARENT_PROBLEM, problem_id="pp0_plain03")
    child = _vrun_dir(tmp_path, "engrun_plain03", problem,
                      {"run_id": "engrun_plain03"})
    out = ri.verify_consumption(
        str(child), _vexp("EV-VU-1", "KX", "kh" * 32, run_id="engrun_plain03"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False


def test_rehearsal_refused_by_verifier(tmp_path):
    problem = _vprob("EV-VR-1", "KX", "kh" * 32)
    child = _vrun_dir(tmp_path, "engrun_vr01", problem,
                      dict(_vman("EV-VR-1", "KX", "kh" * 32,
                                 "engrun_vr01"),
                           run_id="engrun_vr01"))
    exp = _vexp("EV-VR-1", "KX", "kh" * 32, run_id="engrun_vr01")
    exp["rehearsal"] = True
    out = ri.verify_consumption(str(child), exp,
                                _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False
    assert "REHEARSAL" in out["reason"]


def test_verifier_replay_stable(tmp_path):
    import hashlib as _hl
    art = dict(_VART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    problem = _vprob("EV-VS-1", "KX", art_sha)
    child = _vrun_dir(tmp_path, "engrun_vs01", problem,
                      dict(_vman("EV-VS-1", "KX", art_sha, "engrun_vs01"),
                           run_id="engrun_vs01"))
    exp = _vexp("EV-VS-1", "KX", art_sha, run_id="engrun_vs01")
    r1 = ri.verify_consumption(str(child), exp,
                               _vresolver({"KX": art}))
    r2 = ri.verify_consumption(str(child), exp,
                               _vresolver({"KX": art}))
    assert r1["verified"] is True and r2["verified"] is True
    assert r1["contract"] == r2["contract"]


def test_duplicate_receipt_no_upgrade(tmp_path):
    import hashlib as _hl
    art = dict(_VART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    foreign = dict(PARENT_PROBLEM, problem_id="pp0_foreign")
    child = _vrun_dir(tmp_path, "engrun_vdup01", foreign,
                      {"run_id": "engrun_vdup01"},
                      receipt={"consumed": True,
                               "knowledge_record_id": "KX",
                               "artifact_verification": "RESOLVED"})
    out = ri.verify_consumption(
        str(child), _vexp("EV-VDUP-1", "KX", art_sha, run_id="engrun_vdup01"),
        _vresolver({"KX": art}))
    assert out["verified"] is False


def test_precreated_receipt_ignored_when_supported(tmp_path):
    import hashlib as _hl
    art = dict(_VART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    problem = _vprob("EV-VPC-1", "KX", art_sha)
    child = _vrun_dir(tmp_path, "engrun_vpc01", problem,
                      dict(_vman("EV-VPC-1", "KX", art_sha, "engrun_vpc01"),
                           run_id="engrun_vpc01"),
                      receipt={"consumed": False,
                               "reason": "planted lie"})
    out = ri.verify_consumption(
        str(child), _vexp("EV-VPC-1", "KX", art_sha, run_id="engrun_vpc01"),
        _vresolver({"KX": art}))
    assert out["verified"] is True


def test_search_state_stable_hash(tmp_path):
    runs = tmp_path / "runs"
    child = runs / "engrun_vss01"
    child.mkdir(parents=True, exist_ok=True)
    (child / "problem.json").write_text(
        json.dumps(_vprob("EV-VSS-1", "KX", "kh" * 32)),
        encoding="utf-8")
    (child / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_vss01"}), encoding="utf-8")
    s1 = ri.extract_search_state(str(child))
    s2 = ri.extract_search_state(str(child))
    assert s1["canonical_state_hash"] == s2["canonical_state_hash"]
    assert s1["knowledge_binding"]["trigger_event_id"] == "EV-VSS-1"
    assert s1["operator_regions"]["state"] == \
        "UNKNOWN_NO_MECHANISM_SPACE"


def test_delta_falsifier_problem_only(tmp_path):
    runs = tmp_path / "runs"
    for name, pid in (("engrun_vdfa", "pp0_a"), ("engrun_vdfb", "pp0_b")):
        d = runs / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "problem.json").write_text(
            json.dumps(dict(PARENT_PROBLEM, problem_id=pid)),
            encoding="utf-8")
        (d / "run_manifest.json").write_text(
            json.dumps({"run_id": name}), encoding="utf-8")
    s0 = ri.extract_search_state(str(runs / "engrun_vdfa"))
    s1 = ri.extract_search_state(str(runs / "engrun_vdfb"))
    assert s0["problem_sha256"] != s1["problem_sha256"]
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False
    assert delta["all_fields"]["problem_only"] is True


def test_delta_substantive_kill_path(tmp_path):
    import hashlib as _hl
    art = dict(_VART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    runs = tmp_path / "runs"
    plain = runs / "engrun_vdneg"
    plain.mkdir(parents=True, exist_ok=True)
    (plain / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_neg")),
        encoding="utf-8")
    (plain / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_vdneg"}), encoding="utf-8")
    kbdir = runs / "engrun_vdpos"
    kbdir.mkdir(parents=True, exist_ok=True)
    (kbdir / "problem.json").write_text(
        json.dumps(_vprob("EV-VD-2", "KX", art_sha)), encoding="utf-8")
    (kbdir / "run_manifest.json").write_text(
        json.dumps(dict(_vman("EV-VD-2", "KX", art_sha, "engrun_vdpos"),
                        run_id="engrun_vdpos")), encoding="utf-8")
    s0 = ri.extract_search_state(str(plain), cemetery_path=None)
    s1 = ri.extract_search_state(str(kbdir), cemetery_path=None)
    s0["cemetery"] = {"state": "READ", "entry_count": 0,
                      "head_sha256": "EMPTY"}
    s1["cemetery"] = {"state": "READ", "entry_count": 1,
                      "head_sha256": "h1"}
    v0 = ri.verify_consumption(
        str(plain), _vexp("EV-VD-2", "KX", art_sha, run_id="engrun_vdneg"),
        _vresolver({"KX": art}))
    v1 = ri.verify_consumption(
        str(kbdir), _vexp("EV-VD-2", "KX", art_sha, run_id="engrun_vdpos"),
        _vresolver({"KX": art}))
    assert v0["verified"] is False
    assert v1["verified"] is True
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False, delta
    assert "knowledge_bound" in delta["changed_fields"]
    assert "cemetery_flip_informational_only" in delta["changed_fields"]
    assert "constraint_applied" not in delta["changed_fields"]
    assert "record_linked" not in delta["changed_fields"]
    adj = ri.adjudicate_search_learning(delta, None)
    assert adj["verdict"] == "NO_LEARNING", adj


def test_negative_control_no_delta(tmp_path):
    runs = tmp_path / "runs"
    for name in ("engrun_vnc1", "engrun_vnc2"):
        d = runs / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "problem.json").write_text(
            json.dumps(dict(PARENT_PROBLEM,
                            problem_id="pp0_nc_" + name[-1])),
            encoding="utf-8")
        (d / "run_manifest.json").write_text(
            json.dumps({"run_id": name}), encoding="utf-8")
    s0 = ri.extract_search_state(str(runs / "engrun_vnc1"))
    s1 = ri.extract_search_state(str(runs / "engrun_vnc2"))
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False
    out = ri.verify_consumption(
        str(runs / "engrun_vnc2"),
        _vexp("EV-VNC-1", "KX", "kh" * 32, run_id="engrun_vnc2"),
        _vresolver({"KX": dict(_VART)}))
    assert out["verified"] is False


def test_e2e_verified_consumption_measured_delta(tmp_path):
    import os as _os
    if _os.name == "nt":
        pytest = __import__("pytest")
        pytest.skip("production child_run_id values contain colons "
                    "(canonical engrun:...:... lineage format); Windows "
                    "filesystems reject them. Production runs Linux.")
    from discovery_fabric.engine.adapters import STAGE_ORDER
    dis = list(STAGE_ORDER)
    cem_file = _kill_cemetery(tmp_path)

    def _resolver(kid):
        data = json.loads(Path(cem_file).read_text())
        for e in data.get("entries", []):
            if e.get("entry_id") == kid:
                return e
        return None

    def _real(req):
        return ri.default_run_launcher(
            req, str(tmp_path / "runs"), disabled_stages=dis,
            knowledge_resolver=_resolver)

    with _cemetery(tmp_path):
        rec = _exec(_event("EV-E2E-2", verdict="KILL"),
                    str(tmp_path / "ledger"), run_launcher=_real,
                    parent_problem=dict(PARENT_PROBLEM),
                    parent_run_id=PARENT_RUN,
                    cemetery_path=cem_file)
    assert rec["executed"] is True
    assert rec["child"]["request_status"] == "LAUNCHED"
    kid = rec["branch_record"]["cemetery_entry_id"]
    child_id = rec["child"]["child_run_id"]
    child_dir = tmp_path / "runs" / child_id
    _creq = rec["branch_record"]["child_request"]
    exp = {"trigger_event_id": "EV-E2E-2", "parent_run_id": PARENT_RUN,
           "knowledge_record_id": kid, "launch_id": "lid-x",
           "knowledge_artifact_sha256": _creq["knowledge_artifact_sha256"],
           "child_run_id": child_id,
           "parent_problem_sha256": _creq["parent_problem_sha256"],
           "branch": "KILL", "cemetery_entry_id": kid}
    verified = ri.verify_consumption(str(child_dir), exp, _resolver)
    assert verified["verified"] is True, verified["reason"]
    assert verified["contract"]["knowledge_record_id"] == kid
    parent_dir = tmp_path / "runs" / "engrun_parent_e2e"
    parent_dir.mkdir(parents=True, exist_ok=True)
    (parent_dir / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_e2e_parent")),
        encoding="utf-8")
    (parent_dir / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_parent_e2e",
                    "disabled_stages": sorted(dis),
                    "stage_order": []}), encoding="utf-8")
    s0 = ri.extract_search_state(str(parent_dir),
                                 cemetery_path=cem_file)
    s1 = ri.extract_search_state(str(child_dir),
                                 cemetery_path=cem_file)
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False, delta
    assert "knowledge_bound" in delta["changed_fields"]
    assert "constraint_applied" not in delta["changed_fields"]
    search = ri.verify_search_consumption(
        str(child_dir), dict(exp, cemetery_entry_id=kid), _resolver)
    assert search["state"] == "SEARCH_CONSUMPTION_UNPROVEN", search
    assert search["knowledge_state"] == "KNOWLEDGE_BOUND", search
    adj = ri.adjudicate_search_learning(
        delta, {"state": search["state"],
                "record_hash": search.get("record_hash")})
    assert adj["verdict"] == "NO_LEARNING", adj
    impact = json.loads((tmp_path / "ledger" / "search_impact" /
                         "EV-E2E-2.json").read_text())
    assert impact["behavioral_change_observed"] == \
        "CHILD_CONSUMED_VERIFIED", impact["behavioral_change_observed"]
    assert impact["child_consumed_delta"]["artifact_verification"] == \
        "RESOLVED"
    assert impact["operator_region_after"] is not None
    with _cemetery(tmp_path):
        out = ri.reconcile_unknown_launch(
            str(tmp_path / "ledger"), "EV-E2E-2", _real,
            ri.default_execution_checker(str(tmp_path / "runs")))
    assert out["state"] == "LAUNCHED"


_KENTRY = {
    "entry_id": "CE-TEST-K1",
    "territory_id": "CV-TEST",
    "mechanism_name": "cryogenic microvalve stiction lock",
    "proposed_version": "V1",
    "killed_at_version": "V2",
    "kill_reason": "PHYSICS_CEILING",
    "what_was_proposed": "tungsten carbide microvalve for cryogenic soak",
    "why_it_failed": "cryogenic soak raises microvalve stiction torque "
                     "beyond the tungsten carbide actuation budget",
    "reusable_lesson": "cryogenic soak raises microvalve stiction torque "
                       "beyond tungsten carbide actuation limits",
    "what_to_avoid": "tungsten carbide microvalve under cryogenic soak",
    "physical_constraint": "tungsten carbide microvalve stiction torque "
                           "exceeds actuation budget under cryogenic soak",
    "evidence_sources": [],
    "epistemic_class": "PROVEN_INVARIANT",
}

_CAND_TEXT = ("tungsten carbide microvalve with cryogenic soak stiction "
              "torque compensation")


def _sc_candidates():
    return [{"candidate_id": "cand-001", "candidate_state": "CANDIDATE",
             "intervention": _CAND_TEXT, "mechanism": _CAND_TEXT,
             "predicted_effect": _CAND_TEXT,
             "novel_design_variable": _CAND_TEXT}]


def _sc_space(cemetery_record, candidates, full=None):
    space = {"mechanism_space_version": "mechanism_space/1.0.0",
            "state": "BUILT",
            "problem_id": "pp0_sc",
            "operator_ids": ["DIRECT_TRANSFER"],
            "operator_results": [
                {"operator": "DIRECT_TRANSFER",
                 "operator_version": "v1",
                 "transformation_rule": "transfer",
                 "search_constraint": "direct",
                 "n_items_examined": 1,
                 "n_items_selected": 1,
                 "selected_item_ids": ["lean_1"],
                 "state": "OPERATED",
                 "operator_selection": {
                     "selected_operator": "DIRECT_TRANSFER",
                     "contracts_evaluated": [
                         {"satisfied": True}],
                     "selection_basis": "test"}}],
            "cemetery_consumption": cemetery_record,
            "candidates": candidates}
    if full is not None:
        space["operator_candidates_full"] = full
    return space


def _sc_dir(tmp_path, name, eid, art_sha, run_id, space):
    import copy as _copy
    problem = _vprob(eid, "KX", art_sha)
    d = _vrun_dir(tmp_path, name, problem,
                  dict(_vman(eid, "KX", art_sha, run_id),
                       run_id=run_id))
    if space is not None:
        ri.record_search_consumption(str(d), dict(problem[
            "reality_constraints"]), _copy.deepcopy(space))
    return d


def _sc_exp(eid, art_sha, run_id, entry_id=None):
    exp = _vexp(eid, "KX", art_sha, run_id=run_id)
    if entry_id is not None:
        exp = dict(exp, cemetery_entry_id=entry_id)
    return exp


def _sc_art():
    import hashlib as _hl
    art = dict(_VART)
    art_sha = _hl.sha256(json.dumps(
        art, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return art, art_sha


def test_forged_search_consumption_rejected(tmp_path):
    art, art_sha = _sc_art()
    from discovery_fabric.engine import mechanism_space as _ms
    with _cemetery(tmp_path):
        Path(tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": []}), encoding="utf-8")
        rec = _ms._consult_cemetery(_sc_candidates())
    d = _sc_dir(tmp_path, "engrun_sf01", "EV-SF-1", art_sha,
                "engrun_sf01", _sc_space(rec, _sc_candidates()))
    p = d / "SEARCH_CONSUMPTION.json"
    forged = json.loads(p.read_text(encoding="utf-8"))
    forged["search_snapshot"]["cemetery_consultation"]["n_blocked"] = 99
    p.write_text(json.dumps(forged), encoding="utf-8")
    out = ri.verify_search_consumption(
        str(d), _sc_exp("EV-SF-1", art_sha, "engrun_sf01",
                        entry_id="CE-TEST-K1"),
        _vresolver({"KX": art}))
    assert out["state"] == "SEARCH_CONSUMPTION_REJECTED", out
    assert out["knowledge_state"] == "KNOWLEDGE_BOUND", out


def test_bound_without_search_consumption_unproven(tmp_path):
    art, art_sha = _sc_art()
    problem = _vprob("EV-SU-1", "KX", art_sha)
    d = _vrun_dir(tmp_path, "engrun_su01", problem,
                  dict(_vman("EV-SU-1", "KX", art_sha, "engrun_su01"),
                       run_id="engrun_su01"))
    out = ri.verify_search_consumption(
        str(d), _sc_exp("EV-SU-1", art_sha, "engrun_su01",
                        entry_id="CE-TEST-K1"),
        _vresolver({"KX": art}))
    assert out["state"] == "SEARCH_CONSUMPTION_UNPROVEN", out
    assert out["knowledge_state"] == "KNOWLEDGE_BOUND", out
    kb = ri.verify_consumption(
        str(d), _sc_exp("EV-SU-1", art_sha, "engrun_su01"),
        _vresolver({"KX": art}))
    assert kb["verified"] is True


def test_mentioned_unused_search_rejected(tmp_path):
    problem = dict(PARENT_PROBLEM, problem_id="pp0_smu")
    problem["constraint"] = "base mentioning KX knowledge in free text"
    d = _vrun_dir(tmp_path, "engrun_smu01", problem,
                  {"run_id": "engrun_smu01"})
    out = ri.verify_search_consumption(
        str(d), _sc_exp("EV-SM-1", "kh" * 32, "engrun_smu01"),
        _vresolver({"KX": dict(_VART)}))
    assert out["state"] == "SEARCH_CONSUMPTION_REJECTED", out
    assert out["knowledge_state"] == "KNOWLEDGE_UNBOUND", out


def test_control_treatment_no_search_difference_nonsubstantive(tmp_path):
    art, art_sha = _sc_art()
    from discovery_fabric.engine import mechanism_space as _ms
    with _cemetery(tmp_path):
        Path(tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": []}), encoding="utf-8")
        rec0 = _ms._consult_cemetery(_sc_candidates())
        rec1 = _ms._consult_cemetery(_sc_candidates())
    assert rec0["n_blocked"] == 0 and rec1["n_blocked"] == 0
    runs = tmp_path / "runs"
    plain = runs / "engrun_snc0"
    plain.mkdir(parents=True, exist_ok=True)
    (plain / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_snc0")),
        encoding="utf-8")
    (plain / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_snc0"}), encoding="utf-8")
    treat = _sc_dir(tmp_path, "engrun_snc1", "EV-SN-1", art_sha,
                    "engrun_snc1", _sc_space(rec1, _sc_candidates()))
    s0 = ri.extract_search_state(str(plain))
    s1 = ri.extract_search_state(str(treat))
    s1["knowledge_binding"]["cemetery_entry_id"] = "CE-TEST-K1"
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is False, delta
    assert "kill_decision_bound" not in delta["changed_fields"]
    assert delta.get("decision_evidence") is None
    adj = ri.adjudicate_search_learning(delta, None)
    assert adj["verdict"] == "NO_LEARNING", adj


def test_treatment_verified_search_change_substantive(tmp_path):
    art, art_sha = _sc_art()
    from discovery_fabric.engine import mechanism_space as _ms
    with _cemetery(tmp_path):
        Path(tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": []}), encoding="utf-8")
        rec0 = _ms._consult_cemetery(_sc_candidates())
        assert rec0["n_blocked"] == 0
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": [dict(_KENTRY)]}), encoding="utf-8")
        cands = _sc_candidates()
        rec1 = _ms._consult_cemetery(cands)
        assert rec1["n_blocked"] == 1, rec1
        assert rec1["blocked"][0]["entries"] == ["CE-TEST-K1"], rec1
    runs = tmp_path / "runs"
    plain = runs / "engrun_svs0"
    plain.mkdir(parents=True, exist_ok=True)
    (plain / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_svs0")),
        encoding="utf-8")
    (plain / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_svs0"}), encoding="utf-8")
    treat = _sc_dir(tmp_path, "engrun_svs1", "EV-SS-1", art_sha,
                    "engrun_svs1", _sc_space(rec1, cands))
    exp = _sc_exp("EV-SS-1", art_sha, "engrun_svs1",
                  entry_id="CE-TEST-K1")
    out = ri.verify_search_consumption(str(treat), exp,
                                       _vresolver({"KX": art}))
    assert out["state"] == "SEARCH_CONSUMPTION_VERIFIED", out
    assert out["knowledge_state"] == "KNOWLEDGE_BOUND", out
    s0 = ri.extract_search_state(str(plain))
    s1 = ri.extract_search_state(str(treat))
    s1["knowledge_binding"]["cemetery_entry_id"] = "CE-TEST-K1"
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is True, delta
    assert "kill_decision_bound" in delta["changed_fields"]
    assert "constraint_applied" in delta["changed_fields"]
    ev = delta.get("decision_evidence") or {}
    assert ev.get("decision_type") == "CEMETERY_KILL", ev
    assert ev.get("decision_ref") == "CE-TEST-K1", ev
    assert ev.get("record_hash") == out.get("record_hash"), ev
    adj = ri.adjudicate_search_learning(
        delta, {"state": out["state"],
                "record_hash": out.get("record_hash")})
    assert adj["verdict"] == "LEARNING_CANDIDATE", adj


def test_search_verify_replay_no_second_effect(tmp_path):
    art, art_sha = _sc_art()
    from discovery_fabric.engine import mechanism_space as _ms
    with _cemetery(tmp_path):
        Path(tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": [dict(_KENTRY)]}), encoding="utf-8")
        cands = _sc_candidates()
        rec1 = _ms._consult_cemetery(cands)
    treat = _sc_dir(tmp_path, "engrun_srp1", "EV-SR-1", art_sha,
                    "engrun_srp1", _sc_space(rec1, cands))
    exp = _sc_exp("EV-SR-1", art_sha, "engrun_srp1",
                  entry_id="CE-TEST-K1")
    p = treat / "SEARCH_CONSUMPTION.json"
    import hashlib as _hl
    before = _hl.sha256(p.read_bytes()).hexdigest()
    r1 = ri.verify_search_consumption(str(treat), exp,
                                      _vresolver({"KX": art}))
    r2 = ri.verify_search_consumption(str(treat), exp,
                                      _vresolver({"KX": art}))
    after = _hl.sha256(p.read_bytes()).hexdigest()
    assert r1["state"] == r2["state"] == "SEARCH_CONSUMPTION_VERIFIED"
    assert before == after


def test_true_e2e_search_consumption(tmp_path):
    from discovery_fabric.engine.adapters import STAGE_ORDER
    from discovery_fabric.engine.run import EngineRun
    keep = {"RETRIEVE", "FREEZE", "PREMISE_GATE", "VERIFY",
            "MECHANISM_SPACE", "ADJUDICATION", "CLASSIFY"}
    dis = sorted(s for s in STAGE_ORDER if s not in keep)
    cem_file = _kill_cemetery(tmp_path)
    (tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
    Path(cem_file).write_text(json.dumps({"entries": []}),
                              encoding="utf-8")

    def _resolver(kid):
        data = json.loads(Path(cem_file).read_text())
        for e in data.get("entries", []):
            if e.get("entry_id") == kid:
                return e
        return None

    runs = tmp_path / "runs"
    control = EngineRun(problem=dict(PARENT_PROBLEM,
                                     problem_id="pp0_true_ctrl"),
                        out_dir=str(runs / "engrun_true_ctrl"),
                        run_id="engrun_true_ctrl",
                        disabled_stages=list(dis)).run()
    assert control.get("run_id") == "engrun_true_ctrl"
    with _cemetery(tmp_path):
        rec = _exec(_event("EV-TRUE-1", verdict="KILL"),
                    str(tmp_path / "ledger"),
                    parent_problem=dict(PARENT_PROBLEM),
                    parent_run_id=PARENT_RUN,
                    cemetery_path=cem_file)
    assert rec["executed"] is True, rec
    assert rec["branch"] == "KILL", rec
    kid = rec["branch_record"]["cemetery_entry_id"]
    req = rec["branch_record"]["child_request"]
    assert req["status"] == "REQUESTED", req
    base_constraint = str(PARENT_PROBLEM["constraint"])
    assert str(req["child_problem"]["constraint"]).startswith(
        base_constraint)
    treatment = EngineRun(problem=dict(req["child_problem"]),
                          out_dir=str(runs / "engrun_true_trt"),
                          run_id="engrun_true_trt",
                          disabled_stages=list(dis)).run()
    assert treatment.get("run_id") == "engrun_true_trt"
    man_c = json.loads((runs / "engrun_true_ctrl" / "run_manifest.json"
                        ).read_text())
    man_t = json.loads((runs / "engrun_true_trt" / "run_manifest.json"
                        ).read_text())
    assert sorted(man_c.get("disabled_stages", [])) == \
        sorted(man_t.get("disabled_stages", []))
    assert man_c.get("stage_order") == man_t.get("stage_order")
    exp = {"trigger_event_id": "EV-TRUE-1", "parent_run_id": PARENT_RUN,
           "knowledge_record_id": kid, "launch_id": "lid-true",
           "knowledge_artifact_sha256": req["knowledge_artifact_sha256"],
           "child_run_id": "engrun_true_trt",
           "parent_problem_sha256": req["parent_problem_sha256"],
           "branch": "KILL", "cemetery_entry_id": kid}
    kb = ri.verify_consumption(str(runs / "engrun_true_trt"), exp,
                               _resolver)
    assert kb["verified"] is True, kb["reason"]
    sc = ri.verify_search_consumption(str(runs / "engrun_true_trt"),
                                      exp, _resolver)
    assert sc["knowledge_state"] == "KNOWLEDGE_BOUND", sc
    snap_dir = tmp_path / "ledger" / "search_snapshots"
    snap_dir.mkdir(parents=True, exist_ok=True)
    s0 = ri.extract_search_state(str(runs / "engrun_true_ctrl"),
                                 cemetery_path=cem_file)
    s1 = ri.extract_search_state(str(runs / "engrun_true_trt"),
                                 cemetery_path=cem_file)
    s1["knowledge_binding"]["cemetery_entry_id"] = kid
    (snap_dir / "S0.json").write_text(json.dumps(s0), encoding="utf-8")
    (snap_dir / "S1.json").write_text(json.dumps(s1), encoding="utf-8")
    assert s0["canonical_state_hash"] == json.loads(
        (snap_dir / "S0.json").read_text())["canonical_state_hash"]
    delta = ri.measure_search_delta(s0, s1)
    ver = {"state": sc["state"], "record_hash": sc.get("record_hash")}
    adj = ri.adjudicate_search_learning(delta, ver)
    if adj["verdict"] == "LEARNING_CANDIDATE":
        assert sc["state"] == "SEARCH_CONSUMPTION_VERIFIED", sc
        assert delta["substantive"] is True, delta
        assert "constraint_applied" in delta["changed_fields"]
        ev = delta.get("decision_evidence") or {}
        assert ev.get("record_hash") == sc.get("record_hash"), ev
    else:
        assert adj["verdict"] == "NO_LEARNING", adj
        if sc["state"] == "SEARCH_CONSUMPTION_VERIFIED":
            assert delta["substantive"] is False, delta
            assert delta.get("decision_evidence") is None, delta
        else:
            assert sc["state"] == "SEARCH_CONSUMPTION_UNPROVEN", sc
            assert delta["substantive"] is False, delta
            assert "constraint_applied" not in delta["changed_fields"]


_WENTRY = dict(_KENTRY, entry_id="CE-TEST-W1",
               epistemic_class="STRONG_CONSTRAINT",
               physical_constraint="")


def test_kill_citing_foreign_entry_unattributed(tmp_path):
    art, art_sha = _sc_art()
    from discovery_fabric.engine import mechanism_space as _ms
    with _cemetery(tmp_path):
        Path(tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": [dict(_KENTRY)]}), encoding="utf-8")
        cands = _sc_candidates()
        rec1 = _ms._consult_cemetery(cands)
        assert rec1["n_blocked"] == 1, rec1
    treat = _sc_dir(tmp_path, "engrun_sfe1", "EV-SF-2", art_sha,
                    "engrun_sfe1", _sc_space(rec1, cands))
    out = ri.verify_search_consumption(
        str(treat),
        _sc_exp("EV-SF-2", art_sha, "engrun_sfe1",
                entry_id="CE-TEST-OTHER"),
        _vresolver({"KX": art}))
    assert "CEMETERY_KILL" not in out["checks"]["decisions"], out
    runs = tmp_path / "runs"
    plain = runs / "engrun_sfe0"
    plain.mkdir(parents=True, exist_ok=True)
    (plain / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_sfe0")),
        encoding="utf-8")
    (plain / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_sfe0"}), encoding="utf-8")
    s0 = ri.extract_search_state(str(plain))
    s1 = ri.extract_search_state(str(treat))
    s1["knowledge_binding"]["cemetery_entry_id"] = "CE-TEST-OTHER"
    delta = ri.measure_search_delta(s0, s1)
    assert "kill_decision_bound" not in delta["changed_fields"], delta
    assert "kill_decision_unlinked_informational_only" in \
        delta["changed_fields"], delta


def test_warning_decision_verified_to_learning(tmp_path):
    art, art_sha = _sc_art()
    from discovery_fabric.engine import mechanism_space as _ms
    with _cemetery(tmp_path):
        Path(tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": []}), encoding="utf-8")
        rec0 = _ms._consult_cemetery(_sc_candidates())
        assert rec0["n_warned"] == 0
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": [dict(_WENTRY)]}), encoding="utf-8")
        cands = _sc_candidates()
        rec1 = _ms._consult_cemetery(cands)
        assert rec1["n_blocked"] == 0, rec1
        assert rec1["n_warned"] == 1, rec1
    assert cands[0]["cemetery_warnings"][0]["cemetery_entry"] == \
        "CE-TEST-W1"
    runs = tmp_path / "runs"
    plain = runs / "engrun_swv0"
    plain.mkdir(parents=True, exist_ok=True)
    (plain / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_swv0")),
        encoding="utf-8")
    (plain / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_swv0"}), encoding="utf-8")
    space = _sc_space(rec1, cands, full=[{"candidates": cands}])
    treat = _sc_dir(tmp_path, "engrun_swv1", "EV-SW-1", art_sha,
                    "engrun_swv1", space)
    exp = _sc_exp("EV-SW-1", art_sha, "engrun_swv1",
                  entry_id="CE-TEST-W1")
    out = ri.verify_search_consumption(str(treat), exp,
                                       _vresolver({"KX": art}))
    assert out["state"] == "SEARCH_CONSUMPTION_VERIFIED", out
    assert "CEMETERY_WARNING" in out["checks"]["decisions"], out
    assert "CEMETERY_KILL" not in out["checks"]["decisions"], out
    s0 = ri.extract_search_state(str(plain))
    s1 = ri.extract_search_state(str(treat))
    s1["knowledge_binding"]["cemetery_entry_id"] = "CE-TEST-W1"
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is True, delta
    assert "warning_decision_bound" in delta["changed_fields"]
    assert "constraint_applied" in delta["changed_fields"]
    ev = delta.get("decision_evidence") or {}
    assert ev.get("decision_type") == "CEMETERY_WARNING", ev
    assert ev.get("record_hash") == out.get("record_hash"), ev
    adj = ri.adjudicate_search_learning(
        delta, {"state": out["state"],
                "record_hash": out.get("record_hash")})
    assert adj["verdict"] == "LEARNING_CANDIDATE", adj
    assert adj.get("decision_evidence", {}).get(
        "decision_type") == "CEMETERY_WARNING", adj


def test_adjudicator_gates(tmp_path):
    art, art_sha = _sc_art()
    from discovery_fabric.engine import mechanism_space as _ms
    with _cemetery(tmp_path):
        Path(tmp_path / "cemetery").mkdir(parents=True, exist_ok=True)
        (tmp_path / "cemetery" / "CEMETERY.json").write_text(
            json.dumps({"entries": [dict(_KENTRY)]}), encoding="utf-8")
        cands = _sc_candidates()
        rec1 = _ms._consult_cemetery(cands)
    runs = tmp_path / "runs"
    plain = runs / "engrun_sag0"
    plain.mkdir(parents=True, exist_ok=True)
    (plain / "problem.json").write_text(
        json.dumps(dict(PARENT_PROBLEM, problem_id="pp0_sag0")),
        encoding="utf-8")
    (plain / "run_manifest.json").write_text(
        json.dumps({"run_id": "engrun_sag0"}), encoding="utf-8")
    treat = _sc_dir(tmp_path, "engrun_sag1", "EV-SG-1", art_sha,
                    "engrun_sag1", _sc_space(rec1, cands))
    s0 = ri.extract_search_state(str(plain))
    s1 = ri.extract_search_state(str(treat))
    s1["knowledge_binding"]["cemetery_entry_id"] = "CE-TEST-K1"
    delta = ri.measure_search_delta(s0, s1)
    assert delta["substantive"] is True, delta
    assert ri.adjudicate_search_learning(delta, None)["verdict"] == \
        "NO_LEARNING"
    assert ri.adjudicate_search_learning(
        delta, {"state": "SEARCH_CONSUMPTION_UNPROVEN",
                "record_hash": None})["verdict"] == "NO_LEARNING"
    flat = ri.measure_search_delta(s0, s0)
    assert flat["substantive"] is False
    ver = {"state": "SEARCH_CONSUMPTION_VERIFIED",
           "record_hash": (delta.get("decision_evidence") or {}).get(
               "record_hash")}
    assert ri.adjudicate_search_learning(flat, ver)["verdict"] == \
        "NO_LEARNING"
    bad_link = dict(ver, record_hash="00" * 32)
    assert ri.adjudicate_search_learning(delta, bad_link)["verdict"] \
        == "NO_LEARNING"
