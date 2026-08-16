"""
AUTONOMOUS CALIBRATION V3.4 — Passage-Grounded 102 + Independent 103
=====================================================================

Per CEO V3.4 protocol.
"""
from __future__ import annotations
import os, sys, json, time, hashlib, re
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.calibration_v2 import CALIBRATION_CASES_V2
from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256
from discovery_fabric.prior_art_v2.patsnap_claims import fetch_patsnap_claims
from discovery_fabric.prior_art_v2.calibration_v3 import (
    CanonicalClaim, SearchFamilyAttempt, RetrievedPatentEvidence,
    stage_canonical_claim, stage_search_families, stage_claim_retrieval,
    build_case_ground_truth, MIN_FAMILIES_ATTEMPTED,
    PIPELINE_ROLES, ROLE_PROMPT_HASHES, THRESHOLDS,
    MODEL_GENERATOR, MODEL_NOVELTY, MODEL_ADJUDICATOR,
    GENERATOR_PROMPT_HASH, NOVELTY_PROMPT_HASH, ADJUDICATOR_PROMPT_HASH,
)
from discovery_fabric.prior_art_v2.claim_identity import (
    validate_claim_identity, IDENTITY_CONFIRMED, IDENTITY_MISMATCH, IDENTITY_UNRESOLVED,
    should_stop_case,
)
from discovery_fabric.prior_art_v2.novelty_v34 import (
    NoveltyEvidenceV34, LimitationMapping, RelationshipMapping,
    construct_novelty_evidence_v34, is_102_kill_legal,
    NOVELTY_ADVERSARY_V34_PROMPT_HASH,
    ALLOWED_DISCLOSURE_TYPES, FORBIDDEN_DISCLOSURE_TYPES, VALID_KILL_MAPPING_TYPES,
    DISCLOSURE_EXPRESS, DISCLOSURE_NECESSARILY_INHERENT,
    DISCLOSURE_NOT_DISCLOSED, DISCLOSURE_UNCERTAIN,
)
from discovery_fabric.prior_art_v2.obviousness_v34 import (
    ObviousnessEvidenceV34, construct_obviousness_evidence_v34,
    OBVIOUSNESS_ADVERSARY_V34_PROMPT_HASH,
)


# V3.4 error categories
ERROR_CATEGORIES_V34 = [
    "CLAIM_IDENTITY_FAILURE",
    "CLAIM_INTERPRETATION_FAILURE",
    "SEARCH_FAILURE",
    "102_FAILURE",
    "103_FAILURE",
    "HINDSIGHT_FAILURE",
    "MODEL_JUDGMENT_FAILURE",
    "GROUND_TRUTH_FAILURE",
    "EVIDENCE_FAILURE",
    "ELEMENT_OVERCLAIM",
    "ARRANGEMENT_OVERCLAIM",
    "INHERENCY_ERROR",
    "REFERENCE_MISMATCH",
    "LLM_JUDGMENT_ERROR",
    "CORRECT",
]


@dataclass
class CaseResultV34:
    """Full V3.4 result for one case."""
    case_id: str
    patent_number: str
    title: str
    device_class: str
    ground_truth_label: str
    ground_truth_disposition: str

    # Identity validation
    identity_state: str = IDENTITY_UNRESOLVED
    identity_validation: Optional[Dict[str, Any]] = None

    # Pipeline stages
    canonical_claim: Optional[Dict[str, Any]] = None
    search_families: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = field(default_factory=list)
    novelty_evidence: Optional[Dict[str, Any]] = None  # NoveltyEvidenceV34
    obviousness_evidence: Optional[Dict[str, Any]] = None  # ObviousnessEvidenceV34
    final_adjudication: Optional[Dict[str, Any]] = None

    # Cited-art recall + mapping
    cited_art_expected: List[str] = field(default_factory=list)
    cited_art_found: List[str] = field(default_factory=list)
    cited_art_recall: float = 0.0
    cited_art_mapping_accuracy: float = 0.0  # NEW in V3.4

    # Search recall
    families_attempted: int = 0
    families_succeeded: int = 0

    # Comparison to ground truth
    predicted_tier: str = "SEARCH_INSUFFICIENT"
    predicted_outcome: str = "INSUFFICIENT_EVIDENCE"
    correct: bool = False
    error_type: str = "INSUFFICIENT_EVIDENCE"
    error_category: str = "SEARCH_FAILURE"

    # Rescue
    rescue_recognized: Optional[bool] = None

    # Audit
    llm_calls: int = 0
    role_log: List[Dict[str, str]] = field(default_factory=list)


