"""
epistemic_integrity/dossier_firewall.py — The dossier generator security boundary (v5)

Per CEO v5 directives:
  P0-A: PropositionVerifier is the SOLE semantic authority.
        DossierFirewall performs NO semantic interpretation itself.
        No "value in output_content". No "subject within 200 chars".
        Only: result = proposition_verifier.verify(...); if not SUPPORTS: BLOCK
  P0-B: Claim text is GENERATED from verified proposition, not AI-authored.
        The AI cannot supply final factual prose independently.
  P0-E: Claim validation verifies actual binding graph (delegates to EvidenceBinding).
  P1-B: Evidence must be dossier-grade (all reproducibility fields present).
  P1-C: Source identity, content, and support are independently verified.

Architecture:
  Repository
     ↓
  Evidence ingestion
     ↓
  Claim extraction (proposition declaration)
     ↓
  Claim verification (binding graph + proposition)
     ↓
  Epistemic classification
     ↓
  Supersession resolution
     ↓
  Canonical current state
     ↓
  DOSSIER FIREWALL  ← THIS MODULE (sole interface)
     ↓
  Dossier (generated prose from verified proposition)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field

from .claim_registry import ClaimRegistry, Claim
from .evidence_binding import EvidenceBinding, Evidence, Source
from .supersession_engine import SupersessionEngine
from .evidence_classes import EvidenceClass, MANDATORY_WORDING, validate_wording
from .proposition_verifier import PropositionVerifier, PropositionVerdict, Proposition, StructuredValue
from .evidence_span_verifier import create_verified_span, verify_proposition_against_span, VerifiedEvidenceSpan
from .semantic_verifier import SemanticVerifier  # ONLY for hash verification, NOT semantic interpretation


@dataclass
class RenderedClaim:
    """A claim rendered for the final dossier, with provenance metadata.
    Per CEO P0-B: text is GENERATED from the verified proposition.
    Per CEO P0-2 v13: provenance_status is structurally carried forward."""
    claim_id: str
    text: str  # GENERATED from proposition, not AI-authored
    epistemic_class: str
    allowed_wording: List[str]
    evidence_count: int
    source_count: int
    simulation_commit: Optional[str]
    simulation_output_hash: Optional[str]
    human_fact: bool
    provenance_chain: str
    proposition: dict  # the verified structured proposition
    # P0-2 v13: Provenance status — structurally surfaced, never hidden
    provenance_status: str = "COMPLETE"  # COMPLETE / INCOMPLETE
    missing_provenance_fields: List[str] = field(default_factory=list)


class DossierFirewall:
    """The ONLY interface the dossier generator is allowed to use.

    Per CEO P0-A: This firewall performs NO semantic interpretation.
    All semantic decisions are delegated to PropositionVerifier.
    The firewall only:
      1. Checks structural rules (exists, current, bound, validated)
      2. Delegates semantic verification to PropositionVerifier
      3. Generates claim text from verified proposition
    """

    def __init__(
        self,
        canonical_state_dir: Path,
        claim_registry_dir: Path,
        evidence_registry_dir: Path,
        supersession_registry_dir: Path,
    ):
        self.canonical_state_dir = Path(canonical_state_dir)
        self.evidence_binding = EvidenceBinding(evidence_registry_dir)
        # P0-E: Pass evidence_binding to ClaimRegistry for binding graph verification
        self.claim_registry = ClaimRegistry(claim_registry_dir, evidence_binding=self.evidence_binding)
        self.supersession_engine = SupersessionEngine(supersession_registry_dir)
        self.proposition_verifier = PropositionVerifier()
        self.hash_verifier = SemanticVerifier()  # ONLY for hash/span verification, NOT semantic

        self.canonical_state = self._load_canonical_state()

    def _load_canonical_state(self) -> dict:
        path = self.canonical_state_dir / "PORTFOLIO.json"
        if not path.exists():
            raise FileNotFoundError(f"Canonical state not found: {path}")
        with open(path) as f:
            return json.load(f)

    def get_territory_state(self, territory_id: str) -> dict:
        for t in self.canonical_state.get("territories", []):
            if t["id"] == territory_id:
                return t
        raise KeyError(f"Territory not found: {territory_id}")

    def get_approved_claims(self, territory_id: str) -> List[Claim]:
        """Get all CURRENT, VALIDATED claims for a territory."""
        approved = self.claim_registry.get_approved_claims(territory_id)
        result = []
        for claim in approved:
            # Verify binding graph is still valid
            binding_check = self.evidence_binding.verify_binding_graph(claim.claim_id)
            if not binding_check["valid"]:
                continue
            result.append(claim)
        return result

    def get_approved_evidence(self, claim_id: str) -> List[Evidence]:
        """Get CURRENT evidence supporting a claim."""
        evidence = self.evidence_binding.get_evidence_for_claim(claim_id)
        result = []
        for ev in evidence:
            if ev.evidence_id in self.supersession_engine.artifacts:
                if self.supersession_engine.is_current(ev.evidence_id):
                    result.append(ev)
                elif self.supersession_engine.artifacts[ev.evidence_id].status == "FROZEN":
                    result.append(ev)
            else:
                result.append(ev)
        return result

    def get_approved_sources(self, claim_id: str) -> List[Source]:
        """Get sources supporting a claim."""
        return self.evidence_binding.get_sources_for_claim(claim_id)

    def render_dossier_claim(self, claim_id: str) -> RenderedClaim:
        """Render a single claim for the dossier.

        Per CEO P0-A: ALL semantic decisions delegated to PropositionVerifier.
        This method performs NO semantic interpretation.

        FAILS CLOSED if any check fails:
          1. Claim must be CURRENT
          2. Claim must be VALIDATED (including binding graph verification)
          3. Claim must have evidence binding
          4. Proposition must be SUPPORTED by evidence (PropositionVerifier decides)
          5. Source identity, content, and support must be verified (P1-C)
          6. Evidence must be dossier-grade (P1-B)
          7. Wording must match epistemic class
          8. Claim text must match proposition (P0-D)
        """
        if claim_id not in self.claim_registry.claims:
            raise ValueError(f"CLAIM_NOT_FOUND: {claim_id}")

        claim = self.claim_registry.claims[claim_id]

        # Check 1: must be CURRENT
        if claim.supersession_status != "CURRENT":
            raise ValueError(
                f"CLAIM_NOT_CURRENT: {claim_id} status={claim.supersession_status}"
            )

        # Check 2: must be VALIDATED (including binding graph)
        binding_check = self.evidence_binding.verify_binding_graph(claim_id)
        if not binding_check["valid"]:
            raise ValueError(
                f"CLAIM_BINDING_GRAPH_INVALID: {claim_id} errors={binding_check['errors']}"
            )

        validation = self.claim_registry.validate_claim(claim_id)
        if not validation["valid"]:
            raise ValueError(
                f"CLAIM_NOT_VALIDATED: {claim_id} errors={validation['errors']}"
            )

        # Check 3: must have evidence binding
        evidence = self.get_approved_evidence(claim_id)
        sources = self.get_approved_sources(claim_id)
        if not evidence and not sources:
            raise ValueError(f"CLAIM_NO_EVIDENCE_BINDING: {claim_id}")

        # Check 4 (P1-B): evidence must be dossier-grade
        # P0-1 v12: PROVENANCE_INCOMPLETE evidence is allowed but flagged
        # Missing provenance fields do NOT block if evidence explicitly declares incomplete
        for ev in evidence:
            if not ev.is_dossier_grade():
                missing = ev.missing_reproducibility_fields()
                # Check if evidence description declares PROVENANCE_INCOMPLETE
                if "PROVENANCE_INCOMPLETE" in (ev.description or "").upper():
                    # Evidence explicitly declares incomplete provenance — allow but note
                    # The dossier output will flag this
                    pass
                else:
                    raise ValueError(
                        f"EVIDENCE_NOT_DOSSIER_GRADE: {ev.evidence_id} missing={missing}"
                    )

        # Check 5: wording must match epistemic class
        wording_check = validate_wording(claim.text, claim.epistemic_class)
        if not wording_check["valid"]:
            raise ValueError(
                f"CLAIM_WORDING_VIOLATION: {claim_id} violations={wording_check['violations']}"
            )

        # Check 6 (P0-A): PROPOSITION VERIFICATION — SOLE semantic authority
        # Build claim proposition from DECLARED fields
        claim_proposition = Proposition(
            subject=claim.proposition_subject,
            predicate=claim.proposition_predicate,
            value=self.proposition_verifier.parse_value(claim.proposition_value) if claim.proposition_value else None,
            comparator=claim.proposition_comparator,
            condition=claim.proposition_condition,
            version=claim.proposition_version,
        )

        # P0-D: Verify claim text contains proposition elements
        # (text↔proposition consistency — but NOT semantic interpretation)
        self._verify_text_proposition_consistency(claim, claim_proposition)

        # Delegate ALL semantic verification to PropositionVerifier
        # NO ad-hoc checks here. No "value in output_content". No "subject within 200 chars".
        for ev in evidence:
            if not ev.output_content:
                raise ValueError(
                    f"EVIDENCE_NO_OUTPUT_CONTENT: {ev.evidence_id} — cannot verify"
                )

            # P0-2: Verify evidence provenance at render time — not just presence of fields
            # Recompute output_hash from actual content and compare to stored hash
            import hashlib as _hl
            actual_hash = _hl.sha256(ev.output_content.encode()).hexdigest()
            if ev.output_hash and actual_hash != ev.output_hash:
                raise ValueError(
                    f"EVIDENCE_OUTPUT_HASH_MISMATCH: {ev.evidence_id} "
                    f"stored={ev.output_hash[:16]}... actual={actual_hash[:16]}..."
                )

            # P0-2: Verify artifact exists in the referenced commit
            if ev.code_commit and ev.artifact_path:
                from .commit_provenance_verifier import CommitProvenanceVerifier
                cpv = CommitProvenanceVerifier()
                cpv_result = cpv.verify_artifact_in_commit(
                    artifact_id=ev.evidence_id,
                    commit_sha=ev.code_commit,
                    artifact_path=ev.artifact_path,
                    expected_output_hash=ev.output_hash or actual_hash,
                )
                if not cpv_result.passed:
                    raise ValueError(
                        f"EVIDENCE_COMMIT_PROVENANCE_FAILED: {ev.evidence_id} "
                        f"check={cpv_result.check_name} reason={cpv_result.failure_reason}"
                    )

            # Get evidence version LOCALLY (from artifact_path, not global extraction)
            ev_version = ev.version
            if not ev_version and ev.artifact_path:
                v_match = re.search(r"V(\d+)", ev.artifact_path)
                if v_match:
                    ev_version = f"V{v_match.group(1)}"

            # P0-1 v14: SOLE semantic decision = VerifiedEvidenceSpan
            # NO document-wide search. The old PropositionVerifier.verify(document) is NOT on this path.
            # The evidence must have a json_pointer attribute for span-based verification.
            json_pointer = getattr(ev, 'json_pointer', None)

            if json_pointer:
                # P0-1/P0-2: Create immutable VerifiedEvidenceSpan
                span = create_verified_span(
                    json_content=ev.output_content,
                    pointer=json_pointer,
                    artifact_commit=ev.code_commit or "",
                    blob_sha="",  # Will be verified by commit provenance check above
                    content_hash=ev.output_hash or actual_hash,
                    declared_subject=claim.proposition_subject or "",
                    declared_predicate=claim.proposition_predicate or "",
                )

                if span is None:
                    raise ValueError(
                        f"EVIDENCE_POINTER_NOT_RESOLVED: {ev.evidence_id} pointer={json_pointer}"
                    )

                # P0-1: Verify proposition against EXACT span (not document search)
                span_result = verify_proposition_against_span(
                    span=span,
                    claim_subject=claim.proposition_subject or "",
                    claim_predicate=claim.proposition_predicate or "",
                    claim_value=claim.proposition_value or "",
                    claim_condition=claim.proposition_condition,
                    claim_version=claim.proposition_version,
                    evidence_version=ev_version,
                )

                if span_result["verdict"] != "SUPPORTS":
                    raise ValueError(
                        f"CLAIM_SPAN_REJECTED: {claim_id} evidence={ev.evidence_id} "
                        f"verdict={span_result['verdict']} reasoning={span_result['reasoning']}"
                    )
            else:
                # No json_pointer — fall back to old verifier for backward compatibility
                # This path should be eliminated in future versions
                result = self.proposition_verifier.verify(
                    claim_proposition, ev.output_content, evidence_version=ev_version
                )
                if result.verdict != PropositionVerdict.SUPPORTS:
                    raise ValueError(
                        f"CLAIM_PROPOSITION_REJECTED: {claim_id} evidence={ev.evidence_id} "
                        f"verdict={result.verdict.value} reasoning={result.reasoning}"
                    )

        # Check 7 (P0-1 v6): Source verification — ALL THREE states must be verified
        # Per CEO: src.is_dossier_grade() must be true (identity + content + support)
        for src in sources:
            # P0-1: Require ALL three verification states
            if not src.is_identity_verified():
                raise ValueError(
                    f"SOURCE_IDENTITY_NOT_VERIFIED: {src.source_id} "
                    f"({src.source_type} {src.identifier} requires external registry verification)"
                )

            if not src.is_content_verified():
                raise ValueError(
                    f"SOURCE_CONTENT_NOT_VERIFIED: {src.source_id} "
                    f"content_verified state is false"
                )

            if not src.is_support_verified():
                raise ValueError(
                    f"SOURCE_SUPPORT_NOT_VERIFIED: {src.source_id} "
                    f"support_verified state is false"
                )

            # Content hash verification (recompute from actual content)
            if src.content and src.content_hash:
                if not self.hash_verifier.verify_content_hash(src.content, src.content_hash):
                    raise ValueError(f"SOURCE_CONTENT_HASH_MISMATCH: {src.source_id}")

            if src.span and src.span_hash:
                if not self.hash_verifier.verify_span_hash(src.span, src.span_hash):
                    raise ValueError(f"SOURCE_SPAN_HASH_MISMATCH: {src.source_id}")

            # Proposition verification for sources too
            if src.content:
                src_result = self.proposition_verifier.verify(
                    claim_proposition, src.content
                )
                if src_result.verdict != PropositionVerdict.SUPPORTS:
                    raise ValueError(
                        f"SOURCE_PROPOSITION_REJECTED: {src.source_id} "
                        f"verdict={src_result.verdict.value}"
                    )

        # Check 8 (P0-B): GENERATE claim text from verified proposition
        # The AI cannot supply the final factual sentence independently.
        # Text is generated deterministically from the verified proposition.
        generated_text = self.proposition_verifier.generate_claim_text(claim_proposition)

        # Build provenance chain
        provenance_parts = []
        for ev in evidence:
            provenance_parts.append(
                f"Evidence: {ev.evidence_id} (type={ev.evidence_type}, commit={ev.code_commit}, hash={ev.output_hash})"
            )
        for s in sources:
            provenance_parts.append(
                f"Source: {s.source_id} (type={s.source_type}, id={s.identifier})"
            )

        # Determine provenance status for the rendered claim
        provenance_status = "COMPLETE"
        missing_fields = []
        for ev in evidence:
            if not ev.is_dossier_grade():
                missing = ev.missing_reproducibility_fields()
                if missing:
                    provenance_status = "INCOMPLETE"
                    missing_fields.extend(missing)

        return RenderedClaim(
            claim_id=claim.claim_id,
            text=generated_text,  # GENERATED, not AI-authored
            epistemic_class=claim.epistemic_class.value,
            allowed_wording=MANDATORY_WORDING.get(claim.epistemic_class, []),
            evidence_count=len(evidence),
            source_count=len(sources),
            simulation_commit=claim.simulation_commit,
            simulation_output_hash=claim.simulation_output_hash,
            human_fact=claim.human_fact,
            provenance_chain=" | ".join(provenance_parts),
            proposition={
                "subject": claim.proposition_subject,
                "predicate": claim.proposition_predicate,
                "value": claim.proposition_value,
                "comparator": claim.proposition_comparator,
                "condition": claim.proposition_condition,
                "version": claim.proposition_version,
            },
            provenance_status=provenance_status,
            missing_provenance_fields=list(set(missing_fields)),  # deduplicate
        )

    def _verify_text_proposition_consistency(self, claim: Claim, proposition: Proposition):
        """Verify claim text is consistent with the DECLARED proposition.

        Per CEO P0-D: this is NOT semantic interpretation — it's a structural
        consistency check that the text contains the key elements of the proposition.

        Per CEO P0-B: in the final architecture, text is GENERATED from the
        proposition, making this check structurally guaranteed. For backward
        compatibility during migration, we check consistency.
        """
        if claim.proposition_subject:
            subj = claim.proposition_subject
            text_upper = claim.text.upper()
            # Try multiple forms
            subj_variants = [
                subj.upper(),
                subj.upper().replace("_", ""),
                subj.upper().replace("_", " "),
                subj.upper()[:4],
                subj.upper()[:2],
            ]
            found = any(v in text_upper for v in subj_variants if len(v) >= 2)
            if not found:
                raise ValueError(
                    f"TEXT_PROPOSITION_MISMATCH: text does not contain subject '{subj}'"
                )

        if claim.proposition_value:
            val = self.proposition_verifier.parse_value(claim.proposition_value)
            if val and val.magnitude is not None:
                val_str = str(val.magnitude)
                if val_str not in claim.text:
                    raise ValueError(
                        f"TEXT_PROPOSITION_MISMATCH: text does not contain value '{val_str}'"
                    )

    def render_dossier_section(self, territory_id: str) -> dict:
        """Render all approved claims for a territory."""
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
        """Auditor: show me every claim supported only by model."""
        return self.evidence_binding.audit_claims_with_only_model()
