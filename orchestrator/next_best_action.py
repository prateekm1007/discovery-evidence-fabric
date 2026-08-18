"""
NEXT_BEST_ACTION Central Controller
====================================

Continuously calculates: information_gain × p_decision_change × decision_impact
÷ cost - redundancy_penalty. Executes one action, recalculates.

V4 formula (not V3): adds probability_of_decision_change.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from datetime import datetime, timezone


@dataclass
class Action:
    """A candidate action the orchestrator could execute."""
    action_id: str
    description: str
    evidence_question_id: str  # which question this answers
    provider: str  # which provider to use
    expected_information_gain: float  # 0.0-1.0
    probability_of_decision_change: float  # 0.0-1.0
    decision_impact: float  # 0.0-1.0 (1.0 = terminates territory)
    cost: float  # 1-100
    redundancy_penalty: float = 0.0  # computed from evidence graph

    @property
    def score(self) -> float:
        """V4 formula: info_gain × p_decision_change × decision_impact ÷ cost - redundancy_penalty."""
        if self.cost <= 0:
            return 0.0
        raw = (self.expected_information_gain *
               self.probability_of_decision_change *
               self.decision_impact) / self.cost
        return raw - self.redundancy_penalty

    def to_dict(self) -> Dict:
        return {
            **self.__dict__,
            "score": round(self.score, 4),
        }


class NextBestAction:
    """Central controller that ranks and selects the next best action."""

    def __init__(self, score_threshold: float = 0.01):
        self.score_threshold = score_threshold
        self.action_history: List[Action] = []

    def rank_actions(self, actions: List[Action]) -> List[Action]:
        """Rank actions by score (descending)."""
        return sorted(actions, key=lambda a: a.score, reverse=True)

    def select_best(self, actions: List[Action]) -> Optional[Action]:
        """Select the highest-scoring action above threshold."""
        ranked = self.rank_actions(actions)
        if not ranked or ranked[0].score < self.score_threshold:
            return None
        return ranked[0]

    def execute_and_recalculate(self, actions: List[Action],
                                 execute_fn: Callable[[Action], Dict]) -> Optional[Action]:
        """Execute one action, record result, return next best action.
        The orchestrator should continuously calculate, execute one action,
        and recalculate.
        """
        best = self.select_best(actions)
        if best is None:
            return None

        # Execute the action
        result = execute_fn(best)
        self.action_history.append(best)

        # Remove executed action from list
        remaining = [a for a in actions if a.action_id != best.action_id]

        # Recalculate redundancy penalties based on new evidence
        # (In full implementation, this would query the evidence graph)
        for action in remaining:
            # Actions that would produce redundant evidence get higher penalty
            if action.provider == best.provider:
                action.redundancy_penalty += 0.1

        return best

    def get_history(self) -> List[Dict]:
        return [a.to_dict() for a in self.action_history]
