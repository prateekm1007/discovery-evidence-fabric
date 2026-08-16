"""
NOVELTY V3.4 — Passage-Grounded 102 with Inherency + Arrangement Firewalls
=============================================================================

Per CEO V3.4 Sections 2-5:

PASSAGE-GROUNDED 102:
  Every claim limitation requires:
    - limitation_id
    - reference_id
    - disclosure_type (EXPRESS / NECESSARILY_INHERENT / NOT_DISCLOSED / UNCERTAIN)
    - exact_passage (verbatim from reference)
    - claim_number / paragraph
    - mapping_rationale
    - mapping_confidence

  Forbidden disclosure types: POSSIBLE / PLAUSIBLE / TOPICAL / SEMANTICALLY_SIMILAR

INHERENCY FIREWALL:
  INHERENCY requires NECESSARY — not LIKELY / PROBABLE / POSSIBLE.
  Machine assertion: inherency_necessity_proof.
  If missing → NOT_DISCLOSED / UNCERTAIN.

ARRANGEMENT FIREWALL:
  After element mapping, verify the reference discloses the REQUIRED RELATIONSHIPS.
  A disclosed + B disclosed != A+B arranged as claimed unless arrangement is supported.

NoveltyEvidenceV34 DECISION OBJECT:
  single_reference
  all_limitations_mapped
  all_relationships_mapped
  passage_evidence
  inherency_necessity
  arrangement_supported
  uncertainties
  final_result

102_KILL legal only if:
  all_limitations_mapped = TRUE
  AND all_relationships_mapped = TRUE
  AND all_mapping_types in {EXPRESS, NECESSARILY_INHERENT}
  AND uncertainty_count = 0
"""
from __future__ import annotations
import os, sys, json, re, hashlib
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256


# ----------------------- DISCLOSURE TYPES -----------------------
# Allowed disclosure types (per CEO V3.4 Section 2)
DISCLOSURE_EXPRESS = "EXPRESS"
DISCLOSURE_NECESSARILY_INHERENT = "NECESSARILY_INHERENT"
DISCLOSURE_NOT_DISCLOSED = "NOT_DISCLOSED"
DISCLOSURE_UNCERTAIN = "UNCERTAIN"

ALLOWED_DISCLOSURE_TYPES = {
    DISCLOSURE_EXPRESS,
    DISCLOSURE_NECESSARILY_INHERENT,
    DISCLOSURE_NOT_DISCLOSED,
    DISCLOSURE_UNCERTAIN,
}

# Forbidden disclosure types (per CEO V3.4 Section 2)
FORBIDDEN_DISCLOSURE_TYPES = {
    "POSSIBLE",
    "PLAUSIBLE",
    "TOPICAL",
    "SEMANTICALLY_SIMILAR",
    "IMPLICIT",  # too vague — must be NECESSARILY_INHERENT or UNCERTAIN
}

# Valid mapping types for 102_KILL (per CEO V3.4 Section 5)
VALID_KILL_MAPPING_TYPES = {DISCLOSURE_EXPRESS, DISCLOSURE_NECESSARILY_INHERENT}


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class LimitationMapping:
    """One claim limitation mapped to a reference passage.

    Per CEO V3.4 Section 2: passage-grounded mapping.
    """
    limitation_id: str  # L1, L2, ...
    limitation_text: str = ""
    reference_id: str = ""
    disclosure_type: str = DISCLOSURE_NOT_DISCLOSED  # one of ALLOWED_DISCLOSURE_TYPES
    exact_passage: str = ""  # verbatim from reference claim text
    claim_number: str = ""  # e.g., "claim_1" or "paragraph [0032]"
    mapping_rationale: str = ""  # why this passage maps to this limitation
    mapping_confidence: float = 0.0  # 0.0 to 1.0
    # Inherency proof (required if disclosure_type == NECESSARILY_INHERENT)
    inherency_necessity_proof: str = ""  # must explain why it's NECESSARY, not just possible


