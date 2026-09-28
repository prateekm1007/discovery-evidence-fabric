#!/usr/bin/env python3
"""R543 Step 5 — idempotent legacy-session backfill for the finished-state
authority (autocommand-driven; no manual production state manipulation).

For every COMPLETE session whose record lacks `completion_states`, derive
the durable answer from AUTHORITATIVE PERSISTED RUN ARTIFACTS ONLY and
persist it onto the session record via the store's own locked writer:

    source priority (first hit wins, never mixed):
      1. COMPLETION_CONTRACT.json in the run dir (the authority itself)
         -> completion_states(contract)
      2. the SAME live verifier over the run dir
         (completion_contract.verify_completion_contract, read-only)
         -> completion_states(record)
      3. NOTHING else. final_state.json's own completion_states field is
         deliberately NOT a source: pre-R544 engines wrote it from the
         retired optimistic rule, and laundering that rule into the
         durable record would create the second authority Art. IV/XXVIII
         forbid. final_state.json remains what it always was — an INPUT
         the verifier reads, never the answer.

Rules (the directive's Step-5 contract):
    source:    authoritative persisted run artifacts only (above)
    forbidden: legacy user-state prefix inference, manual JSON editing,
               guessed completion state, candidate borrowing
    scope:     --owner KEY processes only sessions visible to KEY
               (the store's own _session_access rule); --all processes
               every session and records the operator authorization.
               Neither flag -> fail closed (refuse).
    terminal:  status COMPLETE only. ERROR_*/INTERRUPTED/BLOCKED/RUNNING
               sessions may still be retried by the worker, whose
               run-tail refresh owns their completion_states — the
               backfill never races the worker (NOT_FINAL, not a failure).
    idempotent: a record already carrying completion_states with
               FINISHED_DISCOVERY is skipped (already_current); re-runs
               change nothing.
    fail-closed: insufficient evidence -> sessions_unresolved with a
               typed reason class; the record is left untouched.
    snapshot:  --snapshot (default on for the real store) takes the
               durable snapshot after the run and records the outcome;
               auto-skipped for --store overrides and --dry-run.

Report (machine-readable JSON, Art. XXIV):
    sessions_seen, sessions_out_of_scope, sessions_updated,
    sessions_already_current, sessions_unresolved,
    reasons_by_unresolved_class, per-session updates, snapshot outcome.

Exit code: 0 when the run completes (even with unresolved sessions —
unresolved is a reported outcome, never a crash); 2 on refusal
(no scope) or store errors. --dry-run changes nothing and reports
what WOULD change.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if sys.platform == "win32":  # pragma: no cover — platform-specific
    try:
        import fcntl  # noqa: F401
    except ImportError:
        import types as _types
        _fake_fcntl = _types.ModuleType("fcntl")
        _fake_fcntl.LOCK_SH = 1
        _fake_fcntl.LOCK_EX = 2
        _fake_fcntl.LOCK_NB = 4
        _fake_fcntl.LOCK_UN = 8
        _fake_fcntl.flock = lambda *a, **k: None
        sys.modules["fcntl"] = _fake_fcntl

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

from toscanini import sessions as _store  # noqa: E402
from discovery_fabric.engine import (  # noqa: E402
    completion_contract as _cc)


def _engine_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or "UNKNOWN"
    except Exception:  # noqa: BLE001
        return "UNKNOWN"


def _sha256_file(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return None


def _backfill_one(session: dict, dry_run: bool) -> dict:
    """Backfill one COMPLETE session. Returns a result record with
    `outcome` in {already_current, updated, unresolved}."""
    sid = session.get("session_id") or ""
    states = session.get("completion_states")
    if isinstance(states, dict) and "FINISHED_DISCOVERY" in states:
        return {"session_id": sid, "outcome": "already_current",
                "finished_discovery": bool(
                    states.get("FINISHED_DISCOVERY"))}
    if (session.get("status") or "") != "COMPLETE":
        return {"session_id": sid, "outcome": "unresolved",
                "reason_class": "NOT_FINAL",
                "reason": ("status=%r: the session may still complete; "
                           "the worker's run-tail refresh owns its "
                           "completion_states" % session.get("status"))}
    run_dir_raw = session.get("run_dir")
    run_dir = Path(run_dir_raw) if run_dir_raw else None
    if run_dir is None or not run_dir.exists():
        return {"session_id": sid, "outcome": "unresolved",
                "reason_class": "NO_RUN_DIR",
                "reason": ("run_dir unset or pruned; no authoritative "
                           "artifact is reachable — fail closed, never "
                           "guessed")}
    contract_path = run_dir / "COMPLETION_CONTRACT.json"
    source = None
    states = None
    contract_sha = None
    if contract_path.is_file():
        try:
            contract = json.loads(
                contract_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001 — corrupt file is no
            contract = None        # source at all (fail closed below)
            _corrupt = f"{type(exc).__name__}: {exc}"
        else:
            _corrupt = None
        if isinstance(contract, dict):
            states = _cc.completion_states(contract)
            source = "COMPLETION_CONTRACT.json"
            contract_sha = _sha256_file(contract_path)
        if states is None:
            return {"session_id": sid, "outcome": "unresolved",
                    "reason_class": "VERIFY_FAILED",
                    "reason": ("COMPLETION_CONTRACT.json unreadable "
                               "(%s); the retired final_state rule is "
                               "not an acceptable substitute"
                               % (_corrupt or "not a dict"))}
    else:
        try:
            live = _cc.verify_completion_contract(run_dir)
            states = _cc.completion_states(live)
            source = "live verify_completion_contract"
        except Exception as exc:  # noqa: BLE001 — fail closed
            return {"session_id": sid, "outcome": "unresolved",
                    "reason_class": "VERIFY_FAILED",
                    "reason": ("%s: %s (no contract file; live "
                               "verification failed)"
                               % (type(exc).__name__, exc))}
    if not isinstance(states, dict) or "FINISHED_DISCOVERY" not in states:
        return {"session_id": sid, "outcome": "unresolved",
                "reason_class": "VERIFY_FAILED",
                "reason": "verifier returned no FINISHED_DISCOVERY answer"}
    # the durable ranked equivalent (Step 4): copy the engine's own
    # ranked rows verbatim when the record lacks them.
    ranked_copied = False
    if session.get("ranked_results") is None:
        try:
            from toscanini import worker as _worker
            pkgs = _worker._ranked_package_set(run_dir)
        except Exception:  # noqa: BLE001 — states stand; ranks stay absent
            pkgs = []
        if pkgs:
            if not dry_run:
                _store.update_session(sid, ranked_results=pkgs)
            ranked_copied = True
    if not dry_run:
        _store.update_session(sid, completion_states=states)
    return {"session_id": sid, "outcome": "updated",
            "source": source,
            "contract_sha256": contract_sha,
            "finished_discovery": bool(states.get("FINISHED_DISCOVERY")),
            "typed_terminal_state": states.get("typed_terminal_state"),
            "ranked_results_copied": ranked_copied}


def main() -> int:
    ap = argparse.ArgumentParser()
    scope = ap.add_mutually_exclusive_group(required=True)
    scope.add_argument("--owner", default=None,
                       help="owner key: only sessions visible to it")
    scope.add_argument("--all", action="store_true",
                       help="operator-authorized full-store scope")
    ap.add_argument("--store", default=None,
                    help="override SESSIONS_PATH (hermetic runs)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--snapshot", action="store_true", default=True)
    ap.add_argument("--no-snapshot", dest="snapshot", action="store_false")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.store:
        _store.SESSIONS_PATH = Path(args.store)
    owner_scope = args.owner if args.owner else "OPERATOR_ALL"

    seen: list = []
    try:
        sessions = _store.list_sessions()
    except Exception as exc:  # noqa: BLE001 — store unreadable: refuse
        print(json.dumps({"fatal": "store unreadable: %s: %s"
                                   % (type(exc).__name__, exc)}))
        return 2
    for s in sessions:
        if args.owner and _store._session_access(s, args.owner) == "DENY":
            continue
        seen.append(s)

    results = [_backfill_one(s, args.dry_run) for s in seen]
    updated = [r for r in results if r["outcome"] == "updated"]
    current = [r for r in results if r["outcome"] == "already_current"]
    unresolved = [r for r in results if r["outcome"] == "unresolved"]
    reasons: dict = {}
    for r in unresolved:
        reasons.setdefault(r["reason_class"], []).append(r["session_id"])

    snapshot_info: dict = {"attempted": False}
    if args.snapshot and not args.dry_run and not args.store:
        snapshot_info["attempted"] = True
        try:
            from toscanini import durable as _durable
            out = _durable.snapshot("r543-backfill completion_states")
            snapshot_info["ok"] = bool(out.get("ok", True))
            snapshot_info["result"] = str(out)[:400]
        except Exception as exc:  # noqa: BLE001 — reported, not fatal
            snapshot_info["ok"] = False
            snapshot_info["error"] = f"{type(exc).__name__}: {exc}"
    elif args.dry_run or args.store:
        snapshot_info["reason"] = ("skipped: dry-run or hermetic store "
                                   "override (production autocommand "
                                   "passes neither)")

    report = {
        "schema": "R543_BACKFILL_REPORT/1.0.0",
        "engine_sha": _engine_sha(),
        "owner_scope": ("owner:%s" % args.owner) if args.owner
        else "OPERATOR_ALL (explicit --all authorization recorded)",
        "dry_run": bool(args.dry_run),
        "sessions_seen": len(seen),
        "sessions_out_of_scope": len(sessions) - len(seen),
        "sessions_updated": len(updated),
        "sessions_already_current": len(current),
        "sessions_unresolved": len(unresolved),
        "reasons_by_unresolved_class": reasons,
        "updates": updated,
        "already_current": [
            {"session_id": r["session_id"],
             "finished_discovery": r.get("finished_discovery")}
            for r in current],
        "unresolved": unresolved,
        "snapshot": snapshot_info,
    }
    out = Path(args.out) if args.out else (
        REPO_ROOT / "R543" / "BACKFILL_REPORT.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    # the report is ALWAYS written — a dry-run report is itself audit
    # evidence of what would change.
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False,
                              default=str), encoding="utf-8")
    print(json.dumps({
        "report": str(out),
        "sessions_seen": report["sessions_seen"],
        "sessions_updated": report["sessions_updated"],
        "sessions_already_current": report["sessions_already_current"],
        "sessions_unresolved": report["sessions_unresolved"],
        "reasons_by_unresolved_class": {
            k: len(v) for k, v in reasons.items()},
        "snapshot": snapshot_info,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
