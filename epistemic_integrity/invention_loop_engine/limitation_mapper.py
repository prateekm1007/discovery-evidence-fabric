"""
Claim Limitation Mapper — maps invention limitations to exact patent claim spans.

Per CEO directive (fifteenth round):
  'The machine is not allowed to jump from "this looks similar" to
   "this is anticipated." The entire causal and legal bridge must be explicit.'

  Allowed dispositions: DIRECT / PARTIAL / ABSENT / UNKNOWN
  Never "probably present."

  §102 rule: ONE single claim must contain ALL required limitations.
  Do NOT combine Claim 1 + Claim 2 + Claim 10 into an invented anticipation.
  Dependent claims can matter, but the claim dependency structure must be
  respected exactly.

  Semantic retrieval may FIND candidate claims.
  It must NOT DECLARE anticipation.
  Final §102 mapping must be based on:
    exact limitation → exact claim text → explicit correspondence
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from uuid import uuid4


class LimitationDisposition(str, Enum):
    """The disposition of a single limitation against a single claim.

    Per CEO directive (fifteenth round):
      DIRECT — the claim explicitly recites this limitation
      PARTIAL — the claim partially recites this limitation (some elements present, some missing)
      ABSENT — the claim does not recite this limitation
      UNKNOWN — cannot determine from the claim text alone

      Never "probably present." If uncertain → UNKNOWN.
    """
    DIRECT = "DIRECT"
    PARTIAL = "PARTIAL"
    ABSENT = "ABSENT"
    UNKNOWN = "UNKNOWN"


class MappingMethod(str, Enum):
    """How the mapping was determined.

    EXACT_TEXT_MATCH — the limitation text appears verbatim in the claim
    EXPLICIT_CORRESPONDENCE — a human or explicit rule established the match
    SEMANTIC_CANDIDATE — semantic retrieval found a candidate (NOT sufficient for §102)
    MANUAL — manually mapped (for testing/validation)
    """
    EXACT_TEXT_MATCH = "EXACT_TEXT_MATCH"
    EXPLICIT_CORRESPONDENCE = "EXPLICIT_CORRESPONDENCE"
    SEMANTIC_CANDIDATE = "SEMANTIC_CANDIDATE"
    MANUAL = "MANUAL"


class MappingConfidence(str, Enum):
    """Confidence level of the mapping.

    HIGH — exact text match or explicit correspondence
    MEDIUM — partial text match with clear semantic overlap
    LOW — semantic candidate only (NOT sufficient for §102)
    UNKNOWN — cannot determine
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    UNKNOWN = "UNKNOWN"


@dataclass
class InventionLimitation:
    """A single limitation of an invention candidate.

    A limitation is a specific structural or functional element that
    must be present in a patent claim for the claim to anticipate the invention.

    Example for C04:
      limitation_id: "A1"
      description: "Shunt body with inlet and outlet"
      limitation_text: "a body having an inlet and an outlet"
      required: True  # Must be present for anticipation
    """
    limitation_id: str
    description: str
    limitation_text: str  # The exact text of the limitation as defined
    required: bool = True  # Is this limitation required for §102?
    source: str = ""  # Where this limitation definition came from

    def to_dict(self) -> dict:
        return {
            "limitation_id": self.limitation_id,
            "description": self.description,
            "limitation_text": self.limitation_text,
            "required": self.required,
            "source": self.source,
        }


@dataclass
class ClaimLimitationMapping:
    """The mapping of one invention limitation to one patent claim.

    Per CEO directive (fifteenth round):
      Every limitation needs an explicit disposition:
        DIRECT / PARTIAL / ABSENT / UNKNOWN
      with the exact claim span supporting it.

      The mapping must be evidence-first:
        exact limitation → exact claim text → explicit correspondence

      Semantic matching may FIND candidates but must NOT DECLARE anticipation.
    """
    candidate_id: str
    reference_patent: str  # e.g., "US4741730A"
    claim_number: int
    limitation_id: str
    disposition: LimitationDisposition
    exact_claim_span: str  # The exact text from the claim that supports this disposition
    evidence_hash: str  # SHA-256 of (limitation_text + claim_span)
    mapping_method: MappingMethod
    mapping_confidence: MappingConfidence
    unresolved_reason: str = ""  # Why this is UNKNOWN or PARTIAL (if applicable)
    mapping_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mapping_id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self):
        if not self.evidence_hash:
            content = f"{self.limitation_id}|{self.claim_number}|{self.exact_claim_span}"
            self.evidence_hash = hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "mapping_id": self.mapping_id,
            "candidate_id": self.candidate_id,
            "reference_patent": self.reference_patent,
            "claim_number": self.claim_number,
            "limitation_id": self.limitation_id,
            "disposition": self.disposition.value,
            "exact_claim_span": self.exact_claim_span,
            "evidence_hash": self.evidence_hash,
            "mapping_method": self.mapping_method.value,
            "mapping_confidence": self.mapping_confidence.value,
            "unresolved_reason": self.unresolved_reason,
            "mapping_timestamp": self.mapping_timestamp,
        }


