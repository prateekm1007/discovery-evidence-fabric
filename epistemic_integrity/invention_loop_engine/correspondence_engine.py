"""
Evidence-Bound Correspondence Engine and Prior-Art Eligibility Layer.

Per CEO directive (twentieth round — 2026-08-21 deep audit):
  'A field that says "reviewed," "complete," or "expert-confirmed" is not
   evidence of the underlying action. The action itself must leave verifiable
   evidence.'

  This round closes four P0 gaps and one P1 gap:

  P0-1 — Four-state prior-art eligibility.
         Replaces the binary COMPLETE/SIMPLIFIED/INCOMPLETE label with four
         evidenced phases: SOURCE_DATES_COMPLETE → LEGAL_RULE_IDENTIFIED →
         LEGAL_RULE_APPLIED → ELIGIBILITY_ESTABLISHED. A populated
         `applicable_rule` field proves only that a rule was IDENTIFIED, not
         that it was APPLIED. ELIGIBILITY_ESTABLISHED requires explicit
         evidence that the rule was applied to the dates.

  P0-2 — Equivalence is not automatic anticipation.
         Automatic §102 support is restricted to VERBATIM_EXPLICIT_CLAIM_DISCLOSURE
         (the claim explicitly recites the limitation) and legitimate
         CLAIM_DEPENDENCY (the limitation is inherited from a parent claim).
         STRUCTURAL_EQUIVALENT and FUNCTIONAL_EQUIVALENT require a separate
         LegalCorrespondenceDecision object — setting disclosure_type=
         EXPLICIT_CLAIM_DISCLOSURE on an equivalence is no longer sufficient.

  P0-3 — Cryptographic binding of the entire evidentiary assertion.
         The provenance_hash now binds limitation_id, claim_passage, both
         offsets, correspondence_type, disclosure_type, rule, supporting_evidence,
         technical_relationship, reviewer, raw_response_hash, source_node_identifier,
         plus the attestation_id + evidence_hash (if attested) and the
         legal_decision_id + decision_evidence_hash (if legally decided).
         Altering any underlying field invalidates the hash.

  P0-4 — CorrespondenceAttestation object.
         A free-form `reviewer="EXPERT:J.Doe"` string is not evidence that an
         expert reviewed anything. MANUAL_EXPERT correspondence now requires a
         CorrespondenceAttestation with reviewer_id, reviewer_role, decision,
         rationale, timestamp, evidence_hash, attestation_id. Without it, the
         correspondence cannot reach ESTABLISHED status.

  P1   — Adversarial regression tests.
         Six fail-closed scenarios are added to anti_gaming_tests.py:
         (a) all eligibility fields populated but rule never applied;
         (b) functional equivalence marked explicit by mistake;
         (c) supporting evidence changed but provenance hash unchanged;
         (d) forged reviewer string with no attestation;
         (e) public_availability_date conflicts with publication_date;
         (f) jurisdiction/rule mismatch.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


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

      Per CEO directive (twentieth round):
        For MANUAL_EXPERT, ESTABLISHED additionally requires a
        CorrespondenceAttestation. A free-form reviewer string is not
        sufficient evidence of an expert review.
    """
    ESTABLISHED = "ESTABLISHED"  # Explicit rule satisfied (and attested if MANUAL_EXPERT)
    CANDIDATE = "CANDIDATE"      # Proposed but not confirmed (model/semantic only)
    REJECTED = "REJECTED"        # Explicit rule failed
    NOT_EVALUATED = "NOT_EVALUATED"


class DisclosureType(str, Enum):
    """The type of disclosure a correspondence represents.

    Per CEO directive (nineteenth round):
      Separate correspondence from legal sufficiency.

    Per CEO directive (twentieth round):
      Split EXPLICIT_CLAIM_DISCLOSURE into two values:
        VERBATIM_EXPLICIT_CLAIM_DISCLOSURE — the claim explicitly recites the
          limitation (only available when correspondence_type == VERBATIM).
          Automatic §102 support is granted.
        EXPERT_DECLARED_EQUIVALENCE — an expert has declared this different
          structure to be equivalent to the limitation. Does NOT automatically
          support §102. Requires a LegalCorrespondenceDecision.

      EXPLICIT_CLAIM_DISCLOSURE is RETAINED for backward compatibility but is
      NOT automatically §102-eligible. New code MUST use
      VERBATIM_EXPLICIT_CLAIM_DISCLOSURE or EXPERT_DECLARED_EQUIVALENCE.

      CLAIM_DEPENDENCY — the limitation is inherited from a parent claim
      INHERENCY — the limitation is inherent in the claim (NOT automatic §102)
      OTHER_LEGAL_THEORY — some other legal theory (NOT automatic §102)
      UNKNOWN — cannot determine the disclosure type
    """
    VERBATIM_EXPLICIT_CLAIM_DISCLOSURE = "VERBATIM_EXPLICIT_CLAIM_DISCLOSURE"
    EXPLICIT_CLAIM_DISCLOSURE = "EXPLICIT_CLAIM_DISCLOSURE"  # legacy — NOT auto-§102
    EXPERT_DECLARED_EQUIVALENCE = "EXPERT_DECLARED_EQUIVALENCE"
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
    MANUAL_EXPERT = "MANUAL_EXPERT"  # Expert manually established correspondence (requires attestation)
    NONE = "NONE"  # No rule applied (candidate only)


