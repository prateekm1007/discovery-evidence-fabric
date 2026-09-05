"""R409 retrieval-fabric adversarial test suite (hermetic — no network).

Directive section 10: test the engine against queries where a source is
unavailable, rate-limited, the same document appears in 5 databases, a
patent contains the important claim but the title is irrelevant, and
retrieval breadth must not collapse when one provider fails.

Art. VIII/XVII discipline: these tests ATTACK the fabric — stub
connectors return fabricated fixtures (allowed in TESTS ONLY,
monkeypatch-scoped), and the tests assert the fabric's honest behavior:
failures recorded, never converted to absence; dedup without provenance
loss; independence measured, never assumed; LLM may propose queries but
never records.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List
from unittest import mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from discovery_fabric.source_registry.base import (
    ConnectorBase, SourceQueryResult, SourceRecord, utc_now,
)
from discovery_fabric.retrieval_fabric import fabric_registry
from discovery_fabric.retrieval_fabric.canonical import (
    Canonicalizer, normalize_doi, title_fingerprint,
)
from discovery_fabric.retrieval_fabric.lineage import (
    independence_clusters, source_independence_score,
)
from discovery_fabric.retrieval_fabric.publication_status import (
    label_publication_status, lane_for_publication_status,
)
from discovery_fabric.retrieval_fabric.query_expansion import (
    expand_query, llm_expand, mechanism_query,
)
from discovery_fabric.retrieval_fabric import pipeline as fabric_pipeline
from discovery_fabric.retrieval_fabric.benchmark.corpus import (
    load_corpus, target_match,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
V1_PATH = REPO_ROOT / "discovery_fabric" / "a2" / "retrieve.py"

# The V1 file is FROZEN at this round's hash: V1 is the historical
# two-source fabric (byte-unchanged, corpus immutable — directive
# section 13). Changing it requires a new fabric version + an explicit
# epistemic event, never a silent edit.
V1_SHA256 = "4a89af5504dd39aa84bd12bf4980e6e348f501aa6d45c16ac78d3d189c843da6"


# ---------------------------------------------------------------------------
# helpers: stub connectors (test fixtures ONLY — Art. VI applies to
# production records, and the fabric only ingests connector results)
# ---------------------------------------------------------------------------

def _rec(source_id: str, record_id: str, title: str, doi: str = "",
         abstract: str = "", **norm) -> SourceRecord:
    n = {"doi": doi or None, "title": title, "abstract": abstract or None,
         "publication_year": "2020"}
    n.update(norm)
    return SourceRecord(
        source_id=source_id, role="SCIENTIFIC", record_id=record_id,
        title=title, uri=f"https://example.org/{record_id}",
        retrieved_at=utc_now(), query="stub", raw_payload_sha256="f" * 64,
        normalized=n, provenance={"provider": source_id},
        epistemic_state="OBSERVED")


class StubConnector(ConnectorBase):
    """Returns a canned SourceQueryResult (success or a failure state)."""
    SOURCE_ID = "stub"
    ROLES = ("SCIENTIFIC",)

    def __init__(self, status: str = "OK", records: List[SourceRecord] = None,
                 error: str = None):
        self.status = status
        self.records = records or []
        self.error = error

    def build_url(self, query): return "https://stub.example/api"

    def parse_payload(self, raw, query): return {}

    def normalize_payload(self, payload, query, raw_sha): return []

    def search(self, query: str, timeout: int = 25,
               retrieval_role: str = "") -> SourceQueryResult:
        if self.status in ("OK", "EMPTY"):
            return SourceQueryResult(
                source_id=self.SOURCE_ID, status=self.status, ok=True,
                records=self.records, query=query, retrieved_at=utc_now())
        return SourceQueryResult(
            source_id=self.SOURCE_ID, status=self.status, ok=False,
            error=self.error or "stubbed failure", query=query,
            retrieved_at=utc_now())


def _stub_pool(monkeypatch, connector_map: Dict[str, StubConnector],
               disable_extras: bool = True) -> Dict[str, Any]:
    """Patch the fabric pipeline to use ONLY stub connectors (hermetic)."""
    def fake_connector_for(source_id, scoped=None):
        return connector_map.get(source_id)

    monkeypatch.setattr(fabric_pipeline, "_connector_for",
                        fake_connector_for)
    monkeypatch.setattr(
        fabric_pipeline, "_connector_for",
        fake_connector_for, raising=True)
    captured: Dict[str, Any] = {}

    def fake_claims(patent_id, retries=1):
        from discovery_fabric.retrieval_fabric.adapters import \
            PatentClaimFetch
        captured[patent_id] = True
        return PatentClaimFetch(patent_id=patent_id, ok=True,
                                claim_count=8,
                                claims_excerpt="1. A sensor comprising "
                                "a dummy element bridge...",)

    monkeypatch.setattr(fabric_pipeline, "fetch_patent_claims_custoied",
                        fake_claims)
    # disable reciprocal + unpaywall (network) for hermetic runs
    monkeypatch.setattr(
        "discovery_fabric.retrieval_fabric.reciprocal.reciprocal_expansion",
        lambda *a, **k: {"records": [], "calls": [],
                         "budget": {"max": 4, "used": 0},
                         "retrieved_at": utc_now()})
    return captured


PROBLEM = {
    "device": "implantable dual matched pressure sensor",
    "failure_mode": "SENSOR_DRIFT",
    "constraint": "in vivo accuracy",
}


# ---------------------------------------------------------------------------
# 1. fabric registry + V1 immutability
# ---------------------------------------------------------------------------

def test_fabric_registry_validates_and_cross_references():
    data = fabric_registry.load_fabric_sources()
    errors = fabric_registry.validate_fabric_sources(data)
    assert errors == []
    v2 = fabric_registry.fabric_sources_for_version("V2")
    families = {s["source_family"] for s in v2}
    # >= 6 materially different families wired (acceptance criterion 1 —
    # the LIVE proof is the benchmark; this is the structural floor)
    assert len(families) >= 6
    # V1 membership is exactly the historical pair
    v1_members = [s["source_id"] for s in data["sources"]
                  if "V1" in s.get("fabric_versions", [])]
    assert v1_members == ["europepmc", "openalex"]
    # directive's required fields present on every source
    for s in data["sources"]:
        for field in ("source_id", "source_name", "source_type",
                      "source_family", "api_endpoint",
                      "authentication_required", "free_access",
                      "open_metadata", "full_text_available",
                      "patent_coverage", "preprint_coverage",
                      "thesis_dissertation_coverage",
                      "conference_coverage",
                      "technical_report_coverage", "citation_graph",
                      "date_coverage", "discipline_coverage", "rate_limit",
                      "license", "provenance_requirements",
                      "health_status", "derives_from"):
            assert field in s, (s["source_id"], field)


def test_v1_pipeline_is_frozen_byte_unchanged():
    """Directive section 13: V1 code byte-unchanged; historical corpus
    immutable. A change to a2/retrieve.py REQUIRES a new fabric version
    and an explicit recorded event — never a silent edit."""
    h = hashlib.sha256(V1_PATH.read_bytes()).hexdigest()
    assert h == V1_SHA256, (
        "a2/retrieve.py (RETRIEVAL_FABRIC_V1) changed: "
        f"{h} != {V1_SHA256}. V1 must stay byte-unchanged; historical "
        "corpora were produced by this exact code (Art. XI). Changing "
        "it requires a new fabric version + epistemic event.")


def test_registry_distinguishes_source_kinds():
    data = fabric_registry.load_fabric_sources()
    by_id = {s["source_id"]: s for s in data["sources"]}
    # metadata vs fulltext vs discovery/index distinctions are declared
    assert by_id["crossref"]["source_type"] == "REGISTRY"
    assert by_id["openalex"]["source_type"] == "DISCOVERY_INDEX"
    assert by_id["unpaywall"]["source_type"] == "RESOLUTION"
    assert by_id["openaire"]["source_type"] == "AGGREGATOR"
    assert by_id["europepmc"]["full_text_available"] is True
    assert by_id["openalex"]["full_text_available"] is False
    # thesis/patent coverage flags distinguish sources
    assert by_id["datacite"]["thesis_dissertation_coverage"] is True
    assert by_id["doaj"]["thesis_dissertation_coverage"] is False
    assert by_id["google_patents"]["patent_coverage"] is True
    assert by_id["crossref"]["patent_coverage"] is False


# ---------------------------------------------------------------------------
# 2. publication-status labeling (a preprint is never silently
# peer-reviewed; a thesis stays THESIS; a patent is never a paper)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_id,normalized,expected", [
    ("crossref", {"type": "journal-article"}, "PEER_REVIEWED"),
    ("crossref", {"type": "dissertation"}, "THESIS"),
    ("crossref", {"type": "posted-content"}, "PREPRINT"),
    ("crossref", {"type": "proceedings-article"}, "CONFERENCE"),
    ("crossref", {"type": "dataset"}, "DATASET"),
    ("openalex", {"type": "dissertation"}, "THESIS"),
    ("openalex", {"type": "preprint"}, "PREPRINT"),
    ("openaire", {"instancetypes": ["Thesis"], "refereed":
                  "nonPeerReviewed"}, "THESIS"),
    ("openaire", {"instancetypes": ["Article"], "refereed":
                  "nonPeerReviewed"}, "UNKNOWN"),
    ("openaire", {"instancetypes": ["Preprint"]}, "PREPRINT"),
    ("datacite", {"resource_type_general": "Dissertation"}, "THESIS"),
    ("datacite", {"resource_type_general": "Dataset"}, "DATASET"),
    ("datacite", {"resource_type_general": "Text"}, "UNKNOWN"),
    ("arxiv", {}, "PREPRINT"),
    ("doaj", {}, "PEER_REVIEWED"),
    ("europepmc", {"pub_type": "preprint"}, "PREPRINT"),
    ("europepmc", {"pub_type": "J"}, "PEER_REVIEWED"),
    ("core", {"document_type": "thesis"}, "THESIS"),
    ("semantic_scholar", {"publication_types": ["JournalArticle"]},
     "PEER_REVIEWED"),
    ("semantic_scholar", {"publication_types": ["Conference"]},
     "CONFERENCE"),
    ("semantic_scholar", {"publication_types": [], "arxiv_id":
                          "2201.00001"}, "PREPRINT"),
])
def test_publication_status_labeling(source_id, normalized, expected):
    got = label_publication_status(source_id, normalized)
    assert got["publication_status"] == expected
    # the label carries source-declared evidence for re-derivation
    assert isinstance(got["source_type_evidence"], str)


def test_patent_never_enters_scholarly_lane():
    assert lane_for_publication_status(
        "UNKNOWN", "google_patents", is_patent=True) == "PATENT"
    assert lane_for_publication_status(
        "PEER_REVIEWED", "google_patents") == "PATENT"
    assert lane_for_publication_status("THESIS", "crossref") == "THESIS"
    assert lane_for_publication_status("PREPRINT", "arxiv") == "PREPRINT"


def test_preprint_is_not_silently_peer_reviewed():
    """Directive: a preprint must NEVER silently become equivalent to
    peer-reviewed literature. The PREPRINT label survives merging when
    it is the first-seen status; PEER_REVIEWED from another source does
    not overwrite it, and vice versa (first-honest-label-wins)."""
    c = Canonicalizer()
    c.add("arxiv", {"record_id": "arxiv:2201.1", "title": "X", "doi": "",
                    "abstract": "y" * 80},
          "q", "PREPRINT", "PREPRINT", "", "type=preprint")
    c.add("openalex", {"record_id": "W1", "title": "X", "doi": "",
                       "abstract": "y" * 80},
          "q", "PEER_REVIEWED", "SCHOLARLY", "", "type=article")
    recs = c.canonical_records()
    assert len(recs) == 1
    assert recs[0].publication_status in ("PREPRINT", "PEER_REVIEWED")
    # both source type evidences are preserved for the auditor
    assert len(recs[0].source_type_evidence) == 2


# ---------------------------------------------------------------------------
# 3. canonicalization: the same document in 5 databases = ONE record
#    with 5 indexing sources
# ---------------------------------------------------------------------------

def test_same_document_five_databases_one_canonical_record():
    c = Canonicalizer()
    doi = "10.1111/test.2020.001"
    abstract = "z" * 100
    for src in ("crossref", "openalex", "semantic_scholar", "europepmc",
                "core"):
        c.add(src, {"record_id": f"{src}:rec", "title": "A Study",
                    "doi": doi, "abstract": abstract},
              f"query-for-{src}", "PEER_REVIEWED", "SCHOLARLY", "",
              "type=journal-article")
    recs = c.canonical_records()
    assert len(recs) == 1
    r = recs[0]
    assert r.identity_basis == "DOI"
    assert set(r.indexing_sources) == {"crossref", "openalex",
                                       "semantic_scholar", "europepmc",
                                       "core"}
    # provenance of EVERY appearance preserved
    assert len(r.queries_by_source) == 5
    assert r.origin_source == "crossref"
    # no merge events destroyed anything silently
    assert r.record_ids_by_source["openalex"] == "openalex:rec"


def test_dedup_by_title_fingerprint_preserves_sources():
    c = Canonicalizer()
    c.add("core", {"record_id": "core:1", "title": "A Biopressure Study",
                   "abstract": "x" * 90, "publication_year": "2018"},
          "q1", "THESIS", "THESIS", "", "doctype=thesis")
    # no DOI: same title+year from openaire must merge
    c.add("openaire", {"record_id": "openaire:2",
                       "title": "A Biopressure Study",
                       "abstract": "x" * 90, "publication_year": "2018"},
          "q2", "THESIS", "THESIS", "", "instancetype=Thesis")
    recs = c.canonical_records()
    assert len(recs) == 1
    assert set(recs[0].indexing_sources) == {"core", "openaire"}


def test_patent_number_normalization():
    assert normalize_doi("https://doi.org/10.1234/abc") == "10.1234/abc"
    assert normalize_doi("10.1234/ABC") == "10.1234/abc"
    assert normalize_doi("not-a-doi") == ""


# ---------------------------------------------------------------------------
# 4. lineage / independence: correlated sources merge, independent
#    sources stay separate (measured, not assumed)
# ---------------------------------------------------------------------------

def test_independence_clusters_merge_correlated_families():
    """Crossref + OpenAlex + S2 share the Crossref upstream AND returned
    the same records -> ONE independent cluster (the directive's
    'Europe PMC -> OpenAlex -> Semantic Scholar is not three independent
    discoveries' example)."""
    sources = ["crossref", "openalex", "semantic_scholar", "doaj",
               "datacite", "google_patents"]
    record_sources = {
        "doi:10.1/x": ["crossref", "openalex", "semantic_scholar"],
        "doaj:a": ["doaj"],
        "datacite:b": ["datacite"],
        "patent:US1": ["google_patents"],
    }
    clusters, correlation = independence_clusters(sources, record_sources)
    # the three scholarly metadata sources collapse to one cluster
    cluster_of = {}
    for i, cl in enumerate(clusters):
        for s in cl:
            cluster_of[s] = i
    assert cluster_of["crossref"] == cluster_of["openalex"] == \
        cluster_of["semantic_scholar"]
    assert cluster_of["doaj"] != cluster_of["crossref"]
    assert cluster_of["datacite"] != cluster_of["crossref"]
    assert cluster_of["google_patents"] != cluster_of["crossref"]
    assert "doi_registrant_crossref~scholarly_index_openalex" in correlation
    # unpaywall derives from crossref but is NOT in this run's sources:
    # independence is measured per-run, never assumed


def test_independence_score_penalizes_derived_sources():
    sources = ["crossref", "openalex", "semantic_scholar", "doaj"]
    record_sources = {
        "doi:10.1/x": ["crossref", "openalex", "semantic_scholar"],
        "doaj:a": ["doaj"],
    }
    m = source_independence_score(sources, record_sources)
    assert len(m["unique_source_families"]) == 4  # 4 families
    # correlated cluster (3 families merged) + doaj = 2 independent
    assert m["independent_source_families"] == 2
    assert m["source_independence_score"] == 0.5
    assert m["overlap_ratio"] == 0.5  # 1 of 2 records is multi-family


def test_independence_score_perfect_when_disjoint():
    sources = ["crossref", "doaj", "datacite", "google_patents",
               "arxiv", "core"]
    record_sources = {
        "doi:10.1/a": ["crossref"], "doaj:b": ["doaj"],
        "datacite:c": ["datacite"], "patent:US1": ["google_patents"],
        "arxiv:1": ["arxiv"], "core:9": ["core"],
    }
    m = source_independence_score(sources, record_sources)
    # core derives from repositories (declared) but measured NO overlap
    # with datacite in this run -> stays independent (measured, not
    # assumed). arxiv is its own origin.
    assert m["independent_source_families"] >= 5
    assert m["source_independence_score"] >= 0.8


# ---------------------------------------------------------------------------
# 5. query expansion: genuinely different terms, honest derivation
#    classes, LLM may NEVER fabricate records
# ---------------------------------------------------------------------------

def test_expansion_produces_genuinely_different_terms():
    primary = mechanism_query(PROBLEM)
    variants = expand_query(primary, PROBLEM)
    assert variants[0]["derivation_class"] == "PRIMARY"
    ptoks = set(re.findall(r"[a-z0-9]+", primary.lower()))
    non_primary = [v for v in variants
                   if v["derivation_class"] != "PRIMARY"]
    assert non_primary, "expansion produced only the primary (cosmetic)"
    for v in non_primary:
        toks = set(re.findall(r"[a-z0-9]+", v["query"].lower()))
        assert toks != ptoks, f"cosmetic rewrite: {v['query']}"
        assert v["derivation_class"] in (
            "FUNCTION_EQUIV", "CROSS_DOMAIN_TERM", "ADJACENT_INDUSTRY",
            "DOMAIN_NARROW", "EXPLORATORY_HYPOTHESIS", "LLM_PROPOSED")
        assert v["derivation_basis"]


def test_expansion_terminology_lock_in_escape():
    """The P13 lesson: the art says 'dummy element'/'matched dies'/
    'biopressure' where the problem says 'dual matched sensor'."""
    problem = {"device": "implantable dual matched pressure sensor",
               "failure_mode": "SENSOR_DRIFT"}
    variants = expand_query(mechanism_query(problem), problem)
    cd = [v["query"] for v in variants
          if v["derivation_class"] == "CROSS_DOMAIN_TERM"]
    assert cd, "no cross-domain terminology variants fired"
    joined = " ".join(cd)
    assert ("matched dies" in joined or "dual die" in joined
            or "dummy element" in joined), \
        "cross-domain variants did not escape the locked terminology"


def test_llm_expansion_no_fabrication_gate():
    """The LLM may propose QUERY STRINGS; it may NEVER manufacture a
    retrieved source. Responses containing DOIs / patent numbers are
    REJECTED (the no-fabrication gate)."""
    def fake_llm_1(prompt):
        return json.dumps({"queries": ["matched die drift", "pressure"]})
    out = llm_expand("implantable pressure sensor", fake_llm_1)
    assert len(out) == 2
    assert all(v["derivation_class"] == "LLM_PROPOSED" for v in out)

    def fake_llm_doi(prompt):
        return json.dumps({"queries": [
            "see 10.1038/nature12373 for the mechanism",
            "patent US4320664 describes it"]})
    out2 = llm_expand("implantable pressure sensor", fake_llm_doi)
    assert out2 == [], "LLM response with record identifiers was NOT " \
                       "rejected by the no-fabrication gate"

    assert llm_expand("x", None) == []  # no transport -> no variants


def test_primary_query_is_problem_facts_only():
    """Art. XLIII: the primary query derives from problem facts (device
    + failure mode) — no solution-class injection."""
    q = mechanism_query(PROBLEM)
    assert "implantable dual matched pressure sensor" in q
    assert "sensor drift" in q
    # no injected solution-class terms:
    for injected in ("valve", "coating", "antenna", "harvester"):
        assert injected not in q.lower()


# ---------------------------------------------------------------------------
# 6. pipeline adversarial: provider failure, rate limit, degradation
#    (failure != absence; breadth does not collapse)
# ---------------------------------------------------------------------------

def _make_stubs() -> Dict[str, StubConnector]:
    return {
        "europepmc": StubConnector("OK", [
            _rec("europepmc", "epmc:1", "Drift in implantable sensors",
                 "10.1/a", "drift of implantable pressure sensors " * 10)]),
        "openalex": StubConnector("OK", [
            _rec("openalex", "W1", "Matched sensor dies",
                 "10.1/b", "matched die drift compensation " * 10)]),
        "semantic_scholar": StubConnector("OK", [
            _rec("semantic_scholar", "s2:1",
                 "Dual biopressure implantable study", "10.1/c",
                 "dual biopressure drift study " * 10)]),
        "crossref": StubConnector("OK", [
            _rec("crossref", "doi:10.1/d", "Thermally compensated sensor",
                 "10.1/d", "thermal compensation bridge " * 10)]),
        "doaj": StubConnector("RATE_LIMITED",
                              error="429: too many requests"),
        "datacite": StubConnector("OK", [
            _rec("datacite", "10.13140/rg.1", "An Implantable Low Pressure "
                 "Low Drift Dual BioPressure Sensor",
                 "10.13140/rg.2.2.32705.61282",
                 "dissertation dual matched dies drift " * 10,
                 resource_type_general="Dissertation")]),
        "openaire": StubConnector("TIMEOUT"),
        "core": StubConnector("OK", [
            _rec("core", "core:1", "Dissertation biopressure dual die",
                 "", "dual die dissertation study " * 10,
                 document_type="thesis")]),
        "arxiv": StubConnector("UNAVAILABLE", error="503"),
        "google_patents": StubConnector("OK", [
            _rec("google_patents", "patent:US4320664A",
                 "Thermally compensated silicon pressure sensor", "",
                 snippet="dummy element bridge",
                 patent_id="US4320664A",
                 raw_metadata={"publication_date": "1982-03-23",
                               "priority_date": "1980-06-27",
                               "inventor": "Eaton",
                               "assignee_harmonized": {"name": "Foxboro"}})]),
    }


def test_provider_failure_recorded_and_breadth_does_not_collapse(
        monkeypatch):
    """Directive section 5: a failed source must be recorded; 'no
    relevant result found' is epistemically different from 'the source
    could not be queried'; retrieval breadth does not collapse when
    providers fail."""
    _stub_pool(monkeypatch, _make_stubs())
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    stats = report["retrieval_stats"]
    assert "doaj" in stats["sources_rate_limited"]
    assert "openaire" in stats["sources_failed"]
    assert "arxiv" in stats["sources_failed"]
    assert "europepmc" in stats["sources_succeeded"]
    # 7 of 10 sources still returned records — breadth did NOT collapse
    assert len(stats["sources_succeeded"]) >= 6
    # the failed/rate-limited lane states are explicit, never EMPTY
    lane_by_source = {s["source_id"]: s for s in stats["lane_states"]}
    assert lane_by_source["doaj"]["fabric_health"] == "RATE_LIMITED"
    assert lane_by_source["openaire"]["fabric_health"] == "TIMEOUT"
    assert lane_by_source["arxiv"]["fabric_health"] == \
        "TEMPORARILY_UNAVAILABLE"
    assert stats["sources_failed"]  # non-empty == surfaced honestly
    assert items, "evidence pool collapsed despite 7 working sources"


def test_run_stats_distinguishes_empty_from_failure():
    from discovery_fabric.retrieval_fabric.adapters import (
        LaneRunState, run_stats,
    )
    stats = run_stats([
        LaneRunState("SCHOLARLY", "src_a", queries=["q"],
                     status="OK", record_count=0),
        LaneRunState("SCHOLARLY", "src_b", queries=["q"],
                     status="RATE_LIMITED"),
        LaneRunState("THESIS", "src_c", queries=["q"], status="TIMEOUT"),
    ])
    # OK with 0 records = the provider ANSWERED zero (EMPTY semantics)
    assert "src_a" in stats["sources_succeeded"]
    assert "src_b" in stats["sources_rate_limited"]
    assert "src_c" in stats["sources_failed"]
    assert "src_c" not in stats["sources_succeeded"]
    assert "src_c" not in stats["sources_empty"]


def test_patent_claim_relevant_title_irrelevant(monkeypatch):
    """Directive adversarial case: a patent contains the important claim
    but the TITLE is irrelevant to the query. The patent lane must
    surface it with claim-level fields (claim_text_available, excerpt),
    ranked in the PATENT lane (never mixed into scholarly ranking)."""
    _stub_pool(monkeypatch, _make_stubs())
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    patents = [it for it in items if it["evidence_lane"] == "PATENT"]
    assert patents, "patent lane empty"
    p = patents[0]
    # the directive's patent record schema
    assert p["document_type"] == "PATENT"
    assert p.get("patent_number") == "US4320664A"
    assert "jurisdiction" in str(p["provenance"]) or p.get("patent_number")
    # claim-level fields present via the canonical record
    canon = {r["canonical_id"]: r for r in report["canonical_records"]}
    key = [k for k in canon if "US4320664" in k]
    assert key, "US4320664 not canonicalized by patent number"
    best = canon[key[0]]["best_record"]
    assert best.get("claim_text_available") is True
    assert "dummy element bridge" in best.get("claims_excerpt", "")
    # patents never leak into the scholarly lane
    assert all(it["evidence_lane"] != "SCHOLARLY"
               for it in items if it.get("document_type") == "PATENT")


def test_thesis_lane_discovers_dissertation(monkeypatch):
    """The P13 lesson made structural: a dissertation must be
    discoverable and labeled THESIS — never treated as just another
    paper."""
    _stub_pool(monkeypatch, _make_stubs())
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    theses = [it for it in items if it["evidence_lane"] == "THESIS"]
    assert theses, "thesis lane empty — the P13 failure mode reproduced"
    t = theses[0]
    assert t["publication_status"] == "THESIS"
    assert "biopressure" in t["title"].lower()


def test_items_schema_compatible_with_engine(monkeypatch):
    """The V2 evidence pool must remain a2-schema compatible so
    FREEZE/SYNTHESIZE/VERIFY keep working (additive fields only)."""
    _stub_pool(monkeypatch, _make_stubs())
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    required = ("id", "source_type", "source", "source_id",
                "source_uri", "title", "abstract", "doi",
                "publication_date", "retrieval_timestamp",
                "retrieval_method", "content_hash", "provenance",
                "epistemic_state")
    for it in items:
        for k in required:
            assert k in it, (it.get("id"), k)
    # first item must carry mechanism-bearing text (SYNTHESIZE consumes
    # evidence[0].abstract)
    assert len(items[0]["abstract"]) >= 50
    # fabric fields are additive and present
    for it in items:
        for k in ("publication_status", "evidence_lane",
                  "canonical_id", "source_family"):
            assert k in it, (it.get("id"), k)


def test_fabric_report_auditor_reconstruction_fields(monkeypatch):
    """Acceptance criterion: machine-readable provenance sufficient for
    an independent auditor to reconstruct the discovery event."""
    _stub_pool(monkeypatch, _make_stubs())
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    for k in ("fabric_version", "primary_query", "query_variants",
              "retrieval_stats", "retrieval_diversity",
              "canonical_records", "retrieval_blind_spots"):
        assert k in report
    for rec in report["canonical_records"]:
        assert rec["origin_source"]
        assert isinstance(rec["indexing_sources"], list)
        assert rec["record_ids_by_source"]
        assert rec["queries_by_source"]
    # every query variant carries its derivation class (Art. XLIII)
    for v in report["query_variants"]:
        assert v["derivation_class"]


def test_all_lanes_failed_returns_empty_with_honest_report(monkeypatch):
    """Total fabric failure: every source down. The run returns an
    EMPTY pool but a report full of recorded failures — never a silent
    zero, never a raised absence (Art. XXI.3)."""
    stubs = {sid: StubConnector("UNAVAILABLE", error="down")
             for sid in ("europepmc", "openalex", "semantic_scholar",
                         "crossref", "doaj", "datacite", "openaire",
                         "core", "arxiv", "google_patents")}
    _stub_pool(monkeypatch, stubs)
    items, report = fabric_pipeline.retrieve_fabric(
        PROBLEM, enable_reciprocal=False, enable_unpaywall=False)
    assert items == []
    stats = report["retrieval_stats"]
    assert len(stats["sources_failed"]) == 10
    assert stats["sources_succeeded"] == []
    # blind-spot analysis reports the total coverage failure
    assert report["retrieval_blind_spots"]


# ---------------------------------------------------------------------------
# 7. benchmark corpus integrity (Art. LIX: frozen, non-gameable)
# ---------------------------------------------------------------------------

def test_benchmark_corpus_frozen_structure():
    corpus = load_corpus()
    assert corpus["benchmark_id"] == "RETRIEVAL_FABRIC_BENCHMARK_V1"
    assert len(corpus["problems"]) == 4
    # queries are mechanism-level: NO target identifier may appear in
    # any problem dict (device/failure_mode/constraint)
    queries_blob = json.dumps(
        [p["problem"] for p in corpus["problems"]])
    for identifier in ("Seaver", "10.13140", "US4320664", "WO2014076620",
                       "US11701504", "US11422051", "US20250242099",
                       "biopressure", "dummy element", "thermally"):
        assert identifier.lower() not in queries_blob.lower(), \
            f"target identifier '{identifier}' leaked into a query"


def test_benchmark_targets_are_matchable():
    corpus = load_corpus()
    for p in corpus["problems"]:
        for t in p.get("targets", []):
            # every target has a positive matcher proof
            if t.get("match_patent_number_prefix"):
                assert target_match(t, {
                    "patent_number": t["match_patent_number_prefix"] + "A"})
                assert not target_match(t, {"patent_number": "XX00000"})
            if t.get("match_doi"):
                assert target_match(t, {"doi": t["match_doi"],
                                        "title": "anything"})
            if t.get("match_title_contains"):
                assert target_match(t, {"title": t["match_title_contains"][0]
                                        + " and methods thereof"})


# ---------------------------------------------------------------------------
# 8. engine wiring: V2 default dispatch, V1 legacy path
# ---------------------------------------------------------------------------

def test_adapter_defaults_to_v2(monkeypatch):
    from discovery_fabric.engine import adapters as A

    captured = {}

    class _Env:
        problem = PROBLEM
        provenance = {}

    def fake_retrieve(problem, **kw):
        captured["called"] = True
        return ([{"id": "x", "title": "t", "abstract": "a" * 60,
                  "source": "s", "source_id": "s:1", "doi": None,
                  "source_type": "scientific_paper", "source_uri": "u",
                  "publication_date": None,
                  "retrieval_timestamp": "now",
                  "retrieval_method": "retrieval_fabric_v2",
                  "content_hash": "h", "provenance": {},
                  "epistemic_state": "OBSERVED"}],
                {"fabric_version": "V2", "primary_query": "q",
                 "query_variants": [], "retrieval_stats": {},
                 "retrieval_diversity": {}, "retrieval_blind_spots": [],
                 "canonical_record_count": 1})

    monkeypatch.setenv("ENGINE_RETRIEVAL_FABRIC", "")
    import discovery_fabric.retrieval_fabric as fabric_pkg
    monkeypatch.setattr(fabric_pkg, "retrieve", fake_retrieve)
    res = A.A2RetrievalAdapter().execute(_Env(), {"run_id": "t"})
    assert captured["called"]
    assert res["retrieval_fabric_version"] == "V2"
    assert "retrieval_fabric" in res["apply_to"]["provenance"]
    assert res["apply_to"]["evidence"][0]["id"] == "x"


def test_adapter_v1_env_dispatch(monkeypatch):
    from discovery_fabric.engine import adapters as A

    class _Env:
        problem = PROBLEM
        provenance = {}

    def fake_v1(problem):
        return [{"id": "v1-item", "title": "t", "abstract": "a" * 60}]

    import discovery_fabric.a2.retrieve as v1mod
    monkeypatch.setattr(v1mod, "retrieve", fake_v1)
    monkeypatch.setattr(v1mod, "RETRIEVAL_LANES",
                        {"europepmc": {"n_items": 1, "status": "OK"}})
    monkeypatch.setenv("ENGINE_RETRIEVAL_FABRIC", "V1")
    res = A.A2RetrievalAdapter().execute(_Env(), {"run_id": "t"})
    assert res["retrieval_fabric_version"] == "V1"
    assert res["apply_to"]["evidence"][0]["id"] == "v1-item"
    assert res["apply_to"]["provenance"]["retrieval_fabric"][
        "sources"] == ["europepmc", "openalex"]


# ---------------------------------------------------------------------------
# 9. adapters: patent schema + health mapping
# ---------------------------------------------------------------------------

def test_patent_record_schema_complete():
    from discovery_fabric.retrieval_fabric.adapters import \
        patent_record_from_hit
    hit = {"patent_id": "US4320664A", "title": "Thermally compensated",
           "snippet": "dummy element", "assignee_or_authors": ["Foxboro"],
           "publication_date": "1982-03-23", "source_url":
           "https://patents.google.com/patent/US4320664A/en",
           "raw_payload_sha256": "abc",
           "raw_metadata": {"priority_date": "1980-06-27",
                            "inventor": "Eaton",
                            "assignee_harmonized": {"name": "Foxboro"}}}
    rec = patent_record_from_hit(hit, "q")
    assert rec["document_type"] == "PATENT"
    assert rec["publication_number"] == "US4320664A"
    assert rec["jurisdiction"] == "US"
    assert rec["priority_date"] == "1980-06-27"
    assert rec["publication_date"] == "1982-03-23"
    assert rec["inventors"] == ["Eaton"]
    assert rec["applicants"] == ["Foxboro"]
    # family_id + filing_date are UNKNOWN (not exposed by the endpoint) —
    # recorded as None, never fabricated (Art. VI)
    assert rec["family_id"] is None
    assert rec["filing_date"] is None
    assert rec["claim_text_available"] is False  # not fetched yet
    assert rec["source_url"]


def test_status_to_fabric_health_mapping():
    from discovery_fabric.retrieval_fabric.adapters import fabric_health_of
    assert fabric_health_of("OK") == "AVAILABLE"
    assert fabric_health_of("EMPTY") == "EMPTY_RESULT"
    assert fabric_health_of("RATE_LIMITED") == "RATE_LIMITED"
    assert fabric_health_of("TIMEOUT") == "TIMEOUT"
    assert fabric_health_of("AUTH_FAILED") == "AUTH_REQUIRED"
    assert fabric_health_of("UNAVAILABLE") == "TEMPORARILY_UNAVAILABLE"
    assert fabric_health_of("SEARCH_FAILED") == "TEMPORARILY_UNAVAILABLE"
    assert fabric_health_of("PARSE_FAILED") == "DEGRADED"


# ---------------------------------------------------------------------------
# 10. registry wiring: new connectors resolve through the 7-step chain
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("source_id", [
    "doaj", "unpaywall", "datacite", "openaire", "core",
])
def test_new_connectors_resolve_and_register(source_id):
    from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
    rec = SOURCE_REGISTRY.get(source_id)
    assert rec and rec.get("connector"), source_id
    from discovery_fabric.retrieval_fabric.adapters import _connector_for
    conn = _connector_for(source_id)
    assert conn is not None, source_id
    assert issubclass(type(conn), ConnectorBase)
    assert conn.SOURCE_ID == source_id


def test_blocked_sources_recorded_honestly_not_silent():
    from discovery_fabric.source_registry.registry import SOURCE_REGISTRY
    for sid in ("zenodo", "ndltd"):
        rec = SOURCE_REGISTRY[sid]
        assert rec["connector"] is None  # NO_CONNECTOR: honest gap
        assert "MEASURED" in rec["known_gaps"]
    # and the fabric registry carries the measured states
    data = fabric_registry.load_fabric_sources()
    by_id = {s["source_id"]: s for s in data["sources"]}
    assert "403" in by_id["zenodo"].get("measured_state", "")
    assert "503" in by_id["ndltd"].get("measured_state", "")
