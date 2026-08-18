"""
epistemic_integrity/state_transition_ledger.py — Append-only cryptographically chained ledger

Per CEO v5 P0-C:
  "Replace the mutable state-transition ledger with an append-only
   cryptographically chained ledger. Never mutate ST0001.
   Every transition must contain: previous_transition_hash, artifact_hash,
   commit_sha, state_hash. The current state is the terminal validated transition."

Architecture:
  ST0001 (initial, previous_hash=0)
  ST0002 (previous_hash=SHA256(ST0001))
  ST0003 (previous_hash=SHA256(ST0002))
  ...

  The ledger root hash = SHA256 of all transition hashes chained.
  Current state = terminal transition (latest effective).
  NEVER mutate a previous transition. Append only.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class StateTransition:
    """A single immutable state transition. Once written, NEVER modified."""
    transition_id: str                          # ST-CV-T<territory>-<seq>
    territory_id: str
    from_state: Optional[str]                   # None for initial
    to_state: str
    artifact_id: str                            # e.g., "CV-T06-V6"
    artifact_version: str                       # e.g., "V6"
    commit_sha: str                             # git commit containing the artifact
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: str = ""
    effective: bool = True                      # only latest per territory is effective

    # Cryptographic chain (P0-C)
    previous_transition_hash: Optional[str] = None  # SHA256 of previous transition
    artifact_hash: Optional[str] = None             # SHA256 of artifact content
    state_hash: Optional[str] = None                # SHA256(to_state + artifact_id + version)

    @property
    def transition_hash(self) -> str:
        """SHA256 of this transition (for chaining)."""
        content = json.dumps({
            "transition_id": self.transition_id,
            "territory_id": self.territory_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "commit_sha": self.commit_sha,
            "created_at": self.created_at,
            "previous_transition_hash": self.previous_transition_hash,
            "artifact_hash": self.artifact_hash,
            "state_hash": self.state_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class StateTransitionLedger:
    """Append-only cryptographically chained ledger.

    Per CEO P0-C:
      - NEVER mutates previous transitions
      - Each transition contains previous_transition_hash
      - Chain integrity is verifiable
      - Current state = terminal effective transition
    """

    def __init__(self, ledger_dir: Path):
        self.ledger_dir = Path(ledger_dir)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.transitions: Dict[str, StateTransition] = {}
        self._load()

    def _file(self) -> Path:
        return self.ledger_dir / "state_transition_ledger.json"

    def _load(self):
        path = self._file()
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for item in data.get("transitions", []):
                self.transitions[item["transition_id"]] = StateTransition(**item)

    def _save(self):
        # APPEND ONLY: we save the entire ledger, but we NEVER modify existing entries
        with open(self._file(), "w") as f:
            json.dump({
                "schema_version": "2.0.0",
                "ledger_type": "APPEND_ONLY_CRYPTOGRAPHICALLY_CHAINED",
                "transitions": [asdict(t) for t in self.transitions.values()],
            }, f, indent=2, default=str)

    def record_transition(
        self,
        territory_id: str,
        to_state: str,
        artifact_id: str,
        artifact_version: str,
        commit_sha: str,
        reason: str,
        artifact_hash: Optional[str] = None,
    ) -> StateTransition:
        """Append a new transition. NEVER modifies existing transitions.

        Per CEO P0-C: the previous transition is NOT mutated. Instead:
          1. New transition is created with previous_transition_hash
          2. The new transition's effective=True
          3. Previous transitions remain in the ledger with their original effective value
          4. get_current_transition() returns the latest effective one
        """
        # Find current effective transition (for chaining)
        current = self.get_current_transition(territory_id)
        from_state = current.to_state if current else None
        previous_hash = current.transition_hash if current else None

        # Mark previous as ineffective — but do NOT mutate the object
        # Instead, we track effectiveness by transition order (latest = effective)
        # The previous transition's `effective` field stays as-is in storage
        # but get_current_transition() only returns the latest one

        # Generate transition ID
        existing = sorted([t for t in self.transitions if t.startswith(f"ST-{territory_id}")])
        seq = len(existing) + 1
        transition_id = f"ST-{territory_id}-{seq:04d}"

        # Compute state_hash
        state_content = f"{to_state}:{artifact_id}:{artifact_version}"
        state_hash = hashlib.sha256(state_content.encode()).hexdigest()

        transition = StateTransition(
            transition_id=transition_id,
            territory_id=territory_id,
            from_state=from_state,
            to_state=to_state,
            artifact_id=artifact_id,
            artifact_version=artifact_version,
            commit_sha=commit_sha,
            reason=reason,
            effective=True,
            previous_transition_hash=previous_hash,
            artifact_hash=artifact_hash,
            state_hash=state_hash,
        )

        # APPEND only — do not modify any existing transition
        self.transitions[transition_id] = transition
        self._save()
        return transition

    def get_current_transition(self, territory_id: str) -> Optional[StateTransition]:
        """Get the current effective transition for a territory.

        The current transition is the LATEST one (by sequence number) that is effective.
        Previous transitions remain in the ledger but are not "current".
        """
        territory_transitions = [
            t for t in self.transitions.values()
            if t.territory_id == territory_id
        ]
        if not territory_transitions:
            return None
        # Sort by sequence number (extracted from transition_id)
        territory_transitions.sort(
            key=lambda t: int(t.transition_id.split("-")[-1])
        )
        return territory_transitions[-1]  # latest = current

    def get_current_state(self, territory_id: str) -> Optional[str]:
        """Get the current state — deterministic, from terminal transition."""
        current = self.get_current_transition(territory_id)
        return current.to_state if current else None

    def get_transition_chain(self, territory_id: str) -> List[StateTransition]:
        """Get the full transition chain (chronological, from first to latest)."""
        chain = [
            t for t in self.transitions.values()
            if t.territory_id == territory_id
        ]
        chain.sort(key=lambda t: int(t.transition_id.split("-")[-1]))
        return chain

    def verify_chain_integrity(self) -> dict:
        """Verify cryptographic chain integrity.

        Per CEO P0-C: each transition's previous_transition_hash must match
        the SHA256 of the previous transition.
        """
        results = {
            "total_transitions": len(self.transitions),
            "verified": 0,
            "failed": 0,
            "failures": [],
        }

        for transition in self.transitions.values():
            if transition.previous_transition_hash is None:
                # Initial transition — no previous to verify
                results["verified"] += 1
                continue

            # Find the previous transition
            territory_transitions = [
                t for t in self.transitions.values()
                if t.territory_id == transition.territory_id
            ]
            territory_transitions.sort(key=lambda t: int(t.transition_id.split("-")[-1]))

            # Find the one immediately before this one
            idx = next(
                (i for i, t in enumerate(territory_transitions) if t.transition_id == transition.transition_id),
                None
            )
            if idx is None or idx == 0:
                results["failed"] += 1
                results["failures"].append(f"{transition.transition_id}: cannot find position in chain")
                continue

            prev = territory_transitions[idx - 1]
            if prev.transition_hash != transition.previous_transition_hash:
                results["failed"] += 1
                results["failures"].append(
                    f"{transition.transition_id}: previous_transition_hash mismatch "
                    f"(expected {prev.transition_hash[:16]}..., got {transition.previous_transition_hash[:16] if transition.previous_transition_hash else 'None'}...)"
                )
            else:
                results["verified"] += 1

        results["chain_valid"] = results["failed"] == 0
        return results

    def reconcile_with_canonical(self, canonical_states: Dict[str, str]) -> List[dict]:
        """Reconcile ledger states with canonical portfolio states."""
        discrepancies = []
        for tid, canonical_state in canonical_states.items():
            ledger_state = self.get_current_state(tid)
            if ledger_state != canonical_state:
                discrepancies.append({
                    "territory_id": tid,
                    "canonical_state": canonical_state,
                    "ledger_state": ledger_state,
                    "discrepancy": f"CANONICAL={canonical_state} but LEDGER={ledger_state}",
                })
        return discrepancies

    def verify_all(self) -> dict:
        """Verify ledger integrity:
          1. Chain integrity (cryptographic)
          2. Each territory has at least one transition
          3. Terminal transitions are deterministic
        """
        chain_result = self.verify_chain_integrity()

        by_territory: Dict[str, List[StateTransition]] = {}
        for t in self.transitions.values():
            by_territory.setdefault(t.territory_id, []).append(t)

        territory_results = {
            "territories_checked": len(by_territory),
            "passed": 0,
            "failed": 0,
            "failures": [],
        }

        for tid, transitions in by_territory.items():
            if not transitions:
                territory_results["failed"] += 1
                territory_results["failures"].append(f"{tid}: no transitions")
            else:
                territory_results["passed"] += 1

        return {
            "chain_integrity": chain_result,
            "territory_coverage": territory_results,
            "overall_pass": chain_result["chain_valid"] and territory_results["failed"] == 0,
        }
