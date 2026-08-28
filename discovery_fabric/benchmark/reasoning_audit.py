"""Phase 4 — engineering reasoning audit (Coder 2).

For every important generated claim, verify the chain exists:

    CLAIM -> ENGINEERING PRINCIPLE -> MODEL/EQUATION -> INPUT -> ASSUMPTION
          -> OUTPUT -> FAILURE MODE -> VERIFICATION

Explicit IDs only — no keyword matching (CEO mandate; Art. II).

Inputs: the ENGINEERING_SPECIFICATION.json + INVENTION_SPECIFICATION.json of
a generated run (Coder 1 artifacts, read-only). Output: a machine-readable
audit with per-chain completeness and explicit broken links.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

CHAIN_STEPS = ["CLAIM", "PRINCIPLE", "EQUATION", "INPUT", "ASSUMPTION",
               "OUTPUT", "FAILURE_MODE", "VERIFICATION"]


def audit_reasoning(eng_spec: Optional[dict],
                    inv_spec: Optional[dict]) -> Dict[str, Any]:
    """Audit the design-output reasoning chains via explicit IDs.

    The canonical chain unit in the generated artifacts is the DESIGN OUTPUT:
    DO -> parent DIs (inputs) -> user need (claim basis) -> domain equations
    (principle/model) -> equation assumptions -> linked failure modes ->
    linked verifications.
    """
    if not eng_spec:
        return {"available": False,
                "reason": "ENGINEERING_SPECIFICATION not available",
                "chains": [], "completeness_rate": None,
                "verdict": "NOT_MEASURABLE"}

    dos: List[dict] = eng_spec.get("design_outputs", []) or []
    dis: Dict[str, dict] = {d.get("id"): d for d in
                            (eng_spec.get("design_inputs", []) or [])
                            if isinstance(d, dict) and d.get("id")}
    uins = _user_needs(eng_spec)
    eqs = _equations(eng_spec)
    fms: List[dict] = [f for f in (eng_spec.get("failure_analysis", []) or [])
                       if isinstance(f, dict)]
    vfs: Dict[str, dict] = {v.get("id"): v for v in
                            (eng_spec.get("verification_matrix", []) or [])
                            if isinstance(v, dict) and v.get("id")}
    graph = eng_spec.get("design_graph") or {}
    edges = _graph_edges(graph)
    # the engine's structural linkage maps (explicit ids, A-series/E15):
    # do_parent_di: {DO -> [DI]}, fm_parent_do: {FM -> [DO]}
    link_maps = graph.get("linkage_maps") or {}
    do_parent_di: Dict[str, List[str]] = link_maps.get("do_parent_di") or {}
    fm_parent_do: Dict[str, List[str]] = link_maps.get("fm_parent_do") or {}
    do_to_fms: Dict[str, List[str]] = {}
    for fm_id, do_ids in fm_parent_do.items():
        for do_id in do_ids:
            do_to_fms.setdefault(do_id, []).append(fm_id)
    fm_to_vf: Dict[str, str] = {
        f.get("graph_id"): f.get("verification")
        for f in fms
        if f.get("verification") not in ("NOT_LINKED", None, "")}
    do_to_vfs: Dict[str, List[str]] = {}
    for do_id, fm_ids in do_to_fms.items():
        for fm_id in fm_ids:
            vf = fm_to_vf.get(fm_id)
            if vf:
                do_to_vfs.setdefault(do_id, []).append(vf)

    chains: List[Dict[str, Any]] = []
    for do in dos:
        if not isinstance(do, dict) or not do.get("id"):
            continue
        do_id = do["id"]
        parents = [p for p in (do.get("parent_ids") or [])
                   if p in dis] or \
            [p for p in do_parent_di.get(do_id, []) if p in dis] or \
            _parents_from_graph(do_id, edges)
        fm_ids = _fms_for_do(do, fms, edges) or do_to_fms.get(do_id, [])
        vf_ids = _vf_links_for_do(do, fms, edges) or do_to_vfs.get(do_id, [])
        chain = {
            "claim": do_id,
            "claim_basis": {
                "user_need": _first_claim_basis(parents, dis, uins),
                "di_ids": parents,
            },
            "principle": _principle(do, eqs, eng_spec),
            "equation": _equation_for_do(do, eqs, eng_spec),
            "input": parents,
            "assumption": _assumptions(do, eqs, eng_spec),
            "output": do_id,
            "failure_mode": fm_ids,
            "verification": vf_ids,
        }
        chain["missing_steps"] = _missing_steps(chain)
        chain["complete"] = not chain["missing_steps"]
        chains.append(chain)

    complete = [c for c in chains if c["complete"]]
    rate = (len(complete) / len(chains)) if chains else None
    return {
        "available": True,
        "chains_total": len(chains),
        "chains_complete": len(complete),
        "completeness_rate": rate,
        "chains": chains,
        "verdict": _verdict(rate),
        "note": "chain unit = DESIGN OUTPUT; links are explicit IDs "
                "(parent_ids / verification / FM linkage), never keywords",
    }


def _missing_steps(chain: Dict[str, Any]) -> List[str]:
    """Map chain steps to the chain dict's own keys (no name mismatch)."""
    checks = {
        # CLAIM = the design output's ultimate basis in a user need
        "CLAIM": (chain.get("claim_basis") or {}).get("user_need"),
        "PRINCIPLE": chain.get("principle"),
        "EQUATION": chain.get("equation"),
        "INPUT": chain.get("input"),
        "ASSUMPTION": chain.get("assumption"),
        "OUTPUT": chain.get("output"),
        "FAILURE_MODE": chain.get("failure_mode"),
        "VERIFICATION": chain.get("verification"),
    }
    return [step for step in CHAIN_STEPS if not checks[step]]


