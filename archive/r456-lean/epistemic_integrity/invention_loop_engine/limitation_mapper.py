"""
Claim Limitation Mapper — maps invention limitations to exact patent claim spans.

Per CEO directive (sixteenth round):
  'The machine must be able to prove its conclusion using a test case that
   was not constructed from the evidence that "proves" the conclusion.'

  P0-1: Eliminate circular testing — limitations from independent spec
  P0-2: Separate discovery matching from legal mapping — word-count ≠ EXACT
  P0-3: Real claim spans — exact substring + offsets + node + hash
  P0-4: Prior-art temporal eligibility — §102 impossible if UNKNOWN
  P0-5: Explicit inheritance chain
  P0-6: Adversarial regression tests
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class LimitationDisposition(str, Enum):
    DIRECT = "DIRECT"
    PARTIAL = "PARTIAL"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class MappingMethod(str, Enum):
    EXACT_SUBSTRING = "EXACT_SUBSTRING"  # Limitation text found verbatim in claim
    SEMANTIC_CANDIDATE = "SEMANTIC_CANDIDATE"  # Word overlap found candidate (NOT sufficient for §102)
    EXPLICIT_CORRESPONDENCE = "EXPLICIT_CORRESPONDENCE"  # Human/explicit rule
    MANUAL = "MANUAL"


class MappingConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class InventionLimitation:
    """A single limitation from an INDEPENDENT candidate specification.

    Per CEO directive (sixteenth round):
      Limitations must come from an independent frozen candidate spec,
      NOT copied from the reference patent's claim text.

      The limitation_text is the CANDIDATE's language, not the reference's.
      The mapper must find correspondence, not identity.
    """
    limitation_id: str
    description: str
    limitation_text: str  # The candidate's own language
    required: bool = True
    source: str = ""  # Must be the candidate spec, not the reference

    def to_dict(self) -> dict:
        return {
            "limitation_id": self.limitation_id,
            "description": self.description,
            "limitation_text": self.limitation_text,
            "required": self.required,
            "source": self.source,
        }


@dataclass
class ClaimSpan:
    """Real claim span with exact offsets.

    Per CEO directive (sixteenth round):
      Every DIRECT mapping must contain:
        exact matched substring, start_offset, end_offset,
        claim_number, source_node_identifier, raw_response_hash
    """
    matched_substring: str
    start_offset: int
    end_offset: int
    claim_number: int
    source_node_identifier: str = ""
    raw_response_hash: str = ""

    def to_dict(self) -> dict:
        return {
            "matched_substring": self.matched_substring,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
            "claim_number": self.claim_number,
            "source_node_identifier": self.source_node_identifier,
            "raw_response_hash": self.raw_response_hash,
        }


@dataclass
class InheritedLimitation:
    """A limitation credited through a dependent claim's parent.

    Per CEO directive (sixteenth round):
      For every inherited limitation, show the explicit chain:
        claim 10 → depends on claim 1 → inherited limitation [A1]
    """
    limitation_id: str
    source_claim_number: int  # The claim where this limitation was actually found
    inheritance_chain: list[int]  # e.g., [10, 1] means: claim 10 inherits from claim 1

    def to_dict(self) -> dict:
        return {
            "limitation_id": self.limitation_id,
            "source_claim_number": self.source_claim_number,
            "inheritance_chain": self.inheritance_chain,
        }


@dataclass
class ClaimLimitationMapping:
    """The mapping of one invention limitation to one patent claim."""
    candidate_id: str
    reference_patent: str
    claim_number: int
    limitation_id: str
    disposition: LimitationDisposition
    # P0-3: Real claim span (not the limitation's own text)
    claim_span: Optional[ClaimSpan] = None
    evidence_hash: str = ""
    mapping_method: MappingMethod = MappingMethod.SEMANTIC_CANDIDATE
    mapping_confidence: MappingConfidence = MappingConfidence.UNKNOWN
    unresolved_reason: str = ""
    # P0-5: Inheritance info
    is_inherited: bool = False
    inherited_from: Optional[InheritedLimitation] = None
    mapping_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mapping_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not self.evidence_hash:
            span_text = self.claim_span.matched_substring if self.claim_span else ""
            content = f"{self.limitation_id}|{self.claim_number}|{span_text}"
            self.evidence_hash = hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "mapping_id": self.mapping_id,
            "candidate_id": self.candidate_id,
            "reference_patent": self.reference_patent,
            "claim_number": self.claim_number,
            "limitation_id": self.limitation_id,
            "disposition": self.disposition.value,
            "claim_span": self.claim_span.to_dict() if self.claim_span else None,
            "evidence_hash": self.evidence_hash,
            "mapping_method": self.mapping_method.value,
            "mapping_confidence": self.mapping_confidence.value,
            "unresolved_reason": self.unresolved_reason,
            "is_inherited": self.is_inherited,
            "inherited_from": self.inherited_from.to_dict() if self.inherited_from else None,
            "mapping_timestamp": self.mapping_timestamp,
        }


@dataclass
class PriorArtEligibility:
    """Prior-art temporal eligibility with provenance-bound dates.

    Per CEO directive (seventeenth round):
      Separate DATE ELIGIBILITY from CLAIM ANTICIPATION.
      Do not collapse them.

      Need: critical_date, priority_date, filing_date, publication_date,
      public_availability_date, jurisdiction, date_source, date_evidence_hash.

      The current engine should NOT call its date logic complete §102
      eligibility analysis — it is a simplified check.
    """
    candidate_critical_date: str = ""  # ISO date
    reference_priority_date: str = ""
    reference_filing_date: str = ""
    reference_publication_date: str = ""
    public_availability_date: str = ""
    jurisdiction: str = ""
    date_source: str = ""  # Where each date came from
    date_evidence_hash: str = ""
    eligibility: str = "UNKNOWN"  # ELIGIBLE / INELIGIBLE / UNKNOWN / SIMPLIFIED_CHECK_ONLY

    def check_eligibility(self):
        """Determine eligibility from dates.

        Per CEO directive (seventeenth round):
          This is a SIMPLIFIED check, not a complete §102 eligibility analysis.
          A real analysis needs priority date, filing date, publication date,
          public availability, jurisdiction, and applicable legal rule.

          If publication_date is unknown → UNKNOWN
          If critical_date is unknown → UNKNOWN
        """
        if not self.reference_publication_date or not self.candidate_critical_date:
            self.eligibility = "UNKNOWN"
            return

        # Simplified check: reference must be published BEFORE critical date
        # This does NOT account for priority dates, provisional applications,
        # grace periods, or jurisdiction-specific rules.
        if self.reference_publication_date < self.candidate_critical_date:
            self.eligibility = "SIMPLIFIED_CHECK_ONLY"
        else:
            self.eligibility = "INELIGIBLE"

    def to_dict(self) -> dict:
        return {
            "candidate_critical_date": self.candidate_critical_date,
            "reference_publication_date": self.reference_publication_date,
            "reference_priority_date": self.reference_priority_date,
            "public_availability_date": self.public_availability_date,
            "jurisdiction": self.jurisdiction,
            "date_source": self.date_source,
            "date_evidence_hash": self.date_evidence_hash,
            "eligibility": self.eligibility,
        }


@dataclass
class Section102Analysis:
    """§102 anticipation analysis with temporal eligibility."""
    candidate_id: str
    reference_patent: str
    per_claim_results: dict[int, dict] = field(default_factory=dict)
    anticipating_claim: Optional[int] = None
    section_102_verdict: str = "NOT_ANALYZED"
    verdict_reasoning: str = ""
    # P0-4: Temporal eligibility
    prior_art_eligibility: Optional[PriorArtEligibility] = None
    analysis_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "reference_patent": self.reference_patent,
            "per_claim_results": {str(k): v for k, v in self.per_claim_results.items()},
            "anticipating_claim": self.anticipating_claim,
            "section_102_verdict": self.section_102_verdict,
            "verdict_reasoning": self.verdict_reasoning,
            "prior_art_eligibility": self.prior_art_eligibility.to_dict() if self.prior_art_eligibility else None,
            "analysis_timestamp": self.analysis_timestamp,
        }


class LimitationMapper:
    """Maps invention limitations to patent claims with exact evidence.

    P0-2 (sixteenth round):
      EXACT_SUBSTRING: the limitation text appears verbatim in the claim.
        → Can establish DIRECT (with real span)
      SEMANTIC_CANDIDATE: word overlap found a candidate.
        → CANNOT establish DIRECT. Only UNKNOWN or PARTIAL.
        → mapping_method = SEMANTIC_CANDIDATE (never EXACT)
    """

    def map_limitation_to_claim(
        self,
        limitation: InventionLimitation,
        claim_text: str,
        claim_number: int,
        reference_patent: str,
        candidate_id: str,
        raw_response_hash: str = "",
        source_node_identifier: str = "",
    ) -> ClaimLimitationMapping:
        """Map one limitation to one claim using exact substring matching.

        Per CEO directive (seventeenth round):
          - DIRECT: only via EXACT_SUBSTRING (verbatim text found in claim)
          - PARTIAL: only via EXPLICIT_CORRESPONDENCE (human/rule-established)
          - ABSENT: only via EXPLICIT_CORRESPONDENCE (human/rule-established)
          - UNKNOWN: default when no exact match and no explicit correspondence

          Semantic retrieval may NOMINATE a candidate passage.
          It may NEVER establish the final disposition by itself.

          No word-overlap heuristic may produce PARTIAL or ABSENT.
          No generated string like "Partial match: ..." may be used as evidence.
          If there is no exact supporting span → UNKNOWN.
        """
        lim_text = limitation.limitation_text.lower().strip()
        claim_lower = claim_text.lower()

        # EXACT_SUBSTRING: find the limitation text verbatim in the claim
        idx = claim_lower.find(lim_text)
        if idx >= 0:
            # Found exact substring — extract the real span
            matched = claim_text[idx:idx + len(lim_text)]  # Original case
            return ClaimLimitationMapping(
                candidate_id=candidate_id,
                reference_patent=reference_patent,
                claim_number=claim_number,
                limitation_id=limitation.limitation_id,
                disposition=LimitationDisposition.DIRECT,
                claim_span=ClaimSpan(
                    matched_substring=matched,
                    start_offset=idx,
                    end_offset=idx + len(lim_text),
                    claim_number=claim_number,
                    source_node_identifier=source_node_identifier,
                    raw_response_hash=raw_response_hash,
                ),
                mapping_method=MappingMethod.EXACT_SUBSTRING,
                mapping_confidence=MappingConfidence.HIGH,
            )

        # No exact substring match → UNKNOWN (not PARTIAL, not ABSENT)
        # Per CEO directive (seventeenth round):
        #   - Absence of keywords ≠ absence of a technical limitation
        #   - Synonyms, functional language, drafting variations make
        #     automated ABSENT unsafe
        #   - Word overlap is a SEMANTIC_CANDIDATE, not a disposition
        #   - If there is no exact supporting span → UNKNOWN
        return ClaimLimitationMapping(
            candidate_id=candidate_id,
            reference_patent=reference_patent,
            claim_number=claim_number,
            limitation_id=limitation.limitation_id,
            disposition=LimitationDisposition.UNKNOWN,
            claim_span=None,  # No exact span → no span
            mapping_method=MappingMethod.SEMANTIC_CANDIDATE,
            mapping_confidence=MappingConfidence.UNKNOWN,
            unresolved_reason=(
                "No exact substring match found. "
                "Semantic word overlap is insufficient to establish "
                "DIRECT, PARTIAL, or ABSENT. Requires explicit correspondence "
                "or expert analysis to resolve."
            ),
        )

    def analyze_section_102(
        self,
        candidate_id: str,
        reference_patent: str,
        limitations: list[InventionLimitation],
        claims: list,
        prior_art_eligibility: PriorArtEligibility = None,
        raw_response_hash: str = "",
    ) -> Section102Analysis:
        """Perform §102 analysis with temporal eligibility and explicit inheritance."""
        analysis = Section102Analysis(
            candidate_id=candidate_id,
            reference_patent=reference_patent,
            prior_art_eligibility=prior_art_eligibility,
        )

        # P0-4: Check temporal eligibility FIRST
        if prior_art_eligibility:
            prior_art_eligibility.check_eligibility()
            if prior_art_eligibility.eligibility == "UNKNOWN":
                analysis.section_102_verdict = "INCONCLUSIVE"
                analysis.verdict_reasoning = (
                    "Prior-art temporal eligibility is UNKNOWN. "
                    "§102 cannot be determined without publication date and critical date."
                )
                return analysis
            if prior_art_eligibility.eligibility == "INELIGIBLE":
                analysis.section_102_verdict = "NOT_ANTICIPATED"
                analysis.verdict_reasoning = (
                    "Reference is INELIGIBLE as prior art: published after critical date."
                )
                return analysis
            # SIMPLIFIED_CHECK_ONLY: proceed but note in reasoning that
            # the temporal check is simplified, not complete §102 eligibility

        required_limitations = [l for l in limitations if l.required]
        required_ids = {l.limitation_id for l in required_limitations}
        claim_lookup = {c.claim_number: c for c in claims}

        for claim in claims:
            # P0-5: Build explicit inheritance chain
            effective_text = claim.exact_claim_text
            inheritance_map: dict[str, InheritedLimitation] = {}

            deps_to_check = list(claim.depends_on_claim_numbers)
            visited = set()
            chain = [claim.claim_number]

            while deps_to_check:
                dep_num = deps_to_check.pop(0)
                if dep_num in visited or dep_num not in claim_lookup:
                    continue
                visited.add(dep_num)
                parent_claim = claim_lookup[dep_num]
                effective_text = parent_claim.exact_claim_text + " " + effective_text
                chain.append(dep_num)
                deps_to_check.extend(parent_claim.depends_on_claim_numbers)

            # Map each limitation
            mappings = []
            present_ids = set()
            missing_ids = set()
            unknown_ids = set()

            for limitation in required_limitations:
                mapping = self.map_limitation_to_claim(
                    limitation=limitation,
                    claim_text=effective_text,
                    claim_number=claim.claim_number,
                    reference_patent=reference_patent,
                    candidate_id=candidate_id,
                    raw_response_hash=raw_response_hash,
                    source_node_identifier=getattr(claim, 'source_node_identifier', ''),
                )

                # P0-5: Check if this limitation came from a parent claim
                if mapping.disposition == LimitationDisposition.DIRECT:
                    # Check if the match is in the parent's text, not this claim's
                    own_text = claim.exact_claim_text.lower()
                    lim_lower = limitation.limitation_text.lower()
                    if lim_lower not in own_text:
                        # This limitation was found in inherited text
                        mapping.is_inherited = True
                        mapping.inherited_from = InheritedLimitation(
                            limitation_id=limitation.limitation_id,
                            source_claim_number=chain[-1] if len(chain) > 1 else claim.claim_number,
                            inheritance_chain=list(reversed(chain)),
                        )

                mappings.append(mapping)

                if mapping.disposition == LimitationDisposition.DIRECT:
                    present_ids.add(limitation.limitation_id)
                elif mapping.disposition == LimitationDisposition.PARTIAL:
                    missing_ids.add(limitation.limitation_id)
                elif mapping.disposition == LimitationDisposition.UNKNOWN:
                    unknown_ids.add(limitation.limitation_id)
                elif mapping.disposition == LimitationDisposition.ABSENT:
                    missing_ids.add(limitation.limitation_id)

            all_present = len(present_ids) == len(required_ids) and not missing_ids and not unknown_ids

            analysis.per_claim_results[claim.claim_number] = {
                "all_present": all_present,
                "present": sorted(present_ids),
                "missing": sorted(missing_ids),
                "unknown": sorted(unknown_ids),
                "inheritance_chain": list(reversed(chain)),
                "mappings": [m.to_dict() for m in mappings],
            }

            if all_present and analysis.anticipating_claim is None:
                analysis.anticipating_claim = claim.claim_number

        # Verdict
        if analysis.anticipating_claim is not None:
            analysis.section_102_verdict = "ANTICIPATED"
            r = analysis.per_claim_results[analysis.anticipating_claim]
            chain = r.get("inheritance_chain", [])
            inherited = [m for m in r.get("mappings", []) if m.get("is_inherited")]
            analysis.verdict_reasoning = (
                f"Claim {analysis.anticipating_claim} "
                f"{'(inheritance chain: ' + '→'.join(str(c) for c in chain) + ') ' if len(chain) > 1 else ''}"
                f"contains ALL {len(required_ids)} required limitations. "
                f"{len(inherited)} inherited from parent claims. "
                f"Prior-art eligibility: {prior_art_eligibility.eligibility if prior_art_eligibility else 'NOT_CHECKED'}."
            )
        else:
            any_unknown = any(len(r.get("unknown", [])) > 0 for r in analysis.per_claim_results.values())
            if any_unknown:
                analysis.section_102_verdict = "INCONCLUSIVE"
                analysis.verdict_reasoning = "Some limitations are UNKNOWN. §102 inconclusive."
            else:
                analysis.section_102_verdict = "NOT_ANTICIPATED"
                analysis.verdict_reasoning = "No single claim contains all required limitations."

        return analysis


def get_c04_limitations_independent() -> list[InventionLimitation]:
    """Get C04 limitations from an INDEPENDENT candidate specification.

    P0-1 (sixteenth round):
      These limitations are defined from the C04 CANDIDATE's requirements,
      NOT from US4741730A's claim text. The wording is the candidate's own
      language describing what it needs, not copied from any reference.

      The mapper must find correspondence between this independent language
      and the reference's claim text — not identity.
    """
    return [
        InventionLimitation(
            limitation_id="C04-L1",
            description="An implantable shunt device with a fluid entry port and a fluid exit port",
            limitation_text="an implantable shunt device with a fluid entry port and a fluid exit port",
            required=True,
            source="C04 candidate specification (independent of any reference patent)",
        ),
        InventionLimitation(
            limitation_id="C04-L2",
            description="A primary drainage channel connecting the entry and exit ports",
            limitation_text="a primary drainage channel connecting the entry and exit ports",
            required=True,
            source="C04 candidate specification (independent of any reference patent)",
        ),
        InventionLimitation(
            limitation_id="C04-L3",
            description="A filtration element positioned within the primary drainage channel",
            limitation_text="a filtration element positioned within the primary drainage channel",
            required=True,
            source="C04 candidate specification (independent of any reference patent)",
        ),
        InventionLimitation(
            limitation_id="C04-L4",
            description="A secondary channel that provides an alternate fluid path bypassing the filtration element",
            limitation_text="a secondary channel that provides an alternate fluid path bypassing the filtration element",
            required=True,
            source="C04 candidate specification (independent of any reference patent)",
        ),
        InventionLimitation(
            limitation_id="C04-L5",
            description="A pressure-responsive valve mechanism in the primary drainage channel",
            limitation_text="a pressure-responsive valve mechanism in the primary drainage channel",
            required=True,
            source="C04 candidate specification (independent of any reference patent)",
        ),
        InventionLimitation(
            limitation_id="C04-L6",
            description="A mechanism for selectively permitting or preventing flow through the secondary channel",
            limitation_text="a mechanism for selectively permitting or preventing flow through the secondary channel",
            required=True,
            source="C04 candidate specification (independent of any reference patent)",
        ),
    ]
