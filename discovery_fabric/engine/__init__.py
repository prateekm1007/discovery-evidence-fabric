"""discovery_fabric.engine — integrated discovery engine (D4-D10).

One governed loop over canonical adapters. See RUNTIME_CAPABILITY_REGISTRY.json
for the promotion ledger and discovery_fabric/engine/run.py for the conductor.
"""
from .candidate import Candidate, StageFailure
from .run import EngineRun

__all__ = ["Candidate", "StageFailure", "EngineRun"]