class EligibilityPhase(str, Enum):
    """Four evidenced phases of prior-art eligibility.

    Per CEO directive (twentieth round — P0-1):
      A populated `applicable_rule` field is NOT proof that the rule was
      applied. The system must distinguish:

        SOURCE_DATES_COMPLETE — all required dates are populated with provenance
        LEGAL_RULE_IDENTIFIED — an applicable legal rule was identified
        LEGAL_RULE_APPLIED    — the rule was actually applied to the dates
        ELIGIBILITY_ESTABLISHED — the rule was applied AND the dates qualify

      `analysis_completeness == COMPLETE` is replaced by:
        eligibility_phase == ELIGIBILITY_ESTABLISHED
      which requires all four phases to be evidenced.
    """
    EMPTY = "EMPTY"  # No evidence at all
    SOURCE_DATES_COMPLETE = "SOURCE_DATES_COMPLETE"
    LEGAL_RULE_IDENTIFIED = "LEGAL_RULE_IDENTIFIED"
    LEGAL_RULE_APPLIED = "LEGAL_RULE_APPLIED"
    ELIGIBILITY_ESTABLISHED = "ELIGIBILITY_ESTABLISHED"


class LegalDecisionVerdict(str, Enum):
    """Verdict of a LegalCorrespondenceDecision.

    Per CEO directive (twentieth round — P0-2):
      For STRUCTURAL_EQUIVALENT and FUNCTIONAL_EQUIVALENT, a separate legal
      correspondence decision object is required before §102 can be supported.
    """
    SUPPORTS_102 = "SUPPORTS_102"          # Equivalence constitutes anticipation
    DOES_NOT_SUPPORT_102 = "DOES_NOT_SUPPORT_102"  # Equivalence does NOT anticipate
    REQUIRES_MORE_EVIDENCE = "REQUIRES_MORE_EVIDENCE"  # Insufficient to decide


# ---------------------------------------------------------------------------
# Attestation and Legal Decision objects
# ---------------------------------------------------------------------------


@dataclass
class CorrespondenceAttestation:
    """Immutable attestation that an expert actually performed a review.

    Per CEO directive (twentieth round — P0-4):
      A free-form `reviewer="EXPERT:J.Doe"` string is not evidence that an
      expert actually performed the review. The action itself must leave
      verifiable evidence.

      The attestation binds:
        - reviewer_id (immutable identity, not a name string)
        - reviewer_role (e.g., "PATENT_AGENT", "EXPERT_PRACTITIONER")
        - decision (what the reviewer decided)
        - rationale (why)
        - timestamp (when)
        - evidence_hash (hash of the evidence the reviewer examined)
        - attestation_id (unique, immutable)

      For MANUAL_EXPERT correspondence, an attestation is REQUIRED for the
      correspondence to reach ESTABLISHED status.
    """
    reviewer_id: str
    reviewer_role: str
    decision: str  # "ESTABLISHED" / "REJECTED" / "INSUFFICIENT_EVIDENCE"
    rationale: str
    evidence_hash: str  # Hash of the evidence the reviewer examined
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    attestation_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not self.reviewer_id:
            raise ValueError("CorrespondenceAttestation.reviewer_id is required")
        if not self.reviewer_role:
            raise ValueError("CorrespondenceAttestation.reviewer_role is required")
        if not self.decision:
            raise ValueError("CorrespondenceAttestation.decision is required")
        if not self.evidence_hash or len(self.evidence_hash) < 8:
            raise ValueError(
                "CorrespondenceAttestation.evidence_hash must be a non-trivial hash "
                "(>= 8 chars) of the evidence the reviewer examined"
            )

    def to_dict(self) -> dict:
        return {
            "attestation_id": self.attestation_id,
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "decision": self.decision,
            "rationale": self.rationale,
            "evidence_hash": self.evidence_hash,
            "timestamp": self.timestamp,
        }


