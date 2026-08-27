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

CEO A4: the engine must prove WHY the domain and each equation apply to the
ACTUAL invention. `why_this_domain` records the matched signals with their
basis; each equation carries an invention-specific applicability judgment
(APPLICABLE / CONDITIONAL / REJECTED) and rejected equations are excluded
from the governing model but recorded with reasons.

CEO A5: every critical parameter is a full record — parameter_id, parameter,
symbol, unit, value, value_status, source, source_hash, derivation,
assumptions, uncertainty, verification_method. No naked numerical values
exist anywhere: a value either carries one of the five epistemic statuses
with its source, or it is UNKNOWN.

CEO A6: failure analysis is INVENTION-SPECIFIC. Domain modules contribute
physical failure mechanisms (mode, physical_mechanism, trigger,
detectability, severity basis, design control direction), each evaluated for
applicability to THIS invention; adversarial attack dimensions keep their
verdicts but honestly carry "physical mechanism NOT ESTABLISHED" rather
than borrowing generic physical content.

CEO A7: design outputs are COMPILED (design_outputs.py) — architecture
blocks, component relationships, interfaces, geometry requirements,
parameter ranges, control logic, data flow and test fixtures, each with the
CONCEPTUAL / PROPOSED / UNKNOWN status vocabulary.

CEO Directive 6 (NO MATERIAL TRUNCATION): this artifact is AUTHORITATIVE.
NO string in it may be shortened — full text everywhere (this file is
scanned by the static slice guard; no slice syntax on content). 
Presentation-level shortening happens ONLY later, via the DisplayRegister.

