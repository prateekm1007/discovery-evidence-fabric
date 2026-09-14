"""
AUTONOMOUS CALIBRATION V3.6 — Evidence-Grounded Motivation + Expectation Graph
===============================================================================
Per CEO V3.6 protocol.
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
from discovery_fabric.prior_art_v2.calibration_v3 import (
    stage_canonical_claim, stage_search_families, stage_claim_retrieval,
    build_case_ground_truth, THRESHOLDS,
    MODEL_GENERATOR,
)
from discovery_fabric.prior_art_v2.claim_identity import (
    validate_claim_identity, IDENTITY_CONFIRMED, IDENTITY_MISMATCH, IDENTITY_UNRESOLVED,
    should_stop_case,
)
from discovery_fabric.prior_art_v2.novelty_v34 import (
    construct_novelty_evidence_v34, is_102_kill_legal,
)
from discovery_fabric.prior_art_v2.obviousness_v36 import (
    ObviousnessEvidenceV36, construct_obviousness_evidence_v36,
    OBVIOUSNESS_ADVERSARY_V36_PROMPT_HASH,
    MOTIVATION_EVIDENCE_TYPES_V36, EXPECTATION_EVIDENCE_TYPES_V36,
    MOTIVATION_SEARCH_FAMILIES, COMPATIBILITY_DIMENSIONS,
)


@dataclass
class CaseResultV36:
    case_id: str
    patent_number: str
    title: str
    device_class: str
    ground_truth_label: str
    ground_truth_disposition: str
    identity_state: str = IDENTITY_UNRESOLVED
    canonical_claim: Optional[Dict[str, Any]] = None
    search_families: List[Dict[str, Any]] = field(default_factory=list)
    retrieved_evidence: List[Dict[str, Any]] = field(default_factory=list)
    novelty_evidence: Optional[Dict[str, Any]] = None
    obviousness_evidence: Optional[Dict[str, Any]] = None
    final_adjudication: Optional[Dict[str, Any]] = None
    cited_art_expected: List[str] = field(default_factory=list)
    cited_art_found: List[str] = field(default_factory=list)
    cited_art_recall: float = 0.0
    families_attempted: int = 0
    families_succeeded: int = 0
    predicted_tier: str = "SEARCH_INSUFFICIENT"
    predicted_outcome: str = "INSUFFICIENT_EVIDENCE"
    correct: bool = False
    error_type: str = "INSUFFICIENT_EVIDENCE"
    error_category: str = "SEARCH_FAILURE"
    rescue_recognized: Optional[bool] = None
    llm_calls: int = 0
    role_log: List[Dict[str, str]] = field(default_factory=list)


def run_v36_case(case: dict, llm: LLMClient) -> CaseResultV36:
    case_id = case["case_id"]
    patent_number = case["patent_number"]
    print(f"\n=== {case_id} — {patent_number} — {case.get('title','')[:60]} ===")

    cited_art = case.get("prior_art_cited", [])
    result = CaseResultV36(
        case_id=case_id, patent_number=patent_number,
        title=case.get("title", ""), device_class=case.get("device_class", ""),
        ground_truth_label=case.get("ground_truth_label", "UNKNOWN"),
        ground_truth_disposition=case.get("ground_truth_disposition", "UNKNOWN"),
        cited_art_expected=list(cited_art),
    )

    # STAGE 1: GENERATOR
    print(f"  [1/5] GENERATOR...")
    canonical, calls = stage_canonical_claim(case, llm)
    result.llm_calls += calls

    # STAGE 2: SEARCHER
    print(f"  [2/5] SEARCHER...")
    families, patent_ids = stage_search_families(case, canonical, cited_art)
    result.families_attempted = sum(1 for f in families if f.attempted)
    result.families_succeeded = sum(1 for f in families if f.failure_state in
                                    ("SUCCESS", "SEARCH_RETURNED_PATENTS",
                                     "SEARCH_RETURNED_NO_RESULTS", "CLAIMS_RETRIEVED"))

    # STAGE 3: CLAIM RETRIEVAL + IDENTITY
    print(f"  [3/5] CLAIM_RETRIEVAL + IDENTITY...")
    evidence, calls = stage_claim_retrieval(patent_ids, cited_art)
    result.llm_calls += calls
    if cited_art:
        found = [e.patent_id for e in evidence if e.is_cited_art and e.claims_retrieved]
        result.cited_art_found = found
        result.cited_art_recall = len(found) / len(cited_art) if cited_art else 1.0
    else:
        result.cited_art_recall = 1.0

    case_evidence = next((e for e in evidence if e.patent_id == patent_number), None)
    if case_evidence and case_evidence.claims_retrieved:
        identity_result = validate_claim_identity(
            case=case, retrieved_patent_number=case_evidence.patent_id,
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

    # STAGE 4: NOVELTY V3.4
    print(f"  [4/5] NOVELTY_V3.4...")
    novelty, calls = construct_novelty_evidence_v34(
        case=case,
        canonical_claim={"patent_number": canonical.patent_number, "limitations": canonical.limitations},
        evidence=[asdict(e) for e in evidence], llm=llm,
    )
    result.llm_calls += calls

    # STAGE 5: OBVIOUSNESS V3.6 (evidence-grounded motivation + expectation graph)
    print(f"  [5/5] OBVIOUSNESS_V3.6 (evidence graph)...")
    obviousness, calls = construct_obviousness_evidence_v36(
        case=case,
        canonical_claim={"patent_number": canonical.patent_number, "limitations": canonical.limitations},
        novelty_evidence=novelty, evidence=[asdict(e) for e in evidence], llm=llm,
    )
    result.llm_calls += calls

    # ADJUDICATE
    adjudication = _adjudicate_v36(novelty, obviousness, evidence)

    result.canonical_claim = {"patent_number": canonical.patent_number, "limitations": canonical.limitations}
    result.search_families = [{"family_id": f.family_id, "failure_state": f.failure_state} for f in families]
    result.retrieved_evidence = [{"patent_id": e.patent_id, "claims_retrieved": e.claims_retrieved} for e in evidence]
    result.novelty_evidence = asdict(novelty)
    result.obviousness_evidence = asdict(obviousness)
    result.final_adjudication = adjudication
    result.predicted_tier = adjudication["predicted_tier"]
    result.predicted_outcome = adjudication["predicted_outcome"]

    if result.ground_truth_label == "AMENDED":
        result.rescue_recognized = (
            adjudication["predicted_tier"] in ("PROMISING", "STRONG", "ELITE")
            and case.get("amendments_made", False)
        )

    _compare_to_ground_truth(result, case)

    print(f"  -> tier={result.predicted_tier} gt={result.ground_truth_label} "
          f"correct={result.correct} mot={obviousness.motivation_evidence_count} "
          f"exp={obviousness.expectation_evidence_count}")
    return result


def _adjudicate_v36(novelty, obviousness, evidence) -> Dict[str, Any]:
    claims_count = sum(1 for e in evidence if e.claims_retrieved)
    if claims_count == 0:
        return {"predicted_outcome": "INSUFFICIENT_EVIDENCE", "predicted_tier": "SEARCH_INSUFFICIENT",
                "adjudicator_rationale": "No claims retrieved.", "claim_only_path_taken": False}

    anticipation = is_102_kill_legal(novelty)
    obviousness_succeeds = obviousness.obviousness_succeeds

    if anticipation:
        return {"predicted_outcome": "NOVELTY_FAILS", "predicted_tier": "REJECT",
                "adjudicator_rationale": "102_KILL legal.", "claim_only_path_taken": False}
    elif obviousness_succeeds:
        return {"predicted_outcome": "OBVIOUSNESS_RISK", "predicted_tier": "REJECT",
                "adjudicator_rationale": f"103: {obviousness.determination_rationale}",
                "claim_only_path_taken": False}
    else:
        gold = claims_count
        hindsight = obviousness.hindsight
        if gold >= 3 and hindsight == "LOW":
            return {"predicted_outcome": "STRONG", "predicted_tier": "STRONG",
                    "adjudicator_rationale": f"Survived. gold={gold}, hindsight={hindsight}.",
                    "claim_only_path_taken": False}
        else:
            return {"predicted_outcome": "NOVELTY_SURVIVES", "predicted_tier": "PROMISING",
                    "adjudicator_rationale": f"Survived. gold={gold}, hindsight={hindsight}. "
                    f"103: {obviousness.determination}",
                    "claim_only_path_taken": False}


def _compare_to_ground_truth(result, case):
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
        result.error_category = "CORRECT" if result.correct else "MOTIVATION_FAILURE"
    elif gt == "AMENDED":
        result.correct = pred in ("PROMISING", "STRONG", "ELITE")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
        result.error_category = "CORRECT" if result.correct else "FINAL_ADJUDICATION_FAILURE"


def calculate_v36_metrics(results: List[CaseResultV36]) -> dict:
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

    cited_cases = [r for r in results if r.cited_art_expected]
    cited_found = sum(1 for r in cited_cases if r.cited_art_recall >= 0.5)
    cited_art_recall = cited_found / max(1, len(cited_cases)) if cited_cases else 1.0

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

    # NEW: Motivation evidence recall
    # For cases with had_103_rejection=True, did system find motivation evidence?
    motivation_recall_correct = 0
    motivation_recall_total = 0
    for r in cases_with_102:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None or not r.obviousness_evidence:
            continue
        had_103 = case.get("had_103_rejection", False)
        if had_103:
            motivation_recall_total += 1
            if r.obviousness_evidence.get("motivation_evidence_count", 0) > 0:
                motivation_recall_correct += 1
    motivation_evidence_recall = motivation_recall_correct / max(1, motivation_recall_total) if motivation_recall_total > 0 else 0.0

    # NEW: Expectation evidence recall
    expectation_recall_correct = 0
    expectation_recall_total = 0
    for r in cases_with_102:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None or not r.obviousness_evidence:
            continue
        had_103 = case.get("had_103_rejection", False)
        if had_103:
            expectation_recall_total += 1
            if r.obviousness_evidence.get("expectation_evidence_count", 0) > 0:
                expectation_recall_correct += 1
    expectation_evidence_recall = expectation_recall_correct / max(1, expectation_recall_total) if expectation_recall_total > 0 else 0.0

    # Motivation/expectation graph completeness
    motivation_graph_completeness = sum(
        r.obviousness_evidence.get("motivation_evidence_count", 0) for r in results
        if r.obviousness_evidence
    ) / max(1, total)
    expectation_graph_completeness = sum(
        r.obviousness_evidence.get("expectation_evidence_count", 0) for r in results
        if r.obviousness_evidence
    ) / max(1, total)

    # Distribution of motivation evidence types
    motivation_types_dist = {}
    for r in results:
        if r.obviousness_evidence:
            for edge in r.obviousness_evidence.get("motivation_edges", []):
                etype = edge.get("evidence_type", "")
                motivation_types_dist[etype] = motivation_types_dist.get(etype, 0) + 1

    expectation_types_dist = {}
    for r in results:
        if r.obviousness_evidence:
            for edge in r.obviousness_evidence.get("expectation_edges", []):
                etype = edge.get("evidence_type", "")
                expectation_types_dist[etype] = expectation_types_dist.get(etype, 0) + 1

    hindsight_high = sum(1 for r in results if r.obviousness_evidence and
                         r.obviousness_evidence.get("hindsight") == "HIGH")
    hindsight_medium = sum(1 for r in results if r.obviousness_evidence and
                           r.obviousness_evidence.get("hindsight") == "MEDIUM")
    hindsight_low = sum(1 for r in results if r.obviousness_evidence and
                        r.obviousness_evidence.get("hindsight") == "LOW")

    amended = [r for r in results if r.ground_truth_label == "AMENDED"]
    rescue_correct = sum(1 for r in amended if r.rescue_recognized == True)
    rescue_acc = rescue_correct / max(1, len(amended)) if amended else 0.0

    passes = (
        accuracy >= 0.85 and
        false_elite_rate <= 0.10 and
        false_reject_rate <= 0.10 and
        cited_art_recall >= 0.90 and
        search_recall >= 0.80 and
        accuracy_102 >= 0.85 and
        accuracy_103 >= 0.80 and
        motivation_evidence_recall >= 0.80 and
        expectation_evidence_recall >= 0.80
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
        "search_recall": round(search_recall, 4),
        "102_accuracy": round(accuracy_102, 4),
        "103_accuracy": round(accuracy_103, 4),
        "motivation_evidence_recall": round(motivation_evidence_recall, 4),
        "expectation_evidence_recall": round(expectation_evidence_recall, 4),
        "motivation_graph_completeness": round(motivation_graph_completeness, 2),
        "expectation_graph_completeness": round(expectation_graph_completeness, 2),
        "motivation_types_distribution": motivation_types_dist,
        "expectation_types_distribution": expectation_types_dist,
        "hindsight_high": hindsight_high,
        "hindsight_medium": hindsight_medium,
        "hindsight_low": hindsight_low,
        "rescue_recognition_accuracy": round(rescue_acc, 4),
        "passes_threshold": passes,
        "thresholds": {**THRESHOLDS, "102_accuracy_min": 0.85, "103_accuracy_min": 0.80,
                       "motivation_evidence_recall_min": 0.80, "expectation_evidence_recall_min": 0.80},
        "status": "UNBLOCK_50_TO_5" if passes else "CALIBRATION_BLOCKED",
    }