# ============================================================
# V3.4 PIPELINE
# ============================================================
def run_v34_case(case: dict, llm: LLMClient) -> CaseResultV34:
    """Run the full V3.4 pipeline on one case."""
    case_id = case["case_id"]
    patent_number = case["patent_number"]
    print(f"\n=== {case_id} — {patent_number} — {case.get('title','')[:60]} ===")

    cited_art = case.get("prior_art_cited", [])

    result = CaseResultV34(
        case_id=case_id,
        patent_number=patent_number,
        title=case.get("title", ""),
        device_class=case.get("device_class", ""),
        ground_truth_label=case.get("ground_truth_label", "UNKNOWN"),
        ground_truth_disposition=case.get("ground_truth_disposition", "UNKNOWN"),
        cited_art_expected=list(cited_art),
    )

    role_log = []

    # STAGE 1: CANONICAL CLAIM (GENERATOR)
    print(f"  [1/6] GENERATOR: canonical claim...")
    canonical, calls = stage_canonical_claim(case, llm)
    result.llm_calls += calls
    role_log.append({"role": "GENERATOR", "model": MODEL_GENERATOR,
                     "prompt_hash": GENERATOR_PROMPT_HASH, "llm_calls": calls})

    # STAGE 2: SEARCH FAMILIES
    print(f"  [2/6] SEARCHER: 14 families...")
    families, patent_ids = stage_search_families(case, canonical, cited_art)
    result.families_attempted = sum(1 for f in families if f.attempted)
    result.families_succeeded = sum(1 for f in families if f.failure_state in
                                    ("SUCCESS", "SEARCH_RETURNED_PATENTS",
                                     "SEARCH_RETURNED_NO_RESULTS", "CLAIMS_RETRIEVED"))

    # STAGE 3: CLAIM RETRIEVAL
    print(f"  [3/6] Claim retrieval: {len(patent_ids)} patents...")
    evidence, calls = stage_claim_retrieval(patent_ids, cited_art)
    result.llm_calls += calls
    if cited_art:
        found = [e.patent_id for e in evidence if e.is_cited_art and e.claims_retrieved]
        result.cited_art_found = found
        result.cited_art_recall = len(found) / len(cited_art) if cited_art else 1.0
        # Cited-art mapping accuracy: for each found cited art, check if it has a limitation mapping
        result.cited_art_mapping_accuracy = result.cited_art_recall  # will be refined after 102
    else:
        result.cited_art_recall = 1.0
        result.cited_art_mapping_accuracy = 1.0

    # STAGE 3.5: CLAIM IDENTITY VALIDATION
    case_evidence = next((e for e in evidence if e.patent_id == patent_number), None)
    if case_evidence and case_evidence.claims_retrieved:
        identity_result = validate_claim_identity(
            case=case,
            retrieved_patent_number=case_evidence.patent_id,
            retrieved_title=case.get("title", ""),
            retrieved_claims=case_evidence.claim_text_excerpt.split(" || ") if case_evidence.claim_text_excerpt else [],
        )
        result.identity_validation = asdict(identity_result)
        result.identity_state = identity_result.state
        if should_stop_case(identity_result):
            result.predicted_tier = "EVIDENCE_CORRUPTED"
            result.predicted_outcome = "EVIDENCE_CORRUPTED"
            result.error_type = "CLAIM_IDENTITY_FAILURE"
            result.error_category = "CLAIM_IDENTITY_FAILURE"
            result.final_adjudication = {
                "predicted_outcome": "EVIDENCE_CORRUPTED",
                "predicted_tier": "EVIDENCE_CORRUPTED",
                "adjudicator_rationale": f"CLAIM_IDENTITY_MISMATCH: {identity_result.mismatch_reasons}",
                "claim_only_path_taken": False,
                "evidence_path_complete": False,
            }
            return result
    else:
        result.identity_state = IDENTITY_UNRESOLVED

    # STAGE 4: NOVELTY V3.4 (passage-grounded 102)
    print(f"  [4/6] NOVELTY_ADVERSARY_V3.4: passage-grounded 102...")
    novelty, calls = construct_novelty_evidence_v34(
        case=case,
        canonical_claim={
            "patent_number": canonical.patent_number,
            "limitations": canonical.limitations,
        },
        evidence=[asdict(e) for e in evidence],
        llm=llm,
    )
    result.llm_calls += calls
    role_log.append({"role": "NOVELTY_ADVERSARY_V3_4", "model": "meta/llama-3.1-8b-instruct",
                     "prompt_hash": NOVELTY_ADVERSARY_V34_PROMPT_HASH, "llm_calls": calls})

    # STAGE 5: OBVIOUSNESS V3.4 (independent 103)
    print(f"  [5/6] OBVIOUSNESS_ADVERSARY_V3.4: independent 103...")
    obviousness, calls = construct_obviousness_evidence_v34(
        case=case,
        canonical_claim={
            "patent_number": canonical.patent_number,
            "limitations": canonical.limitations,
        },
        novelty_evidence=novelty,
        evidence=[asdict(e) for e in evidence],
        llm=llm,
    )
    result.llm_calls += calls
    role_log.append({"role": "OBVIOUSNESS_ADVERSARY_V3_4", "model": "meta/llama-3.1-8b-instruct",
                     "prompt_hash": OBVIOUSNESS_ADVERSARY_V34_PROMPT_HASH, "llm_calls": calls})

    # STAGE 6: FINAL ADJUDICATION
    print(f"  [6/6] FINAL_ADJUDICATOR...")
    adjudication = _adjudicate_v34(novelty, obviousness, evidence)
    result.llm_calls += 0  # no LLM call — deterministic

    # Populate result
    result.canonical_claim = _serialize_claim(canonical)
    result.search_families = [_serialize_family(f) for f in families]
    result.retrieved_evidence = [_serialize_evidence(e) for e in evidence]
    result.novelty_evidence = asdict(novelty)
    result.obviousness_evidence = asdict(obviousness)
    result.final_adjudication = adjudication
    result.predicted_tier = adjudication["predicted_tier"]
    result.predicted_outcome = adjudication["predicted_outcome"]
    result.role_log = role_log

    # Refine cited-art mapping accuracy based on 102 mappings
    if cited_art and result.cited_art_found:
        mapped_count = 0
        for cited in result.cited_art_found:
            # Check if cited art has any limitation mapping in novelty evidence
            has_mapping = any(
                lm.get("reference_id") == cited and lm.get("disclosure_type") in
                ("EXPRESS", "NECESSARILY_INHERENT", "NOT_DISCLOSED", "UNCERTAIN")
                for lm in novelty.limitation_mappings
            )
            if has_mapping:
                mapped_count += 1
        result.cited_art_mapping_accuracy = mapped_count / len(cited_art) if cited_art else 0.0

    # Rescue recognition
    if result.ground_truth_label == "AMENDED":
        result.rescue_recognized = (
            adjudication["predicted_tier"] in ("PROMISING", "STRONG", "ELITE")
            and case.get("amendments_made", False)
        )

    # Compare to ground truth
    _compare_to_ground_truth(result, case, novelty, obviousness)

    print(f"  -> tier={result.predicted_tier} outcome={result.predicted_outcome} "
          f"gt={result.ground_truth_label} correct={result.correct} err={result.error_type}")
    return result


