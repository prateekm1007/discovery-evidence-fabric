#!/usr/bin/env python3
"""R499 — hermetic invariants of the two free evidence legs (Art. LXXV).

Leg A — HF USPTO corpus transport (Tier-3 discovery; free, anonymous).
Leg B — EPO Linked Open Data transport (identity/family/primary docs).

Pins:
  1. LXXV custody fields: the five fields, COMPLETE vs PROVENANCE_INCOMPLETE
     typing, unknown-family typed UNKNOWN (never silently dropped);
  2. HF leg: row->hit mapping (structured id, license, custody embedded);
     INDEX_WARMING_TRANSIENT / RATE_LIMITED / SCHEMA_MISMATCH typed per call;
     /rows deterministic retrieval; zero-hit never typed absence;
  3. EPO LOD leg: URI shape (trailing dash — the R498 406 lesson); identity
     parsing from the REAL measured fixture; NOT_IN_GRAPH is a coverage state
     with the never-absence note; QUERY_COST_TIMEOUT typed; family chain
     (application->simple-family->members); NO_FAMILY_TRIPLE_IN_GRAPH typed;
     primary-document fetch byte-binding fields + non-EPO origin rejected;
  4. wiring: HF_USPTO_CORPUS joins the search ladder; EPO LOD exposed as a
     VERIFICATION source (not a keyword-search provider); registry v1.1.0
     carries the R499 measured states.

All network calls are monkeypatched — hermetic (no live round-trip here; the
live proofs live in R499/R499_FREE_LEGS_LIVE_PROOF.json, and a single green
run seals nothing — the repetition rule).
"""
import json
import os
import sys

import pytest

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, REPO)

from discovery_fabric.prior_art_v2 import free_evidence_sources as fes  # noqa: E402
from discovery_fabric.prior_art_v2 import sources as src  # noqa: E402

REG = os.path.join(REPO, "PATENT_SOURCE_REGISTRY.json")


# ----------------------- fixtures: REAL measured payloads (R499) -----------------------
HF_ROW = {
    "id": "US-71623224-A",
    "text": "Wrench\n\nPatented Nov. 24, 1925.\n1 UNITED STATES PATENT OFFICE.",
    "added": "2024-03-22",
    "created": "1924-05-27",
    "source": "USPTO-Google Patents Public Data",
    "metadata": {"license": "Creative Commons - Attribution - https://creativecommons.org/licenses/by/4.0/",
                 "language": "en", "publication_date": "1925-11-24"},
}

# the REAL identity bindings measured for EP/0084638/A1 at the live endpoint (R499)
EPO_IDENTITY_BINDINGS = [
    {"p": "http://www.w3.org/1999/02/22-rdf-syntax-ns#type", "o": {"type": "uri", "value": "http://data.epo.org/linked-data/def/patent/Publication"}},
    {"p": "http://www.w3.org/2000/01/rdf-schema#label", "o": {"type": "literal", "value": "EP 0084638 A1"}},
    {"p": "http://data.epo.org/linked-data/def/patent/publicationAuthority", "o": {"type": "uri", "value": "http://data.epo.org/linked-data/id/st3/EP"}},
    {"p": "http://data.epo.org/linked-data/def/patent/publicationDate", "o": {"type": "literal", "value": "1983-08-03"}},
    {"p": "http://data.epo.org/linked-data/def/patent/publicationKind", "o": {"type": "uri", "value": "http://data.epo.org/linked-data/def/patent/publicationKind_A1"}},
    {"p": "http://data.epo.org/linked-data/def/patent/publicationNumber", "o": {"type": "literal", "value": "0084638"}},
    {"p": "http://data.epo.org/linked-data/def/patent/titleOfInvention", "o": {"type": "literal", "value": "Dispenser for pasty products"}},
    {"p": "http://purl.org/dc/terms/abstract", "o": {"type": "literal", "value": "Ein Spender fuer pastoese Produkte..."}},
    {"p": "http://data.epo.org/linked-data/def/patent/application", "o": {"type": "uri", "value": "http://data.epo.org/linked-data/id/application/EP/82111372"}},
    {"p": "http://data.epo.org/linked-data/def/patent/priority", "o": {"type": "uri", "value": "http://data.epo.org/linked-data/id/application/DE/3223267"}},
    {"p": "http://data.epo.org/linked-data/def/patent/citesPatentPublication", "o": {"type": "uri", "value": "http://data.epo.org/linked-data/data/publication/US/3268123/A/-"}},
    {"p": "http://data.epo.org/linked-data/def/patent/representation", "o": {"type": "uri", "value": "https://data.epo.org/linked-data/representation/publication/EP/0084638/NWA1.xml"}},
]


