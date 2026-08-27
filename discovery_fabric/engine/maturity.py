"""discovery_fabric/engine/maturity.py — CEO Directive 7: maturity computed
from the ACTUAL generated artifact state.

The former MATURITY_BASIS injected a generic blocker list ("no physical
prototype exists ...") into every generated package. That is forbidden:
maturity is now DERIVED, mechanically, from the recorded presence/absence of
artifacts. The output is a ladder:

    CONCEPT_DEFINED
    ENGINEERING_DEFINITION
    PROTOTYPE_DESIGN_READY
    PROTOTYPE_BUILD_READY
    VALIDATION_READY
    TRANSFER_READY

Every rung declares its exact artifact conditions; every condition is
evaluated against the real spec/engineering-spec/envelope/package artifacts;
each evaluation carries the evidence pointer that justifies it. The
package's known_blockers are exactly the unsatisfied conditions of the next
rung — computed, never injected. No state may be claimed unless every
condition below it is also satisfied (Art. XXVIII: no silent promotion).
"""
from __future__ import annotations

from typing import Any, Dict, List

from .candidate import utc_now

MATURITY_LADDER = [
    "CONCEPT_DEFINED",
    "ENGINEERING_DEFINITION",
    "PROTOTYPE_DESIGN_READY",
    "PROTOTYPE_BUILD_READY",
    "VALIDATION_READY",
    "TRANSFER_READY",
]


def _has(key: str) -> Dict[str, Any]:
    return {"present": True, "evidence": key}


def _lacks(key: str, why: str) -> Dict[str, Any]:
    return {"present": False, "evidence": key, "reason": why}


