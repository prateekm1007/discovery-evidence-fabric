"""tests/test_r6_joint_provenance.py — adversarial pins for the owner
audit round 2026-11-13 P0: quantitative provenance must bind EVERY
value/unit pair to its corresponding quantity in the SAME exact
passage. Partial support, cross-sentence assembly, wrong units,
substring numbers and bare derivations are never evidence backing."""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_contract import (  # noqa: E402
    _joint_support, _joint_violation_class,
)


def sup(claim, source):
    return _joint_support(claim, source)


# ---------------------------------------------------------------------------
# Adversarial classes required by the audit
# ---------------------------------------------------------------------------
def test_matching_number_attached_to_wrong_quantity():
    r = sup("yield strength 450 MPa",
            "The measured hardness was 450 MPa after tempering.")
    assert r["joint_supported"] is False
    assert _joint_violation_class(
        r, "The measured hardness was 450 MPa after tempering.") == (
            "same_number_wrong_quantity")


def test_correct_quantity_wrong_unit():
    r = sup("operating temperature 120 °C",
            "The operating temperature reached 120 MPa in the press.")
    assert r["joint_supported"] is False
    assert _joint_violation_class(
        r, "The operating temperature reached 120 MPa in the press.") == (
            "wrong_unit")


def test_quantity_in_one_sentence_value_unit_in_another():
    src = ("The current rises sharply under load. "
           "The measured value was 12 A at the terminal.")
    r = sup("current 12 A", src)
    assert r["joint_supported"] is False, (
        "quantity in sentence A must not licence value+unit in sentence B")
    assert _joint_violation_class(r, src) == "same_number_wrong_quantity"


def test_one_supported_one_unsupported_multi_value_claim():
    src = "The current reached 12 A under load."
    r = sup("current 12 A and voltage 480 V", src)
    assert r["joint_supported"] is False, (
        "a supported pair must never mask an unsupported pair")
    assert len(r["pair_bindings"]) == 1
    assert len(r["unsupported_pairs"]) == 1
    assert r["unsupported_pairs"][0]["pair"]["value"] == "480"


def test_substring_number_never_supports():
    src = "The current reached 120 A under load."
    r = sup("current 12 A", src)
    assert r["joint_supported"] is False
    assert _joint_violation_class(r, src) == "substring_number"


def test_unsupported_conversion_is_not_evidence():
    # 393 K is a conversion of 250 °F; the source never carries the
    # converted value or a joint derivation — the claim is ASSUMPTION
    # class, never EVIDENCE-BACKED
    src = "The furnace was held at 250 °F for one hour."
    r = sup("temperature 393 K (converted from 250 °F)", src)
    assert r["joint_supported"] is False
    assert r["conversion_recorded"] is True
    assert r.get("derived_quantity") is True


def test_derived_quantity_never_joint():
    src = "The fraction was 0.9 in the reference run."
    r = sup("efficiency 90 % (derived from the 0.9 fraction)", src)
    assert r["joint_supported"] is False
    assert r.get("derived_quantity") is True


def test_wrong_quantity_elsewhere_on_the_same_line():
    # the sample line carries the number for another parameter: the
    # pair's OWN clause quantity governs, not the line's vocabulary
    src = "samples: 6 drives; thickness 12 mm"
    r = sup("bearing temperature 12 mm", src)
    assert r["joint_supported"] is False


# ---------------------------------------------------------------------------
# Positive controls (the tightened check must not become a universal rejector)
# ---------------------------------------------------------------------------
def test_two_pairs_each_bound_in_their_own_exact_passage():
    src = ("Under load the current reached 12 A. "
           "The operating temperature was 120 °C at the winding.")
    r = sup("current 12 A and operating temperature 120 °C", src)
    assert r["joint_supported"] is True
    assert r["single_passage"] is False
    assert len(r["pair_bindings"]) == 2
    assert len(r["unsupported_pairs"]) == 0
    for b in r["pair_bindings"]:
        assert b["passage_sha256"]
        assert b["quantity_matched"]


def test_two_pairs_in_one_passage_are_joint_single_passage():
    src = ("Under load the current reached 12 A at an operating "
           "temperature of 120 °C.")
    r = sup("current 12 A and operating temperature 120 °C", src)
    assert r["joint_supported"] is True
    assert r["single_passage"] is True


def test_qualitative_claim_supported_by_one_passage():
    r = sup("vibration rises before spalling",
            "Bearing vibration rises before spalling becomes visible.")
    assert r["joint_supported"] is True
    assert r["pair_bindings"][0]["kind"] == "qualitative"


def test_qualitative_claim_cannot_assemble_across_sentences():
    src = "Bearing vibration rises with load. The level was 4.5."
    r = sup("vibration 4.5", src)
    assert r["joint_supported"] is False, (
        "a bare number in another sentence must not complete the claim")


def test_quantity_supported_requires_every_pair():
    src = "The current reached 12 A under load."
    r = sup("current 12 A and voltage 480 V", src)
    assert r["quantity_supported"] is False
