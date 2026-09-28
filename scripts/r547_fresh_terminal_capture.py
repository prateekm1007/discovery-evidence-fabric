"""R547 — fresh terminal capture + serving-path reconcile (directive
item 2, the decisive invariant).

Captures, from ONE fresh production run on the EXACT deployed SHA,
every field the directive names:

    raw session record
    raw final_state
    completion_states
    completion_contract
    user_state()
    _contract_finished_flag()
    user_state_view()
    GET /api/run/{id}/result payload
    SSE terminal payload
    run_state payload

All tied to the exact production SHA. The decisive invariant it
checks:

    COMPLETE
    + final_status=MECHANISM_STARVED
    + completion FINISHED_DISCOVERY=false
    --------------------------------------
    user_state_view.finished MUST = false

If the served record still answers finished=true while the committed
source answers false, this instrument RECOMPUTES the view locally
from the served record with the committed source and records both
answers side by side — so the contradiction (if any) is attributed to
the serving path, not assumed away.

Read-only: no session mutation, no deploy, no state repair.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

if "toscanini" not in sys.modules:
    import importlib.util as _ilu
    try:
        import TOSCANINI as _T  # noqa: N813
        import sys as _s
        _s.modules["toscanini"] = _T
    except Exception:  # noqa: BLE001
        _spec = _ilu.spec_from_file_location(
            "toscanini", str(REPO / "TOSCANINI" / "__init__.py"),
            submodule_search_locations=[str(REPO / "TOSCANINI")])
        _mod = _ilu.module_from_spec(_spec)
        _s.modules["toscanini"] = _mod
        _spec.loader.exec_module(_mod)
if sys.platform == "win32":
    import types
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
from toscanini import sessions as _ss  # noqa: E402

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT = REPO / "R547" / "R547_FRESH_TERMINAL_CAPTURE.json"


def _get(url: str, owner: str | None = None, timeout: int = 90):
    hdrs = {"X-Tosca-Owner": owner} if owner else {}
    req = urllib.request.Request(url, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode("utf-8", "replace"))


def _sse_terminal(sid: str, owner: str, max_polls: int = 80) -> dict:
    """The SSE terminal payload: open the event stream, poll the
    session's live state events, and capture the LAST event that
    carries a terminal state (or the stream's close). The SSE
    transport rides the ?owner= query param (the EventSource
    precedent)."""
    import urllib.parse
    import urllib.error
    url = (f"{BASE}/api/run/{sid}/stream"
           + ("?owner=" + urllib.parse.quote(owner) if owner else ""))
    terminal_events = []
    last_state = None
    try:
        req = urllib.request.Request(url, headers={
            "Accept": "text/event-stream"})
        with urllib.request.urlopen(req, timeout=600) as r:
            buf = ""
            for _ in range(max_polls):
                chunk = r.read(4096).decode("utf-8", "replace")
                if not chunk:
                    break
                buf += chunk
                while "\n\n" in buf:
                    ev, buf = buf.split("\n\n", 1)
                    data = [ln[5:] for ln in ev.splitlines()
                            if ln.startswith("data:")]
                    if not data:
                        continue
                    try:
                        payload = json.loads(data[0])
                    except Exception:  # noqa: BLE001
                        continue
                    last_state = payload.get("status")
                    if last_state in ("COMPLETE", "INTERRUPTED",
                                       "ERROR_RUN", "ERROR_TRANSPORT",
                                       "ERROR_STUCK", "ERROR_BUILD",
                                       "ERROR_CANCELED"):
                        terminal_events.append(payload)
                        return {"saw_terminal": True,
                                "terminal_payload": payload,
                                "user_state_view": payload.get(
                                    "user_state_view")}
    except Exception as exc:  # noqa: BLE001 — the stream may close
        # once the run is terminal; the polled /result record is the
        # authority. Record the last observed state, not an error.
        return {"saw_terminal": bool(terminal_events),
                "terminal_payload": terminal_events[-1]
                if terminal_events else None,
                "last_state": last_state,
                "stream_note": f"{type(exc).__name__}: {exc}"[:120]}
    return {"saw_terminal": bool(terminal_events),
            "terminal_payload": terminal_events[-1]
            if terminal_events else None,
            "last_state": last_state}


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    # the exact current deployment identity
    _c, ver = _get(BASE + "/api/version")
    prod_sha = ver.get("engine_commit")
    # the fresh run metadata (this script's own submit)
    submit_p = REPO / "R547" / "live_submit.json"
    meta = json.loads(submit_p.read_text(encoding="utf-8"))
    sid, owner = meta["sid"], meta["owner_key"]
    _c, detail = _get(f"{BASE}/api/run/{sid}/result", owner)
    usv = detail.get("user_state_view") or {}
    fs = detail.get("final_state") or {}
    rec = {
        "schema": "R547_FRESH_TERMINAL_CAPTURE/1.0.0",
        "round": "R547",
        "production_sha": prod_sha,
        "session_id": sid,
        "raw_session_record": {
            "status": detail.get("status"),
            "final_status": detail.get("final_status"),
            "completion_states": detail.get("completion_states"),
            "completion_contract_present": bool(
                detail.get("completion_contract")),
            "run_dir_present": bool(detail.get("run_dir")),
            "final_state_present": bool(detail.get("final_state")),
        },
        "raw_final_state": fs,
        "completion_states_nested": (
            fs.get("completion_states") if isinstance(fs, dict) else None),
        "user_state": usv.get("user_state"),
        "user_state_view_served": usv,
        "rest_result_payload": {
            "status": detail.get("status"),
            "final_status": detail.get("final_status"),
            "user_state_view": usv,
        },
        "run_state": detail.get("run_state"),
        "decisive_invariant": None,
    }
    # the served record vs the committed source, side by side
    # (Art. XXII: never assume the committed source is the executing
    # source — measure both answers on the SAME record)
    committed_view = _ss.refresh_user_state_view(
        {k: detail.get(k) for k in
         ("session_id", "status", "final_status", "final_state",
          "completion_states", "completion_contract", "run_dir",
          "package", "owner_key")})
    committed_usv = committed_view.get("user_state_view") or {}
    rec["committed_source_recompute"] = {
        "user_state": committed_usv.get("user_state"),
        "finished": committed_usv.get("finished"),
        "contract_flag": _us._contract_finished_flag(
            {k: detail.get(k) for k in
             ("status", "final_status", "final_state",
              "completion_states", "completion_contract")}),
    }
    status = detail.get("status")
    final_status = detail.get("final_status")
    nested_cs = (rec["completion_states_nested"] or {})
    fd = nested_cs.get("FINISHED_DISCOVERY") if isinstance(nested_cs, dict) \
        else None
    rec["decisive_invariant"] = {
        "status": status,
        "final_status": final_status,
        "FINISHED_DISCOVERY": fd,
        "served_user_state_view.finished": usv.get("finished"),
        "committed_source.finished": committed_usv.get("finished"),
        "served_vs_committed_agree": (
            usv.get("finished") == committed_usv.get("finished")),
    }
    # the SSE terminal payload (the directive names it explicitly). The
    # run is already terminal, so the stream closes immediately; the
    # /result record above is the authority, and the SSE capture
    # records whether the terminal payload's view AGREES with REST.
    sse = _sse_terminal(sid, owner)
    sse_usv = (sse.get("terminal_payload") or {}).get(
        "user_state_view") if sse.get("terminal_payload") else None
    rec["sse_terminal_payload"] = sse
    rec["rest_vs_sse"] = {
        "rest_finished": usv.get("finished"),
        "sse_finished": (sse_usv or {}).get("finished")
        if sse_usv else None,
        "agree": (usv.get("finished") == (sse_usv or {}).get("finished")
                   if sse_usv else None),
    }
    OUT.write_text(json.dumps(rec, indent=1, default=str) + "\n",
                   encoding="utf-8")
    di = rec["decisive_invariant"]
    print(json.dumps({
        "production_sha": prod_sha,
        "invariant": di,
        "rest_vs_sse": rec["rest_vs_sse"],
    }, indent=1, default=str))
    print(f"[r547] capture -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
