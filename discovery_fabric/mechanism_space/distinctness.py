"""R401 Phase 10 — material distinctness: deterministic STRUCTURAL dedup.

Rules (measured against the Phase-5 lesson: text-only keys are never the
distinctness authority):
  * same structure_hash AND high label similarity (token Jaccard >= 0.8
    over node labels)  ->  LINGUISTIC VARIANT -> collapse (record reason
    + reference mechanism)
  * different structure_hash  ->  MATERIALLY DISTINCT -> always preserved
  * same structure_hash but low label similarity  ->  distinct content in
    the same causal shape (e.g. a cross-domain analogy)  ->  preserved
    with the shared-shape note (they are distinct DESIGNS; their evidence
    bundles differ)

Outputs a full ledger: kept / deduplicated / reason / reference.
"""
from __future__ import annotations
import json
import re
from typing import Any, Dict, List

from . import graph as G

LABEL_SIM_THRESHOLD = 0.8


def _tokens(labels: List[str]):
    out = set()
    for lab in labels:
        out.update(w for w in re.findall(r"[a-z]{3,}", lab.lower()))
    return out


def _jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# Meaning-bearing fields: operator outputs DELIBERATELY share causal
# structure (DIRECT_TRANSFER preserves the shape by definition), so a
# shared structure_hash alone can never mean "same mechanism". Material
# identity additionally requires the same system, geometry, boundary
# regime, novel design variable, and predicted effect.
MEANING_FIELDS = ("system", "geometry", "novel_design_variable",
                  "boundary_conditions", "predicted_effect")


def _identity(c: Dict[str, Any]):
    return tuple((f, json.dumps(c.get(f), sort_keys=True, default=str))
                 for f in MEANING_FIELDS)


def structural_dedup(candidates: List[Dict[str, Any]],
                     threshold: float = LABEL_SIM_THRESHOLD) -> Dict[str, Any]:
    kept: List[Dict[str, Any]] = []
    ledger: List[Dict[str, Any]] = []
    for c in candidates:
        g = c["mechanism_graph"]
        sh, ch = G.structure_hash(g), G.content_hash(g)
        toks = _tokens([n["label"] for n in g["nodes"]])
        ident = _identity(c)
        dup_of = None
        reason = ""
        for k in kept:
            kg = k["mechanism_graph"]
            ksh = G.structure_hash(kg)
            if _identity(k) != ident:
                continue  # differs in a meaning-bearing field -> material
            if ch == G.content_hash(kg):
                dup_of, reason = k, "EXACT content duplicate"
                break
            if sh == ksh:
                sim = _jaccard(toks, _tokens([n["label"] for n in kg["nodes"]]))
                if sim >= threshold:
                    dup_of = k
                    reason = (f"LINGUISTIC VARIANT (structure_hash equal, "
                              f"label similarity {sim:.2f} >= {threshold})")
                    break
        if dup_of is None:
            kept.append(c)
            ledger.append({"id": c["id"], "action": "KEPT",
                           "structure_hash": sh, "reason": "distinct structure/content"})
        else:
            ledger.append({"id": c["id"], "action": "DEDUPED", "reason": reason,
                           "reference": dup_of["id"], "structure_hash": sh})
    return {"kept": kept, "ledger": ledger,
            "stats": {"input": len(candidates), "kept": len(kept),
                      "deduplicated": len(candidates) - len(kept)}}