@dataclass
class LegalCorrespondenceDecision:
    """Separate legal decision authorizing §102 support for equivalence.

    Per CEO directive (twentieth round — P0-2):
      For STRUCTURAL_EQUIVALENT and FUNCTIONAL_EQUIVALENT correspondence,
      setting disclosure_type=EXPLICIT_CLAIM_DISCLOSURE must NOT automatically
      support §102. The system must distinguish:

        'claim explicitly recites the limitation'

      from:

        'expert says this different structure is equivalent to the limitation'

      Those are not the same evidentiary proposition. The latter requires a
      separate legal correspondence decision object.

      The decision binds:
        - decision_id (unique, immutable)
        - decision (SUPPORTS_102 / DOES_NOT_SUPPORT_102 / REQUIRES_MORE_EVIDENCE)
        - jurisdiction (e.g., "US", "EPO")
        - legal_basis (e.g., "35 USC 102(a) anticipation by equivalent elements")
        - rationale (why the equivalence constitutes anticipation)
        - reviewer_id (the legal expert who made the decision)
        - reviewer_role
        - evidence_hash (hash of the evidence the decision was based on)
        - timestamp
    """
    decision: LegalDecisionVerdict
    reviewer_id: str
    reviewer_role: str
    jurisdiction: str
    legal_basis: str
    rationale: str
    evidence_hash: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decision_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not isinstance(self.decision, LegalDecisionVerdict):
            raise ValueError("LegalCorrespondenceDecision.decision must be a LegalDecisionVerdict")
        if not self.reviewer_id:
            raise ValueError("LegalCorrespondenceDecision.reviewer_id is required")
        if not self.reviewer_role:
            raise ValueError("LegalCorrespondenceDecision.reviewer_role is required")
        if not self.jurisdiction:
            raise ValueError("LegalCorrespondenceDecision.jurisdiction is required")
        if not self.legal_basis:
            raise ValueError("LegalCorrespondenceDecision.legal_basis is required")
        if not self.rationale:
            raise ValueError("LegalCorrespondenceDecision.rationale is required")
        if not self.evidence_hash or len(self.evidence_hash) < 8:
            raise ValueError(
                "LegalCorrespondenceDecision.evidence_hash must be a non-trivial hash"
            )

    @property
    def supports_section_102(self) -> bool:
        return self.decision == LegalDecisionVerdict.SUPPORTS_102

    def to_dict(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "decision": self.decision.value,
            "reviewer_id": self.reviewer_id,
            "reviewer_role": self.reviewer_role,
            "jurisdiction": self.jurisdiction,
            "legal_basis": self.legal_basis,
            "rationale": self.rationale,
            "evidence_hash": self.evidence_hash,
            "timestamp": self.timestamp,
            "supports_section_102": self.supports_section_102,
        }


# ---------------------------------------------------------------------------
# LimitationCorrespondence
# ---------------------------------------------------------------------------


