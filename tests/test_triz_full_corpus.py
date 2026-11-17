#!/usr/bin/env python3
"""tests/test_triz_full_corpus.py — R53 (claim c-0073, ROADMAP P2.1):
the TRIZ full-corpus acceptance suite. The corpus is OUR OWN JSON
(discovery_fabric/engine/triz_matrix.json): 40 principles with
self-authored descriptions/examples, the classical 39 engineering
parameters, and the classical 39x39 Altshuller contradiction matrix
(1,254 non-empty cells) — matrix cells cross-checked cell-by-cell
against the MIT-licensed SharathSPhD/triz-engine reference at build
time (NOTICE.md carries the attribution; the pinned reference commit
is recorded in the corpus provenance block). Zero LLM, zero network.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import triz_principles as tp  # noqa: E402


def test_corpus_completeness():
    c = tp.load_corpus()
    assert c["stats"]["principles"] == 40
    assert c["stats"]["parameters"] == 39
    assert c["stats"]["matrix_cells"] == 1254
    assert len(c["principles"]) == 40
    assert len(c["parameters"]) == 39
    assert len(c["matrix"]) == 1254


def test_principle_ids_names_descriptions_examples():
    c = tp.load_corpus()
    for p in c["principles"]:
        assert isinstance(p["id"], int) and 1 <= p["id"] <= 40
        # corpus names byte-match the engine's classical 40 (the legacy
        # table and the corpus can never drift apart)
        assert p["name"] == tp.PRINCIPLES[p["id"]], p["id"]
        assert p["description"].strip()
        assert isinstance(p["examples"], list) and len(p["examples"]) >= 2
        assert all(e.strip() for e in p["examples"])


def test_parameters_wellformed():
    c = tp.load_corpus()
    ids = [p["id"] for p in c["parameters"]]
    assert ids == list(range(1, 40))
    for p in c["parameters"]:
        assert p["name"].strip() and p["description"].strip()


def test_matrix_shape_and_value_range():
    c = tp.load_corpus()
    for k, vals in c["matrix"].items():
        a, _, b = k.partition("_")
        ai, bi = int(a), int(b)
        assert 1 <= ai <= 39 and 1 <= bi <= 39, k
        assert ai != bi, k
        assert isinstance(vals, list) and vals, k
        assert all(isinstance(v, int) and 1 <= v <= 40 for v in vals), k


def test_matrix_known_cells():
    """Spot checks pinned from the classical matrix (verified against
    the MIT reference clone during the R53 build)."""
    c = tp.load_corpus()
    assert c["matrix"]["1_2"] == [15, 8, 29, 34]      # mov.weight vs stat.weight
    assert c["matrix"]["9_10"] == [13, 28, 15, 19]    # speed vs force
    assert c["matrix"]["17_31"] == [22, 35, 2, 24]    # temperature vs object harm
    assert c["matrix"]["39_22"] == [28, 10, 29, 35]   # productivity vs energy loss
    # the encoding is near-symmetric but NOT guaranteed: 10_9 exists
    # and differs from 9_10's tail (12 vs 19), and 2_1 is empty while
    # 1_2 is not — resolve_contradiction must return the EXACT cell,
    # never a mirrored guess
    assert c["matrix"]["10_9"] == [13, 28, 15, 12]
    assert "2_1" not in c["matrix"]


def test_resolve_contradiction_deterministic_and_typed():
    # known cell resolves; order preserved
    assert tp.resolve_contradiction(1, 2) == [15, 8, 29, 34]
    # the exact stored cell for either orientation — never a mirrored
    # guess (10_9 legitimately differs from 9_10's tail in the
    # classical encoding)
    assert tp.resolve_contradiction(10, 9) == [13, 28, 15, 12]
    # an empty cell is a typed empty answer
    assert tp.resolve_contradiction(2, 1) == []
    # typed degenerate cases: empty, never a fallback
    assert tp.resolve_contradiction(1, 1) == []
    assert tp.resolve_contradiction(0, 5) == []
    assert tp.resolve_contradiction(5, 40) == []
    assert tp.resolve_contradiction("1", 2) == []
    assert tp.resolve_contradiction(None, 2) == []


def test_contradiction_for_problem_text():
    # a thermal-harm problem resolves through the hints + the matrix
    r = tp.contradiction_for(
        "improve the throughput of the kiln while the waste heat and "
        "emissions from the burner fall")
    assert r["improving"] == 39          # productivity hint
    assert r["worsening"] == 31          # object-generated harm hint
    assert r["principles"] == tp.resolve_contradiction(39, 31)
    assert r["principles"], "39_31 is a classical non-empty cell"
    assert all(n for n in r["principle_names"])
    # unmatched side -> typed None (never a guessed parameter)
    r2 = tp.contradiction_for("a poem about nothing engineering")
    assert r2["improving"] is None or r2["worsening"] is None or (
        r2["principles"] == tp.resolve_contradiction(
            r2["improving"], r2["worsening"]))


def test_fast_path_untouched():
    """seed_for semantics are byte-stable — the committed regressions
    and plan populations depend on them (R53 added the resolver
    alongside, it did NOT rewire the machine)."""
    seeds, cls = tp.seed_for(
        "thermal degradation and scorch of the resin at elevated "
        "temperature")
    assert seeds == (35, 19, 36) and cls == "thermal-load relief"
    assert tp.seed_for("nothing matches here at all") == (None, None)
    assert tp.distinct_principles([((35, 19),), ((19, 36),)])
    assert not tp.distinct_principles([((35, 19),), ((35, 2),)])


def test_provenance_block_carries_reference_and_attribution():
    c = tp.load_corpus()
    pr = c["provenance"]
    assert "Altshuller" in pr["methodology"]
    assert "triz-engine" in pr["reference"] and "MIT" in pr["reference"]
    assert "17d48dc0273c23bc845" in pr["reference"]
    assert "self-authored" in pr["encoding"]
