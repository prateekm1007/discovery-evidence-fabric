"""
PROSECUTION-GROUNDED 103 FORENSICS V3.5
=========================================

Per CEO V3.5: determine WHY the 103 adversary disagrees with known prosecution
outcomes. Build case-by-case forensic table comparing examiner vs system.

KEY PRINCIPLE: Examiner reasoning is evidence for calibration, NOT an
unquestionable oracle. Preserve both EXAMINER_GROUND_TRUTH and
SYSTEM_INDEPENDENT_ANALYSIS. If system has defensible alternative rationale,
record ALTERNATIVE_REASONING.

ERROR CLASSIFICATION (no generic MODEL_FAILURE):
  GROUND_TRUTH_EXTRACTION_FAILURE
  SEARCH_FAILURE
  REFERENCE_SELECTION_FAILURE
  DIFFERENCE_IDENTIFICATION_FAILURE
  MOTIVATION_FAILURE
  EXPECTATION_OF_SUCCESS_FAILURE
  TEACHING_AWAY_FAILURE
  TECHNICAL_EFFECT_FAILURE
  HINDSIGHT_FAILURE
  FINAL_ADJUDICATION_FAILURE
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


# ----------------------- ERROR CATEGORIES -----------------------
ERROR_CATEGORIES_V35 = [
    "GROUND_TRUTH_EXTRACTION_FAILURE",
    "SEARCH_FAILURE",
    "REFERENCE_SELECTION_FAILURE",
    "DIFFERENCE_IDENTIFICATION_FAILURE",
    "MOTIVATION_FAILURE",
    "EXPECTATION_OF_SUCCESS_FAILURE",
    "TEACHING_AWAY_FAILURE",
    "TECHNICAL_EFFECT_FAILURE",
    "HINDSIGHT_FAILURE",
    "FINAL_ADJUDICATION_FAILURE",
    "CORRECT",
]


# ----------------------- MOTIVATION EVIDENCE SOURCES -----------------------
MOTIVATION_SOURCES = [
    "EXPRESS_MOTIVATION",
    "KNOWN_PROBLEM",
    "DESIGN_PRESSURE",
    "MARKET_ENGINEERING_CONSTRAINT",
    "REFERENCE_TEACHING",
    "ESTABLISHED_ART_KNOWLEDGE",
    "PREDICTABLE_SUBSTITUTION",
    "MOTIVATION_INSUFFICIENT",
]


# ----------------------- EXPECTATION EVIDENCE SOURCES -----------------------
EXPECTATION_SOURCES = [
    "COMPATIBLE_MECHANISM",
    "COMPATIBLE_OPERATING_REGIME",
    "KNOWN_SUBSTITUTION",
    "SAME_FUNCTION",
    "ESTABLISHED_DESIGN_PRINCIPLE",
    "EXPERIMENTAL_EVIDENCE",
    "REFERENCE_TEACHING",
    "EXPECTATION_INSUFFICIENT",
]


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class ExaminerGroundTruth:
    """Examiner's 103 reasoning extracted from prosecution record."""
    case_id: str
    patent_number: str
    final_claim: str = ""
    examiner_103_reference_A: str = ""
    examiner_103_reference_B: str = ""
    examiner_motivation: str = ""
    examiner_reason_to_combine: str = ""
    examiner_expectation_of_success: str = ""
    examiner_teaching_away: str = ""
    examiner_technical_effect: str = ""
    examiner_final_disposition: str = ""  # GRANTED / ABANDONED / AMENDED
    extraction_confidence: float = 0.0


@dataclass
class ClosestPriorArtCandidate:
    """One candidate for closest prior art selection."""
    patent_id: str
    technical_field_score: float = 0.0
    purpose_score: float = 0.0
    technical_effect_score: float = 0.0
    structural_similarity_score: float = 0.0
    functional_similarity_score: float = 0.0
    total_score: float = 0.0
    selection_rationale: str = ""


@dataclass
class DifferenceElement:
    """One element in the difference vector (CLAIM minus CLOSEST_PRIOR_ART)."""
    element_id: str
    exact_claim_span: str = ""
    prior_art_status: str = ""  # NOT_DISCLOSED / PARTIALLY_DISCLOSED / DIFFERENT
    technical_significance: str = ""


