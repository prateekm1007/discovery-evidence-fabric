"""R412 gradient-v3 normalization-field pinning tests (hermetic).

Incident R412-GRADIENT-V3-NORM-METADATA-FIELDS (2026-09-06, gate-fail
decomposition): the fabric's canonicalization dropped every field a
metadata-only source uniquely carried. Measured from the committed v3
lane pool bytes: 212/483 crossref records lost `issued_year`; 176/483
google_patents records lost `publication_date` AND their only text
(`snippet`); `best_record` stayed EMPTY for any record whose sources
all lack abstracts (the longest-abstract comparison never fires), so
FEAL's multi-field year fallback and the engine-item abstract chain
had nothing to read.

These tests pin the repaired field flow end-to-end so the defect
cannot silently return (Art. XVII/XVI: code is a hypothesis about
enforcement; tests are the evidence). They ALSO pin the precedence
that must NOT change: a strictly-richer abstract still replaces a
metadata-only representative; and the repair must never fabricate a
year — a record whose sources carry no year field stays None (Art. XXV).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.source_registry.base import (
    SourceRecord, utc_now,
)
from discovery_fabric.retrieval_fabric.canonical import Canonicalizer
from discovery_fabric.retrieval_fabric.pipeline import _to_engine_item
from discovery_fabric.r412.frontier_evidence import (
    extract_year, pool_record_from_item,
)


def _src_rec(source_id: str, record_id: str, title: str,
             normalized: dict, document_type: str = "") -> SourceRecord:
    return SourceRecord(
        source_id=source_id, role="SCIENTIFIC", record_id=record_id,
        title=title, uri=f"https://example.org/{record_id}",
        retrieved_at=utc_now(), query="stub", raw_payload_sha256="f" * 64,
        normalized=normalized, provenance={"provider": source_id},
        epistemic_state="OBSERVED")


def _add(canon: Canonicalizer, rec: SourceRecord,
         document_type: str = "") -> None:
    canon.add(rec.source_id, rec.normalized, "stub", "UNKNOWN",
              "REPOSITORY", document_type, "")


def _canon_records(canon: Canonicalizer):
    return canon.canonical_records()


def _ingest_patent(canon: Canonicalizer, patent_id: str, title: str,
                   snippet: str, publication_date: str) -> None:
    """Mimic the pipeline's patent ingest path: the adapters' hit is
    converted via patent_record_from_hit and merged into normalized
    BEFORE canonicalizer.add (pipeline.py _ingest path)."""
    from discovery_fabric.retrieval_fabric.adapters import (
        patent_record_from_hit,
    )
    normalized = {
        "patent_id": patent_id, "snippet": snippet, "title": title,
        "publication_date": publication_date,
        "assignee_or_authors": ["ACME"],
        "source_url": f"https://patents.example/{patent_id}",
        "raw_payload_sha256": "f" * 64, "raw_metadata": {},
        "query": "stub",
    }
    normalized.update(patent_record_from_hit(normalized, "stub"))
    canon.add("google_patents", normalized, "stub", "UNKNOWN",
              "PATENT", "PATENT", "document_type=PATENT")


def test_crossref_issued_year_survives_canonicalization():
    """crossref's normalized carries `issued_year` (never
    `publication_year`) and no abstract — the year must still reach
    rec.publication_year AND best_record.issued_year."""
    canon = Canonicalizer()
    _add(canon, _src_rec(
        "crossref", "doi:10.1234/v3test-a", "Measured switching energy study",
        {"doi": "10.1234/v3test-a", "title": "Measured switching energy study",
         "issued_year": 2019, "container_title": "J. Power"}))
    recs = _canon_records(canon)
    assert len(recs) == 1
    r = recs[0]
    assert str(r.publication_year) == "2019"
    assert r.best_record.get("issued_year") == 2019


def test_patent_publication_date_and_snippet_survive():
    """google_patents normalized carries `publication_date` + `snippet`
    (no abstract, no year keys) — both must flow: date to the year
    fields, snippet to the engine item's abstract slot."""
    canon = Canonicalizer()
    _ingest_patent(canon, "US1", "Fuel saving control method",
                   "achieves 12% fuel reduction versus baseline fleet",
                   "2021-03-04")
    recs = _canon_records(canon)
    assert len(recs) == 1
    r = recs[0]
    assert r.publication_year == "2021-03-04"
    item = _to_engine_item(r, rank=0, lane="PATENT")
    assert "12% fuel reduction" in str(item["abstract"])
    # the FEAL pool record (the persisted schema) recovers the year
    pool = pool_record_from_item(item, r.to_dict())
    assert pool["publication_year"] == 2021