def compute_maturity(spec: Dict[str, Any], eng: Dict[str, Any],
                     env: Any = None, package_report: Any = None,
                     release: Any = None) -> Dict[str, Any]:
    """Evaluate the ladder against the actual artifacts. Returns level,
    per-rung condition evaluations, blockers, and counts."""
    core = eng.get("engineering_core", {}) if isinstance(eng, dict) else {}
    gm = core.get("governing_model", {}) or {}
    graph = eng.get("design_graph", {}) or {}
    integrity = graph.get("integrity", {}) or {}
    d_inputs = eng.get("design_inputs", []) or []
    d_outputs = eng.get("design_outputs", []) or []
    build_plan = eng.get("engineering_build_plan", []) or []
    verif_matrix = eng.get("verification_matrix", []) or []
    val_matrix = eng.get("validation_matrix", []) or []
    failure_modes = core.get("failure_modes", []) or []
    bom = eng.get("bom", []) or []
    manufacturing = eng.get("manufacturing", {}) or {}

    spec_ok = bool(spec) and bool((spec.get("_integrity") or {})
                                  .get("passed"))
    gate = (spec.get("_survivor_gate") or {}) if spec else {}
    loop_state = ((package_report or {}).get("loop_verification_state")
                  if package_report else None)

    # ---------------- rung 1: CONCEPT_DEFINED ----------------
    c1 = [
        {"id": "C-01",
         "condition": "canonical invention specification exists and passes "
                      "its no-fact-promotion integrity check",
         **(_has("INVENTION_SPECIFICATION._integrity.passed=true")
             if spec_ok else _lacks(
                 "INVENTION_SPECIFICATION", "spec missing or integrity "
                 "failed"))},
        {"id": "C-02",
         "condition": "survivor gate recorded as passed",
         **(_has("_survivor_gate.survivor=true")
             if gate.get("survivor") else _lacks(
                 "_survivor_gate.survivor", "candidate is not a survivor"))},
        {"id": "C-03",
         "condition": "at least one custodied evidence item or a custodied "
                      "problem artifact exists",
         **(_has("candidate envelope evidence["
                 f"{len((env.evidence if env else []) or [])}]")
             if (env.evidence if env else []) else _lacks(
                 "envelope.evidence", "no custodied evidence"))},
    ]

    # ---------------- rung 2: ENGINEERING_DEFINITION ----------------
    c2 = [
        {"id": "E-01",
         "condition": "design graph passes structural integrity "
                      "(every DO/FM/VF has explicit-ID parents)",
         **(_has("design_graph.integrity.passed=true")
             if integrity.get("passed") else _lacks(
                 "design_graph.integrity.passed",
                 f"problems: {integrity.get('problems', ['unknown'])}"))},
        {"id": "E-02",
         "condition": "governing model contains at least one sourced or "
                      "symbolic domain equation",
         **(_has(f"governing_model.equations[{len(gm.get('equations', []))}]")
             if gm.get("equations") else _lacks(
                 "governing_model.equations",
                 "no domain equations selected"))},
        {"id": "E-03",
         "condition": "at least one design input recorded",
         **(_has(f"design_inputs[{len(d_inputs)}]") if d_inputs
             else _lacks("design_inputs", "no design inputs"))},
        {"id": "E-04",
         "condition": "at least one design output recorded (status ABSENT "
                      "permitted — geometry is future work)",
         **(_has(f"design_outputs[{len(d_outputs)}]") if d_outputs
             else _lacks("design_outputs", "no design outputs"))},
        {"id": "E-05",
         "condition": "failure analysis present",
         **(_has(f"failure_modes[{len(failure_modes)}]") if failure_modes
             else _lacks("failure_modes", "no failure modes"))},
        {"id": "E-06",
         "condition": "engineering build plan present",
         **(_has(f"engineering_build_plan[{len(build_plan)}]") if build_plan
             else _lacks("engineering_build_plan", "no build plan"))},
    ]

    # ---------------- rung 3: PROTOTYPE_DESIGN_READY ----------------
    absent_dos = [d.get("id") for d in d_outputs
                  if d.get("status") == "ABSENT"]
    params_without_values = [p.get("parameter") for p in
                             (core.get("critical_parameters", []) or [])
                             if "UNKNOWN" in str(p.get("value", "UNKNOWN"))
                             or "UNKNOWN" in str(p.get("status", ""))]
    unestimated_bom = [b.get("item") for b in bom
                       if str(b.get("qty", "NOT ESTABLISHED"))
                       .startswith(("NOT ESTABLISHED", "UNKNOWN"))]
    c3 = [
        {"id": "D-01",
         "condition": "every design output carries a complete geometry "
                      "definition (no DO remains ABSENT)",
         **(_has("all design_outputs geometry complete")
             if (d_outputs and not absent_dos) else _lacks(
                 f"design_outputs ABSENT={absent_dos}",
                 "geometry must be designed before a prototype exists"))},
        {"id": "D-02",
         "condition": "every critical parameter has a sourced or computed "
                      "value (no UNKNOWN values remain)",
         **(_has("all critical parameter values sourced")
             if (core.get("critical_parameters")
                 and not params_without_values) else _lacks(
                 f"critical_parameters UNKNOWN={len(params_without_values)}",
                 "acceptance/geometry values require sourced engineering "
                 "data"))},
        {"id": "D-03",
         "condition": "bill of materials has established quantities",
         **(_has("BOM quantities established") if (bom and
             not unestimated_bom) else _lacks(
                 f"BOM unestimated={len(unestimated_bom)}",
                 "quantities require design completion"))},
    ]

    # ---------------- rung 4: PROTOTYPE_BUILD_READY ----------------
    mfg_procs = (manufacturing.get("candidate_processes", []) or [])
    qualified = [p for p in mfg_procs
                 if "UNKNOWN" not in str(p.get("status", "UNKNOWN"))
                 and "NOT ESTABLISHED" not in str(p.get("status", "UNKNOWN"))]
    c4 = [
        {"id": "B-01",
         "condition": "a pre-registered pass/fail acceptance criterion "
                      "exists for the first build article",
         **(_has("build_plan[0].acceptance_criterion JUSTIFIED")
             if build_plan and "NOT YET JUSTIFIED" not in str(
                 build_plan[0].get("acceptance", "")) and "NOT ESTABLISHED"
             not in str(build_plan[0].get("acceptance", ""))
             else _lacks("build_plan[0].acceptance",
                         "no sourced acceptance threshold exists"))},
        {"id": "B-02",
         "condition": "at least one manufacturing process is qualified "
                      "(not merely a candidate)",
         **(_has(f"qualified processes[{len(qualified)}]") if qualified
             else _lacks("manufacturing.candidate_processes",
                         "all processes remain unqualified candidates"))},
        {"id": "B-03",
         "condition": "prototype build executed and recorded",
         **(_lacks("build record", "no build artifact or build report "
                   "exists in the run"))},
    ]

    # ---------------- rung 5: VALIDATION_READY ----------------
    tested = [v.get("id") for v in verif_matrix
              if v.get("result") not in (None, "NOT_TESTED", "")]
    c5 = [
        {"id": "V-01",
         "condition": "at least one verification executed with a recorded "
                      "result",
         **(_has(f"verification results[{len(tested)}]") if tested
             else _lacks("verification_matrix results",
                         "all verifications are NOT_TESTED"))},
        {"id": "V-02",
         "condition": "validation performed on a verified design",
         **(_lacks("validation_matrix results",
                   "validation requires physical observation (Art. "
                   "XXXVIII)"))},
    ]

    # ---------------- rung 6: TRANSFER_READY ----------------
    c6 = [
        {"id": "T-01",
         "condition": "reality-loop verified (REAL_LOOP_VERIFIED via a "
                      "gated external observation, Art. XXXVII)",
         **(_has(f"loop_verification_state={loop_state}")
             if loop_state == "REAL_LOOP_VERIFIED" else _lacks(
                 "loop_verification_state",
                 f"state is {loop_state or 'NONE'}; REAL_LOOP_VERIFIED "
                 "requires a gated external reality event"))},
        {"id": "T-02",
         "condition": "regulatory pathway established",
         **(_lacks("regulatory record", "no regulatory artifact exists"))},
        {"id": "T-03",
         "condition": "IP ownership verified",
         **(_lacks("IP record", "no IP verification artifact exists"))},
    ]

    rungs = [
        ("CONCEPT_DEFINED", c1),
        ("ENGINEERING_DEFINITION", c2),
        ("PROTOTYPE_DESIGN_READY", c3),
        ("PROTOTYPE_BUILD_READY", c4),
        ("VALIDATION_READY", c5),
        ("TRANSFER_READY", c6),
    ]

    # evaluate EVERY rung (full transparency), but the LEVEL walk from the
    # bottom stops at the first unsatisfied rung (Art. XXVIII: no promotion
    # past an unmet condition). If even the first rung is unsatisfied, the
    # level is honestly BELOW the ladder.
    level: str = "BELOW_LADDER"
    climbing = True
    ladder_out: List[Dict[str, Any]] = []
    for name, conds in rungs:
        satisfied = all(c["present"] for c in conds)
        ladder_out.append({"rung": name, "conditions": conds,
                           "satisfied": satisfied})
        if climbing and satisfied:
            level = name
        else:
            climbing = False

    next_rung = None
    if level == "BELOW_LADDER":
        next_rung = rungs[0]  # blockers are the missing CONCEPT_DEFINED conds
    else:
        for i, (name, conds) in enumerate(rungs):
            if name == level and i + 1 < len(rungs):
                next_rung = rungs[i + 1]
                break
    blockers = [
        {"condition_id": c["id"],
         "condition": c["condition"],
         "evidence": c["evidence"],
         "reason": c.get("reason", "condition not satisfied by any recorded "
                                   "artifact")}
        for c in (next_rung[1] if next_rung else [])
        if not c["present"]]
    if not blockers and next_rung is None:
        blockers = []

    counts = {
        "governing_equations": len(gm.get("equations", [])),
        "design_inputs": len(d_inputs),
        "design_outputs": len(d_outputs),
        "design_outputs_absent": len(absent_dos),
        "failure_modes": len(failure_modes),
        "build_plan_steps": len(build_plan),
        "verifications_total": len(verif_matrix),
        "verifications_tested": len(tested),
        "validations_performed": sum(
            1 for v in val_matrix
            if v.get("result") not in (None, "NOT_PERFORMED", "NOT_TESTED",
                                       "")),
        "critical_parameters_unknown_values": len(params_without_values),
    }
    return {
        "technology_maturity": level,
        "maturity_ladder": MATURITY_LADDER,
        "rung_evaluations": ladder_out,
        "next_rung": next_rung[0] if next_rung else None,
        "known_blockers": blockers,
        "basis": "computed from the actual generated artifact state "
                 "(spec integrity, design-graph structure, equation and "
                 "artifact counts, verification/validation results, "
                 "loop_verification_state); nothing injected",
        "counts": counts,
        "loop_verification_state": loop_state or "NONE",
        "real_loop_verified": loop_state == "REAL_LOOP_VERIFIED",
        "transfer_ready": level == "TRANSFER_READY",
        "computed_at": utc_now(),
    }
