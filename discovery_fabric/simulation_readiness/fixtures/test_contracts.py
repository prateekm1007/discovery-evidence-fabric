"""
Test suite for simulation readiness contracts and blocking logic.

These are CONTRACT TESTS, not invention claims.
They verify that:
1. Complete fixtures reach SIMULATION_READY
2. Incomplete fixtures are blocked with SIMULATION_BLOCKED_MISSING_PARAMETERS
3. Non-falsifiable fixtures are blocked with SIMULATION_BLOCKED_NON_FALSIFIABLE
"""
import json
import hashlib
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import the adapter interface
from adapter_interface import (
    SimulationAdapter,
    BlockingStatus,
    JobStatus,
    ValidationResult
)


def load_fixture(fixture_name: str) -> dict:
    """Load a fixture JSON file."""
    # Fixtures are in the same directory as this test file
    fixture_path = Path(__file__).parent / f"{fixture_name}.json"
    with open(fixture_path, 'r') as f:
        return json.load(f)


def compute_hash(data: dict) -> str:
    """Compute SHA-256 hash of a dictionary."""
    canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode()).hexdigest()


class MockSimulationAdapter(SimulationAdapter):
    """Mock adapter for testing blocking logic without real engine integration."""
    
    def __init__(self):
        super().__init__(None)
        self._jobs = {}
    
    def submit(self, request: dict) -> 'JobID':
        # Check blocking status first
        blocking_status = self._check_blocking_status(request)
        
        if blocking_status == BlockingStatus.SIMULATION_BLOCKED_MISSING_PARAMETERS:
            raise ValueError(
                f"Cannot submit: {BlockingStatus.SIMULATION_BLOCKED_MISSING_PARAMETERS.value}. "
                f"Reason: {request.get('blocking_reason', 'Missing parameters')}"
            )
        
        if blocking_status == BlockingStatus.SIMULATION_BLOCKED_NON_FALSIFIABLE:
            raise ValueError(
                f"Cannot submit: {BlockingStatus.SIMULATION_BLOCKED_NON_FALSIFIABLE.value}. "
                f"Reason: {request.get('blocking_reason', 'Non-falsifiable prediction')}"
            )
        
        if blocking_status == BlockingStatus.SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION:
            raise ValueError(
                f"Cannot submit: {BlockingStatus.SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION.value}. "
                f"Reason: {request.get('blocking_reason', 'Unsupported assumptions')}")
        
        # Create a mock job ID
        from datetime import datetime, timezone
        from adapter_interface import EngineType, JobID
        
        job_id = JobID(
            job_id=f"mock_job_{compute_hash(request)[:16]}",
            engine_type=EngineType.OTHER,
            created_at=datetime.now(timezone.utc)
        )
        self._jobs[job_id.job_id] = {
            "request": request,
            "status": JobStatus.PENDING
        }
        return job_id
    
    def status(self, job_id: 'JobID') -> JobStatus:
        if job_id.job_id not in self._jobs:
            raise ValueError(f"Unknown job: {job_id.job_id}")
        return self._jobs[job_id.job_id]["status"]
    
    def retrieve(self, job_id: 'JobID') -> dict:
        if job_id.job_id not in self._jobs:
            raise ValueError(f"Unknown job: {job_id.job_id}")
        # Return empty result - this is just for testing blocking logic
        return {"result_id": job_id.job_id, "outputs": {"metric_values": []}}


def test_fixture_a_complete():
    """Fixture A should reach SIMULATION_READY status."""
    print("\n=== Testing Fixture A (Complete) ===")
    
    fixture = load_fixture("fixture_a_complete")
    request = fixture["simulation_request"]
    
    # Verify expected status
    assert request["blocking_status"] == "SIMULATION_READY", \
        f"Expected SIMULATION_READY, got {request['blocking_status']}"
    
    # Verify missing_parameters is empty
    assert len(request["missing_parameters"]) == 0, \
        f"Expected no missing parameters, got {request['missing_parameters']}"
    
    # Verify predicted_measurable_outcome has all required fields
    outcome = request["predicted_measurable_outcome"]
    assert outcome["metric"], "Metric must be specified"
    assert outcome["predicted_value"] is not None, "Predicted value must be specified"
    assert outcome["unit"], "Unit must be specified"
    assert outcome["baseline_value"] is not None, "Baseline value must be specified"
    
    # Try to submit with mock adapter
    adapter = MockSimulationAdapter()
    try:
        job_id = adapter.submit(request)
        print(f"✓ Fixture A submitted successfully: {job_id.job_id}")
        print(f"✓ Status: SIMULATION_READY")
        return True
    except ValueError as e:
        print(f"✗ Fixture A submission failed: {e}")
        return False


