#!/usr/bin/env python3
"""
Transition tests for the deterministic state machine.

Proves all 4 terminal-state derivations:
  1. Hard gate fail → WOULD_NOT_PAY
  2. Hard gates pass + soft gate fail OR composite < 70 → BELOW_BUYER_THRESHOLD (V1.1)
  3. All gates pass + composite >= 70 + milestones → WOULD_CONSIDER_WITH_MILESTONES
  4. All gates pass + composite >= 70 + no milestones → LEVEL_4_BUYER_READY

No LLM/model may select FINAL_STATUS.
"""

import sys
sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent))
from DETERMINISTIC_STATE_MACHINE import GateResult, derive_terminal_state

def make_gate(name, score, threshold, is_hard, status="PASS"):
    return GateResult(
        name=name, score=score, maximum=100, threshold=threshold,
        weight=0.20, status=status, is_hard_gate=is_hard, evidence_pointer="E001"
    )

def test_1_hard_gate_fail():
    """Hard gate fail → WOULD_NOT_PAY"""
    gates = [
        make_gate("PATENT_GATE", 50, 70, is_hard=True, status="FAIL"),
        make_gate("EVIDENCE_GATE", 75, 70, is_hard=True, status="PASS"),
        make_gate("TECHNICAL_GATE", 80, 65, is_hard=False, status="PASS"),
        make_gate("SAFETY_GATE", 70, 60, is_hard=False, status="PASS"),
        make_gate("COMMERCIAL_GATE", 70, 65, is_hard=False, status="PASS"),
    ]
    result = derive_terminal_state(
        gates=gates, composite_score=75, composite_threshold=70,
        buyer_sentiment="WOULD_CONSIDER_WITH_MILESTONES",
        buyer_sentiment_source="INTERNAL_SIMULATION",
        milestones=[], protocol_version="V1.1", pcp_001_status="APPROVED"
    )
    assert result.final_status == "WOULD_NOT_PAY", f"Expected WOULD_NOT_PAY, got {result.final_status}"
    assert result.buyer_readiness == "NOT_READY"
    print("  test_1_hard_gate_fail: PASS")

def test_2_below_buyer_threshold():
    """Hard gates pass + soft gate fail OR composite < 70 → BELOW_BUYER_THRESHOLD (V1.1)"""
    gates = [
        make_gate("PATENT_GATE", 72, 70, is_hard=True, status="PASS"),
        make_gate("EVIDENCE_GATE", 75, 70, is_hard=True, status="PASS"),
        make_gate("TECHNICAL_GATE", 58, 65, is_hard=False, status="FAIL"),  # soft fail
        make_gate("SAFETY_GATE", 62, 60, is_hard=False, status="PASS"),
        make_gate("COMMERCIAL_GATE", 62, 65, is_hard=False, status="FAIL"),  # soft fail
    ]
    result = derive_terminal_state(
        gates=gates, composite_score=68.1, composite_threshold=70,
        buyer_sentiment="WOULD_CONSIDER_WITH_MILESTONES",
        buyer_sentiment_source="INTERNAL_SIMULATION",
        milestones=["in_vitro", "preclinical"],
        protocol_version="V1.1", pcp_001_status="APPROVED"
    )
    assert result.final_status == "BELOW_BUYER_THRESHOLD", f"Expected BELOW_BUYER_THRESHOLD, got {result.final_status}"
    assert result.buyer_readiness == "NOT_READY"
    print("  test_2_below_buyer_threshold: PASS")

def test_3_would_consider_with_milestones():
    """All gates pass + composite >= 70 + milestones → WOULD_CONSIDER_WITH_MILESTONES"""
    gates = [
        make_gate("PATENT_GATE", 75, 70, is_hard=True, status="PASS"),
        make_gate("EVIDENCE_GATE", 78, 70, is_hard=True, status="PASS"),
        make_gate("TECHNICAL_GATE", 70, 65, is_hard=False, status="PASS"),
        make_gate("SAFETY_GATE", 65, 60, is_hard=False, status="PASS"),
        make_gate("COMMERCIAL_GATE", 70, 65, is_hard=False, status="PASS"),
    ]
    result = derive_terminal_state(
        gates=gates, composite_score=73, composite_threshold=70,
        buyer_sentiment="WOULD_CONSIDER_WITH_MILESTONES",
        buyer_sentiment_source="INTERNAL_SIMULATION",
        milestones=["in_vitro", "preclinical", "patent_counsel"],
        protocol_version="V1.1", pcp_001_status="APPROVED"
    )
    assert result.final_status == "WOULD_CONSIDER_WITH_MILESTONES", f"Expected WOULD_CONSIDER_WITH_MILESTONES, got {result.final_status}"
    assert result.buyer_readiness == "READY"
    print("  test_3_would_consider_with_milestones: PASS")

