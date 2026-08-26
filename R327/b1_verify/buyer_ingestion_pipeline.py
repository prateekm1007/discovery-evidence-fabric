#!/usr/bin/env python3.13
"""
R326 — Executable Buyer-Data Ingestion Pipeline
================================================

Authority: CEO R326 Gates 1-8
Constitutional basis: Article III (verifier never trusts claimant), Article VIII (certification must attack itself),
                      Article XXVI (claimant ≠ verifier), Article XXVIII (no semantic promotion)

This is EXECUTABLE CODE, not a JSON description. It implements:
  Gate 1: Real inbound buyer-data path (file → SHA-256 → protocol → candidate → result → evidence → state)
  Gate 2: Real provenance testing (hash verification + attack detection)
  Gate 3: Deterministic evidence classification
  Gate 4: Statistical semantics (CI-threshold interaction)
  Gate 5: EIG as executable math
  Gate 6: Knowledge atom creation from result
  Gate 7: Deterministic state transition from evidence
  Gate 8: Bidirectional loop in executable code

Usage:
  python3.13 buyer_ingestion_pipeline.py --fixture <path> --mode <pass|fail|ambiguous|attack>
"""

import hashlib
import json
import sys
import os
import math
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from typing import Optional, Tuple, List, Dict
from enum import Enum

# ============================================================
# GATE 3: Evidence Classification (deterministic)
# ============================================================

class EvidenceClass(str, Enum):
    SIMULATED_TEST_FIXTURE = "SIMULATED_TEST_FIXTURE"
    INSPECTABLE = "INSPECTABLE"
    REPRODUCIBLE = "REPRODUCIBLE"
    INDEPENDENTLY_COMPUTATIONALLY_VALIDATED = "INDEPENDENTLY_COMPUTATIONALLY_VALIDATED"
    MECHANISM_EXTERNALLY_VERIFIED = "MECHANISM_EXTERNALLY_VERIFIED"
    PHYSICALLY_VALIDATED = "PHYSICALLY_VALIDATED"
    FALSIFIED = "FALSIFIED"
    INSUFFICIENT_RESOLUTION = "INSUFFICIENT_RESOLUTION"

class CandidateState(str, Enum):
    MODEL_RUNNING = "MODEL_RUNNING"
    MODEL_ATTACKED = "MODEL_ATTACKED"
    MODEL_INDEPENDENTLY_VERIFIED = "MODEL_INDEPENDENTLY_VERIFIED"
    TECHNICALLY_EVALUABLE = "TECHNICALLY_EVALUABLE"
    TECHNOLOGY_TRANSFER_READY = "TECHNOLOGY_TRANSFER_READY"
    EXPERIMENT_READY = "EXPERIMENT_READY"
    EVALUATION_READY = "EVALUATION_READY"
    VERIFICATION_PENDING = "VERIFICATION_PENDING"
    CEMETERY = "CEMETERY"
    BUYER_TESTED = "BUYER_TESTED"

# ============================================================
# GATE 4: Statistical Semantics (CI-threshold interaction)
# ============================================================

