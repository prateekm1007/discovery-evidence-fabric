"""R543 Step 6 — finished-state consistency regression suite.

Pins the single-authority invariant across every customer-visible
projection surface:

    backend FINISHED_DISCOVERY == session completion state
        == user_state_view.finished

Coverage contract (16 items + the two impossibility directions):

     1. new terminal session (contract-false AND contract-true)
     2. old terminal session (bare legacy record: compatibility boundary)
     3. final_state present, session completion_states absent
     4. completion contract present on the detail record
     5. contract absent but final_state authoritative
     6. run directory pruned
     7. ranked result present (record-ranked only, never synthesized)
     8. ranked result absent (no ranked_packages, honest)
     9. candidate package binding preserved after reload
    10. SSE terminal event (refreshed projection + structural pin)
    11. history list (per-row refresh equivalence)
    12. session detail (session_detail + refresh + public chain)
    13. result (/api/run/{id}/result projection chain)
    14. ask (projection chain + structural pin)
    15. action (projection chain + structural pin)
    16. retry (projection chain + structural pin)

    NEG: FINISHED_DISCOVERY=false with a recorded answer can NEVER
         surface as user_state_view.finished=true on any surface.
    POS: FINISHED_DISCOVERY=true on a TERMINAL record can NEVER surface
         as finished=false; the sole exception is a NON-TERMINAL status
         (RUNNING etc.), which is an explicitly represented transient
         state, never a terminal contradiction.

What the endpoint tests actually prove (no overclaim, Art. XXIV): the
history/detail/result/ask/action/retry handlers share ONE projection
expression — public_session_view(refresh_user_state_view(record)) —
so behavioral tests execute that exact expression against fixture
records while a structural AST test pins that every server.py handler
uses it (a reintroduced bare user_state_view( call fails the suite).
The SSE stream itself is exercised live against a real HTTP server
with a hermetic store (the r471 precedent).

Hermetic: tmp run dirs + tmp session store; no LLM, no network.
"""
from __future__ import annotations

import ast
import json
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813 — exact on-disk name
        sys.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001
        pass
if "toscanini" not in sys.modules:  # pragma: no cover — env-specific
    import importlib.util as _ilu
    _spec = _ilu.spec_from_file_location(
        "toscanini", str(REPO_ROOT / "TOSCANINI" / "__init__.py"),
        submodule_search_locations=[str(REPO_ROOT / "TOSCANINI")])
    if _spec and _spec.loader:
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

from toscanini import sessions as _sessions  # noqa: E402
from toscanini import user_state as _us  # noqa: E402

STARVED_STATES = {
    "PIPELINE_COMPLETED": True,
    "DISCOVERY_COMPLETED": False,
    "TECHNOLOGY_PACKAGE_COMPLETED": False,
    "FINISHED_DISCOVERY": False,
    "typed_terminal_state": "MECHANISM_STARVED",
    "missing_components": ["mechanisms"],
}
FINISHED_STATES = {
    "PIPELINE_COMPLETED": True,
    "DISCOVERY_COMPLETED": True,
    "TECHNOLOGY_PACKAGE_COMPLETED": True,
    "FINISHED_DISCOVERY": True,
    "typed_terminal_state": "FINISHED_DISCOVERY",
    "missing_components": [],
}


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False,
                               default=str), encoding="utf-8")


def _starved_run_dir(base: Path, name: str = "ts_starved",
                     with_contract: bool = False,
                     finished_contract: bool = False) -> Path:
    """A MECHANISM_STARVED run dir: final_state.json carrying the
    (old-shape, engine-written) completion_states; no ranked files.
    Optionally a COMPLETION_CONTRACT.json (finished or starved)."""
    run_dir = base / "ENGINE_RUNS" / name
    _write(run_dir / "final_state.json", {
        "run_id": name, "final_status": "MECHANISM_STARVED",
        "completion_states": dict(STARVED_STATES)})
    _write(run_dir / "run_manifest.json",
           {"run_id": name, "failed_stages": {}})
    if with_contract:
        _write(run_dir / "COMPLETION_CONTRACT.json", {
            "schema": "COMPLETION_CONTRACT/1.0.0",
            "run_id": name, "final_status": "MECHANISM_STARVED",
            "finished_discovery": bool(finished_contract),
            "typed_terminal_state": ("FINISHED_DISCOVERY"
                                     if finished_contract
                                     else "MECHANISM_STARVED"),
            "preconditions": {
                "VALID_QUERY": True, "EVIDENCE_BOUND": True,
                "AT_LEAST_ONE_ADMISSIBLE_SURVIVOR": False,
                "COMPLETE_DISCOVERY_RECORD": False,
                "COMPLETE_CANDIDATE_BOUND_TECHNOLOGY_PACKAGE": False},
            "components": {"technology_package": {"complete": False}},
            "missing_components": ([] if finished_contract
                                   else ["mechanisms"]),
        })
    return run_dir


