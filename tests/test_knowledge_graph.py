"""Knowledge-graph tests — hermetic; includes ATTACK tests (Art. XVII).

Covers the 4 store integrity rules (R1 evidence-bound edges, R2 typed
edges, R3 real endpoints, R4 no silent merge) and the lifter identity
discipline (Art. XXI.6).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from discovery_fabric.source_registry.base import SourceRecord
from discovery_fabric.knowledge_graph.entities import (
    Entity, IDENTITY_NAME_ONLY, device_entity_from_record,
)
from discovery_fabric.knowledge_graph.edges import make_edge
from discovery_fabric.knowledge_graph.graph import KnowledgeGraph
from discovery_fabric.knowledge_graph.lifters import (
    lift_510k_record, lift_clinical_trial_record, lift_maude_record,
    lift_recall_record,
)


def _rec(source_id="fda_maude", record_id="maude:1", role="ADVERSE_EVENT",
         normalized=None):
    return SourceRecord(
        source_id=source_id, role=role, record_id=record_id,
        title="t", uri="https://example.org", retrieved_at="2026-01-01T00:00:00Z",
        query="q", raw_payload_sha256="a" * 64,
        normalized=normalized or {}, provenance={"provider": source_id},
    )


class TestStoreIntegrity:
    def test_edge_without_custody_rejected(self):
        g = KnowledgeGraph()
        g.add_entity(Entity("DEVICE", "DEVICE:x:1", "d", {}))
        g.add_entity(Entity("RECALL", "RECALL:fda:1", "r", {}))
        # no record -> no edge
        assert g.add_edge(None) is False
        # edge with empty provenance -> rejected (R1)
        e = make_edge("DEVICE_SUBJECT_OF_RECALL", "DEVICE:x:1", "RECALL:fda:1",
                      _rec(record_id="", source_id=""))
        # record_id empty -> make_edge returns None (no custody)
        assert e is None
        assert g.rejected() == [] or g.stats()["edge_count"] == 0

    def test_phantom_endpoint_rejected(self):
        g = KnowledgeGraph()
        g.add_entity(Entity("DEVICE", "DEVICE:x:1", "d", {}))
        rec = _rec()
        edge = make_edge("DEVICE_SUBJECT_OF_ADVERSE_EVENT",
                         "DEVICE:x:1", "ADVERSE_EVENT:maude:404", rec)
        assert g.add_edge(edge) is False
        assert any(r["reason"] == "PHANTOM_ENDPOINT" for r in g.rejected())

    def test_unknown_edge_type_rejected(self):
        g = KnowledgeGraph()
        g.add_entity(Entity("DEVICE", "DEVICE:x:1", "d", {}))
        g.add_entity(Entity("DEVICE", "DEVICE:y:2", "d2", {}))
        rec = _rec()
        with pytest.raises(ValueError):
            make_edge("DEVICE_SECRETLY_RELATED_TO", "DEVICE:x:1", "DEVICE:y:2", rec)

    def test_no_silent_merge_by_name(self):
        # R4 / Art. XXI.6: same brand text, different identity strength ->
        # DISTINCT nodes, never merged.
        g = KnowledgeGraph()
        rec_named = _rec(normalized={"device_brand_name": "PACER X"})
        rec_k = _rec(record_id="maude:2",
                     normalized={"device_brand_name": "PACER X", "pma_pmn_number": "K1"})
        lift_maude_record(g, rec_named)
        lift_maude_record(g, rec_k)
        devices = g.entities("DEVICE")
        assert len(devices) == 2
        statuses = sorted(d.identity_status for d in devices)
        assert IDENTITY_NAME_ONLY in statuses

    def test_exact_identifier_resolution_merges(self):
        # Two records carrying the SAME k-number resolve to ONE device node
        # with appended custody.
        g = KnowledgeGraph()
        maude = _rec(record_id="maude:9", normalized={
            "device_brand_name": "PACER", "pma_pmn_number": "K77"})
        k510 = _rec(source_id="fda_510k", record_id="510k:K77", role="REGULATORY",
                    normalized={"k_number": "K77", "device_name": "PACER",
                                "decision_date": "2020-01-01"})
        lift_maude_record(g, maude)
        lift_510k_record(g, k510)
        devices = g.entities("DEVICE")
        assert len(devices) == 1
        assert devices[0].entity_id == "DEVICE:510k:K77"
        # custody from BOTH records attached
        assert len(devices[0].provenance) == 2

    def test_duplicate_edge_appends_custody_not_duplicated(self):
        g = KnowledgeGraph()
        rec1 = _rec(record_id="maude:1", normalized={
            "device_brand_name": "PACER", "pma_pmn_number": "K5",
            "mdr_report_key": "1"})
        rec2 = _rec(record_id="maude:2", normalized={
            "device_brand_name": "PACER", "pma_pmn_number": "K5",
            "mdr_report_key": "2"})
        lift_maude_record(g, rec1)
        lift_maude_record(g, rec2)
        # one device, two events, two edges
        assert len(g.entities("DEVICE")) == 1
        assert len(g.entities("ADVERSE_EVENT")) == 2
        assert len(g.edges("DEVICE_SUBJECT_OF_ADVERSE_EVENT")) == 2

    def test_recall_without_k_number_gets_name_only_device(self):
        g = KnowledgeGraph()
        rec = _rec(source_id="fda_recall", record_id="recall:1", role="RECALL",
                   normalized={"product_description": "pacer lead wire",
                               "reason_for_recall": "fracture"})
        lift_recall_record(g, rec)
        assert len(g.entities("RECALL")) == 1
        dev = g.entities("DEVICE")[0]
        assert dev.identity_status == IDENTITY_NAME_ONLY

    def test_recall_with_k_number_resolves_device(self):
        g = KnowledgeGraph()
        rec = _rec(source_id="fda_recall", record_id="recall:2", role="RECALL",
                   normalized={"product_description": "pacer lead",
                               "k_numbers": ["K999"], "reason_for_recall": "x"})
        lift_recall_record(g, rec)
        dev = g.entities("DEVICE")[0]
        assert dev.entity_id == "DEVICE:510k:K999"
        assert dev.identity_status == "RESOLVED"


class TestTrialEdgeDiscipline:
    def test_exact_intervention_match_creates_edge(self):
        g = KnowledgeGraph()
        k510 = _rec(source_id="fda_510k", record_id="510k:K42", role="REGULATORY",
                    normalized={"k_number": "K42", "device_name": "PacerPro Lead"})
        lift_510k_record(g, k510)
        trial = _rec(source_id="clinicaltrials_gov", record_id="nct:NCT1",
                     role="CLINICAL",
                     normalized={"nct_id": "NCT1", "brief_title": "trial",
                                 "interventions": ["PacerPro Lead"]})
        lift_clinical_trial_record(g, trial)
        assert len(g.edges("DEVICE_STUDIED_IN")) == 1

    def test_fuzzy_intervention_match_creates_no_edge(self):
        # Art. XXI.4: generic string adjacency is NOT evidence of relation.
        g = KnowledgeGraph()
        k510 = _rec(source_id="fda_510k", record_id="510k:K42", role="REGULATORY",
                    normalized={"k_number": "K42", "device_name": "PacerPro Lead"})
        lift_510k_record(g, k510)
        trial = _rec(source_id="clinicaltrials_gov", record_id="nct:NCT2",
                     role="CLINICAL",
                     normalized={"nct_id": "NCT2", "brief_title": "trial",
                                 "interventions": ["pacer pro leads (prototype)"]})
        lift_clinical_trial_record(g, trial)
        assert len(g.edges("DEVICE_STUDIED_IN")) == 0


class TestEntityProvenance:
    def test_device_entity_carries_custody(self):
        rec = _rec(normalized={"device_brand_name": "PACER", "pma_pmn_number": "K3"})
        dev = device_entity_from_record(rec)
        assert dev.provenance[0]["record_id"] == "maude:1"
        assert dev.provenance[0]["raw_payload_sha256"] == "a" * 64

    def test_name_only_entity_declares_limitation(self):
        rec = _rec(normalized={"device_brand_name": "PACER"})
        dev = device_entity_from_record(rec)
        assert dev.identity_status == IDENTITY_NAME_ONLY
        assert any("NOT merged" in lim for lim in dev.limitations)

    def test_no_identifier_no_device(self):
        rec = _rec(normalized={})
        assert device_entity_from_record(rec) is None
