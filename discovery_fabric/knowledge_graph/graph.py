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

    # ---- lifecycle progression (L5) --------------------------------------

    #: Which edges evidence which lifecycle stage. A stage is REACHED
    #: only through evidence-bound edges (custody present) — narrative
    #: claims about lifecycle progression are not graph facts.
    LIFECYCLE_STAGES = {
        "PATENT": {"edges": ("PATENT_COVERS_DEVICE",), "side": "target"},
        "REGULATORY": {"edges": ("DEVICE_CLEARED_VIA",), "side": "source"},
        "COMMERCIAL": {"edges": ("DEVICE_COMMERCIALIZED_AS",), "side": "source"},
        "CLINICAL": {"edges": ("DEVICE_STUDIED_IN",
                               "COMMERCIAL_PRODUCT_STUDIED_IN"), "side": "source"},
        "ADVERSE_EVENT": {"edges": ("DEVICE_SUBJECT_OF_ADVERSE_EVENT",
                                    "COMMERCIAL_PRODUCT_SUBJECT_OF_ADVERSE_EVENT"),
                          "side": "source"},
        "RECALL": {"edges": ("DEVICE_SUBJECT_OF_RECALL",
                             "COMMERCIAL_PRODUCT_SUBJECT_OF_RECALL"),
                   "side": "source"},
        "MATERIAL": {"edges": ("DEVICE_USES_MATERIAL",), "side": "source"},
        "MANUFACTURING": {"edges": ("DEVICE_MADE_VIA",), "side": "source"},
        "STANDARD": {"edges": ("DEVICE_GOVERNED_BY",), "side": "source"},
    }

    def lifecycle_progression(self, entity_id: str) -> Dict[str, Any]:
        """Answer the CEO's lifecycle question for one device/product:

        What stages has this approach ACTUALLY reached, with how many
        evidence-bound edges and which custody?

        The canonical lifecycle order is
            invention -> patent -> device -> regulation -> commercial ->
            clinical use -> failure/recall
        Stages without evidence-bound edges report reached=False with
        evidence_count=0 — an explicit UNKNOWN, never an inferred
        absence (Art. XXV: absence of edges is absence of EVIDENCE, not
        proof the stage didn't happen).
        """
        ent = self._entities.get(entity_id)
        if ent is None:
            return {"entity_id": entity_id, "error": "ENTITY_NOT_IN_GRAPH"}
        stages: Dict[str, Any] = {}
        for stage, spec in self.LIFECYCLE_STAGES.items():
            hits = []
            for e in self._edges:
                if e.edge_type not in spec["edges"]:
                    continue
                if spec["side"] == "source" and e.source_entity_id == entity_id:
                    hits.append(e)
                elif spec["side"] == "target" and e.target_entity_id == entity_id:
                    hits.append(e)
                # COMMERCIAL_PRODUCT-side stages also count for the
                # linked device? No — the graph has no inferred
                # adjacency (R4). Stage reach is computed per entity.
            stages[stage] = {
                "reached": bool(hits),
                "evidence_count": len(hits),
                "counterparts": sorted({(e.target_entity_id if spec["side"] == "source"
                                         else e.source_entity_id) for e in hits}),
                "custody": [p for e in hits for p in e.provenance][:20],
            }
        reached_order = [s for s in
                         ("PATENT", "REGULATORY", "COMMERCIAL", "CLINICAL",
                          "ADVERSE_EVENT", "RECALL")
                         if stages[s]["reached"]]
        return {
            "entity_id": entity_id,
            "entity_type": ent.entity_type,
            "display_name": ent.display_name,
            "stages": stages,
            "progression": reached_order,
            "full_chain_reached": (
                stages["PATENT"]["reached"] and stages["REGULATORY"]["reached"]
                and stages["COMMERCIAL"]["reached"]
                and (stages["CLINICAL"]["reached"]
                     or stages["ADVERSE_EVENT"]["reached"]
                     or stages["RECALL"]["reached"])),
            "note": "stages not reached = no evidence-bound edges in THIS "
                    "graph snapshot; not proof the stage never happened "
                    "(Art. XXV)",
        }

    def lifecycle_table(self) -> List[Dict[str, Any]]:
        """Lifecycle progression for every DEVICE / COMMERCIAL_PRODUCT
        node — the query that answers 'what technical approaches have
        actually progressed ... ?' across the graph."""
        rows = []
        for ent in self.entities("DEVICE") + self.entities("COMMERCIAL_PRODUCT"):
            rows.append(self.lifecycle_progression(ent.entity_id))
        return sorted(rows, key=lambda r: -sum(
            1 for s in r.get("stages", {}).values() if s.get("reached")))

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
