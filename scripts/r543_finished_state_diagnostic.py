#!/usr/bin/env python3
"""R543 Step 1 — finished-state diagnostic for production session
ts_d07a006dde9c (and its twin ts_c31658bbe767).

Reproduces, with the repository's OWN response-construction code, the
exact customer-response build for a MECHANISM_STARVED terminal whose
probe showed::

    final_state.completion_states.FINISHED_DISCOVERY = false
    user_state_view.finished = true

and records, at the moment the customer response is constructed::

    engine SHA, request path, run_dir value, run_dir exists,
    final_state file exists, final_state JSON parse success,
    final_state.completion_states, session.completion_states,
    completion_contract presence, _contract_finished_flag result,
    user_state_view.finished

for BOTH response paths:

    Path A (REST: history / detail / result / ask / action / retry):
        session_detail-assembly -> refresh_user_state_view
        -> public_session_view
    Path B (SSE terminal event):
        session_detail-assembly -> user_state_view (direct)

The run dir is reconstructed to the production-at-probe-time state
established by the stored probe artifact: final_state.json present
carrying the probed completion_states payload, NO
COMPLETION_CONTRACT.json, NO ranked-result files (the starved run
left none). A --variant=pruned mode covers the post-deploy-pruning
shape (run dir absent, bare legacy record).

Output: machine-readable JSON (Art. XXIV: the artifact, not prose,
is the evidence). Exit code is ALWAYS 0 — this is a diagnostic, not
a gate; the artifact's "reproduced" field carries the verdict.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# sessions.py does a bare `import fcntl` (POSIX-only). Mirror the
# tests/conftest.py shim so the diagnostic runs on Windows with the
# same honest no-op flock the hermetic suites use.
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

# The toscanini package lives under the lowercase index name; the
# working tree carries the uppercase dir (same content). Alias it the
# way the test suite does so `from toscanini...` resolves.
if "toscanini" not in sys.modules:
    try:
        import TOSCANINI as _T  # noqa: N813 — exact on-disk name
        sys.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001 — fall through to file-location
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

from toscanini import sessions as _sessions  # noqa: E402
from toscanini import user_state as _us  # noqa: E402

# The probed production completion_states payload for ts_d07a006dde9c
# (R542/R543_PROD_FINISHED_FLAG_PROOF_503de62.json, verbatim).
PROBED_COMPLETION_STATES = {
    "PIPELINE_COMPLETED": True,
    "DISCOVERY_COMPLETED": False,
    "TECHNOLOGY_PACKAGE_COMPLETED": False,
    "FINISHED_DISCOVERY": False,
    "invariant": ("FINISHED_DISCOVERY = ADMISSIBLE_RANKED_SURVIVOR + "
                  "COMPLETE_RESULT_RECORD + TECHNOLOGY_PACKAGE; never "
                  "EXECUTION_COMPLETED or SOME_COMPONENTS_PRODUCED alone"),
    "final_status": "UNKNOWN",
}


def _engine_sha() -> str:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=15)
        return out.stdout.strip() or "UNKNOWN"
    except Exception:  # noqa: BLE001 — diagnostic must not crash
        return "UNKNOWN"


def _build_run_dir(base: Path, with_final_state: bool) -> Path:
    """Mirror the production run dir AT PROBE TIME: final_state.json
    present (carrying the probed completion_states), no contract file,
    no ranked-result files — the starved run left none."""
    run_dir = base / "ENGINE_RUNS" / "ts_d07a006dde9c"
    run_dir.mkdir(parents=True, exist_ok=True)
    if with_final_state:
        (run_dir / "final_state.json").write_text(json.dumps({
            "run_id": "ts_d07a006dde9c",
            "final_status": "MECHANISM_STARVED",
            "epistemic_state": "OBSERVED",
            "reason": "fewer than 2 materially distinct mechanisms",
            "completion_states": dict(PROBED_COMPLETION_STATES),
        }), encoding="utf-8")
        (run_dir / "run_manifest.json").write_text(json.dumps({
            "run_id": "ts_d07a006dde9c",
            "failed_stages": {},
        }), encoding="utf-8")
    return run_dir


def _legacy_record(run_dir: Path | None,
                   stored_final_state: bool = False) -> dict:
    """The stored production session record shape established by the
    probe: COMPLETE/MECHANISM_STARVED, NO ranked_results, NO
    completion_states, NO completion_contract
    (record_completion_states was null). The production response DID
    carry final_state.completion_states, so one variant stores the
    engine's final_state payload on the record itself (the R543-1f
    fallback shape) to test whether the in-tree chain honors it."""
    rec = {
        "session_id": "ts_d07a006dde9c",
        "status": "COMPLETE",
        "final_status": "MECHANISM_STARVED",
        "run_dir": str(run_dir) if run_dir else None,
    }
    if stored_final_state:
        rec["final_state"] = {
            "run_id": "ts_d07a006dde9c",
            "final_status": "MECHANISM_STARVED",
            "completion_states": dict(PROBED_COMPLETION_STATES),
        }
    return rec


def _assemble_detail_like_session_detail(record: dict) -> dict:
    """Assemble the `detail` dict EXACTLY the way
    sessions.session_detail does for this record shape (run-dir-present
    branch: attach final_state.json; no ranked files on disk so no
    ranked/completion_states/contract keys)."""
    detail = dict(record)
    run_dir = Path(record["run_dir"]) if record.get("run_dir") else None
    detail["_diag_run_dir_value"] = record.get("run_dir")
    detail["_diag_run_dir_exists"] = bool(run_dir and run_dir.exists())
    if run_dir and run_dir.exists():
        fs = _sessions._read_json(run_dir / "final_state.json")
        detail["_diag_final_state_file_exists"] = (
            (run_dir / "final_state.json").is_file())
        detail["_diag_final_state_parse_ok"] = isinstance(fs, dict)
        if fs is not None:
            detail["final_state"] = fs
    else:
        detail["_diag_final_state_file_exists"] = False
        detail["_diag_final_state_parse_ok"] = False
    return detail


def _run_case(variant: str, proof: dict | None) -> dict:
    tmp = Path(tempfile.mkdtemp(prefix="r543_diag_"))
    pruned = variant in ("pruned", "pruned-stored-final-state")
    with_final_state = variant in ("run-dir-present",)
    run_dir = _build_run_dir(tmp, with_final_state) \
        if not pruned else None
    record = _legacy_record(
        run_dir,
        stored_final_state=(variant == "pruned-stored-final-state"))
    # production probe established the record carries no completion
    # contract fields (record_completion_states was null)
    record_completion_states = record.get("completion_states")
    detail = _assemble_detail_like_session_detail(record)

    fs = detail.get("final_state")
    fs_states = (fs or {}).get("completion_states") \
        if isinstance(fs, dict) else None

    # Path A — every REST surface.
    refreshed = _sessions.refresh_user_state_view(detail)
    pub = _us.public_session_view(refreshed)
    finished_a = (pub.get("user_state_view") or {}).get("finished")
    # Path B — the SSE terminal event (direct user_state_view call).
    sse_view = _us.user_state_view(detail)
    finished_b = sse_view.get("finished")

    flag = _us._contract_finished_flag(detail)
    key = _us.user_state(detail)
    return {
        "variant": variant,
        "engine_sha": _engine_sha(),
        "request_paths": {
            "path_a_rest": ("/api/sessions/{id}, /api/run/{id}/result, "
                            "history, ask, action, retry"),
            "path_b_sse": "SSE terminal 'final' event",
        },
        "run_dir_value": detail.get("_diag_run_dir_value"),
        "run_dir_exists": detail.get("_diag_run_dir_exists"),
        "final_state_file_exists":
            detail.get("_diag_final_state_file_exists"),
        "final_state_parse_ok":
            detail.get("_diag_final_state_parse_ok"),
        "final_state_completion_states": fs_states,
        "session_completion_states": record_completion_states,
        "completion_contract_present":
            isinstance(detail.get("completion_contract"), dict),
        "contract_finished_flag_result": flag,
        "user_state_key": key,
        "user_state_view_finished_path_a_rest": finished_a,
        "user_state_view_finished_path_b_sse": finished_b,
        "expected_finished": False,
        "path_a_consistent": finished_a is False,
        "path_b_consistent": finished_b is False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--session-id", default="ts_d07a006dde9c")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    cases = [_run_case("run-dir-present", None),
             _run_case("pruned", None),
             _run_case("pruned-stored-final-state", None)]
    reproduced = any(
        not c["path_a_consistent"] or not c["path_b_consistent"]
        for c in cases)
    # the mechanism verdict: WHY false became true, in the code's own
    # terms — or "not reproduced in-tree" with the evidence attached.
    mechanisms = []
    for c in cases:
        if not c["path_a_consistent"] or not c["path_b_consistent"]:
            if c["contract_finished_flag_result"] is None:
                mechanisms.append(
                    f"{c['variant']}: _contract_finished_flag returned "
                    f"None (no completion_states, no final_state with "
                    f"completion_states, no completion_contract on the "
                    f"response-construction record) so user_state_view "
                    f"fell back to the COMPLETED_* key-prefix rule -> "
                    f"finished=true")
            else:
                mechanisms.append(
                    f"{c['variant']}: flag={c['contract_finished_flag_result']} "
                    f"yet finished differs by path "
                    f"(rest={c['user_state_view_finished_path_a_rest']}, "
                    f"sse={c['user_state_view_finished_path_b_sse']})")
    artifact = {
        "schema": "R543_FINISHED_STATE_DIAGNOSTIC/1.0.0",
        "session_id": args.session_id,
        "production_probe_reference": (
            "R542/R543_PROD_FINISHED_FLAG_PROOF_503de62.json: "
            "record_completion_states=null, "
            "final_state.completion_states.FINISHED_DISCOVERY=false, "
            "user_state_view.finished=true"),
        "cases": cases,
        "reproduced_in_tree": bool(reproduced),
        "mechanism": mechanisms or [
            "not reproduced in-tree: every response-construction path "
            "returns finished=false for the reconstructed production "
            "shape; the live true predates the in-tree authority chain "
            "or came through an undeployed code path — see mechanism "
            "notes in the round record"],
    }
    out = Path(args.out) if args.out else (
        REPO_ROOT / "R543" /
        f"DIAGNOSTIC_{args.session_id}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False,
                              default=str), encoding="utf-8")
    print(json.dumps({
        "artifact": str(out),
        "reproduced_in_tree": artifact["reproduced_in_tree"],
        "cases": [{k: c[k] for k in (
            "variant", "run_dir_exists", "final_state_file_exists",
            "contract_finished_flag_result",
            "user_state_view_finished_path_a_rest",
            "user_state_view_finished_path_b_sse",
            "path_a_consistent", "path_b_consistent")} for c in cases],
        "mechanism": artifact["mechanism"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
