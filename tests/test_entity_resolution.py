"""Entity resolution + contradiction detection tests (hermetic) and the
cross-source dedup discipline (Art. XXI.6)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.entity_resolution import (
    EntityRegistry, detect_contradictions, extract_identity_keys,
    normalize_doi, normalize_patent_number, normalize_title,
)


# ---------------------------------------------------------------------------
# key normalization
# ---------------------------------------------------------------------------

def test_doi_normalization_forms():
    assert normalize_doi("https://doi.org/10.1234/abc.def") == "10.1234/abc.def"
    assert normalize_doi("DOI: 10.1234/ABC.DEF") == "10.1234/abc.def"
    assert normalize_doi("10.48550/arxiv.2110.02266") == "arxiv:2110.02266"
    assert normalize_doi("10.48550/arxiv.2110.02266v2") == "arxiv:2110.02266"
    assert normalize_doi("not a doi") is None
    assert normalize_doi(None) is None


def test_patent_number_normalization():
    assert normalize_patent_number("US1234567B2") == "US1234567"
    assert normalize_patent_number("US 12,345,678 A1") == "US12345678"
    assert normalize_patent_number("1234567") == "US1234567"
    assert normalize_patent_number("EP12345") is None  # too short
    assert normalize_patent_number("random text") is None


# ---------------------------------------------------------------------------
# same paper across sources -> ONE canonical entity
# ---------------------------------------------------------------------------

def _paper(source, doi=None, pmid=None, arxiv=None, **norm):
    normalized = {"doi": doi, "pmid": pmid, "arxiv_id": arxiv, **norm}
    return {"source_id": source, "record_id": f"{source}:r1",
            "raw_payload_sha256": f"sha-{source}", "normalized": normalized}


def test_same_paper_merges_across_sources():
    records = [
        _paper("europepmc", doi="10.1111/j.123456", pmid="12345",
               title="A Study", publication_year=2020),
        _paper("pubmed", pmid="12345", title="A Study",
               publication_year=2020),
        _paper("arxiv", arxiv="2110.02266", title="A Study"),
        _paper("elsevier_scopus", doi="https://doi.org/10.1111/j.123456",
               title="A  Study", publication_year=2020),
    ]
    reg = EntityRegistry()
    report = reg.resolve(records)
    # europepmc+pubmed merge on PMID; scopus merges on DOI; the arXiv
    # record (different id) stays its own entity
    assert report["records_considered"] == 4
    assert report["canonical_entities"] == 2
    assert report["cross_source_entities"] == 1
    assert report["unresolved_records"] == 0


def test_arxiv_doi_form_merges_with_arxiv_source():
    records = [
        _paper("arxiv", arxiv="2110.02266", title="T"),
        _paper("crossref", doi="10.48550/arxiv.2110.02266", title="T"),
    ]
    reg = EntityRegistry()
    rep = reg.resolve(records)
    assert rep["canonical_entities"] == 1
    assert rep["cross_source_entities"] == 1


def test_patent_merges_across_sources():
    def patent(source, num):
        return {"source_id": source, "record_id": f"{source}:{num}",
                "raw_payload_sha256": f"sha-{source}",
                "normalized": {"patent_number": num}}
    reg = EntityRegistry()
    rep = reg.resolve([patent("google_patents", "US1234567B2"),
                       patent("lens_patent", "US 12,345,678"),
                       patent("patentbear", "1234567")])
    # first two merge (both US12345678? no: US1234567 vs US12345678 differ)
    # google US1234567B2 -> US1234567 ; patentbear 1234567 -> US1234567
    assert rep["canonical_entities"] == 2
    assert rep["cross_source_entities"] == 1


def test_unresolved_records_disclosed_never_title_merged():
    recs = [{"source_id": "x", "record_id": "x:1",
             "normalized": {"title": "Same Title Text"}}]
    reg = EntityRegistry()
    rep = reg.resolve(recs)
    assert rep["canonical_entities"] == 0
    assert rep["unresolved_records"] == 1
    assert rep["unresolved_disclosed"][0]["reason"] == "NO_IDENTITY_KEY"


# ---------------------------------------------------------------------------
# contradiction detection
# ---------------------------------------------------------------------------

def test_contradiction_surfaced_with_both_provenances():
    records = [
        _paper("europepmc", doi="10.1234/x", publication_year=2020),
        _paper("crossref", doi="10.1234/x", publication_year=2019),
    ]
    cons = detect_contradictions(records)
    hits = [c for c in cons if c["field"] == "publication_year"]
    assert len(hits) == 1
    assert hits[0]["severity"] == "CONTRADICTION"
    # both sides carry provenance
    vals = hits[0]["values"]
    assert {"2020", "2019"} <= set(vals)
    assert vals["2020"][0]["source_id"] == "europepmc"
    assert vals["2019"][0]["source_id"] == "crossref"
    assert vals["2019"][0]["raw_payload_sha256"] == "sha-crossref"


def test_time_varying_fields_never_contradict():
    records = [
        _paper("europepmc", doi="10.1234/x", cited_by_count=10),
        _paper("crossref", doi="10.1234/x", cited_by_count=99),
    ]
    cons = detect_contradictions(records)
    assert all(c["field"] != "cited_by_count" for c in cons)


def test_title_divergence_is_soft_not_hard():
    records = [
        _paper("europepmc", doi="10.1234/x", title="A Study: Findings!"),
        _paper("crossref", doi="10.1234/x", title="A Retitled Study"),
    ]
    cons = detect_contradictions(records)
    t = [c for c in cons if c["field"] == "title"]
    assert t and t[0]["severity"] == "SOFT_DIVERGENCE"


def test_identical_titles_no_divergence():
    records = [
        _paper("europepmc", doi="10.1234/x", title="A Study"),
        _paper("crossref", doi="10.1234/x", title="a   STUDY"),
    ]
    cons = detect_contradictions(records)
    assert not [c for c in cons if c["field"] == "title"]


def test_cross_source_only_intra_source_dupe_not_contradiction():
    # same source twice, different years -> duplicate retrieval, not a
    # cross-source contradiction (flagged only across DISTINCT sources)
    records = [
        _paper("europepmc", doi="10.1234/x", publication_year=2020),
        _paper("europepmc", doi="10.1234/x", publication_year=2019),
    ]
    cons = detect_contradictions(records)
    assert not cons
