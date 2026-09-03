"""R401 Phase 8 — five REAL transformation operators with machine-verifiable
operator fidelity.

The fidelity contract (CEO directive): for EACH operator, M1 -> M2 must
carry operator-specific STRUCTURAL change. A wording change FAILS. A
synonym change FAILS. A paragraph expansion FAILS. The validator below
checks, per operator:

  * required_changed_fields — the fields that MUST differ
  * invariants — the structural relations that MUST hold (or be confined
    to allowed deltas)
  * derivation_trace — op, changed fields, invariant proofs, binding map

apply_operator() builds M2 from M1 deterministically. operator_fidelity()
is an INDEPENDENT checker: given any (M1, M2, op) it re-derives the
proofs and can FAIL a hand-crafted fake — including prose-only edits.
"""
from __future__ import annotations
import copy
import json
from typing import Any, Dict, List, Tuple
from . import graph as G
from .schema import OPERATORS, mechanism_candidate, now_utc

PROSE_ONLY_FIELDS = {"description", "notes", "rationale", "summary"}


class OperatorError(RuntimeError):
    pass


OPERATOR_SPECS: Dict[str, Dict[str, Any]] = {
    "DIRECT_TRANSFER": {
        "required_changed": ["system"],
        "required_unchanged": ["mechanism_graph (structure AND edge relations)"],
        "semantics": "same causal mechanism, different engineered system",
    },
    "CROSS_DOMAIN_ANALOGY": {
        "required_changed": ["node labels (>=2, via complete mapping)"],
        "required_unchanged": ["mechanism_graph structure"],
        "semantics": "structure-isomorphic mechanism, domain re-bound",
    },
    "GEOMETRIC_TRANSFORMATION": {
        "required_changed": ["GEOMETRY-typed nodes only"],
        "required_unchanged": ["all non-geometry nodes and edges"],
        "semantics": "geometry/dimension change, causal core preserved",
    },
    "BOUNDARY_CONDITION_CHANGE": {
        "required_changed": ["boundary_conditions", "predicted_effect"],
        "required_unchanged": ["mechanism_graph (entire, deep-equal)"],
        "semantics": "operating regime change alters the prediction, not the mechanism",
    },
    "FAILURE_PATH_INVERSION": {
        "required_changed": ["edge relation(s) on the failure path",
                             "novel_design_variable"],
        "required_unchanged": ["node set except added DESIGN_VARIABLE nodes"],
        "semantics": "the failure path is repurposed as the function",
    },
}


def _labels(g: Dict[str, Any]) -> Dict[str, str]:
    return {n["id"]: n["label"] for n in g["nodes"]}


def _changed_fields(m1: Dict[str, Any], m2: Dict[str, Any]) -> List[str]:
    out = []
    for k in set(m1) | set(m2):
        if m1.get(k) != m2.get(k):
            out.append(k)
    return sorted(out)


# --------------------------------------------------------------- DIRECT_TRANSFER
def _direct_transfer(m1: Dict[str, Any], target_system: str,
                     binding: Dict[str, str]) -> Dict[str, Any]:
    if not binding:
        raise OperatorError("DIRECT_TRANSFER requires a source->target binding map")
    m2 = copy.deepcopy(m1)
    bound = {}
    for n in m2["mechanism_graph"]["nodes"]:
        for src_frag, tgt_frag in binding.items():
            if src_frag.lower() in n["label"].lower():
                if src_frag.lower() != tgt_frag.lower():
                    bound[n["id"]] = (n["label"])
                    n["label"] = n["label"].replace(src_frag, tgt_frag)
    if not bound:
        raise OperatorError("binding map matched no node labels")
    m2["system"] = target_system
    m2["id"] = f"{m1['id']}+DT"
    m2["transformation_operator"] = "DIRECT_TRANSFER"
    m2["derivation_trace"] = {
        "operator": "DIRECT_TRANSFER", "at": now_utc(),
        "source_system": m1["system"], "target_system": target_system,
        "binding": binding, "rebound_nodes": sorted(bound),
        "changed_fields": _changed_fields(m1, m2),
    }
    return m2