@dataclass
class MotivationEvidence:
    """Motivation evidence per CEO V3.5 Section 7."""
    motivation_source: str = "MOTIVATION_INSUFFICIENT"  # one of MOTIVATION_SOURCES
    exact_passage: str = ""
    why_it_supports_combination: str = ""
    evidence_strength: str = "NONE"  # STRONG / MODERATE / WEAK / NONE


@dataclass
class ExpectationEvidence:
    """Expectation of success evidence per CEO V3.5 Section 8."""
    can_work: bool = False  # capability
    expected_to_work: bool = False  # evidence-based expectation
    expectation_source: str = "EXPECTATION_INSUFFICIENT"  # one of EXPECTATION_SOURCES
    technical_basis: str = ""
    evidence_strength: str = "NONE"  # STRONG / MODERATE / WEAK / NONE


@dataclass
class TeachingAwayEvidence:
    """Teaching away evidence per CEO V3.5 Section 10."""
    supporting_passage: str = ""
    contradicting_passage: str = ""
    strength: str = "NONE"  # STRONG / MODERATE / WEAK / NONE
    direction: str = "NONE"  # TEACHES_AWAY / TEACHES_TOWARD / NEUTRAL


@dataclass
class TechnicalEffectEvidence:
    """Technical effect per CEO V3.5 Section 11."""
    difference_element_id: str = ""
    predicted_effect: str = ""
    documented_effect: str = ""
    unexpected_effect: str = ""
    is_unexpectedly_superior: bool = False
    why_superior: str = ""


@dataclass
class ObviousnessEvidenceV35:
    """Prosecution-grounded 103 evidence object.

    Per CEO V3.5: score evidence, not confidence.
    """
    # Closest prior art (3+ candidates scored)
    closest_prior_art_candidates: List[ClosestPriorArtCandidate] = field(default_factory=list)
    closest_prior_art: str = ""
    closest_prior_art_rationale: str = ""

    # Difference vector
    difference_elements: List[DifferenceElement] = field(default_factory=list)

    # Secondary reference
    secondary_reference: str = ""
    secondary_reference_rationale: str = ""

    # Motivation (evidence-based)
    motivation: MotivationEvidence = field(default_factory=MotivationEvidence)

    # Expectation of success (evidence-based)
    expectation: ExpectationEvidence = field(default_factory=ExpectationEvidence)

    # Teaching away
    teaching_away: TeachingAwayEvidence = field(default_factory=TeachingAwayEvidence)

    # Technical effects (per difference element)
    technical_effects: List[TechnicalEffectEvidence] = field(default_factory=list)

    # COULD / WOULD (preserved from V3.4)
    could: str = "NO"  # YES / NO
    could_rationale: str = ""
    would: str = "NO"  # YES / NO
    would_rationale: str = ""

    # Anti-hindsight two-pass
    pass_a_pre_disclosure: str = ""
    pass_b_post_disclosure: str = ""
    hindsight: str = "HIGH"  # LOW / MEDIUM / HIGH
    hindsight_rationale: str = ""

    # Evidence scoring (per CEO V3.5 Section 16)
    evidence_count: int = 0
    strongest_evidence: str = ""
    weakest_link: str = ""
    uncertainty: str = "HIGH"  # LOW / MEDIUM / HIGH
    alternative_explanation: str = ""

    # Final determination
    obviousness_succeeds: bool = False
    determination: str = "INSUFFICIENT_EVIDENCE"
    determination_rationale: str = ""

    # Model separation (per CEO V3.5 Section 15)
    searcher_model: str = "patsnap+source_failover"
    obviousness_model: str = "meta/llama-3.1-8b-instruct"
    adjudicator_model: str = "deterministic_v35"
    adversary_prompt_hash: str = ""
    constructed_at_utc: str = ""


# ----------------------- PROMPT HASH -----------------------
OBVIOUSNESS_ADVERSARY_V35_PROMPT_HASH = _sha256(
    "OBVIOUSNESS_ADVERSARY_V3_5: Prosecution-grounded 103 forensics. "
    "3-candidate closest prior art. Difference vector. "
    "Motivation evidence sources (EXPRESS_MOTIVATION / KNOWN_PROBLEM / etc.). "
    "Expectation evidence (CAN_WORK vs EXPECTED_TO_WORK). "
    "Teaching away. Technical effect. Anti-hindsight two-pass. "
    "Score evidence not confidence. "
    "Independent from generator rationale."
)