def _adjudicate_v34(
    novelty: NoveltyEvidenceV34,
    obviousness: ObviousnessEvidenceV34,
    evidence: List[RetrievedPatentEvidence],
) -> Dict[str, Any]:
    """V3.4 final adjudication — deterministic based on 102/103 evidence."""
    claims_retrieved_count = sum(1 for e in evidence if e.claims_retrieved)

    if claims_retrieved_count == 0:
        return {
            "predicted_outcome": "INSUFFICIENT_EVIDENCE",
            "predicted_tier": "SEARCH_INSUFFICIENT",
            "adjudicator_rationale": "No claims retrieved — cannot adjudicate.",
            "claim_only_path_taken": False,
            "evidence_path_complete": False,
        }

    # 102 result — only legal if kill_legal=TRUE
    anticipation_succeeds = is_102_kill_legal(novelty)

    # 103 result
    obviousness_succeeds = obviousness.obviousness_succeeds

    if anticipation_succeeds:
        return {
            "predicted_outcome": "NOVELTY_FAILS",
            "predicted_tier": "REJECT",
            "adjudicator_rationale": (
                "102_KILL legal: all_limitations_mapped=TRUE, all_relationships_mapped=TRUE, "
                "all_mapping_types in {EXPRESS, NECESSARILY_INHERENT}, uncertainty_count=0."
            ),
            "claim_only_path_taken": False,
            "evidence_path_complete": True,
            "102_result": novelty.final_result,
            "103_result": "not_evaluated",
        }
    elif obviousness_succeeds:
        return {
            "predicted_outcome": "OBVIOUSNESS_RISK",
            "predicted_tier": "REJECT",
            "adjudicator_rationale": (
                "103 OBVIOUSNESS_RISK: COULD=YES AND WOULD=YES AND "
                "MOTIVATION_SUPPORTED=TRUE AND EXPECTED_SUCCESS_SUPPORTED=TRUE."
            ),
            "claim_only_path_taken": False,
            "evidence_path_complete": True,
            "102_result": novelty.final_result,
            "103_result": obviousness.determination,
        }
    else:
        gold_count = claims_retrieved_count
        hindsight = obviousness.hindsight
        if gold_count >= 3 and hindsight == "LOW":
            return {
                "predicted_outcome": "STRONG",
                "predicted_tier": "STRONG",
                "adjudicator_rationale": (
                    f"Survived 102+103 with {gold_count} GOLD patents and LOW hindsight."
                ),
                "claim_only_path_taken": False,
                "evidence_path_complete": True,
                "102_result": novelty.final_result,
                "103_result": obviousness.determination,
            }
        else:
            return {
                "predicted_outcome": "NOVELTY_SURVIVES",
                "predicted_tier": "PROMISING",
                "adjudicator_rationale": (
                    f"Survived 102+103. gold_count={gold_count}, hindsight={hindsight}. "
                    f"103 determination: {obviousness.determination}."
                ),
                "claim_only_path_taken": False,
                "evidence_path_complete": True,
                "102_result": novelty.final_result,
                "103_result": obviousness.determination,
            }


