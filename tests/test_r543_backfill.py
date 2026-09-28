"""R543 Step 5 — backfill autocommand hermetic tests.

The backfill (scripts/r543_backfill_completion_states.py) derives the
durable finished-state answer from AUTHORITATIVE RUN ARTIFACTS ONLY and
persists it via the store's own writer. These tests prove, against an
isolated store + isolated run dirs (production state never touched,
Art. IX):

  1. already-current records are skipped untouched (idempotency base)
  2. COMPLETION_CONTRACT.json present -> updated from the contract file
  3. contract absent, run dir present -> updated from the live verifier
  4. run dir gone -> unresolved NO_RUN_DIR, record untouched (fail closed)
  5. verifier raising -> unresolved VERIFY_FAILED, record untouched
  6. non-COMPLETE status -> unresolved NOT_FINAL (worker owns the future)
  7. --owner scoping excludes other owners' sessions (out of scope)
  8. second run changes nothing (full idempotency)
  9. ranked rows are copied verbatim with binding intact (Step 4 set)
 10. --dry-run changes nothing while reporting what would change
  11. no scope flag -> refusal (exit 2, fail closed)
  12. forbidden sources are never consulted: a final_state.json carrying
      the retired optimistic completion_states can NEVER by itself mark
      a session updated (only the contract file or the live verifier may)
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813 — exact on-disk name
        sys.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001
        pass
if sys.platform == "win32":
    try:
        import fcntl  # noqa: F401
    except ImportError:
        import types as _types
        _fake = _types.ModuleType("fcntl")
        _fake.LOCK_SH = 1
        _fake.LOCK_EX = 2
        _fake.LOCK_NB = 4
        _fake.LOCK_UN = 8
        _fake.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake

from toscanini import sessions as _store  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "r543_backfill_completion_states",
    str(REPO_ROOT / "scripts" / "r543_backfill_completion_states.py"))
_backfill = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_backfill)


def _write(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False,
                               default=str), encoding="utf-8")


def _run_dir(base: Path, name: str, *, contract=None,
             final_status: str = "MECHANISM_STARVED",
             ranked_rows: list | None = None) -> Path:
    rd = base / "ENGINE_RUNS" / name
    _write(rd / "final_state.json",
           {"run_id": name, "final_status": final_status})
    _write(rd / "run_manifest.json",
           {"run_id": name, "failed_stages": {}})
    if contract is not None:
        _write(rd / "COMPLETION_CONTRACT.json", contract)
    if ranked_rows is not None:
        _write(rd / "RANKED_DISCOVERY_RESULTS.json", {
            "schema": "RANKED_DISCOVERY_RESULT/2.0.0",
            "run_id": name, "final_status": final_status,
            "ranked_results": ranked_rows,
            "completion": {"FINISHED_DISCOVERY": True}})
    return rd


def _contract(finished: bool, terminal: str) -> dict:
    return {"schema": "COMPLETION_CONTRACT/1.0.0",
            "run_id": "x", "final_status": "MECHANISM_STARVED",
            "finished_discovery": finished,
            "typed_terminal_state": terminal,
            "preconditions": {"VALID_QUERY": True},
            "components": {"technology_package": {"complete": False}},
            "missing_components": ([] if finished else ["mechanisms"])}


@pytest.fixture
def iso_store(tmp_path, monkeypatch):
    monkeypatch.setattr(_store, "STORE_DIR", tmp_path)
    monkeypatch.setattr(_store, "SESSIONS_PATH",
                        tmp_path / "sessions.json")
    (tmp_path / "sessions.json").write_text(
        json.dumps({"sessions": []}), encoding="utf-8")
    return tmp_path


def _put(store_path: Path, record: dict) -> None:
    data = json.loads(store_path.read_text(encoding="utf-8"))
    data["sessions"].append(record)
    store_path.write_text(json.dumps(data), encoding="utf-8")


def _get(store_path: Path, sid: str) -> dict:
    data = json.loads(store_path.read_text(encoding="utf-8"))
    return next(s for s in data["sessions"]
                if s["session_id"] == sid)


def _rec(sid: str, run_dir: Path | None, status: str = "COMPLETE",
         final_status: str = "MECHANISM_STARVED",
         owner: str = "owner-1", **extra) -> dict:
    rec = {"session_id": sid, "status": status,
           "final_status": final_status, "owner_key": owner,
           "run_dir": str(run_dir) if run_dir else None}
    rec.update(extra)
    return rec


def _run_main(*argv: str):
    old = sys.argv
    sys.argv = ["r543_backfill_completion_states", *argv]
    try:
        rc = _backfill.main()
    finally:
        sys.argv = old
    return rc


def test_01_already_current_skipped_untouched(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_cur")
    _put(sp, _rec("ts_cur", rd, completion_states={
        "FINISHED_DISCOVERY": False,
        "typed_terminal_state": "MECHANISM_STARVED"}))
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["sessions_already_current"] == 1
    assert rep["sessions_updated"] == 0
    assert _get(sp, "ts_cur")["completion_states"][
        "typed_terminal_state"] == "MECHANISM_STARVED"


def test_02_contract_file_is_the_source(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_con",
                  contract=_contract(False, "MECHANISM_STARVED"))
    _put(sp, _rec("ts_con", rd))
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["sessions_updated"] == 1
    upd = rep["updates"][0]
    assert upd["source"] == "COMPLETION_CONTRACT.json"
    assert upd["contract_sha256"] is not None
    assert upd["finished_discovery"] is False
    got = _get(sp, "ts_con")["completion_states"]
    assert got["FINISHED_DISCOVERY"] is False
    assert got["typed_terminal_state"] == "MECHANISM_STARVED"


def test_03_live_verifier_when_no_contract_file(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_live")
    _put(sp, _rec("ts_live", rd))
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["sessions_updated"] == 1
    assert rep["updates"][0]["source"] == "live verify_completion_contract"
    got = _get(sp, "ts_live")["completion_states"]
    assert "FINISHED_DISCOVERY" in got


def test_04_pruned_run_dir_fails_closed(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    _put(sp, _rec("ts_gone", tmp_path / "ENGINE_RUNS" / "gone"))
    before = _get(sp, "ts_gone")
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["sessions_unresolved"] == 1
    assert rep["reasons_by_unresolved_class"] == {
        "NO_RUN_DIR": ["ts_gone"]}
    assert _get(sp, "ts_gone") == before  # untouched, never guessed


def test_05_verifier_failure_fails_closed(iso_store, tmp_path,
                                          monkeypatch):
    import discovery_fabric.engine.completion_contract as _cc
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_boom")
    _put(sp, _rec("ts_boom", rd))
    before = _get(sp, "ts_boom")

    def _raise(_rd):
        raise RuntimeError("synthetic verifier crash")
    monkeypatch.setattr(_cc, "verify_completion_contract", _raise)
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["reasons_by_unresolved_class"] == {
        "VERIFY_FAILED": ["ts_boom"]}
    assert _get(sp, "ts_boom") == before


def test_06_non_terminal_left_for_worker(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_run")
    _put(sp, _rec("ts_run", rd, status="RUNNING", final_status=""))
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["reasons_by_unresolved_class"] == {"NOT_FINAL": ["ts_run"]}
    assert "completion_states" not in _get(sp, "ts_run")


def test_07_owner_scope_excludes_others(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_mine",
                  contract=_contract(False, "MECHANISM_STARVED"))
    _put(sp, _rec("ts_mine", rd, owner="owner-1"))
    _put(sp, _rec("ts_theirs", rd, owner="owner-2"))
    rc = _run_main("--store", str(sp), "--owner", "owner-1",
                   "--no-snapshot", "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["sessions_seen"] == 1
    assert rep["sessions_out_of_scope"] == 1
    assert rep["sessions_updated"] == 1
    assert "completion_states" not in _get(sp, "ts_theirs")


def test_08_second_run_changes_nothing(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_twice",
                  contract=_contract(False, "MECHANISM_STARVED"))
    _put(sp, _rec("ts_twice", rd))
    args = ["--store", str(sp), "--all", "--no-snapshot",
            "--out", str(tmp_path / "rep.json")]
    assert _run_main(*args) == 0
    assert _run_main(*args) == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["sessions_updated"] == 0
    assert rep["sessions_already_current"] == 1


def test_09_ranked_rows_copied_verbatim_with_binding(iso_store, tmp_path):
    sp = iso_store / "sessions.json"

    def _row(rank, cid, sha):
        return {"rank": rank, "candidate_id": cid, "key": "primary",
                "admissible": True,
                "components": {
                    "package": {"complete": True, "zip_name": f"p_{cid}.zip",
                                "zip_sha256": sha, "candidate_id": cid}}}
    rows = [_row(1, "cand_a", "aa" * 32), _row(2, "cand_b", "bb" * 32)]
    rd = _run_dir(tmp_path, "ts_rank",
                  contract=_contract(True, "FINISHED_DISCOVERY"),
                  ranked_rows=rows)
    _put(sp, _rec("ts_rank", rd, final_status="OK"))
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["updates"][0]["ranked_results_copied"] is True
    got = _get(sp, "ts_rank")["ranked_results"]
    assert len(got) == 2
    for row in got:
        assert row["package"]["candidate_id"] == row["candidate_id"]
    assert {r["package"]["zip_sha256"] for r in got} == {"aa" * 32,
                                                         "bb" * 32}


def test_10_dry_run_changes_nothing(iso_store, tmp_path):
    sp = iso_store / "sessions.json"
    rd = _run_dir(tmp_path, "ts_dry",
                  contract=_contract(False, "MECHANISM_STARVED"))
    _put(sp, _rec("ts_dry", rd))
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--dry-run", "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    rep = json.loads((tmp_path / "rep.json").read_text())
    assert rep["dry_run"] is True
    assert rep["sessions_updated"] == 1  # would change
    assert "completion_states" not in _get(sp, "ts_dry")  # did not


def test_11_no_scope_refuses():
    with pytest.raises(SystemExit) as exc:
        _run_main("--no-snapshot")
    assert exc.value.code == 2


def test_12_retired_final_state_rule_never_marks_updated(iso_store,
                                                         tmp_path):
    """The forbidden-source pin: a final_state.json carrying the
    retired optimistic completion_states (FINISHED_DISCOVERY=true on a
    starved run with no contract file and no ranked artifacts) must
    NEVER by itself produce an update. Only the contract file or the
    live verifier — which re-measures and will report false here —
    may answer."""
    sp = iso_store / "sessions.json"
    rd = tmp_path / "ENGINE_RUNS" / "ts_retired"
    rd.mkdir(parents=True)
    (rd / "final_state.json").write_text(json.dumps({
        "run_id": "ts_retired", "final_status": "MECHANISM_STARVED",
        "completion_states": {"PIPELINE_COMPLETED": True,
                              "DISCOVERY_COMPLETED": True,
                              "TECHNOLOGY_PACKAGE_COMPLETED": True,
                              "FINISHED_DISCOVERY": True}}),
        encoding="utf-8")
    (rd / "run_manifest.json").write_text(json.dumps(
        {"run_id": "ts_retired", "failed_stages": {}}), encoding="utf-8")
    _put(sp, _rec("ts_retired", rd))
    rc = _run_main("--store", str(sp), "--all", "--no-snapshot",
                   "--out", str(tmp_path / "rep.json"))
    assert rc == 0
    got = _get(sp, "ts_retired").get("completion_states") or {}
    # the live verifier re-measured: a starved run with no survivors
    # and no packages cannot be finished, whatever the retired field
    # claimed.
    assert got.get("FINISHED_DISCOVERY") is False
