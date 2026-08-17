"""
OBVIOUSNESS V3.4 — Independent 103 with COULD/WOULD Rule + Two-Pass Anti-Hindsight
===================================================================================

Per CEO V3.4 Sections 7-10:

INDEPENDENT 103 PATH:
  The 103 adversary must NOT see:
    - generator rationale
    - commercial rationale
    - final invention explanation written by generator
  It receives ONLY:
    - canonical claim
    - verified evidence
    - prior-art mappings
    - technical context
  It constructs its own reasoning.

COULD/WOULD RULE:
  103 requires:
    COULD = TRUE
    AND WOULD = TRUE
    AND MOTIVATION_SUPPORTED = TRUE
    AND EXPECTED_SUCCESS_SUPPORTED = TRUE
  If any missing: 103 = INSUFFICIENT_EVIDENCE (not OBVIOUSNESS_RISK).

PRE-DISCLOSURE / POST-DISCLOSURE:
  Pass A: do not reveal the claimed solution's novelty thesis.
  Pass B: reveal the full claim.
  Compare: motivation, difference, combination, expected success.
  Large divergence: HINDSIGHT_RISK_HIGH.

ObviousnessEvidenceV34 FIELDS:
  closest_prior_art
  objective_problem
  difference_elements
  secondary_reference
  motivation
  technical_compatibility
  reasonable_expectation
  teaching_away
  could
  would
  why
  technical_effect
  hindsight
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


@dataclass
class ObviousnessEvidenceV34:
    """Independent 103 evidence object per CEO V3.4 Section 7.

    The 103 adversary constructs this WITHOUT seeing generator/commercial rationale.
    """
    # Closest prior art (technically close — similar purpose/effect OR closely related field)
    closest_prior_art: str = ""
    closest_prior_art_rationale: str = ""
    closest_prior_art_similarity: str = ""  # SIMILAR_PURPOSE / CLOSELY_RELATED_FIELD / WEAK

    # Objective technical problem (formulated WITHOUT seeing invention solution)
    objective_problem: str = ""
    otp_formulated_pre_disclosure: bool = False

    # Difference elements (what the claim has that closest prior art doesn't)
    difference_elements: List[str] = field(default_factory=list)

    # Secondary reference (for combination)
    secondary_reference: str = ""

    # Motivation
    motivation: str = ""
    motivation_supported: bool = False
    motivation_evidence: str = ""

    # Technical compatibility
    technical_compatibility: str = ""  # HIGH / MEDIUM / LOW

    # Reasonable expectation of success
    reasonable_expectation: str = ""  # HIGH / MEDIUM / LOW
    expected_success_supported: bool = False
    expectation_evidence: str = ""

    # Teaching away
    teaching_away: str = ""  # YES / NO / PARTIAL
    teaching_away_evidence: str = ""

    # COULD vs WOULD (per CEO V3.4 Section 8)
    could: str = ""  # YES / NO — capability
    could_rationale: str = ""
    would: str = ""  # YES / NO — motivation + expectation
    would_rationale: str = ""

    # WHY explanation
    why: str = ""

    # Technical effect
    technical_effect: str = ""
    technical_effect_source: str = ""  # DOCUMENTED / INFERRED / HYPOTHESIZED
    technical_effect_strength: str = ""  # HIGH / MEDIUM / LOW
    is_unexpected: bool = False

    # Hindsight (two-pass comparison)
    pass_a_pre_disclosure: str = ""  # what PSA would do without seeing invention
    pass_b_post_disclosure: str = ""  # comparison after seeing invention
    hindsight: str = ""  # LOW / MEDIUM / HIGH
    hindsight_rationale: str = ""

    # Final determination
    obviousness_succeeds: bool = False  # True = 103 rejects
    determination: str = "INSUFFICIENT_EVIDENCE"  # OBVIOUSNESS_RISK / INSUFFICIENT_EVIDENCE / NO_OBVIOUSNESS
    determination_rationale: str = ""

    # Audit
    adversary_model: str = ""
    adversary_prompt_hash: str = ""
    constructed_at_utc: str = ""


# ----------------------- OBVIOUSNESS ADVERSARY V3.4 -----------------------
OBVIOUSNESS_ADVERSARY_V34_PROMPT_HASH = _sha256(
    "OBVIOUSNESS_ADVERSARY_V3_4: Independent 103. "
    "Does NOT receive generator/commercial rationale. "
    "Receives ONLY: canonical claim + verified evidence + prior-art mappings + technical context. "
    "COULD != WOULD rule. Two-pass anti-hindsight. "
    "If any of COULD/WOULD/MOTIVATION/EXPECTATION missing: INSUFFICIENT_EVIDENCE."
)


def select_closest_prior_art_v34(
    case: Dict[str, Any],
    novelty_evidence: Any,  # NoveltyEvidenceV34
    evidence: List[Dict[str, Any]],
) -> Tuple[str, str, str]:
    """Select closest prior art per CEO V3.4 Section 8.

    Require: similar purpose/effect OR same/closely related field.
    Do NOT select a convenient patent merely because it shares one keyword.
    """
    # Get limitation mappings from novelty evidence
    limitation_mappings = getattr(novelty_evidence, "limitation_mappings", [])

    if not limitation_mappings:
        return ("NONE_NEEDED", "No limitation mappings — cannot select closest prior art", "NONE")

    # Find the reference that maps the most limitations with EXPRESS or NECESSARILY_INHERENT
    reference_scores: Dict[str, int] = {}
    reference_express_count: Dict[str, int] = {}
    for lm in limitation_mappings:
        ref = lm.reference_id
        if not ref:
            continue
        if ref not in reference_scores:
            reference_scores[ref] = 0
            reference_express_count[ref] = 0
        if lm.disclosure_type in ("EXPRESS", "NECESSARILY_INHERENT"):
            reference_scores[ref] += 2
            if lm.disclosure_type == "EXPRESS":
                reference_express_count[ref] += 1
        elif lm.disclosure_type == "UNCERTAIN":
            reference_scores[ref] += 0  # uncertain doesn't help
        # NOT_DISCLOSED: -1 (penalize)
        elif lm.disclosure_type == "NOT_DISCLOSED":
            reference_scores[ref] -= 1

    if not reference_scores:
        return ("NONE_NEEDED", "No references with mappings", "NONE")

    # Sort by score
    sorted_refs = sorted(reference_scores.items(), key=lambda x: -x[1])
    closest_id, closest_score = sorted_refs[0]

    # Determine similarity level
    express_count = reference_express_count.get(closest_id, 0)
    has_gold = any(e.get("patent_id") == closest_id and e.get("claims_retrieved") for e in evidence)

    if express_count >= 3 and has_gold:
        similarity = "SIMILAR_PURPOSE"
        rationale = (
            f"Selected as closest prior art because it EXPRESSLY discloses {express_count} "
            f"limitations with actual claim text (GOLD evidence). Score={closest_score}. "
            f"This is the most technically close reference."
        )
    elif express_count >= 1:
        similarity = "CLOSELY_RELATED_FIELD"
        rationale = (
            f"Selected as closest prior art because it EXPRESSLY discloses {express_count} "
            f"limitations. Score={closest_score}. Closely related technical field."
        )
    elif closest_score > 0:
        similarity = "WEAK"
        rationale = (
            f"Selected as closest prior art by default — best score={closest_score} "
            f"but only {express_count} EXPRESS disclosures. Weak similarity."
        )
    else:
        similarity = "WEAK"
        rationale = (
            f"No reference has EXPRESS disclosures. Closest={closest_id} with score={closest_score}."
        )

    return (closest_id, rationale, similarity)


def construct_obviousness_evidence_v34(
    case: Dict[str, Any],
    canonical_claim: Dict[str, Any],
    novelty_evidence: Any,  # NoveltyEvidenceV34 — 103 receives 102 results
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[ObviousnessEvidenceV34, int]:
    """Construct independent 103 evidence object.

    Per CEO V3.4 Section 9: 103 adversary does NOT receive generator rationale.
    It receives ONLY: canonical claim + verified evidence + prior-art mappings + technical context.
    """
    obs = ObviousnessEvidenceV34(
        adversary_model="meta/llama-3.1-8b-instruct",
        adversary_prompt_hash=OBVIOUSNESS_ADVERSARY_V34_PROMPT_HASH,
        constructed_at_utc=_now_utc(),
    )

    # Step 1: Select closest prior art (using 102 mapping results)
    closest_id, closest_rationale, similarity = select_closest_prior_art_v34(
        case, novelty_evidence, evidence
    )
    obs.closest_prior_art = closest_id
    obs.closest_prior_art_rationale = closest_rationale
    obs.closest_prior_art_similarity = similarity

    if closest_id == "NONE_NEEDED":
        obs.could = "NO"
        obs.would = "NO"
        obs.obviousness_succeeds = False
        obs.determination = "INSUFFICIENT_EVIDENCE"
        obs.determination_rationale = "No closest prior art available — 103 not applicable."
        return obs, 0

    # Get closest prior art evidence
    closest_evidence = next((e for e in evidence if e.get("patent_id") == closest_id), None)
    closest_claims = closest_evidence.get("claim_text_excerpt", "") if closest_evidence else ""

    # Get difference elements (limitations NOT_DISCLOSED or UNCERTAIN in closest prior art)
    limitation_mappings = getattr(novelty_evidence, "limitation_mappings", [])
    obs.difference_elements = [
        lm.limitation_id for lm in limitation_mappings
        if lm.reference_id == closest_id and lm.disclosure_type in ("NOT_DISCLOSED", "UNCERTAIN")
    ]

    # Find secondary reference
    reference_scores: Dict[str, int] = {}
    for lm in limitation_mappings:
        ref = lm.reference_id
        if ref and ref != closest_id:
            if ref not in reference_scores:
                reference_scores[ref] = 0
            if lm.disclosure_type in ("EXPRESS", "NECESSARILY_INHERENT"):
                reference_scores[ref] += 1

    if reference_scores:
        obs.secondary_reference = max(reference_scores, key=reference_scores.get)

    # Step 2: Pass A — formulate objective technical problem WITHOUT seeing invention
    # Per CEO V3.4 Section 10: Hide the claimed solution's novelty thesis.
    sys_prompt_a = (
        "You are an OBVIOUSNESS_ADVERSARY V3.4 performing Pass A (pre-disclosure). "
        "You see ONLY the closest prior art and its limitations. "
        "You must NOT see the claimed invention's solution or novelty thesis. "
        "Formulate the objective technical problem that a person skilled in the art "
        "would naturally try to solve based on the closest prior art alone. "
        "Do NOT reason backwards from any known solution. "
        "Return strict JSON."
    )
    user_prompt_a = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Closest prior art patent: {closest_id}\n"
        f"Closest prior art claims excerpt: {closest_claims[:1500]}\n"
        f"Limitations EXPRESSLY disclosed in closest prior art: "
        f"{[lm.limitation_id for lm in limitation_mappings if lm.reference_id == closest_id and lm.disclosure_type == 'EXPRESS']}\n"
        f"Limitations NOT disclosed in closest prior art: {obs.difference_elements}\n\n"
        "Return JSON: {\n"
        '  "objective_problem": "...",\n'
        '  "pre_disclosure_solution_direction": "what a PSA would naturally try (NOT the claimed solution)"\n'
        "}"
    )
    content_a, _ = llm.chat(sys_prompt_a, user_prompt_a, temperature=0.0, max_tokens=800)
    llm_calls = 1

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
            direction_before = parsed_a.get("pre_disclosure_solution_direction", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    obs.objective_problem = problem_before
    obs.otp_formulated_pre_disclosure = bool(problem_before)
    obs.pass_a_pre_disclosure = direction_before

    # Step 3: Pass B — reveal invention, compare with pre-disclosure
    # Per CEO V3.4 Section 9: 103 adversary receives ONLY canonical claim + evidence + mappings.
    # It does NOT receive generator rationale.
    sys_prompt_b = (
        "You are an OBVIOUSNESS_ADVERSARY V3.4 performing Pass B (post-disclosure). "
        "Now you may see the claimed invention's CANONICAL CLAIM and PRIOR-ART MAPPINGS. "
        "You do NOT receive any generator/commercial rationale. "
        "Apply EPO 2026 Guidelines: answer COULD (capability) then WOULD (motivation + expectation). "
        "BOTH must be YES for obviousness. "
        "Compare with your pre-disclosure formulation to assess hindsight risk. "
        "Return strict JSON."
    )
    user_prompt_b = (
        f"Pre-disclosure objective problem: {problem_before}\n"
        f"Pre-disclosure direction: {direction_before}\n\n"
        f"Now seeing CANONICAL CLAIM (no generator rationale):\n"
        f"  Patent: {canonical_claim.get('patent_number', '')}\n"
        f"  Technical field: {case.get('device_class', '')}\n"
        f"  Limitations: {canonical_claim.get('limitations', [])[:5]}\n\n"
        f"PRIOR-ART MAPPINGS (from 102 analysis):\n"
        f"  Closest prior art: {closest_id} (similarity: {similarity})\n"
        f"  Difference elements: {obs.difference_elements}\n"
        + (f"  Secondary reference: {obs.secondary_reference}\n" if obs.secondary_reference else "")
        + "\nReturn JSON: {\n"
        '  "motivation": "...",\n'
        '  "motivation_supported": true|false,\n'
        '  "motivation_evidence": "...",\n'
        '  "technical_compatibility": "HIGH|MEDIUM|LOW",\n'
        '  "reasonable_expectation": "HIGH|MEDIUM|LOW",\n'
        '  "expected_success_supported": true|false,\n'
        '  "expectation_evidence": "...",\n'
        '  "teaching_away": "YES|NO|PARTIAL",\n'
        '  "teaching_away_evidence": "...",\n'
        '  "could": "YES|NO",\n'
        '  "could_rationale": "...",\n'
        '  "would": "YES|NO",\n'
        '  "would_rationale": "...",\n'
        '  "why": "...",\n'
        '  "technical_effect": "...",\n'
        '  "technical_effect_source": "DOCUMENTED|INFERRED|HYPOTHESIZED",\n'
        '  "technical_effect_strength": "HIGH|MEDIUM|LOW",\n'
        '  "is_unexpected": true|false,\n'
        '  "pass_b_post_disclosure": "comparison of pre vs post disclosure",\n'
        '  "hindsight": "LOW|MEDIUM|HIGH",\n'
        '  "hindsight_rationale": "...",\n'
        '  "obviousness_succeeds": true|false,\n'
        '  "determination": "OBVIOUSNESS_RISK|INSUFFICIENT_EVIDENCE|NO_OBVIOUSNESS",\n'
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
            obs.technical_compatibility = parsed_b.get("technical_compatibility", "MEDIUM")
            obs.reasonable_expectation = parsed_b.get("reasonable_expectation", "MEDIUM")
            obs.expected_success_supported = bool(parsed_b.get("expected_success_supported", False))
            obs.expectation_evidence = parsed_b.get("expectation_evidence", "")
            obs.teaching_away = parsed_b.get("teaching_away", "NO")
            obs.teaching_away_evidence = parsed_b.get("teaching_away_evidence", "")
            obs.could = parsed_b.get("could", "NO")
            obs.could_rationale = parsed_b.get("could_rationale", "")
            obs.would = parsed_b.get("would", "NO")
            obs.would_rationale = parsed_b.get("would_rationale", "")
            obs.why = parsed_b.get("why", "")
            obs.technical_effect = parsed_b.get("technical_effect", "")
            obs.technical_effect_source = parsed_b.get("technical_effect_source", "INFERRED")
            obs.technical_effect_strength = parsed_b.get("technical_effect_strength", "MEDIUM")
            obs.is_unexpected = bool(parsed_b.get("is_unexpected", False))
            obs.pass_b_post_disclosure = parsed_b.get("pass_b_post_disclosure", "")
            obs.hindsight = parsed_b.get("hindsight", "HIGH")
            obs.hindsight_rationale = parsed_b.get("hindsight_rationale", "")
            obs.determination_rationale = parsed_b.get("determination_rationale", "")
        except (json.JSONDecodeError, AttributeError):
            pass

    # Step 4: Apply COULD/WOULD rule (per CEO V3.4 Section 8)
    # 103 requires:
    #   COULD = TRUE
    #   AND WOULD = TRUE
    #   AND MOTIVATION_SUPPORTED = TRUE
    #   AND EXPECTED_SUCCESS_SUPPORTED = TRUE
    # If any missing: 103 = INSUFFICIENT_EVIDENCE (not OBVIOUSNESS_RISK)
    could_yes = obs.could == "YES"
    would_yes = obs.would == "YES"
    motivation_ok = obs.motivation_supported
    expectation_ok = obs.expected_success_supported

    all_conditions_met = could_yes and would_yes and motivation_ok and expectation_ok

    if all_conditions_met:
        obs.obviousness_succeeds = True
        obs.determination = "OBVIOUSNESS_RISK"
    else:
        obs.obviousness_succeeds = False
        # If COULD=YES but WOULD=NO or motivation/expectation missing → INSUFFICIENT_EVIDENCE
        if could_yes and not (would_yes and motivation_ok and expectation_ok):
            obs.determination = "INSUFFICIENT_EVIDENCE"
        else:
            obs.determination = "NO_OBVIOUSNESS"

    # Hindsight firewall — if HINDSIGHT_RISK_HIGH, reject obviousness
    if obs.hindsight == "HIGH":
        if obs.obviousness_succeeds:
            obs.obviousness_succeeds = False
            obs.determination = "INSUFFICIENT_EVIDENCE"
            obs.determination_rationale += (
                "\n\nV3.4 HINDSIGHT FIREWALL: hindsight=HIGH. "
                "Obviousness rejected because reasoning was constructed backwards from the invention."
            )

    return obs, llm_calls