def _compare_to_ground_truth(
    result: CaseResultV34,
    case: dict,
    novelty: NoveltyEvidenceV34,
    obviousness: ObviousnessEvidenceV34,
):
    """Compare prediction to ground truth and categorize error."""
    gt = result.ground_truth_label
    pred = result.predicted_tier

    if pred in ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED"):
        result.correct = False
        if pred == "EVIDENCE_CORRUPTED":
            result.error_type = "CLAIM_IDENTITY_FAILURE"
            result.error_category = "CLAIM_IDENTITY_FAILURE"
        else:
            result.error_type = "INSUFFICIENT_EVIDENCE"
            result.error_category = "SEARCH_FAILURE"
        return

    if gt == "SURVIVED":
        result.correct = pred in ("STRONG", "ELITE", "PROMISING")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
        result.error_category = "CORRECT" if result.correct else _categorize_false_reject_v34(
            result, case, novelty, obviousness
        )
    elif gt == "REJECTED":
        result.correct = pred == "REJECT"
        result.error_type = "CORRECT" if result.correct else (
            "FALSE_ELITE" if pred in ("STRONG", "ELITE") else "MODEL_JUDGMENT_FAILURE"
        )
        result.error_category = "CORRECT" if result.correct else _categorize_false_elite_v34(
            result, case, novelty, obviousness
        )
    elif gt == "AMENDED":
        result.correct = pred in ("PROMISING", "STRONG", "ELITE")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
        result.error_category = "CORRECT" if result.correct else _categorize_false_reject_v34(
            result, case, novelty, obviousness
        )
    else:
        result.correct = False
        result.error_type = "GROUND_TRUTH_FAILURE"
        result.error_category = "GROUND_TRUTH_FAILURE"


def _categorize_false_reject_v34(
    result: CaseResultV34,
    case: dict,
    novelty: NoveltyEvidenceV34,
    obviousness: ObviousnessEvidenceV34,
) -> str:
    """Categorize the cause of a false reject (V3.4)."""
    # Check 102 first — was 102_KILL issued?
    if novelty.final_result == "102_KILL":
        # 102 killed a granted patent — forensic classification
        # Check if it was element overclaim, arrangement overclaim, or inherency error
        # Look at the limitation mappings for issues
        has_inherency = any(
            lm.disclosure_type == "NECESSARILY_INHERENT"
            for lm in novelty.limitation_mappings
        )
        has_uncertain = any(
            lm.disclosure_type == "UNCERTAIN"
            for lm in novelty.limitation_mappings
        )
        if has_inherency and not all(
            lm.inherency_necessity_proof for lm in novelty.limitation_mappings
            if lm.disclosure_type == "NECESSARILY_INHERENT"
        ):
            return "INHERENCY_ERROR"
        if not novelty.arrangement_supported:
            return "ARRANGEMENT_OVERCLAIM"
        if has_uncertain:
            return "ELEMENT_OVERCLAIM"
        return "LLM_JUDGMENT_ERROR"

    # Check 103
    if obviousness.obviousness_succeeds:
        if obviousness.hindsight == "HIGH":
            return "HINDSIGHT_FAILURE"
        return "103_FAILURE"

    return "MODEL_JUDGMENT_FAILURE"


