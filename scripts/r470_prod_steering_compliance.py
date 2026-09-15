#!/usr/bin/env python3
"""R470-C2 — the production steering-compliance measurement (the
external re-audit's own P0-5 acceptance, n=1): a fresh parent run; a
CHANGE_MECHANISM directive that NAMES the parent's recorded mechanism
as excluded (the re-audit's directive shape verbatim); a steered child
round; the typed directive_outcome read back from the deployed session.

The re-audit's measured complaint this closes: the child adopted the
directive in the INTERVENTION while the MECHANISM identity stayed in
the forbidden territory, and the card said "changed" (string
inequality) — honest machinery, one step short of honest semantics.
This run measures whether the deployed 590b71bb engine now types the
outcome COMPLIED_CHANGED / MOVED_BUT_IN_TERRITORY / etc. from the ONE
shared compliance instrument.
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
STATE = REPO / "R470" / "PROD_RUN" / "steering_state.json"
OUT = REPO / "R470" / "PROD_RUN" / "STEERING_EVALUATION.json"

PROBLEM = {
    "key": "ebike_battery_thermal",
    "text": ("Lithium-ion battery packs in shared e-bike fleets overheat "
             "during summer fast-charging and degrade far faster than "
             "rated. What pack-level thermal intervention would keep "
             "cell temperatures in the safe band through a fast charge?"),
}

PARENT_OUTCOME_ANSWER = (
    "A practical pack-level thermal intervention that keeps cells inside "
    "the manufacturer's safe temperature window during fast charging in "
    "hot climates, verifiable on an instrumented pack within weeks.")

# the directive is composed AT STEER TIME from the parent's RECORDED
# mechanism identity — the re-audit's exact shape:
# "Do not use <parent mechanism>. Use <alternative direction> instead."
CHILD_OUTCOME_ANSWER = PARENT_OUTCOME_ANSWER

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
    return {}


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, indent=2))


def run_to_terminal(sid, owner, outcome_answer, rec_key, st,
                    max_minutes=35):
    """Poll one run to terminal; answer clarifications honestly."""
    answered = set((st.get(rec_key) or {}).get("answered") or [])
    t0 = time.time()
    while True:
        if (time.time() - t0) > max_minutes * 60:
            return {"status": "DRIVER_TIMEOUT", "session_id": sid}
        code, d = req(f"/api/run/{sid}/result", owner=owner)
        status = d.get("status", f"http{code}")
        usv = d.get("user_state_view") or {}
        print(f"{time.strftime('%H:%M:%S')} [{rec_key}] {status} | "
              f"{usv.get('user_state')}", flush=True)
        if status == "AWAITING_CLARIFICATION":
            q = (d.get("clarification") or usv.get("clarification") or {})
            field = str(q.get("field") or "")
            if field and field not in answered:
                ac, ar = req(f"/api/run/{sid}/answer", "POST",
                             {"answer": outcome_answer}, owner)
                print(f"  answered '{field}' -> http {ac}", flush=True)
                if ac in (200, 202):
                    answered.add(field)
                    st.setdefault(rec_key, {})["answered"] = sorted(
                        answered)
                    save_state(st)
            time.sleep(15)
            continue
        if status in TERMINAL or status not in ("PENDING", "RUNNING",
                                                "BUILDING_PROBLEM"):
            return d
        time.sleep(20)


def parent_mechanism(detail):
    """The parent's recorded mechanism identity — the same fields the
    spawn site's identity reader uses (envelope_SYNTHESIZE.mechanism_map
    projected through run_state)."""
    rs = detail.get("run_state") or {}
    gens = ((rs.get("generations") or {}).get("generations")) or []
    if gens:
        arch = (gens[-1].get("architecture") or {})
        mech = str(arch.get("mechanism") or "").strip()
        if mech:
            return mech
    for st_ in detail.get("stages") or []:
        if str(st_.get("stage") or "") == "SYNTHESIZE":
            mm = (st_.get("mechanism_map") or {})
            mech = str(mm.get("mechanism") or "").strip()
            if mech:
                return mech
    return ""


def main() -> int:
    st = load_state()

    # ---- leg A: the parent ------------------------------------------
    if not st.get("parent", {}).get("session_id"):
        owner = uuid.uuid4().hex
        code, resp = req("/api/run", "POST", {"text": PROBLEM["text"]},
                         owner)
        if code != 200 or not resp.get("session_id"):
            print(f"LAUNCH FAILED http {code}: {str(resp)[:200]}")
            return 1
        st["parent"] = {"session_id": resp["session_id"], "owner": owner,
                        "launched_at": time.strftime(
                            "%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        save_state(st)
        print(f"parent launched {resp['session_id']}", flush=True)
    p_sid = st["parent"]["session_id"]
    p_owner = st["parent"]["owner"]

    if not st.get("parent", {}).get("terminal"):
        pd = run_to_terminal(p_sid, p_owner, PARENT_OUTCOME_ANSWER,
                             "parent", st)
        st.setdefault("parent", {})["terminal_status"] = pd.get("status")
        st["parent"]["terminal"] = True
        save_state(st)
    code, pd = req(f"/api/run/{p_sid}/result", owner=p_owner)
    p_mech = parent_mechanism(pd)
    st["parent"]["mechanism"] = p_mech
    st["parent"]["terminal_status"] = pd.get("status")
    save_state(st)
    print(f"parent mechanism recorded: {p_mech[:120]}", flush=True)
    if not p_mech:
        rec = {"honest_state": "NO_PARENT_MECHANISM",
               "parent_status": pd.get("status"),
               "note": ("the parent ended without a recorded mechanism "
                        "identity — there is no forbidden referent to "
                        "steer away from; the compliance leg is not "
                        "reachable this round (typed, not hidden)")}
        OUT.write_text(json.dumps(rec, indent=2) + "\n")
        print(json.dumps(rec, indent=1))
        return 0

    # ---- leg B: the steered child ------------------------------------
    if not st.get("child", {}).get("session_id"):
        directive = (f"Do not use the mechanism the last round recorded "
                     f"('{p_mech}'). Use a different physical route: "
                     f"immersion-style passive heat spreading with a "
                     f"phase-change buffer instead.")
        code, resp = req(f"/api/run/{p_sid}/actions", "POST",
                         {"verb": "CHANGE_MECHANISM",
                          "direction": directive}, owner=p_owner)
        print(f"steer POST -> http {code}: {str(resp)[:200]}", flush=True)
        new_id = (resp.get("new_run_id") or resp.get("session_id")
                  or (resp.get("detail") or {}).get("session_id"))
        if code not in (200, 202) or not new_id:
            st["child"] = {"steer_http": code, "steer_resp":
                           str(resp)[:300]}
            save_state(st)
            rec = {"honest_state": "STEER_NOT_ACCEPTED",
                   "http": code, "resp": str(resp)[:300]}
            OUT.write_text(json.dumps(rec, indent=2) + "\n")
            return 1
        st["child"] = {"session_id": new_id, "owner": p_owner,
                       "directive": directive,
                       "steered_at": time.strftime(
                           "%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        save_state(st)
    c_sid = st["child"]["session_id"]
    c_owner = st["child"]["owner"]
    if not st.get("child", {}).get("terminal"):
        cd = run_to_terminal(c_sid, c_owner, CHILD_OUTCOME_ANSWER,
                             "child", st)
        st["child"]["terminal_status"] = cd.get("status")
        st["child"]["terminal"] = True
        save_state(st)

    # ---- evaluate the child's typed directive_outcome ----------------
    code, cd = req(f"/api/run/{c_sid}/result", owner=c_owner)
    do = cd.get("directive_outcome") or {}
    rec = {
        "round": "R470-C2",
        "measured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "parent": {"session_id": p_sid,
                   "status": st["parent"].get("terminal_status"),
                   "mechanism": p_mech},
        "child": {"session_id": c_sid,
                  "status": st["child"].get("terminal_status"),
                  "directive": st["child"].get("directive")},
        "directive_outcome": do,
        "compliance_verdict": do.get("compliance_verdict"),
        "territory": do.get("territory"),
        "summary": do.get("summary"),
        "note": ("the re-audit's acceptance at n=1: the typed record "
                 "states compliance honestly — a MOVED_BUT_IN_TERRITORY "
                 "or NOT_COMPLIED verdict is the machinery working, "
                 "exactly as much as a COMPLIED_CHANGED one"),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({k: rec[k] for k in
                      ("compliance_verdict", "summary")}, indent=1),
          flush=True)
    print(f"artifact -> {OUT.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
