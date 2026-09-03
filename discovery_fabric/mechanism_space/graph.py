"""Mechanism graphs — canonical hashing and validation.

structure_hash: topology + node types + edge relations, LABELS EXCLUDED.
  Two graphs with identical structure_hash are the same causal SHAPE.
content_hash: structure + labels. Identical content_hash = same mechanism
  verbatim; structure-equal + label-similar = linguistic variant (see
  distinctness.py).
"""
from __future__ import annotations
import hashlib
import json
from typing import Any, Dict
from .schema import NODE_TYPES, EDGE_RELS


def validate_graph(g: Dict[str, Any]) -> None:
    if not isinstance(g, dict) or set(g) < {"nodes", "edges"}:
        raise ValueError("graph must have 'nodes' and 'edges'")
    ids = set()
    for n in g["nodes"]:
        if set(n) < {"id", "type", "label"}:
            raise ValueError(f"node missing fields: {n}")
        if n["type"] not in NODE_TYPES:
            raise ValueError(f"unknown node type {n['type']!r}")
        ids.add(n["id"])
    for e in g["edges"]:
        if set(e) < {"src", "dst", "rel"}:
            raise ValueError(f"edge missing fields: {e}")
        if e["rel"] not in EDGE_RELS:
            raise ValueError(f"unknown edge rel {e['rel']!r}")
        if e["src"] not in ids or e["dst"] not in ids:
            raise ValueError(f"edge references unknown node: {e}")
    if len(ids) != len(g["nodes"]):
        raise ValueError("duplicate node ids")


def _structure(g: Dict[str, Any]):
    deg = {n["id"]: [] for n in g["nodes"]}
    for e in g["edges"]:
        deg[e["src"]].append(("out", e["rel"], sorted([e["src"], e["dst"]])))
        deg[e["dst"]].append(("in", e["rel"], sorted([e["src"], e["dst"]])))
    nodes = sorted(
        (n["id"], n["type"], tuple(sorted(map(str, deg[n["id"]]))))
        for n in g["nodes"])
    return {"nodes": nodes,
            "edges": sorted((e["src"], e["dst"], e["rel"])
                            for e in g["edges"])}


def _content(g: Dict[str, Any]):
    c = _structure(g)
    labels = {n["id"]: n["label"] for n in g["nodes"]}
    c["labels"] = [labels[i] for i, _, _ in c["nodes"]]
    return c


def _h(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, ensure_ascii=True).encode()).hexdigest()[:16]


def structure_hash(g: Dict[str, Any]) -> str:
    validate_graph(g)
    return _h(_structure(g))


def content_hash(g: Dict[str, Any]) -> str:
    validate_graph(g)
    return _h(_content(g))
