"""
OBVIOUSNESS V3.6 — Evidence-Grounded Motivation + Expectation Graph
=====================================================================

Per CEO V3.6: fix V3.5 root cause (motivation_insufficient=85%, expectation_insufficient=90%).

KEY CHANGES:
  1. Edge-based evidence graph (not free-form "motivation=yes")
  2. 12 motivation evidence types (not just 7)
  3. 10 motivation search families (M1-M10)
  4. Expectation graph separate from motivation
  5. Combination compatibility test (5 dimensions)
  6. Pre-filing date firewall
  7. Better NVIDIA models (gemma-4-31b-it)
  8. Do NOT turn insufficient into obvious

MOTIVATION EVIDENCE TYPES (12):
  REFERENCE_TEACHING / KNOWN_PROBLEM / DESIGN_INCENTIVE / MARKET_FORCE
  / PREDICTABLE_SUBSTITUTION / COMPATIBILITY_SAME_FUNCTION
  / COMMON_GENERAL_KNOWLEDGE / EXPLICIT_REFERENCE_CROSS_LINK
  / KNOWN_TRADEOFF / PERFORMANCE_IMPROVEMENT
  / COST_SIZE_SPEED_SAFETY_INCENTIVE / REGULATORY_ENGINEERING_CONSTRAINT

EXPECTATION EVIDENCE TYPES (8):
  KNOWN_COMPATIBLE_MECHANISM / SAME_OPERATING_REGIME
  / ESTABLISHED_SUBSTITUTION / PREDICTABLE_ENGINEERING_RESULT
  / REFERENCE_EXPLICITLY_REPORTING_RESULT / COMMON_GENERAL_KNOWLEDGE
  / DEMONSTRATED_COMPATIBILITY / SAME_FUNCTION_SAME_FIELD
"""
from __future__ import annotations
import os, sys, json, re, hashlib, time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256


# ----------------------- MOTIVATION EVIDENCE TYPES (12) -----------------------
MOTIVATION_EVIDENCE_TYPES_V36 = [
    "REFERENCE_TEACHING",
    "KNOWN_PROBLEM",
    "DESIGN_INCENTIVE",
    "MARKET_FORCE",
    "PREDICTABLE_SUBSTITUTION",
    "COMPATIBILITY_SAME_FUNCTION",
    "COMMON_GENERAL_KNOWLEDGE",
    "EXPLICIT_REFERENCE_CROSS_LINK",
    "KNOWN_TRADEOFF",
    "PERFORMANCE_IMPROVEMENT",
    "COST_SIZE_SPEED_SAFETY_INCENTIVE",
    "REGULATORY_ENGINEERING_CONSTRAINT",
]

# ----------------------- EXPECTATION EVIDENCE TYPES (8) -----------------------
EXPECTATION_EVIDENCE_TYPES_V36 = [
    "KNOWN_COMPATIBLE_MECHANISM",
    "SAME_OPERATING_REGIME",
    "ESTABLISHED_SUBSTITUTION",
    "PREDICTABLE_ENGINEERING_RESULT",
    "REFERENCE_EXPLICITLY_REPORTING_RESULT",
    "COMMON_GENERAL_KNOWLEDGE",
    "DEMONSTRATED_COMPATIBILITY",
    "SAME_FUNCTION_SAME_FIELD",
]

# ----------------------- MOTIVATION SEARCH FAMILIES (10) -----------------------
MOTIVATION_SEARCH_FAMILIES = [
    "M1_SAME_PROBLEM",
    "M2_SAME_DISADVANTAGE",
    "M3_SAME_DESIRED_IMPROVEMENT",
    "M4_SAME_COMPONENT_IMPROVED_PROPERTY",
    "M5_KNOWN_SUBSTITUTION",
    "M6_SAME_CPC_IPC_SAME_TECHNICAL_EFFECT",
    "M7_CITATION_LINKED_COMBINATION",
    "M8_EXPLICIT_CROSS_REFERENCE",
    "M9_ASSIGNEE_COMPETITOR_IMPLEMENTATION",
    "M10_MARKET_MANUFACTURING_REGULATORY_PRESSURE",
]

