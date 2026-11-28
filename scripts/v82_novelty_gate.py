#!/usr/bin/env python3
"""v82_novelty_gate.py — scripts/ shim (F63 remedy R52): the module
lives in discovery_fabric/engine/novelty_gate.py now; this shim
re-exports it. Run the self-test via the engine module's tests
(tests/test_novelty_gate_engine.py) — the pre-registered bands live
there."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.engine import novelty_gate as _engine_mod  # noqa: E402

NOVELTY_REJECT = _engine_mod.NOVELTY_REJECT
NOVELTY_JUDGE_LO = _engine_mod.NOVELTY_JUDGE_LO
tfidf_cosine = _engine_mod.tfidf_cosine
jaccard = _engine_mod.jaccard
duplicate_score = _engine_mod.duplicate_score
gate_row = _engine_mod.gate_row

__all__ = ["NOVELTY_REJECT", "NOVELTY_JUDGE_LO", "tfidf_cosine",
           "jaccard", "duplicate_score", "gate_row"]
