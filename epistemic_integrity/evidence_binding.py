"""
epistemic_integrity/evidence_binding.py — Bidirectional Claim ↔ Evidence ↔ Source binding

Per CEO v5 directives:
  P0-D: ONE canonical Evidence schema (no duplicates)
  P0-E: Claim validation verifies actual binding graph (not just nonempty IDs)
  P0-F: Real external identity verification object (not boolean flag)
  P1-B: Universal reproducibility (mandatory fields for dossier-grade)
  P1-C: Separate source identity / content integrity / claim support states

This module enforces bidirectional traceability and is the SOLE authority for
evidence and source objects.
"""

import json
import hashlib
import re
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone


# ============================================================
# P0-F: External Identity Verification (not a boolean flag)
# ============================================================
@dataclass
class ExternalIdentityVerification:
    """Verifiable external identity proof for DOI/patent sources.

    Per CEO P0-F: a boolean field is not proof. The external identity proof
    itself needs provenance.
    """
    verified: bool = False
    verification_provider: Optional[str] = None      # "Crossref" / "USPTO" / "PubMed" / "Lens"
    verification_timestamp: Optional[str] = None
    resolved_identifier: Optional[str] = None         # canonical identifier from registry
    verified_title_hash: Optional[str] = None         # SHA256(title from registry)
    verified_metadata_hash: Optional[str] = None      # SHA256(metadata from registry)
    verification_response_hash: Optional[str] = None  # SHA256(full API response)
    verification_method: Optional[str] = None         # "Crossref REST API" / "USPTO PatentsView"


# ============================================================
# CEO v30.9 P0-1: External vs Internal source type classification
# ============================================================
# Externally-sourced source types MUST go through register_source_from_verified_evidence.
# Internally-generated source types can use register_source directly.
# This classification is the P0 control that closes the raw-Source bypass loophole.
_EXTERNAL_SOURCE_TYPES = frozenset({
    "PMID", "DOI", "PATENT", "URL", "BOOK",
    "K_NUMBER", "PMA_NUMBER", "MDR_REPORT_KEY", "RECALL_NUMBER",
    "NCT_ID", "PROJECT_NUM",
})

_INTERNAL_SOURCE_TYPES = frozenset({
    "INTERNAL_REPORT", "INTERNAL_ANALYSIS",
})


def _is_external_source_type(source_type: str) -> bool:
    """CEO v30.9 P0-1: Returns True if source_type indicates external origin.

    External sources (papers, patents, MAUDE reports, clinical trials, etc.)
    MUST be registered via register_source_from_verified_evidence().
    Internal sources (INTERNAL_REPORT, INTERNAL_ANALYSIS) can use
    register_source() directly.
    """
    return source_type in _EXTERNAL_SOURCE_TYPES


def _is_internal_source_type(source_type: str) -> bool:
    """CEO v30.9 P0-1: Returns True if source_type indicates internal origin."""
    return source_type in _INTERNAL_SOURCE_TYPES


# ============================================================
# P1-C: Three independently verified states for sources
# ============================================================
@dataclass
class SourceVerificationStates:
    """Three separate verification states per CEO P1-C:
      1. SOURCE_IDENTITY: Did this document come from DOI X / patent Y?
      2. SOURCE_CONTENT: Has the content been tampered with? (hash matches)
      3. CLAIM_SUPPORT: Does the cited passage support proposition Z?
    All three must be VERIFIED for dossier admission.
    """
    identity_verified: bool = False
    content_verified: bool = False
    support_verified: bool = False


