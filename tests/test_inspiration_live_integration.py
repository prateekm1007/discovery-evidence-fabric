"""tests/test_inspiration_live_integration.py — the R145 DIR-6 pin:
the MOOSE-Chem-style inspiration retrieval is integrated into the
LIVE generation conditioning (not a dev-runner import)."""
import importlib
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))


def test_live_conditioning_module_imports_the_lever():
    import r60_v9_one_shot as v10m
    src = Path(v10m.__file__).read_text()
    assert "inspiration_retrieval" in src and (
        "discovery_fabric.generation" in src), (
        "the live generation conditioning (r60_v9_one_shot, the "
        "module whose challenger_prob feeds machine_generate_v79's "
        "prompt) must import the inspiration lever")


def test_typed_plan_carries_inspiration_for_a_family_problem():
    import r60_v9_one_shot as v10m
    prob = {"problem_id": "t-wind",
            "device": "onshore wind turbine",
            "failure": "leading-edge rain erosion of the composite "
                       "blades drops production",
            "failure_mode": "leading-edge erosion energy loss",
            "question_type": "invention"}
    winner = {"operator_id": "GEOMETRIC_TRANSFORMATION",
              "principle_id": "P1", "measure_class": "geometry",
              "signals_used": ["visual_inspection"]}
    p = v10m.challenger_prob(prob, winner, "non_schedule_first")
    insp = p["typed_plan"].get("inspiration")
    assert insp, "the typed_plan must carry the inspiration block"
    assert insp["n_analogies"] >= 1
    assert "INSPIRATION CONTEXT" in insp["block"]


def test_no_family_no_inspiration_field():
    import r60_v9_one_shot as v10m
    prob = {"problem_id": "t-none",
            "device": "a widget",
            "failure": "unrelated text with no physics keyword",
            "failure_mode": "", "question_type": "invention"}
    winner = {"operator_id": "DIRECT_TRANSFER", "principle_id": "P5",
              "measure_class": "configuration",
              "signals_used": ["flow_rate"]}
    p = v10m.challenger_prob(prob, winner, "non_schedule_first")
    assert "inspiration" not in p["typed_plan"]
