#!/usr/bin/env python3
"""tests/test_triz_data.py — the classical contradiction-matrix layer
(P2, claim c-0071). The vendored data must be the COMPLETE classical
table (40 principles / 39 parameters / 1254 non-empty cells, no
diagonal), the accessor must return known-answer recommendations and
typed refusals, and a missing data file must raise — never degrade
into a fabricated recommendation. Zero LLM, zero network (the data is
committed; the MIT attribution lives in NOTICE.md /
NOTICE-triz-engine)."""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

import pytest  # noqa: E402

from discovery_fabric.engine import triz_principles as tp  # noqa: E402


def test_matrix_record_is_complete():
    d = tp.load_matrix()
    assert len(d["parameters"]) == 39
    assert [p["id"] for p in d["parameters"]] == list(range(1, 40))
    cells = d["matrix"]
    assert len(cells) == 1254, len(cells)
    assert all(all(1 <= x <= 40 for x in v) for v in cells.values())
    assert not any(k.split("_")[0] == k.split("_")[1] for k in cells)


def test_accessor_known_answers():
    # the canonical first cell (weight of moving object vs weight of
    # stationary object): dynamics, anti-weight, pneumatics, composites
    assert tp.matrix_principles(1, 2) == [15, 8, 29, 34]
    # stress-pressure vs loss-of-substance
    assert tp.matrix_principles(11, 23) == [10, 36, 3, 37]


def test_accessor_typed_refusals():
    with pytest.raises(ValueError):
        tp.matrix_principles(1, 40)
    with pytest.raises(ValueError):
        tp.matrix_principles(0, 5)
    # an empty cell (non-diagonal pairs absent from the classical
    # table) returns [] — a gap, never a fabricated recommendation
    assert tp.matrix_principles(1, 1) == []


def test_full_40_principles_present():
    assert len(tp.PRINCIPLES) == 40
    assert sorted(tp.PRINCIPLES) == list(range(1, 41))


def test_missing_data_file_raises_typed():
    # simulate the missing-data case with a moved file
    data = tp._DATA_PATH
    moved = data.with_suffix(".json.moved")
    data.rename(moved)
    try:
        tp._MATRIX_CACHE = None
        with pytest.raises(FileNotFoundError):
            tp.load_matrix()
    finally:
        moved.rename(data)
        tp._MATRIX_CACHE = None
    tp.load_matrix()  # restored


def test_seeding_layer_still_coherent():
    # the 13-entry keyword layer coexists with the matrix layer
    pr, fam = tp.seed_for("pump cavitation erosion on the impeller")
    assert pr and fam
    other = ((pr[0] % 40) + 1,)
    assert tp.distinct_principles([(pr, fam), (other, fam)])
