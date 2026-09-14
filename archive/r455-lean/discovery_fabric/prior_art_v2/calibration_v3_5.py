"""
AUTONOMOUS CALIBRATION V3.5 — Prosecution-Grounded 103 Forensics
==================================================================

Per CEO V3.5 protocol.
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
from archive.r455_retired.discovery_fabric.prior_art_v2.calibration_v3 import (
    stage_canonical_claim, stage_search_families, stage_claim_retrieval,
    build_case_ground_truth, MIN_FAMILIES_ATTEMPTED,
    PIPELINE_ROLES, ROLE_PROMPT_HASHES, THRESHOLDS,
    MODEL_GENERATOR, MODEL_NOVELTY, MODEL_ADJUDICATOR,
    GENERATOR_PROMPT_HASH, NOVELTY_PROMPT_HASH, ADJUDICATOR_PROMPT_HASH,
    CanonicalClaim, SearchFamilyAttempt, RetrievedPatentEvidence,
)
from discovery_fabric.prior_art_v2.claim_identity import (
    validate_claim_identity, IDENTITY_CONFIRMED, IDENTITY_MISMATCH, IDENTITY_UNRESOLVED,
    should_stop_case,
)
from discovery_fabric.prior_art_v2.novelty_v34 import (
    construct_novelty_evidence_v34, is_102_kill_legal,
    NOVELTY_ADVERSARY_V34_PROMPT_HASH,
)
from discovery_fabric.prior_art_v2.obviousness_v35 import (
    ObviousnessEvidenceV35, construct_obviousness_evidence_v35,
    compare_examiner_vs_system, classify_103_error_v35,
    OBVIOUSNESS_ADVERSARY_V35_PROMPT_HASH,
    ExaminerGroundTruth, ERROR_CATEGORIES_V35,
    MOTIVATION_SOURCES, EXPECTATION_SOURCES,
)


@dataclass
class CaseResultV35:
    """Full V3.5 result for one case."""
    case_id: str
    patent_number: str
    title: str
    device_class: str
    ground_truth_label: str
    ground_truth_disposition: str

    # Identity
    identity_state: str = IDENTITY_UNRESOLVED

    # Pipeline
    canonical_claim: Optional[Dict[str, Any]] = None
    search_families: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = field(default_factory=list)
    novelty_evidence: Optional[Dict[str, Any]] = None
    obviousness_evidence: Optional[Dict[str, Any]] = None
    examiner_ground_truth: Optional[Dict[str, Any]] = None
    forensic_comparison: Optional[Dict[str, Any]] = None
    final_adjudication: Optional[Dict[str, Any]] = None

    # Cited-art
    cited_art_expected: List[str] = field(default_factory=list)
    cited_art_found: List[str] = field(default_factory=list)
    cited_art_recall: float = 0.0
    cited_103_art_recall: float = 0.0  # NEW: 103-specific cited art recall

    # Search
    families_attempted: int = 0
    families_succeeded: int = 0

    # Comparison
    predicted_tier: str = "SEARCH_INSUFFICIENT"
    predicted_outcome: str = "INSUFFICIENT_EVIDENCE"
    correct: bool = False
    error_type: str = "INSUFFICIENT_EVIDENCE"
    error_category: str = "SEARCH_FAILURE"
    error_103_classification: str = ""  # V3.5 specific

    # Rescue
    rescue_recognized: Optional[bool] = None

    # Audit
    llm_calls: int = 0
    role_log: List[Dict[str, str]] = field(default_factory=list)


def run_v35_case(case: dict, llm: LLMClient) -> CaseResultV35:
    """Run V3.5 pipeline on one case."""
    case_id = case["case_id"]
    patent_number = case["patent_number"]
    print(f"\n=== {case_id} — {patent_number} — {case.get('title','')[:60]} ===")

    cited_art = case.get("prior_art_cited", [])

    result = CaseResultV35(
        case_id=case_id,
        patent_number=patent_number,
        title=case.get("title", ""),
        device_class=case.get("device_class", ""),
        ground_truth_label=case.get("ground_truth_label", "UNKNOWN"),
        ground_truth_disposition=case.get("ground_truth_disposition", "UNKNOWN"),
        cited_art_expected=list(cited_art),
    )

    role_log = []

    # STAGE 1: GENERATOR
    print(f"  [1/7] GENERATOR...")
    canonical, calls = stage_canonical_claim(case, llm)
    result.llm_calls += calls
    role_log.append({"role": "GENERATOR", "model": MODEL_GENERATOR, "llm_calls": calls})

    # STAGE 2: SEARCHER
    print(f"  [2/7] SEARCHER...")
    families, patent_ids = stage_search_families(case, canonical, cited_art)
    result.families_attempted = sum(1 for f in families if f.attempted)
    result.families_succeeded = sum(1 for f in families if f.failure_state in
                                    ("SUCCESS", "SEARCH_RETURNED_PATENTS",
                                     "SEARCH_RETURNED_NO_RESULTS", "CLAIMS_RETRIEVED"))

    # STAGE 3: CLAIM RETRIEVAL
    print(f"  [3/7] CLAIM_RETRIEVAL...")
    evidence, calls = stage_claim_retrieval(patent_ids, cited_art)
    result.llm_calls += calls
    if cited_art:
        found = [e.patent_id for e in evidence if e.is_cited_art and e.claims_retrieved]
        result.cited_art_found = found
        result.cited_art_recall = len(found) / len(cited_art)
        # 103-specific cited art: cited art that's relevant to 103 (had_103_rejection)
        if case.get("had_103_rejection"):
            result.cited_103_art_recall = result.cited_art_recall
        else:
            result.cited_103_art_recall = 1.0  # N/A if no 103 rejection
    else:
        result.cited_art_recall = 1.0
        result.cited_103_art_recall = 1.0

    # STAGE 3.5: IDENTITY VALIDATION
    case_evidence = next((e for e in evidence if e.patent_id == patent_number), None)
    if case_evidence and case_evidence.claims_retrieved:
        identity_result = validate_claim_identity(
            case=case,
            retrieved_patent_number=case_evidence.patent_id,
            retrieved_title=case.get("title", ""),
            retrieved_claims=case_evidence.claim_text_excerpt.split(" || ") if case_evidence.claim_text_excerpt else [],
        )
        result.identity_state = identity_result.state
        if should_stop_case(identity_result):
            result.predicted_tier = "EVIDENCE_CORRUPTED"
            result.error_type = "CLAIM_IDENTITY_FAILURE"
            result.error_category = "CLAIM_IDENTITY_FAILURE"
            return result
    else:
        result.identity_state = IDENTITY_UNRESOLVED

    # STAGE 4: NOVELTY V3.4 (passage-grounded 102)
    print(f"  [4/7] NOVELTY_ADVERSARY_V3.4...")
    novelty, calls = construct_novelty_evidence_v34(
        case=case,
        canonical_claim={"patent_number": canonical.patent_number, "limitations": canonical.limitations},
        evidence=[asdict(e) for e in evidence],
        llm=llm,
    )
    result.llm_calls += calls
    role_log.append({"role": "NOVELTY_ADVERSARY_V3_4", "model": "meta/llama-3.1-8b-instruct", "llm_calls": calls})

    # STAGE 5: OBVIOUSNESS V3.5 (prosecution-grounded 103)
    print(f"  [5/7] OBVIOUSNESS_ADVERSARY_V3.5 (prosecution-grounded)...")
    obviousness, calls, examiner_gt = construct_obviousness_evidence_v35(
        case=case,
        canonical_claim={"patent_number": canonical.patent_number, "limitations": canonical.limitations},
        novelty_evidence=novelty,
        evidence=[asdict(e) for e in evidence],
        llm=llm,
    )
    result.llm_calls += calls
    role_log.append({"role": "OBVIOUSNESS_ADVERSARY_V3_5", "model": "meta/llama-3.1-8b-instruct", "llm_calls": calls})

    # STAGE 6: FORENSIC COMPARISON (examiner vs system)
    print(f"  [6/7] FORENSIC_COMPARISON...")
    forensic = compare_examiner_vs_system(examiner_gt, obviousness, case)
    result.forensic_comparison = forensic
    result.examiner_ground_truth = asdict(examiner_gt)

    # STAGE 7: FINAL ADJUDICATION
    print(f"  [7/7] FINAL_ADJUDICATOR...")
    adjudication = _adjudicate_v35(novelty, obviousness, evidence)

    # Populate result
    result.canonical_claim = {
        "patent_number": canonical.patent_number,
        "limitations": canonical.limitations,
    }
    result.search_families = [{"family_id": f.family_id, "failure_state": f.failure_state} for f in families]
    result.retrieved_evidence = [{"patent_id": e.patent_id, "claims_retrieved": e.claims_retrieved} for e in evidence]
    result.novelty_evidence = asdict(novelty)
    result.obviousness_evidence = asdict(obviousness)
    result.final_adjudication = adjudication
    result.predicted_tier = adjudication["predicted_tier"]
    result.predicted_outcome = adjudication["predicted_outcome"]
    result.role_log = role_log

    # Rescue
    if result.ground_truth_label == "AMENDED":
        result.rescue_recognized = (
            adjudication["predicted_tier"] in ("PROMISING", "STRONG", "ELITE")
            and case.get("amendments_made", False)
        )

    # Compare to ground truth
    _compare_to_ground_truth_v35(result, case, novelty, obviousness, examiner_gt)

    print(f"  -> tier={result.predicted_tier} gt={result.ground_truth_label} "
          f"correct={result.correct} err={result.error_type} 103_class={result.error_103_classification}")
    return result


def _adjudicate_v35(novelty, obviousness, evidence) -> Dict[str, Any]:
    """V3.5 final adjudication."""
    claims_count = sum(1 for e in evidence if e.claims_retrieved)

    if claims_count == 0:
        return {
            "predicted_outcome": "INSUFFICIENT_EVIDENCE",
            "predicted_tier": "SEARCH_INSUFFICIENT",
            "adjudicator_rationale": "No claims retrieved.",
            "claim_only_path_taken": False,
            "evidence_path_complete": False,
        }

    anticipation = is_102_kill_legal(novelty)
    obviousness_succeeds = obviousness.obviousness_succeeds

    if anticipation:
        return {
            "predicted_outcome": "NOVELTY_FAILS", "predicted_tier": "REJECT",
            "adjudicator_rationale": "102_KILL legal.",
            "claim_only_path_taken": False, "evidence_path_complete": True,
        }
    elif obviousness_succeeds:
        return {
            "predicted_outcome": "OBVIOUSNESS_RISK", "predicted_tier": "REJECT",
            "adjudicator_rationale": f"103: {obviousness.determination_rationale}",
            "claim_only_path_taken": False, "evidence_path_complete": True,
        }
    else:
        gold = claims_count
        hindsight = obviousness.hindsight
        if gold >= 3 and hindsight == "LOW":
            return {
                "predicted_outcome": "STRONG", "predicted_tier": "STRONG",
                "adjudicator_rationale": f"Survived 102+103. gold={gold}, hindsight={hindsight}.",
                "claim_only_path_taken": False, "evidence_path_complete": True,
            }
        else:
            return {
                "predicted_outcome": "NOVELTY_SURVIVES", "predicted_tier": "PROMISING",
                "adjudicator_rationale": f"Survived 102+103. gold={gold}, hindsight={hindsight}. 103: {obviousness.determination}",
                "claim_only_path_taken": False, "evidence_path_complete": True,
            }


def _compare_to_ground_truth_v35(result, case, novelty, obviousness, examiner_gt):
    """Compare and classify error."""
    gt = result.ground_truth_label
    pred = result.predicted_tier

    if pred in ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED"):
        result.correct = False
        result.error_type = "INSUFFICIENT_EVIDENCE"
        result.error_category = "SEARCH_FAILURE"
        return

    if gt == "SURVIVED":
        result.correct = pred in ("STRONG", "ELITE", "PROMISING")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
        result.error_category = "CORRECT" if result.correct else "FINAL_ADJUDICATION_FAILURE"
    elif gt == "REJECTED":
        result.correct = pred == "REJECT"
        result.error_type = "CORRECT" if result.correct else (
            "FALSE_ELITE" if pred in ("STRONG", "ELITE") else "MODEL_JUDGMENT_FAILURE"
        )
        result.error_category = "CORRECT" if result.correct else "FINAL_ADJUDICATION_FAILURE"
    elif gt == "AMENDED":
        result.correct = pred in ("PROMISING", "STRONG", "ELITE")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
        result.error_category = "CORRECT" if result.correct else "FINAL_ADJUDICATION_FAILURE"

    # V3.5 specific 103 error classification
    result.error_103_classification = classify_103_error_v35(
        case, examiner_gt, obviousness, result.correct
    )


def calculate_v35_metrics(results: List[CaseResultV35]) -> dict:
    """Calculate V3.5 metrics."""
    total = len(results)
    if total == 0:
        return {"error": "no results"}

    unable = sum(1 for r in results if r.predicted_tier in
                 ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED"))
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

    # Cited-art recall
    cited_cases = [r for r in results if r.cited_art_expected]
    cited_found = sum(1 for r in cited_cases if r.cited_art_recall >= 0.5)
    cited_art_recall = cited_found / max(1, len(cited_cases)) if cited_cases else 1.0

    # 103-specific cited art recall
    cited_103_cases = [r for r in results if r.cited_art_expected and r.ground_truth_label == "REJECTED"]
    cited_103_found = sum(1 for r in cited_103_cases if r.cited_103_art_recall >= 0.5)
    cited_103_art_recall = cited_103_found / max(1, len(cited_103_cases)) if cited_103_cases else 1.0

    # Search recall
    total_attempted = sum(r.families_attempted for r in results)
    total_succeeded = sum(r.families_succeeded for r in results)
    search_recall = total_succeeded / max(1, total_attempted)

    # 102 accuracy
    cases_with_102 = [r for r in results if r.novelty_evidence and r.predicted_tier not in
                      ("SEARCH_INSUFFICIENT", "SOURCE_UNAVAILABLE", "EVIDENCE_CORRUPTED")]
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

    # 103 error classification summary
    error_103_summary = {}
    for r in results:
        if r.error_103_classification and r.error_103_classification != "CORRECT":
            error_103_summary[r.error_103_classification] = error_103_summary.get(r.error_103_classification, 0) + 1

    # Hindsight
    hindsight_high = sum(1 for r in results if r.obviousness_evidence and
                         r.obviousness_evidence.get("hindsight") == "HIGH")
    hindsight_medium = sum(1 for r in results if r.obviousness_evidence and
                           r.obviousness_evidence.get("hindsight") == "MEDIUM")
    hindsight_low = sum(1 for r in results if r.obviousness_evidence and
                        r.obviousness_evidence.get("hindsight") == "LOW")

    # Identity
    identity_confirmed = sum(1 for r in results if r.identity_state == IDENTITY_CONFIRMED)

    # Rescue
    amended = [r for r in results if r.ground_truth_label == "AMENDED"]
    rescue_correct = sum(1 for r in amended if r.rescue_recognized == True)
    rescue_acc = rescue_correct / max(1, len(amended)) if amended else 0.0

    # Motivation sources distribution
    motivation_sources = {}
    for r in results:
        if r.obviousness_evidence and r.obviousness_evidence.get("motivation"):
            src = r.obviousness_evidence["motivation"].get("motivation_source", "UNKNOWN")
            motivation_sources[src] = motivation_sources.get(src, 0) + 1

    # Expectation sources distribution
    expectation_sources = {}
    for r in results:
        if r.obviousness_evidence and r.obviousness_evidence.get("expectation"):
            src = r.obviousness_evidence["expectation"].get("expectation_source", "UNKNOWN")
            expectation_sources[src] = expectation_sources.get(src, 0) + 1

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
        "unable_to_adjudicate_count": unable,
        "correct_predictions": correct,
        "overall_accuracy": round(accuracy, 4),
        "false_elite_count": false_elite,
        "false_elite_rate": round(false_elite_rate, 4),
        "false_reject_count": false_reject,
        "false_reject_rate": round(false_reject_rate, 4),
        "cited_art_recall": round(cited_art_recall, 4),
        "cited_103_art_recall": round(cited_103_art_recall, 4),
        "search_recall": round(search_recall, 4),
        "102_accuracy": round(accuracy_102, 4),
        "103_accuracy": round(accuracy_103, 4),
        "hindsight_high": hindsight_high,
        "hindsight_medium": hindsight_medium,
        "hindsight_low": hindsight_low,
        "identity_confirmed": identity_confirmed,
        "rescue_recognition_accuracy": round(rescue_acc, 4),
        "motivation_sources_distribution": motivation_sources,
        "expectation_sources_distribution": expectation_sources,
        "error_103_classification_summary": error_103_summary,
        "passes_threshold": passes,
        "thresholds": {**THRESHOLDS, "102_accuracy_min": 0.85, "103_accuracy_min": 0.80},
        "status": "UNBLOCK_50_TO_5" if passes else "CALIBRATION_BLOCKED",
    }
