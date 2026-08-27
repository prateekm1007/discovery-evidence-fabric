#!/usr/bin/env python3
"""scripts/a12_batch_driver.py — run the A12 capstone across the canonical
problem manifest until ONE genuine problem produces a RELEASED package.

Discovery reality: most candidates die at the adversarial attack (that is
the engine working — every kill is recorded with its reason). This driver
iterates the canonical problems, resume-capable, and stops at the first
full RELEASED package. The operator provider override (ENGINE_*_PROVIDER)
is explicit and printed by the engine itself on every call (CEO E1: never
a silent substitution).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def main() -> int:
    from discovery_fabric.a2.run import PROBLEM_MANIFEST
    problem_ids = list(PROBLEM_MANIFEST.keys())[:10] \
        if isinstance(PROBLEM_MANIFEST, dict) else \
        [p.get("problem_id") for p in PROBLEM_MANIFEST][:10]
    print(f"[batch] canonical problems: {problem_ids}", flush=True)
    released_dir = None
    for pid in problem_ids:
        if released_dir:
            break
        for attempt in range(1, 4):   # resume-capable relaunches per problem
            env = dict(os.environ)
            env["A12_PROBLEM_ID"] = pid
            print(f"[batch] === problem {pid} attempt {attempt} ===",
                  flush=True)
            proc = subprocess.run(
                [sys.executable, "-u", str(REPO / "scripts" /
                                           "a12_capstone_run.py")],
                env=env, cwd=str(REPO), capture_output=True, text=True,
                timeout=560)
            tail = proc.stdout.strip().splitlines()[-6:]
            for line in tail:
                print(f"[batch]   {line}", flush=True)
            if "release=RELEASED" in proc.stdout:
                released_dir = "ok"
                break
            # an honest REJECTED (attack kill) is final for this problem;
            # only infra kills/timeouts justify relaunching the same problem
            if "final_status=REJECTED" in proc.stdout and \
                    "SURVIVOR_GATE" in proc.stdout:
                break
            time.sleep(3)
    print(f"[batch] DONE released={bool(released_dir)}", flush=True)
    return 0 if released_dir else 1


if __name__ == "__main__":
    raise SystemExit(main())
