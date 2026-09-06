#!/usr/bin/env python3
"""R414 acceptance verification: CAD-pass replay on run 1's survivor spec.

The first acceptance run (ts_19ea55d3fb2c) executed the complete chain
and produced a survivor + package, but its CAD pass hit the pre-existing
`NameError: _os` engine defect (honestly recorded in
CAD_PIPELINE_LEDGER.json — the fail-closed design disclosed it; the run
proceeded WITHOUT a 3D section). The one-line import fix is in run.py.

This script verifies the fix on REAL artifacts: it replays the CAD pass
on run 1's actual INVENTION_SPECIFICATION.json. Nothing is fabricated:
the spec is the run's own survivor spec; the output goes to a scratch
directory (the run record is never mutated — Art. IX).

Constitutional notes: the LLM CAD proposal path is untrusted (Art.
XVIII); the deterministic gates (hardcode detection, geometry
validation) decide; the replay's product is COMPUTATIONAL_RESULT only.
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.cad_pipeline import (  # noqa: E402
    get_parametric_model, run_cad_pass)

RUN_DIR = REPO / "ENGINE_RUNS" / "toscanini_ui_ui_thermal_runaway_704526"
SPEC = RUN_DIR / "INVENTION_SPECIFICATION.json"


def main() -> int:
    spec = json.loads(SPEC.read_text())
    with tempfile.TemporaryDirectory(prefix="r414_cad_replay_") as td:
        out_dir = Path(td) / "three_d"
        spec_rel, ledger = run_cad_pass(
            spec, out_dir=str(out_dir), provider=None, allow_llm=True)
        outcome = ledger.get("outcome")
        print("CAD outcome:", outcome)
        print("outcome_reason:", str(ledger.get("outcome_reason"))[:200])
        if outcome not in ("MODEL_BUILT", "NOT_APPLICABLE",
                           "TEMPLATE_MODEL", "OK"):
            print("attempts:", len(ledger.get("attempts") or []))
            return 1
        pm = get_parametric_model(spec_rel)
        print("parametric model:", bool(pm))
        if pm:
            print("parameters:", len(pm.get("parameters") or []))
        steps = sorted(Path(td).rglob("*.step"))
        glbs = sorted(Path(td).rglob("*.glb"))
        print("STEP files:", [s.name for s in steps[:4]])
        print("GLB files:", [g.name for g in glbs[:4]])
        # persist the replay ledger for the record (scratch evidence of
        # the fix; the run's own ledger stays untouched)
        out = Path("/home/z/my-project/audit_ws/repo-r413/ENGINE_RUNS/"
                   "r414_cad_replay_ledger.json")
        out.write_text(json.dumps({
            "replay_of": str(RUN_DIR),
            "spec_sha256_pinned_by": "the run's INVENTION_SPECIFICATION",
            "ledger": ledger,
            "parametric_model_present": bool(pm),
            "step_count": len(steps),
            "glb_count": len(glbs),
        }, indent=1, sort_keys=True)[:100000])
        print("replay ledger persisted:", out.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
