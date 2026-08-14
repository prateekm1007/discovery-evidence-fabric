"""
Simulation Adapter Interface — NOT a simulation engine.

This module defines the interface for submitting simulation requests to external
physics/engineering engines (Ansys, SimScale, Siemens, Altair, Quanscient, etc.).

DO NOT:
- Integrate paid APIs
- Scrape commercial simulation websites
- Create fake simulation results
- Build a physics solver

The interface allows:
- submit(request) -> JobID
- status(job_id) -> JobStatus
- retrieve(job_id) -> SimulationResult
- validate(result) -> ValidationResult

Every result has provenance attached.
"""
from __future__ import annotations
import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List


class EngineType(Enum):
    """Supported simulation engine types."""
    ANSYS_MECHANICAL = "ANSYS_MECHANICAL"
    ANSYS_FLUENT = "ANSYS_FLUENT"
    SIMSCALE = "SIMSCALE"
    SIEMENS_NX_NASTRAN = "SIEMENS_NX_NASTRAN"
    SIEMENS_STAR_CCM = "SIEMENS_STAR_CCM"
    ALTAIR_HYPERWORKS = "ALTAIR_HYPERWORKS"
    ALTAIR_OPTISTRUCT = "ALTAIR_OPTISTRUCT"
    QUANSCIENT = "QUANSCIENT"
    OTHER = "OTHER"


class JobStatus(Enum):
    """Simulation job status."""
    PENDING = "PENDING"
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    WARNING = "WARNING"
    DID_NOT_CONVERGE = "DID_NOT_CONVERGE"
    PARTIAL_RESULTS = "PARTIAL_RESULTS"
    CANCELLED = "CANCELLED"


class BlockingStatus(Enum):
    """Request blocking status."""
    SIMULATION_READY = "SIMULATION_READY"
    SIMULATION_BLOCKED_MISSING_PARAMETERS = "SIMULATION_BLOCKED_MISSING_PARAMETERS"
    SIMULATION_BLOCKED_NON_FALSIFIABLE = "SIMULATION_BLOCKED_NON_FALSIFIABLE"
    SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION = "SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION"


@dataclass
class JobID:
    """Unique identifier for a simulation job."""
    job_id: str
    engine_type: EngineType
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "engine_type": self.engine_type.value,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ValidationResult:
    """Result of validating a simulation result."""
    valid: bool
    checks_passed: List[str] = field(default_factory=list)
    checks_failed: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    provenance_verified: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "valid": self.valid,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "warnings": self.warnings,
            "provenance_verified": self.provenance_verified
        }


