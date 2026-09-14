#!/usr/bin/env python3
"""scripts/r453_production_fresh_run.py — the R453-LEAN-CORE fresh
production-run proof: ONE genuinely fresh problem through the REAL
user path on the DEPLOYED canonical Space at the pushed R453 commit
(f092f1e5 — the adaptive admission + capability fail-closed round).

The problem below was authored for this proof and has NEVER been
submitted to any environment (not the sandbox batteries, not the
R453/NO_CANDIDATE_VERIFY local run — that used the municipal grit
basin problem — not any prior round's cases).

The R453-SPECIFIC production proofs captured here:
  1. the no-candidate path shows skip_reason on the expensive stages
     (the mandate's productionVerification contract);
  2. fewer run-owned LLM lines than assay A's 9 (measured from the
     durable-state routing ledger, from OUTSIDE the container);
  3. the deployed chain records the typed capability state — never a
     pseudo-invention, never a scientific rejection (Art. LXI).

Transport: the fixed owner-capability path (the R447 closure) — run
creation with no cookie; the response carries the caller's own
owner_key; every subsequent request carries X-Tosca-Owner.

Slice-resumable: session persists to R453/PRODUCTION_FRESH_RUN_
SESSION.json; re-invoke to resume the SAME run.

Usage: HF_TOKEN=... GITHUB_TOKEN=... python3 \
    scripts/r453_production_fresh_run.py [poll-minutes]
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
OUT = REPO_ROOT / "R453" / "PRODUCTION_FRESH_RUN.json"
RUNS_DIR = REPO_ROOT / "R453" / "PRODUCTION_FRESH_RUN"
SESSION = REPO_ROOT / "R453" / "PRODUCTION_FRESH_RUN_SESSION.json"
STATE_BRANCH = "runtime-state-hf"

POLL_INTERVAL_S = 30

CASE: Dict[str, str] = {
    "case_id": "r453-fresh-railway-axle-bearing-fluting",
    "directive_class": (
        "R453-LEAN-CORE fresh production-run proof: railway axle-box "
        "electromagnetic fluting — a genuinely fresh problem through "
        "the real user path on the deployed R453 engine (the adaptive-"
        "admission round), on the Space's OWN zero-paid local route"),
    "text": (
        "A regional rail operator runs 25-kilovolt AC electric "
        "multiple units whose axle-box rolling bearings fail by "
        "electromagnetic fluting: raceway surfaces develop washboard "
        "corrugation with a 0.9-millimetre wavelength, axle-box "
        "vibration velocity climbs from 2 to 11 millimetres per "
        "second RMS within a year of overhaul, and measured "
        "shaft-to-frame voltage reaches 8 to 15 volts RMS during "
        "regenerative braking at the 2-kilohertz inverter switching "
        "harmonics. The bearing lubricant film computes to 0.4 to 0.8 "
        "micrometres under the 14-tonne axle load at 320 rpm, and the "
        "operator's audits attribute fluting whenever the voltage "
        "across the film exceeds roughly 3 volts. Four axle-box "
        "failures in the last audit year cost 28,000 euros each "
        "including wheelset removal. The operator needs bearing "
        "raceway fluting eliminated across a 10-year design life at "
        "300,000 kilometres annual duty, without insulated axle-box "
        "bearing retrofits (the approved axle-box envelope and "
        "bearing part number are fixed), without traction inverter "
        "firmware or switching-frequency changes, without adding "
        "maintenance intervals beyond the existing 12-month depot "
        "ultrasonic inspection, and with total added cost per vehicle "
        "held under 3,000 euros."),
}


def _log(msg: str) -> None:
    print(f"[r453-fresh] {msg}", flush=True)


def _req(path: str, body: Optional[Dict[str, Any]] = None,
         timeout: int = 120, owner_key: Optional[str] = None
         ) -> Dict[str, Any]:
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
    ev_state = st.get("evidence_state") or {}
    mech_state = st.get("mechanism_state") or {}
    atk_state = st.get("attack_state") or {}
    rec["chain"] = {
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
    }
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    (RUNS_DIR / f"{session_id}_state.json").write_text(
        json.dumps(st, indent=1, default=str)[:400_000])
    (RUNS_DIR / f"{session_id}_result.json").write_text(
        json.dumps(body, indent=1, default=str)[:400_000])
    return rec


def _fetch_durable_ledger(session_id: str) -> Dict[str, Any]:
    """The run-owned ledger lines from the durable-state branch (from
    OUTSIDE the container) — the LLM-line count for the mandate's
    fewer-than-9 contract."""
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
        lines = []
        if ledger.exists():
            for ln in ledger.open():
                try:
                    lines.append(json.loads(ln))
                except Exception:  # noqa: BLE001
                    pass
        run_lines = [l for l in lines
                     if l.get("session_id") == session_id]
        run_owned = [l for l in run_lines
                     if l.get("call_class") == "RUN_OWNED"]
        paid = [l for l in run_lines
                if (l.get("cost_class") or "") not in
                ("ZERO_PAID_COST_SELF_HOSTED", None)]
        out.update({
            "fetched": True,
            "run_owned_lines": len(run_owned),
            "assay_a_baseline_lines": 9,
            "fewer_than_assay_a": len(run_owned) < 9,
            "paid_cost_lines": len(paid),
            "models": sorted({str(l.get("model")) for l in run_lines}),
            "engine_stages_called": sorted(
                {str(l.get("engine_stage")) for l in run_lines
                 if l.get("engine_stage")}),
            "task_degradation_records": sum(
                1 for l in run_owned if l.get("task_degradation")),
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

    _log("verifying the deployed identity (Art. LXXI)...")
    ver = _version()
    engine_commit = ((ver.get("version") or {}).get("engine_commit"))
    _log(f"deployed engine_commit: {engine_commit}; "
         f"health: {ver.get('health')}")

    if not sess:
        _log("creating the fresh production run (POST /api/run)...")
        created = _create()
        if not created or not created.get("session_id"):
            return 2
        sess = {"session_id": created["session_id"],
                "owner_key": created.get("owner_key"),
                "created": created.get("created")}
        SESSION.write_text(json.dumps(sess, indent=1))
        _log(f"session {sess['session_id']} persisted (slice-resumable)")
    session_id = sess["session_id"]
    owner_key = sess.get("owner_key")
    _log(f"polling run {session_id} for {poll_minutes} min...")
    r = _poll(session_id, owner_key, poll_minutes * 60)
    status = str((r.get("body") or {}).get("status") or
                 r.get("http_status"))
    _log(f"poll slice ended with status: {status}")

    rec: Dict[str, Any] = {
        "artifact_type": "R453_PRODUCTION_FRESH_RUN",
        "recorded_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "baseline": {"deployed_engine_commit": engine_commit,
                     "health": ver.get("health")},
        "session_id": session_id,
        "poll_status": status,
    }
    if str(r.get("http_status")) != "SLICE_DEADLINE":
        rec["run"] = _capture_run(session_id, owner_key)
        rec["durable_provenance"] = _fetch_durable_ledger(session_id)
        SESSION.unlink(missing_ok=True)
        OUT.write_text(json.dumps(rec, indent=1, default=str))
        _log(f"COMPLETE -> {OUT}")
        return 0
    OUT.write_text(json.dumps(rec, indent=1, default=str))
    _log(f"slice record -> {OUT} (re-invoke to continue polling)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
