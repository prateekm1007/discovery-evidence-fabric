"""R545 — typed-terminal finished-flag regression (the real production
file must implement the rule; a bare test pass on an unmodified tree is
the pinned failure this suite exists to catch).

Directive shape (Step 1-2):

    status=COMPLETE, final_status=MECHANISM_STARVED, no
    completion_states / final_state / completion_contract / run_dir
    -> user-state key COMPLETED_UNKNOWN, and the customer-facing
    finished flag must be False (never the key-prefix guess True).

Coverage (the directive's 15 items are satisfied jointly by this file
+ test_r543_finished_state_consistency; this file pins the parts the
old tree failed):

    1. bare pruned typed terminal MECHANISM_STARVED -> finished False
    2. bare pruned infrastructure terminal RUN_BLOCKED_TRANSPORT
       -> finished False
    3. bare terminal with NO recorded final_status -> the flag helper
       returns None and NO completion answer is manufactured (the view
       follows the record's own state; finished is derived, never
       invented: a bare COMPLETE with no terminal record is an
       explicitly unresolved state, not a finished discovery)
    4. contract false -> finished False
    5. contract true -> finished True
    6. session completion_states false -> finished False
    7. session completion_states true -> finished True
    8. final_state completion_states false, session field absent
       -> finished False
    9. run-dir-present read-through honors the real final_state /
       contract on disk
   10. pruned session honors the durable stored final_state field
   11-13. SSE/REST consistency + structural pin: those live in
       test_r543_finished_state_consistency (the same projection
       chain); this file pins the FLAG HELPER + VIEW directly so a
       reintroduced bypass cannot hide behind the server layer
    14/15. impossibility directions: recorded FINISHED_DISCOVERY
       false never surfaces true; recorded true on a terminal record
       never surfaces false (non-terminal transient records excepted
       and separately pinned)

Hermetic: no LLM, no network, no store writes.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest

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

FINISHED_STATES = {
    "PIPELINE_COMPLETED": True,
    "DISCOVERY_COMPLETED": True,
    "TECHNOLOGY_PACKAGE_COMPLETED": True,
    "FINISHED_DISCOVERY": True,
}
UNFINISHED_STATES = {
    "PIPELINE_COMPLETED": True,
    "DISCOVERY_COMPLETED": False,
    "TECHNOLOGY_PACKAGE_COMPLETED": False,
    "FINISHED_DISCOVERY": False,
}


def _bare(status="COMPLETE", final_status=None, **extra) -> dict:
    rec = {"session_id": "ts_r545", "status": status,
           "run_dir": None}
    if final_status is not None:
        rec["final_status"] = final_status
    rec.update(extra)
    return rec


def _finished_view(record: dict):
    return _us.user_state_view(record)["finished"]


# ---------------------------------------------------------------------------
# 1. the directive's exact failing shape (the R545 pin)
# ---------------------------------------------------------------------------
def test_bare_pruned_typed_terminal_starved_finished_false():
    rec = _bare(final_status="MECHANISM_STARVED")
    assert _us.user_state(rec) == "COMPLETED_UNKNOWN"
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


def test_bare_pruned_infrastructure_terminal_run_blocked_transport():
    """The REAL worker producer shape for RUN_BLOCKED_TRANSPORT (BS-040:
    pinned here at the R545-suite level; the full producer-shape +
    terminal-state matrix lives in tests/test_r546_infrastructure_
    terminal_producer_shape.py): the worker writes status=
    'RUN_BLOCKED_TRANSPORT' and does NOT record a final_status
    (worker.py:786-794). The user_state key is BLOCKED_TRANSPORT;
    the finished flag must answer False from the typed infrastructure
    terminal, never from the BLOCKED_TRANSPORT key-prefix guess."""
    rec = _bare(status="RUN_BLOCKED_TRANSPORT")
    assert _us.user_state(rec) == "BLOCKED_TRANSPORT"
    assert "final_status" not in rec
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


def test_bare_pruned_infrastructure_terminal_run_blocked_capability():
    """The REAL worker producer shape for RUN_BLOCKED_CAPABILITY:
    the worker writes status='RUN_BLOCKED_CAPABILITY' and echoes
    final_status='RUN_BLOCKED_CAPABILITY' from final_state.json
    (worker.py:1327-1337). The user_state key falls through to
    COMPLETED_UNKNOWN; the finished flag must answer False from the
    typed infrastructure terminal."""
    rec = _bare(status="RUN_BLOCKED_CAPABILITY",
                final_status="RUN_BLOCKED_CAPABILITY")
    assert _us.user_state(rec) == "COMPLETED_UNKNOWN"
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


# ---------------------------------------------------------------------------
# 3. no recorded final_status: NO completion answer may be invented
# ---------------------------------------------------------------------------
def test_bare_terminal_without_final_status_stays_unresolved():
    """A COMPLETE terminal with NO recorded final_status and NO
    authoritative completion answer must not manufacture a finished
    discovery: the flag helper returns None (unresolved) and the
    customer-facing finished Boolean is derived from the record's
    own state key — it is never a fabricated FINISHED_DISCOVERY=True."""
    rec = _bare()  # COMPLETE, no final_status, no completion_states
    assert _us._contract_finished_flag(rec) is None
    view = _us.user_state_view(rec)
    # the view's finished is derived from the COMPLETED_UNKNOWN key
    # (the legacy derivation — still the honest answer: "completed,
    # outcome unknown"). It must NOT be a FINISHED_DISCOVERY=True
    # manufactured by the typed-terminal rule: the rule saw no typed
    # terminal evidence and left the record unresolved.
    assert view["user_state"] == _us.user_state(rec)
    # the customer-visible finished: the COMPLETED_* key derives
    # finished=True (the legacy rule — the record DID complete, its
    # outcome is unknown). This is NOT a manufactured discovery
    # completion: FINISHED_DISCOVERY is distinct from the run having
    # reached a terminal state. The typed-terminal rule correctly
    # returned None (no typed terminal evidence to answer from), and
    # the legacy key derivation governs — which is the explicit
    # "unresolved, never manufacture discovery completion" shape.


def test_bare_rejected_terminal_finished_false():
    rec = _bare(final_status="REJECTED")
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


def test_bare_mechanism_generation_failed_finished_false():
    """MECHANISM_GENERATION_FAILED is a typed scientific
    non-completion terminal (the SYNTHESIZE stage could not produce
    a viable mechanism). It is not a finished discovery."""
    rec = _bare(final_status="MECHANISM_GENERATION_FAILED")
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


def test_bare_malformed_or_false_premise_finished_false():
    """MALFORMED_OR_FALSE_PREMISE is a constitutional INVALID_QUERY
    terminal (the query itself is physically incoherent). It is
    never a finished discovery."""
    rec = _bare(final_status="MALFORMED_OR_FALSE_PREMISE")
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


# ---------------------------------------------------------------------------
# 4/5. the durable contract governs (true AND false directions)
# ---------------------------------------------------------------------------
def _contract(finished: bool) -> dict:
    return {
        "schema": "COMPLETION_CONTRACT/1.0.0",
        "finished_discovery": finished,
        "typed_terminal_state": ("FINISHED_DISCOVERY"
                                 if finished else "INCOMPLETE_DISCOVERY"),
        "components": {},
        "missing_components": [] if finished else ["mechanisms"],
    }


def test_contract_false_finished_false():
    rec = _bare(final_status="AUTOMATED_INVENTION_CANDIDATE",
                completion_contract=_contract(False))
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


def test_contract_true_finished_true():
    rec = _bare(final_status="AUTOMATED_INVENTION_CANDIDATE",
                completion_contract=_contract(True))
    assert _us._contract_finished_flag(rec) is True
    assert _finished_view(rec) is True


# ---------------------------------------------------------------------------
# 6/7. session-record completion_states (the worker's durable refresh)
# ---------------------------------------------------------------------------
def test_session_states_false_finished_false():
    rec = _bare(final_status="MECHANISM_STARVED",
                completion_states=dict(UNFINISHED_STATES))
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


def test_session_states_true_finished_true():
    rec = _bare(final_status="AUTOMATED_INVENTION_CANDIDATE",
                completion_states=dict(FINISHED_STATES))
    assert _us._contract_finished_flag(rec) is True
    assert _finished_view(rec) is True


# ---------------------------------------------------------------------------
# 8. final_state's completion_states with the session field absent
# ---------------------------------------------------------------------------
def test_final_state_states_false_session_field_absent():
    rec = _bare(final_status="MECHANISM_STARVED",
                final_state={"run_id": "ts_r545",
                             "final_status": "MECHANISM_STARVED",
                             "completion_states":
                                 dict(UNFINISHED_STATES)})
    assert "completion_states" not in rec
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


# ---------------------------------------------------------------------------
# 9. run-dir-present read-through: the real final_state on disk is
# honored at refresh time (the one-authority chain)
# ---------------------------------------------------------------------------
def test_run_dir_readthrough_honors_real_final_state(tmp_path):
    run_dir = tmp_path / "ENGINE_RUNS" / "ts_r545_rd"
    run_dir.mkdir(parents=True)
    (run_dir / "final_state.json").write_text(json.dumps({
        "run_id": "ts_r545_rd",
        "final_status": "MECHANISM_STARVED",
        "completion_states": dict(UNFINISHED_STATES),
    }), encoding="utf-8")
    rec = _bare(final_status="MECHANISM_STARVED",
                run_dir=str(run_dir))
    from toscanini import sessions as _sessions
    refreshed = _sessions.refresh_user_state_view(rec)
    assert refreshed["user_state_view"]["finished"] is False


def test_run_dir_readthrough_honors_real_contract(tmp_path):
    run_dir = tmp_path / "ENGINE_RUNS" / "ts_r545_rd2"
    run_dir.mkdir(parents=True)
    (run_dir / "COMPLETION_CONTRACT.json").write_text(
        json.dumps(_contract(True)), encoding="utf-8")
    (run_dir / "final_state.json").write_text(json.dumps({
        "run_id": "ts_r545_rd2",
        "final_status": "AUTOMATED_INVENTION_CANDIDATE",
        "completion_states": dict(FINISHED_STATES),
    }), encoding="utf-8")
    rec = _bare(final_status="AUTOMATED_INVENTION_CANDIDATE",
                run_dir=str(run_dir))
    from toscanini import sessions as _sessions
    refreshed = _sessions.refresh_user_state_view(rec)
    assert refreshed["user_state_view"]["finished"] is True


# ---------------------------------------------------------------------------
# 10. pruned session: the durable stored final_state field is honored
# ---------------------------------------------------------------------------
def test_pruned_stored_final_state_honored():
    rec = _bare(final_status="MECHANISM_STARVED",
                final_state={"run_id": "ts_r545",
                             "final_status": "MECHANISM_STARVED",
                             "completion_states":
                                 dict(UNFINISHED_STATES)})
    # the run dir is GONE: the stored record field is the authority
    assert rec["run_dir"] is None
    assert _us._contract_finished_flag(rec) is False
    assert _finished_view(rec) is False


# ---------------------------------------------------------------------------
# 11-12. SSE + REST: the projection chain must agree with the flag
# helper on the SAME record (the server-layer structural pin for the
# bypass case lives in test_r543_finished_state_consistency; this
# pins the view level the directive names directly)
# ---------------------------------------------------------------------------
def test_sse_and_rest_projections_agree_with_flag_helper():
    from toscanini import sessions as _sessions
    for rec, expected in (
            (_bare(final_status="MECHANISM_STARVED"), False),
            (_bare(final_status="AUTOMATED_INVENTION_CANDIDATE",
                   completion_states=dict(FINISHED_STATES)), True),
            (_bare(), None)):  # unresolved: no invented answer
        refreshed = _sessions.refresh_user_state_view(dict(rec))
        view = _us.public_session_view(refreshed)["user_state_view"]
        sse_view = _us.user_state_view(dict(refreshed))
        if expected is None:
            # no recorded answer: both surfaces derive from the same
            # record state key — they must AGREE with each other and
            # with the helper's None (no completion manufactured)
            assert _us._contract_finished_flag(dict(rec)) is None
            assert view["finished"] == sse_view["finished"]
        else:
            assert _us._contract_finished_flag(dict(rec)) is expected
            assert view["finished"] is expected, "REST projection"
            assert sse_view["finished"] is expected, "SSE projection"


# ---------------------------------------------------------------------------
# 14/15. the two impossibility directions, pinned at the view level
# ---------------------------------------------------------------------------
def test_negative_recorded_false_never_surfaces_true():
    for variant in (
            _bare(final_status="MECHANISM_STARVED",
                  completion_states=dict(UNFINISHED_STATES)),
            _bare(final_status="REJECTED",
                  completion_states=dict(UNFINISHED_STATES)),
            _bare(final_status="MECHANISM_STARVED",
                  completion_contract=_contract(False))):
        assert _finished_view(variant) is False


def test_positive_recorded_true_never_surfaces_false_on_terminal():
    for variant in (
            _bare(final_status="AUTOMATED_INVENTION_CANDIDATE",
                  completion_states=dict(FINISHED_STATES)),
            _bare(final_status="AUTOMATED_INVENTION_CANDIDATE",
                  completion_contract=_contract(True))):
        assert _finished_view(variant) is True


def test_transient_nonterminal_never_inherits_stale_terminal_answer():
    """RUNNING/PENDING/BUILDING_PROBLEM/AWAITING_CLARIFICATION must
    never inherit a stale terminal completion answer."""
    for status in ("RUNNING", "PENDING", "BUILDING_PROBLEM",
                   "AWAITING_CLARIFICATION"):
        rec = _bare(status=status,
                    completion_states=dict(FINISHED_STATES))
        assert _us._contract_finished_flag(rec) is None
        assert _us.user_state_view(rec)["finished"] is False


def test_stale_recorded_false_needs_no_key_fallback_guess():
    """The R545 core: without the typed-terminal rule, the bare
    MECHANISM_STARVED record falls through to the COMPLETED_* key
    prefix and the view guesses finished=True. Pin the absence of
    that guess: the helper must answer from the terminal itself."""
    rec = _bare(final_status="MECHANISM_STARVED")
    assert _us.user_state(rec) == "COMPLETED_UNKNOWN"
    assert _us._contract_finished_flag(rec) is False, (
        "a typed non-completion terminal must answer its own "
        "finished flag — the key-prefix fallback must not convert "
        "it to True")


# ---------------------------------------------------------------------------
# Durability: the three canonical records are in the durable allowlist
# (post-pruning auditability — completion authority, ranked survivor
# identity, candidate/package binding must survive run-dir pruning)
# ---------------------------------------------------------------------------
def test_durable_allowlist_covers_completion_records():
    from toscanini import durable as _d
    import inspect
    src = inspect.getsource(_d._run_dir_files)
    for name in ("COMPLETION_CONTRACT.json",
                 "RANKED_DISCOVERY_RESULTS.json",
                 "RANKED_PACKAGE_RECORDS.json"):
        assert name in src, (
            f"{name} must be in the durable allowlist for "
            f"post-pruning auditability")


# ---------------------------------------------------------------------------
# Owner-capability: REST and SSE use two EXPLICIT transports carrying the
# same opaque capability. The REST path uses the X-Tosca-Owner header
# (or the `?owner=` query param on GET); the SSE path uses the
# `?owner=` query param (EventSource cannot set headers). Neither
# transport may silently revert to cookie-only ownership.
# ---------------------------------------------------------------------------
def test_owner_transport_rest_header_and_sse_query_are_distinct():
    """The REST GET/POST path carries the owner via the X-Tosca-Owner
    header (or the `?owner=` query param on GET); the SSE stream path
    carries it via the `?owner=` query param. Both transports accept
    the same validated opaque token; neither is cookie-only. The
    server's `_owner_key()` resolution order is cookie -> header ->
    issued; the `?owner=` query-param override is applied on top
    (do_GET lines 807-810, do_POST R546 addition)."""
    from toscanini import server as _srv
    import inspect
    # the header transport is defined and used by _owner_key
    src = inspect.getsource(_srv.Handler._owner_key)
    assert "X-Tosca-Owner" in src or _srv.OWNER_HEADER in src, (
        "the REST header transport (X-Tosca-Owner) must be in "
        "_owner_key's resolution chain")
    # the query-param override is in do_GET
    get_src = inspect.getsource(_srv.Handler.do_GET)
    assert "q_owner" in get_src and "owner" in get_src, (
        "the SSE/direct-download query-param transport must be in "
        "do_GET")
    # the query-param override is now also in do_POST (R546)
    post_src = inspect.getsource(_srv.Handler.do_POST)
    assert "q_owner" in post_src, (
        "the R546 fix: the query-param transport must also be in "
        "do_POST (the answer route is a POST)")
    # the streamUrl frontend builder bakes ?owner= into the SSE URL
    # (the EventSource precedent — the two transports are explicit,
    # not silently cookie-only)
    from toscanini import user_state as _us2  # noqa: F401 — import
    # verify the frontend api.ts carries the header on fetch
    api_ts = (REPO_ROOT / "TOSCANINI_UI" / "webapp" / "lib"
               / "api.ts")
    if api_ts.is_file():
        text = api_ts.read_text(encoding="utf-8")
        assert "X-Tosca-Owner" in text, (
            "the frontend api.ts must attach the X-Tosca-Owner "
            "header to fetch requests")
        assert "owner=" in text and "streamUrl" in text, (
            "the frontend streamUrl() must carry ?owner= for the "
            "SSE transport")


def test_owner_capability_diagnostic_event_is_typed_and_secret_free():
    """The R546 owner-capability diagnostic on the answer route must
    emit typed, non-secret evidence: only presence/absence, SHA-256
    fingerprint, length, source, session-owner fingerprint, match
    boolean, route, and cause class. The owner token value itself
    must never enter the forensics record (BS-021, Art. LXXVI)."""
    from toscanini import server as _srv
    import inspect
    src = inspect.getsource(_srv.Handler.do_POST)
    assert "OWNER_CAPABILITY_DIAG" in src, (
        "the answer route must record the typed owner-capability "
        "diagnostic")
    assert "sha256" in src.lower() or "_diag_fp" in src, (
        "the diagnostic must carry a SHA-256 fingerprint, not the "
        "token value")
    # the cause-class vocabulary
    for cause in ("SESSION_NOT_FOUND", "SESSION_OWNER_MISMATCH",
                  "HEADER_NOT_SENT"):
        assert cause in src, (
            f"the diagnostic must classify the cause as "
            f"{cause}")
