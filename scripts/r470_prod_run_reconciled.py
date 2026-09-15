#!/usr/bin/env python3
"""R470 (reconciled line) — the fresh production discovery run through
the deployed user path on the RECONCILED deployment (67323d1e), the
measured exercise of THIS line's verifier-assist pass.

The question this run answers: on a fresh problem, does the deployed
VERIFY stage recover a grounded-but-unquoted mechanism span through the
recorded assist (span_extraction / verifier_assist on the candidate),
or does it honestly type the failure — never a silent pass, never a
fabricated span?

Fresh problem, never run in production (lithium-ion grid-storage
calendar-life degradation — a battery/thermal domain, distinct from
every prior measured problem: R466 irrigation/vacuum/infusion, R468
espresso thermoblock, the re-audit telecom cooling, and the sibling
R470-C2's turbine bearings). The driver plays the user honestly.
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
STATE = REPO / "R470" / "PROD_RUN_RECONCILED" / "driver_state.json"
OUT = REPO / "R470" / "PROD_RUN_RECONCILED" / "EVALUATION.json"

PROBLEM = {
    "key": "grid_battery_calendar_life",
    "text": ("Why do lithium-ion grid-storage cells lose capacity "
             "faster in hot climates even when rarely cycled, and what "
             "thermal-management or electrode-coating intervention "
             "would extend their calendar life?"),
}

DESIRED_OUTCOME_ANSWER = (
    "A practical, testable intervention that measurably slows calendar "
    "aging at 35-40 C ambient, verifiable with celled accelerated-aging "
    "chambers within months, without redesigning the cell chemistry.")

PROVIDER_FIELDS = ("provider", "provider_id", "model", "model_id",
                   "task_degradation", "degraded_reason", "capability",
                   "cost_basis", "key_slot", "key_advances")

TERMINAL = {"COMPLETE", "INTERRUPTED", "FAILED_ENGINE",
            "FAILED_TRANSPORT", "BLOCKED_TRANSPORT", "REJECTED"}

MAX_MINUTES = 40


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


def assist_story(obj):
    """THIS line's measurement: every verifier_assist /
    span_extraction record on the run's own artifacts."""
    found = []

    def walk(o, path):
        if isinstance(o, dict):
            if ("verifier_assist" in o and o["verifier_assist"]) or \
                    ("span_extraction" in o and
                     o.get("span_extraction") not in
                     (None, "PROPOSER_CITED", "")):
                found.append({
                    "at": path,
                    "span_extraction": o.get("span_extraction"),
                    "verifier_assist": o.get("verifier_assist"),
                })
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
    t0 = time.time()

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
        if (time.time() - t0) / 60 > MAX_MINUTES:
            rec["terminal_status"] = "DRIVER_TIMEOUT"
            save_state(st)
            print("DRIVER TIMEOUT — the run continues server-side; "
                  "re-run this script to resume evaluation")
            return 1
        time.sleep(20)

    # evaluate
    code, d = req(f"/api/run/{sid}/result", owner=owner)
    code2, ev = req(f"/api/run/{sid}/events", owner=owner)
    usv = d.get("user_state_view") or {}
    stages = d.get("stages") or []
    evs = ev.get("events", []) if isinstance(ev, dict) else []
    eval_rec = {
        "round": "R470",
        "line": "reconciled (the verifier-assist deployment)",
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
        "assist_story": assist_story(
            {"stages": stages, "events": evs[-60:]})[:12],
        "provider_story": provider_story(
            {"stages": stages, "events": evs[-60:]})[:40],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"run": eval_rec}, indent=2) + "\n")
    print(f"artifact -> {OUT.relative_to(REPO)}")
    print(json.dumps(eval_rec, indent=1)[:3200])
    return 0


if __name__ == "__main__":
    sys.exit(main())