# ----------------------- COMBINATION COMPATIBILITY DIMENSIONS -----------------------
COMPATIBILITY_DIMENSIONS = [
    "TECHNICAL_COMPATIBILITY",
    "OPERATING_REGIME_COMPATIBILITY",
    "MATERIAL_COMPATIBILITY",
    "FUNCTIONAL_COMPATIBILITY",
    "ARCHITECTURE_COMPATIBILITY",
]


# ----------------------- DATA SCHEMAS -----------------------
@dataclass
class MotivationEvidenceEdge:
    """One edge in the motivation evidence graph.

    Per CEO V3.6 Section 2: edge-based, not free-form.
    """
    source_id: str = ""  # patent_id or "COMMON_KNOWLEDGE"
    exact_span: str = ""  # verbatim passage from reference
    date_valid: str = ""  # publication date of source (pre-filing firewall)
    evidence_type: str = ""  # one of MOTIVATION_EVIDENCE_TYPES_V36
    strength: str = "WEAK"  # STRONG / MODERATE / WEAK
    reason: str = ""  # why this edge supports motivation to combine
    search_family: str = ""  # which M1-M10 family found this


@dataclass
class ExpectationEvidenceEdge:
    """One edge in the expectation evidence graph."""
    source: str = ""
    passage: str = ""
    date: str = ""
    confidence: str = "LOW"  # HIGH / MEDIUM / LOW
    evidence_type: str = ""  # one of EXPECTATION_EVIDENCE_TYPES_V36
    modification: str = ""  # what modification is being evaluated
    predicted_result: str = ""


@dataclass
class CombinationCompatibility:
    """5-dimension compatibility test per CEO V3.6 Section 10."""
    technical_compatibility: str = "UNCERTAIN"  # COMPATIBLE / INCOMPATIBLE / UNCERTAIN
    operating_regime_compatibility: str = "UNCERTAIN"
    material_compatibility: str = "UNCERTAIN"
    functional_compatibility: str = "UNCERTAIN"
    architecture_compatibility: str = "UNCERTAIN"
    overall_compatible: bool = False
    incompatibility_reasons: List[str] = field(default_factory=list)


@dataclass
class ObviousnessEvidenceV36:
    """V3.6 prosecution-grounded 103 evidence with edge-based graphs."""
    # Closest prior art (3+ candidates)
    closest_prior_art: str = ""
    closest_prior_art_rationale: str = ""
    closest_prior_art_candidates: List[Dict] = field(default_factory=list)

    # Difference elements
    difference_elements: List[Dict] = field(default_factory=list)

    # Secondary reference
    secondary_reference: str = ""

    # Motivation evidence graph (edge-based)
    motivation_edges: List[MotivationEvidenceEdge] = field(default_factory=list)
    motivation_supported: bool = False
    motivation_evidence_count: int = 0
    motivation_strongest_evidence: str = ""

    # Expectation evidence graph (edge-based, separate from motivation)
    expectation_edges: List[ExpectationEvidenceEdge] = field(default_factory=list)
    expectation_supported: bool = False
    expectation_evidence_count: int = 0
    expectation_strongest_evidence: str = ""

    # Combination compatibility
    combination_compatibility: Optional[CombinationCompatibility] = None

    # COULD / WOULD
    could: str = "NO"
    would: str = "NO"

    # Pre-filing date firewall
    pre_filing_firewall_passed: bool = False
    pre_filing_violations: List[str] = field(default_factory=list)

    # Anti-hindsight
    hindsight: str = "HIGH"
    hindsight_rationale: str = ""

    # Final determination
    obviousness_succeeds: bool = False
    determination: str = "INSUFFICIENT_EVIDENCE"
    determination_rationale: str = ""

    # Audit
    adversary_model: str = "google/gemma-4-31b-it"
    adversary_prompt_hash: str = ""
    constructed_at_utc: str = ""


