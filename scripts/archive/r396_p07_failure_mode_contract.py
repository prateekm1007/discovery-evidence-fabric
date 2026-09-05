#!/usr/bin/env python3
"""scripts/r396_p07_failure_mode_contract.py — R396 Phase D.3:

"Demonstrate explicit solver outputs for: NORMAL / PARTIAL_FAILURE /
SEVERE_FAILURE / ALTERNATIVE_PATH. Use P-07 as the reference case."

Runs the physics core V0 on the P-07 reference geometry (primary 1.0 mm
+ floor 0.6 mm, 90 mm segments, water-class fluid at 310.15 K, 12/4
mmHg — every value's epistemic class recorded) and persists the FULL
solver outputs for the four failure-mode scenarios on candidate AND
baseline, plus the baseline comparison with the directive vocabulary.

Writes R396/P07_FAILURE_MODE_CONTRACT.json.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.engine import physics_core as pc  # noqa: E402
from discovery_fabric.engine import physics_gate as pgate  # noqa: E402


def main() -> int:
    env = pgate.REFERENCE_ENVELOPE
    candidate = pgate._network_spec(
        env["primary_lumen_diameter_mm"],
        env["floor_lumen_diameter_mm"],
        "P-07-candidate-reference")
    baseline = pgate._network_spec(
        env["primary_lumen_diameter_mm"], None, "P-07-baseline-reference")

    cand_fm = pc.simulate_failure_modes(candidate, "primary")
    base_fm = pc.simulate_failure_modes(baseline, "primary")
    comp = pc.compare_to_baseline(
        candidate, baseline, "primary",
        scenario="SEVERE_OBSTRUCTION",
        required_min=env["required_min_flow_ml_min"])

    report = {
        "run": "R396 Phase D.3 — P-07 failure-mode contract "
               "(explicit solver outputs)",
        "reference_case": "P-07 (portfolio 04_drainage_floor)",
        "envelope": env,
        "scenario_vocabulary": {
            "directive": ["NORMAL", "PARTIAL_FAILURE", "SEVERE_FAILURE",
                          "ALTERNATIVE_PATH"],
            "engine": list(pc.FAILURE_MODE_SCENARIOS),
            "mapping": {
                "NORMAL": "NORMAL (unobstructed)",
                "PARTIAL_FAILURE": "PARTIAL_OBSTRUCTION "
                                   f"({pc.THRESHOLDS['PARTIAL_OBSTRUCTION_PCT']['value']}% "
                                   "primary obstruction)",
                "SEVERE_FAILURE": "SEVERE_OBSTRUCTION "
                                  f"({pc.THRESHOLDS['SEVERE_OBSTRUCTION_PCT']['value']}% "
                                  "primary obstruction)",
                "ALTERNATIVE_PATH": "ALTERNATIVE_PATH (primary 100% "
                                    "obstructed; flow through the "
                                    "invented floor path)"},
        },
        "candidate_scenarios": cand_fm["scenarios"],
        "baseline_scenarios": base_fm["scenarios"],
        "baseline_comparison": comp,
        "plausibility_gate": {
            "status": (cand_fm["scenarios"][0]["result"] or {}).get(
                "status"),
            "note": "deterministic bounds (six families) executed "
                    "before/inside every solve above; a violation would "
                    "have produced PLAUSIBILITY_BOUND_VIOLATED and NO "
                    "computational evidence",
        },
        "evidence_class_note": (
            "every scenario output is COMPUTATIONAL_RESULT (Art. "
            "XXXVIII layer 4) with input/output hashes, convergence "
            "residual, assumptions and limitations recorded; none of "
            "it may be cited as physical observation — physical "
            "validation is the Phase E flow-rig experiment"),
    }
    out = REPO_ROOT / "R396" / "P07_FAILURE_MODE_CONTRACT.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=1, default=str))
    for s in cand_fm["scenarios"]:
        v = s.get("value")
        b = next((x.get("value") for x in base_fm["scenarios"]
                  if x["scenario"] == s["scenario"]), None)
        print(f"  {s['scenario']:20s} candidate="
              f"{v!r:>24} baseline={b!r:>24}")
    print(f"  comparison: {comp['outcome']} / {comp['candidate_outcome']} "
          f"(rel improvement "
          f"{comp['comparison']['improvement_relative']})")
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
