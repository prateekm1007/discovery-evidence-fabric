"""Manufacturing-role tests (L4) — hermetic, no network, Art. XVII
hardened.

Covers:
- PMA supplement connector: process/sterilizer/material classification,
  record ids from PMA+supplement numbers.
- Manufacturing literature connector: 8-process taxonomy
  classification, exact-span constraint/risk/verification extraction
  (quotes, not paraphrase), non-taxonomy records keep process=None.
- GUDID sterilization connector: method list parsing, sterile flags.
- Process knowledge layer: the directive's chain
  (mechanism -> route -> constraint -> risk -> verification) with
  per-link epistemic class; ENGINEERING_TAXONOMY vs EVIDENCE_BOUND
  separation; standards grammar relevance filter (Art. II); unknown
  routes REFUSED.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry import retrieval_log
from discovery_fabric.source_registry.base import (
    STATUS_EMPTY, STATUS_OK, SourceRecord, utc_now,
)
from discovery_fabric.source_registry.connectors.manufacturing import (
    GudidSterilizationConnector, ManufacturingLiteratureConnector,
    PmaManufacturingSupplementConnector, classify_process,
)
from discovery_fabric.discovery_modes.process_knowledge import (
    EPISTEMIC_TAXONOMY, PROCESS_KNOWLEDGE, all_processes,
    candidate_routes, enrich_process, manufacturing_route_chain,
    process_entry,
)
from discovery_fabric.source_registry.registry import (
    SOURCE_REGISTRY, validate_registry,
)


@pytest.fixture(autouse=True)
def _isolated_log(tmp_path, monkeypatch):
    monkeypatch.setattr(retrieval_log, "LOG_PATH", tmp_path / "retrieval_log.jsonl")
    yield


def _wire(connector, payload: bytes | None, http_status=200, status=STATUS_OK):
    if payload is not None:
        connector._request = lambda url, timeout=25: (
            payload, status, http_status, None, None)
    else:
        connector._request = lambda url, timeout=25: (
            None, status, http_status, "injected", None)
    return connector


PMA_PAYLOAD = {
    "results": [
        {"pma_number": "P980040", "supplement_number": "S172",
         "supplement_type": "30-Day Notice",
         "supplement_reason": "Process Change - Manufacturer/Sterilizer/Packager/Supplier",
         "trade_name": "DEVICE X", "applicant": "ACME",
         "decision_code": "APPR", "decision_date": "2020-01-01",
         "product_code": "MEA"},
        {"pma_number": "P960042", "supplement_number": "S014",
         "supplement_type": "Real-Time Process",
         "supplement_reason": "Change Design/Components/Specifications/Material",
         "trade_name": "DEVICE Y", "applicant": "BCORP",
         "decision_code": "APPR", "decision_date": "2019-01-01"},
    ],
    "meta": {"results": {"total": 2}},
}

LIT_PAYLOAD = {
    "resultList": {"result": [
        {"id": "111", "pmid": "111", "title": "Laser cutting of nitinol stents",
         "abstractText": "Laser cutting produced heat-affected zones. "
         "Surface roughness limits fatigue performance. "
         "Verification of edge quality by imaging was performed.",
         "journalTitle": "J Med Eng", "firstPublicationDate": "2021-01-01"},
        {"id": "222", "pmid": "222", "title": "Something unrelated entirely",
         "abstractText": "No process terms here at all.", "journalTitle": "J Misc"},
    ]},
}

GUDID_STER_PAYLOAD = {
    "results": [
        {"public_device_record_key": "k1", "brand_name": "Cath A",
         "company_name": "Co",
         "sterilization": {"is_sterile": "true",
                           "is_sterilization_prior_use": "false",
                           "sterilization_methods": "Ethylene Oxide"}},
        {"public_device_record_key": "k2", "brand_name": "Tool B",
         "company_name": "Co",
         "sterilization": {"is_sterile": "false",
                           "is_sterilization_prior_use": "true",
                           "sterilization_methods": "Moist Heat or Steam Sterilization"}},
    ],
    "meta": {"results": {"total": 2}},
}


class TestPmaSupplements:
    def test_process_and_sterilizer_classification(self):
        res = _wire(PmaManufacturingSupplementConnector(),
                    json.dumps(PMA_PAYLOAD).encode()).search("q")
        n = res.records[0].normalized
        assert n["classification"]["is_process_change"] is True
        assert n["classification"]["is_sterilizer_change"] is True
        assert n["classification"]["is_material_or_design_change"] is False
        assert res.records[0].record_id == "pma-sup:P980040SS172"

    def test_material_change_classification(self):
        res = _wire(PmaManufacturingSupplementConnector(),
                    json.dumps(PMA_PAYLOAD).encode()).search("q")
        n = res.records[1].normalized
        assert n["classification"]["is_material_or_design_change"] is True
        assert n["classification"]["is_process_change"] is False

    def test_limitations_disclose_scope(self):
        res = _wire(PmaManufacturingSupplementConnector(),
                    json.dumps(PMA_PAYLOAD).encode()).search("q")
        assert any("PMA-class devices only" in l for l in res.records[0].limitations)


class TestManufacturingLiterature:
    def test_process_classification_from_taxonomy(self):
        res = _wire(ManufacturingLiteratureConnector(),
                    json.dumps(LIT_PAYLOAD).encode()).search("laser")
        assert res.records[0].normalized["processes"] == ["laser_processing"]

    def test_exact_span_extraction_quotes_abstract(self):
        res = _wire(ManufacturingLiteratureConnector(),
                    json.dumps(LIT_PAYLOAD).encode()).search("laser")
        n = res.records[0].normalized
        assert any("heat-affected" in s for s in n["process_constraint_spans"])
        assert any("roughness" in s for s in n["process_constraint_spans"])
        assert any("fatigue" in s for s in n["quality_risk_spans"])
        assert any("Verification" in s or "verification" in s
                   for s in n["verification_spans"])

    def test_non_taxonomy_record_keeps_processes_empty(self):
        res = _wire(ManufacturingLiteratureConnector(),
                    json.dumps(LIT_PAYLOAD).encode()).search("laser")
        assert res.records[1].normalized["processes"] == []
        # still a record — the provider answered (not absence, Art. XXI.3)
        assert res.records[1].record_id == "mfg-lit:222"

    def test_url_targets_device_literature(self):
        url = ManufacturingLiteratureConnector().build_url("extrusion")
        assert "europepmc" in url
        assert "medical+device" in url or "medical%20device" in url


class TestGudidSterilization:
    def test_method_list_parsing(self):
        res = _wire(GudidSterilizationConnector(),
                    json.dumps(GUDID_STER_PAYLOAD).encode()).search("q")
        n = res.records[1].normalized
        assert n["sterilization_method_list"] == [
            "Moist Heat", "Steam Sterilization"]
        assert n["processes"] == ["sterilization"]

    def test_sterile_flag(self):
        res = _wire(GudidSterilizationConnector(),
                    json.dumps(GUDID_STER_PAYLOAD).encode()).search("q")
        assert res.records[0].normalized["is_sterile"] == "true"
        assert res.records[0].normalized["sterilization_methods"] == "Ethylene Oxide"


class TestProcessKnowledge:
    def test_all_eight_directive_processes_present(self):
        assert all_processes() == [
            "additive_manufacturing", "coatings", "extrusion",
            "injection_molding", "laser_processing", "machining",
            "microfabrication", "sterilization",
        ]

    def test_every_entry_carries_the_chain_fields(self):
        for p in all_processes():
            e = process_entry(p)
            assert e["physical_principle"], p
            assert e["process_constraints"], p
            assert e["quality_risks"], p
            assert e["verification_methods"], p
            assert e["epistemic_class"] == EPISTEMIC_TAXONOMY

    def test_candidate_routes_from_mechanism_text(self):
        routes = candidate_routes("titanium porous acetabular cup")
        names = [r["route"] for r in routes]
        assert "machining" in names and "additive_manufacturing" in names
        assert all(r["epistemic_class"] == EPISTEMIC_TAXONOMY for r in routes)

    def test_route_chain_has_all_links_with_classes(self):
        chain = manufacturing_route_chain("PEEK spinal implant cage", "machining")
        for link in ("mechanism", "candidate_route", "process_constraint",
                     "quality_risk", "verification"):
            assert link in chain
            assert chain[link]["epistemic_class"]
        assert chain["process_constraint"]["epistemic_class"] == EPISTEMIC_TAXONOMY

    def test_unknown_route_refused(self):
        # Art. VI: no fabricated process entries
        with pytest.raises(ValueError, match="unknown manufacturing route"):
            manufacturing_route_chain("x", "cold_fusion")

    def test_enrich_requires_valid_process(self):
        with pytest.raises(ValueError):
            enrich_process("not_a_process")

    def _lit_record(self, processes):
        return SourceRecord(
            source_id="manufacturing_literature", role="MANUFACTURING",
            record_id="mfg-lit:1", title="t", uri="u",
            retrieved_at=utc_now(), query="q", raw_payload_sha256="h1",
            normalized={"processes": processes,
                        "process_constraint_spans": ["The tolerance was 0.1 mm."]},
            provenance={"provider": "manufacturing_literature"},
        )

    def _std_record(self, designation, title):
        return SourceRecord(
            source_id="fda_recognized_standards", role="STANDARDS",
            record_id="fda_std:rec:1-1", title=title, uri="u",
            retrieved_at=utc_now(), query="q", raw_payload_sha256="h2",
            normalized={"standard_designation": designation,
                        "standard_title": title,
                        "specialty_task_group_area": "X"},
            provenance={"provider": "fda_recognized_standards"},
        )

    def test_enrichment_attaches_evidence_with_custody(self):
        entry = enrich_process(
            "sterilization",
            [self._lit_record(["sterilization"]), self._lit_record(["machining"])],
            [self._std_record("17665-1", "Sterilization of health care products - moist heat")])
        lit = entry["evidence_enrichment"]["literature"]
        assert len(lit) == 1  # only the sterilization-classified record
        assert lit[0]["custody"]["record_id"] == "mfg-lit:1"
        assert lit[0]["epistemic_class"] == "EVIDENCE_BOUND"

    def test_standards_grammar_filters_irrelevant_records(self):
        # Art. II: a keyword-matched but topically unrelated standard is
        # NOT attached
        entry = enrich_process(
            "sterilization", [],
            [self._std_record("G175-24",
                              "Ignition sensitivity of oxygen regulators"),
             self._std_record("17665-1", "Moist heat sterilization")])
        stds = entry["evidence_enrichment"]["standards"]
        assert len(stds) == 1
        assert stds[0]["standard"] == "17665-1"


class TestRegistryWiring:
    def test_connectors_resolve(self):
        from discovery_fabric.source_registry.health import load_connector
        for sid in ("fda_pma_supplements", "manufacturing_literature",
                    "gudid_sterilization"):
            cls = load_connector(sid)
            assert cls is not None and cls.SOURCE_ID == sid

    def test_placeholder_removed(self):
        assert "manufacturing_process_sources" not in SOURCE_REGISTRY

    def test_registry_validates_clean_after_manufacturing_edit(self):
        assert validate_registry() == []