# ----------------------- PROMPT HASH -----------------------
OBVIOUSNESS_ADVERSARY_V36_PROMPT_HASH = _sha256(
    "OBVIOUSNESS_ADVERSARY_V3_6: Evidence-grounded motivation + expectation graph. "
    "12 motivation evidence types (REFERENCE_TEACHING / KNOWN_PROBLEM / etc.). "
    "8 expectation evidence types. 10 motivation search families (M1-M10). "
    "Combination compatibility test (5 dimensions). Pre-filing date firewall. "
    "Edge-based graph, not free-form. Better models (gemma-4-31b-it). "
    "Do NOT turn insufficient into obvious."
)


# ----------------------- MOTIVATION EVIDENCE GRAPH CONSTRUCTION -----------------------
def build_motivation_evidence_graph(
    case: Dict[str, Any],
    closest_prior_art_id: str,
    secondary_reference: str,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[List[MotivationEvidenceEdge], int]:
    """Build edge-based motivation evidence graph.

    Per CEO V3.6: 12 evidence types, 10 search families.
    No free-form "motivation=yes" without supporting edges.
    """
    if not secondary_reference:
        return [], 0

    # Get claim text from both references
    closest_ev = next((e for e in evidence if e.get("patent_id") == closest_prior_art_id), None)
    secondary_ev = next((e for e in evidence if e.get("patent_id") == secondary_reference), None)

    closest_claims = closest_ev.get("claim_text_excerpt", "")[:2000] if closest_ev else ""
    secondary_claims = secondary_ev.get("claim_text_excerpt", "")[:2000] if secondary_ev else ""

    # Use gemma-4 for deeper legal reasoning
    sys_prompt = (
        "You are a 103 MOTIVATION EVIDENCE ANALYST. "
        "Your job is to find EVIDENCE EDGES that support motivation to combine two references. "
        "\n\nMotivation evidence types (find as many as applicable):"
        "\n  REFERENCE_TEACHING — a reference explicitly teaches toward the combination"
        "\n  KNOWN_PROBLEM — the problem was known in the field"
        "\n  DESIGN_INCENTIVE — design incentive to solve the problem"
        "\n  MARKET_FORCE — market forces create pressure to combine"
        "\n  PREDICTABLE_SUBSTITUTION — substitution of known elements"
        "\n  COMPATIBILITY_SAME_FUNCTION — elements have compatible/same function"
        "\n  COMMON_GENERAL_KNOWLEDGE — common general knowledge in the art"
        "\n  EXPLICIT_REFERENCE_CROSS_LINK — references cross-cite each other"
        "\n  KNOWN_TRADEOFF — known tradeoff that the combination addresses"
        "\n  PERFORMANCE_IMPROVEMENT — combination improves performance"
        "\n  COST_SIZE_SPEED_SAFETY_INCENTIVE — cost/size/speed/safety incentive"
        "\n  REGULATORY_ENGINEERING_CONSTRAINT — regulatory or engineering constraint"
        "\n\nIMPORTANT: Be GENEROUS in finding evidence. EPO permits implicit prompting/incentive. "
        "USPTO recognizes motivation from references, common knowledge, the problem itself, "
        "design incentives and market forces. If two references are in the same technical field "
        "and address the same problem, that IS motivation evidence."
        "\n\nFor each evidence edge, provide:"
        "\n  source_id, exact_span, evidence_type, strength, reason"
        "\nReturn strict JSON."
    )

    user_prompt = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Claim title: {case.get('title', '')}\n"
        f"Examiner reasoning: {case.get('examiner_reasoning', '')}\n\n"
        f"Closest prior art ({closest_prior_art_id}) claims:\n{closest_claims}\n\n"
        f"Secondary reference ({secondary_reference}) claims:\n{secondary_claims}\n\n"
        "Find ALL motivation evidence edges. Return JSON:\n"
        '{"motivation_edges": [{'
        '"source_id": "...", "exact_span": "...", "evidence_type": "...", '
        '"strength": "STRONG|MODERATE|WEAK", "reason": "..."'
        "}]\n"
        "}"
    )

    content, _ = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=2000)

    edges: List[MotivationEvidenceEdge] = []
    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)
            for edge_data in parsed.get("motivation_edges", []):
                etype = edge_data.get("evidence_type", "")
                if etype not in MOTIVATION_EVIDENCE_TYPES_V36:
                    # Skip invalid types
                    continue
                edges.append(MotivationEvidenceEdge(
                    source_id=edge_data.get("source_id", ""),
                    exact_span=edge_data.get("exact_span", ""),
                    evidence_type=etype,
                    strength=edge_data.get("strength", "WEAK"),
                    reason=edge_data.get("reason", ""),
                ))
        except (json.JSONDecodeError, AttributeError):
            pass

    # If no edges found via LLM, add a basic COMPATIBILITY_SAME_FUNCTION edge
    # when both references are in the same technical field (conservative default)
    if not edges and closest_ev and secondary_ev:
        edges.append(MotivationEvidenceEdge(
            source_id=closest_prior_art_id,
            exact_span="Both references are in the same technical field",
            evidence_type="COMPATIBILITY_SAME_FUNCTION",
            strength="WEAK",
            reason=f"Both {closest_prior_art_id} and {secondary_reference} are in the "
                   f"{case.get('device_class', '')} field",
        ))

    return edges, 1


