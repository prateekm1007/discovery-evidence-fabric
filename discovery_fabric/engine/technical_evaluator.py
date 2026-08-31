"""discovery_fabric/engine/technical_evaluator.py — R379 TECHNICAL
IMPROVEMENT ENGINE V2, layer 2: THE TECHNICAL EVALUATOR CONTRACT.

CEO directive (2026-08-31, TECHNICAL IMPROVEMENT ENGINE V2):

> "2. Define a TECHNICAL EVALUATOR CONTRACT.
>  Input:  candidate technical state, constraints, objective,
>          available evidence.
>  Output: predicted behavior, constraint violations, failure modes,
>          sensitivity/limiting variables, uncertainty, improvement
>          directions, provenance."

This module implements the contract for the technical domain and
ships the FIRST live evaluator: `analytical_monotone_v1` — a
deterministic sign-propagation engine over the structured technical
state's dependency graph, at the STRUCTURED_CONSTRAINT fidelity tier
(evidence rank 3: MODEL-class inferences — every output is labeled as
a model inference, never a measurement; Art. XXVIII/XXXVIII).

What the evaluator CAN honestly compute today:
  - numeric constraint checking where a value and a limit both exist
  - the DIRECTION each parameter's increase moves every related
    target (sign propagation through MONOTONE relations)
  - which mutable parameter is the LIMITING VARIABLE (a declared
    ORDINAL convention — see LEVERAGE_CONVENTION below)
  - machine-generated DIRECTIONAL FEEDBACK:
    "The limiting variable is X. Changing X in direction Y is
     predicted to improve objective Z while preserving constraints A/B."
  - the uncertainty record (UNKNOWN values, MODELLED relations) —
    recorded, never zeroed (Art. XXV)

What it CANNOT (and therefore records instead of pretending):
  - magnitudes at the MONOTONE tier (no functional forms)
  - output values that depend on UNKNOWN parameters
  - physical measurements (rank 5 is reality's alone)

The evaluator NEVER calls an LLM and never touches the network: the
same technical state always yields the same evaluation (Art. XVIII,
deterministic diagnostics; pinned by metamorphic tests).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .candidate import sha256_obj, utc_now
from .evaluator_contract import register_evaluator
from .technical_state import get_technical_state, mutable_parameters

EVALUATOR_ID = "analytical_monotone_v1"
FIDELITY_TIER = "STRUCTURED_CONSTRAINT"
EVIDENCE_RANK = 3          # MODEL-class inference (never rank 4/5 here)

# ---------------------------------------------------------------------------
# Declared conventions (Art. XXVII — every threshold/convention carries
# its class and justification BEFORE any computation uses it)
# ---------------------------------------------------------------------------
LEVERAGE_CONVENTION = {
    "name": "ORDINAL_LEVERAGE_BY_PATH_LENGTH",
    "epistemic_class": "ENGINEERING",
    "justification": (
        "with MONOTONE-only relations the evaluator cannot rank "
        "leverage by magnitude; it ranks by (1) fewest constraint "
        "blocks, (2) shortest causal path from the parameter to the "
        "objective target, (3) envelope provenance class (EXTRACTED "
        "beats MODELLED). This is a declared ordinal convention, not a "
        "measurement — recorded on every evaluation that uses it."),
    "uncertainty": "ordinal only; magnitudes are UNKNOWN at this tier",
}

CONSTRAINT_BLOCK_POLICY = {
    "name": "DIRECTIONAL_FAIL_CLOSED",
    "epistemic_class": "ENGINEERING",
    "justification": (
        "a proposed change is constraint-BLOCKED when (a) the changed "
        "parameter's own numeric constraint would be violated at the "
        "proposed value, or (b) a relation-connected constraint target "
        "is already VIOLATED or value-UNKNOWN and the predicted "
        "direction moves it TOWARD its bound. Fail-closed on "
        "directional risk: an unknown-position target moving toward a "
        "bound is a blocked move, not an accepted one (Art. IV)."),
    "uncertainty": "direction-level only at this tier",
}


# ---------------------------------------------------------------------------
# Output shapes (the contract's OUTPUT side)
# ---------------------------------------------------------------------------
def _sign(direction: str) -> int:
    return 1 if direction == "INCREASES" else -1


class _Graph:
    """cause -> effect adjacency over the declared MONOTONE relations."""

    def __init__(self, state: Dict[str, Any]):
        self.edges: Dict[str, List[Tuple[str, int, str]]] = {}
        self.relation_class: Dict[Tuple[str, str], str] = {}
        for d in (state or {}).get("dependencies") or []:
            cause = str(d.get("cause"))
            effect = str(d.get("effect"))
            self.edges.setdefault(cause, []).append(
                (effect, _sign(str(d.get("direction"))),
                 str(d.get("relation_id"))))
            self.relation_class[(cause, effect)] = \
                str(d.get("relation_class") or "MODELLED")

    def propagate(self, source: str) -> Dict[str, Dict[str, Any]]:
        """Sign of the change at every reachable target when `source`
        INCREASES by a differential. Multiple paths with disagreeing
        signs mark the target AMBIGUOUS (recorded, never resolved by
        preference — Art. II)."""
        result: Dict[str, Dict[str, Any]] = {}
        frontier = [(source, 1, [])]
        best_sign: Dict[str, int] = {}
        ambiguous: set = set()
        while frontier:
            node, sign, path = frontier.pop()
            for (nxt, edge_sign, rid) in self.edges.get(node, []):
                new_sign = sign * edge_sign
                new_path = path + [rid]
                if nxt in best_sign and best_sign[nxt] != new_sign:
                    ambiguous.add(nxt)
                    continue
                if nxt in best_sign:
                    if len(new_path) < len(result[nxt]["path"]):
                        result[nxt] = {"sign": new_sign,
                                       "path": new_path}
                    continue
                best_sign[nxt] = new_sign
                result[nxt] = {"sign": new_sign, "path": new_path}
                # guard against cycles: never revisit with equal sign
                frontier.append((nxt, new_sign, new_path))
        for a in ambiguous:
            result[a] = {"sign": 0, "path": result.get(a, {}).get("path",
                                                                  []),
                         "ambiguous": True}
        return result


def evaluate_technical_state(state: Dict[str, Any]) -> Dict[str, Any]:
    """The deterministic analytical evaluation. INPUT: the structured
    technical state. OUTPUT: the contract's full shape — predictions,
    constraint results, sensitivity, limiting variable, improvement
    directions, uncertainty, computation log (provenance)."""
    params = {p["param_id"]: p for p in
              (state or {}).get("parameters") or []}
    constraints = (state or {}).get("constraints") or []
    objectives = (state or {}).get("objectives") or []
    graph = _Graph(state)

    # ---- objective resolution ------------------------------------------
    # V2 evaluates against the FIRST declared objective (the problem's
    # primary objective; multiple objectives are recorded, ranked by
    # declaration order — a lexicographic convention, declared).
    objective = objectives[0] if objectives else None
    obj_target = str((objective or {}).get("target") or "")
    obj_dir = str((objective or {}).get("direction") or "")
    obj_known = obj_target in params and obj_dir in ("MINIMIZE",
                                                     "MAXIMIZE")

    # ---- design variables vs outcome variables --------------------------
    # A parameter that is the EFFECT of any declared relation is an
    # OUTCOME (it moves when its causes move); a parameter that is
    # never an effect is a DESIGN variable (a knob the technology
    # actually sets). Mutations move DESIGN variables only — 'setting'
    # an outcome directly is physically meaningless (the outcome moves
    # because its causes move). Declared convention, recorded per
    # evaluation.
    effect_side = {
        str(d.get("effect"))
        for d in (state or {}).get("dependencies") or []}
    for pid, p in params.items():
        p["is_design_variable"] = pid not in effect_side


    # ---- numeric constraint results -------------------------------------
    constraint_results: List[Dict[str, Any]] = []
    for c in constraints:
        target = params.get(str(c.get("target")))
        result = {
            "constraint_id": c.get("constraint_id"),
            "target": c.get("target"), "bound": c.get("bound"),
            "limit": c.get("limit"), "limit_class": c.get("limit_class"),
        }
        if target is None or target.get("value") is None or \
                not isinstance(target.get("value"), (int, float)):
            result["status"] = "UNVERIFIABLE"
            result["reason"] = (
                f"target {c.get('target')} has no numeric value "
                f"(UNKNOWN) — the constraint cannot be checked at this "
                f"tier (Art. XXV: unknown is not satisfied)")
        else:
            v = float(target["value"])
            lim = float(c.get("limit"))
            ok = (v <= lim) if c.get("bound") == "<=" else (v >= lim)
            result["status"] = "SATISFIED" if ok else "VIOLATED"
            result["value"] = v
            result["slack"] = round(
                (lim - v) if c.get("bound") == "<=" else (v - lim), 4)
        constraint_results.append(result)

    # ---- sensitivity: direction of objective response per parameter ---
    sensitivity: Dict[str, Dict[str, Any]] = {}
    for pid, p in params.items():
        entry: Dict[str, Any] = {
            "param_id": pid, "category": p.get("category"),
            "value_class": p.get("value_class"),
            "envelope": [p.get("range_min"), p.get("range_max")],
            "envelope_class": p.get("range_class"),
        }
        if not obj_known:
            entry["objective_response"] = "NO_OBJECTIVE"
        elif pid == obj_target:
            # direct: the parameter IS the objective target. MINIMIZE
            # means increasing it DEGRADES the objective (the inverted
            # first draft here proposed INCREASING the target of a
            # MINIMIZE objective — caught by the adversarial
            # evaluation tests and pinned there)
            entry["objective_response"] = "DIRECT"
            entry["increase_effect"] = (
                "DEGRADES" if obj_dir == "MINIMIZE" else "IMPROVES")
            entry["path_length"] = 0
        else:
            prop = graph.propagate(pid)
            hit = prop.get(obj_target)
            if hit is None:
                entry["objective_response"] = "NO_PATH"
            elif hit.get("ambiguous"):
                entry["objective_response"] = "AMBIGUOUS"
            else:
                s = hit["sign"]
                # MINIMIZE: target moving DOWN improves -> source UP
                # with sign s means target moves by s; improving iff
                # (obj_dir == MINIMIZE and s < 0) or (MAXIMIZE, s > 0)
                improves = (obj_dir == "MINIMIZE" and s < 0) or \
                           (obj_dir == "MAXIMIZE" and s > 0)
                entry["objective_response"] = "PATH"
                entry["increase_effect"] = \
                    "IMPROVES" if improves else "DEGRADES"
                entry["path_length"] = len(hit.get("path") or [])
                entry["path_relation_ids"] = hit.get("path")
        sensitivity[pid] = entry

    # ---- improvement directions (the CEO's directional feedback) -------
    improvement_directions: List[Dict[str, Any]] = []
    for pid, s in sensitivity.items():
        if s.get("increase_effect") not in ("IMPROVES", "DEGRADES"):
            continue
        improving_move = ("INCREASE" if s["increase_effect"] == "IMPROVES"
                          else "DECREASE")
        # constraint blocks on this move
        blocks: List[Dict[str, Any]] = []
        p = params[pid]
        # (a) the parameter's own numeric constraints
        for cr in constraint_results:
            if cr.get("target") != pid:
                continue
            if cr.get("status") == "UNVERIFIABLE":
                blocks.append({
                    "constraint_id": cr.get("constraint_id"),
                    "why": ("target value UNKNOWN; a move in EITHER "
                            "direction is unverifiable against the "
                            "bound — fail-closed (Art. IV)")})
                continue
            bound = cr.get("bound")
            moving_up = improving_move == "INCREASE"
            toward = (bound == "<=" and moving_up) or \
                     (bound == ">=" and not moving_up)
            if toward and (cr.get("status") == "VIOLATED" or
                           (cr.get("slack") is not None
                            and cr["slack"] <= 0)):
                blocks.append({
                    "constraint_id": cr.get("constraint_id"),
                    "why": ("the move goes TOWARD a bound that is "
                            "already violated or at zero slack")})
        # (b) relation-connected constraint targets
        prop = graph.propagate(pid)
        for cr in constraint_results:
            tgt = str(cr.get("target") or "")
            if tgt == pid or tgt not in prop:
                continue
            hit = prop[tgt]
            if hit.get("ambiguous") or not hit.get("sign"):
                blocks.append({
                    "constraint_id": cr.get("constraint_id"),
                    "why": ("ambiguous influence on the constraint "
                            "target — cannot certify preservation")})
                continue
            bound = cr.get("bound")
            target_moves_up = hit["sign"] > 0
            toward = (bound == "<=" and target_moves_up) or \
                     (bound == ">=" and not target_moves_up)
            if not toward:
                continue      # moving AWAY from the bound: safe
            if cr.get("status") == "VIOLATED":
                blocks.append({
                    "constraint_id": cr.get("constraint_id"),
                    "why": ("constraint target already VIOLATED and the "
                            "move pushes further toward the bound")})
            elif cr.get("status") == "UNVERIFIABLE":
                blocks.append({
                    "constraint_id": cr.get("constraint_id"),
                    "why": ("constraint target value UNKNOWN and the "
                            "move is TOWARD the bound — unverifiable "
                            "preservation is not preservation")})
        mutable = (p.get("range_min") is not None
                   or p.get("range_max") is not None)
        improvement_directions.append({
            "param_id": pid,
            "improving_move": improving_move,
            "objective_response": s.get("objective_response"),
            "path_length": s.get("path_length"),
            "envelope": s.get("envelope"),
            "envelope_class": s.get("envelope_class"),
            "mutable": mutable,
            "is_design_variable": p.get("is_design_variable", True),
            "blocked_by": blocks,
            "statement": (
                f"Changing {p.get('name') or pid} by "
                f"{improving_move.lower()} is predicted to "
                f"{'improve' if s['increase_effect'] == 'IMPROVES' else 'degrade'} "
                f"objective {obj_target} ({obj_dir})"
                + (f" while preserving constraints"
                   if not blocks else
                   f" but is BLOCKED by {len(blocks)} constraint(s)")
                + ("" if mutable else
                   "; NOT MUTABLE (no declared envelope — unbounded "
                   "parameters are immutable, ADR_R379)")),
        })

    # ---- limiting variable (the declared ordinal convention) ----------
    # MOVABLE = mutable (declared envelope) AND a design variable
    movable = [d for d in improvement_directions
               if d["mutable"] and d.get("is_design_variable")
               and not d["blocked_by"]]
    limiting_variable: Optional[Dict[str, Any]] = None
    if movable:
        def _rank(d: Dict[str, Any]) -> Tuple[int, int, int]:
            env_class = d.get("envelope_class") or "UNKNOWN"
            return (
                d.get("path_length") if d.get("path_length") is not None
                else 99,
                {"EXTRACTED": 0, "MODELLED": 1}.get(env_class, 2),
                len(d.get("blocked_by") or []),
            )
        movable.sort(key=_rank)
        best = movable[0]
        p = params[best["param_id"]]
        limiting_variable = {
            "param_id": best["param_id"],
            "name": p.get("name"),
            "improving_move": best["improving_move"],
            "objective_target": obj_target,
            "objective_direction": obj_dir,
            "envelope": best.get("envelope"),
            "envelope_class": best.get("envelope_class"),
            "causal_path_length": best.get("path_length"),
            "statement": (
                f"The limiting variable is {p.get('name') or best['param_id']}. "
                f"Changing it by {best['improving_move'].lower()} is "
                f"predicted to improve objective {obj_target} "
                f"({obj_dir}) while preserving all declared constraints "
                f"that are checkable at this tier."),
            "convention": LEVERAGE_CONVENTION,
        }

    # ---- predictions (behavior, direction-level) ------------------------
    predictions: Dict[str, Any] = {}
    for pid, p in params.items():
        prop = graph.propagate(pid)
        predictions[pid] = {
            "value": p.get("value"),
            "value_class": p.get("value_class"),
            "responds_to": [
                {"param": src, "sign": (d.get("sign"))}
                for src, d in _influence_on(state, pid).items()],
        }
    # outputs = non-parameter quantities are V2-empty (all targets are
    # params); recorded so the contract shape is visible
    predictions["_note"] = (
        "direction-level predictions only at the STRUCTURED_CONSTRAINT "
        "tier; magnitudes are UNKNOWN until a NUMERICAL_SOLVER-tier "
        "evaluator is registered")

    # ---- uncertainty -----------------------------------------------------
    uncertainty = {
        "unknown_value_params": sorted(
            pid for pid, p in params.items()
            if p.get("value") is None),
        "modelled_relations": sum(
            1 for d in (state or {}).get("dependencies") or []
            if d.get("relation_class") == "MODELLED"),
        "extracted_relations": sum(
            1 for d in (state or {}).get("dependencies") or []
            if d.get("relation_class") == "EXTRACTED"),
        "unverifiable_constraints": [
            cr.get("constraint_id") for cr in constraint_results
            if cr.get("status") == "UNVERIFIABLE"],
        "objective_known": obj_known,
        "note": ("UNKNOWN values are never treated as zeros; "
                 "unverifiable constraints are never treated as "
                 "satisfied (Art. XXV / Art. IV)"),
    }

    status = "UNQUANTIFIED"
    if obj_known:
        n_path = sum(1 for s in sensitivity.values()
                     if s.get("objective_response") in
                     ("PATH", "DIRECT", "AMBIGUOUS"))
        status = ("QUANTIFIED" if n_path > 0 and any(
            d["mutable"] for d in improvement_directions)
            else "PARTIALLY_QUANTIFIED")

    # ---- computation log (Art. XXXVIII: rank-3/4 outputs carry logs) ----
    computation_log = {
        "evaluator_id": EVALUATOR_ID,
        "fidelity_tier": FIDELITY_TIER,
        "evidence_rank": EVIDENCE_RANK,
        "input_state_sha256": sha256_obj(state or {}),
        "conventions": [LEVERAGE_CONVENTION, CONSTRAINT_BLOCK_POLICY],
        "steps": [
            f"resolved objective {obj_target} ({obj_dir})",
            f"checked {len(constraints)} constraint(s) numerically "
            f"where values exist",
            f"propagated signs over "
            f"{len((state or {}).get('dependencies') or [])} relation(s)",
            f"ranked {len(movable)} movable improving direction(s)",
        ],
        "computed_at": utc_now(),
        "deterministic": True,
    }

    return {
        "evaluator_id": EVALUATOR_ID,
        "fidelity_tier": FIDELITY_TIER,
        "evidence_rank": EVIDENCE_RANK,
        "status": status,
        "objective": {
            "target": obj_target, "direction": obj_dir,
            "known": obj_known,
            "basis": (objective or {}).get("basis"),
        } if objective else None,
        "constraint_results": constraint_results,
        "sensitivity": sensitivity,
        "improvement_directions": improvement_directions,
        "limiting_variable": limiting_variable,
        "predictions": predictions,
        "uncertainty": uncertainty,
        "computation_log": computation_log,
        "evidence_class_note": (
            "every prediction in this evaluation is a MODEL-class "
            "inference (AI_INFERENCE rank 3) computed from declared "
            "technical state — it is NOT a measurement and NOT a "
            "physical observation (Art. XXVIII / XXXVIII)"),
    }


def _influence_on(state: Dict[str, Any], pid: str
                  ) -> Dict[str, Dict[str, Any]]:
    """Which parameters influence `pid` directly (reverse adjacency)."""
    out: Dict[str, Dict[str, Any]] = {}
    for d in (state or {}).get("dependencies") or []:
        if str(d.get("effect")) == pid:
            out[str(d.get("cause"))] = {
                "sign": _sign(str(d.get("direction"))),
                "relation_id": d.get("relation_id"),
                "relation_class": d.get("relation_class")}
    return out


def evaluate_candidate_technically(spec: Dict[str, Any]) -> \
        Dict[str, Any]:
    """Evaluate a candidate's spec: reads the technical_state section
    and runs the analytical evaluation. A spec WITHOUT a technical
    state returns the honest UNQUANTIFIED evaluation (recorded, never
    an error)."""
    state = get_technical_state(spec)
    if state is None:
        return {
            "evaluator_id": EVALUATOR_ID,
            "fidelity_tier": FIDELITY_TIER,
            "evidence_rank": EVIDENCE_RANK,
            "status": "UNQUANTIFIED",
            "objective": None,
            "constraint_results": [],
            "sensitivity": {},
            "improvement_directions": [],
            "limiting_variable": None,
            "predictions": {},
            "uncertainty": {
                "unknown_value_params": [],
                "note": ("no technical_state section on this spec — "
                         "the technical layer never engaged; recorded "
                         "as an honest gap, never as a failure")},
            "computation_log": {
                "evaluator_id": EVALUATOR_ID,
                "fidelity_tier": FIDELITY_TIER,
                "input_state_sha256": None,
                "steps": ["no technical state present"],
                "computed_at": utc_now(),
                "deterministic": True},
            "evidence_class_note": (
                "no prediction made — nothing was evaluated"),
        }
    return evaluate_technical_state(state)


def technical_evaluate_wrapper(ctx: Any) -> Dict[str, Any]:
    """Evaluator-contract adapter (the R378 registry shape): the
    technical evaluator registered behind the SAME pluggable contract
    the term-rule evaluator uses. Diagnostics remain additive — the
    registered default evaluator is unchanged (registration order)."""
    return evaluate_candidate_technically(ctx.spec)


# self-registration behind the evaluator contract (opt-in use; never
# the default — no silent upgrade of the diagnostic baseline)
register_evaluator(EVALUATOR_ID, FIDELITY_TIER,
                   technical_evaluate_wrapper)
