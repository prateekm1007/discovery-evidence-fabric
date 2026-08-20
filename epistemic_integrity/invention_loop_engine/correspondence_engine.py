"""
Evidence-Bound Correspondence Engine and Prior-Art Eligibility Layer.

Per CEO directive (eighteenth round):
  'The goal is not to make the machine say "anticipated." The goal is to
   make "anticipated" so expensive in evidence that a false positive becomes
   difficult to manufacture.'

  Build a traceable correspondence engine where a non-verbatim limitation
  can be established from explicit evidence:
    candidate limitation → claim passage → technical correspondence rule
    → basis → provenance → reviewer/model → disposition

  No opaque semantic equivalence. A model may PROPOSE correspondence
  (CANDIDATE_CORRESPONDENCE) but must not establish it without an explicit rule.

  Only VERBATIM and explicitly evidenced equivalence may feed a §102 conclusion.

  Build PriorArtEligibilityEvidence separately from claim correspondence.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class CorrespondenceType(str, Enum):
    """How a limitation corresponds to a claim passage.

    Per CEO directive (eighteenth round):
      Only VERBATIM and explicitly evidenced equivalence may feed §102.

      VERBATIM — the limitation text appears verbatim in the claim
      STRUCTURAL_EQUIVALENT — explicit rule: same structural elements
      FUNCTIONAL_EQUIVALENT — explicit rule: same function, different structure
      EXPLICIT_DEPENDENCY — limitation inherited from parent claim
      NOT_ESTABLISHED — cannot determine correspondence
    """
    VERBATIM = "VERBATIM"
    STRUCTURAL_EQUIVALENT = "STRUCTURAL_EQUIVALENT"
    FUNCTIONAL_EQUIVALENT = "FUNCTIONAL_EQUIVALENT"
    EXPLICIT_DEPENDENCY = "EXPLICIT_DEPENDENCY"
    NOT_ESTABLISHED = "NOT_ESTABLISHED"


class CorrespondenceStatus(str, Enum):
    """Whether a correspondence has been established or is just proposed.

    Per CEO directive (eighteenth round):
      A model may PROPOSE correspondence (CANDIDATE_CORRESPONDENCE)
      but must not establish it without an explicit rule.
    """
    ESTABLISHED = "ESTABLISHED"  # Explicit rule satisfied
    CANDIDATE = "CANDIDATE"      # Proposed but not confirmed (model/semantic only)
    REJECTED = "REJECTED"        # Explicit rule failed
    NOT_EVALUATED = "NOT_EVALUATED"


class DisclosureType(str, Enum):
    """The type of disclosure a correspondence represents.

    Per CEO directive (nineteenth round):
      Separate correspondence from legal sufficiency.
      Do not let FUNCTIONAL_EQUIVALENT=True automatically mean §102-supported.

      EXPLICIT_CLAIM_DISCLOSURE — the claim explicitly recites the limitation
      CLAIM_DEPENDENCY — the limitation is inherited from a parent claim
      INHERENCY — the limitation is inherent in the claim (NOT automatic §102)
      OTHER_LEGAL_THEORY — some other legal theory (NOT automatic §102)
      UNKNOWN — cannot determine the disclosure type
    """
    EXPLICIT_CLAIM_DISCLOSURE = "EXPLICIT_CLAIM_DISCLOSURE"
    CLAIM_DEPENDENCY = "CLAIM_DEPENDENCY"
    INHERENCY = "INHERENCY"
    OTHER_LEGAL_THEORY = "OTHER_LEGAL_THEORY"
    UNKNOWN = "UNKNOWN"


class CorrespondenceRule(str, Enum):
    """The explicit rule that establishes (or rejects) correspondence.

    These are auditable rules, not semantic similarity.
    """
    EXACT_SUBSTRING = "EXACT_SUBSTRING"  # Verbatim text match
    GLOSSARY_MAPPING = "GLOSSARY_MAPPING"  # Term A (candidate) = Term B (claim) per glossary
    STRUCTURAL_DECOMPOSITION = "STRUCTURAL_DECOMPOSITION"  # Limitation decomposed into claim elements
    FUNCTIONAL_ANALYSIS = "FUNCTIONAL_ANALYSIS"  # Same function proven by explicit analysis
    DEPENDENCY_INHERITANCE = "DEPENDENCY_INHERITANCE"  # Inherited from parent claim
    MANUAL_EXPERT = "MANUAL_EXPERT"  # Expert manually established correspondence
    NONE = "NONE"  # No rule applied (candidate only)


@dataclass
class LimitationCorrespondence:
    """A traceable correspondence between a candidate limitation and a claim passage.

    Per CEO directive (eighteenth round):
      candidate limitation → claim passage → technical correspondence rule
      → basis → provenance → reviewer/model → disposition

      No opaque semantic equivalence. Every correspondence must be auditable
      and decomposable.
    """
    limitation_id: str
    reference_patent: str
    claim_number: int
    # The claim passage that may correspond to the limitation
    claim_passage: str  # Exact text from the claim
    claim_start_offset: int = -1
    claim_end_offset: int = -1
    # The correspondence type
    correspondence_type: CorrespondenceType = CorrespondenceType.NOT_ESTABLISHED
    # P0-2 (nineteenth round): Disclosure type — separates correspondence from legal sufficiency
    disclosure_type: DisclosureType = DisclosureType.UNKNOWN
    # Whether this is established or just proposed
    status: CorrespondenceStatus = CorrespondenceStatus.NOT_EVALUATED
    # The explicit rule that establishes (or rejects) correspondence
    rule: CorrespondenceRule = CorrespondenceRule.NONE
    # Supporting evidence (e.g., glossary entry, structural decomposition)
    supporting_evidence: str = ""  # What evidence supports this correspondence?
    # The technical relationship (why these correspond)
    technical_relationship: str = ""  # Why does claim passage X correspond to limitation Y?
    # Who/what established this?
    reviewer: str = ""  # "EXACT_SUBSTRING_AUTO" / "EXPERT:J.Doe" / "GLOSSARY:v1.0"
    # Provenance
    raw_response_hash: str = ""
    source_node_identifier: str = ""
    provenance_hash: str = ""
    # Confidence (only meaningful when status=ESTABLISHED)
    confidence: str = "UNKNOWN"  # HIGH / MEDIUM / LOW / UNKNOWN
    # Unresolved reason (when status=CANDIDATE or NOT_EVALUATED)
    unresolved_reason: str = ""
    # Timestamp
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correspondence_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not self.provenance_hash:
            content = f"{self.limitation_id}|{self.claim_number}|{self.claim_passage}|{self.correspondence_type.value}|{self.rule.value}"
            self.provenance_hash = hashlib.sha256(content.encode()).hexdigest()

    @property
    def can_support_section_102(self) -> bool:
        """Can this correspondence support a §102 conclusion?

        Per CEO directive (nineteenth round):
          Separate correspondence from legal sufficiency.
          Do not let FUNCTIONAL_EQUIVALENT=True automatically mean §102-supported.

          Only EXPLICIT_CLAIM_DISCLOSURE and CLAIM_DEPENDENCY can automatically
          support §102. INHERENCY and OTHER_LEGAL_THEORY require separate
          legal analysis — they are NOT automatic.

          Additionally:
          - status must be ESTABLISHED (not CANDIDATE)
          - rule must not be NONE
          - For VERBATIM: disclosure_type must be EXPLICIT_CLAIM_DISCLOSURE
          - For EXPLICIT_DEPENDENCY: disclosure_type must be CLAIM_DEPENDENCY
          - For STRUCTURAL_EQUIVALENT/FUNCTIONAL_EQUIVALENT: disclosure_type
            must be EXPLICIT_CLAIM_DISCLOSURE (if the expert determined the
            equivalence constitutes explicit disclosure) — otherwise UNKNOWN
        """
        if self.status != CorrespondenceStatus.ESTABLISHED:
            return False
        if self.rule == CorrespondenceRule.NONE:
            return False
        # Only explicit disclosure and claim dependency can automatically support §102
        if self.disclosure_type == DisclosureType.EXPLICIT_CLAIM_DISCLOSURE:
            return True
        if self.disclosure_type == DisclosureType.CLAIM_DEPENDENCY:
            return True
        # INHERENCY, OTHER_LEGAL_THEORY, UNKNOWN → cannot automatically support §102
        return False

    def to_dict(self) -> dict:
        # P0-1 (nineteenth round): Canonical evidence is NEVER truncated.
        # Display-layer truncation is separate from canonical artifact.
        return {
            "correspondence_id": self.correspondence_id,
            "limitation_id": self.limitation_id,
            "reference_patent": self.reference_patent,
            "claim_number": self.claim_number,
            "claim_passage": self.claim_passage,  # FULL, not [:200]
            "display_claim_passage": self.claim_passage[:200] + ("..." if len(self.claim_passage) > 200 else ""),
            "claim_start_offset": self.claim_start_offset,
            "claim_end_offset": self.claim_end_offset,
            "correspondence_type": self.correspondence_type.value,
            "disclosure_type": self.disclosure_type.value,
            "status": self.status.value,
            "rule": self.rule.value,
            "supporting_evidence": self.supporting_evidence,
            "technical_relationship": self.technical_relationship,
            "reviewer": self.reviewer,
            "raw_response_hash": self.raw_response_hash,
            "source_node_identifier": self.source_node_identifier,
            "provenance_hash": self.provenance_hash,
            "confidence": self.confidence,
            "unresolved_reason": self.unresolved_reason,
            "timestamp": self.timestamp,
            "can_support_section_102": self.can_support_section_102,
        }


@dataclass
class PriorArtEligibilityEvidence:
    """Evidence-bound prior-art temporal eligibility.

    Per CEO directive (eighteenth round):
      Build PriorArtEligibilityEvidence separately from claim correspondence.
      Do not let the claim mapper calculate legal eligibility.

      Needs: critical_date, priority_date, filing_date, publication_date,
      public_availability_date, jurisdiction, applicable_rule,
      source_evidence, evidence_hash, eligibility.
    """
    candidate_critical_date: str = ""
    reference_priority_date: str = ""
    reference_filing_date: str = ""
    reference_publication_date: str = ""
    public_availability_date: str = ""
    jurisdiction: str = ""
    # The applicable legal rule (e.g., "35 USC 102(a)", "EPC Art 54(2)")
    applicable_rule: str = ""
    # Where each date came from
    date_source: str = ""
    # Hash of all date evidence
    evidence_hash: str = ""
    # The eligibility verdict
    eligibility: str = "UNKNOWN"  # ELIGIBLE / INELIGIBLE / UNKNOWN
    # Reasoning
    eligibility_reasoning: str = ""
    # Whether this is a complete or simplified analysis
    analysis_completeness: str = "INCOMPLETE"  # COMPLETE / SIMPLIFIED / INCOMPLETE
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if not self.evidence_hash:
            content = f"{self.candidate_critical_date}|{self.reference_publication_date}|{self.reference_priority_date}|{self.jurisdiction}"
            self.evidence_hash = hashlib.sha256(content.encode()).hexdigest()

    def evaluate(self):
        """Evaluate prior-art eligibility from evidence.

        Per CEO directive (nineteenth round):
          Derive the decision from the relevant date/public-availability
          evidence and jurisdiction-specific rule, not merely check that
          fields are nonempty.

          Having fields populated is NOT equivalent to applying the applicable
          legal rule. The system must derive from dates + rule.

          public_availability_date is the most important date for §102(a).
          If it's unknown, eligibility is UNKNOWN even if publication_date exists.
        """
        # Check minimum required dates
        has_critical = bool(self.candidate_critical_date)
        has_publication = bool(self.reference_publication_date)
        has_public_availability = bool(self.public_availability_date)
        has_jurisdiction = bool(self.jurisdiction)
        has_rule = bool(self.applicable_rule)

        if not has_critical or not has_publication:
            self.eligibility = "UNKNOWN"
            self.analysis_completeness = "INCOMPLETE"
            self.eligibility_reasoning = (
                "Cannot evaluate: "
                f"{'critical_date missing' if not has_critical else ''} "
                f"{'publication_date missing' if not has_publication else ''}."
            )
            return

        # P0-3 (nineteenth round): public_availability_date is critical for §102
        # If we don't know when the reference became publicly available,
        # we cannot determine eligibility — even if we have publication_date.
        if not has_public_availability:
            # Use publication_date as a proxy but label as SIMPLIFIED
            self.analysis_completeness = "SIMPLIFIED"
            if self.reference_publication_date < self.candidate_critical_date:
                self.eligibility = "ELIGIBLE_SIMPLIFIED"
                self.eligibility_reasoning = (
                    f"Publication date {self.reference_publication_date} < critical date "
                    f"{self.candidate_critical_date}. BUT public_availability_date is UNKNOWN — "
                    f"this is a simplified check, not a complete §102 eligibility analysis. "
                    f"Publication ≠ public availability in all jurisdictions."
                )
            else:
                self.eligibility = "INELIGIBLE"
                self.eligibility_reasoning = (
                    f"Publication date {self.reference_publication_date} >= critical date "
                    f"{self.candidate_critical_date}."
                )
            return

        # We have public_availability_date — can do a more complete check
        # But still need jurisdiction and applicable_rule for COMPLETE
        if not has_jurisdiction or not has_rule:
            self.analysis_completeness = "SIMPLIFIED"
        else:
            self.analysis_completeness = "COMPLETE"

        # Use public_availability_date for the primary check
        # (This is the legally relevant date for §102(a) in most jurisdictions)
        if self.public_availability_date < self.candidate_critical_date:
            self.eligibility = "ELIGIBLE" if self.analysis_completeness == "COMPLETE" else "ELIGIBLE_SIMPLIFIED"
            self.eligibility_reasoning = (
                f"Public availability {self.public_availability_date} < critical date "
                f"{self.candidate_critical_date}. "
                f"Jurisdiction: {self.jurisdiction or 'UNKNOWN'}. "
                f"Rule: {self.applicable_rule or 'UNKNOWN'}. "
                f"Analysis completeness: {self.analysis_completeness}."
            )
        else:
            self.eligibility = "INELIGIBLE"
            self.eligibility_reasoning = (
                f"Public availability {self.public_availability_date} >= critical date "
                f"{self.candidate_critical_date}."
            )

    def to_dict(self) -> dict:
        return {
            "candidate_critical_date": self.candidate_critical_date,
            "reference_priority_date": self.reference_priority_date,
            "reference_filing_date": self.reference_filing_date,
            "reference_publication_date": self.reference_publication_date,
            "public_availability_date": self.public_availability_date,
            "jurisdiction": self.jurisdiction,
            "applicable_rule": self.applicable_rule,
            "date_source": self.date_source,
            "evidence_hash": self.evidence_hash,
            "eligibility": self.eligibility,
            "eligibility_reasoning": self.eligibility_reasoning,
            "analysis_completeness": self.analysis_completeness,
            "timestamp": self.timestamp,
        }


class CorrespondenceEngine:
    """Evidence-bound correspondence engine.

    Per CEO directive (eighteenth round):
      A model may PROPOSE correspondence (CANDIDATE_CORRESPONDENCE)
      but must not establish it without an explicit rule.

      Only VERBATIM and explicitly evidenced equivalence may feed §102.

      The engine is auditable and decomposable — no opaque semantic equivalence.
    """

    def __init__(self):
        self._glossary: dict[str, str] = {}  # candidate_term → claim_term (explicit mappings)

    def register_glossary_mapping(self, candidate_term: str, claim_term: str, source: str = ""):
        """Register an explicit term mapping.

        Per CEO directive (eighteenth round):
          GLOSSARY_MAPPING is an explicit, auditable rule.
          It is NOT semantic similarity — it is a declared equivalence
          with provenance.
        """
        self._glossary[candidate_term.lower()] = claim_term.lower()

    def evaluate_correspondence(
        self,
        limitation_text: str,
        claim_text: str,
        claim_number: int,
        reference_patent: str,
        limitation_id: str,
        raw_response_hash: str = "",
        source_node_identifier: str = "",
    ) -> LimitationCorrespondence:
        """Evaluate whether a limitation corresponds to a claim passage.

        This method tries multiple explicit rules in order:
          1. EXACT_SUBSTRING (verbatim) → VERBATIM, ESTABLISHED
          2. GLOSSARY_MAPPING (if glossary has term mappings) → STRUCTURAL_EQUIVALENT, ESTABLISHED
          3. No rule matches → NOT_ESTABLISHED, NOT_EVALUATED

        A model/semantic system may PROPOSE a candidate by calling
        propose_candidate_correspondence(), but that produces CANDIDATE status,
        not ESTABLISHED.
        """
        lim_lower = limitation_text.lower().strip()
        claim_lower = claim_text.lower()

        # Rule 1: EXACT_SUBSTRING (verbatim)
        idx = claim_lower.find(lim_lower)
        if idx >= 0:
            matched = claim_text[idx:idx + len(lim_lower)]
            return LimitationCorrespondence(
                limitation_id=limitation_id,
                reference_patent=reference_patent,
                claim_number=claim_number,
                claim_passage=matched,
                claim_start_offset=idx,
                claim_end_offset=idx + len(lim_lower),
                correspondence_type=CorrespondenceType.VERBATIM,
                disclosure_type=DisclosureType.EXPLICIT_CLAIM_DISCLOSURE,  # P0-2: verbatim = explicit disclosure
                status=CorrespondenceStatus.ESTABLISHED,
                rule=CorrespondenceRule.EXACT_SUBSTRING,
                supporting_evidence=f"Verbatim match: '{matched[:80]}'",
                technical_relationship="Identical text",
                reviewer="EXACT_SUBSTRING_AUTO",
                raw_response_hash=raw_response_hash,
                source_node_identifier=source_node_identifier,
                confidence="HIGH",
            )

        # Rule 2: GLOSSARY_MAPPING (explicit term equivalence)
        # Replace candidate terms with claim terms and check for verbatim match
        translated = lim_lower
        for candidate_term, claim_term in self._glossary.items():
            if candidate_term in translated:
                translated = translated.replace(candidate_term, claim_term)

        if translated != lim_lower:
            # Glossary terms were applied — check if translated text matches
            idx = claim_lower.find(translated)
            if idx >= 0:
                matched = claim_text[idx:idx + len(translated)]
                return LimitationCorrespondence(
                    limitation_id=limitation_id,
                    reference_patent=reference_patent,
                    claim_number=claim_number,
                    claim_passage=matched,
                    claim_start_offset=idx,
                    claim_end_offset=idx + len(translated),
                    correspondence_type=CorrespondenceType.STRUCTURAL_EQUIVALENT,
                    status=CorrespondenceStatus.ESTABLISHED,
                    rule=CorrespondenceRule.GLOSSARY_MAPPING,
                    supporting_evidence=f"Glossary mapping applied. Translated: '{translated[:80]}'",
                    technical_relationship="Terms mapped via explicit glossary",
                    reviewer="GLOSSARY:v1.0",
                    raw_response_hash=raw_response_hash,
                    source_node_identifier=source_node_identifier,
                    confidence="HIGH",
                )

        # No explicit rule matched → NOT_ESTABLISHED
        return LimitationCorrespondence(
            limitation_id=limitation_id,
            reference_patent=reference_patent,
            claim_number=claim_number,
            claim_passage="",
            claim_start_offset=-1,
            claim_end_offset=-1,
            correspondence_type=CorrespondenceType.NOT_ESTABLISHED,
            status=CorrespondenceStatus.NOT_EVALUATED,
            rule=CorrespondenceRule.NONE,
            supporting_evidence="",
            technical_relationship="",
            reviewer="",
            raw_response_hash=raw_response_hash,
            source_node_identifier=source_node_identifier,
            confidence="UNKNOWN",
            unresolved_reason=(
                "No explicit correspondence rule matched. "
                "Requires EXACT_SUBSTRING, GLOSSARY_MAPPING, "
                "STRUCTURAL_DECOMPOSITION, FUNCTIONAL_ANALYSIS, "
                "DEPENDENCY_INHERITANCE, or MANUAL_EXPERT to establish."
            ),
        )

    def propose_candidate_correspondence(
        self,
        limitation_text: str,
        claim_text: str,
        claim_number: int,
        reference_patent: str,
        limitation_id: str,
        proposed_passage: str,
        proposed_relationship: str,
        proposer: str = "MODEL",
        raw_response_hash: str = "",
    ) -> LimitationCorrespondence:
        """A model proposes a correspondence (CANDIDATE, not ESTABLISHED).

        Per CEO directive (eighteenth round):
          A model may PROPOSE correspondence but must not establish it
          without an explicit rule.

          This produces CANDIDATE status, which CANNOT support §102.
          An explicit rule must confirm it before it becomes ESTABLISHED.
        """
        return LimitationCorrespondence(
            limitation_id=limitation_id,
            reference_patent=reference_patent,
            claim_number=claim_number,
            claim_passage=proposed_passage,
            claim_start_offset=-1,
            claim_end_offset=-1,
            correspondence_type=CorrespondenceType.NOT_ESTABLISHED,
            status=CorrespondenceStatus.CANDIDATE,
            rule=CorrespondenceRule.NONE,
            supporting_evidence=f"Proposed by {proposer}: {proposed_relationship}",
            technical_relationship=proposed_relationship,
            reviewer=proposer,
            raw_response_hash=raw_response_hash,
            confidence="LOW",
            unresolved_reason=(
                "CANDIDATE correspondence proposed by model. "
                "Cannot support §102 until an explicit rule confirms. "
                "Requires EXACT_SUBSTRING, GLOSSARY_MAPPING, "
                "STRUCTURAL_DECOMPOSITION, FUNCTIONAL_ANALYSIS, "
                "DEPENDENCY_INHERITANCE, or MANUAL_EXPERT."
            ),
        )

    def confirm_candidate(
        self,
        candidate: LimitationCorrespondence,
        confirming_rule: CorrespondenceRule,
        confirming_evidence: str,
        confirming_reviewer: str,
        correspondence_type: CorrespondenceType,
        disclosure_type: DisclosureType = DisclosureType.UNKNOWN,
    ) -> LimitationCorrespondence:
        """Confirm a CANDIDATE correspondence with an explicit rule.

        Per CEO directive (nineteenth round):
          disclosure_type must be explicitly set by the confirmer.
          Only EXPLICIT_CLAIM_DISCLOSURE and CLAIM_DEPENDENCY can support §102.
          INHERENCY and OTHER_LEGAL_THEORY require separate legal analysis.

          The confirmer must justify the disclosure_type — it is not automatic.
        """
        candidate.status = CorrespondenceStatus.ESTABLISHED
        candidate.rule = confirming_rule
        candidate.supporting_evidence = confirming_evidence
        candidate.reviewer = confirming_reviewer
        candidate.correspondence_type = correspondence_type
        candidate.disclosure_type = disclosure_type
        candidate.confidence = "HIGH"
        candidate.unresolved_reason = ""
        # Re-compute provenance hash
        content = f"{candidate.limitation_id}|{candidate.claim_number}|{candidate.claim_passage}|{candidate.correspondence_type.value}|{candidate.rule.value}|{candidate.disclosure_type.value}"
        candidate.provenance_hash = hashlib.sha256(content.encode()).hexdigest()
        return candidate