def test_fixture_b_incomplete():
    """Fixture B should be blocked with SIMULATION_BLOCKED_MISSING_PARAMETERS."""
    print("\n=== Testing Fixture B (Incomplete) ===")
    
    fixture = load_fixture("fixture_b_incomplete")
    request = fixture["simulation_request"]
    
    # Verify expected status
    assert request["blocking_status"] == "SIMULATION_BLOCKED_MISSING_PARAMETERS", \
        f"Expected SIMULATION_BLOCKED_MISSING_PARAMETERS, got {request['blocking_status']}"
    
    # Verify missing_parameters is non-empty
    assert len(request["missing_parameters"]) > 0, \
        "Expected missing parameters, got empty list"
    
    # Verify blocking reason is provided
    assert request["blocking_reason"], "Blocking reason must be provided"
    
    # Try to submit - should fail
    adapter = MockSimulationAdapter()
    try:
        job_id = adapter.submit(request)
        print(f"✗ Fixture B should have been blocked but was submitted: {job_id.job_id}")
        return False
    except ValueError as e:
        if "SIMULATION_BLOCKED_MISSING_PARAMETERS" in str(e):
            print(f"✓ Fixture B correctly blocked: SIMULATION_BLOCKED_MISSING_PARAMETERS")
            print(f"  Reason: {request['blocking_reason']}")
            print(f"  Missing parameters: {len(request['missing_parameters'])} items")
            return True
        else:
            print(f"✗ Fixture B blocked with wrong error: {e}")
            return False


def test_fixture_c_non_falsifiable():
    """Fixture C should be blocked with SIMULATION_BLOCKED_NON_FALSIFIABLE."""
    print("\n=== Testing Fixture C (Non-Falsifiable) ===")
    
    fixture = load_fixture("fixture_c_non_falsifiable")
    request = fixture["simulation_request"]
    
    # Verify expected status
    assert request["blocking_status"] == "SIMULATION_BLOCKED_NON_FALSIFIABLE", \
        f"Expected SIMULATION_BLOCKED_NON_FALSIFIABLE, got {request['blocking_status']}"
    
    # Verify predicted_measurable_outcome is invalid
    outcome = request["predicted_measurable_outcome"]
    assert not outcome["metric"] or outcome["metric"] in ["durability", "performance"], \
        "Non-falsifiable metrics should be vague"
    assert outcome["predicted_value"] is None, "Predicted value should be null for non-falsifiable"
    assert not outcome["unit"], "Unit should be empty for non-falsifiable"
    
    # Verify blocking reason is provided
    assert request["blocking_reason"], "Blocking reason must be provided"
    
    # Try to submit - should fail
    adapter = MockSimulationAdapter()
    try:
        job_id = adapter.submit(request)
        print(f"✗ Fixture C should have been blocked but was submitted: {job_id.job_id}")
        return False
    except ValueError as e:
        if "SIMULATION_BLOCKED_NON_FALSIFIABLE" in str(e):
            print(f"✓ Fixture C correctly blocked: SIMULATION_BLOCKED_NON_FALSIFIABLE")
            print(f"  Reason: {request['blocking_reason']}")
            return True
        else:
            print(f"✗ Fixture C blocked with wrong error: {e}")
            return False