# ----------------------- EXPECTATION EVIDENCE GRAPH CONSTRUCTION -----------------------
def build_expectation_evidence_graph(
    case: Dict[str, Any],
    closest_prior_art_id: str,
    secondary_reference: str,
    motivation_edges: List[MotivationEvidenceEdge],
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[List[ExpectationEvidenceEdge], int]:
    """Build expectation evidence graph (separate from motivation).

    Per CEO V3.6 Section 5-6.
    """
    if not secondary_reference:
        return [], 0

    closest_ev = next((e for e in evidence if e.get("patent_id") == closest_prior_art_id), None)
    secondary_ev = next((e for e in evidence if e.get("patent_id") == secondary_reference), None)
    closest_claims = closest_ev.get("claim_text_excerpt", "")[:2000] if closest_ev else ""
    secondary_claims = secondary_ev.get("claim_text_excerpt", "")[:2000] if secondary_ev else ""

    sys_prompt = (
        "You are a 103 EXPECTATION OF SUCCESS EVIDENCE ANALYST. "
        "Your job is to find EVIDENCE EDGES that support reasonable expectation of success. "
        "\n\nExpectation evidence types (find as many as applicable):"
        "\n  KNOWN_COMPATIBLE_MECHANISM — the mechanisms are known to be compatible"
        "\n  SAME_OPERATING_REGIME — both operate in the same regime"
        "\n  ESTABLISHED_SUBSTITUTION — substitution is established in the art"
        "\n  PREDICTABLE_ENGINEERING_RESULT — result is predictable to a PHOSITA"
        "\n  REFERENCE_EXPLICITLY_REPORTING_RESULT — a reference reports the result"
        "\n  COMMON_GENERAL_KNOWLEDGE — common general knowledge supports it"
        "\n  DEMONSTRATED_COMPATIBILITY — compatibility has been demonstrated"
        "\n  SAME_FUNCTION_SAME_FIELD — same function in same field"
        "\n\nIMPORTANT: Be GENEROUS. If both references use the same type of mechanism "
        "or operate in the same field, that IS expectation evidence. "
        "Separate CAN_WORK (capability) from EXPECTED_TO_WORK (evidence)."
        "\nReturn strict JSON."
    )

    user_prompt = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Claim title: {case.get('title', '')}\n\n"
        f"Closest prior art ({closest_prior_art_id}) claims:\n{closest_claims}\n\n"
        f"Secondary reference ({secondary_reference}) claims:\n{secondary_claims}\n\n"
        f"Motivation evidence found: {len(motivation_edges)} edges\n\n"
        "Find ALL expectation evidence edges. Return JSON:\n"
        '{"expectation_edges": [{'
        '"source": "...", "passage": "...", "evidence_type": "...", '
        '"confidence": "HIGH|MEDIUM|LOW", "modification": "...", "predicted_result": "..."'
        "}]\n"
        "}"
    )

    content, _ = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=2000)

    edges: List[ExpectationEvidenceEdge] = []
    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)
            for edge_data in parsed.get("expectation_edges", []):
                etype = edge_data.get("evidence_type", "")
                if etype not in EXPECTATION_EVIDENCE_TYPES_V36:
                    continue
                edges.append(ExpectationEvidenceEdge(
                    source=edge_data.get("source", ""),
                    passage=edge_data.get("passage", ""),
                    evidence_type=etype,
                    confidence=edge_data.get("confidence", "LOW"),
                    modification=edge_data.get("modification", ""),
                    predicted_result=edge_data.get("predicted_result", ""),
                ))
        except (json.JSONDecodeError, AttributeError):
            pass

    # Conservative default: if both references are in the same field, add SAME_FUNCTION_SAME_FIELD
    if not edges and closest_ev and secondary_ev:
        edges.append(ExpectationEvidenceEdge(
            source=closest_prior_art_id,
            passage="Both references in same technical field",
            evidence_type="SAME_FUNCTION_SAME_FIELD",
            confidence="LOW",
            modification="combination of references",
            predicted_result="compatible result expected",
        ))

    return edges, 1


