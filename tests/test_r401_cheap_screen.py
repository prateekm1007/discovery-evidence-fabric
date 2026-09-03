"""tests/test_r401_cheap_screen.py — R401B B8: the cheap-first
scientific filter.

Directive rules pinned here:
  - Skipped stages record explicit reasons (never silence).
  - Kills happen only on CHEAPLY DECIDABLE defects (declared-envelope
    impossibility, explicit baseline equivalence).
  - UNDECIDED checks ADVANCE (information is never skipped merely
    because a candidate looks weak — learning-critical info flows).
  - Out-of-physics-scope mechanisms ADVANCE with the honest
    MECHANISM_NOT_SIMULATABLE disclosure (never a cheap kill).
  - TOP-N defers (does not reject) — rank + score + reason recorded.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import cheap_screen as cs  # noqa: E402

PROBLEM = {
    "problem_id": "r401_b8",
    "device": "tunneled hemodialysis catheter",
    "failure": "thrombotic occlusion of the lumen under low flow",
    "failure_mode": "thrombotic occlusion",
    "constraint": "maintain drainage above 0.05 mL/min",
}


def _cand(**over):
    base = {
        "candidate_id": "cand:MS:TEST:0001",
        "mechanism": "heparin bonding inhibits clotting cascade "
                     "activation at the catheter lumen surface",
        "intervention": "bond heparin to the catheter lumen wall",
        "predicted_effect": "thrombus area reduced by 50 percent "
                            "under low flow",
        "testable_prediction": "thrombus area reduced by 50 percent "
                               "at 50 mL/min",
        "testable_prediction_check": {"testable": True},
        "constraint_set": {
            "problem_constraint": "maintain drainage above 0.05 "
                                  "mL/min",
            "boundary_conditions": "flow 20-50 mL/min",
            "stated_constraints": "none"},
        "mechanism_support": {"mechanism_support_state": "SUPPORTED"},
        "derivation_trace": {"operator": "DIRECT_TRANSFER"},
    }
    base.update(over)
    return base


class TestCheapScreen:
    def test_healthy_candidate_advances(self):
        s = cs.screen_candidate(_cand(), PROBLEM)
        assert s["state"] == "ADVANCE"
        assert s["checks"]["representability"]["verdict"] == \
            "REPRESENTABLE"
        assert s["checks"]["baseline_screen"]["verdict"] == \
            "DIRECTION_OF_EFFECT_PRESENT"
        assert s["cheap_score"] >= 4

    def test_out_of_physics_scope_advances_with_disclosure(self):
        # an electromagnetic mechanism: NOT in the V0 hydraulic scope —
        # it ADVANCES with MECHANISM_NOT_SIMULATABLE_EXPECTED (Phase 7:
        # never a cheap kill, never fabricated physics)
        s = cs.screen_candidate(_cand(
            mechanism="electromagnetic antenna coupling radiates "
                      "telemetry power through tissue",
            intervention="embed a resonant antenna in the catheter "
                         "wall"), PROBLEM)
        assert s["state"] == "ADVANCE"
        assert s["checks"]["representability"]["verdict"] == \
            "MECHANISM_NOT_SIMULATABLE_EXPECTED"

    def test_declared_impossible_envelope_is_killed(self):
        s = cs.screen_candidate(_cand(
            constraint_set={"problem_constraint":
                            "the design requires a negative lumen "
                            "diameter of -0.2 mm"}), PROBLEM)
        assert s["state"] == "SCREENED_OUT"
        assert any("CONSTRAINT_SCREEN" in r for r in s["reasons"])
        assert s["checks"]["constraint_screen"]["verdict"] == \
            "IMPOSSIBLE_DECLARED"

    def test_perpetual_motion_declaration_is_killed(self):
        s = cs.screen_candidate(_cand(
            constraint_set={"stated_constraints":
                            "provides perpetual flow without pressure "
                            "gradient"}), PROBLEM)
        assert s["state"] == "SCREENED_OUT"

    def test_explicit_baseline_equivalence_is_killed(self):
        s = cs.screen_candidate(_cand(
            predicted_effect="total flow unchanged relative to the "
                             "baseline catheter"), PROBLEM)
        assert s["state"] == "SCREENED_OUT"
        assert any("BASELINE_SCREEN" in r for r in s["reasons"])

    def test_undecided_baseline_advances(self):
        # no direction vocabulary AND no explicit equivalence —
        # UNDECIDED must advance (never skipped for looking weak)
        s = cs.screen_candidate(_cand(
            predicted_effect="thrombus behavior observed",
            testable_prediction="thrombus behavior is observed over "
            "time"), PROBLEM)
        assert s["state"] == "ADVANCE"
        assert s["checks"]["baseline_screen"]["verdict"] == "UNDECIDED"

    def test_missing_prediction_advances_undecided(self):
        s = cs.screen_candidate(_cand(predicted_effect=""), PROBLEM)
        assert s["state"] == "ADVANCE"
        assert s["checks"]["baseline_screen"]["verdict"] == "UNDECIDED"

    def test_screen_records_its_policy_and_version(self):
        s = cs.screen_candidate(_cand(), PROBLEM)
        assert s["cheap_screen_version"] == "cheap_screen/1.0.0"
        assert "learning-critical" in s["policy"]


class TestTopN:
    def test_top_n_selects_and_defers(self):
        screens = [cs.screen_candidate(
            _cand(candidate_id=f"cand{i}",
                  mechanism_support={"mechanism_support_state":
                                    support}), PROBLEM)
            for i, support in enumerate(
                ["SUPPORTED", "SUPPORTED", "PARTIALLY_SUPPORTED",
                 "PARTIALLY_SUPPORTED", None, None, None], 1)]
        out = cs.rank_top_n(screens, top_n=3)
        assert out["n_advance"] == 7
        assert len(out["selected_ids"]) == 3
        assert len(out["deferred"]) == 4
        for d in out["deferred"]:
            assert d["skip_reason"].startswith("SKIPPED_TOPN")
            assert d["rank"] > 3
            assert d["cheap_score"] >= 0

    def test_top_n_deterministic(self):
        screens = [cs.screen_candidate(_cand(candidate_id=f"c{i}"),
                                       PROBLEM) for i in range(5)]
        a = cs.rank_top_n(screens, top_n=2)
        b = cs.rank_top_n(screens, top_n=2)
        assert a["selected_ids"] == b["selected_ids"]
        assert a["deferred"] == b["deferred"]

    def test_top_n_zero_selects_nothing_defers_all(self):
        screens = [cs.screen_candidate(_cand(), PROBLEM)]
        out = cs.rank_top_n(screens, top_n=0)
        assert out["selected_ids"] == []
        assert len(out["deferred"]) == 1


class TestCostModel:
    def test_every_stage_has_a_cost_class(self):
        from discovery_fabric.engine.adapters import STAGE_ORDER
        for stage in STAGE_ORDER:
            assert stage in cs.STAGE_COST_CLASSES, \
                f"stage {stage} missing a cost class"

    def test_expensive_stages_are_flagged(self):
        assert cs.STAGE_COST_CLASSES["MECHANISM_SPACE"] == \
            "EXPENSIVE_LLM"
        assert cs.STAGE_COST_CLASSES["GAUNTLET_SPEC"] == \
            "EXPENSIVE_EVALUATION"
        assert cs.STAGE_COST_CLASSES["GAUNTLET_PACKAGE"] == \
            "EXPENSIVE_EVALUATION"

    def test_cheap_deterministic_stages_are_flagged(self):
        for stage in ("FREEZE", "PREMISE_GATE", "VERIFY", "PHYSICS",
                      "ATTACK", "RANK"):
            assert cs.STAGE_COST_CLASSES[stage] == "CHEAP_DETERMINISTIC"