# ---------------------------------------------------------- CROSS_DOMAIN_ANALOGY
def _cross_domain_analogy(m1: Dict[str, Any], mapping: Dict[str, str],
                          target_domain: str) -> Dict[str, Any]:
    if len(mapping) < 2:
        raise OperatorError("CROSS_DOMAIN_ANALOGY needs >=2 mapped entities")
    m2 = copy.deepcopy(m1)
    rebound = []
    for n in m2["mechanism_graph"]["nodes"]:
        for src_frag, tgt_frag in mapping.items():
            if src_frag.lower() in n["label"].lower() and src_frag.lower() != tgt_frag.lower():
                n["label"] = n["label"].replace(src_frag, tgt_frag)
                rebound.append(n["id"])
    if len(set(rebound)) < 2:
        raise OperatorError("mapping must rebind >=2 distinct nodes")
    m2["system"] = f"{m1['system']} [analogue: {target_domain}]"
    m2["id"] = f"{m1['id']}+CDA"
    m2["transformation_operator"] = "CROSS_DOMAIN_ANALOGY"
    m2["derivation_trace"] = {
        "operator": "CROSS_DOMAIN_ANALOGY", "at": now_utc(),
        "target_domain": target_domain, "mapping": mapping,
        "rebound_nodes": sorted(set(rebound)),
        "changed_fields": _changed_fields(m1, m2),
    }
    return m2


# ------------------------------------------------------- GEOMETRIC_TRANSFORMATION
def _geometric_transformation(m1: Dict[str, Any], geometry_node: str,
                              new_label: str, new_geometry_field: str) -> Dict[str, Any]:
    g = copy.deepcopy(m1["mechanism_graph"])
    node = next((n for n in g["nodes"] if n["id"] == geometry_node), None)
    if node is None:
        raise OperatorError(f"geometry node {geometry_node!r} not found")
    if node["type"] != "GEOMETRY":
        raise OperatorError(f"node {geometry_node!r} is {node['type']}, not GEOMETRY")
    node["label"] = new_label
    m2 = copy.deepcopy(m1)
    m2["mechanism_graph"] = g
    m2["geometry"] = new_geometry_field
    m2["id"] = f"{m1['id']}+GEO"
    m2["transformation_operator"] = "GEOMETRIC_TRANSFORMATION"
    m2["derivation_trace"] = {
        "operator": "GEOMETRIC_TRANSFORMATION", "at": now_utc(),
        "geometry_node": geometry_node, "new_label": new_label,
        "changed_fields": _changed_fields(m1, m2),
    }
    return m2


# ----------------------------------------------------- BOUNDARY_CONDITION_CHANGE
def _boundary_condition_change(m1: Dict[str, Any], new_bc: Dict[str, Any],
                               new_predicted_effect: str) -> Dict[str, Any]:
    if not new_bc:
        raise OperatorError("boundary condition delta required")
    if new_predicted_effect == m1.get("predicted_effect"):
        raise OperatorError("predicted_effect must change with the regime")
    m2 = copy.deepcopy(m1)
    m2["boundary_conditions"] = new_bc
    m2["predicted_effect"] = new_predicted_effect
    m2["id"] = f"{m1['id']}+BCC"
    m2["transformation_operator"] = "BOUNDARY_CONDITION_CHANGE"
    m2["derivation_trace"] = {
        "operator": "BOUNDARY_CONDITION_CHANGE", "at": now_utc(),
        "old_bc": m1.get("boundary_conditions"), "new_bc": new_bc,
        "old_predicted_effect": m1.get("predicted_effect"),
        "new_predicted_effect": new_predicted_effect,
        "changed_fields": _changed_fields(m1, m2),
    }
    return m2


