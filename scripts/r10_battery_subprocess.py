#!/usr/bin/env python3
"""r10_battery_subprocess.py — the R10 live A0+ battery, SUBPROCESS
model (owner round 2026-11-13): ONE arm invocation per problem, each
with its own gateway start-or-probe (the measured reaper race kills a
long-lived gateway node mid-battery; the runner's per-item subprocess
model isolates it). Typed: a problem's transport failure is recorded
and the battery continues; ONE immediate typed retry per problem."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

from r7_queue_runner import _load_key_vault  # noqa: E402

names = _load_key_vault()
print("[r10bat2] vault loaded (names only):", sorted(names))
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location(
    "r7_a0plus_mod", REPO / "scripts" / "r7_a0plus.py")
A0P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A0P)

ids = sys.argv[1:] or A0P._arm_queue_ids()
print("[r10bat2] subprocess battery queue:", len(ids), "problems")
t0 = time.time()
results = {}
for pid in ids:
    print(f"\n=== [r10bat2] {pid} (elapsed {round(time.time()-t0,1)}s) ===")
    env = dict(os.environ)
    env["ENGINE_LLM_TIMEOUT_S"] = "40"
    env["ENGINE_LLM_RETRY_SLEEP_S"] = "0"
    env["A0P_QUEUE_WAIT_S"] = f"{max(0.0, time.time() - t0):.1f}"
    gw_t0 = time.time()
    gw_ok = False
    for _try in (1, 2):
        gw = subprocess.run(["bash", "scripts/zai_gateway_env.sh"],
                            cwd=str(REPO), capture_output=True, text=True,
                            timeout=90)
        lines = (gw.stdout or "").splitlines()
        if gw.returncode == 0 and any(
                l.startswith("export ") for l in lines):
            for line in lines:
                line = line.strip()
                if line.startswith("export ") and "=" in line:
                    k, v = line[len("export "):].split("=", 1)
                    env[k] = v
            gw_ok = True
            break
    env["A0P_GATEWAY_SETUP_S"] = f"{round(time.time() - gw_t0, 1):.1f}"
    if not gw_ok:
        print(f"[r10bat2] {pid}: TYPED gateway unavailable this window")
        results[pid] = {"exit": 3, "state": "GATEWAY_UNAVAILABLE"}
        continue
    cmd = [sys.executable, "-B", "scripts/r7_a0plus.py", pid]
    proc = subprocess.run(cmd, cwd=str(REPO), env=env,
                          capture_output=True, text=True, timeout=900)
    tail = ((proc.stdout or "") + "\n--stderr--\n" +
            (proc.stderr or "")).strip().splitlines()
    for ln in tail[-4:]:
        print("   ", ln[:150])
    rec_f = A0P.PAIRS_A0 / f"{pid}.json"
    state = "NO_RECORD"
    if rec_f.exists():
        try:
            state = json.loads(rec_f.read_text(
                encoding="utf-8")).get("result") or "?"
        except Exception:  # noqa: BLE001
            state = "UNREADABLE"
    if proc.returncode == 3 and state == "NO_RECORD":
        print(f"[r10bat2] {pid}: transport-failed — ONE immediate "
              "typed retry (fresh gateway)")
        proc = subprocess.run(cmd, cwd=str(REPO), env=env,
                              capture_output=True, text=True,
                              timeout=900)
        for ln in tail[-4:]:
            print("   ", ln[:150])
        if rec_f.exists():
            try:
                state = json.loads(rec_f.read_text(
                    encoding="utf-8")).get("result") or "?"
            except Exception:  # noqa: BLE001
                state = "UNREADABLE"
    results[pid] = {"exit": proc.returncode, "state": state}
    print(f"[r10bat2] {pid}: exit={proc.returncode} result={state}")

print("\n[r10bat2] SUMMARY (exit/result):")
for pid, r in results.items():
    print(f"  {pid}: exit={r['exit']} result={r['state']}")
print(f"[r10bat2] total wall {round(time.time()-t0,1)}s")
