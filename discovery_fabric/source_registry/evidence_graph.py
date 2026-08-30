"""CANONICAL EVIDENCE GRAPH — CEO directive 2026-08-30 #4.

    SOURCE_RECORD
    → CANONICAL_ENTITY
    → CLAIM / EVIDENCE
    → ENGINEERING_CONSTRAINT
    → FAILURE / GAP
    → MECHANISM
    → INVENTION

"Every record should become [this chain]. Deduplication, provenance and
contradictions must survive that entire chain."

Design (constitutional anchors in brackets):
- SOURCE_RECORD nodes are leaves verifiable against the hash-chained
  retrieval log (source_id + record_id + raw_payload_sha256) [Art. XII].
- CANONICAL_ENTITY nodes come from entity_resolution (EXACT identity
  keys only — DOI/PMID/patent-normalized/K-number/NCT; records without
  keys are UNRESOLVED and stay visible) [Art. II/XXV/XXI.6].
- CLAIM nodes bind a proposition to canonical entities + source records;
  the claim CANNOT define what its evidence says — the evidence-side
  field is independently resolved [Art. III].
- ENGINEERING_CONSTRAINT nodes quantify constraints and must cite ≥1
  claim; thresholds carry provenance + class + uncertainty [Art. XXVII].
- FAILURE_GAP nodes come from negative_evidence records with their
  epistemic caps attached [Art. XXI.5 generalized].
- MECHANISM nodes must cite ≥1 constraint AND ≥1 failure-gap-or-claim;
  INVENTION nodes must cite ≥1 mechanism and prior-art entities.
- Contradictions computed on canonical entities PROPAGATE: every node
  whose evidence subtree contains a contradiction carries the
  contradiction reference — surfaced at every level, never adjudicated,
  never averaged [Art. III / XV].
- Trust tiers annotate every provenance edge; aggregation is tier-
  weighted with raw counts always present [CEO directive #5].
- Validation is FAIL-CLOSED: any broken edge, missing custody entry,
  or unclassified trust tier makes the whole graph INVALID.

The graph is a DETERMINISTIC function of its inputs (records +
synthesis): building twice from the same inputs yields byte-identical
serialization (node ids are content-derived, ordering is canonical).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from discovery_fabric.source_registry import trust as trust_mod
from discovery_fabric.source_registry.entity_resolution import (
    EntityRegistry,
    detect_contradictions,
    extract_identity_keys,
)

NODE_TYPES = (
    "SOURCE_RECORD", "CANONICAL_ENTITY", "CLAIM",
    "ENGINEERING_CONSTRAINT", "FAILURE_GAP", "MECHANISM", "INVENTION",
)

# Edge kinds (from-child -> to-parent direction is "child EVIDENCES parent")
EDGE_KINDS = {
    "RESOLVES_TO": "source record resolves to canonical entity (identity key)",
    "EVIDENCES": "claim is evidenced by source record / constraint evidenced by claim",
    "CONSTRAINS": "constraint feeds mechanism",
    "INDICATES": "failure/gap node indicates an opportunity",
    "MOTIVATES": "failure/gap motivates mechanism",
    "SYNTHESIZED_FROM": "invention derived from mechanism",
    "PRIOR_ART_FOR": "canonical entity is prior art for an invention",
    "CONTRADICTS": "two claims about the same entity disagree (surfaced, never adjudicated)",
}


def _sha(obj: Any) -> str:
    return hashlib.sha256(json.dumps(
        obj, sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()[:16]


class EvidenceGraph:
    """Append-only in-memory canonical evidence graph."""

    def __init__(self) -> None:
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.edges: List[Dict[str, Any]] = []
        self._edge_keys: Set[Tuple[str, str, str]] = set()

    # ------------------------------------------------------------------
    # node/edge primitives
    # ------------------------------------------------------------------

    def add_node(self, node_type: str, payload: Dict[str, Any],
                 node_id: Optional[str] = None) -> str:
        if node_type not in NODE_TYPES:
            raise ValueError(f"unknown node type {node_type!r}")
        nid = node_id or f"{node_type}:{_sha(payload)}"
        if nid in self.nodes:
            return nid  # content-derived ids dedupe naturally
        node = {
            "node_id": nid,
            "node_type": node_type,
            "payload": payload,
        }
        self.nodes[nid] = node
        return nid

    def add_edge(self, kind: str, child: str, parent: str,
                 meta: Optional[Dict[str, Any]] = None) -> None:
        if kind not in EDGE_KINDS:
            raise ValueError(f"unknown edge kind {kind!r}")
        if child not in self.nodes:
            raise KeyError(f"edge child {child!r} not a node (fail-closed)")
        if parent not in self.nodes:
            raise KeyError(f"edge parent {parent!r} not a node (fail-closed)")
        key = (kind, child, parent)
        if key in self._edge_keys:
            return
        self._edge_keys.add(key)
        self.edges.append({
            "kind": kind, "child": child, "parent": parent,
            "meta": meta or {},
        })

    # ------------------------------------------------------------------
    # the chain: records -> entities -> claims -> ...
    # ------------------------------------------------------------------

    def ingest_records(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """SOURCE_RECORD + CANONICAL_ENTITY layers + negative-evidence caps.

        records: SourceRecord.to_dict() payloads (or run-envelope evidence
        dicts with source_id/record_id provenance fields).
        Returns a summary {resolved, unresolved, contradictions}.
        """
        summary = {"ingested": len(records), "resolved": 0,
                   "unresolved": 0, "contradictions": 0}
        # entity resolution over the batch (EXACT keys only)
        registry = EntityRegistry()
        resolution = registry.resolve(records)
        for record in records:
            # trust tier annotation — unmapped source FAILS the build
            sid = record.get("source_id")
            if sid is None:
                prov = record.get("provenance") or {}
                sid = prov.get("provider") or prov.get("source_id")
            tier, weight = trust_mod.trust_tier(sid)
            rec_id = record.get("record_id") or record.get("source_id")
            payload = {
                "source_id": sid,
                "record_id": rec_id,
                "title": (record.get("title") or "")[:300],
                "raw_payload_sha256": (
                    record.get("raw_payload_sha256")
                    or (record.get("provenance") or {}).get("raw_payload_sha256")
                ),
                "trust_tier": tier,
                "trust_weight": weight,
                "limitations": record.get("limitations") or [],
                "normalized_keys": sorted((record.get("normalized") or {}).keys()),
            }
            rid = self.add_node("SOURCE_RECORD", payload,
                                node_id=f"SOURCE_RECORD:{sid}:{rec_id}")
            _kind, keys = extract_identity_keys(record)
            if keys:
                for key in keys:
                    eid = self.add_node("CANONICAL_ENTITY", {
                        "identity_key": key,
                        "key_type": key.split(":", 1)[0],
                    }, node_id=f"CANONICAL_ENTITY:{key}")
                    self.add_edge("RESOLVES_TO", rid, eid,
                                  {"identity": "exact key (Art. II)"})
                summary["resolved"] += 1
            else:
                payload["unresolved_identity"] = True
                summary["unresolved"] += 1
        # negative-evidence classification layer
        from discovery_fabric.source_registry.negative_evidence import (
            classify_negative_evidence,
        )
        for record in records:
            cls = classify_negative_evidence(record)
            if cls.get("evidence_class", "NONE") != "NONE":
                sid = record.get("source_id")
                rec_id = record.get("record_id")
                self.add_node("FAILURE_GAP", {
                    "negative_evidence_class": cls["evidence_class"],
                    "failure_domain": cls.get("failure_domain"),
                    "source": f"{sid}:{rec_id}",
                    "raw_payload_sha256": record.get("raw_payload_sha256"),
                    "limitations": cls.get("limitations") or [],
                }, node_id=f"FAILURE_GAP:{sid}:{rec_id}")
                # FAILURE_GAP edges back to its source record
                src_node = f"SOURCE_RECORD:{sid}:{rec_id}"
                if src_node in self.nodes:
                    self.add_edge("EVIDENCES", src_node,
                                  f"FAILURE_GAP:{sid}:{rec_id}",
                                  {"kind": "negative_evidence_record"})
        # contradictions across canonical entities (both-side provenance)
        contradictions = detect_contradictions(records)
        for c in contradictions:
            ck = _sha(c)
            cid = self.add_node("CLAIM", {
                "claim_type": "CONTRADICTION_SURFACE",
                "about_entity": c.get("entity_id"),
                "field": c.get("field"),
                "values": c.get("values"),
                "severity": c.get("severity"),
            }, node_id=f"CONTRADICTION:{ck}")
            summary["contradictions"] += 1
            # keep the contradiction attached to its entity
            ek = f"CANONICAL_ENTITY:{c.get('entity_id')}"
            if ek in self.nodes:
                self.add_edge("CONTRADICTS", cid, ek,
                              {"surfaced": "never adjudicated (Art. III)"})
        return summary

    def add_claim(self, claim_id: str, proposition: str,
                  evidence_record_ids: List[Tuple[str, str]],
                  field_bindings: Optional[Dict[str, Any]] = None) -> str:
        """CLAIM node: a proposition + the exact records evidencing it.

        The evidence side independently resolves what the records say
        (field_bindings carry the field/value the evidence ACTUALLY
        establishes — the claim may not define it) [Art. III].
        """
        cid = self.add_node("CLAIM", {
            "claim_id": claim_id,
            "proposition": proposition,
            "field_bindings": field_bindings or {},
        }, node_id=f"CLAIM:{claim_id}")
        for sid, rec_id in evidence_record_ids:
            rid = f"SOURCE_RECORD:{sid}:{rec_id}"
            if rid not in self.nodes:
                raise KeyError(
                    f"claim {claim_id!r} cites unknown record {rid!r} — "
                    "evidence must be ingested first (fail-closed, Art. I)")
            self.add_edge("EVIDENCES", rid, cid)
        return cid

    def add_engineering_constraint(self, constraint_id: str, statement: str,
                                   claim_ids: List[str],
                                   threshold: Optional[Dict[str, Any]] = None) -> str:
        """ENGINEERING_CONSTRAINT: quantified constraint citing claims.

        threshold must carry provenance/class/uncertainty when present
        [Art. XXVII].
        """
        if threshold is not None:
            for req in ("provenance", "class", "uncertainty"):
                if req not in threshold:
                    raise ValueError(
                        f"threshold missing {req!r} — Art. XXVII requires "
                        "provenance, explicit class and uncertainty")
        nid = self.add_node("ENGINEERING_CONSTRAINT", {
            "constraint_id": constraint_id,
            "statement": statement,
            "threshold": threshold,
        }, node_id=f"ENGINEERING_CONSTRAINT:{constraint_id}")
        for cid in claim_ids:
            cnode = f"CLAIM:{cid}"
            if cnode not in self.nodes:
                raise KeyError(
                    f"constraint cites unknown claim {cid!r} (fail-closed)")
            self.add_edge("EVIDENCES", cnode, nid)
        return nid

    def add_mechanism(self, mechanism_id: str, description: str,
                      constraint_ids: List[str],
                      motivator_ids: List[str]) -> str:
        """MECHANISM: must cite >=1 constraint AND >=1 failure-gap-or-claim."""
        if not constraint_ids:
            raise ValueError("mechanism without an engineering constraint "
                             "is a hypothetical (Art. XX — fail-closed)")
        if not motivator_ids:
            raise ValueError("mechanism without a failure/gap or claim "
                             "motivator solves an assumed problem (Art. XX)")
        nid = self.add_node("MECHANISM", {
            "mechanism_id": mechanism_id,
            "description": description,
        }, node_id=f"MECHANISM:{mechanism_id}")
        for c in constraint_ids:
            cnode = f"ENGINEERING_CONSTRAINT:{c}"
            if cnode not in self.nodes:
                raise KeyError(f"mechanism cites unknown constraint {c!r}")
            self.add_edge("CONSTRAINS", cnode, nid)
        for m in motivator_ids:
            for kind, prefix in (("gap", "FAILURE_GAP"), ("claim", "CLAIM")):
                mnode = f"{prefix}:{m}"
                if mnode in self.nodes:
                    self.add_edge("MOTIVATES", mnode, nid)
                    break
            else:
                raise KeyError(
                    f"mechanism motivator {m!r} is neither FAILURE_GAP nor "
                    "CLAIM (fail-closed)")
        return nid

    def add_invention(self, invention_id: str, description: str,
                      mechanism_ids: List[str],
                      prior_art_entity_keys: List[str]) -> str:
        """INVENTION: must cite >=1 mechanism and >=1 prior-art entity."""
        if not mechanism_ids:
            raise ValueError("invention without a mechanism (fail-closed)")
        if not prior_art_entity_keys:
            raise ValueError("invention with zero prior-art citation is an "
                             "unsearched idea (Art. XXI — fail-closed)")
        nid = self.add_node("INVENTION", {
            "invention_id": invention_id,
            "description": description,
        }, node_id=f"INVENTION:{invention_id}")
        for m in mechanism_ids:
            mnode = f"MECHANISM:{m}"
            if mnode not in self.nodes:
                raise KeyError(f"invention cites unknown mechanism {m!r}")
            self.add_edge("SYNTHESIZED_FROM", mnode, nid)
        for key in prior_art_entity_keys:
            enode = f"CANONICAL_ENTITY:{key}"
            if enode not in self.nodes:
                raise KeyError(
                    f"invention cites prior-art entity {key!r} never "
                    "resolved in this graph — evidence must precede "
                    "assertion (Art. I)")
            self.add_edge("PRIOR_ART_FOR", enode, nid)
        return nid

    # ------------------------------------------------------------------
    # propagation + validation
    # ------------------------------------------------------------------

    def _children(self) -> Dict[str, List[Dict[str, Any]]]:
        out: Dict[str, List[Dict[str, Any]]] = {}
        for e in self.edges:
            out.setdefault(e["parent"], []).append(e)
        return out

    def contradictions_reaching(self, node_id: str) -> List[str]:
        """Contradiction node ids in the evidence subtree of node_id.

        Contradictions SURVIVE the chain: any node whose subtree contains
        a contradiction carries it (surfaced at every level).
        """
        children = self._children()
        seen: Set[str] = set()
        found: List[str] = []

        def walk(nid: str) -> None:
            if nid in seen:
                return
            seen.add(nid)
            if nid.startswith("CONTRADICTION:"):
                found.append(nid)
                return
            for e in children.get(nid, []):
                walk(e["child"])

        walk(node_id)
        return found

    def validate(self) -> List[str]:
        """FAIL-CLOSED structural validation; empty list = valid."""
        v: List[str] = []
        children = self._children()
        for nid, node in self.nodes.items():
            t = node["node_type"]
            kids = children.get(nid, [])
            kid_types = {self.nodes[e["child"]]["node_type"] for e in kids}
            if t == "CLAIM" and not nid.startswith("CONTRADICTION:"):
                if "SOURCE_RECORD" not in kid_types:
                    v.append(f"{nid}: CLAIM without SOURCE_RECORD evidence (Art. I)")
                payload = node["payload"]
                if not payload.get("proposition"):
                    v.append(f"{nid}: CLAIM without a proposition")
            elif t == "ENGINEERING_CONSTRAINT":
                if "CLAIM" not in kid_types:
                    v.append(f"{nid}: CONSTRAINT without a citing chain to CLAIM")
            elif t == "MECHANISM":
                if "ENGINEERING_CONSTRAINT" not in kid_types:
                    v.append(f"{nid}: MECHANISM without CONSTRAINT (Art. XX)")
                if not ({"FAILURE_GAP", "CLAIM"} & kid_types):
                    v.append(f"{nid}: MECHANISM without FAILURE_GAP/CLAIM motivator (Art. XX)")
            elif t == "INVENTION":
                if "MECHANISM" not in kid_types:
                    v.append(f"{nid}: INVENTION without MECHANISM")
                if not any(
                        e["kind"] == "PRIOR_ART_FOR"
                        for e in kids):
                    v.append(f"{nid}: INVENTION without prior-art entities (Art. XXI)")
            elif t == "SOURCE_RECORD":
                if node["payload"].get("trust_tier") is None:
                    v.append(f"{nid}: SOURCE_RECORD without trust tier (CEO #5)")
                if not node["payload"].get("raw_payload_sha256"):
                    v.append(f"{nid}: SOURCE_RECORD without custody hash (Art. XII)")
        # trust coverage: every distinct source in the graph must be classified
        sids = {n["payload"].get("source_id") for n in self.nodes.values()
                if n["node_type"] == "SOURCE_RECORD"}
        unclassified = trust_mod.all_sources_classified(sorted(x for x in sids if x))
        if unclassified:
            v.append(f"unclassified trust tiers: {unclassified} (Art. XXV)")
        return v

    def tier_weighted_summary(self) -> Dict[str, Any]:
        records = [n["payload"] for n in self.nodes.values()
                   if n["node_type"] == "SOURCE_RECORD"]
        agg = trust_mod.aggregate_by_tier([
            {"source_id": r.get("source_id"),
             "record_id": r.get("record_id")}
            for r in records
        ])
        agg["node_counts"] = {
            t: sum(1 for n in self.nodes.values() if n["node_type"] == t)
            for t in NODE_TYPES
        }
        agg["contradiction_nodes"] = sum(
            1 for n in self.nodes.values() if n["node_id"].startswith("CONTRADICTION:"))
        return agg

    def to_dict(self) -> Dict[str, Any]:
        """Deterministic serialization (canonical ordering, content hashes)."""
        nodes = [self.nodes[k] for k in sorted(self.nodes)]
        edges = sorted(self.edges, key=lambda e: (e["kind"], e["child"], e["parent"]))
        doc = {
            "artifact": "CANONICAL_EVIDENCE_GRAPH",
            "directive": "CEO 2026-08-30 #4 — canonical evidence graph; "
                         "dedup + provenance + contradictions survive the "
                         "whole chain",
            "nodes": nodes,
            "edges": edges,
            "summary": self.tier_weighted_summary(),
        }
        doc["graph_sha256"] = _sha({"n": len(nodes), "e": len(edges),
                                    "nodes": [n["node_id"] for n in nodes],
                                    "edges": [[e["kind"], e["child"], e["parent"]]
                                              for e in edges]})
        return doc
