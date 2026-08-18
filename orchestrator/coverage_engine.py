"""
Coverage / Materiality Engine
==============================

7-dimension adaptive coverage + PatSnap materiality test.

NOT_FOUND_AFTER_COMPLETE_SEARCH is mechanically derived from satisfied
coverage dimensions, NOT a human declaration.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timezone


@dataclass
class CoverageContract:
    """Territory-specific coverage contract (NOT universal defaults)."""
    territory_id: str
    technology_class: str
    required_jurisdictions: List[str]  # based on competitor geography
    temporal_floor: str  # priority date of earliest foundational patent
    temporal_ceiling: str = "present"
    mechanism_search_depth: int = 3  # how many CREDIBLE_COMPETITOR alternatives
    family_collapse_required: bool = False
    claim_audit_threshold: int = 5  # top N threats to claim-audit
    source_requirements: Dict[str, str] = field(default_factory=dict)
    patsnap_materiality: str = "MEDIUM"  # LOW/MEDIUM/HIGH

    def to_dict(self) -> Dict:
        return self.__dict__


class CoverageEngine:
    """7-dimension coverage assessment with PatSnap materiality test."""

    DIMENSIONS = [
        "query_coverage",
        "family_coverage",
        "jurisdiction_coverage",
        "temporal_coverage",
        "mechanism_coverage",
        "claim_coverage",
        "source_coverage",
    ]

    def __init__(self, contract: CoverageContract):
        self.contract = contract
        self.dimension_status: Dict[str, Dict] = {
            dim: {"satisfied": False, "evidence": "", "metric": ""}
            for dim in self.DIMENSIONS
        }

    def assess_dimension(self, dimension: str, satisfied: bool,
                         evidence: str, metric: str):
        """Update the status of a coverage dimension."""
        self.dimension_status[dimension] = {
            "satisfied": satisfied,
            "evidence": evidence,
            "metric": metric,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def all_dimensions_satisfied(self) -> bool:
        """Mechanically derive whether NOT_FOUND_AFTER_COMPLETE_SEARCH can be declared."""
        return all(d["satisfied"] for d in self.dimension_status.values())

    def get_completeness_state(self, unresolved_contradictions: int = 0) -> str:
        """Determine the patent completeness state mechanically.
        NOT_FOUND_AFTER_COMPLETE_SEARCH = all dimensions satisfied AND no blocking contradictions.
        """
        if not self.all_dimensions_satisfied():
            return "SEARCH_INCOMPLETE"
        if unresolved_contradictions > 0:
            return "SEARCH_INCOMPLETE"  # unresolved contradictions block completeness
        return "NOT_FOUND_AFTER_COMPLETE_SEARCH"

    def assess_patsnap_materiality(self, cheaper_sources_findings: Dict) -> str:
        """PatSnap materiality test — could PatSnap materially change the decision?
        PatSnap is NEVER a ceremonial checkbox.
        """
        # If cheaper sources found NO same-problem threats → PatSnap unlikely to find new (LOW)
        same_problem_threats = cheaper_sources_findings.get("same_problem_threats", 0)
        claim_text_audited = cheaper_sources_findings.get("claim_text_audited", False)
        neighboring_only = cheaper_sources_findings.get("neighboring_only", False)
        family_members_missed = cheaper_sources_findings.get("family_members_missed", False)

        if same_problem_threats == 0 and neighboring_only:
            return "LOW"  # cheaper sources found no real threats
        if same_problem_threats > 0 and claim_text_audited:
            return "LOW"  # threats already audited via PatentBear
        if family_members_missed:
            return "HIGH"  # family-expansion needed
        if same_problem_threats > 0 and not claim_text_audited:
            return "HIGH"  # claim-data needed
        return "MEDIUM"

    def is_patsnap_required(self, materiality: str) -> bool:
        """PatSnap is required only if materiality is HIGH."""
        return materiality == "HIGH"

    def document_patsnap_skip(self, materiality: str, reason: str) -> Dict:
        """When PatSnap is ruled unnecessary, document WHY (required by V4)."""
        return {
            "patsnap_required": False,
            "materiality": materiality,
            "reason": reason,
            "cheaper_sources_coverage": "documented in evidence graph",
            "what_patsnap_would_add": "low incremental value — cannot materially change decision",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def to_dict(self) -> Dict:
        return {
            "contract": self.contract.to_dict(),
            "dimension_status": self.dimension_status,
            "all_satisfied": self.all_dimensions_satisfied(),
            "completeness_state": self.get_completeness_state(),
        }