def test_pool_record_year_recovery_crossref_chain():
    """FEAL pool_record_from_item must recover the crossref year through
    the engine item + canonical best_record chain (the exact path the
    v3 lane pools measured broken: 212/483 records year=None)."""
    canon = Canonicalizer()
    _add(canon, _src_rec(
        "crossref", "doi:10.1234/v3test-b", "Actuation bandwidth measurements",
        {"doi": "10.1234/v3test-b", "title": "Actuation bandwidth measurements",
         "issued_year": 2018}))
    r = _canon_records(canon)[0]
    item = _to_engine_item(r, rank=0, lane="SCHOLARLY")
    pool = pool_record_from_item(item, r.to_dict())
    assert pool["publication_year"] == 2018


def test_metadata_only_seeds_best_record_then_richer_wins():
    """Precedence pin: a metadata-only first appearance seeds
    best_record (never left empty), and a strictly-richer abstract
    still replaces it — the original 'richest representative' rule is
    unchanged by the repair."""
    canon = Canonicalizer()
    norm_meta = {"doi": "10.1234/v3test-c", "title": "Same paper", "issued_year": 2017}
    norm_rich = {"doi": "10.1234/v3test-c", "title": "Same paper",
                 "publication_year": "2017",
                 "abstract": "A" * 200 + " with measured 40% efficiency"}
    _add(canon, _src_rec("crossref", "doi:10.1234/v3test-c", "Same paper", norm_meta))
    _add(canon, _src_rec("core", "core:1", "Same paper", norm_rich))
    r = _canon_records(canon)[0]
    assert r.best_record.get("abstract")  # richer representative won
    assert str(r.publication_year) == "2017"  # year preserved either way


def test_no_year_is_never_fabricated():
    """Art. XXV pin: a record whose sources carry no year-bearing field
    stays year=None through the whole chain — the repair reads fields,
    it never invents values."""
    canon = Canonicalizer()
    _add(canon, _src_rec(
        "datacite", "dc:1", "Dataset without any date field",
        {"title": "Dataset without any date field"}))
    r = _canon_records(canon)[0]
    assert r.publication_year is None
    item = _to_engine_item(r, rank=0, lane="SCHOLARLY")
    pool = pool_record_from_item(item, r.to_dict())
    assert pool["publication_year"] is None
    assert extract_year(None, "", None) is None


def test_patent_snippet_numeric_evidence_now_extractable():
    """The directive-level purpose of the repair: a patent snippet
    carrying a measured value becomes extractable numeric evidence in
    the FEAL pool (title+abstract text), instead of a zero-text pool
    record (measured: 176/483 v3 pool records had NO text)."""
    from discovery_fabric.r412.frontier_evidence import (
        extract_numeric_evidence,
    )
    title = "Fuel saving control method"
    snippet = ("The method achieves 12.5% fuel reduction versus the "
               "unmodified baseline under identical load.")
    out = extract_numeric_evidence(title, snippet)
    evs = out["evidences"]
    assert any("12.5%" in e.get("span", "") for e in evs)
    assert any(e.get("baseline_comparator") for e in evs)
