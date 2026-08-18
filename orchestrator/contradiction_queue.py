"""
Contradiction Queue
====================

6-field prioritized contradiction queue.
Goal: resolve contradictions that could actually KILL the invention
(not eliminate all contradictions).
"""
from __future__ import annotations
from typing import List, Dict, Optional
from .evidence_graph import Contradiction


class ContradictionQueue:
    """Prioritized queue of materially falsifying results."""

    def __init__(self):
        self.contradictions: List[Contradiction] = []

    def add(self, contradiction: Contradiction):
        self.contradictions.append(contradiction)

    def get_blocking(self) -> List[Contradiction]:
        """Only HIGH severity + probability > 0.5 + STRONG/MODERATE evidence blocks survivor."""
        return [c for c in self.contradictions if c.is_blocking]

    def get_unresolved_sorted(self) -> List[Contradiction]:
        """Get unresolved contradictions sorted by priority (highest first)."""
        unresolved = [c for c in self.contradictions if c.currently_unresolved]
        return sorted(unresolved, key=lambda c: c.priority_score, reverse=True)

    def get_next_to_attack(self) -> Optional[Contradiction]:
        """Attack the highest-value unresolved contradiction first."""
        unresolved = self.get_unresolved_sorted()
        return unresolved[0] if unresolved else None

    def resolve(self, contradiction_id: str, resolution_action: str,
                resolution_result: str):
        """Mark a contradiction as resolved."""
        for c in self.contradictions:
            if c.contradiction_id == contradiction_id:
                c.resolution_action = resolution_action
                c.resolution_result = resolution_result
                c.currently_unresolved = False
                return
        raise ValueError(f"Contradiction {contradiction_id} not found")

    def all_blocking_resolved(self) -> bool:
        """Check if all blocking contradictions are resolved."""
        return len(self.get_blocking()) == 0

    def to_dict(self) -> Dict:
        return {
            "contradictions": [c.__dict__ for c in self.contradictions],
            "blocking_count": len(self.get_blocking()),
            "unresolved_count": len(self.get_unresolved_sorted()),
            "all_blocking_resolved": self.all_blocking_resolved(),
        }
