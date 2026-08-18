"""Provider adapters — pluggable, independent of reasoning engine."""
from .base import BaseProvider, ProviderResult
from .lens import LensProvider
from .scopus import ScopusProvider
from .patentbear import PatentBearProvider
from .google_patents import GooglePatentsProvider
from .patsnap import PatSnapProvider
from .simulation import SimulationProvider

__all__ = [
    "BaseProvider", "ProviderResult",
    "LensProvider", "ScopusProvider", "PatentBearProvider",
    "GooglePatentsProvider", "PatSnapProvider", "SimulationProvider",
]
