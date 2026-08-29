"""Knowledge-graph edges — every edge is EVIDENCE-BOUND.

Core rule (Art. I/XXI.9): an edge may only exist if a retrieved source
record MEASURABLY establishes it. Each edge carries the custody reference
(source_id, record_id, raw_payload_sha256) of the establishing record.
An edge without verifiable provenance is REJECTED at insertion time —
adjacency is never inferred, suggested, or completed by the graph layer.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Allowed directed edge types between first-class entities.
EDGE_TYPES = {
    # device reality chain (CEO directive)
    "DEVICE_SUBJECT_OF_ADVERSE_EVENT": ("DEVICE", "ADVERSE_EVENT"),
    "DEVICE_SUBJECT_OF_RECALL": ("DEVICE", "RECALL"),
    "DEVICE_CLEARED_VIA": ("DEVICE", "REGULATORY_ACTION"),
    "DEVICE_STUDIED_IN": ("DEVICE", "CLINICAL_TRIAL"),
    "DEVICE_HAS_PREDICATE": ("DEVICE", "PREDICATE"),
    "DEVICE_USES_MATERIAL": ("DEVICE", "MATERIAL"),
    "DEVICE_MADE_VIA": ("DEVICE", "MANUFACTURING_PROCESS"),
    "DEVICE_GOVERNED_BY": ("DEVICE", "STANDARD"),
    "PATENT_COVERS_DEVICE": ("PATENT_FAMILY", "DEVICE"),
    "PATENT_CLAIM_BELONGS_TO": ("PATENT_CLAIM", "PATENT_FAMILY"),
    "REGULATORY_ACTION_RECOGNIZES": ("REGULATORY_ACTION", "STANDARD"),
    "DEVICE_MEMBER_OF_FAMILY": ("DEVICE", "DEVICE_FAMILY"),
    # lifecycle closure (L5): commercial + manufacturing reality
    "DEVICE_COMMERCIALIZED_AS": ("DEVICE", "COMMERCIAL_PRODUCT"),
    "COMMERCIAL_PRODUCT_SUBJECT_OF_RECALL": ("COMMERCIAL_PRODUCT", "RECALL"),
    "COMMERCIAL_PRODUCT_STUDIED_IN": ("COMMERCIAL_PRODUCT", "CLINICAL_TRIAL"),
    "COMMERCIAL_PRODUCT_SUBJECT_OF_ADVERSE_EVENT": ("COMMERCIAL_PRODUCT", "ADVERSE_EVENT"),
}


@dataclass
class Edge:
    edge_type: str
    source_entity_id: str
    target_entity_id: str
    provenance: List[Dict[str, Any]]  # custody refs of establishing records

    def to_dict(self) -> Dict[str, Any]:
        return {
            "edge_type": self.edge_type,
            "source": self.source_entity_id,
            "target": self.target_entity_id,
            "provenance": self.provenance,
        }


def custody_of(record) -> Dict[str, Any]:
    return {
        "source_id": record.source_id,
        "record_id": record.record_id,
        "raw_payload_sha256": record.raw_payload_sha256,
        "retrieved_at": record.retrieved_at,
        "query": record.query,
    }


def make_edge(edge_type: str, source_id: str, target_id: str, record) -> Optional[Edge]:
    """Construct an edge IF the type exists and provenance is present."""
    if edge_type not in EDGE_TYPES:
        raise ValueError(f"unknown edge type {edge_type!r}")
    if record is None:
        return None
    prov = custody_of(record)
    if not prov.get("record_id") or not prov.get("raw_payload_sha256"):
        # No custody -> no edge (Art. I: evidence precedes assertion)
        return None
    return Edge(edge_type=edge_type, source_entity_id=source_id,
                target_entity_id=target_id, provenance=[prov])
