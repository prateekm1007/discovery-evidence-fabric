"""tests/test_novelty_strength.py — the R146 DIR-2/DIR-6 lever tests:
the EPO problem-solution conditioning + the MOOSE-Chem hypothesis
ranking (novelty strength at generation time)."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.generation.novelty_strength import (
    rank_mechanism_hypotheses, epo_prompt_block, novelty_strength_block,
    transfer_distance, CONVENTIONAL_FIRST_RESPONSE)
from discovery_fabric.generation.mechanism_map import FAILURE_CLASSES


def test_all_failure_classes_have_a_conventional_response():
    missing = [fc for fc in FAILURE_CLASSES
               if fc not in CONVENTIONAL_FIRST_RESPONSE]
    assert not missing, f"missing conventional responses: {missing}"


def test_ranking_orders_by_transfer_distance_desc():
    out = rank_mechanism_hypotheses(
        "leading-edge rain erosion of the composite blades drops "
        "energy production", "wind-energy")
    assert out["failure_class"] == "abrasion_erosion"
    ranked = out["ranked"]
    assert len(ranked) >= 3
    # every class is from the map (the off-target constraint untouched)
    tds = [r["transfer_distance"] for r in ranked]
    assert tds == sorted(tds, reverse=True), (
        "the ranking must order transfer distance DESC")


def test_conventional_proximity_demotes():
    out = rank_mechanism_hypotheses(
        "biofilm fouling on the membranes forces cleaning every three "
        "weeks", "water-treatment")
    ranked = [r for r in out["ranked"] if r["conventional_proximity"]]
    others = [r for r in out["ranked"] if not r["conventional_proximity"]]
    if ranked and others:
        # the conventional-proximate classes must not outrank the
        # non-conventional ones
        assert max(r["rank"] for r in others) < min(
            r["rank"] for r in ranked)


def test_epo_block_names_the_rejection_clause_and_steps():
    out = novelty_strength_block(
        "leading-edge rain erosion of the composite blades drops "
        "energy production", "wind-energy")
    b = out["prompt_block"]
    assert "CLOSEST CONVENTIONAL PRACTICE" in b
    assert "DISTINGUISHING FEATURES" in b
    assert "OBJECTIVE TECHNICAL PROBLEM" in b
    assert "NOT a distinguishing feature" in b, (
        "the routine-parameter-change rejection clause is the lever's "
        "core (DIR 2)")
    assert "assumed" in b, ("the no-invented-numbers clause (DIR 3's "
                            "contract partner) must ride the block")
    assert "PREDICTION" in b


def test_unclassified_is_typed_not_silent():
    out = rank_mechanism_hypotheses("a widget fails somehow", "any")
    assert out["failure_class"] == "unclassified"
    assert out["ranked"] == []
    b = epo_prompt_block(out)
    assert "no failure class detected" in b


def test_transfer_distance_same_family_is_shorter():
    # same family (aerospace) < distant (biomedical) for an
    # aerospace-domain problem
    d_same = transfer_distance("aerospace", "helicopter rotor "
                                            "rain-erosion boots "
                                            "(aerospace)")
    d_far = transfer_distance("aerospace", "carnivorous-plant SLIPS "
                                            "surfaces")
    assert d_same < d_far