class Verdict(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    AMBIGUOUS = "AMBIGUOUS"
    BLOCKED = "BLOCKED"

def classify_result_ci(
    point_estimate: float,
    ci_low: float,
    ci_high: float,
    pass_threshold: float,
    fail_threshold: float,
    higher_is_better: bool = True
) -> Tuple[Verdict, str]:
    """
    Deterministic CI-threshold classification.

    Rules (for higher_is_better=True, e.g., reduction %):
      - PASS: CI entirely above pass_threshold (ci_low >= pass_threshold)
      - FAIL: CI entirely below fail_threshold (ci_high <= fail_threshold)
      - AMBIGUOUS: CI spans either threshold

    For higher_is_better=False (e.g., response time, lower is better):
      - PASS: CI entirely below pass_threshold (ci_high <= pass_threshold)
      - FAIL: CI entirely above fail_threshold (ci_low >= fail_threshold)
    """
    if higher_is_better:
        if ci_low >= pass_threshold:
            return Verdict.PASS, f"CI [{ci_low:.1f}, {ci_high:.1f}] entirely above PASS threshold {pass_threshold}"
        elif ci_high <= fail_threshold:
            return Verdict.FAIL, f"CI [{ci_low:.1f}, {ci_high:.1f}] entirely below FAIL threshold {fail_threshold}"
        else:
            return Verdict.AMBIGUOUS, f"CI [{ci_low:.1f}, {ci_high:.1f}] spans PASS({pass_threshold})/FAIL({fail_threshold}) boundary"
    else:
        if ci_high <= pass_threshold:
            return Verdict.PASS, f"CI [{ci_low:.1f}, {ci_high:.1f}] entirely below PASS threshold {pass_threshold}"
        elif ci_low >= fail_threshold:
            return Verdict.FAIL, f"CI [{ci_low:.1f}, {ci_high:.1f}] entirely above FAIL threshold {fail_threshold}"
        else:
            return Verdict.AMBIGUOUS, f"CI [{ci_low:.1f}, {ci_high:.1f}] spans PASS({pass_threshold})/FAIL({fail_threshold}) boundary"

# ============================================================
# GATE 2: Provenance Verification
# ============================================================

def compute_sha256(file_path: str) -> str:
    """Compute SHA-256 of a file."""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()

def verify_provenance(
    raw_data_path: str,
    declared_hash: str,
    expected_candidate: str,
    expected_experiment: str,
    expected_protocol_version: str,
    submission_candidate: str,
    submission_experiment: str,
    submission_protocol: str,
    submission_analysis_version: str,
    expected_analysis_version: str,
    calibration_metadata: dict
) -> Tuple[bool, List[str]]:
    """
    Verify provenance of buyer-submitted data.
    Returns (passed, list_of_errors).
    """
    errors = []

    # 1. Hash verification
    actual_hash = compute_sha256(raw_data_path)
    if actual_hash != declared_hash:
        errors.append(f"HASH_MISMATCH: declared={declared_hash[:16]}... actual={actual_hash[:16]}...")

    # 2. Candidate verification
    if submission_candidate != expected_candidate:
        errors.append(f"WRONG_CANDIDATE: expected={expected_candidate} submitted={submission_candidate}")

    # 3. Experiment ID verification
    if submission_experiment != expected_experiment:
        errors.append(f"WRONG_EXPERIMENT: expected={expected_experiment} submitted={submission_experiment}")

    # 4. Protocol version verification
    if submission_protocol != expected_protocol_version:
        errors.append(f"WRONG_PROTOCOL: expected={expected_protocol_version} submitted={submission_protocol}")

    # 5. Analysis version verification
    if submission_analysis_version != expected_analysis_version:
        errors.append(f"STALE_ANALYSIS: expected={expected_analysis_version} submitted={submission_analysis_version}")

    # 6. Calibration metadata
    if not calibration_metadata or 'equipment' not in calibration_metadata:
        errors.append("MISSING_CALIBRATION: no equipment/calibration metadata provided")

    return (len(errors) == 0, errors)

# ============================================================
# GATE 7: Deterministic State Transition
# ============================================================

def deterministic_state_transition(
    current_state: CandidateState,
    verdict: Verdict,
    evidence_class: EvidenceClass,
    repair_budget_remaining: int
) -> Tuple[CandidateState, str]:
    """
    Deterministic state machine. The AI does NOT choose the state.
    The state is derived from evidence by deterministic rules.
    """
    if current_state == CandidateState.EXPERIMENT_READY:
        if verdict == Verdict.PASS and evidence_class == EvidenceClass.PHYSICALLY_VALIDATED:
            return CandidateState.TECHNICALLY_EVALUABLE, "PASS + PHYSICALLY_VALIDATED → TECHNICALLY_EVALUABLE"
        elif verdict == Verdict.FAIL:
            if repair_budget_remaining > 0:
                return CandidateState.EXPERIMENT_READY, "FAIL + repair budget remaining → EXPERIMENT_READY (repair)"
            else:
                return CandidateState.CEMETERY, "FAIL + no repair budget → CEMETERY"
        elif verdict == Verdict.AMBIGUOUS:
            return CandidateState.EXPERIMENT_READY, "AMBIGUOUS → EXPERIMENT_READY (repeat with higher n)"
        else:
            return CandidateState.VERIFICATION_PENDING, f"Unexpected verdict {verdict}"
    elif current_state == CandidateState.TECHNICALLY_EVALUABLE:
        if verdict == Verdict.PASS and evidence_class == EvidenceClass.PHYSICALLY_VALIDATED:
            return CandidateState.TECHNOLOGY_TRANSFER_READY, "PASS + PHYSICAL → TTR"
        elif verdict == Verdict.FAIL:
            return CandidateState.CEMETERY, "FAIL at TECHNICALLY_EVALUABLE → CEMETERY"
        else:
            return current_state, f"Verdict {verdict} at TECHNICALLY_EVALUABLE → no change"
    elif current_state == CandidateState.TECHNOLOGY_TRANSFER_READY:
        if verdict == Verdict.FAIL:
            return CandidateState.CEMETERY, "FAIL at TTR → CEMETERY (catastrophic)"
        else:
            return current_state, f"Verdict {verdict} at TTR → no change"
    else:
        return current_state, f"No transition rule for {current_state} + {verdict}"

# ============================================================
# GATE 5: EIG as Executable Math
# ============================================================

def calculate_eig(
    hypothesis_priors: Dict[str, float],
    outcome_likelihoods: Dict[str, Dict[str, float]],
    cost_USD: float,
    time_weeks: float,
    risk_score: float
) -> dict:
    """
    Calculate Expected Information Gain using actual Shannon entropy.

    hypothesis_priors: {hypothesis_name: prior_probability}
    outcome_likelihoods: {outcome_name: {hypothesis_name: P(outcome|hypothesis)}}

    EIG = H(prior) - E[H(posterior)]
    """
    # Prior entropy
    prior_entropy = 0.0
    for h, p in hypothesis_priors.items():
        if p > 0:
            prior_entropy -= p * math.log2(p)

    # For each outcome, compute posterior and posterior entropy
    outcomes = list(outcome_likelihoods.keys())
    outcome_probs = {}
    posterior_entropies = {}

    for outcome in outcomes:
        # P(outcome) = sum_h P(outcome|h) * P(h)
        p_outcome = sum(outcome_likelihoods[outcome][h] * hypothesis_priors[h] for h in hypothesis_priors)
        outcome_probs[outcome] = p_outcome

        # Posterior: P(h|outcome) = P(outcome|h) * P(h) / P(outcome)
        posterior = {}
        posterior_entropy = 0.0
        for h in hypothesis_priors:
            if p_outcome > 0:
                p_h_given_outcome = outcome_likelihoods[outcome][h] * hypothesis_priors[h] / p_outcome
            else:
                p_h_given_outcome = 0
            posterior[h] = p_h_given_outcome
            if p_h_given_outcome > 0:
                posterior_entropy -= p_h_given_outcome * math.log2(p_h_given_outcome)
        posterior_entropies[outcome] = posterior_entropy

    # Expected posterior entropy
    expected_posterior_entropy = sum(outcome_probs[o] * posterior_entropies[o] for o in outcomes)

    # EIG
    eig = prior_entropy - expected_posterior_entropy

    # Selection value: EIG / (cost * time * risk)
    selection_value = eig / (cost_USD * time_weeks * risk_score) if cost_USD > 0 else 0

    return {
        "prior_entropy_bits": round(prior_entropy, 4),
        "expected_posterior_entropy_bits": round(expected_posterior_entropy, 4),
        "eig_bits": round(eig, 4),
        "cost_USD": cost_USD,
        "time_weeks": time_weeks,
        "risk_score": risk_score,
        "selection_value": round(selection_value, 8),
        "outcome_probabilities": {k: round(v, 4) for k, v in outcome_probs.items()},
        "posterior_entropies": {k: round(v, 4) for k, v in posterior_entropies.items()}
    }

# ============================================================
# GATE 6: Knowledge Atom Creation
# ============================================================

def create_knowledge_atom(
    ka_id: str,
    source_result: dict,
    lesson: str,
    trigger_condition: str,
    affected_class: str,
    design_rule: str,
    machine_action: str
) -> dict:
    """Create a machine-executable knowledge atom from an experimental result."""
    return {
        "ka_id": ka_id,
        "source_experiment_id": source_result.get("experiment_id"),
        "source_candidate": source_result.get("candidate_id"),
        "source_verdict": source_result.get("verdict"),
        "source_evidence_class": source_result.get("evidence_class"),
        "lesson": lesson,
        "trigger_condition": trigger_condition,
        "affected_candidate_class": affected_class,
        "changed_design_rule": design_rule,
        "machine_action": machine_action,
        "created_timestamp": datetime.now(timezone.utc).isoformat(),
        "executable": True
    }

def check_factory_inheritance(candidate_class: str, design_properties: dict, knowledge_atoms: list) -> list:
    """Check if a candidate satisfies all inherited knowledge atom rules."""
    violations = []
    for ka in knowledge_atoms:
        if candidate_class in ka.get("affected_candidate_class", "") or ka.get("affected_candidate_class") == "ALL":
            trigger = ka.get("trigger_condition", "")
            if "distributed" in trigger and "hydraulic" in candidate_class.lower():
                if not design_properties.get("conductance_matched_3d_verified", False):
                    violations.append(f"KA-{ka['ka_id']}: {ka['machine_action']} — conductance matching not verified")
            if "optical" in trigger and "optical" in candidate_class.lower():
                if not design_properties.get("monte_carlo_used", False):
                    violations.append(f"KA-{ka['ka_id']}: {ka['machine_action']} — Monte Carlo not used")
    return violations

# ============================================================
# GATE 8: Full Bidirectional Pipeline
# ============================================================

def ingest_buyer_submission(
    raw_data_path: str,
    declared_hash: str,
    submission: dict,
    experiment_contract: dict,
    is_synthetic: bool = True
) -> dict:
    """
    Full inbound pipeline: raw data → hash → provenance → analysis → evidence → state → KA → next experiment.
    """
    result = {
        "pipeline_version": "R326-executable",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_synthetic": is_synthetic,
        "evidence_class_override": None
    }

    # Gate 2: Provenance verification
    provenance_passed, provenance_errors = verify_provenance(
        raw_data_path=raw_data_path,
        declared_hash=declared_hash,
        expected_candidate=experiment_contract["candidate_id"],
        expected_experiment=experiment_contract["experiment_id"],
        expected_protocol_version=experiment_contract["protocol_version"],
        submission_candidate=submission.get("candidate_id", ""),
        submission_experiment=submission.get("experiment_id", ""),
        submission_protocol=submission.get("protocol_version", ""),
        submission_analysis_version=submission.get("analysis_version", ""),
        expected_analysis_version=experiment_contract.get("analysis_version", "v1"),
        calibration_metadata=submission.get("calibration", {})
    )

    if not provenance_passed:
        result["verdict"] = "BLOCKED"
        result["evidence_class"] = EvidenceClass.INSUFFICIENT_RESOLUTION.value
        result["provenance_errors"] = provenance_errors
        result["state_transition"] = "NONE — provenance failed"
        return result

    result["provenance_passed"] = True

    # Gate 4: Statistical classification
    point_est = submission["result_point_estimate"]
    ci_low = submission["result_ci_low"]
    ci_high = submission["result_ci_high"]
    pass_thresh = experiment_contract["pass_threshold"]
    fail_thresh = experiment_contract["fail_threshold"]
    higher_better = experiment_contract.get("higher_is_better", True)

    verdict, verdict_reason = classify_result_ci(
        point_est, ci_low, ci_high, pass_thresh, fail_thresh, higher_better
    )

    result["verdict"] = verdict.value
    result["verdict_reason"] = verdict_reason
    result["point_estimate"] = point_est
    result["ci"] = [ci_low, ci_high]

    # Gate 3: Evidence classification
    # CRITICAL: synthetic data can NEVER be PHYSICALLY_VALIDATED
    if is_synthetic:
        if verdict == Verdict.PASS:
            result["evidence_class"] = EvidenceClass.SIMULATED_TEST_FIXTURE.value
        elif verdict == Verdict.FAIL:
            result["evidence_class"] = EvidenceClass.SIMULATED_TEST_FIXTURE.value
        elif verdict == Verdict.AMBIGUOUS:
            result["evidence_class"] = EvidenceClass.SIMULATED_TEST_FIXTURE.value
        result["evidence_class_warning"] = "SYNTHETIC/TEST ONLY — this result does NOT constitute physical validation. Evidence class is SIMULATED_TEST_FIXTURE regardless of verdict."
    else:
        if verdict == Verdict.PASS:
            result["evidence_class"] = EvidenceClass.PHYSICALLY_VALIDATED.value
        elif verdict == Verdict.FAIL:
            result["evidence_class"] = EvidenceClass.FALSIFIED.value
        elif verdict == Verdict.AMBIGUOUS:
            result["evidence_class"] = EvidenceClass.INSUFFICIENT_RESOLUTION.value

    # Gate 7: Deterministic state transition
    current_state = CandidateState(experiment_contract["current_state"])
    repair_budget = experiment_contract.get("repair_budget_remaining", 1)

    # For synthetic, don't actually transition state (just demonstrate the rule)
    evidence_class_for_transition = EvidenceClass.PHYSICALLY_VALIDATED if (not is_synthetic and verdict == Verdict.PASS) else EvidenceClass.SIMULATED_TEST_FIXTURE

    new_state, transition_reason = deterministic_state_transition(
        current_state=current_state,
        verdict=verdict,
        evidence_class=evidence_class_for_transition,
        repair_budget_remaining=repair_budget
    )

    result["state_transition"] = {
        "from": current_state.value,
        "to": new_state.value if not is_synthetic else f"{new_state.value} (DEMONSTRATED ONLY — synthetic data does not execute real transition)",
        "reason": transition_reason,
        "real_transition_executed": not is_synthetic
    }

    # Gate 6: Knowledge atom creation
    if verdict == Verdict.PASS and not is_synthetic:
        ka = create_knowledge_atom(
            ka_id=f"KA-{submission.get('candidate_id','?')}-PASS-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            source_result={"experiment_id": submission.get("experiment_id"), "candidate_id": submission.get("candidate_id"), "verdict": verdict.value, "evidence_class": result["evidence_class"]},
            lesson=f"{submission.get('candidate_id')} mechanism validated: point={point_est}, CI=[{ci_low},{ci_high}]",
            trigger_condition=f"candidate_class:{experiment_contract.get('candidate_class','')}",
            affected_class=experiment_contract.get("candidate_class", ""),
            design_rule="Mechanism validated — proceed to next development phase",
            machine_action="Promote to TECHNICALLY_EVALUABLE"
        )
        result["knowledge_atom_created"] = ka
    elif verdict == Verdict.FAIL and not is_synthetic:
        ka = create_knowledge_atom(
            ka_id=f"KA-{submission.get('candidate_id','?')}-FAIL-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            source_result={"experiment_id": submission.get("experiment_id"), "candidate_id": submission.get("candidate_id"), "verdict": verdict.value, "evidence_class": result["evidence_class"]},
            lesson=f"{submission.get('candidate_id')} mechanism falsified: point={point_est}, CI=[{ci_low},{ci_high}]",
            trigger_condition=f"candidate_class:{experiment_contract.get('candidate_class','')}",
            affected_class=experiment_contract.get("candidate_class", ""),
            design_rule="Mechanism falsified — do not retry without fundamentally different approach",
            machine_action="Send to CEMETERY with reusable negative knowledge"
        )
        result["knowledge_atom_created"] = ka
    else:
        result["knowledge_atom_created"] = None

    return result


# ============================================================
# ADVERSARIAL TESTS
# ============================================================

def run_adversarial_tests():
    """Run all adversarial tests for Gates 2, 4, 7."""
    tests = []
    tmp = Path("/tmp/r326_tests")
    tmp.mkdir(exist_ok=True)

    # --- Gate 2: Provenance Tests ---
    print("=== GATE 2: Provenance Adversarial Tests ===")

    # Create a test fixture file
    fixture_data = {"adaptive_mean": 8.2, "fixed_mean": 15.1, "n": 10}
    fixture_path = str(tmp / "fixture_pass.json")
    with open(fixture_path, 'w') as f:
        json.dump(fixture_data, f)

    real_hash = compute_sha256(fixture_path)

    # Test 1: Correct hash → PASS
    passed, errors = verify_provenance(
        fixture_path, real_hash, "P-02", "EXP-P02-001", "v1",
        "P-02", "EXP-P02-001", "v1", "v1", "v1",
        {"equipment": "mock CSF loop", "calibration": "2026-08-26"}
    )
    tests.append({"test": "G2-1-correct-hash", "expected": "PASS", "actual": "PASS" if passed else "FAIL", "passed": passed})

    # Test 2: One byte changed → hash mismatch → BLOCK
    tampered_path = str(tmp / "fixture_tampered.json")
    with open(tampered_path, 'w') as f:
        f.write(json.dumps(fixture_data)[:-1] + "X")  # change last byte
    passed, errors = verify_provenance(
        tampered_path, real_hash, "P-02", "EXP-P02-001", "v1",
        "P-02", "EXP-P02-001", "v1", "v1", "v1",
        {"equipment": "mock CSF loop"}
    )
    tests.append({"test": "G2-2-tampered-hash", "expected": "BLOCK", "actual": "BLOCK" if not passed else "PASS", "passed": not passed, "errors": errors})

    # Test 3: Wrong candidate → BLOCK
    passed, errors = verify_provenance(
        fixture_path, real_hash, "P-02", "EXP-P02-001", "v1",
        "P-04", "EXP-P02-001", "v1", "v1", "v1",
        {"equipment": "mock CSF loop"}
    )
    tests.append({"test": "G2-3-wrong-candidate", "expected": "BLOCK", "actual": "BLOCK" if not passed else "PASS", "passed": not passed, "errors": errors})

    # Test 4: Missing calibration → BLOCK
    passed, errors = verify_provenance(
        fixture_path, real_hash, "P-02", "EXP-P02-001", "v1",
        "P-02", "EXP-P02-001", "v1", "v1", "v1",
        {}
    )
    tests.append({"test": "G2-4-missing-calibration", "expected": "BLOCK", "actual": "BLOCK" if not passed else "PASS", "passed": not passed, "errors": errors})

    # --- Gate 4: Statistical Semantics Tests ---
    print("\n=== GATE 4: Statistical Semantics Tests ===")

    # P-02 contract: pass=40%, fail=20%, higher_is_better=True
    # Test 1: CI entirely in PASS zone (50, [45, 55])
    v, r = classify_result_ci(50, 45, 55, 40, 20, True)
    tests.append({"test": "G4-1-ci-in-pass", "expected": "PASS", "actual": v.value, "passed": v == Verdict.PASS})

    # Test 2: CI entirely in FAIL zone (10, [5, 15])
    v, r = classify_result_ci(10, 5, 15, 40, 20, True)
    tests.append({"test": "G4-2-ci-in-fail", "expected": "FAIL", "actual": v.value, "passed": v == Verdict.FAIL})

    # Test 3: CI spans PASS boundary (42, [35, 50]) — point above but CI crosses
    v, r = classify_result_ci(42, 35, 50, 40, 20, True)
    tests.append({"test": "G4-3-ci-spans-pass", "expected": "AMBIGUOUS", "actual": v.value, "passed": v == Verdict.AMBIGUOUS})

    # Test 4: CI spans FAIL boundary (18, [10, 25]) — point below fail but CI crosses
    v, r = classify_result_ci(18, 10, 25, 40, 20, True)
    tests.append({"test": "G4-4-ci-spans-fail", "expected": "AMBIGUOUS", "actual": v.value, "passed": v == Verdict.AMBIGUOUS})

    # Test 5: CI spans BOTH boundaries (30, [15, 50])
    v, r = classify_result_ci(30, 15, 50, 40, 20, True)
    tests.append({"test": "G4-5-ci-spans-both", "expected": "AMBIGUOUS", "actual": v.value, "passed": v == Verdict.AMBIGUOUS})

    # --- Gate 7: State Transition Adversarial Tests ---
    print("\n=== GATE 7: State Transition Adversarial Tests ===")

    # Test 1: EXPERIMENT_READY + PASS + PHYSICAL → TECHNICALLY_EVALUABLE
    s, r = deterministic_state_transition(CandidateState.EXPERIMENT_READY, Verdict.PASS, EvidenceClass.PHYSICALLY_VALIDATED, 1)
    tests.append({"test": "G7-1-pass-physical", "expected": "TECHNICALLY_EVALUABLE", "actual": s.value, "passed": s == CandidateState.TECHNICALLY_EVALUABLE})

    # Test 2: EXPERIMENT_READY + FAIL + budget=0 → CEMETERY
    s, r = deterministic_state_transition(CandidateState.EXPERIMENT_READY, Verdict.FAIL, EvidenceClass.FALSIFIED, 0)
    tests.append({"test": "G7-2-fail-no-budget", "expected": "CEMETERY", "actual": s.value, "passed": s == CandidateState.CEMETERY})

    # Test 3: EXPERIMENT_READY + FAIL + budget=1 → EXPERIMENT_READY (repair)
    s, r = deterministic_state_transition(CandidateState.EXPERIMENT_READY, Verdict.FAIL, EvidenceClass.FALSIFIED, 1)
    tests.append({"test": "G7-3-fail-with-budget", "expected": "EXPERIMENT_READY", "actual": s.value, "passed": s == CandidateState.EXPERIMENT_READY})

    # Test 4: EXPERIMENT_READY + AMBIGUOUS → EXPERIMENT_READY (repeat)
    s, r = deterministic_state_transition(CandidateState.EXPERIMENT_READY, Verdict.AMBIGUOUS, EvidenceClass.INSUFFICIENT_RESOLUTION, 1)
    tests.append({"test": "G7-4-ambiguous", "expected": "EXPERIMENT_READY", "actual": s.value, "passed": s == CandidateState.EXPERIMENT_READY})

    # Test 5: Adversarial — SIMULATED data trying to claim PHYSICAL → state machine overrides
    # The AI writes "PHYSICALLY_VALIDATED" but is_synthetic=True
    # The pipeline MUST override to SIMULATED_TEST_FIXTURE
    # (This is tested in the full pipeline below)

    # --- Gate 3: Evidence Classification Adversarial ---
    print("\n=== GATE 3: Evidence Classification Tests ===")

    # Synthetic PASS → must be SIMULATED_TEST_FIXTURE, NOT PHYSICALLY_VALIDATED
    contract = {
        "candidate_id": "P-02", "experiment_id": "EXP-P02-001", "protocol_version": "v1",
        "analysis_version": "v1", "current_state": "EXPERIMENT_READY",
        "pass_threshold": 40, "fail_threshold": 20, "higher_is_better": True,
        "candidate_class": "cardiovascular_valve", "repair_budget_remaining": 1
    }
    submission = {
        "candidate_id": "P-02", "experiment_id": "EXP-P02-001", "protocol_version": "v1",
        "analysis_version": "v1", "result_point_estimate": 45.7,
        "result_ci_low": 37.2, "result_ci_high": 54.2,
        "calibration": {"equipment": "mock CSF loop"}
    }
    result = ingest_buyer_submission(fixture_path, real_hash, submission, contract, is_synthetic=True)
    tests.append({
        "test": "G3-1-synthetic-cannot-be-physical",
        "expected": "SIMULATED_TEST_FIXTURE",
        "actual": result["evidence_class"],
        "passed": result["evidence_class"] == EvidenceClass.SIMULATED_TEST_FIXTURE.value,
        "note": "Synthetic data MUST be SIMULATED_TEST_FIXTURE even if verdict is PASS"
    })

    # Test with REAL data flag (simulating real external data)
    submission_real = dict(submission)
    submission_real["result_ci_low"] = 42.0  # CI entirely in PASS zone
    submission_real["result_ci_high"] = 50.0
    result_real = ingest_buyer_submission(fixture_path, real_hash, submission_real, contract, is_synthetic=False)
    tests.append({
        "test": "G3-2-real-pass-is-physical",
        "expected": "PHYSICALLY_VALIDATED",
        "actual": result_real["evidence_class"],
        "passed": result_real["evidence_class"] == EvidenceClass.PHYSICALLY_VALIDATED.value,
        "note": "REAL data with PASS → PHYSICALLY_VALIDATED. (This test uses is_synthetic=False to demonstrate the rule; the data is still a fixture but the classification logic is correct.)"
    })

    # --- Gate 5: EIG Math Tests ---
    print("\n=== GATE 5: EIG Executable Math Tests ===")

    # Simple case: 2 hypotheses, 2 outcomes
    eig_result = calculate_eig(
        hypothesis_priors={"works": 0.5, "doesnt_work": 0.5},
        outcome_likelihoods={
            "pass": {"works": 0.9, "doesnt_work": 0.1},
            "fail": {"works": 0.1, "doesnt_work": 0.9}
        },
        cost_USD=7500, time_weeks=7, risk_score=1.0
    )
    tests.append({
        "test": "G5-1-basic-eig",
        "expected": "EIG > 0",
        "actual": f"EIG={eig_result['eig_bits']} bits",
        "passed": eig_result["eig_bits"] > 0,
        "details": eig_result
    })

    # High EIG but huge cost → low selection value
    eig_expensive = calculate_eig(
        hypothesis_priors={"works": 0.5, "doesnt_work": 0.5},
        outcome_likelihoods={"pass": {"works": 0.9, "doesnt_work": 0.1}, "fail": {"works": 0.1, "doesnt_work": 0.9}},
        cost_USD=1000000, time_weeks=52, risk_score=5.0
    )
    tests.append({
        "test": "G5-2-high-eig-huge-cost",
        "expected": "low selection_value",
        "actual": f"selection_value={eig_expensive['selection_value']}",
        "passed": eig_expensive["selection_value"] < eig_result["selection_value"]
    })

    # --- Gate 6: Knowledge Atom Factory Inheritance ---
    print("\n=== GATE 6: Knowledge Atom Inheritance Tests ===")

    ka_009 = {
        "ka_id": "009",
        "affected_candidate_class": "distributed_hydraulic",
        "trigger_condition": "distributed hydraulic comparison",
        "machine_action": "Require conductance-matched 3D verification"
    }

    # Test: distributed hydraulic candidate without conductance matching → VIOLATION
    violations = check_factory_inheritance(
        "distributed_hydraulic",
        {"conductance_matched_3d_verified": False},
        [ka_009]
    )
    tests.append({
        "test": "G6-1-ka-009-blocks-unverified",
        "expected": "VIOLATION",
        "actual": "VIOLATION" if violations else "PASS",
        "passed": len(violations) > 0
    })

    # Test: distributed hydraulic candidate WITH conductance matching → NO violation
    violations_ok = check_factory_inheritance(
        "distributed_hydraulic",
        {"conductance_matched_3d_verified": True},
        [ka_009]
    )
    tests.append({
        "test": "G6-2-ka-009-passes-verified",
        "expected": "NO_VIOLATION",
        "actual": "NO_VIOLATION" if not violations_ok else "VIOLATION",
        "passed": len(violations_ok) == 0
    })

    # --- Summary ---
    print(f"\n{'='*60}")
    print(f"ADVERSARIAL TEST SUMMARY")
    print(f"{'='*60}")
    total = len(tests)
    passed = sum(1 for t in tests if t["passed"])
    print(f"Total: {total}, Passed: {passed}, Failed: {total - passed}")
    print()
    for t in tests:
        status = "✅" if t["passed"] else "❌"
        print(f"  {status} {t['test']}: expected={t['expected']} actual={t['actual']}")

    return tests

# ============================================================
# MAIN
# ============================================================

if __name__ == "__main__":
    tests = run_adversarial_tests()

    # Write results
    out = Path("/home/z/my-project/discovery-evidence-fabric/R326/g12_final_proof")
    out.mkdir(parents=True, exist_ok=True)

    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_tests": len(tests),
        "passed": sum(1 for t in tests if t["passed"]),
        "failed": sum(1 for t in tests if not t["passed"]),
        "tests": tests,
        "demonstration_type": "DEMONSTRATED WITH SYNTHETIC FIXTURE",
        "real_external_data": False,
        "note": "All tests use synthetic fixtures. The pipeline is executable and adversarially tested. Real external data has not been processed. The loop is executable but not yet closed with real data."
    }

    outfile = out / "R326_FINAL_PROOF.json"
    outfile.write_text(json.dumps(result, indent=2, default=str))
    print(f"\nFinal proof written: {outfile}")
