"""
epistemic_integrity/append_only_binding_registry.py — Immutable binding history

Per CEO v6 P0-6:
  "Bindings themselves need immutable records: ADD/REVOKE events.
   Never overwrite binding history."

Each binding operation is an immutable event:
  BIND-0001: ADD claim CLM-X to evidence EXP-Y
  BIND-0002: ADD claim CLM-X to source SRC-Z
  BIND-0003: REVOKE claim CLM-X from evidence EXP-Y

The current binding state is derived by replaying the event log.
Events are never modified or deleted.
"""

import json
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime, timezone
from enum import Enum


class BindingOperation(str, Enum):
    ADD = "ADD"
    REVOKE = "REVOKE"


@dataclass
class BindingEvent:
    """An immutable binding operation. Once written, NEVER modified."""
    event_id: str                            # BIND-<seq>
    operation: str                           # ADD / REVOKE
    claim_id: str
    target_type: str                         # EVIDENCE / SOURCE
    target_id: str                           # evidence_id or source_id
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    commit_sha: Optional[str] = None
    reason: str = ""
    previous_event_hash: Optional[str] = None  # cryptographic chain

    @property
    def event_hash(self) -> str:
        """SHA256 of this event for chaining."""
        content = json.dumps({
            "event_id": self.event_id,
            "operation": self.operation,
            "claim_id": self.claim_id,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "timestamp": self.timestamp,
            "commit_sha": self.commit_sha,
            "reason": self.reason,
            "previous_event_hash": self.previous_event_hash,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()


class AppendOnlyBindingRegistry:
    """Immutable binding event log.

    Per CEO P0-6: bindings are ADD/REVOKE events, never overwritten.
    Current state is derived by replaying the event log.
    """

    def __init__(self, registry_dir: Path):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.events: Dict[str, BindingEvent] = {}
        self._load()

    def _file(self) -> Path:
        return self.registry_dir / "binding_events.json"

    def _load(self):
        path = self._file()
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for item in data.get("events", []):
                self.events[item["event_id"]] = BindingEvent(**item)

    def _save(self):
        with open(self._file(), "w") as f:
            json.dump({
                "schema_version": "1.0.0",
                "registry_type": "APPEND_ONLY_BINDING_EVENTS",
                "events": [asdict(e) for e in self.events.values()],
            }, f, indent=2, default=str)

    def add_binding(
        self,
        claim_id: str,
        target_type: str,  # EVIDENCE / SOURCE
        target_id: str,
        commit_sha: str = None,
        reason: str = "",
    ) -> BindingEvent:
        """Append an ADD binding event. Never modifies existing events."""
        # Find previous event hash for chaining
        all_events = sorted(self.events.values(), key=lambda e: e.event_id)
        prev_hash = all_events[-1].event_hash if all_events else None

        seq = len(self.events) + 1
        event_id = f"BIND-{seq:05d}"

        event = BindingEvent(
            event_id=event_id,
            operation=BindingOperation.ADD.value,
            claim_id=claim_id,
            target_type=target_type,
            target_id=target_id,
            commit_sha=commit_sha,
            reason=reason,
            previous_event_hash=prev_hash,
        )
        self.events[event_id] = event
        self._save()
        return event

    def revoke_binding(
        self,
        claim_id: str,
        target_type: str,
        target_id: str,
        commit_sha: str = None,
        reason: str = "",
    ) -> BindingEvent:
        """Append a REVOKE binding event. Never modifies existing events."""
        all_events = sorted(self.events.values(), key=lambda e: e.event_id)
        prev_hash = all_events[-1].event_hash if all_events else None

        seq = len(self.events) + 1
        event_id = f"BIND-{seq:05d}"

        event = BindingEvent(
            event_id=event_id,
            operation=BindingOperation.REVOKE.value,
            claim_id=claim_id,
            target_type=target_type,
            target_id=target_id,
            commit_sha=commit_sha,
            reason=reason,
            previous_event_hash=prev_hash,
        )
        self.events[event_id] = event
        self._save()
        return event

    def get_current_bindings(self, claim_id: str) -> dict:
        """Derive current binding state by replaying the event log.

        Returns:
          {"evidence_ids": [...], "source_ids": [...]}
        """
        evidence_ids: Set[str] = set()
        source_ids: Set[str] = set()

        # Replay events in order
        sorted_events = sorted(self.events.values(), key=lambda e: e.event_id)
        for event in sorted_events:
            if event.claim_id != claim_id:
                continue

            if event.target_type == "EVIDENCE":
                if event.operation == BindingOperation.ADD.value:
                    evidence_ids.add(event.target_id)
                elif event.operation == BindingOperation.REVOKE.value:
                    evidence_ids.discard(event.target_id)
            elif event.target_type == "SOURCE":
                if event.operation == BindingOperation.ADD.value:
                    source_ids.add(event.target_id)
                elif event.operation == BindingOperation.REVOKE.value:
                    source_ids.discard(event.target_id)

        return {
            "evidence_ids": sorted(evidence_ids),
            "source_ids": sorted(source_ids),
        }

    def get_binding_history(self, claim_id: str) -> List[BindingEvent]:
        """Get full binding history for a claim (all ADD/REVOKE events)."""
        return sorted(
            [e for e in self.events.values() if e.claim_id == claim_id],
            key=lambda e: e.event_id
        )

    def verify_chain_integrity(self) -> dict:
        """Verify the cryptographic chain of binding events."""
        results = {"total_events": len(self.events), "verified": 0, "failed": 0, "failures": []}
        sorted_events = sorted(self.events.values(), key=lambda e: e.event_id)

        for i, event in enumerate(sorted_events):
            if i == 0:
                if event.previous_event_hash is not None:
                    results["failed"] += 1
                    results["failures"].append(f"{event.event_id}: first event should have null previous_hash")
                else:
                    results["verified"] += 1
            else:
                prev = sorted_events[i - 1]
                if event.previous_event_hash != prev.event_hash:
                    results["failed"] += 1
                    results["failures"].append(f"{event.event_id}: previous_hash mismatch")
                else:
                    results["verified"] += 1

        results["chain_valid"] = results["failed"] == 0
        return results
