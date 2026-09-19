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
