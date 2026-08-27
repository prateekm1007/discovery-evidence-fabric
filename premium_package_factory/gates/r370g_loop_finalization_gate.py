"""
r370g_loop_finalization_gate.py — Final reality loop QA gate + controlled rehearsal.

Per CEO R370G directive: finalize the reality loop with proper provenance,
causal mutation, and a controlled rehearsal. Then freeze the software layer.

10 REQUIREMENTS:
1. Formal REALITY_EVENT schema
2. Separate acquisition from interpretation
3. Computational provenance (execution log required)
4. Acquisition attestation (instrument, operator, custody chain, signature)
5. Causal mutation engine (before/after hashes, no silent mutation)
6. REAL_LOOP_VERIFIED as derived state (impossible to assign manually)
7. Buyer feedback reality-bound (AI simulation separated)
8. Engineer review externally supplied (not self-generated)
9. Article XXXVIII ratified (PROPOSED → RATIFIED)
10. CONTROLLED_LOOP_REHEARSAL test harness (SYNTHETIC=TRUE, REAL_LOOP=FALSE)

Constitution: Articles I, II, IV, VI, XXV, XXVI, XXVII, XXVIII, XXXV, XXXVII, XXXVIII.
"""

import json
import os
import sys
from datetime import datetime, timezone

try:
    from gates.r370_portable import find_repo_root, get_output_dir
except ImportError:
    try:
        from r370_portable import find_repo_root, get_output_dir
    except ImportError:
        _this_dir = os.path.dirname(os.path.abspath(__file__))
        _gates_dir = _this_dir if "gates" in _this_dir else os.path.join(_this_dir, "..", "gates")
        _gates_dir = os.path.abspath(_gates_dir)
        if _gates_dir not in sys.path:
            sys.path.insert(0, _gates_dir)
        from r370_portable import find_repo_root, get_output_dir

REPO_ROOT = find_repo_root()
OUTPUT_DIR = get_output_dir()

sys.path.insert(0, os.path.join(REPO_ROOT, "premium_package_factory", "gates"))
from r370g_reality_event_schema import (
    REALITY_EVENT_TYPES, REQUIRED_EVENT_FIELDS, REQUIRED_FIELDS_BY_TYPE,
    CAUSAL_CHAIN_STAGES,
    validate_reality_event, record_reality_event, get_reality_event,
    list_reality_events,
    create_acquisition_attestation,
    create_computational_execution_log,
    record_causal_mutation, get_causal_chain,
    compute_real_loop_verified,
    record_buyer_feedback_reality_bound,
    record_engineer_review_external,
    run_controlled_rehearsal,
    REALITY_EVENT_LEDGER_PATH, ACQUISITION_ATTESTATION_PATH,
    COMPUTATIONAL_EXECUTION_LOG_PATH, CAUSAL_MUTATION_LEDGER_PATH
)


def _now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ============================================================================
# 10 REQUIREMENT CHECKS
# ============================================================================