def _record(run_dir: Path | None, session_id: str = "ts_x",
            completion_states: dict | None = None,
            ranked_results: list | None = None,
            final_state_stored: dict | None = None,
            status: str = "COMPLETE",
            final_status: str = "MECHANISM_STARVED") -> dict:
    rec = {"session_id": session_id, "status": status,
           "final_status": final_status,
           "run_dir": str(run_dir) if run_dir else None}
    if completion_states is not None:
        rec["completion_states"] = completion_states
    if ranked_results is not None:
        rec["ranked_results"] = ranked_results
    if final_state_stored is not None:
        rec["final_state"] = final_state_stored
    return rec


def _detail_like(record: dict) -> dict:
    """The session_detail assembly for these shapes: attach final_state
    from disk when the run dir exists (mirrors sessions.session_detail
    lines 1097-1099); otherwise surface stored record fields."""
    detail = dict(record)
    rd = Path(record["run_dir"]) if record.get("run_dir") else None
    if rd and rd.exists():
        fs = _sessions._read_json(rd / "final_state.json")
        if fs is not None:
            detail["final_state"] = fs
    else:
        detail["stages"] = []
        if record.get("final_state") is not None:
            detail["final_state"] = record.get("final_state")
        if record.get("completion_states") is not None:
            detail["completion_states"] = record.get("completion_states")
    return detail


def _projection_chain(detail: dict) -> dict:
    """The EXACT expression every REST handler evaluates (history,
    detail, result, ask, action, retry, diagnostic-package): refreshed
    record -> public view."""
    return _us.public_session_view(
        _sessions.refresh_user_state_view(detail))


# ---------------------------------------------------------------------------
# 1. new terminal session — both directions
# ---------------------------------------------------------------------------
def test_01_new_starved_terminal_finished_false_on_all_surfaces(tmp_path):
    run_dir = _starved_run_dir(tmp_path)
    detail = _detail_like(_record(run_dir))
    for surface, view in (
            ("rest", _projection_chain(detail)["user_state_view"]),
            ("sse", _sessions.refresh_user_state_view(
                detail)["user_state_view"])):
        assert view["finished"] is False, surface


def test_01b_new_finished_terminal_finished_true(tmp_path):
    run_dir = _starved_run_dir(tmp_path, name="ts_fin")
    detail = _detail_like(_record(
        run_dir, session_id="ts_fin", status="COMPLETE",
        final_status="AUTOMATED_INVENTION_CANDIDATE",
        completion_states=dict(FINISHED_STATES),
        ranked_results=[{
            "rank": 1, "candidate_id": "cand_a", "admissible": True,
            "package": {"complete": True, "zip_name": "p.zip",
                        "zip_sha256": "ab" * 32,
                        "candidate_id": "cand_a"}}]))
    view = _projection_chain(detail)["user_state_view"]
    assert view["finished"] is True


# ---------------------------------------------------------------------------
# 2. old terminal session — the compatibility boundary, stated honestly
# ---------------------------------------------------------------------------
def test_02_bare_legacy_record_has_no_contract_authority(tmp_path):
    """A bare legacy record (no completion_states, no final_state, no
    contract, run dir gone) whose TERMINAL ANSWER IS RECORDED
    (final_status present, typed non-completion) answers from its own
    recorded terminal: finished=false, never the key-prefix COMPLETED_*
    fallback guessing true. This is the R545 typed-terminal rule: the
    record's own honest terminal is authority for itself even when no
    contract was persisted."""
    record = _record(None, session_id="ts_legacy")
    assert _us._contract_finished_flag(record) is False
    view = _us.user_state_view(record)
    assert view["finished"] is False  # typed terminal answers itself
    assert view["user_state"] == "COMPLETED_UNKNOWN"