def _categorize_false_elite_v34(
    result: CaseResultV34,
    case: dict,
    novelty: NoveltyEvidenceV34,
    obviousness: ObviousnessEvidenceV34,
) -> str:
    """Categorize the cause of a false elite (V3.4)."""
    # Check identity
    if result.identity_state == IDENTITY_MISMATCH:
        return "CLAIM_IDENTITY_FAILURE"
    if result.identity_state == IDENTITY_UNRESOLVED:
        return "CLAIM_IDENTITY_FAILURE"

    # Check if 102 missed an anticipation
    if case.get("had_102_rejection") and novelty.final_result != "102_KILL":
        return "102_FAILURE"

    # Check if 103 missed obviousness
    if case.get("had_103_rejection") and not obviousness.obviousness_succeeds:
        return "103_FAILURE"

    return "MODEL_JUDGMENT_FAILURE"


# ============================================================
# SERIALIZATION
# ============================================================
def _serialize_claim(c: CanonicalClaim) -> dict:
    return {
        "patent_number": c.patent_number,
        "raw_claim_text": c.raw_claim_text[:2000],
        "claim_hash": c.claim_hash,
        "limitations": c.limitations,
        "relationships": c.relationships,
        "technical_field": c.technical_field,
    }


def _serialize_family(f: SearchFamilyAttempt) -> dict:
    return {
        "family_id": f.family_id,
        "attempted": f.attempted,
        "source": f.source,
        "query": f.query,
        "results_count": f.results_count,
        "failure_state": f.failure_state,
        "failure_substate": getattr(f, "failure_substate", "NONE"),
        "patents_returned": f.patents_returned,
    }


def _serialize_evidence(e: RetrievedPatentEvidence) -> dict:
    return {
        "patent_id": e.patent_id,
        "source": e.source,
        "claims_retrieved": e.claims_retrieved,
        "claim_count": e.claim_count,
        "claim_text_excerpt": e.claim_text_excerpt[:1500],
        "content_hash": e.content_hash,
        "is_cited_art": e.is_cited_art,
    }