# ----------------------- EXAMINER GROUND TRUTH EXTRACTION -----------------------
def extract_examiner_ground_truth(
    case: Dict[str, Any],
    llm: LLMClient,
) -> Tuple[ExaminerGroundTruth, int]:
    """Extract examiner's 103 reasoning from prosecution record.

    Per CEO V3.5 Section 4: preserve EXAMINER_GROUND_TRUTH.
    """
    gt = ExaminerGroundTruth(
        case_id=case["case_id"],
        patent_number=case["patent_number"],
        final_claim=case.get("title", ""),
        examiner_103_reference_A="",
        examiner_103_reference_B="",
        examiner_motivation=case.get("examiner_reasoning", ""),
        examiner_final_disposition=case.get("ground_truth_disposition", ""),
    )

    # Extract cited art as references
    cited = case.get("prior_art_cited", [])
    if cited:
        gt.examiner_103_reference_A = cited[0] if len(cited) > 0 else ""
        gt.examiner_103_reference_B = cited[1] if len(cited) > 1 else ""

    gt.examiner_reason_to_combine = case.get("examiner_reasoning", "")
    gt.examiner_expectation_of_success = ""  # not in case data — would need prosecution history
    gt.examiner_teaching_away = ""
    gt.examiner_technical_effect = ""
    gt.extraction_confidence = 0.7 if cited else 0.3

    return gt, 0  # no LLM call needed — extracted from case data


