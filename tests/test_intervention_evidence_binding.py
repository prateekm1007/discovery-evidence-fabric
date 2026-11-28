"""R5 P0-7 deterministic tests for the strengthened intervention contract:
EVIDENCE-BACKED labels must bind to a source id present in the packet;
assumption-labeled numbers are excluded from the fabricated-number
count. The contract is a shape floor, not a quality score."""
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine.answer_contract import validate_answer

PKT = [{"id": "sealed-1",
        "doi": "10.0000/se12345",
        "abstract": ("Accelerated testing evidence for elastomer-seal "
                     "aging (500 cycles)"),
        "title": "Elastomer seal aging study"}]


def test_evidence_backed_binds_to_packet_source_id():
    ans = ("PARAMETER: seal glass fraction — 0.15 — ASSUMPTION [sealed-1]. "
           "PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [sealed-1]. "
           "Test in thermal-cycling rig; falsify if OCV < 1.0 V after "
           "500 cycles.")
    res = validate_answer(ans, "intervention-proposal", packet=PKT)
    assert res["valid"] is True, res["violations"]


def test_evidence_backed_without_citation_rejected():
    ans = ("PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED. "
           "Test in rig; falsify if OCV < 1.0 V.")
    res = validate_answer(ans, "intervention-proposal", packet=PKT)
    assert res["valid"] is False
    assert any("referenced source id" in v for v in res["violations"])


def test_evidence_backed_citation_not_in_packet_rejected():
    ans = ("PARAMETER: cycle count — 500 cycles — EVIDENCE-BACKED [missing-1]. "
           "Test in rig; falsify if OCV < 1.0 V after 500 cycles.")
    res = validate_answer(ans, "intervention-proposal", packet=PKT)
    assert res["valid"] is False
    assert any("not found in evidence packet" in v
               for v in res["violations"])


def test_predictor_threshold_tied_to_indicator():
    pkt = [{"id": "iso-1",
            "abstract": "RMS velocity criterion: 4.5 mm/s RMS alarm",
            "title": "ISO 10816-3"}]
    ans = ("INDICATOR: bearing vibration RMS band excess. "
           "THRESHOLD: RMS > 4.5 mm/s with units. "
           "VALIDATION PROTOCOL: n=12 machines monitored 90 days; "
           "pass if band excess above threshold 3 shifts; fail "
           "otherwise.")
    res = validate_answer(ans, "predictor-design", packet=pkt,
                          user_variables=["4.5 mm/s RMS"])
    assert res["valid"] is True, res["violations"]
