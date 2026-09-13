"""discovery_fabric/engine/causal_learning.py — R452 Phase 7: the
first causal learning loop closed IN SOFTWARE.

Directive Phase 7 (the strategically most important work):

    CANDIDATE
       ↓
    MECHANISTIC MODEL
       ↓
    VIRTUAL EXPERIMENT
       ↓
    FALSIFICATION / SUPPORT OUTCOME
       ↓
    TECHNICAL STATE UPDATE
       ↓
    AUTOMATIC MUTATION
       ↓
    NEW CANDIDATE
       ↓
    RE-EVALUATION

"The mutation must be generated from the experiment result, not from
an unrelated random second LLM proposal."

"Store the causal edge explicitly:

    parent_candidate_id
    experiment_id
    observed_outcome
    failed_constraint
    mutation_reason
    child_candidate_id

Add a regression proving that changing the experiment outcome changes
the resulting mutation."

This module is DETERMINISTIC SOFTWARE (zero LLM): the mutation is the
closed-form inverse of the Poiseuille relation solved for the
experiment's own observed deficit (mechanistic_solver.
mechanistic_mutation); the technical state update records the measured
fact (the computed flow vs the problem's own requirement); the child
candidate carries the mutated parameter and is re-evaluated through
the SAME experiment chain (no second, weaker evaluator — Art. IV).

HONESTY CONTRACT:
  - loop_verification_state = SYNTHETIC_LOOP_VERIFIED (Art. XXXVII):
    the machinery works, the posterior moved by COMPUTATION, not by
    external reality; a virtual experiment's evidence class is
    COMPUTATIONAL_RESULT and can never be labeled a physical
    observation (Art. XXXVIII / LIII).
  - a SUPPORT outcome is computational support, never validation.
  - the loop is BOUNDED (one experiment, one mutation, one
    re-evaluation — the directive's "one bounded virtual decisive
    experiment"); the record says so explicitly.
  - every state change is a recorded transition with before/after
    (Art. XI discipline; the technical state is append-only).
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from . import mechanistic_solver as ms
from . import decisive_experiment as de

CAUSAL_LOOP_VERSION = "causal_learning/1.0.0"

#: the closed loop-stage vocabulary (the directive's eight steps)
LOOP_STAGES = (
    "CANDIDATE",
    "MECHANISTIC_MODEL",
    "VIRTUAL_EXPERIMENT",
    "FALSIFICATION_SUPPORT_OUTCOME",
    "TECHNICAL_STATE_UPDATE",
    "AUTOMATIC_MUTATION",
    "NEW_CANDIDATE",
    "RE_EVALUATION",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _cid(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def run_causal_learning_loop(
        problem_text: str,
        parent_candidate_id: str,
        candidate_parameters: Optional[Dict[str, Dict[str, Any]]] = None,
        problem_constraints: Optional[Dict[str, Any]] = None,
        run_label: str = "r452-causal-loop") -> Dict[str, Any]:
    """Execute ONE bounded causal learning loop.

    Returns the full loop record: the eight stages, the experiment
    contract, the causal edge (the directive's six fields, verbatim),
    the technical state transition, and the honest verification state.

    Fail-closed behaviors (never silently weaker):
      - an invalid experiment contract (no kill outcome) STOPS the
        loop at VIRTUAL_EXPERIMENT (the directive's Phase 6 invariant
        enforced inside the loop);
      - a MODEL_INVALIDITY or INCONCLUSIVE experiment records the
        honest state and NO mutation executes;
      - a mutation that violates the problem's own declared
        constraints (when the caller supplies them) is REFUSED and
        recorded (a constraint-violating mutation is not a discovery).
    """
    loop_id = "cl-" + _cid(
        json.dumps([run_label, parent_candidate_id, problem_text[:400]],
                   default=str))
    stages: List[Dict[str, Any]] = []

    def _stage(name: str, state: str, **kw) -> None:
        stages.append({"stage": name, "state": state,
                      "recorded_at": _now(), **kw})

    # 1. CANDIDATE --------------------------------------------------------
    _stage("CANDIDATE", "ENTERED",
           candidate_id=parent_candidate_id,
           declared_parameters={
               k: v.get("value") for k, v in
               (candidate_parameters or {}).items()})

    # 2. MECHANISTIC MODEL -------------------------------------------------
    model_vars = ms.build_canonical_variables(
        problem_text, candidate_parameters)
    _stage("MECHANISTIC_MODEL", "BUILT" if not
           model_vars["unknown_variables"] else "PARTIAL",
           unknown_variables=model_vars["unknown_variables"],
           variables={k: v.get("value") for k, v in
                      model_vars["variables"].items()})

    # 3. VIRTUAL EXPERIMENT (the decisive experiment contract gates it) --
    exp = ms.run_mechanistic_virtual_experiment(
        problem_text, parent_candidate_id, candidate_parameters,
        experiment_id=f"{loop_id}:vexp")
    contract = de.build_virtual_experiment_contract(exp)
    contract_valid = contract["validation"]["valid"]
    _stage("VIRTUAL_EXPERIMENT", exp["status"],
           experiment_id=exp.get("experiment_id"),
           solver_status=exp["status"],
           contract_valid=contract_valid,
           contract_rejection=contract["validation"]
           ["rejection_reason"])
    if not contract_valid:
        return _finish(loop_id, run_label, stages, exp, None, None,
                       None, None, None, None,
                       stop_reason="EXPERIMENT_CONTRACT_INVALID",
                       note=("the decisive-experiment contract failed "
                             "validation — no kill outcome exists, so "
                             "no decisive experiment ran (Phase 6 "
                             "invariant enforced inside the loop)"))
    if exp["status"] in ("MODEL_INVALIDITY", "INCONCLUSIVE_UNKNOWN_INPUT"):
        return _finish(loop_id, run_label, stages, exp, contract, None,
                       None, None, None, None,
                       stop_reason=f"EXPERIMENT_{exp['status']}",
                       note=("the mechanistic experiment could not "
                             "produce a decisive computed outcome; NO "
                             "mutation executes (an honest unknown, "
                             "never a fabricated result)"))

    # 4. FALSIFICATION / SUPPORT OUTCOME ----------------------------------
    co = exp["computed_outcome"]
    outcome = co["outcome"]
    if outcome == "COMPUTED_FAIL":
        loop_outcome = "FALSIFIED_CONSTRAINT"
        _stage("FALSIFICATION_SUPPORT_OUTCOME", loop_outcome,
               observed=outcome,
               detail=(f"predicted {co['candidate_flow_ml_min']:.4f} "
                       f"mL/min < required "
                       f"{co['required_flow_ml_min']:.4f} mL/min"))
    elif outcome in ("COMPUTED_PASS",
                     "COMPUTED_PASS_BASELINE_INCONCLUSIVE"):
        loop_outcome = "SUPPORTED_COMPUTATIONALLY"
        _stage("FALSIFICATION_SUPPORT_OUTCOME", loop_outcome,
               observed=outcome,
               detail=(f"predicted {co['candidate_flow_ml_min']:.4f} "
                       f"mL/min >= required "
                       f"{co['required_flow_ml_min']:.4f} mL/min "
                       f"(computational support — NOT validation)"))
        return _finish(loop_id, run_label, stages, exp, contract,
                       loop_outcome, None, None, None, None,
                       stop_reason="NO_MUTATION_REQUIRED",
                       note=("the candidate already satisfies the "
                             "problem's own requirement computationally; "
                             "no mutation executes (a mutation here "
                             "would be optimization, not learning)"))
    else:
        loop_outcome = "NO_ADVANTAGE_DETECTED"
        _stage("FALSIFICATION_SUPPORT_OUTCOME", loop_outcome,
               observed=outcome,
               detail=("both arms meet the requirement; the candidate "
                       "offers no measured advantage over the "
                       "baseline"))
        return _finish(loop_id, run_label, stages, exp, contract,
                       loop_outcome, None, None, None, None,
                       stop_reason="NO_MUTATION_REQUIRED",
                       note=("the candidate already satisfies the "
                             "problem's own requirement computationally; "
                             "no mutation executes (a mutation here "
                             "would be optimization, not learning)"))

    # 5. TECHNICAL STATE UPDATE -------------------------------------------
    failed_constraint = (
        f"primary-segment flow >= "
        f"{co['required_flow_ml_min']:.4f} mL/min at the stated "
        f"operating condition (the problem's own declared requirement)")
    observed_fact = {
        "fact": (f"computed primary-segment flow "
                 f"{co['candidate_flow_ml_min']:.6f} mL/min under the "
                 f"declared parameters"),
        "epistemic_class": "COMPUTED",
        "observed_at": _now(),
        "experiment_id": exp["experiment_id"],
    }
    technical_state = {
        "before": {
            "constraint": failed_constraint,
            "status": "UNMEASURED",
        },
        "after": {
            "constraint": failed_constraint,
            "status": "VIOLATED_COMPUTATIONALLY",
            "measured": co["candidate_flow_ml_min"],
            "required": co["required_flow_ml_min"],
            "deficit_ml_min": round(
                co["required_flow_ml_min"] -
                co["candidate_flow_ml_min"], 6),
        },
        "transition": "TECHNICAL_STATE_UPDATED_FROM_EXPERIMENT",
        "transition_rule": ("the technical state moves ONLY on the "
                           "experiment's own computed observation — "
                           "never on narrative"),
    }
    _stage("TECHNICAL_STATE_UPDATE", "UPDATED",
           observed_fact=observed_fact,
           failed_constraint=failed_constraint,
           deficit_ml_min=technical_state["after"]["deficit_ml_min"])

    # 6. AUTOMATIC MUTATION (from the experiment result) ------------------
    mutation = ms.mechanistic_mutation(exp, candidate_parameters or {})
    if mutation is None:
        return _finish(loop_id, run_label, stages, exp, contract,
                       loop_outcome, technical_state, None, None,
                       None, stop_reason="MUTATION_NOT_DERIVABLE",
                       note=("no mechanistic mutation is derivable "
                             "from this experiment outcome (the "
                             "closed-form inverse does not apply)"))
    # constraint check: a mutation that violates the problem's own
    # declared constraints is REFUSED (recorded, never executed)
    if problem_constraints:
        d_max = problem_constraints.get("max_primary_diameter_mm")
        if isinstance(d_max, (int, float)) and \
                mutation["to_value"] > float(d_max):
            mutation["refused"] = True
            mutation["refusal_reason"] = (
                f"mutated diameter {mutation['to_value']} mm exceeds "
                f"the problem's own declared constraint "
                f"{d_max} mm — the mutation is refused and recorded")
            _stage("AUTOMATIC_MUTATION", "REFUSED_BY_CONSTRAINT",
                   mutation=mutation)
            return _finish(loop_id, run_label, stages, exp, contract,
                           loop_outcome, technical_state, mutation,
                           None, None,
                           stop_reason="MUTATION_REFUSED_BY_PROBLEM_CONSTRAINT",
                           note=("the derived mutation violates the "
                                 "problem's own declared constraint; "
                                 "the constraint stands and the "
                                 "candidate is NOT silently mutated "
                                 "past it"))
    _stage("AUTOMATIC_MUTATION", "EXECUTED",
           mutation_kind=mutation["mutation_kind"],
           from_value=mutation["from_value"],
           to_value=mutation["to_value"],
           derivation=mutation["derivation"])

    # 7. NEW CANDIDATE ------------------------------------------------------
    child_candidate_id = f"{parent_candidate_id}:mut1"
    child_parameters = dict(candidate_parameters or {})
    child_parameters[mutation["target_variable"]] = {
        "value": mutation["to_value"],
        "unit": "mm",
        "epistemic_class": "COMPUTED",
        "source": (f"mechanistic mutation "
                   f"{mutation['mutation_kind']} from experiment "
                   f"{exp['experiment_id']} (closed-form inverse "
                   f"Poiseuille for the required flow)"),
    }
    _stage("NEW_CANDIDATE", "CREATED",
           candidate_id=child_candidate_id,
           mutated_parameter=(mutation["target_variable"],
                              mutation["from_value"],
                              mutation["to_value"]))

    # 8. RE-EVALUATION (the SAME experiment chain — no weaker evaluator) --
    child_exp = ms.run_mechanistic_virtual_experiment(
        problem_text, child_candidate_id, child_parameters,
        experiment_id=f"{loop_id}:vexp-child")
    child_co = child_exp.get("computed_outcome") or {}
    if child_exp["status"] == "COMPUTED_FAIL":
        child_outcome = "CHILD_STILL_FALSIFIED"
    elif child_exp["status"] in ("COMPUTED_PASS",
                                 "COMPUTED_PASS_BASELINE_INCONCLUSIVE"):
        child_outcome = "CHILD_SUPPORTS_HYPOTHESIS_COMPUTATIONALLY"
    else:
        child_outcome = f"CHILD_{child_exp['status']}"
    _stage("RE_EVALUATION", child_outcome,
           child_experiment_id=child_exp.get("experiment_id"),
           child_flow_ml_min=child_co.get("candidate_flow_ml_min"),
           required_ml_min=child_co.get("required_flow_ml_min"))

    # THE CAUSAL EDGE (the directive's six fields, verbatim) --------------
    causal_edge = {
        "parent_candidate_id": parent_candidate_id,
        "experiment_id": exp["experiment_id"],
        "observed_outcome": outcome,
        "failed_constraint": failed_constraint,
        "mutation_reason": mutation["causal_basis"]["mutation_reason"],
        "child_candidate_id": child_candidate_id,
    }

    return _finish(loop_id, run_label, stages, exp, contract,
                   loop_outcome, technical_state, mutation,
                   child_exp, causal_edge,
                   child_outcome=child_outcome)


def _finish(loop_id: str, run_label: str, stages: List[Dict[str, Any]],
            exp: Dict[str, Any], contract: Optional[Dict[str, Any]],
            loop_outcome: Optional[str],
            technical_state: Optional[Dict[str, Any]],
            mutation: Optional[Dict[str, Any]],
            child_exp: Optional[Dict[str, Any]],
            causal_edge: Optional[Dict[str, Any]],
            stop_reason: Optional[str] = None,
            child_outcome: Optional[str] = None,
            note: Optional[str] = None) -> Dict[str, Any]:
    return {
        "artifact_type": "R452_CAUSAL_LEARNING_LOOP",
        "loop_id": loop_id,
        "run_label": run_label,
        "causal_loop_version": CAUSAL_LOOP_VERSION,
        "loop_stages_executed": [s["stage"] for s in stages],
        "stages": stages,
        "experiment": exp,
        "experiment_contract": contract,
        "loop_outcome": loop_outcome,
        "child_outcome": child_outcome,
        "technical_state": technical_state,
        "mutation": mutation,
        "child_experiment": child_exp,
        "causal_edge": causal_edge,
        "stop_reason": stop_reason,
        "note": note,
        "bounded": True,
        "loop_verification_state": "SYNTHETIC_LOOP_VERIFIED",
        "loop_verification_basis": (
            "the loop closed on COMPUTED evidence only (a virtual "
            "decisive experiment through the deterministic solver); "
            "the machinery works and the technical state moved on the "
            "experiment's own observation — but NO external reality "
            "produced the evidence (Art. XXXVII/XXXVIII: SYNTHETIC, "
            "never REAL_LOOP_VERIFIED; a virtual experiment may never "
            "be labeled a physical observation)"),
        "deterministic": True,
        "llm_calls": 0,
        "recorded_at": _now(),
    }
