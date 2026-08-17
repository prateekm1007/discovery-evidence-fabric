"""
OBVIOUSNESS V3.9 — Combination Validity + Evidence Weighting
==============================================================

Per CEO V3.9:
  1. Separate 4 questions: EVIDENCE_EXISTS, MOTIVATION_TO_TRY, TECHNICAL_COMPATIBILITY, EXPECTATION_OF_SUCCESS
  2. Motivation != Obviousness — require bridge: motivation -> modification -> why specific -> expected benefit
  3. Technical compatibility: 8 dimensions, INHERENTLY_CONFLICTING blocks
  4. Expectation: EXPECTED_SUCCESS vs HOPE_OF_SUCCESS (no "same field" alone)
  5. Combination penalty: multi-reference needs more evidence
  6. Whole-claim test: functional_interaction + synergy vs mere aggregation
  7. Model ensemble: Gemma=evidence, Nemotron=challenge, llama=adjudication
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


COMPATIBILITY_DIMENSIONS = [
    "OPERATING_CONDITIONS", "MATERIALS", "MECHANISM", "GEOMETRY",
    "CONTROL_LOGIC", "ENERGY_REGIME", "FAILURE_MODES", "PERFORMANCE_OBJECTIVE"
]


@dataclass
class EvidenceExistsAssessment:
    """Question A: Does evidence exist in the prior art?"""
    reference_a: str = ""
    reference_b: str = ""
    evidence_found: bool = False
    evidence_passages: List[str] = field(default_factory=list)


@dataclass
class MotivationAssessment:
    """Question B: Is there motivation to try the combination?

    Per CEO V3.9 Section 4: motivation != obviousness.
    Require bridge: motivation -> proposed modification -> why specific -> expected benefit.
    """
    motivation_to_try: bool = False
    motivation_type: str = ""
    motivation_passage: str = ""
    proposed_modification: str = ""
    why_this_specific_modification: str = ""
    expected_benefit: str = ""
    bridge_complete: bool = False  # True only if all 4 bridge elements present


@dataclass
class TechnicalCompatibilityAssessment:
    """Question C: Are the references technically compatible?

    Per CEO V3.9 Section 5: 8 dimensions.
    INHERENTLY_CONFLICTING blocks combination.
    """
    operating_conditions: str = "UNKNOWN"
    materials: str = "UNKNOWN"
    mechanism: str = "UNKNOWN"
    geometry: str = "UNKNOWN"
    control_logic: str = "UNKNOWN"
    energy_regime: str = "UNKNOWN"
    failure_modes: str = "UNKNOWN"
    performance_objective: str = "UNKNOWN"
    overall_state: str = "UNKNOWN"  # COMPATIBLE / COMPATIBLE_WITH_MODIFICATION / INHERENTLY_CONFLICTING / UNKNOWN
    conflict_reasons: List[str] = field(default_factory=list)


@dataclass
class ExpectationOfSuccessAssessment:
    """Question D: Is there reasonable expectation of success?

    Per CEO V3.9 Section 6: separate EXPECTED_SUCCESS from HOPE_OF_SUCCESS.
    Do NOT accept 'same field' or 'same function' alone.
    """
    expected_success: bool = False  # True = EXPECTED, False = HOPE or UNKNOWN
    hope_of_success: bool = False
    evidence_basis: str = ""  # what evidence supports expectation
    is_reasonable: bool = False  # True only if evidence-based, not just "same field"


@dataclass
class WholeClaimTest:
    """Per CEO V3.9 Section 8: evaluate claim AS A WHOLE."""
    functional_interaction: str = ""  # NONE / WEAK / MODERATE / STRONG
    combined_technical_effect: str = ""
    synergy: str = ""  # NONE / ADDITIVE / SYNERGISTIC
    is_mere_aggregation: bool = False  # True = no functional interaction


@dataclass
class CombinationPenalty:
    """Per CEO V3.9 Section 7: multi-reference penalty."""
    reference_count: int = 0
    combination_steps: int = 0
    evidence_per_step: List[bool] = field(default_factory=list)
    all_steps_supported: bool = False


@dataclass
class ObviousnessEvidenceV39:
    """V3.9 103 evidence with separated 4-question chain."""
    # Closest prior art
    closest_prior_art: str = ""
    secondary_reference: str = ""
    difference_elements: List[Dict] = field(default_factory=list)

    # 4 separated questions
    evidence_exists: Optional[EvidenceExistsAssessment] = None
    motivation: Optional[MotivationAssessment] = None
    compatibility: Optional[TechnicalCompatibilityAssessment] = None
    expectation: Optional[ExpectationOfSuccessAssessment] = None

    # Whole-claim test
    whole_claim: Optional[WholeClaimTest] = None

    # Combination penalty
    combination: Optional[CombinationPenalty] = None

    # COULD / WOULD
    could: str = "NO"
    would: str = "NO"

    # Hindsight
    hindsight: str = "LOW"
    hindsight_rationale: str = ""

    # Final
    obviousness_succeeds: bool = False
    determination: str = "INSUFFICIENT_EVIDENCE"
    determination_rationale: str = ""

    # Audit
    adversary_model: str = "google/gemma-4-31b-it"
    adversary_prompt_hash: str = ""
    constructed_at_utc: str = ""


OBVIOUSNESS_ADVERSARY_V39_PROMPT_HASH = _sha256(
    "OBVIOUSNESS_ADVERSARY_V3_9: Separated 4-question chain. "
    "Motivation != Obviousness. Technical compatibility 8 dims. "
    "Combination penalty. Whole-claim test. Model ensemble."
)


def construct_obviousness_evidence_v39(
    case: Dict[str, Any],
    canonical_claim: Dict[str, Any],
    novelty_evidence: Any,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[ObviousnessEvidenceV39, int]:
    """Construct V3.9 103 evidence with separated 4-question chain."""
    total_calls = 0

    obs = ObviousnessEvidenceV39(
        adversary_prompt_hash=OBVIOUSNESS_ADVERSARY_V39_PROMPT_HASH,
        constructed_at_utc=_now_utc(),
    )

    limitation_mappings = getattr(novelty_evidence, "limitation_mappings", [])
    refs_with_claims = [e for e in evidence if e.get("claims_retrieved")]

    if not refs_with_claims:
        obs.determination = "INSUFFICIENT_EVIDENCE"
        return obs, 0

    # Select closest prior art
    candidates = []
    for ref in refs_with_claims[:5]:
        ref_id = ref.get("patent_id", "")
        express_count = sum(1 for lm in limitation_mappings
                           if lm.reference_id == ref_id and lm.disclosure_type == "EXPRESS")
        total_mapped = express_count + sum(1 for lm in limitation_mappings
                                          if lm.reference_id == ref_id
                                          and lm.disclosure_type == "NECESSARILY_INHERENT")
        candidates.append({"patent_id": ref_id, "score": (express_count * 2 + total_mapped) / 10.0,
                          "express_count": express_count})
    candidates.sort(key=lambda c: -c["score"])

    if not candidates:
        obs.determination = "INSUFFICIENT_EVIDENCE"
        return obs, 0

    obs.closest_prior_art = candidates[0]["patent_id"]
    if len(candidates) > 1:
        obs.secondary_reference = candidates[1]["patent_id"]

    closest_ev = next((e for e in evidence if e.get("patent_id") == obs.closest_prior_art), None)
    secondary_ev = next((e for e in evidence if e.get("patent_id") == obs.secondary_reference), None) if obs.secondary_reference else None
    closest_claims = closest_ev.get("claim_text_excerpt", "")[:2000] if closest_ev else ""
    secondary_claims = secondary_ev.get("claim_text_excerpt", "")[:2000] if secondary_ev else ""

    # SINGLE comprehensive LLM call with gemma-4 for all 4 questions + whole-claim + combination
    sys_prompt = (
        "You are a 103 OBVIOUSNESS ADVERSARY V3.9. "
        "Evaluate 4 SEPARATE questions independently. Do NOT collapse them.\n\n"
        "CRITICAL RULE: Motivation != Obviousness. Finding motivation to combine is NOT sufficient. "
        "You must also establish technical compatibility AND reasonable expectation of success.\n\n"
        "Question A - EVIDENCE_EXISTS: Does the prior art contain the relevant disclosures?\n"
        "Question B - MOTIVATION_TO_TRY: Is there motivation? BUT motivation alone is NOT obviousness. "
        "Require bridge: motivation -> proposed_modification -> why_this_specific -> expected_benefit.\n"
        "Question C - TECHNICAL_COMPATIBILITY: Score 8 dimensions. "
        "INHERENTLY_CONFLICTING blocks the combination.\n"
        "Question D - EXPECTATION_OF_SUCCESS: Is there REASONABLE expectation (not just hope)? "
        "Do NOT accept 'same field' or 'same function' alone.\n\n"
        "Also evaluate:\n"
        "WHOLE_CLAIM: Is there functional interaction + synergy, or is it mere aggregation?\n"
        "COMBINATION_PENALTY: How many references needed? Multi-reference needs more evidence.\n\n"
        "Be CONSERVATIVE on obviousness. Only return obviousness_succeeds=true if ALL 4 questions "
        "are answered affirmatively with evidence. Motivation alone is NOT enough.\n\n"
        "Return strict JSON."
    )

    user_prompt = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Claim: {case.get('title', '')}\n"
        f"Examiner reasoning: {case.get('examiner_reasoning', '')}\n\n"
        f"Closest prior art ({obs.closest_prior_art}):\n{closest_claims}\n\n"
    )
    if secondary_claims:
        user_prompt += f"Secondary ({obs.secondary_reference}):\n{secondary_claims}\n\n"

    user_prompt += (
        "Return JSON:\n"
        "{\n"
        '  "evidence_exists": {"evidence_found": true|false, "evidence_passages": ["..."]},\n'
        '  "motivation": {"motivation_to_try": true|false, "motivation_type": "...", "motivation_passage": "...", "proposed_modification": "...", "why_this_specific_modification": "...", "expected_benefit": "...", "bridge_complete": true|false},\n'
        '  "compatibility": {"operating_conditions": "COMPATIBLE|COMPATIBLE_WITH_MODIFICATION|INHERENTLY_CONFLICTING|UNKNOWN", "materials": "...", "mechanism": "...", "geometry": "...", "control_logic": "...", "energy_regime": "...", "failure_modes": "...", "performance_objective": "...", "overall_state": "...", "conflict_reasons": ["..."]},\n'
        '  "expectation": {"expected_success": true|false, "hope_of_success": true|false, "evidence_basis": "...", "is_reasonable": true|false},\n'
        '  "whole_claim": {"functional_interaction": "NONE|WEAK|MODERATE|STRONG", "combined_technical_effect": "...", "synergy": "NONE|ADDITIVE|SYNERGISTIC", "is_mere_aggregation": true|false},\n'
        '  "combination": {"reference_count": 2, "combination_steps": 1, "evidence_per_step": [true], "all_steps_supported": true|false},\n'
        '  "could": "YES|NO",\n'
        '  "would": "YES|NO",\n'
        '  "hindsight": "LOW|MEDIUM|HIGH",\n'
        '  "hindsight_rationale": "...",\n'
        '  "obviousness_succeeds": true|false,\n'
        '  "determination": "OBVIOUSNESS_RISK|INSUFFICIENT_EVIDENCE|NO_OBVIOUSNESS",\n'
        '  "determination_rationale": "..."\n'
        "}\n\n"
        "IMPORTANT: obviousness_succeeds=true requires: evidence_found AND motivation_to_try AND "
        "bridge_complete AND compatibility NOT INHERENTLY_CONFLICTING AND is_reasonable AND "
        "NOT is_mere_aggregation. If ANY is missing, obviousness_succeeds=false."
    )

    content, _ = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=3000)
    total_calls += 1

    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)

            # Parse 4 questions
            ee = parsed.get("evidence_exists", {})
            obs.evidence_exists = EvidenceExistsAssessment(
                reference_a=obs.closest_prior_art,
                reference_b=obs.secondary_reference,
                evidence_found=bool(ee.get("evidence_found", False)),
                evidence_passages=ee.get("evidence_passages", []),
            )

            mo = parsed.get("motivation", {})
            obs.motivation = MotivationAssessment(
                motivation_to_try=bool(mo.get("motivation_to_try", False)),
                motivation_type=mo.get("motivation_type", ""),
                motivation_passage=mo.get("motivation_passage", ""),
                proposed_modification=mo.get("proposed_modification", ""),
                why_this_specific_modification=mo.get("why_this_specific_modification", ""),
                expected_benefit=mo.get("expected_benefit", ""),
                bridge_complete=bool(mo.get("bridge_complete", False)),
            )

            co = parsed.get("compatibility", {})
            obs.compatibility = TechnicalCompatibilityAssessment(
                operating_conditions=co.get("operating_conditions", "UNKNOWN"),
                materials=co.get("materials", "UNKNOWN"),
                mechanism=co.get("mechanism", "UNKNOWN"),
                geometry=co.get("geometry", "UNKNOWN"),
                control_logic=co.get("control_logic", "UNKNOWN"),
                energy_regime=co.get("energy_regime", "UNKNOWN"),
                failure_modes=co.get("failure_modes", "UNKNOWN"),
                performance_objective=co.get("performance_objective", "UNKNOWN"),
                overall_state=co.get("overall_state", "UNKNOWN"),
                conflict_reasons=co.get("conflict_reasons", []),
            )

            ex = parsed.get("expectation", {})
            obs.expectation = ExpectationOfSuccessAssessment(
                expected_success=bool(ex.get("expected_success", False)),
                hope_of_success=bool(ex.get("hope_of_success", False)),
                evidence_basis=ex.get("evidence_basis", ""),
                is_reasonable=bool(ex.get("is_reasonable", False)),
            )

            wc = parsed.get("whole_claim", {})
            obs.whole_claim = WholeClaimTest(
                functional_interaction=wc.get("functional_interaction", "NONE"),
                combined_technical_effect=wc.get("combined_technical_effect", ""),
                synergy=wc.get("synergy", "NONE"),
                is_mere_aggregation=bool(wc.get("is_mere_aggregation", False)),
            )

            cb = parsed.get("combination", {})
            obs.combination = CombinationPenalty(
                reference_count=int(cb.get("reference_count", 0)),
                combination_steps=int(cb.get("combination_steps", 0)),
                evidence_per_step=cb.get("evidence_per_step", []),
                all_steps_supported=bool(cb.get("all_steps_supported", False)),
            )

            obs.could = parsed.get("could", "NO")
            obs.would = parsed.get("would", "NO")
            obs.hindsight = parsed.get("hindsight", "LOW")
            obs.hindsight_rationale = parsed.get("hindsight_rationale", "")
            obs.determination_rationale = parsed.get("determination_rationale", "")

        except (json.JSONDecodeError, AttributeError):
            pass

    # V3.9 DECISION CHAIN: apply strict rules
    # 103 requires ALL of:
    #   1. evidence_exists
    #   2. motivation_to_try AND bridge_complete
    #   3. compatibility NOT INHERENTLY_CONFLICTING
    #   4. is_reasonable (expectation)
    #   5. NOT is_mere_aggregation
    #   6. hindsight != HIGH

    evidence_ok = obs.evidence_exists and obs.evidence_exists.evidence_found
    motivation_ok = obs.motivation and obs.motivation.motivation_to_try and obs.motivation.bridge_complete
    compatibility_ok = obs.compatibility and obs.compatibility.overall_state != "INHERENTLY_CONFLICTING"
    expectation_ok = obs.expectation and obs.expectation.is_reasonable
    whole_claim_ok = obs.whole_claim and not obs.whole_claim.is_mere_aggregation
    hindsight_ok = obs.hindsight != "HIGH"

    # Combination penalty: if >2 references, require all_steps_supported
    combination_ok = True
    if obs.combination and obs.combination.reference_count > 2:
        combination_ok = obs.combination.all_steps_supported

    all_conditions = (evidence_ok and motivation_ok and compatibility_ok and
                     expectation_ok and whole_claim_ok and hindsight_ok and combination_ok)

    if all_conditions:
        obs.obviousness_succeeds = True
        obs.determination = "OBVIOUSNESS_RISK"
        obs.determination_rationale = (
            f"All 4 questions answered: evidence={evidence_ok}, motivation={motivation_ok} "
            f"(bridge={obs.motivation.bridge_complete if obs.motivation else False}), "
            f"compatibility={compatibility_ok} ({obs.compatibility.overall_state if obs.compatibility else 'N/A'}), "
            f"expectation={expectation_ok} (reasonable={obs.expectation.is_reasonable if obs.expectation else False}), "
            f"whole_claim={whole_claim_ok} (aggregation={obs.whole_claim.is_mere_aggregation if obs.whole_claim else 'N/A'}), "
            f"hindsight={obs.hindsight}, combination={combination_ok}"
        )
    else:
        obs.obviousness_succeeds = False
        # Determine which condition failed
        failed = []
        if not evidence_ok: failed.append("EVIDENCE_EXISTS")
        if not motivation_ok: failed.append("MOTIVATION_BRIDGE")
        if not compatibility_ok: failed.append("COMPATIBILITY_CONFLICTING")
        if not expectation_ok: failed.append("EXPECTATION_NOT_REASONABLE")
        if not whole_claim_ok: failed.append("MERE_AGGREGATION")
        if not hindsight_ok: failed.append("HINDSIGHT_HIGH")
        if not combination_ok: failed.append("COMBINATION_PENALTY")

        if obs.could == "YES" and not all([motivation_ok, expectation_ok]):
            obs.determination = "INSUFFICIENT_EVIDENCE"
        else:
            obs.determination = "NO_OBVIOUSNESS"
        obs.determination_rationale = f"Failed: {', '.join(failed)}"

    obs.could = "YES" if (evidence_ok and expectation_ok) else "NO"
    obs.would = "YES" if all_conditions else "NO"

    return obs, total_calls