def _sparql_json(bindings):
    return {"head": {"vars": ["p", "o"]},
            "results": {"bindings": [
                {"p": {"type": "uri", "value": b["p"]}, "o": b["o"]} for b in bindings]}}


def _mk_http(monkeypatch, status_by_url):
    def fake_get(url, headers=None, timeout=30, max_bytes=0):
        for frag, (status, body) in status_by_url.items():
            if frag in url:
                return status, (body if isinstance(body, bytes) else json.dumps(body).encode()), 12
        return 404, b"{}", 12
    monkeypatch.setattr(fes, "_http_get", fake_get)


# ----------------------- 1. LXXV custody fields -----------------------

def test_custody_complete_has_all_five_fields():
    c = fes.make_custody(source="X", endpoint="https://e", query="q", retrieved_at_utc="now",
                         publication_number="EP0084638", kind_code="A1",
                         application_reference="app", family_uri="fam", family_members=["a"],
                         publication_date="1983-08-03")
    for f in fes.CUSTODY_FIELDS:
        assert f in c
    assert fes.custody_completeness(c) == {"state": "COMPLETE", "missing": []}


def test_custody_missing_family_typed_incomplete():
    c = fes.make_custody(source="X", endpoint="e", query="q", retrieved_at_utc="now",
                         publication_number="EP0084638", kind_code="A1",
                         application_reference="app", publication_date="1983-08-03")
    # family unknown and not declared -> the field is empty -> PROVENANCE_INCOMPLETE
    cc = fes.custody_completeness(c)
    assert cc["state"] == "PROVENANCE_INCOMPLETE"
    assert "family_relationship" in cc["missing"]


def test_custody_unknown_family_typed_not_missing():
    c = fes.make_custody(source="X", endpoint="e", query="q", retrieved_at_utc="now",
                         publication_number="EP0084638", kind_code="A1",
                         application_reference="app", publication_date="1983-08-03")
    # an explicit knowledge boundary: family_basis UNKNOWN (declared, not silent)
    c["family_relationship"]["family_basis"] = "UNKNOWN"
    cc = fes.custody_completeness(c)
    assert cc["state"] == "COMPLETE"


def test_custody_none_typed_incomplete_with_all_fields():
    cc = fes.custody_completeness(None)
    assert cc["state"] == "PROVENANCE_INCOMPLETE"
    assert set(cc["missing"]) == set(fes.CUSTODY_FIELDS)


# ----------------------- 2. Leg A: HF USPTO corpus -----------------------

def test_hf_search_maps_row_to_hit_with_custody(monkeypatch):
    body = {"rows": [{"row": HF_ROW}], "num_rows_total": 131755}
    _mk_http(monkeypatch, {"datasets-server.huggingface.co/search": (200, body)})
    r = fes.search_hf_uspto("wrench", 5)
    assert r.success and len(r.hits) == 1
    h = r.hits[0]
    assert h.patent_id == "US71623224A"           # structured id normalized
    assert h.source_id == "HF_USPTO_CORPUS"
    assert h.publication_date == "1925-11-24"
    assert "Attribution" in h.raw_metadata["license"]
    cu = h.raw_metadata["custody_lxxv"]
    assert cu["publication_identity"]["publication_number"] == "US71623224"
    assert cu["publication_identity"]["kind_code"] == "A"
    assert cu["provenance"]["source"] == "HF_USPTO_CORPUS"
    assert cu["temporal_status"]["publication_date"] == "1925-11-24"
    # LXXV pin: a Tier-3 corpus discovery hit carries family UNMEASURED ->
    # honestly PROVENANCE_INCOMPLETE: it may DISCOVER, never verify (clause 3)
    cc = fes.custody_completeness(cu)
    assert cc["state"] == "PROVENANCE_INCOMPLETE"
    assert "family_relationship" in cc["missing"]


