#!/usr/bin/env python3
"""r10_battery.py — the R10 live A0+ battery driver (owner round
2026-11-13, P0-1): runs the simple arm over DEV12 + the killed
non-DEV12 problems, sequentially, one invocation per problem (the
queue's chunk model). Loads the gitignored vault through the ACTUAL
runner loader, starts-or-probes the zai gateway, and prints every
[a0plus] verdict line. No retries beyond the arm's own typed bounds;
a typed transport failure is recorded and the battery continues.

The per-problem records land in eval/pairs/r10_a0plus/<pid>.json.
"""
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
print("[r10bat] vault loaded (names only):", sorted(names))
os.environ.setdefault("ENGINE_MODEL_COST_POLICY", "UNRESTRICTED")

# the zai gateway env (started-or-probed, one script; ONE immediate
# retry, no fixed sleep)
gw = None
for _try in (1, 2):
    gw = subprocess.run(["bash", "scripts/zai_gateway_env.sh"],
                        cwd=str(REPO), capture_output=True, text=True,
                        timeout=90)
    if gw.returncode == 0 and any(
            l.startswith("export ") for l in
            (gw.stdout or "").splitlines()):
        print("[r10bat] zai gateway admitted")
        for line in (gw.stdout or "").splitlines():
            line = line.strip()
            if line.startswith("export ") and "=" in line:
                k, v = line[len("export "):].split("=", 1)
                os.environ[k] = v
        break
    print(f"[r10bat] gateway attempt {_try} failed (typed) — immediate "
          "retry, no sleep")
else:
    print("[r10bat] TYPED: zai gateway unavailable this window — the "
          "battery cannot run (Art. LXI)")
    sys.exit(3)

import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location(
    "r7_a0plus_mod", REPO / "scripts" / "r7_a0plus.py")
A0P = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A0P)


def _re_admit_gateway() -> bool:
    """Start-or-probe the zai gateway PER PROBLEM (the measured reaper
    race: the probe passes, the background node dies mid-battery; the
    runner's own per-item probe-before-admit rule). One immediate
    retry, no fixed sleep."""
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
                    os.environ[k] = v
            return True
    return False


ids = A0P._arm_queue_ids()
print("[r10bat] battery queue:", len(ids), "problems")
t0 = time.time()
results = {}
for pid in ids:
    print(f"\n=== [r10bat] {pid} (elapsed {round(time.time()-t0,1)}s) ===")
    _re_admit_gateway()
    rc = A0P.run_a0plus(pid)
    rec_f = A0P.PAIRS_A0 / f"{pid}.json"
    state = "NO_RECORD"
    if rec_f.exists():
        try:
            state = json.loads(rec_f.read_text(
                encoding="utf-8")).get("result") or "?"
        except Exception:  # noqa: BLE001
            state = "UNREADABLE"
    if rc == A0P.EXIT_TRANSPORT:
        # ONE immediate typed retry in the same window (the gateway
        # may have just been re-admitted); still no sleep
        print(f"[r10bat] {pid}: transport-failed — ONE immediate typed "
              "retry after gateway re-admission")
        _re_admit_gateway()
        rc = A0P.run_a0plus(pid)
        if rec_f.exists():
            try:
                state = json.loads(rec_f.read_text(
                    encoding="utf-8")).get("result") or "?"
            except Exception:  # noqa: BLE001
                state = "UNREADABLE"
    results[pid] = {"exit": rc, "state": state}
    print(f"[r10bat] {pid}: exit={rc} result={state}")

print("\n[r10bat] SUMMARY (exit/result):")
for pid, r in results.items():
    print(f"  {pid}: exit={r['exit']} result={r['state']}")
print(f"[r10bat] total wall {round(time.time()-t0,1)}s")
