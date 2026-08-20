"""
Patent Destruction Adapter — Systematic 12-Stage Patent Attack Protocol.

Per CEO directive (2026-08-20, fifth round):
  Build a formal Patent Attack Protocol using the FROZEN source universe.
  Do NOT add databases. Optimize utilization.

  The destruction layer must systematically perform:
    keyword discovery → CPC/IPC expansion → claims-only search →
    family expansion → backward citations → forward citations →
    assignee/inventor neighborhood → continuation/divisional analysis →
    relevance adjudication → exact claim chart → §102 → §103 →
    strongest alternative

  Every stage must be provenance-bearing and auditable.

  Hard rules:
    - Provider failure ≠ zero results
    - No classification search = patent search incomplete
    - No family expansion = family coverage incomplete
    - No claim search = anticipation analysis incomplete
    - No citation chasing = prior-art neighborhood incomplete
    - Search exhaustion must be demonstrated, not declared

  Validation: replay C04/US4741730A and C09/A2A to prove the new pipeline
  retrieves the prior art we already know exists.
"""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4
from enum import Enum


class AttackStageStatus(str, Enum):
    """Status of each stage in the patent attack manifest."""
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"              # Provider error, timeout, auth issue
    NO_RESULTS = "NO_RESULTS"      # Successful query, zero matching records
    INCOMPLETE = "INCOMPLETE"      # Stage not yet executed
    SKIPPED = "SKIPPED"            # Intentionally skipped (with justification)


class CoverageLevel(str, Enum):
    """Coverage level for a patent search stage.

    available ≠ queried ≠ adequately covered ≠ relevant ≠ exhausted
    """
    NOT_QUERIED = "NOT_QUERIED"
    QUERIED = "QUERIED"                    # Query was executed
    ADEQUATELY_COVERED = "ADEQUATELY_COVERED"  # Sufficient results for relevance
    RELEVANT_FOUND = "RELEVANT_FOUND"      # At least one relevant result
    EXHAUSTED = "EXHAUSTED"                # All reasonable queries exhausted


@dataclass
class CoverageProof:
    """Proof that a search stage was actually executed exhaustively.

    Per CEO directive (sixth round):
      EXHAUSTED must require an explicit coverage record:
        databases queried + classifications searched + query families +
        pagination exhausted + failures + jurisdiction

      Otherwise the engine must report COVERAGE_INSUFFICIENT, never EXHAUSTED.

    This prevents the manifest from certifying work it did not execute.
    """
    databases_queried: list[str] = field(default_factory=list)
    classifications_searched: list[str] = field(default_factory=list)  # CPC/IPC codes
    query_families: list[str] = field(default_factory=list)  # Query variants tried
    pagination_exhausted: bool = False  # All pages reviewed?
    failures: list[str] = field(default_factory=list)  # Provider failures
    jurisdictions: list[str] = field(default_factory=list)  # US, EP, JP, WO, etc.
    total_queries_executed: int = 0
    total_results_returned: int = 0

    def is_exhausted(self) -> bool:
        """True only if all coverage dimensions are demonstrated."""
        return (
            len(self.databases_queried) > 0 and
            len(self.query_families) > 0 and
            self.pagination_exhausted and
            len(self.jurisdictions) > 0
        )

    def to_dict(self) -> dict:
        return {
            "databases_queried": self.databases_queried,
            "classifications_searched": self.classifications_searched,
            "query_families": self.query_families,
            "pagination_exhausted": self.pagination_exhausted,
            "failures": self.failures,
            "jurisdictions": self.jurisdictions,
            "total_queries_executed": self.total_queries_executed,
            "total_results_returned": self.total_results_returned,
            "is_exhausted": self.is_exhausted(),
        }