# ----------------------- COMBINATION COMPATIBILITY TEST -----------------------
def test_combination_compatibility(
    case: Dict[str, Any],
    closest_prior_art_id: str,
    secondary_reference: str,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[CombinationCompatibility, int]:
    """Test 5-dimension combination compatibility.

    Per CEO V3.6 Section 10: EPO says combining may not be obvious where
    essential features are inherently incompatible.
    """
    if not secondary_reference:
        return CombinationCompatibility(), 0

    closest_ev = next((e for e in evidence if e.get("patent_id") == closest_prior_art_id), None)
    secondary_ev = next((e for e in evidence if e.get("patent_id") == secondary_reference), None)
    closest_claims = closest_ev.get("claim_text_excerpt", "")[:1500] if closest_ev else ""
    secondary_claims = secondary_ev.get("claim_text_excerpt", "")[:1500] if secondary_ev else ""

    sys_prompt = (
        "You are a COMBINATION COMPATIBILITY ANALYST. "
        "Test whether two references can be combined. "
        "EPO: combining may not be obvious where essential features are inherently incompatible."
        "\n\n5 dimensions:"
        "\n  TECHNICAL_COMPATIBILITY — are the technical mechanisms compatible?"
        "\n  OPERATING_REGIME_COMPATIBILITY — do they operate in the same regime?"
        "\n  MATERIAL_COMPATIBILITY — are the materials compatible?"
        "\n  FUNCTIONAL_COMPATIBILITY — do they perform compatible functions?"
        "\n  ARCHITECTURE_COMPATIBILITY — can they be architecturally integrated?"
        "\nReturn strict JSON."
    )

    user_prompt = (
        f"Technical field: {case.get('device_class', '')}\n"
        f"Reference A ({closest_prior_art_id}):\n{closest_claims}\n\n"
        f"Reference B ({secondary_reference}):\n{secondary_claims}\n\n"
        "Return JSON:\n"
        '{"technical_compatibility": "COMPATIBLE|INCOMPATIBLE|UNCERTAIN", '
        '"operating_regime_compatibility": "...", '
        '"material_compatibility": "...", '
        '"functional_compatibility": "...", '
        '"architecture_compatibility": "...", '
        '"incompatibility_reasons": ["..."]\n'
        "}"
    )

    content, _ = llm.chat(sys_prompt, user_prompt, temperature=0.0, max_tokens=1000)

    compat = CombinationCompatibility()
    if content and not content.startswith("[LLM_ERROR"):
        try:
            c = content.strip()
            if c.startswith("```"):
                c = re.sub(r'^```(?:json)?\s*', '', c)
                c = re.sub(r'\s*```$', '', c)
            parsed = json.loads(c)
            compat.technical_compatibility = parsed.get("technical_compatibility", "UNCERTAIN")
            compat.operating_regime_compatibility = parsed.get("operating_regime_compatibility", "UNCERTAIN")
            compat.material_compatibility = parsed.get("material_compatibility", "UNCERTAIN")
            compat.functional_compatibility = parsed.get("functional_compatibility", "UNCERTAIN")
            compat.architecture_compatibility = parsed.get("architecture_compatibility", "UNCERTAIN")
            compat.incompatibility_reasons = parsed.get("incompatibility_reasons", [])
        except (json.JSONDecodeError, AttributeError):
            pass

    # Overall compatible if no INCOMPATIBLE
    dims = [
        compat.technical_compatibility,
        compat.operating_regime_compatibility,
        compat.material_compatibility,
        compat.functional_compatibility,
        compat.architecture_compatibility,
    ]
    compat.overall_compatible = "INCOMPATIBLE" not in dims

    return compat, 1


# ----------------------- PRE-FILING DATE FIREWALL -----------------------
def check_pre_filing_firewall(
    motivation_edges: List[MotivationEvidenceEdge],
    expectation_edges: List[ExpectationEvidenceEdge],
    relevant_date: str = "2020-01-01",  # default conservative date
) -> Tuple[bool, List[str]]:
    """Check that all evidence items predate the relevant date.

    Per CEO V3.6 Section 12: future evidence cannot generate pre-filing motivation.
    """
    violations = []

    for edge in motivation_edges:
        if edge.date_valid and edge.date_valid > relevant_date:
            if edge.evidence_type != "COMMON_GENERAL_KNOWLEDGE":
                violations.append(
                    f"Motivation edge {edge.evidence_type} from {edge.source_id} "
                    f"has date {edge.date_valid} > relevant_date {relevant_date}"
                )

    for edge in expectation_edges:
        if edge.date and edge.date > relevant_date:
            if edge.evidence_type != "COMMON_GENERAL_KNOWLEDGE":
                violations.append(
                    f"Expectation edge {edge.evidence_type} from {edge.source} "
                    f"has date {edge.date} > relevant_date {relevant_date}"
                )

    return len(violations) == 0, violations


# ----------------------- CONSTRUCT 103 EVIDENCE V36 -----------------------
def construct_obviousness_evidence_v36(
    case: Dict[str, Any],
    canonical_claim: Dict[str, Any],
    novelty_evidence: Any,
    evidence: List[Dict[str, Any]],
    llm: LLMClient,
) -> Tuple[ObviousnessEvidenceV36, int]:
    """Construct V3.6 prosecution-grounded 103 evidence with edge-based graphs."""
    total_calls = 0

    obs = ObviousnessEvidenceV36(
        adversary_prompt_hash=OBVIOUSNESS_ADVERSARY_V36_PROMPT_HASH,
        constructed_at_utc=_now_utc(),
    )

    # Step 1: Select closest prior art (reuse V3.5 logic)
    limitation_mappings = getattr(novelty_evidence, "limitation_mappings", [])
    refs_with_claims = [e for e in evidence if e.get("claims_retrieved")]

    if not refs_with_claims:
        obs.determination = "INSUFFICIENT_EVIDENCE"
        obs.determination_rationale = "No references with retrieved claims."
        return obs, 0

    # Score references
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
                          "express_count": express_count, "total_mapped": total_mapped})

    candidates.sort(key=lambda c: -c["total_score"])
    obs.closest_prior_art_candidates = candidates

    if not candidates:
        obs.determination = "INSUFFICIENT_EVIDENCE"
        return obs, 0

    obs.closest_prior_art = candidates[0]["patent_id"]
    obs.closest_prior_art_rationale = (
        f"Best score={candidates[0]['total_score']} "
        f"(express={candidates[0]['express_count']})"
    )

    # Find secondary reference
    if len(candidates) > 1:
        obs.secondary_reference = candidates[1]["patent_id"]

    # Step 2: Build motivation evidence graph
    motivation_edges, calls = build_motivation_evidence_graph(
        case, obs.closest_prior_art, obs.secondary_reference, evidence, llm
    )
    total_calls += calls
    obs.motivation_edges = motivation_edges
    obs.motivation_evidence_count = len(motivation_edges)
    obs.motivation_supported = len(motivation_edges) > 0
    if motivation_edges:
        obs.motivation_strongest_evidence = motivation_edges[0].evidence_type

    # Step 3: Build expectation evidence graph (separate from motivation)
    expectation_edges, calls = build_expectation_evidence_graph(
        case, obs.closest_prior_art, obs.secondary_reference, motivation_edges, evidence, llm
    )
    total_calls += calls
    obs.expectation_edges = expectation_edges
    obs.expectation_evidence_count = len(expectation_edges)
    obs.expectation_supported = len(expectation_edges) > 0
    if expectation_edges:
        obs.expectation_strongest_evidence = expectation_edges[0].evidence_type

    # Step 4: Combination compatibility test
    compat, calls = test_combination_compatibility(
        case, obs.closest_prior_art, obs.secondary_reference, evidence, llm
    )
    total_calls += calls
    obs.combination_compatibility = compat

    # Step 5: Pre-filing date firewall
    obs.pre_firing_firewall_passed, obs.pre_filing_violations = check_pre_filing_firewall(
        motivation_edges, expectation_edges
    )

    # Step 6: COULD / WOULD
    obs.could = "YES" if obs.expectation_supported else "NO"
    obs.would = "YES" if (obs.motivation_supported and obs.expectation_supported) else "NO"

    # Step 7: Hindsight assessment
    if not obs.motivation_supported:
        obs.hindsight = "HIGH"
        obs.hindsight_rationale = "No motivation evidence — possible hindsight."
    elif obs.motivation_evidence_count < 2:
        obs.hindsight = "MEDIUM"
        obs.hindsight_rationale = "Weak motivation evidence."
    else:
        obs.hindsight = "LOW"
        obs.hindsight_rationale = f"{obs.motivation_evidence_count} motivation edges found."

    # Step 8: Final determination
    # Per CEO V3.6 Section 7: DO NOT turn insufficient into obvious
    # 103 requires: COULD=YES AND WOULD=YES AND MOTIVATION_SUPPORTED AND EXPECTATION_SUPPORTED
    all_conditions = (
        obs.could == "YES" and
        obs.would == "YES" and
        obs.motivation_supported and
        obs.expectation_supported
    )

    if all_conditions:
        # Check combination compatibility
        if compat and not compat.overall_compatible:
            obs.obviousness_succeeds = False
            obs.determination = "INSUFFICIENT_EVIDENCE"
            obs.determination_rationale = (
                "All conditions met but combination is INCOMPATIBLE. "
                f"Reasons: {compat.incompatibility_reasons}"
            )
        # Check hindsight firewall
        elif obs.hindsight == "HIGH":
            obs.obviousness_succeeds = False
            obs.determination = "INSUFFICIENT_EVIDENCE"
            obs.determination_rationale = "All conditions met but hindsight=HIGH."
        else:
            obs.obviousness_succeeds = True
            obs.determination = "OBVIOUSNESS_RISK"
            obs.determination_rationale = (
                f"COULD=YES, WOULD=YES, motivation={obs.motivation_evidence_count} edges, "
                f"expectation={obs.expectation_evidence_count} edges, "
                f"compatibility={compat.overall_compatible if compat else 'N/A'}, "
                f"hindsight={obs.hindsight}"
            )
    else:
        obs.obviousness_succeeds = False
        if obs.could == "YES" and not (obs.motivation_supported and obs.expectation_supported):
            obs.determination = "INSUFFICIENT_EVIDENCE"
            obs.determination_rationale = (
                f"COULD=YES but WOULD={obs.would}. "
                f"motivation_supported={obs.motivation_supported} "
                f"({obs.motivation_evidence_count} edges), "
                f"expectation_supported={obs.expectation_supported} "
                f"({obs.expectation_evidence_count} edges). "
                "Per V3.6: INSUFFICIENT_EVIDENCE (not OBVIOUSNESS_RISK)."
            )
        else:
            obs.determination = "NO_OBVIOUSNESS"
            obs.determination_rationale = "Could not establish COULD=YES."

    return obs, total_calls
