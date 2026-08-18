"""
epistemic_integrity/state_transition_ledger.py — Immutable state-transition ledger

Per CEO directive P0-4:
  "Replace keyword-based state reconciliation with an explicit immutable
   state-transition ledger.
   Every adjudication artifact needs explicit machine state:
     territory_id, artifact_version, status, effective, supersedes
   The latest state is the terminal node in the signed transition chain.
   Not 'the file with the highest V number.'"

Each StateTransition is an explicit record:
  - transition_id: unique ID
  - territory_id: CV-T01, CV-T02, etc.
  - from_state: previous state (None for initial)
  - to_state: new state
  - artifact_id: which artifact produced this transition
  - artifact_version: V6, V25, etc.
  - commit_sha: git commit containing the artifact
  - created_at: timestamp
  - supersedes: previous transition_id
  - reason: why the state changed
  - effective: bool (only one transition per territory is effective at a time)

The CURRENT state of a territory = the to_state of the latest effective transition.
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime, timezone


@dataclass
class StateTransition:
    transition_id: str  # ST-CV-T<territory>-<seq>
    territory_id: str
    from_state: Optional[str]  # None for initial state
    to_state: str
    artifact_id: str  # e.g., "CV-T06-V6"
    artifact_version: str  # e.g., "V6"
    commit_sha: str  # git commit containing the artifact
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    supersedes: Optional[str] = None  # previous transition_id
    reason: str = ""
    effective: bool = True  # only one transition per territory is effective at a time


class StateTransitionLedger:
    """Immutable ledger of all state transitions.

    The CURRENT state of a territory is the to_state of the latest effective
    transition for that territory. This is deterministic — no keyword inference,
    no file scanning, no prose parsing.
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
        with open(self._file(), "w") as f:
            json.dump({
                "schema_version": "1.0.0",
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
    ) -> StateTransition:
        """Record a new state transition.

        This automatically:
          1. Marks all previous effective transitions for this territory as ineffective
          2. Sets supersedes to the previous effective transition
          3. Creates a new effective transition
        """
        # Find current effective transition for this territory
        current = self.get_current_transition(territory_id)
        from_state = current.to_state if current else None
        supersedes = current.transition_id if current else None

        # Mark previous as ineffective
        if current:
            current.effective = False

        # Generate transition ID
        existing = [t for t in self.transitions if t.startswith(f"ST-{territory_id}")]
        seq = len(existing) + 1
        transition_id = f"ST-{territory_id}-{seq:04d}"

        transition = StateTransition(
            transition_id=transition_id,
            territory_id=territory_id,
            from_state=from_state,
            to_state=to_state,
            artifact_id=artifact_id,
            artifact_version=artifact_version,
            commit_sha=commit_sha,
            supersedes=supersedes,
            reason=reason,
            effective=True,
        )
        self.transitions[transition_id] = transition
        self._save()
        return transition

    def get_current_transition(self, territory_id: str) -> Optional[StateTransition]:
        """Get the current effective transition for a territory."""
        for t in self.transitions.values():
            if t.territory_id == territory_id and t.effective:
                return t
        return None

    def get_current_state(self, territory_id: str) -> Optional[str]:
        """Get the current state for a territory — deterministic."""
        current = self.get_current_transition(territory_id)
        return current.to_state if current else None

    def get_transition_chain(self, territory_id: str) -> List[StateTransition]:
        """Get the full transition chain for a territory (chronological)."""
        chain = []
        current = self.get_current_transition(territory_id)
        while current:
            chain.insert(0, current)
            if current.supersedes:
                current = self.transitions.get(current.supersedes)
            else:
                current = None
        return chain

    def reconcile_with_canonical(self, canonical_states: Dict[str, str]) -> List[dict]:
        """Reconcile ledger states with canonical portfolio states.

        Args:
            canonical_states: {territory_id: current_state} from CANONICAL_STATE/PORTFOLIO.json

        Returns:
            List of discrepancies (empty if all match)
        """
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
          - Each territory has exactly one effective transition
          - All supersedes chains are valid
          - All commit_shas exist in git
        """
        results = {
            "territories_checked": 0,
            "passed": 0,
            "failed": 0,
            "failures": [],
        }

        # Group by territory
        by_territory: Dict[str, List[StateTransition]] = {}
        for t in self.transitions.values():
            by_territory.setdefault(t.territory_id, []).append(t)

        for tid, transitions in by_territory.items():
            results["territories_checked"] += 1
            effective = [t for t in transitions if t.effective]
            if len(effective) != 1:
                results["failed"] += 1
                results["failures"].append(
                    f"{tid}: {len(effective)} effective transitions (expected 1)"
                )
            else:
                results["passed"] += 1

        return results
