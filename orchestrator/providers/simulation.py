"""Local simulation provider — for engineering/comparator tests."""
from __future__ import annotations
from typing import Dict, Any
from .base import BaseProvider, ProviderResult


class SimulationProvider(BaseProvider):
    name = "Simulation"
    cost_per_call = 5.0  # local compute
    evidence_class = "engineering"

    def search(self, query: str, **kwargs) -> ProviderResult:
        """Simulation doesn't 'search' — it runs experiments.
        Use run_simulation() instead.
        """
        return ProviderResult(provider=self.name, query=query,
                              error="Use run_simulation() for engineering tests")

    def retrieve_claims(self, patent_number: str) -> ProviderResult:
        return ProviderResult(provider=self.name, query=patent_number,
                              error="Simulation does not retrieve claims")

    def run_simulation(self, config: Dict[str, Any]) -> ProviderResult:
        """Run a simulation with given configuration.
        config should include: controllers, disturbances, metrics, threshold.
        """
        # Placeholder — actual simulation would import from scripts/
        return ProviderResult(provider=self.name, query=str(config),
                              total_hits=1,
                              results=[{"status": "placeholder",
                                        "config": config}],
                              cost_incurred=self.cost_per_call)
