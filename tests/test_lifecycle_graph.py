"""Lifecycle graph tests (L5) — hermetic, no network, Art. XVII hardened.

Covers:
- COMMERCIAL_PRODUCT entity type (13th first-class type).
- New lifecycle edges: DEVICE_COMMERCIALIZED_AS,
  COMMERCIAL_PRODUCT_SUBJECT_OF_RECALL, COMMERCIAL_PRODUCT_STUDIED_IN,
  COMMERCIAL_PRODUCT_SUBJECT_OF_ADVERSE_EVENT.
- New lifters: gudid_commercial, gudid_sterilization,
  fda_pma_supplements, manufacturing_literature, standards (FDA + eCFR),
  materials (COD/WebBook).
- lifecycle_progression: stage reach ONLY via evidence-bound edges;
  unreached stages are explicit evidence_count=0 (Art. XXV); unknown
  entity refused; lifecycle_table ranks by stage count.
- MATERIAL nodes carry the PROPERTY_DATA / NOT_ESTABLISHED split.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.base import SourceRecord, utc_now
from discovery_fabric.knowledge_graph.entities import (
    ENTITY_TYPES, commercial_product_entity, manufacturing_process_entity,
    material_entity, standard_entity,
)
from discovery_fabric.knowledge_graph.edges import EDGE_TYPES
from discovery_fabric.knowledge_graph.graph import KnowledgeGraph
from discovery_fabric.knowledge_graph.lifters import (
    LIFTERS, lift_gudid_commercial_record, lift_gudid_sterilization_record,
    lift_manufacturing_literature_record, lift_material_record,
    lift_pma_supplement_record, lift_standard_record,
)


def _rec(source_id, role, record_id, normalized, title="t"):
    return SourceRecord(
        source_id=source_id, role=role, record_id=record_id, title=title,
        uri="https://example.org", retrieved_at=utc_now(), query="q",
        raw_payload_sha256="sha-" + record_id, normalized=normalized,
        provenance={"provider": source_id}, epistemic_state="OBSERVED",
        limitations=["test limitation"],
    )


GUDID_COMMERCIAL = _rec(
    "gudid_commercial", "COMMERCIAL", "gudid-commercial:key-1",
    {"public_device_record_key": "key-1", "brand_name": "HipSys",
     "company_name": "Co", "labeler_duns_number": "12",
     "product_codes": ["MEH"], "product_code_names": ["hip prosthesis"],
     "gmdn_pt_names": ["Hip prosthesis"],
     "commercial_distribution_status": "In Commercial Distribution",
     "commercial_distribution_end_date": None, "is_on_market": True,
     "version_or_model_number": "v1"})

GUDID_STER = _rec(
    "gudid_sterilization", "MANUFACTURING", "gudid-ster:key-1",
    {"public_device_record_key": "key-1", "brand_name": "HipSys",
     "company_name": "Co", "is_sterile": "true",
     "is_sterilization_prior_use": "false",
     "sterilization_methods": "Ethylene Oxide",
     "sterilization_method_list": ["Ethylene Oxide"],
     "processes": ["sterilization"]})

PMA_SUP = _rec(
    "fda_pma_supplements", "MANUFACTURING", "pma-sup:P123S4",
    {"pma_number": "P123", "supplement_number": "4",
     "supplement_type": "30-Day Notice",
     "supplement_reason": "Process Change - Manufacturer/Sterilizer/Packager/Supplier",
     "trade_name": "DevX", "applicant": "Co", "decision_code": "APPR",
     "decision_date": "2020-01-01", "product_code": "MEH",
     "devices": [], "classification": {"is_process_change": True,
                                        "is_sterilizer_change": True,
                                        "is_material_or_design_change": False}})

FDA_STD = _rec(
    "fda_recognized_standards", "STANDARDS", "fda_std:rec:1-1",
    {"recognition_number": "1-1", "standard_designation": "17665-1",
     "standard_title": "Sterilization moist heat",
     "standards_organization": "ISO",
     "specialty_task_group_area": "Sterility",
     "extent_of_recognition": "Complete", "date_of_entry": "2024-01-01",
     "standard_identification_no": "1"})

ECFR_SEC = _rec(
    "ecfr_title21", "STANDARDS", "ecfr:21cfr:820.1",
    {"cfr_title": 21, "section": "820.1", "section_text": "scope",
     "issue_date": "2026-08-27"})

COD = _rec(
    "cod_optimade", "MATERIALS", "cod:2300273",
    {"cod_id": "2300273", "chemical_formula": "Ca5HO13P3",
     "chemical_name": "hydroxyapatite", "space_group": "P 63/m",
     "elements": ["Ca", "H", "O", "P"],
     "evidence_dimension": "PROPERTY_DATA",
     "implant_suitability": "NOT_ESTABLISHED_BY_THIS_SOURCE"})

MFG_LIT = _rec(
    "manufacturing_literature", "MANUFACTURING", "mfg-lit:9",
    {"pmid": "9", "title": "AM porosity study",
     "processes": ["additive_manufacturing"],
     "process_constraint_spans": ["Porosity limits fatigue."],
     "quality_risk_spans": [], "verification_spans": []})


class TestEntityTypeAndEdges:
    def test_commercial_product_is_first_class(self):
        assert "COMMERCIAL_PRODUCT" in ENTITY_TYPES
        assert len(ENTITY_TYPES) == 13

    def test_lifecycle_edges_typed(self):
        assert EDGE_TYPES["DEVICE_COMMERCIALIZED_AS"] == ("DEVICE", "COMMERCIAL_PRODUCT")
        assert EDGE_TYPES["COMMERCIAL_PRODUCT_SUBJECT_OF_RECALL"] == ("COMMERCIAL_PRODUCT", "RECALL")
        assert EDGE_TYPES["COMMERCIAL_PRODUCT_STUDIED_IN"] == ("COMMERCIAL_PRODUCT", "CLINICAL_TRIAL")
        assert EDGE_TYPES["COMMERCIAL_PRODUCT_SUBJECT_OF_ADVERSE_EVENT"] == ("COMMERCIAL_PRODUCT", "ADVERSE_EVENT")


class TestNewLifters:
    def test_gudid_commercial_lifts_product_device_edge(self):
        g = KnowledgeGraph()
        made = lift_gudid_commercial_record(g, GUDID_COMMERCIAL)
        assert "COMMERCIAL_PRODUCT:gudid:key-1" in made
        edges = g.edges("DEVICE_COMMERCIALIZED_AS")
        assert len(edges) == 1
        assert edges[0].provenance[0]["record_id"] == "gudid-commercial:key-1"

    def test_gudid_sterilization_lifts_process_edge(self):
        g = KnowledgeGraph()
        made = lift_gudid_sterilization_record(g, GUDID_STER)
        assert any(e.startswith("MANUFACTURING_PROCESS:sterilization") for e in made)
        assert len(g.edges("DEVICE_MADE_VIA")) == 1

    def test_pma_supplement_lifts_regulatory_action(self):
        g = KnowledgeGraph()
        made = lift_pma_supplement_record(g, PMA_SUP)
        assert "REGULATORY_ACTION:pma:P123S4" in made
        action = [e for e in g.entities("REGULATORY_ACTION")
                  if e.entity_id == "REGULATORY_ACTION:pma:P123S4"][0]
        assert action.attributes["action_type"] == "PMA_MANUFACTURING_SUPPLEMENT"
        assert action.attributes["classification"]["is_sterilizer_change"] is True
        assert len(g.edges("DEVICE_CLEARED_VIA")) == 1

    def test_pma_supplement_without_numbers_refused(self):
        rec = _rec("fda_pma_supplements", "MANUFACTURING", "x",
                   {"pma_number": "", "supplement_number": ""})
        assert lift_pma_supplement_record(KnowledgeGraph(), rec) == []

    def test_manufacturing_literature_no_device_edge(self):
        # Art. XXI.4: literature does not identify a marketed device —
        # no DEVICE edge is fabricated
        g = KnowledgeGraph()
        made = lift_manufacturing_literature_record(g, MFG_LIT)
        assert made and made[0].startswith("MANUFACTURING_PROCESS:lit:")
        assert g.edges("DEVICE_MADE_VIA") == []

    def test_standards_lift_to_standard_nodes(self):
        g = KnowledgeGraph()
        lift_standard_record(g, FDA_STD)
        lift_standard_record(g, ECFR_SEC)
        ids = {e.entity_id for e in g.entities("STANDARD")}
        assert "STANDARD:fda_recognized:1_1" in ids
        assert "STANDARD:ecfr:21cfr_820_1" in ids

    def test_material_node_carries_epistemic_split(self):
        g = KnowledgeGraph()
        lift_material_record(g, COD)
        mat = g.entities("MATERIAL")[0]
        assert mat.attributes["evidence_dimension"] == "PROPERTY_DATA"
        assert mat.attributes["implant_suitability"] == "NOT_ESTABLISHED_BY_THIS_SOURCE"

    def test_all_new_sources_have_lifters(self):
        for sid in ("gudid_commercial", "gudid_sterilization",
                    "fda_pma_supplements", "manufacturing_literature",
                    "fda_recognized_standards", "ecfr_title21",
                    "cod_optimade", "nist_webbook", "materials_project"):
            assert sid in LIFTERS, sid


class TestLifecycleProgression:
    def _graph_with_lifecycle(self):
        g = KnowledgeGraph()
        lift_gudid_commercial_record(g, GUDID_COMMERCIAL)   # REGULATORY? no — COMMERCIAL
        lift_gudid_sterilization_record(g, GUDID_STER)      # MANUFACTURING
        lift_pma_supplement_record(g, PMA_SUP)              # REGULATORY
        return g

    def test_stage_reach_requires_evidence_edges(self):
        g = self._graph_with_lifecycle()
        dev_edges = g.edges("DEVICE_COMMERCIALIZED_AS")
        dev_id = dev_edges[0].source_entity_id
        prog = g.lifecycle_progression(dev_id)
        assert prog["stages"]["COMMERCIAL"]["reached"] is True
        assert prog["stages"]["COMMERCIAL"]["evidence_count"] == 1
        assert prog["stages"]["MANUFACTURING"]["reached"] is True
        # identity discipline (Art. XXI.6): the supplement's device node
        # is DEVICE:pma:P123 (its own exact identifier) — a DIFFERENT node
        # from DEVICE:gudid:key-1 until identifier-resolved. The gudid
        # node therefore carries commercial+manufacturing evidence, and
        # the pma node carries the regulatory evidence.
        pma_dev = g.edges("DEVICE_CLEARED_VIA")[0].source_entity_id
        assert pma_dev == "DEVICE:pma:P123"
        pma_prog = g.lifecycle_progression(pma_dev)
        assert pma_prog["stages"]["REGULATORY"]["reached"] is True

    def test_unreached_stage_is_explicit_zero_not_absence(self):
        g = self._graph_with_lifecycle()
        dev_id = g.edges("DEVICE_COMMERCIALIZED_AS")[0].source_entity_id
        prog = g.lifecycle_progression(dev_id)
        assert prog["stages"]["RECALL"]["reached"] is False
        assert prog["stages"]["RECALL"]["evidence_count"] == 0
        assert "not proof the stage never happened" in prog["note"]

    def test_unknown_entity_refused(self):
        g = KnowledgeGraph()
        res = g.lifecycle_progression("DEVICE:nowhere:X")
        assert res.get("error") == "ENTITY_NOT_IN_GRAPH"

    def test_full_chain_requires_patent_regulatory_commercial_and_failure(self):
        g = self._graph_with_lifecycle()
        dev_id = g.edges("DEVICE_COMMERCIALIZED_AS")[0].source_entity_id
        prog = g.lifecycle_progression(dev_id)
        # no patent/clinical/recall edges in this snapshot -> not full
        assert prog["full_chain_reached"] is False

    def test_lifecycle_table_ranks_by_stage_count(self):
        g = self._graph_with_lifecycle()
        table = g.lifecycle_table()
        assert len(table) >= 2
        counts = [sum(1 for s in r["stages"].values() if s["reached"])
                  for r in table]
        assert counts == sorted(counts, reverse=True)

    def test_every_progression_carries_custody(self):
        g = self._graph_with_lifecycle()
        dev_id = g.edges("DEVICE_COMMERCIALIZED_AS")[0].source_entity_id
        prog = g.lifecycle_progression(dev_id)
        for stage in ("COMMERCIAL", "MANUFACTURING"):
            assert prog["stages"][stage]["custody"], stage
            for c in prog["stages"][stage]["custody"]:
                assert c["raw_payload_sha256"]
        pma_prog = g.lifecycle_progression("DEVICE:pma:P123")
        assert pma_prog["stages"]["REGULATORY"]["custody"]


class TestEntityConstructors:
    def test_commercial_product_attributes(self):
        e = commercial_product_entity(GUDID_COMMERCIAL)
        assert e.attributes["company_name"] == "Co"
        assert e.attributes["is_on_market"] is True

    def test_manufacturing_process_identity_by_method(self):
        e = manufacturing_process_entity(GUDID_STER)
        assert e.entity_id == "MANUFACTURING_PROCESS:sterilization:Ethylene_Oxide"

    def test_standard_kinds_distinguished(self):
        s1 = standard_entity(FDA_STD)
        s2 = standard_entity(ECFR_SEC)
        assert s1.attributes["kind"] == "consensus_standard"
        assert s2.attributes["kind"] == "codified_regulation"

    def test_material_formula_from_cod(self):
        m = material_entity(COD)
        assert m.attributes["chemical_formula"] == "Ca5HO13P3"
        assert m.attributes["space_group"] == "P 63/m"