def test_hf_search_index_warming_typed_transient(monkeypatch):
    body = {"error": "the dataset index is loading, this can take longer than usual"}
    _mk_http(monkeypatch, {"datasets-server.huggingface.co/search": (500, body)})
    r = fes.search_hf_uspto("anything", 5)
    assert not r.success
    assert "INDEX_WARMING_TRANSIENT" in r.error
    assert r.error_code == 500


def test_hf_search_rate_limited_typed(monkeypatch):
    _mk_http(monkeypatch, {"datasets-server.huggingface.co/search": (429, {"error": "slow down"})})
    r = fes.search_hf_uspto("q", 5)
    assert not r.success and r.error == "RATE_LIMITED" and r.error_code == 429


def test_hf_search_schema_mismatch_typed(monkeypatch):
    body = {"rows": [{"row": "a-string-not-an-object"}]}
    _mk_http(monkeypatch, {"datasets-server.huggingface.co/search": (200, body)})
    r = fes.search_hf_uspto("q", 5)
    assert not r.success and "SCHEMA_MISMATCH" in r.error


def test_hf_rows_deterministic_retrieval(monkeypatch):
    body = {"rows": [{"row": HF_ROW}], "num_rows_total": 131755,
            "features": [{"name": "id"}, {"name": "text"}]}
    _mk_http(monkeypatch, {"datasets-server.huggingface.co/rows": (200, body)})
    r = fes.fetch_hf_uspto_rows(offset=0, length=1)
    assert r.success and len(r.hits) == 1
    assert r.rate_limit_remaining == 131755  # carried as a count signal
    assert r.hits[0].raw_metadata["corpus_id"] == "US-71623224-A"


def test_hf_zero_hits_never_typed_absence(monkeypatch):
    body = {"rows": [], "num_rows_total": 131755}
    _mk_http(monkeypatch, {"datasets-server.huggingface.co/search": (200, body)})
    r = fes.search_hf_uspto("xyzzy-not-a-patent-term", 5)
    assert r.success and r.hits == []
    # success-with-zero-hits is a true zero FOR THIS CORPUS ONLY — the typed
    # state lives in the hit-level custody; the caller must never read absence.


def test_hf_corpus_status_ok(monkeypatch):
    body = {"splits": [{"dataset": "common-pile/uspto", "config": "default", "split": "train"}]}
    _mk_http(monkeypatch, {"datasets-server.huggingface.co/splits": (200, body)})
    st = fes.hf_uspto_corpus_status()
    assert st["state"] == "OK"
    assert "never coverage statements" in st["note"]


# ----------------------- 3. Leg B: EPO LOD -----------------------

def test_epo_publication_uri_shape_trailing_dash():
    assert fes.epo_publication_uri("EP", "0084638", "A1") == \
        "http://data.epo.org/linked-data/data/publication/EP/0084638/A1/-"
    # the R498 406 lesson: no trailing dash = a different (UI) resource


def _mk_sparql(monkeypatch, by_query):
    def fake_sparql(query, timeout=45):
        for frag, result in by_query.items():
            if frag in query:
                return result
        return (fes.EPO_STATE_OK, _sparql_json([]), 10, "")
    monkeypatch.setattr(fes, "_sparql", fake_sparql)


def test_epo_identity_parses_measured_fixture(monkeypatch):
    _mk_sparql(monkeypatch, {"?p ?o WHERE { <http://data.epo.org/linked-data/data/publication/EP/0084638/A1/-> ?p ?o":
                             (fes.EPO_STATE_OK, _sparql_json(EPO_IDENTITY_BINDINGS), 30, "")})
    ident = fes.epo_lod_identity("EP", "0084638", "A1")
    assert ident["state"] == "OK"
    assert ident["label"] == "EP 0084638 A1"
    assert ident["publication_date"] == "1983-08-03"
    assert ident["kind_code"] == "A1"
    assert ident["titles"] == ["Dispenser for pasty products"]
    assert ident["applications"] == ["http://data.epo.org/linked-data/id/application/EP/82111372"]
    assert ident["priorities"] == ["http://data.epo.org/linked-data/id/application/DE/3223267"]
    assert ident["citations_count_signal"] == 1
    assert any(u.endswith("NWA1.xml") for u in ident["representations"])
    assert ident["custody_completeness"]["state"] == "COMPLETE"


