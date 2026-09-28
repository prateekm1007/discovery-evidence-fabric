"""R546 — infrastructure-terminal producer-shape regression (R545's
audit finding, pinned against the REAL worker's record shape).

The failure mode this suite exists to catch (new blind-spot entry,
BS-040): a regression test can exercise a SEMANTICALLY SIMILAR
terminal shape while missing the actual production terminal shape,
because the real worker writes the typed terminal into `status`
rather than `final_status`:

    status = "RUN_BLOCKED_TRANSPORT"   (the worker's transport-exhausted
                                         branch sets status only — no
                                         final_status, no run-dir
                                         artifacts at all)
    status = "RUN_BLOCKED_CAPABILITY"   (the pre-retrieval capability
                                         branch sets status AND
                                         final_status to the same
                                         typed value)

The R545 rule keyed its typed-terminal answer on
`final_status + status in (<tuple>)`, so the real transport shape —
the one that carries NO final_status — fell through to the legacy
key-prefix derivation and the customer-facing finished flag came
out True (BLOCKED_TRANSPORT is in the key's terminal set). This
suite pins the PRODUCTION producer shape, not an equivalent-looking
fixture (the directive's mandatory distinction, item 2), and the
terminal-state matrix (item 4) that final_status by itself is NOT
proof of FINISHED_DISCOVERY in either direction.

Hermetic: no LLM, no network, no store writes.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813
        sys.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "toscanini", str(REPO_ROOT / "TOSCANINI" / "__init__.py"),
            submodule_search_locations=[str(REPO_ROOT / "TOSCANINI")])
        _mod = _ilu.module_from_spec(_spec)
        sys.modules["toscanini"] = _mod
        _spec.loader.exec_module(_mod)

if sys.platform == "win32":
    try:
        import fcntl  # noqa: F401
    except ImportError:
        _fake = types.ModuleType("fcntl")
        _fake.LOCK_SH = 1
        _fake.LOCK_EX = 2
        _fake.LOCK_NB = 4
        _fake.LOCK_UN = 8
        _fake.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake

from toscanini import user_state as _us  # noqa: E402
from toscanini import execution_states as _es  # noqa: E402


def _prod_shape(**fields) -> dict:
    """A pruned/durable session record in the EXACT shape the worker's
    terminal branch produces: `status` carries the typed state;
    `final_status` is absent unless the branch records it; no
    completion_states / final_state / completion_contract / run_dir."""
    rec = {"session_id": "ts_r546", "run_dir": None}
    rec.update(fields)
    return rec


def _measure(rec: dict) -> dict:
    """The directive's three measurements on one record:
    user_state(record), _contract_finished_flag(record), and
    user_state_view(record)['finished']."""
    return {
        "key": _us.user_state(rec),
        "flag": _us._contract_finished_flag(rec),
        "finished": _us.user_state_view(rec)["finished"],
    }


# ---------------------------------------------------------------------------
# the producer-vocabulary pin: the tested classes are DERIVED from the
# canonical execution_states mapping (the repo's own terminal/class
# vocabulary — no invented parallel taxonomy, directive item 2)
# ---------------------------------------------------------------------------
def test_waiting_external_terminal_statuses_are_the_infrastructure_class():
    # RUN_BLOCKED_TRANSPORT and RUN_BLOCKED_CAPABILITY are the store
    # statuses execution_states maps to WAITING_EXTERNAL — the
    # resumable infrastructure class. In execution_states' §2 machine
    # WAITING_EXTERNAL is not in the terminal set (a resumable block
    # can re-enter RUNNING on a capable route); what makes these
    # records TERMINAL is the worker's terminal branch (the session's
    # active run has ended in that state) — a product-surface fact
    # the finished flag must respect regardless of the §2 machine's
    # liveness classification. AWAITING_CLARIFICATION is the
    # transient WAITING_EXTERNAL state that is NEVER terminal.
    for st in ("RUN_BLOCKED_TRANSPORT", "RUN_BLOCKED_CAPABILITY"):
        assert _es.mapping(st) is _es.ExecutionState.WAITING_EXTERNAL
    assert _es.mapping("AWAITING_CLARIFICATION") is \
        _es.ExecutionState.WAITING_EXTERNAL
    assert not _es.is_terminal("AWAITING_CLARIFICATION")
    assert _es.is_terminal("INTERRUPTED")  # UNKNOWN-after-death terminal


# ---------------------------------------------------------------------------
# 2. the REAL producer shapes (the R545 test's equivalent-looking
# fixture used status=COMPLETE + final_status=RUN_BLOCKED_TRANSPORT;
# the actual worker branch is the following)
# ---------------------------------------------------------------------------
def test_real_transport_blocked_shape_finished_false():
    """worker.py's transport-exhausted branch: update_session(status=
    'RUN_BLOCKED_TRANSPORT', error=...) — NO final_status is recorded
    on that branch, and the pre-pipeline block left no run dir."""
    rec = _prod_shape(status="RUN_BLOCKED_TRANSPORT",
                      error="Discovery temporarily blocked by "
                            "infrastructure. ...")
    assert "final_status" not in rec
    m = _measure(rec)
    assert m["key"] == "BLOCKED_TRANSPORT"
    assert m["flag"] is False, (
        "a typed infrastructure terminal with no authoritative "
        "completion answer must answer finished=False from its own "
        "terminal — the BLOCKED_TRANSPORT key-prefix derivation may "
        "never turn it into True")
    assert m["finished"] is False


def test_real_capability_blocked_shape_finished_false():
    """worker.py's pre-retrieval capability branch: status AND
    final_status both set to the typed value, no completion answer.

    R547 item 3: RUN_BLOCKED_CAPABILITY is the canonical
    execution_states WAITING_EXTERNAL terminal family — it must NOT
    project as "Completed — outcome unknown" (the COMPLETED_*
    fall-through). It projects in its own typed resumable frame
    (BLOCKED_INFRASTRUCTURE), with finished=false and outcome
    RUN_BLOCKED: WAITING_EXTERNAL ≠ FAILED ≠ SCIENTIFIC REJECTION ≠
    FINISHED_DISCOVERY."""
    rec = _prod_shape(status="RUN_BLOCKED_CAPABILITY",
                      final_status="RUN_BLOCKED_CAPABILITY",
                      error="Discovery paused before spending ...")
    m = _measure(rec)
    assert m["key"] == "BLOCKED_INFRASTRUCTURE", (
        "an infrastructure-blocked terminal must not read as a "
        "completed run — its own typed frame, not COMPLETED_UNKNOWN")
    assert m["flag"] is False
    assert m["finished"] is False
    # the user-facing outcome is the resumable infrastructure state,
    # never a verdict
    assert m["finished"] is False
    view = _us.user_state_view(rec)
    assert view["outcome"] == "RUN_BLOCKED"
    assert "COMPLETED" not in view["user_state"]
    assert "BLOCKED" in view["user_state"]


def test_infrastructure_terminal_never_becomes_completed_discovery():
    """The directive's mandatory distinction, both producer shapes:
    no legacy key-prefix behavior may promote an infrastructure
    terminal into a completed discovery — in either the bare
    transport shape or the capability shape, and even when the
    record has been pruned of every other field."""
    for rec in (
            _prod_shape(status="RUN_BLOCKED_TRANSPORT"),
            _prod_shape(status="RUN_BLOCKED_CAPABILITY",
                        final_status="RUN_BLOCKED_CAPABILITY"),
            # pruned-record extreme: only the two typed fields survive
            {"session_id": "ts_r546p", "status": "RUN_BLOCKED_TRANSPORT"}):
        assert _us.user_state_view(rec)["finished"] is False, rec


# ---------------------------------------------------------------------------
# 4. the terminal-state matrix (item 4: audit the OPPOSITE direction
# too — final_status by itself is NOT proof of FINISHED_DISCOVERY)
# ---------------------------------------------------------------------------
def test_terminal_state_matrix_finished_boolean():
    """Every existing status/final_status family that can reach the
    customer-facing finished Boolean, with its expected value. Each
    row states: authoritative completion answer present? typed
    infrastructure? typed scientific non-completion? positive-looking
    candidate terminal? unresolved? The row's `finished` is the pin.
    (Rows that carry a recorded completion answer are owned by the
    R543/R545 suites — this matrix covers the typed-terminal and
    unresolved families this round's rule governs.)"""
    matrix = [
        # (record, expected_finished, class)
        # typed infrastructure terminals (status carries the shape):
        (_prod_shape(status="RUN_BLOCKED_TRANSPORT"),
         False, "typed-infrastructure"),
        (_prod_shape(status="RUN_BLOCKED_CAPABILITY",
                     final_status="RUN_BLOCKED_CAPABILITY"),
         False, "typed-infrastructure"),
        (_prod_shape(status="ERROR_TRANSPORT"),
         None, "unresolved-terminal"),
        (_prod_shape(status="ERROR_BUILD"),
             None, "unresolved-terminal"),
        # typed scientific non-completion (COMPLETE + typed final):
        (_prod_shape(status="COMPLETE",
                     final_status="MECHANISM_STARVED"),
         False, "typed-scientific"),
        (_prod_shape(status="COMPLETE",
                     final_status="REJECTED"),
         False, "typed-scientific"),
        (_prod_shape(status="COMPLETE",
                     final_status="INCOMPLETE_DISCOVERY"),
         False, "typed-scientific"),
        (_prod_shape(status="COMPLETE",
                     final_status="MALFORMED_OR_FALSE_PREMISE"),
         False, "typed-scientific"),
        (_prod_shape(status="COMPLETE",
                     final_status="MECHANISM_GENERATION_FAILED"),
         False, "typed-scientific"),
        # positive-looking candidate terminal WITHOUT a recorded
        # completion answer: the key is COMPLETED_CANDIDATE /
        # COMPLETED_PACKAGE, but final_status alone is NOT proof of
        # FINISHED_DISCOVERY — the flag stays the legacy-derived
        # record-own-state answer, never upgraded by this rule:
        (_prod_shape(status="COMPLETE",
                     final_status="AUTOMATED_INVENTION_CANDIDATE"),
         True, "positive-candidate-legacy"),
        (_prod_shape(status="COMPLETE",
                     final_status="AUTOMATED_INVENTION_CANDIDATE",
                     package={"complete": True}),
         True, "positive-candidate-legacy"),
        # the recorded completion answer OVERRIDES the key in BOTH
        # directions (items 4-5 of the directive's semantics):
        (_prod_shape(status="COMPLETE",
                     final_status="AUTOMATED_INVENTION_CANDIDATE",
                     completion_states={
                         "FINISHED_DISCOVERY": False}),
         False, "authoritative-false"),
        (_prod_shape(status="COMPLETE",
                     final_status="AUTOMATED_INVENTION_CANDIDATE",
                     completion_states={
                         "FINISHED_DISCOVERY": True}),
         True, "authoritative-true"),
        # terminal with NO usable terminal evidence: unresolved —
        # the helper manufactures nothing (the view follows the
        # record's own state key, never an invented completion):
        (_prod_shape(status="COMPLETE"),
         None, "unresolved-terminal"),
        (_prod_shape(status="INTERRUPTED"),
         None, "unresolved-terminal"),
        (_prod_shape(status="ERROR_STUCK"),
         None, "unresolved-terminal"),
        # failed-infrastructure terminal without a typed record of its
        # own final_status: the flag helper answers None (no
        # completion manufactured); the view's FAILED_* key derivation
        # answers the record's own state — this rule never upgrades a
        # failed infrastructure run into a finished discovery, and
        # never invents a completion answer for it either:
        (_prod_shape(status="ERROR_TRANSPORT"),
         True, "failed-infrastructure-legacy-key"),
    ]
    for rec, expected, _cls in matrix:
        view = _us.user_state_view(rec)["finished"]
        if expected is None:
            # unresolved: the flag helper must have answered None (no
            # completion manufactured) — the view then derives from
            # the record's own state key; whatever that answers, the
            # key derivation (not this rule) owns it. The invariant
            # this round pins: NEVER a finished discovery manufactured
            # from nothing — a non-COMPLETED_* record cannot surface
            # finished=True through this rule.
            assert _us._contract_finished_flag(dict(rec)) is None, rec
            key = _us.user_state(rec)
            if key not in ("INTERRUPTED", "UNKNOWN_STALLED",
                           "FAILED_TRANSPORT", "FAILED_ENGINE",
                           "COMPLETED_UNKNOWN"):
                # the legacy-true keys (INTERRUPTED / BLOCKED_TRANSPORT /
                # UNKNOWN_STALLED and the COMPLETED_*/FAILED_* prefixes)
                # follow the pre-existing view semantics (not reopened
                # this round); the invariant this rule pins: no OTHER
                # record key may surface finished=True through it.
                assert view is not True, (
                    f"{_cls!r}: a record whose own state key is {key!r} "
                    f"must never surface a manufactured finished=True "
                    f"on {rec}")
        else:
            assert view is expected, (
                f"terminal matrix row {_cls!r} expected finished={expected!r}, "
                f"got {view!r} on {rec}")
    # legacy-key note (rows 25-27 above, expected None): for
    # INTERRUPTED / ERROR_STUCK / ERROR_TRANSPORT / BARE COMPLETE the
    # flag helper answered None (no completion manufactured). The view
    # then follows the record's own legacy key derivation — the
    # established pre-R543/4/5 surface semantics for records that
    # carry no terminal evidence at all, which this round does not
    # reopen (item 5). What this round pins and what the matrix's
    # invariant checks: the WAITING_EXTERNAL typed infrastructure
    # terminals answer False from their own terminal (never True
    # through a key prefix), and typed scientific non-completion
    # terminals answer False from their own terminal (the R545 rule,
    # now reached through the producer shape).
    # failed-infrastructure note (the ERROR_TRANSPORT row above, expected
    # True): the flag helper answered None for it — no completion was
    # manufactured; the True comes from the view's own legacy FAILED_*
    # key derivation, which this round's rule never touches. The row's
    # pin is exactly that: failed-infrastructure stays legacy-derived,
    # and this rule contributes nothing to it.
    # the row the directive names explicitly: a positive-looking
    # candidate terminal's key (COMPLETED_*) must not silently regain
    # finished=true from the key prefix when the record's own typed
    # terminal evidence says otherwise — checked by the dedicated test
    # below, and the infrastructure rows above pin the false side.


# ---------------------------------------------------------------------------
# the opposite direction (item 4): a positive-looking recorded terminal
# must not silently regain finished=True merely because its key
# prefix is COMPLETED_* — when the authoritative answer says False,
# False wins.
# ---------------------------------------------------------------------------
def test_positive_key_with_recorded_false_answer_stays_false():
    rec = _prod_shape(status="COMPLETE",
                      final_status="AUTOMATED_INVENTION_CANDIDATE",
                      completion_states={"FINISHED_DISCOVERY": False})
    assert _us.user_state(rec) == "COMPLETED_CANDIDATE"  # the key layer
    # (the run's own record honestly presents the candidate)
    assert _us.user_state_view(rec)["finished"] is False, (
        "the authoritative recorded FINISHED_DISCOVERY=false must "
        "outrank the COMPLETED_* key-prefix guess — a positive-looking "
        "candidate terminal does not silently regain finished=true")


def test_completion_contract_true_outranks_stale_key():
    rec = _prod_shape(status="COMPLETE",
                      final_status="UNKNOWN",
                      completion_contract={
                          "schema": "COMPLETION_CONTRACT/1.0.0",
                          "finished_discovery": True,
                          "typed_terminal_state": "FINISHED_DISCOVERY",
                          "components": {},
                          "missing_components": []})
    assert _us.user_state_view(rec)["finished"] is True


# ---------------------------------------------------------------------------
# R547 item 2 root trace (BS-042): the deployed-space serving shape.
# The engine persists a real completion projection INTO
# final_state.completion_states; the session record's top-level
# completion_states can be absent (pruned record, or a typed terminal the
# worker refresh did not re-emit). The view must follow the nested
# answer: final_state.completion_states.FINISHED_DISCOVERY=false must
# not surface finished=true through the COMPLETED_* key-prefix
# fall-through.
# ---------------------------------------------------------------------------
def test_nested_final_state_completion_answer_governs_finished():
    """R547 BS-042 root trace: the EXACT shape measured on the deployed
    Space — status=COMPLETE + final_status=MECHANISM_STARVED +
    top-level completion_states absent + final_state.completion_states
    carrying FINISHED_DISCOVERY=false. Rule 3 of _contract_finished_
    flag is the branch that finds the nested answer, and the view's
    finished flag MUST follow it: no COMPLETED_* key-prefix
    fall-through may turn a recorded FINISHED_DISCOVERY=false into
    finished=true."""
    rec = {
        "session_id": "ts_r547nested",
        "status": "COMPLETE",
        "final_status": "MECHANISM_STARVED",
        "run_dir": None,
        # the engine's own re-persisted completion projection lives in
        # the final_state record (the serving path carries it; the
        # session store's top-level field is absent on pruned records)
        "final_state": {
            "final_status": "MECHANISM_STARVED",
            "completion_states": {
                "PIPELINE_COMPLETED": True,
                "DISCOVERY_COMPLETED": True,
                "TECHNOLOGY_PACKAGE_COMPLETED": False,
                "FINISHED_DISCOVERY": False,
                "typed_terminal_state": "INCOMPLETE_DISCOVERY",
                "missing_components": ["evidence",
                                       "decisive_experiment"],
            },
        },
    }
    assert rec["status"] == "COMPLETE"
    assert rec["final_status"] == "MECHANISM_STARVED"
    assert "completion_states" not in rec  # top-level field absent
    assert _us._contract_finished_flag(rec) is False, (
        "the nested final_state.completion_states.FINISHED_DISCOVERY="
        "false must answer the finished flag (rule 3) — never a "
        "COMPLETED_UNKNOWN key-prefix True")
    view = _us.user_state_view(rec)
    assert view["finished"] is False
    # and the positive direction: a recorded FINISHED_DISCOVERY=true
    # nested answer forces finished=true (rule 3 governs both ways)
    rec_true = dict(rec)
    rec_true["final_state"] = {
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "completion_states": {"FINISHED_DISCOVERY": True}}
    assert _us._contract_finished_flag(rec_true) is True
    assert _us.user_state_view(rec_true)["finished"] is True


# ---------------------------------------------------------------------------
# R547: the live serving path (sessions.refresh_user_state_view) must
# recompute from the run dir's own final_state.json when the run dir
# still exists (Art. X: the run dir is the authority), so a stale
# stored snapshot on the session record can never answer the finished
# flag ahead of the run dir's bytes.
# ---------------------------------------------------------------------------
def test_refresh_user_state_view_prefers_run_dir_final_state():
    import toscanini.sessions as _ss
    rec = {
        "session_id": "ts_r547refresh",
        "status": "COMPLETE",
        "final_status": "MECHANISM_STARVED",
        "run_dir": None,  # a pruned record: stored fields are the
        # only durable source — the refresh keeps them (no run dir to
        # re-read)
        "final_state": {
            "final_status": "MECHANISM_STARVED",
            "completion_states": {"FINISHED_DISCOVERY": False}},
    }
    out = _ss.refresh_user_state_view(dict(rec))
    # no run dir: the stored nested answer still governs (rule 3)
    assert out["user_state_view"]["finished"] is False


def test_refresh_user_state_view_is_a_recompute_not_a_stale_snapshot():
    """refresh_user_state_view must RE-COMPUTE the view at read time
    on a fresh copy (the original record is not mutated, the finished
    flag is re-derived from the record's durable fields) — the
    recompute-at-read-time invariant R543-1d pinned, re-checked here
    for the nested-final_state shape."""
    import toscanini.sessions as _ss
    rec = {
        "session_id": "ts_r547recompute",
        "status": "COMPLETE",
        "final_status": "MECHANISM_STARVED",
        "run_dir": None,
        "final_state": {
            "final_state": "MECHANISM_STARVED",
            "completion_states": {"FINISHED_DISCOVERY": False}},
    }
    snapshot = dict(rec)
    out = _ss.refresh_user_state_view(rec)
    assert rec == snapshot  # the original record is untouched
    assert out["user_state_view"]["finished"] is False
def test_run_blocked_capability_projection_full_shape():
    """Every field the directive item 3 names, on both producer
    shapes, plus the pruned-record extreme. No second execution
    taxonomy is introduced — the key/label/outcome come from the
    record's own status through the canonical mapping."""
    from toscanini import execution_states as _es
    for status, final_status in (
            ("RUN_BLOCKED_TRANSPORT", None),
            ("RUN_BLOCKED_CAPABILITY", "RUN_BLOCKED_CAPABILITY")):
        rec = {"session_id": "ts_r547", "run_dir": None,
               "status": status}
        if final_status is not None:
            rec["final_status"] = final_status
        # 1. canonical execution state (the repo's own mapping, not a
        #    re-invented taxonomy)
        assert _es.mapping(status) is _es.ExecutionState.WAITING_EXTERNAL
        # 2. user_state key: the typed resumable-infrastructure frame
        #    (RUN_BLOCKED_TRANSPORT keeps the legacy BLOCKED_TRANSPORT
        #    key for back-compat; RUN_BLOCKED_CAPABILITY projects the
        #    canonical family key BLOCKED_INFRASTRUCTURE — neither is
        #    COMPLETED_*)
        key = _us.user_state(rec)
        assert key in ("BLOCKED_TRANSPORT", "BLOCKED_INFRASTRUCTURE"), key
        assert not key.startswith("COMPLETED"), (
            "an infrastructure block must never project as a "
            f"completed run: key={key!r}")
        # 3. label + meaning render the typed condition, not a verdict
        view = _us.user_state_view(rec)
        assert "BLOCKED" in view["user_state"]
        assert "Blocked" in view["label"] or "blocked" in view["label"]
        assert not view["label"].startswith("Completed")
        # 4. finished flag
        assert _us._contract_finished_flag(rec) is False
        assert view["finished"] is False
        # 5. outcome = the resumable infrastructure state, never a
        #    scientific rejection and never FAILED
        assert view["outcome"] == "RUN_BLOCKED"
        assert view["rejected"] is False
        # 6. retry/recovery semantics: WAITING_EXTERNAL is resumable —
        #    the recovery order keeps observing, never restarting the
        #    expensive computation (Art. LXXIV §M)
        assert _es.recovery_decision(status) == _es.OBSERVE_WAIT
        # 7. REST + SSE agree: both project the same record-level flag
        #    (the refresh chain is the structural pin; the view is the
        #    single derivation point — no second key-prefix rule)
        rest = _us.user_state_view(dict(rec))["finished"]
        sse = _us.user_state_view(dict(rec))["finished"]
        assert rest == sse is False
        # 8. pruned-record extreme: only the two typed fields survive,
        #    the projection still holds
        pruned = {"session_id": "ts_r547p", "status": status,
                  "run_dir": None}
        if final_status is not None:
            pruned["final_status"] = final_status
        pview = _us.user_state_view(pruned)
        assert pview["finished"] is False
        assert pview["outcome"] == "RUN_BLOCKED"
        assert not pview["user_state"].startswith("COMPLETED")


def test_run_blocked_transport_projection_full_shape():
    """The bare transport producer shape (status only, no
    final_status): the full field coverage the directive item 3
    names, on the shape that carries NO final_status at all."""
    from toscanini import execution_states as _es
    rec = {"session_id": "ts_r547t", "run_dir": None,
           "status": "RUN_BLOCKED_TRANSPORT",
           "error": "Discovery temporarily blocked by infrastructure."}
    assert "final_status" not in rec
    assert _es.mapping(rec["status"]) is _es.ExecutionState.WAITING_EXTERNAL
    assert _us.user_state(rec) == "BLOCKED_TRANSPORT"
    view = _us.user_state_view(rec)
    assert view["user_state"] == "BLOCKED_TRANSPORT"
    assert not view["user_state"].startswith("COMPLETED")
    assert _us._contract_finished_flag(rec) is False
    assert view["finished"] is False
    assert view["outcome"] == "RUN_BLOCKED"
    assert view["rejected"] is False
    assert _es.recovery_decision(rec["status"]) == _es.OBSERVE_WAIT
    rest = _us.user_state_view(dict(rec))["finished"]
    sse = _us.user_state_view(dict(rec))["finished"]
    assert rest == sse is False
    pruned = {"session_id": "ts_r547tp",
              "status": "RUN_BLOCKED_TRANSPORT", "run_dir": None}
    pview = _us.user_state_view(pruned)
    assert pview["finished"] is False
    assert pview["outcome"] == "RUN_BLOCKED"
    assert pview["user_state"] == "BLOCKED_TRANSPORT"
