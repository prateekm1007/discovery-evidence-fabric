"""
epistemic_integrity/claim_registry.py — Claim ID assignment + storage + lookup

Every sentence eligible for the final dossier becomes a Claim with:
  - claim_id (CLM-CV<T#>-<seq>)
  - text
  - epistemic_class
  - evidence_ids (list of EXP-IDs that support this claim)
  - source_ids (list of SRC-IDs from external sources)
  - simulation_commit (git commit hash of the simulation that produced this)
  - allowed_wording (from evidence_classes.MANDATORY_WORDING)
  - human_fact (bool — has a human verified this?)
  - supersession_status (CURRENT / SUPERSEDED / INVALIDATED / HISTORICAL / FROZEN)
  - superseded_by (claim_id that replaces this, if any)

The dossier compiler MUST reject any CLAIM without EVIDENCE_BINDING.
No exceptions.
"""

import json
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone

from .evidence_classes import EvidenceClass, validate_wording, can_support_claims


CLAIM_ID_PATTERN = re.compile(r"^CLM-CV-T(\d+)-(\d+)$")


@dataclass
class Claim:
    claim_id: str  # CLM-CV-T<territory>-<sequence>
    text: str
    epistemic_class: EvidenceClass
    territory_id: str  # CV-T01, CV-T02, etc.
    evidence_ids: List[str] = field(default_factory=list)  # EXP-IDs
    source_ids: List[str] = field(default_factory=list)  # SRC-IDs
    simulation_commit: Optional[str] = None  # git commit hash
    simulation_output_hash: Optional[str] = None  # SHA256 of simulation output JSON
    human_fact: bool = False
    supersession_status: str = "CURRENT"  # CURRENT/SUPERSEDED/INVALIDATED/HISTORICAL/FROZEN
    superseded_by: Optional[str] = None
    invalidated_by: Optional[str] = None
    reason: str = ""  # reason for supersession/invalidation
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    validated: bool = False  # has passed validation
    validation_errors: List[str] = field(default_factory=list)


