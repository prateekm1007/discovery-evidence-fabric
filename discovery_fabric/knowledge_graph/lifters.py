"""Lifters: normalized SourceRecords -> knowledge-graph entities + edges.

The device-reality chain the CEO directive requires:

    PATENT <-> DEVICE <-> REGULATORY_ACTION <-> CLINICAL_TRIAL <->
    ADVERSE_EVENT <-> RECALL <-> MATERIAL <-> MANUFACTURING_PROCESS

Edges exist ONLY where a record measurably establishes them:

  MAUDE event     -> ADVERSE_EVENT node + DEVICE node + DEVICE->ADVERSE_EVENT
  Recall record   -> RECALL node + DEVICE node (via k_numbers) + DEVICE->RECALL
  510(k) record   -> REGULATORY_ACTION node + DEVICE node + DEVICE->REG_ACTION
  PMA record      -> REGULATORY_ACTION node + DEVICE node + DEVICE->REG_ACTION
  GUDID record    -> DEVICE node (strong identity)
  Clinical trial  -> CLINICAL_TRIAL node + DEVICE->TRIAL edge ONLY on exact
                     intervention-name match to an existing DEVICE node
                     (no fuzzy adjacency — Art. XXI.4)
  Patent record   -> PATENT_FAMILY node; PATENT_FAMILY->DEVICE edge only on
                     exact measured linkage (none fabricated)

PREDICATE / MATERIAL / MANUFACTURING_PROCESS / STANDARD entities: types are
first-class in the schema; lifters create them ONLY when a source field
measurably carries the linkage. No invented linkages (Art. VI).
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from discovery_fabric.knowledge_graph.entities import (
    Entity, adverse_event_entity, clinical_trial_entity, device_entity_from_record,
    patent_family_entity, recall_entity, regulatory_action_entity,
    IDENTITY_NAME_ONLY,
)
from discovery_fabric.knowledge_graph.graph import KnowledgeGraph, edge_from_record


def _norm_name(name: str) -> str:
    return " ".join((name or "").upper().split())


def lift_maude_record(g: KnowledgeGraph, record) -> List[str]:
    """MAUDE event -> ADVERSE_EVENT + DEVICE + edge."""
    dev = device_entity_from_record(record)
    if dev is None:
        return []
    g.add_entity(dev)
    event = adverse_event_entity(record)
    g.add_entity(event)
    g.add_edge(edge_from_record(
        "DEVICE_SUBJECT_OF_ADVERSE_EVENT", dev.entity_id, event.entity_id, record))
    return [dev.entity_id, event.entity_id]


def lift_recall_record(g: KnowledgeGraph, record) -> List[str]:
    """Recall -> RECALL + DEVICE (via k_number linkage when present) + edge."""
    n = record.normalized
    k = n.get("k_numbers")
    k_list = [k] if isinstance(k, str) and k else (k or [])
    created = []
    if k_list:
        # recall record measurably carries K-number linkage
        for kn in k_list[:3]:
            dev = Entity(
                entity_type="DEVICE", entity_id=f"DEVICE:510k:{kn}",
                display_name=n.get("product_description") or kn,
                identifiers={"k_number": kn},
                provenance=[{
                    "source_id": record.source_id,
                    "record_id": record.record_id,
                    "raw_payload_sha256": record.raw_payload_sha256,
                    "retrieved_at": record.retrieved_at,
                    "query": record.query,
                }],
                attributes={"recalled": True},
            )
            g.add_entity(dev)
            rec = recall_entity(record)
            g.add_entity(rec)
            g.add_edge(edge_from_record(
                "DEVICE_SUBJECT_OF_RECALL", dev.entity_id, rec.entity_id, record))
            created.extend([dev.entity_id, rec.entity_id])
        return created
    # no K linkage: recall node + name-only device node (explicitly unresolved)
    dev = device_entity_from_record(record)
    rec = recall_entity(record)
    if dev is not None:
        g.add_entity(dev)
        g.add_entity(rec)
        g.add_edge(edge_from_record(
            "DEVICE_SUBJECT_OF_RECALL", dev.entity_id, rec.entity_id, record))
        return [dev.entity_id, rec.entity_id]
    g.add_entity(rec)
    return [rec.entity_id]


def lift_510k_record(g: KnowledgeGraph, record) -> List[str]:
    """510(k) -> REGULATORY_ACTION + DEVICE + edge."""
    n = record.normalized
    if not n.get("k_number"):
        return []
    dev = device_entity_from_record(record)
    action = regulatory_action_entity(record, "510K_CLEARANCE")
    if dev is None:
        return []
    g.add_entity(dev)
    g.add_entity(action)
    g.add_edge(edge_from_record(
        "DEVICE_CLEARED_VIA", dev.entity_id, action.entity_id, record))
    return [dev.entity_id, action.entity_id]


def lift_pma_record(g: KnowledgeGraph, record) -> List[str]:
    """PMA -> REGULATORY_ACTION + DEVICE + edge."""
    n = record.normalized
    if not n.get("pma_number"):
        return []
    dev = device_entity_from_record(record)
    action = regulatory_action_entity(record, "PMA_APPROVAL")
    if dev is None:
        return []
    g.add_entity(dev)
    g.add_entity(action)
    g.add_edge(edge_from_record(
        "DEVICE_CLEARED_VIA", dev.entity_id, action.entity_id, record))
    return [dev.entity_id, action.entity_id]


def lift_udi_record(g: KnowledgeGraph, record) -> List[str]:
    """GUDID -> DEVICE node with strong identity."""
    dev = device_entity_from_record(record)
    if dev is None:
        return []
    g.add_entity(dev)
    return [dev.entity_id]


def lift_clinical_trial_record(g: KnowledgeGraph, record) -> List[str]:
    """ClinicalTrial -> CLINICAL_TRIAL node; DEVICE->TRIAL edge ONLY on
    exact intervention-name match with an existing DEVICE node."""
    trial = clinical_trial_entity(record)
    g.add_entity(trial)
    created = [trial.entity_id]
    interventions = record.normalized.get("interventions") or []
    existing_devices = g.entities("DEVICE")
    by_name = {}
    for d in existing_devices:
        if d.display_name:
            by_name.setdefault(_norm_name(d.display_name), d.entity_id)
    for iv in interventions:
        if not iv:
            continue
        target = by_name.get(_norm_name(str(iv)))
        if target:
            g.add_edge(edge_from_record(
                "DEVICE_STUDIED_IN", target, trial.entity_id, record))
            created.append(target)
    return created


def lift_patent_record(g: KnowledgeGraph, record) -> List[str]:
    """Patent hit -> PATENT_FAMILY node (+ PATENT_CLAIM nodes when the
    record carries verbatim claims, e.g. a Patent Bear full-text fetch).

    No PATENT_COVERS_DEVICE edge unless a measured linkage exists (none
    fabricated — device linkage is asserted by NOBODY here).
    """
    from discovery_fabric.knowledge_graph.entities import (
        patent_claim_entity,
    )
    from discovery_fabric.knowledge_graph.edges import make_edge

    fam = patent_family_entity(record)
    g.add_entity(fam)
    made = [fam.entity_id]

    claims = (record.normalized or {}).get("claims") or []
    for claim in claims:
        if not isinstance(claim, dict) or not str(claim.get("text") or "").strip():
            continue
        ent = patent_claim_entity(record, claim)
        g.add_entity(ent)
        edge = make_edge("PATENT_CLAIM_BELONGS_TO", ent.entity_id,
                         fam.entity_id, record)
        if edge is not None:
            g.add_edge(edge)
        made.append(ent.entity_id)
    return made


LIFTERS = {
    "fda_maude": lift_maude_record,
    "fda_recall": lift_recall_record,
    "fda_510k": lift_510k_record,
    "fda_pma": lift_pma_record,
    "fda_udi": lift_udi_record,
    "clinicaltrials_gov": lift_clinical_trial_record,
    # patent sources -> PATENT_FAMILY (+PATENT_CLAIM when verbatim claims
    # are present in the record). Bibliographic hits produce family nodes
    # only; claim nodes require full-text retrieval (measured providers:
    # Patent Bear get_patent_record).
    "lens_patent": lift_patent_record,
    "patentbear": lift_patent_record,
    "google_patents": lift_patent_record,
    "epo_ops": lift_patent_record,
    "uspto_odp": lift_patent_record,
    "patsnap_eureka": lift_patent_record,
    "google_bigquery_patents": lift_patent_record,
}


def lift_query_result(g: KnowledgeGraph, query_result) -> dict:
    """Lift all records from a SourceQueryResult into the graph."""
    lifted, skipped = 0, 0
    lifter = LIFTERS.get(query_result.source_id)
    for rec in query_result.records:
        if lifter is not None:
            lifter(g, rec)
            lifted += 1
        else:
            skipped += 1
    return {
        "source_id": query_result.source_id,
        "status": query_result.status,
        "lifted": lifted,
        "skipped_no_lifter": skipped,
    }
