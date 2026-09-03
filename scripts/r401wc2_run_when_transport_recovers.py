#!/usr/bin/env python3
"""scripts/r401wc2_run_when_transport_recovers.py — the ONE entry
point for the transport-blocked measurements (R401-WC2).

The z.ai upstream quota was measured EXHAUSTED (HTTP 429 'Too many
requests', continuous 14:07 onward, 2026-09-03). Four measurements are
built and frozen, waiting only on the transport:

  1. the operator proof (directive 2)  — scripts/r401wc2_operator_proof.py
  2. the benchmark battery (directive 3) — scripts/r401wc2_benchmark_run.py
  3. the attacker calibration (directive 4) — scripts/r401wc2_attacker_calibration.py
  4. the model contest (directive 7)    — scripts/r401wc2_model_contest.py

This orchestrator probes the transport first (an honest BLOCKED state
stops it cleanly, Art. XXV), then runs each measurement in order, and
records the session state after each (every driver is itself
resumable). It is idempotent: completed measurements (their output
records exist) are skipped unless --force.

Usage:
  python3 scripts/r401wc2_run_when_transport_recovers.py [--only 2,3]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

STATE_PATH = REPO_ROOT / "R401-WC2" / "TRANSPORT_SESSION_STATE.json"

MEASUREMENTS = {
    "2": {
        "name": "operator proof (directive 2)",
        "script": "scripts/r401wc2_operator_proof.py",
        "done_marker": REPO_ROOT / "R401-WC2" / "OPERATOR_PROOF" /
        "OPERATOR_PROOF_SUMMARY.json",
    },
    "3": {
        "name": "benchmark battery (directive 3)",
        "script": "scripts/r401wc2_benchmark_run.py --problems 2",
        "done_marker": REPO_ROOT / "R401-WC2" / "BENCHMARK" / "RUNS" /
        "BATTERY_STATE.json",
    },
    "4": {
        "name": "attacker calibration (directive 4)",
        "script": "scripts/r401wc2_attacker_calibration.py --resume",
        "done_marker": REPO_ROOT / "R401-WC2" / "ATTACKER_CALIBRATION" /
        "CALIBRATION_RESULTS.json",
    },
    "7": {
        "name": "model contest (directive 7)",
        "script": "scripts/r401wc2_model_contest.py",
        "done_marker": REPO_ROOT / "R401-WC2" / "MODEL_CONTEST" /
        "MODEL_CONTEST_RESULTS.json",
    },
}


def _load_key() -> str:
    kv = {}
    p = REPO_ROOT / ".env.keys"
    if p.exists():
        for line in p.read_text().splitlines():
            m = re.match(r"^([A-Z_]+)=(.*)$", line.strip())
            if m:
                kv[m.group(1)] = m.group(2)
    return kv.get("ZAI_API_KEY", "")


def _probe_transport() -> dict:
    """One tiny direct CLI call — the honest transport state."""
    r = subprocess.run(
        ["z-ai", "chat", "--prompt", "Reply with exactly: TRANSPORT_OK",
         "-o", "/tmp/r401wc2_transport_probe.json"],
        capture_output=True, text=True, timeout=180)
    try:
        content = json.loads(
            Path("/tmp/r401wc2_transport_probe.json").read_text()
        ).get("content") or ""
    except Exception:  # noqa: BLE001
        content = ""
    ok = "TRANSPORT_OK" in content
    return {"ok": ok,
            "rc": r.returncode,
            "error": (r.stderr or r.stdout or "")[-200:]
            if not ok else None,
            "probed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                       time.gmtime())}


def _load_state() -> dict:
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text())
        except Exception:  # noqa: BLE001
            pass
    return {"runs": {}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="",
                    help="comma-separated measurement ids to run "
                         "(default: all)")
    ap.add_argument("--force", action="store_true",
                    help="re-run even when the done-marker exists")
    args = ap.parse_args()

    state = _load_state()
    state["last_attempt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                          time.gmtime())
    probe = _probe_transport()
    state["transport_probe"] = probe
    print(f"[orchestrator] transport: "
          f"{'OK' if probe['ok'] else 'BLOCKED'}")
    if not probe["ok"]:
        state["state"] = ("TRANSPORT_BLOCKED (honest state; the z.ai "
                          "429 quota window; re-run this orchestrator "
                          "— every driver is resumable)")
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=1))
        print(json.dumps(probe, indent=1))
        return 3

    order = [k for k in ("2", "3", "4", "7")
             if not args.only or k in args.only.split(",")]
    for mid in order:
        m = MEASUREMENTS[mid]
        if m["done_marker"].exists() and not args.force:
            print(f"[orchestrator] {mid} ({m['name']}): done-marker "
                  f"exists — skipping (use --force to re-run)")
            state["runs"][mid] = {"status": "DONE (marker present)"}
            continue
        print(f"[orchestrator] running {mid} ({m['name']})...")
        t0 = time.time()
        r = subprocess.run(
            [sys.executable, str(REPO_ROOT / m["script"])] +
            [a for a in m["script"].split()[1:]],
            cwd=str(REPO_ROOT), capture_output=True, text=True)
        elapsed = round(time.time() - t0, 1)
        state["runs"][mid] = {
            "status": "RUN" if r.returncode == 0 else
            f"EXIT_{r.returncode}",
            "elapsed_s": elapsed,
            "stdout_tail": (r.stdout or "")[-1500:],
            "stderr_tail": (r.stderr or "")[-800:],
            "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ",
                                         time.gmtime()),
        }
        print(f"[orchestrator] {mid}: rc={r.returncode} ({elapsed}s)")
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, indent=1))
    state["state"] = "SESSION_COMPLETE (see per-measurement records)"
    STATE_PATH.write_text(json.dumps(state, indent=1))
    print(f"[orchestrator] state -> {STATE_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
