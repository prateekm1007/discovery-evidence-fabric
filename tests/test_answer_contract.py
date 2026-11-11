"""Answer-shape contract tests (R3): predictor-design and
intervention-proposal contracts are deterministic and routed by
question_type."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine.answer_contract import validate_answer

PREDICTOR_GOOD = (
    "Track bearing vibration RMS on the predictor envelope. "
    "INDICATOR: bearing vibration RMS band excess. "
    "THRESHOLD: RMS > 4.5 mm/s with units (ISO 10816-3); baseline 2.1 mm/s. "
    "PROTOCOL: n=12 machines, 90 days; pass if RMS band excess rises above "
    "threshold 3 consecutive shifts before a maintenance-needed flag; fail "
    "otherwise. Falsify if flag fires after maintenance."
)
PREDICTOR_BAD = (
    "Use machine learning to detect anomalies in bearing signals. "
    "The system will learn normal operation and alert when anomalies occur."
)
INTERVENTION_GOOD = (
    "Change seal compound to HNR with 5.8 pphr curing agent. "
    "PARAMETER: seal glass fraction — 0.15 — ASSUMPTION. "
    "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED. "
    "Test in a thermal-cycling rig per the record; falsify if OCV < 1.0 V "
    "after 500 cycles."
)
INTERVENTION_BAD = (
    "Use better seal materials and improve design."
)


def test_predictor_contract_accepts_complete_answer():
    # the THRESHOLD number must appear in the evidence packet or in
    # user variables; the packet contains the ISO 10816-3 band 4.5 mm/s
    pkt = [{"id": "iso10816-3", "abstract":
            "velocity criterion for machine group 1: 4.5 mm/s RMS alarm",
            "title": "ISO 10816-3"}]
    res = validate_answer(PREDICTOR_GOOD, "predictor-design", packet=pkt)
    assert res["valid"] is True, res["violations"]


def test_predictor_contract_rejects_generic_answer():
    res = validate_answer(PREDICTOR_BAD, "predictor-design")
    assert res["valid"] is False
    assert any("indicator" in v.lower() for v in res["violations"])
    assert any("threshold" in v.lower() for v in res["violations"])
    assert any("n=" in v.lower() or "n " in v.lower()
               for v in res["violations"])


def test_intervention_contract_accepts_labeled_parameters():
    # the EVIDENCE-BACKED parameter cites evidence that is present
    pkt = [{"id": "astm-seal", "abstract":
            "accelerated thermal-cycling evidence: 500 cycles, OCV 1.0 V",
            "title": "Seal compound validation"}]
    good = ("Change seal compound to HNR. "
            "PARAMETER: glass fraction — 0.15 — ASSUMPTION [astm-seal]. "
            "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [astm-seal]. "
            "Test in a thermal-cycling rig per the record; falsify if "
            "OCV < 1.0 V after 500 cycles.")
    res = validate_answer(good, "intervention-proposal", packet=pkt)
    assert res["valid"] is True, res["violations"]


def test_intervention_contract_rejects_unlabeled_generic_answer():
    res = validate_answer(INTERVENTION_BAD, "intervention-proposal")
    assert res["valid"] is False
    assert any("EVIDENCE-BACKED" in v or "ASSUMPTION" in v
               for v in res["violations"])


def test_unknown_type_is_rejected():
    res = validate_answer("whatever", "something-else")
    assert res["valid"] is False


PERCENT_CASE = (
    "PARAMETER: creep-rate alert — 10 percent of rated deflection — ASSUMPTION. "
    "Test in the creep rig; falsify if deflection exceeds 5-10 percent before "
    "500 cycles; accept if below threshold."
)


def test_intervention_contract_accepts_percent_and_range():
    # R5 P0-2: "10%" and ranges like "5-10 percent" must satisfy the
    # numeric-with-units floor (\b after % never matched)
    res = validate_answer(PERCENT_CASE, "intervention-proposal")
    assert res["valid"] is True, res["violations"]


def test_intervention_contract_accepts_percent_symbol():
    ans = ("PARAMETER: creep-rate alert — 10% of rated deflection — "
           "ASSUMPTION. Test in the rig; falsify if deflection exceeds "
           "5-10% before 500 cycles; accept if below threshold.")
    res = validate_answer(ans, "intervention-proposal")
    assert res["valid"] is True, res["violations"]


def test_predictor_contract_accepts_percent_threshold():
    ans = ("INDICATOR: dropout fraction of laser diodes. "
           "THRESHOLD: dropout fraction > 2% of fleet; baseline 0.4%. "
           "PROTOCOL: n=80 devices, 180 days; pass if dropout exceeds 2% "
           "before end of service; fail otherwise.")
    res = validate_answer(ans, "predictor-design")
    assert res["valid"] is True, res["violations"]
