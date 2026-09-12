"""R450-C2: generate the trajectory demo fixture from the REAL canonical
R445 evolution lineage (Coder 1's engine output, committed in the repo),
plus the sensitivity SCHEMA_EXAMPLE fixture (clearly labeled as a schema
example — never presented as a real Toscanini result, because no canonical
sensitivity record exists yet; honest absence is preserved on real
surfaces).

Art. IX (certification is observational): this script only READS the
canonical lineage; it never mutates it.
Art. VI (never manufacture provenance): the sensitivity fixture is labeled
SCHEMA_EXAMPLE at the record level; the webapp shows it only on the lab
route with that label in the page title.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "visual-lab" / "trajectory"))

from schema import project_trajectory, record_sha256  # noqa: E402

LINEAGE = REPO / "R445" / "EVOLUTION_RUNS" / \
    "evol-x02-bus-fastcharge-lithium-plating" / "INVENTION_LINEAGE.json"
OUT_DIR = REPO / "TOSCANINI_UI" / "webapp" / "lib" / "fixtures"
OUT_TRAJECTORY = OUT_DIR / "r450-trajectory-evol-x02.json"
OUT_SENSITIVITY = OUT_DIR / "r450-sensitivity-schema-example.json"


def main() -> None:
    lineage = json.loads(LINEAGE.read_text())
    traj = project_trajectory(lineage)
    traj["demo_provenance"] = {
        "fixture_kind": "REAL_CANONICAL_LINEAGE_PROJECTION",
        "lineage_path": str(LINEAGE.relative_to(REPO)),
        "lineage_sha256_record": record_sha256(lineage),
        "note": ("projected from the engine's committed INVENTION_LINEAGE "
                 "(R445 evolution run evol-x02-bus-fastcharge-lithium-plating); "
                 "rendered verbatim by the lab route"),
    }
    # The sensitivity fixture is a SCHEMA EXAMPLE, labeled as such at the
    # record level. No canonical sensitivity result exists yet — the real
    # surfaces render honest absence until Coder 1 supplies one.
    sensitivity = {
        "schema": "TOSCANINI_SENSITIVITY/1.0.0",
        "parameter": "fin_pitch_mm",
        "objective": "objective (dimensionless)",
        "basis": "SIMULATED",
        "epistemic_badge": "SIMULATED",
        "provenance": {
            "computation": {
                "instrument": "schema_example_evaluator",
                "basis": "SCHEMA_EXAMPLE — not a measured or projected "
                         "Toscanini result; demonstrates the parameter -> "
                         "response presentation contract only",
            }
        },
        "points": [
            {"value": 1.0, "objective": 0.71},
            {"value": 1.2, "objective": 0.68},
            {"value": 1.4, "objective": 0.62},
        ],
        "note": "SCHEMA_EXAMPLE — values are illustrative of the rendering "
                "contract, not a Toscanini engineering result.",
    }
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_TRAJECTORY.write_text(json.dumps(traj, indent=1) + "\n")
    OUT_SENSITIVITY.write_text(json.dumps(sensitivity, indent=1) + "\n")
    print("trajectory fixture:", OUT_TRAJECTORY)
    print("  trajectory_id:", traj["trajectory_id"],
          "states:", len(traj["states"]))
    print("sensitivity fixture:", OUT_SENSITIVITY)


if __name__ == "__main__":
    main()