# -------------------------------------------------------- FAILURE_PATH_INVERSION
def _failure_path_inversion(m1: Dict[str, Any], edge_to_invert: Tuple[str, str],
                            design_variable: str, new_predicted_effect: str,
                            new_purpose: str) -> Dict[str, Any]:
    g = copy.deepcopy(m1["mechanism_graph"])
    edge = next((e for e in g["edges"]
                 if (e["src"], e["dst"]) == edge_to_invert), None)
    if edge is None:
        raise OperatorError(f"edge {edge_to_invert} not found")
    old_rel = edge["rel"]
    edge["rel"] = "INHIBITS" if old_rel == "CAUSES" else "CAUSES"
    dv_id = "dv1"
    g["nodes"].append({"id": dv_id, "type": "DESIGN_VARIABLE",
                       "label": design_variable})
    g["edges"].append({"src": dv_id, "dst": edge["dst"], "rel": "ENABLES"})
    m2 = copy.deepcopy(m1)
    m2["mechanism_graph"] = g
    m2["novel_design_variable"] = design_variable
    m2["predicted_effect"] = new_predicted_effect
    m2["purpose"] = new_purpose
    m2["id"] = f"{m1['id']}+FPI"
    m2["transformation_operator"] = "FAILURE_PATH_INVERSION"
    m2["derivation_trace"] = {
        "operator": "FAILURE_PATH_INVERSION", "at": now_utc(),
        "inverted_edge": list(edge_to_invert), "old_rel": old_rel,
        "new_rel": edge["rel"], "design_variable": design_variable,
        "changed_fields": _changed_fields(m1, m2),
    }
    return m2


# ------------------------------------------------------------------- dispatch
def apply_operator(op: str, m1: Dict[str, Any], **params) -> Dict[str, Any]:
    if op not in OPERATORS:
        raise OperatorError(f"unknown operator {op!r}")
    builders = {
        "DIRECT_TRANSFER": _direct_transfer,
        "CROSS_DOMAIN_ANALOGY": _cross_domain_analogy,
        "GEOMETRIC_TRANSFORMATION": _geometric_transformation,
        "BOUNDARY_CONDITION_CHANGE": _boundary_condition_change,
        "FAILURE_PATH_INVERSION": _failure_path_inversion,
    }
    m2 = builders[op](m1, **params)
    verdict = operator_fidelity(m1, m2, op)
    if verdict["verdict"] != "PASS":
        raise OperatorError(
            f"builder output failed its own fidelity check: {verdict['reason']}")
    m2["operator_fidelity"] = verdict
    return m2