@dataclass
class Section102Analysis:
    """§102 anticipation analysis for one reference against one candidate.

    Per CEO directive (fifteenth round):
      §102 = whether ONE reference contains ALL required limitations
      in a SINGLE claim.

      Do NOT combine Claim 1 + Claim 2 + Claim 10 into an invented anticipation.
      Dependent claims can matter, but the claim dependency structure must be
      respected exactly.

      A dependent claim incorporates its parent by reference.
      So Claim 2 (dependent on Claim 1) includes all limitations of Claim 1
      PLUS its own additional limitations.

      But Claim 1 and Claim 10 (both dependent on Claim 1 but independent of
      each other) CANNOT be combined unless one depends on the other.
    """
    candidate_id: str
    reference_patent: str
    # Per-claim analysis: for each claim, did it contain ALL limitations?
    per_claim_results: dict[int, dict] = field(default_factory=dict)
    # claim_number → {"all_present": bool, "missing": [limitation_ids], "mappings": [ClaimLimitationMapping]}
    # The single best claim (if any) that contains all limitations
    anticipating_claim: Optional[int] = None
    # §102 verdict
    section_102_verdict: str = "NOT_ANALYZED"  # ANTICIPATED / NOT_ANTICIPATED / INCONCLUSIVE
    verdict_reasoning: str = ""
    analysis_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "candidate_id": self.candidate_id,
            "reference_patent": self.reference_patent,
            "per_claim_results": {
                str(k): v for k, v in self.per_claim_results.items()
            },
            "anticipating_claim": self.anticipating_claim,
            "section_102_verdict": self.section_102_verdict,
            "verdict_reasoning": self.verdict_reasoning,
            "analysis_timestamp": self.analysis_timestamp,
        }


