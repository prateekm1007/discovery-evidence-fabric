"""R5 P1-5 deterministic tests: strict unsupported-hypothesis qualifier,
A/B ablation decision, and the attacker's rank demotion semantics.

No network, no LLM. Every case is machine-checked.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.a2.adversarial import (
    unsupported_hypothesis_qualifies, _ab_survive_decision)
from discovery_fabric.engine.engineering_attack import select_survivors

# a grounded unsupported-but-plausible+falsifiable candidate: engineered
# to fail ONLY the evidence-presence dimension (it is absent from the
# packet by construction) while passing every structural requirement.
GROUNDED = {
    "mechanism": ("membrane-bound separator pad flattens the stress "
                  "concentration at the radiused bearing seal land so "
                  "local fatigue initiation is pushed below service stress"),
    "intervention": ("install graded-bond separator pads at each bearing "
                     "seal land before first service"),
    "falsification_test": ("run 200 cycles to 85 °C then measure drift "
                           "below 5 percent; accept if drift stays below "
                           "5 percent and reject otherwise"),
    "expected_effect": "drift below 5 percent across 200 cycles at 85 °C",
    "failure": "bearing seal lip drift under cyclic thermal exposure",
    "constraint": "no unplanned downtime; rated load supported",
    "user_variables": ["1 kHz vibration sensor only",
                       "at least 14 days warning"],
}


def test_qualifies_when_structural_requirements_met():
    out = unsupported_hypothesis_qualifies(GROUNDED)
    assert out["qualifies"], out["reasons"]


def test_rejects_no_numeric_falsifier():
    c = dict(GROUNDED)
    c["falsification_test"] = "run it for a while then inspect"
    out = unsupported_hypothesis_qualifies(c)
    assert not out["qualifies"]
    assert any("falsifier" in r for r in out["reasons"])


def test_rejects_numeric_without_unit():
    c = dict(GROUNDED)
    c["falsification_test"] = ("measure drift below 5 accept if it passes")
    out = unsupported_hypothesis_qualifies(c)
    assert not out["qualifies"]
    assert any("units" in r for r in out["reasons"])


def test_rejects_numeric_with_unit_but_no_comparator():
    c = dict(GROUNDED)
    c["falsification_test"] = ("measure drift at 85 °C over the week; "
                               "accept whatever it shows")
    out = unsupported_hypothesis_qualifies(c)
    assert not out["qualifies"]
    assert any("comparator" in r for r in out["reasons"])


def test_rejects_numeric_with_unit_and_comparator_but_no_acceptance():
    c = dict(GROUNDED)
    c["falsification_test"] = ("measure drift at 85 °C below 5 percent "
                               "over 200 cycles")
    out = unsupported_hypothesis_qualifies(c)
    assert not out["qualifies"]
    assert any("acceptance" in r for r in out["reasons"])


def test_rejects_unrelated_falsifier():
    # structurally perfect test that says nothing about THIS failure
    c = dict(GROUNDED)
    c["falsification_test"] = ("measure the catalyst conversion at 300 K "
                               "below 2 percent; accept if it passes")
    out = unsupported_hypothesis_qualifies(c)
    assert not out["qualifies"]
    assert any("target" in r for r in out["reasons"])


def test_rejects_bare_C_celsius_but_accepts_degree_symbol():
    c = dict(GROUNDED)
    c["falsification_test"] = ("rate drift at 85 C; accept if drift "
                               "stays below the limit")
    out = unsupported_hypothesis_qualifies(c)
    assert not out["qualifies"]          # bare C must not parse as Celsius
    c["falsification_test"] = ("run 200 cycles to 85 °C then measure drift "
                               "below 5 percent; accept if drift stays "
                               "below 5 percent and reject otherwise")
    out = unsupported_hypothesis_qualifies(c)
    assert out["qualifies"], out["reasons"]


def test_bare_c_kelvin_collision_is_explicit():
    # 300 K (Kelvin) must parse; a bare trailing C must not
    c = dict(GROUNDED)
    c["falsification_test"] = ("measure catalyst conversion at 300 K below "
                               "2 percent; accept if it passes")
    out = unsupported_hypothesis_qualifies(c)
    assert any("target" in r for r in out["reasons"])  # unrelated to failure


def test_contradiction_dimension_never_gets_ab_rescue():
    d = _ab_survive_decision("CONTRADICTION", True, GROUNDED)
    assert d["applies"] is False
    assert d["qualifies"] is False


def test_infeasibility_dimension_never_gets_ab_rescue():
    d = _ab_survive_decision("FEASIBILITY", True, GROUNDED)
    assert d["applies"] is False


def test_user_constraint_violation_never_gets_ab_rescue():
    d = _ab_survive_decision("USER_CONSTRAINT", True, GROUNDED)
    assert d["applies"] is False


def test_prior_art_collision_never_gets_ab_rescue():
    d = _ab_survive_decision("PRIOR_ART", True, GROUNDED)
    assert d["applies"] is False


def test_unsupported_with_junk_candidate_stays_killed():
    junk = {"mechanism": "it fails", "intervention": "fix it",
            "falsification_test": "looks better", "failure": "degradation"}
    d = _ab_survive_decision("UNSUPPORTED_MECHANISM", True, junk)
    assert d["applies"] is False
    assert d["qualifier_reasons"]


def test_unsupported_with_qualified_candidate_survives_flagged():
    d = _ab_survive_decision("UNSUPPORTED_MECHANISM", True, GROUNDED)
    assert d["applies"] is True


def _cand(cid, hypothesis_flag):
    return {"candidate_id": cid,
            "attack": {"overall": "PASS",
                       "counts": {"UNCERTAIN": 0},
                       **({"risk_flags": [
                           {"source": "ab_unsupported_hypothesis",
                            "hypothesis": True, "ranked_lower": True}]}
                          if hypothesis_flag else {})},
            "quality": {"verdict": "PASS", "deficient_areas": []},
            "repaired": False,
            "span_underived": False,
            "physics_lifecycle": "BEATS_BASELINE"}


def test_ranked_lower_actually_changes_ranking():
    supported = _cand("SUPP-1", hypothesis_flag=False)
    hypothesis = _cand("HYP-1", hypothesis_flag=True)
    out = select_survivors([hypothesis, supported])
    assert out["selected"] == "SUPP-1"
    assert out["selected_is_hypothesis"] is False
    assert out["hypothesis_demoted"] == ["HYP-1"]
    reversed_out = select_survivors([supported, hypothesis])
    assert reversed_out["selected"] == "SUPP-1"


def test_hypothesis_only_pool_still_selects_a_hypothesis():
    out = select_survivors([_cand("HYP-1", True), _cand("HYP-2", True)])
    assert out["selected"] in ("HYP-1", "HYP-2")
    assert out["selected_is_hypothesis"] is True
