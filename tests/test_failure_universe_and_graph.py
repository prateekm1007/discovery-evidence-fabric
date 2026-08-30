"""Hermetic tests — CEO 2026-08-30 failure-universe + maturity + graph
+ trust-weighting directive.

Covers:
1. failure_universe connectors (fixtures from MEASURED payload shapes)
2. negative-evidence classifier extension (new domains)
3. QUERY_RELEVANCE instrument (threshold, folding, field-binding,
   query-differentiation, structural grammars, battery coverage)
4. trust tiers (CEO #5 — MAUDE never outranks peer review)
5. canonical evidence graph (CEO #4 — fail-closed chain + contradiction
   survival)
6. CDRH standards client-side window rewrite

No network access in this suite (hermetic; live proof is the committed
QUERY_RELEVANCE_PROBES / EVIDENCE_GRAPH_DEMO artifacts).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import query_relevance as qr
from discovery_fabric.source_registry import trust
from discovery_fabric.source_registry.connectors.failure_universe import (
    CpscRecallConnector,
    FraRailAccidentConnector,
    NhtsaComplaintConnector,
    UsgsEarthquakeConnector,
)
from discovery_fabric.source_registry.connectors.standards import (
    FdaRecognizedStandardsConnector,
)
from discovery_fabric.source_registry.evidence_graph import EvidenceGraph
from discovery_fabric.source_registry.negative_evidence import (
    classify_negative_evidence,
)
from discovery_fabric.source_registry.query_relevance import (
    aggregate,
    grade_query_relevance,
)
from discovery_fabric.source_registry.registry import SOURCE_REGISTRY

# ---------------------------------------------------------------------------
# 1. failure-universe connectors (measured payload fixtures)
# ---------------------------------------------------------------------------

NHTSA_COMPLAINT_PAYLOAD = {
    "count": 268,
    "message": "Results returned successfully",
    "results": [
        {
            "odiNumber": 11756265,
            "manufacturer": "Toyota Motor Corporation",
            "crash": False,
            "fire": False,
            "numberOfInjuries": 0,
            "numberOfDeaths": 0,
            "dateOfIncident": "07/30/2026",
            "dateComplaintFiled": "08/11/2026",
            "vin": "4T1C11BK8LU",
            "components": "POWER TRAIN,ELECTRICAL SYSTEM,ENGINE",
            "summary": "The vehicle contains a known manufacturing defect "
                       "where the engine coolant bypass valve cracks.",
        },
        {"odiNumber": 11550001, "manufacturer": "Toyota Motor Corporation",
         "crash": True, "fire": False, "numberOfInjuries": 1,
         "numberOfDeaths": 0, "dateOfIncident": "01/15/2025",
         "dateComplaintFiled": "02/01/2025", "vin": "X",
         "components": "STEERING", "summary": "Steering locked."},
    ],
}


def _records_for(connector, payload, query):
    raw = json.dumps(payload).encode()
    parsed = connector.parse_payload(raw, query)
    import hashlib
    sha = hashlib.sha256(raw).hexdigest()
    return connector.normalize_payload(parsed, query, sha)


def test_nhtsa_complaints_normalize():
    c = NhtsaComplaintConnector()
    recs = _records_for(c, NHTSA_COMPLAINT_PAYLOAD, "toyota|camry|2020")
    assert len(recs) == 2
    r = recs[0]
    assert r.record_id == "nhtsa_odi:11756265"
    assert r.normalized["failure_domain"] == "transport"
    assert r.normalized["report_class"] == "VOLUNTARY_OWNER_REPORT"
    assert any("NOT failure rates" in x for x in r.limitations)
    # grammar: malformed queries are rejected, never guessed
    assert c.parse_query("toyota camry") is None
    assert c.parse_query("toyota|camry|notayear") is None
    assert c.parse_query("toyota|camry|2020") == {
        "make": "toyota", "model": "camry", "modelYear": "2020"}


CPSC_PAYLOAD = [
    {
        "RecallID": 10937, "RecallNumber": "26716",
        "RecallDate": "2026-08-20T00:00:00",
        "Title": "CCM Hybrid Hockey Visors Recalled",
        "Description": "This recall involves the CCM Hybrid Hockey Visors.",
        "Hazards": [{"Name": "Impact Injury"}],
        "Products": [{"Name": "Hockey Visor"}, {"Name": "Battery pack"}],
        "Injuries": [{"Name": "Laceration"}],
        "ManufacturerCountries": [{"Name": "China"}],
        "URL": "https://www.cpsc.gov/Recalls/2026/x",
    },
]


def test_cpsc_normalize():
    c = CpscRecallConnector()
    recs = _records_for(c, CPSC_PAYLOAD, "2026-06-01")
    assert len(recs) == 1
    r = recs[0]
    assert r.record_id == "cpsc:26716"
    assert r.normalized["failure_domain"] == "consumer_products"
    assert "Impact Injury" in (r.normalized["hazards"] or "")
    assert any("NOT an incidence" in x for x in r.limitations)
    assert c.parse_query("not-a-date") is None


USGS_PAYLOAD = {
    "type": "FeatureCollection",
    "metadata": {"count": 2},
    "features": [
        {"id": "us6000abcd", "type": "Feature",
         "geometry": {"coordinates": [142.5, 38.2, 47.0]},
         "properties": {"mag": 6.1, "place": "68 km E of Namie, Japan",
                        "time": 1754000000000, "url": "https://earthquake.usgs.gov/x",
                        "tsunami": 0, "felt": 12, "alert": "green",
                        "magType": "mww"}},
    ],
}


def test_usgs_normalize():
    c = UsgsEarthquakeConnector()
    recs = _records_for(c, USGS_PAYLOAD, "2026-07-01")
    r = recs[0]
    assert r.record_id == "usgs:us6000abcd"
    assert r.normalized["magnitude"] == 6.1
    assert r.normalized["report_class"] == "INSTRUMENT_MEASURED_EVENT"
    assert any("NOT an engineering-failure record" in x for x in r.limitations)


FRA_PAYLOAD = [
    {"reportingrailroadname": "Delaware & Hudson Railway Company",
     "accidentnumber": "220316", "accidenttype": "Derailment",
     "date": "2010-06-12T00:00:00.000", "accidentyear": "10",
     "accidentmonth": "06", "accidentcausecode": "T110",
     "accidentcause": "Track alignment", "state": "OH",
     "countyname": "Cuyahoga", "fatalities": "0", "injured": "2",
     "derailedemptyfreightcars": "3", "derailedloadedfreightcars": "4",
     "trainspeed": "25",
     "url": {"url": "https://safetydata.fra.dot.gov/x"}},
]


def test_fra_normalize():
    c = FraRailAccidentConnector()
    recs = _records_for(c, FRA_PAYLOAD, "2023-01-01")
    r = recs[0]
    assert r.role == "INCIDENT"
    assert r.normalized["derailed_cars_total"] == 7
    assert r.normalized["cause_code"] == "T110"
    assert any("not proven root causes" in x for x in r.limitations)


# ---------------------------------------------------------------------------
# 2. negative-evidence classifier — new failure universe
# ---------------------------------------------------------------------------

def _rec(sid, role, normalized):
    return {"source_id": sid, "record_id": f"{sid}:x", "role": role,
            "normalized": normalized, "limitations": []}


def test_classifier_transport_complaint():
    out = classify_negative_evidence(_rec(
        "nhtsa_complaints", "ADVERSE_EVENT",
        {"odi_number": 11756265, "components": "ELECTRICAL SYSTEM"}))
    assert out["evidence_class"] == "ADVERSE_EVENT_SIGNAL"
    assert out["failure_domain"] == "transport"


def test_classifier_cpsc():
    out = classify_negative_evidence(_rec(
        "cpsc_recalls", "RECALL", {"recall_number": "26716"}))
    assert out["evidence_class"] == "RECALL_EVENT"
    assert out["failure_domain"] == "consumer_products"


def test_classifier_fra():
    out = classify_negative_evidence(_rec(
        "fra_rail_accidents", "INCIDENT", {"accident_number": "220316"}))
    assert out["evidence_class"] == "INCIDENT_REPORT"
    assert out["failure_domain"] == "industrial_transport"


def test_classifier_usgs_is_not_negative_evidence():
    out = classify_negative_evidence(_rec(
        "usgs_earthquakes", "HAZARD_EVENT", {"event_id": "x", "magnitude": 6.1}))
    assert out["evidence_class"] == "NONE"  # hazard input, NOT a failure


# ---------------------------------------------------------------------------
# 3. QUERY_RELEVANCE instrument
# ---------------------------------------------------------------------------

def test_adjudicator_single_term_threshold():
    rec = {"record_id": "x", "title": "Aspirin mechanism review",
           "normalized": {}}
    a = qr.adjudicate_record(rec, "aspirin")
    assert a["relevance"] == "RELEVANT"  # 1-term query needs 1 overlap


def test_adjudicator_plural_folding():
    rec = {"record_id": "x",
           "title": "Zinc batteries for grid-scale energy storage",
           "normalized": {}}
    a = qr.adjudicate_record(rec, "battery storage")
    assert a["relevance"] == "RELEVANT"  # batteries -> battery


def test_adjudicator_field_binding():
    rec = {"record_id": "x", "title": "PMA P100021: Stent Graft",
           "normalized": {"applicant": "Medtronic Vascular"}}
    a = qr.adjudicate_record(rec, "applicant:medtronic")
    assert a["relevance"] == "RELEVANT"  # via applicant field in record_text


def test_query_differentiation_flag():
    r1 = {"record_id": "a", "title": "one", "normalized": {}}
    r2 = {"record_id": "b", "title": "two", "normalized": {}}
    results = {
        "src": [
            {"query": "alpha beta", "status": "OK", "records": [r1, r2]},
            {"query": "gamma delta", "status": "OK", "records": [r1, r2]},
        ]
    }
    agg = aggregate(results)
    assert agg["src"]["query_differentiation"] == "QUERY_POSSIBLY_IGNORED"
    g = grade_query_relevance(agg["src"])
    assert g["grade"] == 1
    assert "possibly ignored" in g["evidence"]


def test_date_window_no_false_flag():
    r1 = {"record_id": "a", "title": "M5.0 earthquake", "normalized": {}}
    r2 = {"record_id": "b", "title": "M4.9 earthquake", "normalized": {}}
    results = {
        "usgs_earthquakes": [
            {"query": "2026-07-01", "status": "OK", "records": [r1, r2]},
            {"query": "2026-01-01", "status": "OK", "records": [r1, r2]},
        ]
    }
    agg = aggregate(results)
    assert agg["usgs_earthquakes"]["query_differentiation"] == \
        "PARAMETERIZED_DATE_WINDOW"


def test_battery_covers_all_probed_sources():
    # every battery source exists in the registry
    for sid in qr.BATTERY:
        assert sid in SOURCE_REGISTRY, f"battery source {sid} not registered"
    # every metered source is excluded from the battery
    for sid, rec in SOURCE_REGISTRY.items():
        if rec.get("metered_quota"):
            assert sid not in qr.BATTERY


def test_battery_excludes_documented_only():
    for sid in qr.BATTERY_EXCLUSIONS:
        if sid.endswith("_note"):
            continue
        assert sid not in qr.BATTERY


# ---------------------------------------------------------------------------
# 4. trust tiers (CEO #5)
# ---------------------------------------------------------------------------

def test_maud_never_outranks_peer_review():
    assert trust.weight("fda_maude") < trust.weight("pubmed")
    assert trust.weight("fda_maude") < trust.weight("europepmc")


def test_complaint_vs_recall_tier():
    # same host family: a complaint (voluntary) is weaker than a recall
    # (regulatory action) — hosting is not authorship
    assert trust.trust_tier("nhtsa_complaints")[0] == "SECONDARY"
    assert trust.trust_tier("nhtsa_recalls")[0] == "PRIMARY_REGULATORY"


def test_unknown_source_raises():
    with pytest.raises(KeyError):
        trust.trust_tier("totally_unknown_source")


def test_all_registry_sources_classified():
    missing = trust.all_sources_classified(list(SOURCE_REGISTRY.keys()))
    assert missing == [], f"unclassified trust tiers: {missing}"


def test_aggregate_reports_raw_alongside_weighted():
    out = trust.aggregate_by_tier([
        {"source_id": "fda_maude", "record_id": "a"},
        {"source_id": "fda_maude", "record_id": "b"},
        {"source_id": "pubmed", "record_id": "c"},
    ])
    assert out["raw_record_count"] == 3
    assert out["tier_distribution"]["SECONDARY"] == 2
    assert out["weighted_count"] == 2 * 2 + 3 * 1


def test_preprint_below_peer_review():
    assert trust.weight("arxiv") < trust.weight("pubmed")


# ---------------------------------------------------------------------------
# 5. canonical evidence graph (CEO #4)
# ---------------------------------------------------------------------------

def _paper(sid, rec_id, doi, title, extra_norm=None):
    return {
        "source_id": sid, "record_id": rec_id, "title": title,
        "raw_payload_sha256": f"sha-{rec_id}",
        "normalized": {"doi": doi, **(extra_norm or {})},
        "provenance": {"provider": sid},
        "limitations": [],
    }


def _complaint(rec_id):
    return {
        "source_id": "nhtsa_complaints", "record_id": rec_id,
        "title": "coolant valve", "role": "ADVERSE_EVENT",
        "raw_payload_sha256": f"sha-{rec_id}",
        "normalized": {"odi_number": int(rec_id),
                       "components": "ELECTRICAL SYSTEM",
                       "summary": "coolant bypass valve cracks"},
        "limitations": [],
    }


def _build_valid_graph():
    g = EvidenceGraph()
    papers = [
        _paper("europepmc", "1", "10.1007/demo.001",
               "Connector corrosion study", {"publication_year": 2024}),
        _paper("crossref", "9", "10.1007/demo.001",
               "Connector corrosion study"),
        _paper("europepmc", "2", "10.1007/demo.002",
               "Battery thermal study"),
    ]
    g.ingest_records(papers + [_complaint("1001"), _complaint("1002")])
    g.add_claim("C1", "Fluid intrusion degrades connector contacts",
                [("europepmc", "1"), ("crossref", "9")])
    g.add_engineering_constraint("EC1", "seal must resist thermal cycling",
                                 ["C1"],
                                 threshold={
                                     "statement": "10 mOhm max",
                                     "provenance": "postulate (MODEL_DERIVED)",
                                     "class": "MODEL_DERIVED",
                                     "uncertainty": "unquantified"})
    g.add_mechanism("M1", "hydrophobic vent labyrinth drain",
                    ["EC1"], ["nhtsa_complaints:1001"])  # gap motivator
    g.add_invention("I1", "vented connector with capillary drain",
                    ["M1"], ["doi:10.1007/demo.001"])
    return g


def test_full_chain_validates():
    g = _build_valid_graph()
    assert g.validate() == []


def test_dedup_same_doi_one_canonical_entity():
    g = _build_valid_graph()
    ents = [n for n in g.nodes.values()
            if n["node_type"] == "CANONICAL_ENTITY"
            and n["payload"]["identity_key"] == "doi:10.1007/demo.001"]
    assert len(ents) == 1
    # both source records resolve to it
    resolvers = [e for e in g.edges if e["parent"] == ents[0]["node_id"]]
    assert len(resolvers) == 2


def test_fail_closed_claim_without_record():
    g = EvidenceGraph()
    g.ingest_records([_paper("europepmc", "1", "10.1/x", "t")])
    with pytest.raises(KeyError):
        g.add_claim("CX", "claim citing nothing", [("europepmc", "ghost")])


def test_fail_closed_mechanism_without_constraint():
    g = _build_valid_graph()
    with pytest.raises(ValueError):
        g.add_mechanism("MX", "hypothetical", [], [])


def test_fail_closed_invention_without_prior_art():
    g = _build_valid_graph()
    with pytest.raises(ValueError):
        g.add_invention("IX", "unsearched idea", ["M1"], [])


def test_fail_closed_unknown_edge_node():
    g = EvidenceGraph()
    g.ingest_records([_paper("europepmc", "1", "10.1/x", "t")])
    with pytest.raises(KeyError):
        g.add_edge("EVIDENCES", "SOURCE_RECORD:europepmc:1", "CLAIM:ghost")


def test_threshold_requires_provenance_class_uncertainty():
    g = _build_valid_graph()
    with pytest.raises(ValueError):
        g.add_engineering_constraint("ECX", "bad threshold", ["C1"],
                                     threshold={"statement": "nonsense"})


def test_trust_tier_on_every_record():
    g = _build_valid_graph()
    for n in g.nodes.values():
        if n["node_type"] == "SOURCE_RECORD":
            assert n["payload"]["trust_tier"] in trust.TRUST_TIERS
            assert n["payload"]["raw_payload_sha256"]


def _conflicting_pair():
    # same DOI, genuinely different publication_year (not time-varying-
    # exempt) from two sources -> contradiction must surface
    a = _paper("europepmc", "1", "10.1007/demo.009", "Study X",
               {"publication_year": 2020})
    b = _paper("crossref", "9", "10.1007/demo.009", "Study X",
               {"publication_year": 2015})
    return a, b


def test_contradiction_detected_and_survives_to_invention():
    g = EvidenceGraph()
    a, b = _conflicting_pair()
    g.ingest_records([a, b, _complaint("1001")])
    g.add_claim("C1", "publication-year-dependent claim",
                [("europepmc", "1"), ("crossref", "9")])
    g.add_engineering_constraint(
        "EC1", "constraint", ["C1"],
        threshold={"statement": "x", "provenance": "p",
                   "class": "MODEL_DERIVED", "uncertainty": "u"})
    g.add_mechanism("M1", "mech", ["EC1"], ["nhtsa_complaints:1001"])
    g.add_invention("I1", "inv", ["M1"], ["doi:10.1007/demo.009"])
    assert g.validate() == []
    reaching = g.contradictions_reaching("INVENTION:I1")
    assert reaching, "contradiction must SURVIVE the chain to the invention"
    node = g.nodes[reaching[0]]
    assert node["payload"]["severity"] == "CONTRADICTION"
    # both sides' provenance carried
    assert set(node["payload"]["values"]) >= {2020, 2015} or \
        len(node["payload"]["values"]) >= 2


def test_serialization_deterministic():
    g1 = _build_valid_graph().to_dict()
    g2 = _build_valid_graph().to_dict()
    assert g1["graph_sha256"] == g2["graph_sha256"]


def test_unclassified_trust_invalidates():
    g = _build_valid_graph()
    g.add_node("SOURCE_RECORD", {
        "source_id": "mystery_source", "record_id": "x",
        "raw_payload_sha256": "sha", "trust_tier": None,
    }, node_id="SOURCE_RECORD:mystery_source:x")
    v = g.validate()
    assert any("unclassified trust" in x for x in v)


# ---------------------------------------------------------------------------
# 6. CDRH standards client-side window rewrite
# ---------------------------------------------------------------------------

PAGE1 = """<html><table><tr><td>Date of Entry</td><td>x</td><td>hdr</td>
<td>hdr</td><td>hdr</td><td>hdr</td><td>hdr</td></tr>
<tr><td>2026-08-01</td><td>x</td><td>r1</td><td>Complete</td><td>ISO</td>
<td>10993-1</td><td>Biocompatibility</td></tr>
<tr><td>2026-08-01</td><td>x</td><td>r2</td><td>Partial</td><td>ASTM</td>
<td>F2338</td><td>Leak detection</td></tr></table>
<a href="detail.cfm?standard__identification_no=1">d</a></html>"""


def test_standards_client_side_filter():
    c = FdaRecognizedStandardsConnector()
    parsed = c.parse_payload(PAGE1.encode(), "10993")
    recs = c.normalize_payload(parsed, "10993", "sha")
    # '10993' matches only the ISO row after client-side filtering is
    # applied by search(); normalize itself is unfiltered — the filter
    # lives in search(). Here we verify parse + normalize fidelity.
    assert len(recs) == 2
    assert recs[0].normalized["standard_designation"] == "10993-1"
    assert recs[1].normalized["standard_designation"] == "F2338"


def test_standards_filter_function():
    # emulate the search() client filter over two pages
    c = FdaRecognizedStandardsConnector()
    rows = c.parse_payload(PAGE1.encode(), "")["records"]
    qterms = ["10993"]
    filtered = [r for r in rows
                if all(t in " ".join([r["standard_designation"] or "",
                                      r["standard_title"] or ""]).lower()
                       for t in qterms)]
    assert len(filtered) == 1
    assert filtered[0]["standard_designation"] == "10993-1"