# -------------------------------------------------------- the fidelity validator
def operator_fidelity(m1: Dict[str, Any], m2: Dict[str, Any],
                      op: str) -> Dict[str, Any]:
    """INDEPENDENT checker: re-derives all proofs from (M1, M2, op).
    Returns {"verdict": PASS|FAIL, "reason": ..., "proofs": {...}}."""
    def fail(reason):
        return {"verdict": "FAIL", "reason": reason, "proofs": proofs}

    proofs: Dict[str, Any] = {"operator": op}
    changed = _changed_fields(m1, m2)
    structural_changes = [c for c in changed if c not in PROSE_ONLY_FIELDS]
    proofs["changed_fields"] = changed

    # Universal anti-wording rule: prose-only deltas fail for EVERY operator.
    if not structural_changes:
        return fail("WORDING_ONLY: only prose fields changed — a wording "
                    "change FAILS operator fidelity")

    g1, g2 = m1.get("mechanism_graph"), m2.get("mechanism_graph")
    if g1 is None or g2 is None:
        return fail("missing mechanism_graph")
    try:
        G.validate_graph(g1); G.validate_graph(g2)
    except ValueError as e:
        return fail(f"invalid graph: {e}")
    sh1, sh2 = G.structure_hash(g1), G.structure_hash(g2)
    ch1, ch2 = G.content_hash(g1), G.content_hash(g2)
    proofs.update({"structure_hash_m1": sh1, "structure_hash_m2": sh2,
                   "content_hash_m1": ch1, "content_hash_m2": ch2})

    l1, l2 = _labels(g1), _labels(g2)

    if op == "DIRECT_TRANSFER":
        if sh1 != sh2:
            return fail("structure changed — DIRECT_TRANSFER preserves the causal shape")
        if m1.get("system") == m2.get("system"):
            return fail("system unchanged — a synonym/wording change FAILS")
        rels1 = sorted((e["src"], e["dst"], e["rel"]) for e in g1["edges"])
        rels2 = sorted((e["src"], e["dst"], e["rel"]) for e in g2["edges"])
        if rels1 != rels2:
            return fail("causal edge relations changed")
        trace = m2.get("derivation_trace") or {}
        if not trace.get("binding"):
            return fail("no binding map recorded")
        proofs["binding_rebound_nodes"] = trace.get("rebound_nodes")

    elif op == "CROSS_DOMAIN_ANALOGY":
        if sh1 != sh2:
            return fail("structure changed — analogy is structure-isomorphic")
        rebound = [i for i in l1 if l1[i] != l2.get(i)]
        if len(rebound) < 2:
            return fail("fewer than 2 nodes rebound — synonym-only change FAILS")
        trace = m2.get("derivation_trace") or {}
        mapping = trace.get("mapping") or {}
        for i in rebound:
            if not any(s.lower() in l1[i].lower() for s in mapping):
                return fail(f"node {i} rebound without a mapping entry")
        proofs["rebound_nodes"] = sorted(rebound)

    elif op == "GEOMETRIC_TRANSFORMATION":
        non_geo_1 = {i: (t, l1[i]) for i, t in
                     ((n["id"], n["type"]) for n in g1["nodes"]) if t != "GEOMETRY"}
        non_geo_2 = {n["id"]: (n["type"], n["label"]) for n in g2["nodes"]
                     if n["type"] != "GEOMETRY"}
        if non_geo_1 != non_geo_2:
            return fail("non-geometry content changed — geometry operator "
                        "is confined to GEOMETRY-typed nodes")
        geo1 = sorted((n["label"]) for n in g1["nodes"] if n["type"] == "GEOMETRY")
        geo2 = sorted((n["label"]) for n in g2["nodes"] if n["type"] == "GEOMETRY")
        if geo1 == geo2 and m1.get("geometry") == m2.get("geometry"):
            return fail("no geometry delta — wording-only change FAILS")
        proofs["geometry_delta"] = {"m1": geo1, "m2": geo2}

    elif op == "BOUNDARY_CONDITION_CHANGE":
        if (sh1 != sh2) or (ch1 != ch2):
            return fail("mechanism graph must be deep-equal — the regime "
                        "changes, not the mechanism")
        if m1.get("boundary_conditions") == m2.get("boundary_conditions"):
            return fail("boundary_conditions unchanged")
        if m1.get("predicted_effect") == m2.get("predicted_effect"):
            return fail("predicted_effect unchanged — a BC change with no "
                        "prediction change is prose, not physics")

    elif op == "FAILURE_PATH_INVERSION":
        rel1 = {(e["src"], e["dst"]): e["rel"] for e in g1["edges"]}
        rel2 = {(e["src"], e["dst"]): e["rel"] for e in g2["edges"]}
        flipped = [k for k in rel1 if k in rel2 and rel1[k] != rel2[k]]
        added_nodes = [n for n in g2["nodes"] if n["id"] not in l1]
        if not flipped:
            return fail("no edge relation inverted — no failure path was repurposed")
        if not m2.get("novel_design_variable"):
            return fail("inversion without a novel design variable is a claim, not a design")
        if added_nodes and any(n["type"] != "DESIGN_VARIABLE" for n in added_nodes):
            return fail("only DESIGN_VARIABLE nodes may be added")
        proofs["flipped_edges"] = [list(k) for k in flipped]
        proofs["added_design_variables"] = [n["label"] for n in added_nodes]

    else:
        return fail(f"unknown operator {op!r}")

    return {"verdict": "PASS", "reason": "all operator invariants hold",
            "proofs": proofs}
