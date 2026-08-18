"""
Portfolio Manager
=================

Manages the 10-invention portfolio. The machine ultimately exists to reach
10 functional, buyer-grade CereVasc inventions.

Territory states: NOT_STARTED, ACTIVE, SURVIVOR, CEILING, EXHAUSTED,
REPLACEMENT_CANDIDATE.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timezone
from .territory_discovery import Territory, TerritoryDiscovery, CereVascGap


@dataclass
class TerritoryState:
    """Full state of a territory — engineering and patent kept SEPARATE."""
    territory_id: str
    name: str
    # Engineering and patent are ALWAYS separate dimensions
    engineering_status: str = "NOT_STARTED"  # NOT_STARTED/PARTIAL/PASS/CEILING/FAIL
    patent_status: str = "NOT_STARTED"  # NOT_STARTED/SEARCH_INCOMPLETE/FOUND/NOT_FOUND_AFTER_COMPLETE_SEARCH
    buyer_readiness: str = "NOT_READY"  # NOT_READY/WOULD_CONSIDER_WITH_MILESTONES/BUYER_READY
    selection_rationale: str = ""
    frozen: bool = False
    freeze_reason: str = ""
    reopen_triggers: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return self.__dict__


class Portfolio:
    """Manages 10 functional, buyer-grade CereVasc inventions."""

    TARGET_INVENTION_COUNT = 10

    def __init__(self):
        self.discovery = TerritoryDiscovery()
        self.territory_states: Dict[str, TerritoryState] = {}
        self._init_territory_states()

    def _init_territory_states(self):
        for t in self.discovery.territories:
            self.territory_states[t.territory_id] = TerritoryState(
                territory_id=t.territory_id,
                name=t.name,
                selection_rationale=t.selection_rationale
            )

    def get_state(self, territory_id: str) -> TerritoryState:
        return self.territory_states[territory_id]

    def update_engineering(self, territory_id: str, status: str):
        """Update engineering status ONLY (does not affect patent status)."""
        self.territory_states[territory_id].engineering_status = status

    def update_patent(self, territory_id: str, status: str):
        """Update patent status ONLY (does not affect engineering status)."""
        self.territory_states[territory_id].patent_status = status

    def freeze(self, territory_id: str, reason: str):
        """Freeze a territory (SURVIVOR/CEILING/EXHAUSTED)."""
        state = self.territory_states[territory_id]
        state.frozen = True
        state.freeze_reason = reason

    def reopen(self, territory_id: str, trigger: str):
        """Reopen a frozen territory — ONLY when new evidence changes the
        reachable hypothesis space, not merely the confidence estimate.
        """
        state = self.territory_states[territory_id]
        if not state.frozen:
            raise ValueError(f"Territory {territory_id} is not frozen")
        state.frozen = False
        state.freeze_reason = ""
        state.reopen_triggers.append(trigger)

    def mark_replacement_candidate(self, dead_territory_id: str,
                                    new_gap: CereVascGap) -> Territory:
        """When a territory dies, generate a replacement candidate.
        The system must be equally willing to kill and replace rather than
        spend months rescuing a bad one.
        """
        dead = next(t for t in self.discovery.territories
                    if t.territory_id == dead_territory_id)
        dead.state = self.territory_states[dead_territory_id].engineering_status
        replacement = self.discovery.generate_replacement_candidate(dead, new_gap)
        self.territory_states[replacement.territory_id] = TerritoryState(
            territory_id=replacement.territory_id,
            name=replacement.name,
            selection_rationale=replacement.selection_rationale
        )
        return replacement

    def get_portfolio_scoreboard(self) -> Dict:
        """Scoreboard with engineering and patent SEPARATE (per CEO directive)."""
        return {
            "target_invention_count": self.TARGET_INVENTION_COUNT,
            "territories": [s.to_dict() for s in self.territory_states.values()],
            "survivors": sum(1 for s in self.territory_states.values()
                             if s.engineering_status == "PASS" and
                             s.patent_status == "NOT_FOUND_AFTER_COMPLETE_SEARCH"),
            "ceilings": sum(1 for s in self.territory_states.values()
                           if s.engineering_status == "CEILING"),
            "frozen": sum(1 for s in self.territory_states.values() if s.frozen),
            "active": sum(1 for s in self.territory_states.values()
                         if s.engineering_status == "ACTIVE" and not s.frozen),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def select_next_territory(self) -> Territory:
        """Select the highest-priority available (not frozen, not started) territory."""
        portfolio_state = {
            tid: s.engineering_status for tid, s in self.territory_states.items()
        }
        return self.discovery.select_next_territory(portfolio_state)