def test_epo_identity_not_in_graph_is_coverage_state_never_absence(monkeypatch):
    _mk_sparql(monkeypatch, {"US/8968233/B2/-": (fes.EPO_STATE_OK, _sparql_json([]), 20, "")})
    ident = fes.epo_lod_identity("US", "8968233", "B2")
    assert ident["state"] == "NOT_IN_GRAPH"
    assert "never evidence of absence" in ident["note"]


def test_epo_identity_query_cost_timeout_typed(monkeypatch):
    _mk_sparql(monkeypatch, {"EP/0084638/A1/-": (fes.EPO_STATE_QUERY_TIMEOUT, None, 45000, "The read operation timed out")})
    ident = fes.epo_lod_identity("EP", "0084638", "A1")
    assert ident["state"] == "QUERY_COST_TIMEOUT"


def test_epo_family_chain_parses(monkeypatch):
    by = {
        "<http://data.epo.org/linked-data/data/publication/EP/0084638/A1/-> patent:application":
            (fes.EPO_STATE_OK, {"head": {"vars": ["app"]}, "results": {"bindings": [
                {"app": {"type": "uri", "value": "http://data.epo.org/linked-data/id/application/EP/82111372"}}]}}, 20, ""),
        "<http://data.epo.org/linked-data/id/application/EP/82111372> patent:familyMemberOf":
            (fes.EPO_STATE_OK, {"head": {"vars": ["fam"]}, "results": {"bindings": [
                {"fam": {"type": "uri", "value": "http://data.epo.org/linked-data/data/simple-family/25798930"}}]}}, 20, ""),
        "familyMember ?app2":
            (fes.EPO_STATE_OK, {"head": {"vars": ["app2", "pub"]}, "results": {"bindings": [
                {"app2": {"type": "uri", "value": "http://data.epo.org/linked-data/id/application/EP/82111372"},
                 "pub": {"type": "uri", "value": "http://data.epo.org/linked-data/data/publication/EP/0084638/A1/-"}},
                {"app2": {"type": "uri", "value": "http://data.epo.org/linked-data/id/application/EP/82111372"},
                 "pub": {"type": "uri", "value": "http://data.epo.org/linked-data/data/publication/EP/0084638/B1/-"}},
                {"app2": {"type": "uri", "value": "http://data.epo.org/linked-data/id/application/US/45644983"},
                 "pub": {"type": "uri", "value": "http://data.epo.org/linked-data/data/publication/US/4511068/A/-"}},
            ]}}, 25, ""),
    }
    _mk_sparql(monkeypatch, by)
    fam = fes.epo_lod_family_for_publication("EP", "0084638", "A1")
    assert fam["state"] == "OK"
    assert fam["family_uri"] == "http://data.epo.org/linked-data/data/simple-family/25798930"
    assert fam["family_basis"] == "SIMPLE_FAMILY"
    assert fam["family_size_count_signal"] == 2
    assert len(fam["member_publications"]["http://data.epo.org/linked-data/id/application/EP/82111372"]) == 2
    assert fam["custody_completeness"]["state"] == "COMPLETE"


def test_epo_family_no_family_triple_typed_not_absence(monkeypatch):
    by = {
        "patent:application ?app": (fes.EPO_STATE_OK, {"head": {"vars": ["app"]}, "results": {"bindings": [
            {"app": {"type": "uri", "value": "http://data.epo.org/linked-data/id/application/EP/82111372"}}]}}, 20, ""),
        "patent:familyMemberOf": (fes.EPO_STATE_OK, _sparql_json([]), 20, ""),
    }
    _mk_sparql(monkeypatch, by)
    fam = fes.epo_lod_family_for_publication("EP", "0084638", "A1")
    assert fam["state"] == "OK"
    assert fam["family_basis"] == "NO_FAMILY_TRIPLE_IN_GRAPH"
    assert "never absence" in fam["note"]


