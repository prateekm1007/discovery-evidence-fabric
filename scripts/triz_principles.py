#!/usr/bin/env python3
"""triz_principles.py — scripts/ shim (F63 remedy R52): the module
lives in discovery_fabric/engine/ now; this shim re-exports it so the
existing script-side importers (r45_machine_v81, r45_round_record,
r45_claims, test_v81_binds, v82 CLIs) keep their import surface
unchanged. The engine module is the single source of truth."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import triz_principles as _engine_mod  # noqa: E402

PRINCIPLES = _engine_mod.PRINCIPLES
CONTRADICTION_MAP = _engine_mod.CONTRADICTION_MAP
DUTY_CYCLE_FAMILY_RX = _engine_mod.DUTY_CYCLE_FAMILY_RX
seed_for = _engine_mod.seed_for
distinct_principles = _engine_mod.distinct_principles

__all__ = ["PRINCIPLES", "CONTRADICTION_MAP", "seed_for",
           "distinct_principles", "DUTY_CYCLE_FAMILY_RX"]
