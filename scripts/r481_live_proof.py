#!/usr/bin/env python3
"""R481 — the P0-1 LIVE PROOF: a fresh production run through the REAL
user path on the deployed union (identity a3ed021, atria transport),
harvesting the IMPROVE stage's execution from the run's own records.

The audit's exit criterion (verbatim): a live V1 -> kill -> V2 loop —
"no candidate has yet died and re-entered as a mutated child" is the
score-blocking fact. THIS script submits ONE genuinely fresh problem
(never submitted to any environment), waits through the REAL run, and
reads the IMPROVE stage's typed outcome from the run's stage_log (the
canonical state projection — never internal state, the R450 capture
discipline):

  typed outcomes (the record, whatever it says — Art. VI):
    LOOP_CLOSED_ADMITTED   — >=1 dead candidate mutated and its child
                             RE-ENTERED the gauntlet (CHILDREN_ADMITTED).
    LOOP_CLOSED_REKILLED   — the child re-entered and died again
                             (NO_CHILD_ADMITTED — an honest closure).
    NO_KILL_EVIDENCE       — nothing died in this run's gauntlet; the
                             stage typed its honest skip (the live
                             execution IS proven; the closure awaits a
                             run with kills — the campaign's work).
    STAGE_FAILURE / others — recorded verbatim, never dressed.

Slice-resumable: the session persists to R481/LIVE_PROOF_SESSION.json
(redacted of the owner key — BS-021); re-invoke to resume the SAME run.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, Optional

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE = "https://prateekm1-toscanini-prod-validation.hf.space"
OUT = REPO_ROOT / "R481" / "LIVE_PROOF.json"
# the REAL session (with the owner capability) lives OUTSIDE the
# tracked tree (BS-021: a session capability never lands in git);
# the tracked R481/LIVE_PROOF_SESSION.json stays redacted
SESSION = Path("/home/z/my-project/scripts/r481_live_session.json")
SESSION_TRACKED = REPO_ROOT / "R481" / "LIVE_PROOF_SESSION.json"
POLL_DEADLINE_S = 60 * 60          # one hour per invocation slice
POLL_INTERVAL_S = 25
EXPECTED_IDENTITY = os.environ.get(
    "EXPECTED_IDENTITY", "a3ed02165deafe78cb6bff79d110c7ca5cd7227e")

HF_TOKEN = (os.environ.get("HF_TOKEN", "").strip()
            or "")
if not HF_TOKEN:
    p = Path("/home/z/my-project/.secrets.env")
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith("HF_TOKEN="):
                HF_TOKEN = line.split("=", 1)[1].strip()

# The problem: authored for THIS proof, never submitted anywhere —
# geothermal wellhead scale + flash-vessel deposition (a
# thermodynamics + surface-chemistry + two-phase flow problem,
# mechanically distinct from every prior case: hydro runner erosion,
# battery thermal runaway, conveyor idlers, district heating, hospital
# heat pump, seawater condensers, slurry pumps, crew rostering).
CASE_TEXT = (
    "A 12-well intermediate-enthalpy geothermal field loses 6 to 11 "
    "percent of delivered thermal output every quarter: calcite scales "
    "out of the flashed brine onto the wellhead cyclone separators and "
    "the flash-vessel internals within 45 to 60 days of operation, "
    "silica gel then deposits downstream of the separator at a rate "
    "that plugs the injection headers within a season, and the current "
    "response — quarterly acid washes with the plant online at reduced "
    "load — corrodes the carbon-steel vessel lining and cannot reach "
    "the cyclone vortex finder without a full shutdown. Design a "
    "scale-management arrangement that keeps the separator pressure "
    "drop below 8 kilopascals across a full 90-day operating window, "
    "holds the injection-water silica below 120 parts per million "
    "without raising the brine temperature above the reservoir limit "
    "of 180 degrees Celsius, tolerates brine calcium concentrations up "
    "to 900 milligrams per liter, fits inside the existing vessel "
    "geometry without welding on the pressure boundary, and can be "
    "serviced during the planned 4-day annual outage with equipment "
    "already on site.")


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, owner_key: Optional[str] = None):
    import urllib.error
    import urllib.request
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json",
               "Authorization": f"Bearer {HF_TOKEN}"}
    if owner_key:
        headers["X-Tosca-Owner"] = owner_key
    req = urllib.request.Request(BASE + path, data=data, headers=headers,
                                 method="POST" if data is not None
                                 else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return {"http_status": r.status,
                    "body": json.loads(r.read() or b"{}")}
    except urllib.error.HTTPError as e:
        try:
            txt = e.read()[:300].decode(errors="replace")
        except Exception:  # noqa: BLE001
            txt = ""
        return {"http_status": e.code, "error": txt}
    except Exception as exc:  # noqa: BLE001
        return {"http_status": None,
                "error": f"{type(exc).__name__}: {exc}"}


def _resume() -> Dict[str, Any]:
    if SESSION.exists():
        try:
            return json.loads(SESSION.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {}


def main() -> int:
    sess = _resume()
    entry = sess.get("case") or {}
    record: Dict[str, Any] = sess.get("record") or {}

    # 0. identity gate: the union must be what production serves
    v = _req("/api/version")
    served = (v.get("body") or {}).get("engine_commit", "")
    if served != EXPECTED_IDENTITY:
        print(f"identity gate: production serves {served[:12]}, "
              f"expected {EXPECTED_IDENTITY[:12]} — the build may still "
              f"be rolling; re-invoke in a few minutes")
        return 2
    print(f"[r481-proof] identity verified: {served[:12]}")

    # 1. submit (once; resumable)
    if not entry.get("run_id"):
        r = _req("/api/run", body={"text": CASE_TEXT}, timeout=180)
        if r.get("http_status") not in (200, 202):
            print(f"submit failed {r.get('http_status')} "
                  f"{str(r.get('error'))[:200]}")
            return 1
        b = r.get("body") or {}
        entry = {"run_id": b.get("session_id") or b.get("run_id"),
                 "owner_key": b.get("owner_key"),
                 "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                               time.gmtime())}
        print(f"[r481-proof] submitted {entry['run_id']}")
    sess["case"] = entry
    sess["record"] = record
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(sess, indent=1))
    sess_redacted = json.loads(json.dumps(sess))
    if sess_redacted.get("case", {}).get("owner_key"):
        sess_redacted["case"]["owner_key"] = "(redacted, BS-021)"
    SESSION_TRACKED.write_text(json.dumps(sess_redacted, indent=1))

    sid, owner = entry["run_id"], entry.get("owner_key")

    # 2. poll to terminal
    t0 = time.time()
    final = None
    while time.time() - t0 < POLL_DEADLINE_S:
        r = _req(f"/api/run/{sid}/result", owner_key=owner, timeout=90)
        if r.get("http_status") == 200:
            body = r.get("body") or {}
            st = str(body.get("status") or "").upper()
            if st in ("COMPLETE", "FAILED", "ERROR", "DONE",
                      "INTERRUPTED", "RUN_BLOCKED_TRANSPORT",
                      "RUN_BLOCKED_CAPABILITY"):
                final = body
                print(f"[r481-proof] terminal: {st}")
                break
            if st:
                print(f"[r481-proof] ... {st}")
        elif r.get("http_status") not in (200, 404):
            print(f"[r481-proof] poll {r.get('http_status')} "
                  f"{str(r.get('error'))[:120]}")
        time.sleep(POLL_INTERVAL_S)
    if final is None:
        print("[r481-proof] slice deadline reached — re-invoke to "
              "resume the SAME run (the session persists)")
        return 2

    # 3. harvest the IMPROVE stage's entries from the canonical state
    st = _req(f"/api/run/{sid}/state", owner_key=owner, timeout=120)
    state = st.get("body") or {}
    stage_log = (state.get("stage_log")
                 or state.get("env", {}).get("stage_log") or [])
    improve_entries = [e for e in stage_log
                       if e.get("stage") == "IMPROVE"]
    final_status = (final.get("status")
                    or state.get("final_status") or "")
    record.update({
        "run_id": sid, "final_status": final_status,
        "identity_verified": served[:12],
        "submitted_at": entry.get("submitted_at"),
        "terminal_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "stage_count": len(stage_log),
        "improve_entries": improve_entries,
    })
    statuses = [e.get("result_meta", {}).get("status")
                for e in improve_entries]
    print(f"[r481-proof] IMPROVE entries: {statuses}")

    if any(s == "CHILDREN_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_ADMITTED"
        code = 0
    elif any(s == "NO_CHILD_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_REKILLED"
        code = 0
    elif any(s == "NO_KILL_EVIDENCE" for s in statuses if s):
        record["proof_outcome"] = "NO_KILL_EVIDENCE"
        code = 0
    elif not improve_entries:
        record["proof_outcome"] = "IMPROVE_ABSENT"
        code = 3
    else:
        record["proof_outcome"] = "STAGE_" + "_".join(
            str(s) for s in statuses if s)[:60]
        code = 3

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    print(f"[r481-proof] outcome: {record['proof_outcome']} -> {OUT}")
    sess["record"] = json.loads(json.dumps(record, default=str))
    SESSION.write_text(json.dumps(sess, indent=1))
    sess_redacted = json.loads(json.dumps(sess))
    if sess_redacted.get("case", {}).get("owner_key"):
        sess_redacted["case"]["owner_key"] = "(redacted, BS-021)"
    SESSION_TRACKED.write_text(json.dumps(sess_redacted, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
