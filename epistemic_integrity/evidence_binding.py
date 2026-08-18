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
        self.sources[source.source_id] = source
        self._save()

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
