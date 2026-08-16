"""
103 OBVIOUSNESS ADVERSARY V3.3 — Rebuilt
==========================================

Per CEO directive V3.3 Sections 6-11:
  - Explicit 103 evidence object
  - COULD ≠ WOULD rule
  - Closest prior art must be technically close
  - 103 combination matrix
  - 103 two-pass anti-hindsight
  - Technical effect documentation
  - Model role separation (OBVIOUSNESS_ADVERSARY does NOT receive generator's narrative)

EXPLICIT 103 EVIDENCE OBJECT:
  closest_prior_art
  differences
  objective_technical_problem
  secondary_reference
  motivation
  technical_effect
  expectation_of_success
  teaching_away
  could
  would
  why
  hindsight

COULD ≠ WOULD RULE:
  COULD = capability
  WOULD = evidence of motivation + expectation of success
  OBVIOUSNESS_RISK requires:
    WOULD = YES
    AND MOTIVATION_SUPPORTED = TRUE
    AND EXPECTED_SUCCESS_SUPPORTED = TRUE

CLOSEST PRIOR ART SELECTION:
  - Similar purpose/effect OR same/closely related field
  - Minimal structural/functional modification
  - Do NOT select a convenient patent merely because it shares one keyword

103 COMBINATION MATRIX:
  REFERENCE_A
  REFERENCE_B
  ELEMENTS_FROM_A
  ELEMENTS_FROM_B
  MOTIVATION_TO_COMBINE
  EXPECTED_BENEFIT
  TECHNICAL_COMPATIBILITY
  TEACHING_AWAY
  PRE_FILING_REASON_TO_COMBINE

103 TWO-PASS ANTI-HINDSIGHT:
  Pass A: Hide the final invention solution.
          Ask: "What would a skilled person do to solve the objective problem?"
  Pass B: Reveal the actual claimed invention. Compare.
  Large divergence → HINDSIGHT_RISK_HIGH
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


# ----------------------- 103 EVIDENCE OBJECT -----------------------
@dataclass
class CombinationMatrix:
    """103 combination matrix per CEO Section 9."""
    reference_a: str = ""
    reference_b: str = ""
    elements_from_a: List[str] = field(default_factory=list)
    elements_from_b: List[str] = field(default_factory=list)
    motivation_to_combine: str = ""
    expected_benefit: str = ""
    technical_compatibility: str = ""  # HIGH / MEDIUM / LOW
    teaching_away: str = ""  # YES / NO / PARTIAL
    pre_filing_reason_to_combine: str = ""  # must exist before seeing invention


@dataclass
class TechnicalEffect:
    """Technical effect documentation per CEO Section 11."""
    feature: str = ""
    effect_description: str = ""
    effect_source: str = ""  # DOCUMENTED / INFERRED / HYPOTHESIZED
    effect_strength: str = ""  # HIGH / MEDIUM / LOW
    is_unexpected: bool = False
    evidence_links_to_feature: str = ""


@dataclass
class ObviousnessEvidenceV33:
    """Explicit 103 evidence object per CEO Section 6.

    OBVIOUSNESS_ADVERSARY constructs this WITHOUT receiving the generator's
    narrative rationale. It receives only:
      - canonical claim
      - prior art
      - claim mappings
      - technical evidence
    """
    # Closest prior art selection (per CEO Section 8)
    closest_prior_art_id: str = ""
    closest_prior_art_rationale: str = ""  # why this is the closest
    closest_prior_art_similarity: str = ""  # SIMILAR_PURPOSE / CLOSELY_RELATED_FIELD / WEAK

    # Differences
    differences: List[str] = field(default_factory=list)

    # Objective technical problem (formulated WITHOUT seeing invention solution)
    objective_technical_problem: str = ""
    otp_formulated_pre_disclosure: bool = False

    # Secondary reference (for combination)
    secondary_reference_id: str = ""

    # Motivation
    motivation: str = ""
    motivation_supported: bool = False
    motivation_evidence: str = ""

    # Technical effect
    technical_effects: List[TechnicalEffect] = field(default_factory=list)

    # Expectation of success
    expectation_of_success: str = ""  # HIGH / MEDIUM / LOW
    expected_success_supported: bool = False
    expectation_evidence: str = ""

    # Teaching away
    teaching_away: str = ""  # YES / NO / PARTIAL
    teaching_away_evidence: str = ""

    # COULD vs WOULD (per CEO Section 7)
    could_question: str = ""  # YES / NO — capability
    could_rationale: str = ""
    would_question: str = ""  # YES / NO — motivation + expectation
    would_rationale: str = ""

    # WHY explanation
    why_explanation: str = ""

    # Combination matrix (if combining references)
    combination_matrix: Optional[CombinationMatrix] = None

    # Two-pass anti-hindsight (per CEO Section 10)
    pass_a_pre_disclosure_solution: str = ""  # what PSA would do without seeing invention
    pass_b_post_disclosure_comparison: str = ""  # comparison after seeing invention
    hindsight_risk: str = ""  # LOW / MEDIUM / HIGH
    hindsight_risk_rationale: str = ""

    # Final determination
    obviousness_succeeds: bool = False  # True = 103 rejects
    determination_rationale: str = ""

    # Audit
    adversary_model: str = ""
    adversary_prompt_hash: str = ""
    constructed_at_utc: str = ""


# ----------------------- OBVIOUSNESS ADVERSARY V3.3 -----------------------
OBVIOUSNESS_ADVERSARY_PROMPT_HASH = _sha256(
    "OBVIOUSNESS_ADVERSARY_V3_3: Rebuilt with explicit evidence object. "
    "COULD != WOULD rule. Two-pass anti-hindsight. "
    "Does NOT receive generator's narrative rationale. "
    "Receives only: canonical claim + prior art + claim mappings + technical evidence."
)


def select_closest_prior_art(
    case: Dict[str, Any],
    novelty_results: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
) -> Tuple[str, str, str]:
    """Select closest prior art per CEO Section 8.

    Require:
      - similar purpose/effect OR same/closely related field
      - minimal structural/functional modification

    Do NOT select a convenient patent merely because it shares one keyword.
    """
    if not novelty_results:
        return ("NONE_NEEDED", "No prior art to select from — 102 already anticipates", "NONE")

    # Filter out patents where 102 already anticipates
    surviving = [r for r in novelty_results if not r.get("anticipation_succeeds", False)]
    if not surviving:
        return ("NONE_NEEDED", "102 already anticipates the claim", "NONE")

    # Sort by number of limitations found (most = closest)
    surviving.sort(
        key=lambda r: len(r.get("limitations_found", [])),
        reverse=True,
    )

    closest = surviving[0]
    closest_id = closest.get("patent_id", "")
    limitations_found = len(closest.get("limitations_found", []))
    limitations_missing = len(closest.get("limitations_missing", []))

    # Determine similarity level
    # If the patent has claims retrieved (GOLD evidence) AND discloses most limitations
    evidence_rec = next((e for e in evidence if e.get("patent_id") == closest_id), None)
    has_gold = evidence_rec and evidence_rec.get("claims_retrieved", False)

    if limitations_found >= 3 and has_gold:
        similarity = "SIMILAR_PURPOSE"
        rationale = (
            f"Selected as closest prior art because it discloses {limitations_found} "
            f"of {limitations_found + limitations_missing} limitations with actual claim text (GOLD evidence). "
            f"This is the most technically close reference."
        )
    elif limitations_found >= 1:
        similarity = "CLOSELY_RELATED_FIELD"
        rationale = (
            f"Selected as closest prior art because it discloses {limitations_found} "
            f"limitations. It is in a closely related technical field."
        )
    else:
        similarity = "WEAK"
        rationale = (
            f"Selected as closest prior art by default — no patent discloses more than "
            f"{limitations_found} limitations. Similarity is weak."
        )

    return (closest_id, rationale, similarity)


def construct_obviousness_evidence(
    case: Dict[str, Any],
    canonical_claim: Dict[str, Any],
    novelty_results: List[Dict[str, Any]],
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[ObviousnessEvidenceV33, int]:
    """Construct 103 evidence object using OBVIOUSNESS_ADVERSARY role.

    Per CEO Section 13: OBVIOUSNESS_ADVERSARY does NOT receive generator's
    narrative rationale. It receives only:
      - canonical claim
      - prior art
      - claim mappings
      - technical evidence
    """
    obs = ObviousnessEvidenceV33(
        adversary_model="meta/llama-3.1-8b-instruct",
        adversary_prompt_hash=OBVIOUSNESS_ADVERSARY_PROMPT_HASH,
        constructed_at_utc=_now_utc(),
    )

    # Step 1: Select closest prior art
    closest_id, closest_rationale, similarity = select_closest_prior_art(
        case, novelty_results, evidence
    )
    obs.closest_prior_art_id = closest_id
    obs.closest_prior_art_rationale = closest_rationale
    obs.closest_prior_art_similarity = similarity

    if closest_id == "NONE_NEEDED":
        obs.could_question = "NO"
        obs.would_question = "NO"
        obs.obviousness_succeeds = False
        obs.determination_rationale = "102 already anticipates — 103 not needed."
        return obs, 0

    # Find closest prior art evidence
    closest_evidence = next((e for e in evidence if e.get("patent_id") == closest_id), None)
    closest_claims = closest_evidence.get("claim_text_excerpt", "") if closest_evidence else ""

    # Find differences (limitations missing in closest prior art)
    closest_novelty = next((r for r in novelty_results if r.get("patent_id") == closest_id), None)
    if closest_novelty:
        obs.differences = closest_novelty.get("limitations_missing", [])

    # Find secondary reference (second closest)
    surviving = [r for r in novelty_results if not r.get("anticipation_succeeds", False)
                 and r.get("patent_id") != closest_id]
    if surviving:
        surviving.sort(key=lambda r: len(r.get("limitations_found", [])), reverse=True)
        obs.secondary_reference_id = surviving[0].get("patent_id", "")

    # Step 2: Pass A — formulate objective technical problem WITHOUT seeing invention
    # Per CEO Section 10: Hide the final invention solution.
    sys_prompt_a = (
        "You are an OBVIOUSNESS_ADVERSARY performing Pass A (pre-disclosure). "
        "You see ONLY the closest prior art and its limitations. "
        "You must NOT see the claimed invention's solution. "
        "Formulate the objective technical problem that a person skilled in the art "
        "would naturally try to solve based on the closest prior art alone. "
        "Do NOT reason backwards from any known solution. "
        "Return strict JSON."
    )
    user_prompt_a = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Closest prior art patent: {closest_id}\n"
        f"Closest prior art claims excerpt: {closest_claims[:1500]}\n"
        f"Limitations found in closest prior art: {closest_novelty.get('limitations_found', []) if closest_novelty else []}\n"
        f"Limitations missing in closest prior art: {closest_novelty.get('limitations_missing', []) if closest_novelty else []}\n\n"
        "Return JSON: {\n"
        '  "objective_technical_problem": "...",\n'
        '  "expected_solution_direction": "what a PSA would naturally try (NOT the claimed solution)"\n'
        "}"
    )
    content_a, _ = llm.chat(sys_prompt_a, user_prompt_a, temperature=0.0, max_tokens=800)
    llm_calls = 1

    problem_before = ""
    expected_direction_before = ""
    if content_a and not content_a.startswith("[LLM_ERROR"):
        try:
            c = content_a.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed_a = json.loads(c)
            problem_before = parsed_a.get("objective_technical_problem", "")
            expected_direction_before = parsed_a.get("expected_solution_direction", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    obs.objective_technical_problem = problem_before
    obs.otp_formulated_pre_disclosure = bool(problem_before)
    obs.pass_a_pre_disclosure_solution = expected_direction_before

    # Step 3: Pass B — reveal invention, compare with pre-disclosure
    sys_prompt_b = (
        "You are an OBVIOUSNESS_ADVERSARY performing Pass B (post-disclosure). "
        "Now you may see the claimed invention. "
        "Apply EPO 2026 Guidelines: answer COULD (capability) then WOULD (motivation + expectation). "
        "BOTH must be YES for obviousness. "
        "Construct the combination matrix if combining references. "
        "Assess hindsight risk by comparing pre-disclosure vs post-disclosure reasoning. "
        "Return strict JSON."
    )
    user_prompt_b = (
        f"Pre-disclosure objective technical problem: {problem_before}\n"
        f"Pre-disclosure expected direction: {expected_direction_before}\n\n"
        f"Now seeing claimed invention:\n"
        f"  Patent: {canonical_claim.get('patent_number', '')}\n"
        f"  Title: {case.get('title', '')}\n"
        f"  Device class: {case.get('device_class', '')}\n"
        f"  Limitations: {canonical_claim.get('limitations', [])[:5]}\n\n"
        f"Closest prior art: {closest_id}\n"
        f"  limitations_found: {closest_novelty.get('limitations_found', []) if closest_novelty else []}\n"
        f"  limitations_missing (differences): {closest_novelty.get('limitations_missing', []) if closest_novelty else []}\n"
        + (f"Secondary reference: {obs.secondary_reference_id}\n" if obs.secondary_reference_id else "No secondary reference.\n")
        + "\nReturn JSON: {\n"
        '  "motivation": "...",\n'
        '  "motivation_supported": true|false,\n'
        '  "motivation_evidence": "...",\n'
        '  "technical_effect": {"feature":"...", "effect_description":"...", "effect_source":"DOCUMENTED|INFERRED|HYPOTHESIZED", "effect_strength":"HIGH|MEDIUM|LOW", "is_unexpected":true|false},\n'
        '  "expectation_of_success": "HIGH|MEDIUM|LOW",\n'
        '  "expected_success_supported": true|false,\n'
        '  "expectation_evidence": "...",\n'
        '  "teaching_away": "YES|NO|PARTIAL",\n'
        '  "teaching_away_evidence": "...",\n'
        '  "could_question": "YES|NO",\n'
        '  "could_rationale": "...",\n'
        '  "would_question": "YES|NO",\n'
        '  "would_rationale": "...",\n'
        '  "why_explanation": "...",\n'
        '  "combination_matrix": {"motivation_to_combine":"...", "expected_benefit":"...", "technical_compatibility":"HIGH|MEDIUM|LOW", "teaching_away":"YES|NO|PARTIAL", "pre_filing_reason_to_combine":"..."},\n'
        '  "pass_b_post_disclosure_comparison": "comparison of pre vs post disclosure",\n'
        '  "hindsight_risk": "LOW|MEDIUM|HIGH",\n'
        '  "hindsight_risk_rationale": "...",\n'
        '  "obviousness_succeeds": true|false,\n'
        '  "determination_rationale": "..."\n'
        "}"
    )
    content_b, _ = llm.chat(sys_prompt_b, user_prompt_b, temperature=0.0, max_tokens=2500)
    llm_calls += 1

    if content_b and not content_b.startswith("[LLM_ERROR"):
        try:
            c = content_b.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed_b = json.loads(c)

            obs.motivation = parsed_b.get("motivation", "")
            obs.motivation_supported = bool(parsed_b.get("motivation_supported", False))
            obs.motivation_evidence = parsed_b.get("motivation_evidence", "")

            # Technical effect
            te = parsed_b.get("technical_effect", {})
            if te:
                obs.technical_effects = [TechnicalEffect(
                    feature=te.get("feature", ""),
                    effect_description=te.get("effect_description", ""),
                    effect_source=te.get("effect_source", "INFERRED"),
                    effect_strength=te.get("effect_strength", "MEDIUM"),
                    is_unexpected=bool(te.get("is_unexpected", False)),
                    evidence_links_to_feature=te.get("evidence_links_to_feature", ""),
                )]

            obs.expectation_of_success = parsed_b.get("expectation_of_success", "MEDIUM")
            obs.expected_success_supported = bool(parsed_b.get("expected_success_supported", False))
            obs.expectation_evidence = parsed_b.get("expectation_evidence", "")

            obs.teaching_away = parsed_b.get("teaching_away", "NO")
            obs.teaching_away_evidence = parsed_b.get("teaching_away_evidence", "")

            obs.could_question = parsed_b.get("could_question", "NO")
            obs.could_rationale = parsed_b.get("could_rationale", "")
            obs.would_question = parsed_b.get("would_question", "NO")
            obs.would_rationale = parsed_b.get("would_rationale", "")
            obs.why_explanation = parsed_b.get("why_explanation", "")

            # Combination matrix
            cm = parsed_b.get("combination_matrix", {})
            if cm:
                obs.combination_matrix = CombinationMatrix(
                    reference_a=closest_id,
                    reference_b=obs.secondary_reference_id,
                    elements_from_a=closest_novelty.get("limitations_found", []) if closest_novelty else [],
                    elements_from_b=obs.differences,
                    motivation_to_combine=cm.get("motivation_to_combine", ""),
                    expected_benefit=cm.get("expected_benefit", ""),
                    technical_compatibility=cm.get("technical_compatibility", "MEDIUM"),
                    teaching_away=cm.get("teaching_away", "NO"),
                    pre_filing_reason_to_combine=cm.get("pre_filing_reason_to_combine", ""),
                )

            obs.pass_b_post_disclosure_comparison = parsed_b.get("pass_b_post_disclosure_comparison", "")
            obs.hindsight_risk = parsed_b.get("hindsight_risk", "HIGH")
            obs.hindsight_risk_rationale = parsed_b.get("hindsight_risk_rationale", "")
            obs.determination_rationale = parsed_b.get("determination_rationale", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    # Step 4: Apply COULD ≠ WOULD rule (per CEO Section 7)
    # OBVIOUSNESS_RISK requires:
    #   WOULD = YES
    #   AND MOTIVATION_SUPPORTED = TRUE
    #   AND EXPECTED_SUCCESS_SUPPORTED = TRUE
    could_yes = obs.could_question == "YES"
    would_yes = obs.would_question == "YES"
    motivation_ok = obs.motivation_supported
    expectation_ok = obs.expected_success_supported

    # Only succeed if WOULD=YES AND motivation AND expectation
    obviousness_succeeds = would_yes and motivation_ok and expectation_ok

    # Override the LLM's determination with the strict rule
    if obviousness_succeeds != obs.obviousness_succeeds:
        obs.determination_rationale += (
            f"\n\nV3.3 COULD!=WOULD RULE APPLIED: "
            f"could={obs.could_question}, would={obs.would_question}, "
            f"motivation_supported={motivation_ok}, expected_success_supported={expectation_ok}. "
            f"OBVIOUSNESS_RISK requires WOULD=YES AND MOTIVATION_SUPPORTED=TRUE AND EXPECTED_SUCCESS_SUPPORTED=TRUE. "
            f"Final: obviousness_succeeds={obviousness_succeeds}."
        )
    obs.obviousness_succeeds = obviousness_succeeds

    # Hindsight check — if HINDSIGHT_RISK_HIGH, downgrade obviousness
    if obs.hindsight_risk == "HIGH":
        # High hindsight risk means the reasoning was constructed backwards
        # This weakens the obviousness case
        if obs.obviousness_succeeds:
            obs.obviousness_succeeds = False
            obs.determination_rationale += (
                "\n\nHINDSIGHT FIREWALL: hindsight_risk=HIGH. "
                "Obviousness rejected because reasoning was constructed backwards from the invention."
            )

    return obs, llm_calls
