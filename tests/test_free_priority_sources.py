"""New free/open priority-source connectors (CEO directive 2026-08-30):
NASA NTRS, DOE OSTI, arXiv, NHTSA recalls.

Hermetic parse/normalize tests against MEASURED payload shapes (fixtures
captured from live probes this session). No network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.connectors.govtech_reports import (
    DoeOstiConnector, NasaNtrsConnector,
)
from discovery_fabric.source_registry.connectors.nonmedical_failure import (
    NhtsaRecallConnector,
)
from discovery_fabric.source_registry.connectors.scientific import ArxivConnector
from discovery_fabric.source_registry.registry import SOURCE_REGISTRY


NTRS_FIXTURE = {"results": [{
    "id": "20190025091", "title": ["Battery Safety Report"],
    "publicationDate": "2019-04-01", "distributionDate": "2019-04-01",
    "subjectCategories": ["ENERGY"], "otherReportNumbers": ["NASA/TM-2019"],
    "copyright": [{"publication": "Public"}],
    "abstracts": [{"abstract": "Thermal runaway analysis with negative findings."}],
}]}

OSTI_FIXTURE = [{
    "osti_id": "3413920", "title": "Ionic Liquids Study ",
    "doi": "https://doi.org/10.2172/3413920",
    "publication_date": "2027-09-01T00:00:00Z",
    "product_type": "Technical Report",
    "authors": ["Doe, Jane [SNL]"], "research_orgs": ["Sandia"],
}]

ARXIV_FIXTURE = b"""<?xml version='1.0' encoding='UTF-8'?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/2110.02266v1</id>
    <title>  Flow   around   stents </title>
    <summary>Fluid dynamics of flow diverters.</summary>
    <published>2021-10-05T00:00:00Z</published>
    <updated>2021-10-05T00:00:00Z</updated>
    <author><name>A. Author</name></author>
    <arxiv:primary_category term="physics.flu-dyn"/>
    <link title="pdf" href="http://arxiv.org/pdf/2110.02266v1"/>
  </entry>
</feed>"""

NHTSA_FIXTURE = {"Count": 1, "Message": "ok", "results": [{
    "Manufacturer": "Toyota", "NHTSACampaignNumber": "20V682000",
    "Component": "FUEL SYSTEM, GASOLINE", "ReportReceivedDate": "2020-11-13",
    "Summary": "Fuel pump may fail.", "Conequence": "Engine stall.",
    "Remedy": "Dealer will replace pump.",
}]}


def test_ntrs_normalize():
    conn = NasaNtrsConnector()
    recs = conn.normalize_payload(json.loads(json.dumps(NTRS_FIXTURE)), "q", "sha")
    assert len(recs) == 1
    r = recs[0]
    assert r.record_id == "ntrs:20190025091"
    assert r.title == "Battery Safety Report"
    assert "Thermal runaway" in r.normalized["abstract"]
    assert any("NEGATIVE_RESULTS_UNLABELED" in l for l in r.limitations)


def test_osti_normalize_and_doi():
    conn = DoeOstiConnector()
    payload = conn.parse_payload(json.dumps(OSTI_FIXTURE).encode(), "q")
    recs = conn.normalize_payload(payload, "q", "sha")
    assert recs[0].record_id == "osti:3413920"
    assert recs[0].title == "Ionic Liquids Study"  # stripped
    assert recs[0].normalized["doi"] == "10.2172/3413920"


def test_osti_rejects_non_array():
    conn = DoeOstiConnector()
    with pytest.raises(ValueError):
        conn.parse_payload(b'{"error": "not the native shape"}', "q")


def test_arxiv_atom_parse_and_doi():
    conn = ArxivConnector()
    payload = conn.parse_payload(ARXIV_FIXTURE, "q")
    recs = conn.normalize_payload(payload, "q", "sha")
    assert len(recs) == 1
    r = recs[0]
    assert r.record_id == "arxiv:2110.02266v1"
    assert r.title == "Flow around stents"  # whitespace collapsed
    assert r.normalized["doi"] == "10.48550/arxiv.2110.02266"
    assert any("PREPRINT" in l for l in r.limitations)


def test_nhtsa_normalize_failure_domain():
    conn = NhtsaRecallConnector()
    payload = conn.parse_payload(json.dumps(NHTSA_FIXTURE).encode(), "q")
    recs = conn.normalize_payload(payload, "toyota|camry|2020", "sha")
    r = recs[0]
    assert r.record_id == "nhtsa:20V682000"
    assert r.normalized["failure_domain"] == "transport"
    assert r.normalized["defect_summary"].startswith("Fuel pump")
    # FDA-analog limitations are structural
    assert any("NOT an incidence" in l for l in r.limitations)


def test_nhtsa_query_grammar_validation():
    conn = NhtsaRecallConnector()
    assert conn.parse_query("toyota|camry|2020") == {
        "make": "toyota", "model": "camry", "modelYear": "2020"}
    assert conn.parse_query("free text query") is None
    assert conn.parse_query("a|b|notayear") is None
    assert conn.parse_query("a|b|1700") is None


def test_all_four_registered_with_13_fields():
    for sid in ("nasa_ntrs", "doe_osti", "arxiv", "nhtsa_recalls"):
        rec = SOURCE_REGISTRY[sid]
        for f in ("source_id", "name", "authority_role", "coverage",
                  "access_method", "update_frequency", "rate_limits",
                  "licensing", "primary_or_secondary", "freshness",
                  "known_gaps", "provenance_method"):
            assert rec.get(f), (sid, f)
        assert rec["connector"] and "health_status" in rec