The output `engineering_content` mirrors the ArtifactRichDossier schema that
premium_package_factory/templates/build_portfolio_v4.py consumes — so the
existing dossier factory renders it unchanged (E4 reuse, no template
recreation).
"""
from __future__ import annotations

import itertools
from typing import Any, Dict, List, Optional

from .candidate import Candidate, sha256_obj, utc_now
from .design_outputs import compile_design_outputs
from .domains import detect_domain, domain_label, get_domain_module
from .equations import select_equations
from .invention_spec import tagged

# Epistemic gate for engineering: DO results are ABSENT until reality
# produces them (Art. XXXVIII: COMPUTATIONAL_RESULT != PHYSICAL_OBSERVATION).

PARAMETER_VALUE_STATUSES = ("SOURCE_FACT", "COMPUTED", "MODELLED",
                            "ENGINEERING_PROPOSED", "UNKNOWN")


# --------------------------------------------------------------------------
def _invention_tokens(spec: Dict[str, Any]) -> List[str]:
    """Content tokens of THIS invention (exact substrings, Art. II) used for
    mechanical invention-tie checks throughout the specification."""
    mech = ((spec.get("mechanism") or {}).get("value") or {})
    problem = ((spec.get("problem") or {}).get("value") or {})
    text = " ".join(str(mech.get(k, "")) for k in
                    ("mechanism", "intervention", "expected_effect")) + " " + \
        " ".join(str(problem.get(k, "")) for k in
                 ("device", "failure", "constraint"))
    stop = {"that", "this", "with", "from", "which", "while", "when",
            "have", "has", "are", "the", "and", "for", "into", "than",
            "must", "should", "their", "there", "between", "through",
            "where", "would", "could", "these", "those", "such", "each"}
    tokens = sorted({w for w in text.lower().split()
                     if len(w) >= 5 and w.isalpha() and w not in stop})
    return tokens


def _tie(text: str, tokens: List[str]) -> Dict[str, Any]:
    lower = text.lower()
    hits = [t for t in tokens if t in lower]
    return {"invention_tied": bool(hits), "matched_tokens": hits}


def _first_n(seq: List[Any], n: int) -> List[Any]:
    out = []
    for i, x in enumerate(seq):
        if i >= n:
            break
        out.append(x)
    return out


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
    NOTE: `build_engineering_spec` replaces the thin fallback d_outputs with
    the A7-compiled design outputs (design_outputs.py) and re-runs
    integrity; this function remains the standalone structural skeleton
    (used directly by the bridge tests and as the no-module fallback).
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

    # DO — fallback thin outputs. build_engineering_spec replaces these with
    # the A7-compiled outputs; the skeleton keeps the structural contract.
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
# CEO A5 — critical parameter records
# --------------------------------------------------------------------------
def _link_parameter_to_equation(parameter_name: str,
                                equation_entries: List[Dict[str, Any]],
                                ) -> Dict[str, Any]:
    """Deterministic parameter->equation linkage by exact token overlap
    between the parameter name and the equation's variable descriptions.
    Returns the FIRST variable match (or NONE — never a guess)."""
    name_lower = parameter_name.lower()
    name_words = [w for w in name_lower.replace("/", " ").split()
                  if len(w) >= 4]
    for entry in equation_entries:
        eq = entry["equation"]
        for var in eq["variables"]:
            desc_words = [w for w in var["description"].lower()
                          .replace("/", " ").split() if len(w) >= 4]
            overlap = [w for w in name_words if w in desc_words]
            if overlap:
                return {"equation_id": eq["equation_id"],
                        "symbol": var["symbol"], "unit": var["unit"],
                        "matched_tokens": overlap,
                        "assumptions": list(eq.get("assumptions", []))}
    return {"equation_id": None, "symbol": None, "unit": None,
            "matched_tokens": [], "assumptions": []}


def _build_critical_parameters(spec: Dict[str, Any], module: Dict[str, Any],
                               domain: str,
                               equation_entries: List[Dict[str, Any]],
                               verification_methods: List[str],
                               ) -> List[Dict[str, Any]]:
    """CEO A5: full parameter records. The registry proposes WHAT matters;
    every VALUE stays UNKNOWN with an explicit value_status (no naked
    numbers, Art. XXVII)."""
    params: List[Dict[str, Any]] = []
    for i, pname in enumerate(module.get("critical_parameters", []), 1):
        link = _link_parameter_to_equation(pname, equation_entries)
        vm = _match_verification_method(pname, verification_methods)
        params.append({
            "parameter_id": f"CP-{i:03d}",
            "parameter": pname,
            "name": pname,
            "symbol": link["symbol"] or "NOT_ASSIGNED",
            "unit": link["unit"] or "UNKNOWN",
            "value": "UNKNOWN (no sourced value)",
            "value_status": "UNKNOWN",
            "source": None,
            "source_hash": None,
            "derivation": (
                f"linked to {link['equation_id']} via "
                f"{link['matched_tokens']}; derivation requires design "
                f"geometry and sourced inputs that do not exist yet"
                if link["equation_id"] else
                "domain registry candidate — no derivation possible until "
                "a design exists and sources are obtained"),
            "assumptions": link["assumptions"],
            "uncertainty": "UNKNOWN — unquantified (no measurement exists)",
            "verification_method": vm,
            # compatibility keys consumed by the v4 builders and maturity
            "basis": "ENGINEERING_PROPOSED (domain registry candidate)",
            "status": "ENGINEERING_PROPOSED / VALUE UNKNOWN",
            "verification_requirement":
                "assign a sourced target value and verification method "
                "before any build decision",
            "reason": "domain candidate parameter; no measurement exists",
            "domain": domain,
            "linked_equation_id": link["equation_id"],
            "invention_tie": {
                "linkage_kind": "equation_linkage" if link["equation_id"]
                else "domain_candidate",
                "linked_equation_id": link["equation_id"],
                "matched_tokens": link["matched_tokens"]},
            "principle": (
                next((g["model"] for g in module.get("governing_models", [])
                      if link["equation_id"] in
                      (g.get("equation_ids") or [])),
                     "domain engineering principle per the registry")),
        })
    return params


def _match_verification_method(parameter_name: str,
                               verification_methods: List[str]) -> str:
    name_lower = parameter_name.lower()
    name_words = [w for w in name_lower.replace("/", " ").split()
                  if len(w) >= 4]
    for m in verification_methods:
        m_lower = m.lower()
        if any(w in m_lower for w in name_words):
            return m
    return ("domain bench verification per verification matrix; method "
            "selection NOT ESTABLISHED until the parameter has a sourced "
            "target value")


# --------------------------------------------------------------------------
# CEO A6 — invention-specific failure analysis
# --------------------------------------------------------------------------
def _build_failure_analysis(spec: Dict[str, Any], module: Dict[str, Any],
                            domain: str, graph_f_modes: List[Dict[str, Any]],
                            graph_verifications: List[Dict[str, Any]],
                            arch_do_id: Optional[str],
                            verification_methods: List[str],
                            ) -> List[Dict[str, Any]]:
    """Assemble failure_analysis rows in the CEO A6 nine-field shape.

    Content policy (honesty per Art. XXV/XXXVIII):
      - problem-stated failure  -> SOURCE_FACT row (the motivating failure)
      - attack dimensions       -> COMPUTED verdicts; physical mechanism
                                   honestly NOT ESTABLISHED
      - domain candidate FMs    -> ENGINEERING_PROPOSED rows WITH physical
                                   mechanism/trigger/detection detail, each
                                   carrying a mechanical invention-
                                   applicability evaluation (TIED when its
                                   applicability signals match this
                                   invention's tokens; NOT_ESTABLISHED
                                   otherwise — never silently generic)
    """
    tokens = _invention_tokens(spec)
    # FM -> VF linkage from the structural graph (explicit parent ids)
    vf_by_fm: Dict[str, str] = {}
    for v in graph_verifications:
        for target in v.get("parent_ids", []) or []:
            vf_by_fm[target] = v["id"]
    rows: List[Dict[str, Any]] = []

    def _row(graph_id: str, mode: str, physical_mechanism: str,
             trigger: str, detectability: str, severity_basis: str,
             design_control: str, verification: str, basis: str,
             kill_condition: str = "NOT ESTABLISHED",
             domain_basis: str = "UNKNOWN",
             ) -> Dict[str, Any]:
        return {
            "graph_id": graph_id,
            "failure_mode": mode,
            "mode": mode,
            "physical_mechanism": physical_mechanism,
            "trigger": trigger,
            "detectability": detectability,
            "severity": "UNKNOWN (no sourced severity basis)",
            "severity_basis": severity_basis,
            "design_control": design_control,
            "design_feature": "NOT ESTABLISHED",
            "verification": verification,
            "verification_test": verification,
            "validation": ("NOT_PERFORMED — validation requires physical "
                           "observation (Art. XXXVIII)"),
            "kill_condition": kill_condition,
            "evidence": basis,
            "mitigation": design_control,
            "residual_uncertainty":
                "UNKNOWN — untested candidate failure mode (Art. XXV)",
            "epistemic_class": basis.split(" (")[0] or "UNKNOWN",
            "domain_basis": domain_basis,
        }

    # 1+2. the design-graph FMs (problem-stated + attack dimensions)
    for f in graph_f_modes:
        vf_id = vf_by_fm.get(f["id"], "NOT_LINKED")
        if f["basis"].startswith("SOURCE_FACT"):
            rows.append(_row(
                f["id"], f["mode"],
                f["mechanism"] + (f" — physical mechanism per domain "
                                  f"knowledge: NOT ESTABLISHED"),
                "the operating condition stated in the problem "
                "(trigger quantification NOT ESTABLISHED)",
                _match_verification_method(f["mode"], verification_methods),
                "the failure motivates the invention itself (buyer "
                "consequence follows from the problem statement)",
                "design control NOT ESTABLISHED (requires design work)",
                vf_id, f["basis"]))
        else:
            rows.append(_row(
                f["id"], f["mode"],
                "physical mechanism NOT ESTABLISHED — adversarial verdict "
                "recorded: " + f["mechanism"],
                "trigger NOT ESTABLISHED (adversarial probe)",
                "detectability NOT ESTABLISHED (adversarial probe)",
                "severity basis NOT ESTABLISHED (adversarial verdict only)",
                "design control NOT ESTABLISHED (requires design work)",
                vf_id, f["basis"]))

    # 3. domain candidate failure modes with applicability evaluation
    for j, dfm in enumerate(module.get("failure_modes", [])):
        sig_hits = [s for s in dfm.get("applicability_signals", [])
                    if s in " ".join(tokens)]
        content_hits = [t for t in _tie(
            dfm.get("mode", "") + " " +
            dfm.get("physical_mechanism", ""), tokens)["matched_tokens"]]
        tied = bool(sig_hits or content_hits)
        rows.append({
            "graph_id": f"FM-DOM-{j+1:03d}",
            "failure_mode": dfm.get("mode", "UNKNOWN"),
            "mode": dfm.get("mode", "UNKNOWN"),
            "physical_mechanism": dfm.get("physical_mechanism",
                                          "NOT ESTABLISHED"),
            "trigger": dfm.get("trigger", "NOT ESTABLISHED"),
            "detectability": dfm.get("detectability", "NOT ESTABLISHED"),
            "severity": "UNKNOWN (no sourced severity basis)",
            "severity_basis": dfm.get("severity_basis", "NOT ESTABLISHED"),
            "design_control": dfm.get("design_control_direction",
                                      "NOT ESTABLISHED"),
            "design_feature": "NOT ESTABLISHED",
            "verification": "NOT_LINKED",
            "verification_test": "NOT_LINKED",
            "validation": ("NOT_PERFORMED — validation requires physical "
                           "observation (Art. XXXVIII)"),
            "kill_condition": ("NOT ESTABLISHED — pre-register pass/fail "
                               "for this mode before transfer decisions"),
            "evidence": "domain registry candidate from the engineering "
                        "domain registry — applicability to THIS invention "
                        "recorded below",
            "mitigation": dfm.get("design_control_direction",
                                  "NOT ESTABLISHED"),
            "residual_uncertainty":
                "UNKNOWN — untested candidate failure mode (Art. XXV)",
            "epistemic_class": "ENGINEERING_PROPOSED",
            "domain_basis": domain_label(domain),
            "invention_applicability": {
                "verdict": "TIED" if tied else "NOT_ESTABLISHED",
                "matched_applicability_signals": sig_hits,
                "matched_invention_tokens": content_hits,
                "evaluation": "mechanical token match (exact substring); "
                              "MODEL_DERIVED, recorded for audit",
            },
        })
    return rows


# --------------------------------------------------------------------------
def build_engineering_spec(spec: Dict[str, Any], env: Optional[Candidate],
                           run_ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Produce the full engineering content (E3 + Directives 4/A2-A7), shaped
    for the existing dossier factory. Every block is explicitly classed;
    nothing claims physical existence; NOTHING is truncated (Directive 6)."""
    mech_text = " ".join(str(((spec.get("mechanism") or {}).get("value") or {}).get(k, ""))
                         for k in ("mechanism", "intervention",
                                   "expected_effect", "falsification_test"))
    problem = ((spec.get("problem") or {}).get("value") or {})

    detection = detect_domain(mech_text + " " + " ".join(
        str(problem.get(k, "")) for k in ("device", "failure", "constraint")))
    domain = detection["domain"]
    module = get_domain_module(domain)

    graph = build_design_graph(spec, env)
    equations = select_equations(spec, domain)
    equation_entries = equations.get("value") or []
    rejected_equations = equations.get("rejected_equations") or []

    # ---- extend the design-input set to benchmark depth ------------------
    # (a) domain design-input patterns — ENGINEERING_PROPOSED candidates,
    #     each carrying its invention-applicability evaluation;
    # (b) custodied evidence observations — SOURCE_FACT rows citing the
    #     custody chain (real evidence, never invented).
    tokens = _invention_tokens(spec)
    di_n = len(graph["d_inputs"])
    for pattern in module.get("design_input_patterns", []):
        di_n += 1
        tie = _tie(pattern, tokens)
        graph["d_inputs"].append({
            "id": f"DI-{di_n:03d}", "parent_ids": ["UIN-001"],
            "label": f"Domain design input pattern: {pattern}",
            "value": ("invention applicability: TIED via tokens "
                      f"{tie['matched_tokens']}" if tie["invention_tied"]
                      else "invention applicability: NOT_ESTABLISHED "
                           "(candidate pattern; confirm against the actual "
                           "use profile)"),
            "basis": "ENGINEERING_PROPOSED (domain registry pattern)",
            "evidence_refs": []})
    ev_index = spec.get("_evidence_index") or {}
    for ev_id, ev in sorted(ev_index.items()):
        if ev_id.startswith("problem:"):
            continue   # the operator problem statement is already DI/UIN basis
        di_n += 1
        graph["d_inputs"].append({
            "id": f"DI-{di_n:03d}", "parent_ids": ["UIN-001"],
            "label": f"Custodied observation: {ev.get('title', '')}",
            "value": (f"source {ev.get('source_uri', 'UNKNOWN')}; "
                      f"content_hash {ev.get('content_hash', 'UNKNOWN')}"),
            "basis": "SOURCE_FACT (custodied evidence)",
            "evidence_refs": [ev_id]})
    graph["counts"]["DI"] = len(graph["d_inputs"])

    # ---- CEO A5: full parameter records ---------------------------------
    critical_parameters = _build_critical_parameters(
        spec, module, domain, equation_entries,
        module.get("verification_methods", []))

    # ---- CEO A7: compiled design outputs --------------------------------
    compiled = compile_design_outputs(
        spec, module, graph["d_inputs"], critical_parameters,
        module.get("verification_methods", []))
    d_outputs = compiled["items"]
    arch_do_id = next((d["id"] for d in d_outputs
                       if d["kind"] == "architecture_block"), None) or \
        (d_outputs[0]["id"] if d_outputs else None)

    # replace the skeleton's thin outputs; re-parent problem FMs onto the
    # first architecture output; re-run graph integrity on the new graph
    graph["d_outputs"] = d_outputs
    for f in graph["f_modes"]:
        if arch_do_id:
            f["parent_ids"] = [arch_do_id]
    graph["counts"]["DO"] = len(d_outputs)
    graph["graph_integrity"] = _graph_integrity(
        graph["d_inputs"], d_outputs, graph["f_modes"],
        graph["verifications"], graph["validations"])

    # ---- CEO A4: why this domain (per invention) -------------------------
    why_this_domain = {
        "domain": domain,
        "label": domain_label(domain),
        "matched_signals": detection["matched_signals"],
        "matched_in_text": True,
        "runner_up": detection.get("runner_up"),
        "basis": ("domain selected by exact-substring matching of the "
                  "domain's characteristic signals against THIS invention's "
                  "mechanism/problem text; the matched signals above are "
                  "the mechanical justification"),
        "epistemic_class": "MODEL_DERIVED",
        "note": detection["note"],
        "equation_applicability_summary": {
            "applicable": [e["selection_rationale"]["verdict"] and
                           e["equation"]["equation_id"]
                           for e in equation_entries
                           if e["selection_rationale"]["verdict"] ==
                           "APPLICABLE"],
            "conditional": [e["equation"]["equation_id"]
                            for e in equation_entries
                            if e["selection_rationale"]["verdict"] ==
                            "CONDITIONAL"],
            "rejected": [r["equation_id"] for r in rejected_equations],
        },
    }

    # ---- CEO A6: invention-specific failure analysis ---------------------
    failure_modes_out = _build_failure_analysis(
        spec, module, domain, graph["f_modes"], graph["verifications"],
        arch_do_id, module.get("verification_methods", []))

    # register the domain candidate FMs in the structural graph (parented
    # to the architecture output) so FM->VF links are checkable
    dom_graph_fms = []
    for f in failure_modes_out:
        if f["graph_id"].startswith("FM-DOM-"):
            dom_graph_fms.append({
                "id": f["graph_id"],
                "parent_ids": [arch_do_id] if arch_do_id else ["UIN-001"],
                "mode": f["mode"],
                "mechanism": f.get("physical_mechanism", ""),
                "basis": "ENGINEERING_PROPOSED (domain registry candidate)",
                "evidence_refs": []})
    graph["f_modes"].extend(dom_graph_fms)
    graph["counts"]["FM"] = len(graph["f_modes"])

    # governing model from domain equations — symbolic unless fully sourced
    governing = {
        "summary": (f"{domain_label(domain)} governing relations proposed for "
                    "this invention; SYMBOLIC ONLY until inputs are sourced"),
        "equations": [
            {"equation_id": eq["equation"]["equation_id"],
             "name": eq["equation"]["name"],
             "expression": eq["equation"]["expression"],
             "source": eq["equation"]["source"],
             "applicability": eq["equation"]["applicability"],
             "assumptions": eq["equation"]["assumptions"],
             "selection_rationale": eq["selection_rationale"],
             "model_applicability": eq["equation"]["applicability"]["condition"],
             "model_assumptions": list(eq["equation"]["assumptions"]),
             "invention_tie": {
                 "linkage_kind": "applicability_judgment",
                 "verdict": eq["selection_rationale"]["verdict"],
                 "engaged_variables":
                     eq["selection_rationale"].get("engaged_variables", []),
                 "mechanism_mention_count":
                     len(eq["selection_rationale"].get(
                         "mechanism_mentions", []))}}
            for eq in equation_entries],
        "rejected_equations": rejected_equations,
        "why_this_domain": why_this_domain,
        "domain_governing_models": [
            {"model": m.get("model"),
             "registry_equation_ids": m.get("equation_ids", []),
             "applicability": m.get("model_applicability",
                                    m.get("applicability",
                                          m.get("note",
                                                "ENGINEERING_PROPOSED"))),
             "model_assumptions": list(m.get("model_assumptions", []))}
            for m in module.get("governing_models", [])],
        "assumptions": [a for eq in equation_entries
                        for a in eq["equation"]["assumptions"]],
        "boundary_conditions": ["to be established by the first bench "
                                "characterization (not yet performed)"],
        "input_variables": [
            {"symbol": v["symbol"], "unit": v["unit"],
             "epistemic_status": "UNKNOWN (no sourced value)"}
            for eq in equation_entries
            for v in eq["equation"]["variables"] if v.get("role") == "input"],
        "output_variables": [
            {"symbol": v["symbol"], "unit": v["unit"],
             "epistemic_status": "UNKNOWN (no computed value)"}
            for eq in equation_entries
            for v in eq["equation"]["variables"] if v.get("role") == "output"],
        "parameter_sensitivities": [],
        "failure_regimes": [
            {"regime": f["mode"], "basis": f["evidence"]}
            for f in failure_modes_out],
    }

    # domain verification-method rows — planned characterizations the
    # domain registry prescribes for this invention class (planned, never
    # executed: result stays NOT_TESTED, Art. XXXVIII). Each names the
    # TIED domain failure modes it would expose.
    tied_dom_fms = [f["graph_id"] for f in failure_modes_out
                    if (f.get("invention_applicability") or {})
                    .get("verdict") == "TIED"]
    extra_verifications: List[Dict[str, Any]] = []
    vf_extra_counter = len(graph["verifications"])
    if tied_dom_fms:
        # a planned domain characterization enters the graph ONLY when it
        # has invention-tied failure modes to expose (VF->FM structural
        # rule; untied candidates would be noise, not depth)
        for m in _first_n(module.get("verification_methods", []), 2):
            vf_extra_counter += 1
            extra_verifications.append({
                "id": f"VF-{vf_extra_counter:03d}",
                "parent_ids": tied_dom_fms,
                "method": m,
                "basis": "ENGINEERING_PROPOSED (domain verification method)",
                "result": "NOT_TESTED"})
    graph["verifications"].extend(extra_verifications)
    graph["counts"]["VF"] = len(graph["verifications"])
    graph["graph_integrity"] = _graph_integrity(
        graph["d_inputs"], d_outputs, graph["f_modes"],
        graph["verifications"], graph["validations"])

    # ---- build plan (unchanged contract) ---------------------------------
    ke = (spec.get("killer_experiment") or {}).get("value") or {}
    ke_name = ke.get("selected") if isinstance(ke.get("selected"), str) \
        else (ke.get("selected") or {}).get("name", "UNKNOWN") if \
        ke.get("selected") else ""
    ke_def = ke.get("definition", "")
    if ke_name == "UNKNOWN":
        ke_name = ""   # no killer experiment was selected: no WP is claimed

    build_plan: List[Dict[str, Any]] = []
    if ke_name:
        build_plan.append({
            "work_package": "WP-01",
            "test_article": f"first physical article implementing the "
                            f"proposed intervention (GEOMETRY ABSENT — must "
                            f"be designed)",
            "equipment": "domain bench equipment per verification methods",
            "design_work": "complete design-output geometry from proposal "
                           "to manufacturable definition",
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
    # (domain verification methods enter the plan THROUGH their VF rows
    # above — no duplicated work packages)

    # ---- CEO A2 companion blocks -----------------------------------------
    # (the build plan's domain verification WPs come from the same methods;
    # deduplicate by method text against the VF rows)
    interfaces_block = {
        "description": "device boundary definitions (A7 interface outputs "
                       "are the authoritative entries)",
        "interfaces": [
            {"id": d["id"], "description": d["description"],
             "status": d["status"],
             "detail": d.get("interface_list")}
            for d in d_outputs if d["kind"] == "interface"] or
            [{"id": "IF-NONE", "description": "NOT ESTABLISHED",
              "status": "UNKNOWN", "detail": None}],
        "status": "CONCEPTUAL — no interface is quantified",
    }
    regulatory_block = {
        "pathway": "UNKNOWN (no regulatory determination exists for this "
                   "invention; per R370C correction the pathway is never "
                   "inferred from device class alone)",
        "candidate_standards": [
            {"standard": s["standard"],
             "class": "EXTERNAL_PRECEDENT_CANDIDATE",
             "verify_applicability": True}
            for s in module.get("standards_candidates", [])],
        "status": "NOT_ESTABLISHED",
        "basis": "candidate standards from the engineering domain registry; "
                 "applicability verification is the buyer's/regulatory "
                 "affair's first engineering action",
    }
    kill_condition_block = {
        "statement": _kill_statement(spec),
        "falsification_test": (((spec.get("causal_chain") or {})
                                .get("value") or {}).get("falsification_test",
                                                         "")),
        "killer_experiment": {"selected": ke_name or "UNKNOWN",
                              "eig": ke.get("eig"),
                              "eig_per_cost": ke.get("eig_per_cost")},
        "basis": "COMPUTED (killer experiment selection)" if ke_name
        else "UNKNOWN (no killer experiment selected)",
    }
    buyer_diligence_block = {
        "independent_review_required": True,
        "verify_prior_art": {
            "instruction": "independently confirm novelty against the "
                           "searched sources; novelty is a HYPOTHESIS "
                           "bounded by searched sources (Art. XXI.2)",
            "nearest_prior_art": ((spec.get("distinguishing_features") or {})
                                  .get("value") or {})
                                 .get("vs_nearest_prior_art", [])},
        "verify_evidence_custody": {
            "instruction": "recompute evidence content hashes from the "
                           "custody references before relying on any "
                           "SOURCE_FACT",
            "evidence_ids": sorted((spec.get("_evidence_index") or {}).keys())
            if spec.get("_evidence_index") else []},
        "verify_precedent_applicability": {
            "instruction": "every external precedent/standard candidate "
                           "carries verify_applicability=true; applicability "
                           "to THIS design is unverified",
            "count": len(module.get("standards_candidates", []))},
        "open_uncertainties": ((spec.get("uncertainties") or {})
                               .get("value") or []),
        "basis": "COMPUTED from the invention specification's recorded "
                 "uncertainties and evidence index",
    }
    investment_ladder = []
    for wp in build_plan:
        investment_ladder.append({
            "stage": wp["work_package"],
            "gate": wp["measurement"],
            "unlocks": ("next work package on pass; re-design on fail "
                        "(kill condition governs)"),
            "estimated_effort": wp["estimated_effort"],
            "capital": "NOT ESTABLISHED (no quotation exists)",
            "basis": wp["basis"]})
    investment_ladder.append({
        "stage": "TRANSFER_DECISION",
        "gate": "REAL_LOOP_VERIFIED via a gated external reality event "
                "(Art. XXXVII/XXXVIII) plus regulatory pathway determination",
        "unlocks": "technology-transfer transaction",
        "estimated_effort": "NOT ESTABLISHED",
        "capital": "NOT ESTABLISHED",
        "basis": "UNKNOWN until the loop closes"})

    eng = {
        "technology_domain": domain if domain != "UNKNOWN" else "NOT ESTABLISHED",
        "domain_detection": {
            "epistemic_class": detection["epistemic_class"],
            "matched_signals": detection["matched_signals"],
            "note": detection["note"],
            "label": domain_label(domain)},
        "why_this_domain": why_this_domain,
        "engineering_disciplines": module["disciplines"],
        "system_architecture": {
            "description": (
                "PROPOSED architecture (no physical system exists): "
                + "; ".join(module["architecture_blocks"])
                + f" — realizing: {((spec.get('mechanism') or {}).get('value') or {}).get('intervention', '')}"),
            "subsystems": [
                {"name": b, "status": "ENGINEERING_PROPOSED",
                 "detail": "NOT ESTABLISHED (requires design work)",
                 "invention_tie": _tie(
                     b + " " + ((spec.get("mechanism") or {}).get("value")
                                or {}).get("intervention", ""),
                     _invention_tokens(spec))}
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
        "design_outputs": d_outputs,
        "design_output_compilation": {
            "kinds": compiled["counts"],
            "status_counts": compiled["status_counts"],
            "invention_tie_summary": compiled["invention_tie_summary"],
            "contract": "CEO A7: CONCEPTUAL/PROPOSED/UNKNOWN vocabulary; "
                        "no geometry invented",
        },
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
             "verify_applicability": True,
             "invention_tie": _tie(m["material"] + " " + mech_text,
                                   tokens)}
            for m in module.get("materials_candidates", [])] or
            [{"component": "NOT_APPLICABLE — data-only invention: no "
              "physical materials exist to select; hardware dependencies "
              "are recorded under design outputs instead",
              "material": "NOT_APPLICABLE (data-only invention)",
              "candidate_material": None,
              "status": "NOT_APPLICABLE",
              "invention_tie": {"linkage_kind": "domain_kind",
                                "domain": domain}}],
        "manufacturing": {
            "candidate_processes": [
                {"process": p.get("process", p)
                 if isinstance(p, dict) else str(p),
                 "status": p.get("status", "ENGINEERING_PROPOSED")
                 if isinstance(p, dict) else "ENGINEERING_PROPOSED",
                 "source": "domain registry manufacturing route",
                 "note": "candidate only; no process qualification exists",
                 "invention_tie": _tie(
                     (p.get("process", p) if isinstance(p, dict)
                      else str(p)) + " " + mech_text, tokens)}
                for p in module.get("manufacturing_patterns", [])] or
                [{"process": "NOT ESTABLISHED", "status": "UNKNOWN"}],
            "manufacturing_routes": list(
                module.get("manufacturing_routes", [])),
            "status": "NO MANUFACTURING ANALYSIS POSSIBLE — no design exists; "
                      "processes are candidates only",
        },
        "regulatory": regulatory_block,
        "interfaces": interfaces_block,
        "kill_condition": kill_condition_block,
        "buyer_diligence": buyer_diligence_block,
        "investment_ladder": investment_ladder,
        "transfer_boundary": {
            "buyer_receives": [
                "canonical invention specification (with epistemic classes)",
                "engineering specification (this document, all blocks classed)",
                "design input/output graph with explicit IDs",
                "engineering reasoning chains (claim->principle->model->"
                "input->assumption->output->failure->verification)",
                "killer-experiment definition and its EIG basis",
                "evidence custody references and hashes",
                "unresolved-uncertainty register",
                "domain equation set (symbolic; sources and applicability "
                "judgments identified)"],
            "buyer_must_create": [
                "actual geometry and detailed design",
                "sourced engineering parameters and acceptance thresholds",
                "physical prototypes",
                "all verification and validation results",
                "manufacturing process qualification",
                "regulatory pathway determination and submissions"],
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
             "result": "NOT_TESTED",
             "invention_tie": {
                 "linkage_kind": "killer_experiment" if
                 "killer experiment" in v["method"] else
                 "domain_verification_method" if
                 "domain verification method" in v.get("basis", "") else
                 "falsification_test",
                 "targets": v.get("parent_ids", [])}}
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
                                "novelty search results",
                                "equation applicability judgments"],
            "MODELLED_fields": ["mechanism", "causal chain",
                                "distinguishing features"],
            "ENGINEERING_PROPOSED_fields": ["architecture blocks", "materials",
                                            "manufacturing candidates",
                                            "domain critical parameters",
                                            "domain candidate failure modes",
                                            "compiled design outputs",
                                            "reasoning chains"],
            "UNKNOWN_fields": ["all parameter values", "all acceptance "
                              "thresholds", "all validation results",
                               "all severity ratings"],
            "rule": "the generator may not turn a model into a fact "
                    "(Art. XXVIII/XXXVIII)"},
    }

    # ---- CEO A3: engineering reasoning chains ----------------------------
    _attach_reasoning_chains(eng, spec)
    return eng


def _kill_statement(spec: Dict[str, Any]) -> str:
    ke = (spec.get("killer_experiment") or {}).get("value") or {}
    sel = ke.get("selected")
    name = sel if isinstance(sel, str) else (sel or {}).get("name", "")
    name = "" if name == "UNKNOWN" else name
    return (f"killer experiment fails: {name or 'NOT ESTABLISHED'} "
            "(pre-registered pass/fail required before any transfer)")


def _attach_reasoning_chains(eng: Dict[str, Any], spec: Dict[str, Any]
                             ) -> None:
    """CEO A3: build the reasoning chains over the assembled engineering
    artifact and record them (with their content hash) into it."""
    from .reasoning_chain import build_reasoning_chains
    chains = build_reasoning_chains(spec, eng)
    chains["hash"] = sha256_obj(chains)
    eng["engineering_reasoning_chains"] = chains
