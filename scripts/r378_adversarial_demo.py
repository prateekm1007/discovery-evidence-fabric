"""R378 — ADVERSARIAL LIVE DEMONSTRATION of the TECHNICAL IMPROVEMENT
ENGINE on a fresh, difficult, arbitrary NON-medical problem where the
answer is NOT obvious:

  offshore wind turbine blade leading-edge rain/hail erosion

(w7; the R377 stress set used solder thermal cycling, titanium
grinding, propeller cavitation — this domain is fresh to the engine:
no prior run, no cached art, no contamination).

The demonstration runs the LIVE production loop:
  evidence retrieval (live scholarly sources, free)
  -> synthesis (zai gateway, glm-4-plus)
  -> mechanism-centered collision with PatentBear (CEO-designated
     patent source; persistent quota guard; Lens 429-exhausted and
     Google 503 are recorded honestly as UNRESOLVED_SOURCE_FAILURE)
  -> engineering attack -> survivor selection
  -> THE IMPROVEMENT PASS (integrated in the post-rank pipeline):
     DIAGNOSE -> CONTROLLED MUTATION (zai proposal, deterministically
     validated) -> FULL RE-EVALUATION (REPLAY_CACHE re-adjudication
     against the run's OWN live-found hash-custodied family texts)
     -> RE-SCORE (frozen Q + I instruments) -> KEEP OR KILL ->
     IMPROVE AGAIN

Budget discipline (measured before launch): PatentBear meter showed 8
searches remaining (5 will be spent by the collision ladder's 5 query
classes; the reserve floor 2 is guarded; 1 spare remains).

Reproduction:
  bash scripts/zai_gw_run.sh python scripts/r378_adversarial_demo.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

PROBLEM = REPO / "scripts" / "r378_adversarial_problem.json"
RUN_DIR = REPO / "ENGINE_RUNS" / "w7_energy_offshore_wind_blade_leading_edge_erosion"


def main() -> int:
    env = {
        # transport: the zai gateway wrapper already pins synthesis /
        # attack / grid providers; the improvement proposer follows
        "ENGINE_IMPROVEMENT_PROVIDER": "zai",
        # patent source: the CEO-designated PatentBear (opt-in, quota
        # guarded) — google (503) and lens (429) are still queried by
        # default alongside? NO: the override replaces the list; the
        # failed free sources are recorded as UNRESOLVED_SOURCE_FAILURE
        # in the ladder errors either way (the engine records google +
        # lens failures per query; passing them keeps the honest record
        # AND spends nothing — they fail without cost).
        "ENGINE_COLLISION_SOURCES": "google_patents,lens_patent,patentbear",
    }
    cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
           "--problem-json", str(PROBLEM),
           "--out", str(RUN_DIR)]
    import os
    for k, v in env.items():
        os.environ[k] = v
    print("[adversarial] engine run starting (live loop, PatentBear "
          "collision, integrated improvement pass)...", flush=True)
    r = subprocess.run(cmd, cwd=str(REPO))
    print(f"[adversarial] engine exit code: {r.returncode}", flush=True)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