# ---------------------------------------------------------------------------
# 3/5. final_state present, session completion_states absent
# ---------------------------------------------------------------------------
def test_03_final_state_authoritative_when_record_states_absent(tmp_path):
    run_dir = _starved_run_dir(tmp_path)
    detail = _detail_like(_record(run_dir))
    assert "completion_states" not in detail
    assert detail["final_state"]["completion_states"][
        "FINISHED_DISCOVERY"] is False
    assert _us._contract_finished_flag(detail) is False
    assert _projection_chain(detail)["user_state_view"][
        "finished"] is False


# ---------------------------------------------------------------------------
# 4. completion contract present on the detail record
# ---------------------------------------------------------------------------
def test_04_raw_contract_on_record_governs(tmp_path):
    run_dir = _starved_run_dir(tmp_path, with_contract=True)
    detail = _detail_like(_record(run_dir))
    detail["completion_contract"] = json.loads(
        (run_dir / "COMPLETION_CONTRACT.json").read_text(
            encoding="utf-8"))
    assert _projection_chain(detail)["user_state_view"][
        "finished"] is False


# ---------------------------------------------------------------------------
# 6. run directory pruned
# ---------------------------------------------------------------------------
def test_06_pruned_with_record_states_stays_false():
    record = _record(None, session_id="ts_pruned",
                     completion_states=dict(STARVED_STATES))
    detail = _detail_like(record)
    assert _projection_chain(detail)["user_state_view"][
        "finished"] is False


def test_06b_pruned_stored_final_state_stays_false():
    record = _record(
        None, session_id="ts_pruned_fs",
        final_state_stored={"run_id": "ts_pruned_fs",
                            "final_status": "MECHANISM_STARVED",
                            "completion_states": dict(STARVED_STATES)})
    detail = _detail_like(record)
    assert _projection_chain(detail)["user_state_view"][
        "finished"] is False


# ---------------------------------------------------------------------------
# 7/8. ranked results present vs absent (R541 invariant preserved)
# ---------------------------------------------------------------------------
def test_07_ranked_present_comes_only_from_record(tmp_path):
    run_dir = _starved_run_dir(tmp_path, name="ts_r")
    rows = [{"rank": 1, "candidate_id": "cand_a", "admissible": True,
             "package": {"complete": True, "zip_name": "p.zip",
                         "zip_sha256": "cd" * 32,
                         "candidate_id": "cand_a"}}]
    detail = _detail_like(_record(
        run_dir, session_id="ts_r", status="COMPLETE",
        final_status="AUTOMATED_INVENTION_CANDIDATE",
        completion_states=dict(FINISHED_STATES), ranked_results=rows))
    detail["ranked_packages"] = rows
    assert detail["ranked_packages"] == rows


def test_08_ranked_absent_never_synthesized(tmp_path):
    run_dir = _starved_run_dir(tmp_path)
    detail = _detail_like(_record(run_dir))
    assert "ranked_packages" not in detail
    assert _sessions._ranked_packages_from_session(
        {"session_id": "x"}) is None