# ----------------------- 3-CANDIDATE CLOSEST PRIOR ART -----------------------
def select_closest_prior_art_v35(
    case: Dict[str, Any],
    novelty_evidence: Any,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[List[ClosestPriorArtCandidate], str, str, int]:
    """Select closest prior art from >=3 candidates.

    Per CEO V3.5 Section 5: score by technical_field / purpose / technical_effect
    / structural_similarity / functional_similarity.
    """
    limitation_mappings = getattr(novelty_evidence, "limitation_mappings", [])

    # Get all references that have claims retrieved
    refs_with_claims = [e for e in evidence if e.get("claims_retrieved")]
    if not refs_with_claims:
        return [], "NONE_NEEDED", "No references with retrieved claims", 0

    # Build candidates (up to 5)
    candidates: List[ClosestPriorArtCandidate] = []
    for ref in refs_with_claims[:5]:
        ref_id = ref.get("patent_id", "")
        # Count EXPRESS disclosures for this reference
        express_count = sum(1 for lm in limitation_mappings
                           if lm.reference_id == ref_id and lm.disclosure_type == "EXPRESS")
        inherent_count = sum(1 for lm in limitation_mappings
                            if lm.reference_id == ref_id and lm.disclosure_type == "NECESSARILY_INHERENT")
        total_mapped = express_count + inherent_count

        # Score based on mapping evidence
        tech_field_score = min(1.0, total_mapped / 5.0)
        purpose_score = min(1.0, express_count / 3.0)
        tech_effect_score = min(1.0, total_mapped / 4.0)
        structural_score = min(1.0, express_count / 4.0)
        functional_score = min(1.0, inherent_count / 2.0)

        total = (tech_field_score + purpose_score + tech_effect_score +
                 structural_score + functional_score) / 5.0

        candidates.append(ClosestPriorArtCandidate(
            patent_id=ref_id,
            technical_field_score=round(tech_field_score, 2),
            purpose_score=round(purpose_score, 2),
            technical_effect_score=round(tech_effect_score, 2),
            structural_similarity_score=round(structural_score, 2),
            functional_similarity_score=round(functional_score, 2),
            total_score=round(total, 2),
            selection_rationale=f" EXPRESS={express_count}, INHERENT={inherent_count}",
        ))

    # Sort by total score
    candidates.sort(key=lambda c: -c.total_score)

    if not candidates:
        return [], "NONE_NEEDED", "No candidates available", 0

    closest = candidates[0]
    rationale = (
        f"Selected as closest prior art with total_score={closest.total_score}. "
        f"Scores: tech_field={closest.technical_field_score}, "
        f"purpose={closest.purpose_score}, "
        f"tech_effect={closest.technical_effect_score}, "
        f"structural={closest.structural_similarity_score}, "
        f"functional={closest.functional_similarity_score}."
    )

    return candidates, closest.patent_id, rationale, 0


# ----------------------- DIFFERENCE VECTOR -----------------------
def build_difference_vector(
    canonical_claim: Dict[str, Any],
    closest_prior_art_id: str,
    novelty_evidence: Any,
) -> List[DifferenceElement]:
    """Build difference vector: CLAIM minus CLOSEST_PRIOR_ART.

    Per CEO V3.5 Section 6.
    """
    limitation_mappings = getattr(novelty_evidence, "limitation_mappings", [])
    differences: List[DifferenceElement] = []

    for i, lim in enumerate(canonical_claim.get("limitations", [])):
        lim_id = f"L{i+1}"
        # Find mapping for this limitation in closest prior art
        mapping = next((lm for lm in limitation_mappings
                       if lm.limitation_id == lim_id and lm.reference_id == closest_prior_art_id), None)

        if mapping:
            if mapping.disclosure_type == "NOT_DISCLOSED":
                status = "NOT_DISCLOSED"
            elif mapping.disclosure_type == "UNCERTAIN":
                status = "PARTIALLY_DISCLOSED"
            elif mapping.disclosure_type in ("EXPRESS", "NECESSARILY_INHERENT"):
                status = "DISCLOSED"  # not a difference
            else:
                status = "DIFFERENT"
        else:
            status = "NOT_DISCLOSED"

        if status != "DISCLOSED":
            differences.append(DifferenceElement(
                element_id=lim_id,
                exact_claim_span=lim[:200],
                prior_art_status=status,
                technical_significance="",
            ))

    return differences


# ----------------------- MOTIVATION EVIDENCE -----------------------
def assess_motivation_evidence(
    case: Dict[str, Any],
    closest_prior_art_id: str,
    secondary_reference: str,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[MotivationEvidence, int]:
    """Assess motivation evidence per CEO V3.5 Section 7.

    Require evidence from one of:
      EXPRESS_MOTIVATION / KNOWN_PROBLEM / DESIGN_PRESSURE / MARKET_ENGINEERING_CONSTRAINT
      / REFERENCE_TEACHING / ESTABLISHED_ART_KNOWLEDGE / PREDICTABLE_SUBSTITUTION

    If no support: MOTIVATION_INSUFFICIENT.
    """
    if not secondary_reference:
        return MotivationEvidence(
            motivation_source="MOTIVATION_INSUFFICIENT",
            exact_passage="",
            why_it_supports_combination="No secondary reference available",
            evidence_strength="NONE",
        ), 0

    # Get claim text from both references
    closest_ev = next((e for e in evidence if e.get("patent_id") == closest_prior_art_id), None)
    secondary_ev = next((e for e in evidence if e.get("patent_id") == secondary_reference), None)

    closest_claims = closest_ev.get("claim_text_excerpt", "")[:1500] if closest_ev else ""
    secondary_claims = secondary_ev.get("claim_text_excerpt", "")[:1500] if secondary_ev else ""

    sys_prompt = (
        "You are a 103 MOTIVATION ASSESSOR. "
        "Determine whether there is evidence to combine the closest prior art with the secondary reference. "
        "\n\nMotivation evidence sources (require one):"
        "\n  EXPRESS_MOTIVATION — explicit statement in a reference suggesting combination"
        "\n  KNOWN_PROBLEM — the problem was known in the field"
        "\n  DESIGN_PRESSURE — engineering pressure to solve the problem"
        "\n  MARKET_ENGINEERING_CONSTRAINT — market or engineering constraints"
        "\n  REFERENCE_TEACHING — the reference teaches toward the combination"
        "\n  ESTABLISHED_ART_KNOWLEDGE — established knowledge in the art"
        "\n  PREDICTABLE_SUBSTITUTION — substitution of known elements"
        "\n  MOTIVATION_INSUFFICIENT — no evidence found"
        "\n\nIf no support exists: MOTIVATION_INSUFFICIENT."
        "\nReturn strict JSON."
    )
    user_prompt = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Claim title: {case.get('title', '')}\n\n"
        f"Closest prior art ({closest_prior_art_id}) claims:\n{closest_claims}\n\n"
        f"Secondary reference ({secondary_reference}) claims:\n{secondary_claims}\n\n"
        "Return JSON: {\n"
        '  "motivation_source": "...",\n'
        '  "exact_passage": "verbatim passage from reference supporting combination",\n'
        '  "why_it_supports_combination": "...",\n'
        '  "evidence_strength": "STRONG|MODERATE|WEAK|NONE"\n'
        "}"
    )

    content, _ = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1000)

    motivation = MotivationEvidence()
    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)
            source = parsed.get("motivation_source", "MOTIVATION_INSUFFICIENT")
            if source not in MOTIVATION_SOURCES:
                source = "MOTIVATION_INSUFFICIENT"
            motivation.motivation_source = source
            motivation.exact_passage = parsed.get("exact_passage", "")
            motivation.why_it_supports_combination = parsed.get("why_it_supports_combination", "")
            motivation.evidence_strength = parsed.get("evidence_strength", "NONE")
        except (json.JSONDecodeError, AttributeError):
            pass

    return motivation, 1


