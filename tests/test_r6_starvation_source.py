"""R6 A3/A4 regression pins (owner round 2026-11-12, zero LLM spend):

A4 — retrieval relevance: the primary query (device + failure_mode only)
was the measured starvation cause — the committed DEV pairs' failure texts
and constraints carry the mechanism vocabulary ('brush wear', 'arcing',
'creep', 'ozone cracking') that the primary never surfaced. New deterministic
variant classes FAILURE_TEXT_TERMS and CONSTRAINT_TARGETED (Art. XLIII:
problem facts, still no solution-class injection) — pinned against the
ACTUAL committed problems (eval/problems.json).

A3 — starvation at the source: the committed eval-new02 kill record shows
the on-domain Holm/IEEE records arrived METADATA-ONLY (abstract "") —
SYNTHESIZE consumes evidence[0].abstract, so the chain was cut before any
operator ran. The abstract backfill fetches missing abstracts from the
abstract-bearing S2 metadata lane (bounded, typed, custody-logged,
enrichment recorded on the record). Pinned from the committed envelope
shape (eval/kills/eval-new02-slipring-predictor.json: title-only records
with empty abstracts).
"""
import json
import sys
import urllib.error
from pathlib import Path
from unittest import mock

import pytest

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from discovery_fabric.retrieval_fabric import pipeline as rfp  # noqa: E402
from discovery_fabric.retrieval_fabric import reciprocal as _recip  # noqa: E402
from discovery_fabric.retrieval_fabric.adapters import LaneRunState  # noqa: E402
from discovery_fabric.retrieval_fabric.canonical import (  # noqa: E402
    Canonicalizer, CanonicalRecord)
from discovery_fabric.retrieval_fabric.query_expansion import (  # noqa: E402
    expand_query, failure_constraint_variants, mechanism_query)


def _committed_problem(pid):
    problems = json.loads((REPO / "eval" / "problems.json")
                          .read_text(encoding="utf-8"))["problems"]
    return next(p for p in problems if p["problem_id"] == pid)


# ---------------------------------------------------------------------------
# A4: query variants from failure text + constraint (committed problems)


def test_a4_new02_failure_terms_surface_mechanism_vocabulary():
    """The committed new02 problem: failure_mode is the bare
    'contact-wear'; the failure text carries 'brush wear', 'arcing',
    'open-circuit excitation' — the vocabulary the starved run needed."""
    p = _committed_problem("eval-new02-slipring-predictor")
    primary = mechanism_query(p)
    variants = expand_query(primary, p)
    classes = {v["derivation_class"] for v in variants}
    assert "FAILURE_TEXT_TERMS" in classes
    assert "CONSTRAINT_TARGETED" in classes
    fvar = next(v for v in variants
                if v["derivation_class"] == "FAILURE_TEXT_TERMS")
    fterms = set(fvar["query"].split())
    # the mechanism vocabulary from the failure text is now IN a query
    # ('brush'/'wear' are already in the primary; 'arcing' and the
    # open-circuit transient vocabulary are what the primary MISSED)
    assert "arcing" in fterms
    assert "open-circuit" in fterms


def test_a4_p05_failure_terms_surface_creep_and_ozone():
    """The committed p05 problem: failure_mode 'degradation' never carried
    the actual physics (creep, ozone-induced cracking) that an on-domain
    anchor needed."""
    p = _committed_problem("bench-p05-bridge-bearing-aging")
    primary = mechanism_query(p)
    variants = failure_constraint_variants(p, primary)
    fvar = next(v for v in variants
                if v["derivation_class"] == "FAILURE_TEXT_TERMS")
    fterms = set(fvar["query"].split())
    assert "creep" in fterms
    assert any("ozone" in t for t in fterms)
    cvar = next(v for v in variants
                if v["derivation_class"] == "CONSTRAINT_TARGETED")
    # the constraint's measurable bound (75-year service life) is queried
    assert "75-year" in cvar["query"] or "service" in cvar["query"]


def test_a4_variants_are_problem_facts_never_solution_class():
    """Art. XLIII: every new variant's terms originate verbatim from the
    problem's own failure/constraint texts — no invented vocabulary."""
    p = _committed_problem("eval-new02-slipring-predictor")
    primary = mechanism_query(p)
    variants = expand_query(primary, p)
    failure_lc = p["failure"].lower().replace("-", " ")
    constraint_lc = p["constraint"].lower().replace("-", " ")
    for v in variants:
        if v["derivation_class"] not in ("FAILURE_TEXT_TERMS",
                                         "CONSTRAINT_TARGETED"):
            continue
        for tok in v["query"].split():
            base = tok.replace("-", " ")
            assert tok in failure_lc or all(
                part in failure_lc or part in constraint_lc
                for part in base.split()), \
                f"invented term '{tok}' in {v['derivation_class']}"


# ---------------------------------------------------------------------------
# A3: abstract backfill (regression from the committed new02 envelope)


def _metadata_only_record(doi, title, cid="c-1", cited=None):
    rec = CanonicalRecord(canonical_id=cid, identity_basis="DOI",
                          title=title, doi=doi,
                          document_type="ARTICLE", evidence_lane="SCHOLARLY",
                          origin_source="crossref")
    rec.best_record = {
        "record_id": f"cr:{doi}", "doi": doi, "title": title,
        "abstract": "",  # the measured starved shape (title-only lane)
        "citation_count": cited or 0,
    }
    rec.doi = doi
    rec.queries_by_source = {rec.origin_source: "q"}
    return rec


