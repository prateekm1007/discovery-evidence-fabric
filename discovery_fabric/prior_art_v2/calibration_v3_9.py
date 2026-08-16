"""V3.9 calibration pipeline."""
from __future__ import annotations
import os, sys, json, time, re
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent.parent
sys.path.insert(0, str(REPO_ROOT))

from discovery_fabric.prior_art_v2.calibration_v2 import CALIBRATION_CASES_V2
from discovery_fabric.prior_art_v2.elite_v3 import LLMClient, _now_utc, _sha256
from discovery_fabric.prior_art_v2.calibration_v3 import (
    stage_canonical_claim, stage_search_families, stage_claim_retrieval,
    build_case_ground_truth, THRESHOLDS,
)
from discovery_fabric.prior_art_v2.claim_identity import (
    validate_claim_identity, IDENTITY_UNRESOLVED, should_stop_case,
)
from discovery_fabric.prior_art_v2.novelty_v34 import (
    construct_novelty_evidence_v34, is_102_kill_legal,
)
from discovery_fabric.prior_art_v2.obviousness_v39 import (
    ObviousnessEvidenceV39, construct_obviousness_evidence_v39,
    OBVIOUSNESS_ADVERSARY_V39_PROMPT_HASH,
)


@dataclass
class CaseResultV39:
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


def run_v39_case(case: dict, llm: LLMClient) -> CaseResultV39:
    case_id = case["case_id"]
    patent_number = case["patent_number"]
    print(f"\n=== {case_id} — {patent_number} ===")

    cited_art = case.get("prior_art_cited", [])
    result = CaseResultV39(
        case_id=case_id, patent_number=patent_number,
        title=case.get("title", ""), device_class=case.get("device_class", ""),
        ground_truth_label=case.get("ground_truth_label", "UNKNOWN"),
        ground_truth_disposition=case.get("ground_truth_disposition", "UNKNOWN"),
        cited_art_expected=list(cited_art),
    )

    canonical, calls = stage_canonical_claim(case, llm)
    result.llm_calls += calls

    families, patent_ids = stage_search_families(case, canonical, cited_art)
    result.families_attempted = sum(1 for f in families if f.attempted)
    result.families_succeeded = sum(1 for f in families if f.failure_state in
                                    ("SUCCESS", "SEARCH_RETURNED_PATENTS",
                                     "SEARCH_RETURNED_NO_RESULTS", "CLAIMS_RETRIEVED"))

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
            return result
    else:
        result.identity_state = IDENTITY_UNRESOLVED

    novelty, calls = construct_novelty_evidence_v34(
        case=case,
        canonical_claim={"patent_number": canonical.patent_number, "limitations": canonical.limitations},
        evidence=[asdict(e) for e in evidence], llm=llm,
    )
    result.llm_calls += calls

    obviousness, calls = construct_obviousness_evidence_v39(
        case=case,
        canonical_claim={"patent_number": canonical.patent_number, "limitations": canonical.limitations},
        novelty_evidence=novelty, evidence=[asdict(e) for e in evidence], llm=llm,
    )
    result.llm_calls += calls

    adjudication = _adjudicate_v39(novelty, obviousness, evidence)

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

    _compare(result, case)
    print(f"  -> {result.predicted_tier} gt={result.ground_truth_label} correct={result.correct} "
          f"103={obviousness.determination}")
    return result


def _adjudicate_v39(novelty, obviousness, evidence) -> Dict[str, Any]:
    claims_count = sum(1 for e in evidence if e.claims_retrieved)
    if claims_count == 0:
        return {"predicted_outcome": "INSUFFICIENT_EVIDENCE", "predicted_tier": "SEARCH_INSUFFICIENT"}

    if is_102_kill_legal(novelty):
        return {"predicted_outcome": "NOVELTY_FAILS", "predicted_tier": "REJECT"}
    elif obviousness.obviousness_succeeds:
        return {"predicted_outcome": "OBVIOUSNESS_RISK", "predicted_tier": "REJECT",
                "adjudicator_rationale": obviousness.determination_rationale}
    else:
        gold = claims_count
        hindsight = obviousness.hindsight
        if gold >= 3 and hindsight == "LOW":
            return {"predicted_outcome": "STRONG", "predicted_tier": "STRONG"}
        return {"predicted_outcome": "NOVELTY_SURVIVES", "predicted_tier": "PROMISING"}


def _compare(result, case):
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
    elif gt == "REJECTED":
        result.correct = pred == "REJECT"
        result.error_type = "CORRECT" if result.correct else (
            "FALSE_ELITE" if pred in ("STRONG", "ELITE") else "MODEL_JUDGMENT_FAILURE")
    elif gt == "AMENDED":
        result.correct = pred in ("PROMISING", "STRONG", "ELITE")
        result.error_type = "CORRECT" if result.correct else "FALSE_REJECT"
    result.error_category = "CORRECT" if result.correct else "FINAL_ADJUDICATION_FAILURE"


