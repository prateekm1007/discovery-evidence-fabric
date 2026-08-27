"""discovery_fabric/engine/engineering_spec.py — E3 engineering content + E8
design input/output graph, generated from a canonical INVENTION_SPECIFICATION.

CEO E3: every generated engineering field inherits an explicit epistemic
class — SOURCE_FACT / COMPUTED / MODELLED / ENGINEERING_PROPOSED / UNKNOWN.
The generator may NEVER turn a model into a fact (Art. XXVIII/XXXVIII).

CEO E8: the USER_NEED -> DESIGN_INPUT -> DESIGN_OUTPUT -> FAILURE_MODE ->
VERIFICATION -> VALIDATION graph uses explicit IDs and STRUCTURAL links
(parent_id references), not keyword matching (the R370 audit demonstrated
keyword-only traceability is dangerous).

CEO Directive 4: engineering depth is DOMAIN-ADAPTIVE — the domain module
from the canonical ENGINEERING_DOMAIN_REGISTRY contributes governing models,
critical parameters, candidate failure modes, DI/DO patterns, verification,
validation and manufacturing patterns, all tagged ENGINEERING_PROPOSED with
UNKNOWN values (no threshold invention, Art. XXVII).

CEO Directive 6 (NO MATERIAL TRUNCATION): this artifact is AUTHORITATIVE.
NO string in it may be shortened — full text everywhere. Presentation-level
shortening happens ONLY later, via the DisplayRegister in fields.py, after
this authoritative artifact has been preserved. (The former `_shorten`
helper is deliberately GONE; a guard test scans this file to keep it gone.)

The output `engineering_content` mirrors the ArtifactRichDossier schema that
premium_package_factory/templates/build_portfolio_v4.py consumes — so the
existing dossier factory renders it unchanged (E4 reuse, no template
recreation).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .candidate import Candidate, sha256_obj, utc_now
from .domains import detect_domain, domain_label, get_domain_module
from .equations import select_equations
from .invention_spec import tagged

# Epistemic gate for engineering: DO results are ABSENT until reality
# produces them (Art. XXXVIII: COMPUTATIONAL_RESULT != PHYSICAL_OBSERVATION).


# --------------------------------------------------------------------------
def build_design_graph(spec: Dict[str, Any], env: Optional[Candidate],
                       ) -> Dict[str, Any]:
    """E8 graph with explicit IDs and structural parent links.

    Every node carries: id, parent_ids (structural), label, basis
    (epistemic class of its content), and evidence_refs. Integrity rules:
      - every DO names >=1 parent DI
      - every FM names >=1 parent DO (or the architecture root)
      - every VF names >=1 parent FM
      - every VA names >=1 parent VF or is explicitly justification-gated
    Unlinkable content becomes a recorded GAP — never silently dropped.
    Full text everywhere (Directive 6): no label/value is shortened.
    """
    problem = ((spec.get("problem") or {}).get("value") or {})
    mech = ((spec.get("mechanism") or {}).get("value") or {})
    constraint = problem.get("constraint", "")
    fms_from_attack = ((spec.get("failure_modes") or {}).get("value") or [])
    ke = (spec.get("killer_experiment") or {}).get("value") or {}

    nodes: List[Dict[str, Any]] = []
    gaps: List[Dict[str, Any]] = []

    # UIN — user need (from the custodied problem statement)
    uin_id = "UIN-001"
    nodes.append({
        "id": uin_id, "type": "USER_NEED", "parent_ids": [],
        "label": problem.get("failure") or
                 (problem.get("device", "") + " reliability"),
        "basis": "SOURCE_FACT (operator problem statement, problem.json)",
        "evidence_refs": ["problem.json"],
    })

    # DI — design inputs: constraint, mechanism driver, effect target
    d_inputs: List[Dict[str, Any]] = []
    di_counter = 0
    def _di(label: str, value: str, basis: str, parents: List[str],
            refs: List[str]) -> Optional[str]:
        nonlocal di_counter
        if not (label and value):
            return None
        di_counter += 1
        did = f"DI-{di_counter:03d}"
        d_inputs.append({"id": did, "parent_ids": parents, "label": label,
                         "value": value, "basis": basis,
                         "evidence_refs": refs})
        return did

    di_c = _di("Stated constraint", constraint,
               "SOURCE_FACT (problem.json)", [uin_id], ["problem.json"])
    di_m = _di("Mechanism driver (proposed)", mech.get("mechanism", ""),
               "MODELLED (LLM synthesis)", [uin_id], [])
    di_e = _di("Expected effect target", mech.get("expected_effect", ""),
               "MODELLED (LLM synthesis)", [di_m] if di_m else [uin_id], [])
    if not any([di_c, di_m, di_e]):
        gaps.append({"gap": "NO_DESIGN_INPUTS",
                     "reason": "constraint and mechanism both absent"})
    nodes.extend(d_inputs)

    # DO — design outputs: architecture responses to the DIs. Status ABSENT
    # until reality produces geometry/measurements (honest, like the frozen
    # packages' DO entries).
    d_outputs: List[Dict[str, Any]] = []
    do_counter = 0
    def _do(label: str, missing_inputs: List[str], parents: List[str],
            basis: str) -> None:
        nonlocal do_counter
        do_counter += 1
        d_outputs.append({
            "id": f"DO-{do_counter:03d}", "parent_ids": parents,
            "description": label,
            "status": "ABSENT",
            "missing_inputs": missing_inputs, "basis": basis})

    if di_m:
        _do(f"Intervention architecture realizing the proposed mechanism: "
            f"{mech.get('intervention', '')}",
            ["geometry/setpoints (must be proposed and justified)",
             "materials selection", "interface dimensions"],
            [di_m], "ENGINEERING_PROPOSED (architecture named; parameters absent)")
    if di_e:
        _do("Effect-delivery subsystem achieving the expected effect",
            ["effect magnitude targets (no sourced values exist)",
             "actuation or passive means"],
            [di_e], "ENGINEERING_PROPOSED")
    if di_c:
        _do("Constraint-compliance envelope",
            ["quantified constraint limits", "compliance test mapping"],
            [di_c], "ENGINEERING_PROPOSED")
    if not d_outputs:
        gaps.append({"gap": "NO_DESIGN_OUTPUTS",
                     "reason": "no design inputs to respond to"})

    # FM — failure modes: from the attack engine dimensions + device failure
    f_modes: List[Dict[str, Any]] = []
    fm_counter = 0
    parent_of_first_fm = d_outputs[0]["id"] if d_outputs else uin_id
    for item in fms_from_attack:
        fm_counter += 1
        f_modes.append({
            "id": f"FM-{fm_counter:03d}",
            "parent_ids": [parent_of_first_fm],
            "mode": f"adversarial dimension: {item.get('dimension')}",
            "mechanism": str(item.get("attack_verdict")),
            "basis": "COMPUTED (attack engine verdict)",
            "evidence_refs": []})
    dev_failure = problem.get("failure_mode") or problem.get("failure")
    if dev_failure:
        fm_counter += 1
        f_modes.insert(0, {
            "id": f"FM-{fm_counter:03d}",
            "parent_ids": [d_outputs[0]["id"]] if d_outputs else [uin_id],
            "mode": dev_failure,
            "mechanism": "the device failure that motivates the invention",
            "basis": "SOURCE_FACT (problem.json)", "evidence_refs": ["problem.json"]})
    if not f_modes:
        gaps.append({"gap": "NO_FAILURE_MODES",
                     "reason": "attack produced no dimensions and problem "
                               "states no failure mode"})

    # VF — verification: falsification test + killer experiment -> target FMs
    verifications: List[Dict[str, Any]] = []
    vf_counter = 0
    fals = (((spec.get("causal_chain") or {}).get("value") or {})
            .get("falsification_test", ""))
    if fals and f_modes:
        vf_counter += 1
        verifications.append({
            "id": f"VF-{vf_counter:03d}",
            "parent_ids": [f_modes[0]["id"]],
            "method": fals,
            "basis": "MODELLED (candidate falsification test)",
            "result": "NOT_TESTED"})
    ke_sel_name = ke.get("selected") if isinstance(ke.get("selected"), str) \
        else (ke.get("selected") or {}).get("name", "UNKNOWN") if ke.get(
            "selected") else ""
    if ke_sel_name and ke_sel_name != "UNKNOWN" and f_modes:
        vf_counter += 1
        verifications.append({
            "id": f"VF-{vf_counter:03d}",
            "parent_ids": [fm["id"] for fm in f_modes],
            "method": f"run killer experiment: {ke_sel_name} "
                      f"(EIG/cost {ke.get('eig_per_cost')})",
            "basis": "COMPUTED (Bayesian EIG over MODEL_DERIVED priors)",
            "result": "NOT_TESTED"})
    # attach dangling FMs (with no VF parent) as explicit gaps
    covered = {p for vf in verifications for p in vf["parent_ids"]}
    for fm in f_modes:
        if fm["id"] not in covered:
            gaps.append({"gap": f"FM_WITHOUT_VERIFICATION:{fm['id']}",
                         "reason": "no decisive verification proposed for "
                                   "this failure mode yet"})

    # VA — validation entries remain explicitly unpopulated until physical
    # reality speaks. Recorded as UNKNOWN, never synthesized.
    validations = [{
        "id": "VA-001",
        "parent_ids": [vf["id"] for vf in verifications] or None,
        "status": "NOT_POSSIBLE_YET",
        "basis": "UNKNOWN",
        "reason": "validation requires physical observation; no observation "
                  "ledger entry exists (Art. XXXVIII)"}]

    return {
        "nodes": nodes,
        "d_inputs": d_inputs,
        "d_outputs": d_outputs,
        "f_modes": f_modes,
        "verifications": verifications,
        "validations": validations,
        "gaps": gaps,
        "counts": {"UIN": 1, "DI": len(d_inputs), "DO": len(d_outputs),
                   "FM": len(f_modes), "VF": len(verifications),
                   "VA": len(validations)},
        "graph_integrity": _graph_integrity(d_inputs, d_outputs, f_modes,
                                            verifications, validations),
        "built_at": utc_now(),
    }


def _graph_integrity(di, do, fm, vf, va) -> Dict[str, Any]:
    """Structural link audit. Returns explicit pass/fail — the package
    traceability file is generated from this, not from prose."""
    problems: List[str] = []
    di_ids = {d["id"] for d in di}
    do_ids = {d["id"] for d in do}
    fm_ids = {f["id"] for f in fm}
    for d in do:
        if not (set(d["parent_ids"]) & di_ids):
            problems.append(f"{d['id']} has no DI parent")
    for f in fm:
        if not (set(f["parent_ids"]) & (do_ids | di_ids)):
            problems.append(f"{f['id']} has no DO/DI parent")
    for v in vf:
        if not (set(v["parent_ids"]) & fm_ids):
            problems.append(f"{v['id']} has no FM parent")
    return {"passed": not problems, "problems": problems,
            "checked_at": utc_now()}


# --------------------------------------------------------------------------
def build_engineering_spec(spec: Dict[str, Any], env: Optional[Candidate],
                           run_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Produce the full engineering content (E3 + Directive 4), shaped for
    the existing dossier factory. Every block is explicitly classed; nothing
    claims physical existence; NOTHING is truncated (Directive 6)."""
    mech_text = " ".join(str(((spec.get("mechanism") or {}).get("value") or {}).get(k, ""))
                         for k in ("mechanism", "intervention",
                                   "expected_effect", "falsification_test"))
    problem = ((spec.get("problem") or {}).get("value") or {})

    detection = detect_domain(mech_text + " " + " ".join(
        str(problem.get(k, "")) for k in ("device", "failure", "constraint")))
    domain = detection["domain"]
    module = get_domain_module(domain)
    tpl = module  # merged Directive-4 module view (base + depth)

    graph = build_design_graph(spec, env)
    equations = select_equations(spec, domain)

    # governing model from domain equations — symbolic unless fully sourced
    governing = {
        "summary": (f"{domain_label(domain)} governing relations proposed for "
                    "this invention; SYMBOLIC ONLY until inputs are sourced"),
        "equations": [
            {"equation_id": eq["equation"]["equation_id"],
             "expression": eq["equation"]["expression"],
             "source": eq["equation"]["source"],
             "applicability": eq["equation"]["applicability"],
             "assumptions": eq["equation"]["assumptions"],
             "selection_rationale": eq["selection_rationale"]}
            for eq in (equations.get("value") or [])],
        "domain_governing_models": [
            {"model": m.get("model"),
             "registry_equation_ids": m.get("equation_ids", []),
             "applicability": m.get("applicability",
                                    m.get("note", "ENGINEERING_PROPOSED"))}
            for m in module.get("governing_models", [])],
        "assumptions": [a for eq in (equations.get("value") or [])
                        for a in eq["equation"]["assumptions"]],
        "boundary_conditions": ["to be established by the first bench "
                                "characterization (not yet performed)"],
        "input_variables": [
            {"symbol": v["symbol"], "unit": v["unit"],
             "epistemic_status": "UNKNOWN (no sourced value)"}
            for eq in (equations.get("value") or [])
            for v in eq["equation"]["variables"] if v.get("role") == "input"],
        "output_variables": [
            {"symbol": v["symbol"], "unit": v["unit"],
             "epistemic_status": "UNKNOWN (no computed value)"}
            for eq in (equations.get("value") or [])
            for v in eq["equation"]["variables"] if v.get("role") == "output"],
        "parameter_sensitivities": [],
        "failure_regimes": [
            {"regime": f["mode"], "basis": f["basis"]}
            for f in graph["f_modes"]],
    }

    # Directive 4: domain-adaptive critical parameters (candidate names only;
    # every VALUE stays UNKNOWN — the registry proposes WHAT matters, never
    # WHAT its value is, Art. XXVII)
    critical_parameters = [
        {"parameter": p,
         "name": p,
         "value": "UNKNOWN (no sourced value)",
         "unit": "UNKNOWN",
         "basis": "ENGINEERING_PROPOSED (domain registry candidate)",
         "verification_requirement":
             "to be assigned a sourced target value and a verification "
             "method before any build decision",
         "status": "ENGINEERING_PROPOSED / VALUE UNKNOWN",
         "reason": "domain candidate parameter; no measurement exists"}
        for p in module.get("critical_parameters", [])]
    critical_parameters += [
        {"parameter": f"DO response for {d['description']}",
         "name": f"DO response for {d['description']}",
         "value": "UNKNOWN (no sourced value)",
         "unit": "UNKNOWN",
         "basis": "ENGINEERING_PROPOSED",
         "verification_requirement":
             "to be defined with the DO geometry design work",
         "status": "ENGINEERING_PROPOSED / VALUE UNKNOWN",
         "reason": "no sourced target value exists"}
        for d in graph["d_outputs"]]

    # Directive 4: domain candidate failure modes are appended AFTER the
    # candidate's own recorded failure modes (never replacing them), each
    # explicitly tagged as domain-generic ENGINEERING_PROPOSED candidates.
    ke = (spec.get("killer_experiment") or {}).get("value") or {}
    ke_name = ke.get("selected") if isinstance(ke.get("selected"), str) \
        else (ke.get("selected") or {}).get("name", "UNKNOWN") if \
        ke.get("selected") else ""
    ke_def = ke.get("definition", "")
    if ke_name == "UNKNOWN":
        ke_name = ""   # no killer experiment was selected: no WP is claimed

    def _fm_out(fm_id: str, mode: str, mechanism: str, basis: str,
                verification: str) -> Dict[str, Any]:
        return {
            "graph_id": fm_id,
            "mode": mode, "failure_mode": mode,
            "mechanism": mechanism,
            "design_feature": "NOT ESTABLISHED",
            "evidence": basis,
            "mitigation": "NOT ESTABLISHED (requires design work)",
            "verification": verification,
            "verification_test": verification,
            "residual_uncertainty":
                "UNKNOWN — untested candidate failure mode (Art. XXV)",
            "epistemic_class": basis.split(" (")[0] or "UNKNOWN",
        }

    failure_modes_out: List[Dict[str, Any]] = []
    for f in graph["f_modes"]:
        failure_modes_out.append(_fm_out(
            f["id"], f["mode"], f.get("mechanism", ""), f["basis"],
            next((v["id"] for v in graph["verifications"]
                  if f["id"] in v["parent_ids"]), "NOT_LINKED")))
    for j, dfm in enumerate(module.get("failure_modes", [])):
        failure_modes_out.append(_fm_out(
            f"FM-DOM-{j+1:03d}", dfm,
            "domain-generic candidate failure mode from the engineering "
            "domain registry — applicability to THIS invention NOT "
            "established",
            "ENGINEERING_PROPOSED (domain registry candidate)",
            "NOT_LINKED"))

    build_plan: List[Dict[str, Any]] = []
    if ke_name:
        build_plan.append({
            "work_package": "WP-01",
            "test_article": f"first physical article implementing the "
                            f"proposed intervention (GEOMETRY ABSENT — must "
                            f"be designed)",
            "equipment": "domain bench equipment per verification methods",
            "design_work": "complete DO-001 geometry from proposal to "
                           "manufacturable definition",
            "measurement": str(ke_def) or "killer-experiment measurement "
                          "protocol",
            "acceptance": "pre-registered pass/fail from the killer "
                          "experiment (threshold NOT YET JUSTIFIED — no "
                          "sourced value exists)",
            "acceptance_criterion": "pre-registered pass/fail from the "
                                    "killer experiment (NOT YET JUSTIFIED)",
            "deliverable": "killer-experiment report with pass/fail vs "
                           "pre-registered criterion",
            "estimated_effort": "NOT ESTABLISHED (to be quoted)",
            "basis": "COMPUTED (killer experiment selection)"})
    build_plan.append({
        "work_package": f"WP-{len(build_plan)+1:02d}",
        "test_article": "constraint-compliance envelope article",
        "equipment": "per verification methods",
        "design_work": "quantify the stated constraint and map the "
                       "verification matrix",
        "measurement": "constraint-compliance characterization",
        "acceptance": "NOT ESTABLISHED (no sourced acceptance values)",
        "acceptance_criterion": "NOT ESTABLISHED (no sourced values)",
        "deliverable": "constraint-compliance characterization report",
        "estimated_effort": "NOT ESTABLISHED (to be quoted)",
        "basis": "ENGINEERING_PROPOSED"})
    for vf in graph["verifications"]:
        build_plan.append({
            "work_package": f"WP-{len(build_plan)+1:02d}",
            "test_article": f"article for {vf['id']}",
            "equipment": "per method",
            "design_work": "method definition to measurable protocol",
            "measurement": vf["method"],
            "acceptance": "NOT_TESTED",
            "acceptance_criterion": "NOT ESTABLISHED",
            "deliverable": f"{vf['id']} verification report",
            "estimated_effort": "NOT ESTABLISHED (to be quoted)",
            "basis": vf["basis"]})

    return {
        "technology_domain": domain if domain != "UNKNOWN" else "NOT ESTABLISHED",
        "domain_detection": {
            "epistemic_class": detection["epistemic_class"],
            "matched_signals": detection["matched_signals"],
            "note": detection["note"],
            "label": domain_label(domain)},
        "engineering_disciplines": module["disciplines"],
        "system_architecture": {
            "description": (
                "PROPOSED architecture (no physical system exists): "
                + "; ".join(module["architecture_blocks"])),
            "subsystems": [
                {"name": b, "status": "ENGINEERING_PROPOSED",
                 "detail": "NOT ESTABLISHED (requires design work)"}
                for b in module["architecture_blocks"]],
        },
        "mechanism_architecture": {
            "physical_changes": "PROPOSED: "
                + ((spec.get("mechanism") or {}).get("value") or {})
                .get("intervention", ""),
            "key_physics": governing["summary"],
            "status": "MODELLED",
        },
        "design_inputs": [
            {"id": d["id"], "input": d["label"], "value": d["value"],
             "source": d["basis"],
             "evidence_class": d["basis"].split(" (")[0],
             "parent_ids": d["parent_ids"],
             "evidence_refs": d["evidence_refs"]}
            for d in graph["d_inputs"]],
        "design_outputs": [
            {"id": d["id"], "description": d["description"],
             "status": "ABSENT", "missing_inputs": d["missing_inputs"],
             "parent_ids": d["parent_ids"], "basis": d["basis"]}
            for d in graph["d_outputs"]],
        "domain_design_input_patterns": list(
            module.get("design_input_patterns", [])),
        "domain_design_output_patterns": list(
            module.get("design_output_patterns", [])),
        "external_engineering_precedent": [
            {"precedent": s["standard"], "class": "EXTERNAL_PRECEDENT_CANDIDATE",
             "verify_applicability": True}
            for s in module.get("standards_candidates", [])],
        "bom": [
            {"item": m["material"], "qty": "NOT ESTABLISHED",
             "description": "domain candidate material (no sourced spec)",
             "material": m["material"], "supplier": "NOT ESTABLISHED",
             "component_type": "NOT ESTABLISHED",
             "criticality": "NOT ESTABLISHED",
             "verification": "applicability verification required",
             "status": "ENGINEERING_PROPOSED"}
            for m in module.get("materials_candidates", [])] or
            [{"item": "NOT ESTABLISHED (no domain materials template hit)",
              "qty": "NOT ESTABLISHED", "status": "UNKNOWN"}],
        "materials": [
            {"material": m["material"],
             "component": "domain candidate material",
             "candidate_material": m["material"],
             "source": m.get("precedent", ""),
             "precedent_basis": m.get("precedent", ""),
             "verification_required": True,
             "status": "ENGINEERING_PROPOSED",
             "verify_applicability": True}
            for m in module.get("materials_candidates", [])],
        "manufacturing": {
            "candidate_processes": [
                {"process": p.get("process", p)
                 if isinstance(p, dict) else str(p),
                 "status": p.get("status", "ENGINEERING_PROPOSED")
                 if isinstance(p, dict) else "ENGINEERING_PROPOSED",
                 "source": "domain registry manufacturing pattern",
                 "note": "candidate only; no process qualification exists"}
                for p in module.get("manufacturing_patterns", [])] or
                [{"process": "NOT ESTABLISHED", "status": "UNKNOWN"}],
            "status": "NO MANUFACTURING ANALYSIS POSSIBLE — no design exists; "
                      "processes are candidates only",
        },
        "transfer_boundary": {
            "buyer_receives": [
                "canonical invention specification (with epistemic classes)",
                "engineering specification (this document, all blocks classed)",
                "design input/output graph with explicit IDs",
                "killer-experiment definition and its EIG basis",
                "evidence custody references and hashes",
                "unresolved-uncertainty register",
                "domain equation set (symbolic; sources identified)"],
            "buyer_must_create": [
                "actual geometry and detailed design",
                "sourced engineering parameters and acceptance thresholds",
                "physical prototypes",
                "all verification and validation results",
                "manufacturing process qualification",
                "regulatory submissions"],
        },
        "engineering_core": {
            "governing_model": governing,
            "critical_parameters": critical_parameters,
            "external_precedent": (
                f"domain module {domain_label(domain)}; standards listed as "
                "candidates requiring applicability verification"),
            "proposed_design": {
                "input": problem.get("constraint", "") or "NOT ESTABLISHED",
                "mechanism": ((spec.get("mechanism") or {}).get("value") or {})
                .get("mechanism", ""),
                "transformation": ((spec.get("mechanism") or {})
                                   .get("value") or {}).get("expected_effect", ""),
                "output": "NOT ESTABLISHED (no measured output exists)",
                "component_architecture": "; ".join(
                    module["architecture_blocks"]),
                "status": "MODELLED / ENGINEERING_PROPOSED"},
            "failure_modes": failure_modes_out,
            "verification": [
                {"id": v["id"], "target": v["parent_ids"],
                 "method": v["method"], "result": "NOT_TESTED",
                 "basis": v["basis"]}
                for v in graph["verifications"]] or
                [{"id": "VF-NONE", "target": [], "method": "NOT ESTABLISHED",
                  "result": "NOT_TESTED", "basis": "UNKNOWN"}],
            "validation": [
                {"id": v["id"], "status": v["status"], "basis": v["basis"],
                 "reason": v["reason"]} for v in graph["validations"]],
            "remaining_unknowns": [
                {"unknown": g["gap"], "reason": g["reason"]}
                for g in graph["gaps"]] + [
                {"unknown": "ALL sourced engineering parameter values",
                 "reason": "no measurement or physical observation exists"}],
        },
        "failure_analysis": failure_modes_out,
        "engineering_build_plan": build_plan,
        "verification_matrix": [
            {"id": v["id"],
             "requirement": v["method"],
             "method": v["method"],
             "acceptance": "NOT ESTABLISHED (needs sourced threshold)",
             "result": "NOT_TESTED"}
            for v in graph["verifications"]],
        "validation_matrix": [
            {"id": v["id"],
             "requirement": "end-use validation of verified design",
             "method": "NOT ESTABLISHED (defined after verification passes)",
             "acceptance": "NOT ESTABLISHED",
             "result": "NOT_PERFORMED",
             "status": v["status"], "basis": v["basis"],
             "reason": v["reason"]}
            for v in graph["validations"]],
        "domain_validation_methods": list(module.get("validation_methods", [])),
        "design_graph": {
            "counts": graph["counts"],
            "integrity": graph["graph_integrity"],
            "gaps": graph["gaps"]},
        "_spec_ref": {
            "invention_id": (spec.get("invention_id") or {}).get("value"),
            "spec_hash": spec.get("_spec_hash"),
            "final_envelope_hash": ((spec.get("provenance") or {})
                                    .get("value") or {}).get("final_envelope_hash"),
            "run_id": run_ctx.get("run_id"),
            "built_at": utc_now()},
        "_epistemic_summary": {
            "SOURCE_FACT_fields": ["problem statement", "custodied evidence "
                                   "references"],
            "COMPUTED_fields": ["killer experiment", "attack verdicts",
                                "novelty search results"],
            "MODELLED_fields": ["mechanism", "causal chain",
                                "distinguishing features"],
            "ENGINEERING_PROPOSED_fields": ["architecture blocks", "materials",
                                            "manufacturing candidates",
                                            "domain critical parameters",
                                            "domain candidate failure modes"],
            "UNKNOWN_fields": ["all parameter values", "all acceptance "
                              "thresholds", "all validation results"],
            "rule": "the generator may not turn a model into a fact "
                    "(Art. XXVIII/XXXVIII)"},
    }