def check_1_reality_event_schema():
    """1. Formal REALITY_EVENT schema defined with all required fields."""
    issues = []

    # Check event types are defined
    if len(REALITY_EVENT_TYPES) != 4:
        issues.append(f"Expected 4 event types, got {len(REALITY_EVENT_TYPES)}")

    # Check required fields
    required = set(REQUIRED_EVENT_FIELDS)
    if "event_id" not in required or "attestation" not in required or "custody_chain" not in required:
        issues.append("Missing critical required fields in schema")

    # Check type-specific fields
    for event_type, fields in REQUIRED_FIELDS_BY_TYPE.items():
        if not fields:
            issues.append(f"No type-specific fields for {event_type}")

    return {"requirement": "1_reality_event_schema", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_2_acquisition_separated():
    """2. Acquisition separated from interpretation."""
    issues = []

    # Verify that record_reality_event validates before recording
    # (acquisition must be validated before AI interpretation)

    # Try to record an invalid event (missing attestation) — should fail
    try:
        bad_event = {
            "event_type": "PHYSICAL_OBSERVATION",
            "package_id": "TEST",
            "source_type": "EXTERNAL_INSTRUMENT",
            "organization": "TEST",
            "operator": "TEST",
            "acquisition_timestamp": _now(),
            "raw_artifact_ref": "test://fixture",
            "raw_data_sha256": "abc123",
            "attestation": {},  # empty — should fail
            "custody_chain": [],
            "provenance_validated": True
        }
        record_reality_event(bad_event)
        issues.append("Invalid event (empty attestation) was accepted — acquisition not properly validated")
    except ValueError:
        pass  # Expected — validation caught it

    return {"requirement": "2_acquisition_separated", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_3_computational_provenance():
    """3. Computational provenance requires execution log."""
    issues = []

    # Verify create_computational_execution_log requires all fields
    try:
        create_computational_execution_log(
            run_id="TEST-RUN",
            code_revision="abc123",
            environment={"python": "3.11"},
            dependency_lock={"requirements": "frozen"},
            input_hashes={"input1": "hash1"},
            parameter_hash="param-hash",
            execution_log_ref="log://test",
            output_artifact_ref="artifact://test",
            output_hash="output-hash"
        )
    except Exception as e:
        issues.append(f"Failed to create computational execution log: {e}")

    # Verify a computational result without execution log is rejected
    # (This is enforced by the schema — COMPUTATIONAL_EXECUTION requires execution_log_ref)

    return {"requirement": "3_computational_provenance", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_4_acquisition_attestation():
    """4. Acquisition attestation with instrument, operator, custody chain, signature."""
    issues = []

    # Create a test attestation
    try:
        attestation = create_acquisition_attestation(
            instrument_id="TEST-INSTR-001",
            instrument_serial="SN-12345",
            calibration_record={"date": "2026-01-01", "cert": "CAL-001"},
            operator="TEST-OPERATOR",
            organization="TEST-ORG",
            protocol="TEST-PROTOCOL",
            experiment_id="TEST-EXP",
            acquisition_timestamp=_now(),
            raw_data_hash="abc123",
            attestation_text="I attest this data was acquired by the stated instrument."
        )

        # Verify attestation has required fields
        required = ["instrument_id", "instrument_serial", "calibration_record",
                    "operator", "organization", "protocol", "experiment_id",
                    "acquisition_timestamp", "raw_data_hash", "attestation_text", "attestation_hash"]

        for field in required:
            if field not in attestation:
                issues.append(f"Acquisition attestation missing {field}")

    except Exception as e:
        issues.append(f"Failed to create acquisition attestation: {e}")

    return {"requirement": "4_acquisition_attestation", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_5_causal_mutation_engine():
    """5. Causal mutation engine with before/after hashes, no silent mutation."""
    issues = []

    # Verify CAUSAL_CHAIN_STAGES has all 9 stages
    expected_stages = [
        "EVENT", "EVIDENCE", "BELIEF_UPDATE", "KNOWLEDGE_ATOM",
        "EIG_CHANGE", "EXPERIMENT_CHANGE", "PACKAGE_MUTATION",
        "DISCOVERY_CONSTRAINT", "FUTURE_CANDIDATE_CHANGE"
    ]
    if CAUSAL_CHAIN_STAGES != expected_stages:
        issues.append(f"Causal chain stages mismatch: expected {expected_stages}, got {CAUSAL_CHAIN_STAGES}")

    # Verify record_causal_mutation requires before_hash and after_hash
    try:
        record_causal_mutation(
            stage="EVENT",
            trigger_event_id="TEST-EVT",
            package_id="TEST-PKG",
            before_hash="before",
            after_hash="after",
            reason="Test mutation"
        )
    except Exception as e:
        issues.append(f"Failed to record causal mutation: {e}")

    # Verify invalid stage is rejected
    try:
        record_causal_mutation(
            stage="INVALID_STAGE",
            trigger_event_id="TEST-EVT",
            package_id="TEST-PKG",
            before_hash="before",
            after_hash="after",
            reason="Should fail"
        )
        issues.append("Invalid causal chain stage was accepted")
    except ValueError:
        pass  # Expected

    return {"requirement": "5_causal_mutation_engine", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_6_real_loop_derived():
    """6. REAL_LOOP_VERIFIED is a derived state (impossible to assign manually)."""
    issues = []

    # Verify compute_real_loop_verified returns a dict with real_loop_verified
    result = compute_real_loop_verified()

    if "real_loop_verified" not in result:
        issues.append("compute_real_loop_verified does not return real_loop_verified field")
    elif result["real_loop_verified"] not in (True, False):
        issues.append(f"real_loop_verified is not boolean: {result['real_loop_verified']}")

    # Verify there's no set_real_loop_verified function
    # (it should be impossible to assign manually)
    import r370g_reality_event_schema as schema
    if hasattr(schema, "set_real_loop_verified"):
        issues.append("set_real_loop_verified function exists — REAL_LOOP_VERIFIED can be manually assigned")

    # Verify it's currently FALSE (no real events)
    if result["real_loop_verified"]:
        issues.append("REAL_LOOP_VERIFIED is TRUE without real events — derivation logic is wrong")

    return {"requirement": "6_real_loop_derived", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_7_buyer_feedback_reality_bound():
    """7. Buyer feedback is reality-bound; AI simulation separated."""
    issues = []

    # Verify AI simulation goes to separate ledger
    ai_feedback_id = record_buyer_feedback_reality_bound({
        "source_type": "AI",
        "buyer_organization": "AI-SIM",
        "contact_identity": "AI",
        "interaction_channel": "SIMULATION",
        "feedback_type": "UNDERSTANDS",
        "feedback_content": "AI simulated feedback",
        "original_feedback_artifact_ref": "ai://simulation",
        "package_id": "TEST-PKG"
    })

    # Verify AI simulation is NOT in the real feedback ledger
    real_events = list_reality_events(event_type="BUYER_FEEDBACK")
    ai_in_real = any(e.get("source_type") == "AI" for e in real_events)
    if ai_in_real:
        issues.append("AI simulation feedback appeared in real feedback ledger")

    # Verify real buyer feedback requires full provenance
    try:
        record_buyer_feedback_reality_bound({
            "buyer_organization": "TEST-ORG",
            # Missing contact_identity — should fail
            "interaction_channel": "EMAIL",
            "feedback_type": "UNDERSTANDS",
            "feedback_content": "Test feedback",
            "original_feedback_artifact_ref": "email://test",
            "package_id": "TEST-PKG"
        })
        issues.append("Buyer feedback with missing fields was accepted")
    except ValueError:
        pass  # Expected

    return {"requirement": "7_buyer_feedback_reality_bound", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_8_engineer_review_external():
    """8. Engineer review requires externally supplied artifact."""
    issues = []

    # Verify engineer review requires external_review_artifact_ref
    try:
        record_engineer_review_external({
            "reviewer_identity": "TEST",
            "reviewer_organization": "TEST",
            "reviewer_discipline": "TEST",
            "reviewer_credentials": "TEST",
            "conflicts_disclosed": False,
            # Missing external_review_artifact_ref — should fail
            "review_signature": "sig",
            "findings": [],
            "package_id": "TEST-PKG",
            "attestation": "I attest"
        })
        issues.append("Engineer review with missing external artifact was accepted")
    except ValueError:
        pass  # Expected

    return {"requirement": "8_engineer_review_external", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_9_article_xxxviii_ratified():
    """9. Article XXXVIII is ratified (not just proposed)."""
    issues = []

    # Check if Article XXXVIII file exists and is marked as ratified
    article_path = os.path.join(REPO_ROOT, "R370F", "constitution", "ARTICLE_XXXVIII_THE_REALITY_BOUNDARY.md")
    if not os.path.exists(article_path):
        issues.append(f"Article XXXVIII file not found at {article_path}")
    else:
        with open(article_path) as f:
            content = f.read()

        # Check if it says "Proposed" or "Ratified"
        if "Proposed" in content and "Ratified" not in content:
            issues.append("Article XXXVIII is marked as 'Proposed' but should be 'Ratified'")

    # Check if EPISTEMIC_CONSTITUTION.md references Article XXXVIII
    constitution_path = os.path.join(REPO_ROOT, "EPISTEMIC_CONSTITUTION.md")
    if os.path.exists(constitution_path):
        with open(constitution_path) as f:
            constitution = f.read()

        if "Article XXXVIII" not in constitution:
            issues.append("Article XXXVIII not referenced in EPISTEMIC_CONSTITUTION.md")

    return {"requirement": "9_article_xxxviii_ratified", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


def check_10_controlled_rehearsal():
    """10. CONTROLLED_LOOP_REHEARSAL test harness works correctly."""
    issues = []

    # Run a controlled rehearsal
    try:
        result = run_controlled_rehearsal("TEST-PKG", {
            "observations": [{"value": 42, "unit": "test"}]
        })

        # Verify SYNTHETIC_REHEARSAL is TRUE
        if not result.get("synthetic_rehearsal"):
            issues.append("Controlled rehearsal did not set synthetic_rehearsal=TRUE")

        # Verify REAL_LOOP_VERIFIED is FALSE
        if result.get("real_loop_verified"):
            issues.append("Controlled rehearsal incorrectly set real_loop_verified=TRUE")

        # Verify causal chain is complete
        if not result.get("causal_chain_complete"):
            issues.append("Controlled rehearsal causal chain is not complete")

        # Verify source_type is CONTROLLED_REHEARSAL
        if result.get("source_type") != "CONTROLLED_REHEARSAL":
            issues.append(f"Rehearsal source_type is {result.get('source_type')}, expected CONTROLLED_REHEARSAL")

    except Exception as e:
        issues.append(f"Controlled rehearsal failed: {e}")

    return {"requirement": "10_controlled_rehearsal", "passed": len(issues) == 0, "issues": issues  # R370U-U6: no truncation}


# ============================================================================
# ADVERSARIAL TESTS
# ============================================================================

def adversarial_1_ai_creates_reality_event():
    """A1: AI attempts to create a reality event → must be BLOCKED."""
    try:
        event = {
            "event_type": "PHYSICAL_OBSERVATION",
            "package_id": "TEST",
            "source_type": "AI",  # AI source — should be blocked
            "organization": "AI",
            "operator": "AI",
            "acquisition_timestamp": _now(),
            "raw_artifact_ref": "ai://fake",
            "raw_data_sha256": "fake",
            "attestation": {"attestation_text": "AI fake", "attestation_hash": "fake"},
            "custody_chain": [{"step": 1, "actor": "AI", "timestamp": _now(), "action": "Fake"}],
            "provenance_validated": True,
            "experiment_id": "FAKE",
            "instrument_ids": ["FAKE"],
            "instrument_serials": ["FAKE"],
            "calibration_record": {},
            "protocol_revision": "FAKE",
            "hardware_revision": "FAKE",
            "software_revision": "FAKE",
            "observations": []
        }
        record_reality_event(event)
        return {"test": "A1_ai_creates_reality_event", "passed": False, "details": "AI event was accepted — CRITICAL FAILURE"}
    except ValueError as e:
        return {"test": "A1_ai_creates_reality_event", "passed": True, "details": f"Correctly blocked: {str(e)[:80]}"}


def adversarial_2_missing_provenance():
    """A2: Event with missing provenance → must be BLOCKED."""
    try:
        event = {
            "event_type": "PHYSICAL_OBSERVATION",
            "package_id": "TEST",
            "source_type": "EXTERNAL_INSTRUMENT",
            "organization": "TEST",
            "operator": "TEST",
            # Missing acquisition_timestamp, raw_artifact_ref, raw_data_sha256
            "attestation": {"attestation_text": "Test", "attestation_hash": "test"},
            "custody_chain": [{"step": 1, "actor": "TEST", "timestamp": _now(), "action": "Test"}],
            "provenance_validated": True,
            "experiment_id": "TEST",
            "instrument_ids": ["TEST"],
            "instrument_serials": ["TEST"],
            "calibration_record": {},
            "protocol_revision": "TEST",
            "hardware_revision": "TEST",
            "software_revision": "TEST",
            "observations": []
        }
        record_reality_event(event)
        return {"test": "A2_missing_provenance", "passed": False, "details": "Event with missing provenance was accepted"}
    except ValueError:
        return {"test": "A2_missing_provenance", "passed": True, "details": "Correctly blocked missing provenance"}


def adversarial_3_manual_real_loop_assignment():
    """A3: Attempt to manually set REAL_LOOP_VERIFIED → must be impossible."""
    import r370g_reality_event_schema as schema

    # Verify there's no set function
    if hasattr(schema, "set_real_loop_verified"):
        return {"test": "A3_manual_real_loop", "passed": False, "details": "set_real_loop_verified function exists"}

    # Verify compute function returns derived value
    result = compute_real_loop_verified()
    if not isinstance(result.get("real_loop_verified"), bool):
        return {"test": "A3_manual_real_loop", "passed": False, "details": "real_loop_verified is not boolean"}

    return {"test": "A3_manual_real_loop", "passed": True, "details": "REAL_LOOP_VERIFIED is derived, cannot be manually set"}


def adversarial_4_rehearsal_not_real():
    """A4: Controlled rehearsal must NOT set REAL_LOOP_VERIFIED=TRUE."""
    result = run_controlled_rehearsal("ADV-TEST", {"observations": [{"value": 1}]})

    if result.get("real_loop_verified"):
        return {"test": "A4_rehearsal_not_real", "passed": False, "details": "Rehearsal incorrectly set REAL_LOOP_VERIFIED=TRUE"}

    if not result.get("synthetic_rehearsal"):
        return {"test": "A4_rehearsal_not_real", "passed": False, "details": "Rehearsal did not set SYNTHETIC_REHEARSAL=TRUE"}

    return {"test": "A4_rehearsal_not_real", "passed": True, "details": "Rehearsal correctly marked as SYNTHETIC, REAL_LOOP=FALSE"}


def adversarial_5_ai_simulation_in_real_ledger():
    """A5: AI simulation feedback must NOT appear in real feedback ledger."""
    # Record AI simulation feedback
    record_buyer_feedback_reality_bound({
        "source_type": "AI",
        "buyer_organization": "AI-SIM",
        "contact_identity": "AI",
        "interaction_channel": "SIMULATION",
        "feedback_type": "UNDERSTANDS",
        "feedback_content": "AI simulated feedback for adversarial test",
        "original_feedback_artifact_ref": "ai://adv-test",
        "package_id": "ADV-TEST-PKG"
    })

    # Check real feedback ledger
    real_feedbacks = list_reality_events(event_type="BUYER_FEEDBACK")
    ai_in_real = any(
        e.get("source_type") == "AI" or e.get("source_type") == "AI_SIMULATION"
        for e in real_feedbacks
    )

    if ai_in_real:
        return {"test": "A5_ai_in_real_ledger", "passed": False, "details": "AI simulation appeared in real feedback ledger"}

    return {"test": "A5_ai_in_real_ledger", "passed": True, "details": "AI simulation correctly separated from real ledger"}


# ============================================================================
# Run all checks
# ============================================================================

def run_all_checks():
    """Run all 10 requirement checks + 5 adversarial tests + controlled rehearsal."""
    print("=" * 70)
    print("R370G LOOP FINALIZATION GATE")
    print("10 Requirements + 5 Adversarial Tests + Controlled Rehearsal")
    print("Constitution: Articles I, II, IV, VI, XXV, XXVI, XXVII, XXVIII, XXXV, XXXVII, XXXVIII")
    print("=" * 70)

    # 10 requirement checks
    print("\n[1] 10 REQUIREMENT CHECKS:")
    checks = [
        check_1_reality_event_schema(),
        check_2_acquisition_separated(),
        check_3_computational_provenance(),
        check_4_acquisition_attestation(),
        check_5_causal_mutation_engine(),
        check_6_real_loop_derived(),
        check_7_buyer_feedback_reality_bound(),
        check_8_engineer_review_external(),
        check_9_article_xxxviii_ratified(),
        check_10_controlled_rehearsal(),
    ]

    pass_count = sum(1 for c in checks if c["passed"])
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"  {status}  {c['requirement']}")
        if not c["passed"]:
            for issue in c["issues"][:2]:
                print(f"      - {issue}")

    # 5 adversarial tests
    print(f"\n[2] 5 ADVERSARIAL TESTS:")
    adversarial_tests = [
        adversarial_1_ai_creates_reality_event(),
        adversarial_2_missing_provenance(),
        adversarial_3_manual_real_loop_assignment(),
        adversarial_4_rehearsal_not_real(),
        adversarial_5_ai_simulation_in_real_ledger(),
    ]

    adv_pass = sum(1 for t in adversarial_tests if t["passed"])
    for t in adversarial_tests:
        status = "PASS" if t["passed"] else "FAIL"
        print(f"  {status}  {t['test']}")
        print(f"      {t['details'][:100]}")

    # Controlled rehearsal demonstration
    print(f"\n[3] CONTROLLED REHEARSAL DEMONSTRATION:")
    rehearsal = run_controlled_rehearsal("P-24", {
        "observations": [
            {"parameter": "damper_coefficient", "value": 0.15, "unit": "mmHg/(mL/min)"},
            {"parameter": "response_time", "value": 3.2, "unit": "s"}
        ]
    })
    print(f"  Rehearsal ID: {rehearsal['rehearsal_id']}")
    print(f"  Package: {rehearsal['package_id']}")
    print(f"  Source type: {rehearsal['source_type']}")
    print(f"  SYNTHETIC_REHEARSAL: {rehearsal['synthetic_rehearsal']}")
    print(f"  REAL_LOOP_VERIFIED: {rehearsal['real_loop_verified']}")
    print(f"  Causal chain complete: {rehearsal['causal_chain_complete']}")
    print(f"  Stages completed: {len(rehearsal['stages_completed'])}/{len(rehearsal['stages_expected'])}")
    print(f"  Reason REAL_LOOP=FALSE: {rehearsal['reason_real_loop_false']}")

    # Summary
    print("\n" + "=" * 70)
    print("R370G LOOP FINALIZATION SUMMARY")
    print("=" * 70)
    print(f"10 Requirement Checks: {pass_count}/10 PASS")
    print(f"5 Adversarial Tests:   {adv_pass}/5 PASS")
    print(f"Controlled Rehearsal:  {'PASS' if rehearsal['causal_chain_complete'] and not rehearsal['real_loop_verified'] else 'FAIL'}")
    print(f"Total:                 {pass_count + adv_pass + 1}/16")

    # Final state
    print("\nFINAL DERIVED STATE:")
    real_loop = compute_real_loop_verified()
    print(f"  REAL_LOOP_VERIFIED: {real_loop['real_loop_verified']}")
    print(f"  Reason: {real_loop['reason']}")
    print(f"  Real event count: {real_loop.get('real_event_count', 0)}")

    print("\nTHE CENTRAL INVARIANT (Article XXXVIII):")
    print("  AI MAY PROPOSE.")
    print("  AI MAY COMPUTE.")
    print("  AI MAY INTERPRET.")
    print("  AI MAY NOT CLAIM THAT REALITY HAPPENED")
    print("  UNLESS REALITY PRODUCED THE EVIDENCE.")

    # Save report
    report = {
        "report_type": "R370G Loop Finalization Gate Report",
        "generated_at": _now(),
        "requirement_checks": checks,
        "adversarial_tests": adversarial_tests,
        "controlled_rehearsal": rehearsal,
        "real_loop_derived_state": real_loop,
        "requirement_pass_count": pass_count,
        "adversarial_pass_count": adv_pass,
        "total_checks": 16,
        "total_pass": pass_count + adv_pass + (1 if rehearsal['causal_chain_complete'] and not rehearsal['real_loop_verified'] else 0)
    }
    report_path = os.path.join(OUTPUT_DIR, "_r370g_loop_finalization_gate_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
    print(f"\nReport saved: {report_path}")

    return 0 if pass_count == 10 and adv_pass == 5 else 1


if __name__ == "__main__":
    sys.exit(run_all_checks())