@dataclass
class RelationshipMapping:
    """One relationship (A→B, A+B+C arrangement) mapped to a reference.

    Per CEO V3.4 Section 4: Arrangement Firewall.
    """
    relationship: str  # e.g., "A→B", "A+B+C arrangement"
    reference_id: str = ""
    arrangement_disclosed: bool = False  # TRUE only if arrangement explicitly supported
    exact_passage: str = ""  # passage showing the arrangement
    mapping_rationale: str = ""


@dataclass
class NoveltyEvidenceV34:
    """102 decision object per CEO V3.4 Section 5.

    102_KILL is legal only if:
      - all_limitations_mapped = TRUE
      - AND all_relationships_mapped = TRUE
      - AND all_mapping_types in {EXPRESS, NECESSARILY_INHERENT}
      - AND uncertainty_count = 0
    """
    single_reference: str = ""  # the one reference that allegedly anticipates
    all_limitations_mapped: bool = False
    all_relationships_mapped: bool = False
    limitation_mappings: List[LimitationMapping] = field(default_factory=list)
    relationship_mappings: List[RelationshipMapping] = field(default_factory=list)
    inherency_necessity: str = ""  # proof that any inherency is NECESSARY
    arrangement_supported: bool = False
    uncertainties: List[str] = field(default_factory=list)
    uncertainty_count: int = 0
    final_result: str = "NO_KILL"  # NO_KILL or 102_KILL
    kill_legal: bool = False  # True only if all conditions met
    rationale: str = ""
    # Audit
    adversary_model: str = ""
    adversary_prompt_hash: str = ""
    constructed_at_utc: str = ""


# ----------------------- NOVELTY ADVERSARY V3.4 -----------------------
NOVELTY_ADVERSARY_V34_PROMPT_HASH = _sha256(
    "NOVELTY_ADVERSARY_V3_4: Passage-grounded 102. "
    "Every limitation requires exact_passage + claim_number + mapping_rationale. "
    "Disclosure types: EXPRESS / NECESSARILY_INHERENT / NOT_DISCLOSED / UNCERTAIN. "
    "Forbidden: POSSIBLE / PLAUSIBLE / TOPICAL / SEMANTICALLY_SIMILAR. "
    "Inherency requires NECESSARY (not LIKELY/PROBABLE/POSSIBLE). "
    "Arrangement firewall: A+B disclosed != A+B arranged as claimed."
)