def calculate_v39_metrics(results: List[CaseResultV39]) -> dict:
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
        if case is None: continue
        had_102 = case.get("had_102_rejection", False)
        predicted_102 = r.novelty_evidence.get("final_result") == "102_KILL"
        if had_102 == predicted_102: correct_102 += 1
        total_102 += 1
    accuracy_102 = correct_102 / max(1, total_102) if total_102 > 0 else 0.0

    # 103 accuracy + precision + recall
    correct_103 = 0
    total_103 = 0
    tp_103 = 0  # system says obvious, case was rejected (correct)
    fp_103 = 0  # system says obvious, case was NOT rejected (false positive)
    fn_103 = 0  # system says not obvious, case WAS rejected (false negative)
    tn_103 = 0  # system says not obvious, case was NOT rejected (correct)
    for r in cases_with_102:
        case = next((c for c in CALIBRATION_CASES_V2 if c["case_id"] == r.case_id), None)
        if case is None or not r.obviousness_evidence: continue
        had_103 = case.get("had_103_rejection", False)
        predicted_103 = r.obviousness_evidence.get("obviousness_succeeds", False)
        if had_103 == predicted_103: correct_103 += 1
        total_103 += 1
        if predicted_103 and had_103: tp_103 += 1
        elif predicted_103 and not had_103: fp_103 += 1
        elif not predicted_103 and had_103: fn_103 += 1
        else: tn_103 += 1
    accuracy_103 = correct_103 / max(1, total_103) if total_103 > 0 else 0.0
    precision_103 = tp_103 / max(1, tp_103 + fp_103) if (tp_103 + fp_103) > 0 else 0.0
    recall_103 = tp_103 / max(1, tp_103 + fn_103) if (tp_103 + fn_103) > 0 else 0.0

    # Hindsight
    hindsight_high = sum(1 for r in results if r.obviousness_evidence and
                         r.obviousness_evidence.get("hindsight") == "HIGH")
    hindsight_medium = sum(1 for r in results if r.obviousness_evidence and
                           r.obviousness_evidence.get("hindsight") == "MEDIUM")
    hindsight_low = sum(1 for r in results if r.obviousness_evidence and
                        r.obviousness_evidence.get("hindsight") == "LOW")

    # 4-question assessment stats
    evidence_found_count = sum(1 for r in results if r.obviousness_evidence and
                               r.obviousness_evidence.get("evidence_exists", {}) and
                               r.obviousness_evidence["evidence_exists"].get("evidence_found"))
    motivation_bridge_complete = sum(1 for r in results if r.obviousness_evidence and
                                     r.obviousness_evidence.get("motivation", {}) and
                                     r.obviousness_evidence["motivation"].get("bridge_complete"))
    compatibility_conflicting = sum(1 for r in results if r.obviousness_evidence and
                                    r.obviousness_evidence.get("compatibility", {}) and
                                    r.obviousness_evidence["compatibility"].get("overall_state") == "INHERENTLY_CONFLICTING")
    expectation_reasonable = sum(1 for r in results if r.obviousness_evidence and
                                 r.obviousness_evidence.get("expectation", {}) and
                                 r.obviousness_evidence["expectation"].get("is_reasonable"))
    mere_aggregation = sum(1 for r in results if r.obviousness_evidence and
                           r.obviousness_evidence.get("whole_claim", {}) and
                           r.obviousness_evidence["whole_claim"].get("is_mere_aggregation"))

    amended = [r for r in results if r.ground_truth_label == "AMENDED"]
    rescue_acc = sum(1 for r in amended if r.rescue_recognized == True) / max(1, len(amended)) if amended else 0.0

    passes = (accuracy >= 0.85 and false_elite_rate <= 0.10 and false_reject_rate <= 0.10 and
              cited_art_recall >= 0.90 and search_recall >= 0.80 and
              accuracy_102 >= 0.85 and accuracy_103 >= 0.80 and precision_103 >= 0.85)

    return {
        "total_cases": total,
        "sufficient_evidence_cases": sufficient,
        "correct_predictions": correct,
        "overall_accuracy": round(accuracy, 4),
        "false_elite_rate": round(false_elite_rate, 4),
        "false_reject_rate": round(false_reject_rate, 4),
        "cited_art_recall": round(cited_art_recall, 4),
        "search_recall": round(search_recall, 4),
        "102_accuracy": round(accuracy_102, 4),
        "103_accuracy": round(accuracy_103, 4),
        "103_precision": round(precision_103, 4),
        "103_recall": round(recall_103, 4),
        "103_tp": tp_103, "103_fp": fp_103, "103_fn": fn_103, "103_tn": tn_103,
        "hindsight_high": hindsight_high,
        "hindsight_medium": hindsight_medium,
        "hindsight_low": hindsight_low,
        "evidence_found_count": evidence_found_count,
        "motivation_bridge_complete": motivation_bridge_complete,
        "compatibility_conflicting": compatibility_conflicting,
        "expectation_reasonable": expectation_reasonable,
        "mere_aggregation_count": mere_aggregation,
        "rescue_recognition_accuracy": round(rescue_acc, 4),
        "passes_threshold": passes,
        "status": "UNBLOCK_50_TO_5" if passes else "CALIBRATION_BLOCKED",
    }
