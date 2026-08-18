#!/usr/bin/env python3
"""
Deterministic Terminal-State Machine for INVENTION_PROTOCOL_V1.

Per CEO directive §3: "No model gets to choose the final status."

The FINAL_STATUS is mechanically derived from gate results:

    Hard gate fail
        → WOULD_NOT_PAY

    Hard gates pass + any soft gate fail OR composite < 70
        → BELOW_BUYER_THRESHOLD (PCP-001, PROPOSED — maps to WOULD_NOT_PAY under V1.0)

    All gates pass + composite ≥ 70 + milestones remain
        → WOULD_CONSIDER_WITH_MILESTONES

    All gates pass + composite ≥ 70 + no required milestones
        → LEVEL_4_BUYER_READY

This is the ONLY way FINAL_STATUS is determined. No LLM, no agent judgment.
"""

from dataclasses import dataclass
from typing import Literal

@dataclass
class GateResult:
    name: str
    score: float
    maximum: float
    threshold: float
    weight: float
    status: Literal["PASS", "FAIL"]
    is_hard_gate: bool
    evidence_pointer: str

@dataclass
class TerminalState:
    final_status: str
    buyer_readiness: Literal["READY", "NOT_READY"]
    patent_status: str
    engineering_status: str
    buyer_sentiment: str
    derivation: str  # human-readable explanation of how FINAL_STATUS was derived
    pcp_001_note: str  # whether BELOW_BUYER_THRESHOLD is constitutional or proposed

def derive_terminal_state(
    gates: list[GateResult],
    composite_score: float,
    composite_threshold: float,
    buyer_sentiment: str,
    buyer_sentiment_source: str,
    milestones: list[str],
    protocol_version: str = "V1.0",
    pcp_001_status: str = "PROPOSED",
) -> TerminalState:
    """Deterministically derive FINAL_STATUS from gate results. No model judgment."""

    hard_gates = [g for g in gates if g.is_hard_gate]
    soft_gates = [g for g in gates if not g.is_hard_gate]

    hard_pass = all(g.status == "PASS" for g in hard_gates)
    soft_pass = all(g.status == "PASS" for g in soft_gates)
    composite_pass = composite_score >= composite_threshold
    has_milestones = len(milestones) > 0

    # Patent status
    patent_gate = next((g for g in gates if g.name == "PATENT_GATE"), None)
    patent_status = "UNKNOWN"
    if patent_gate:
        if patent_gate.status == "PASS":
            patent_status = "102_PROVEN / 103_UNCERTAIN (or as specified)"
        else:
            patent_status = "PATENT_GATE_FAILED"

    # Engineering status
    tech_gate = next((g for g in gates if g.name == "TECHNICAL_GATE"), None)
    safety_gate = next((g for g in gates if g.name == "SAFETY_GATE"), None)
    tech_status = tech_gate.status if tech_gate else "UNKNOWN"
    safety_status = safety_gate.status if safety_gate else "UNKNOWN"
    if tech_status == "PASS" and safety_status == "PASS":
        engineering_status = "PASS"
    elif tech_status == "FAIL" or safety_status == "FAIL":
        engineering_status = "BELOW_THRESHOLD"
    else:
        engineering_status = "UNKNOWN"

    # Buyer readiness (mechanical)
    if hard_pass and soft_pass and composite_pass:
        buyer_readiness = "READY"
    else:
        buyer_readiness = "NOT_READY"

    # FINAL_STATUS (deterministic derivation)
    if not hard_pass:
        final_status = "WOULD_NOT_PAY"
        derivation = "Hard gate(s) failed → WOULD_NOT_PAY (per §16)"
    elif hard_pass and (not soft_pass or not composite_pass):
        # This is the BELOW_BUYER_THRESHOLD case
        if pcp_001_status == "APPROVED" and protocol_version >= "V1.1":
            final_status = "BELOW_BUYER_THRESHOLD"
            derivation = "Hard gates PASS + soft gate fail OR composite < 70 → BELOW_BUYER_THRESHOLD (per V1.1 §16)"
        else:
            final_status = "WOULD_NOT_PAY"  # maps to WOULD_NOT_PAY under V1.0
            derivation = "Hard gates PASS + soft gate fail OR composite < 70 → would be BELOW_BUYER_THRESHOLD under PCP-001, but PCP-001 is only PROPOSED → maps to WOULD_NOT_PAY under V1.0 §16"
    elif hard_pass and soft_pass and composite_pass and has_milestones:
        final_status = "WOULD_CONSIDER_WITH_MILESTONES"
        derivation = "All gates PASS + composite ≥ 70 + milestones remain → WOULD_CONSIDER_WITH_MILESTONES (per §16)"
    elif hard_pass and soft_pass and composite_pass and not has_milestones:
        final_status = "LEVEL_4_BUYER_READY"
        derivation = "All gates PASS + composite ≥ 70 + no required milestones → LEVEL_4_BUYER_READY (per §16)"
    else:
        final_status = "WOULD_NOT_PAY"
        derivation = "Default: conditions not met → WOULD_NOT_PAY"

    pcp_001_note = (
        f"PCP-001 status: {pcp_001_status}. "
        f"Protocol version: {protocol_version}. "
        f"BELOW_BUYER_THRESHOLD is {'constitutional' if pcp_001_status == 'APPROVED' else 'PROPOSED only — maps to WOULD_NOT_PAY under V1.0'}."
    )

    return TerminalState(
        final_status=final_status,
        buyer_readiness=buyer_readiness,
        patent_status=patent_status,
        engineering_status=engineering_status,
        buyer_sentiment=buyer_sentiment,
        derivation=derivation,
        pcp_001_note=pcp_001_note,
    )


if __name__ == "__main__":
    # Test with Invention #1 V4 values
    gates = [
        GateResult("PATENT_GATE", 72, 100, 70, 0.35, "PASS", True, "E001,E002"),
        GateResult("EVIDENCE_GATE", 75, 100, 70, 0.25, "PASS", True, "E001-E004"),
        GateResult("TECHNICAL_GATE", 58, 100, 65, 0.15, "FAIL", False, "E003"),
        GateResult("SAFETY_GATE", 62, 100, 60, 0.15, "PASS", False, "E004"),
        GateResult("COMMERCIAL_GATE", 62, 100, 65, 0.10, "FAIL", False, "E008"),
    ]
    composite = 68.1
    result = derive_terminal_state(
        gates=gates,
        composite_score=composite,
        composite_threshold=70,
        buyer_sentiment="WOULD_CONSIDER_WITH_MILESTONES",
        buyer_sentiment_source="INTERNAL_SIMULATION",
        milestones=["patent_counsel", "in_vitro", "preclinical"],
        protocol_version="V1.0",
        pcp_001_status="PROPOSED",
    )
    print(f"FINAL_STATUS: {result.final_status}")
    print(f"BUYER_READINESS: {result.buyer_readiness}")
    print(f"Derivation: {result.derivation}")
    print(f"PCP-001 note: {result.pcp_001_note}")
