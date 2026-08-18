"""
epistemic_integrity/evidence_binding.py — Bidirectional Claim <-> Evidence <-> Source binding

Per CEO directive:
  "Every final sentence should be traceable:
     Dossier sentence → Claim ID → Evidence IDs → Source IDs / Experiment IDs
     → Hashes → Commit → Current state
   And reverse:
     Evidence → Which claims use it? → Which dossiers contain those claims?"

This module enforces bidirectional traceability.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone


@dataclass
class Evidence:
    """An experiment or simulation that produces evidence."""
    evidence_id: str  # EXP-CV-T<territory>-<seq>
    territory_id: str
    description: str
    evidence_type: str  # SIMULATION / EXPERIMENT / BENCHTOP / ANALYSIS
    reproducibility_capsule_id: Optional[str] = None  # links to reproducibility_capsules/
    code_commit: Optional[str] = None  # git commit hash
    config_hash: Optional[str] = None
    input_hashes: List[str] = field(default_factory=list)
    output_hash: Optional[str] = None
    random_seed: Optional[int] = None
    python_version: Optional[str] = None
    dependency_lock_hash: Optional[str] = None
    model_id: Optional[str] = None
    model_parameters: Dict = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supersession_status: str = "CURRENT"
    superseded_by: Optional[str] = None


@dataclass
class Source:
    """An external source (paper, patent, etc.) cited as evidence.

    Per CEO P0-2: sources must have cryptographically verifiable content.
    """
    source_id: str  # SRC-<type>-<seq> e.g. SRC-PMID-12345, SRC-PATENT-US12345
    source_type: str  # PMID / PATENT / DOI / URL / BOOK
    identifier: str  # the actual PMID, patent number, DOI, etc.
    title: str
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    url: Optional[str] = None
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    retrieval_method: Optional[str] = None  # "Lens API" / "Scopus API" / "Google Patents web" / etc.
    content: Optional[str] = None  # actual retrieved content (abstract, claim text, passage)
    content_hash: Optional[str] = None  # SHA256(content) — MUST recompute to verify
    span: Optional[str] = None  # exact passage cited
    span_hash: Optional[str] = None  # SHA256(span) — MUST recompute to verify
    source_locator: Optional[str] = None  # full URL or file path to immutable artifact
    # Immutability: once registered with content_hash, content cannot change
    _content_immutable: bool = False


@dataclass
class Evidence:
    """An experiment or simulation that produces evidence.

    Per CEO P1: hashes must recompute from repository artifacts, not just be stored.
    """
    evidence_id: str  # EXP-CV-T<territory>-<seq>
    territory_id: str
    description: str
    evidence_type: str  # SIMULATION / EXPERIMENT / BENCHTOP / ANALYSIS
    reproducibility_capsule_id: Optional[str] = None  # links to reproducibility_capsules/
    code_commit: Optional[str] = None  # git commit hash
    config_hash: Optional[str] = None
    input_hashes: List[str] = field(default_factory=list)
    output_content: Optional[str] = None  # actual output JSON content
    output_hash: Optional[str] = None  # SHA256(output_content) — MUST recompute
    random_seed: Optional[int] = None
    python_version: Optional[str] = None
    dependency_lock_hash: Optional[str] = None
    model_id: Optional[str] = None
    model_parameters: Dict = field(default_factory=dict)
    artifact_path: Optional[str] = None  # path to output file in repo
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supersession_status: str = "CURRENT"
    superseded_by: Optional[str] = None


class EvidenceBinding:
    """Manages bidirectional bindings between Claims, Evidence, and Sources."""

    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.evidence: Dict[str, Evidence] = {}
        self.sources: Dict[str, Source] = {}
        # Forward: claim_id -> list of evidence_ids
        self.claim_to_evidence: Dict[str, List[str]] = {}
        # Forward: claim_id -> list of source_ids
        self.claim_to_sources: Dict[str, List[str]] = {}
        # Reverse: evidence_id -> list of claim_ids that use it
        self.evidence_to_claims: Dict[str, List[str]] = {}
        # Reverse: source_id -> list of claim_ids that use it
        self.source_to_claims: Dict[str, List[str]] = {}
        self._load()

    def _evidence_file(self) -> Path:
        return self.registry_dir / "evidence_registry.json"

    def _sources_file(self) -> Path:
        return self.registry_dir / "source_registry.json"

    def _bindings_file(self) -> Path:
        return self.registry_dir / "bindings.json"

    def _load(self):
        for path, attr, cls_name in [
            (self._evidence_file(), "evidence", "Evidence"),
            (self._sources_file(), "sources", "Source"),
        ]:
            if path.exists():
                with open(path) as f:
                    data = json.load(f)
                cls = Evidence if cls_name == "Evidence" else Source
                for item in data.get(attr, []):
                    # Filter out private fields
                    item = {k: v for k, v in item.items() if not k.startswith("_")}
                    obj = cls(**item)
                    key = obj.evidence_id if cls == Evidence else obj.source_id
                    getattr(self, attr)[key] = obj

        if self._bindings_file().exists():
            with open(self._bindings_file()) as f:
                bindings = json.load(f)
            self.claim_to_evidence = bindings.get("claim_to_evidence", {})
            self.claim_to_sources = bindings.get("claim_to_sources", {})
            self._rebuild_reverse_indexes()

    def _save(self):
        with open(self._evidence_file(), "w") as f:
            json.dump({
                "schema_version": "1.0.0",
                "evidence": [{k: v for k, v in asdict(e).items() if not k.startswith("_")} for e in self.evidence.values()],
            }, f, indent=2, default=str)

        with open(self._sources_file(), "w") as f:
            json.dump({
                "schema_version": "1.0.0",
                "sources": [{k: v for k, v in asdict(s).items() if not k.startswith("_")} for s in self.sources.values()],
            }, f, indent=2, default=str)

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

        # Forward
        self.claim_to_evidence.setdefault(claim_id, [])
        if evidence_id not in self.claim_to_evidence[claim_id]:
            self.claim_to_evidence[claim_id].append(evidence_id)

        # Reverse
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