def test_validation_result():
    """Test the ValidationResult class."""
    print("\n=== Testing ValidationResult ===")
    
    adapter = MockSimulationAdapter()
    
    # Valid result
    valid_result = {
        "result_id": "test_001",
        "request_reference": "req_001",
        "engine_info": {"engine_name": "OTHER", "engine_version": "1.0"},
        "job_status": "COMPLETED",
        "completion_timestamp": "2026-08-14T00:00:00Z",
        "outputs": {"metric_values": [{"metric_name": "stress", "value": 100, "unit": "Pa"}]},
        "provenance": {
            "request_hash": "abc123",
            "submission_timestamp": "2026-08-14T00:00:00Z",
            "retrieval_timestamp": "2026-08-14T00:00:00Z",
            "engine_run_id": "run_001"
        }
    }
    
    validation = adapter.validate(valid_result)
    assert validation.valid, "Valid result should pass validation"
    print(f"✓ Valid result passes validation: {validation.checks_passed}")
    
    # Invalid result (missing provenance)
    invalid_result = {
        "result_id": "test_002",
        "request_reference": "req_002",
        "job_status": "COMPLETED"
        # Missing engine_info, outputs, provenance
    }
    
    validation = adapter.validate(invalid_result)
    assert not validation.valid, "Invalid result should fail validation"
    print(f"✓ Invalid result fails validation: {validation.checks_failed}")
    
    return True


def test_provenance_chain():
    """Test that provenance chain is preserved from candidate to request."""
    print("\n=== Testing Provenance Chain ===")
    
    fixture = load_fixture("fixture_a_complete")
    candidate = fixture["automated_invention_candidate"]
    request = fixture["simulation_request"]
    
    # Verify candidate reference matches
    assert request["candidate_reference"] == candidate["candidate_id"], \
        "Request must reference parent candidate"
    
    # Verify provenance includes candidate hash
    assert "candidate_hash" in request["provenance"], \
        "Request provenance must include candidate hash"
    
    # Verify source hashes are preserved
    assert len(candidate["source_hashes"]) > 0, \
        "Candidate must have source hashes"
    
    print(f"✓ Provenance chain preserved:")
    print(f"  Candidate ID: {candidate['candidate_id']}")
    print(f"  Request references: {request['candidate_reference']}")
    print(f"  Source hashes: {len(candidate['source_hashes'])} sources")
    
    return True


def test_fixture_d_unsupported_assumption():
    """Fixture D should be blocked with SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION."""
    print("\n=== Testing Fixture D (Unsupported Assumption) ===")
    
    fixture = load_fixture("fixture_d_unsupported_assumption")
    request = fixture["simulation_request"]
    
    # Verify expected status
    assert request["blocking_status"] == "SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION", \
        f"Expected SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION, got {request['blocking_status']}"
    
    # Verify unsupported_assumptions is non-empty
    assert len(request.get("unsupported_assumptions", [])) > 0, \
        "Expected unsupported assumptions, got empty list"
    
    # Verify blocking reason is provided
    assert request["blocking_reason"], "Blocking reason must be provided"
    
    # Try to submit - should fail
    adapter = MockSimulationAdapter()
    try:
        job_id = adapter.submit(request)
        print(f"✗ Fixture D should have been blocked but was submitted: {job_id.job_id}")
        return False
    except ValueError as e:
        if "SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION" in str(e):
            print(f"✓ Fixture D correctly blocked: SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION")
            print(f"  Reason: {request['blocking_reason']}")
            print(f"  Unsupported assumptions: {len(request['unsupported_assumptions'])} items")
            return True
        else:
            print(f"✗ Fixture D blocked with wrong error: {e}")
            return False


def run_all_tests():
    """Run all contract tests."""
    print("=" * 60)
    print("SIMULATION READINESS CONTRACT TESTS")
    print("=" * 60)
    
    results = {
        "fixture_a_complete": test_fixture_a_complete(),
        "fixture_b_incomplete": test_fixture_b_incomplete(),
        "fixture_c_non_falsifiable": test_fixture_c_non_falsifiable(),
        "fixture_d_unsupported_assumption": test_fixture_d_unsupported_assumption(),
        "validation_result": test_validation_result(),
        "provenance_chain": test_provenance_chain()
    }
    
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ ALL CONTRACT TESTS PASSED")
        return True
    else:
        print("\n✗ SOME CONTRACT TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)
