"""discovery_fabric/engine/reasoning_chain.py — CEO A3: engineering
reasoning chains.

For every MAJOR engineering statement the engineering specification makes
(each selected equation, each critical parameter, each invention-specific
failure mode), this module emits an explicit reasoning chain:

    CLAIM
      -> ENGINEERING_PRINCIPLE
        -> EQUATION / MODEL
          -> INPUT
            -> ASSUMPTION
              -> OUTPUT
                -> FAILURE_MODE
                  -> VERIFICATION

Every node carries full provenance:

    node_id          stable id within the package (RC-xxx_<TYPE>)
    node_type        one of the eight chain roles above
    content          the statement itself (FULL text, never truncated)
    epistemic_class  SOURCE_FACT | COMPUTED | MODELLED |
                     ENGINEERING_PROPOSED | UNKNOWN   (Art. XXVIII)
    provenance       {origin_stage, evidence_ids, refs} — the mechanical
                     pointer chain to the custody system

This is the difference between a templated dossier and an engineering
reasoning system: a reader can walk from any engineering claim down to its
physical principle, its model, its inputs and assumptions, the failure it
guards against, and the verification that would detect it — without a
single unexplained leap.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .candidate import sha256_obj, utc_now

CHAIN_ROLES = ("CLAIM", "ENGINEERING_PRINCIPLE", "EQUATION_MODEL",
               "INPUT", "ASSUMPTION", "OUTPUT", "FAILURE_MODE",
               "VERIFICATION")


def _node(chain_id: str, idx: int, role: str, content: str,
          epistemic_class: str, origin_stage: str,
          evidence_ids: Optional[List[str]] = None,
          refs: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "node_id": f"{chain_id}-{idx:02d}_{role}",
        "parent_ids": [f"{chain_id}-{idx - 1:02d}_{CHAIN_ROLES[idx - 1]}"]
        if idx else [],
        "node_type": role,
        "content": content,
        "epistemic_class": epistemic_class,
        "provenance": {
            "origin_stage": origin_stage,
            "evidence_ids": list(evidence_ids or []),
            "refs": refs or {},
        },
    }


def _chain_for_equation(gm_row: Dict[str, Any], idx: int,
                        failure_links: Dict[str, List[str]],
                        verification_links: Dict[str, List[str]],
                        evidence_ids: List[str]) -> Dict[str, Any]:
    """Build one chain from a FLATTENED governing-model row (equation_id,
    name, expression, source, applicability, assumptions,
    selection_rationale) as stored in engineering_core.governing_model."""
    rationale = gm_row.get("selection_rationale") or {}
    eq_id = gm_row.get("equation_id", "UNKNOWN")
    name = gm_row.get("name", "UNKNOWN")
    expression = gm_row.get("expression", "UNKNOWN")
    source_text = (gm_row.get("source") or {}).get("text", "UNKNOWN") \
        if isinstance(gm_row.get("source"), dict) else \
        str(gm_row.get("source", "UNKNOWN"))
    applicability = (gm_row.get("applicability") or {}).get("condition", "") \
        if isinstance(gm_row.get("applicability"), dict) else \
        str(gm_row.get("applicability", ""))
    assumptions = list(gm_row.get("assumptions", []) or [])
    cid = f"RC-EQ{idx:03d}"
    fms = failure_links.get(eq_id, [])
    vfs = verification_links.get(eq_id, [])
    nodes = [
        _node(cid, 0, "CLAIM",
              f"{name} governs the behavior of this invention's primary "
              f"output within its stated applicability",
              "MODELLED", "ENGINEERING_SPEC",
              refs={"equation_id": eq_id,
                    "verdict": rationale.get("verdict", "UNKNOWN")}),
        _node(cid, 1, "ENGINEERING_PRINCIPLE",
              source_text,
              "EXTERNAL_PRECEDENT", "EQUATION_LIBRARY",
              refs={"source_epistemic_class":
                    (gm_row.get("source") or {}).get("epistemic_class",
                                                     "EXTERNAL_PRECEDENT")
                    if isinstance(gm_row.get("source"), dict)
                    else "EXTERNAL_PRECEDENT"}),
        _node(cid, 2, "EQUATION_MODEL",
              f"{expression}  [{eq_id}]",
              "EXTERNAL_PRECEDENT", "EQUATION_LIBRARY",
              refs={"applicability": applicability,
                    "applicability_verdict": rationale.get("verdict",
                                                           "UNKNOWN"),
                    "applicability_reason": rationale.get("reason",
                                                          "UNKNOWN")}),
        _node(cid, 3, "INPUT",
              "all input variables UNKNOWN (no sourced value) — see "
              "governing_model.input_variables",
              "UNKNOWN", "ENGINEERING_SPEC",
              refs={"numeric_evaluation": "FORBIDDEN until every input is "
                                          "SOURCE_FACT/COMPUTED (Art. "
                                          "XXVII/XXXVIII)"}),
        _node(cid, 4, "ASSUMPTION",
              "Model assumptions: " + "; ".join(assumptions)
              if assumptions else
              "explicit assumptions: none beyond the applicability condition",
              "MODELLED", "EQUATION_LIBRARY",
              refs={"assumption_check": rationale.get("assumption_check")}),
        _node(cid, 5, "OUTPUT",
              "no computed value exists (no sourced inputs)",
              "UNKNOWN", "ENGINEERING_SPEC",
              refs={"numeric_evaluation": "FORBIDDEN until every input is "
                                          "SOURCE_FACT/COMPUTED"}),
        _node(cid, 6, "FAILURE_MODE",
              "Failure modes this relation informs: " +
              (", ".join(fms) if fms else
               "NOT_LINKED — no failure mode references this model yet"),
              "ENGINEERING_PROPOSED", "FAILURE_ANALYSIS",
              refs={"failure_mode_ids": fms}),
        _node(cid, 7, "VERIFICATION",
              "Verification: " +
              (", ".join(vfs) if vfs else
               "proposed — bench characterization per domain verification "
               "methods; NOT_TESTED"),
              "MODELLED", "VERIFICATION_PLANNING",
              refs={"verification_ids": vfs}),
    ]
    return {"chain_id": cid, "subject": f"equation:{eq_id}",
            "nodes": nodes}


def _chain_for_parameter(param: Dict[str, Any], idx: int,
                         vf_ids: List[str], evidence_ids: List[str]
                         ) -> Dict[str, Any]:
    name = param.get("parameter", "UNNAMED")
    cid = f"RC-CP{idx:03d}"
    pid = param.get("parameter_id", "UNKNOWN")
    nodes = [
        _node(cid, 0, "CLAIM",
              f"Critical parameter '{name}' materially determines whether "
              f"this invention's mechanism achieves its expected effect",
              "ENGINEERING_PROPOSED", "ENGINEERING_SPEC",
              refs={"parameter_id": pid}),
        _node(cid, 1, "ENGINEERING_PRINCIPLE",
              param.get("principle", "domain engineering principle per the "
                                     "engineering domain registry"),
              "ENGINEERING_PROPOSED", "DOMAIN_REGISTRY",
              refs={"domain": param.get("domain", "UNKNOWN")}),
        _node(cid, 2, "EQUATION_MODEL",
              param.get("linked_equation_id") and
              f"appears in {param['linked_equation_id']}" or
              "no governing equation linked yet (linkage NOT_ESTABLISHED)",
              "UNKNOWN", "EQUATION_LIBRARY",
              refs={"equation_id": param.get("linked_equation_id")}),
        _node(cid, 3, "INPUT",
              f"value = {param.get('value', 'UNKNOWN')} "
              f"(value_status {param.get('value_status', 'UNKNOWN')}); "
              f"unit {param.get('unit', 'UNKNOWN')}",
              param.get("value_status", "UNKNOWN"), "ENGINEERING_SPEC",
              refs={"source": param.get("source"),
                    "source_hash": param.get("source_hash")}),
        _node(cid, 4, "ASSUMPTION",
              param.get("derivation", "no derivation recorded") +
              (". Assumptions: " + "; ".join(param["assumptions"])
               if param.get("assumptions") else ""),
              "MODELLED", "ENGINEERING_SPEC",
              refs={"assumptions": param.get("assumptions", [])}),
        _node(cid, 5, "OUTPUT",
              f"uncertainty: {param.get('uncertainty', 'UNKNOWN')}",
              "UNKNOWN", "ENGINEERING_SPEC",
              refs={"uncertainty": param.get("uncertainty")}),
        _node(cid, 6, "FAILURE_MODE",
              param.get("failure_consequence",
                        "NOT ESTABLISHED — the failure consequence of "
                        "losing control of this parameter has not been "
                        "analyzed yet"),
              "ENGINEERING_PROPOSED", "FAILURE_ANALYSIS",
              refs={}),
        _node(cid, 7, "VERIFICATION",
              param.get("verification_method", "NOT ESTABLISHED") +
              ("; linked: " + ", ".join(vf_ids) if vf_ids else
               "; NOT_LINKED to a verification entry yet"),
              "MODELLED", "VERIFICATION_PLANNING",
              refs={"verification_ids": vf_ids}),
    ]
    return {"chain_id": cid, "subject": f"parameter:{pid}", "nodes": nodes}


def _chain_for_failure(fm: Dict[str, Any], idx: int, vf_id: str,
                       ) -> Dict[str, Any]:
    fid = fm.get("graph_id", f"FM-UNK-{idx:03d}")
    cid = f"RC-FM{idx:03d}"
    detect = fm.get("detectability", "NOT ESTABLISHED")
    severity = fm.get("severity", "UNKNOWN")
    sev_basis = fm.get("severity_basis", "NOT ESTABLISHED")
    design_control = fm.get("design_control", "NOT ESTABLISHED")
    kill = fm.get("kill_condition", "NOT ESTABLISHED")
    nodes = [
        _node(cid, 0, "CLAIM",
              f"Failure mode '{fm.get('failure_mode', fm.get('mode', ''))}' "
              f"is a candidate failure of this invention's design",
              fm.get("epistemic_class", "ENGINEERING_PROPOSED"),
              "FAILURE_ANALYSIS", refs={"failure_mode_id": fid}),
        _node(cid, 1, "ENGINEERING_PRINCIPLE",
              fm.get("physical_mechanism", "NOT ESTABLISHED"),
              "ENGINEERING_PROPOSED", "DOMAIN_REGISTRY",
              refs={"domain_basis": fm.get("domain_basis", "UNKNOWN")}),
        _node(cid, 2, "EQUATION_MODEL",
              fm.get("linked_equation_id") and
              f"modeled by {fm['linked_equation_id']}" or
              "no quantitative model linked (NOT_ESTABLISHED)",
              "UNKNOWN", "EQUATION_LIBRARY",
              refs={"equation_id": fm.get("linked_equation_id")}),
        _node(cid, 3, "INPUT",
              f"trigger: {fm.get('trigger', 'NOT ESTABLISHED')}",
              "ENGINEERING_PROPOSED", "FAILURE_ANALYSIS", refs={}),
        _node(cid, 4, "ASSUMPTION",
              f"detectability basis: {detect}",
              "ENGINEERING_PROPOSED", "FAILURE_ANALYSIS", refs={}),
        _node(cid, 5, "OUTPUT",
              f"severity basis: {severity} — {sev_basis}",
              "UNKNOWN", "FAILURE_ANALYSIS", refs={}),
        _node(cid, 6, "FAILURE_MODE",
              f"design control: {design_control}; kill condition: {kill}",
              "ENGINEERING_PROPOSED", "FAILURE_ANALYSIS",
              refs={"graph_id": fid}),
        _node(cid, 7, "VERIFICATION",
              vf_id if vf_id not in ("NOT_LINKED", "", None) else
              "NOT_LINKED — no decisive verification proposed yet "
              "(recorded as a design-graph gap)",
              "MODELLED", "VERIFICATION_PLANNING",
              refs={"verification_id": vf_id}),
    ]
    return {"chain_id": cid, "subject": f"failure_mode:{fid}", "nodes": nodes}


def build_reasoning_chains(spec: Dict[str, Any], eng: Dict[str, Any],
                           ) -> Dict[str, Any]:
    """Assemble all reasoning chains from the engineering specification's
    own statements. Deterministic: same spec+eng -> same chains."""
    equations = (eng.get("engineering_core", {})
                 .get("governing_model", {}).get("equations", []))
    params = eng.get("engineering_core", {}).get("critical_parameters", [])
    fms = eng.get("failure_analysis", [])
    vms = eng.get("verification_matrix", [])
    ev_index = spec.get("_evidence_index") or {}
    ev_ids = sorted(ev_index.keys())

    # equation -> FM/VF links via the design graph ids recorded on rows
    failure_links: Dict[str, List[str]] = {}
    for fm in fms:
        eqid = fm.get("linked_equation_id")
        if eqid:
            failure_links.setdefault(eqid, []).append(fm.get("graph_id"))
    verification_links: Dict[str, List[str]] = {
        eq.get("equation_id"): [] for eq in equations}
    vf_by_fm = {}
    for v in eng.get("engineering_core", {}).get("verification", []):
        for target in v.get("target", []) or []:
            vf_by_fm[target] = v.get("id")

    chains = []
    for i, gm_row in enumerate(equations, 1):
        eqid = gm_row.get("equation_id", "UNKNOWN")
        chains.append(_chain_for_equation(
            gm_row, i,
            {eqid: failure_links.get(eqid, [])},
            {eqid: verification_links.get(eqid, [])}, ev_ids))
    for i, p in enumerate(params, 1):
        chains.append(_chain_for_parameter(
            p, i, [], ev_ids))
    for i, fm in enumerate(fms, 1):
        chains.append(_chain_for_failure(
            fm, i, fm.get("verification", "NOT_LINKED")))

    return {
        "provenance_rule": ("every node carries node_type, content, "
                            "epistemic_class and a provenance pointer "
                            "(origin_stage, evidence_ids, refs); no node "
                            "asserts reality without a SOURCE_FACT-class "
                            "provenance (Art. XXXVIII)"),
        "chain_roles": list(CHAIN_ROLES),
        "counts": {
            "equation_chains": sum(1 for c in chains
                                   if c["subject"].startswith("equation:")),
            "parameter_chains": sum(1 for c in chains
                                    if c["subject"].startswith("parameter:")),
            "failure_chains": sum(1 for c in chains
                                  if c["subject"].startswith("failure_mode:")),
            "total_chains": len(chains),
            "total_nodes": sum(len(c["nodes"]) for c in chains),
        },
        "chains": chains,
        "built_at": utc_now(),
        "hash": None,  # filled by caller (needs the full artifact)
    }
