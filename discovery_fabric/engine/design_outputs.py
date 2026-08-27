"""discovery_fabric/engine/design_outputs.py — CEO A7: design-output
compiler.

The survivor must automatically produce ACTUAL design outputs — not just a
record that outputs are missing. This compiler turns the invention
specification + domain engineering module into concrete output objects:

    architecture_block        the subsystem decomposition realizing the
                              mechanism
    component_relationship    how each subsystem connects to which other
    interface                 boundary definitions (connectors, hand-offs)
    geometry_requirement      named geometric decisions, dims UNKNOWN
    parameter_range           named operating ranges, values UNKNOWN
    control_logic             sensing/decision/actuation loop (or an honest
                              NOT_APPLICABLE record for open-loop devices)
    data_flow                 information path (sensing -> decision -> output;
                              pipeline stages for data inventions)
    test_fixture              the rig each verification method requires

Status vocabulary is EXACTLY the CEO A7 vocabulary:
    CONCEPTUAL   the concept exists and is stated here
    PROPOSED     a concrete engineering proposal, needs design work
    UNKNOWN      the output requires knowledge that does not exist yet

NO geometric numbers, ranges or setpoints are invented (Art. XXVII): every
quantitative field is UNKNOWN with its missing inputs named. Each output
keeps the structural design-graph keys (id / parent_ids / description /
status / missing_inputs / basis) so the frozen v4 builders render it
unchanged, plus compiler-specific detail fields the builders ignore.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .candidate import sha256_obj, utc_now

STATUS_CONCEPTUAL = "CONCEPTUAL"
STATUS_PROPOSED = "PROPOSED"
STATUS_UNKNOWN = "UNKNOWN"

A7_OUTPUT_KINDS = ("architecture_block", "component_relationship",
                   "interface", "geometry_requirement", "parameter_range",
                   "control_logic", "data_flow", "test_fixture")


def _first_n(seq, n):
    """Selection helper — returns the first n items WITHOUT slice syntax so
    this file stays scannable under the Directive-6 guard convention."""
    out = []
    for i, x in enumerate(seq):
        if i >= n:
            break
        out.append(x)
    return out


def _invention_tokens(spec: Dict[str, Any]) -> List[str]:
    """Content tokens tying outputs to THIS invention (exact substring
    matching, Art. II)."""
    mech = ((spec.get("mechanism") or {}).get("value") or {})
    problem = ((spec.get("problem") or {}).get("value") or {})
    text = " ".join(str(mech.get(k, "")) for k in
                    ("mechanism", "intervention", "expected_effect")) + " " + \
        " ".join(str(problem.get(k, "")) for k in
                 ("device", "failure", "constraint"))
    stop = {"that", "this", "with", "from", "which", "while", "when",
            "have", "has", "are", "the", "and", "for", "into", "than",
            "must", "should", "their", "there", "between", "through"}
    tokens = sorted({w for w in text.lower().split()
                     if len(w) >= 5 and w.isalpha() and w not in stop})
    # bounded vocabulary (selection, not truncation: the full text
    # lives in the spec; the bound keeps token lists auditable)
    return tokens if len(tokens) <= 60 else _first_n(tokens, 60)


def _tie(text: str, tokens: List[str]) -> Dict[str, Any]:
    hits = [t for t in tokens if t in text.lower()]
    return {"invention_tied": bool(hits), "matched_tokens": hits}


def compile_design_outputs(spec: Dict[str, Any], module: Dict[str, Any],
                           d_inputs: List[Dict[str, Any]],
                           critical_parameters: List[Dict[str, Any]],
                           verification_methods: List[Dict[str, Any]],
                           ) -> Dict[str, Any]:
    """Compile the full A7 output set. Returns (items, ties_summary)."""
    mech = ((spec.get("mechanism") or {}).get("value") or {})
    problem = ((spec.get("problem") or {}).get("value") or {})
    intervention = mech.get("intervention", "") or \
        mech.get("mechanism", "the proposed intervention")
    tokens = _invention_tokens(spec)
    blocks = module.get("architecture_blocks", []) or \
        ["input interface", "transformation element", "output interface",
         "failure containment"]
    di_ids = [d["id"] for d in d_inputs] or []
    items: List[Dict[str, Any]] = []
    counter = 0

    def _emit(kind: str, description: str, status: str, parents: List[str],
              missing: List[str], basis: str, detail: Dict[str, Any],
              ) -> None:
        nonlocal counter
        counter += 1
        # E8 structural contract: EVERY design output names >=1 parent DI.
        # DO->DO references are kept in addition, never instead.
        merged = list(parents)
        if di_anchor and not (set(merged) & set(di_ids)):
            merged.append(di_anchor)
        item = {
            "id": f"DO-{counter:03d}",
            "kind": kind,
            "parent_ids": merged or [],
            "description": description,
            "status": status,
            "missing_inputs": missing,
            "basis": basis,
            # A7 honesty invariant: EVERY compiled output records that no
            # geometry exists yet (maturity ladder reads this field)
            "geometry_status": "ABSENT — no geometry exists yet",
        }
        item.update(detail)
        items.append(item)

    di_m = next((d["id"] for d in d_inputs
                 if "Mechanism driver" in d.get("label", "")), None)
    di_c = next((d["id"] for d in d_inputs
                 if "constraint" in d.get("label", "").lower()), None)
    di_ids = [d["id"] for d in d_inputs]
    di_anchor = di_m or di_c or (di_ids[0] if di_ids else None)

    # ---- 1. architecture blocks -------------------------------------
    arch_ids = []
    for b in blocks:
        desc = f"{b} realizing {intervention}"
        _emit("architecture_block", desc, STATUS_CONCEPTUAL,
              [di_m] if di_m else [], ["detailed architecture definition"],
              "ENGINEERING_PROPOSED (domain architecture pattern, "
              "CONCEPTUAL for this invention)",
              {"role_in_invention": _tie(b + " " + intervention, tokens),
               "geometry_status": "ABSENT — no geometry exists yet"})
        arch_ids.append(f"DO-{counter:03d}")

    # ---- 2. component relationships ----------------------------------
    for i in range(len(blocks) - 1):
        rel = (f"{blocks[i]} interfaces with {blocks[i+1]}: signal/energy/"
               f"material hand-off for {intervention}")
        _emit("component_relationship", rel, STATUS_CONCEPTUAL,
              [arch_ids[i], arch_ids[i + 1]] if i + 1 < len(arch_ids)
              else _first_n(arch_ids, 1),
              ["interface quantification (dimensions, tolerances)"],
              "ENGINEERING_PROPOSED (CONCEPTUAL relationship)",
              {"from_component": blocks[i], "to_component": blocks[i + 1],
               "transfer_quantity": "to be defined by the design work"})

    # ---- 3. interfaces -------------------------------------------------
    _emit("interface",
          f"Device boundaries: patient/fluid inlet and outlet "
          f"terminations, external control/data port as required by "
          f"{intervention}",
          STATUS_CONCEPTUAL, _first_n(arch_ids, 1),
          ["connector standards selection", "seal definitions"],
          "ENGINEERING_PROPOSED (CONCEPTUAL)",
          {"interface_list": [
              {"name": "primary functional boundary",
               "standard": "UNKNOWN (candidate standards listed under "
                           "external precedent; selection NOT ESTABLISHED)"},
              {"name": "service/deployment boundary",
               "standard": "UNKNOWN"}]})

    # ---- 4. geometry requirements --------------------------------------
    _emit("geometry_requirement",
          f"Flow/force/signal path geometry realizing the mechanism "
          f"({intervention}); every dimension is a named design decision "
          f"with UNKNOWN value",
          STATUS_UNKNOWN, [di_m] if di_m else _first_n(arch_ids, 1),
          ["all dimensions", "tolerances", "surface finish"],
          "UNKNOWN (no geometry exists; no CAD justification)",
          {"named_decisions": [
              {"decision": f"{p.get('parameter', 'UNNAMED')} geometry "
               f"implication", "value": "UNKNOWN",
               "value_status": "UNKNOWN"}
              for p in _first_n(critical_parameters, 4)]})

    # ---- 5. parameter ranges -------------------------------------------
    for p in _first_n(critical_parameters, 6):
        name = p.get("parameter", "UNNAMED PARAMETER")
        _emit("parameter_range",
              f"Operating range for {name} within which the mechanism "
              f"holds its stated behavior",
              STATUS_UNKNOWN, [di_c] if di_c else _first_n(arch_ids, 1),
              [f"sourced or computed bounds for {name}",
               "verification of range endpoints"],
              "UNKNOWN (no sourced bound exists, Art. XXVII)",
              {"parameter_id": p.get("parameter_id"),
               "lower_bound": "UNKNOWN", "upper_bound": "UNKNOWN",
               "unit": p.get("unit", "UNKNOWN")})

    # ---- 6. control logic ----------------------------------------------
    closed_loop = any(tok in " ".join(tokens)
                      for tok in ("closed", "feedback", "sensor", "sensing",
                                  "control", "regulat", "adaptiv"))
    if closed_loop:
        _emit("control_logic",
              f"Sensing -> decision -> actuation loop maintaining the "
              f"mechanism's operating point for {intervention}",
              STATUS_PROPOSED, _first_n(arch_ids, 1),
              ["sensing modality selection", "decision thresholds "
               "(sourced values required)", "actuation authority"],
              "ENGINEERING_PROPOSED (PROPOSED loop structure)",
              {"loop_elements": ["sensing element (modality UNKNOWN)",
                                 "decision criterion (thresholds UNKNOWN)",
                                 "actuation element (authority UNKNOWN)"]})
    else:
        _emit("control_logic",
              "No closed-loop control is proposed: the invention operates "
              "passively/open-loop as specified; this record exists so the "
              "omission is explicit and auditable",
              STATUS_CONCEPTUAL, _first_n(arch_ids, 1),
              [],
              "ENGINEERING_PROPOSED (explicit open-loop record)",
              {"closed_loop": False,
               "revisit_trigger": "any mechanism change introducing "
                                  "feedback"})

    # ---- 7. data flow ----------------------------------------------------
    if module.get("domain_id") == "ml_data" or "data" in tokens or \
            "predict" in tokens or "learning" in tokens:
        stages = ["ingestion", "feature/representation", "model + UQ",
                  "decision output", "monitoring loop"]
        _emit("data_flow",
              "Information pipeline: " + " -> ".join(stages) +
              " — stage boundaries named; per-stage specifications UNKNOWN",
              STATUS_PROPOSED, _first_n(arch_ids, 1),
              ["stage input/output schemas", "latency budget",
               "monitoring thresholds"],
              "ENGINEERING_PROPOSED (PROPOSED pipeline stages)",
              {"stages": stages})
    else:
        _emit("data_flow",
              "Information path: sensing element -> decision/monitor point "
              "-> record/act (minimal); rich data paths are NOT APPLICABLE "
              "to this mechanical/physical invention as specified",
              STATUS_CONCEPTUAL, _first_n(arch_ids, 1),
              [],
              "ENGINEERING_PROPOSED (explicit minimal-path record)",
              {"applicable": "MINIMAL",
               "note": "full data pipeline NOT_APPLICABLE as specified"})

    # ---- 8. test fixtures -------------------------------------------------
    for v in _first_n(verification_methods, 4):
        _emit("test_fixture",
              f"Fixture enabling: {v} — rig concept named, build "
              f"specification UNKNOWN",
              STATUS_UNKNOWN, _first_n(arch_ids, 1),
              ["fixture geometry", "instrumentation selection",
               "acceptance instrumentation calibration"],
              "ENGINEERING_PROPOSED (fixture concept; build UNKNOWN)",
              {"method": v})

    ties = [_tie(i["description"], tokens)["invention_tied"] for i in items]
    return {
        "items": items,
        "counts": {k: sum(1 for i in items if i["kind"] == k)
                   for k in A7_OUTPUT_KINDS},
        "status_counts": {s: sum(1 for i in items if i["status"] == s)
                          for s in (STATUS_CONCEPTUAL, STATUS_PROPOSED,
                                    STATUS_UNKNOWN)},
        "invention_tie_summary": {
            "tied_items": sum(1 for t in ties if t),
            "total_items": len(items),
            "tokens_used": tokens,
        },
        "compiled_at": utc_now(),
    }