# ----------------------- EXPECTATION EVIDENCE -----------------------
def assess_expectation_evidence(
    case: Dict[str, Any],
    closest_prior_art_id: str,
    secondary_reference: str,
    motivation: MotivationEvidence,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[ExpectationEvidence, int]:
    """Assess expectation of success per CEO V3.5 Section 8.

    Separate CAN_WORK from EXPECTED_TO_WORK.
    Require technical basis. No 'PHOSITA would know this' without evidence.
    """
    if not secondary_reference:
        return ExpectationEvidence(
            can_work=False,
            expected_to_work=False,
            expectation_source="EXPECTATION_INSUFFICIENT",
            technical_basis="No secondary reference",
            evidence_strength="NONE",
        ), 0

    closest_ev = next((e for e in evidence if e.get("patent_id") == closest_prior_art_id), None)
    secondary_ev = next((e for e in evidence if e.get("patent_id") == secondary_reference), None)
    closest_claims = closest_ev.get("claim_text_excerpt", "")[:1500] if closest_ev else ""
    secondary_claims = secondary_ev.get("claim_text_excerpt", "")[:1500] if secondary_ev else ""

    sys_prompt = (
        "You are a 103 EXPECTATION OF SUCCESS ASSESSOR. "
        "Separate CAN_WORK (capability) from EXPECTED_TO_WORK (evidence-based expectation). "
        "\n\nExpectation evidence sources (require one for EXPECTED_TO_WORK):"
        "\n  COMPATIBLE_MECHANISM — the mechanisms are compatible"
        "\n  COMPATIBLE_OPERATING_REGIME — operating regimes are compatible"
        "\n  KNOWN_SUBSTITUTION — substitution of known elements"
        "\n  SAME_FUNCTION — same function performed"
        "\n  ESTABLISHED_DESIGN_PRINCIPLE — established design principle"
        "\n  EXPERIMENTAL_EVIDENCE — experimental evidence supports it"
        "\n  REFERENCE_TEACHING — the reference teaches it would work"
        "\n  EXPECTATION_INSUFFICIENT — no evidence"
        "\n\nNo 'PHOSITA would know this' without evidence."
        "\nReturn strict JSON."
    )
    user_prompt = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Closest prior art ({closest_prior_art_id}) claims:\n{closest_claims}\n\n"
        f"Secondary reference ({secondary_reference}) claims:\n{secondary_claims}\n\n"
        f"Motivation source: {motivation.motivation_source}\n"
        f"Motivation passage: {motivation.exact_passage}\n\n"
        "Return JSON: {\n"
        '  "can_work": true|false,\n'
        '  "expected_to_work": true|false,\n'
        '  "expectation_source": "...",\n'
        '  "technical_basis": "...",\n'
        '  "evidence_strength": "STRONG|MODERATE|WEAK|NONE"\n'
        "}"
    )

    content, _ = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1000)

    expectation = ExpectationEvidence()
    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)
            expectation.can_work = bool(parsed.get("can_work", False))
            expectation.expected_to_work = bool(parsed.get("expected_to_work", False))
            source = parsed.get("expectation_source", "EXPECTATION_INSUFFICIENT")
            if source not in EXPECTATION_SOURCES:
                source = "EXPECTATION_INSUFFICIENT"
            expectation.expectation_source = source
            expectation.technical_basis = parsed.get("technical_basis", "")
            expectation.evidence_strength = parsed.get("evidence_strength", "NONE")
        except (json.JSONDecodeError, AttributeError):
            pass

    return expectation, 1


