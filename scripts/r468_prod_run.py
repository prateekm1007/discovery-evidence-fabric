#!/usr/bin/env python3
"""R468 — one REAL discovery run on production through the user path
(POST /api/run with a fresh owner capability — exactly what the browser
does), measuring the thing the R466 reaudit left NOT PROVEN: whether the
freshly deployed atria rung serves MECHANISM-stage synthesis without the
INCOMPLETE_INFERENCE_FAILURE degradation that killed 2 of 3 R466 fresh
runs (the R466 binding constraint the atria rung was registered to
answer).

The problem is fresh (never run in production before — R466 ran vacuum /
irrigation / infusion) and stated as a user would state it.

Slice-resumable (the R446/R466 pattern): state persists in
R468/PROD_RUN/driver_state.json; re-running skips completed slices.

commands: launch | poll | evaluate
"""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
STATE_DIR = REPO / "R468" / "PROD_RUN"
STATE = STATE_DIR / "driver_state.json"
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"

PROBLEM = {
    "key": "espresso_scale",
    "text": ("Why do espresso machines lose brewing pressure as limescale "
             "accumulates inside the thermoblock, and what surface or "
             "flow-path intervention would delay the buildup?"),
}

# fields that tell WHICH rung served each stage (the provider story)
PROVIDER_FIELDS = ("provider", "provider_id", "model", "model_id",
                   "task_degradation", "degraded_reason", "capability",
                   "cost_basis")


def load_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"run": {}}


def save_state(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def req(path: str, method: str = "GET", body: dict | None = None,
        owner: str | None = None, timeout: int = 90) -> tuple[int, dict]:
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
        except Exception:  # noqa: BLE001
            return e.code, {}
    except Exception as exc:  # noqa: BLE001
        return 0, {"error": repr(exc)[:200]}


def cmd_launch() -> int:
    st = load_state()
    if st["run"].get("session_id"):
        print(f"{PROBLEM['key']}: already launched "
              f"{st['run']['session_id']}")
        return 0
    owner = uuid.uuid4().hex
    code, resp = req("/api/run", "POST", {"text": PROBLEM["text"]}, owner)
    if code != 200 or not resp.get("session_id"):
        print(f"{PROBLEM['key']}: LAUNCH FAILED http {code}: "
              f"{str(resp)[:200]}")
        return 1
    st["run"] = {"session_id": resp["session_id"], "owner": owner,
                 "launched_at": time.strftime(
                     "%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "problem": PROBLEM["text"]}
    save_state(st)
    print(f"{PROBLEM['key']}: launched {resp['session_id']}")
    return 0


TERMINAL = {"COMPLETE", "INTERRUPTED", "FAILED_ENGINE",
            "FAILED_TRANSPORT", "BLOCKED_TRANSPORT", "REJECTED"}


def cmd_poll() -> int:
    st = load_state()
    rec = st["run"]
    sid = rec.get("session_id")
    if not sid:
        print("NOT LAUNCHED")
        return 2
    if rec.get("terminal_status"):
        print(f"{PROBLEM['key']}: {rec['terminal_status']} (recorded)")
        return 0
    code, d = req(f"/api/run/{sid}/result", owner=rec["owner"])
    status = d.get("status", f"http{code}")
    usv = d.get("user_state_view") or {}
    print(f"{PROBLEM['key']}: {status} | user_state: "
          f"{usv.get('user_state')} | {usv.get('label')}")
    if status in TERMINAL or status not in (
            "PENDING", "RUNNING", "AWAITING_CLARIFICATION"):
        rec["terminal_status"] = status
        rec["terminal_at"] = time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        save_state(st)
        return 0
    return 2


def _provider_story(obj) -> list:
    """Extract provider/model/degradation fields from any nested dict."""
    found = []

    def walk(o, path):
        if isinstance(o, dict):
            hit = {k: o[k] for k in PROVIDER_FIELDS
                   if k in o and o[k] is not None}
            if hit:
                found.append({"at": path, **hit})
            for k, v in o.items():
                if isinstance(v, (dict, list)):
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o[:200]):
                walk(v, f"{path}[{i}]")

    walk(obj, "$")
    return found


def cmd_evaluate() -> int:
    st = load_state()
    rec = st["run"]
    sid, owner = rec.get("session_id"), rec.get("owner")
    if not sid:
        print("NOT LAUNCHED")
        return 2
    code, d = req(f"/api/run/{sid}/result", owner=owner)
    code2, ev = req(f"/api/run/{sid}/events", owner=owner)
    usv = d.get("user_state_view") or {}
    stages = d.get("stages") or []
    evs = ev.get("events", []) if isinstance(ev, dict) else []
    stage_names = [s.get("stage") or s.get("name") or s.get("id")
                   for s in stages if isinstance(s, dict)]
    eval_rec = {
        "round": "R468",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "session_id": sid,
        "problem": rec.get("problem"),
        "status": d.get("status"),
        "user_state": usv.get("user_state"),
        "outcome": usv.get("outcome"),
        "outcome_label": usv.get("outcome_label"),
        "final_status": d.get("final_status"),
        "stages_recorded": len(stages),
        "stage_names": stage_names,
        "events_recorded": len(evs),
        "package": bool((d.get("package") or {}).get("complete"))
                   if isinstance(d.get("package"), dict) else False,
        "error": d.get("error"),
        "provider_story": _provider_story(
            {"stages": stages, "events": evs[-60:]})[:40],
    }
    out = {"run": eval_rec}
    path = STATE_DIR / "EVALUATION.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(f"artifact -> {path.relative_to(REPO)}")
    print(json.dumps(eval_rec, indent=1)[:2400])
    return 0


if __name__ == "__main__":
    cmds = {"launch": cmd_launch, "poll": cmd_poll,
            "evaluate": cmd_evaluate}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print("usage: r468_prod_run.py {launch|poll|evaluate}")
        sys.exit(2)
    sys.exit(cmds[sys.argv[1]]())