def test_4_level_4_buyer_ready():
    """All gates pass + composite >= 70 + no milestones → LEVEL_4_BUYER_READY"""
    gates = [
        make_gate("PATENT_GATE", 85, 70, is_hard=True, status="PASS"),
        make_gate("EVIDENCE_GATE", 88, 70, is_hard=True, status="PASS"),
        make_gate("TECHNICAL_GATE", 80, 65, is_hard=False, status="PASS"),
        make_gate("SAFETY_GATE", 75, 60, is_hard=False, status="PASS"),
        make_gate("COMMERCIAL_GATE", 78, 65, is_hard=False, status="PASS"),
    ]
    result = derive_terminal_state(
        gates=gates, composite_score=82, composite_threshold=70,
        buyer_sentiment="WOULD_PAY",
        buyer_sentiment_source="EXTERNAL_AUDIT",
        milestones=[],  # no milestones
        protocol_version="V1.1", pcp_001_status="APPROVED"
    )
    assert result.final_status == "LEVEL_4_BUYER_READY", f"Expected LEVEL_4_BUYER_READY, got {result.final_status}"
    assert result.buyer_readiness == "READY"
    print("  test_4_level_4_buyer_ready: PASS")

def test_5_v10_maps_below_threshold_to_would_not_pay():
    """Under V1.0 (PCP-001 not approved), BELOW_BUYER_THRESHOLD maps to WOULD_NOT_PAY"""
    gates = [
        make_gate("PATENT_GATE", 72, 70, is_hard=True, status="PASS"),
        make_gate("EVIDENCE_GATE", 75, 70, is_hard=True, status="PASS"),
        make_gate("TECHNICAL_GATE", 58, 65, is_hard=False, status="FAIL"),
        make_gate("SAFETY_GATE", 62, 60, is_hard=False, status="PASS"),
        make_gate("COMMERCIAL_GATE", 62, 65, is_hard=False, status="FAIL"),
    ]
    result = derive_terminal_state(
        gates=gates, composite_score=68.1, composite_threshold=70,
        buyer_sentiment="WOULD_CONSIDER_WITH_MILESTONES",
        buyer_sentiment_source="INTERNAL_SIMULATION",
        milestones=["in_vitro"],
        protocol_version="V1.0", pcp_001_status="PROPOSED"  # NOT approved
    )
    assert result.final_status == "WOULD_NOT_PAY", f"Under V1.0, expected WOULD_NOT_PAY, got {result.final_status}"
    assert "BELOW_BUYER_THRESHOLD" in result.derivation or "WOULD_NOT_PAY" in result.derivation
    print("  test_5_v10_maps_below_threshold_to_would_not_pay: PASS")

def test_6_no_llm_override():
    """Verify FINAL_STATUS is deterministic — same inputs always produce same output"""
    gates = [
        make_gate("PATENT_GATE", 72, 70, is_hard=True, status="PASS"),
        make_gate("EVIDENCE_GATE", 75, 70, is_hard=True, status="PASS"),
        make_gate("TECHNICAL_GATE", 58, 65, is_hard=False, status="FAIL"),
        make_gate("SAFETY_GATE", 62, 60, is_hard=False, status="PASS"),
        make_gate("COMMERCIAL_GATE", 62, 65, is_hard=False, status="FAIL"),
    ]
    result1 = derive_terminal_state(
        gates=gates, composite_score=68.1, composite_threshold=70,
        buyer_sentiment="WOULD_CONSIDER_WITH_MILESTONES",
        buyer_sentiment_source="INTERNAL_SIMULATION",
        milestones=["in_vitro"], protocol_version="V1.1", pcp_001_status="APPROVED"
    )
    result2 = derive_terminal_state(
        gates=gates, composite_score=68.1, composite_threshold=70,
        buyer_sentiment="WOULD_CONSIDER_WITH_MILESTONES",
        buyer_sentiment_source="INTERNAL_SIMULATION",
        milestones=["in_vitro"], protocol_version="V1.1", pcp_001_status="APPROVED"
    )
    assert result1.final_status == result2.final_status, "Same inputs must produce same output (deterministic)"
    print("  test_6_no_llm_override (deterministic): PASS")

if __name__ == "__main__":
    print("=== Transition Tests for Deterministic State Machine ===")
    print()
    test_1_hard_gate_fail()
    test_2_below_buyer_threshold()
    test_3_would_consider_with_milestones()
    test_4_level_4_buyer_ready()
    test_5_v10_maps_below_threshold_to_would_not_pay()
    test_6_no_llm_override()
    print()
    print("ALL TRANSITION TESTS: PASS")