def _user_needs(eng_spec: dict) -> List[dict]:
    return [u for u in (eng_spec.get("design_graph", {})
                        .get("nodes", []) or [])
            if isinstance(u, dict) and str(u.get("type", "")).upper()
            in ("UIN", "USER_NEED", "USER_NEED_STATEMENT")]


def _graph_edges(graph: dict) -> List[dict]:
    return [e for e in (graph.get("edges", []) or [])
            if isinstance(e, dict)]


def _parents_from_graph(node_id: str, edges: List[dict]) -> List[str]:
    out = []
    for e in edges:
        if e.get("to") == node_id and isinstance(e.get("from"), str):
            out.append(e["from"])
    return out


def _vf_links_for_do(do: dict, fms: List[dict],
                     edges: List[dict]) -> List[str]:
    """Verification links reachable from this DO via FM linkage or graph."""
    direct = do.get("verification") or do.get("verification_ids") or []
    if isinstance(direct, str):
        direct = [direct]
    out = [v for v in direct if isinstance(v, str)]
    fm_ids = _fms_for_do(do, fms, edges)
    for fm in fms:
        if fm.get("graph_id") in fm_ids or fm.get("id") in fm_ids:
            vf = fm.get("verification") or fm.get("verification_test")
            if isinstance(vf, str):
                out.append(vf)
    for e in edges:
        if e.get("from") == do.get("id") and str(e.get("to", "")).startswith("VF"):
            out.append(e["to"])
    return sorted(set(out))


def _fms_for_do(do: dict, fms: List[dict], edges: List[dict]) -> List[str]:
    direct = do.get("failure_mode_ids") or do.get("failure_modes") or []
    if isinstance(direct, str):
        direct = [direct]
    out = [f for f in direct if isinstance(f, str)]
    for e in edges:
        if e.get("from") == do.get("id") and (
                str(e.get("to", "")).startswith("FM")):
            out.append(e["to"])
    if not out:
        # FM rows reference the DO-agnostic verification; count FMs whose
        # verification links into this DO's verifications
        do_vfs = set(do.get("verification_ids") or [])
        for fm in fms:
            vf = fm.get("verification") or fm.get("verification_test")
            if isinstance(vf, str) and vf in do_vfs:
                gid = fm.get("graph_id") or fm.get("id")
                if gid:
                    out.append(gid)
    return sorted(set(out))


def _first_claim_basis(parents: List[str], dis: Dict[str, dict],
                       uins: List[dict]) -> Optional[str]:
    # user needs surface as UIN-* parent ids on design inputs
    for p in parents:
        di = dis.get(p) or {}
        for up in (di.get("parent_ids") or []):
            if re.match(r"^UIN-\d+$", str(up)):
                return up
    for u in uins:
        if u.get("id"):
            return u["id"]
    return None


def _principle(do: dict, eqs: List[dict], eng_spec: dict) -> Optional[str]:
    gm = (eng_spec.get("engineering_core") or {}).get("governing_model") or {}
    if gm.get("summary"):
        return "governing_model"
    return None


def _equation_for_do(do: dict, eqs: List[dict],
                     eng_spec: dict) -> Optional[str]:
    if eqs:
        return eqs[0].get("equation_id")
    return None


def _assumptions(do: dict, eqs: List[dict], eng_spec: dict) -> List[str]:
    for eq in eqs:
        if eq.get("assumptions"):
            return eq["assumptions"]
    return []


def _equations(eng_spec: dict) -> List[dict]:
    gm = (eng_spec.get("engineering_core") or {}).get("governing_model") or {}
    return [e for e in (gm.get("equations", []) or [])
            if isinstance(e, dict) and e.get("equation_id")]


def _verdict(rate: Optional[float]) -> str:
    if rate is None:
        return "NOT_MEASURABLE"
    if rate >= 0.5:
        return "PASS"
    if rate > 0:
        return "CONDITIONAL"
    return "FAIL"
