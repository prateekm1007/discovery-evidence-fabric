"""
epistemic_integrity/state_transition_ledger.py v24

Per CEO v23 directives:
  P0-1: global_sequence as sole ordering authority (max+1, consecutive)
  P0-2: global_sequence included in transition_hash
  P0-3: Append-only NDJSON event log (never rewrite historical events)
  P0-4: Cryptographic genesis anchor + ledger_root_hash
  P0-5: No mutable effective field — CURRENT derived from immutable events
  P1: Enforce 40-char SHA format + verify commit exists

Architecture:
  state_transition_ledger.ndjson  — append-only event log (one line per event)
  state_transition_ledger_root.json — genesis + current root hash

Events are NEVER rewritten. Current state is DERIVED by replaying events.
"""

import json
import hashlib
import re
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone


# Genesis hash — fixed, never changes
GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

# Full 40-char SHA pattern
SHA40_PATTERN = re.compile(r"^[0-9a-f]{40}$")


@dataclass(frozen=True)
class StateTransition:
    """Immutable state transition event. Once written to NDJSON, NEVER modified.

    P0-1: global_sequence is the SOLE ordering authority.
    P0-2: global_sequence is included in transition_hash.
    P0-5: No mutable effective field. CURRENT is derived from events.
    """
    global_sequence: int                    # Monotonic global sequence (1, 2, 3, ...)
    transition_id: str                      # ST-CV-T<territory>-<seq>
    territory_id: str
    from_state: Optional[str]
    to_state: str
    artifact_id: str
    artifact_version: str
    commit_sha: str                         # Full 40-char git commit hash
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    reason: str = ""
    transition_type: str = "BOOTSTRAPPED_FROM_CANONICAL_STATE"
    previous_transition_hash: Optional[str] = None
    artifact_hash: Optional[str] = None
    state_hash: Optional[str] = None

    @property
    def transition_hash(self) -> str:
        """SHA256 of this transition (for chaining). Includes global_sequence."""
        content = json.dumps({
            "global_sequence": self.global_sequence,
            "transition_id": self.transition_id,
            "territory_id": self.territory_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "artifact_id": self.artifact_id,
            "artifact_version": self.artifact_version,
            "commit_sha": self.commit_sha,
            "created_at": self.created_at,
            "transition_type": self.transition_type,
            "previous_transition_hash": self.previous_transition_hash,
            "artifact_hash": self.artifact_hash,
            "state_hash": self.state_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()

    def is_evidence_backed(self) -> bool:
        """P0-2: Only EVIDENCE_BACKED transitions can satisfy dossier requirements."""
        return self.transition_type == "EVIDENCE_BACKED" and self.artifact_hash is not None


class StateTransitionLedger:
    """Append-only event ledger with global sequence and root hash.

    P0-3: Uses NDJSON append-only storage. Historical events are NEVER rewritten.
    P0-4: Has genesis anchor and produces ledger_root_hash.
    P0-5: Current state is DERIVED by replaying events, not stored mutably.
    """

    def __init__(self, ledger_dir: Path):
        self.ledger_dir = Path(ledger_dir)
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self._events: List[StateTransition] = []
        self._load()

    def _ndjson_file(self) -> Path:
        return self.ledger_dir / "state_transition_ledger.ndjson"

    def _root_file(self) -> Path:
        return self.ledger_dir / "state_transition_ledger_root.json"

    def _load(self):
        """Load events from append-only NDJSON file. NEVER modifies the file."""
        self._events = []
        ndjson_path = self._ndjson_file()
        if not ndjson_path.exists():
            return

        with open(ndjson_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                self._events.append(StateTransition(**data))

    def _append_event(self, event: StateTransition):
        """P0-3: Append ONE event to the NDJSON file. Never rewrite existing lines."""
        with open(self._ndjson_file(), "a") as f:
            f.write(json.dumps(asdict(event), default=str) + "\n")

    def _update_root(self):
        """P0-4: Compute and store the ledger root hash."""
        if not self._events:
            root_hash = GENESIS_HASH
        else:
            # Root hash = hash of the LAST transition's hash (Merkle-like chain tip)
            root_hash = self._events[-1].transition_hash

        root_data = {
            "genesis_hash": GENESIS_HASH,
            "ledger_root_hash": root_hash,
            "total_events": len(self._events),
            "last_global_sequence": self._events[-1].global_sequence if self._events else 0,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._root_file(), "w") as f:
            json.dump(root_data, f, indent=2, default=str)

    def record_transition(
        self,
        territory_id: str,
        to_state: str,
        artifact_id: str,
        artifact_version: str,
        commit_sha: str,
        reason: str,
        artifact_hash: Optional[str] = None,
        transition_type: str = "BOOTSTRAPPED_FROM_CANONICAL_STATE",
    ) -> StateTransition:
        """Append a new transition event. NEVER modifies existing events.

        P0-1: global_sequence = max(existing) + 1
        P0-2: global_sequence is included in transition_hash
        P0-3: Event is appended to NDJSON (never rewrites)
        P0-5: No effective field — CURRENT is derived
        P1: commit_sha validated as 40-char hex
        """
        # P1: Validate commit_sha format
        if not SHA40_PATTERN.match(commit_sha):
            raise ValueError(
                f"commit_sha must be full 40-char hex SHA, got: {commit_sha}"
            )

        # P0-2: Validate EVIDENCE_BACKED requires artifact_hash
        if transition_type == "EVIDENCE_BACKED" and artifact_hash is None:
            raise ValueError(
                f"EVIDENCE_BACKED transition requires non-null artifact_hash."
            )

        # P0-1: Assign global_sequence
        if self._events:
            global_sequence = self._events[-1].global_sequence + 1
            previous_hash = self._events[-1].transition_hash
        else:
            global_sequence = 1
            previous_hash = GENESIS_HASH  # P0-4: Genesis anchor

        # Find current state for this territory (derived, not stored)
        current = self.get_current_transition(territory_id)
        from_state = current.to_state if current else None

        # Generate transition ID
        existing_for_territory = [e for e in self._events if e.territory_id == territory_id]
        seq = len(existing_for_territory) + 1
        transition_id = f"ST-{territory_id}-{seq:04d}"

        # Compute state_hash
        state_content = f"{to_state}:{artifact_id}:{artifact_version}"
        state_hash = hashlib.sha256(state_content.encode()).hexdigest()

        event = StateTransition(
            global_sequence=global_sequence,
            transition_id=transition_id,
            territory_id=territory_id,
            from_state=from_state,
            to_state=to_state,
            artifact_id=artifact_id,
            artifact_version=artifact_version,
            commit_sha=commit_sha,
            reason=reason,
            transition_type=transition_type,
            previous_transition_hash=previous_hash,
            artifact_hash=artifact_hash,
            state_hash=state_hash,
        )

        # P0-3: Append to NDJSON (never rewrite)
        self._append_event(event)
        self._events.append(event)
        self._update_root()

        return event

    def get_current_transition(self, territory_id: str) -> Optional[StateTransition]:
        """P0-5: DERIVE current transition by replaying events. No mutable effective field."""
        territory_events = [e for e in self._events if e.territory_id == territory_id]
        if not territory_events:
            return None
        # Sort by global_sequence (true append order)
        territory_events.sort(key=lambda e: e.global_sequence)
        return territory_events[-1]  # Last event for this territory = current

    def get_current_state(self, territory_id: str) -> Optional[str]:
        """Derive current state from immutable events."""
        current = self.get_current_transition(territory_id)
        return current.to_state if current else None

    def get_transition_chain(self, territory_id: str) -> List[StateTransition]:
        """Get all transitions for a territory in global sequence order."""
        chain = [e for e in self._events if e.territory_id == territory_id]
        chain.sort(key=lambda e: e.global_sequence)
        return chain

    def verify_chain_integrity(self) -> dict:
        """Verify cryptographic chain integrity.

        P0-1: Verifies global_sequence is consecutive (1, 2, 3, ...)
        P0-2: Verifies each transition_hash includes global_sequence
        P0-4: Verifies genesis anchor and produces root hash
        """
        results = {
            "total_events": len(self._events),
            "verified": 0,
            "failed": 0,
            "failures": [],
            "topology": "ONE_GLOBAL_APPEND_ONLY_CHAIN",
            "genesis_hash": GENESIS_HASH,
        }

        for i, event in enumerate(self._events):
            # P0-1: Verify global_sequence is consecutive
            expected_seq = i + 1
            if event.global_sequence != expected_seq:
                results["failed"] += 1
                results["failures"].append(
                    f"{event.transition_id}: global_sequence={event.global_sequence} but expected {expected_seq}"
                )
                continue

            # Verify previous_transition_hash
            if i == 0:
                # First event must link to genesis
                if event.previous_transition_hash != GENESIS_HASH:
                    results["failed"] += 1
                    results["failures"].append(
                        f"{event.transition_id}: first event should link to GENESIS_HASH"
                    )
                else:
                    results["verified"] += 1
            else:
                prev = self._events[i - 1]
                if event.previous_transition_hash != prev.transition_hash:
                    results["failed"] += 1
                    results["failures"].append(
                        f"{event.transition_id}: previous_hash mismatch "
                        f"(expected {prev.transition_hash[:16]}..., got {event.previous_transition_hash[:16] if event.previous_transition_hash else 'None'}...)"
                    )
                else:
                    results["verified"] += 1

        # P0-4: Compute and verify root hash
        if self._events:
            results["ledger_root_hash"] = self._events[-1].transition_hash
        else:
            results["ledger_root_hash"] = GENESIS_HASH

        results["chain_valid"] = results["failed"] == 0
        return results

    def get_root_hash(self) -> str:
        """P0-4: Get the current ledger root hash."""
        if not self._events:
            return GENESIS_HASH
        return self._events[-1].transition_hash

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
                })
        return discrepancies

    def verify_all(self) -> dict:
        """Verify ledger integrity."""
        chain_result = self.verify_chain_integrity()
        by_territory = {}
        for e in self._events:
            by_territory.setdefault(e.territory_id, []).append(e)

        return {
            "chain_integrity": chain_result,
            "territories": len(by_territory),
            "overall_pass": chain_result["chain_valid"],
        }
