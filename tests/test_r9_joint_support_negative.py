"""R9 P1 item 7 negative pins (owner round 2026-11-13): _joint_support
must reject — unrelated source sentences, wrong units, wrong quantities,
PARTIAL multi-value support, substring numbers, and unsupported
conversions. Every pin is the adversarial class the check exists to
catch (Art. II/VI: exact evidence beats semantic plausibility).

Hermetic (pure functions, no LLM, no network).
"""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_contract import _joint_support  # noqa: E402

SRC = ("The grid alloy was tested at 60 C for 3000 hours with n = 20 "
       "cells; capacity retention exceeded 80 percent of the initial "
       "value across all specimens in the survey fleet.")


def test_wrong_unit_rejected():
    res = _joint_support("PARAMETER: test temperature = 60 K", SRC)
    assert not res["joint_supported"]
    assert res["pairs_detail"][0]["value_unit_found"] is False


def test_wrong_quantity_rejected():
    # the value+unit co-occurs but the passage names a DIFFERENT
    # quantity than the claim states (the 80 percent passage vs the
    # 60 C claim)
    res = _joint_support(
        "PARAMETER: ozone concentration = 80 percent", SRC)
    assert not res["joint_supported"], res
    d = res["pairs_detail"][0]
    assert d["value_unit_found"] is True
    assert d["quantity_in_passage"] is False


def test_unrelated_source_sentence_rejected():
    res = _joint_support(
        "PARAMETER: shelf life = 15 years",
        "The packaging line ships 500 units per day to the warehouse.")
    assert not res["joint_supported"]


def test_partial_multi_value_support_rejected_at_contract_level():
    # the parser is one pair per parameter segment; the multi-value
    # claim is therefore TWO parameter lines — one supported, one not:
    # the contract must fail the UNSUPPORTED line while the supported
    # one passes (never one-supported-passes-all)
    import sys
    from discovery_fabric.engine.answer_contract import validate_answer
    pkt = [{"id": "src-1", "doi": "10.1/src1",
            "title": "Grid corrosion survey",
            "abstract": "The temperature was controlled at 60 C for "
                        "500 hours with n = 20 cells in the survey."}]
    ans = ("Intervention:\n"
           "PARAMETER: test temperature = 60 C — EVIDENCE-BACKED [src-1]\n"
           "PARAMETER: shelf life = 15 years — EVIDENCE-BACKED [src-1]\n"
           "FALSIFICATION TEST: hold at 60 C for 500 hours, n = 20 "
           "cells, fail if capacity < 80 percent.")
    res = validate_answer(ans, "intervention-proposal", packet=pkt)
    assert res["valid"] is False, res["violations"]
    assert any("does not jointly support" in v
               for v in res["violations"]), res["violations"]


def test_substring_number_rejected():
    # the claim says 60 C; the source says 1600 C — the digit guard
    # must never admit 60 inside 1600
    res = _joint_support(
        "PARAMETER: test temperature = 60 C",
        "The furnace reached 1600 C during the sintering run.")
    assert not res["joint_supported"]
    assert res["pairs_detail"][0]["value_unit_found"] is False


def test_unsupported_conversion_rejected():
    # the claim names a conversion but the source carries neither the
    # quantity nor any number+unit
    res = _joint_support(
        "PARAMETER: float life = 131400 hours (converted from 15 years "
        "by x8760)", "The battery is a lead-acid automotive unit.")
    assert not res["joint_supported"]


def test_full_pair_with_quantity_in_passage_passes():
    res = _joint_support(
        "PARAMETER: test temperature = 60 C",
        "The temperature was controlled at 60 C with n = 20 cells.")
    assert res["joint_supported"], res
    d = res["pairs_detail"][0]
    assert d["value_unit_found"] and d["quantity_in_passage"]