def test_a3_backfill_enriches_metadata_only_record(tmp_path):
    """The committed new02 kill record's evidence shape (title-only,
    abstract '') + a DOI -> backfill fetches the abstract, records the
    enrichment ON the record (never a silent rewrite)."""
    canon = Canonicalizer()
    rec = _metadata_only_record("10.1109/holm.2018.8611774",
                                "Contact Voltage Drop and Brush Wear "
                                "Characteristics", cited=12)
    canon.canonical_records_list = None  # not used by this path
    with mock.patch.object(type(canon), "canonical_records",
                           return_value=[rec]):
        with mock.patch.object(_recip, "_s2_get") as fake_get:
            fake_get.return_value = {
                "status": "OK",
                "data": {"title": "Contact Voltage Drop",
                         "abstract": "Silver graphite brushes in slip ring "
                                     "systems exhibit wear rates that "
                                     "depend strongly on contact voltage "
                                     "drop and spring pressure; we measure "
                                     "wear across several silver content "
                                     "alloys at industrial current "
                                     "densities.",
                         "externalIds": {"DOI": "10.1109/holm.2018.8611774"}},
                "error": None, "latency_ms": 100,
                "raw_payload_sha256": "abc"}
            report = rfp._abstract_backfill(canon, [])
    assert report["attempted"] == 1 and report["enriched"] == 1
    assert rec.best_record["abstract"].startswith("Silver graphite brushes")
    assert rec.best_record["abstract_backfilled_from"] == \
        "semantic_scholar_metadata"
    assert len(rec.best_record["abstract_backfill_sha256"]) == 64
    lk = report["lookups"][0]
    assert lk["enriched"] is True and lk["status"] == "OK"
    assert fake_get.call_count == 1


def test_a3_backfill_typed_failure_never_crashes(tmp_path):
    """A RATE_LIMITED metadata answer is a typed failure in the report —
    never a crash, never absence (Art. XXI.3)."""
    canon = Canonicalizer()
    rec = _metadata_only_record("10.1109/x.2017.1", "No abstract here",
                                cid="c-2")
    with mock.patch.object(type(canon), "canonical_records",
                           return_value=[rec]):
        with mock.patch.object(_recip, "_s2_get") as fake_get:
            fake_get.return_value = {"status": "RATE_LIMITED", "data": None,
                                     "error": "throttled",
                                     "latency_ms": 5,
                                     "raw_payload_sha256": "h"}
            report = rfp._abstract_backfill(canon, [])
    assert report["enriched"] == 0 and report["failed"] == 1
    assert report["lookups"][0]["status"] == "RATE_LIMITED"
    assert rec.best_record["abstract"] == ""  # unchanged, honest


def test_a3_backfill_disabled_by_env_and_k0(tmp_path, monkeypatch):
    monkeypatch.setenv("RETRIEVE_ABSTRACT_BACKFILL_K", "0")
    canon = Canonicalizer()
    rec = _metadata_only_record("10.1/x", "t", cid="c-3")
    with mock.patch.object(type(canon), "canonical_records",
                           return_value=[rec]):
        with mock.patch.object(_recip, "_s2_get") as fake_get:
            report = rfp._abstract_backfill(canon, [])
    assert report["enabled"] is False
    assert fake_get.call_count == 0


def test_a3_backfill_caps_at_top_k_and_records_lane_state(tmp_path,
                                                          monkeypatch):
    monkeypatch.setenv("RETRIEVE_ABSTRACT_BACKFILL_K", "2")
    canon = Canonicalizer()
    recs = [_metadata_only_record(f"10.1/{i}", f"t{i}", cid=f"c-{i}",
                                  cited=i) for i in range(5)]
    with mock.patch.object(type(canon), "canonical_records",
                           return_value=recs):
        with mock.patch.object(_recip, "_s2_get") as fake_get:
            fake_get.return_value = {"status": "EMPTY", "data": {},
                                     "error": None, "latency_ms": 1,
                                     "raw_payload_sha256": "h"}
            states: list = []
            report = rfp._abstract_backfill(canon, states)
    assert report["attempted"] == 2 and len(report["lookups"]) == 2
    # deterministic order: highest citation count first
    assert report["lookups"][0]["doi"] == "10.1/4"
    assert len(states) == 1 and states[0].source_id == \
        "semantic_scholar_metadata"
    assert states[0].record_count == 0 and states[0].status == "EMPTY"


def test_a3_backfill_skips_records_that_already_have_abstracts(tmp_path):
    canon = Canonicalizer()
    rec = _metadata_only_record("10.1/y", "rich record", cid="c-4")
    rec.best_record["abstract"] = "x" * 120  # already text-bearing
    with mock.patch.object(type(canon), "canonical_records",
                           return_value=[rec]):
        with mock.patch.object(_recip, "_s2_get") as fake_get:
            report = rfp._abstract_backfill(canon, [])
    assert report["attempted"] == 0 and report["candidates"] == 0
    assert fake_get.call_count == 0