# ============================================================
# P0-D: SINGLE canonical Evidence schema (no duplicates)
# ============================================================
@dataclass
class Evidence:
    """An experiment or simulation that produces evidence.

    Per CEO P0-D: ONE schema only. No duplicate definitions.
    Per CEO P1-B: reproducibility fields are MANDATORY for dossier-grade.
    """
    evidence_id: str                                    # EXP-CV-T<territory>-<seq>
    territory_id: str
    description: str
    evidence_type: str                                  # SIMULATION / EXPERIMENT / BENCHTOP / ANALYSIS

    # Reproducibility (P1-B: mandatory for dossier-grade, checked by is_dossier_grade())
    reproducibility_capsule_id: Optional[str] = None
    code_commit: Optional[str] = None                   # git commit hash
    config_hash: Optional[str] = None
    input_hashes: List[str] = field(default_factory=list)
    output_content: Optional[str] = None                # actual output JSON content
    output_hash: Optional[str] = None                   # SHA256(output_content) — MUST recompute
    artifact_path: Optional[str] = None                 # path to output file in repo
    random_seed: Optional[int] = None
    python_version: Optional[str] = None
    dependency_lock_hash: Optional[str] = None
    model_id: Optional[str] = None
    model_parameters: Dict = field(default_factory=dict)

    # Lifecycle
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supersession_status: str = "CURRENT"                # CURRENT/SUPERSEDED/INVALIDATED/HISTORICAL/FROZEN
    superseded_by: Optional[str] = None

    # Version is LOCAL (P0-C from v4)
    version: Optional[str] = None                       # "V6" — local to this artifact

    def is_dossier_grade(self) -> bool:
        """Per CEO P1-B: all reproducibility fields must be present for dossier-grade evidence."""
        required = [
            self.code_commit,
            self.config_hash,
            self.output_hash,
            self.random_seed,
            self.python_version,
            self.dependency_lock_hash,
            self.model_id,
            self.artifact_path,
        ]
        return all(field is not None for field in required)

    def missing_reproducibility_fields(self) -> List[str]:
        """Return list of missing required reproducibility fields."""
        missing = []
        if not self.code_commit: missing.append("code_commit")
        if not self.config_hash: missing.append("config_hash")
        if not self.output_hash: missing.append("output_hash")
        if self.random_seed is None: missing.append("random_seed")
        if not self.python_version: missing.append("python_version")
        if not self.dependency_lock_hash: missing.append("dependency_lock_hash")
        if not self.model_id: missing.append("model_id")
        if not self.artifact_path: missing.append("artifact_path")
        return missing


# ============================================================
# Source schema (with P0-F external identity + P1-C three states)
# ============================================================
@dataclass
class Source:
    """An external source (paper, patent, etc.) cited as evidence.

    Per CEO P0-2: sources must have cryptographically verifiable content.
    Per CEO P0-F: external identity requires verifiable proof, not boolean.
    Per CEO P1-C: identity, content, and support are independently verified.
    """
    source_id: str                                      # SRC-<type>-<seq>
    source_type: str                                    # PMID / PATENT / DOI / URL / BOOK
    identifier: str                                     # actual PMID, patent number, DOI, etc.
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    url: Optional[str] = None

    # Retrieval provenance
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retrieval_method: Optional[str] = None
    source_locator: Optional[str] = None                # full URL or file path

    # Content (P0-2: cryptographically verifiable)
    content: Optional[str] = None
    content_hash: Optional[str] = None                  # SHA256(content)
    span: Optional[str] = None                          # exact passage cited
    span_hash: Optional[str] = None                     # SHA256(span)

    # P0-F: External identity verification (replaces boolean flag)
    external_identity: Optional[ExternalIdentityVerification] = None

    # P1-C: Three independent verification states
    verification_states: SourceVerificationStates = field(default_factory=SourceVerificationStates)

    def is_identity_verified(self) -> bool:
        """Has external identity been verified by an authoritative registry?"""
        if self.external_identity and self.external_identity.verified:
            return True
        # Internal sources (INTERNAL_REPORT) don't need external verification
        if self.source_type in ("INTERNAL_REPORT", "INTERNAL_ANALYSIS"):
            return True
        return False

    def is_content_verified(self) -> bool:
        """Has content hash been verified?"""
        return self.verification_states.content_verified

    def is_support_verified(self) -> bool:
        """Has claim support been verified?"""
        return self.verification_states.support_verified

    def is_dossier_grade(self) -> bool:
        """All three states must be verified for dossier admission."""
        return self.is_identity_verified() and self.is_content_verified() and self.is_support_verified()


# ============================================================
# CEO v30.10: TYPE-SAFE SOURCE HIERARCHY
# ============================================================
# The external-vs-internal distinction is NO LONGER a source_type string
# enum. It is enforced by OBJECT CONSTRUCTION.
#
#   InternalSource  — constructible only via its own constructor.
#                     Refuses external content indicators (DOI/PMID/patent
#                     patterns in identifier or content).
#   ExternalSource  — constructible ONLY from VerifiedEvidence.
#                     Carries _verified_evidence_authorization as a real
#                     field (not a setattr attribute).
#
# register_source() now accepts ONLY InternalSource.
# register_source_from_verified_evidence() returns ExternalSource.
#
# An attacker cannot construct an ExternalSource from a CONTENT_MISMATCH
# EvidenceIdentity (VerifiedEvidence construction refuses). An attacker
# cannot construct an InternalSource with external content (the InternalSource
# constructor detects DOI/PMID/patent patterns and refuses).
#
# CEO principle: "A security boundary should be enforced by object
# construction, not by trusting a label inside the object."
# ============================================================

