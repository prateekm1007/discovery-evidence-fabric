"""
CereVasc Automated Research Orchestrator
=========================================

V4 specification implementation. One canonical orchestrator with:
  - Territory-discovery layer (CereVasc platform → gap → territory → candidate)
  - NEXT_BEST_ACTION central controller
  - Pluggable provider adapters
  - Unified evidence graph/ledger
  - Coverage/materiality engine
  - Contradiction queue
  - Alternative-defeated ledger
  - REPLACEMENT_CANDIDATE logic

Package structure:
  orchestrator/
    __init__.py
    territory_discovery.py    # CereVasc platform → gap → territory ranking
    next_best_action.py       # Central controller (info×p_decision×impact÷cost-redundancy)
    evidence_graph.py         # Question → query → provider → result → evidence → contradiction
    coverage_engine.py        # 7-dimension adaptive coverage + PatSnap materiality
    contradiction_queue.py    # 6-field prioritized contradiction queue
    alternative_ledger.py     # Alternative-defeated ledger with 6-axis equivalence
    portfolio.py              # 10-invention portfolio with REPLACEMENT_CANDIDATE
    providers/
      __init__.py
      base.py                 # Abstract provider interface
      lens.py                 # Lens scholarly adapter
      scopus.py               # Elsevier Scopus adapter
      patentbear.py           # PatentBear free web search adapter
      google_patents.py       # Google Patents adapter
      patsnap.py              # PatSnap adapter (HIGH cost, materiality-gated)
      simulation.py           # Local simulation provider
    test/
      hostile_synthetic.py    # Deliberately hostile synthetic test case
"""
from .territory_discovery import TerritoryDiscovery
from .next_best_action import NextBestAction, Action
from .evidence_graph import EvidenceGraph, EvidenceItem
from .coverage_engine import CoverageEngine, CoverageContract
from .contradiction_queue import ContradictionQueue, Contradiction
from .alternative_ledger import AlternativeLedger, Alternative
from .portfolio import Portfolio, TerritoryState

__version__ = "0.1.0"
__spec_version__ = "V4_FINAL"

__all__ = [
    "TerritoryDiscovery",
    "NextBestAction",
    "Action",
    "EvidenceGraph",
    "EvidenceItem",
    "CoverageEngine",
    "CoverageContract",
    "ContradictionQueue",
    "Contradiction",
    "AlternativeLedger",
    "Alternative",
    "Portfolio",
    "TerritoryState",
]
