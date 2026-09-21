#!/usr/bin/env python3
"""R513 — MULTI_SOURCE_DISCOVERY removal fresh production battery.

Runs the byte-identical R510/R511/R512 5-case battery (manifest:
R510/POST_FIX_BATTERY/MANIFEST.json) against the deployed removal
build (4d4964e8) through the REAL user path (POST /api/run + poll),
capturing result/state payloads per case for the before/after
runtime attribution (R511/PRODUCTION_RUNTIME_ATTRIBUTION.json is the
pre-removal reference with per-stage walls including
MULTI_SOURCE_DISCOVERY).

Slice-resumable: R513/REMOVAL_BATTERY_SESSION.json persists per-case
progress; re-invoke to continue. argv[1] = slice budget in minutes
(default 25). Exit 0 = all 5 terminal; exit 1 = slice exhausted.

Usage: HF_TOKEN=... python R513/removal_battery.py [budget-minutes]
Tokens via env only; raw captures may contain run payloads but never
credential values.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO = Path(__file__).resolve().parents[1]
OUT_DIR = REPO / "R513"
RUNS_DIR = OUT_DIR / "REMOVAL_BATTERY_RUNS"
SESSION = OUT_DIR / "REMOVAL_BATTERY_SESSION.json"
OUT = OUT_DIR / "REMOVAL_BATTERY.json"

BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
HF_TOKEN = os.environ.get("HF_TOKEN", "")

POLL_INTERVAL_S = 30
PER_CASE_DEADLINE_S = 25 * 60
TERMINAL = {"COMPLETE", "FAILED", "ERROR", "DONE", "INTERRUPTED",
            "RUN_BLOCKED_TRANSPORT", "ERROR_RUN", "ERROR_BUILD"}

CASES = [
    {"case": "A",
     "text": "Countertop microwave ovens develop hot spots that burn food edges while centers stay cold. The household wants even heating without stirring mid-cycle."},
    {"case": "B",
     "text": "Offshore wind turbine blades accumulate ice in winter, cutting power output. The operator wants ice protection that survives salt spray and high winds."},
    {"case": "C",
     "text": "A water-powered car that runs forever on a single glass of water with no other energy input, claimed to violate no physical laws. The inventor wants validation of infinite mileage."},
    {"case": "D",
     "text": "City bus routes bunch up so three buses arrive together then nothing for half an hour. Commuters want evenly spaced arrivals without adding buses."},
    {"case": "E",
     "text": "Power drill batteries fade within minutes under heavy load on construction sites. Workers want sustained power through a full shift without swapping packs."},
]

# Honest clarification answers in each case's own terms (r471 precedent:
# plain restatements of the submitted problem text; no new claims).
ANSWERS = {
    "A": {
        "target_variable": "Spatial temperature uniformity of the food load after a standard heating cycle (minimize the hot-spot/cold-spot spread), with no mid-cycle stirring.",
        "observed_failure": "Countertop microwave oven edges burn while centers stay cold during normal household use.",
        "desired_outcome": "Even heating without stirring mid-cycle, verifiable by temperature mapping of the food load.",
        "constraints": "Countertop form factor kept; no user intervention mid-cycle.",
        "context": "Household kitchen use."},
    "B": {
        "target_variable": "Winter power-output retention (minimize icing-related output loss), with protection surviving salt spray and high winds.",
        "observed_failure": "Offshore wind turbine blades accumulate ice in winter, cutting power output.",
        "desired_outcome": "Ice protection that survives salt spray and high winds, verifiable by winter output records.",
        "constraints": "Blades stay in service; protection must survive salt spray and high winds.",
        "context": "Offshore winter operation."},
    "C": {
        "target_variable": "Net energy balance of the claimed water-only operation: whether infinite mileage can satisfy energy conservation; validate or refute the claim as stated.",
        "observed_failure": "A claimed water-powered car running forever on a single glass of water with no other energy input.",
        "desired_outcome": "Validation or refutation of the infinite-mileage claim against physical law, verifiable by energy accounting.",
        "constraints": "The claim is tested as stated; no physical law is set aside in the assessment.",
        "context": "An inventor seeks validation of the claim."},
    "D": {
        "target_variable": "Headway regularity (evenly spaced arrivals, minimize bunching gaps), without adding buses.",
        "observed_failure": "Three buses arrive together then nothing for half an hour on city routes.",
        "desired_outcome": "Evenly spaced arrivals without adding buses, verifiable by arrival-interval records.",
        "constraints": "Fleet size fixed; no added buses.",
        "context": "City bus routes in normal service."},
    "E": {
        "target_variable": "Sustained power delivery through a full construction shift under heavy load, without swapping packs.",
        "observed_failure": "Power drill batteries fade within minutes under heavy load on construction sites.",
        "desired_outcome": "Sustained power through a full shift without swapping packs, verifiable by shift-long load tests.",
        "constraints": "Same drill platform; no mid-shift pack swaps.",
        "context": "Construction-site heavy-load use."},
}
FALLBACK_ANSWER = ("The problem statement as submitted; no additional "
                   "specification beyond the case text.")


def _log(msg: str) -> None:
    print("[r513-battery] " + msg, flush=True)


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, owner_key: Optional[str] = None
         ) -> Dict[str, Any]:
    import urllib.error
    import urllib.request
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": "Bearer " + HF_TOKEN}
    if owner_key:
        headers["X-Tosca-Owner"] = owner_key
    req = urllib.request.Request(
        url, data=data, headers=headers,
        method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"http_status": r.status,
                    "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:400].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None,
                "error": type(exc).__name__ + ": " + str(exc)[:160]}


def _load_session() -> Dict[str, Any]:
    if SESSION.exists():
        try:
            return json.loads(SESSION.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {"cases": {}}


def _save_session(sess: Dict[str, Any]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(sess, indent=1))


def _drive_case(case: Dict[str, Any], sess_cases: Dict[str, Any],
                budget_left_s: float) -> float:
    """Drive one case to terminal or budget exhaustion. Returns seconds
    consumed."""
    t_start = time.time()
    cid = case["case"]
    st = sess_cases.get(cid, {})
    session_id = st.get("session_id")
    owner_key = st.get("owner_key")
    if not session_id:
        r = _req("/api/run", body={"text": case["text"]}, timeout=180)
        if r.get("http_status") not in (200, 201, 202):
            _log("case %s create failed: %s %s" % (
                cid, r.get("http_status"),
                str(r.get("error") or r.get("body"))[:200]))
            return time.time() - t_start
        b = r.get("body") or {}
        session_id = b.get("session_id") or b.get("id")
        owner_key = b.get("owner_key")
        if not session_id:
            _log("case %s create returned no session id" % cid)
            return time.time() - t_start
        st = {"session_id": session_id, "owner_key": owner_key,
              "created_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                              time.gmtime())}
        sess_cases[cid] = st
        _save_session({"cases": sess_cases})
        _log("case %s created session %s" % (cid, session_id))
    deadline = min(PER_CASE_DEADLINE_S, budget_left_s)
    t0 = time.time()
    while time.time() - t0 < deadline:
        r = _req("/api/run/" + session_id + "/result", timeout=120,
                 owner_key=owner_key)
        if r.get("http_status") == 200:
            body = r.get("body") or {}
            status = str(body.get("status") or "").upper()
            if status == "AWAITING_CLARIFICATION" \
                    and not st.get("clarified"):
                q = body.get("clarification") or {}
                field = q.get("field")
                answer = (ANSWERS.get(cid, {}).get(field)
                          or FALLBACK_ANSWER)
                a = _req("/api/run/" + session_id + "/answer",
                         body={"answer": answer}, timeout=120,
                         owner_key=owner_key)
                st["clarified"] = True
                st["clarification_field"] = field
                st["clarification_answer"] = answer
                st["clarification_http"] = a.get("http_status")
                sess_cases[cid] = st
                _save_session({"cases": sess_cases})
                _log("case %s clarification (%s) answered http=%s"
                     % (cid, field, a.get("http_status")))
                time.sleep(POLL_INTERVAL_S)
                continue
            if status in TERMINAL:
                st["terminal"] = status
                st["finished_at_utc"] = time.strftime(
                    "%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                sess_cases[cid] = st
                RUNS_DIR.mkdir(parents=True, exist_ok=True)
                (RUNS_DIR / (cid + "_" + session_id + "_result.json")
                 ).write_text(json.dumps(body, indent=1, default=str)
                              [:500_000])
                s = _req("/api/run/" + session_id + "/state", timeout=120,
                         owner_key=owner_key)
                if s.get("http_status") == 200:
                    (RUNS_DIR / (cid + "_" + session_id + "_state.json")
                     ).write_text(json.dumps(s.get("body"), indent=1,
                                             default=str)[:500_000])
                _save_session({"cases": sess_cases})
                _log("case %s terminal %s" % (cid, status))
                return time.time() - t_start
        elif r.get("http_status") is None:
            _log("case %s poll hiccup: %s" % (cid, str(r.get("error"))[:80]))
        time.sleep(POLL_INTERVAL_S)
    _log("case %s slice exhausted (still running)" % cid)
    return time.time() - t_start


def main() -> int:
    budget_min = float(sys.argv[1]) if len(sys.argv) > 1 else 25.0
    if not HF_TOKEN:
        print("FATAL: HF_TOKEN absent from env")
        return 2
    v = _req("/api/version", timeout=60)
    eng = ((v.get("body") or {}).get("engine_commit")
           if v.get("http_status") == 200 else "?")
    _log("deployed engine_commit=%s (expect 4d4964e89a6f)" % str(eng)[:12])
    sess = _load_session()
    sess_cases = sess.get("cases", {})
    budget_s = budget_min * 60
    t_slice = time.time()
    for case in CASES:
        if sess_cases.get(case["case"], {}).get("terminal"):
            _log("case %s already terminal, skipping" % case["case"])
            continue
        left = budget_s - (time.time() - t_slice)
        if left < 120:
            _log("slice budget exhausted")
            break
        _drive_case(case, sess_cases, left)
    _save_session({"cases": sess_cases})
    done = sum(1 for c in CASES
               if sess_cases.get(c["case"], {}).get("terminal"))
    OUT.write_text(json.dumps(
        {"artifact": "R513_REMOVAL_BATTERY/1.0",
         "deployed_engine_commit": eng,
         "cases": sess_cases,
         "terminal_count": done,
         "reviewer_provenance": "AI_REVIEW"}, indent=1))
    _log("%d/5 cases terminal" % done)
    return 0 if done == 5 else 1


if __name__ == "__main__":
    raise SystemExit(main())