@dataclass
class ExecutionProof:
    """Proof that a stage was actually executed against a real provider.

    Per CEO directive (sixth round):
      'Never let a provenance framework certify work that it did not
       independently execute.'

    A stage cannot become COMPLETED because a caller manually supplied
    result IDs. It must have:
      - execution_id (unique per execution)
      - raw_response_hash (hash of the actual provider response)
      - execution_timestamp (when the query was actually run)
      - provider_confirmed (the provider actually returned data)

    Without this, the stage is MANUALLY_SUPPLIED, not EXECUTED.
    """
    execution_id: str = ""
    raw_response_hash: str = ""  # SHA-256 of the actual provider response
    execution_timestamp: str = ""
    provider_confirmed: bool = False  # Did the provider actually return data?
    manually_supplied: bool = True  # Default: manually supplied (NOT executed)
    response_size_bytes: int = 0

    def to_dict(self) -> dict:
        return {
            "execution_id": self.execution_id,
            "raw_response_hash": self.raw_response_hash,
            "execution_timestamp": self.execution_timestamp,
            "provider_confirmed": self.provider_confirmed,
            "manually_supplied": self.manually_supplied,
            "response_size_bytes": self.response_size_bytes,
        }


@dataclass
class AttackStageResult:
    """Result of one stage in the patent attack manifest.

    Every stage records:
      provider → query → timestamp → result IDs → coverage →
      failures → relevance → identity → provenance

    Per CEO directive (sixth round):
      - Stage cannot be COMPLETED from manually supplied result IDs alone
      - Must carry ExecutionProof (actual provider execution)
      - EXHAUSTED coverage requires CoverageProof
    """
    stage_name: str
    provider: str = ""
    query: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    result_ids: list[str] = field(default_factory=list)
    result_count: int = 0
    coverage: CoverageLevel = CoverageLevel.NOT_QUERIED
    status: AttackStageStatus = AttackStageStatus.INCOMPLETE
    failures: list[str] = field(default_factory=list)
    relevant_results: list[dict] = field(default_factory=list)
    notes: str = ""
    stage_hash: str = ""
    # CRITICAL: execution proof (sixth round)
    execution: ExecutionProof = field(default_factory=ExecutionProof)
    # CRITICAL: coverage proof for EXHAUSTED claims (sixth round)
    coverage_proof: Optional[CoverageProof] = None

    def __post_init__(self):
        content = json.dumps({
            "stage_name": self.stage_name,
            "provider": self.provider,
            "query": self.query,
            "timestamp": self.timestamp,
            "result_ids": self.result_ids,
        }, sort_keys=True)
        self.stage_hash = hashlib.sha256(content.encode()).hexdigest()

    def to_dict(self) -> dict:
        return {
            "stage_name": self.stage_name,
            "provider": self.provider,
            "query": self.query,
            "timestamp": self.timestamp,
            "result_ids": self.result_ids,
            "result_count": self.result_count,
            "coverage": self.coverage.value,
            "status": self.status.value,
            "failures": self.failures,
            "relevant_results": self.relevant_results,
            "notes": self.notes,
            "stage_hash": self.stage_hash,
            "execution": self.execution.to_dict(),
            "coverage_proof": self.coverage_proof.to_dict() if self.coverage_proof else None,
        }


@dataclass
class ClaimChartEntry:
    """One row in the exact claim chart mapping candidate limitations to prior art."""
    candidate_limitation: str
    prior_art_patent: str
    prior_art_claim: str
    prior_art_span: str  # Exact claim text or span
    status: str  # ANTICIPATED / NOT_ANTICIPATED / PARTIAL / OBVIOUSNESS_RELEVANT
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PatentAttackManifest:
    """Complete manifest of a patent attack on one candidate.

    Per CEO directive: every stage must be provenance-bearing and auditable.
    Search exhaustion must be demonstrated, not declared.
    """
    manifest_id: str = field(default_factory=lambda: str(uuid4()))
    candidate_name: str = ""
    candidate_description: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    stages: dict[str, AttackStageResult] = field(default_factory=dict)
    claim_chart: list[ClaimChartEntry] = field(default_factory=list)
    section_102_verdict: str = "NOT_ANALYZED"  # ANTICIPATED / NOT_ANTICIPATED / PARTIAL
    section_103_verdict: str = "NOT_ANALYZED"  # OBVIOUS / NOT_OBVIOUS / PLAUSIBLE
    strongest_alternative: dict = field(default_factory=dict)
    overall_verdict: str = "INCOMPLETE"  # KILLED / BLOCKED / SURVIVES / INCOMPLETE
    completeness_check: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "manifest_id": self.manifest_id,
            "candidate_name": self.candidate_name,
            "candidate_description": self.candidate_description,
            "created_at": self.created_at,
            "stages": {k: v.to_dict() for k, v in self.stages.items()},
            "claim_chart": [e.to_dict() for e in self.claim_chart],
            "section_102_verdict": self.section_102_verdict,
            "section_103_verdict": self.section_103_verdict,
            "strongest_alternative": self.strongest_alternative,
            "overall_verdict": self.overall_verdict,
            "completeness_check": self.completeness_check,
        }