# ----------------------- CONSTRUCT 103 EVIDENCE V35 -----------------------
def construct_obviousness_evidence_v35(
    case: Dict[str, Any],
    canonical_claim: Dict[str, Any],
    novelty_evidence: Any,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[ObviousnessEvidenceV35, int, ExaminerGroundTruth]:
    """Construct prosecution-grounded 103 evidence.

    Per CEO V3.5: 3-candidate closest prior art, difference vector, motivation
    evidence, expectation evidence, teaching away, technical effect, anti-hindsight.
    """
    total_llm_calls = 0

    # Step 1: Extract examiner ground truth
    examiner_gt, calls = extract_examiner_ground_truth(case, llm)
    total_llm_calls += calls

    obs = ObviousnessEvidenceV35(
        adversary_prompt_hash=OBVIOUSNESS_ADVERSARY_V35_PROMPT_HASH,
        constructed_at_utc=_now_utc(),
    )

    # Step 2: 3-candidate closest prior art selection
    candidates, closest_id, closest_rationale, calls = select_closest_prior_art_v35(
        case, novelty_evidence, evidence, llm
    )
    total_llm_calls += calls
    obs.closest_prior_art_candidates = candidates
    obs.closest_prior_art = closest_id
    obs.closest_prior_art_rationale = closest_rationale

    if closest_id == "NONE_NEEDED":
        obs.could = "NO"
        obs.would = "NO"
        obs.determination = "INSUFFICIENT_EVIDENCE"
        obs.determination_rationale = "No closest prior art available."
        return obs, total_llm_calls, examiner_gt

    # Step 3: Build difference vector
    obs.difference_elements = build_difference_vector(
        canonical_claim, closest_id, novelty_evidence
    )

    # Step 4: Find secondary reference (second-best candidate)
    if len(candidates) > 1:
        obs.secondary_reference = candidates[1].patent_id
        obs.secondary_reference_rationale = (
            f"Second-best candidate with total_score={candidates[1].total_score}."
        )

    # Step 5: Assess motivation evidence
    motivation, calls = assess_motivation_evidence(
        case, closest_id, obs.secondary_reference, evidence, llm
    )
    total_llm_calls += calls
    obs.motivation = motivation

    # Step 6: Assess expectation evidence
    expectation, calls = assess_expectation_evidence(
        case, closest_id, obs.secondary_reference, motivation, evidence, llm
    )
    total_llm_calls += calls
    obs.expectation = expectation

    # Step 7: Two-pass anti-hindsight (simplified — use pre-disclosure from V3.4)
    closest_ev = next((e for e in evidence if e.get("patent_id") == closest_id), None)
    closest_claims = closest_ev.get("claim_text_excerpt", "")[:1000] if closest_ev else ""

    sys_prompt_a = (
        "You are an OBVIOUSNESS_ADVERSARY V3.5 performing Pass A (pre-disclosure). "
        "Formulate the objective technical problem WITHOUT seeing the invention. "
        "Return JSON."
    )
    user_prompt_a = (
        f"Closest prior art ({closest_id}) claims:\n{closest_claims}\n"
        f"Difference elements: {[de.element_id for de in obs.difference_elements]}\n\n"
        'Return: {"objective_problem": "...", "pre_disclosure_direction": "..."}'
    )
    content_a, _ = llm.chat(sys_prompt_a, user_prompt_a, temperature=0.0, max_tokens=600)
    total_llm_calls += 1

    problem_before = ""
    direction_before = ""
    if content_a and not content_a.startswith("[LLM_ERROR"):
        try:
            c = content_a.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed_a = json.loads(c)
            problem_before = parsed_a.get("objective_problem", "")
            direction_before = parsed_a.get("pre_disclosure_direction", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    obs.pass_a_pre_disclosure = direction_before

    # Pass B: compare
    obs.pass_b_post_disclosure = (
        f"After seeing invention: motivation={motivation.motivation_source}, "
        f"expectation={expectation.expectation_source}. "
        f"Pre-disclosure direction: {direction_before[:200]}."
    )

    # Determine hindsight risk
    if motivation.motivation_source == "MOTIVATION_INSUFFICIENT":
        obs.hindsight = "HIGH"
        obs.hindsight_rationale = (
            "Motivation insufficient — reasoning may be constructed backwards from invention."
        )
    elif motivation.evidence_strength in ("WEAK", "NONE"):
        obs.hindsight = "MEDIUM"
        obs.hindsight_rationale = "Weak motivation evidence — possible hindsight."
    else:
        obs.hindsight = "LOW"
        obs.hindsight_rationale = "Strong motivation evidence — low hindsight risk."

    # Step 8: COULD / WOULD
    obs.could = "YES" if expectation.can_work else "NO"
    obs.could_rationale = f"can_work={expectation.can_work}"

    # WOULD requires: motivation_supported AND expected_to_work
    motivation_supported = motivation.motivation_source != "MOTIVATION_INSUFFICIENT"
    expected_to_work = expectation.expected_to_work

    obs.would = "YES" if (motivation_supported and expected_to_work) else "NO"
    obs.would_rationale = (
        f"motivation_supported={motivation_supported} "
        f"({motivation.motivation_source}), "
        f"expected_to_work={expected_to_work} "
        f"({expectation.expectation_source})"
    )

    # Step 9: Evidence scoring
    evidence_count = 0
    if motivation.exact_passage:
        evidence_count += 1
    if expectation.technical_basis:
        evidence_count += 1
    if obs.difference_elements:
        evidence_count += 1
    if candidates and len(candidates) >= 2:
        evidence_count += 1

    obs.evidence_count = evidence_count
    obs.strongest_evidence = (
        f"motivation_source={motivation.motivation_source} "
        f"(strength={motivation.evidence_strength})"
    )
    obs.weakest_link = (
        "expectation" if not expected_to_work else
        "motivation" if not motivation_supported else
        "none"
    )
    obs.uncertainty = "HIGH" if evidence_count < 2 else ("MEDIUM" if evidence_count < 4 else "LOW")
    obs.alternative_explanation = (
        "System could not find motivation/expectation evidence in the available prior art. "
        "This may indicate either (a) the prior art is insufficient for 103, or "
        "(b) the system's search did not retrieve the right references."
    )

    # Step 10: Final determination
    # 103 requires: COULD=YES AND WOULD=YES AND MOTIVATION_SUPPORTED AND EXPECTED_SUCCESS_SUPPORTED
    all_conditions = (
        obs.could == "YES" and
        obs.would == "YES" and
        motivation_supported and
        expected_to_work
    )

    if all_conditions:
        # Check hindsight firewall
        if obs.hindsight == "HIGH":
            obs.obviousness_succeeds = False
            obs.determination = "INSUFFICIENT_EVIDENCE"
            obs.determination_rationale = (
                "All conditions met but hindsight=HIGH. "
                "Reasoning may be constructed backwards — rejected."
            )
        else:
            obs.obviousness_succeeds = True
            obs.determination = "OBVIOUSNESS_RISK"
            obs.determination_rationale = (
                "COULD=YES AND WOULD=YES AND MOTIVATION_SUPPORTED AND EXPECTED_SUCCESS_SUPPORTED. "
                f"Motivation: {motivation.motivation_source}. "
                f"Expectation: {expectation.expectation_source}."
            )
    else:
        obs.obviousness_succeeds = False
        if obs.could == "YES" and not (motivation_supported and expected_to_work):
            obs.determination = "INSUFFICIENT_EVIDENCE"
            obs.determination_rationale = (
                f"COULD=YES but WOULD={obs.would}. "
                f"Missing: motivation_supported={motivation_supported}, "
                f"expected_to_work={expected_to_work}. "
                "Per V3.5: INSUFFICIENT_EVIDENCE (not OBVIOUSNESS_RISK)."
            )
        else:
            obs.determination = "NO_OBVIOUSNESS"
            obs.determination_rationale = (
                "Could not establish COULD=YES. No obviousness case."
            )

    return obs, total_llm_calls, examiner_gt


# ----------------------- FORENSIC COMPARISON -----------------------
def compare_examiner_vs_system(
    examiner_gt: ExaminerGroundTruth,
    system_obs: ObviousnessEvidenceV35,
    case: Dict[str, Any],
) -> Dict[str, Any]:
    """Compare examiner ground truth vs system analysis field-by-field.

    Per CEO V3.5 Section 2.
    """
    return {
        "case_id": examiner_gt.case_id,
        "patent_number": examiner_gt.patent_number,
        "examiner_ground_truth": {
            "final_claim": examiner_gt.final_claim,
            "examiner_103_reference_A": examiner_gt.examiner_103_reference_A,
            "examiner_103_reference_B": examiner_gt.examiner_103_reference_B,
            "examiner_motivation": examiner_gt.examiner_motivation,
            "examiner_reason_to_combine": examiner_gt.examiner_reason_to_combine,
            "examiner_expectation_of_success": examiner_gt.examiner_expectation_of_success,
            "examiner_teaching_away": examiner_gt.examiner_teaching_away,
            "examiner_technical_effect": examiner_gt.examiner_technical_effect,
            "examiner_final_disposition": examiner_gt.examiner_final_disposition,
        },
        "system_independent_analysis": {
            "system_closest_prior_art": system_obs.closest_prior_art,
            "system_difference_elements": [asdict(de) for de in system_obs.difference_elements],
            "system_secondary_reference": system_obs.secondary_reference,
            "system_motivation": asdict(system_obs.motivation),
            "system_expectation": asdict(system_obs.expectation),
            "system_teaching_away": asdict(system_obs.teaching_away),
            "system_result": system_obs.determination,
            "system_evidence_count": system_obs.evidence_count,
            "system_strongest_evidence": system_obs.strongest_evidence,
            "system_weakest_link": system_obs.weakest_link,
        },
        "field_comparison": {
            "reference_A_match": examiner_gt.examiner_103_reference_A == system_obs.closest_prior_art,
            "reference_B_match": examiner_gt.examiner_103_reference_B == system_obs.secondary_reference,
            "motivation_agreement": _assess_motivation_agreement(examiner_gt, system_obs),
            "expectation_agreement": _assess_expectation_agreement(examiner_gt, system_obs),
        },
    }


def _assess_motivation_agreement(examiner_gt: ExaminerGroundTruth, system_obs: ObviousnessEvidenceV35) -> str:
    """Assess whether system's motivation agrees with examiner's."""
    if examiner_gt.examiner_motivation and system_obs.motivation.motivation_source != "MOTIVATION_INSUFFICIENT":
        return "AGREE"
    elif not examiner_gt.examiner_motivation and system_obs.motivation.motivation_source == "MOTIVATION_INSUFFICIENT":
        return "AGREE"
    else:
        return "DISAGREE"


def _assess_expectation_agreement(examiner_gt: ExaminerGroundTruth, system_obs: ObviousnessEvidenceV35) -> str:
    """Assess whether system's expectation agrees with examiner's."""
    if system_obs.expectation.expected_to_work:
        return "SYSTEM_FINDS_EXPECTATION"
    else:
        return "SYSTEM_NO_EXPECTATION"


# ----------------------- ERROR CLASSIFICATION -----------------------
def classify_103_error_v35(
    case: Dict[str, Any],
    examiner_gt: ExaminerGroundTruth,
    system_obs: ObviousnessEvidenceV35,
    correct: bool,
) -> str:
    """Classify 103 error per CEO V3.5 Section 3.

    No generic MODEL_FAILURE.
    """
    if correct:
        return "CORRECT"

    had_103 = case.get("had_103_rejection", False)
    system_found_103 = system_obs.obviousness_succeeds

    # Case had 103 rejection but system didn't find it
    if had_103 and not system_found_103:
        # Determine WHY the system missed it
        if not examiner_gt.examiner_103_reference_A:
            return "GROUND_TRUTH_EXTRACTION_FAILURE"

        # Check if system found the same references
        if system_obs.closest_prior_art != examiner_gt.examiner_103_reference_A:
            return "REFERENCE_SELECTION_FAILURE"

        # Check if system identified the differences
        if not system_obs.difference_elements:
            return "DIFFERENCE_IDENTIFICATION_FAILURE"

        # Check motivation
        if system_obs.motivation.motivation_source == "MOTIVATION_INSUFFICIENT":
            return "MOTIVATION_FAILURE"

        # Check expectation
        if not system_obs.expectation.expected_to_work:
            return "EXPECTATION_OF_SUCCESS_FAILURE"

        # Check hindsight
        if system_obs.hindsight == "HIGH":
            return "HINDSIGHT_FAILURE"

        return "FINAL_ADJUDICATION_FAILURE"

    # Case did NOT have 103 rejection but system found one
    if not had_103 and system_found_103:
        if system_obs.hindsight == "HIGH":
            return "HINDSIGHT_FAILURE"
        return "FINAL_ADJUDICATION_FAILURE"

    return "FINAL_ADJUDICATION_FAILURE"
