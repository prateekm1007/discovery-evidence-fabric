"""tests/test_nonobvious_departure.py — the v19 non-obviousness lever
tests (R173-F1 / CORR-R172-1; DIR 2+3): the departure contract (PART A)
+ the feasibility-conservation check (PART B) + the typed emission
check."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.generation.nonobvious_departure import (
    DEPARTURE_PROMPT_BLOCK, check_departure, departure_block,
    departure_ranked_inspirations, failure_sign)


PROB = ("leading-edge rain erosion of the composite wind blades drops "
        "energy production")


def test_failure_sign_typed():
    # a deposition/solidification problem is SUPPRESS
    assert failure_sign(
        "Gas hydrates nucleate in the subsea pipeline during "
        "shutdowns") == "suppress"
    # a supercooling-burst problem is PROMOTE
    assert failure_sign(
        "stochastic supercooling bursts freeze the line "
        "unpredictably") == "promote"
    # an erosion problem is SUPPRESS (the damage must be prevented)
    assert failure_sign(
        "the impeller pitting forces replacement every 8 months "
        "under cavitation") == "suppress"


def test_wrong_sign_mechanisms_are_excluded():
    out = departure_ranked_inspirations(
        "Gas hydrates nucleate in the subsea pipeline during "
        "shutdowns; methanol dosing is standard", "offshore-energy")
    assert out["sign"] == "suppress"
    offered = [r["mech_class"] for r in out["ranked"]]
    assert "controlled_nucleation_sites" not in offered, (
        "nucleation sites PROMOTE hydrate formation — a wrong-sign "
        "mechanism must never be offered (the round-2 smoke lesson)")


def test_block_has_all_seven_contract_headings():
    for h in ("CROSS-DOMAIN INSPIRATION", "NEAREST PRIOR ART",
              "THE DEPARTURE", "NOT-A-SUBSTITUTION", "DIRECTION CHECK",
              "ENABLING CONDITIONS", "ENVELOPE CHECK"):
        assert h in DEPARTURE_PROMPT_BLOCK, f"missing heading {h}"
    # the anti-inversion clause (the s4 smoke lesson: a cooling
    # mechanism cannot prevent a cold-triggered solidification)
    assert "pushes the SAME direction as the failure driver" in \
        DEPARTURE_PROMPT_BLOCK


def test_ranked_inspirations_exclude_own_family():
    out = departure_ranked_inspirations(PROB, "wind-energy")
    assert out["problem_family"] in (None, "energy-turbines")
    for r in out["ranked"]:
        # a wind-energy problem must not be handed a wind-energy
        # precedent as its departure inspiration
        assert "wind" not in r["cross_domain"].lower()


def test_block_names_conventional_first_response():
    out = departure_block(PROB, "wind-energy")
    assert out["conventional_first"], (
        "the NEAREST PRIOR ART line must name the domain's first "
        "response (the thing to depart from)")


def test_check_departure_passes_a_complete_section():
    good = (
        "CROSS-DOMAIN INSPIRATION: helicopter rotor rain-erosion "
        "elastomer boots (compliant-layer stress spreading).\n"
        "NEAREST PRIOR ART: hard-facing coating at the wear site.\n"
        "THE DEPARTURE: low-modulus viscoelastic dissipation vs "
        "hard-on-hard reflection.\n"
        "NOT-A-SUBSTITUTION: the coupling class changes, not the "
        "material dose.\n"
        "DIRECTION CHECK: the failure driver is impact stress "
        "concentration rising; the compliant layer pushes the peak "
        "stress DOWN — opposite direction.\n"
        "ENABLING CONDITIONS: polyurethane service window -40..120C; "
        "bond to composite; 2-4mm layer.\n"
        "ENVELOPE CHECK: blades see -30..60C — inside the window; "
        "bond via film adhesive — compatible.\n"
        "STEELMAN: the strongest counter is UV/erosion degradation of "
        "the elastomer at the leading edge; answered by the 8-year "
        "field record of rotor boots in rain service at higher tip "
        "speeds.")
    out = check_departure(good)
    assert out["passed"], out["missing"]


def test_check_departure_flags_missing_parts():
    bad = ("CROSS-DOMAIN INSPIRATION: something.\n"
           "NEAREST PRIOR ART: something else.")
    out = check_departure(bad)
    assert not out["passed"]
    assert "departure_stated" in out["missing"]
    assert "enabling_conditions_stated" in out["missing"]
    assert out["repair_directive"], (
        "the repair directive must feed the missing headings back "
        "(the physics_truth repair-loop shape)")