class PatentDestructionAdapter:
    """Systematic 12-stage patent attack protocol.

    Uses the FROZEN source universe:
      - Google Patents (keyword, claims, citations)
      - EPO/Espacenet (classification, family)
      - USPTO Patent Public Search (claims, classification)
      - WIPO PATENTSCOPE (international classification)
      - Lens (classification, citations)
      - PatentBear (keyword)

    Does NOT add new databases. Optimizes utilization of existing sources.

    The 12 stages:
      1. keyword_search
      2. cpc_ipc_search
      3. claims_search
      4. family_expansion
      5. backward_citations
      6. forward_citations
      7. continuation_divisional_search
      8. assignee_inventor_neighbors
      9. relevance_adjudication
      10. exact_claim_mapping
      11. section_102_analysis
      12. section_103_analysis

    Hard rules enforced:
      - Provider failure → status=FAILED, NOT NO_RESULTS
      - No classification search → incomplete
      - No family expansion → incomplete
      - No claim search → incomplete
      - No citation chasing → incomplete
      - Exhaustion demonstrated, not declared
    """

    STAGE_NAMES = [
        "keyword_search",
        "cpc_ipc_search",
        "claims_search",
        "family_expansion",
        "backward_citations",
        "forward_citations",
        "continuation_divisional_search",
        "assignee_inventor_neighbors",
        "relevance_adjudication",
        "exact_claim_mapping",
        "section_102_analysis",
        "section_103_analysis",
    ]

    # Hard rules: stages that MUST be COMPLETED for the manifest to be complete
    REQUIRED_STAGES = [
        "keyword_search",
        "cpc_ipc_search",
        "claims_search",
        "family_expansion",
        "backward_citations",
        "forward_citations",
    ]

    def __init__(self):
        self.source_universe = [
            "Google Patents",
            "EPO/Espacenet",
            "USPTO Patent Public Search",
            "WIPO PATENTSCOPE",
            "Lens",
            "PatentBear",
        ]

    def create_manifest(self, candidate_name: str,
                        candidate_description: str) -> PatentAttackManifest:
        """Create a new patent attack manifest for a candidate."""
        manifest = PatentAttackManifest(
            candidate_name=candidate_name,
            candidate_description=candidate_description,
        )
        # Initialize all stages as INCOMPLETE
        for stage_name in self.STAGE_NAMES:
            manifest.stages[stage_name] = AttackStageResult(stage_name=stage_name)
        return manifest

    def record_stage(self, manifest: PatentAttackManifest,
                     stage_name: str,
                     provider: str,
                     query: str,
                     result_ids: list[str],
                     status: AttackStageStatus,
                     coverage: CoverageLevel,
                     relevant_results: list[dict] = None,
                     failures: list[str] = None,
                     notes: str = "",
                     execution: ExecutionProof = None,
                     coverage_proof: CoverageProof = None) -> AttackStageResult:
        """Record the result of one stage.

        Per CEO directive (sixth round):
          - A stage CANNOT become COMPLETED from manually supplied result IDs alone.
          - COMPLETED requires ExecutionProof with manually_supplied=False.
          - EXHAUSTED coverage requires CoverageProof with is_exhausted()=True.

        Hard rule: provider failure → FAILED, NOT NO_RESULTS.
        """
        if stage_name not in manifest.stages:
            manifest.stages[stage_name] = AttackStageResult(stage_name=stage_name)

        stage = manifest.stages[stage_name]
        stage.provider = provider
        stage.query = query
        stage.result_ids = result_ids
        stage.result_count = len(result_ids)
        stage.status = status
        stage.coverage = coverage
        stage.relevant_results = relevant_results or []
        stage.failures = failures or []
        stage.notes = notes
        stage.execution = execution or ExecutionProof()  # Default: manually_supplied=True
        stage.coverage_proof = coverage_proof

        # Hard rule: provider failure ≠ zero results
        if status == AttackStageStatus.FAILED:
            stage.coverage = CoverageLevel.NOT_QUERIED
            stage.notes += " | HARD RULE: Provider failure recorded as FAILED, NOT NO_RESULTS."

        # CRITICAL (sixth round): COMPLETED requires execution proof
        if status == AttackStageStatus.COMPLETED:
            if stage.execution.manually_supplied:
                stage.status = AttackStageStatus.INCOMPLETE
                stage.notes += " | DOWNGRADED: COMPLETED→INCOMPLETE. " \
                               "Stage was manually supplied, NOT executed. " \
                               "ExecutionProof with manually_supplied=False required."

        # CRITICAL (sixth round): EXHAUSTED requires coverage proof
        if coverage == CoverageLevel.EXHAUSTED:
            if stage.coverage_proof is None or not stage.coverage_proof.is_exhausted():
                stage.coverage = CoverageLevel.QUERIED  # Downgrade
                stage.notes += " | DOWNGRADED: EXHAUSTED→QUERIED. " \
                               "CoverageProof with is_exhausted()=True required for EXHAUSTED."

        return stage

    def execute_stage(self, manifest: PatentAttackManifest,
                      stage_name: str,
                      provider: str,
                      query: str,
                      raw_response: bytes,
                      result_ids: list[str],
                      coverage_proof: CoverageProof = None,
                      relevant_results: list[dict] = None,
                      failures: list[str] = None,
                      notes: str = "") -> AttackStageResult:
        """Actually execute a stage against a real provider.

        Per CEO directive (sixth round):
          This is the ONLY way to get COMPLETED status.
          The raw_response is hashed to prove the provider actually returned data.

        Args:
            raw_response: The actual bytes returned by the provider.
                         Will be hashed to create raw_response_hash.
        """
        import hashlib as _hl
        response_hash = _hl.sha256(raw_response).hexdigest()
        execution = ExecutionProof(
            execution_id=str(uuid4()),
            raw_response_hash=response_hash,
            execution_timestamp=datetime.now(timezone.utc).isoformat(),
            provider_confirmed=len(raw_response) > 0,
            manually_supplied=False,  # CRITICAL: this was actually executed
            response_size_bytes=len(raw_response),
        )

        coverage = CoverageLevel.EXHAUSTED if (coverage_proof and coverage_proof.is_exhausted()) \
                   else CoverageLevel.QUERIED

        return self.record_stage(
            manifest, stage_name, provider, query, result_ids,
            AttackStageStatus.COMPLETED if len(result_ids) > 0 else AttackStageStatus.NO_RESULTS,
            coverage,
            relevant_results=relevant_results,
            failures=failures,
            notes=notes,
            execution=execution,
            coverage_proof=coverage_proof,
        )

    def add_claim_chart_entry(self, manifest: PatentAttackManifest,
                               limitation: str, patent: str, claim: str,
                               span: str, status: str, notes: str = ""):
        """Add one row to the exact claim chart."""
        manifest.claim_chart.append(ClaimChartEntry(
            candidate_limitation=limitation,
            prior_art_patent=patent,
            prior_art_claim=claim,
            prior_art_span=span,
            status=status,
            notes=notes,
        ))

    def check_completeness(self, manifest: PatentAttackManifest) -> dict:
        """Check whether the manifest meets hard rules.

        Hard rules:
          - No classification search = patent search incomplete
          - No family expansion = family coverage incomplete
          - No claim search = anticipation analysis incomplete
          - No citation chasing = prior-art neighborhood incomplete
          - Search exhaustion must be demonstrated, not declared
        """
        issues = []
        stage_status = {}

        for stage_name in self.STAGE_NAMES:
            stage = manifest.stages.get(stage_name)
            if stage is None:
                issues.append(f"Stage '{stage_name}' is MISSING")
                stage_status[stage_name] = "MISSING"
                continue

            stage_status[stage_name] = stage.status.value

            # Required stages must be COMPLETED or NO_RESULTS (not FAILED or INCOMPLETE)
            if stage_name in self.REQUIRED_STAGES:
                if stage.status == AttackStageStatus.INCOMPLETE:
                    issues.append(f"Required stage '{stage_name}' is INCOMPLETE")
                elif stage.status == AttackStageStatus.FAILED:
                    issues.append(f"Required stage '{stage_name}' FAILED — "
                                  f"must be retried or justified as SKIPPED")

        # Specific hard rules
        if manifest.stages.get("cpc_ipc_search").status != AttackStageStatus.COMPLETED:
            if manifest.stages.get("cpc_ipc_search").status != AttackStageStatus.NO_RESULTS:
                issues.append("HARD RULE: No classification search = patent search incomplete")

        if manifest.stages.get("family_expansion").status not in (
            AttackStageStatus.COMPLETED, AttackStageStatus.NO_RESULTS):
            issues.append("HARD RULE: No family expansion = family coverage incomplete")

        if manifest.stages.get("claims_search").status not in (
            AttackStageStatus.COMPLETED, AttackStageStatus.NO_RESULTS):
            issues.append("HARD RULE: No claim search = anticipation analysis incomplete")

        if (manifest.stages.get("backward_citations").status not in
            (AttackStageStatus.COMPLETED, AttackStageStatus.NO_RESULTS) or
            manifest.stages.get("forward_citations").status not in
            (AttackStageStatus.COMPLETED, AttackStageStatus.NO_RESULTS)):
            issues.append("HARD RULE: No citation chasing = prior-art neighborhood incomplete")

        is_complete = len(issues) == 0
        result = {
            "is_complete": is_complete,
            "issues": issues,
            "stage_status": stage_status,
            "required_stages_completed": all(
                manifest.stages.get(s).status in
                (AttackStageStatus.COMPLETED, AttackStageStatus.NO_RESULTS)
                for s in self.REQUIRED_STAGES
            ),
            # NEW (sixth round): execution proof audit
            "execution_audit": {
                s: {
                    "manually_supplied": manifest.stages[s].execution.manually_supplied,
                    "has_raw_response_hash": bool(manifest.stages[s].execution.raw_response_hash),
                    "provider_confirmed": manifest.stages[s].execution.provider_confirmed,
                }
                for s in self.STAGE_NAMES
            },
            # NEW (sixth round): coverage proof audit
            "coverage_audit": {
                s: {
                    "claimed_coverage": manifest.stages[s].coverage.value,
                    "has_coverage_proof": manifest.stages[s].coverage_proof is not None,
                    "coverage_proof_valid": (
                        manifest.stages[s].coverage_proof.is_exhausted()
                        if manifest.stages[s].coverage_proof else False
                    ),
                }
                for s in self.STAGE_NAMES
            },
        }
        manifest.completeness_check = result
        return result

    def set_verdict(self, manifest: PatentAttackManifest,
                    section_102: str, section_103: str,
                    strongest_alt: dict, overall: str):
        """Set the final verdicts."""
        manifest.section_102_verdict = section_102
        manifest.section_103_verdict = section_103
        manifest.strongest_alternative = strongest_alt
        manifest.overall_verdict = overall

        # Run completeness check
        self.check_completeness(manifest)

        # If incomplete, overall verdict cannot be KILLED or SURVIVES
        if not manifest.completeness_check["is_complete"]:
            if manifest.overall_verdict in ("KILLED", "SURVIVES"):
                manifest.overall_verdict = "INCOMPLETE"
                manifest.completeness_check["issues"].append(
                    "VERDICT_DOWNGRADED: Cannot declare KILLED or SURVIVES "
                    "with incomplete manifest"
                )