def test_epo_document_fetch_byte_binding_and_origin_gate(monkeypatch):
    _mk_http(monkeypatch, {"representation/publication/EP/0084638/NWA1.xml": (200, b"<?xml version='1.0'?><doc/>")})
    r = fes.epo_lod_fetch_document("https://data.epo.org/linked-data/representation/publication/EP/0084638/NWA1.xml", 1000)
    assert r["state"] == "OK"
    assert len(r["sha256"]) == 64 and r["size_bytes"] > 0
    assert r["content_type"] == "application/xml"
    # non-EPO origin refused: the verification path never fetches elsewhere
    r2 = fes.epo_lod_fetch_document("https://evil.example.com/doc.xml")
    assert r2["state"] == "REJECTED_NON_EPO_ORIGIN"


# ----------------------- 4. wiring + registry -----------------------

def test_hf_joins_the_search_ladder(monkeypatch):
    monkeypatch.setattr(fes, "search_hf_uspto", lambda q, n=8: src.SourceQueryResult(
        source_id="HF_USPTO_CORPUS", success=True, latency_ms=5, hits=[]))
    res = src.search_all_sources("anything", 3)
    assert "HF_USPTO_CORPUS" in res
    assert res["HF_USPTO_CORPUS"].success


def test_epo_lod_is_verification_not_search_provider():
    status = src.get_source_status()
    assert "EPO_LINKED_OPEN_DATA" in status
    assert "VERIFICATION" in status["EPO_LINKED_OPEN_DATA"]["role"]
    assert "never absence" in status["EPO_LINKED_OPEN_DATA"]["coverage"]
    # and it is deliberately NOT in the search ladder's provider set
    import inspect
    body = inspect.getsource(src.search_all_sources)
    assert "EPO_LINKED_OPEN_DATA" not in body.split('"""')[2].replace("EPO LOD", "@@")  # doc mentions EPO LOD by design
    ladder = [l for l in body.splitlines() if "ex.submit" in l]
    assert len(ladder) == 5 and not any("epo" in l.lower() and "uspto" not in l.lower() for l in ladder)


def test_registry_union_v1_2_0_carries_r499_measurements():
    reg = json.load(open(REG))
    # v1.2.0 = the two-line union (Coder 2's R500 v1.1.0 + Coder 1's R499 v1.1.0)
    assert reg["version"] == "1.2.0"
    s = reg["sources"]
    # EPO LOD: the 406 is superseded by the discovered live endpoint (BOTH lines)
    assert "MEASURED_R499" in s["epo_linked_open_data"]["properties"]["ACCESSIBLE"]
    assert "MEASURED_R500" in s["epo_linked_open_data"]["properties"]["ACCESSIBLE"]
    assert s["epo_linked_open_data"]["measured_state"] == "LIVE_MEASURED"
    # the R500 open item is closed ON THE SPARQL PATH (this line's evidence)
    assert "CLOSED ON THE SPARQL PATH" in s["epo_linked_open_data"]["properties"]["ACCESSIBLE"]
    # HF: datasets-server rows measured
    assert "MEASURED_R499" in s["huggingface_patent_datasets"]["properties"]["ACCESSIBLE"]
    # github recovered this round
    assert "MEASURED_R499" in s["github_patent_infra"]["properties"]["ACCESSIBLE"]
    # epo_ops / uspto_odp anonymous boundaries measured
    assert "MEASURED_R499" in s["epo_ops"]["properties"]["ACCESSIBLE"]
    assert "MEASURED_R499" in s["uspto_open_data_bulk"]["properties"]["ACCESSIBLE"] or \
           "MEASURED_R499" in s["uspto_patent_public_search"]["properties"]["ACCESSIBLE"]


def test_registry_no_absence_claims_introduced():
    reg = json.load(open(REG))
    blob = json.dumps(reg)
    # the R499 states are coverage/typing statements, never absence claims
    assert "NOT_IN_GRAPH" in blob  # typed coverage state, defined
    assert "never absence" in blob or "never evidence of absence" in blob
