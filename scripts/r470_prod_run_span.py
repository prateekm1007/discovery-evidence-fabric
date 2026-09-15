#!/usr/bin/env python3
"""R470 — the fresh production discovery run through the deployed user
path, measuring THE R469 SPAN CONTRACT on atria-default transport.

The R469-narrowed output-quality question: does the engineered
evidence-span citation contract (the mechanical prompt rules + the
claimant-side verbatim-subwindow repair + the verifier source
alignment) close the 'mechanism_span_not_verbatim' block that typed
R466/R468's fresh runs INCOMPLETE_INFERENCE_FAILURE?

Fresh problem, never run in production (wind-turbine gearbox bearings —
a tribology domain, distinct from R466's irrigation/vacuum/infusion and
R468's espresso thermoblock). The driver plays the user honestly: it
answers the one clarification pause with a plain statement of the
desired outcome, exactly a real operator would.
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
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
STATE = REPO / "R470" / "PROD_RUN" / "driver_state.json"
OUT = REPO / "R470" / "PROD_RUN" / "EVALUATION.json"

PROBLEM = {
    "key": "turbine_bearing",
    "text": ("Why do wind-turbine gearbox bearings fail prematurely "
             "under variable loads, and what surface or lubrication-path "
             "intervention would extend their service life?"),
}

DESIRED_OUTCOME_ANSWER = (
    "A practical, testable intervention that measurably delays bearing "
    "wear under variable loads, verifiable with a bench rig within "
    "weeks, without a full gearbox redesign.")

PROVIDER_FIELDS = ("provider", "provider_id", "model", "model_id",
                   "task_degradation", "degraded_reason", "capability",
                   "cost_basis", "key_slot", "key_advances")

TERMINAL = {"COMPLETE", "INTERRUPTED", "FAILED_ENGINE",
            "FAILED_TRANSPORT", "BLOCKED_TRANSPORT", "REJECTED"}


def req(path, method="GET", body=None, owner=None, timeout=90):
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


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"run": {}}


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def provider_story(obj):
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


def main() -> int:
    st = load_state()
    rec = st["run"]
    if not rec.get("session_id"):
        owner = uuid.uuid4().hex
        code, resp = req("/api/run", "POST", {"text": PROBLEM["text"]},
                         owner)
        if code != 200 or not resp.get("session_id"):
            print(f"LAUNCH FAILED http {code}: {str(resp)[:200]}")
            return 1
        rec = {"session_id": resp["session_id"], "owner": owner,
               "launched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                            time.gmtime()),
               "problem": PROBLEM["text"]}
        st["run"] = rec
        save_state(st)
        print(f"launched {resp['session_id']}")
    sid, owner = rec["session_id"], rec["owner"]

    answered = set(rec.get("answered", []))
    while True:
        code, d = req(f"/api/run/{sid}/result", owner=owner)
        status = d.get("status", f"http{code}")
        usv = d.get("user_state_view") or {}
        print(f"{time.strftime('%H:%M:%S')} {status} | "
              f"{usv.get('user_state')} | {usv.get('label')}")
        if status == "AWAITING_CLARIFICATION":
            q = (d.get("clarification")
                 or usv.get("clarification") or {})
            field = str(q.get("field") or "")
            if field and field not in answered:
                ac, ar = req(f"/api/run/{sid}/answer", "POST",
                             {"answer": DESIRED_OUTCOME_ANSWER}, owner)
                print(f"  answered clarification '{field}' -> http {ac}")
                if ac in (200, 202):
                    answered.add(field)
                    rec["answered"] = sorted(answered)
                    save_state(st)
            time.sleep(15)
            continue
        if status in TERMINAL or status not in ("PENDING", "RUNNING"):
            rec["terminal_status"] = status
            rec["terminal_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                               time.gmtime())
            save_state(st)
            break
        time.sleep(20)

    # evaluate
    code, d = req(f"/api/run/{sid}/result", owner=owner)
    code2, ev = req(f"/api/run/{sid}/events", owner=owner)
    usv = d.get("user_state_view") or {}
    stages = d.get("stages") or []
    evs = ev.get("events", []) if isinstance(ev, dict) else []
    eval_rec = {
        "round": "R470",
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
        "stage_names": [s.get("stage") or s.get("name") or s.get("id")
                        for s in stages if isinstance(s, dict)],
        "events_recorded": len(evs),
        "package": bool((d.get("package") or {}).get("complete"))
        if isinstance(d.get("package"), dict) else False,
        "error": d.get("error"),
        "verification": d.get("verification"),
        "provider_story": provider_story(
            {"stages": stages, "events": evs[-60:]})[:40],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"run": eval_rec}, indent=2) + "\n")
    print(f"artifact -> {OUT.relative_to(REPO)}")
    print(json.dumps(eval_rec, indent=1)[:2600])
    return 0


if __name__ == "__main__":
    sys.exit(main())
