"""
epistemic_integrity/dossier_firewall.py — The dossier generator security boundary

Per CEO directive:
  "The dossier generator itself must become a security boundary.
   Do NOT let the final dossier generator query arbitrary files.
   It should only receive:
     CANONICAL_STATE + APPROVED_CLAIMS + APPROVED_EVIDENCE + APPROVED_PROVENANCE
   The dossier generator must have NO direct filesystem authority over raw historical artifacts."

Architecture:
  Repository
     ↓
  Evidence ingestion
     ↓
  Claim extraction
     ↓
  Claim verification
     ↓
  Epistemic classification
     ↓
  Supersession resolution
     ↓
  Canonical current state
     ↓
  DOSSIER FIREWALL  ← THIS MODULE
     ↓
  Dossier

The firewall exposes ONLY:
  - get_approved_claims(territory_id)
  - get_approved_evidence(claim_id)
  - get_approved_sources(claim_id)
  - render_dossier_claim(claim_id)
  - render_dossier_section(territory_id)

Any attempt to bypass the firewall (e.g. read raw files) MUST fail.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from .claim_registry import ClaimRegistry, Claim
from .evidence_binding import EvidenceBinding, Evidence, Source
from .supersession_engine import SupersessionEngine
from .evidence_classes import EvidenceClass, MANDATORY_WORDING, validate_wording


@dataclass
class RenderedClaim:
    """A claim rendered for the final dossier, with provenance metadata attached."""
    claim_id: str
    text: str
    epistemic_class: str
    allowed_wording: List[str]
    evidence_count: int
    source_count: int
    simulation_commit: Optional[str]
    simulation_output_hash: Optional[str]
    human_fact: bool
    provenance_chain: str  # human-readable chain


class DossierFirewall:
    """The ONLY interface the dossier generator is allowed to use."""

    def __init__(
        self,
        canonical_state_dir: Path,
        claim_registry_dir: Path,
        evidence_registry_dir: Path,
        supersession_registry_dir: Path,
    ):
        self.canonical_state_dir = Path(canonical_state_dir)
        self.claim_registry = ClaimRegistry(claim_registry_dir)
        self.evidence_binding = EvidenceBinding(evidence_registry_dir)
        self.supersession_engine = SupersessionEngine(supersession_registry_dir)

        # Load canonical state
        self.canonical_state = self._load_canonical_state()

    def _load_canonical_state(self) -> dict:
        path = self.canonical_state_dir / "PORTFOLIO.json"
        if not path.exists():
            raise FileNotFoundError(f"Canonical state not found: {path}")
        with open(path) as f:
            return json.load(f)

    def get_territory_state(self, territory_id: str) -> dict:
        """Get the canonical current state for a territory."""
        for t in self.canonical_state.get("territories", []):
            if t["id"] == territory_id:
                return t
        raise KeyError(f"Territory not found in canonical state: {territory_id}")

    def get_approved_claims(self, territory_id: str) -> List[Claim]:
        """Get all CURRENT, VALIDATED claims for a territory.

        This is the ONLY way the dossier generator should access claims.
        Raw claim_registry access is FORBIDDEN for the dossier generator.
        """
        approved = self.claim_registry.get_approved_claims(territory_id)

        # Double-check: filter out any claim whose evidence is SUPERSEDED
        result = []
        for claim in approved:
            evidence = self.evidence_binding.get_evidence_for_claim(claim.claim_id)
            if any(not self.supersession_engine.is_current(e.evidence_id) for e in evidence):
                continue  # skip claims with superseded evidence
            result.append(claim)
        return result

    def get_approved_evidence(self, claim_id: str) -> List[Evidence]:
        """Get CURRENT evidence supporting a claim."""
        evidence = self.evidence_binding.get_evidence_for_claim(claim_id)
        return [e for e in evidence if self.supersession_engine.is_current(e.evidence_id)]

    def get_approved_sources(self, claim_id: str) -> List[Source]:
        """Get sources supporting a claim."""
        return self.evidence_binding.get_sources_for_claim(claim_id)

    def render_dossier_claim(self, claim_id: str) -> RenderedClaim:
        """Render a single claim for the dossier, with provenance.

        FAILS CLOSED if:
          - claim is not CURRENT
          - claim is not VALIDATED
          - claim has no evidence binding
          - claim's evidence is SUPERSEDED
          - claim's wording violates epistemic class rules
        """
        if claim_id not in self.claim_registry.claims:
            raise ValueError(f"CLAIM_NOT_FOUND: {claim_id}")

        claim = self.claim_registry.claims[claim_id]

        # Firewall check 1: must be CURRENT
        if claim.supersession_status != "CURRENT":
            raise ValueError(
                f"CLAIM_NOT_CURRENT: {claim_id} status={claim.supersession_status} "
                f"superseded_by={claim.superseded_by}"
            )

        # Firewall check 2: must be VALIDATED
        validation = self.claim_registry.validate_claim(claim_id)
        if not validation["valid"]:
            raise ValueError(
                f"CLAIM_NOT_VALIDATED: {claim_id} errors={validation['errors']}"
            )

        # Firewall check 3: must have evidence binding
        evidence = self.get_approved_evidence(claim_id)
        sources = self.get_approved_sources(claim_id)
        if not evidence and not sources:
            raise ValueError(
                f"CLAIM_NO_EVIDENCE_BINDING: {claim_id} has no current evidence or sources"
            )

        # Firewall check 4: wording must match epistemic class
        wording_check = validate_wording(claim.text, claim.epistemic_class)
        if not wording_check["valid"]:
            raise ValueError(
                f"CLAIM_WORDING_VIOLATION: {claim_id} violations={wording_check['violations']}"
            )

        # Build provenance chain
        provenance_parts = []
        if evidence:
            for e in evidence:
                provenance_parts.append(
                    f"Evidence: {e.evidence_id} (type={e.evidence_type}, commit={e.code_commit}, hash={e.output_hash})"
                )
        if sources:
            for s in sources:
                provenance_parts.append(
                    f"Source: {s.source_id} (type={s.source_type}, id={s.identifier})"
                )
        provenance_chain = " | ".join(provenance_parts)

        return RenderedClaim(
            claim_id=claim.claim_id,
            text=claim.text,
            epistemic_class=claim.epistemic_class.value,
            allowed_wording=MANDATORY_WORDING.get(claim.epistemic_class, []),
            evidence_count=len(evidence),
            source_count=len(sources),
            simulation_commit=claim.simulation_commit,
            simulation_output_hash=claim.simulation_output_hash,
            human_fact=claim.human_fact,
            provenance_chain=provenance_chain,
        )

    def render_dossier_section(self, territory_id: str) -> dict:
        """Render all approved claims for a territory as a dossier section.

        Returns dict with:
          - territory_id
          - territory_state (from canonical state)
          - rendered_claims: list of RenderedClaim
          - rejected_claims: list of (claim_id, reason) for claims that failed firewall
        """
        territory_state = self.get_territory_state(territory_id)
        claims = self.claim_registry.get_current_claims(territory_id)

        rendered = []
        rejected = []
        for claim in claims:
            try:
                r = self.render_dossier_claim(claim.claim_id)
                rendered.append(r)
            except ValueError as e:
                rejected.append({"claim_id": claim.claim_id, "reason": str(e)})

        return {
            "territory_id": territory_id,
            "territory_state": territory_state,
            "rendered_claims": [r.__dict__ for r in rendered],
            "rejected_claims": rejected,
            "total_claims": len(claims),
            "rendered_count": len(rendered),
            "rejected_count": len(rejected),
        }

    def audit_query_simulation_only_claims(self) -> List[str]:
        """Auditor: show me every claim supported only by simulation."""
        return self.evidence_binding.audit_claims_with_only_simulation()

    def audit_query_model_only_claims(self) -> List[str]:
        """Auditor: show me every claim supported only by model (no observation)."""
        return self.evidence_binding.audit_claims_with_only_model()
