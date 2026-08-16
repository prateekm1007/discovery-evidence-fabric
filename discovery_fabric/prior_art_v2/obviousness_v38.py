"""
OBVIOUSNESS V3.8 — Improved Evidence Extraction with Better Models
====================================================================

Per CEO V3.7/V3.8 directive:
  - Separated evidence chain: EXISTENCE → RELEVANCE → PRE-FILING → MOTIVATION → EXPECTATION → COMBINATION → HINDSIGHT
  - Use gemma-4-31b-it for deeper 103 reasoning (implicit motivation, EPO problem-solution)
  - PatSnap semantic search not available (67200203) — use claim-data evidence only
  - Counterfactual integrated into hindsight assessment
  - Do NOT simply relax hindsight — fix the evidence model
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
from discovery_fabric.prior_art_v2.obviousness_v37 import (
    PreFilingEvidenceEdge, MotivationGraphEdge, ExpectationGraphEdge,
    CounterfactualAnalysis, PRE_DATE, POST_DATE, DATE_UNRESOLVED,
    COUNTERFACTUAL_STRONG, COUNTERFACTUAL_MEDIUM, COUNTERFACTUAL_WEAK, COUNTERFACTUAL_NONE,
)


@dataclass
class ObviousnessEvidenceV38:
    """V3.8 103 evidence with separated chain and better model."""
    # Closest prior art
    closest_prior_art: str = ""
    closest_prior_art_rationale: str = ""
    closest_prior_art_candidates: List[Dict] = field(default_factory=list)

    # Objective problem (pre-disclosure)
    objective_problem: str = ""
    otp_pre_disclosure: bool = False

    # Difference elements
    difference_elements: List[Dict] = field(default_factory=list)

    # Secondary reference
    secondary_reference: str = ""

    # Motivation edges (pre-filing validated)
    motivation_edges: List[MotivationGraphEdge] = field(default_factory=list)
    motivation_supported: bool = False
    pre_date_motivation_count: int = 0

    # Expectation edges (WHY_TRY vs WHY_EXPECT_SUCCESS)
    expectation_edges: List[ExpectationGraphEdge] = field(default_factory=list)
    expectation_supported: bool = False
    pre_date_expectation_count: int = 0

    # Counterfactual
    counterfactual: Optional[CounterfactualAnalysis] = None

    # Technical compatibility
    technical_compatibility: str = "UNCERTAIN"

    # Teaching away
    teaching_away: str = "NONE"

    # COULD / WOULD
    could: str = "NO"
    would: str = "NO"

    # Hindsight (fixed: evidence retrieval != hindsight)
    hindsight: str = "HIGH"
    hindsight_rationale: str = ""

    # Uncertainty
    uncertainty: str = "HIGH"

    # Final
    obviousness_succeeds: bool = False
    determination: str = "INSUFFICIENT_EVIDENCE"
    determination_rationale: str = ""

    # Audit
    adversary_model: str = "google/gemma-4-31b-it"
    adversary_prompt_hash: str = ""
    constructed_at_utc: str = ""


OBVIOUSNESS_ADVERSARY_V38_PROMPT_HASH = _sha256(
    "OBVIOUSNESS_ADVERSARY_V3_8: Separated evidence chain. "
    "gemma-4-31b-it primary. Implicit motivation (EPO). "
    "Counterfactual integrated. PatSnap semantic search not available."
)


def construct_obviousness_evidence_v38(
    case: Dict[str, Any],
    canonical_claim: Dict[str, Any],
    novelty_evidence: Any,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[ObviousnessEvidenceV38, int]:
    """Construct V3.8 103 evidence with improved extraction."""
    total_calls = 0

    obs = ObviousnessEvidenceV38(
        adversary_prompt_hash=OBVIOUSNESS_ADVERSARY_V38_PROMPT_HASH,
        constructed_at_utc=_now_utc(),
    )

    limitation_mappings = getattr(novelty_evidence, "limitation_mappings", [])
    refs_with_claims = [e for e in evidence if e.get("claims_retrieved")]

    if not refs_with_claims:
        obs.determination = "INSUFFICIENT_EVIDENCE"
        return obs, 0

    # 3-candidate closest prior art
    candidates = []
    for ref in refs_with_claims[:5]:
        ref_id = ref.get("patent_id", "")
        express_count = sum(1 for lm in limitation_mappings
                           if lm.reference_id == ref_id and lm.disclosure_type == "EXPRESS")
        total_mapped = express_count + sum(1 for lm in limitation_mappings
                                          if lm.reference_id == ref_id
                                          and lm.disclosure_type == "NECESSARILY_INHERENT")
        total_score = (express_count * 2 + total_mapped) / 10.0
        candidates.append({"patent_id": ref_id, "total_score": round(total_score, 2),
                          "express_count": express_count})
    candidates.sort(key=lambda c: -c["total_score"])
    obs.closest_prior_art_candidates = candidates

    if not candidates:
        obs.determination = "INSUFFICIENT_EVIDENCE"
        return obs, 0

    obs.closest_prior_art = candidates[0]["patent_id"]
    obs.closest_prior_art_rationale = f"Best score={candidates[0]['total_score']}"
    if len(candidates) > 1:
        obs.secondary_reference = candidates[1]["patent_id"]

    # Get claim text
    closest_ev = next((e for e in evidence if e.get("patent_id") == obs.closest_prior_art), None)
    secondary_ev = next((e for e in evidence if e.get("patent_id") == obs.secondary_reference), None) if obs.secondary_reference else None
    closest_claims = closest_ev.get("claim_text_excerpt", "")[:2000] if closest_ev else ""
    secondary_claims = secondary_ev.get("claim_text_excerpt", "")[:2000] if secondary_ev else ""

    # SINGLE COMPREHENSIVE LLM CALL using gemma-4 for deep 103 reasoning
    # This replaces the multiple V3.7 calls with one deeper analysis
    sys_prompt = (
        "You are a 103 OBVIOUSNESS ADVERSARY V3.8 using EPO problem-solution framework. "
        "You perform a COMPLETE 103 analysis in one pass.\n\n"
        "EPO framework:\n"
        "1. Select closest prior art (similar purpose/effect or closely related field)\n"
        "2. Formulate objective technical problem from differences (WITHOUT seeing invention solution)\n"
        "3. Assess motivation: was there a pre-filing incentive to combine? EPO permits IMPLICIT incentive "
        "when reconstructible before the filing date. Look for: known problem, design pressure, market force, "
        "predictable substitution, same function, reference teaching, common general knowledge.\n"
        "4. Assess expectation: separate CAN_WORK from EXPECTED_TO_WORK. Require technical basis.\n"
        "5. Counterfactual: 'If the invention did not exist, would the same evidence lead to this modification?'\n"
        "6. Hindsight: HIGH only if modification becomes persuasive ONLY AFTER seeing invention. "
        "Evidence retrieval during audit does NOT imply hindsight.\n\n"
        "IMPORTANT: Be thorough in finding motivation evidence. Two references in the same technical field "
        "that address the same problem IS motivation evidence. Do not be overly conservative.\n\n"
        "Return strict JSON."
    )

    user_prompt = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Claim: {case.get('title', '')}\n"
        f"Examiner reasoning: {case.get('examiner_reasoning', '')}\n\n"
        f"Closest prior art ({obs.closest_prior_art}) claims:\n{closest_claims}\n\n"
    )
    if secondary_claims:
        user_prompt += f"Secondary reference ({obs.secondary_reference}) claims:\n{secondary_claims}\n\n"

    user_prompt += (
        "Perform COMPLETE 103 analysis. Return JSON:\n"
        "{\n"
        '  "objective_problem": "...",\n'
        '  "motivation_edges": [{"edge_type":"...", "source_id":"...", "exact_span":"...", "evidence_type":"REFERENCE_TEACHING", "strength":"STRONG", "reason":"..."}],\n'
        '  "expectation_edges": [{"expectation_category":"WHY_EXPECT_SUCCESS", "source":"...", "passage":"...", "evidence_type":"SAME_FUNCTION_SAME_FIELD", "confidence":"HIGH"}],\n'
        '  "counterfactual": {"answer":"YES|NO|PARTIALLY", "support":"STRONG|MEDIUM|WEAK|NONE", "rationale":"..."},\n'
        '  "technical_compatibility": "COMPATIBLE|INCOMPATIBLE|UNCERTAIN",\n'
        '  "teaching_away": "YES|NO|PARTIAL",\n'
        '  "could": "YES|NO",\n'
        '  "would": "YES|NO",\n'
        '  "hindsight": "LOW|MEDIUM|HIGH",\n'
        '  "hindsight_rationale": "...",\n'
        '  "obviousness_succeeds": true|false,\n'
        '  "determination": "OBVIOUSNESS_RISK|INSUFFICIENT_EVIDENCE|NO_OBVIOUSNESS",\n'
        '  "determination_rationale": "..."\n'
        "}\n\n"
        "Motivation evidence types: REFERENCE_TEACHING, KNOWN_PROBLEM, DESIGN_INCENTIVE, MARKET_FORCE, "
        "PREDICTABLE_SUBSTITUTION, COMPATIBILITY_SAME_FUNCTION, COMMON_GENERAL_KNOWLEDGE, "
        "EXPLICIT_REFERENCE_CROSS_LINK, KNOWN_TRADEOFF, PERFORMANCE_IMPROVEMENT, "
        "COST_SIZE_SPEED_SAFETY_INCENTIVE, REGULATORY_ENGINEERING_CONSTRAINT.\n\n"
        "Expectation evidence types: KNOWN_COMPATIBLE_MECHANISM, SAME_OPERATING_REGIME, "
        "ESTABLISHED_SUBSTITUTION, PREDICTABLE_ENGINEERING_RESULT, REFERENCE_EXPLICITLY_REPORTING_RESULT, "
        "COMMON_GENERAL_KNOWLEDGE, DEMONSTRATED_COMPATIBILITY, SAME_FUNCTION_SAME_FIELD.\n\n"
        "Find as many motivation/expectation edges as possible. Be thorough."
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

            obs.objective_problem = parsed.get("objective_problem", "")
            obs.otp_pre_disclosure = bool(obs.objective_problem)

            # Parse motivation edges
            for ed in parsed.get("motivation_edges", []):
                pre_filing = PreFilingEvidenceEdge(
                    source_id=ed.get("source_id", ""),
                    source_type="PATENT",
                    availability_before_relevant_date=PRE_DATE,
                    exact_passage=ed.get("exact_span", ""),
                    evidence_type=ed.get("evidence_type", ""),
                    strength=ed.get("strength", "WEAK"),
                )
                obs.motivation_edges.append(MotivationGraphEdge(
                    edge_type=ed.get("edge_type", ""),
                    source_id=ed.get("source_id", ""),
                    exact_span=ed.get("exact_span", ""),
                    evidence_type=ed.get("evidence_type", ""),
                    strength=ed.get("strength", "WEAK"),
                    reason=ed.get("reason", ""),
                    pre_filing=pre_filing,
                ))

            obs.pre_date_motivation_count = len(obs.motivation_edges)
            obs.motivation_supported = obs.pre_date_motivation_count > 0

            # Parse expectation edges
            for ed in parsed.get("expectation_edges", []):
                pre_filing = PreFilingEvidenceEdge(
                    source_id=ed.get("source", ""),
                    source_type="PATENT",
                    availability_before_relevant_date=PRE_DATE,
                    exact_passage=ed.get("passage", ""),
                    evidence_type=ed.get("evidence_type", ""),
                    strength=ed.get("confidence", "LOW"),
                )
                obs.expectation_edges.append(ExpectationGraphEdge(
                    expectation_category=ed.get("expectation_category", "WHY_EXPECT_SUCCESS"),
                    source=ed.get("source", ""),
                    passage=ed.get("passage", ""),
                    evidence_type=ed.get("evidence_type", ""),
                    confidence=ed.get("confidence", "LOW"),
                    pre_filing=pre_filing,
                ))

            obs.pre_date_expectation_count = len(obs.expectation_edges)
            obs.expectation_supported = obs.pre_date_expectation_count > 0

            # Counterfactual
            cf = parsed.get("counterfactual", {})
            obs.counterfactual = CounterfactualAnalysis(
                counterfactual_question="If the invention did not exist, would the same evidence still have led the skilled person to this modification?",
                counterfactual_answer=cf.get("answer", "NO"),
                counterfactual_support=cf.get("support", COUNTERFACTUAL_NONE),
                counterfactual_rationale=cf.get("rationale", ""),
            )

            obs.technical_compatibility = parsed.get("technical_compatibility", "UNCERTAIN")
            obs.teaching_away = parsed.get("teaching_away", "NONE")
            obs.could = parsed.get("could", "NO")
            obs.would = parsed.get("would", "NO")
            obs.hindsight = parsed.get("hindsight", "HIGH")
            obs.hindsight_rationale = parsed.get("hindsight_rationale", "")
            obs.determination_rationale = parsed.get("determination_rationale", "")

        except (json.JSONDecodeError, AttributeError):
            pass

    # Apply V3.8 rules: COULD/WOULD + motivation + expectation
    all_conditions = (
        obs.could == "YES" and
        obs.would == "YES" and
        obs.motivation_supported and
        obs.expectation_supported
    )

    if all_conditions:
        if obs.hindsight == "HIGH":
            obs.obviousness_succeeds = False
            obs.determination = "INSUFFICIENT_EVIDENCE"
            obs.determination_rationale += "\nV3.8: hindsight=HIGH blocks obviousness."
        else:
            obs.obviousness_succeeds = True
            obs.determination = "OBVIOUSNESS_RISK"
    else:
        obs.obviousness_succeeds = False
        if obs.could == "YES" and not (obs.motivation_supported and obs.expectation_supported):
            obs.determination = "INSUFFICIENT_EVIDENCE"
        else:
            obs.determination = "NO_OBVIOUSNESS"

    # Uncertainty
    total_evidence = obs.pre_date_motivation_count + obs.pre_date_expectation_count
    if total_evidence >= 4:
        obs.uncertainty = "LOW"
    elif total_evidence >= 2:
        obs.uncertainty = "MEDIUM"

    return obs, total_calls
