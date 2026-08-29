"""Knowledge-graph store — nodes + edges with constitutional integrity rules.

Rules enforced at insert time:
  R1 (evidence-bound edges): an edge whose provenance lacks a record_id or
      raw_payload_sha256 is rejected (Art. I / XXI.9).
  R2 (typed edges): only EDGE_TYPES relations exist.
  R3 (entity endpoints exist): an edge may only reference entities in the
      graph — no phantom adjacency.
  R4 (no silent merge): entities with different entity_ids are distinct,
      always. Merging happens ONLY by explicit identifier equality at
      construction time (entities.py), never in the store (Art. XXI.6).
  R5 (append-only custody): entity provenance lists grow; none are removed.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from discovery_fabric.knowledge_graph.entities import Entity
from discovery_fabric.knowledge_graph.edges import EDGE_TYPES, Edge, make_edge


class KnowledgeGraph:
    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._edges: List[Edge] = []
        self._rejected: List[Dict[str, Any]] = []

    # ---- entities ---------------------------------------------------------

    def add_entity(self, entity: Entity) -> str:
        existing = self._entities.get(entity.entity_id)
        if existing is None:
            self._entities[entity.entity_id] = entity
            return entity.entity_id
        # same id = same resolved identity: custody APPENDS (R5)
        for prov in entity.provenance:
            if prov not in existing.provenance:
                existing.provenance.append(prov)
        # attributes: keep first-seen (deterministic); record richer attrs
        for k, v in entity.attributes.items():
            existing.attributes.setdefault(k, v)
        return existing.entity_id

    # ---- edges ------------------------------------------------------------

    def add_edge(self, edge: Optional[Edge]) -> bool:
        if edge is None:
            return False
        # R2: typed
        if edge.edge_type not in EDGE_TYPES:
            self._rejected.append({"reason": "UNKNOWN_EDGE_TYPE",
                                   "edge": edge.to_dict()})
            return False
        # R1: evidence-bound
        for prov in edge.provenance:
            if not prov.get("record_id") or not prov.get("raw_payload_sha256"):
                self._rejected.append({"reason": "EDGE_WITHOUT_CUSTODY",
                                       "edge": edge.to_dict()})
                return False
        # R3: endpoints exist
        for endpoint in (edge.source_entity_id, edge.target_entity_id):
            if endpoint not in self._entities:
                self._rejected.append({"reason": "PHANTOM_ENDPOINT",
                                       "edge": edge.to_dict()})
                return False
        # duplicate suppression (same type+endpoints+first custody)
        for e in self._edges:
            if (e.edge_type == edge.edge_type
                    and e.source_entity_id == edge.source_entity_id
                    and e.target_entity_id == edge.target_entity_id):
                for prov in edge.provenance:
                    if prov not in e.provenance:
                        e.provenance.append(prov)
                return True
        self._edges.append(edge)
        return True

    # ---- queries ----------------------------------------------------------

    def entities(self, entity_type: Optional[str] = None) -> List[Entity]:
        out = [e for e in self._entities.values()
               if entity_type is None or e.entity_type == entity_type]
        return sorted(out, key=lambda e: e.entity_id)

    def edges(self, edge_type: Optional[str] = None) -> List[Edge]:
        return [e for e in self._edges
                if edge_type is None or e.edge_type == edge_type]

    def neighbors(self, entity_id: str) -> List[Dict[str, Any]]:
        out = []
        for e in self._edges:
            if e.source_entity_id == entity_id:
                out.append({"edge": e.edge_type, "direction": "out",
                            "other": e.target_entity_id})
            elif e.target_entity_id == entity_id:
                out.append({"edge": e.edge_type, "direction": "in",
                            "other": e.source_entity_id})
        return out

    def rejected(self) -> List[Dict[str, Any]]:
        return list(self._rejected)

    def stats(self) -> Dict[str, Any]:
        by_type: Dict[str, int] = {}
        for e in self._entities.values():
            by_type[e.entity_type] = by_type.get(e.entity_type, 0) + 1
        edge_by_type: Dict[str, int] = {}
        for e in self._edges:
            edge_by_type[e.edge_type] = edge_by_type.get(e.edge_type, 0) + 1
        return {
            "entity_count": len(self._entities),
            "entities_by_type": by_type,
            "edge_count": len(self._edges),
            "edges_by_type": edge_by_type,
            "rejected_count": len(self._rejected),
        }

    # ---- persistence ------------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entities": [e.to_dict() for e in self.entities()],
            "edges": [e.to_dict() for e in self._edges],
            "rejected": self._rejected,
            "stats": self.stats(),
        }

    def save(self, path) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)


def edge_from_record(edge_type: str, source_id: str, target_id: str, record) -> Optional[Edge]:
    """Public helper: make_edge with None-safety (no record -> no edge)."""
    if record is None:
        return None
    return make_edge(edge_type, source_id, target_id, record)
