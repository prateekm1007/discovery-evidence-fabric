#!/usr/bin/env python3
"""scripts/r444_smoke_run.py — R444 machinery smoke test.

One throwaway problem (NOT from any frozen instrument: not the R401-WC2
benchmark, not the attacker-calibration domain, not the production
battery) through the CURRENT HEAD engine, to measure per-problem wall
time and confirm the W11 machinery still executes end-to-end before the
real battery burns problems. Art. VIII/LIX discipline: the smoke problem
shares no domain-class overlap concern with the frozen set (it is a
consumer-electronics thermal problem, adjacent to nothing in the frozen
corpus by problem_id, and its only purpose is machinery validation).
"""
from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

SMOKE_PROBLEM = {
    "problem_id": "r444-smoke-thermal-throttle",
    "device": "fanless compact gaming laptop chassis",
    "failure": "sustained CPU thermal throttling collapses frame rates after roughly eight minutes of load because heat accumulates in the sealed chassis faster than the passive heat spreader can move it to the skin",
    "failure_mode": "heat_accumulation",
    "constraint": "hold CPU package temperature below 92 C for a 30-minute sustained load with no fans, no pump, and external skin temperature below 44 C",
    "domain": "consumer-thermal",
}


def main() -> int:
    out_dir = REPO_ROOT / "R444" / "SMOKE"
    out_dir.mkdir(parents=True, exist_ok=True)
    from discovery_fabric.engine.run import EngineRun
    run = EngineRun(SMOKE_PROBLEM, str(out_dir),
                    run_id="r444-smoke-1",
                    package_registry_path=str(out_dir / "PACKAGE_ID_REGISTRY.json"))
    t0 = time.time()
    final = run.run()
    elapsed = round(time.time() - t0, 1)
    print(json.dumps({
        "elapsed_s": elapsed,
        "final_status": final.get("final_status"),
        "final_reason": (final.get("reason") or "")[:300],
        "n_evolution_generations": final.get("n_evolution_generations"),
        "stage_statuses": {
            e.get("stage"): e.get("status")
            for e in (final.get("stage_log") or [])},
    }, indent=1, default=str))
    (out_dir / "SMOKE_RESULT.json").write_text(json.dumps(
        {"elapsed_s": elapsed, "final": final}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
