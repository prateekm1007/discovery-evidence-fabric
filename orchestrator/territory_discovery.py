"""
Territory Discovery Layer
=========================

Implements: CereVasc / eShunt platform → technology-gap map → high-value
territory ranking → territory selection → candidate mechanism.

Preserves WHY a territory was selected (required by V4 reconstruction contract).

All territories are CereVasc/eShunt-derived — NOT generic medical-device ideas.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime, timezone


@dataclass
class CereVascGap:
    """A technology gap in the CereVasc/eShunt platform."""
    gap_id: str
    description: str
    platform_component: str  # e.g., "shunt lumen", "venous boundary", "valve"
    clinical_problem: str
    buyer_value_estimate: float  # 0.0-1.0
    evidence_support: str = ""  # why we believe this gap exists


@dataclass
class Territory:
    """A CereVasc-derived research territory."""
    territory_id: str
    name: str
    cerevasc_gap: CereVascGap
    selection_rationale: str  # WHY this territory was selected (preserved for reconstruction)
    candidate_mechanism: str = ""
    frozen_limitations: Dict[str, str] = field(default_factory=dict)
    priority: float = 0.0  # ranking score
    state: str = "NOT_STARTED"  # NOT_STARTED, ACTIVE, SURVIVOR, CEILING, EXHAUSTED, REPLACEMENT_CANDIDATE


class TerritoryDiscovery:
    """CereVasc platform → gap map → territory ranking → selection."""

    # The 10 CereVasc/eShunt-derived territories (starting taxonomy, not commandment)
    DEFAULT_TERRITORIES = [
        {"id": "T1", "name": "Hydraulic state estimation / active interrogation",
         "gap": "eShunt needs failure detection without imaging",
         "component": "shunt system", "buyer_value": 0.8},
        {"id": "T2", "name": "Selective retention + preserved drainage",
         "gap": "eShunt could deliver therapeutics while draining",
         "component": "shunt lumen", "buyer_value": 0.75},
        {"id": "T3", "name": "Controlled therapeutic retention / CNS delivery",
         "gap": "eShunt as drug delivery platform",
         "component": "shunt lumen + therapy", "buyer_value": 0.9},
        {"id": "T4", "name": "Venous-aware closed-loop flow regulation",
         "gap": "eShunt drains to venous system — pressure regulation",
         "component": "valve + venous boundary", "buyer_value": 0.7},
        {"id": "T5", "name": "Fouling / obstruction prevention",
         "gap": "eShunt lumen can obstruct from biological fouling",
         "component": "shunt lumen", "buyer_value": 0.65},
        {"id": "T6", "name": "Retrieval / rescue",
         "gap": "eShunt may need removal or rescue if failed",
         "component": "shunt body", "buyer_value": 0.6},
        {"id": "T7", "name": "Venous-interface protection",
         "gap": "eShunt contacts venous endothelium — needs protection",
         "component": "venous boundary", "buyer_value": 0.6},
        {"id": "T8", "name": "Patient-specific adaptive eShunt",
         "gap": "eShunt parameters vary by patient physiology",
         "component": "valve + control", "buyer_value": 0.55},
        {"id": "T9", "name": "CNS therapy platform",
         "gap": "eShunt as platform for multiple CNS therapies",
         "component": "platform", "buyer_value": 0.7},
        {"id": "T10", "name": "Lifecycle / platform intelligence",
         "gap": "eShunt long-term monitoring and predictive maintenance",
         "component": "sensors + analytics", "buyer_value": 0.6},
    ]

    def __init__(self):
        self.gaps: List[CereVascGap] = []
        self.territories: List[Territory] = []
        self._load_default_territories()

    def _load_default_territories(self):
        """Load the 10 CereVasc-derived starting territories."""
        for t in self.DEFAULT_TERRITORIES:
            gap = CereVascGap(
                gap_id=f"GAP_{t['id']}",
                description=t["gap"],
                platform_component=t["component"],
                clinical_problem=t["gap"],
                buyer_value_estimate=t["buyer_value"],
                evidence_support="CereVasc eShunt platform gap analysis"
            )
            territory = Territory(
                territory_id=t["id"],
                name=t["name"],
                cerevasc_gap=gap,
                selection_rationale=f"CereVasc eShunt gap: {t['gap']} (component: {t['component']})",
                priority=t["buyer_value"]
            )
            self.gaps.append(gap)
            self.territories.append(territory)

    def rank_territories(self, portfolio_state: Optional[Dict[str, str]] = None) -> List[Territory]:
        """Rank territories by buyer value, excluding exhausted/frozen ones.
        The first automated run must prove the system can discover whether #5
        is actually the best current CereVasc territory (taxonomy is starting point, not commandment).
        """
        portfolio_state = portfolio_state or {}
        # Exclude territories that are already SURVIVOR, CEILING, or EXHAUSTED
        available = [t for t in self.territories
                     if portfolio_state.get(t.territory_id, "NOT_STARTED") == "NOT_STARTED"]
        # Sort by priority descending
        available.sort(key=lambda t: t.priority, reverse=True)
        return available

    def select_next_territory(self, portfolio_state: Optional[Dict[str, str]] = None) -> Territory:
        """Select the highest-priority available territory."""
        ranked = self.rank_territories(portfolio_state)
        if not ranked:
            raise RuntimeError("No available territories — portfolio complete or exhausted")
        return ranked[0]

    def generate_replacement_candidate(self, dead_territory: Territory,
                                       new_gap: CereVascGap) -> Territory:
        """When a territory dies (CEILING/EXHAUSTED), generate a replacement candidate.
        The system must be equally willing to kill a territory and replace it.
        """
        new_id = f"T{len(self.territories) + 1}"
        replacement = Territory(
            territory_id=new_id,
            name=f"Replacement for {dead_territory.territory_id}: {new_gap.description}",
            cerevasc_gap=new_gap,
            selection_rationale=(
                f"REPLACEMENT_CANDIDATE for {dead_territory.territory_id} ({dead_territory.name}) "
                f"which reached {dead_territory.state}. New gap: {new_gap.description}"
            ),
            priority=new_gap.buyer_value_estimate
        )
        self.territories.append(replacement)
        return replacement

    def to_dict(self) -> Dict:
        return {
            "gaps": [g.__dict__ for g in self.gaps],
            "territories": [
                {**t.__dict__, "cerevasc_gap": t.cerevasc_gap.__dict__}
                for t in self.territories
            ],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
