#!/usr/bin/env python3
"""R466 — Measurement B: three REAL discovery runs on production,
launched through the user path (POST /api/run with a fresh owner
capability, exactly what the browser does), then evaluated as
professional deliverables.

Slice-resumable (the R446 pattern): state persists in
R466/RUNS/driver_state.json; re-running skips completed slices.

The three problems are fresh (never run in production before), span
three domains, and are stated as a user would state them.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE_DIR = REPO / "R466" / "RUNS"
STATE = STATE_DIR / "driver_state.json"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"

PROBLEMS = [
    {"key": "vacuum", "text": ("Why do cordless vacuum cleaners lose suction "
                               "within the first two years of use, and what "
                               "mechanical intervention would restore it?")},
    {"key": "irrigation", "text": ("How can drip irrigation emitters be "
                                   "protected from root intrusion clogging "
                                   "without chemical treatment?")},
    {"key": "infusion", "text": ("Why do insulin pump infusion sets fail "
                                 "prematurely when the adhesive loosens "
                                 "during exercise, and what would keep the "
                                 "cannula stable?")},
]


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"runs": {}}


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def req(path: str, method: str = "GET", body: dict | None = None,
        owner: str | None = None, timeout: int = 60) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(BASE + path, data=data, method=method)
    if data:
        r.add_header("Content-Type", "application/json")
    if owner:
        r.add_header("X-Tosca-Owner", owner)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.load(resp)
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def cmd_launch() -> int:
    st = load_state()
    for p in PROBLEMS:
        key = p["key"]
        if st["runs"].get(key, {}).get("session_id"):
            print(f"{key}: already launched "
                  f"{st['runs'][key]['session_id']}")
            continue
        owner = uuid.uuid4().hex
        code, resp = req("/api/run", "POST", {"text": p["text"]}, owner)
        if code != 200 or not resp.get("session_id"):
            print(f"{key}: LAUNCH FAILED http {code}: {str(resp)[:200]}")
            st["runs"][key] = {"error": f"launch http {code}",
                               "detail": str(resp)[:300]}
            save_state(st)
            return 1
        sid = resp["session_id"]
        st["runs"][key] = {"session_id": sid, "owner": owner,
                           "launched_at": time.strftime(
                               "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                           "problem": p["text"]}
        save_state(st)
        print(f"{key}: launched {sid}")
    return 0


TERMINAL = {"COMPLETE", "INTERRUPTED", "FAILED_ENGINE",
            "FAILED_TRANSPORT", "BLOCKED_TRANSPORT", "REJECTED"}


def cmd_poll() -> int:
    st = load_state()
    all_terminal = True
    for p in PROBLEMS:
        key = p["key"]
        rec = st["runs"].get(key, {})
        sid = rec.get("session_id")
        if not sid:
            print(f"{key}: NOT LAUNCHED")
            all_terminal = False
            continue
        if rec.get("terminal_status"):
            print(f"{key}: {rec['terminal_status']} (recorded)")
            continue
        code, d = req(f"/api/run/{sid}/result", owner=rec["owner"])
        status = d.get("status", f"http{code}")
        usv = (d.get("user_state_view") or {})
        print(f"{key}: {status} | user_state: "
              f"{usv.get('user_state')} | {usv.get('label')}")
        if status in TERMINAL or status not in (
                "PENDING", "RUNNING", "AWAITING_CLARIFICATION"):
            rec["terminal_status"] = status
            rec["terminal_at"] = time.strftime(
                "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            save_state(st)
        else:
            all_terminal = False
    return 0 if all_terminal else 2


def cmd_evaluate() -> int:
    st = load_state()
    out = {"round": "R466", "measured_at": time.strftime(
        "%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "runs": {}}
    ok = True
    for p in PROBLEMS:
        key = p["key"]
        rec = st["runs"].get(key, {})
        sid, owner = rec.get("session_id"), rec.get("owner")
        if not sid:
            print(f"{key}: no session")
            ok = False
            continue
        code, d = req(f"/api/run/{sid}/result", owner=owner)
        code2, ev = req(f"/api/run/{sid}/events", owner=owner)
        usv = d.get("user_state_view") or {}
        stages = d.get("stages") or []
        evs = ev.get("events", []) if isinstance(ev, dict) else []
        eval_rec = {
            "session_id": sid,
            "problem": p["text"],
            "status": d.get("status"),
            "user_state": usv.get("user_state"),
            "outcome": usv.get("outcome"),
            "outcome_label": usv.get("outcome_label"),
            "final_status": d.get("final_status"),
            "stages_recorded": len(stages),
            "events_recorded": len(evs),
            "package": bool((d.get("package") or {}).get("complete"))
                       if isinstance(d.get("package"), dict) else False,
            "run_state_phases": list((d.get("run_state") or {}).get(
                "phases", {}).keys()) if isinstance(
                d.get("run_state"), dict) else [],
            "error": d.get("error"),
        }
        out["runs"][key] = eval_rec
        print(json.dumps(eval_rec, indent=1)[:800])
    path = REPO / "R466" / "RUNS_EVALUATION.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> {path.relative_to(REPO)}")
    return 0 if ok else 1


if __name__ == "__main__":
    cmds = {"launch": cmd_launch, "poll": cmd_poll,
            "evaluate": cmd_evaluate}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("usage: r466_runs_driver.py {launch|poll|evaluate}")
        sys.exit(2)
    sys.exit(cmds[sys.argv[1]]())
