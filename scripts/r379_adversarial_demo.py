"""R379 — ADVERSARIAL LIVE DEMONSTRATION of the TECHNICAL IMPROVEMENT
ENGINE V2 on a fresh, difficult, arbitrary NON-CereVasc problem:

  tunneled cuffed hemodialysis catheter flow dysfunction

(w8; fresh to the engine: no prior run, no cached art, no
contamination. Chosen deliberately for a QUANTITATIVE clinical
literature: blood flow rates, pressure limits, recirculation
fractions — the quantities the structured technical state extracts
from custodied evidence with verbatim spans.)

The demonstration runs the LIVE production loop with BOTH improvement
layers, in the CEO's composed order:
  evidence retrieval (live scholarly sources, free)
  -> synthesis (zai gateway, glm-4-plus)
  -> mechanism-centered collision (PatentBear opt-in; google/lens
     failures recorded honestly per query)
  -> engineering attack -> survivor selection
  -> R378 EPISTEMIC improvement pass (wording-level; unchanged)
  -> R379 TECHNICAL improvement pass (design-variable level; NEW):
     extraction (untrusted LLM proposal -> deterministic span
     verification) -> technical diagnosis (limiting variable +
     direction) -> technical mutation (an ACTUAL design variable,
     inside evidence-declared envelopes) -> INDEPENDENT technical
     re-evaluation + prior-art recheck + both instruments ->
     KEEP/KILL -> SECOND IMPROVEMENT -> attribution.

The child must prove it is TECHNICALLY better (objective direction
confirmed on its own re-evaluation, constraints preserved) — a score
increase is never sufficient (CEO R379 items 4/8).

Reproduction:
  bash scripts/zai_gw_run.sh python scripts/r379_adversarial_demo.py
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

PROBLEM = REPO / "scripts" / "r379_adversarial_problem.json"
RUN_DIR = REPO / "ENGINE_RUNS" / \
    "w8_nephrology_tunneled_dialysis_catheter_flow_dysfunction"


def main() -> int:
    env = {
        # transport: the zai gateway pins synthesis/attack/grid
        # providers; BOTH improvement proposers follow
        "ENGINE_IMPROVEMENT_PROVIDER": "zai",
        "ENGINE_TECHNICAL_PROVIDER": "zai",
        # patent source: the CEO-designated PatentBear (opt-in, quota
        # guarded); google (503) and lens (429) are recorded honestly
        # as UNRESOLVED_SOURCE_FAILURE per query
        "ENGINE_COLLISION_SOURCES": "google_patents,lens_patent,patentbear",
    }
    cmd = [sys.executable, "-m", "discovery_fabric.engine.run",
           "--problem-json", str(PROBLEM),
           "--out", str(RUN_DIR)]
    for k, v in env.items():
        os.environ[k] = v
    print("[adversarial-v2] engine run starting (live loop, both "
          "improvement layers: epistemic + technical)...", flush=True)
    r = subprocess.run(cmd, cwd=str(REPO))
    print(f"[adversarial-v2] engine exit code: {r.returncode}", flush=True)
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
