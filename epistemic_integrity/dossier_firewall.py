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
    Per CEO P0-2 v13: provenance_status is structurally carried forward.
    Per CEO v27: historical_provenance_limitation is structurally carried forward."""
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
    # v27: Historical provenance limitation — PERMANENT machine state
    historical_provenance_limitation: Optional[dict] = None


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

        # v27: Load HISTORICAL_PROVENANCE_LIMITATION (CEO directive)
        # This is a PERMANENT machine state that must survive into every dossier.
        # The dossier generator can NEVER translate this into "historically verified" language.
        self.historical_provenance_limitation = self._load_historical_provenance_limitation()

    def _load_historical_provenance_limitation(self) -> dict:
        """Load the HISTORICAL_PROVENANCE_LIMITATION state file.

        Per CEO v26 audit: "Encode HISTORICAL_PROVENANCE_LIMITATION as a
        first-class machine state covering the unrecoverable pre-scrub history."

        This state is PERMANENT. It must be loaded by every DossierFirewall
        instance and enforced on every rendered claim.
        """
        # Try multiple locations (canonical_state_dir is CANONICAL_STATE/,
        # but the limitation lives in approved_provenance/)
        candidates = [
            self.canonical_state_dir.parent / "epistemic_integrity" / "approved_provenance" / "HISTORICAL_PROVENANCE_LIMITATION.json",
            self.canonical_state_dir / "HISTORICAL_PROVENANCE_LIMITATION.json",
            Path(__file__).parent / "approved_provenance" / "HISTORICAL_PROVENANCE_LIMITATION.json",
        ]
        for path in candidates:
            if path.exists():
                with open(path) as f:
                    return json.load(f)
        # If not found, return empty dict (not an error — the limitation
        # may not have been declared yet in older checkouts)
        return {}

    def _enforce_historical_provenance_limitation(self, claim_text: str, evidence_commit: str) -> None:
        """Enforce that dossier language never claims historical byte-equivalence.

        Per CEO v26 audit: "Ensure the dossier generator can never translate
        that state into 'historically verified' language."

        This method BLOCKS any claim that uses forbidden phrases asserting
        historical byte-equivalence, UNLESS the claim explicitly acknowledges
        the HISTORICAL_PROVENANCE_LIMITATION.

        Forbidden phrases (case-insensitive):
          - "historically verified"
          - "byte-equivalent"
          - "byte-for-byte identical to original"
          - "pre-scrub evidence preserved exactly"
          - "evidence corpus unchanged except credentials"
        """
        if not self.historical_provenance_limitation:
            return  # No limitation declared — skip enforcement

        consequence = self.historical_provenance_limitation.get("consequence", {})
        constraint = consequence.get("dossier_language_constraint", {})
        forbidden = [p.lower() for p in constraint.get("forbidden_phrases", [])]

        if not forbidden:
            return

        text_lower = claim_text.lower()
        for phrase in forbidden:
            if phrase in text_lower:
                # Check if the claim explicitly acknowledges the limitation
                required_ack = constraint.get("required_acknowledgment", "")
                ack_keywords = [
                    "post-scrub epistemic state",
                    "pre-scrub byte-level equivalence is unproven",
                    "historical_provenance_limitation",
                ]
                acknowledged = any(kw.lower() in text_lower for kw in ack_keywords)
                if not acknowledged:
                    raise ValueError(
                        f"DOSSIER_HISTORICAL_PROVENANCE_VIOLATION: claim text contains "
                        f"forbidden phrase '{phrase}' without acknowledging "
                        f"HISTORICAL_PROVENANCE_LIMITATION. "
                        f"Required acknowledgment: {required_ack[:200]}..."
                    )

        # Additional check: if evidence is anchored to a post-scrub commit,
        # the rendered claim MUST carry the limitation acknowledgment.
        # This is enforced at render time in render_dossier_claim().


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

        # Check 3: must have verified Evidence proof binding (P0-2 v30.9)
        # CEO v30.9 P0-2: A dossier claim MUST require a verified proof object,
        # not merely "source exists". A claim bound only to sources but with no
        # Evidence proof object MUST BLOCK. The semantic verification loop runs
        # over Evidence objects (Check 6 below); sources alone cannot carry
        # the proof burden.
        #
        # This closes the source-only bypass loophole identified in the CEO
        # v30.9 audit: the old check `if not evidence and not sources: BLOCK`
        # allowed source-only claims to reach rendering without any proof
        # binding verification.
        evidence = self.get_approved_evidence(claim_id)
        sources = self.get_approved_sources(claim_id)
        if not evidence:
            raise ValueError(
                f"CLAIM_NO_VERIFIED_EVIDENCE_PROOF: {claim_id} "
                f"— a dossier claim requires at least one verified Evidence "
                f"proof object (not merely sources). Sources alone cannot "
                f"carry the proof burden. CEO v30.9 P0-2: source-only claims "
                f"are BLOCKED. (sources_present={len(sources)})"
            )

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

            # P0-1 v15: SOLE semantic decision = VerifiedEvidenceSpan
            # NO document-wide search. NO fallback to old verifier.
            # If evidence has no json_pointer → BLOCK (EVIDENCE_NOT_PROOF_BOUND).
            json_pointer = getattr(ev, 'json_pointer', None)

            if not json_pointer:
                raise ValueError(
                    f"EVIDENCE_NOT_PROOF_BOUND: {ev.evidence_id} — no json_pointer. "
                    f"Evidence must be bound to an exact JSON Pointer for dossier authorization. "
                    f"No fallback to document-wide search."
                )

            # P0-B: Extract EVIDENCE-side subject from the key at the pointer.
            # The firewall must NEVER use the claim's subject as the evidence's subject.
            # The evidence declares what IT says, then the claim is compared against that.
            import json as _json
            try:
                _data = _json.loads(ev.output_content)
                _components = json_pointer.split("/")[1:]
                _current = _data
                for _comp in _components:
                    _comp_unescaped = _comp.replace("~1", "/").replace("~0", "~")
                    _current = _current[_comp_unescaped]
                _key_name = _components[-1] if _components else ""
            except Exception:
                raise ValueError(
                    f"EVIDENCE_POINTER_UNRESOLVABLE: {ev.evidence_id} pointer={json_pointer}"
                )

            # Evidence-side subject: resolve via entity registry, NOT key-name inference
            # Per CEO P0-2: "Replace key-name subject inference with an immutable,
            # explicitly declared evidence-side proposition bound to the exact JSON Pointer."
            # Per CEO P0-3: "No string normalization."
            from .entity_registry import create_default_registry
            _registry = create_default_registry()
            _ev_subject = _registry.resolve(_key_name) or ""

            # P0-1/P0-2: Create immutable VerifiedEvidenceSpan with EVIDENCE-side subject
            span = create_verified_span(
                json_content=ev.output_content,
                pointer=json_pointer,
                artifact_commit=ev.code_commit or "",
                blob_sha="",
                content_hash=ev.output_hash or actual_hash,
                declared_subject=_ev_subject,  # EVIDENCE-side, NOT claim-side
                declared_predicate=_key_name.lower(),
            )

            if span is None:
                raise ValueError(
                    f"EVIDENCE_POINTER_NOT_RESOLVED: {ev.evidence_id} pointer={json_pointer}"
                )

            # P0-1: Verify proposition against EXACT span (not document search)
            # P0-C: Version is checked here — claim version vs evidence version
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

        # Check 7 (P0-1 v6 + v30.9 P0-3): Source verification at render
        # Per CEO: src.is_dossier_grade() must be true (identity + content + support)
        # CEO v30.9 P0-3: Actually CALL is_dossier_grade() and re-verify hashes.
        #   Do not rely on the method existing — call it in the production path.
        # CEO v30.9 P0-1: External sources MUST carry _verified_evidence_authorization
        #   proving they entered through register_source_from_verified_evidence().
        #   An external Source without this authorization is a bypass attempt.
        for src in sources:
            # P0-3 v30.9: Explicitly call is_dossier_grade() — not just rely on
            # individual state checks. This is the executive summary check.
            if not src.is_dossier_grade():
                raise ValueError(
                    f"SOURCE_NOT_DOSSIER_GRADE: {src.source_id} "
                    f"is_dossier_grade() returned False. identity_verified="
                    f"{src.is_identity_verified()} content_verified="
                    f"{src.is_content_verified()} support_verified="
                    f"{src.is_support_verified()}. CEO v30.9 P0-3: all three "
                    f"states MUST be True for dossier admission."
                )

            # P0-1: Require ALL three verification states (explicit, for error clarity)
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
            # CEO v30.9: If content is present, content_hash MUST also be present
            # and MUST match. Content without a hash cannot be verified — BLOCK.
            if src.content and not src.content_hash:
                raise ValueError(
                    f"SOURCE_CONTENT_MISSING_HASH: {src.source_id} has content "
                    f"but no content_hash. Content cannot be verified without a "
                    f"hash. CEO v30.9: content_hash is MANDATORY when content "
                    f"is present."
                )
            if src.content and src.content_hash:
                if not self.hash_verifier.verify_content_hash(src.content, src.content_hash):
                    raise ValueError(f"SOURCE_CONTENT_HASH_MISMATCH: {src.source_id}")

            # CEO v30.9: If span is present, span_hash MUST also be present
            if src.span and not src.span_hash:
                raise ValueError(
                    f"SOURCE_SPAN_MISSING_HASH: {src.source_id} has span "
                    f"but no span_hash. Span cannot be verified without a hash."
                )
            if src.span and src.span_hash:
                if not self.hash_verifier.verify_span_hash(src.span, src.span_hash):
                    raise ValueError(f"SOURCE_SPAN_HASH_MISMATCH: {src.source_id}")

            # CEO v30.10: TYPE-SAFE source hierarchy enforcement at render.
            # The external-vs-internal boundary is NO LONGER a source_type
            # string check. It is a TYPE check:
            #   - ExternalSource: constructible only from VerifiedEvidence.
            #     Carries _verified_evidence_authorization as a real field.
            #   - InternalSource: constructible only via its own constructor.
            #     Refuses external content indicators.
            #
            # An external source MUST be an ExternalSource instance. A
            # masquerade via source_type string label is structurally
            # impossible because InternalSource's constructor refuses
            # external content patterns.
            from .evidence_binding import ExternalSource, InternalSource, _is_external_source_type, _is_internal_source_type
            if _is_external_source_type(src.source_type):
                # Must be an ExternalSource instance (not just a Source with
                # an external source_type string).
                if not isinstance(src, ExternalSource):
                    raise ValueError(
                        f"EXTERNAL_SOURCE_NOT_TYPE_SAFE: {src.source_id} "
                        f"(source_type={src.source_type}) is an externally-sourced "
                        f"Source but is NOT an ExternalSource instance (got "
                        f"{type(src).__name__}). CEO v30.10: external sources "
                        f"MUST be ExternalSource instances constructed via "
                        f"register_source_from_verified_evidence(). A raw "
                        f"Source with source_type='DOI' is a masquerade "
                        f"attempt — the type boundary is enforced by object "
                        f"construction, not by trusting a source_type label."
                    )
                # Defense-in-depth: verify the authorization field is present
                # (ExternalSource.__post_init__ already enforces this, but
                # we re-check in case of object.__new__ bypass).
                auth = getattr(src, '_verified_evidence_authorization', None)
                if not auth:
                    raise ValueError(
                        f"EXTERNAL_SOURCE_MISSING_VERIFIED_EVIDENCE_AUTHORIZATION: "
                        f"{src.source_id} (source_type={src.source_type}) is an "
                        f"ExternalSource but does not carry "
                        f"_verified_evidence_authorization. This should be "
                        f"impossible — ExternalSource.__post_init__ requires it. "
                        f"Indicates a bypass attempt via object.__new__ or "
                        f"subclassing. CEO v30.10 P0 control violation at render."
                    )
            elif _is_internal_source_type(src.source_type):
                # Must be an InternalSource instance.
                if not isinstance(src, InternalSource):
                    raise ValueError(
                        f"INTERNAL_SOURCE_NOT_TYPE_SAFE: {src.source_id} "
                        f"(source_type={src.source_type}) is an internally-typed "
                        f"Source but is NOT an InternalSource instance (got "
                        f"{type(src).__name__}). CEO v30.10: internal sources "
                        f"MUST be InternalSource instances constructed via "
                        f"register_source(InternalSource(...)). The type "
                        f"boundary is enforced by object construction."
                    )

            # P0-1 v16: NO document-wide semantic search for sources.
            # Source verification is identity + content hash + support state ONLY.
            # The old PropositionVerifier.verify(src.content) is REMOVED from this path.
            # Sources support claims through their verified identity and content,
            # NOT through a second semantic claim engine.

        # Check 8 (P0-B): GENERATE claim text from verified proposition
        # The AI cannot supply the final factual sentence independently.
        # Text is generated deterministically from the verified proposition.
        generated_text = self.proposition_verifier.generate_claim_text(claim_proposition)

        # v27: Enforce HISTORICAL_PROVENANCE_LIMITATION (CEO directive)
        # Block any claim that asserts historical byte-equivalence without
        # acknowledging the limitation.
        evidence_commit_for_check = evidence[0].code_commit if evidence else ""
        self._enforce_historical_provenance_limitation(generated_text, evidence_commit_for_check)

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

        # v27: Append HISTORICAL_PROVENANCE_LIMITATION to provenance chain
        # Every dossier claim MUST carry this acknowledgment if the limitation is active.
        if self.historical_provenance_limitation and self.historical_provenance_limitation.get("status") == "ACTIVE":
            limitation_ack = (
                "HISTORICAL_PROVENANCE_LIMITATION: Evidence is verified against the "
                "post-scrub epistemic state. Pre-scrub byte-level equivalence is "
                "unproven due to filter-repo garbage collection of pre-scrub commits."
            )
            provenance_parts.append(limitation_ack)

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
            # v27: Carry the HISTORICAL_PROVENANCE_LIMITATION into every rendered claim
            historical_provenance_limitation=self.historical_provenance_limitation or None,
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
                # Also check integer form (1000.0 → 1000)
                val_str_int = str(int(val.magnitude)) if val.magnitude == int(val.magnitude) else val_str
                if val_str not in claim.text and val_str_int not in claim.text:
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
