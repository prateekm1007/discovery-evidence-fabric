"""R450-C2: the STRUCTURED before/after delta schema example.

The real R445 lineage carries narrative-shape mutations (change_delta
text). The R378 improvement engine's canonical mutation record carries
the structured {field: {before, after}} map — the BEFORE/AFTER/DELTA
table's data source. This fixture demonstrates that shape with the same
labeling discipline as the sensitivity example: SCHEMA_EXAMPLE at the
record level, never presented as a real Toscanini engineering delta.
"""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "visual-lab" / "trajectory"))

from schema import canonical_json, record_sha256  # noqa: E402

OUT = REPO / "TOSCANINI_UI" / "webapp" / "lib" / "fixtures" / \
    "r450-trajectory-structured-example.json"

# The R378 improvement-engine mutation record shape (see
# discovery_fabric/engine/improvement_engine.py::apply_mutation --
# mutation_block.changed: {field: {before, after}}).
LINEAGE_EXAMPLE = {
    "schema": "INVENTION_LINEAGE/SCHEMA_EXAMPLE",
    "run_id": "SCHEMA_EXAMPLE_NOT_A_REAL_RUN",
    "stop_reason": "SURVIVOR_REACHED",
    "survivor_reached": True,
    "current_invention": {"gen": 2, "invention_id": None,
                          "status": "INVENTION_REQUIRES_EXPERIMENT",
                          "maturity": "GENERATED"},
    "generations": [
        {
            "gen": 1, "state": "INVENTION_EVOLVED",
            "maturity": "GENERATED", "origin": "BASELINE_SYNTHESIS",
            "invention_id": None,
            "challenge": {
                "killed": True,
                "kill_reason": ("SCHEMA_EXAMPLE: thermal margin below the "
                                "declared design band"),
                "attack_overall": "KILLED", "final_status": "REJECTED",
            },
            "diagnosis": {
                "cause": "THERMAL_MARGIN_SHORTFALL",
                "basis": ["SCHEMA_EXAMPLE: evaluator margin -0.18 vs band "
                          "[0, +]"],
                "infrastructure_class": False,
                "diagnosed_by": "evolution.diagnose_from_generation/1.0.0",
            },
        },
        {
            "gen": 2, "state": "INVENTION_REQUIRES_EXPERIMENT",
            "maturity": "GENERATED", "origin": "IMPROVEMENT_MUTATION",
            "invention_id": None,
            "expected_effect": ("SCHEMA_EXAMPLE: margin +0.22 "
                                "(MODELLED, never measured)"),
            "falsification_test": ("bench: margin < 0.05 at nominal "
                                   "load kills the mechanism"),
            "evaluation": {"verdict": None,
                           "note": "SCHEMA_EXAMPLE: experiment not yet run"},
            "change_delta": ("SCHEMA_EXAMPLE: fin pitch tightened to raise "
                             "the thermal margin"),
            "causal_delta": {
                "failure_or_challenge": "thermal margin below the declared band",
                "diagnosed_cause": "THERMAL_MARGIN_SHORTFALL",
                "causal_change": ("SCHEMA_EXAMPLE: increased exchange area "
                                  "via tighter fin pitch"),
            },
            "mutation": {
                "mutation_id": "mut:SCHEMAEXAMPLE00",
                "mutation_type": "MECHANISM_STRENGTHENING",
                "changed": {
                    "fin_pitch_mm": {"before": "1.0", "after": "1.4"},
                    "expected_effect": {
                        "before": "margin +0.05 (modelled)",
                        "after": "margin +0.22 (modelled)"},
                },
                "diagnostic_trigger": {
                    "dimension": "engineering_coherence",
                    "measured_before": 0.55,
                    "basis": "SCHEMA_EXAMPLE (deterministic)",
                },
            },
        },
    ],
}


def main() -> None:
    traj = __import__("schema").project_trajectory(LINEAGE_EXAMPLE)
    traj["demo_provenance"] = {
        "fixture_kind": "SCHEMA_EXAMPLE_NOT_A_REAL_RUN",
        "note": ("demonstrates the STRUCTURED mutation shape (the R378 "
                 "improvement-engine record) and the BEFORE/AFTER/DELTA "
                 "table contract; the values are illustrative of the "
                 "rendering contract, never a Toscanini engineering result"),
        "lineage_sha256_record": record_sha256(LINEAGE_EXAMPLE),
    }
    OUT.write_text(json.dumps(traj, indent=1) + "\n")
    t = traj["transitions"][0]
    print("structured example written:", OUT.relative_to(REPO))
    print("  mutation shape:", t["mutation"]["shape"],
          "| fields:", [f["field"] for f in t["mutation"]["fields"]])
    print("  prediction:", t["prediction"]["prediction_outcome"])


if __name__ == "__main__":
    main()