def construct_novelty_evidence_v34(
    case: Dict[str, Any],
    canonical_claim: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[NoveltyEvidenceV34, int]:
    """Construct passage-grounded 102 evidence object.

    Per CEO V3.4: every limitation must have exact_passage citation.
    No POSSIBLE/PLAUSIBLE/TOPICAL/SEMANTICALLY_SIMILAR allowed.
    """
    nov = NoveltyEvidenceV34(
        adversary_model="meta/llama-3.1-8b-instruct",
        adversary_prompt_hash=NOVELTY_ADVERSARY_V34_PROMPT_HASH,
        constructed_at_utc=_now_utc(),
    )

    limitations = canonical_claim.get("limitations", [])
    if not limitations:
        nov.uncertainties.append("No limitations parsed from canonical claim")
        nov.uncertainty_count = 1
        return nov, 0

    # Find patents with actual claims retrieved (GOLD evidence)
    patents_with_claims = [e for e in evidence if e.get("claims_retrieved")]
    if not patents_with_claims:
        nov.uncertainties.append("No patents with retrieved claims (GOLD evidence)")
        nov.uncertainty_count = 1
        return nov, 0

    # Build the LLM prompt — passage-grounded mapping
    sys_prompt = (
        "You are a NOVELTY_ADVERSARY V3.4 performing passage-grounded 102 analysis. "
        "For EVERY claim limitation, you must cite an EXACT PASSAGE from the reference patent's claims. "
        "\n\n"
        "Disclosure types (ONLY these are allowed):\n"
        "  EXPRESS — the limitation is explicitly stated in the reference claim text\n"
        "  NECESSARILY_INHERENT — the limitation is necessarily present (not just possibly)\n"
        "  NOT_DISCLOSED — the limitation is not in the reference\n"
        "  UNCERTAIN — cannot determine from the available text\n"
        "\n"
        "FORBIDDEN disclosure types (do NOT use these):\n"
        "  POSSIBLE, PLAUSIBLE, TOPICAL, SEMANTICALLY_SIMILAR, IMPLICIT\n"
        "\n"
        "INHERENCY FIREWALL: If you claim NECESSARILY_INHERENT, you MUST provide "
        "inherency_necessity_proof explaining why it is NECESSARY (not just likely or possible). "
        "If you cannot prove necessity, use NOT_DISCLOSED or UNCERTAIN.\n"
        "\n"
        "ARRANGEMENT FIREWALL: A disclosed somewhere + B disclosed somewhere ≠ A+B arranged as claimed. "
        "The arrangement must be explicitly supported in the reference.\n"
        "\n"
        "Return strict JSON."
    )

    # Build user prompt with claim text from each reference
    user_prompt = (
        f"Claim under test: {canonical_claim.get('patent_number', '')} — {case.get('title', '')}\n"
        f"Limitations to map:\n"
    )
    for i, lim in enumerate(limitations[:8]):
        user_prompt += f"  {lim}\n"

    user_prompt += "\nReference patents with actual claim text:\n"
    for e in patents_with_claims[:5]:
        user_prompt += (
            f"\n--- Reference: {e.get('patent_id', '')} ---\n"
            f"Claim text excerpt:\n{e.get('claim_text_excerpt', '')[:2000]}\n"
        )

    user_prompt += (
        "\nFor EACH limitation, return a JSON object with:\n"
        "  limitation_id, reference_id, disclosure_type, exact_passage, "
        "claim_number, mapping_rationale, mapping_confidence, inherency_necessity_proof\n\n"
        "Also return relationship_mappings for each relationship (A→B, A+B+C arrangement) "
        "with arrangement_disclosed (TRUE only if explicitly supported).\n\n"
        "Return JSON: {\n"
        '  "limitation_mappings": [{...}],\n'
        '  "relationship_mappings": [{...}],\n'
        '  "single_reference": "the one reference that allegedly anticipates (or empty)",\n'
        '  "all_limitations_mapped": true|false,\n'
        '  "all_relationships_mapped": true|false,\n'
        '  "arrangement_supported": true|false,\n'
        '  "uncertainties": ["..."],\n'
        '  "final_result": "NO_KILL"|"102_KILL",\n'
        '  "rationale": "..."\n'
        "}"
    )

    content, _ = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=3000)
    llm_calls = 1

    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)

            # Parse limitation mappings
            for lm in parsed.get("limitation_mappings", []):
                # Validate disclosure_type
                dt = lm.get("disclosure_type", DISCLOSURE_NOT_DISCLOSED)
                if dt in FORBIDDEN_DISCLOSURE_TYPES:
                    # Convert forbidden types to UNCERTAIN
                    dt = DISCLOSURE_UNCERTAIN
                    lm["mapping_rationale"] = (
                        f"(V3.4 firewall: original disclosure_type was forbidden, "
                        f"converted to UNCERTAIN) " + lm.get("mapping_rationale", "")
                    )
                elif dt not in ALLOWED_DISCLOSURE_TYPES:
                    dt = DISCLOSURE_UNCERTAIN

                # If NECESSARILY_INHERENT, require inherency_necessity_proof
                inh_proof = lm.get("inherency_necessity_proof", "")
                if dt == DISCLOSURE_NECESSARILY_INHERENT and not inh_proof:
                    # Inherency firewall — downgrade to UNCERTAIN
                    dt = DISCLOSURE_UNCERTAIN
                    lm["mapping_rationale"] = (
                        "(V3.4 inherency firewall: NECESSARILY_INHERENT without "
                        "necessity proof downgraded to UNCERTAIN) " + lm.get("mapping_rationale", "")
                    )

                nov.limitation_mappings.append(LimitationMapping(
                    limitation_id=lm.get("limitation_id", ""),
                    limitation_text=lm.get("limitation_text", ""),
                    reference_id=lm.get("reference_id", ""),
                    disclosure_type=dt,
                    exact_passage=lm.get("exact_passage", ""),
                    claim_number=lm.get("claim_number", ""),
                    mapping_rationale=lm.get("mapping_rationale", ""),
                    mapping_confidence=float(lm.get("mapping_confidence", 0.0)),
                    inherency_necessity_proof=inh_proof,
                ))

            # Parse relationship mappings
            for rm in parsed.get("relationship_mappings", []):
                nov.relationship_mappings.append(RelationshipMapping(
                    relationship=rm.get("relationship", ""),
                    reference_id=rm.get("reference_id", ""),
                    arrangement_disclosed=bool(rm.get("arrangement_disclosed", False)),
                    exact_passage=rm.get("exact_passage", ""),
                    mapping_rationale=rm.get("mapping_rationale", ""),
                ))

            nov.single_reference = parsed.get("single_reference", "")
            nov.all_limitations_mapped = bool(parsed.get("all_limitations_mapped", False))
            nov.all_relationships_mapped = bool(parsed.get("all_relationships_mapped", False))
            nov.arrangement_supported = bool(parsed.get("arrangement_supported", False))
            nov.uncertainties = parsed.get("uncertainties", [])
            nov.uncertainty_count = len(nov.uncertainties)
            nov.final_result = parsed.get("final_result", "NO_KILL")
            nov.rationale = parsed.get("rationale", "")
        except (json.JSONDecodeError, AttributeError, ValueError):
            nov.uncertainties.append("LLM JSON parse error")
            nov.uncertainty_count = 1

    # V3.4 FIREWALL: Apply strict 102_KILL legality check
    # 102_KILL legal only if:
    #   all_limitations_mapped = TRUE
    #   AND all_relationships_mapped = TRUE
    #   AND all_mapping_types in {EXPRESS, NECESSARILY_INHERENT}
    #   AND uncertainty_count = 0
    all_mapped = nov.all_limitations_mapped and nov.all_relationships_mapped
    all_types_valid = all(
        lm.disclosure_type in VALID_KILL_MAPPING_TYPES
        for lm in nov.limitation_mappings
    ) if nov.limitation_mappings else False
    no_uncertainties = nov.uncertainty_count == 0
    arrangement_ok = nov.arrangement_supported

    # Also verify every limitation has a non-empty exact_passage
    all_have_passages = all(
        bool(lm.exact_passage and len(lm.exact_passage) > 10)
        for lm in nov.limitation_mappings
    ) if nov.limitation_mappings else False

    nov.kill_legal = (
        all_mapped and
        all_types_valid and
        no_uncertainties and
        arrangement_ok and
        all_have_passages
    )

    # Override final_result based on firewall
    if nov.final_result == "102_KILL" and not nov.kill_legal:
        nov.final_result = "NO_KILL"
        nov.rationale += (
            "\n\nV3.4 FIREWALL: 102_KILL overridden because kill_legal=FALSE. "
            f"all_limitations_mapped={nov.all_limitations_mapped}, "
            f"all_relationships_mapped={nov.all_relationships_mapped}, "
            f"all_types_valid={all_types_valid}, "
            f"uncertainty_count={nov.uncertainty_count}, "
            f"arrangement_supported={arrangement_ok}, "
            f"all_have_passages={all_have_passages}. "
            "102_KILL requires ALL conditions TRUE."
        )

    return nov, llm_calls


def is_102_kill_legal(nov: NoveltyEvidenceV34) -> bool:
    """Check if 102_KILL is legal per V3.4 firewalls."""
    return nov.kill_legal and nov.final_result == "102_KILL"
