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
    # slip-ring contact vocabulary are what the primary MISSED)
    assert "arcing" in fterms
    assert "slip-ring" in fterms
    assert "wear" in fterms
    # R6 A4 follow-up (measured 2026-11-12): the variant is capped at
    # the measured 5-term cliff (6+ ANDed terms -> 0 records live), so
    # 'open-circuit' (the 6th+ first-occurrence term) no longer rides
    # the FAILURE_TEXT variant — breadth past the cliff is worthless;
    # the strongest terms (slip-ring, contact, wear, arcing) stay.
    assert "open-circuit" not in fterms


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


# ---------------------------------------------------------------------------
# R6 A4 follow-up (owner round 2026-11-12, measured on the composer-era
# DEV12 chunk 1 + live europepmc probes): the term-count cliff and the
# whole-token exclusion — the two measured retrieval defects behind the
# dev-fu-001 MECHANISM_STARVED (all 9 candidates rejected
# NOT_EVIDENCE_ANCHORED_DOMAIN because every scholarly query was a
# sentence or a 6+ term AND-chain that retrieves 0).
# ---------------------------------------------------------------------------

def test_a4_whole_token_exclusion_keeps_split_compound_terms():
    """The primary's hyphenated compound ('bearing-spalling') must NOT
    hide the failure text's own term ('spalling') from the variant —
    the measured 0-record sentence primary carries the term only inside
    the compound, so excluding by parts starves every effective query."""
    from discovery_fabric.retrieval_fabric.query_expansion import (
        _content_terms)
    failure = ("inner-race spalling progresses for weeks before the "
               "vibration alarm trips; by then the bearing is past repair")
    primary = ("rolling-element bearing in a 350 kW industrial fan drive "
               "bearing-spalling")
    terms = _content_terms(failure, exclude=primary)
    assert "spalling" in terms, terms
    # 'bearing' IS a whole token of the primary -> still excluded
    assert "bearing" not in terms, terms


def test_a4_variant_cap_at_measured_term_cliff():
    """Live-measured europepmc cliff (2026-11-12): 4-5 ANDed terms -> 10
    records; a 6th term -> 0. Both A4 variants are capped at 5 terms."""
    from discovery_fabric.retrieval_fabric.query_expansion import (
        failure_constraint_variants, mechanism_query)
    problem = {
        "problem_id": "dev-fu-001-bearing-spalling",
        "device": "rolling-element bearing in a 350 kW industrial fan drive",
        "failure_mode": "bearing-spalling",
        "failure": ("inner-race spalling progresses for weeks before the "
                    "vibration alarm trips; by then the bearing is past "
                    "repair and must be replaced"),
        "constraint": ("predictor must use the existing 1 kHz vibration "
                       "sensor and 1 Hz SCADA logging, fire at least 14 "
                       "days early, at most 2 false alarms per year"),
    }
    primary = mechanism_query(problem)
    variants = failure_constraint_variants(problem, primary)
    by_class = {v["derivation_class"]: v for v in variants}
    for cls in ("FAILURE_TEXT_TERMS", "CONSTRAINT_TARGETED"):
        q = by_class[cls]["query"]
        assert len(q.split()) <= 5, (cls, q)


def test_a4_variants_routed_to_scholarly_keyword_sources():
    """The measured 0-record sentence primary means the scholarly
    keyword sources need the A4 term variants ADDITIVELY (measured:
    4-5 term forms retrieve 10 on-domain records where the sentence
    retrieves 0)."""
    from discovery_fabric.retrieval_fabric.pipeline import (
        SOURCE_VARIANT_POLICY, _select_variants)
    for src in ("semantic_scholar", "crossref", "doaj", "arxiv",
                "openaire"):
        assert SOURCE_VARIANT_POLICY[src] == "PRIMARY_AND_FAILURE_TEXT", src
    variants = [
        {"query": "primary form", "derivation_class": "PRIMARY"},
        {"query": "spalling vibration alarm", "derivation_class":
         "FAILURE_TEXT_TERMS"},
        {"query": "predictor khz scada", "derivation_class":
         "CONSTRAINT_TARGETED"},
    ]
    sel = _select_variants(variants, "PRIMARY_AND_FAILURE_TEXT")
    classes = [v["derivation_class"] for v in sel]
    assert classes == ["PRIMARY", "FAILURE_TEXT_TERMS",
                       "CONSTRAINT_TARGETED"], classes


def test_mechanism_rerank_prefers_problem_relevant_records():
    """R6 A4 follow-up (measured 2026-11-12, dev-fu-001 chunk 1): the
    density-only rerank selected a mechanism-dense OFF-DOMAIN composite
    beams paper for a bearing problem; the anchor gate then rejected
    every candidate -> MECHANISM_STARVED. With the problem given, the
    relevance component (0.5 per shared problem-fact term) puts the
    on-domain record first; without a problem the order is unchanged."""
    from discovery_fabric.engine import mechanism_space as ms
    problem = {
        "problem_id": "dev-fu-001-bearing-spalling",
        "device": "rolling-element bearing in a 350 kW industrial fan drive",
        "failure_mode": "bearing-spalling",
        "failure": ("inner-race spalling progresses for weeks before the "
                    "vibration alarm trips"),
        "constraint": ("predictor must use the existing 1 kHz vibration "
                       "sensor"),
    }
    off_domain = {
        "id": "doi:10.3390/ma19173622",
        "title": "Interlaminar stress in composite beams",
        "abstract": ("The governing role of interlaminar stress in "
                     "determining structural performance and failure; "
                     "fatigue crack growth, delamination, stress "
                     "distribution, fracture, load transfer, stiffness "
                     "degradation, matrix cracking, shear stress."),
    }
    on_domain = {
        "id": "doi:10.1016/j.jsv.2026.120074",
        "title": "Bearing fault diagnosis via vibration monitoring",
        "abstract": ("Rolling element bearing spalling on the inner race "
                     "produces characteristic vibration signatures; the "
                     "alarm threshold fires weeks before replacement."),
    }
    bare = ms.mechanism_signal_rerank([off_domain, on_domain], top_k=2)
    assert bare["selected_ids"][0] == "doi:10.3390/ma19173622", (
        "fixture precondition: the off-domain record is denser (this is "
        "the measured defect)")
    with_rel = ms.mechanism_signal_rerank([off_domain, on_domain],
                                          top_k=2, problem=problem)
    assert with_rel["selected_ids"][0] == "doi:10.1016/j.jsv.2026.120074", (
        with_rel["policy"])
    on = next(s for s in with_rel["all_scores"]
              if s["record_id"] == "doi:10.1016/j.jsv.2026.120074")
    assert on["n_relevance_hits"] >= 3, on
    # R6 A2 (owner 2026-11-12): the problem-given rerank adds the
    # capped BM25 component and bumps the version; the bare-call pin
    # (1.0.0, asserted just above via `bare`) is unchanged.
    assert "1.2.0" in with_rel["reranker_version"]
    assert "bm25" in with_rel["policy"].lower()
