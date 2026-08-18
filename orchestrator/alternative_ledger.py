"""
Alternative-Defeated Ledger
============================

Every rejected alternative records: alternative → 6-axis same-problem test →
evidence → comparator → result → why rejected.

Part of the invention's provenance.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict
from datetime import datetime, timezone


@dataclass
class Alternative:
    """A plausible alternative architecture that was tested and rejected."""
    alternative_id: str
    description: str
    source: str  # Scopus/Lens/PatentBear/PatSnap/generated_by_orchestrator
    # 6-axis equivalence test
    axis_1_objective: str = ""  # match/mismatch
    axis_2_mechanism: str = ""
    axis_3_constraints: str = ""
    axis_4_operating_environment: str = ""
    axis_5_output: str = ""
    axis_6_failure_mode: str = ""
    classification: str = ""  # SAME_PROBLEM_SAME_MECHANISM etc.
    evidence: str = ""
    comparator: str = ""
    result: str = ""  # alternative_defeated/alternative_wins/alternative_neighboring
    why_rejected: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict:
        return self.__dict__


class AlternativeLedger:
    """Ledger of all rejected alternatives — provenance for the invention."""

    def __init__(self):
        self.alternatives: List[Alternative] = []

    def add(self, alt: Alternative):
        self.alternatives.append(alt)

    def get_defeated(self) -> List[Alternative]:
        return [a for a in self.alternatives if a.result == "alternative_defeated"]

    def get_neighboring(self) -> List[Alternative]:
        return [a for a in self.alternatives if a.result == "alternative_neighboring"]

    def get_winning(self) -> List[Alternative]:
        """Alternatives that WON — would trigger CEILING or architecture change."""
        return [a for a in self.alternatives if a.result == "alternative_wins"]

    def get_credible_competitors(self) -> List[Alternative]:
        """Alternatives classified as SAME_PROBLEM (credible competitors)."""
        return [a for a in self.alternatives
                if a.classification in ("SAME_PROBLEM_SAME_MECHANISM",
                                        "SAME_PROBLEM_DIFFERENT_MECHANISM")]

    def mechanism_diversity_count(self) -> int:
        """Count of CREDIBLE_COMPETITOR alternatives with materially different mechanisms."""
        credible = self.get_credible_competitors()
        # Group by mechanism_hash or axis_2_mechanism
        mechanisms = set()
        for a in credible:
            if a.axis_2_mechanism == "match":
                continue  # same mechanism, not diversity
            mechanisms.add(a.description[:50])  # simplified
        return len(mechanisms)

    def to_dict(self) -> Dict:
        return {
            "alternatives": [a.to_dict() for a in self.alternatives],
            "defeated_count": len(self.get_defeated()),
            "neighboring_count": len(self.get_neighboring()),
            "winning_count": len(self.get_winning()),
            "credible_competitor_count": len(self.get_credible_competitors()),
            "mechanism_diversity": self.mechanism_diversity_count(),
        }
