#!/usr/bin/env python3
"""tests/test_rediscovery_benchmark.py — zero-LLM pins for the DIR-8
Score-7 rediscovery wiring (the MOOSE-Chem-derived benchmark, the
loader, the pre-date restriction hook, the scanner output shape)."""
from __future__ import annotations

import hashlib
import json
import sys
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from discovery_fabric.generation import (  # noqa: E402
    inspiration_retrieval as ir,
)

BENCH = REPO / "eval" / "moose_chem" / "rediscovery_benchmark.json"
XLSX = REPO / "eval" / "moose_chem" / "chem_research_2024.xlsx"


def test_benchmark_exists_with_at_least_20_items():
    doc = json.loads(BENCH.read_text(encoding="utf-8"))
    assert doc["n_items"] >= 20
    assert len(doc["items"]) == doc["n_items"]
    assert doc["n_items"] == 51  # the committed extraction (typed pin)


def test_every_item_is_post_cutoff_with_a_real_hypothesis():
    doc = json.loads(BENCH.read_text(encoding="utf-8"))
    for it in doc["items"]:
        d = date.fromisoformat(it["public_date"])
        assert d.year == 2024, it["item_id"]
        assert it["true_hypothesis"].strip(), it["item_id"]
        assert it["background_question"].strip(), it["item_id"]
        assert it["retrieval_restriction"]["cutoff"] == it["public_date"]


def test_provenance_xlsx_bytes_match_the_recorded_sha():
    doc = json.loads(BENCH.read_text(encoding="utf-8"))
    sha = hashlib.sha256(XLSX.read_bytes()).hexdigest()
    assert doc["source"]["xlsx_sha256"] == sha
    assert doc["source"]["repo"] == "github.com/ZonglinY/MOOSE-Chem"


def test_loader_and_pre_date_filter_fail_closed():
    items = ir.rediscovery_benchmark_items()
    assert len(items) >= 20
    filt = ir.pre_date_corpus_filter(
        [{"source_id": "a", "published": "2023-05-01"},
         {"source_id": "b", "published": "2024-08-07"},
         {"source_id": "c", "published": None}],
        "2024-01-10")
    assert filt["kept"] == 1
    # undated evidence is EXCLUDED (fail closed: undated != pre-date)
    assert {e["why"].split()[0] for e in filt["excluded"]} == {
        "post-cutoff", "unparseable"}


def test_github_scan_output_shape():
    scan = sorted((REPO / "eval").glob("github_scan_*.json"))
    assert scan, "at least one scan output must exist"
    doc = json.loads(scan[-1].read_text(encoding="utf-8"))
    keys = {t["key"] for t in doc["targets"]}
    assert {"MOOSE-Chem", "AutoPatent", "HypoBench", "open-collider",
            "SciAgents", "FlagEmbedding"} <= keys
    for t in doc["targets"]:
        assert t["decision"] and t["basis"]
    moose = next(t for t in doc["targets"] if t["key"] == "MOOSE-Chem")
    assert moose["repo"]["exists"] is True
    assert moose["repo"]["full_name"] == "ZonglinY/MOOSE-Chem"