# ============================================================
# METRICS V3.4
# ============================================================
def calculate_v34_metrics(results: List[CaseResultV34]) -> dict:
    """Calculate V3.4 metrics including 102/103 accuracy + cited-art mapping."""
    total = len(results)
    if total == 0:
        return {"error": "no results"}

    evidence_corrupted = sum(1 for r in results if r.predicted_tier == "EVIDENCE_CORRUPTED")
    insufficient = sum(1 for r in results if r.predicted_tier == "SEARCH_INSUFFICIENT")
    source_unavailable = sum(1 for r in results if r.predicted_tier == "SOURCE_UNAVAILABLE")
    unable = evidence_corrupted + insufficient + source_unavailable
    sufficient = total - unable

    correct = sum(1 for r in results if r.correct and r.predicted_tier not in
                  ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED"))

    false_elite = sum(1 for r in results if r.predicted_tier in ("STRONG", "ELITE")
                     and r.ground_truth_label == "REJECTED")
    false_reject = sum(1 for r in results if r.predicted_tier == "REJECT"
                      and r.ground_truth_label in ("SURVIVED", "AMENDED"))

    accuracy = correct / max(1, sufficient) if sufficient > 0 else 0.0
    false_elite_rate = false_elite / max(1, sufficient) if sufficient > 0 else 0.0
    false_reject_rate = false_reject / max(1, sufficient) if sufficient > 0 else 0.0

    # Cited-art recall + mapping accuracy
    cited_cases = [r for r in results if r.cited_art_expected]
    cited_found = sum(1 for r in cited_cases if r.cited_art_recall >= 0.5)
    cited_art_recall = cited_found / max(1, len(cited_cases)) if cited_cases else 1.0

    cited_mapping_correct = sum(1 for r in cited_cases if r.cited_art_mapping_accuracy >= 0.5)
    cited_art_mapping_accuracy = cited_mapping_correct / max(1, len(cited_cases)) if cited_cases else 1.0

    # Search recall
    total_attempted = sum(r.families_attempted for r in results)
    total_succeeded = sum(r.families_succeeded for r in results)
    search_recall = total_succeeded / max(1, total_attempted)

    # 102 accuracy
    cases_with_102 = [
        r for r in results
        if r.novelty_evidence and r.predicted_tier not in
        ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED")
    ]
    correct_102 = 0
    total_102 = 0
    for r in cases_with_102:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None:
            continue
        had_102 = case.get("had_102_rejection", False)
        predicted_102 = r.novelty_evidence.get("final_result") == "102_KILL"
        if had_102 == predicted_102:
            correct_102 += 1
        total_102 += 1
    accuracy_102 = correct_102 / max(1, total_102) if total_102 > 0 else 0.0

    # 103 accuracy
    correct_103 = 0
    total_103 = 0
    for r in cases_with_102:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None or not r.obviousness_evidence:
            continue
        had_103 = case.get("had_103_rejection", False)
        predicted_103 = r.obviousness_evidence.get("obviousness_succeeds", False)
        if had_103 == predicted_103:
            correct_103 += 1
        total_103 += 1
    accuracy_103 = correct_103 / max(1, total_103) if total_103 > 0 else 0.0

    # Hindsight
    hindsight_high = sum(1 for r in results if r.obviousness_evidence and
                         r.obviousness_evidence.get("hindsight") == "HIGH")
    hindsight_medium = sum(1 for r in results if r.obviousness_evidence and
                           r.obviousness_evidence.get("hindsight") == "MEDIUM")
    hindsight_low = sum(1 for r in results if r.obviousness_evidence and
                        r.obviousness_evidence.get("hindsight") == "LOW")

    # Identity
    identity_confirmed = sum(1 for r in results if r.identity_state == IDENTITY_CONFIRMED)
    identity_mismatch = sum(1 for r in results if r.identity_state == IDENTITY_MISMATCH)

    # Rescue
    amended = [r for r in results if r.ground_truth_label == "AMENDED"]
    rescue_correct = sum(1 for r in amended if r.rescue_recognized == True)
    rescue_acc = rescue_correct / max(1, len(amended)) if amended else 0.0

    # 102 kill legal count
    kill_legal_count = sum(1 for r in results if r.novelty_evidence and
                           r.novelty_evidence.get("kill_legal"))

    passes = (
        accuracy >= 0.85 and
        false_elite_rate <= 0.10 and
        false_reject_rate <= 0.10 and
        cited_art_recall >= 0.90 and
        search_recall >= 0.80 and
        accuracy_102 >= 0.85 and
        accuracy_103 >= 0.80
    )

    return {
        "total_cases": total,
        "sufficient_evidence_cases": sufficient,
        "evidence_corrupted_count": evidence_corrupted,
        "unable_to_adjudicate_count": unable,
        "correct_predictions": correct,
        "overall_accuracy": round(accuracy, 4),
        "false_elite_count": false_elite,
        "false_elite_rate": round(false_elite_rate, 4),
        "false_reject_count": false_reject,
        "false_reject_rate": round(false_reject_rate, 4),
        "cited_art_recall": round(cited_art_recall, 4),
        "cited_art_mapping_accuracy": round(cited_art_mapping_accuracy, 4),
        "search_recall": round(search_recall, 4),
        "102_accuracy": round(accuracy_102, 4),
        "103_accuracy": round(accuracy_103, 4),
        "hindsight_high": hindsight_high,
        "hindsight_medium": hindsight_medium,
        "hindsight_low": hindsight_low,
        "identity_confirmed": identity_confirmed,
        "identity_mismatch": identity_mismatch,
        "rescue_recognition_accuracy": round(rescue_acc, 4),
        "kill_legal_count": kill_legal_count,
        "passes_threshold": passes,
        "thresholds": {**THRESHOLDS, "102_accuracy_min": 0.85, "103_accuracy_min": 0.80},
        "status": "UNBLOCK_50_TO_5" if passes else "CALIBRATION_BLOCKED",
    }
