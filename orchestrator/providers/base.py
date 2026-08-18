"""Base provider interface — pluggable adapters."""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class ProviderResult:
    """Result from a provider query."""
    provider: str
    query: str
    total_hits: int = 0
    results: List[Dict[str, Any]] = field(default_factory=list)
    error: str = ""
    cost_incurred: float = 0.0
    timestamp: str = ""

    @property
    def success(self) -> bool:
        return not self.error


class BaseProvider(ABC):
    """Abstract provider interface. Provider-specific reasoning must NOT
    live inside the state machine — keep one canonical orchestrator with
    pluggable providers."""

    name: str = "base"
    cost_per_call: float = 1.0
    evidence_class: str = ""  # discovery/mechanism/etc.

    @abstractmethod
    def search(self, query: str, **kwargs) -> ProviderResult:
        """Execute a search query. Returns ProviderResult."""
        pass

    @abstractmethod
    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        """Retrieve claims for a patent (if applicable)."""
        pass

    def get_cost_estimate(self, query_type: str = "search") -> float:
        """Estimate cost before executing."""
        return self.cost_per_call