class ClaimRegistry:
    """In-memory + on-disk registry of all canonical claims."""

    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.claims: Dict[str, Claim] = {}
        self._load()

    def _registry_file(self) -> Path:
        return self.registry_dir / "claim_registry.json"

    def _load(self):
        path = self._registry_file()
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for claim_data in data.get("claims", []):
                # Convert epistemic_class string back to enum
                claim_data["epistemic_class"] = EvidenceClass(claim_data["epistemic_class"])
                claim = Claim(**claim_data)
                self.claims[claim.claim_id] = claim

    def _save(self):
        path = self._registry_file()
        data = {
            "schema_version": "1.0.0",
            "claims": [asdict(c) for c in self.claims.values()],
        }
        # Convert enums to strings for JSON
        for c in data["claims"]:
            c["epistemic_class"] = c["epistemic_class"].value
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def next_claim_id(self, territory_id: str) -> str:
        """Generate next sequential claim ID for a territory."""
        # Extract territory number (CV-T01 → 01)
        match = re.match(r"CV-T(\d+)", territory_id)
        if not match:
            raise ValueError(f"Invalid territory_id: {territory_id}")
        t_num = match.group(1)

        # Find max sequence for this territory
        existing = [c for c in self.claims if f"CV-T{t_num}" in c]
        if not existing:
            return f"CLM-CV-T{t_num}-00001"
        max_seq = max(int(c.split("-")[-1]) for c in existing)
        return f"CLM-CV-T{t_num}-{max_seq+1:05d}"

    def register_claim(
        self,
        text: str,
        epistemic_class: EvidenceClass,
        territory_id: str,
        evidence_ids: List[str] = None,
        source_ids: List[str] = None,
        simulation_commit: str = None,
        simulation_output_hash: str = None,
        human_fact: bool = False,
    ) -> Claim:
        """Register a new claim. Auto-assigns claim_id."""
        if evidence_ids is None:
            evidence_ids = []
        if source_ids is None:
            source_ids = []

        claim_id = self.next_claim_id(territory_id)
        claim = Claim(
            claim_id=claim_id,
            text=text,
            epistemic_class=epistemic_class,
            territory_id=territory_id,
            evidence_ids=evidence_ids,
            source_ids=source_ids,
            simulation_commit=simulation_commit,
            simulation_output_hash=simulation_output_hash,
            human_fact=human_fact,
        )
        self.claims[claim_id] = claim
        self._save()
        return claim

    def validate_claim(self, claim_id: str) -> dict:
        """Validate a claim against all epistemic rules.

        Returns dict with:
          - valid: bool
          - errors: list of specific violations
        """
        if claim_id not in self.claims:
            return {"valid": False, "errors": [f"CLAIM_NOT_FOUND: {claim_id}"]}

        claim = self.claims[claim_id]
        errors = []

        # Rule 1: Every claim MUST have at least one evidence binding
        if not claim.evidence_ids and not claim.source_ids:
            errors.append("MISSING_EVIDENCE_BINDING: claim has no evidence_ids and no source_ids")

        # Rule 2: SUPERSEDED evidence cannot support current claims
        if claim.supersession_status == "SUPERSEDED":
            errors.append("CLAIM_SUPERSEDED: cannot be used as current evidence")
        if claim.supersession_status == "INVALIDATED":
            errors.append("CLAIM_INVALIDATED: cannot be used as current evidence")

        # Rule 3: Epistemic class must be valid for dossier
        if not can_support_claims(claim.epistemic_class):
            errors.append(f"EPISTEMIC_CLASS_CANNOT_SUPPORT: {claim.epistemic_class}")

        # Rule 4: Wording must match epistemic class
        wording_check = validate_wording(claim.text, claim.epistemic_class)
        if not wording_check["valid"]:
            errors.extend(wording_check["violations"])

        # Rule 5: SIMULATION_DERIVED claims MUST have simulation_commit
        if claim.epistemic_class == EvidenceClass.SIMULATION_DERIVED:
            if not claim.simulation_commit:
                errors.append("SIMULATION_DERIVED_REQUIRES_COMMIT: simulation_commit is None")
            if not claim.simulation_output_hash:
                errors.append("SIMULATION_DERIVED_REQUIRES_OUTPUT_HASH: simulation_output_hash is None")

        # Rule 6: MODEL_DERIVED claims MUST have simulation_commit (code that produced the model)
        if claim.epistemic_class == EvidenceClass.MODEL_DERIVED:
            if not claim.simulation_commit:
                errors.append("MODEL_DERIVED_REQUIRES_COMMIT: simulation_commit is None")

        # Rule 7: PRIMARY_OBSERVED claims MUST have at least one evidence_id (our own experiment)
        if claim.epistemic_class == EvidenceClass.PRIMARY_OBSERVED:
            if not claim.evidence_ids:
                errors.append("PRIMARY_OBSERVED_REQUIRES_EVIDENCE_ID: must have at least one EXP-ID")

        # Rule 8: SECONDARY_REPORTED claims MUST have at least one source_id (external)
        if claim.epistemic_class == EvidenceClass.SECONDARY_REPORTED:
            if not claim.source_ids:
                errors.append("SECONDARY_REPORTED_REQUIRES_SOURCE_ID: must have at least one SRC-ID")

        claim.validated = len(errors) == 0
        claim.validation_errors = errors
        self._save()

        return {"valid": claim.validated, "errors": errors}

    def supersede_claim(self, claim_id: str, superseded_by: str, reason: str):
        """Mark a claim as SUPERSEDED by another claim."""
        if claim_id not in self.claims:
            raise KeyError(f"Claim not found: {claim_id}")
        claim = self.claims[claim_id]
        claim.supersession_status = "SUPERSEDED"
        claim.superseded_by = superseded_by
        claim.reason = reason
        self._save()

    def invalidate_claim(self, claim_id: str, invalidated_by: str, reason: str):
        """Mark a claim as INVALIDATED (stronger than SUPERSEDED — was wrong)."""
        if claim_id not in self.claims:
            raise KeyError(f"Claim not found: {claim_id}")
        claim = self.claims[claim_id]
        claim.supersession_status = "INVALIDATED"
        claim.invalidated_by = invalidated_by
        claim.reason = reason
        self._save()

    def get_current_claims(self, territory_id: str = None) -> List[Claim]:
        """Get all CURRENT (non-superseded, non-invalidated) claims.
        Optionally filtered by territory."""
        result = []
        for claim in self.claims.values():
            if claim.supersession_status != "CURRENT":
                continue
            if territory_id and claim.territory_id != territory_id:
                continue
            result.append(claim)
        return result

    def get_approved_claims(self, territory_id: str = None) -> List[Claim]:
        """Get all claims that PASSED validation AND are CURRENT."""
        current = self.get_current_claims(territory_id)
        return [c for c in current if c.validated]