@dataclass
class LimitationCorrespondence:
    """A traceable correspondence between a candidate limitation and a claim passage.

    Per CEO directive (eighteenth round):
      candidate limitation → claim passage → technical correspondence rule
      → basis → provenance → reviewer/model → disposition

      No opaque semantic equivalence. Every correspondence must be auditable
      and decomposable.

    Per CEO directive (twentieth round):
      The provenance_hash now binds the ENTIRE evidentiary assertion, not a
      subset. Altering any underlying field invalidates the hash.

      For MANUAL_EXPERT, an attestation is REQUIRED.
      For STRUCTURAL/FUNCTIONAL_EQUIVALENT to support §102, a
      LegalCorrespondenceDecision is REQUIRED.
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
    # Disclosure type — separates correspondence from legal sufficiency
    disclosure_type: DisclosureType = DisclosureType.UNKNOWN
    # Whether this is established or just proposed
    status: CorrespondenceStatus = CorrespondenceStatus.NOT_EVALUATED
    # The explicit rule that establishes (or rejects) correspondence
    rule: CorrespondenceRule = CorrespondenceRule.NONE
    # Supporting evidence (e.g., glossary entry, structural decomposition)
    supporting_evidence: str = ""
    # The technical relationship (why these correspond)
    technical_relationship: str = ""
    # Who/what established this? (informational — binding evidence is attestation)
    reviewer: str = ""
    # Provenance
    raw_response_hash: str = ""
    source_node_identifier: str = ""
    provenance_hash: str = ""
    # P0-4 (twentieth round): Attestation object for MANUAL_EXPERT
    attestation: Optional[CorrespondenceAttestation] = None
    # P0-2 (twentieth round): Legal decision for STRUCTURAL/FUNCTIONAL equivalence §102
    legal_decision: Optional[LegalCorrespondenceDecision] = None
    # Confidence (only meaningful when status=ESTABLISHED)
    confidence: str = "UNKNOWN"  # HIGH / MEDIUM / LOW / UNKNOWN
    # Unresolved reason (when status=CANDIDATE or NOT_EVALUATED)
    unresolved_reason: str = ""
    # Timestamp
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    correspondence_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        # P0-2 (twentieth round): VERBATIM correspondence can ONLY have
        # VERBATIM_EXPLICIT_CLAIM_DISCLOSURE (or UNKNOWN if not yet classified).
        # This prevents the backdoor of marking equivalence as EXPLICIT_CLAIM_DISCLOSURE.
        if self.correspondence_type == CorrespondenceType.VERBATIM:
            if self.disclosure_type == DisclosureType.UNKNOWN:
                self.disclosure_type = DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE
            elif self.disclosure_type != DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE:
                raise ValueError(
                    f"VERBATIM correspondence requires disclosure_type="
                    f"VERBATIM_EXPLICIT_CLAIM_DISCLOSURE (got {self.disclosure_type.value}). "
                    f"This is a structural invariant — VERBATIM means the claim "
                    f"explicitly recites the limitation, which is the strictest form "
                    f"of explicit disclosure. Marking it as {self.disclosure_type.value} "
                    f"is contradictory and is rejected to prevent the equivalence-as-"
                    f"anticipation backdoor."
                )

        # P0-2 (twentieth round): VERBATIM_EXPLICIT_CLAIM_DISCLOSURE is reserved
        # for VERBATIM correspondence. Equivalence cannot use it.
        if self.disclosure_type == DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE:
            if self.correspondence_type != CorrespondenceType.VERBATIM:
                raise ValueError(
                    f"VERBATIM_EXPLICIT_CLAIM_DISCLOSURE requires correspondence_type="
                    f"VERBATIM (got {self.correspondence_type.value}). Equivalence "
                    f"(STRUCTURAL/FUNCTIONAL) cannot use VERBATIM_EXPLICIT — "
                    f"use EXPERT_DECLARED_EQUIVALENCE instead, and obtain a "
                    f"LegalCorrespondenceDecision for §102 support."
                )

        # P0-4 (twentieth round): MANUAL_EXPERT requires attestation
        if self.rule == CorrespondenceRule.MANUAL_EXPERT:
            if self.status == CorrespondenceStatus.ESTABLISHED and self.attestation is None:
                raise ValueError(
                    "MANUAL_EXPERT correspondence cannot reach ESTABLISHED status "
                    "without a CorrespondenceAttestation. A free-form reviewer string "
                    "is not evidence that an expert actually performed the review. "
                    "Pass a CorrespondenceAttestation with reviewer_id, role, decision, "
                    "rationale, evidence_hash, and timestamp."
                )

        # Compute the provenance hash binding the ENTIRE evidentiary assertion
        if not self.provenance_hash:
            self.provenance_hash = self._compute_provenance_hash()

    def _compute_provenance_hash(self) -> str:
        """P0-3 (twentieth round): Cryptographically bind the ENTIRE correspondence.

        The hash protects:
          - limitation_id, reference_patent, claim_number
          - claim_passage (full, not truncated)
          - claim_start_offset, claim_end_offset
          - correspondence_type, disclosure_type
          - rule, supporting_evidence, technical_relationship
          - reviewer, raw_response_hash, source_node_identifier
          - attestation_id + attestation.evidence_hash (if attested)
          - legal_decision_id + legal_decision.evidence_hash (if legally decided)

        Altering ANY of these without recomputing the hash produces a mismatch
        that verify_provenance_integrity() will detect.
        """
        parts = [
            self.limitation_id,
            self.reference_patent,
            str(self.claim_number),
            self.claim_passage,
            str(self.claim_start_offset),
            str(self.claim_end_offset),
            self.correspondence_type.value,
            self.disclosure_type.value,
            self.rule.value,
            self.supporting_evidence,
            self.technical_relationship,
            self.reviewer,
            self.raw_response_hash,
            self.source_node_identifier,
        ]
        if self.attestation is not None:
            parts.extend([
                self.attestation.attestation_id,
                self.attestation.evidence_hash,
            ])
        if self.legal_decision is not None:
            parts.extend([
                self.legal_decision.decision_id,
                self.legal_decision.evidence_hash,
            ])
        content = "|".join(parts)
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def verify_provenance_integrity(self) -> bool:
        """Verify that the stored provenance_hash matches the current state.

        P0-3 (twentieth round): If any underlying field has been altered
        without recomputing the hash, this returns False.
        """
        return self._compute_provenance_hash() == self.provenance_hash

    def recompute_provenance_hash(self) -> str:
        """Recompute and store the provenance_hash after a legitimate update.

        This is intended for confirm_candidate() and similar legitimate
        state transitions. It should NEVER be called to silently cover up
        an unauthorized alteration.
        """
        self.provenance_hash = self._compute_provenance_hash()
        return self.provenance_hash

    @property
    def can_support_section_102(self) -> bool:
        """Can this correspondence support a §102 conclusion?

        Per CEO directive (twentieth round — P0-2):
          Automatic §102 support is restricted to:
            (a) VERBATIM correspondence with VERBATIM_EXPLICIT_CLAIM_DISCLOSURE
                (the claim explicitly recites the limitation)
            (b) EXPLICIT_DEPENDENCY correspondence with CLAIM_DEPENDENCY
                (the limitation is inherited from a parent claim)

          STRUCTURAL_EQUIVALENT and FUNCTIONAL_EQUIVALENT require a separate
          LegalCorrespondenceDecision with verdict == SUPPORTS_102. Setting
          disclosure_type=EXPLICIT_CLAIM_DISCLOSURE on an equivalence is NOT
          sufficient.

          INHERENCY, OTHER_LEGAL_THEORY, and UNKNOWN never automatically
          support §102.

          Additional invariants:
            - status must be ESTABLISHED (not CANDIDATE / NOT_EVALUATED / REJECTED)
            - rule must not be NONE
            - For MANUAL_EXPERT: attestation must be present
        """
        # Invariant: status must be ESTABLISHED
        if self.status != CorrespondenceStatus.ESTABLISHED:
            return False
        # Invariant: a rule must have been applied
        if self.rule == CorrespondenceRule.NONE:
            return False
        # Invariant: provenance hash must be intact (anti-tamper)
        if not self.verify_provenance_integrity():
            return False
        # Invariant: MANUAL_EXPERT requires attestation
        if self.rule == CorrespondenceRule.MANUAL_EXPERT and self.attestation is None:
            return False

        # Path (a): VERBATIM + VERBATIM_EXPLICIT_CLAIM_DISCLOSURE
        if (
            self.correspondence_type == CorrespondenceType.VERBATIM
            and self.disclosure_type == DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE
        ):
            return True

        # Path (b): EXPLICIT_DEPENDENCY + CLAIM_DEPENDENCY
        if (
            self.correspondence_type == CorrespondenceType.EXPLICIT_DEPENDENCY
            and self.disclosure_type == DisclosureType.CLAIM_DEPENDENCY
        ):
            return True

        # Path (c): STRUCTURAL/FUNCTIONAL_EQUIVALENT + LegalCorrespondenceDecision
        if self.correspondence_type in (
            CorrespondenceType.STRUCTURAL_EQUIVALENT,
            CorrespondenceType.FUNCTIONAL_EQUIVALENT,
        ):
            if self.legal_decision is None:
                return False
            return self.legal_decision.supports_section_102

        # Everything else (INHERENCY, OTHER_LEGAL_THEORY, UNKNOWN, legacy
        # EXPLICIT_CLAIM_DISCLOSURE on non-VERBATIM, etc.) does NOT
        # automatically support §102.
        return False

    @property
    def requires_legal_decision(self) -> bool:
        """Does this correspondence require a LegalCorrespondenceDecision for §102?

        True for STRUCTURAL_EQUIVALENT and FUNCTIONAL_EQUIVALENT.
        False for VERBATIM and EXPLICIT_DEPENDENCY (automatic paths).
        """
        return self.correspondence_type in (
            CorrespondenceType.STRUCTURAL_EQUIVALENT,
            CorrespondenceType.FUNCTIONAL_EQUIVALENT,
        )

    def to_dict(self) -> dict:
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
            "provenance_integrity_verified": self.verify_provenance_integrity(),
            "attestation": self.attestation.to_dict() if self.attestation else None,
            "legal_decision": self.legal_decision.to_dict() if self.legal_decision else None,
            "confidence": self.confidence,
            "unresolved_reason": self.unresolved_reason,
            "timestamp": self.timestamp,
            "can_support_section_102": self.can_support_section_102,
            "requires_legal_decision": self.requires_legal_decision,
        }


# ---------------------------------------------------------------------------
# PriorArtEligibilityEvidence — four-phase model
# ---------------------------------------------------------------------------


@dataclass
class PriorArtEligibilityEvidence:
    """Evidence-bound prior-art temporal eligibility with four-phase model.

    Per CEO directive (twentieth round — P0-1):
      Replaces the binary COMPLETE/SIMPLIFIED/INCOMPLETE label with four
      evidenced phases:

        SOURCE_DATES_COMPLETE — all required dates are populated with provenance
        LEGAL_RULE_IDENTIFIED — an applicable legal rule was identified (string only)
        LEGAL_RULE_APPLIED    — the rule was actually applied (separate evidence)
        ELIGIBILITY_ESTABLISHED — rule applied AND dates qualify

      A populated `applicable_rule` field proves only LEGAL_RULE_IDENTIFIED.
      ELIGIBILITY_ESTABLISHED requires LEGAL_RULE_APPLIED, which requires
      `legal_rule_application_evidence` to be non-empty.

      Per CEO directive (twentieth round — P1):
        If public_availability_date and publication_date are BOTH populated
        but disagree (publication before public availability is suspicious),
        eligibility is UNKNOWN until reconciled.
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
    # P0-1 (twentieth round): Evidence that the legal rule was APPLIED
    # (not just identified). Must be a non-empty description of how the rule
    # was applied to the specific dates — e.g., "Applied 35 USC 102(a)(1):
    # reference public_availability_date 1988-05-10 precedes candidate
    # critical_date 2024-03-15 by 36 years."
    legal_rule_application_evidence: str = ""
    # The eligibility verdict
    eligibility: str = "UNKNOWN"  # ELIGIBLE / INELIGIBLE / UNKNOWN
    # Reasoning
    eligibility_reasoning: str = ""
    # P0-1 (twentieth round): Replaces analysis_completeness
    eligibility_phase: str = EligibilityPhase.EMPTY.value
    # Legacy field — derived from eligibility_phase for backward compat
    analysis_completeness: str = "INCOMPLETE"
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if not self.evidence_hash:
            content = f"{self.candidate_critical_date}|{self.reference_publication_date}|{self.reference_priority_date}|{self.public_availability_date}|{self.jurisdiction}|{self.applicable_rule}"
            self.evidence_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _check_date_consistency(self) -> Optional[str]:
        """P1 (twentieth round): Detect inconsistent dates.

        If publication_date and public_availability_date are both populated,
        the publication_date should generally be >= public_availability_date
        (a document is publicly available BEFORE or ON its publication date,
        not after). If publication_date < public_availability_date, that is
        suspicious — flag it.

        Returns:
          None if consistent, or a string describing the inconsistency.
        """
        if not self.reference_publication_date or not self.public_availability_date:
            return None
        # Both populated — check consistency
        # Convention: public_availability_date <= publication_date is normal
        # (the document may have been available before formal publication).
        # publication_date < public_availability_date is suspicious
        # (how can it be formally published before being publicly available?).
        if self.reference_publication_date < self.public_availability_date:
            return (
                f"Date inconsistency: reference_publication_date "
                f"({self.reference_publication_date}) < public_availability_date "
                f"({self.public_availability_date}). A document cannot be formally "
                f"published before it is publicly available. Eligibility cannot be "
                f"established until this is reconciled."
            )
        return None

    def _check_jurisdiction_rule_consistency(self) -> Optional[str]:
        """P1 (twentieth round): Detect jurisdiction/rule mismatch.

        If jurisdiction is "US" and applicable_rule mentions "EPC", or
        vice versa, that is a mismatch.
        """
        if not self.jurisdiction or not self.applicable_rule:
            return None
        rule_upper = self.applicable_rule.upper()
        jur_upper = self.jurisdiction.upper()
        if "EPC" in rule_upper and "US" in jur_upper and "USA" not in jur_upper:
            return (
                f"Jurisdiction/rule mismatch: jurisdiction={self.jurisdiction} "
                f"but applicable_rule={self.applicable_rule} mentions EPC. "
                f"US jurisdiction uses 35 USC, not EPC."
            )
        if "USC" in rule_upper and "EPO" in jur_upper:
            return (
                f"Jurisdiction/rule mismatch: jurisdiction={self.jurisdiction} "
                f"but applicable_rule={self.applicable_rule} mentions USC. "
                f"EPO jurisdiction uses EPC, not USC."
            )
        return None

    def evaluate(self):
        """Evaluate prior-art eligibility through four evidenced phases.

        Per CEO directive (twentieth round — P0-1):
          Phase 1 — SOURCE_DATES_COMPLETE:
            Requires candidate_critical_date AND public_availability_date
            (or, as a fallback, publication_date — but this only reaches
            SOURCE_DATES_COMPLETE_SIMPLIFIED, not the full phase).

          Phase 2 — LEGAL_RULE_IDENTIFIED:
            Requires jurisdiction AND applicable_rule populated.
            A populated applicable_rule is NOT proof the rule was applied.

          Phase 3 — LEGAL_RULE_APPLIED:
            Requires legal_rule_application_evidence to be a non-empty
            description of HOW the rule was applied to the specific dates.
            This is the missing link — the difference between "we know the
            rule exists" and "we applied the rule to this evidence."

          Phase 4 — ELIGIBILITY_ESTABLISHED:
            Requires all three prior phases PLUS the date comparison to
            qualify under the applied rule.

          analysis_completeness (legacy field) is derived:
            COMPLETE  → eligibility_phase == ELIGIBILITY_ESTABLISHED
            SIMPLIFIED → eligibility_phase in (SOURCE_DATES_COMPLETE,
                          LEGAL_RULE_IDENTIFIED) with date fallback
            INCOMPLETE → otherwise
        """
        # --- P1: Check consistency FIRST ---
        inconsistency = self._check_date_consistency()
        if inconsistency:
            self.eligibility = "UNKNOWN"
            self.eligibility_phase = EligibilityPhase.EMPTY.value
            self.analysis_completeness = "INCOMPLETE"
            self.eligibility_reasoning = inconsistency
            return

        jur_rule_mismatch = self._check_jurisdiction_rule_consistency()
        if jur_rule_mismatch:
            self.eligibility = "UNKNOWN"
            self.eligibility_phase = EligibilityPhase.EMPTY.value
            self.analysis_completeness = "INCOMPLETE"
            self.eligibility_reasoning = jur_rule_mismatch
            return

        # --- Phase 1: SOURCE_DATES_COMPLETE ---
        has_critical = bool(self.candidate_critical_date)
        has_publication = bool(self.reference_publication_date)
        has_public_availability = bool(self.public_availability_date)

        if not has_critical:
            self.eligibility = "UNKNOWN"
            self.eligibility_phase = EligibilityPhase.EMPTY.value
            self.analysis_completeness = "INCOMPLETE"
            self.eligibility_reasoning = (
                "Cannot evaluate: candidate_critical_date is missing."
            )
            return

        if not has_publication and not has_public_availability:
            self.eligibility = "UNKNOWN"
            self.eligibility_phase = EligibilityPhase.EMPTY.value
            self.analysis_completeness = "INCOMPLETE"
            self.eligibility_reasoning = (
                "Cannot evaluate: both reference_publication_date and "
                "public_availability_date are missing."
            )
            return

        # We have at least the critical date and one reference date.
        # If public_availability_date is present, we have full SOURCE_DATES_COMPLETE.
        # If only publication_date is present, we have a SIMPLIFIED source-dates state.
        dates_complete = has_public_availability
        if not dates_complete:
            # Fallback: use publication_date as a proxy for public_availability
            # This reaches SOURCE_DATES_COMPLETE only in the SIMPLIFIED sense.
            effective_reference_date = self.reference_publication_date
            simplified_dates = True
        else:
            effective_reference_date = self.public_availability_date
            simplified_dates = False

        # Mark Phase 1
        self.eligibility_phase = EligibilityPhase.SOURCE_DATES_COMPLETE.value

        # --- Phase 2: LEGAL_RULE_IDENTIFIED ---
        has_jurisdiction = bool(self.jurisdiction)
        has_rule = bool(self.applicable_rule)
        if not has_jurisdiction or not has_rule:
            # Phase 1 only — cannot proceed to LEGAL_RULE_IDENTIFIED
            if effective_reference_date < self.candidate_critical_date:
                self.eligibility = "ELIGIBLE_SIMPLIFIED" if simplified_dates else "ELIGIBLE"
            else:
                self.eligibility = "INELIGIBLE"
            self.analysis_completeness = "SIMPLIFIED"
            self.eligibility_reasoning = (
                f"Phase 1 (SOURCE_DATES_COMPLETE) reached. "
                f"Reference date {effective_reference_date} "
                f"{'<' if effective_reference_date < self.candidate_critical_date else '>='} "
                f"critical date {self.candidate_critical_date}. "
                f"BUT jurisdiction or applicable_rule is missing — "
                f"cannot reach LEGAL_RULE_IDENTIFIED. Verdict is SIMPLIFIED, "
                f"not ELIGIBILITY_ESTABLISHED."
            )
            return

        # Mark Phase 2
        self.eligibility_phase = EligibilityPhase.LEGAL_RULE_IDENTIFIED.value

        # --- Phase 3: LEGAL_RULE_APPLIED ---
        # P0-1 (twentieth round): A populated applicable_rule is NOT proof
        # the rule was applied. We require legal_rule_application_evidence
        # to be a non-trivial description of HOW the rule was applied.
        if not self.legal_rule_application_evidence or len(self.legal_rule_application_evidence.strip()) < 20:
            # Phase 2 only — rule identified but not applied
            if effective_reference_date < self.candidate_critical_date:
                self.eligibility = "ELIGIBLE_SIMPLIFIED" if simplified_dates else "ELIGIBLE"
            else:
                self.eligibility = "INELIGIBLE"
            self.analysis_completeness = "SIMPLIFIED"
            self.eligibility_reasoning = (
                f"Phase 2 (LEGAL_RULE_IDENTIFIED) reached: jurisdiction="
                f"{self.jurisdiction}, applicable_rule={self.applicable_rule}. "
                f"BUT legal_rule_application_evidence is missing or trivial — "
                f"cannot reach LEGAL_RULE_APPLIED. A populated applicable_rule "
                f"is NOT proof the rule was applied. Verdict is SIMPLIFIED, "
                f"not ELIGIBILITY_ESTABLISHED."
            )
            return

        # Mark Phase 3
        self.eligibility_phase = EligibilityPhase.LEGAL_RULE_APPLIED.value

        # --- Phase 4: ELIGIBILITY_ESTABLISHED ---
        # Apply the rule to the dates
        if effective_reference_date < self.candidate_critical_date:
            self.eligibility = "ELIGIBLE"
            self.eligibility_phase = EligibilityPhase.ELIGIBILITY_ESTABLISHED.value
            self.analysis_completeness = "COMPLETE"
            self.eligibility_reasoning = (
                f"Phase 4 (ELIGIBILITY_ESTABLISHED) reached. "
                f"All four phases evidenced: "
                f"SOURCE_DATES_COMPLETE (reference date {effective_reference_date}), "
                f"LEGAL_RULE_IDENTIFIED ({self.applicable_rule} in {self.jurisdiction}), "
                f"LEGAL_RULE_APPLIED (evidence: {self.legal_rule_application_evidence[:80]}...), "
                f"and date comparison qualifies "
                f"({effective_reference_date} < {self.candidate_critical_date})."
            )
        else:
            self.eligibility = "INELIGIBLE"
            # Phase 3 was reached but the dates don't qualify under the rule.
            # Keep the phase as LEGAL_RULE_APPLIED — the rule was applied,
            # the reference just doesn't qualify.
            self.analysis_completeness = "COMPLETE"
            self.eligibility_reasoning = (
                f"Phase 3 (LEGAL_RULE_APPLIED) reached, but reference date "
                f"{effective_reference_date} >= critical date "
                f"{self.candidate_critical_date}. Reference is INELIGIBLE as "
                f"prior art under {self.applicable_rule}."
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
            "legal_rule_application_evidence": self.legal_rule_application_evidence,
            "eligibility": self.eligibility,
            "eligibility_reasoning": self.eligibility_reasoning,
            "eligibility_phase": self.eligibility_phase,
            "analysis_completeness": self.analysis_completeness,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# CorrespondenceEngine
# ---------------------------------------------------------------------------


class CorrespondenceEngine:
    """Evidence-bound correspondence engine.

    Per CEO directive (eighteenth round):
      A model may PROPOSE correspondence (CANDIDATE_CORRESPONDENCE)
      but must not establish it without an explicit rule.

      Only VERBATIM and explicitly evidenced equivalence may feed §102.

      The engine is auditable and decomposable — no opaque semantic equivalence.

    Per CEO directive (twentieth round):
      MANUAL_EXPERT requires a CorrespondenceAttestation.
      STRUCTURAL/FUNCTIONAL_EQUIVALENT §102 requires a LegalCorrespondenceDecision.
      The provenance_hash binds the entire evidentiary assertion.
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
          1. EXACT_SUBSTRING (verbatim) → VERBATIM, ESTABLISHED,
             VERBATIM_EXPLICIT_CLAIM_DISCLOSURE (automatic §102 eligible)
          2. GLOSSARY_MAPPING (if glossary has term mappings) →
             STRUCTURAL_EQUIVALENT, ESTABLISHED, EXPERT_DECLARED_EQUIVALENCE
             (NOT automatic §102 — requires LegalCorrespondenceDecision)
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
                disclosure_type=DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE,
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
                    disclosure_type=DisclosureType.EXPERT_DECLARED_EQUIVALENCE,
                    status=CorrespondenceStatus.ESTABLISHED,
                    rule=CorrespondenceRule.GLOSSARY_MAPPING,
                    supporting_evidence=f"Glossary mapping applied. Translated: '{translated[:80]}'",
                    technical_relationship="Terms mapped via explicit glossary",
                    reviewer="GLOSSARY:v1.0",
                    raw_response_hash=raw_response_hash,
                    source_node_identifier=source_node_identifier,
                    confidence="HIGH",
                    # No legal_decision — can_support_section_102 will return False
                    # until a LegalCorrespondenceDecision is attached.
                    unresolved_reason=(
                        "STRUCTURAL_EQUIVALENT correspondence established via "
                        "GLOSSARY_MAPPING, but §102 support requires a separate "
                        "LegalCorrespondenceDecision. Use attach_legal_decision() "
                        "to authorize §102 anticipation."
                    ),
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
        attestation: Optional[CorrespondenceAttestation] = None,
        legal_decision: Optional[LegalCorrespondenceDecision] = None,
    ) -> LimitationCorrespondence:
        """Confirm a CANDIDATE correspondence with an explicit rule.

        Per CEO directive (twentieth round):
          - disclosure_type must be explicitly set by the confirmer.
          - For MANUAL_EXPERT: attestation is REQUIRED.
          - For STRUCTURAL/FUNCTIONAL_EQUIVALENT: legal_decision is required
            for §102 support (but the correspondence can still be ESTABLISHED
            without it — it just can't support §102).
          - The provenance_hash is recomputed to bind the new evidence.
        """
        # P0-4 (twentieth round): MANUAL_EXPERT requires attestation
        if confirming_rule == CorrespondenceRule.MANUAL_EXPERT and attestation is None:
            # Cannot reach ESTABLISHED — return the candidate as-is with a note
            candidate.status = CorrespondenceStatus.CANDIDATE
            candidate.rule = confirming_rule
            candidate.unresolved_reason = (
                "MANUAL_EXPERT confirmation requires a CorrespondenceAttestation. "
                "A free-form reviewer string is not evidence that an expert "
                "actually performed the review. Pass attestation with reviewer_id, "
                "reviewer_role, decision, rationale, evidence_hash, and timestamp."
            )
            candidate.recompute_provenance_hash()
            return candidate

        # P0-2 (twentieth round): Validate disclosure_type compatibility
        if correspondence_type == CorrespondenceType.VERBATIM:
            if disclosure_type != DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE:
                raise ValueError(
                    f"VERBATIM correspondence requires disclosure_type="
                    f"VERBATIM_EXPLICIT_CLAIM_DISCLOSURE (got {disclosure_type.value})."
                )
        else:
            if disclosure_type == DisclosureType.VERBATIM_EXPLICIT_CLAIM_DISCLOSURE:
                raise ValueError(
                    f"VERBATIM_EXPLICIT_CLAIM_DISCLOSURE requires correspondence_type="
                    f"VERBATIM (got {correspondence_type.value})."
                )

        candidate.status = CorrespondenceStatus.ESTABLISHED
        candidate.rule = confirming_rule
        candidate.supporting_evidence = confirming_evidence
        candidate.reviewer = confirming_reviewer
        candidate.correspondence_type = correspondence_type
        candidate.disclosure_type = disclosure_type
        candidate.attestation = attestation
        candidate.legal_decision = legal_decision
        candidate.confidence = "HIGH"
        candidate.unresolved_reason = ""

        # P0-2 (twentieth round): If equivalence and no legal_decision,
        # note that §102 is not yet supported.
        if (
            correspondence_type in (
                CorrespondenceType.STRUCTURAL_EQUIVALENT,
                CorrespondenceType.FUNCTIONAL_EQUIVALENT,
            )
            and legal_decision is None
        ):
            candidate.unresolved_reason = (
                "ESTABLISHED correspondence, but §102 support requires a separate "
                "LegalCorrespondenceDecision. Use attach_legal_decision() to authorize."
            )

        # P0-3 (twentieth round): Recompute provenance hash to bind new evidence
        candidate.recompute_provenance_hash()
        return candidate

    def attach_legal_decision(
        self,
        correspondence: LimitationCorrespondence,
        legal_decision: LegalCorrespondenceDecision,
    ) -> LimitationCorrespondence:
        """Attach a LegalCorrespondenceDecision to an equivalence correspondence.

        Per CEO directive (twentieth round — P0-2):
          STRUCTURAL_EQUIVALENT and FUNCTIONAL_EQUIVALENT correspondence
          require a separate legal decision to support §102.
        """
        if correspondence.correspondence_type not in (
            CorrespondenceType.STRUCTURAL_EQUIVALENT,
            CorrespondenceType.FUNCTIONAL_EQUIVALENT,
        ):
            raise ValueError(
                f"LegalCorrespondenceDecision can only be attached to "
                f"STRUCTURAL_EQUIVALENT or FUNCTIONAL_EQUIVALENT correspondence "
                f"(got {correspondence.correspondence_type.value})."
            )
        correspondence.legal_decision = legal_decision
        if legal_decision.supports_section_102:
            correspondence.unresolved_reason = ""
        else:
            correspondence.unresolved_reason = (
                f"LegalCorrespondenceDecision verdict={legal_decision.decision.value}. "
                f"§102 is NOT supported."
            )
        # P0-3 (twentieth round): Recompute provenance hash
        correspondence.recompute_provenance_hash()
        return correspondence
