#!/usr/bin/env python3
"""R484 — the loop-closure DECISIVE proof (the unloseable-evidence build): the SAME geothermal problem
that structurally failed three consecutive production runs (the
title-only paper + the free-leg hijack), re-submitted through the REAL
user path on the deployed R484 build (identity b0f3e913 — the checkpoint-timer build; the kill-point record can no longer die with the container), measured for:

  1. THE ROUTE   — which rung served SYNTHESIZE (the credited atria leg
                   is the expected head under the R469 operator pin +
                   the R483 zai-pin retirement + the re-point
                   reconciliation).
  2. THE GATE    — the served paper carries a quotable abstract (the
                   R483 abstract-bearing gate; the title-only specimen
                   doi:10.1186/s40517-019-0138-3 is excluded, recorded).
  3. THE SPAN    — evidence_verified TRUE (the loop closure's blocker
                   class gone) or the honest typed remainder.
  4. THE LOOP    — the IMPROVE stage's typed outcome from the durable
                   state (the R481 lesson: the durable branch is the
                   authority; the /state projection carries no raw
                   stage_log).

Typed proof outcomes (the record, whatever it says — Art. VI):
  LOOP_CLOSED_ADMITTED / LOOP_CLOSED_REKILLED / NO_KILL_EVIDENCE /
  IMPROVE_ABSENT — the R481 vocabulary, unchanged.

Slice-resumable: the session persists OUTSIDE the tracked tree
(/home/z/my-project/scripts/r484_live_session.json — BS-021: the owner
capability never lands in git; the tracked copy stays redacted).
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
OUT = REPO_ROOT / "R484" / "LIVE_PROOF.json"
SESSION = Path("/home/z/my-project/scripts/r484_live_session.json")
SESSION_TRACKED = REPO_ROOT / "R484" / "LIVE_PROOF_SESSION.json"
POLL_DEADLINE_S = 60 * 80
POLL_INTERVAL_S = 25
EXPECTED_IDENTITY = os.environ.get(
    "EXPECTED_IDENTITY", "b0f3e91337460c27028ebbcedbbfd522999d2247")

# the SAME problem text as R481/R482 (the decisive comparison: the
# retrieval that twice surfaced the title-only record)
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


def _durable_harvest(session_id: str) -> Dict[str, Any]:
    """Read the run's envelopes from the durable branch (the authority,
    the R481 lesson). Best-effort: the worker pushes its checkpoints —
    a lagging branch returns an empty harvest and the driver records
    that state honestly."""
    out: Dict[str, Any] = {}
    try:
        subprocess.run(["git", "fetch", "origin", "runtime-state-hf"],
                       cwd=REPO_ROOT, capture_output=True, timeout=120)
        tree = subprocess.run(
            ["git", "ls-tree", "--name-only", "origin/runtime-state-hf:runs"],
            cwd=REPO_ROOT, capture_output=True, text=True,
            timeout=60).stdout.split()
        cand = [t for t in tree if "calcite_and_silica" in t]
        if not cand:
            return {"harvested": False, "reason": "run dir not on the durable branch yet"}
        # pick the dir whose problem_understanding session matches: the
        # newest candidate dir (the R483 run is the latest submission)
        dirs = sorted(cand)
        rdir = dirs[-1]
        out["durable_run_dir"] = rdir
        for env in ("SYNTHESIZE", "VERIFY", "IMPROVE", "ADJUDICATION"):
            p = subprocess.run(
                ["git", "show", f"origin/runtime-state-hf:runs/{rdir}/envelope_{env}.json"],
                cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
            if p.returncode != 0:
                continue
            try:
                d = json.loads(p.stdout)
            except Exception:  # noqa: BLE001
                continue
            if env == "SYNTHESIZE":
                rc = ((d.get("mechanism_map") or {}).get("raw_candidate")
                      or {})
                se = rc.get("source_evidence") or {}
                out["synthesis_route"] = {
                    "provider": rc.get("provider"),
                    "model": rc.get("model"),
                    "source_id": se.get("source_id"),
                    "source_span_chars": len(se.get("source_span") or ""),
                    "span_corrective_retry": rc.get(
                        "span_corrective_retry"),
                    "synthesis_rotation": rc.get("synthesis_rotation"),
                }
            elif env == "VERIFY":
                ev = ((d.get("adjudication") or {})
                      .get("evidence_verification") or {})
                out["verify"] = {
                    "verified": ev.get("verified"),
                    "issues": ev.get("issues"),
                    "span_extraction": ev.get("span_extraction"),
                    "verifier_assist": ev.get("verifier_assist"),
                }
            elif env == "IMPROVE":
                sl = d.get("stage_log") or []
                out["improve_entries"] = [
                    {k: e.get(k) for k in ("stage", "status", "result_meta")}
                    for e in sl if e.get("stage") == "IMPROVE"]
        out["harvested"] = True
    except Exception as exc:  # noqa: BLE001 — honest harvest failure
        out["harvested"] = False
        out["reason"] = f"{type(exc).__name__}: {exc}"
    return out


HF_TOKEN = (os.environ.get("HF_TOKEN", "").strip() or "")
if not HF_TOKEN:
    p = Path("/home/z/my-project/.secrets.env")
    if p.exists():
        for line in p.read_text().splitlines():
            if line.startswith("HF_TOKEN="):
                HF_TOKEN = line.split("=", 1)[1].strip()


def main() -> int:
    sess = _resume()
    entry = sess.get("case") or {}
    record: Dict[str, Any] = sess.get("record") or {}

    v = _req("/api/version")
    served = (v.get("body") or {}).get("engine_commit", "")
    if served != EXPECTED_IDENTITY:
        print(f"[r484-proof] identity gate: production serves "
              f"{served[:12]}, expected {EXPECTED_IDENTITY[:12]}")
        return 2
    print(f"[r484-proof] identity verified: {served[:12]}")

    if not entry.get("run_id"):
        r = _req("/api/run", body={"text": CASE_TEXT}, timeout=180)
        if r.get("http_status") not in (200, 202):
            print(f"[r484-proof] submit failed {r.get('http_status')} "
                  f"{str(r.get('error'))[:200]}")
            return 1
        b = r.get("body") or {}
        entry = {"run_id": b.get("session_id") or b.get("run_id"),
                 "owner_key": b.get("owner_key"),
                 "submitted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                               time.gmtime())}
        print(f"[r484-proof] submitted {entry['run_id']}")
    sess["case"] = entry
    sess["record"] = record
    SESSION.parent.mkdir(parents=True, exist_ok=True)
    SESSION.write_text(json.dumps(sess, indent=1))
    sess_redacted = json.loads(json.dumps(sess))
    if sess_redacted.get("case", {}).get("owner_key"):
        sess_redacted["case"]["owner_key"] = "(redacted, BS-021)"
    SESSION_TRACKED.parent.mkdir(parents=True, exist_ok=True)
    SESSION_TRACKED.write_text(json.dumps(sess_redacted, indent=1))

    sid, owner = entry["run_id"], entry.get("owner_key")

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
                print(f"[r484-proof] terminal: {st}")
                break
            if st:
                print(f"[r484-proof] ... {st}")
        elif r.get("http_status") not in (200, 404):
            print(f"[r484-proof] poll {r.get('http_status')} "
                  f"{str(r.get('error'))[:120]}")
        time.sleep(POLL_INTERVAL_S)
    if final is None:
        print("[r484-proof] slice deadline reached — re-invoke to "
              "resume the SAME run")
        return 2

    # 3. the durable harvest (the authority for stage_log + routes)
    time.sleep(90)  # the worker's durable checkpoint cadence
    durable = _durable_harvest(sid)
    record.update({
        "run_id": sid,
        "final_status": (final.get("status") or ""),
        "final_reason": str(final.get("reason") or "")[:500],
        "identity_verified": served[:12],
        "submitted_at": entry.get("submitted_at"),
        "terminal_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                     time.gmtime()),
        "durable": durable,
    })

    imp = durable.get("improve_entries") or []
    statuses = [e.get("status") for e in imp]
    print(f"[r484-proof] IMPROVE entries: {statuses}")
    print(f"[r484-proof] synthesis route: "
          f"{json.dumps(durable.get('synthesis_route'))[:300]}")
    print(f"[r484-proof] verify: "
          f"{json.dumps(durable.get('verify'))[:300]}")

    if any(s == "CHILDREN_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_ADMITTED"
        code = 0
    elif any(s == "NO_CHILD_ADMITTED" for s in statuses if s):
        record["proof_outcome"] = "LOOP_CLOSED_REKILLED"
        code = 0
    elif any(s == "NO_KILL_EVIDENCE" for s in statuses if s):
        record["proof_outcome"] = "NO_KILL_EVIDENCE"
        code = 0
    elif durable.get("harvested") and not imp:
        record["proof_outcome"] = "IMPROVE_ABSENT"
        code = 3
    elif not durable.get("harvested"):
        record["proof_outcome"] = "DURABLE_HARVEST_PENDING"
        code = 3
    else:
        record["proof_outcome"] = "STAGE_" + "_".join(
            str(s) for s in statuses if s)[:60]
        code = 3

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(record, indent=1, default=str))
    print(f"[r484-proof] outcome: {record['proof_outcome']} -> {OUT}")
    sess["record"] = json.loads(json.dumps(record, default=str))
    SESSION.write_text(json.dumps(sess, indent=1))
    sess_redacted = json.loads(json.dumps(sess))
    if sess_redacted.get("case", {}).get("owner_key"):
        sess_redacted["case"]["owner_key"] = "(redacted, BS-021)"
    SESSION_TRACKED.write_text(json.dumps(sess_redacted, indent=1))
    return code


if __name__ == "__main__":
    sys.exit(main())
