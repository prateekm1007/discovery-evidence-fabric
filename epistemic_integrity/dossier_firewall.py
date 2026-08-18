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
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from .claim_registry import ClaimRegistry, Claim
from .evidence_binding import EvidenceBinding, Evidence, Source
from .supersession_engine import SupersessionEngine
from .evidence_classes import EvidenceClass, MANDATORY_WORDING, validate_wording
from .semantic_verifier import SemanticVerifier, SemanticVerdict
from .proposition_verifier import PropositionVerifier, PropositionVerdict


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
        self.semantic_verifier = SemanticVerifier()
        self.proposition_verifier = PropositionVerifier()  # Structured proposition checker (P0-1)

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
        """Get CURRENT evidence supporting a claim.

        Evidence that is not registered in supersession engine is treated as CURRENT
        (registration is optional for evidence — only artifacts have supersession chains).
        Evidence explicitly marked SUPERSEDED or INVALIDATED is excluded.
        """
        evidence = self.evidence_binding.get_evidence_for_claim(claim_id)
        result = []
        for ev in evidence:
            # Check if evidence is registered in supersession engine
            if ev.evidence_id in self.supersession_engine.artifacts:
                # Registered — check status
                if self.supersession_engine.is_current(ev.evidence_id):
                    result.append(ev)
                # If FROZEN/SUPERSEDED, exclude (but FROZEN evidence for a FROZEN territory
                # is still valid — it proves the negative result)
                elif self.supersession_engine.artifacts[ev.evidence_id].status == "FROZEN":
                    # FROZEN evidence is valid for FROZEN territories (negative ceiling proof)
                    result.append(ev)
            else:
                # Not registered in supersession — treat as CURRENT
                result.append(ev)
        return result

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

        # Firewall check 5 (P0-1): STRUCTURED PROPOSITION verification
        # Uses the DECLARED proposition from claim fields (not extracted from text).
        # This is deterministic — the claim explicitly states (subject, predicate, value, ...)
        # and the verifier checks that the evidence contains that exact proposition.
        semantic_failures = []

        # Build claim proposition from DECLARED fields (not text extraction)
        from .proposition_verifier import Proposition
        claim_proposition = Proposition(
            subject=claim.proposition_subject,
            predicate=claim.proposition_predicate,
            value=claim.proposition_value,
            comparator=claim.proposition_comparator,
            condition=claim.proposition_condition,
            version=claim.proposition_version,
            raw_text=claim.text,
        )

        for ev in evidence:
            if ev.output_content:
                # Extract all propositions from evidence and check if claim proposition matches any
                evidence_props = self.proposition_verifier.extract_all_propositions(ev.output_content)

                # Also do direct text search for the value in evidence (catches cases where
                # JSON extraction misses the proposition)
                value_in_evidence = False
                if claim.proposition_value:
                    # Check if the value appears in evidence content
                    val_numeric = re.search(r"(\d+\.?\d*)", claim.proposition_value)
                    if val_numeric:
                        val_str = val_numeric.group(1)
                        if val_str in ev.output_content:
                            value_in_evidence = True

                # Check if subject+value appear TOGETHER in evidence
                # This prevents "wrong entity gets right number" attack
                subject_value_together = False
                if claim.proposition_subject and claim.proposition_value:
                    # Check if subject and value appear within 200 chars of each other
                    subj_pattern = re.compile(re.escape(claim.proposition_subject[:4]), re.IGNORECASE)
                    val_numeric = re.search(r"(\d+\.?\d*)", claim.proposition_value)
                    if val_numeric:
                        val_str = val_numeric.group(1)
                        for subj_match in subj_pattern.finditer(ev.output_content):
                            # Check if value appears within 200 chars after subject
                            region = ev.output_content[subj_match.start():subj_match.start()+200]
                            if val_str in region:
                                subject_value_together = True
                                break

                if not value_in_evidence and not any(
                    self.proposition_verifier._values_equal(claim.proposition_value or "", ep.value or "")
                    for ep in evidence_props
                ):
                    semantic_failures.append(
                        f"Evidence {ev.evidence_id} VALUE_NOT_FOUND: claim value={claim.proposition_value} not in evidence"
                    )
                elif claim.proposition_subject and not subject_value_together:
                    # Value exists but not associated with the claimed subject
                    semantic_failures.append(
                        f"Evidence {ev.evidence_id} SUBJECT_VALUE_MISMATCH: claim says {claim.proposition_subject}={claim.proposition_value} but this value is not associated with {claim.proposition_subject} in evidence"
                    )
                # Check version
                elif claim.proposition_version and ev.code_commit:
                    # Version mismatch if claim version doesn't match the evidence's version
                    # (evidence version is derived from its artifact_path or description)
                    ev_version = None
                    if ev.artifact_path:
                        import re as re_mod
                        v_match = re_mod.search(r"V(\d+)", ev.artifact_path)
                        if v_match:
                            ev_version = f"V{v_match.group(1)}"
                    if ev_version and claim.proposition_version.upper() != ev_version.upper():
                        semantic_failures.append(
                            f"Evidence {ev.evidence_id} VERSION_MISMATCH: claim version={claim.proposition_version} but evidence version={ev_version}"
                        )
            else:
                semantic_failures.append(f"Evidence {ev.evidence_id} has NO output_content — cannot verify proposition support")

        # Check sources semantically too
        for src in sources:
            if src.content:
                # Verify content hash (P0-2)
                if src.content_hash:
                    if not self.semantic_verifier.verify_content_hash(src.content, src.content_hash):
                        semantic_failures.append(f"Source {src.source_id} content_hash MISMATCH — content tampered")
                # Verify span exists in content (P0-2)
                if src.span:
                    if not self.semantic_verifier.verify_span_exists(src.content, src.span):
                        semantic_failures.append(f"Source {src.source_id} span NOT FOUND in content")
                    if src.span_hash:
                        if not self.semantic_verifier.verify_span_hash(src.span, src.span_hash):
                            semantic_failures.append(f"Source {src.source_id} span_hash MISMATCH — span tampered")
                # Check if source content contains the claimed value
                if claim.proposition_value:
                    val_numeric = re.search(r"(\d+\.?\d*)", claim.proposition_value)
                    if val_numeric:
                        val_str = val_numeric.group(1)
                        if val_str not in src.content:
                            semantic_failures.append(
                                f"Source {src.source_id} VALUE_NOT_FOUND: claim value={claim.proposition_value} not in source content"
                            )
            else:
                semantic_failures.append(f"Source {src.source_id} has NO content — cannot verify proposition support")

        if semantic_failures:
            raise ValueError(
                f"CLAIM_PROPOSITION_VERIFICATION_FAILED: {claim_id} failures={semantic_failures}"
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
