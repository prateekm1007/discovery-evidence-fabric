"""tests/test_triz_matrix_wiring.py — D1 (auditor direction 1, claim
c-0128): the classical TRIZ matrix (1,254 cells) is the principle
SOURCE on the generation seeding path, not a shipped-but-unwired
table. The >=80% matrix-sourced bind is MEASURED here on the
population_search plan tags across every CONTRADICTION_MAP family
(and a mixed problem battery), plus the ablation guard: the
matrix-sourced pool never DROPS the family's own seed principles
(the keyword layer stays the identifier) and never falls below the
keyword-only pool's distinct-principle count."""
from __future__ import annotations

import json

from discovery_fabric.engine import population_search as ps
from discovery_fabric.engine import triz_principles as tp

PROBLEMS = [
    {"device": "shell-and-tube heat exchanger", "failure": "fouling deposit on tube surfaces reduces heat transfer", "constraint": "no chemical cleaning", "failure_mode": "progressive U-value degradation"},
    {"device": "centrifugal pump", "failure": "cavitation at the suction side at high flow", "constraint": "fixed installation height", "failure_mode": "impeller erosion"},
    {"device": "compressed-air receiver", "failure": "moisture condensation causes corrosion downstream", "constraint": "no external power", "failure_mode": "rust carryover"},
    {"device": "conveyor bearing", "failure": "wear from abrasive particle ingress", "constraint": "sealed unit required", "failure_mode": "premature seizure"},
    {"device": "district heating pipe", "failure": "waterhammer transients crack fittings", "constraint": "retrofit only", "failure_mode": "joint leaks"},
    {"device": "sterile filling line", "failure": "contamination breaches at transfer points", "constraint": "no added cycle time", "failure_mode": "batch rejects"},
    {"device": "gas turbine combustor", "failure": "thermal load overheats liner walls", "constraint": "same fuel", "failure_mode": "liner scorching"},
    {"device": "reverse-osmosis train", "failure": "scaling raises energy consumption", "constraint": "no antiscalant change", "failure_mode": "permeate decline"},
]


def test_matrix_seeded_pool_covers_all_families():
    """Every CONTRADICTION_MAP family resolves to a matrix cell —
    the keyword tuples were chosen from the classical literature, so
    a no-cell family would mean the bridge (or the matrix data) is
    broken."""
    for rx, principles, cls in tp.CONTRADICTION_MAP:
        res = tp.matrix_seeded_pool(principles)
        assert res["source"] == "triz_matrix_cell", \
            f"{cls}: no matrix cell contains {principles}"
        assert res["principles"], f"{cls}: empty pool"
        # the family's own seeds survive (no identifier loss)
        for p in principles:
            assert p in res["principles"], \
                f"{cls}: seed principle {p} dropped from the pool"
        assert res["cell"]["improving"] in range(1, 40)
        assert res["cell"]["worsening"] in range(1, 40)


def test_seeding_path_matrix_sourced_share():
    """The auditor's >=80% bind, MEASURED: across the problem battery,
    plans tagged triz_matrix_cell >= 80% of plans that carry a
    principle_source tag."""
    total = tagged = matrix_sourced = 0
    for prob in PROBLEMS:
        for plan in ps.enumerate_plans(prob):
            total += 1
            tag = plan.get("principle_source")
            if tag:
                tagged += 1
                matrix_sourced += int(tag == "triz_matrix_cell")
    assert total > 0, "no plans enumerated (fixture regression)"
    assert tagged >= total * 0.8, \
        f"only {tagged}/{total} plans carry a principle_source tag"
    share = matrix_sourced / max(tagged, 1)
    assert share >= 0.80, \
        f"matrix-sourced share {share:.3f} < 0.80 (D1 bind)"


def test_ablation_no_mean_drop():
    """The ablation guard: matrix-sourced pools never reduce the
    distinct-principle count vs the keyword-only pool (per family),
    and enumerate_plans under matrix seeding keeps the
    distinct-principles bind (no two plans on one principle) at
    least as well as the keyword layer."""
    for rx, principles, cls in tp.CONTRADICTION_MAP:
        m = tp.matrix_seeded_pool(principles)["principles"]
        kw = list(principles)
        assert len(set(m)) == len(m), f"{cls}: pool has duplicates"
        assert len(m) >= len(kw), \
            f"{cls}: matrix pool {len(m)} < keyword pool {len(kw)}"
    for prob in PROBLEMS:
        plans = ps.enumerate_plans(prob)
        pids = [p["principle_id"] for p in plans if
                p.get("principle_id") is not None]
        assert len(pids) == len(set(pids)), \
            f"distinct-principles bind broken: {pids}"


def test_matrix_principles_determinism_and_bounds():
    """The cell reader stays deterministic and typed."""
    assert tp.matrix_principles(13, 32) == tp.matrix_principles(13, 32)
    assert isinstance(tp.matrix_principles(9, 37), list)
    for bad in [(0, 5), (40, 5), (5, 0), (5, 40)]:
        try:
            tp.matrix_principles(*bad)
            raise AssertionError(f"no typed error for {bad}")
        except ValueError:
            pass
