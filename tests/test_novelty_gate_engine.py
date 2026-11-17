#!/usr/bin/env python3
"""tests/test_novelty_gate_engine.py — the engine novelty gate (the
former scripts/v82_novelty_gate.py __main__ self-test, now a CI-wired
test). The pre-registered bands: duplicate composite >= 0.85 rejected,
distinct composite < 0.70 novel, borderline band routes to judge.
Zero LLM, zero network."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import novelty_gate as ng  # noqa: E402

NEAR = ("seeds scale nucleation sites so calcium carbonate grows "
        "on the sacrificial porous coating not the tube wall")
DUP = ("seeds scale nucleation sites so calcium carbonate grows "
       "on the sacrificial porous coating not the tube surface")
OTHER = ("periodic reversal of the cooling water flow direction "
         "shears the developing boundary layer off the tube wall")


def test_pre_registered_bands_hold():
    s_dup = ng.duplicate_score(NEAR, DUP, [NEAR, DUP, OTHER])
    s_other = ng.duplicate_score(NEAR, OTHER, [NEAR, DUP, OTHER])
    assert s_dup >= ng.NOVELTY_REJECT, "duplicate not caught"
    assert s_other < ng.NOVELTY_JUDGE_LO, "distinct flagged as duplicate"


def test_row_verdicts():
    g = ng.gate_row([{"candidate_id": "c1", "text": NEAR},
                     {"candidate_id": "c2", "text": DUP},
                     {"candidate_id": "c3", "text": OTHER}])
    assert g["verdicts"]["c2"] == "reject-duplicate"
    assert g["verdicts"]["c3"] == "novel"
    assert g["rejected"] == 1 and g["kept"] == ["c1", "c3"]