class LimitationMapper:
    """Maps invention limitations to patent claims with exact evidence.

    Per CEO directive (fifteenth round):
      'The machine is not allowed to jump from "this looks similar" to
       "this is anticipated." The entire causal and legal bridge must be explicit.'

    This mapper:
      1. Takes a set of invention limitations
      2. Takes a set of parsed claims (ClaimEvidence objects)
      3. For each limitation × claim pair, determines DIRECT/PARTIAL/ABSENT/UNKNOWN
      4. For each claim, checks if ALL required limitations are present
      5. Respects claim dependency: dependent claims inherit parent limitations
      6. Does NOT combine independent claims
      7. Produces a §102 verdict

    The mapper uses EXACT TEXT MATCHING, not semantic similarity.
    Semantic similarity may find candidates but cannot declare anticipation.
    """

    def __init__(self):
        pass

    def map_limitation_to_claim(
        self,
        limitation: InventionLimitation,
        claim_text: str,
        claim_number: int,
        reference_patent: str,
        candidate_id: str,
    ) -> ClaimLimitationMapping:
        """Map one limitation to one claim.

        Uses exact text matching. If the limitation text appears verbatim
        (or nearly verbatim with minor formatting differences) in the claim,
        → DIRECT.

        If some key terms appear but the full limitation is not present,
        → PARTIAL.

        If the limitation text does not appear and no key terms match,
        → ABSENT.

        If the claim text is too ambiguous to determine,
        → UNKNOWN.
        """
        # Normalize texts for comparison
        lim_text = limitation.limitation_text.lower().strip()
        claim_lower = claim_text.lower().strip()

        # Check for exact or near-exact match
        if lim_text in claim_lower:
            # Exact match — the limitation text appears verbatim in the claim
            return ClaimLimitationMapping(
                candidate_id=candidate_id,
                reference_patent=reference_patent,
                claim_number=claim_number,
                limitation_id=limitation.limitation_id,
                disposition=LimitationDisposition.DIRECT,
                exact_claim_span=limitation.limitation_text,
                evidence_hash=hashlib.sha256(
                    f"{limitation.limitation_text}|{claim_text}".encode()).hexdigest(),
                mapping_method=MappingMethod.EXACT_TEXT_MATCH,
                mapping_confidence=MappingConfidence.HIGH,
            )

        # Check for key term matches (partial)
        # Split limitation into key terms (nouns, technical terms)
        lim_words = [w for w in lim_text.split() if len(w) > 3]
        matched_words = [w for w in lim_words if w in claim_lower]

        if len(matched_words) >= len(lim_words) * 0.7:
            # Most key terms present but not exact match
            matched_text = " ".join(matched_words[:5])
            return ClaimLimitationMapping(
                candidate_id=candidate_id,
                reference_patent=reference_patent,
                claim_number=claim_number,
                limitation_id=limitation.limitation_id,
                disposition=LimitationDisposition.PARTIAL,
                exact_claim_span=f"Partial match: {matched_text}...",
                evidence_hash=hashlib.sha256(
                    f"{limitation.limitation_text}|{matched_text}".encode()).hexdigest(),
                mapping_method=MappingMethod.EXACT_TEXT_MATCH,
                mapping_confidence=MappingConfidence.MEDIUM,
                unresolved_reason=f"Key terms matched ({len(matched_words)}/{len(lim_words)}) "
                                  f"but full limitation text not found verbatim.",
            )

        if len(matched_words) > 0:
            # Some terms match but not enough for partial
            return ClaimLimitationMapping(
                candidate_id=candidate_id,
                reference_patent=reference_patent,
                claim_number=claim_number,
                limitation_id=limitation.limitation_id,
                disposition=LimitationDisposition.UNKNOWN,
                exact_claim_span=f"Terms found: {' '.join(matched_words[:3])}",
                evidence_hash=hashlib.sha256(
                    f"{limitation.limitation_text}|partial".encode()).hexdigest(),
                mapping_method=MappingMethod.EXACT_TEXT_MATCH,
                mapping_confidence=MappingConfidence.LOW,
                unresolved_reason=f"Only {len(matched_words)}/{len(lim_words)} key terms matched. "
                                  f"Cannot determine if limitation is present.",
            )

        # No key terms match
        return ClaimLimitationMapping(
            candidate_id=candidate_id,
            reference_patent=reference_patent,
            claim_number=claim_number,
            limitation_id=limitation.limitation_id,
            disposition=LimitationDisposition.ABSENT,
            exact_claim_span="",
            evidence_hash=hashlib.sha256(
                f"{limitation.limitation_text}|absent".encode()).hexdigest(),
            mapping_method=MappingMethod.EXACT_TEXT_MATCH,
            mapping_confidence=MappingConfidence.HIGH,
            unresolved_reason="No key terms from the limitation found in the claim.",
        )

    def analyze_section_102(
        self,
        candidate_id: str,
        reference_patent: str,
        limitations: list[InventionLimitation],
        claims: list,  # list of ClaimEvidence
    ) -> Section102Analysis:
        """Perform §102 analysis.

        Per CEO directive (fifteenth round):
          §102 = whether ONE reference contains ALL required limitations
          in a SINGLE claim.

          A dependent claim inherits ALL limitations from its parent claims.
          So Claim 2 (depends on Claim 1) includes Claim 1's limitations
          PLUS Claim 2's own limitations.

          But two independent claims (e.g., Claim 1 and Claim 10, both
          independent or both depending on Claim 1 but not on each other)
          CANNOT be combined.

        This method:
          1. For each claim, maps all limitations
          2. For dependent claims, inherits parent limitations
          3. Checks if any SINGLE claim (with inheritance) contains ALL required limitations
          4. Produces §102 verdict
        """
        analysis = Section102Analysis(
            candidate_id=candidate_id,
            reference_patent=reference_patent,
        )

        required_limitations = [l for l in limitations if l.required]
        required_ids = {l.limitation_id for l in required_limitations}

        # Build claim lookup
        claim_lookup = {c.claim_number: c for c in claims}

        # For each claim, check if it (with inheritance) contains all limitations
        for claim in claims:
            # Get the effective claim text (this claim + all parent claims)
            effective_text = claim.exact_claim_text
            inherited_from = []

            # Walk the dependency chain
            deps_to_check = list(claim.depends_on_claim_numbers)
            visited = set()
            while deps_to_check:
                dep_num = deps_to_check.pop(0)
                if dep_num in visited or dep_num not in claim_lookup:
                    continue
                visited.add(dep_num)
                parent_claim = claim_lookup[dep_num]
                effective_text = parent_claim.exact_claim_text + " " + effective_text
                inherited_from.append(dep_num)
                deps_to_check.extend(parent_claim.depends_on_claim_numbers)

            # Map each limitation to this claim (with inheritance)
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
                )
                mappings.append(mapping)

                if mapping.disposition == LimitationDisposition.DIRECT:
                    present_ids.add(limitation.limitation_id)
                elif mapping.disposition == LimitationDisposition.PARTIAL:
                    # Partial does NOT count as present for §102
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
                "inherited_from": inherited_from,
                "mappings": [m.to_dict() for m in mappings],
            }

            if all_present and analysis.anticipating_claim is None:
                analysis.anticipating_claim = claim.claim_number

        # Determine §102 verdict
        if analysis.anticipating_claim is not None:
            analysis.section_102_verdict = "ANTICIPATED"
            claim_result = analysis.per_claim_results[analysis.anticipating_claim]
            inherited = claim_result.get("inherited_from", [])
            analysis.verdict_reasoning = (
                f"Claim {analysis.anticipating_claim} "
                f"{'(with inheritance from claims ' + str(inherited) + ') ' if inherited else ''}"
                f"contains ALL {len(required_ids)} required limitations: "
                f"{sorted(required_ids)}. "
                f"§102 anticipation established: ONE single claim "
                f"(with dependency inheritance) contains every limitation."
            )
        else:
            # Check if any claims have UNKNOWN limitations
            any_unknown = any(
                len(r.get("unknown", [])) > 0
                for r in analysis.per_claim_results.values()
            )
            if any_unknown:
                analysis.section_102_verdict = "INCONCLUSIVE"
                analysis.verdict_reasoning = (
                    "No single claim contains all required limitations. "
                    "However, some limitations are UNKNOWN (cannot determine "
                    "from claim text alone). §102 cannot be concluded."
                )
            else:
                analysis.section_102_verdict = "NOT_ANTICIPATED"
                analysis.verdict_reasoning = (
                    "No single claim (with dependency inheritance) contains "
                    "all required limitations. §102 anticipation NOT established."
                )

        return analysis