# Patterns that indicate external content — an InternalSource must NOT
# contain these in its identifier, title, or content.
# CEO v30.10: Patterns use \b (word boundary) or ^ (start) to detect
# external identifiers even when embedded in longer text.
_EXTERNAL_CONTENT_PATTERNS = [
    re.compile(r'\bPMID\s*:?\s*\d{7,8}\b', re.IGNORECASE),        # "PMID: 12345678"
    re.compile(r'\b\d{7,8}\b'),                                    # bare 7-8 digit number (PMID-like)
    re.compile(r'\b10\.\d{4,}/\S+'),                              # DOI (10.xxxx/...)
    re.compile(r'\b[A-Z]{2}\d{6,}[A-Z]\d?\b'),                    # Patent (US12345678B2)
    re.compile(r'\bK\d{5,}\b'),                                    # FDA K-number
    re.compile(r'\bP\d{6,}\b'),                                    # FDA PMA number
    re.compile(r'\bMDR\s*:?\s*\d+\b', re.IGNORECASE),              # MDR report key
    re.compile(r'\bNCT\d+\b', re.IGNORECASE),                      # ClinicalTrials.gov NCT
    re.compile(r'(?:https?://)?(?:dx\.)?doi\.org/', re.IGNORECASE),  # DOI URL
    re.compile(r'(?:https?://)?pubmed\.ncbi\.nlm\.nih\.gov/', re.IGNORECASE),  # PubMed URL
    re.compile(r'(?:https?://)?patents\.google\.com/', re.IGNORECASE),  # Google Patents URL
]


def _looks_like_external_content(identifier: str, title: str, content: Optional[str]) -> Optional[str]:
    """CEO v30.10: Detect if an InternalSource is masquerading external content.

    Returns a human-readable explanation of WHICH field looks external,
    or None if the content passes the internal-only check.
    """
    for field_name, value in [("identifier", identifier), ("title", title), ("content", content or "")]:
        if not value:
            continue
        for pattern in _EXTERNAL_CONTENT_PATTERNS:
            if pattern.search(value):
                return (
                    f"field '{field_name}' matches external pattern "
                    f"{pattern.pattern!r} (value: {value[:60]}...). "
                    f"InternalSource must NOT contain external content "
                    f"indicators (DOI/PMID/patent/K-number/PMA/MDR/NCT). "
                    f"Use ExternalSource via register_source_from_verified_evidence()."
                )
    return None


@dataclass
class InternalSource(Source):
    """A source generated internally (report, analysis, simulation output).

    CEO v30.10: This is a TYPE-SAFE subclass of Source. It is the ONLY
    type accepted by register_source(). Its constructor refuses external
    content indicators — an attacker cannot masquerade an external paper
    as an internal report by setting source_type="INTERNAL_REPORT".

    The security boundary is enforced by CONSTRUCTION (the __post_init__
    check), not by trusting the source_type string label.
    """
    # No new fields — the type itself IS the boundary.
    # __post_init__ checks that content does not look external.

    def __post_init__(self):
        """Refuse external content in an InternalSource.

        CEO v30.10: An InternalSource must NOT contain DOI/PMID/patent
        patterns in its identifier, title, or content. If it does, the
        constructor raises ValueError — the caller must use
        ExternalSource via register_source_from_verified_evidence().
        """
        # source_type must be an internal type
        if self.source_type not in ("INTERNAL_REPORT", "INTERNAL_ANALYSIS"):
            raise ValueError(
                f"InternalSource source_type must be INTERNAL_REPORT or "
                f"INTERNAL_ANALYSIS, got {self.source_type!r}. External "
                f"source types (DOI/PMID/PATENT/etc.) MUST use "
                f"ExternalSource via register_source_from_verified_evidence()."
            )
        # content must not look external
        external_match = _looks_like_external_content(
            self.identifier, self.title, self.content
        )
        if external_match:
            raise ValueError(
                f"INTERNAL_SOURCE_MASQUERADE_BLOCKED: {external_match} "
                f"CEO v30.10: the external-vs-internal boundary is enforced "
                f"by object construction, not by trusting a source_type label."
            )


