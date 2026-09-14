"""
AUTONOMOUS CALIBRATION V3.3 — Fixed Pipeline
==============================================

V3.3 fixes:
  1. CLAIM_IDENTITY_VALIDATION — prevent cross-patent contamination
  2. 103 rebuild with explicit evidence object + COULD≠WOULD + two-pass anti-hindsight
  3. Search recall audit

Per CEO V3.3 protocol.
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

from archive.r455_retired.discovery_fabric.prior_art_v2.calibration_v2 import CALIBRATION_CASES_V2
from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256
from discovery_fabric.prior_art_v2.patsnap_claims import fetch_patsnap_claims
from discovery_fabric.prior_art_v2.patsnap_discovery import (
    patsnap_claim_data,
)
from discovery_fabric.prior_art_v2.source_failover import (
    patsnap_search_count,
)
from archive.r455_retired.discovery_fabric.prior_art_v2.calibration_v3 import (
    CanonicalClaim, SearchFamilyAttempt, RetrievedPatentEvidence,
    ElementMapping, NoveltyResult, FinalAdjudication,
    stage_canonical_claim, stage_search_families, stage_claim_retrieval,
    stage_novelty_102, stage_final_adjudication,
    build_case_ground_truth, MIN_FAMILIES_ATTEMPTED,
    FAILURE_STATES, FAILURE_SUBSTATES, FAMILY_COLLAPSE_MODES, DEFAULT_FAMILY_MODE,
    PIPELINE_ROLES, ROLE_PROMPT_HASHES, THRESHOLDS,
    MODEL_GENERATOR, MODEL_NOVELTY, MODEL_OBVIOUSNESS, MODEL_ADJUDICATOR,
    GENERATOR_PROMPT_HASH, NOVELTY_PROMPT_HASH, ADJUDICATOR_PROMPT_HASH,
    PREDICTED_OUTCOMES, PREDICTED_TIERS,
)
from discovery_fabric.prior_art_v2.claim_identity import (
    validate_claim_identity, IdentityValidationResult,
    IDENTITY_CONFIRMED, IDENTITY_MISMATCH, IDENTITY_UNRESOLVED,
    EVIDENCE_CORRUPTED, should_stop_case,
)
from discovery_fabric.prior_art_v2.obviousness_v33 import (
    ObviousnessEvidenceV33, construct_obviousness_evidence,
    OBVIOUSNESS_ADVERSARY_PROMPT_HASH,
)


# V3.3 error categories (expanded per CEO Section 16)
ERROR_CATEGORIES_V33 = [
    "CLAIM_IDENTITY_FAILURE",
    "CLAIM_INTERPRETATION_FAILURE",
    "SEARCH_FAILURE",
    "102_FAILURE",
    "103_FAILURE",
    "HINDSIGHT_FAILURE",
    "MODEL_JUDGMENT_FAILURE",
    "GROUND_TRUTH_FAILURE",
    "EVIDENCE_FAILURE",
    "CORRECT",
]


@dataclass
class CaseResultV33:
    """Full V3.3 result for one case."""
    case_id: str
    patent_number: str
    title: str
    device_class: str
    ground_truth_label: str
    ground_truth_disposition: str

    # Identity validation
    identity_validation: Optional[Dict[str, Any]] = None
    identity_state: str = IDENTITY_UNRESOLVED

    # Pipeline stages
    canonical_claim: Optional[Dict[str, Any]] = None
    search_families: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = field(default_factory=list)
    element_mappings: List[Dict[str, Any]] = field(default_factory=list)
    novelty_results: List[Dict[str, Any]] = field(default_factory=list)
    obviousness_result: Optional[Dict[str, Any]] = None
    final_adjudication: Optional[Dict[str, Any]] = None

    # Cited-art recall
    cited_art_expected: List[str] = field(default_factory=list)
    cited_art_found: List[str] = field(default_factory=list)
    cited_art_recall: float = 0.0

    # Search recall
    families_attempted: int = 0
    families_succeeded: int = 0
    search_sufficient: bool = False

    # Comparison to ground truth
    predicted_tier: str = "SEARCH_INSUFFICIENT"
    predicted_outcome: str = "INSUFFICIENT_EVIDENCE"
    correct: bool = False
    error_type: str = "INSUFFICIENT_EVIDENCE"
    error_category: str = "SEARCH_FAILURE"

    # Rescue (amended cases)
    rescue_recognized: Optional[bool] = None

    # Audit
    llm_calls: int = 0
    role_log: List[Dict[str, str]] = field(default_factory=list)


# ============================================================
# V3.3 PIPELINE STAGES
# ============================================================
def run_v33_case(case: dict, llm: LLMClient) -> CaseResultV33:
    """Run the full V3.3 pipeline on one case."""
    case_id = case["case_id"]
    patent_number = case["patent_number"]
    print(f"\n=== {case_id} — {patent_number} — {case.get('title','')[:60]} ===")

    cited_art = case.get("prior_art_cited", [])

    result = CaseResultV33(
        case_id=case_id,
        patent_number=patent_number,
        title=case.get("title", ""),
        device_class=case.get("device_class", ""),
        ground_truth_label=case.get("ground_truth_label", "UNKNOWN"),
        ground_truth_disposition=case.get("ground_truth_disposition", "UNKNOWN"),
        cited_art_expected=list(cited_art),
    )

    role_log = []

    # STAGE 1: CANONICAL CLAIM (GENERATOR role)
    print(f"  [1/7] GENERATOR: canonical claim...")
    canonical, calls = stage_canonical_claim(case, llm)
    result.llm_calls += calls
    role_log.append({
        "role": "GENERATOR",
        "model": MODEL_GENERATOR,
        "prompt_hash": GENERATOR_PROMPT_HASH,
        "llm_calls": calls,
    })

    # STAGE 2: 14 SEARCH FAMILIES (SEARCHER role)
    print(f"  [2/7] SEARCHER: 14 families...")
    families, patent_ids = stage_search_families(case, canonical, cited_art)
    result.families_attempted = sum(1 for f in families if f.attempted)
    result.families_succeeded = sum(1 for f in families if f.failure_state in
                                    ("SUCCESS", "SEARCH_RETURNED_PATENTS",
                                     "SEARCH_RETURNED_NO_RESULTS", "CLAIMS_RETRIEVED"))
    result.search_sufficient = result.families_attempted >= MIN_FAMILIES_ATTEMPTED

    # STAGE 3: ACTUAL CLAIM RETRIEVAL
    print(f"  [3/7] Claim retrieval: {len(patent_ids)} patents...")
    evidence, calls = stage_claim_retrieval(patent_ids, cited_art)
    result.llm_calls += calls
    if cited_art:
        found = [e.patent_id for e in evidence if e.is_cited_art and e.claims_retrieved]
        result.cited_art_found = found
        result.cited_art_recall = len(found) / len(cited_art) if cited_art else 1.0
    else:
        result.cited_art_recall = 1.0

    # STAGE 4: CLAIM IDENTITY VALIDATION (NEW in V3.3)
    print(f"  [4/7] CLAIM_IDENTITY_VALIDATION...")
    # Find the case patent's retrieved evidence
    case_evidence = next((e for e in evidence if e.patent_id == patent_number), None)
    if case_evidence and case_evidence.claims_retrieved:
        identity_result = validate_claim_identity(
            case=case,
            retrieved_patent_number=case_evidence.patent_id,
            retrieved_title=case.get("title", ""),  # PatSnap doesn't return title in claim-data
            retrieved_claims=case_evidence.claim_text_excerpt.split(" || ") if case_evidence.claim_text_excerpt else [],
            retrieved_assignee="",
            retrieved_priority_date="",
        )
        result.identity_validation = asdict(identity_result)
        result.identity_state = identity_result.state

        if should_stop_case(identity_result):
            # IDENTITY_MISMATCH — STOP CASE per CEO Section 2
            print(f"  -> IDENTITY_MISMATCH: {identity_result.mismatch_reasons}")
            result.predicted_tier = "EVIDENCE_CORRUPTED"
            result.predicted_outcome = "EVIDENCE_CORRUPTED"
            result.error_type = "CLAIM_IDENTITY_FAILURE"
            result.error_category = "CLAIM_IDENTITY_FAILURE"
            result.final_adjudication = {
                "predicted_outcome": "EVIDENCE_CORRUPTED",
                "predicted_tier": "EVIDENCE_CORRUPTED",
                "adjudicator_rationale": (
                    f"CLAIM_IDENTITY_MISMATCH: {identity_result.mismatch_reasons}. "
                    "Case STOPPED per CEO V3.3 Section 2. "
                    "102/103/commercial/rescue NOT run."
                ),
                "claim_only_path_taken": False,
                "evidence_path_complete": False,
            }
            return result
    else:
        # No claims retrieved — can't validate identity
        result.identity_state = IDENTITY_UNRESOLVED
        result.identity_validation = {
            "state": IDENTITY_UNRESOLVED,
            "mismatch_reasons": ["No claims retrieved for case patent — cannot validate identity"],
        }

    # STAGE 5: ELEMENT MAPPING + 102 (NOVELTY_ADVERSARY role)
    print(f"  [5/7] NOVELTY_ADVERSARY: 102...")
    element_mappings, novelty_results, calls = stage_novelty_102(
        case, canonical, evidence, llm
    )
    result.llm_calls += calls
    role_log.append({
        "role": "NOVELTY_ADVERSARY",
        "model": MODEL_NOVELTY,
        "prompt_hash": NOVELTY_PROMPT_HASH,
        "llm_calls": calls,
    })

    # STAGE 6: 103 (OBVIOUSNESS_ADVERSARY V3.3 — REBUILT)
    print(f"  [6/7] OBVIOUSNESS_ADVERSARY_V3.3: 103 (explicit evidence object)...")
    obviousness, calls = construct_obviousness_evidence(
        case=case,
        canonical_claim={
            "patent_number": canonical.patent_number,
            "limitations": canonical.limitations,
        },
        novelty_results=[asdict(nr) for nr in novelty_results],
        evidence=[asdict(e) for e in evidence],
        llm=llm,
    )
    result.llm_calls += calls
    role_log.append({
        "role": "OBVIOUSNESS_ADVERSARY_V3_3",
        "model": "meta/llama-3.1-8b-instruct",
        "prompt_hash": OBVIOUSNESS_ADVERSARY_PROMPT_HASH,
        "llm_calls": calls,
    })

    # STAGE 7: FINAL ADJUDICATION
    print(f"  [7/7] FINAL_ADJUDICATOR...")
    adjudication, calls = stage_final_adjudication(
        case, canonical, families, evidence, novelty_results, obviousness, llm
    )
    result.llm_calls += calls
    role_log.append({
        "role": "FINAL_ADJUDICATOR",
        "model": MODEL_ADJUDICATOR,
        "prompt_hash": ADJUDICATOR_PROMPT_HASH,
        "llm_calls": calls,
    })

    # Populate result
    result.canonical_claim = _serialize_claim(canonical)
    result.search_families = [_serialize_family(f) for f in families]
    result.retrieved_evidence = [_serialize_evidence(e) for e in evidence]
    result.element_mappings = [_serialize_em(em) for em in element_mappings]
    result.novelty_results = [_serialize_novelty(nr) for nr in novelty_results]
    result.obviousness_result = asdict(obviousness)
    result.final_adjudication = _serialize_adjudication(adjudication)
    result.predicted_tier = adjudication.predicted_tier
    result.predicted_outcome = adjudication.predicted_outcome
    result.role_log = role_log

    # Rescue recognition (amended cases)
    if result.ground_truth_label == "AMENDED":
        result.rescue_recognized = (
            adjudication.predicted_tier in ("PROMISING", "STRONG", "ELITE")
            and case.get("amendments_made", False)
        )

    # Compare to ground truth + categorize error
    _compare_to_ground_truth(result, case)

    print(f"  -> tier={result.predicted_tier} outcome={result.predicted_outcome} "
          f"gt={result.ground_truth_label} correct={result.correct} err={result.error_type}")
    return result


def _compare_to_ground_truth(result: CaseResultV33, case: dict):
    """Compare prediction to ground truth and categorize error."""
    gt = result.ground_truth_label
    pred = result.predicted_tier

    if pred in ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED"):
        result.correct = False
        if pred == "EVIDENCE_CORRUPTED":
            result.error_type = "CLAIM_IDENTITY_FAILURE"
            result.error_category = "CLAIM_IDENTITY_FAILURE"
        elif pred == "SOURCE_UNAVAILABLE":
            result.error_type = "SOURCE_UNAVAILABLE"
            result.error_category = "SEARCH_FAILURE"
        else:
            result.error_type = "INSUFFICIENT_EVIDENCE"
            result.error_category = "SEARCH_FAILURE"
        return

    if gt == "SURVIVED":
        result.correct = pred in ("STRONG", "ELITE", "PROMISING")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
        result.error_category = "CORRECT" if result.correct else _categorize_false_reject(result, case)
    elif gt == "REJECTED":
        result.correct = pred == "REJECT"
        result.error_type = "CORRECT" if result.correct else (
            "FALSE_ELITE" if pred in ("STRONG", "ELITE") else "MODEL_JUDGMENT_FAILURE"
        )
        result.error_category = "CORRECT" if result.correct else _categorize_false_elite(result, case)
    elif gt == "AMENDED":
        result.correct = pred in ("PROMISING", "STRONG", "ELITE")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
        result.error_category = "CORRECT" if result.correct else _categorize_false_reject(result, case)
    else:
        result.correct = False
        result.error_type = "GROUND_TRUTH_FAILURE"
        result.error_category = "GROUND_TRUTH_FAILURE"


def _categorize_false_reject(result: CaseResultV33, case: dict) -> str:
    """Categorize the cause of a false reject."""
    # Check 102 first
    if any(nr.get("anticipation_succeeds") for nr in result.novelty_results):
        return "102_FAILURE"
    # Check 103
    if result.obviousness_result and result.obviousness_result.get("obviousness_succeeds"):
        # Was it hindsight?
        if result.obviousness_result.get("hindsight_risk") == "HIGH":
            return "HINDSIGHT_FAILURE"
        return "103_FAILURE"
    # Check identity
    if result.identity_state == IDENTITY_UNRESOLVED:
        return "CLAIM_IDENTITY_FAILURE"
    return "MODEL_JUDGMENT_FAILURE"


def _categorize_false_elite(result: CaseResultV33, case: dict) -> str:
    """Categorize the cause of a false elite."""
    # Check identity first
    if result.identity_state == IDENTITY_MISMATCH:
        return "CLAIM_IDENTITY_FAILURE"
    if result.identity_state == IDENTITY_UNRESOLVED:
        return "CLAIM_IDENTITY_FAILURE"
    # Check if 102 missed an anticipation
    if case.get("had_102_rejection") and not any(nr.get("anticipation_succeeds") for nr in result.novelty_results):
        return "102_FAILURE"
    # Check if 103 missed obviousness
    if case.get("had_103_rejection") and result.obviousness_result and not result.obviousness_result.get("obviousness_succeeds"):
        return "103_FAILURE"
    return "MODEL_JUDGMENT_FAILURE"


# ============================================================
# SERIALIZATION HELPERS
# ============================================================
def _serialize_claim(c: CanonicalClaim) -> dict:
    return {
        "patent_number": c.patent_number,
        "raw_claim_text": c.raw_claim_text[:2000],
        "claim_hash": c.claim_hash,
        "independent_claims_count": len(c.independent_claims),
        "limitations": c.limitations,
        "relationships": c.relationships,
        "technical_field": c.technical_field,
        "generator_model": c.generator_model,
        "generator_prompt_hash": c.generator_prompt_hash,
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
        "http_status": getattr(f, "http_status", 0),
        "api_status": getattr(f, "api_status", False),
        "api_error_code": getattr(f, "api_error_code", 0),
        "api_error_msg": getattr(f, "api_error_msg", ""),
        "patents_returned": f.patents_returned,
        "family_collapse": getattr(f, "family_collapse", "DOCDB"),
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


def _serialize_em(em: ElementMapping) -> dict:
    return {
        "patent_id": em.patent_id,
        "limitation_id": em.limitation_id,
        "disclosure_type": em.disclosure_type,
        "exact_passage": em.exact_passage,
        "evidence_level": em.evidence_level,
    }


def _serialize_novelty(nr: NoveltyResult) -> dict:
    return {
        "patent_id": nr.patent_id,
        "all_limitations_found": nr.all_limitations_found,
        "limitations_found": nr.limitations_found,
        "limitations_missing": nr.limitations_missing,
        "arrangement_disclosed": nr.arrangement_disclosed,
        "anticipation_succeeds": nr.anticipation_succeeds,
        "rationale": nr.rationale,
    }


def _serialize_adjudication(adj: FinalAdjudication) -> dict:
    return {
        "predicted_outcome": adj.predicted_outcome,
        "predicted_tier": adj.predicted_tier,
        "adjudicator_rationale": adj.adjudicator_rationale,
        "adjudicator_model": adj.adjudicator_model,
        "adjudicator_prompt_hash": adj.adjudicator_prompt_hash,
        "evidence_path_complete": adj.evidence_path_complete,
        "claim_only_path_taken": adj.claim_only_path_taken,
    }


# ============================================================
# METRICS V3.3
# ============================================================
def calculate_v33_metrics(results: List[CaseResultV33]) -> dict:
    """Calculate V3.3 metrics including 102/103 accuracy."""
    total = len(results)
    if total == 0:
        return {"error": "no results"}

    # Count by status
    evidence_corrupted = sum(1 for r in results if r.predicted_tier == "EVIDENCE_CORRUPTED")
    insufficient = sum(1 for r in results if r.predicted_tier == "SEARCH_INSUFFICIENT")
    source_unavailable = sum(1 for r in results if r.predicted_tier == "SOURCE_UNAVAILABLE")
    unable_to_adjudicate = evidence_corrupted + insufficient + source_unavailable
    sufficient = total - unable_to_adjudicate

    # Correct predictions
    correct = sum(1 for r in results if r.correct and r.predicted_tier not in
                  ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED"))

    # False elite / false reject
    false_elite = 0
    false_reject = 0
    for r in results:
        gt = r.ground_truth_label
        pred = r.predicted_tier
        if pred in ("STRONG", "ELITE") and gt == "REJECTED":
            false_elite += 1
        if pred == "REJECT" and gt in ("SURVIVED", "AMENDED"):
            false_reject += 1

    accuracy = correct / max(1, sufficient) if sufficient > 0 else 0.0
    false_elite_rate = false_elite / max(1, sufficient) if sufficient > 0 else 0.0
    false_reject_rate = false_reject / max(1, sufficient) if sufficient > 0 else 0.0

    # Cited-art recall
    cited_cases = [r for r in results if r.cited_art_expected]
    cited_found = sum(1 for r in cited_cases if r.cited_art_recall >= 0.5)
    cited_art_recall = cited_found / max(1, len(cited_cases)) if cited_cases else 1.0

    # Search recall
    total_families_attempted = sum(r.families_attempted for r in results)
    total_families_succeeded = sum(r.families_succeeded for r in results)
    search_recall = total_families_succeeded / max(1, total_families_attempted)

    # 102 accuracy
    cases_with_102 = [
        r for r in results
        if r.novelty_results and r.predicted_tier not in
        ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED")
    ]
    correct_102 = 0
    total_102 = 0
    for r in cases_with_102:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None:
            continue
        had_102 = case.get("had_102_rejection", False)
        predicted_102 = any(nr.get("anticipation_succeeds") for nr in r.novelty_results)
        if had_102 == predicted_102:
            correct_102 += 1
        total_102 += 1
    accuracy_102 = correct_102 / max(1, total_102) if total_102 > 0 else 0.0

    # 103 accuracy
    correct_103 = 0
    total_103 = 0
    for r in cases_with_102:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None or not r.obviousness_result:
            continue
        had_103 = case.get("had_103_rejection", False)
        predicted_103 = r.obviousness_result.get("obviousness_succeeds", False)
        if had_103 == predicted_103:
            correct_103 += 1
        total_103 += 1
    accuracy_103 = correct_103 / max(1, total_103) if total_103 > 0 else 0.0

    # Hindsight metrics
    hindsight_high = sum(1 for r in results if r.obviousness_result and
                         r.obviousness_result.get("hindsight_risk") == "HIGH")
    hindsight_medium = sum(1 for r in results if r.obviousness_result and
                           r.obviousness_result.get("hindsight_risk") == "MEDIUM")
    hindsight_low = sum(1 for r in results if r.obviousness_result and
                        r.obviousness_result.get("hindsight_risk") == "LOW")

    # Identity validation metrics
    identity_confirmed = sum(1 for r in results if r.identity_state == IDENTITY_CONFIRMED)
    identity_mismatch = sum(1 for r in results if r.identity_state == IDENTITY_MISMATCH)
    identity_unresolved = sum(1 for r in results if r.identity_state == IDENTITY_UNRESOLVED)

    # Rescue recognition
    amended_cases = [r for r in results if r.ground_truth_label == "AMENDED"]
    rescue_correct = sum(1 for r in amended_cases if r.rescue_recognized == True)
    rescue_recognition_accuracy = rescue_correct / max(1, len(amended_cases)) if amended_cases else 0.0

    # Elite precision/recall
    elite_predictions = sum(1 for r in results if r.predicted_tier in ("ELITE", "STRONG"))
    elite_correct = sum(1 for r in results if r.predicted_tier in ("ELITE", "STRONG")
                       and r.ground_truth_label == "SURVIVED")
    elite_precision = elite_correct / max(1, elite_predictions) if elite_predictions > 0 else 0.0
    elite_recall = elite_correct / max(1, sum(1 for r in results if r.ground_truth_label == "SURVIVED"))

    passes_threshold = (
        accuracy >= THRESHOLDS["overall_accuracy_min"] and
        false_elite_rate <= THRESHOLDS["false_elite_rate_max"] and
        false_reject_rate <= THRESHOLDS["false_reject_rate_max"] and
        cited_art_recall >= THRESHOLDS["cited_art_recall_min"] and
        search_recall >= THRESHOLDS["search_recall_min"] and
        accuracy_102 >= 0.85 and
        accuracy_103 >= 0.80
    )

    return {
        "total_cases": total,
        "sufficient_evidence_cases": sufficient,
        "evidence_corrupted_count": evidence_corrupted,
        "insufficient_evidence_count": insufficient,
        "source_unavailable_count": source_unavailable,
        "unable_to_adjudicate_count": unable_to_adjudicate,
        "correct_predictions": correct,
        "overall_accuracy": round(accuracy, 4),
        "false_elite_count": false_elite,
        "false_elite_rate": round(false_elite_rate, 4),
        "false_reject_count": false_reject,
        "false_reject_rate": round(false_reject_rate, 4),
        "cited_art_recall": round(cited_art_recall, 4),
        "cited_art_cases": len(cited_cases),
        "cited_art_found": cited_found,
        "search_recall": round(search_recall, 4),
        "102_accuracy": round(accuracy_102, 4),
        "103_accuracy": round(accuracy_103, 4),
        "hindsight_high": hindsight_high,
        "hindsight_medium": hindsight_medium,
        "hindsight_low": hindsight_low,
        "identity_confirmed": identity_confirmed,
        "identity_mismatch": identity_mismatch,
        "identity_unresolved": identity_unresolved,
        "rescue_recognition_accuracy": round(rescue_recognition_accuracy, 4),
        "elite_precision": round(elite_precision, 4),
        "elite_recall": round(elite_recall, 4),
        "passes_threshold": passes_threshold,
        "thresholds": {**THRESHOLDS, "102_accuracy_min": 0.85, "103_accuracy_min": 0.80},
        "status": "UNBLOCK_50_TO_5" if passes_threshold else "CALIBRATION_BLOCKED",
    }