def get_c04_limitations() -> list[InventionLimitation]:
    """Get the C04 invention limitation set.

    C04 = PHH blood-tolerant drainage: a CSF shunt with filter + bypass.

    The limitations are derived from the C04 candidate definition, NOT from
    any prior art. These represent what the C04 invention requires.
    """
    return [
        InventionLimitation(
            limitation_id="A1",
            description="Shunt body with inlet and outlet",
            limitation_text="a body having an inlet and an outlet",
            required=True,
            source="C04 candidate definition",
        ),
        InventionLimitation(
            limitation_id="A2",
            description="First fluid-flow passageway",
            limitation_text="a first fluid-flow passageway",
            required=True,
            source="C04 candidate definition",
        ),
        InventionLimitation(
            limitation_id="A3",
            description="Filter in the first passageway",
            limitation_text="a filter positioned within the first fluid-flow passageway",
            required=True,
            source="C04 candidate definition",
        ),
        InventionLimitation(
            limitation_id="A4",
            description="Second passageway (bypass) around the filter",
            limitation_text="a second fluid-flow passageway extending between the inlet and outlet and providing a passageway through the body around the filter",
            required=True,
            source="C04 candidate definition",
        ),
        InventionLimitation(
            limitation_id="A5",
            description="Pressure-regulated valve in the first passageway",
            limitation_text="a pressure regulated valve",
            required=True,
            source="C04 candidate definition",
        ),
        InventionLimitation(
            limitation_id="A6",
            description="Selective blocking/opening of the bypass",
            limitation_text="selectively blocking or opening",
            required=True,
            source="C04 candidate definition",
        ),
    ]