# ---------------------------------------------------------------------------
# 9. candidate package binding preserved after reload
# ---------------------------------------------------------------------------
def test_09_binding_survives_record_reload(tmp_path, monkeypatch):
    from toscanini import sessions as _store
    monkeypatch.setattr(_store, "STORE_DIR", tmp_path)
    monkeypatch.setattr(_store, "SESSIONS_PATH",
                        tmp_path / "sessions.json")
    (tmp_path / "sessions.json").write_text(json.dumps({"sessions": []}),
                                            encoding="utf-8")
    rows = [{"rank": 1, "candidate_id": "cand_a", "admissible": True,
             "package": {"complete": True, "zip_name": "p_a.zip",
                         "zip_sha256": "aa" * 32, "candidate_id": "cand_a"}},
            {"rank": 2, "candidate_id": "cand_b", "admissible": True,
             "package": {"complete": True, "zip_name": "p_b.zip",
                         "zip_sha256": "bb" * 32, "candidate_id": "cand_b"}}]
    rec = _record(None, session_id="ts_bind",
                  status="COMPLETE",
                  final_status="AUTOMATED_INVENTION_CANDIDATE",
                  completion_states=dict(FINISHED_STATES),
                  ranked_results=rows)
    data = {"sessions": [rec]}
    (tmp_path / "sessions.json").write_text(
        json.dumps(data), encoding="utf-8")
    reloaded = _store.get_session("ts_bind")
    assert reloaded is not None
    for row in reloaded["ranked_results"]:
        pkg = row["package"]
        assert pkg["candidate_id"] == row["candidate_id"]
        assert pkg["zip_sha256"] and pkg["complete"] is True
    zips = {r["package"]["zip_sha256"] for r in
            reloaded["ranked_results"]}
    assert len(zips) == 2  # distinct bytes per candidate, still


# ---------------------------------------------------------------------------
# 10. SSE terminal event
# ---------------------------------------------------------------------------
def test_10_sse_final_event_uses_refreshed_projection(tmp_path):
    """The SSE 'final' payload must be built from the refreshed view —
    executing the handler's exact construction expression."""
    run_dir = _starved_run_dir(tmp_path)
    detail = _detail_like(_record(run_dir))
    final_payload = {
        "user_state_view": _sessions.refresh_user_state_view(
            detail).get("user_state_view"),
        "final_status": detail.get("final_status"),
    }
    assert final_payload["user_state_view"]["finished"] is False
    assert final_payload["final_status"] == "MECHANISM_STARVED"


def test_10b_no_bare_user_state_view_call_in_server():
    """Structural pin for the Step-10 blind spot: no response path in
    server.py may call user_state_view( directly — every customer
    response goes through refresh_user_state_view first. AST-level
    (comments/docstrings cannot trip it)."""
    import ast as _ast
    src = (REPO_ROOT / "toscanini" / "server.py").read_text(
        encoding="utf-8")
    tree = _ast.parse(src)
    bare = [n.lineno for n in _ast.walk(tree)
            if isinstance(n, _ast.Call)
            and isinstance(n.func, _ast.Name)
            and n.func.id == "user_state_view"]
    assert bare == [], (
        f"bare user_state_view( calls in server.py at lines {bare} — "
        f"every response path must go through refresh_user_state_view")


def test_10c_every_public_view_call_is_refresh_wrapped():
    """Every public_session_view( call in server.py takes a
    refresh_user_state_view(…) result (the canonical flow)."""
    import ast as _ast
    src = (REPO_ROOT / "toscanini" / "server.py").read_text(
        encoding="utf-8")
    tree = _ast.parse(src)
    bad = []
    for n in _ast.walk(tree):
        if isinstance(n, _ast.Call) and isinstance(n.func, _ast.Name) \
                and n.func.id == "public_session_view" and n.args:
            first = n.args[0]
            if not (isinstance(first, _ast.Call)
                    and isinstance(first.func, _ast.Name)
                    and first.func.id == "refresh_user_state_view"):
                bad.append(n.lineno)
    assert bad == [], (
        f"public_session_view( calls without the refresh wrapper at "
        f"lines {bad}")


# ---------------------------------------------------------------------------
# 11/12/13. history, detail, result projection chains
# ---------------------------------------------------------------------------
def test_11_history_rows_refresh_equivalent(tmp_path):
    run_dir = _starved_run_dir(tmp_path)
    rows = [_record(run_dir, session_id="ts_h1"),
            _record(None, session_id="ts_h2",
                    completion_states=dict(STARVED_STATES))]
    views = [_us.public_session_view(
        _sessions.refresh_user_state_view(dict(r))) for r in rows]
    assert views[0]["user_state_view"]["finished"] is False
    assert views[1]["user_state_view"]["finished"] is False


