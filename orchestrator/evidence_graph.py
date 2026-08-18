"""
Evidence Graph / Ledger
========================

Unified evidence model: question → query → provider → result → document →
family → mechanism → claim/passage → evidence → contradiction → decision.

Builds on existing EvidenceItem/provenance foundation in the repo.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
import hashlib


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()[:16]


@dataclass
class EvidenceQuestion:
    """A specific uncertainty to resolve."""
    question_id: str
    question: str
    hypothesis: str
    expected_decision_impact: Dict[str, str]  # if_found / if_not_found / if_ambiguous
    evidence_class: str  # discovery/mechanism/architecture/hostile_prior_art/engineering/patent/clinical
    cheapest_capable_source: str
    stop_condition: str
    result: str = "PENDING"  # PENDING/FOUND/NOT_FOUND/AMBIGUOUS/FALSE_POSITIVE
    result_evidence: str = ""
    next_question_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class EvidenceItem:
    """A single piece of evidence with full provenance."""
    evidence_id: str
    question_id: str  # which question generated this
    source: str  # Lens/Scopus/PatentBear/PatSnap/Google/simulation
    content: str  # passage/patent/simulation result
    content_hash: str  # SHA-256 of content
    document_id: str = ""  # patent number / DOI / sim run ID
    family_hash: str = ""  # patent family hash (DOCDB)
    mechanism_hash: str = ""  # mechanism taught
    evidence_type: str = ""  # OBSERVED/EXTERNAL/MODEL_DERIVED/HYPOTHESIS
    independence: str = "PENDING"  # FULLY_INDEPENDENT/PARTIALLY_INDEPENDENT/REDUNDANT
    independence_assessment: Dict[str, str] = field(default_factory=dict)
    # 4-axis independence: family, mechanism, evidence_type, source
    classification: str = ""  # SAME_PROBLEM_SAME_MECHANISM etc.
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = _sha256(self.content)


@dataclass
class Contradiction:
    """A result that could materially falsify the candidate."""
    contradiction_id: str
    description: str
    claim_or_limitation_affected: str  # which L1-Ln
    severity: str  # HIGH/MEDIUM/LOW
    probability: float  # 0.0-1.0
    evidence_quality: str  # STRONG/MODERATE/WEAK/NONE
    decision_impact: float  # 0.0-1.0
    currently_unresolved: bool = True
    resolution_action: str = ""
    resolution_result: str = ""  # RESOLVED_FALSE_ALARM/RESOLVED_REAL_THREAT/UNRESOLVED

    @property
    def priority_score(self) -> float:
        severity_weight = {"HIGH": 1.0, "MEDIUM": 0.5, "LOW": 0.2}[self.severity]
        quality_weight = {"STRONG": 1.0, "MODERATE": 0.7, "WEAK": 0.3, "NONE": 0.1}[self.evidence_quality]
        return severity_weight * self.probability * quality_weight * self.decision_impact

    @property
    def is_blocking(self) -> bool:
        """Only HIGH severity + probability > 0.5 + STRONG/MODERATE evidence blocks survivor status."""
        return (self.severity == "HIGH" and
                self.probability > 0.5 and
                self.evidence_quality in ("STRONG", "MODERATE") and
                self.currently_unresolved)


class EvidenceGraph:
    """Unified evidence ledger with full traceability."""

    def __init__(self):
        self.questions: List[EvidenceQuestion] = []
        self.evidence: List[EvidenceItem] = []
        self.contradictions: List[Contradiction] = []

    def add_question(self, q: EvidenceQuestion):
        self.questions.append(q)

    def add_evidence(self, e: EvidenceItem):
        # Assess independence
        e.independence = self._assess_independence(e)
        self.evidence.append(e)

    def add_contradiction(self, c: Contradiction):
        self.contradictions.append(c)

    def _assess_independence(self, new_evidence: EvidenceItem) -> str:
        """4-axis independence: family + mechanism + evidence_type + source."""
        if not self.evidence:
            return "FULLY_INDEPENDENT"

        matches = {"family": 0, "mechanism": 0, "evidence_type": 0, "source": 0}
        for existing in self.evidence:
            if existing.family_hash and existing.family_hash == new_evidence.family_hash:
                matches["family"] += 1
            if existing.mechanism_hash and existing.mechanism_hash == new_evidence.mechanism_hash:
                matches["mechanism"] += 1
            if existing.evidence_type and existing.evidence_type == new_evidence.evidence_type:
                matches["evidence_type"] += 1
            if existing.source == new_evidence.source:
                matches["source"] += 1

        # All 4 match = REDUNDANT; some match = PARTIALLY_INDEPENDENT; none = FULLY_INDEPENDENT
        match_count = sum(1 for v in matches.values() if v > 0)
        if match_count == 4:
            return "REDUNDANT"
        elif match_count == 0:
            return "FULLY_INDEPENDENT"
        else:
            return "PARTIALLY_INDEPENDENT"

    def get_blocking_contradictions(self) -> List[Contradiction]:
        return [c for c in self.contradictions if c.is_blocking]

    def get_unresolved_contradictions(self) -> List[Contradiction]:
        return [c for c in self.contradictions if c.currently_unresolved]

    def get_independent_evidence_count(self) -> int:
        return sum(1 for e in self.evidence if e.independence == "FULLY_INDEPENDENT")

    def to_dict(self) -> Dict:
        return {
            "questions": [q.__dict__ for q in self.questions],
            "evidence": [e.__dict__ for e in self.evidence],
            "contradictions": [c.__dict__ for c in self.contradictions],
            "summary": {
                "total_questions": len(self.questions),
                "total_evidence": len(self.evidence),
                "independent_evidence": self.get_independent_evidence_count(),
                "blocking_contradictions": len(self.get_blocking_contradictions()),
                "unresolved_contradictions": len(self.get_unresolved_contradictions()),
            }
        }