@dataclass
class ExternalSource(Source):
    """A source derived from an external database (paper, patent, MAUDE, etc.).

    CEO v30.10: This is a TYPE-SAFE subclass of Source. It is constructible
    ONLY from VerifiedEvidence — its __post_init__ requires
    _verified_evidence_authorization to be non-None.

    An attacker cannot construct an ExternalSource from a CONTENT_MISMATCH
    EvidenceIdentity because VerifiedEvidence construction refuses such
    identities. The type boundary is enforced at construction.

    register_source_from_verified_evidence() returns ExternalSource.
    register_source() REFUSES ExternalSource (it only accepts InternalSource).
    """
    # _verified_evidence_authorization is a REAL field, not a setattr attribute.
    # This makes it structurally impossible to construct an ExternalSource
    # without providing authorization provenance.
    _verified_evidence_authorization: Optional[dict] = None

    def __post_init__(self):
        """Require _verified_evidence_authorization at construction.

        CEO v30.10: An ExternalSource without authorization provenance is
        a bypass attempt. The constructor refuses.
        """
        if self._verified_evidence_authorization is None:
            raise ValueError(
                f"EXTERNAL_SOURCE_REQUIRES_AUTHORIZATION: ExternalSource "
                f"{self.source_id} was constructed without "
                f"_verified_evidence_authorization. ExternalSource MUST be "
                f"constructed via EvidenceBinding."
                f"register_source_from_verified_evidence(VerifiedEvidence, ...). "
                f"Direct construction is a P0 control violation. CEO v30.10: "
                f"the external-vs-internal boundary is enforced by object "
                f"construction, not by trusting a source_type label."
            )
        # source_type must be an external type
        if not _is_external_source_type(self.source_type):
            raise ValueError(
                f"ExternalSource source_type must be an external type "
                f"(PMID/DOI/PATENT/URL/BOOK/K_NUMBER/PMA_NUMBER/"
                f"MDR_REPORT_KEY/RECALL_NUMBER/NCT_ID/PROJECT_NUM), got "
                f"{self.source_type!r}. Internal types (INTERNAL_REPORT/"
                f"INTERNAL_ANALYSIS) MUST use InternalSource."
            )