class SimulationAdapter(ABC):
    """
    Abstract base class for simulation engine adapters.
    
    Concrete implementations must be built for each supported engine:
    - AnsysMechanicalAdapter
    - SimScaleAdapter
    - SiemensNXNastranAdapter
    - etc.
    
    DO NOT implement a fake solver or mock results.
    """
    
    def __init__(self, engine_type: EngineType, config: Optional[Dict[str, Any]] = None):
        self.engine_type = engine_type
        self.config = config or {}
        self._request_log: Dict[str, Dict[str, Any]] = {}
        self._result_log: Dict[str, Dict[str, Any]] = {}
    
    @abstractmethod
    def submit(self, request: Dict[str, Any]) -> JobID:
        """
        Submit a simulation request to the external engine.
        
        Args:
            request: SimulationRequest dict conforming to simulation_request_schema.json
            
        Returns:
            JobID for tracking the job
            
        Raises:
            ValueError: If request is blocked (missing parameters or non-falsifiable)
            ConnectionError: If engine is unreachable
        """
        pass
    
    @abstractmethod
    def status(self, job_id: JobID) -> JobStatus:
        """
        Check the status of a submitted job.
        
        Args:
            job_id: JobID returned from submit()
            
        Returns:
            Current job status
        """
        pass
    
    @abstractmethod
    def retrieve(self, job_id: JobID) -> Dict[str, Any]:
        """
        Retrieve simulation results for a completed job.
        
        Args:
            job_id: JobID returned from submit()
            
        Returns:
            SimulationResult dict conforming to simulation_result_schema.json
            
        Raises:
            ValueError: If job is not yet completed
        """
        pass
    
    def validate(self, result: Dict[str, Any]) -> ValidationResult:
        """
        Validate a simulation result for provenance and consistency.
        
        This is a default implementation that can be overridden by subclasses
        for engine-specific validation.
        
        Args:
            result: SimulationResult dict
            
        Returns:
            ValidationResult with validation checks
        """
        checks_passed = []
        checks_failed = []
        warnings = []
        
        # Check required fields
        required_fields = ["result_id", "request_reference", "engine_info", 
                          "job_status", "completion_timestamp", "outputs", "provenance"]
        for field_name in required_fields:
            if field_name in result:
                checks_passed.append(f"required_field:{field_name}")
            else:
                checks_failed.append(f"required_field:{field_name}")
        
        # Verify provenance hash
        if "provenance" in result and "request_hash" in result["provenance"]:
            checks_passed.append("provenance:request_hash_present")
        else:
            checks_failed.append("provenance:request_hash_missing")
        
        # Check job status
        if result.get("job_status") == "COMPLETED":
            checks_passed.append("job_status:completed")
        elif result.get("job_status") in ["WARNING", "PARTIAL_RESULTS"]:
            warnings.append("job_completed_with_warnings")
            checks_passed.append("job_status:completed_with_warnings")
        else:
            checks_failed.append(f"job_status:not_completed:{result.get('job_status')}")
        
        # Verify outputs exist
        if "outputs" in result and "metric_values" in result["outputs"]:
            if len(result["outputs"]["metric_values"]) > 0:
                checks_passed.append("outputs:metric_values_present")
            else:
                warnings.append("outputs:no_metric_values")
        else:
            checks_failed.append("outputs:metric_values_missing")
        
        valid = len(checks_failed) == 0
        
        return ValidationResult(
            valid=valid,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            warnings=warnings,
            provenance_verified="provenance:request_hash_present" in checks_passed
        )
    
    def _compute_hash(self, data: Dict[str, Any]) -> str:
        """Compute SHA-256 hash of a dictionary."""
        canonical = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def _check_blocking_status(self, request: Dict[str, Any]) -> BlockingStatus:
        """
        Check if request should be blocked.
        
        Returns SIMULATION_BLOCKED_MISSING_PARAMETERS if missing_parameters is non-empty.
        Returns SIMULATION_BLOCKED_NON_FALSIFIABLE if predicted_measurable_outcome is invalid.
        Returns SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION if unsupported_assumptions is non-empty.
        Returns SIMULATION_READY otherwise.
        """
        missing_params = request.get("missing_parameters", [])
        if missing_params and len(missing_params) > 0:
            return BlockingStatus.SIMULATION_BLOCKED_MISSING_PARAMETERS
        
        # Check for unsupported assumptions (invented parameters)
        unsupported_assumptions = request.get("unsupported_assumptions", [])
        if unsupported_assumptions and len(unsupported_assumptions) > 0:
            return BlockingStatus.SIMULATION_BLOCKED_UNSUPPORTED_ASSUMPTION
        
        # Check falsifiability
        predicted_outcome = request.get("predicted_measurable_outcome", {})
        if not predicted_outcome:
            return BlockingStatus.SIMULATION_BLOCKED_NON_FALSIFIABLE
        
        metric = predicted_outcome.get("metric", "")
        predicted_value = predicted_outcome.get("predicted_value")
        unit = predicted_outcome.get("unit", "")
        
        if not metric or predicted_value is None or not unit:
            return BlockingStatus.SIMULATION_BLOCKED_NON_FALSIFIABLE
        
        return BlockingStatus.SIMULATION_READY


# Placeholder implementation that raises NotImplementedError
# This prevents accidental use without a real engine adapter
class NotImplementedAdapter(SimulationAdapter):
    """
    Placeholder adapter that always raises NotImplementedError.
    
    This prevents accidental simulation attempts without a real engine integration.
    """
    
    def submit(self, request: Dict[str, Any]) -> JobID:
        raise NotImplementedError(
            "No simulation engine adapter configured. "
            "Implement a concrete adapter for Ansys, SimScale, Siemens, Altair, or Quanscient."
        )
    
    def status(self, job_id: JobID) -> JobStatus:
        raise NotImplementedError("No simulation engine adapter configured.")
    
    def retrieve(self, job_id: JobID) -> Dict[str, Any]:
        raise NotImplementedError("No simulation engine adapter configured.")
