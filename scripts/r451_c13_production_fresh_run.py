#!/usr/bin/env python3
"""scripts/r451_c13_production_fresh_run.py — the R451-C1.3 §C1.10
fresh production-run proof: ONE genuinely fresh problem through the REAL
user path on the DEPLOYED canonical Space (the R451-C1.3 engine at the
pushed commit — the runtime-admission authority + run-level routing
provenance + the Space's OWN zero-paid llama-server route).

The problem below was authored for this proof and has NEVER been
submitted to any environment — not Render, not the sandbox batteries,
not R446-HF/R447/R449/R450 cases, not the R451 acceptance problems
(ozone diffuser fouling / EV-bus battery thermal / greenhouse emitter
clogging / dual-lumen drainage catheter). Domain: pharmaceutical
freeze-drying (lyophilization) batch non-uniformity — mechanically and
physically distinct from every prior case (coupled radiative/vacuum
heat transfer + sublimation front kinetics + stopper sealing).

Transport: the FIXED owner-capability path (the R447 run-not-found
closure) — run creation with no cookie; the response carries the
caller's own owner_key; every subsequent request carries X-Tosca-Owner.

The C1.3-SPECIFIC production proofs captured here:
  1. the run executes on the Space's OWN zero-paid localqwen route
     (LOCAL_QWEN_ENABLE=1, the llama-server started by the entrypoint,
     admitted by the SAME runtime-admission authority — probe-before-
     admit, no bespoke local exception);
  2. after the run completes, the durable-state snapshot carries the
     MODEL_ROUTING_LEDGER + the capability store to the runtime-state-hf
     branch — fetched and verified from OUTSIDE the container: every
     run-owned line carries the run_id (the C1.3-3 invariant measured
     ON PRODUCTION), zero paid lines, the 13 directive fields, and the
     task-degradation records.

Slice-resumable (the sandbox reaps processes at tool-call boundaries):
session persists to R451/PRODUCTION_FRESH_RUN_C13_SESSION.json;
re-invoke to resume the SAME run.

Usage: HF_TOKEN=... GITHUB_TOKEN=... python3 \
    scripts/r451_c13_production_fresh_run.py [poll-minutes]
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13.json"
RUNS_DIR = REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13"
SESSION = REPO_ROOT / "R451" / "PRODUCTION_FRESH_RUN_C13_SESSION.json"
STATE_BRANCH = "runtime-state-hf"

POLL_INTERVAL_S = 30

CASE: Dict[str, str] = {
    "case_id": "r451c13-fresh-pharma-lyophilization",
    "directive_class": (
        "R451-C1.3 §C1.10 fresh production-run proof: pharmaceutical "
        "freeze-drying batch non-uniformity — a genuinely fresh "
        "problem/domain through the real user path on the deployed "
        "R451-C1.3 engine, on the Space's OWN zero-paid local route"),
    "text": (
        "A contract freeze-drying plant produces 40,000-vial batches of "
        "a protein injectable in a shelf-mounted lyophilizer, and the "
        "center-vial collapse problem recurs every run: shelf-edge "
        "vials finish at 0.3 percent residual moisture while "
        "center-shelf vials reach 1.8 percent, above the 1.0 percent "
        "specification limit, and roughly 4 percent of center vials "
        "show visible cake collapse or stoppers that fail to seat "
        "during backfill, which forces 100 percent visual inspection "
        "and scraps whole center trays. The product loads at 11 "
        "milliliters per 20-milliliter vial with a 3-millimeter "
        "liquid depth, primary drying currently runs 62 hours at minus "
        "28 degrees Celsius shelf and 0.16 millibar, and the "
        "controlled-nucleation step is absent. We need an arrangement "
        "that brings center-vial residual moisture below 1.0 percent "
        "and eliminates stopper-seating failures within a 55-hour "
        "primary-drying window, without vial-format changes, without "
        "cycle extensions beyond the 55-hour constraint, and without "
        "re-qualifying the loading recipe from scratch."),
}


def _log(msg: str) -> None:
    print(f"[r451c13-fresh] {msg}", flush=True)


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, owner_key: Optional[str] = None,
         binary: bool = False) -> Dict[str, Any]:
    import urllib.error
    import urllib.request
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {HF_TOKEN}"}
    if owner_key:
        headers["X-Tosca-Owner"] = owner_key
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            if binary:
                chunks = b""
                while True:
                    c = r.read(65536)
                    if not c:
                        break
                    chunks += c
                return {"http_status": r.status, "bytes": chunks}
            return {"http_status": r.status,
                    "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:600].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None,
                "error": f"{type(exc).__name__}: {str(exc)[:200]}"}


def _version() -> Dict[str, Any]:
    v = _req("/api/version", timeout=60)
    h = _req("/api/health", timeout=90)
    return {
        "version": (v.get("body") or {}) if v.get("http_status") == 200
        else {"error": v.get("error")},
        "health": {k: (h.get("body") or {}).get(k)
                   for k in ("ok", "engine_commit", "deployment_drift",
                             "discovery_ready")}
        if h.get("http_status") == 200 else {"error": h.get("error")},
    }


def _create() -> Optional[Dict[str, Any]]:
    body = {"text": CASE["text"], "problem_id": CASE["case_id"]}
    r = _req("/api/run", body=body, timeout=180)
    if r.get("http_status") not in (200, 201, 202):
        _log(f"create failed: {r.get('http_status')} "
             f"{str(r.get('error') or r.get('body'))[:300]}")
        return None
    b = r.get("body") or {}
    return {"session_id": b.get("session_id") or b.get("id"),
            "owner_key": b.get("owner_key"),
            "created": b}


def _poll(session_id: str, owner_key: Optional[str],
          deadline_s: float) -> Dict[str, Any]:
    t0 = time.time()
    last: Dict[str, Any] = {}
    while time.time() - t0 < deadline_s:
        r = _req(f"/api/run/{session_id}/result", timeout=120,
                 owner_key=owner_key)
        if r.get("http_status") == 200:
            last = r
            body = r.get("body") or {}
            status = str(body.get("status") or "").upper()
            if status in ("COMPLETE", "FAILED", "ERROR", "DONE",
                          "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
                          "ERROR_RUN", "ERROR_BUILD"):
                return r
        elif r.get("http_status") is None:
            _log(f"poll transport hiccup: {str(r.get('error'))[:80]}")
        time.sleep(POLL_INTERVAL_S)
    return {"http_status": "SLICE_DEADLINE", "last": last}


def _capture_run(session_id: str,
                 owner_key: Optional[str]) -> Dict[str, Any]:
    rec: Dict[str, Any] = {"case_id": CASE["case_id"],
                           "directive_class": CASE["directive_class"],
                           "session_id": session_id}
    result = _req(f"/api/run/{session_id}/result", timeout=120,
                  owner_key=owner_key)
    body = (result.get("body") or {})
    rec["user_visible_state"] = {
        "status": body.get("status"),
        "final_status": body.get("final_status"),
        "reason": body.get("reason"),
    }
    state = _req(f"/api/run/{session_id}/state", timeout=120,
                 owner_key=owner_key)
    st = (state.get("body") or {}) if state.get("http_status") == 200 \
        else {"error": state.get("error")}
    rec["canonical_state_keys"] = sorted(st.keys()) \
        if isinstance(st, dict) else []
    # the ACTUAL persisted state shapes (Art. X): the state endpoint
    # carries evidence_state / mechanism_state / attack_state /
    # evolution_state (the _state-suffixed canonical keys)
    ev_state = st.get("evidence_state") or {}
    mech_state = st.get("mechanism_state") or {}
    atk_state = st.get("attack_state") or {}
    rec["chain"] = {
        "problem": bool(st.get("user_problem")
                        or st.get("problem")
                        or st.get("phase_progression")),
        "evidence_present": bool(
            ev_state.get("state") in ("GATHERED", "FROZEN")
            or ev_state.get("records_found")),
        "evidence_records": ev_state.get("records_found"),
        "mechanism_present": bool(
            mech_state.get("state") in ("GENERATED", "BUILT")
            or mech_state.get("mechanism")),
        "attack_present": bool(
            atk_state.get("state") in ("EXECUTED", "ADJUDICATED")
            or atk_state.get("overall")),
        "attack_overall": atk_state.get("overall"),
        "evolution_present": bool(st.get("evolution_state")
                                  or st.get("generations")),
        "experiment_present": bool(st.get("experiment_state")),
        "package_terminal": (st.get("package_state") or {}),
        "invention_state": st.get("invention_state") or {},
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{session_id}_state.json").write_text(
        json.dumps(st, indent=1, default=str)[:400_000])
    (RUNS_DIR / f"{session_id}_result.json").write_text(
        json.dumps(body, indent=1, default=str)[:400_000])
    return rec


def _fetch_durable_ledger(session_id: str) -> Dict[str, Any]:
    """Fetch the runtime-state-hf branch and isolate THIS session's
    run-owned ledger lines + the capability store — the C1.3-3
    production-side provenance verification (from OUTSIDE the
    container, through the durable push)."""
    out: Dict[str, Any] = {"fetched": False}
    if not GITHUB_TOKEN:
        out["error"] = "GITHUB_TOKEN not set"
        return out
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        url = (f"https://{GITHUB_TOKEN}@github.com/prateekm1007/"
               f"discovery-evidence-fabric.git")
        r = subprocess.run(
            ["git", "clone", "--depth", "1", "--branch", STATE_BRANCH,
             url, td], capture_output=True, text=True, timeout=300)
        if r.returncode != 0:
            out["error"] = (r.stderr or "")[:300]
            return out
        ledger = Path(td) / "model_routing" / "ledger.jsonl"
        cap = Path(td) / "transport_capability" / "capability_state.json"
        lines = []
        if ledger.exists():
            for ln in ledger.open():
                try:
                    lines.append(json.loads(ln))
                except Exception:  # noqa: BLE001
                    pass
        # the run_id on production is the EngineRun id bound to this
        # session — isolate by prefix: the run dir name carries the
        # session id; ledger lines carry run_id == the engine run id
        # (engrun:...) — match by the run dirs of this session.
        sessions_f = Path(td) / "sessions.json"
        run_ids = []
        if sessions_f.exists():
            try:
                sdoc = json.loads(sessions_f.read_text())
                for sid, srec in (sdoc.get("sessions")
                                  or sdoc.items()):
                    if sid == session_id and isinstance(srec, dict):
                        rd = srec.get("run_dir")
                        if rd:
                            run_ids.append(Path(rd).name)
            except Exception:  # noqa: BLE001
                pass
        run_lines = [l for l in lines
                     if l.get("session_id") == session_id
                     or (l.get("run_id") or "").endswith(
                         tuple(run_ids))
                     or any(rid and rid in str(l.get("run_id") or "")
                            for rid in run_ids)]
        run_owned = [l for l in run_lines
                     if l.get("call_class") == "RUN_OWNED"]
        paid = [l for l in run_lines
                if (l.get("cost_class") or "") not in
                ("ZERO_PAID_COST_SELF_HOSTED", None)]
        out.update({
            "fetched": True,
            "ledger_total_lines": len(lines),
            "run_ids_found": run_ids,
            "run_window_lines": len(run_lines),
            "run_owned_lines": len(run_owned),
            "invariant_run_owned_non_null_run_id": all(
                bool(l.get("run_id")) for l in run_owned),
            "paid_cost_lines": len(paid),
            "providers": sorted({str(l.get("provider"))
                                 for l in run_lines}),
            "thirteen_fields_on_run_owned": all(
                all(k in l for k in (
                    "run_id", "session_id", "request_id", "stage",
                    "provider", "model", "attempt", "task",
                    "cost_class", "account_domain", "failure_class",
                    "fallback_from", "fallback_to"))
                for l in run_owned),
            "capability_states_on_run_owned": sorted({
                str(l.get("capability_state")) for l in run_owned}),
            "task_degradation_records": sum(
                1 for l in run_owned if l.get("task_degradation")),
            "capability_store_present": cap.exists(),
            "example_line": {k: run_owned[-1].get(k) for k in (
                "run_id", "session_id", "engine_stage", "call_class",
                "provider", "model", "cost_class", "account_domain",
                "capability_state")}
            if run_owned else None,
        })
        (RUNS_DIR / f"{session_id}_ledger_lines.json").write_text(
            json.dumps(run_lines, indent=1, default=str))
    return out


def main() -> int:
    poll_minutes = int(sys.argv[1]) if len(sys.argv) > 1 else 8
    sess = None
    if SESSION.exists():
        try:
            sess = json.loads(SESSION.read_text())
        except Exception:  # noqa: BLE001
            sess = None

    _log("deployment identity (the Art. LXXI tuple, re-measured here):")
    ident = _version()
    _log(json.dumps(ident.get("health"), indent=1)[:400])
    rec: Dict[str, Any] = {
        "artifact_type": "R451_C13_PRODUCTION_FRESH_RUN",
        "case": CASE,
        "deployment_identity_at_run": ident,
    }

    if not sess:
        _log("creating the fresh production run (POST /api/run)...")
        created = _create()
        if not created or not created.get("session_id"):
            rec["created"] = "FAILED"
            OUT.write_text(json.dumps(rec, indent=1, default=str))
            _log("create FAILED — record written")
            return 1
        sess = created
        SESSION.write_text(json.dumps(sess, indent=1))
        _log(f"session {sess.get('session_id')} created "
             f"(owner_key {'returned' if sess.get('owner_key') else 'ABSENT'})")
    else:
        _log(f"resuming session {sess.get('session_id')}")

    sid = sess.get("session_id")
    ok = sess.get("owner_key")
    rec["session_id"] = sid
    rec["owner_key_returned"] = bool(ok)

    _log(f"polling the run (slice budget {poll_minutes} min)...")
    pr = _poll(sid, ok, poll_minutes * 60)
    body = (pr.get("body") or (pr.get("last") or {}).get("body") or {})
    rec["polled_status"] = body.get("status") or pr.get("http_status")
    _log(f"polled status: {rec['polled_status']}")

    terminal = str(rec.get("polled_status") or "").upper() in (
        "COMPLETE", "FAILED", "ERROR", "DONE", "INTERRUPTED",
        "RUN_BLOCKED_TRANSPORT", "ERROR_RUN", "ERROR_BUILD")
    rec["terminal"] = terminal

    cap = _capture_run(sid, ok)
    rec.update(cap)

    if terminal:
        _log("run terminal — fetching the durable-state provenance "
             "(runtime-state-hf branch)...")
        rec["durable_provenance"] = _fetch_durable_ledger(sid)
        _log(json.dumps(rec["durable_provenance"], indent=1,
                        default=str)[:600])
        OUT.write_text(json.dumps(rec, indent=1, default=str))
        _log(f"record -> {OUT}")
        return 0

    OUT.write_text(json.dumps(rec, indent=1, default=str))
    _log(f"slice budget reached — re-invoke to continue "
         f"(record -> {OUT})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
