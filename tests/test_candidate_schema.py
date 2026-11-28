#!/usr/bin/env python3
"""tests/test_candidate_schema.py — P1.2 schema-extension tests.

The 1.0.0 core stays byte-stable through the extension (hash never
recomputed); the validator reads SCHEMA FIELDS, never prose (the
F57/F58/F59 retirement path); unstated restrictions never fire
(Art. XXV). Zero LLM, zero network.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from discovery_fabric.engine import candidate_schema as cs  # noqa: E402


def _cand_1_0():
    return {"candidate_schema": "mechanism_candidate/1.0.0",
            "candidate_id": "cand:MS:X:abc123",
            "candidate_hash": "deadbeef00",
            "mechanism": "m", "intervention": "i"}


def test_extend_wraps_without_touching_identity():
    c = _cand_1_0()
    out = cs.extend_to_1_1(c)
    assert out["candidate_schema"] == "mechanism_candidate/1.1.0"
    assert out["candidate_hash"] == c["candidate_hash"]
    assert out["candidate_id"] == c["candidate_id"]
    for f in cs.SCHEMA_1_1_FIELDS:
        assert f in out
    assert out["principle_id"] == "UNASSIGNED"
    assert out["mechanism_class"] == "UNDECLARED"
    assert out["signals_used"] == []


def test_extend_refuses_non_1_0_input():
    with pytest.raises(ValueError, match="expects"):
        cs.extend_to_1_1({"candidate_schema": "mechanism_candidate/0.9"})


def test_validator_refuses_unextended_candidate():
    f = cs.validate_candidate_schema(_cand_1_0())
    assert "SCHEMA_VERSION_MISMATCH" in f


def test_mechanism_class_mandatory_schema_sourced():
    out = cs.extend_to_1_1(_cand_1_0())
    f = cs.validate_candidate_schema(out)
    assert "MECHANISM_CLASS_UNSTATED" in f
    ok = cs.extend_to_1_1(_cand_1_0(), mechanism_class="duty cycle shift")
    assert "MECHANISM_CLASS_UNSTATED" not in cs.validate_candidate_schema(ok)


def test_measure_class_domain_violation_and_none_domain():
    prob = {"allowed_measures": ["geometry", "control_setpoint"]}
    bad = cs.extend_to_1_1(_cand_1_0(), problem=prob,
                           measure_class="schedule_change")
    assert "MEASURE_CLASS_NOT_ALLOWED" in cs.validate_candidate_schema(bad)
    # an UNASSIGNED class against a declared domain also fires
    unass = cs.extend_to_1_1(_cand_1_0(), problem=prob)
    assert "MEASURE_CLASS_NOT_ALLOWED" in cs.validate_candidate_schema(unass)
    good = cs.extend_to_1_1(_cand_1_0(), problem=prob,
                            measure_class="geometry")
    assert "MEASURE_CLASS_NOT_ALLOWED" not in cs.validate_candidate_schema(good)
    # no declared domain -> no violation ever fires (Art. XXV)
    free = cs.extend_to_1_1(_cand_1_0(), measure_class="anything")
    assert "MEASURE_CLASS_NOT_ALLOWED" not in cs.validate_candidate_schema(free)


def test_signal_not_permitted_and_absent_restriction():
    class _P(dict):
        pass
    prob = {"constraint": "must use existing temperature and flow "
                          "measurements only"}
    bad = cs.extend_to_1_1(_cand_1_0(), problem=prob,
                           signals_used=["vibration spectrum"])
    f = cs.validate_candidate_schema(bad, prob)
    assert "SIGNAL_NOT_PERMITTED" in f
    good = cs.extend_to_1_1(_cand_1_0(), problem=prob,
                            signals_used=["temperature", "flow"])
    assert "SIGNAL_NOT_PERMITTED" not in cs.validate_candidate_schema(good, prob)
    # the problem states no restriction -> the check does NOT fire
    free = cs.extend_to_1_1(_cand_1_0(), signals_used=["vibration spectrum"])
    assert "SIGNAL_NOT_PERMITTED" not in cs.validate_candidate_schema(free)


def test_principle_unassigned_is_a_typed_p2_gate():
    out = cs.extend_to_1_1(_cand_1_0())
    f = cs.validate_candidate_schema(out)
    assert "PRINCIPLE_UNASSIGNED" in f
    p2 = cs.extend_to_1_1(_cand_1_0(), principle_id="principle/10")
    assert "PRINCIPLE_UNASSIGNED" not in cs.validate_candidate_schema(p2)
