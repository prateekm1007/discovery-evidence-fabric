"""tests/test_r6_retrieval_relevance.py — owner audit round 2026-11-13 P1.

Pins the retrieval-relevance improvement, not a generalization claim:
  1. The frozen benchmark is authored (NOT_INDEPENDENT), covers five
     labeled dimensions, and the report says lexical screening only.
  2. The improved reranker (mechanism_signal_rerank/1.1.0 +
     retrieval_relevance/1.0.0) is measured against the frozen 1.0.0
     comparator at every declared depth, with counts and Wilson CIs.
  3. The measured result: improved precision/recall is never WORSE at any
     depth and is strictly better at depth 5 (the hard-confuser depth).
  4. The term-priority regression: the old sorted-14 extraction dropped
     device-critical late-alphabet terms ('transformer'); the live list
     must carry it.
  5. Bare calls (no problem) keep the 1.0.0 replay semantics; problem
     calls record the per-dimension basis.
  6. Labels cannot leak into the ranker.

Deterministic, zero LLM, zero network.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.engine import mechanism_space as ms  # noqa: E402

_SPEC = importlib.util.spec_from_file_location(
    "r6_retrieval_relevance_benchmark",
    REPO / "scripts" / "r6_retrieval_relevance_benchmark.py")
B = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(B)


def _benchmark():
    return json.loads(
        (REPO / "R6" / "RETRIEVAL_RELEVANCE_BENCHMARK.json").read_text(
            encoding="utf-8"))


def _report():
    return B.run(_benchmark())


def test_benchmark_is_labeled_and_disclosed_as_authored():
    b = _benchmark()
    assert b["independence_state"] == "NOT_INDEPENDENT"
    assert b["authoring_provenance"]
    assert b["label_dimensions"] == list(
        ms.RETRIEVAL_RELEVANCE_DIMENSIONS)
    assert b["depths"] == [3, 5, 8]
    for pr in b["problems"]:
        assert pr["problem"]["device"]
        for r in pr["records"]:
            assert set(r["relevance"]) == set(
                ms.RETRIEVAL_RELEVANCE_DIMENSIONS)
            assert set(r["relevance"].values()) <= {0, 1}


def test_report_never_promotes_the_lexical_screen():
    r = _report()
    assert r["classification"] == "LEXICAL_SCREENING_HEURISTIC"
    assert r["discovery_credit"] == (
        "NOT_ESTABLISHED_AS_RELEVANCE_VALIDATION")
    assert r["baseline_instrument"] == "mechanism_signal_rerank/1.0.0"
    assert r["improved_instrument"] == "mechanism_signal_rerank/1.1.0"


def test_every_depth_carries_counts_and_cis():
    r = _report()
    for arm in ("baseline", "improved"):
        for depth, v in r[arm].items():
            for key in ("precision_at_depth", "core_recall_at_depth"):
                m = v[key]
                assert set(m) == {"numerator", "denominator", "rate",
                                  "ci95_low", "ci95_high"}, (arm, depth,
                                                             key)
                assert 0.0 <= m["rate"] <= 1.0
            for d, m in v["dimension_recall_at_depth"].items():
                assert d in ms.RETRIEVAL_RELEVANCE_DIMENSIONS
                assert set(m) == {"numerator", "denominator", "rate",
                                  "ci95_low", "ci95_high"}


def test_measured_improvement_is_never_worse_and_better_at_depth_five():
    r = _report()
    for depth in r["baseline"]:
        b = r["baseline"][depth]
        i = r["improved"][depth]
        assert (i["precision_at_depth"]["rate"]
                >= b["precision_at_depth"]["rate"]), depth
        assert (i["core_recall_at_depth"]["rate"]
                >= b["core_recall_at_depth"]["rate"]), depth
    d5 = r["deltas"]["5"]
    assert d5["precision_at_depth_delta"] > 0
    assert d5["core_recall_at_depth_delta"] > 0
    assert d5["mean_dimension_recall_at_depth_delta"] > 0


def test_term_priority_keeps_late_alphabet_device_terms():
    problem = _benchmark()["problems"][4]["problem"]
    terms = ms._problem_relevance_terms(problem)
    # the sorted-14 legacy extraction measured-dropped both of these
    assert "transformer" in terms
    assert "winding" in terms
    assert len(terms) <= 20


def test_bare_rerank_keeps_replay_semantics():
    records = [{"id": "a", "title": "plain index page",
                "abstract": "table of contents"}]
    bare = ms.mechanism_signal_rerank(records, top_k=1)
    assert bare["reranker_version"] == "mechanism_signal_rerank/1.0.0"
    assert bare["retrieval_relevance_version"] is None
    assert "dimension_basis" not in bare["all_scores"][0]


def test_problem_rerank_records_dimension_basis():
    pr = _benchmark()["problems"][0]
    out = ms.mechanism_signal_rerank(pr["records"], top_k=3,
                                     problem=pr["problem"])
    assert out["reranker_version"] == "mechanism_signal_rerank/1.1.0"
    assert out["retrieval_relevance_version"] == (
        ms.RETRIEVAL_RELEVANCE_VERSION)
    for s in out["all_scores"]:
        assert set(s["dimension_basis"]) == set(
            ms.RETRIEVAL_RELEVANCE_DIMENSIONS)
        assert s["n_aligned_dimensions"] == len(
            s["aligned_dimensions"])


def test_labels_cannot_leak_into_the_ranker():
    pr = _benchmark()["problems"][1]
    flipped = [dict(r, relevance={k: 0 for k in
                                  ms.RETRIEVAL_RELEVANCE_DIMENSIONS})
               for r in pr["records"]]
    a = ms.mechanism_signal_rerank(pr["records"], top_k=5,
                                   problem=pr["problem"])
    b = ms.mechanism_signal_rerank(flipped, top_k=5,
                                   problem=pr["problem"])
    assert a["selected_ids"] == b["selected_ids"]
    assert [s["score"] for s in a["all_scores"]] == \
        [s["score"] for s in b["all_scores"]]


def test_report_is_deterministic():
    b = _benchmark()
    assert (json.dumps(B.run(b), sort_keys=True)
            == json.dumps(B.run(b), sort_keys=True))