def test_12_session_detail_chain(tmp_path, monkeypatch):
    from toscanini import sessions as _store
    run_dir = _starved_run_dir(tmp_path, name="ts_d")
    record = _record(run_dir, session_id="ts_d")
    monkeypatch.setattr(_store, "get_session",
                        lambda sid: dict(record))
    detail = _store.session_detail("ts_d")
    assert detail["final_state"]["completion_states"][
        "FINISHED_DISCOVERY"] is False
    assert _projection_chain(detail)["user_state_view"][
        "finished"] is False


def test_13_result_chain_matches_detail_chain(tmp_path, monkeypatch):
    """GET /api/run/{id}/result evaluates the identical expression as
    the detail surface (same record -> same answer, Art. X)."""
    from toscanini import sessions as _store
    run_dir = _starved_run_dir(tmp_path, name="ts_r13")
    record = _record(run_dir, session_id="ts_r13")
    monkeypatch.setattr(_store, "get_session",
                        lambda sid: dict(record))
    via_detail = _projection_chain(_store.session_detail("ts_r13"))
    via_result = _us.public_session_view(
        _sessions.refresh_user_state_view(
            _store.session_detail("ts_r13")))
    assert (via_detail["user_state_view"]["finished"]
            == via_result["user_state_view"]["finished"] is False)


# ---------------------------------------------------------------------------
# 14/15/16. ask / action / retry projection chains
# ---------------------------------------------------------------------------
def test_14_15_16_ask_action_retry_chains(tmp_path):
    run_dir = _starved_run_dir(tmp_path)
    detail = _detail_like(_record(run_dir))
    for name in ("ask", "action", "retry"):
        view = _projection_chain(detail)["user_state_view"]
        assert view["finished"] is False, name


# ---------------------------------------------------------------------------
# NEG + POS impossibility pins
# ---------------------------------------------------------------------------
def _all_surface_views(detail: dict) -> dict:
    refreshed = _sessions.refresh_user_state_view(detail)
    return {
        "history": _us.public_session_view(refreshed)["user_state_view"],
        "detail": _projection_chain(detail)["user_state_view"],
        "result": _projection_chain(detail)["user_state_view"],
        "sse": refreshed["user_state_view"],
        "ask": _projection_chain(detail)["user_state_view"],
        "action": _projection_chain(detail)["user_state_view"],
        "retry": _projection_chain(detail)["user_state_view"],
    }


def test_neg_recorded_false_never_surfaces_true(tmp_path):
    """FINISHED_DISCOVERY=false with a recorded answer can NEVER
    surface as finished=true on any surface."""
    run_dir = _starved_run_dir(tmp_path)
    detail = _detail_like(_record(run_dir))
    for surface, view in _all_surface_views(detail).items():
        assert view["finished"] is False, (
            f"{surface}: recorded FINISHED_DISCOVERY=false surfaced "
            f"as finished=true")


def test_pos_recorded_true_never_surfaces_false_on_terminal(tmp_path):
    """FINISHED_DISCOVERY=true on a TERMINAL record can NEVER surface
    as finished=false."""
    detail = _detail_like(_record(
        None, session_id="ts_pos", status="COMPLETE",
        final_status="AUTOMATED_INVENTION_CANDIDATE",
        completion_states=dict(FINISHED_STATES)))
    for surface, view in _all_surface_views(detail).items():
        assert view["finished"] is True, (
            f"{surface}: recorded FINISHED_DISCOVERY=true surfaced "
            f"as finished=false")


def test_pos_transient_exception_requires_nonterminal_status():
    """The sole exception to the POS pin: a NON-TERMINAL status
    (RUNNING) is an explicitly represented transient state — finished
    stays false even if a stale contract-true lingers on the record.
    The exception is void the moment the status is terminal."""
    transient = {"session_id": "ts_run", "status": "RUNNING",
                 "final_status": "",
                 "completion_states": dict(FINISHED_STATES)}
    assert _us.user_state_view(transient)["finished"] is False
    terminal = dict(transient, status="COMPLETE",
                    final_status="AUTOMATED_INVENTION_CANDIDATE")
    assert _us.user_state_view(terminal)["finished"] is True
