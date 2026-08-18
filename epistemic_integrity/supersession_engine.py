"""
epistemic_integrity/supersession_engine.py — Enforces CURRENT/SUPERSEDED/INVALIDATED/HISTORICAL/FROZEN

Per CEO directive:
  "V18 called impedance a breakthrough.
   V19 destroyed it under electrode-fouling attacks.
   V20 partially recovered it.
   V21 exposed additional failures.
   V22–V25 eventually demonstrated numerical non-identifiability and froze the branch.
   That historical sequence is excellent research provenance.
   But a dossier generator could still retrieve the V18 '+34pp breakthrough'
   and present it without the later V19–V25 destruction. That is unacceptable.
   Every artifact needs: CURRENT / SUPERSEDED / INVALIDATED / HISTORICAL / FROZEN
   plus: superseded_by / supersedes / invalidated_by / reason
   The retrieval layer must exclude SUPERSEDED from current-state answers
   unless explicitly requested."
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone


VALID_STATUSES = {"CURRENT", "SUPERSEDED", "INVALIDATED", "HISTORICAL", "FROZEN", "ARCHITECTURE_CHANGE"}


@dataclass
class ArtifactState:
    artifact_id: str  # e.g. "CV-T01-V18-impedance_breakthrough"
    territory_id: str
    version: str  # V18, V25, etc.
    description: str
    status: str  # one of VALID_STATUSES
    superseded_by: Optional[str] = None  # artifact_id that replaces this
    supersedes: Optional[str] = None  # artifact_id this replaces
    invalidated_by: Optional[str] = None  # artifact_id that invalidated this
    reason: str = ""
    frozen_reason: Optional[str] = None
    git_commit: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SupersessionEngine:
    """Manages artifact supersession state. Excludes SUPERSEDED from current-state queries."""

    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts: Dict[str, ArtifactState] = {}
        self._load()

    def _file(self) -> Path:
        return self.registry_dir / "supersession_registry.json"

    def _load(self):
        path = self._file()
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for item in data.get("artifacts", []):
                self.artifacts[item["artifact_id"]] = ArtifactState(**item)

    def _save(self):
        with open(self._file(), "w") as f:
            json.dump({
                "schema_version": "1.0.0",
                "artifacts": [asdict(a) for a in self.artifacts.values()],
            }, f, indent=2, default=str)

    def register_artifact(
        self,
        artifact_id: str,
        territory_id: str,
        version: str,
        description: str,
        status: str = "CURRENT",
        git_commit: str = None,
    ):
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {VALID_STATUSES}")
        self.artifacts[artifact_id] = ArtifactState(
            artifact_id=artifact_id,
            territory_id=territory_id,
            version=version,
            description=description,
            status=status,
            git_commit=git_commit,
        )
        self._save()

    def supersede(self, artifact_id: str, superseded_by: str, reason: str):
        """Mark artifact as SUPERSEDED by another artifact."""
        if artifact_id not in self.artifacts:
            raise KeyError(f"Artifact not found: {artifact_id}")
        a = self.artifacts[artifact_id]
        a.status = "SUPERSEDED"
        a.superseded_by = superseded_by
        a.reason = reason
        # Update the supersedes field on the replacing artifact
        if superseded_by in self.artifacts:
            self.artifacts[superseded_by].supersedes = artifact_id
        self._save()

    def invalidate(self, artifact_id: str, invalidated_by: str, reason: str):
        """Mark artifact as INVALIDATED (was wrong)."""
        if artifact_id not in self.artifacts:
            raise KeyError(f"Artifact not found: {artifact_id}")
        a = self.artifacts[artifact_id]
        a.status = "INVALIDATED"
        a.invalidated_by = invalidated_by
        a.reason = reason
        self._save()

    def freeze(self, artifact_id: str, frozen_reason: str):
        """Mark artifact as FROZEN (terminal state, e.g. NEGATIVE_CEILING)."""
        if artifact_id not in self.artifacts:
            raise KeyError(f"Artifact not found: {artifact_id}")
        a = self.artifacts[artifact_id]
        a.status = "FROZEN"
        a.frozen_reason = frozen_reason
        self._save()

    def get_current_artifacts(self, territory_id: str = None) -> List[ArtifactState]:
        """Get all CURRENT artifacts. SUPERSEDED/INVALIDATED/FROZEN/HISTORICAL are excluded."""
        result = []
        for a in self.artifacts.values():
            if a.status != "CURRENT":
                continue
            if territory_id and a.territory_id != territory_id:
                continue
            result.append(a)
        return result

    def is_current(self, artifact_id: str) -> bool:
        """Is this artifact's status CURRENT (usable for dossier)?"""
        if artifact_id not in self.artifacts:
            return False
        return self.artifacts[artifact_id].status == "CURRENT"

    def get_supersession_chain(self, artifact_id: str) -> List[ArtifactState]:
        """Get the full chain: this artifact → what superseded it → what superseded that → ..."""
        chain = []
        current_id = artifact_id
        while current_id and current_id in self.artifacts:
            a = self.artifacts[current_id]
            chain.append(a)
            current_id = a.superseded_by
        return chain

    def can_use_in_dossier(self, artifact_id: str) -> dict:
        """Check if an artifact can be used in the final dossier.

        Returns:
          - allowed: bool
          - reason: str (if not allowed)
          - supersession_chain: list of artifacts in the chain
        """
        if artifact_id not in self.artifacts:
            return {
                "allowed": False,
                "reason": f"ARTIFACT_NOT_REGISTERED: {artifact_id}",
                "supersession_chain": [],
            }

        a = self.artifacts[artifact_id]
        chain = self.get_supersession_chain(artifact_id)

        if a.status == "SUPERSEDED":
            return {
                "allowed": False,
                "reason": f"ARTIFACT_SUPERSEDED by {a.superseded_by}: {a.reason}",
                "supersession_chain": chain,
            }
        if a.status == "INVALIDATED":
            return {
                "allowed": False,
                "reason": f"ARTIFACT_INVALIDATED by {a.invalidated_by}: {a.reason}",
                "supersession_chain": chain,
            }
        if a.status == "FROZEN":
            return {
                "allowed": False,
                "reason": f"ARTIFACT_FROZEN: {a.frozen_reason}",
                "supersession_chain": chain,
            }
        if a.status == "HISTORICAL":
            return {
                "allowed": False,
                "reason": "ARTIFACT_HISTORICAL: not current state",
                "supersession_chain": chain,
            }
        if a.status == "ARCHITECTURE_CHANGE":
            return {
                "allowed": False,
                "reason": "ARTIFACT_ARCHITECTURE_CHANGE: replaced by different mechanism",
                "supersession_chain": chain,
            }

        return {
            "allowed": True,
            "reason": "CURRENT",
            "supersession_chain": chain,
        }