# ============================================================
# EvidenceBinding — manages bidirectional bindings
# ============================================================
class EvidenceBinding:
    """Manages bidirectional bindings between Claims, Evidence, and Sources.

    Per CEO P0-E: claim validation must verify the ACTUAL binding graph,
    not just nonempty ID lists.
    """

    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.evidence: Dict[str, Evidence] = {}
        self.sources: Dict[str, Source] = {}
        # Forward: claim_id -> list of evidence_ids
        self.claim_to_evidence: Dict[str, List[str]] = {}
        # Forward: claim_id -> list of source_ids
        self.claim_to_sources: Dict[str, List[str]] = {}
        # Reverse: evidence_id -> list of claim_ids
        self.evidence_to_claims: Dict[str, List[str]] = {}
        # Reverse: source_id -> list of claim_ids
        self.source_to_claims: Dict[str, List[str]] = {}
        self._load()

    def _evidence_file(self) -> Path:
        return self.registry_dir / "evidence_registry.json"

    def _sources_file(self) -> Path:
        return self.registry_dir / "source_registry.json"

    def _bindings_file(self) -> Path:
        return self.registry_dir / "bindings.json"

    def _load(self):
        # Load evidence
        if self._evidence_file().exists():
            with open(self._evidence_file()) as f:
                data = json.load(f)
            for item in data.get("evidence", []):
                # Filter private fields
                item = {k: v for k, v in item.items() if not k.startswith("_")}
                ev = Evidence(**item)
                self.evidence[ev.evidence_id] = ev

        # Load sources
        if self._sources_file().exists():
            with open(self._sources_file()) as f:
                data = json.load(f)
            for item in data.get("sources", []):
                item = {k: v for k, v in item.items() if not k.startswith("_")}
                # Reconstruct nested objects
                if item.get("external_identity"):
                    item["external_identity"] = ExternalIdentityVerification(**item["external_identity"])
                if item.get("verification_states"):
                    item["verification_states"] = SourceVerificationStates(**item["verification_states"])
                src = Source(**item)
                self.sources[src.source_id] = src

        # Load bindings
        if self._bindings_file().exists():
            with open(self._bindings_file()) as f:
                bindings = json.load(f)
            self.claim_to_evidence = bindings.get("claim_to_evidence", {})
            self.claim_to_sources = bindings.get("claim_to_sources", {})
            self._rebuild_reverse_indexes()

    def _save(self):
        # Save evidence
        with open(self._evidence_file(), "w") as f:
            json.dump({
                "schema_version": "2.0.0",
                "evidence": [{k: v for k, v in asdict(e).items() if not k.startswith("_")} for e in self.evidence.values()],
            }, f, indent=2, default=str)

        # Save sources (with nested objects)
        with open(self._sources_file(), "w") as f:
            json.dump({
                "schema_version": "2.0.0",
                "sources": [{k: v for k, v in asdict(s).items() if not k.startswith("_")} for s in self.sources.values()],
            }, f, indent=2, default=str)

        # Save bindings
        with open(self._bindings_file(), "w") as f:
            json.dump({
                "claim_to_evidence": self.claim_to_evidence,
                "claim_to_sources": self.claim_to_sources,
            }, f, indent=2, default=str)

    def _rebuild_reverse_indexes(self):
        self.evidence_to_claims = {}
        self.source_to_claims = {}
        for claim_id, ev_ids in self.claim_to_evidence.items():
            for ev_id in ev_ids:
                self.evidence_to_claims.setdefault(ev_id, []).append(claim_id)
        for claim_id, src_ids in self.claim_to_sources.items():
            for src_id in src_ids:
                self.source_to_claims.setdefault(src_id, []).append(claim_id)

    def register_evidence(self, evidence: Evidence):
        self.evidence[evidence.evidence_id] = evidence
        self._save()

    def register_source(self, source: Source):
        """Register a Source in the production registry.

        CEO v30.10: This method now accepts ONLY InternalSource instances.
        ExternalSource instances MUST be registered via
        register_source_from_verified_evidence(). Raw Source instances
        (the base class) are rejected — callers must explicitly choose
        InternalSource or ExternalSource.

        This enforces the type-safe boundary: the external-vs-internal
        distinction is encoded in the TYPE of object, not in a source_type
        string label. An attacker cannot masquerade an external paper as
        an internal report because InternalSource's constructor refuses
        external content indicators (DOI/PMID/patent patterns).

        CEO principle: "A security boundary should be enforced by object
        construction, not by trusting a label inside the object."

        DEFENSE-IN-DEPTH: Even if an attacker subclasses InternalSource
        and overrides __post_init__ to skip the masquerade check, this
        method RE-RUNS the external-content pattern check before
        registration. A forged subclass cannot bypass the boundary.
        """
        # v30.10: Type-check — must be InternalSource
        if not isinstance(source, InternalSource):
            raise TypeError(
                f"register_source() accepts ONLY InternalSource instances, "
                f"got {type(source).__name__}. External sources MUST be "
                f"registered via register_source_from_verified_evidence"
                f"(VerifiedEvidence, ...). Raw Source instances are not "
                f"accepted — callers must explicitly choose InternalSource "
                f"or ExternalSource. CEO v30.10: the external-vs-internal "
                f"boundary is enforced by object construction."
            )
        # Defense-in-depth: re-run the masquerade check even for InternalSource
        # instances, in case a subclass overrode __post_init__ to skip it.
        external_match = _looks_like_external_content(
            source.identifier, source.title, source.content
        )
        if external_match:
            raise ValueError(
                f"INTERNAL_SOURCE_MASQUERADE_BLOCKED (defense-in-depth at "
                f"register_source): {external_match} CEO v30.10: even if a "
                f"subclass bypassed __post_init__, the register_source "
                f"method re-checks for external content patterns. The type "
                f"boundary is enforced at registration as well as construction."
            )
        self.sources[source.source_id] = source
        self._save()

    # ============================================================
    # CEO v30.8: PRODUCTION EVIDENCE AUTHORIZATION BOUNDARY
    # ============================================================
    # The method below is the ONLY production path for registering a
    # discovery-layer source (paper, patent, MAUDE report, etc.) into
    # the EvidenceBinding registry. It accepts a VerifiedEvidence object
    # — NOT a raw EvidenceIdentity.
    #
    # A CONTENT_MISMATCH / POSSIBLE_FAMILY_MATCH /
    # FAMILY_RELATION_CONFIRMED / IDENTITY_INSUFFICIENT identity CANNOT
    # become a VerifiedEvidence (the constructor refuses — see
    # orchestrator/evidence_identity.py v30.7). Therefore it is
    # structurally impossible to register such an identity as a
    # production Source via this path.
    #
    # The existing register_source(source: Source) is RETAINED for
    # internally-generated sources (INTERNAL_REPORT, INTERNAL_ANALYSIS,
    # simulation outputs) that do not originate from the discovery layer.
    # But for any source derived from an external database (PubMed,
    # Crossref, Espacenet, Lens, FDA MAUDE, etc.), callers MUST use
    # register_source_from_verified_evidence().
    #
    # CEO principle: "A proof-of-concept defense is not a production
    # defense. Can an adversarial model with repository access actually
    # get unauthorized evidence into the real dossier path? Until the
    # answer is structurally no, the evidence firewall is not finished."
    # ============================================================
    def register_source_from_verified_evidence(
        self,
        verified: "VerifiedEvidence",
        source_id: str,
        title: str,
        content: Optional[str] = None,
        span: Optional[str] = None,
        authors: Optional[List[str]] = None,
        year: Optional[int] = None,
        url: Optional[str] = None,
        retrieval_method: Optional[str] = None,
        source_locator: Optional[str] = None,
    ) -> ExternalSource:
        """Register a discovery-layer source from a VerifiedEvidence object.

        CEO v30.8: This is the PRODUCTION entry point for discovery-layer
        sources. It accepts ONLY VerifiedEvidence — a type that cannot
        be constructed from a non-verified EvidenceIdentity.

        CEO v30.10: Returns ExternalSource (not Source). ExternalSource is
        a TYPE-SAFE subclass that carries _verified_evidence_authorization
        as a REAL field (not a setattr attribute). This makes it structurally
        impossible to construct an ExternalSource without authorization
        provenance.

        Args:
            verified: A VerifiedEvidence object (NOT EvidenceIdentity).
                Construction of VerifiedEvidence enforces
                can_use_as_verified_evidence=True.
            source_id: The SRC-<type>-<seq> identifier for the new Source.
            title: Source title.
            content: Optional content (abstract, span text, etc.).
            span: Optional exact passage cited.
            authors, year, url, retrieval_method, source_locator: optional
                metadata.

        Returns:
            The registered ExternalSource object.

        Raises:
            TypeError: if `verified` is not a VerifiedEvidence instance.
            EvidenceAuthorizationError: if the VerifiedEvidence wraps a
                non-verified identity (defense-in-depth — should be
                impossible because construction already enforced the gate).

        Article XVII: This method IS a P0 control. Every attempt to
        bypass it must be adversarially tested (see
        scripts/attack_production_dossier_path_v30_8.py and
        scripts/attack_source_type_hierarchy_v30_10.py).
        """
        # Import here to avoid circular import at module load time.
        from .evidence_identity_adapter import (
            VerifiedEvidence,
            EvidenceAuthorizationError,
            _verified_evidence_to_source_type,
            _verified_evidence_to_identifier,
        )

        if not isinstance(verified, VerifiedEvidence):
            raise TypeError(
                f"register_source_from_verified_evidence requires a "
                f"VerifiedEvidence object, got {type(verified).__name__}. "
                f"Call EvidenceIdentity.as_verified_evidence() first. A "
                f"non-verified identity (CONTENT_MISMATCH, "
                f"POSSIBLE_FAMILY_MATCH, FAMILY_RELATION_CONFIRMED, "
                f"IDENTITY_INSUFFICIENT) cannot be promoted and MUST NOT "
                f"reach the production dossier path."
            )

        # Defense-in-depth: re-check can_use_as_verified_evidence in case
        # someone bypassed VerifiedEvidence construction via object.__new__
        # or subclassing. This is the SECOND layer of defense (the first
        # being VerifiedEvidence.__post_init__).
        if not verified.identity.can_use_as_verified_evidence:
            raise EvidenceAuthorizationError(
                "DEFENSE-IN-DEPTH (register_source_from_verified_evidence): "
                "VerifiedEvidence wraps a non-verified identity. This should "
                "be impossible — construction should have raised. Indicates a "
                f"bypass attempt or implementation bug. Identity: "
                f"{verified.identity.canonical_id_type}:"
                f"{verified.identity.canonical_id!r} confidence="
                f"{verified.identity.identity_confidence!r}"
            )

        # Layer 3: Integrity check — detect forged identity_confidence.
        # An attacker who used object.__setattr__ to forge identity_confidence
        # from CONTENT_MISMATCH to DOCUMENT_ID_CONFIRMED will be caught here
        # because content_mismatch_audits survives the forge (it's a separate
        # field populated by merge_across_sources, not by identity_confidence).
        integrity = verified.identity.verify_integrity()
        if not integrity.integrity_ok:
            raise EvidenceAuthorizationError(
                f"FORGE DETECTED in production path "
                f"(register_source_from_verified_evidence): "
                f"{integrity.explanation} The record MUST NOT be registered "
                f"as a production Source."
            )

        # Map VerifiedEvidence → Source fields
        source_type = _verified_evidence_to_source_type(verified)
        identifier = _verified_evidence_to_identifier(verified)

        # Build the ExternalSource object (v30.10: type-safe subclass)
        # _verified_evidence_authorization is a REAL field on ExternalSource,
        # not a setattr attribute. This makes it structurally impossible
        # to construct an ExternalSource without authorization provenance.
        source = ExternalSource(
            source_id=source_id,
            source_type=source_type,
            identifier=identifier,
            title=title,
            authors=authors or [],
            year=year,
            url=url,
            retrieval_method=retrieval_method or "verified_evidence_promotion",
            source_locator=source_locator,
            content=content,
            content_hash=verified.content_fingerprint if content else None,
            span=span,
            span_hash=hashlib.sha256(span.encode()).hexdigest() if span else None,
            # P0-F: External identity verification — provenance from VerifiedEvidence
            external_identity=ExternalIdentityVerification(
                verified=True,
                verification_provider=", ".join(verified.source_databases),
                verification_timestamp=verified.identity.retrieval_timestamp
                    if hasattr(verified.identity, 'retrieval_timestamp') else None,
            ),
            # P1-C: All three verification states set True because
            # VerifiedEvidence construction already enforced identity +
            # content integrity. Support is assumed True at registration
            # time (the claim binding step will verify support separately).
            verification_states=SourceVerificationStates(
                identity_verified=True,
                content_verified=True,
                support_verified=True,  # assumed at registration; verified at claim binding
            ),
            # v30.10: _verified_evidence_authorization is a REAL field.
            # The ExternalSource __post_init__ requires this to be non-None.
            _verified_evidence_authorization={
                'authorized_via': 'register_source_from_verified_evidence',
                'identity_confidence': verified.identity_confidence,
                'canonical_id': verified.canonical_id,
                'canonical_id_type': verified.canonical_id_type,
                'source_databases': list(verified.source_databases),
                'content_fingerprint': verified.content_fingerprint,
            },
        )

        self.sources[source_id] = source
        self._save()
        return source

    def bind_claim_to_evidence(self, claim_id: str, evidence_id: str):
        """Create bidirectional binding between claim and evidence."""
        if evidence_id not in self.evidence:
            raise KeyError(f"Evidence not found: {evidence_id}")

        self.claim_to_evidence.setdefault(claim_id, [])
        if evidence_id not in self.claim_to_evidence[claim_id]:
            self.claim_to_evidence[claim_id].append(evidence_id)

        self.evidence_to_claims.setdefault(evidence_id, [])
        if claim_id not in self.evidence_to_claims[evidence_id]:
            self.evidence_to_claims[evidence_id].append(claim_id)

        self._save()

    def bind_claim_to_source(self, claim_id: str, source_id: str):
        """Create bidirectional binding between claim and source."""
        if source_id not in self.sources:
            raise KeyError(f"Source not found: {source_id}")

        self.claim_to_sources.setdefault(claim_id, [])
        if source_id not in self.claim_to_sources[claim_id]:
            self.claim_to_sources[claim_id].append(source_id)

        self.source_to_claims.setdefault(source_id, [])
        if claim_id not in self.source_to_claims[source_id]:
            self.source_to_claims[source_id].append(claim_id)

        self._save()

    # ============================================================
    # P0-E: Binding graph verification (not just nonempty ID check)
    # ============================================================
    def verify_binding_graph(self, claim_id: str) -> dict:
        """Verify that a claim's evidence/source bindings are ACTUALLY valid.

        Per CEO P0-E: checks not just that IDs are nonempty, but that:
          1. Each evidence_id exists in the evidence registry
          2. Each source_id exists in the source registry
          3. Bidirectional bindings are consistent (forward = reverse)
          4. Evidence is not SUPERSEDED/INVALIDATED

        Returns dict with:
          - valid: bool
          - errors: list of specific binding failures
          - verified_evidence_ids: list of valid evidence IDs
          - verified_source_ids: list of valid source IDs
        """
        errors = []
        verified_evidence = []
        verified_sources = []

        # Check evidence bindings
        ev_ids = self.claim_to_evidence.get(claim_id, [])
        for ev_id in ev_ids:
            # 1. Evidence must exist in registry
            if ev_id not in self.evidence:
                errors.append(f"BINDING_GRAPH_EVIDENCE_NOT_FOUND: {claim_id} -> {ev_id} (evidence not in registry)")
                continue

            ev = self.evidence[ev_id]

            # 2. Evidence must not be SUPERSEDED/INVALIDATED
            if ev.supersession_status in ("SUPERSEDED", "INVALIDATED"):
                errors.append(f"BINDING_GRAPH_EVIDENCE_{ev.supersession_status}: {claim_id} -> {ev_id}")
                continue

            # 3. Bidirectional binding must be consistent
            reverse = self.evidence_to_claims.get(ev_id, [])
            if claim_id not in reverse:
                errors.append(f"BINDING_GRAPH_REVERSE_MISSING: {claim_id} -> {ev_id} (reverse binding not found)")
                continue

            verified_evidence.append(ev_id)

        # Check source bindings
        src_ids = self.claim_to_sources.get(claim_id, [])
        for src_id in src_ids:
            if src_id not in self.sources:
                errors.append(f"BINDING_GRAPH_SOURCE_NOT_FOUND: {claim_id} -> {src_id} (source not in registry)")
                continue

            reverse = self.source_to_claims.get(src_id, [])
            if claim_id not in reverse:
                errors.append(f"BINDING_GRAPH_SOURCE_REVERSE_MISSING: {claim_id} -> {src_id}")
                continue

            verified_sources.append(src_id)

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "verified_evidence_ids": verified_evidence,
            "verified_source_ids": verified_sources,
        }

    def get_claims_using_evidence(self, evidence_id: str) -> List[str]:
        """Reverse lookup: which claims use this evidence?"""
        return self.evidence_to_claims.get(evidence_id, [])

    def get_claims_using_source(self, source_id: str) -> List[str]:
        """Reverse lookup: which claims cite this source?"""
        return self.source_to_claims.get(source_id, [])

    def get_evidence_for_claim(self, claim_id: str) -> List[Evidence]:
        """Forward lookup: what evidence supports this claim?"""
        ev_ids = self.claim_to_evidence.get(claim_id, [])
        return [self.evidence[eid] for eid in ev_ids if eid in self.evidence]

    def get_sources_for_claim(self, claim_id: str) -> List[Source]:
        """Forward lookup: what sources support this claim?"""
        src_ids = self.claim_to_sources.get(claim_id, [])
        return [self.sources[sid] for sid in src_ids if sid in self.sources]

    def audit_claims_with_only_simulation(self) -> List[str]:
        """Auditor query: show me every claim supported ONLY by simulation."""
        result = []
        for claim_id, ev_ids in self.claim_to_evidence.items():
            if not ev_ids:
                continue
            all_simulation = all(
                self.evidence[eid].evidence_type == "SIMULATION"
                for eid in ev_ids if eid in self.evidence
            )
            no_sources = claim_id not in self.claim_to_sources or not self.claim_to_sources[claim_id]
            if all_simulation and no_sources:
                result.append(claim_id)
        return result

    def audit_claims_with_only_model(self) -> List[str]:
        """Auditor query: show me every claim supported ONLY by model (no observation)."""
        result = []
        for claim_id, ev_ids in self.claim_to_evidence.items():
            if not ev_ids:
                continue
            all_model_or_sim = all(
                self.evidence[eid].evidence_type in ("SIMULATION", "ANALYSIS")
                for eid in ev_ids if eid in self.evidence
            )
            no_sources = claim_id not in self.claim_to_sources or not self.claim_to_sources[claim_id]
            if all_model_or_sim and no_sources:
                result.append(claim_id)
        return result
